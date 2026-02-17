from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    x_carrier_tracking_ref = fields.Char(string="Carrier Tracking Ref")
    x_carrier_partner_name = fields.Char(string="Carrier Partner Name")
    x_carrier_identity_document = fields.Char(string="Carrier Identity Document")
    x_carrier_delivery_address = fields.Char(string="Carrier Delivery Address")
    x_carrier_state = fields.Char(string="Carrier State")
