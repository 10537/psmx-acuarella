# Odoo Shopify Connector Hardening Modules

This repository contains 4 custom Odoo 18 modules designed to improve and enforce security, accuracy, and traceability over the VentorTech Odoo Shopify Connector PRO.

## Modules Included:
1. `integration_shopify_ssot`: Enforces Odoo as the Single Source of Truth (SSOT), blocking destructive webhooks and validating location mappings.
2. `integration_shopify_inventory_ssot`: Fixes overselling in Shopify by exporting only "Free to Use" stock (Total On Hand - Reserved/Outgoing).
3. `integration_shopify_reconciliation`: Implements a daily Cron Job to detect inventory drifts between Odoo and Shopify.
4. `integration_shopify_observability`: Implements Structured Logging with `correlation_id` injection for distributed tracing across `queue_job` and the connector.

## Technical Notes regarding Emipro's `common_connector_library`
The code in these addons correctly relies on standard Odoo functionality (`super()` overrides, context injection via `with_context`, and extending models correctly) so that it does not break Emipro's automatic workflow processing. We safely evaluate properties like `product.outgoing_qty` without overriding base data read/writes that could collide with Emipro's flow.

## Installation Instructions

1. Ensure that you have the base modules `integration` and `integration_shopify` (by VentorTech) installed in your Odoo 18 environment.
2. Ensure that you have the `queue_job` module installed.
3. Place these 4 module folders in your active Odoo `addons` path.
4. Restart your Odoo server.
5. In Odoo, activate **Developer Mode**.
6. Go to **Apps** -> **Update Apps List**.
7. Search for "Shopify" and install the following modules:
   - **Odoo Shopify SSOT Enforcement** (`integration_shopify_ssot`)
   - **Odoo Shopify Inventory SSOT** (`integration_shopify_inventory_ssot`)
   - **Odoo Shopify Reconciliation Engine** (`integration_shopify_reconciliation`)
   - **Odoo Shopify Observability** (`integration_shopify_observability`)

## Verification
- Navigate to the **E-Commerce Integrations** menu.
- Open your Shopify integration settings. You will now see an **"Enforce SSOT"** active toggle.
- A new Scheduled Action (Cron) named **"Shopify: Daily Reconciliation"** has been created.
- Check your Odoo server logs; `correlation_id` and other structured metadata are now injected into the connector output.
