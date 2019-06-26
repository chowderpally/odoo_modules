# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError

import time
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from lxml import etree
from odoo.osv.orm import setup_modifiers


class AccountReportGeneralLedger(models.TransientModel):
    _inherit = "account.common.account.report"
    _name = "account.report.general.ledger"
    _description = "General Ledger Report"

    initial_balance = fields.Boolean(string='Include Initial Balances',
                                    help='If you selected date, this field allow you to add a row to display the amount of debit/credit/balance that precedes the filter you\'ve set.')
    sortby = fields.Selection([('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')], string='Sort by', required=True, default='sort_date')
    journal_ids = fields.Many2many('account.journal', 'account_report_general_ledger_journal_rel', 'account_id', 'journal_id', string='Journals', required=True)
    # ABS
    account_ids = fields.Many2many('account.account', 'account_report_general_ledger_account_rel', 'report_id', 'account_id', string='Accounts', required=False)
    # ABS



    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AccountReportGeneralLedger, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        print (self._context.get('active_model'))
        if self._context.get('active_model', False) and self._context.get('active_model') == 'account.account':
            if view_type == 'form':
                for node in doc.xpath("//field[@name='account_ids']"):
                    node.set('attrs', "{'invisible': True}")
                    setup_modifiers(node, res['fields']['account_ids'])
        res['arch'] = etree.tostring(doc)
        return res

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['initial_balance', 'sortby'])[0])
        if data['form'].get('initial_balance') and not data['form'].get('date_from'):
            raise UserError(_("You must define a Start Date"))
        records = self.env[data['model']].browse(data.get('ids', []))
        # ABS
        account_ids = self.account_ids.mapped('id')
        if account_ids:
            data['form'].update({'account_ids': account_ids})
        # ABS
        return self.env.ref('accounting_pdf_reports.action_report_general_ledger').with_context(landscape=True).report_action(records, data=data)



