# Repository Structure — psmx-acuarella

## Root Layout

```
psmx-acuarella/
├── README.md                          # Overview of the Shopify hardening modules
├── requirements.txt                   # Python dependencies (ShopifyAPI==12.7.0)
│
├── acuarella_api/                     # FastAPI shipping webhook receiver
├── acuarella_stock_reports/           # Custom stock/batch picking reports
├── common_connector_library/          # [Third-party] Emipro shared connector library
├── delivery_coordinadora/             # Coordinadora carrier integration
├── integration/                       # [Third-party] VentorTech e-commerce core
├── integration_shopify/               # [Third-party] VentorTech Shopify connector
├── integration_shopify_customer_ssot/ # Custom: real-time customer sync to Shopify
├── integration_shopify_inventory_ssot/# Custom: Free to Use stock push to Shopify
├── integration_shopify_observability/ # Custom: structured logging & distributed tracing
├── integration_shopify_reconciliation/# Custom: daily inventory drift detection
├── integration_shopify_ssot/          # Custom: SSOT policy enforcement
├── oca-queue/                         # [Third-party] OCA Job Queue
│   ├── queue_job/
│   └── queue_job_subscribe/
├── shopify_ept/                       # [Third-party] Emipro Shopify connector
├── ventor_base/                       # [Third-party] VentorTech base for WMS modules
├── website_sale_melonn/               # Envía carrier + Melonn fulfillment integration
└── wms_sorter_api/                    # FastAPI warehouse sorting machine integration
```

---

## Custom Modules — Detailed Structure

### `acuarella_api/`
```
acuarella_api/
├── __init__.py
├── __manifest__.py                    # depends: stock, fastapi, fastapi_auth_api_key
├── dependencies.py                    # get_current_user: Bearer token → auth.api.key
├── data/
│   └── fastapi_endpoints.xml          # registers the FastAPI endpoint record in Odoo
├── models/
│   ├── __init__.py
│   ├── fastapi_endpoint.py            # inherits fastapi.endpoint, registers the router
│   └── stock_picking.py               # adds x_carrier_* custom fields to stock.picking
├── routers/
│   ├── __init__.py
│   └── shipping_router.py             # POST /update_info, POST /update_status
├── schemas/
│   ├── __init__.py
│   └── shipping_schema.py             # Pydantic: ShippingUpdateSchema, StatusUpdateSchema
├── security/
│   └── ir.model.access.csv
├── tests/
│   ├── __init__.py
│   └── test_shipping_api.py
└── views/
    └── stock_picking_view.xml         # adds x_carrier_* fields to picking form
```

### `acuarella_stock_reports/`
```
acuarella_stock_reports/
├── __init__.py
├── __manifest__.py                    # depends: sale_stock, stock_picking_batch, stock_delivery
├── README.rst
├── data/
│   ├── acuarella_stock_reports_demo.xml
│   └── stock_picking_batch_reports.xml # registers the batch picking report action
├── i18n/
│   └── es_CO.po                       # Spanish (Colombia) translations
├── models/
│   ├── __init__.py
│   ├── res_partner.py
│   ├── sale_order.py                  # adds logistic_route selection field (18 options)
│   ├── stock_picking.py               # adds sale_logistic_route to picking
│   └── stock_picking_batch.py         # computed sale_logistic_routes + supervisor field
├── reports/
│   ├── external_layouts.xml           # custom report layout/branding
│   └── report_picking_batch_acuarella.xml # main QWeb batch picking report template
├── static/src/scss/
│   └── acuarella_reports.scss         # report PDF styling
└── views/
    ├── sale_order_views.xml
    ├── stock_picking_batch_views.xml
    └── stock_picking_views.xml
```

### `delivery_coordinadora/`
```
delivery_coordinadora/
├── __init__.py
├── __manifest__.py                    # depends: delivery, stock_delivery, mail
├── models/
│   ├── __init__.py
│   └── delivery_carrier.py            # DeliveryCarrier: coordinadora delivery_type, SOAP/REST methods
│                                      # StockPicking: action_generate_coordinadora_guide button
│                                      # SaleOrder: carrier_delivery_ref, carrier_delivery_url
└── views/
    └── delivery_carrier_views.xml     # Coordinadora config fields in carrier form
```

