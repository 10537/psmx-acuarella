# Technical Concerns

**Analysis Date:** 2026-04-16

## Security

### Credentials Logged in Plain Text
- `delivery_coordinadora/models/delivery_carrier.py`: SOAP request payloads (including `password` and `apikey` fields) are passed to `_logger.info()` before sending. Credentials appear in Odoo server logs in clear text.
- `website_sale_melonn/models/sale_order.py`: `_logger.info(password)` logs the Envía carrier password directly.
- **Risk:** Any user with log access can read carrier credentials.

### Passwords Stored as Plain `fields.Char`
- Carrier password fields in `delivery_coordinadora` and `website_sale_melonn` use `fields.Char` with no encryption — stored in plain text in PostgreSQL and visible in the Odoo UI to users with carrier configuration access.

### No Rate Limiting on FastAPI Endpoints
- Both `acuarella_api` and `wms_sorter_api` rely solely on API key authentication with no rate limiting. A leaked key allows unlimited requests.

---

## Technical Debt

### Hardcoded Test URL in Production Payload
- `website_sale_melonn/models/sale_order.py`: `"https://test.jdchouse.com/"` is hardcoded inside the guide generation payload as `UrlRetorno`. This test URL is sent to the Envía carrier API in production.

### Carrier Routing by Display Name
- `website_sale_melonn/models/sale_order.py`: routing between Envía and Melonn is done by checking `picking.carrier_id.name == 'Envía'`. Breaks silently if the carrier record is renamed.

### Missing `external_dependencies` for `zeep`
- `delivery_coordinadora/__manifest__.py` does not declare `zeep` in `external_dependencies`. If `zeep` is missing, the module installs silently and only fails at runtime when a SOAP call is made.

### Inline Imports Inside Method Bodies
- Several methods in `website_sale_melonn` and `delivery_coordinadora` import `zeep`, `requests`, and `json` inside the method body rather than at module level. This hides dependency failures until the method is called.

### Deprecated Fields Retained Past Stated Deadlines
- `integration/models/sale_integration.py`: fields marked with `# deprecated — remove in X.Y` comments have not been removed. The 6,255-line god-class file makes it hard to audit what is still in use.

### Unimplemented Stub Methods
- Several `execute(self, *args, **kw)` methods contain only `"""TODO"""` as the body.

### Module Identity Mismatch
- `website_sale_melonn` is named for Melonn (3PL), but its primary integration is now **Envía** (carrier). Both names appear throughout, making it confusing to navigate.

---

## Known Bugs

### `update_shipping_info` Silently Drops Split Deliveries
- `acuarella_api/routers/shipping_router.py`: searches `stock.picking` by `origin` with `limit=1`. If a sale order has multiple delivery pickings (split delivery or backorder), only the first match is updated; the others are silently ignored.

### `x_carrier_tracking_ref` Duplicates Native Odoo Field
- `acuarella_api/models/stock_picking.py` adds `x_carrier_tracking_ref` as a custom field, but Odoo already has `carrier_tracking_ref` on `stock.picking`. The two fields are not linked, so tracking references may diverge.

### Commented-Out Test Assertions
- `integration_shopify/tests/`: several test methods have `# self.assertEqual(...)` assertions commented out, reducing actual test coverage without removing the scaffolding.

### `test_odoo.py` Stub
- `website_sale_melonn/test_odoo.py` contains only `print("Testing")`. Not an Odoo test case; has no value.

---

## Performance

### Missing HTTP Timeout on Melonn `requests.post`
- `website_sale_melonn/models/sale_order.py`: the `requests.post()` call to the Melonn API has no `timeout` parameter. A slow endpoint will block the Odoo worker thread indefinitely.

### Hardcoded Package Dimensions for All Coordinadora Shipments
- `delivery_coordinadora/models/delivery_carrier.py`: all rate and guide requests use hardcoded dimensions of 10×10×10 cm and a fixed weight. Actual package dimensions are never used, resulting in incorrect rate quotes.

### Large God-Class Model File
- `integration/models/sale_integration.py` is 6,255+ lines. Slow to parse, hard to review, high likelihood of merge conflicts.

---

## Fragile Areas

### Advisory Lock Scope
- `integration_shopify_inventory_ssot`: `pg_advisory_xact_lock` keyed on `(integration_id, product_id)` correctly serializes within a transaction, but does not protect against concurrent pushes from different Odoo processes if the lock is not held long enough.

### `queue_job` Monkey-Patch
- `integration_shopify_observability/models/queue_job.py` monkey-patches `Job.perform` from OCA's queue_job. Any OCA queue_job update that changes the `perform` signature or lifecycle will silently break distributed tracing.

### Shopify GraphQL Customer Sync — Email Lookup Fallback
- `integration_shopify_customer_ssot/models/sale_integration.py`: the email fallback `customers(first: 1, query: "email:X")` will arbitrarily pick one customer if multiple Shopify customers share the same email.

### Colombian City Code Normalization
- `delivery_coordinadora/models/delivery_carrier.py`: `_normalize_city_code` pads/trims to 8 digits. If `res.city.l10n_co_city_code` is missing or malformed, normalization may silently produce an invalid code.

---

## Test Coverage Gaps

| Module | Coverage |
|--------|----------|
| `delivery_coordinadora` | **Zero tests** — all SOAP/REST carrier logic untested |
| `website_sale_melonn` | **Zero real tests** — only `test_odoo.py` stub (no assertions) |
| `acuarella_stock_reports` | **Zero tests** |
| `acuarella_api` | Partial — happy path only; no tests for split deliveries or concurrent updates |
| `wms_sorter_api` | Partial — `test_wave_end.py` only; no tests for `/wave-sorting`, `/sorting-status-push`, or `action_push_sorting_data` |
| `integration_shopify_customer_ssot` | No tests for email collision fallback or deletion edge cases |
| `integration_shopify_reconciliation` | No tests for notification path or multi-integration runs |
