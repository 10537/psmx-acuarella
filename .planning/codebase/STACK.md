# Technology Stack

## Core
- **Framework:** Odoo 18.0 (LGPL-3/OPL-1)
- **Language:** Python 3.10+
- **Database:** PostgreSQL

## API Infrastructure
- **API Framework:** FastAPI (integrated via Odoo `fastapi` module)
- **Authentication:** API Key (`fastapi_auth_api_key`)
- **Data Validation:** Pydantic (via FastAPI)

## External Integrations
- **E-commerce:** Shopify (via `integration_shopify` and `ShopifyAPI` python library)
- **Carrier:** Coordinadora (via `delivery_coordinadora`)
- **Warehouse:** Custom Sorting Equipment (via `wms_sorter_api`)

## Backend Processing
- **Queue System:** OCA `queue_job` for asynchronous task management.
- **Reporting:** Custom stock reports (`acuarella_stock_reports`)

## Frontend (Odoo)
- **Web Client:** Odoo Web Framework (OWL)
- **Templating:** QWeb (XML)
