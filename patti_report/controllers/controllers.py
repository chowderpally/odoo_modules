# -*- coding: utf-8 -*-
from odoo import http

# class PattiReport(http.Controller):
#     @http.route('/patti_report/patti_report/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/patti_report/patti_report/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('patti_report.listing', {
#             'root': '/patti_report/patti_report',
#             'objects': http.request.env['patti_report.patti_report'].search([]),
#         })

#     @http.route('/patti_report/patti_report/objects/<model("patti_report.patti_report"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('patti_report.object', {
#             'object': obj
#         })