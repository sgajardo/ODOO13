from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import ValidationError, RedirectWarning


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    account_analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de costo')

    @api.onchange('account_analytic_account_id')
    def _onchange_analytic_account(self):
        employees = self.env['hr.contract'].search([('account_analytic_account_id', '=?', self.account_analytic_account_id.id)]).mapped('employee_id')
        return {
            'value': {
                'employee_ids': [(6, 0, employees.ids)]
            },
            'domain': {
                'employee_ids': [('id', 'in', employees.ids)]
            }
        }

    def compute_sheet(self):
        payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id', 0)).exists()
        # Si existe otro procesamiento de nómina con el mismo empleado dentro del mismo periodo, lanzamos un raise
        repeat = self.env['hr.payslip'].search([('employee_id', 'in', self.employee_ids.ids), ('date_from', '<=', payslip_run.date_end), ('date_to', '>=', payslip_run.date_start)], limit=1)
        if repeat:
            raise ValidationError('La nómina de "%s" ya está siendo calculada en el procesamiento "%s".' % (repeat.employee_id.display_name, repeat.payslip_run_id.name))
        # Dejamos que continúe normalmente su trabajo
        stats_id = False
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'hr.payslip.run':
            stats_id = self.env['hr.payslip.run'].browse(self.env.context.get('active_id')).stats_id.id
        if not stats_id:
            stats = self.env['hr.stats'].search([], limit=1, order='id desc')
            action = self.env.ref('l10n_cl_hr_payroll.hr_stats_previsionales_action', raise_if_not_found=False)
            if not stats and action:
                raise RedirectWarning('No se han cargado los indicadores Previred, ¿desea crearlos ahora?', action.id, 'Crear indicadores previred')
            elif not stats:
                raise ValidationError('No se han cargado los indicadores Previred')
            stats_id = stats.id
        payslip_run.account_analytic_account_id = self.account_analytic_account_id
        # Borramos las entradas del periodo
        self.env['hr.work.entry'].search([
            ('employee_id', 'in', self.employee_ids.ids),
            ('date_start', '>=', datetime.combine(payslip_run.date_start, datetime.min.time())),
            ('date_stop', '<=', datetime.combine(payslip_run.date_end, datetime.max.time())),
        ]).unlink()
        contracts = self.employee_ids._get_contracts(payslip_run.date_start, payslip_run.date_end, states=['open', 'close'])
        date_generated = datetime.combine(payslip_run.date_start, datetime.min.time())
        contracts.write({'date_generated_from': date_generated, 'date_generated_to': date_generated})
        return super(HrPayslipEmployees, self.with_context(default_stats_id=stats_id)).compute_sheet()
