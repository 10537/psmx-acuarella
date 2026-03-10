# -*- coding: utf-8 -*-
{
    'name': "Envia Shipping Integration",

    'description': """
    This module integrates the Envia Shipping service with Odoo, allowing users to manage their shipments and deliveries directly from the Odoo platform.
    """,

    'author': "GRUPO AZULADO SAS",
    'website': "https://vivance.co",

    'category': 'Uncategorized',
    'version': '18.0.2.0',
    'license': 'OPL-1',
    'depends': ['base','sale','website_sale','delivery', 'l10n_co'],

    'data': [
        'security/ir.model.access.csv',
        'views/delivery.xml',
        'views/sale.xml',
        'data/delivery_data.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],
}
