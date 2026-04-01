# Testing Standards

## Unit Tests
- Use **Odoo's `TransactionCase`** for all database-related tests.
- Location: `tests/` directory within each module.
- Filename pattern: `test_*.py`.

## API Testing
- When testing FastAPI routers, call the endpoint functions directly from the Odoo test case.
- Pass `self.env` directly to the router functions as the `env: Environment` dependency.
- Bypass router-level authentication in unit tests by calling functions directly (logic-only testing).

## External Integrations
- Mock external service calls (e.g., Shopify, Carrier APIs) using `unittest.mock`.
- Ensure tests are independent of external network state.

## Execution
Run tests from the Odoo CLI:
```bash
./odoo-bin -i <module_name> -c <config_file> --test-enable --stop-after-init
```
