# Coding Conventions

**Analysis Date:** 2026-04-16

## Naming Patterns

**Files:**
- Python model files: `snake_case.py` matching Odoo model name (e.g., `stock_picking.py`, `sale_order.py`)
- Router files: `snake_case_router.py` (e.g., `shipping_router.py`)
- Schema files: `snake_case_schema.py` (e.g., `shipping_schema.py`)
- Test files: `test_<feature>.py` (e.g., `test_shipping_api.py`, `test_wave_end.py`)

**Python Classes:**
- Odoo models: `PascalCase` (e.g., `StockPicking`, `SaleOrder`, `WizardDeliveryEnvia`)
- Pydantic schemas: `PascalCase` + `Schema` suffix (e.g., `ShippingUpdateSchema`)
- Custom exceptions: `PascalCase` describing error (e.g., `NotMappedFromExternal`, `ResourceConflict`)
- Test classes: `Test<Feature>` prefix (e.g., `TestShippingApi`, `TestWaveEnd`)

**Functions and Methods:**
- Python: `snake_case` throughout
- Odoo action methods: `action_<verb>` (e.g., `action_generar_guia`)
- Odoo compute methods: `_compute_<field>` (e.g., `_compute_fields`)
- Odoo private methods: `_snake_case` (e.g., `_send_by_melonn`)
- Integration API methods: camelCase per inherited VentorTech convention (`integrationApiImportPaymentMethods`)

**Fields:**
- Custom fields on standard Odoo models: `x_` prefix — `x_carrier_tracking_ref`, `x_carrier_state` (`acuarella_api/models/stock_picking.py`)
- Extension fields on custom models: plain `snake_case` — `melonn_order`, `guia_envia_url` (`website_sale_melonn/models/sale_order.py`)
- Field `string=` labels use Spanish in Colombian-specific modules

## Code Style

**Formatting:**
- No autoformatter config at project root
- Indentation: **4 spaces** in newer modules (`acuarella_api`, `wms_sorter_api`, `integration`); **tabs** in legacy `website_sale_melonn/models/sale_order.py`
- Long lines suppressed with `# noqa: E501` in `integration/exceptions.py`

**License Headers:**
- VentorTech modules: `# Copyright 2020 VentorTech OU\n# License LGPL-3.0 or later`
- Local custom modules (`acuarella_api`, `website_sale_melonn`): no license header

## Import Organization

**Order:**
1. Standard library (`json`, `logging`, `requests`, `typing`)
2. Third-party (`fastapi`, `pydantic`, `zeep`)
3. Odoo framework (`from odoo import fields, models, api`)
4. Odoo addon (`from odoo.addons.fastapi.dependencies import odoo_env`)
5. Local/relative (`from ..routers.shipping_router import router`)

**Path Aliases:** None — relative imports used for intra-module references.

## Error Handling

**In Odoo Models:**
- `odoo.exceptions.UserError` for user-facing errors (UI dialog)
- `odoo.exceptions.ValidationError` for field-level constraints
- Wrap external HTTP calls: catch `requests.exceptions.HTTPError`, re-raise as `UserError`

```python
# website_sale_melonn/models/sale_order.py
try:
    response = requests.post(url, auth=HTTPBasicAuth(user, password), headers=headers, data=json.dumps(datas))
    response.raise_for_status()
except requests.exceptions.HTTPError as err:
    raise UserError('{}\n\t{}'.format(err, json_response['respuesta']))
```

**In FastAPI Routers:**
- `fastapi.HTTPException` with explicit `status_code`
- Success: return plain dict `{"status": "success", "message": "..."}`

```python
# acuarella_api/routers/shipping_router.py
picking = env["stock.picking"].search([("origin", "=", data.order_name)], limit=1)
if not picking:
    raise HTTPException(status_code=404, detail="Picking not found for this Order")
```

**Custom Exception Hierarchy (`integration/exceptions.py`):**
- Domain exceptions inherit from `Exception`: `NotMappedFromExternal`, `ApiImportError`, `TooManyRequestsError`, `ResourceConflict`
- `ErrorStore` static utility: typed error codes E1xx (import), E2xx (export), E3xx (mapping)
- `IntegrationNotImplementedError`: auto-captures calling method name from call stack

## Logging

**Pattern:** Module-level `_logger = logging.getLogger(__name__)` at top of file.

```python
_logger.info(json_response)    # Log API responses before processing
_logger.warning('...')         # Warn on ambiguous usage
```

Tests suppress logs with `@mute_logger('odoo.addons.integration.tools')`.

## Comments

**When to Comment:**
- Inline for non-obvious constants: `"Mca_NoSabado": 0, # Entrega los sábados (default no)`
- Section dividers in long wizard methods: `# -- Remitente --`, `# -- Destinatario --`
- Test comments explain framework limitations (e.g., auth bypass note in `acuarella_api/tests/test_shipping_api.py`)
- TODO stubs in unimplemented patches: `def execute(self, *args, **kw): """TODO"""`

**Docstrings:** Used selectively on business action methods; most internal methods lack them.

## Function Design

**Size:** Methods can be long (100+ lines) — e.g., `WizardDeliveryEnvia.send_by_envia` in `website_sale_melonn/models/sale_order.py`

**Return Values:**
- Odoo window actions: `{'type': 'ir.actions.act_window', 'res_model': ..., 'view_mode': ...}`
- FastAPI routers: `{"status": "success", "message": "..."}`
- Compute methods: assign to `self.<field>`, no return

## FastAPI Extension Pattern (`acuarella_api`, `wms_sorter_api`)

```
<module>/
├── models/fastapi_endpoint.py   # Extends fastapi.endpoint, registers router via _get_fastapi_routers()
├── routers/<feature>_router.py  # APIRouter with business logic
├── schemas/<feature>_schema.py  # Pydantic BaseModel for request/response
├── dependencies.py              # Auth helpers (get_current_user)
└── tests/test_<feature>.py
```

**Exports:** `__init__.py` uses `from . import <submodule>` chains; no `__all__`.
