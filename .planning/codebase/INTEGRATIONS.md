# External Integrations

## E-commerce: Shopify
- **Module:** `integration_shopify`
- **Focus:** Multi-channel e-commerce synchronization (orders, customers, inventory).
- **Communication:** Shopify REST/GraphQL API via `ShopifyAPI` library.
- **Workflow:** `integration_shopify_ssot` manages Source of Truth (SSOT).

## Warehouse: Sorter API
- **Module:** `wms_sorter_api`
- **Focus:** Real-time communication with warehouse sorting machines.
- **Communication:** FastAPI endpoints (`wms_sorter_api/routers`).
- **Functionality:** Wave sorting data pushes, status updates, and order queries.
- **Observability:** Technical audit layer (`wms.sorter.api.log`) capturing all raw JSON requests/responses and sender IPs.

## Carrier: Coordinadora
- **Module:** `delivery_coordinadora`
- **Focus:** Shipping logistics for Colombia (Coordinadora).
- **Communication:** SOAP/REST API (standard Odoo `delivery` carrier implementation).

## Backend: OCA queue_job
- **Module:** `oca-queue`
- **Focus:** Asynchronous execution and retry logic for long-running integrations.
- **Dependency:** PostgreSQL-based queueing.
