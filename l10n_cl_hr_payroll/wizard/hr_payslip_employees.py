# coding: utf-8
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def compute_sheet(self):
        payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id', 0)).exists()
        # Si existe otro procesamiento de nómina con el mismo empleado dentro del mismo periodo, lanzamos un raise
        repeat = self.env['hr.payslip'].search([('employee_id', 'in', self.employee_ids.ids), ('date_from', '<=', payslip_run.date_end), ('date_to', '>=', payslip_run.date_start)], limit=1)
        if repeat:
            raise ValidationError(u'La nómina de "%s" ya está siendo calculada en el procesamiento "%s".' % (repeat.employee_id.display_name, repeat.payslip_run_id.name))
        # Dejamos que continúe normalmente su trabajo
        return super(HrPayslipEmployees, self).compute_sheet()
