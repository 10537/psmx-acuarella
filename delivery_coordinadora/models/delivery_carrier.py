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

    def coordinadora_rate_shipment(self, order):
        """Implement pricing calculation for Coordinadora."""
        self.ensure_one()
        
        if not self.coordinadora_use_api:
            return {'success': False, 'price': 0.0, 'error_message': 'Coordinadora API is disabled.', 'warning_message': False}
            
        try:
            client = self._get_coordinadora_client(ws_type='guias')
            
            # Extract required info from order
            partner_shipping = order.partner_shipping_id
            city = self._normalize_city_code(partner_shipping.city_id and partner_shipping.city_id.code or '11001000')
            
            # Simple sum of weights & volume (or standard box size if none)
            total_weight = sum([line.product_id.weight * line.product_uom_qty for line in order.order_line if line.product_id.type != 'service']) or 1.0

            request_data = {
                'detalle': [{
                    'ubl': 0,
                    'alto': 10,
                    'ancho': 10,
                    'largo': 10,
                    'peso': float(total_weight),
                    'unidades': 1,
                    'referencia': order.name,
                    'nombre_empaque': '',
                }],
                'nivel_servicio': 1,
                'recaudos': xsd.SkipValue,
                'cnit': self.coordinadora_nit,
                'cdiv': self.coordinadora_div,
                'rcodigo_cm_ciudad': self._normalize_city_code(self.company_id.partner_id.city_id.code or '11001000'),
                'dcodigo_cm_ciudad': city,
                'codigo_cuenta': 1,
                'valor_declarado': order.amount_total,
                'liquidacion_enguia': '',
                'liquidacion_endespacho': xsd.SkipValue,
                'codigo_producto': 0,
                'token': xsd.SkipValue
            }

            response = client.service.Sifa_liquidarSifa(p=request_data)
            
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
        """
        res = []
        for picking in pickings:
            self.ensure_one()
            
            if not self.coordinadora_use_api:
                raise UserError("Coordinadora API is disabled but send_shipping was called.")

            # If order already has tracking, we just return it
            tracking_number = picking.sale_id.carrier_tracking_ref if picking.sale_id else picking.carrier_tracking_ref
            
            if tracking_number:
                # Recalculate exact price locally if missing or fetch from SO
                rate_res = self.coordinadora_rate_shipment(picking.sale_id) if picking.sale_id else {}
                exact_price = rate_res['price'] if rate_res.get('success') else 0.0

                res.append({
                    'exact_price': exact_price,
                    'tracking_number': tracking_number,
                })
            else:
                # We don't implement picking-level guide generation here yet
                # as the current logic is in the SO button.
                res.append({
                    'exact_price': 0.0,
                    'tracking_number': '',
                })
                
        return res

    def coordinadora_get_tracking_link(self, picking):
        """Implement tracking link for Coordinadora."""
        return f"https://www.coordinadora.com/portafolio-de-servicios/servicios-en-linea/rastrear-guias/?guia={picking.carrier_tracking_ref}"

    def coordinadora_cancel_shipment(self, pickings):
        """Implement cancellation for Coordinadora."""
        self.ensure_one()
        
        if not self.coordinadora_use_api:
            raise UserError("Coordinadora API is disabled but cancel_shipment was called.")
            
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

    def action_coordinadora_generate_guide(self, order):
        """
        Refactored logic from SaleOrder._send_by_coordinadora
        """
        self.ensure_one()
        if order.state not in ['sale', 'done']:
            raise UserError("Para generar la guía de Coordinadora, la orden debe estar confirmada.")
        
        if order.carrier_tracking_ref:
            raise UserError("Ya existe una guía generada para esta orden.")

        try:
            client = self._get_coordinadora_client(ws_type='guias')
            
            sender = order.company_id.partner_id
            receiver = order.partner_shipping_id
            
            sender_city = self._normalize_city_code(sender.city_id and sender.city_id.code or '11001000')
            receiver_city = self._normalize_city_code(receiver.city_id and receiver.city_id.code or '11001000')

            total_weight = sum([line.product_id.weight * line.product_uom_qty for line in order.order_line if line.product_id.type != 'service']) or 1.0

            request_data = {
                'codigo_remision': '',
                'fecha': fields.Date.today().strftime('%Y-%m-%d'),
                'id_cliente': int(self.coordinadora_client_id),
                'id_remitente': 0,
                'nit_remitente': sender.vat or self.coordinadora_nit,
                'nombre_remitente': sender.name,
                'direccion_remitente': sender.street,
                'telefono_remitente': sender.phone or sender.mobile,
                'ciudad_remitente': sender_city,
                'nit_destinatario': receiver.vat,
                'div_destinatario': '01',
                'nombre_destinatario': receiver.name,
                'direccion_destinatario': receiver.street,
                'ciudad_destinatario': receiver_city,
                'telefono_destinatario': receiver.phone or receiver.mobile,
                'valor_declarado': order.amount_total,
                'codigo_cuenta': 1,
                'codigo_producto': 0,
                'nivel_servicio': 1,
                'linea': '',
                'contenido': order.client_order_ref or 'Mercancia',
                'referencia': order.name,
                'observaciones': order.note or '',
                'estado': 'PRE',
                'detalle': [{
                    'ubl': 0,
                    'alto': 10,
                    'ancho': 10,
                    'largo': 10,
                    'peso': float(total_weight),
                    'unidades': 1,
                    'referencia': order.name,
                    'nombre_empaque': '',
                }],
                'cuenta_contable': '',
                'centro_costos': '',
                'recaudos': xsd.SkipValue,
                'margen_izquierdo': '',
                'margen_superior': '',
                'usuario_vmi': '',
                'formato_impresion': '',
                'atributo1_nombre': '',
                'atributo1_valor': '',
                'notificaciones': [{
                    'tipo_medio': '1',
                    'destino_notificacion': receiver.email
                }] if receiver.email else xsd.SkipValue,
                'atributos_retorno': [{'nombre': 'pdf_guia'}],
                'nro_doc_radicados': '',
                'nro_sobre': '',
                'codigo_vendedor': '',
                'usuario': self.coordinadora_user,
                'clave': self.coordinadora_password
            }

            response = client.service.Guias_generarGuia(p=request_data)
            
            if hasattr(response, 'codigo_remision'):
                tracking_number = response.codigo_remision
                tracking_url = f"https://www.coordinadora.com/portafolio-de-servicios/servicios-en-linea/rastrear-guias/?guia={tracking_number}"
                
                order.write({
                    'carrier_tracking_ref': tracking_number,
                    'carrier_tracking_url': tracking_url
                })

                pdf_base64 = getattr(response, 'pdf_guia', False)
                if pdf_base64:
                    order.env['ir.attachment'].create({
                        'name': f"Guia_Coordinadora_{tracking_number}.pdf",
                        'type': 'binary',
                        'datas': pdf_base64,
                        'res_model': 'sale.order',
                        'res_id': order.id,
                        'mimetype': 'application/pdf',
                    })
                
                # Propagar al picking actual si existe
                pickings = order.picking_ids.filtered(lambda p: p.state not in ('draft', 'cancel', 'done'))
                for picking in pickings:
                    picking.write({
                        'carrier_tracking_ref': tracking_number,
                        'carrier_id': self.id,
                    })
                    
            else:
                raise UserError(f"Falló la generación de etiqueta Coordinadora: {response}")
                
        except Exception as e:
            raise UserError(f"Error comunicando con Coordinadora API: {e}")

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for picking in self:
            if picking.sale_id and picking.sale_id.carrier_tracking_ref and picking.carrier_id and picking.carrier_id.delivery_type == 'coordinadora':
                if not picking.carrier_tracking_ref:
                    picking.carrier_tracking_ref = picking.sale_id.carrier_tracking_ref
        return res

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    carrier_tracking_ref = fields.Char(string='Tracking Reference', copy=False)
    carrier_tracking_url = fields.Char(string='Tracking URL', copy=False)
