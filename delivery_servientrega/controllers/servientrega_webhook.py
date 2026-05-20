from odoo import http
from odoo.http import request
import hashlib
import logging

_logger = logging.getLogger(__name__)


class ServientregaWebhookController(http.Controller):

    @http.route("/servientrega/tracking", type="json", auth="public", csrf=False)
    def servientrega_tracking(self, **kwargs):
        payload = request.jsonrequest or {}
        raw_body = request.httprequest.data or b""

        guia = payload.get("guia")
        eventos = payload.get("eventos", [])

        signature = request.httprequest.headers.get("X-Servi-Signature")
        if not signature:
            _logger.error("Webhook Servientrega sin firma")
            return {"status": "error", "msg": "Missing signature"}

        carrier = request.env["delivery.carrier"].sudo().search(
            [("delivery_type", "=", "servientrega")], limit=1
        )
        if not carrier or not carrier.servientrega_webhook_secret:
            _logger.error("Carrier Servientrega sin secreto configurado")
            return {"status": "error", "msg": "No secret configured"}

        secret = carrier.servientrega_webhook_secret or ""
        expected = hashlib.sha256((secret + raw_body.decode("utf-8")).encode("utf-8")).hexdigest()

        if signature != expected:
            _logger.error("Firma inválida Servientrega: %s", signature)
            return {"status": "error", "msg": "Invalid signature"}

        picking = request.env["stock.picking"].sudo().search(
            [("servientrega_guide_number", "=", guia)], limit=1
        )
        if not picking:
            _logger.error("Guía no encontrada en Odoo: %s", guia)
            return {"status": "error", "msg": "Guide not found"}

        for ev in eventos:
            request.env["servientrega.tracking"].sudo().create({
                "picking_id": picking.id,
                "event_code": ev.get("codigo"),
                "event_description": ev.get("descripcion"),
                "event_date": ev.get("fecha"),
                "location": ev.get("lugar"),
            })
            picking.message_post(body=f"Evento Servientrega: {ev.get('descripcion')}")

        ultimo = eventos[-1].get("codigo", "").upper() if eventos else ""
        if ultimo in ("ENT", "ENTREGADO"):
            picking.sudo().write({"state": "done"})
        elif ultimo in ("DEV", "DEVUELTO"):
            picking.sudo().write({"state": "cancel"})

        return {"status": "ok"}
