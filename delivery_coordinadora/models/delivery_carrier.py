# -*- coding: utf-8 -*-

import hashlib
import logging
import base64

from odoo import models, fields, api
from odoo.exceptions import UserError
from zeep import xsd

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('coordinadora', 'Coordinadora')
    ], ondelete={'coordinadora': 'set default'})

    coordinadora_use_api = fields.Boolean(string="Use Coordinadora API", default=True)
    coordinadora_environment = fields.Selection([
        ('test', 'Test'),
        ('production', 'Production')
    ], string="Coordinadora Environment", default='test')

    coordinadora_client_id = fields.Char(string="Client ID (Acuerdo)")
    coordinadora_user = fields.Char(string="User")
    coordinadora_password = fields.Char(string="Password")
    coordinadora_apikey = fields.Char(string="API Key (Tracking)")
    coordinadora_tracking_password = fields.Char(string="Tracking Password")
    coordinadora_nit = fields.Char(string="NIT")
    coordinadora_div = fields.Char(string="Div", default="01")
    coordinadora_id_rotulo = fields.Char(string="ID Rótulo (Etiqueta)")

    coordinadora_ws_guias_test = fields.Char(
        string="WS Guias URL (Test)",
        default="https://sandbox.coordinadora.com/agw/ws/guias/1.6/server.php?wsdl",
    )
    coordinadora_ws_guias_prod = fields.Char(string="WS Guias URL (Prod)")
    coordinadora_ws_seguimiento_test = fields.Char(
        string="WS Seguimiento URL (Test)",
        default="https://ws.coordinadora.com/ags/1.5/server.php?wsdl",
    )
    coordinadora_ws_seguimiento_prod = fields.Char(string="WS Seguimiento URL (Prod)")

    # -------------------------------------------------------------------------
    # Security: SHA-256 hashing for stored passwords
    # -------------------------------------------------------------------------

    @staticmethod
    def _hash_password(value):
        """Return SHA-256 hex digest of *value* unless it looks already hashed."""
        if not value:
            return value
        # A SHA-256 hex digest is exactly 64 lowercase hex chars — skip re-hashing.
        if len(value) == 64 and all(c in '0123456789abcdef' for c in value):
            return value
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

    def write(self, vals):
        # Only coordinadora_password (guide WS) uses SHA-256.
        # coordinadora_tracking_password (cotizador) is sent as plaintext per API spec.
        if vals.get('coordinadora_password'):
            vals['coordinadora_password'] = self._hash_password(vals['coordinadora_password'])
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('coordinadora_password'):
                vals['coordinadora_password'] = self._hash_password(vals['coordinadora_password'])
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_coordinadora_client(self, ws_type='guias'):
        """Return a Zeep SOAP client for the requested WS type and environment."""
        self.ensure_one()
        try:
            from zeep import Client
        except ImportError:
            raise ImportError("Please install 'zeep' library to use Coordinadora integration.")

        if self.coordinadora_environment == 'test':
            wsdl = self.coordinadora_ws_guias_test if ws_type == 'guias' else self.coordinadora_ws_seguimiento_test
        else:
            wsdl = self.coordinadora_ws_guias_prod if ws_type == 'guias' else self.coordinadora_ws_seguimiento_prod

        if not wsdl:
            raise UserError(
                f"Configure la URL del WebService Coordinadora ({ws_type}) "
                f"para el entorno '{self.coordinadora_environment}'."
            )
        return Client(wsdl)

    def _normalize_city_code(self, city_code):
        """Normalise a city code to the 8-digit format required by Coordinadora."""
        if not city_code:
            return '11001000'
        city_code = str(city_code).strip()
        if len(city_code) == 8:
            return city_code
        if city_code.endswith('000'):
            return city_code.zfill(8)
        return f"{city_code.zfill(5)}000"

    @api.depends('delivery_type')
    def _compute_can_generate_return(self):
        super()._compute_can_generate_return()
        for carrier in self.filtered(lambda c: c.delivery_type == 'coordinadora'):
            carrier.can_generate_return = True

    @api.depends('delivery_type')
    def _compute_supports_shipping_insurance(self):
        super()._compute_supports_shipping_insurance()
        for carrier in self.filtered(lambda c: c.delivery_type == 'coordinadora'):
            carrier.supports_shipping_insurance = True

    # -------------------------------------------------------------------------
    # Rate shipment (Cotizador) — FIX SIFA
    # -------------------------------------------------------------------------

    def coordinadora_rate_shipment(self, order):
        """Compute the shipping rate via Coordinadora's Cotizador_cotizar endpoint.

        Critical JSON structure (confirmed against SIFA spec):
          - cuenta:         integer  (e.g. 2)
          - producto:       integer  (e.g. 0)
          - nivel_servicio: list of objects  [{"item": 1}]
          - detalle:        flat list of package objects
          - apikey / clave: sent in the request body
        """
        self.ensure_one()

        if not self.coordinadora_use_api:
            return {
                'success': False, 'price': 0.0,
                'error_message': 'Coordinadora API is disabled.', 'warning_message': False,
            }

        if not self.coordinadora_client_id or not self.coordinadora_nit:
            return {
                'success': False, 'price': 0.0,
                'error_message': 'Configure Client ID y NIT en la transportadora Coordinadora.',
                'warning_message': False,
            }

        try:
            client = self._get_coordinadora_client(ws_type='seguimiento')

            partner_shipping = order.partner_shipping_id
            origin_city = self._normalize_city_code(
                self.company_id.partner_id.city_id and self.company_id.partner_id.city_id.code or '11001000'
            )
            dest_city = self._normalize_city_code(
                partner_shipping.city_id and partner_shipping.city_id.code or '11001000'
            )

            # Dimensions: prefer values injected by the delivery wizard via context
            ctx = self.env.context
            alto = ctx.get('coordinadora_alto') or 50.0
            ancho = ctx.get('coordinadora_ancho') or 50.0
            largo = ctx.get('coordinadora_largo') or 50.0

            serviceable_lines = [
                l for l in order.order_line if l.product_id.type != 'service'
            ]
            if ctx.get('coordinadora_peso'):
                total_weight = float(ctx['coordinadora_peso'])
            else:
                total_weight = sum(
                    l.product_id.weight * l.product_uom_qty for l in serviceable_lines
                ) or 1.0

            total_units = len(serviceable_lines) or 1

            request_data = {
                'nit': self.coordinadora_nit,
                'div': self.coordinadora_div or '01',
                'cuenta': 2,                        # Integer — required by SIFA
                'producto': 0,                      # Integer — required by SIFA
                'origen': origin_city,
                'destino': dest_city,
                'valoracion': int(order.amount_total),
                'nivel_servicio': [1],
                'detalle': {'item': [{
                    'ubl': 0,
                    'alto': str(int(alto)),
                    'ancho': str(int(ancho)),
                    'largo': str(int(largo)),
                    'peso': str(int(total_weight)),
                    'unidades': str(int(total_units)),
                }]},
                'apikey': self.coordinadora_apikey,
                'clave': self.coordinadora_tracking_password,
            }

            _logger.info("Coordinadora Cotizador request: %s", request_data)

            response = client.service.Cotizador_cotizar(p=request_data)

            _logger.info("Coordinadora Cotizador response: %s", response)

            if hasattr(response, 'flete_total'):
                return {
                    'success': True,
                    'price': float(response.flete_total),
                    'carrier_price': float(response.flete_total),
                    'error_message': False,
                    'warning_message': False,
                }
            return {
                'success': False, 'price': 0.0,
                'error_message': str(response), 'warning_message': False,
            }
        except Exception as e:
            _logger.exception("Coordinadora rate_shipment error")
            return {
                'success': False, 'price': 0.0,
                'error_message': str(e), 'warning_message': False,
            }

    # -------------------------------------------------------------------------
    # Send shipping (guide generation is manual via button)
    # -------------------------------------------------------------------------

    def coordinadora_send_shipping(self, pickings):
        """Validation hook — guide is generated manually; return dummy result."""
        return [{'exact_price': 0.0, 'tracking_number': False} for _ in pickings]

    # -------------------------------------------------------------------------
    # Guide generation
    # -------------------------------------------------------------------------

    def _coordinadora_generate_guide(self, picking):
        """Generate a Coordinadora shipping guide and attach the label PDF to the picking."""
        self.ensure_one()

        if not self.coordinadora_use_api:
            raise UserError("Coordinadora API is disabled.")
        if not self.coordinadora_client_id:
            raise UserError("Configure el Client ID (Acuerdo) en la transportadora Coordinadora.")

        order = picking.sale_id
        if not order:
            raise UserError(
                "El picking debe estar relacionado a una Orden de Venta para generar la guía."
            )

        try:
            client = self._get_coordinadora_client(ws_type='guias')

            sender = order.company_id.partner_id
            receiver = order.partner_shipping_id

            sender_city = self._normalize_city_code(
                sender.city_id and sender.city_id.code or '11001000'
            )
            receiver_city = self._normalize_city_code(
                receiver.city_id and receiver.city_id.code or '11001000'
            )

            total_weight = sum(
                l.product_id.weight * l.product_uom_qty
                for l in order.order_line if l.product_id.type != 'service'
            ) or 1.0

            request_data = {
                'codigo_remision': '',
                'fecha': '',
                'id_cliente': int(self.coordinadora_client_id),
                'id_remitente': '',
                'nit_remitente': self.coordinadora_nit or '',
                'nombre_remitente': sender.name,
                'direccion_remitente': sender.street or '',
                'telefono_remitente': (sender.phone or sender.mobile or '0')[:10],
                'ciudad_remitente': sender_city,
                'nit_destinatario': receiver.vat or '0',
                'div_destinatario': '01',
                'nombre_destinatario': receiver.name,
                'direccion_destinatario': receiver.street or '',
                'ciudad_destinatario': receiver_city,
                'telefono_destinatario': (receiver.phone or receiver.mobile or '0')[:10],
                'valor_declarado': order.amount_total,
                'codigo_cuenta': 2,
                'codigo_producto': 0,
                'nivel_servicio': 1,
                'linea': '',
                'contenido': (order.client_order_ref or 'Mercancia')[:30],
                'referencia': order.name,
                'observaciones': '',
                'estado': 'IMPRESO',
                'detalle': [{
                    'ubl': 0,
                    'alto': 10,
                    'ancho': 10,
                    'largo': 10,
                    'peso': float(total_weight),
                    'unidades': 1,
                    'referencia': '',
                    'nombre_empaque': '',
                }],
                'cuenta_contable': '',
                'centro_costos': '',
                'recaudos': xsd.SkipValue,
                'margen_izquierdo': 0,
                'margen_superior': 0,
                'usuario_vmi': '',
                'formato_impresion': '',
                'atributo1_nombre': '',
                'atributo1_valor': '',
                'notificaciones': xsd.SkipValue,
                'atributos_retorno': {
                    'nit': '',
                    'div': '',
                    'nombre': 'pdf_guia',
                    'direccion': '',
                    'codigo_ciudad': '',
                    'telefono': '',
                },
                'nro_doc_radicados': '',
                'nro_sobre': '',
                'codigo_vendedor': 0,
                'usuario': self.coordinadora_user,
                'clave': self.coordinadora_password,
            }

            _logger.info("Coordinadora generate guide request: %s", request_data)

            response = client.service.Guias_generarGuia(p=request_data)

            _logger.info("Coordinadora generate guide response: %s", response)

            if not hasattr(response, 'codigo_remision'):
                raise UserError(f"Falló la generación de guía Coordinadora: {response}")

            tracking_number = response.codigo_remision
            picking.carrier_tracking_ref = tracking_number

            # Attach label PDF to the picking (Albarán) — spec item 4
            pdf_base64 = getattr(response, 'pdf_guia', False)
            if pdf_base64:
                # Ensure the value is a proper base64 string (decode/re-encode if needed)
                try:
                    base64.b64decode(pdf_base64, validate=True)
                    pdf_data = pdf_base64
                except Exception:
                    pdf_data = base64.b64encode(
                        pdf_base64 if isinstance(pdf_base64, bytes) else pdf_base64.encode()
                    ).decode()

                attachment = self.env['ir.attachment'].create({
                    'name': f'Etiqueta_Coordinadora_{tracking_number}.pdf',
                    'type': 'binary',
                    'datas': pdf_data,
                    'res_model': 'stock.picking',
                    'res_id': picking.id,
                    'mimetype': 'application/pdf',
                })
                picking.message_post(
                    body=f'Guía Coordinadora generada: {tracking_number}',
                    attachment_ids=[attachment.id],
                )
            else:
                picking.message_post(
                    body=f'Guía Coordinadora generada: {tracking_number} (sin PDF adjunto)',
                )

        except UserError:
            raise
        except Exception as e:
            _logger.exception("Coordinadora generate guide error")
            raise UserError(f"Error comunicando con Coordinadora API: {e}")

    # -------------------------------------------------------------------------
    # Label printing (rótulos)
    # -------------------------------------------------------------------------

    def _coordinadora_print_labels(self, picking):
        """Print Coordinadora shipping label (rótulo) via SOAP (zeep) and attach PDF to picking.

        The WS Guías endpoint is SOAP-only; calling it with JSON-RPC returns an empty
        response.  We use the same zeep client as guide generation.
        """
        self.ensure_one()

        if not picking.carrier_tracking_ref:
            raise UserError(
                "Este picking no tiene número de guía. Genere la guía primero."
            )
        if not self.coordinadora_id_rotulo:
            raise UserError(
                "Configure el ID Rótulo (Etiqueta) en la transportadora Coordinadora."
            )

        try:
            client = self._get_coordinadora_client(ws_type='guias')

            from lxml import etree
            item = etree.Element("item")
            item.text = picking.carrier_tracking_ref

            request_data = {
                'id_rotulo': int(self.coordinadora_id_rotulo),
                'codigos_remisiones': {'_value_1': [item]},
                'usuario': self.coordinadora_user,
                'clave': self.coordinadora_password,
            }

            _logger.info("Coordinadora imprimirRotulos SOAP request: %s", request_data)

            response = client.service.Guias_imprimirRotulos(p=request_data)

            _logger.info("Coordinadora imprimirRotulos SOAP response: %s", response)

        except UserError:
            raise
        except Exception as e:
            error_msg = str(e)
            _logger.exception("Coordinadora imprimirRotulos error")
            if "Could not connect to host" in error_msg:
                raise UserError(
                    "El servidor de pruebas (Sandbox) de Coordinadora falló internamente al generar el PDF "
                    "('Could not connect to host'). Esto es común en su ambiente de pruebas. "
                    "Por favor, intenta más tarde o realiza la prueba en Producción."
                )
            raise UserError(f"Error comunicando con Coordinadora API (rótulos): {e}")

        # Extract the base64 PDF — field name may vary by API version
        pdf_b64 = (
            getattr(response, 'pdf_rotulo', None)
            or getattr(response, 'rotulo', None)
            or getattr(response, 'pdf', None)
        )

        if not pdf_b64:
            raise UserError(
                f"No se recibió PDF de rótulo en la respuesta de Coordinadora: {response}"
            )

        tracking = picking.carrier_tracking_ref
        attachment = self.env['ir.attachment'].create({
            'name': f'Etiqueta_Coordinadora_{tracking}.pdf',
            'type': 'binary',
            'datas': pdf_b64,
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'mimetype': 'application/pdf',
        })

        picking.message_post(
            body=f'Rótulo Coordinadora generado para guía: {tracking}',
            attachment_ids=[attachment.id],
        )

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    # -------------------------------------------------------------------------
    # Tracking / cancel
    # -------------------------------------------------------------------------

    def coordinadora_get_tracking_link(self, picking):
        return (
            picking.sale_id.carrier_delivery_url
            or f"https://www.coordinadora.com/portafolio-de-servicios/servicios-en-linea/"
               f"rastrear-guias/?guia={picking.carrier_tracking_ref}"
        )

    def coordinadora_cancel_shipment(self, pickings):
        self.ensure_one()
        if not self.coordinadora_use_api:
            raise UserError("Coordinadora API is disabled.")
        try:
            client = self._get_coordinadora_client(ws_type='guias')
            for picking in pickings:
                if picking.carrier_tracking_ref:
                    client.service.Guias_anularGuia(p={
                        'codigo_remision': picking.carrier_tracking_ref,
                        'usuario': self.coordinadora_user,
                        'clave': self.coordinadora_password,
                    })
                    picking.carrier_tracking_ref = False
        except Exception as e:
            raise UserError(f"Error al cancelar con Coordinadora API: {e}")


