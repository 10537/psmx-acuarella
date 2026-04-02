from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    assign_chute = fields.Boolean(
        string="Assign Sorter Chute",
        default=False,
        help="If enabled, a sorter chute will be assigned when a picking of this type is created.",
    )
