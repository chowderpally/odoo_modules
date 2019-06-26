# -*- coding: utf-8 -*-

from odoo import fields, models, _

import time
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from lxml import etree
from odoo.osv.orm import setup_modifiers

class AccountPartnerLedger(models.TransientModel):
    _inherit = "account.common.partner.report"
    _name = "account.report.partner.ledger"
    _description = "Account Partner Ledger"

    amount_currency = fields.Boolean("With Currency",
                                     help="It adds the currency column on report if the "
                                          "currency differs from the company currency.")
    reconciled = fields.Boolean('Reconciled Entries')
    # ABS
    partner_ids = fields.Many2many('res.partner', 'account_report_partner_ledger_partner_rel', 'report_id', 'account_id', string='Partners', required=False)
    # ABS


    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AccountPartnerLedger, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        print (self._context.get('active_model'))
        if self._context.get('active_model', False) and self._context.get('active_model') == 'res.partner':
            if view_type == 'form':
                for node in doc.xpath("//field[@name='partner_ids']"):
                    node.set('attrs', "{'invisible': True}")
                    setup_modifiers(node, res['fields']['partner_ids'])
        res['arch'] = etree.tostring(doc)
        return res

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled, 'amount_currency': self.amount_currency})
        # ABS
        partner_ids = self.partner_ids.mapped('id')
        if partner_ids:
            data['form'].update({'partner_ids': partner_ids})
        # ABS
        return self.env.ref('accounting_pdf_reports.action_report_partnerledger').report_action(self, data=data)
