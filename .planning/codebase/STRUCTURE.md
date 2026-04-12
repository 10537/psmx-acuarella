# Project Structure

## Overview
The repository follows the standard Odoo 18 module structure. Custom functionality is divided into multiple apps/modules for maintainability and modularity.

## Directory Layout

### Custom Odoo Modules
- `acuarella_api/`: Core FastAPI infrastructure for Acuarella.
- `acuarella_stock_reports/`: Inventory reporting logic.
- `wms_sorter_api/`: Warehouse sorter integration (fastapi routers, models, schemas).
  - Models: `wms.sorter.chute`, `wms.sorter.log`, `wms.sorter.api.log`.
  - Automation: `data/ir_cron.xml` for log retention.
- `delivery_coordinadora/`: Colombian carrier integration for Coordinadora.

### Integration Modules (Shopify)
- `integration/`: Base integration framework.
- `integration_shopify/`: Shopify-specific integration logic.
- `integration_shopify_ssot/`: Source of Truth (SSOT) logic for Shopify.
- `integration_shopify_observability/`: Logging and tracing for e-commerce sync.

### Infrastructure & Dependencies (OCA/Standard)
- `oca-queue/`: OCA Queue for async jobs (`queue_job`).
- `common_connector_library/`: Shared library for connectors.

## Module Internals
Each custom module typically includes:
- `models/`: Odoo database models (Python).
- `routers/`: FastAPI endpoint definitions (FastAPI).
- `schemas/`: Pydantic models for API validation.
- `views/`: Odoo UI XML definitions (Forms, Lists).
- `security/`: Access rights configuration (CSV).
- `data/`: XML data (FastAPI endpoints, etc.).
- `dependencies.py`: FastAPI authorization and Odoo env dependencies.
