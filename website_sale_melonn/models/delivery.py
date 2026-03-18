# -*- coding: utf-8 -*-

from odoo import models, fields, api
from zeep import xsd

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

