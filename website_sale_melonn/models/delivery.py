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
		# TODO: Implement the actual get_shipping_rate logic calling the SOAP API
		return {
			'success': True,
			'price': 0.0,
			'error_message': False,
			'warning_message': False
		}

	def coordinadora_send_shipping(self, pickings):
		"""Implement shipping label generation for Coordinadora."""
		res = []
		for picking in pickings:
			self.ensure_one()
			# TODO: Implement the send_shipping logic calling the SOAP API Guia_generar
			res.append({
				'exact_price': 0.0,
				'tracking_number': 'TODO-COORD',
			})
		return res

	def coordinadora_get_tracking_link(self, picking):
		"""Implement tracking link for Coordinadora."""
		return f"https://www.coordinadora.com/portafolio-de-servicios/servicios-en-linea/rastrear-guias/?guia={picking.carrier_tracking_ref}"

	def coordinadora_cancel_shipment(self, pickings):
		"""Implement cancellation for Coordinadora."""
		self.ensure_one()
		# TODO: Implement cancellation logic via SOAP API API
		raise NotImplementedError("Cancel shipment not yet fully implemented for Coordinadora.")

