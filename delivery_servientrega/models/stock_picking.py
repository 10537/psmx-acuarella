from odoo import fields, models
import base64


class StockPicking(models.Model):
    _inherit = "stock.picking"

    servientrega_guide_number = fields.Char(readonly=True)
    servientrega_label_pdf = fields.Binary(readonly=True, attachment=True)
    servientrega_label_filename = fields.Char()
    servientrega_recaudo = fields.Float()
    servientrega_tracking_ids = fields.One2many(
        "servientrega.tracking",
        "picking_id",
        string="Eventos Servientrega"
    )
    servientrega_enabled = fields.Boolean(
        compute="_compute_servientrega_enabled",
        store=False
    )

    def _compute_servientrega_enabled(self):
        for picking in self:
            carrier = picking.carrier_id or (picking.sale_id and picking.sale_id.carrier_id)
            picking.servientrega_enabled = bool(carrier and carrier.delivery_type == "servientrega")

    def action_servientrega_generate_guide(self):
        for picking in self:
            if picking.carrier_id and picking.carrier_id.delivery_type == "servientrega":
                picking.carrier_id.servientrega_send_shipping(picking)
        return True

    def action_servientrega_print_label(self):
        self.ensure_one()
        if not self.carrier_id or self.carrier_id.delivery_type != "servientrega":
            return False
        self.carrier_id.servientrega_get_label(self)
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/stock.picking/{self.id}/servientrega_label_pdf/{self.servientrega_label_filename}?download=true",
            "target": "self",
        }
