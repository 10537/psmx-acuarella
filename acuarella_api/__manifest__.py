{
    "name": "Acuarella API",
    "version": "18.0.1.0.0",
    "category": "Inventory/API",
    "summary": "FastAPI integration for shipping updates",
    "depends": ["stock", "fastapi", "fastapi_auth_api_key"],
    "data": [
        "data/fastapi_endpoints.xml",
        "security/ir.model.access.csv",
        "views/stock_picking_view.xml",

    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
