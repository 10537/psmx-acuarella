{
    'name': 'Odoo Shopify Reconciliation Engine',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Daily reconciliation cron job to detect inventory desync/drift between Odoo and Shopify.',
    'depends': ['integration_shopify', 'integration_shopify_ssot'],
    'data': [
        'data/ir_cron.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
