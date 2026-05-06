# External Integrations

## 1. Shopify

**Modules:** `integration`, `integration_shopify`, `integration_shopify_ssot`, `integration_shopify_inventory_ssot`, `integration_shopify_customer_ssot`, `integration_shopify_reconciliation`, `integration_shopify_observability`

**Library:** `ShopifyAPI==12.7.0`

**What it does:**
- Bidirectional sync of products, variants, inventory, orders, and customers between Odoo 18 and Shopify stores.
- SSOT enforcement: Odoo is the authoritative source; destructive webhooks from Shopify are blocked.
- Inventory export sends only "Free to Use" qty (On Hand minus Reserved/Outgoing) to prevent overselling.
- Real-time customer/contact sync (B2B and B2C).
- Daily reconciliation cron (`_cron_reconcile_shopify`) checks for inventory, product, and order drift and notifies configured email recipients and an admin user via mail activities.
- Structured logging injects a `correlation_id` into every queue_job and connector log entry to enable distributed tracing across the async job chain.

**Configuration points (on `sale.integration`):**
- `enforce_ssot` toggle
- `reconciliation_email_list` (comma-separated)
- `reconciliation_admin_id` (res.users)

---

## 2. Coordinadora Carrier

**Module:** `delivery_coordinadora`

**Protocol:** SOAP (via `zeep`) + JSON-RPC over HTTP for label printing

**What it does:**
- Extends Odoo's `delivery.carrier` with a `coordinadora` delivery type.
- Supports rate calculation, shipping guide (label) generation, cancellation, and parcel tracking.
- Dual-environment: test (`sandbox.coordinadora.com`) and production endpoints configurable per carrier record.
- Fields: Client ID (Acuerdo), User, Password, API Key, NIT, Division, label ID.
- Normalizes Colombian city codes (DANE format, 8 digits) before sending to the carrier API.
- Adds `carrier_delivery_ref` and `carrier_delivery_url` fields to `sale.order`.

**WSDL endpoints:**
- Guides: `https://sandbox.coordinadora.com/agw/ws/guias/1.6/server.php?wsdl` (test)
- Tracking: `https://sandbox.coordinadora.com/ags/1.5/server.php?wsdl` (test)

---

## 3. Envia / Melonn Shipping

**Module:** `website_sale_melonn`

**Protocol:** REST JSON (via `requests`), HTTP Basic Auth

**What it does:**
- Extends `delivery.carrier` with Envia shipping carrier support, including test/production dual config.
- Shipping guide generation from sale orders via wizard (`WizardDeliveryEnvia`).
- Stores Melonn order reference (`melonn_order`) and generated guide URL (`guia_envia_url`) on `sale.order`.
- Extends `res.city` with the Colombian DANE city code (`code` field) required for address validation.
- Depends on `l10n_co` (Colombian localization).
- Includes SQL migration files (`code_dane-R1.sql`, `code_dane-R2.sql`) for seeding DANE city codes.

**Configuration per carrier:** regional code, office code, account, recaudo account, URL, username, password (separate sets for test and production).

---

## 4. Acuarella Shipping API (Inbound REST)

**Module:** `acuarella_api`

**Protocol:** REST / FastAPI (via `odoo-addon-fastapi`)

**Authentication:** Bearer token → `auth.api.key`

**Endpoints:**
- `POST /update_info` — updates carrier tracking ref, partner name, identity document, delivery address, and state on a `stock.picking` (matched by `origin` = order name).
- `POST /update_status` — updates only the carrier state on a `stock.picking`.

**Custom fields written to `stock.picking`:**
`x_carrier_tracking_ref`, `x_carrier_partner_name`, `x_carrier_identity_document`, `x_carrier_delivery_address`, `x_carrier_state`

---

## 5. WMS Sorter API (Bidirectional REST)

**Module:** `wms_sorter_api`

**Protocol:** REST / FastAPI (via `odoo-addon-fastapi`)

**Authentication:** Bearer token → `auth.api.key`

**Server endpoints (equipment calls Odoo):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/wave-sorting` | Equipment requests move lines for a batch by `wave_No` |
| GET | `/scheduled-data` | Equipment polls for all active/in-progress batches |
| POST | `/realtime-data` | Equipment looks up a single product by barcode |
| POST | `/sorting-status-push` | Equipment reports a sorted item (updates `sorter_state` on `stock.move.line`) |
| POST | `/wave-end` | Equipment signals wave completion; Odoo calls `batch.action_done()` |

**Client mode (Odoo calls equipment):**
- `StockPickingBatch.action_push_sorting_data()`: pushes all move lines for a batch to the equipment's `/in_order` endpoint.
- Configurable via system parameter `wms_sorter_api.auto_push_on_confirm`.

**All API requests logged** to `wms.sorter.api.log` (IP, payload, response, status code, errors).

**System parameters:**
- `wms_sorter_api.equipment_url` — sorter machine URL
- `wms_sorter_api.request_timeout` — outbound timeout (default 10s)
- `wms_sorter_api.auto_push_on_confirm` — auto-push on batch confirm
- `wms_sorter_api.total_chutes` — number of chutes (default 48)

---

## 6. OCA Job Queue

**Module:** `oca-queue` (`queue_job`, `queue_job_subscribe`)

**What it does:**
- Provides the async job queue infrastructure used by the VentorTech Shopify connector and the custom observability layer.
- All Shopify sync operations (product export, inventory push, order import, customer sync) are dispatched as `queue_job` records.
- The observability module hooks into job execution to inject `correlation_id` into structured log output.

---

## Notes

- `website_sale_melonn` was originally branded for "Melonn" but its actual current carrier is **Envia** — both names appear in the code.
- The FastAPI modules (`acuarella_api`, `wms_sorter_api`) depend on `odoo-addon-fastapi`, which is not vendored in this repo — it must be present in the Odoo addons path separately.
- `acuarella_stock_reports` carries an `OEEL-1` license, meaning it requires an Odoo Enterprise subscription.
