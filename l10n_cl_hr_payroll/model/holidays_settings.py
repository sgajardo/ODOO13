# coding: utf-8
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HolidaysSettings(models.Model):
    _name = 'holidays.settings'
    _description ='Ajustes de Vacaciones'
    _order = 'valid_on desc'
    _rec_name = 'valid_on'

    def get_cron(self):
        u""" Busca el cron que se designó para vacaciones y lo coloca por
        default para todas las configuraciones de vacaciones """
        cron = self.env.ref('l10n_cl_hr_payroll.vacation_assigment_cron', raise_if_not_found=False)
        for record in self:
            record.cron_id = cron

    cron_id = fields.Many2one('ir.cron', compute=get_cron)
    cron_active = fields.Boolean(related='cron_id.active')
    valid_on = fields.Date(u'Válido desde', required=True, help=u'Indica desde qué fecha es válido esta configuración', default='1959-01-01')
    days_amount = fields.Integer(u'Días de vacaciones', required=True,
                                 help=u'Cantidad de días que se otorgan por año a los empleados para disfrute de vacaciones.', default=15)
    waiting_time = fields.Integer(u'Tiempo de antigüedad', required=True,
                                  help=u'Tiempo que debe tener el trabajador en su contrato para comenzar a acumular vacaciones, calculado en meses.')

    def toggle_cron(self):
        u""" Activa o desactiva el cron """
        self.cron_active = not self.cron_active

    @property
    def last_waiting_time(self):
        u""" Solo se calcula el tiempo de antigüedad en base al último registro
        cargado, por eso lo tomaremos desde ahí. """
        return self.search([], order='valid_on desc')[0].waiting_time

    @api.model
    def cron_asign_vacation_days(self):
        u""" Asigna las vacaciones pendientes a cada empleado """
        to_date = fields.Date.from_string
        to_str = fields.Date.to_string
        today = to_date(fields.Date.today())
        months_waiting = relativedelta(months=self.last_waiting_time)
        vacaciones = self.env.ref('l10n_cl_hr_payroll.LC05')
        progresivas = self.env.ref('l10n_cl_hr_payroll.LC06')
        employees = self.env['hr.employee'].search([('active', '=', True), ('contract_ids', '!=', False)])
        # employees = employees.filtered(lambda e: (not e.contract_id.date_end or e.contract_id.date_end > to_str(today)) and
        #                                (e.contract_id.vacation_date_start or e.contract_id.date_start) < to_str(today - months_waiting) or
        #                                e.contract_id.progressive_days)
        holidays = self.env['hr.holidays'].search([('type', '=', 'add'), ('employee_id', 'in', employees.ids),
                                                   ('state', '=', 'validate'), ('holiday_status_id', '=', vacaciones.id)])
        progressive_holidays = self.env['hr.holidays'].search([('type', '=', 'add'), ('employee_id', 'in', employees.ids),
                                                               ('state', '=', 'validate'), ('holiday_status_id', '=', progresivas.id)])

        # Primero creamos un listado de los periodos en las configuraciones
        first = today - relativedelta(years=100)
        last = today + relativedelta(years=100)
        i, periods = 0, []
        for setting in self.search([], order='valid_on'):
            if i == 0:
                periods.append({'start': to_str(first), 'days': setting.days_amount})
            else:
                periods.append({'start': setting.valid_on, 'days': setting.days_amount})
                periods[i - 1].update({'end': to_str(to_date(setting.valid_on) - relativedelta(days=1))})
            i += 1
        periods[i - 1].update({'end': to_str(last)})
        ids = []
        to_delete = self.env['hr.holidays']  # Recordset vacío donde guardaremos los registros repetidos a eliminar
        for employee in employees:
            # Definimos desde cuando comienza a disfrutar las vacaciones, su fecha
            # de inicio mas los meses que debe esperar para empezar a disfrutar
            date_start = to_date(employee.contract_id.vacation_date_start or employee.contract_id.date_start)
            if date_start >= today:
                # Ignoramos los que tengan fecha inicial mayor al día actual
                continue
            days = 0.0
            # Se calculan cuantos días de vacaciones debería tener el trabajador
            # desde que inició su relación laboral en la empresa
            for period in periods:
                start = to_date(period['start'])
                end = to_date(period['end'])
                if date_start >= end or today <= start:
                    # Si este caso se da, es porque no necesita calcular en este periodo
                    continue
                if date_start > start:
                    start = date_start
                contract_end = to_date(employee.contract_id.date_end)
                if contract_end and contract_end < end and contract_end <= today:
                    end = contract_end
                elif today < end:
                    end = today
                rel_time = relativedelta(end + relativedelta(days=1), start)
                months = rel_time.months + rel_time.years * 12 + rel_time.days / 30.0
                days += period['days'] / 12.0 * months
            # Pasamos a actualizar las vacaciones, o crearlas si no existen
            employee_holidays = holidays.filtered(lambda h: h.employee_id.id == employee.id)
            if len(employee_holidays) > 1:
                to_delete += employee_holidays - employee_holidays[0]
                employee_holidays = employee_holidays[0]
            if days <= 0:
                raise UserError(_('Verifique las fechas de vacaciones para %s.\nDías de vacaciones deben ser mayor a 0.') % employee.display_name)
            if employee_holidays:
                calculated_holiday = employee_holidays
                employee_holidays.write({
                    'number_of_days_temp': days,
                    'name':'Vacaciones pendientes de %s' % employee.name
                })
            else:
                calculated_holiday = holidays.create({
                    'employee_id': employee.id,
                    'type': 'add',
                    'state': 'validate',
                    'holiday_type': 'employee',
                    'holiday_status_id': vacaciones.id,
                    'number_of_days_temp': days,
                    'name':'Vacaciones pendientes de %s' % employee.name
                })
            ids.append(calculated_holiday.id)
            # Y y luego calculamos los días progresivos, si aplicara...
            employee_progressive_holidays = progressive_holidays.filtered(lambda h: h.employee_id.id == employee.id)
            if len(employee_progressive_holidays) > 1:
                to_delete += employee_progressive_holidays - employee_progressive_holidays[0]
                employee_progressive_holidays = employee_progressive_holidays[0]
            progressive_days = self.calcular_progresivos(employee, employee_progressive_holidays)
            if progressive_days:
                if employee_progressive_holidays:
                    calculated_progressive = employee_progressive_holidays
                    calculated_progressive.write({
                        'number_of_days_temp': progressive_days,
                    })
                else:
                    calculated_progressive = employee_progressive_holidays.create({
                        'employee_id': employee.id,
                        'type': 'add',
                        'state': 'validate',
                        'holiday_type': 'employee',
                        'holiday_status_id': progresivas.id,
                        'number_of_days_temp': progressive_days,
                        'name':'Vacaciones progresivas pendientes de %s' % employee.name
                    })
                ids.append(calculated_progressive.id)
        # Terminamos borrando los registros repetidos
        to_delete.write({'state': 'draft'})
        to_delete.unlink()
        if not ids:
            raise UserError(_(u'No se encontraron vacaciones pendientes'))
        return ids

    def calcular_progresivos(self, employee, employee_progressive_holidays=None):
        u""" Se separa para hacer más fácil la herencia, solo debe devolver los
        registros duplicados a borrar en caso de haberlos """
        progressive_days = employee.contract_id.progressive_days
        if progressive_days:
            progressive_days += employee_progressive_holidays and employee_progressive_holidays.number_of_days_temp or 0
            # Debemos llevar a 0 los días progresivos en el contrato del trabajador
            employee.contract_id.write({'progressive_days': 0})
        return progressive_days

    def action_asign_vacation_days(self):
        u""" Ejecuta manualmente el cron desde la vista de configuración """
        ids = self.cron_asign_vacation_days()
        return {
            'name': _(u'Vacaciones calculadas'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.holidays',
            'domain': [('id', 'in', ids)],
            'view_mode': 'tree,form',
        }