### `integration_shopify_ssot/`
```
integration_shopify_ssot/
├── __init__.py
├── __manifest__.py                    # depends: integration_shopify
├── models/
│   ├── __init__.py
│   └── sale_integration.py            # enforce_ssot field + 2 @api.constrains methods
└── views/
    └── sale_integration_views.xml     # exposes enforce_ssot toggle in UI
```

### `integration_shopify_inventory_ssot/`
```
integration_shopify_inventory_ssot/
├── __init__.py
├── __manifest__.py                    # depends: integration_shopify, integration_shopify_ssot,
│                                      #          integration_shopify_observability
└── models/
    ├── __init__.py
    └── sale_integration.py            # overrides _prepare_inventory_data:
                                       # Free to Use = max(0, qty_available - outgoing_qty)
                                       # + pg_advisory_xact_lock for concurrency
```

### `integration_shopify_reconciliation/`
```
integration_shopify_reconciliation/
├── __init__.py
├── __manifest__.py                    # depends: integration_shopify, integration_shopify_ssot
├── data/
│   └── ir_cron.xml                    # daily cron: _cron_reconcile_shopify
└── models/
    ├── __init__.py
    └── sale_integration.py            # reconciliation_email_list, reconciliation_admin_id fields
                                       # _cron_reconcile_shopify, _notify_discrepancies
```

### `integration_shopify_observability/`
```
integration_shopify_observability/
├── __init__.py
├── __manifest__.py                    # depends: integration_shopify, queue_job,
│                                      #          integration_shopify_reconciliation
├── logging.conf.example
├── models/
│   ├── __init__.py
│   ├── queue_job.py                   # monkey-patches Job.perform for correlation_id injection
│   └── sale_integration.py            # overrides _cron_reconcile_shopify (sets root correlation_id)
└── tools/
    ├── __init__.py
    └── logging_helper.py              # StructuredLogger class + correlation_id_var ContextVar
```

### `integration_shopify_customer_ssot/`
```
integration_shopify_customer_ssot/
├── __init__.py
├── __manifest__.py                    # depends: integration_shopify, integration_shopify_ssot,
│                                      #          integration_shopify_observability
└── models/
    ├── __init__.py
    ├── res_partner.py                 # create/write/unlink hooks → _enqueue_shopify_sync
    └── sale_integration.py            # sync_shopify_customer (GraphQL upsert/create/update)
                                       # delete_shopify_customer (GraphQL delete)
```

### `website_sale_melonn/`
```
website_sale_melonn/
├── __init__.py
├── __manifest__.py                    # depends: base, sale, website_sale, delivery, l10n_co
├── code_dane-R1.sql                   # SQL: seed DANE city codes (revision 1)
├── code_dane-R2.sql                   # SQL: seed DANE city codes (revision 2)
├── get_estados.sql                    # SQL utility: query Colombian states
├── test_odoo.py                       # standalone debug stub (no real tests)
├── controllers/
│   ├── __init__.py
│   └── controllers.py                 # website_sale checkout extensions
├── data/
│   └── delivery_data.xml              # default carrier records
├── models/
│   ├── __init__.py
│   ├── delivery.py                    # WizardDeliveryEnvia transient model (guide wizard)
│   ├── res_city.py                    # adds 'code' (DANE code) field to res.city
│   └── sale_order.py                  # melonn_order, guia_envia_url; action_generar_guia
├── security/
│   └── ir.model.access.csv
└── views/
    ├── delivery.xml
    ├── sale.xml
    └── templates.xml                  # website checkout template overrides
```