# ---------------------------------------------------------------------------
# Stock Picking
# ---------------------------------------------------------------------------

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_coordinadora_delivery = fields.Boolean(
        string="Es entrega Coordinadora",
        compute='_compute_is_coordinadora_delivery',
        store=False,
    )

    @api.depends('carrier_id', 'carrier_id.delivery_type', 'picking_type_code')
    def _compute_is_coordinadora_delivery(self):
        for picking in self:
            picking.is_coordinadora_delivery = (
                picking.picking_type_code == 'outgoing'
                and picking.carrier_id
                and picking.carrier_id.delivery_type == 'coordinadora'
            )

    def action_generate_coordinadora_guide(self):
        self.ensure_one()
        if not self.carrier_id or self.carrier_id.delivery_type != 'coordinadora':
            raise UserError("Este picking no tiene una transportadora Coordinadora asignada.")
        self.carrier_id._coordinadora_generate_guide(self)

    def action_print_coordinadora_label(self):
        self.ensure_one()
        if not self.carrier_id or self.carrier_id.delivery_type != 'coordinadora':
            raise UserError("Este picking no tiene una transportadora Coordinadora asignada.")
        return self.carrier_id._coordinadora_print_labels(self)


# ---------------------------------------------------------------------------
# Sale Order
# ---------------------------------------------------------------------------

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    carrier_delivery_ref = fields.Char(string='Tracking Reference (Coordinadora)', copy=False)
    carrier_delivery_url = fields.Char(string='Tracking URL (Coordinadora)', copy=False)
