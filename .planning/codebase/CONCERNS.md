# Codebase Concerns & Technical Debt

## Architectural Challenges
- **Synchronous Odoo vs Asynchronous FastAPI:** Odoo's `Environment` and database operations are blocking. FastAPI's asynchronous nature needs careful coordination (e.g., using `run_in_threadpool` or accepting blocking behavior) to avoid performance degradation.
- **Model Hooks:** Direct record creation/updates in FastAPI routers must be carefully audited to ensure all relevant Odoo `create`/`write` overrides are triggered correctly.

## Reliability & Performance
- **Sorter API Push:** If the warehouse equipment pushes status notifications rapidly, ensure Odoo scales and handles concurrent database locks on the same records (e.g., `stock.move.line`).
- **Shopify Sync Latency:** Synchronizing complex product trees and warehouse inventory in real-time across Shopify and Odoo can lead to performance bottlenecks. Use `queue_job` extensively for non-realtime flows.

## Security & Maintenance
- **API Key Management:** Ensure keys are securely stored and rotated. Currently, these appear to be managed within Odoo. Add monitoring for failed API authentication attempts.
- **FastAPI Dependency Updates:** Maintaining consistent Pydantic versioning across both Odoo and a potential external environment.

## Suggested Improvements
- Implement a more structured API logging/observability layer (already partially handled by `integration_shopify_observability`).
- Standardize the `x_` prefix usage across all custom fields for clarity.
- Increase unit test coverage for the FastAPI routers using `TestClient`.
