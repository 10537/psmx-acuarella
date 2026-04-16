# Testing Patterns

**Analysis Date:** 2026-04-16

## Test Framework

**Runner:** Odoo built-in test runner (wraps `unittest`)
**Base Class:** `odoo.tests.common.TransactionCase` — all tests in this codebase use this class; each test method runs inside a rolled-back transaction

**Run Commands:**
```bash
./odoo-bin -i <module_name> -c <config_file> --test-enable --stop-after-init
```

## Test File Organization

**Location:** `tests/` directory inside each Odoo module
**Naming:** `test_<feature>.py` (e.g., `test_shipping_api.py`, `test_wave_end.py`)
**Registration:** `tests/__init__.py` explicitly imports every test module

```
acuarella_api/tests/
├── __init__.py              # from . import test_shipping_api
└── test_shipping_api.py

integration_shopify/tests/
├── __init__.py
├── data/                    # XML fixtures loaded at setUp
├── json_data.py             # Shared JSON test data constants
├── init_integration_shopify.py   # Base class for integration tests
├── patch/                   # API mock implementations
│   ├── shopify_api_patch.py
│   ├── storage.py
│   └── resources_patch/
└── test_*.py
```

## Test Structure

**Suite Organization:**
```python
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestIntegrationShopify(IntegrationShopifyBase):

    def setUp(self):
        super(TestIntegrationShopify, self).setUp()

    def test_<behavior>(self):
        # Arrange: use self.env to create/fetch records
        # Act: call method under test
        # Assert: self.assertEqual / self.assertTrue / self.assertFalse
```

**Base Class Pattern:**
- Complex test suites define a base class: `OdooIntegrationBase` (`integration/tests/config/integration_init.py`), extended by `IntegrationShopifyBase` (`integration_shopify/tests/init_integration_shopify.py`)
- Base setUp loads XML fixture data via `load_xml(env, module, path_file, filename)`
- Base setUp creates common records (`self.integration`, `self.wh`, `self.company`, `self.product1`, etc.)

**Minimal setUp Pattern** (simpler modules):
```python
class TestShippingApi(TransactionCase):
    def setUp(self):
        super().setUp()
        self.picking = self.env["stock.picking"].create({
            "name": "TEST-PICKING-001",
            "origin": "SO001",
            "picking_type_id": self.env.ref("stock.picking_type_out").id,
        })
```

## Mocking

**Shopify API Patch Pattern** (`integration_shopify/tests/patch/`):
- Subclasses of the real client/resource classes return static test data
- `ShopifyAPIClientPatchTest` replaces the live Shopify client with hardcoded fixture responses
- `ShopifyGraphQLPatchTest` overrides `execute()` to return `{}` stub
- Injected via `self.patch(type(self.integration), 'get_class', self._get_class_patch)` in setUp

**FastAPI Auth Bypass:**
- Router functions called directly: `update_shipping_info(payload, env=self.env)`
- This bypasses `dependencies=[Depends(get_current_user)]` — auth is not tested in unit tests
- See comment in `acuarella_api/tests/test_shipping_api.py` explaining this limitation

**Queue Job Bypass:**
- Set context `{'queue_job__no_delay': 1}` in base setUp to execute jobs synchronously during tests

## Fixtures and Factories

**XML Fixtures:**
```python
# integration/tests/config/integration_init.py
def load_xml(env, module, path_file, filename):
    pth = file_path(f'{module}/{path_file}/{filename}', ('xml',), env)
    convert_file(env, module, f'{path_file}/{filename}', {}, 'init', False, 'test', pth)
```
- XML test data in `tests/data/` directories
- Records accessed via `self.env.ref('module.xml_id')`

**Inline Record Creation:**
```python
self.picking = self.env["stock.picking"].create({...})
self.batch = self.env["stock.picking.batch"].create({...})
```

**Shared JSON Data:** `integration_shopify/tests/json_data.py` holds raw API response fixtures.

## Coverage

- No coverage requirements enforced — no coverage config detected.

## Test Types

**Unit Tests:**
- Scope: single model method or router function
- Examples: `acuarella_api/tests/test_shipping_api.py`, `wms_sorter_api/tests/test_wave_end.py`

**Integration Tests:**
- Scope: full import/export flow through multiple models with patched external APIs
- Examples: `integration_shopify/tests/test_integration_shopify.py`
- Base class: `IntegrationShopifyBase` → `OdooIntegrationBase`

**E2E Tests:** Not used.

## Common Patterns

**Odoo Record Invalidation After Write:**
```python
self.picking.invalidate_recordset()
self.assertEqual(self.picking.x_carrier_state, "Delivered")
```

**Tagged Tests:**
```python
@tagged('post_install', '-at_install')
class TestIntegrationShopify(IntegrationShopifyBase):
    ...
```

**Suppress Log Noise:**
```python
@mute_logger('odoo.addons.integration.tools')
def test_convert_product_fields_in_and_out(self):
    ...
```

**Disable Tracking:**
```python
self.env = self.env(context=dict(self.env.context, tracking_disable=True))
```
