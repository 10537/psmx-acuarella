{
    'name': 'Coordinadora Delivery',
    'version': '18.0.1.0',
    'category': 'Operations/Inventory',
    'summary': 'Integration with Coordinadora shipping service',
    'description': """
        This module provides integration with Coordinadora shipping service for Odoo.
        It allows for rate calculation, guide generation, and tracking.
    """,
    'author': 'Psmx-Acuarella',
    'depends': ['delivery', 'mail'],
    'data': [
        'views/delivery_carrier_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
