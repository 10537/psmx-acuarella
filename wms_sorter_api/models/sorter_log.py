import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

SORTER_LOG_STATES = [
    ("info", "Info"),
    ("warning", "Warning"),
    ("error", "Error"),
]


class WmsSorterLog(models.Model):
    """
    Audit log for all interactions with the sorter equipment:
    - Incoming status pushes (Endpoint 5)
    - Outgoing data pushes (Endpoint 4)
    - Errors / jams reported by equipment
    """

    _name = "wms.sorter.log"
    _description = "WMS Sorter Event Log"
    _order = "create_date desc"
    _rec_name = "wave_no"

    # ------------------------------------------------------------------ #
    # Fields                                                               #
    # ------------------------------------------------------------------ #

    wave_no = fields.Char(string="Wave / Batch No", index=True)
    sku = fields.Char(string="Order / Sales Order")
    barcode = fields.Char(string="Barcode (sn)")
    quantity = fields.Integer(string="Quantity (num)")
    chute = fields.Char(string="Chute")
    status = fields.Char(string="Status")
    direction = fields.Selection(
        [("in", "Inbound (Equipment → Odoo)"), ("out", "Outbound (Odoo → Equipment)")],
        string="Direction",
        default="in",
    )
    level = fields.Selection(
        SORTER_LOG_STATES,
        string="Level",
        default="info",
    )
    note = fields.Text(string="Notes / Detail")

    # Related picking batch (optional, set when identifiable)
    batch_id = fields.Many2one(
        "stock.picking.batch",
        string="Picking Batch",
        ondelete="set null",
    )

    # ------------------------------------------------------------------ #
    # Convenience constructor                                              #
    # ------------------------------------------------------------------ #

    @api.model
    def log_event(
        self,
        *,
        wave_no: str = "",
        sku: str = "",
        barcode: str = "",
        quantity: int = 0,
        chute: str = "",
        status: str = "",
        direction: str = "in",
        level: str = "info",
        note: str = "",
        batch_id: int | None = None,
    ):
        vals = {
            "wave_no": wave_no,
            "sku": sku,
            "barcode": barcode,
            "quantity": quantity,
            "chute": chute,
            "status": status,
            "direction": direction,
            "level": level,
            "note": note,
        }
        if batch_id:
            vals["batch_id"] = batch_id
        return self.create(vals)
