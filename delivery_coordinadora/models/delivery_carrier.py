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

    def coordinadora_get_shipping_price(self, order):
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

            if not self.coordinadora_client_id or not self.coordinadora_nit:
                return {'success': False, 'price': 0.0, 'error_message': 'Please configure Client ID and NIT in the carrier settings.', 'warning_message': False}

            request_data = {
                'nit': self.coordinadora_nit,
                'div': self.coordinadora_div or '01',
                'cuenta': int(self.coordinadora_client_id),
                'producto': 0,
                'origen': origin_city,
                'destino': dest_city,
                'valoracion': order.amount_total,
                'nivel_servicio': {'item': []},
                'detalle': {
                    'item': [{
                        'ubl': 0,
                        'alto': 10,
                        'ancho': 10,
                        'largo': 10,
                        'peso': float(total_weight),
                        'unidades': 1,
                    }]
                },
                'apikey': self.coordinadora_apikey,
                'clave': self.coordinadora_tracking_password
            }

            response = client.service.Cotizador_cotizar(p=request_data)
            
            if hasattr(response, 'flete_total'):
                return {
                    'success': True,
                    'price': float(response.flete_total),
                    'error_message': False,
                    'warning_message': False
                }
            return {'success': False, 'price': 0.0, 'error_message': str(response), 'warning_message': False}
        except Exception as e:
            return {'success': False, 'price': 0.0, 'error_message': str(e), 'warning_message': False}

    def coordinadora_send_shipping(self, pickings):
        """Implement shipping label generation for Coordinadora.
        Usando Guias_generarGuia (WebService Guías - AGW).
        """
        res = []
        for picking in pickings:
            self.ensure_one()
            if not self.coordinadora_use_api:
                raise UserError("Coordinadora API is disabled.")
            
            if not self.coordinadora_client_id:
                raise UserError("Please configure Client ID (Acuerdo) in the Coordinadora carrier settings.")

            order = picking.sale_id
            if not order:
                raise UserError("Picking must be related to a Sale Order to generate Coordinadora guide.")

            try:
                client = self._get_coordinadora_client(ws_type='guias')
                
                sender = order.company_id.partner_id
                receiver = order.partner_shipping_id
                
                sender_city = self._normalize_city_code(sender.city_id and sender.city_id.code or '11001000')
                receiver_city = self._normalize_city_code(receiver.city_id and receiver.city_id.code or '11001000')

                total_weight = sum([line.product_id.weight * line.product_uom_qty for line in order.order_line if line.product_id.type != 'service']) or 1.0

                request_data = {
                    'codigo_remision': '',
                    'fecha': '', # Vacío según el ejemplo
                    'id_cliente': int(self.coordinadora_client_id),
                    'id_remitente': 0,
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
                    'codigo_cuenta': 1,
                    'codigo_producto': 0,
                    'nivel_servicio': 1,
                    'linea': '',
                    'contenido': (order.client_order_ref or 'Mercancia')[:30],
                    'referencia': order.name,
                    'observaciones': (order.note or '')[:100],
                    'estado': 'IMPRESO',
                    'detalle': {
                        'item': [{
                            'ubl': 0,
                            'alto': 10,
                            'ancho': 10,
                            'largo': 10,
                            'peso': float(total_weight),
                            'unidades': 1,
                            'referencia': '',
                            'nombre_empaque': '',
                        }]
                    },
                    'cuenta_contable': '',
                    'centro_costos': '',
                    'recaudos': xsd.SkipValue,
                    'margen_izquierdo': 0,
                    'margen_superior': 0,
                    'id_rotulo': xsd.SkipValue,
                    'usuario_vmi': '',
                    'formato_impresion': '',
                    'atributo1_nombre': '',
                    'atributo1_valor': '',
                    'notificaciones': xsd.SkipValue,
                    'atributos_retorno': {
                        'item': [{'nombre': 'pdf_guia'}]
                    },
                    'nro_doc_radicados': '',
                    'nro_sobre': '',
                    'usuario': self.coordinadora_user,
                    'clave': self.coordinadora_password
                }

                response = client.service.Guias_generarGuia(p=request_data)
                
                if hasattr(response, 'codigo_remision'):
                    tracking_number = response.codigo_remision
                    tracking_url = f"https://www.coordinadora.com/portafolio-de-servicios/servicios-en-linea/rastrear-guias/?guia={tracking_number}"
                    
                    # Persistencia en SO (campos especificados)
                    order.write({
                        'carrier_delivery_ref': tracking_number,
                        'carrier_delivery_url': tracking_url
                    })

                    # Adjuntar PDF al chatter de SO
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
                        order.message_post(body=f"Guía Coordinadora generada: {tracking_number}", attachment_ids=[attachment.id])
                    
                    res.append({
                        'exact_price': self.coordinadora_get_shipping_price(order)['price'],
                        'tracking_number': tracking_number,
                    })
                else:
                    raise UserError(f"Falló la generación de etiqueta Coordinadora: {response}")
            except Exception as e:
                raise UserError(f"Error comunicando con Coordinadora API: {e}")
                
        return res

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

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for picking in self:
            if picking.sale_id and picking.sale_id.carrier_delivery_ref and picking.carrier_id and picking.carrier_id.delivery_type == 'coordinadora':
                if not picking.carrier_tracking_ref:
                    picking.carrier_tracking_ref = picking.sale_id.carrier_delivery_ref
        return res

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    carrier_delivery_ref = fields.Char(string='Tracking Reference (Coordinadora)', copy=False)
    carrier_delivery_url = fields.Char(string='Tracking URL (Coordinadora)', copy=False)
