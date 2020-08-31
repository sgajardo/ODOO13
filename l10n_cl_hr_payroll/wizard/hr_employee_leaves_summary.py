import base64
from calendar import monthrange
from cStringIO import StringIO

import xlwt

from odoo import api, fields, models


class HrEmployeeLeavesSummary(models.TransientModel):
    _name = 'hr.employee.leaves.summary'
    _description = 'Reporte de ausencias'

    @api.model
    def default_get(self, def_fields):
        res = super(HrEmployeeLeavesSummary, self).default_get(def_fields)
        year, month = map(int, fields.Date.today().split('-')[:2])
        res['date_from'] = '%d-%.2d-01' % (year, month)
        res['date_to'] = '%d-%.2d-%.2d' % (year, month, monthrange(year, month)[-1])
        employee_ids = self.env.context.get('active_ids')
        if self.env.context.get('active_model') == 'hr.employee':
            res['employee_ids'] = [(6, 0, employee_ids)]
        return res

    date_from = fields.Date('Desde', required=True)
    date_to = fields.Date('Hasta', required=True)
    employee_ids = fields.Many2many('hr.employee', string='Empleados')

    @api.onchange('date_from')
    def _onchange_dates(self):
        if self.date_from:
            year, month = map(int, self.date_from.split('-')[:2])
            self.date_to = '%d-%.2d-%.2d' % (year, month, monthrange(year, month)[-1])

    def print_xls(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        style_title = xlwt.easyxf('font: height 200; font: name Liberation Sans, bold on, color black; align: horiz center;')
        style_header = xlwt.easyxf('font: height 200; font: name Liberation Sans, bold on, color black; align: horiz center; align: vertical center; pattern: pattern solid, fore_colour silver_ega;')
        style_center = xlwt.easyxf('font: height 200; font: name Liberation Sans, color black; align: horiz center;')
        date_format = xlwt.easyxf('font: height 200; font: name Liberation Sans, bold on, color black; align: horiz center;', num_format_str='dd/mm/yyyy')
        style_currency = xlwt.easyxf('font: height 200; align: wrap yes, horiz right;', num_format_str='$#0')
        style_currency_bold = xlwt.easyxf('font: height 200; font: name Liberation Sans, bold on, color black; align: wrap yes, horiz right;', num_format_str='$#0')
        payslips = self.env['hr.payslip'].search([('date_from', '<=', self.date_to), ('date_to', '>=', self.date_from), ('employee_id', 'in', self.employee_ids.ids)])
        licencia_id = self.env.ref('l10n_cl_hr_payroll.LC02')
        # Escribimos cabeceras
        worksheet = workbook.add_sheet('Ausencias')
        worksheet.write_merge(1, 1, 0, 8, 'Reporte de Ausencias', style_title)
        worksheet.write_merge(1, 1, 9, 10, fields.Date.from_string(self.date_from), date_format)
        worksheet.write_merge(1, 1, 11, 12, fields.Date.from_string(self.date_to), date_format)
        worksheet.write(3, 0, 'RUT', style_header)
        worksheet.write(3, 1, 'Nombre Completo', style_header)
        worksheet.write(3, 2, 'Horas\nExtras\n50%', style_header)
        worksheet.write(3, 3, 'Monto\nHoras\n50%', style_header)
        worksheet.write(3, 4, 'Horas\nExtras\n100%', style_header)
        worksheet.write(3, 5, 'Monto\nHoras\n100%', style_header)
        worksheet.write(3, 6, 'Horas\nDomingo', style_header)
        worksheet.write(3, 7, 'Monto\nHoras\nDomingo', style_header)
        worksheet.write(3, 8, 'TOTAL\nHORAS\nEXTRAS', style_header)
        worksheet.write(3, 9, 'MONTO\nTOTAL\nHE', style_header)
        worksheet.write(3, 10, 'Licencias', style_header)
        worksheet.write(3, 11, 'Sin\nLicencias', style_header)
        worksheet.write(3, 12, 'TOTAL\nAusencias', style_header)
        # Ajustamos la anchura de las cabeceras
        worksheet.row(3).height_mismatch = True
        worksheet.row(3).height = 256 * 3
        worksheet.col(1).width = 256 * 40
        worksheet.col(2).width = 256 * 10
        worksheet.col(3).width = 256 * 14
        worksheet.col(4).width = 256 * 10
        worksheet.col(5).width = 256 * 14
        worksheet.col(6).width = 256 * 10
        worksheet.col(7).width = 256 * 14
        worksheet.col(8).width = 256 * 10
        worksheet.col(9).width = 256 * 14
        worksheet.col(10).width = 256 * 10
        worksheet.col(11).width = 256 * 10
        worksheet.col(12).width = 256 * 10
        # Iteramos por empleado
        total_line = 4
        for i, employee in enumerate(self.employee_ids, 4):
            worksheet.write(i, 0, employee.identification_id or '')
            worksheet.write(i, 1, employee.full_name)
            # Buscamos las horas extras
            haberes = employee.balance_ids.filtered(lambda hyd: hyd.date_from <= self.date_to and (hyd.date_to >= self.date_from or not hyd.date_to))
            hex_total = sum(haberes.filtered(lambda hyd: hyd.name.inputs_id.code == 'HEX').mapped('monto'))
            hex100_total = sum(haberes.filtered(lambda hyd: hyd.name.inputs_id.code == 'HEX100').mapped('monto'))
            hxd_total = sum(haberes.filtered(lambda hyd: hyd.name.inputs_id.code == 'HXD').mapped('monto'))
            worksheet.write(i, 2, hex_total, style_center)
            worksheet.write(i, 4, hex100_total, style_center)
            worksheet.write(i, 6, hxd_total, style_center)
            worksheet.write(i, 8, xlwt.Formula('C{0}+E{0}+G{0}'.format(i + 1)), style_center)
            # Buscamos los montos de horas extras
            emp_payslips = payslips.filtered(lambda p: p.employee_id == employee)
            hex_amount = sum(emp_payslips.mapped('line_ids').filtered(lambda l: l.code == 'HEX').mapped('total'))
            hex100_amount = sum(emp_payslips.mapped('line_ids').filtered(lambda l: l.code == 'HEX100').mapped('total'))
            hxd_amount = sum(emp_payslips.mapped('line_ids').filtered(lambda l: l.code == 'HXD').mapped('total'))
            worksheet.write(i, 3, hex_amount, style_currency)
            worksheet.write(i, 5, hex100_amount, style_currency)
            worksheet.write(i, 7, hxd_amount, style_currency)
            worksheet.write(i, 9, xlwt.Formula('D{0}+F{0}+H{0}'.format(i + 1)), style_currency)
            # Buscamos las ausencias
            leaves = employee.leave_ids.filtered(lambda l: l.type == 'remove')
            licencias = sum(leaves.filtered(lambda l: l.holiday_status_id == licencia_id).mapped('number_of_days_display'))
            sin_licencias = sum(leaves.filtered(lambda l: l.holiday_status_id != licencia_id).mapped('number_of_days_display'))
            worksheet.write(i, 10, licencias, style_center)
            worksheet.write(i, 11, sin_licencias, style_center)
            worksheet.write(i, 12, xlwt.Formula('K{0}+L{0}'.format(i + 1)), style_center)
            total_line += 1
        # Totalizamos
        worksheet.write_merge(total_line, total_line, 0, 1, 'TOTAL', style_title)
        for j, cel in enumerate('CDEFGHIJKLM', 2):
            if cel in 'DFHJ':
                continue
            if total_line != 4:
                worksheet.write(total_line, j, xlwt.Formula('SUM({0}4:{0}{1})'.format(cel, total_line)), style_title)
        for j, cel in enumerate('CDEFGHIJKLM', 2):
            if cel not in 'DFHJ':
                continue
            if total_line != 4:
                worksheet.write(total_line, j, xlwt.Formula('SUM({0}4:{0}{1})'.format(cel, total_line)), style_currency_bold)

        tmp = StringIO()
        workbook.save(tmp)
        tmp.seek(0)
        data = base64.encodestring(tmp.read())
        tmp.close()
        attach_vals = {
            'name': 'reporte_ausencias.xls',
            'datas': data,
            'datas_fname': 'reporte_ausencias.xls',
        }
        doc_id = self.env['ir.attachment'].create(attach_vals)
        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=ir.attachment&id={id}&field=datas'
                   '&filename_field=datas_fname&download=true&filename={name}'
                   .format(id=doc_id.id, name=doc_id.name),
            'target': 'new',
        }
