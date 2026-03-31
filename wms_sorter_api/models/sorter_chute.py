import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class WmsSorterChute(models.Model):
    """
    Model to track the 48 output 'chutes' of the sorting machine.
    """

    _name = "wms.sorter.chute"
    _description = "WMS Sorter Chute"
    _order = "name asc"

    name = fields.Char(string="Chute ID", required=True, index=True)
    state = fields.Selection(
        [("free", "Free"), ("occupied", "Occupied")],
        string="State",
        default="free",
        required=True,
    )
    current_picking_id = fields.Many2one(
        "stock.picking",
        string="Current Picking",
        help="The picking currently assigned to this chute.",
        ondelete="set null",
    )

    _sql_constraints = [
        ("name_unique", "unique(name)", "Chute name must be unique!"),
    ]

    @api.model
    def action_initialize_chutes(self):
        """
        Create the initial set of chutes if they don't exist.
        The number of chutes is defined by 'wms_sorter_api.total_chutes'.
        """
        total_chutes_str = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("wms_sorter_api.total_chutes", default="48")
        )
        try:
            total_chutes = int(total_chutes_str)
        except ValueError:
            total_chutes = 48

        existing_count = self.search_count([])
        if existing_count >= total_chutes:
            _logger.info("Chutes already initialized.")
            return

        for i in range(1, total_chutes + 1):
            chute_name = f"C{i:02d}"
            if not self.search([("name", "=", chute_name)], limit=1):
                self.create({"name": chute_name, "state": "free"})
        
        _logger.info("Initialized %d chutes.", total_chutes)
