from odoo import fields, models


class ServientregaTracking(models.Model):
    _name = "servientrega.tracking"
    _description = "Eventos Servientrega"
    _order = "event_date"

    picking_id = fields.Many2one("stock.picking", required=True)
    event_code = fields.Char()
    event_description = fields.Char()
    event_date = fields.Datetime()
    location = fields.Char()
