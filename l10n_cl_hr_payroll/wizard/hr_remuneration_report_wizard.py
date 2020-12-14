import base64
import csv
import io
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrRemunerationReportWizard(models.TransientModel):
    _name = 'hr.remuneration.report.wizard'
    _description = 'Informe Remuneracion'

    @api.model
    def _get_default_start_date(self):
        return fields.Date.today() + relativedelta(day=1)

    @api.model
    def _get_default_end_date(self):
        return fields.Date.today() + relativedelta(months=1, day=1, days=-1)

    start_date = fields.Date(string='Fecha Inicio', default=_get_default_start_date, help="Ingrese la fecha inicio del periodo")
    end_date = fields.Date(string='Fecha Fin', default=_get_default_end_date, help="Ingrese la fecha fin del periodo")
    account_analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de costo')
    type_delimitador = fields.Selection([(';', 'Punto y Coma'),
                                         (',', 'Coma')],
                                        'Tipo de Delimitador', size=1, default=';')

    @api.onchange('start_date')
    def _onchange_dates(self):
        if self.start_date:
            self.end_date = self.start_date + relativedelta(months=1, day=1, days=-1)

    def get_total_worked_days(self, payslip):
        work100 = payslip.worked_days_line_ids.filtered(lambda w: w.work_entry_type_id.code == 'WORK100')
        return work100.number_of_days

    def get_rule_value(self, code=None, payslip_id=None, emp_id=None, date_from=None, date_to=None):
        sql = """select COALESCE(sum(pl.total),0) from hr_payslip_line as pl
                left join hr_payslip as p on pl.slip_id = p.id
                where 1 = 1"""

        if payslip_id:
            sql += " and p.id = %s" % payslip_id

        if emp_id:
            sql += " and p.employee_id = %s" % emp_id

        if date_from:
            sql += " and p.date_from >= %s" % date_from

        if date_to:
            sql += " and p.date_to <= %s" % date_to

        if code:
            sql += " and pl.code = '%s' " % code

        self.env.cr.execute(sql)

        results = self.env.cr.fetchone()

        if results:
            return results[0]
        else:
            return 0

    def get_input_value(self, code=None, payslip_id=None, emp_id=None, date_from=None, date_to=None):
        sql = """ select COALESCE(sum(pl.amount),0) from hr_payslip_input as pl
                left join hr_payslip as p on pl.payslip_id = p.id
                left join hr_payslip_input_type as t on t.id = pl.input_type_id
                where 1 = 1"""

        if payslip_id:
            sql += " and p.id = %s" % payslip_id

        if emp_id:
            sql += " and p.employee_id = %s" % emp_id

        if date_from:
            sql += " and p.date_from >= %s" % date_from

        if date_to:
            sql += " and p.date_to <= %s" % date_to

        if code:
            sql += " and t.code = '%s' " % code

        self.env.cr.execute(sql)

        results = self.env.cr.fetchone()

        if results:
            return results[0]
        else:
            return 0

    def print_txt(self):
        payslips = self.env['hr.payslip'].search([
            ('date_to', '>=', self.start_date),
            ('date_from', '<=', self.end_date),
            ('contract_id.account_analytic_account_id', '=?', self.account_analytic_account_id.id)
        ])
        if not payslips:
            raise ValidationError('No existen recibos de pago validados para este periodo')
        fname = 'odoo-informe-remuneracion-%s.csv' % self.end_date.strftime('%m-%d')

        txt_file = io.StringIO()
        writer = csv.writer(txt_file, delimiter=str(self.type_delimitador), quoting=csv.QUOTE_NONE)
        row = ['RUT', 'NOMBRE', 'CENTRO COSTOS', 'AFP', 'SALUD', 'CARGO', 'DIAS', 'S. BASE', 'S. MES', 'No. HORAS EXTRAS (50%)', 'MONTO HORAS EXTRAS 50%',
               'No. HORAS EXTRAS (100%)', 'MONTO HORAS EXTRAS 100%', 'TOTAL HABERES', 'ALCANCE LIQUIDO', 'TOTAL NO IMPONIBLES',
               'TOTAL DESCUENTOS LEGALES', 'TOTAL OTROS DESCUENTOS ', 'TOTAL DESCUENTOS', 'TOTAL COSTO EMPRESA', 'TOTAL IMPONIBLE']
        rules = self.env['hr.salary.rule'].browse()
        for categ in ['IMPONIBLE', 'NOIMPO', 'DED', 'ODESC', 'COMP', 'PREV', 'SALUD']:
            rules += rules.search([('struct_id', '=', self.env.ref('l10n_cl_hr_payroll.hr_struct_cl').id), ('category_id.code', '=', categ),
                                   ('code', 'not in', ['SUELDO', 'HEX', 'HEX100'])])
        # Saltar la gratificación legal que se repite
        grat_dupe = self.env.ref('l10n_cl_hr_payroll.hr_rule_6', raise_if_not_found=True)

        for rule in rules:
            if rule == grat_dupe:
                # Nos saltamos la gratificación legal repetida.
                continue
            row.insert(-8, rule.name.upper())
        writer.writerow(row)

        for p in payslips:
            emp = p.employee_id
            complete_name = '%s %s %s %s' % (emp.last_name and emp.last_name or '', emp.mothers_name and emp.mothers_name or '', emp.first_name and emp.first_name or '', emp.middle_name and emp.middle_name or '')

            row = [
                emp.identification_id, complete_name, emp.contract_id.account_analytic_account_id.name or '',
                # AFP
                emp.afp_id.display_name if not emp.no_afp and emp.afp_id else '',
                # Salud
                emp.isapre_id.display_name if not emp.no_salud and emp.isapre_id else '',
                # Cargo
                emp.contract_id.job_id.display_name or '',
                # Dias
                int(self.get_total_worked_days(p)),
                # Sueldo Base
                int(self.get_rule_value('SUELDO', p.id)),
                # Sueldo del mes (Base menos DDNT)
                int(self.get_rule_value('SUELDO', p.id)) + int(self.get_rule_value('DDNT', p.id)),
                # No. Horas Extras 50%
                int(self.get_input_value('HEX', p.id)),
                # Monto Horas Extras 50%
                int(self.get_rule_value('HEX', p.id)),
                # No. Horas Extras 100%
                int(self.get_input_value('HEX100', p.id)),
                # Monto Horas Extras 100%
                int(self.get_rule_value('HEX100', p.id)),
                # Total haberes
                int(self.get_rule_value('HAB', p.id)),
                int(self.get_rule_value('LIQ', p.id)),
                int(self.get_rule_value('TOTNOI', p.id)),
                int(self.get_rule_value('TODELE', p.id)),
                int(self.get_rule_value('TOD', p.id)),
                int(self.get_rule_value('TDE', p.id)),
                int(self.get_rule_value('HAB', p.id) + self.get_rule_value('SIS', p.id) + self.get_rule_value('MUT', p.id) + self.get_rule_value('TRABPES', p.id)),
                # Total imponible
                int(self.get_rule_value('TOTIM', p.id)),
            ]
            for rule in rules:
                if rule == grat_dupe:
                    # Nos saltamos la gratificación legal repetida.
                    continue
                row.insert(-8, int(self.get_rule_value(rule.code, p.id)))
            writer.writerow(row)
        data = base64.b64encode(txt_file.getvalue().encode('utf-8'))
        txt_file.close()
        attach_vals = {'name': fname, 'datas': data, 'store_fname': fname}
        attachment = self.env['ir.attachment'].create(attach_vals)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new'
        }
