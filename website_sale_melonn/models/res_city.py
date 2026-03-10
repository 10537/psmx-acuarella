# -*- coding: utf-8 -*-

from odoo import models, fields

class res_city(models.Model):
	_inherit = 'res.city'

	code = fields.Char(string="Código DANE", size=10)
	