# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from zeep import xsd
import logging

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

    coordinadora_ws_guias_test = fields.Char(string="WS Guias URL (Test)", default="https://sandbox.coordinadora.com/agw/ws/guias/1.6/server.php?wsdl")
    coordinadora_ws_guias_prod = fields.Char(string="WS Guias URL (Prod)")
    coordinadora_ws_seguimiento_test = fields.Char(string="WS Seguimiento URL (Test)", default="https://sandbox.coordinadora.com/ags/1.5/server.php?wsdl")
    coordinadora_ws_seguimiento_prod = fields.Char(string="WS Seguimiento URL (Prod)")

    def _get_coordinadora_client(self, ws_type='guias'):
        """Helper method to get Zeep client for Coordinadora based on environment and requested WS type."""
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
            raise UserError(f"Please configure the Coordinadora {ws_type} WebService URL for {self.coordinadora_environment} environment.")
        
        return Client(wsdl)

    def _normalize_city_code(self, city_code):
        if not city_code:
            return '11001000'
        city_code = str(city_code).strip()
        
        # Coordinadora city code must be 8 digits
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

    def coordinadora_rate_shipment(self, order):
        """Implement pricing calculation for Coordinadora correctly.
        Usando Cotizador_cotizar (WebService Seguimiento - AGS).
        """
        self.ensure_one()
        
        if not self.coordinadora_use_api:
            return {'success': False, 'price': 0.0, 'error_message': 'Coordinadora API is disabled.', 'warning_message': False}
            
        try:
            client = self._get_coordinadora_client(ws_type='seguimiento')
            
            partner_shipping = order.partner_shipping_id
            origin_city = self._normalize_city_code(self.company_id.partner_id.city_id.code or '11001000')
            dest_city = self._normalize_city_code(partner_shipping.city_id and partner_shipping.city_id.code or '11001000')
            
            total_weight = sum([line.product_id.weight * line.product_uom_qty for line in order.order_line if line.product_id.type != 'service']) or 1.0
            total_product = len([line.product_id.default_code for line in order.order_line if line.product_id.type != 'service'])

            if not self.coordinadora_client_id or not self.coordinadora_nit:
                return {'success': False, 'price': 0.0, 'error_message': 'Please configure Client ID and NIT in the carrier settings.', 'warning_message': False}

            request_data = {
                'nit': self.coordinadora_nit,
                'div': self.coordinadora_div or '01',
                'cuenta': "02",
                'producto': "0",
                'origen': origin_city,
                'destino': dest_city,
                'valoracion': int(order.amount_total),
                'nivel_servicio': xsd.SkipValue,
                'detalle': {
                    'item': [{
                        'ubl': 1,
                        'alto': 10,
                        'ancho': 10,
                        'largo': 10,
                        'peso': float(total_weight),
                        'unidades': int(total_product),
                    }]
                },
                'apikey': self.coordinadora_apikey,
                'clave': self.coordinadora_tracking_password
            }

            _logger.info(f"Request data: {request_data}")
            _logger.info(f"Client: {client.wsdl.location}")
            _logger.info(f"Client Active Service: {client.service._binding_options['address']}")

            response = client.service.Cotizador_cotizar(p=request_data)
            
            if hasattr(response, 'flete_total'):
                return {
                    'success': True,
                    'price': float(response.flete_total),
                    'carrier_price': float(response.flete_total),
                    'error_message': False,
                    'warning_message': False
                }
            return {'success': False, 'price': 0.0, 'error_message': str(response), 'warning_message': False}
        except Exception as e:
            return {'success': False, 'price': 0.0, 'error_message': str(e), 'warning_message': False}

    def coordinadora_send_shipping(self, pickings):
        """Called automatically on picking validation. For Coordinadora the guide
        is generated manually via the 'Generar Guía' button, so we return a
        dummy result here to allow validation to proceed without errors.
        """
        return [{'exact_price': 0.0, 'tracking_number': False} for _ in pickings]

    def _coordinadora_generate_guide(self, picking):
        """Generate the Coordinadora shipping guide for a single picking.
        Called from the manual button on the delivery picking form.
        """
        self.ensure_one()
        if not self.coordinadora_use_api:
            raise UserError("Coordinadora API is disabled.")

        if not self.coordinadora_client_id:
            raise UserError("Please configure Client ID (Acuerdo) in the Coordinadora carrier settings.")

        order = picking.sale_id
        if not order:
            raise UserError("El picking debe estar relacionado a una Orden de Venta para generar la guía de Coordinadora.")

        try:
            client = self._get_coordinadora_client(ws_type='guias')

            sender = order.company_id.partner_id
            receiver = order.partner_shipping_id

            sender_city = self._normalize_city_code(sender.city_id and sender.city_id.code or '11001000')
            receiver_city = self._normalize_city_code(receiver.city_id and receiver.city_id.code or '11001000')

            total_weight = sum([line.product_id.weight * line.product_uom_qty for line in order.order_line if line.product_id.type != 'service']) or 1.0

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
                'observaciones': "https://test.jdchouse.com/terms",
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
                'clave': self.coordinadora_password
            }

            _logger.info(f"Coordinadora generate guide request: {request_data}")

            response = client.service.Guias_generarGuia(p=request_data)

            _logger.info(f"Coordinadora generate guide response: {response}")

            if hasattr(response, 'codigo_remision'):
                tracking_number = response.codigo_remision
                tracking_url = f"https://www.coordinadora.com/portafolio-de-servicios/servicios-en-linea/rastrear-guias/?guia={tracking_number}"

                order.write({
                    'carrier_delivery_ref': tracking_number,
                    'carrier_delivery_url': tracking_url,
                })
                picking.carrier_tracking_ref = tracking_number

                pdf_base64 = getattr(response, 'pdf_guia', False)
                if pdf_base64:
                    attachment = self.env['ir.attachment'].create({
                        'name': f"Guia_Coordinadora_{tracking_number}.pdf",
                        'type': 'binary',
                        'datas': pdf_base64,
                        'res_model': 'sale.order',
                        'res_id': order.id,
                        'mimetype': 'application/pdf',
                    })
                    order.message_post(
                        body=f"Guía Coordinadora generada: {tracking_number}",
                        attachment_ids=[attachment.id],
                    )
            else:
                raise UserError(f"Falló la generación de guía Coordinadora: {response}")
        except UserError:
            raise
        except Exception as e:
            raise UserError(f"Error comunicando con Coordinadora API: {e}")

    def _coordinadora_print_labels(self, picking):
        """Print Coordinadora shipping labels (rótulos) for a picking.
        Uses Guias.imprimirRotulos via JSON-RPC over HTTP.
        """
        self.ensure_one()
        import requests, base64, json

        if not picking.carrier_tracking_ref:
            raise UserError("Este picking no tiene un número de guía asignado. Genere la guía primero.")

        if not self.coordinadora_id_rotulo:
            raise UserError("Configure el ID Rótulo (Etiqueta) en la transportadora Coordinadora.")

        if self.coordinadora_environment == 'test':
            url = (self.coordinadora_ws_guias_test or '').replace('?wsdl', '')
        else:
            url = self.coordinadora_ws_guias_prod or ''

        if not url:
            raise UserError("Configure la URL del WS Guías para el entorno actual.")

        payload = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "Guias.imprimirRotulos",
            "params": {
                "id_rotulo": self.coordinadora_id_rotulo,
                "codigos_remisiones": [picking.carrier_tracking_ref],
                "usuario": self.coordinadora_user,
                "clave": self.coordinadora_password,
            }
        }

        _logger.info(f"Coordinadora imprimirRotulos request to {url}: {payload}")

        try:
            response = requests.post(
                url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(payload),
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            raise UserError(f"Error comunicando con Coordinadora API (rótulos): {e}")

        _logger.info(f"Coordinadora imprimirRotulos response: {result}")

        # The API returns the PDF in base64 inside result['result'] or directly
        pdf_b64 = None
        if isinstance(result, dict):
            res_data = result.get('result') or result.get('pdf') or result.get('rotulo')
            if isinstance(res_data, str):
                pdf_b64 = res_data
            elif isinstance(res_data, dict):
                pdf_b64 = res_data.get('pdf') or res_data.get('rotulo') or res_data.get('pdf_rotulo')

        if not pdf_b64:
            raise UserError(f"No se recibió PDF de rótulo en la respuesta: {result}")

        tracking = picking.carrier_tracking_ref
        attachment = self.env['ir.attachment'].create({
            'name': f"Rotulo_Coordinadora_{tracking}.pdf",
            'type': 'binary',
            'datas': pdf_b64,
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'mimetype': 'application/pdf',
        })

        order = picking.sale_id
        if order:
            order.message_post(
                body=f"Rótulo Coordinadora generado para guía: {tracking}",
                attachment_ids=[attachment.id],
            )

        picking.message_post(
            body=f"Rótulo Coordinadora generado para guía: {tracking}",
            attachment_ids=[attachment.id],
        )

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def coordinadora_get_tracking_link(self, picking):
        """Implement tracking link for Coordinadora."""
        return picking.sale_id.carrier_delivery_url or f"https://www.coordinadora.com/portafolio-de-servicios/servicios-en-linea/rastrear-guias/?guia={picking.carrier_tracking_ref}"

    def coordinadora_cancel_shipment(self, pickings):
        """Implement cancellation for Coordinadora."""
        self.ensure_one()
        if not self.coordinadora_use_api:
            raise UserError("Coordinadora API is disabled.")
        try:
            client = self._get_coordinadora_client(ws_type='guias')
            for picking in pickings:
                if picking.carrier_tracking_ref:
                    request_data = {
                        'codigo_remision': picking.carrier_tracking_ref,
                        'usuario': self.coordinadora_user,
                        'clave': self.coordinadora_password
                    }
                    client.service.Guias_anularGuia(p=request_data)
                    picking.carrier_tracking_ref = False
        except Exception as e:
            raise UserError(f"Error cancelling with Coordinadora API: {e}")

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_generate_coordinadora_guide(self):
        """Button action: generate Coordinadora guide for this delivery picking."""
        self.ensure_one()
        if not self.carrier_id or self.carrier_id.delivery_type != 'coordinadora':
            raise UserError("Este picking no tiene una transportadora Coordinadora asignada.")
        self.carrier_id._coordinadora_generate_guide(self)

    def action_print_coordinadora_label(self):
        """Button action: print Coordinadora shipping label (rótulo) for this delivery picking."""
        self.ensure_one()
        if not self.carrier_id or self.carrier_id.delivery_type != 'coordinadora':
            raise UserError("Este picking no tiene una transportadora Coordinadora asignada.")
        return self.carrier_id._coordinadora_print_labels(self)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    carrier_delivery_ref = fields.Char(string='Tracking Reference (Coordinadora)', copy=False)
    carrier_delivery_url = fields.Char(string='Tracking URL (Coordinadora)', copy=False)