### `wms_sorter_api/`
```
wms_sorter_api/
├── __init__.py
├── __manifest__.py                    # depends: base, stock, stock_picking_batch,
│                                      #          fastapi, fastapi_auth_api_key
├── dependencies.py                    # same Bearer token auth as acuarella_api
├── schemas.py                         # Pydantic schemas for all sorter request/response types
├── data/
│   ├── fastapi_endpoints.xml
│   └── ir_cron.xml                    # log cleanup cron
├── models/
│   ├── __init__.py
│   ├── fastapi_endpoint.py            # inherits fastapi.endpoint, registers sorter router
│   ├── sorter_api_log.py              # wms.sorter.api.log (HTTP request/response log)
│   ├── sorter_chute.py                # wms.sorter.chute (48 output chutes)
│   ├── sorter_log.py                  # wms.sorter.log (event audit log)
│   ├── stock_move_line.py             # adds sorter_state (draft/picking/collected)
│   ├── stock_picking.py               # assigned_chute_id field
│   ├── stock_picking_batch.py         # action_push_sorting_data (Odoo → sorter)
│   └── stock_picking_type.py          # optional sorter config on operation type
├── routers/
│   ├── __init__.py
│   └── sorting.py                     # all sorter endpoints + SorterApiLoggedRoute
├── security/
│   └── ir.model.access.csv
├── tests/
│   ├── __init__.py
│   └── test_wave_end.py
└── views/
    ├── sorter_api_log_views.xml
    ├── sorter_chute_views.xml
    ├── sorter_log_views.xml
    ├── stock_move_line_views.xml
    ├── stock_picking_batch_views.xml
    ├── stock_picking_type_views.xml
    └── stock_picking_views.xml
```

---

## Standard Odoo Module Layout

```
<module_name>/
├── __manifest__.py          # Module metadata: name, version, depends, data files, assets
├── __init__.py              # Python package init
├── models/                  # ORM model definitions (_inherit or new _name)
├── views/                   # XML view definitions (forms, lists, menus, actions)
├── data/                    # Records loaded on install (crons, config params)
├── security/
│   └── ir.model.access.csv  # Model-level access rules
├── reports/                 # QWeb PDF report templates
├── static/src/              # Frontend assets (JS, SCSS, OWL templates)
└── tests/                   # Odoo test cases (TransactionCase)
```

---

## Key File Reference

| File | Purpose |
|------|---------|
| `acuarella_api/dependencies.py` | Shared Bearer auth dependency |
| `acuarella_api/routers/shipping_router.py` | Shipping update REST endpoints |
| `acuarella_api/schemas/shipping_schema.py` | Pydantic models for shipping API |
| `acuarella_stock_reports/models/sale_order.py` | 18-option logistic route field |
| `delivery_coordinadora/models/delivery_carrier.py` | Full Coordinadora SOAP/REST integration |
| `integration_shopify_ssot/models/sale_integration.py` | SSOT constraint validation |
| `integration_shopify_inventory_ssot/models/sale_integration.py` | Free to Use stock + advisory lock |
| `integration_shopify_reconciliation/models/sale_integration.py` | Daily reconciliation cron |
| `integration_shopify_observability/tools/logging_helper.py` | StructuredLogger + correlation_id_var |
| `integration_shopify_observability/models/queue_job.py` | queue_job monkey-patch for tracing |
| `integration_shopify_customer_ssot/models/res_partner.py` | ORM hooks for async customer sync |
| `integration_shopify_customer_ssot/models/sale_integration.py` | Shopify GraphQL customer upsert/delete |
| `website_sale_melonn/models/sale_order.py` | Envía guide + Melonn order dispatch |
| `website_sale_melonn/models/delivery.py` | Envía guide wizard + carrier config |
| `wms_sorter_api/routers/sorting.py` | All sorter endpoints + HTTP logging |
| `wms_sorter_api/schemas.py` | Pydantic models for sorter API |
| `wms_sorter_api/models/sorter_chute.py` | Chute state tracker |
| `wms_sorter_api/models/stock_picking_batch.py` | Outbound push to sorter |
| `wms_sorter_api/models/stock_move_line.py` | sorter_state field |
