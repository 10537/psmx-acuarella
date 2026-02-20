{
    'name': 'Odoo Shopify SSOT Enforcement',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Enforces Odoo as the Single Source of Truth for Shopify integrations.',
    'depends': ['integration_shopify'],
    'data': [
        'views/sale_integration_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
