# Technology Stack

## Platform

- **Odoo 18** — ERP platform (Community / Enterprise base)
- **Python 3.x** — all backend business logic
- **PostgreSQL** — relational database (Odoo default)
- **OWL (Odoo Web Library) / JavaScript** — frontend components via Odoo asset bundles
- **SCSS** — custom report and UI styles

## Custom Modules (this repository)

| Module | Version | Purpose |
|---|---|---|
| `acuarella_api` | 18.0.1.0.0 | FastAPI endpoints for shipping info/status updates |
| `acuarella_stock_reports` | 18.0.1.0.0 | Custom batch picking reports and stock document layouts |
| `delivery_coordinadora` | 18.0.1.0 | Coordinadora carrier integration (rate, guide, tracking) |
| `integration_shopify_ssot` | 18.0.1.0.0 | Enforces Odoo as Single Source of Truth for Shopify |
| `integration_shopify_inventory_ssot` | 18.0.1.0.0 | Exports only "Free to Use" stock to prevent overselling |
| `integration_shopify_customer_ssot` | 18.0.1.0.0 | Real-time Odoo contact sync to Shopify (B2B/B2C) |
| `integration_shopify_reconciliation` | 18.0.1.0.0 | Daily cron reconciliation to detect inventory drift |
| `integration_shopify_observability` | 18.0.1.0.0 | Structured logging and distributed tracing (correlation_id) |
| `website_sale_melonn` | 18.0.2.0 | Envia/Melonn shipping carrier integration (REST) |
| `wms_sorter_api` | 18.0.1.0.0 | FastAPI interface for warehouse sorter equipment |

## Third-Party Odoo Modules (vendored/included)

| Module | Source | Purpose |
|---|---|---|
| `integration` | VentorTech (OPL-1) | Core e-commerce connector framework |
| `integration_shopify` | VentorTech (OPL-1) | Shopify Connector PRO |
| `shopify_ept` | Emipro / common_connector_library | Alternate Shopify connector base |
| `common_connector_library` | Emipro | Shared connector utilities |
| `ventor_base` | VentorTech (LGPL-3) | WMS base for Ventor mobile picking |
| `oca-queue` (`queue_job`, `queue_job_subscribe`) | OCA / Camptocamp (LGPL-3) | Async job queue |

## Key Python Libraries

| Library | Usage |
|---|---|
| `fastapi` | REST API layer inside Odoo (via `odoo-addon-fastapi`) |
| `fastapi_auth_api_key` | API key authentication for FastAPI endpoints |
| `ShopifyAPI==12.7.0` | Direct Shopify API calls |
| `zeep` | SOAP client for Coordinadora web services |
| `requests` | HTTP calls (queue_job, reconciliation, Envia carrier) |
| `pydantic` | Request/response schema validation (via FastAPI) |

## Async / Background Processing

- **OCA queue_job** — all heavy sync operations (Shopify product/order/inventory export) are queued as background jobs
- **ir.cron** — scheduled actions for daily reconciliation (`_cron_reconcile_shopify`) and sorter log cleanup

## Licensing mix

- Custom modules: `LGPL-3` or `OPL-1`
- VentorTech connector: `OPL-1` (commercial)
- OCA queue: `LGPL-3`
- Stock reports: `OEEL-1` (Odoo Enterprise)
