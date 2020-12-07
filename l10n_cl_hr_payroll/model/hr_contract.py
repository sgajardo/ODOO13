from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    date_start = fields.Date(tracking=True)
    date_end = fields.Date(tracking=True)
    complete_name = fields.Char('Nombre completo', related='employee_id.display_name')
    last_name = fields.Char(related='employee_id.last_name')
    struct_id = fields.Many2one('hr.payroll.structure', default=lambda self: self.env.ref('l10n_cl_hr_payroll.hr_struct_cl', raise_if_not_found=False))
    type_id = fields.Many2one('hr.contract.type', 'Tipo de Contrato', default=lambda self: self.env.ref('l10n_cl_hr_payroll.hr_contract_type_not_defined', raise_if_not_found=False))
    parent_id = fields.Many2one('hr.contract', 'Anexado a', tracking=True)
    child_ids = fields.One2many('hr.contract', 'parent_id', 'Anexos', copy=False)
    account_analytic_account_id = fields.Many2one('account.analytic.account', 'Cuenta Analítica')
    # date_exp = fields.Date(tracking=True, string='Fecha Vencimiento', compute='_compute_giveme_date_exp')
    rut = fields.Char(related='employee_id.identification_id')
    use_mid_wage = fields.Boolean('Usar salario promedio para asignación familiar')
    mid_wage = fields.Monetary('Salario promedio')

    # @api.depends('type_id')
    # def _compute_giveme_date_exp(self):
    #     for record in self:
    #         if record.type_id and 'Indefinido' not in record.type_id.name:
    #             record.date_exp = record.date_start + relativedelta(months=3)

    # Campos para vacaciones
    vacation_date_start = fields.Date('Fecha Inicial de Cálculo',
                                      help='Fecha desde la que se empezará a '
                                      'tomar en cuenta el cálculo de sus vacaciones. '
                                      'Si no se indica, se tomará la fecha inicial'
                                      ' de este contrato.', tracking=True)
    progressive_days = fields.Float('Días progresivos', default=0.0,
                                    help='Días que se otorgan anualmente como'
                                    ' vacaciones extras por antigüedad. Los días'
                                    ' que se carguen acá serán asignados automáticamente'
                                    ' por la acción planificada y volverán ser llevados'
                                    ' a cero una vez ejecutada la misma.', tracking=True)

    @api.constrains('vacation_date_start')
    def _check_vacation_start(self):
        today = fields.Date.today()
        for record in self:
            if record.vacation_date_start and record.vacation_date_start > today:
                raise ValidationError(_('Fecha inicial de vacaciones no puede ser mayor al día de hoy.'))

    @api.onchange('employee_id')
    def _onchange_employee_anexo(self):
        return {
            'value': {
                'parent_id': False
            }
        }

    def _get_work_hours(self, date_from, date_to):
        work_hours = super()._get_work_hours(date_from, date_to)
        wet_leaves_ids = self.env['hr.work.entry.type'].search([('is_leave', '=', True)]).ids
        if self.resource_calendar_id:
            # Si el tipo de contrato es Sueldo Diario Pactado, se calcula los días trabajables en el periodo
            if self.type_id.codigo in ['diario', 'diariof']:
                wdf = date_from if date_from >= self.date_start else self.date_start
                wdt = date_to if (not self.date_end or date_to <= self.date_end) else self.date_end
                nod = self.employee_id.get_workable_days_count(wdf, wdt)
            # Si el contrato empieza antes del periodo de nómina y termina después del periodo de nómina: 30 días
            elif self.date_start <= date_from and (not self.date_end or self.date_end >= date_to):
                nod = 30.0
            # Si el contrato empieza después del periodo de nómina y termina después del periodo: 31 - día que comenzó el contrato
            elif self.date_start > date_from and (not self.date_end or self.date_end >= date_to):
                nod = 31.0 - self.date_start.day
            # Si el contrato empieza antes del periodo de nómina y termina antes del periodo: día en que termina el contrato
            elif self.date_start <= date_from and (self and self.date_end < date_to):
                nod = self.date_end.day
            # Si el contrato empieza después y termina antes del periodo de nómina: días entre el periodo del contrato
            else:
                nod = (self.date_end - self.date_start).days + 1
            attendance_entry_id = self.env.ref('hr_work_entry.work_entry_type_attendance').id
            total_hours = nod * self.resource_calendar_id.hours_per_day
            leave_hours = sum(hours for wet_id, hours in work_hours.items() if wet_id in wet_leaves_ids)
            for work_entry_type_id in work_hours:
                if work_entry_type_id == attendance_entry_id:
                    work_hours[work_entry_type_id] = total_hours - leave_hours
        return work_hours
