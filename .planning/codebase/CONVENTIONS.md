# Coding Conventions

## General Python
- Follow **PEP 8** style guidelines.
- Use explicit type hints for function arguments and return types.
- Use `logging.getLogger(__name__)` for all module-level logging.

## Odoo Development
- **Naming:** Modules are prefixed with `acuarella_` or `wms_sorter_`.
- **Fields:** Custom fields on standard models should use the `x_` prefix (e.g., `x_carrier_tracking_ref`) or be clearly named within the module's namespace.
- **Inheritance:** Use `_inherit` for extending standard Odoo models.
- **Security:** Define access rights in `security/ir.model.access.csv`.

## FastAPI Integration
- **Schemas:** Use Pydantic models in `schemas/` for all API request/response bodies.
- **Routers:** Group related endpoints in `routers/`. Use tags for documentation.
- **Dependencies:** Use `Depends(odoo_env)` to access the Odoo environment.
- **Auth:** Use `Depends(get_current_user)` for all protected endpoints.
- **Errors:** Raise `fastapi.HTTPException` with appropriate status codes for API-level errors.

## XML/UI
- Use standard Odoo XML syntax for views and data.
- Keep data files (like `fastapi_endpoints.xml`) in the `data/` directory.
