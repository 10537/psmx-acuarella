# -*- coding: utf-8 -*-
# from odoo import http


# class WebsiteSaleMelonn(http.Controller):
#     @http.route('/website_sale_melonn/website_sale_melonn', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/website_sale_melonn/website_sale_melonn/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('website_sale_melonn.listing', {
#             'root': '/website_sale_melonn/website_sale_melonn',
#             'objects': http.request.env['website_sale_melonn.website_sale_melonn'].search([]),
#         })

#     @http.route('/website_sale_melonn/website_sale_melonn/objects/<model("website_sale_melonn.website_sale_melonn"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('website_sale_melonn.object', {
#             'object': obj
#         })
