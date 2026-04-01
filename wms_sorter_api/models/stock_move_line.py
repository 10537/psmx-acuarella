from odoo import fields, models

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    sorter_state = fields.Selection(
        [
            ("draft", "En Cola"),
            ("picking", "Recogiendo"),
            ("collected", "Recogido"),
        ],
        string="Sorter State",
        default="draft",
        index=True,
        help="Progress of this item through the warehouse sorting machine.",
    )
