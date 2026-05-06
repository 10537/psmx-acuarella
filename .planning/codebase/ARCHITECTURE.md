# Architecture Overview — psmx-acuarella

## Project Purpose

This repository is a collection of custom Odoo 18 add-on modules for a Colombian fashion/retail company (Acuarella / JDC Luxury). The modules span three main concerns:

1. **Shopify Integration Hardening** — a layer of custom modules built on top of the third-party VentorTech Shopify Connector PRO (`integration` + `integration_shopify`) to enforce data integrity, prevent overselling, and add observability.
2. **Warehouse & Logistics Operations** — two FastAPI-based modules that integrate Odoo with external hardware (a shipping carrier webhook receiver and a physical warehouse sorting machine).
3. **Shipping Carrier Integrations** — native Odoo `delivery.carrier` extensions for Coordinadora (SOAP) and Envía (REST JSON) carriers, specific to the Colombian logistics market.

---

## High-Level System Diagram

```
                     ┌────────────────────────────────────────┐
                     │             Odoo 18 Instance            │
                     │                                         │
                     │  ┌──────────────────────────────────┐  │
                     │  │     VentorTech Integration Stack  │  │
                     │  │  integration (core)               │  │
                     │  │  integration_shopify              │  │
                     │  └──────────────────────────────────┘  │
                     │           ▲ extends (_inherit)          │
                     │  ┌──────────────────────────────────┐  │
                     │  │   Shopify Hardening Layer (custom)│  │
                     │  │  integration_shopify_ssot         │  │
                     │  │  integration_shopify_inventory_ssot│ │
                     │  │  integration_shopify_reconciliation│ │
                     │  │  integration_shopify_observability │  │
                     │  │  integration_shopify_customer_ssot │  │
                     │  └──────────────────────────────────┘  │
                     │                │                        │
                     │        OCA queue_job (async)            │
                     │                │                        │
                     │  ┌──────────────────────────────────┐  │
                     │  │      FastAPI Endpoints             │  │
                     │  │  acuarella_api (shipping webhooks)│  │
                     │  │  wms_sorter_api (sorter machine)  │  │
                     │  └──────────────────────────────────┘  │
                     │                                         │
                     │  ┌──────────────────────────────────┐  │
                     │  │   Carrier Integrations             │  │
                     │  │  delivery_coordinadora (SOAP)     │  │
                     │  │  website_sale_melonn (Envía REST) │  │
                     │  └──────────────────────────────────┘  │
                     │                                         │
                     │  ┌──────────────────────────────────┐  │
                     │  │   Custom Reports & UI              │  │
                     │  │  acuarella_stock_reports           │  │
                     │  └──────────────────────────────────┘  │
                     └────────────────────────────────────────┘
                              │                     │
                    ┌─────────┴──────┐    ┌─────────┴──────┐
                    │  Shopify Store │    │ Sorter Machine │
                    │  (GraphQL API) │    │  (HTTP/JSON)   │
                    └────────────────┘    └────────────────┘
```

---

## Module Dependency Graph

```
queue_job (OCA)
  └─ integration (VentorTech core)
       └─ integration_shopify (VentorTech Shopify)
            ├─ integration_shopify_ssot  (custom)
            ├─ integration_shopify_reconciliation (custom)
            │    └─ integration_shopify_ssot
            ├─ integration_shopify_observability (custom)
            │    ├─ integration_shopify_reconciliation
            │    └─ queue_job
            ├─ integration_shopify_inventory_ssot (custom)
            │    ├─ integration_shopify_ssot
            │    └─ integration_shopify_observability
            └─ integration_shopify_customer_ssot (custom)
                 ├─ integration_shopify_ssot
                 └─ integration_shopify_observability

stock + fastapi + fastapi_auth_api_key
  ├─ acuarella_api (custom FastAPI)
  └─ wms_sorter_api (custom FastAPI)
       └─ stock_picking_batch

delivery + stock_delivery + mail
  └─ delivery_coordinadora (custom)

base + sale + website_sale + delivery + l10n_co
  └─ website_sale_melonn (custom)

sale_stock + stock_picking_batch + stock_delivery
  └─ acuarella_stock_reports (custom)

common_connector_library (Emipro, standalone)
  └─ shopify_ept (Emipro, standalone)

ventor_base (VentorTech, standalone)
```

---

## Shopify Hardening Layer — Detail

This is the most architecturally sophisticated part of the repository. Five modules each extend `sale.integration` via Odoo's `_inherit` mechanism.

### `integration_shopify_ssot` — SSOT Policy Enforcement

**Pattern:** `@api.constrains` on `sale.integration`.

- `enforce_ssot` boolean field (default `True`).
- `_check_ssot_webhooks`: blocks `products/update` or `products/delete` webhooks when SSOT is on.
- `_check_location_mapping`: validates every Shopify location has a mapped Odoo warehouse location.

Enforcement is at the ORM constraint level — always active regardless of the API path that triggers a change.

### `integration_shopify_inventory_ssot` — Overselling Prevention

**Pattern:** Override `_prepare_inventory_data` on `sale.integration`.

Replaces the standard quantity with:
```
Free to Use = max(0, qty_available - outgoing_qty)
```

A **PostgreSQL advisory lock** (`pg_advisory_xact_lock`) is acquired per `(integration_id, product_id)` pair to serialize concurrent inventory push jobs.

Only applies to storable products (`product.type == 'consu' and product.is_storable`).

### `integration_shopify_reconciliation` — Daily Drift Detection

**Pattern:** `ir.cron` calling `_cron_reconcile_shopify`.

