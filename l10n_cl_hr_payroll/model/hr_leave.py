from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrHolidaysStatus(models.Model):
    _inherit = 'hr.leave.type'

    move_type_id = fields.Many2one('hr.move.type', 'Tipo de Movimiento',
                                   help='Al crear una ausencia, se creará '
                                   'un Movimiento de Personal de este tipo')
    affects_payslip = fields.Boolean('Afecta Nómina', default=True,
                                     help='Si no está activo este campo, este'
                                     ' tipo de ausencias no afectará el pago '
                                     'de la nómina')
    extended = fields.Boolean('Corrido', help='Indica si este tipo de ausencia incluye feriados y días no laborables.', default=False)

    @api.model
    def update_hr_holidays_status(self):
        """ Método que se encarga de desactivar todos los tipos de ausencias
        que estén cargados en el sistema a la hora de instalar éste módulo,
        exceptuando los tipos cargados en la data de este módulo """
        ids = {getattr(self.env.ref('l10n_cl_hr_payroll.LC0%s' % i, raise_if_not_found=False), 'id', 0) for i in range(1, 7)}
        return self.search([('id', 'not in', list(ids))]).write({'active': False})


class HrHolidaysAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    date_from = fields.Date('Desde', readonly=True, index=True, copy=False, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    date_to = fields.Date('Hasta', readonly=True, index=True, copy=False, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    remaining_vacations = fields.Float('Días restantes', help='Días que puede consumir el empleado por concepto de vacaciones',
                                       compute='_compute_remaining_vacations')
    consumed_vacations = fields.Float('Días consumidos', help='Días que el trabajador ha tomado para gozar sus vacaciones',
                                      compute='_compute_consumed_vacations')
    consumed_vacations_count = fields.Float('Ausencias', compute='_compute_vacations_count')

    @api.depends('number_of_days_display')
    def _compute_consumed_vacations(self):
        """ Calcula los días que el trabajador ya ha consumido de vacaciones """
        leave_obj = self.env['hr.leave']
        contract_obj = self.env['hr.contract']
        for record in self:
            date_from = min(contract_obj.search([('employee_id', '=', record.employee_id.id)]).mapped('date_start'))
            date_to = record.employee_id.contract_id.date_end or fields.Date.today()
            record.consumed_vacations = sum(leave_obj.search([
                ('employee_id', '=', record.employee_id.id),
                ('state', '=', 'validate'),
                ('holiday_status_id', '=', record.holiday_status_id.id),
                ('date_to', '>=', date_from),
                ('date_from', '<=', date_to),
            ]).mapped('number_of_days_display'))

    @api.depends('number_of_days_display', 'consumed_vacations')
    def _compute_remaining_vacations(self):
        """ Calcula los días restantes de vacaciones, tomando en cuenta los días
        asignados menos los días ya tomados hasta la fecha """
        for record in self:
            record.remaining_vacations = record.number_of_days_display - record.consumed_vacations

    def _compute_vacations_count(self):
        """ Devuelve cuantas peticiones de ausencias por concepto de vacaciones
        ha hecho el trabajador """
        for record in self:
            record.consumed_vacations_count = self.search_count([
                ('employee_id', '=', record.employee_id.id),
                ('state', '=', 'validate'),
                ('holiday_status_id', '=', record.holiday_status_id.id)
            ])

    def vacation_days_taken(self):
        """ Devuelve vista con las vacaciones que ha pedido el trabajador """
        tree = self.env.ref('l10n_cl_hr_payroll.hr_holidays_vacations_taken_list').id
        form = self.env.ref('l10n_cl_hr_payroll.hr_holidays_vacations_taken_form').id
        ids = self.search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'validate'),
            ('holiday_status_id', '=', self.holiday_status_id.id)
        ]).mapped('id')
        return {
            'name': _('Vacaciones Tomadas'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave',
            'domain': [('id', 'in', ids)],
            'view_mode': 'tree,form',
            'views': [(tree, 'tree'), (form, 'form')]
        }

    @api.model
    def create(self, values):
        """ Se sobrecarga para evitar que se creen varios registros de
        vacaciones para un mismo empleado """
        if not values.get('name'):
            employee_name = self.env['hr.employee'].browse(values['employee_id']).display_name
            holiday_name = self.env['hr.leave.type'].browse(values['holiday_status_id']).name
            values.update({'name': 'Ausencia por %s para %s' % (holiday_name, employee_name)})
        vacaciones = self.env.ref('l10n_cl_hr_payroll.LC05')
        progresivas = self.env.ref('l10n_cl_hr_payroll.LC06')
        if values.get('holiday_status_id') in [vacaciones.id, progresivas.id] and values.get('type') == 'add':
            if values.get('holiday_type') == 'category':
                raise ValidationError(_('No se pueden crear vacaciones por '
                                        'categoría, solo por empleado.'))
            holidays = self.search([
                ('employee_id', '=', values['employee_id']),
                ('holiday_status_id', '=', values['holiday_status_id']),
            ])
            if holidays:
                raise ValidationError(_('Ya existe un registro de vacaciones para %s') % self.env['hr.employee'].browse(values['employee_id']).name)
        return super().create(values)


class HrHolidays(models.Model):
    _inherit = 'hr.leave'

    remaining_vacations = fields.Float('Días restantes', help='Días que puede consumir el empleado por concepto de vacaciones',
                                       compute='_compute_remaining_vacations')
    consumed_vacations = fields.Float('Días consumidos', help='Días que el trabajador ha tomado para gozar sus vacaciones',
                                      compute='_compute_consumed_vacations')

    @api.depends('number_of_days_display')
    def _compute_consumed_vacations(self):
        """ Calcula los días que el trabajador ya ha consumido de vacaciones """
        contract_obj = self.env['hr.contract']
        for record in self:
            date_from = min(contract_obj.search([('employee_id', '=', record.employee_id.id)]).mapped('date_start'))
            date_to = record.employee_id.contract_id.date_end or fields.Date.today()
            record.consumed_vacations = sum(self.search([
                ('employee_id', '=', record.employee_id.id),
                ('state', '=', 'validate'),
                ('holiday_status_id', '=', record.holiday_status_id.id),
                ('date_to', '>=', date_from),
                ('date_from', '<=', date_to),
            ]).mapped('number_of_days_display'))

    @api.depends('number_of_days_display', 'consumed_vacations')
    def _compute_remaining_vacations(self):
        """ Calcula los días restantes de vacaciones, tomando en cuenta los días
        asignados menos los días ya tomados hasta la fecha """
        for record in self:
            record.remaining_vacations = record.number_of_days_display - record.consumed_vacations

    # def action_approve(self):
    #     if self.holiday_status_id.move_type_id:
    #         self.env['hr.move'].create({
    #             'date_start': self.date_from,
    #             'date_end': self.date_to,
    #             'employee_id': self.employee_id.id,
    #             'tipo': self.holiday_status_id.move_type_id.id,
    #             'holiday_id': self.id
    #         })
    #     return super(HrHolidays, self).action_approve()

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ Se sobrecarga para agregar siempre 1 día, ya que el cálculo que
        hace omite el día inicial, además, se ignorarán los días feriados """
        if employee_id and not self.holiday_status_id.extended:
            return {'days': self.env['hr.employee'].browse(employee_id).get_worked_days_count(date_from, date_to), 'hours': 0}
        dt_from, dt_to = map(fields.Date.from_string, [date_from, date_to])
        return {'days': relativedelta(dt_to, dt_from).days + 1, 'hours': 0}

    def print_vacation_report(self):
        return self.env.ref('l10n_cl_hr_payroll.certificado_vacaciones_report').report_action(self)
