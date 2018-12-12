# -*- coding: utf-8 -*-

import xlsxwriter
import base64

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ReportLog(models.Model):
    _name = 'report.log'

    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    po_value = fields.Float(string='Purchase Value')
    payments = fields.Float(string='Payments')
    opening_bal = fields.Float(string='Opening Balance')
    closing_bal = fields.Float(string='Closing Balance')


class PattiReportWizard(models.TransientModel):
    _name = 'report.wizard'

    partner_id = fields.Many2one('res.partner', string='Vendor')
    from_date = fields.Date(string='From')
    to_date = fields.Date(string='To')

    @api.multi
    def generate_xlsx_report(self):

        def get_total_freight():
            po_domain = ['&', ('partner_id', '=', self.partner_id.id), ('type', '=', 'in_invoice'),
                              ('date_invoice', '>=', self.from_date), ('date_invoice', '<=', self.to_date)]
            po_value = self.env['account.invoice'].search(po_domain)

            tot_freight = 0.00
            for po in po_value:
                for fr in po.invoice_line_ids:
                    tot_freight += fr.freight
            return tot_freight

        def get_po_value():
            po_domain = ['&', ('partner_id', '=', self.partner_id.id), ('type', '=', 'in_invoice'),
                              ('date_invoice', '>=', self.from_date), ('date_invoice', '<=', self.to_date)]
            po_value = self.env['account.invoice'].search(po_domain)

            po_total = 0.00
            for po in po_value:
                po_total += po.amount_total
            return po_total

        def get_payments():
            pay_domain = ['&', ('partner_type', '=', 'supplier'), ('partner_id', '=', self.partner_id.id),
                               ('payment_date', '>=', self.from_date), ('payment_date', '<=', self.to_date)]
            payment_value = self.env['account.payment'].search(pay_domain)

            pay_total = 0.00
            for pay in payment_value:
                pay_total += pay.amount

            return pay_total

        def render_report():
            workbook = xlsxwriter.Workbook('patti_report.xls')

            # Cell & Sheet formatting
            sheet = workbook.add_worksheet('Patti Report')
            title_format = workbook.add_format({'bold': 1, 'border': 1, 'align': 'center', 'valign': 'vcenter',
                                                'fg_color': '#FCFCD9'})
            title_format1 = workbook.add_format({'bold': 1, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            border = workbook.add_format({'border': 1})

            # Report Title
            sheet.merge_range('A1:Q1', 'Patti Report', title_format)
            sheet.merge_range('A2:Q2',
                              '{} - From: {} To: {}'.format(self.partner_id.name, self.from_date, self.to_date),
                              title_format1)

            # Setting Column Widths
            sheet.set_column('A:A', 11)
            sheet.set_column('B:B', 11)
            sheet.set_column('C:C', 10)
            sheet.set_column('D:D', 15)
            sheet.set_column('E:E', 5)
            sheet.set_column('F:F', 8)
            sheet.set_column('G:G', 8)
            sheet.set_column('H:H', 8)
            sheet.set_column('I:I', 15)
            sheet.set_column('J:J', 15)
            sheet.set_column('K:K', 8)
            sheet.set_column('L:L', 8)
            sheet.set_column('M:M', 8)
            sheet.set_column('N:N', 8)
            sheet.set_column('O:O', 8)
            sheet.set_column('P:P', 8)
            sheet.set_column('Q:Q', 10)

            # Report Headers
            sheet.write('A3', 'Date', title_format)
            sheet.write('B3', 'Purchase No', title_format)
            sheet.write('C3', 'Vehicle No', title_format)
            sheet.write('D3', 'Item Name', title_format)
            sheet.write('E3', 'KG', title_format)
            sheet.write('F3', 'Bags', title_format)
            sheet.write('G3', 'Weightment', title_format)
            sheet.write('H3', 'Net Weight', title_format)
            sheet.write('I3', 'Moisture Cut', title_format)
            sheet.write('J3', 'Shortage Weight', title_format)
            sheet.write('K3', 'Quantity', title_format)
            sheet.write('L3', 'Rate', title_format)
            sheet.write('M3', 'Gross', title_format)
            sheet.write('N3', 'Rusum', title_format)
            sheet.write('O3', 'Freight', title_format)
            sheet.write('P3', 'Other Debits & Credits', title_format)
            sheet.write('Q3', 'Net Amount', title_format)

            domain = ['&', ('partner_id', '=', self.partner_id.id), ('type', '=', 'in_invoice'),
                      ('date_invoice', '>=', self.from_date), ('date_invoice', '<=', self.to_date)]
            vendor_bills = self.env['account.invoice'].search(domain)

            row = 3
            for v in vendor_bills:
                line_ids = v.invoice_line_ids
                for line in line_ids:
                    col = 0
                    sheet.write(row, col, v.date_invoice, border)
                    col += 1
                    sheet.write(row, col, v.sequence_number_next, border)
                    col += 1
                    sheet.write(row, col, line.vehicle_no, border)
                    col += 1
                    sheet.write(row, col, line.product_id.name, border)
                    col += 1
                    sheet.write(row, col, line.bag_wt, border)
                    col += 1
                    sheet.write(row, col, line.filled_bags, border)
                    col += 1
                    sheet.write(row, col, line.weighment, border)
                    col += 1
                    sheet.write(row, col, line.net_wt, border)
                    col += 1
                    sheet.write(row, col, line.moisture_qty, border)
                    col += 1
                    sheet.write(row, col, line.short, border)
                    col += 1
                    sheet.write(row, col, line.final_qty, border)
                    col += 1
                    sheet.write(row, col, line.price_unit, border)
                    col += 1
                    sheet.write(row, col, line.gross, border)
                    col += 1
                    sheet.write(row, col, line.rusum, border)
                    col += 1
                    sheet.write(row, col, line.freight, border)
                    col += 1
                    sheet.write(row, col, '0.00', border)
                    col += 1
                    sheet.write(row, col, line.price_subtotal, border)
                    row += 1

            sheet.write(row, 0, 'Totals', border)
            sheet.write(row, 1, '', border)
            sheet.write(row, 2, '', border)
            sheet.write(row, 3, '', border)
            sheet.write(row, 4, '', border)
            bags = '=SUM(F4:F{})'.format(row)
            sheet.write(row, 5, bags, border)
            weightment = '=SUM(G4:G{})'.format(row)
            sheet.write(row, 6, weightment, border)
            net_wt = '=SUM(H4:H{})'.format(row)
            sheet.write(row, 7, net_wt, border)
            moisture_cut = '=SUM(I4:I{})'.format(row)
            sheet.write(row, 8, moisture_cut, border)
            shortage_wt = '=SUM(J4:J{})'.format(row)
            sheet.write(row, 9, shortage_wt, border)
            qty = '=SUM(K4:K{})'.format(row)
            sheet.write(row, 10, qty, border)
            sheet.write(row, 11, '', border)
            gross = '=SUM(M4:M{})'.format(row)
            sheet.write(row, 12, gross, border)
            rusum = '=SUM(N4:N{})'.format(row)
            sheet.write(row, 13, rusum, border)
            freight = '=SUM(O4:O{})'.format(row)
            sheet.write(row, 14, freight, border)
            othdc = '=SUM(P4:P{})'.format(row)
            sheet.write(row, 15, othdc, border)
            nt_amt = '=SUM(Q4:Q{})'.format(row)
            sheet.write(row, 16, nt_amt, border)

            row += 2
            nw_row = row

            # Second Table Headers
            col = 0
            sheet.write(row, col, 'Voucher No.', title_format)
            col += 1
            sheet.write(row, col, 'Date', title_format)
            col += 1
            sheet.write(row, col, 'Account', title_format)
            col += 1
            sheet.write(row, col, '', title_format)
            col += 1
            sheet.write(row, col, '', title_format)
            col += 1
            sheet.write(row, col, 'Amount', title_format)
            col += 1
            sheet.write(row, col, '')
            col += 1
            sheet.write(row, col, '')

            payments_domain = ['&', ('partner_type', '=', 'supplier'), ('partner_id', '=', self.partner_id.id),
                               ('payment_date', '>=', self.from_date), ('payment_date', '<=', self.to_date)]
            payments = self.env['account.payment'].search(payments_domain)

            row += 1
            nw_row1 = row

            # Second Table Data
            for payment in payments:
                col = 0
                sheet.write(row, col, payment.name, border)
                col += 1
                sheet.write(row, col, payment.payment_date, border)
                col += 1
                sheet.write(row, col, payment.journal_id.name, border)
                col += 1
                sheet.write(row, col, '', border)
                col += 1
                sheet.write(row, col, '', border)
                col += 1
                sheet.write(row, col, payment.amount, border)
                row += 1

            sheet.write(row, 0, 'Totals', border)
            sheet.write(row, 1, '', border)
            sheet.write(row, 2, '', border)
            sheet.write(row, 3, '', border)
            sheet.write(row, 4, '', border)

            payments_dom = ['&', ('partner_type', '=', 'supplier'), ('partner_id', '=', self.partner_id.id),
                          ('payment_date', '>=', self.from_date), ('payment_date', '<=', self.to_date)]
            payments_count = self.env['account.payment'].search(payments_dom)

            if len(payments_count) == 0:
                paid_amt = '0.00'
                sheet.write(row, 5, paid_amt, border)
            if len(payments_count) == 1:
                paid_amt = '=F{}'.format(nw_row1 + 1)
                sheet.write(row, 5, paid_amt, border)
            if len(payments_count) > 1:
                paid_amt = '=SUM(F{}:F{})'.format(nw_row1 + 1, row)
                sheet.write(row, 5, paid_amt, border)

            # Third Table
            sheet.write(nw_row, 8, 'Total Quantity', border)
            sheet.write(nw_row, 9, qty, border)
            nw_row += 1
            sheet.write(nw_row, 8, 'Total Purchase Value', border)
            sheet.write(nw_row, 9, gross, border)
            nw_row += 1
            sheet.write(nw_row, 8, 'Total Rusum', border)
            sheet.write(nw_row, 9, rusum, border)
            nw_row += 1
            sheet.write(nw_row, 8, 'Freight', border)
            sheet.write(nw_row, 9, freight, border)
            nw_row += 1
            sheet.write(nw_row, 8, 'Other Debits & Credits', border)
            sheet.write(nw_row, 9, othdc, border)
            nw_row += 1
            temp = nw_row
            sheet.write(nw_row, 8, 'Net Amount', border)
            sheet.write(nw_row, 9, nt_amt, border)
            nw_row += 1
            sheet.write(nw_row, 8, 'Opening Balance', border)
            if not report_log:
                sheet.write(nw_row, 9, '0.00', border)
            else:
                sheet.write(nw_row, 9, report_log.closing_bal, border)
            nw_row += 1
            sheet.write(nw_row, 8, 'Paid Amount', border)
            sheet.write(nw_row, 9, paid_amt, border)
            nw_row += 1
            sheet.write(nw_row, 8, 'Payable Amount', border)
            payable = '=SUM(J{}:J{}) - J{} - J{}'.format(temp + 1, nw_row - 1, nw_row, nw_row - 4)
            sheet.write(nw_row, 9, payable, border)
            nw_row += 1
            temp1 = nw_row
            sheet.write(nw_row, 8, 'Brokens', border)
            sheet.write(nw_row, 9, '0.00', border)
            nw_row += 1
            sheet.write(nw_row, 8, '', border)
            total = '=J{}-J{}'.format(temp1, nw_row)
            sheet.write(nw_row, 9, total, border)

            # Closing Workbook
            workbook.close()

            result_file = open('patti_report.xls', 'rb').read()
            attachment_id = self.env['report.store'].create({
                'name': 'Patti Report {}.xls'.format(self.partner_id.name),
                'report': base64.encodebytes(result_file)
            })

            return {
                'name': _('Download Report'),
                'context': self.env.context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'report.store',
                'res_id': attachment_id.id,
                'data': None,
                'type': 'ir.actions.act_window',
                'target': 'new'
            }

        partner_domain = [('partner_id', '=', self.partner_id.id)]
        report_log = self.env['report.log'].search(partner_domain, limit=1, order='create_date desc')

        if not report_log:
            po_val = get_po_value()
            total_pay = get_payments()
            total_freight = get_total_freight()

            self.env['report.log'].create({
                'date_from': self.from_date,
                'date_to': self.to_date,
                'partner_id': self.partner_id.id,
                'po_value': po_val,
                'payments': total_pay,
                'opening_bal': 0.00,
                'closing_bal': (po_val + 0.00) - total_pay - total_freight,
            })
            return render_report()
        else:
            if (self.from_date > report_log.date_from) and (self.from_date > report_log.date_to):
                po_val = get_po_value()
                total_pay = get_payments()
                total_freight = get_total_freight()

                self.env['report.log'].create({
                    'date_from': self.from_date,
                    'date_to': self.to_date,
                    'partner_id': self.partner_id.id,
                    'po_value': po_val,
                    'payments': total_pay,
                    'opening_bal': report_log.closing_bal,
                    'closing_bal': (po_val + report_log.closing_bal) - total_pay - total_freight,
                })
                return render_report()
            else:
                raise ValidationError('Report that you are trying to generate has the dates that are being overlapped '
                                      'by already generated reports. Kindly, please try with other date range')


class ReportStore(models.TransientModel):
    _name = 'report.store'

    name = fields.Char(string='File Name', size=64)
    report = fields.Binary('Download File', filters='.xls', readonly=True)
