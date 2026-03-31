import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_waiting_chute = fields.Boolean(
        string="Waiting for Chute",
        default=False,
        index=True,
        copy=False,
        help="If True, this picking is in queue awaiting an available machine chute.",
    )
    assigned_chute_id = fields.Many2one(
        "wms.sorter.chute",
        string="Assigned Chute",
        index=True,
        copy=False,
        help="The machine chute station assigned to this picking.",
        ondelete="set null",
    )

    def button_validate(self):
        """
        When validating a picking, attempt to assign it a chute.
        """
        res = super(StockPicking, self).button_validate()
        for picking in self:
            if picking.picking_type_code == "outgoing":
                picking._assign_sorter_chute()
        return res

    def _assign_sorter_chute(self):
        """
        Logic to assign the first available chute to this picking.
        If no chutes are free, marks as waiting.
        """
        self.ensure_one()
        if self.assigned_chute_id:
            return  # Already has one

        Chute = self.env["wms.sorter.chute"].sudo()
        
        # Auto-initialize if empty
        if not Chute.search_count([]):
            Chute.action_initialize_chutes()

        # Find first free chute
        free_chute = Chute.search(
            [("state", "=", "free")], order="name asc", limit=1
        )
        if free_chute:
            free_chute.write(
                {"state": "occupied", "current_picking_id": self.id}
            )
            self.sudo().write(
                {
                    "assigned_chute_id": free_chute.id,
                    "is_waiting_chute": False,
                }
            )
            self.message_post(
                body=_("Sorter Chute <b>%s</b> assigned.") % free_chute.name
            )
        else:
            self.sudo().write({"is_waiting_chute": True})
            self.message_post(
                body=_("No sorter chutes available. Picking added to queue.")
            )

    @api.model
    def _process_chute_queue(self):
        """
        Find the oldest waiting picking and assign it a newly freed chute.
        This should be called whenever a chute is released.
        """
        waiting_pickings = self.search(
            [("is_waiting_chute", "=", True)], order="id asc"
        )
        for picking in waiting_pickings:
            # Re-check if any chute became free since last iteration
            free_chute = self.env["wms.sorter.chute"].search(
                [("state", "=", "free")], order="name asc", limit=1
            )
            if free_chute:
                picking._assign_sorter_chute()
            else:
                break
