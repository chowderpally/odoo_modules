# -*- coding: utf-8 -*-

try:
    import xlsxwriter
except ImportError:
    pass

import time
from dateutil.relativedelta import relativedelta
import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class AgedPartnerReportStore(models.TransientModel):
    _name = 'aged.partner.report.store'

    name = fields.Char(string='File Name', size=64)
    report = fields.Binary('Download File', filters='.xls', readonly=True)


class AccountAgedTrialBalance(models.TransientModel):
    _name = 'account.aged.trial.balance'
    _inherit = 'account.common.partner.report'
    _description = 'Account Aged Trial balance Report'

    period_length = fields.Integer(string='Period Length (days)', required=True, default=30)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True)
    date_from = fields.Date(default=lambda *a: time.strftime('%Y-%m-%d'))
    partner_ids = fields.Many2many('res.partner', 'aged_partners', 'cust_id',
                                   'customer_id', 'Customers/Suppliers')

    def _print_report(self, data):
        res = {}
        data = self.pre_print_report(data)
        data['form'].update(self.read(['period_length'])[0])
        period_length = data['form']['period_length']
        if period_length<=0:
            raise UserError(_('You must set a period length greater than 0.'))
        if not data['form']['date_from']:
            raise UserError(_('You must set a start date.'))

        start = data['form']['date_from']
        data['form']['partner_ids'] = self.partner_ids.ids
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length - 1)
            res[str(i)] = {
                'name': (i != 0 and (str((5-(i+1)) * period_length) + '-' + str((5-i) * period_length)) or ('+'+str(4 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)
        data['form'].update(res)
        return self.env.ref('accounting_pdf_reports.action_report_aged_partner_balance').with_context(landscape=True).report_action(self, data=data)

    def _get_partner_move_lines(self, account_type, date_from, target_move, period_length,partner_ids):
        # This method can receive the context key 'include_nullified_amount' {Boolean}
        # Do an invoice and a payment and unreconcile. The amount will be nullified
        # By default, the partner wouldn't appear in this report.
        # The context key allow it to appear
        # In case of a period_length of 30 days as of 2019-02-08, we want the following periods:
        # Name       Stop         Start
        # 1 - 30   : 2019-02-07 - 2019-01-09
        # 31 - 60  : 2019-01-08 - 2018-12-10
        # 61 - 90  : 2018-12-09 - 2018-11-10
        # 91 - 120 : 2018-11-09 - 2018-10-11
        # +120     : 2018-10-10
        periods = {}
        start = date_from
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length)
            period_name = str((5-(i+1)) * period_length + 1) + '-' + str((5-i) * period_length)
            period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
            if i == 0:
                period_name = '+' + str(4 * period_length)
            periods[str(i)] = {
                'name': period_name,
                'stop': period_stop,
                'start': (i!=0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop

        res = []
        total = []
        cr = self.env.cr
        user_company = self.env.user.company_id
        user_currency = user_company.currency_id
        ResCurrency = self.env['res.currency'].with_context(date=date_from)
        company_ids = self._context.get('company_ids') or [user_company.id]
        move_state = ['draft', 'posted']
        if target_move == 'posted':
            move_state = ['posted']
        arg_list = (tuple(move_state), tuple(account_type))
        #build the reconciliation clause to see what partner needs to be printed
        reconciliation_clause = '(l.reconciled IS FALSE)'
        cr.execute('SELECT debit_move_id, credit_move_id FROM account_partial_reconcile where max_date > %s', (date_from,))
        reconciled_after_date = []
        for row in cr.fetchall():
            reconciled_after_date += [row[0], row[1]]
        if reconciled_after_date:
            reconciliation_clause = '(l.reconciled IS FALSE OR l.id IN %s)'
            arg_list += (tuple(reconciled_after_date),)
        arg_list += (date_from, tuple(company_ids))
        if len(partner_ids)>0:
            query = '''
                SELECT DISTINCT l.partner_id, UPPER(res_partner.name)
                FROM account_move_line AS l left join res_partner on l.partner_id = res_partner.id, account_account, account_move am
                WHERE (l.account_id = account_account.id)
                    AND (l.move_id = am.id)
                    AND (am.state IN %s)
                    AND (account_account.internal_type IN %s)
                    AND ''' + reconciliation_clause + '''
                    AND (l.date <= %s)
                    AND l.company_id IN %s
                    AND l.partner_id IN ('''+','.join(map(str, partner_ids))+''')
                ORDER BY UPPER(res_partner.name)'''
            cr.execute(query, arg_list)
        else:
            query = '''
                SELECT DISTINCT l.partner_id, UPPER(res_partner.name)
                FROM account_move_line AS l left join res_partner on l.partner_id = res_partner.id, account_account, account_move am
                WHERE (l.account_id = account_account.id)
                    AND (l.move_id = am.id)
                    AND (am.state IN %s)
                    AND (account_account.internal_type IN %s)
                    AND ''' + reconciliation_clause + '''
                    AND (l.date <= %s)
                    AND l.company_id IN %s
                ORDER BY UPPER(res_partner.name)'''
            cr.execute(query, arg_list)

        partners = cr.dictfetchall()
        # put a total of 0
        for i in range(7):
            total.append(0)

        # Build a string like (1,2,3) for easy use in SQL query
        partner_ids = [partner['partner_id'] for partner in partners if partner['partner_id']]
        lines = dict((partner['partner_id'] or False, []) for partner in partners)
        if not partner_ids:
            return [], [], {}

        # This dictionary will store the not due amount of all partners
        undue_amounts = {}
        query = '''SELECT l.id
                FROM account_move_line AS l, account_account, account_move am
                WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                    AND (am.state IN %s)
                    AND (account_account.internal_type IN %s)
                    AND (COALESCE(l.date_maturity,l.date) >= %s)\
                    AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                AND (l.date <= %s)
                AND l.company_id IN %s'''
        cr.execute(query, (tuple(move_state), tuple(account_type), date_from, tuple(partner_ids), date_from, tuple(company_ids)))
        aml_ids = cr.fetchall()
        aml_ids = aml_ids and [x[0] for x in aml_ids] or []
        for line in self.env['account.move.line'].browse(aml_ids):
            partner_id = line.partner_id.id or False
            if partner_id not in undue_amounts:
                undue_amounts[partner_id] = 0.0
            line_amount = ResCurrency._compute(line.company_id.currency_id, user_currency, line.balance)
            if user_currency.is_zero(line_amount):
                continue
            for partial_line in line.matched_debit_ids:
                if partial_line.max_date <= date_from:
                    line_amount += ResCurrency._compute(partial_line.company_id.currency_id, user_currency, partial_line.amount)
            for partial_line in line.matched_credit_ids:
                if partial_line.max_date <= date_from:
                    line_amount -= ResCurrency._compute(partial_line.company_id.currency_id, user_currency, partial_line.amount)
            if not self.env.user.company_id.currency_id.is_zero(line_amount):
                undue_amounts[partner_id] += line_amount
                lines[partner_id].append({
                    'line': line,
                    'amount': line_amount,
                    'period': 6,
                })

        # Use one query per period and store results in history (a list variable)
        # Each history will contain: history[1] = {'<partner_id>': <partner_debit-credit>}
        history = []
        for i in range(5):
            args_list = (tuple(move_state), tuple(account_type), tuple(partner_ids),)
            dates_query = '(COALESCE(l.date_maturity,l.date)'

            if periods[str(i)]['start'] and periods[str(i)]['stop']:
                dates_query += ' BETWEEN %s AND %s)'
                args_list += (periods[str(i)]['start'], periods[str(i)]['stop'])
            elif periods[str(i)]['start']:
                dates_query += ' >= %s)'
                args_list += (periods[str(i)]['start'],)
            else:
                dates_query += ' <= %s)'
                args_list += (periods[str(i)]['stop'],)
            args_list += (date_from, tuple(company_ids))

            query = '''SELECT l.id
                    FROM account_move_line AS l, account_account, account_move am
                    WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                        AND (am.state IN %s)
                        AND (account_account.internal_type IN %s)
                        AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                        AND ''' + dates_query + '''
                    AND (l.date <= %s)
                    AND l.company_id IN %s'''
            cr.execute(query, args_list)
            partners_amount = {}
            aml_ids = cr.fetchall()
            aml_ids = aml_ids and [x[0] for x in aml_ids] or []
            for line in self.env['account.move.line'].browse(aml_ids):
                partner_id = line.partner_id.id or False
                if partner_id not in partners_amount:
                    partners_amount[partner_id] = 0.0
                line_amount = ResCurrency._compute(line.company_id.currency_id, user_currency, line.balance)
                if user_currency.is_zero(line_amount):
                    continue
                for partial_line in line.matched_debit_ids:
                    if partial_line.max_date <= date_from:
                        line_amount += ResCurrency._compute(partial_line.company_id.currency_id, user_currency, partial_line.amount)
                for partial_line in line.matched_credit_ids:
                    if partial_line.max_date <= date_from:
                        line_amount -= ResCurrency._compute(partial_line.company_id.currency_id, user_currency, partial_line.amount)

                if not self.env.user.company_id.currency_id.is_zero(line_amount):
                    partners_amount[partner_id] += line_amount
                    lines[partner_id].append({
                        'line': line,
                        'amount': line_amount,
                        'period': i + 1,
                        })
            history.append(partners_amount)

        for partner in partners:
            if partner['partner_id'] is None:
                partner['partner_id'] = False
            at_least_one_amount = False
            values = {}
            undue_amt = 0.0
            if partner['partner_id'] in undue_amounts:  # Making sure this partner actually was found by the query
                undue_amt = undue_amounts[partner['partner_id']]

            total[6] = total[6] + undue_amt
            values['direction'] = undue_amt
            if not float_is_zero(values['direction'], precision_rounding=self.env.user.company_id.currency_id.rounding):
                at_least_one_amount = True

            for i in range(5):
                during = False
                if partner['partner_id'] in history[i]:
                    during = [history[i][partner['partner_id']]]
                # Adding counter
                total[(i)] = total[(i)] + (during and during[0] or 0)
                values[str(i)] = during and during[0] or 0.0
                if not float_is_zero(values[str(i)], precision_rounding=self.env.user.company_id.currency_id.rounding):
                    at_least_one_amount = True
            values['total'] = sum([values['direction']] + [values[str(i)] for i in range(5)])
            ## Add for total
            total[(i + 1)] += values['total']
            values['partner_id'] = partner['partner_id']
            if partner['partner_id']:
                browsed_partner = self.env['res.partner'].browse(partner['partner_id'])
                values['name'] = browsed_partner.name and len(browsed_partner.name) >= 45 and browsed_partner.name[0:40] + '...' or browsed_partner.name
                values['trust'] = browsed_partner.trust
            else:
                values['name'] = _('Unknown Partner')
                values['trust'] = False

            if at_least_one_amount or (self._context.get('include_nullified_amount') and lines[partner['partner_id']]):
                res.append(values)

        return res, total, lines

    def generate_xlsx_aged_partner_balance(self):
        if self.period_length <= 0:
            raise UserError(_('You must set a period length greater than 0'))

        if not self.date_from:
            raise UserError(_('You must set a start date.'))

        if self.result_selection == 'customer':
            account_type = ['receivable']
        elif self.result_selection == 'supplier':
            account_type = ['payable']
        else:
            account_type = ['payable', 'receivable']

        date_from = self.date_from
        target_move = self.target_move
        period_length = self.period_length

        partner_ids = list(self.partner_ids.ids)

        movelines, total, dummy = self._get_partner_move_lines(account_type, date_from, target_move, period_length,
                                                               partner_ids)

        workbook = xlsxwriter.Workbook('Aged Partner Balance Report.xls')

        # Cell & Sheet Formatting
        sheet = workbook.add_worksheet('Aged Partner Balance')
        title_format = workbook.add_format({'bold': 1, 'align': 'left', 'font_size': 15, 'fg_color': '#BCBCB7'})
        title_format1 = workbook.add_format({'bold': 1, 'align': 'left', 'font_size': 11})
        title_format2 = workbook.add_format({'bold': 1, 'align': 'right', 'font_size': 11})
        title_format3 = workbook.add_format({'bold': 1, 'align': 'center', 'font_size': 11, 'fg_color': '#BCBCB7'})

        # Column Widths
        sheet.set_column('A:A', 15)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 15)

        # Report Title
        sheet.merge_range('A3:B3', 'Aged Partner Balance', title_format)

        # Report Information
        sheet.write('A5', 'Start Date', title_format1)
        sheet.write('A6', str(self.date_from))

        sheet.write('D5', 'Period Length', title_format1)
        sheet.write('D6', str(self.period_length))

        sheet.write('A9', "Partner's", title_format1)
        if self.result_selection == 'customer':
            sheet.write('A10', 'Receivable Accounts')
        elif self.result_selection == 'supplier':
            sheet.write('A10', 'Payable Accounts')
        elif self.result_selection == 'customer_supplier':
            sheet.write('A10', 'Receivable and Payable Accounts')

        sheet.write('D9', 'Target Moves', title_format1)
        if self.target_move == 'all':
            sheet.write('D10', 'All Entries')
        elif self.target_move == 'posted':
            sheet.write('D10', 'All Posted Entries')

        # Table Header
        sheet.write('A12', 'Partners', title_format3)
        sheet.write('B12', 'Not Due', title_format3)
        sheet.write('C12', '0-30', title_format3)
        sheet.write('D12', '30-60', title_format3)
        sheet.write('E12', '60-90', title_format3)
        sheet.write('F12', '90-120', title_format3)
        sheet.write('G12', '+120', title_format3)
        sheet.write('H12', 'Total', title_format3)

        # Content Total
        if movelines:
            sheet.write('A13', 'Account Total', title_format1)
            sheet.write('B13', total[6], title_format2)
            sheet.write('C13', total[4], title_format2)
            sheet.write('D13', total[3], title_format2)
            sheet.write('E13', total[2], title_format2)
            sheet.write('F13', total[1], title_format2)
            sheet.write('G13', total[0], title_format2)
            sheet.write('H13', total[5], title_format2)
            row = 13
        else:
            row = 12

        # Table Content
        for move in movelines:
            sheet.write(row, 0, move['name'])
            sheet.write(row, 1, move['direction'])
            sheet.write(row, 2, move['4'])
            sheet.write(row, 3, move['3'])
            sheet.write(row, 4, move['2'])
            sheet.write(row, 5, move['1'])
            sheet.write(row, 6, move['0'])
            sheet.write(row, 7, move['total'])
            row += 1

        workbook.close()

        result_file = open('Aged Partner Balance Report.xls', 'rb').read()
        attachment_id = self.env['aged.partner.report.store'].create({
            'name': 'Aged Partner Balance Report {}.xls'.format(str(self.date_from)),
            'report': base64.encodebytes(result_file)
        })

        return {
            'name': _('Download Aged Partner Balance Report'),
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aged.partner.report.store',
            'res_id': attachment_id.id,
            'data': None,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
