from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    dane_code = fields.Char(string="Código DANE", size=8)
