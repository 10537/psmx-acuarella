# -*- coding: utf-8 -*-

from odoo import models, fields, api

class DeliveryCarrier(models.Model):
	_inherit = 'delivery.carrier'

	token = fields.Char(string="Token")
	url_sale_order_melonn = fields.Char(string="URL Sell-Order Melonn")
	url_product_melonn = fields.Char(string="URL Products Melonn")

	wsg_test = fields.Boolean("Generar guía en modo de prueba")

	# Producción
	wsg_production_url = fields.Char("URL")
	wsg_production_usuario = fields.Char("Usuario")
	wsg_production_password = fields.Char("Password")
	wsg_production_cod_regional = fields.Char("Regional")
	wsg_production_cod_oficina = fields.Char("Oficina")
	wsg_production_cod_cuenta = fields.Char("Cuenta")
	wsg_production_cod_cuenta_recaudo = fields.Char("Cuenta recaudo")

	# Pruebas
	wsg_test_url = fields.Char("URL")
	wsg_test_usuario = fields.Char("Usuario")
	wsg_test_password = fields.Char("Password")
	wsg_test_cod_regional = fields.Char("Regional")
	wsg_test_cod_oficina = fields.Char("Oficina")
	wsg_test_cod_cuenta = fields.Char("Cuenta")
	wsg_test_cod_cuenta_recaudo = fields.Char("Cuenta recaudo")

	# --- Coordinadora Integration ---
	coordinadora_use_api = fields.Boolean(string="Use Coordinadora API")
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
			from odoo.exceptions import UserError
			raise UserError(f"Please configure the Coordinadora {ws_type} WebService URL for {self.coordinadora_environment} environment.")
		
		return Client(wsdl)

	def coordinadora_rate_shipment(self, order):
		"""Implement pricing calculation for Coordinadora."""
		self.ensure_one()
		
		if not self.coordinadora_use_api:
			return {'success': False, 'price': 0.0, 'error_message': 'Coordinadora API is disabled.', 'warning_message': False}
			
		try:
			client = self._get_coordinadora_client(ws_type='guias')
			
			# Extract required info from order
			partner_shipping = order.partner_shipping_id
			city = partner_shipping.city_id and partner_shipping.city_id.l10n_co_edi_code or '11001000'
			
			# Simple sum of weights & volume (or standard box size if none)
			total_weight = sum([line.product_id.weight * line.product_uom_qty for line in order.order_line]) or 1.0
			total_volume = sum([line.product_id.volume * line.product_uom_qty for line in order.order_line]) or 1.0

			request_data = {
				'detalle': {
					'item': [{
						'peso': float(total_weight),
						'alto': 10,
						'ancho': 10,
						'largo': 10,
						'unidades': 1,
						'referencia': order.name,
					}]
				},
				'nivel_servicio': 1,
				'recaudos': '',
				'cnit': self.coordinadora_nit,
				'cdiv': self.coordinadora_div,
				'rcodigo_cm_ciudad': self.company_id.partner_id.city_id.l10n_co_edi_code or '11001000',
				'dcodigo_cm_ciudad': city,
				'codigo_cuenta': 1,
				'valor_declarado': order.amount_total,
				'liquidacion_enguia': '',
				'liquidacion_endespacho': '',
				'codigo_producto': 0,
				'token': ''
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
		"""Implement shipping label generation for Coordinadora."""
		res = []
		for picking in pickings:
			self.ensure_one()
			
			if not self.coordinadora_use_api:
				raise UserError("Coordinadora API is disabled but send_shipping was called.")

			try:
				client = self._get_coordinadora_client(ws_type='guias')
				
				# Setup Sender & Receiver data
				sender = picking.picking_type_id.warehouse_id.partner_id or self.company_id.partner_id
				receiver = picking.partner_id
				
				sender_city = sender.city_id and sender.city_id.l10n_co_edi_code or '11001000'
				receiver_city = receiver.city_id and receiver.city_id.l10n_co_edi_code or '11001000'
				
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
					'valor_declarado': picking.sale_id.amount_total if picking.sale_id else 100000.0,
					'codigo_cuenta': 1,
					'codigo_producto': 0,
					'nivel_servicio': 1,
					'linea': '',
					'contenido': picking.origin or 'Mercancia',
					'referencia': picking.name,
					'observaciones': picking.note or '',
					'estado': 'PRE',
					'detalle': {
						'item': [{
							'peso': float(picking.shipping_weight) or 1.0,
							'alto': 10,
							'ancho': 10,
							'largo': 10,
							'unidades': 1,
							'referencia': picking.name
						}]
					},
					'cuenta_contable': '',
					'centro_costos': '',
					'recaudos': '',
					'margen_izquierdo': '',
					'margen_superior': '',
					'usuario_vmi': '',
					'formato_impresion': '',
					'atributo1_nombre': '',
					'atributo1_valor': '',
					'notificaciones': {
						'item': [{
							'tipo_medio': '1',
							'destino_notificacion': receiver.email
						}]
					} if receiver.email else '',
					'atributos_retorno': {
						'item': [{'nombre': 'pdf_guia'}]
					},
					'nro_doc_radicados': '',
					'nro_sobre': '',
					'codigo_vendedor': '',
					'usuario': self.coordinadora_user,
					'clave': self.coordinadora_password
				}
				
				response = client.service.Guias_generarGuia(p=request_data)
				
				# Parse response
				if hasattr(response, 'codigo_remision'):
					tracking_number = response.codigo_remision
					
					# Note: In a real integration we'd save response.pdf_guia as an attachment on the picking
					
					res.append({
						'exact_price': 0.0,
						'tracking_number': tracking_number,
					})
				else:
					raise UserError(f"Coordinadora label generation failed: {response}")
					
			except Exception as e:
				raise UserError(f"Error communicating with Coordinadora API: {e}")
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