For each active Shopify integration:
1. Fetches all inventory from Shopify via the adapter.
2. Calculates Odoo's Free to Use stock per product.
3. Detects divergences larger than 1 unit.
4. Notifies via: email (`reconciliation_email_list`), Odoo mail activity (`reconciliation_admin_id`), and chatter post.

### `integration_shopify_observability` — Structured Logging + Distributed Tracing

**Pattern:** Custom logger wrapper + `contextvars.ContextVar` + monkey-patching OCA `queue_job`.

Key components:
- `StructuredLogger` (`tools/logging_helper.py`): wraps `logging.Logger`, injects `correlation_id`, `integration_id`, `entity_type`, `entity_id` into every log record.
- `correlation_id_var`: a `ContextVar` propagated across async queue workers.
- `queue_job.py`: monkey-patches `Job.perform`. Before each job, retrieves `correlation_id` from job context and restores it in `correlation_id_var`; clears after completion.
- Overrides `_cron_reconcile_shopify` to generate a root `correlation_id` (UUID4) at cron start and propagate it to all downstream jobs.

### `integration_shopify_customer_ssot` — Real-time Customer Sync

**Pattern:** ORM `create`/`write`/`unlink` hooks on `res.partner` + `queue_job` async.

On partner create/write (name, email, phone, is_company, active) or unlink, enqueues an async job to sync the change to all active Shopify integrations.

Uses **Shopify Admin GraphQL API** exclusively. Implements:
- **Upsert logic**: checks `integration.res.partner.mapping`, falls back to email lookup before deciding to create or update.
- **Address deduplication**: queries existing default address ID before pushing updates.
- Tags: B2B → `"Mayorista"`, B2C → `"Detal"`, archived → `"DISABLED"`.

---

## FastAPI Warehouse Modules

Both modules use `odoo-addon-fastapi`, which mounts FastAPI apps within Odoo's HTTP stack. Auth is via Bearer token against `auth.api.key`.

### `acuarella_api` — Shipping Update Webhook Receiver

| Method | Path | Description |
|--------|------|-------------|
| POST | `/update_info` | Updates carrier tracking fields on `stock.picking` identified by `origin` |
| POST | `/update_status` | Updates only the carrier state on `stock.picking` |

Custom fields on `stock.picking`: `x_carrier_tracking_ref`, `x_carrier_partner_name`, `x_carrier_identity_document`, `x_carrier_delivery_address`, `x_carrier_state`.

### `wms_sorter_api` — Warehouse Sorting Machine Integration

Bidirectional integration with a 48-chute physical conveyor. Odoo is both server (receives from equipment) and client (pushes to equipment).

All requests logged via `SorterApiLoggedRoute` (subclass of `fastapi.routing.APIRoute`) into `wms.sorter.api.log`.

**Custom models:**
- `wms.sorter.chute` — state of each physical chute (`free`/`occupied`)
- `wms.sorter.log` — event audit log (direction, level, wave, SKU, barcode, qty, chute)
- `wms.sorter.api.log` — raw HTTP request/response log
- `stock.move.line` extended with `sorter_state` (`draft`/`picking`/`collected`)

---

## Carrier Integrations

### `delivery_coordinadora` — Coordinadora SOAP + REST

Adds `coordinadora` as a `delivery_type` on `delivery.carrier` via `zeep` (SOAP) and `requests` (JSON-RPC labels).

Capabilities: rate calculation, guide generation (returns PDF attachment), label printing, cancellation, tracking link. City codes normalized to 8-digit DANE format via `_normalize_city_code`.

### `website_sale_melonn` — Envía Carrier + Melonn Fulfillment

Dual-purpose:
- **Envía**: guide generation via REST JSON + HTTP Basic Auth via `WizardDeliveryEnvia` wizard.
- **Melonn**: pushes orders to 3PL API when carrier is not Envía.
- Extends `res.city` with DANE `code` field. Includes SQL migration files for seeding DANE codes.

---

## Authentication

Both FastAPI modules share the same pattern:
1. Client sends `Bearer <token>` header.
2. `get_current_user` dependency looks up token in `auth.api.key`.
3. 401 if not found; returns associated `res.users` if found.

---

## Database Considerations

- Advisory locks in `integration_shopify_inventory_ssot` serialize inventory pushes per `(integration_id, product_id)`.
- All custom models use standard Odoo ORM — no raw SQL except the advisory lock call.
- `website_sale_melonn` ships SQL scripts for data migration (DANE city codes), not model code.

---

## External System Summary

| External System | Protocol | Direction | Module |
|----------------|----------|-----------|--------|
| Shopify Admin API | GraphQL (HTTPS) | Odoo → Shopify | integration_shopify_customer_ssot |
| Shopify webhooks | HTTP webhooks | Shopify → Odoo | integration_shopify (VentorTech) |
| Sorting machine | REST JSON | Bidirectional | wms_sorter_api |
| Carrier webhooks | REST JSON | Carrier → Odoo | acuarella_api |
| Coordinadora guide WS | SOAP/WSDL (Zeep) | Odoo → Coordinadora | delivery_coordinadora |
| Coordinadora tracking WS | SOAP/WSDL (Zeep) | Odoo → Coordinadora | delivery_coordinadora |
| Coordinadora labels | JSON-RPC over HTTP | Odoo → Coordinadora | delivery_coordinadora |
| Envía carrier | REST JSON (Basic Auth) | Odoo → Envía | website_sale_melonn |
| Melonn fulfillment | REST JSON (API key) | Odoo → Melonn | website_sale_melonn |
