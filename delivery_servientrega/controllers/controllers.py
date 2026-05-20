# -*- coding: utf-8 -*-
# from odoo import http


# class DeliveryServientrega(http.Controller):
#     @http.route('/delivery_servientrega/delivery_servientrega', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/delivery_servientrega/delivery_servientrega/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('delivery_servientrega.listing', {
#             'root': '/delivery_servientrega/delivery_servientrega',
#             'objects': http.request.env['delivery_servientrega.delivery_servientrega'].search([]),
#         })

#     @http.route('/delivery_servientrega/delivery_servientrega/objects/<model("delivery_servientrega.delivery_servientrega"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('delivery_servientrega.object', {
#             'object': obj
#         })

