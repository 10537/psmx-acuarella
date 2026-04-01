# Architecture Overview

## Hybrid Odoo-FastAPI Architecture
The project uses a hybrid architecture where Odoo 18 provides the core ERP functionality (Inventory, Sales, etc.) and FastAPI provides a high-performance, asynchronous REST API layer for real-time integrations.

### Components
1. **Odoo Layer:**
   - Standard Odoo modules (`stock`, `base`, `sale`).
   - Custom business logic in models (`wms.sorter.chute`, `wms.sorter.log`).
   - Database: PostgreSQL.

2. **Integration Layer (FastAPI):**
   - Managed via the `fastapi` Odoo module.
   - Routers define endpoints for external systems (Shopify, Warehouse Sorter).
   - Uses `Pydantic` for strict data validation (Schemas).

3. **Asynchronous Processing:**
   - `queue_job` (OCA) handles background tasks, ensuring Odoo remains responsive during long-running integration workflows.

### Data Flow (Sorter Example)
1. **Request:** Sorting equipment sends a POST request to `/wave-sorting`.
2. **FastAPI Context:** The `odoo_env` dependency initializes an Odoo Environment.
3. **Business Logic:** The router searches for the `stock.picking.batch` in Odoo.
4. **Response:** Odoo records are transformed into Pydantic models (JSON) and returned to the equipment.

## Security
- API Key authentication managed via `fastapi_auth_api_key`.
- Custom dependency `get_current_user` validates the token against Odoo configuration.
