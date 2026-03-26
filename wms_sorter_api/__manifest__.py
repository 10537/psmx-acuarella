{
    "name": "WMS Sorter API",
    "version": "18.0.1.0.0",
    "category": "Inventory/WMS",
    "summary": "FastAPI integration for warehouse sorter equipment control",
    "description": """
        Provides a FastAPI interface to integrate Odoo 18 with warehouse
        sorting equipment. Exposes endpoints for wave sorting data, real-time
        order queries, and receives sorting status push notifications.
    """,
    "author": "JDC Luxury",
    "depends": ["base", "stock", "stock_picking_batch", "fastapi", "fastapi_auth_api_key"],
    "data": [
        "security/ir.model.access.csv",
        "data/fastapi_endpoints.xml",
        "views/sorter_log_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
