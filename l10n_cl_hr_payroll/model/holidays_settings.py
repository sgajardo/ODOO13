from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HolidaysSettings(models.Model):
    _name = 'holidays.settings'
    _description = 'Ajustes de Vacaciones'
    _order = 'valid_on desc'
    _rec_name = 'valid_on'

    valid_on = fields.Date('Válido desde', required=True, help='Indica desde qué fecha es válido esta configuración', default='1959-01-01')
    days_amount = fields.Integer('Días de vacaciones', required=True,
                                 help='Cantidad de días que se otorgan por año a los empleados para disfrute de vacaciones.', default=15)
    waiting_time = fields.Integer('Tiempo de antigüedad', required=True,
                                  help='Tiempo que debe tener el trabajador en su contrato para comenzar a acumular vacaciones, calculado en meses.')

    def toggle_cron(self):
        """ Activa o desactiva el cron """
        self.cron_active = not self.cron_active

    @property
    def last_waiting_time(self):
        """ Solo se calcula el tiempo de antigüedad en base al último registro
        cargado, por eso lo tomaremos desde ahí. """
        return self.search([], order='valid_on desc')[0].waiting_time

    @api.model
    def cron_asign_vacation_days(self):
        """ Asigna las vacaciones pendientes a cada empleado """
        today = fields.Date.today()
        vacaciones = self.env.ref('l10n_cl_hr_payroll.LC05')
        progresivas = self.env.ref('l10n_cl_hr_payroll.LC06')
        employees = self.env['hr.employee'].search([('active', '=', True), ('contract_ids', '!=', False)])
        holidays = self.env['hr.leave.allocation'].search([('employee_id', 'in', employees.ids),
                                                           ('state', '=', 'validate'), ('holiday_status_id', '=', vacaciones.id)])
        progressive_holidays = self.env['hr.leave.allocation'].search([('employee_id', 'in', employees.ids),
                                                                       ('state', '=', 'validate'), ('holiday_status_id', '=', progresivas.id)])

        # Primero creamos un listado de los periodos en las configuraciones
        first = today - relativedelta(years=100)
        last = today + relativedelta(years=100)
        i, periods = 0, []
        for setting in self.search([], order='valid_on'):
            if i == 0:
                periods.append({'start': first, 'days': setting.days_amount})
            else:
                periods.append({'start': setting.valid_on, 'days': setting.days_amount})
                periods[i - 1].update({'end': setting.valid_on - relativedelta(days=1)})
            i += 1
        periods[i - 1].update({'end': last})
        ids = []
        to_delete = self.env['hr.leave']  # Recordset vacío donde guardaremos los registros repetidos a eliminar
        for employee in employees:
            # Definimos desde cuando comienza a disfrutar las vacaciones, su fecha
            # de inicio mas los meses que debe esperar para empezar a disfrutar
            date_start = employee.contract_id.vacation_date_start or employee.contract_id.date_start
            if date_start >= today:
                # Ignoramos los que tengan fecha inicial mayor al día actual
                continue
            days = 0.0
            # Se calculan cuantos días de vacaciones debería tener el trabajador
            # desde que inició su relación laboral en la empresa
            for period in periods:
                start = period['start']
                end = period['end']
                if date_start >= end or today <= start:
                    # Si este caso se da, es porque no necesita calcular en este periodo
                    continue
                if date_start > start:
                    start = date_start
                contract_end = employee.contract_id.date_end
                if contract_end and contract_end < end and contract_end <= today:
                    end = contract_end
                elif today < end:
                    end = today
                rel_time = relativedelta(end + relativedelta(days=1), start)
                months = rel_time.months + rel_time.years * 12 + rel_time.days / 30.0
                days += period['days'] / 12.0 * months
            # Pasamos a actualizar las vacaciones, o crearlas si no existen
            employee_holidays = holidays.filtered_domain([('employee_id', '=', employee.id)])
            if len(employee_holidays) > 1:
                to_delete += employee_holidays - employee_holidays[0]
                employee_holidays = employee_holidays[0]
            if days <= 0:
                raise UserError(_('Verifique las fechas de vacaciones para %s.\nDías de vacaciones deben ser mayor a 0.') % employee.display_name)
            if employee_holidays:
                calculated_holiday = employee_holidays
                employee_holidays.write({
                    'number_of_days': days,
                    'name': 'Vacaciones pendientes de %s' % employee.display_name
                })
            else:
                calculated_holiday = holidays.create({
                    'employee_id': employee.id,
                    'state': 'validate',
                    'holiday_type': 'employee',
                    'holiday_status_id': vacaciones.id,
                    'number_of_days': days,
                    'name': 'Vacaciones pendientes de %s' % employee.display_name
                })
            ids.append(calculated_holiday.id)
            # Y y luego calculamos los días progresivos, si aplicara...
            employee_progressive_holidays = progressive_holidays.filtered_domain([('employee_id', '=', employee.id)])
            if len(employee_progressive_holidays) > 1:
                to_delete += employee_progressive_holidays - employee_progressive_holidays[0]
                employee_progressive_holidays = employee_progressive_holidays[0]
            progressive_days = self.calcular_progresivos(employee, employee_progressive_holidays)
            if progressive_days:
                if employee_progressive_holidays:
                    calculated_progressive = employee_progressive_holidays
                    calculated_progressive.write({
                        'number_of_days_display': progressive_days,
                    })
                else:
                    calculated_progressive = employee_progressive_holidays.create({
                        'employee_id': employee.id,
                        'state': 'validate',
                        'holiday_type': 'employee',
                        'holiday_status_id': progresivas.id,
                        'number_of_days_display': progressive_days,
                        'name': 'Vacaciones progresivas pendientes de %s' % employee.name
                    })
                ids.append(calculated_progressive.id)
        # Terminamos borrando los registros repetidos
        to_delete.write({'state': 'draft'})
        to_delete.unlink()
        if not ids:
            raise UserError(_('No se encontraron vacaciones pendientes'))
        return ids

    def calcular_progresivos(self, employee, employee_progressive_holidays=None):
        """ Se separa para hacer más fácil la herencia, solo debe devolver los
        registros duplicados a borrar en caso de haberlos """
        progressive_days = employee.contract_id.progressive_days
        if progressive_days:
            progressive_days += employee_progressive_holidays and employee_progressive_holidays.number_of_days_display or 0
            # Debemos llevar a 0 los días progresivos en el contrato del trabajador
            employee.contract_id.write({'progressive_days': 0})
        return progressive_days

    def action_asign_vacation_days(self):
        """ Ejecuta manualmente el cron desde la vista de configuración """
        ids = self.cron_asign_vacation_days()
        return {
            'name': _('Vacaciones calculadas'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.allocation',
            'domain': [('id', 'in', ids)],
            'view_mode': 'tree,form',
        }
