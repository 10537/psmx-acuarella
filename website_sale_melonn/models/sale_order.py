# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError, ValidationError
import requests
from requests.auth import HTTPBasicAuth
import json
import logging
_logger = logging.getLogger(__name__)

def _get_cuentas(self):
	lcuentas = []
	for rec in self.env["delivery.carrier"].search([('name','=','Envía')]):
		if rec.wsg_test:
			lcuentas.append((rec.wsg_test_cod_cuenta, rec.wsg_test_cod_cuenta))
			lcuentas.append((rec.wsg_test_cod_cuenta_recaudo, '{} {}'.format(rec.wsg_test_cod_cuenta_recaudo, 'Recaudo')))
		else:
			lcuentas.append((rec.wsg_production_cod_cuenta, rec.wsg_production_cod_cuenta))
			lcuentas.append((rec.wsg_production_cod_cuenta_recaudo, '{} {}'.format(rec.wsg_production_cod_cuenta_recaudo, 'Recaudo')))
	return lcuentas

def get_selection_label(self, object, field_name, field_value):
	return dict(self.env[object].fields_get(allfields=[field_name])[field_name]['selection'])[field_value]

class SaleOrder(models.Model):
	_inherit = 'sale.order'

	melonn_order = fields.Char(string="Melonn Order")

	guia_envia_url = fields.Char("Guía envía URL")
	guia_envia = fields.Char("Guía envía")

	# Coordinadora Ext.
	carrier_tracking_ref = fields.Char(string='Tracking Reference', copy=False)
	carrier_tracking_url = fields.Char(string='Tracking URL', copy=False)

	def action_generar_guia(self):
		"""
		Función para generar guías de acuerdo al campo carrier_id
		"""
		for order in self:
			if order.carrier_id:
				if order.carrier_id.name == 'Envía':
					if order.guia_envia:
						raise UserError("Ya existe una guía para esta orden, consúltela en la pestaña: Guía")
					return {
						'type': 'ir.actions.act_window',
						'name': 'Generar guía envía',
						'res_model': 'wizard.delivery.envia',
						'view_mode': 'form',
						'view_type': 'form',
						'target': 'new'
					}
				elif order.carrier_id.name in ['Coordinadora', 'coordinadora']:
					order._send_by_coordinadora()
				else:
					order._send_by_melonn()
			else:
				raise UserError("Este pedido no tiene configurado el método de entrega")
			return True

	def _send_by_coordinadora(self):
		for order in self:
			if order.state not in ['sale', 'done']:
				raise UserError("Para generar la guía de Coordinadora, la orden debe estar confirmada (tener orden de entrega en estado listo).")
			
			if order.carrier_tracking_ref:
				raise UserError("Ya existe una guía generada para esta orden.")

			# 1. Cotizar y agregar monto en la orden de venta (producto configurado en el transportista)
			res_rate = order.carrier_id.coordinadora_rate_shipment(order)
			if not res_rate.get('success'):
				raise UserError(f"Error cotizando con Coordinadora: {res_rate.get('error_message')}")
			
			# Agrega la línea usando la funcionalidad estándar de Odoo
			order.set_delivery_line(order.carrier_id, res_rate['price'])

			# 2. Generar la guía directamente usando el cliente zeep
			try:
				client = order.carrier_id._get_coordinadora_client(ws_type='guias')
				
				sender = order.company_id.partner_id
				receiver = order.partner_shipping_id
				
				sender_city = sender.city_id and sender.city_id.code or '11001000'
				receiver_city = receiver.city_id and receiver.city_id.code or '11001000'

				total_weight = sum([line.product_id.weight * line.product_uom_qty for line in order.order_line if line.product_id.type != 'service']) or 1.0

				request_data = {
					'codigo_remision': '',
					'fecha': fields.Date.today().strftime('%Y-%m-%d'),
					'id_cliente': int(order.carrier_id.coordinadora_client_id),
					'id_remitente': 0,
					'nit_remitente': sender.vat or order.carrier_id.coordinadora_nit,
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
					'detalle': {
						'item': [{
							'peso': float(total_weight),
							'alto': 10,
							'ancho': 10,
							'largo': 10,
							'unidades': 1,
							'referencia': order.name
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
					'usuario': order.carrier_id.coordinadora_user,
					'clave': order.carrier_id.coordinadora_password
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
					
					# 3. Propagar al picking actual si existe (caso de que se haya creado ya el albarán de salida)
					pickings = order.picking_ids.filtered(lambda p: p.state not in ('draft', 'cancel', 'done'))
					for picking in pickings:
						picking.write({
							'carrier_tracking_ref': tracking_number,
							'carrier_id': order.carrier_id.id,
						})
						
				else:
					raise UserError(f"Falló la generación de etiqueta Coordinadora: {response}")
					
			except Exception as e:
				raise UserError(f"Error comunicando con Coordinadora API: {e}")

	def _send_by_melonn(self):
		INVOKE_URL = self.carrier_id.url_sale_order_melonn
		datas = {}
		lineItems = []

		for line in self.order_line.filtered(lambda l: l.product_id.type != 'service'):
			lineItems.append({'sku':line.product_id.default_code, 'quantity':line.product_uom_qty})

		datas = {
			"orderNumber": self.name,
			"orderId": str(self.id),
			"comments": "",
			"requestProcessing": True,
			"shipping": {
				"fullName": self.partner_shipping_id.name,
				"addressL1": self.partner_shipping_id.street,
				"addressL2": self.partner_shipping_id.street2,
				"city": self.partner_shipping_id.city,
				"region": self.partner_shipping_id.state_id.name,
				"country": self.partner_shipping_id.country_id.name,
				"postalCode": self.partner_shipping_id.zip,
				"phoneNumber": "+57-{0}".format(self.partner_shipping_id.phone)
			},
			"buyer": {
				"fullName": self.partner_id.name,
				"phoneNumber": "+57-{0}".format(self.partner_id.phone),
				"email": self.partner_id.email
			},
			"lineItems": lineItems,
			"shippingMethodTitle": "Envío estandar",
			"paymentOnDelivery": {
				"title": "Pago contra entrega en efectivo",
				"amount": self.amount_total
			}
		}

		token = self.carrier_id.token
		headers = {"Content-type": "application/json", "accept": "application/json", "X-Api-Key": token}

		response = requests.post(
			INVOKE_URL,
			data=json.dumps(datas),
			headers=headers
		)
		json_response = response.json()
		_logger.info(json_response)
		
		self.message_post(body="Melonn API Response <b>{0}<b> ".format(json_response))
		if json_response['statusCode'] not in (200, 201):
			raise UserError("ERROR AL GENERAR LA GUIA \n {0}".format(json_response['message']))	

class WizardDeliveryEnvia(models.TransientModel):
	_name = "wizard.delivery.envia"

	order_id = fields.Many2one("sale.order", string="Orden")
	produccion = fields.Boolean("Guía en producción")
	guia = fields.Boolean("Guía generada")
	guia_url = fields.Char("Guía")

	# -- Remitente --
	remitente = fields.Many2one("res.partner", string="Origen")
	# Persona natural o jurídica Remitente
	nom_remitente = fields.Char("Nombre remitente", compute="_compute_fields")
	# Dirección de Remitente del envío
	dir_remitente = fields.Char("Dirección remitente", compute="_compute_fields")
	# Teléfono de Contacto Remitente
	tel_remitente = fields.Char("Teléfono remitente", compute="_compute_fields")
	tel_remitente_wng = fields.Boolean("Warning teléfono remitente", compute="_compute_fields")
	# Numero de Identificación de Remitente
	ced_remitente = fields.Char("Identificación de remitente", compute="_compute_fields")
	# Ciudad código DANE de Remitente
	ciudad_origen = fields.Char("DANE", compute="_compute_fields")

	# -- Destinatario --
	destinatario = fields.Many2one("res.partner", string="Destino")
	# Persona natural o jurídica destino del envío
	nom_destinatario = fields.Char("Nombre destinatario", compute="_compute_fields")
	# Dirección de entrega del envío
	dir_destinatario = fields.Text(string="Dirección destinatario", compute="_compute_fields")
	# Teléfono de Contacto en Destino
	tel_destinatario = fields.Char("Teléfono destinatario", compute="_compute_fields")
	tel_destinatario_wng = fields.Boolean("Warning teléfono destinatario", compute="_compute_fields")
	# Numero de Identificación del Destino
	ced_destinatario = fields.Char("Identificación de destinatario", compute="_compute_fields")
	# Ciudad código DANE de Remitente
	ciudad_destino = fields.Char("DANE", compute="_compute_fields")

	# Codigo de Condición comercial que indica la forma de Pago.
	cod_formapago = fields.Selection([
		('4', 'Crédito'),
		('7', 'Contraentrega'),
	], string="Forma de pago")

	cod_formapago_recaudo = fields.Selection([
		('4', 'Crédito'),
	], string="Forma de pago")

	cod_servicio = fields.Selection([
		('1', '1 (Documento Express) Si es un documento, sobre, carta o factura.'),
		('2', '2 (Mercancia Aerea) Si supera los 9 Kg o es más de una unidad de empaque.'),
		('3', '3 (Mercancia Terrestre) Si supera los 9 Kg o es más de una unidad de empaque.'),
		('4', '4 (Radicacion Factura) Si es un documento, sobre, carta o factura que requiere retorno de documentos firmados.'),
		('7', '7 (Envía Internacional) Envios entre 0.5 y 300 Kg por unidad de empaque.'),
		('12', '12 (Paquete Terrestre) Si el peso se encuentra entre 1 y 8 Kg y es una sola unidad de empaque.'),
		('13', '13 (Paquete Aereo) Si el peso se encuentra entre 1 y 8 '),
	], string="Servicio")

	cod_servicio_recaudo = fields.Selection([
		('2', '2 (Mercancia Aerea) Si supera los 9 Kg o es más de una unidad de empaque.'),
		('3','3 (Mercancia Terrestre) Si supera los 9 Kg o es más de una unidad de empaque.'),
		('12', '12 (Paquete Terrestre) Si el peso se encuentra entre 1 y 8 Kg y es una sola unidad de empaque.'),
		('13', '13 (Paquete Aereo) Si el peso se encuentra entre 1 y 8 '),
	], string="Servicio")

	num_unidades = fields.Integer("Número de unidades")
	mpesoreal_k = fields.Integer("Peso real kg.")
	mpesovolumen_k = fields.Integer("Peso volumen kg.")

	cod_regional_cta = fields.Char("Cod. regional cuenta")
	cod_oficina_cta = fields.Char("Cod. oficina cuenta")
	cod_cuenta = fields.Selection(_get_cuentas, string="Cuenta")
	es_recaudo = fields.Boolean("¿Es cuenta de recaudo?")

	valor_declarado = fields.Integer("Valor declarado")
	# Este campo se usa para la cuenta de recaudo
	valorproducto = fields.Integer("Valor producto")
	#  Descripción de Contenido
	dice_contener = fields.Char("Dice contener")
	# Notas texto/Responsable:	
	texto_guia = fields.Char("Notas texto/Responsable")

	@api.model
	def default_get(self, fields):
		res = super(WizardDeliveryEnvia, self).default_get(fields)
		order_id = self.env["sale.order"].browse(self._context["active_id"])
		res["order_id"] = order_id.id
		res["produccion"] = not order_id.carrier_id.wsg_test
		if res["produccion"]:
			res["cod_regional_cta"] = order_id.carrier_id.wsg_production_cod_regional
			res["cod_oficina_cta"] = order_id.carrier_id.wsg_production_cod_oficina
		else:
			res["cod_regional_cta"] = order_id.carrier_id.wsg_test_cod_regional
			res["cod_oficina_cta"] = order_id.carrier_id.wsg_test_cod_oficina
		res["remitente"] = order_id.company_id.partner_id.id
		res["destinatario"] = order_id.partner_shipping_id.id
		return res

	def fix_numero_telefono(self, numero_string):
		numero_string = numero_string.replace('+57', '')
		numero_string = numero_string.replace(' ', '')
		numero_string = numero_string.strip()
		return numero_string

	@api.depends("remitente", "destinatario")
	def _compute_fields(self):
		# Datos del remitente
		if self.remitente.parent_id:
			nom_remitente = ((self.remitente.parent_id.name or '') + (self.remitente.name or ''))[:50]
			ced_remitente = (self.remitente.parent_id.vat or '')[:15]
		else:
			nom_remitente = (self.remitente.name or '')[:50]
			ced_remitente = (self.remitente.vat or '')[:15]
		self.nom_remitente = nom_remitente
		self.dir_remitente = ((self.remitente.street or '') + (self.remitente.street2 or ''))[:100]
		tel_remitente = self.fix_numero_telefono(self.remitente.phone or self.remitente.mobile or '')
		self.tel_remitente = tel_remitente
		self.tel_remitente_wng = len(tel_remitente) > 10
		self.ced_remitente = ced_remitente
		if self.produccion:
			self.ciudad_origen = (self.remitente.city_id.code or '')[:10]
		else:
			self.ciudad_origen = '1'
		
		# Datos del destinatario
		if self.destinatario.parent_id:
			nom_destinatario = ((self.destinatario.parent_id.name or '') + (self.destinatario.name or ''))[:50]
			ced_destinatario = (self.destinatario.parent_id.vat or '')[:15]
		else:
			nom_destinatario = (self.destinatario.name or '')[:50]
			ced_destinatario = (self.destinatario.vat or '')[:15]
		self.nom_destinatario = nom_destinatario
		self.dir_destinatario = ((self.destinatario.street or '') + (self.destinatario.street2 or ''))[:100]
		tel_destinatario = self.fix_numero_telefono(self.destinatario.phone or self.destinatario.mobile or '')
		self.tel_destinatario = tel_destinatario
		self.tel_destinatario_wng = len(tel_destinatario) > 10
		self.ced_destinatario = ced_destinatario
		if self.produccion:
			self.ciudad_destino = (self.destinatario.city_id.code or '')[:10]
		else:
			self.ciudad_destino = '1'

	@api.onchange('cod_cuenta')
	def on_change_cod_cuenta(self):
		if self.cod_cuenta:
			label = get_selection_label(self, self._name, 'cod_cuenta', self.cod_cuenta)
			if 'recaudo' in label.lower():
				self.es_recaudo = True
			else:
				self.es_recaudo = False
		else:
			self.es_recaudo = False

	def send_by_envia(self):
		# Campos obligados
		if not self.tel_destinatario:
			raise UserError("Destinatario no tiene configurado un número de teléfono")

		headers = { "Content-type": "application/json"}
		# Campos del modo de pruebas
		if not self.produccion:
			url = self.order_id.carrier_id.wsg_test_url
			user = self.order_id.carrier_id.wsg_test_usuario
			password = self.order_id.carrier_id.wsg_test_password
		else:
			# Campos de producción
			url = self.order_id.carrier_id.wsg_production_url
			user = self.order_id.carrier_id.wsg_production_usuario
			password = self.order_id.carrier_id.wsg_production_password

		datas = {
			"Ciudad_Origen": self.ciudad_origen,
			"Ciudad_Destino": self.ciudad_destino,
			"Cod_FormaPago": self.cod_formapago if not self.es_recaudo else self.cod_formapago_recaudo,
			"Cod_Servicio": self.cod_servicio if not self.es_recaudo else self.cod_servicio_recaudo,
			"Num_Unidades": self.num_unidades,
			"MPesoReal_K": self.mpesoreal_k,
			"MPesoVolumen_K": self.mpesovolumen_k,
			"Valor_Declarado": self.valor_declarado,
			"Mca_NoSabado": 0, # Entrega los sábados (default no)
			"Mca_DocInternacional": 0, # Despachos al Exterior (default no)
			"Cod_Regional_Cta": self.cod_regional_cta,
			"Cod_Oficina_Cta": self.cod_oficina_cta,
			"Cod_Cuenta": self.cod_cuenta,
			"info_origen": {
				"Nom_Remitente": self.nom_remitente,
				"Dir_Remitente":  self.dir_remitente,
				"Tel_Remitente": self.tel_remitente[:10],
				"Ced_Remitente": self.ced_remitente,
			},
			"info_destino": {
				"Nom_Destinatario": self.nom_destinatario,
				"Dir_Destinatario":  self.dir_destinatario,
				"Tel_Destinatario": self.tel_destinatario[:10],
				"Ced_Destinatario": self.ced_destinatario,
			},
			"info_contenido": {
				# Numero de Factura u otros documentos relacionados con el despacho
				"Num_Documentos": self.order_id.name,
				"Dice_Contener": self.dice_contener,
				"Texto_Guia": self.texto_guia or '',
				"Accion_NotaGuia": '', # Observaciones adicionales en la guía
				"CentroCosto": '', # Centro de costo que aplicará
			},
			"Numero_Guia": '', # Numero de guia previamente asignado
			# Si este documento lleva carta de porte y debe devolverse
			"Con_Cartaporte": "0",
			# Si se requiere que el sistema genere la orden de
			#   servicio para la recolección debe enviar la letra S.
			#   En caso de ser solo liquidación no es necesario enviar
			"generar_os": "N",
		}
		if self.es_recaudo:
			datas["info_contenido"].update({
				"valorproducto": self.valorproducto
			})
		_logger.info(datas)
		_logger.info(user)
		_logger.info(password)
		
		try:
			response = requests.post(
				url,
				auth=HTTPBasicAuth(user, password),
				headers=headers,
				data=json.dumps(datas),
			)
			json_response = response.json()
			_logger.info(json_response)
			response.raise_for_status()
			self.order_id.update({
				'guia_envia_url': json_response['urlguia'],
				'guia_envia': json_response['guia']
				})
			self.update({
				'guia': True,
				'guia_url': json_response['urlguia']
			})
			return {
				'type': 'ir.actions.act_window',
				'name': 'Generar guía envía',
				'res_model': 'wizard.delivery.envia',
				'res_id': self.id,
				'view_mode': 'form',
				'view_type': 'form',
				'target': 'new'
			}
		except requests.exceptions.HTTPError as err:
			raise UserError('{}\n\t{}'.format(err, json_response['respuesta']))
	