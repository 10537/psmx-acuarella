import logging
import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPickingBatch(models.Model):
    """
    Endpoint 4 – Odoo as CLIENT: push wave/sorting data to equipment.

    When a batch is confirmed, call `action_push_sorting_data()` to send
    all its move lines to the sorter's /in_order endpoint.
    """

    _inherit = "stock.picking.batch"

    # ------------------------------------------------------------------ #
    # Public action (can be wired to a button or called from automation)  #
    # ------------------------------------------------------------------ #

    def action_push_sorting_data(self):
        """POST sorting data for this batch to the sorter equipment."""
        self.ensure_one()
        sorter_url = self.env["ir.config_parameter"].sudo().get_param(
            "wms_sorter_api.equipment_url", default=""
        )
        if not sorter_url:
            raise UserError(
                "Sorter equipment URL not configured. "
                "Set 'wms_sorter_api.equipment_url' in System Parameters."
            )

        endpoint = sorter_url.rstrip("/") + "/in_order"
        payload = self._build_sorting_payload()

        try:
            timeout = int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("wms_sorter_api.request_timeout", default="10")
            )
            resp = requests.post(endpoint, json=payload, timeout=timeout)
            resp.raise_for_status()
            result = resp.json()
            _logger.info(
                "Sorter equipment accepted batch %s: %s", self.name, result
            )
        except requests.exceptions.RequestException as exc:
            _logger.error(
                "Failed to push sorting data for batch %s to %s: %s",
                self.name,
                endpoint,
                exc,
            )
            raise UserError(
                f"Could not push sorting data to sorter equipment:\n{exc}"
            ) from exc

        return True

    # ------------------------------------------------------------------ #
    # Override confirm to auto-push (optional – can be disabled via param)#
    # ------------------------------------------------------------------ #

    def action_confirm(self):
        res = super().action_confirm()
        auto_push = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("wms_sorter_api.auto_push_on_confirm", default="False")
        )
        if auto_push.lower() in ("1", "true", "yes"):
            for batch in self:
                try:
                    batch.action_push_sorting_data()
                except UserError as exc:
                    _logger.warning(
                        "Auto-push skipped for batch %s: %s", batch.name, exc
                    )
        return res

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _build_sorting_payload(self) -> dict:
        """Build the JSON payload expected by the sorter equipment."""
        items = []
        for move_line in self.move_line_ids:
            product = move_line.product_id
            chute = (
                move_line.location_dest_id.complete_name
                if move_line.location_dest_id
                else ""
            )
            items.append(
                {
                    "order": product.default_code or "",
                    "sn": product.barcode or "",
                    "num": int(move_line.quantity or move_line.qty_done or 0),
                    "chute": chute,
                }
            )
        return {
            "wave_No": self.name,
            "data": items,
        }
