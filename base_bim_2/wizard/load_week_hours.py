# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta


class LoadWeekHours(models.TransientModel):
    _name = "load.week.hours"
    _description = 'Carga de Horas Semanales'

    @api.model
    def default_get(self, fields):
        res = super(LoadWeekHours, self).default_get(fields)
        today = date.today()
        res['week_date'] = datetime.strftime((today - timedelta(days=today.weekday())), '%Y-%m-%d')
        context = self._context
        project = self.env['bim.project'].browse(context['active_id'])
        lines = []
        working_hours = self.env.user.company_id.working_hours
        for line in project.employee_line_ids:
            lines.append([0, 0, {
                'employee_id': line.employee_id.id,
                'hours1': working_hours,
                'extra1': 0,
                'hours2': working_hours,
                'extra2': 0,
                'hours3': working_hours,
                'extra3': 0,
                'hours4': working_hours,
                'extra4': 0,
                'hours5': working_hours,
                'extra5': 0,
                'hours6': 0,
                'hours7': 0,
            }])
        res['line_ids'] = lines
        res = self._convert_to_write(res)
        return res

    week_date = fields.Date('Lunes de la Semana',
        help="Ingrese la fecha del lunes de la semana a la cual desea cargar las horas")
    line_ids = fields.One2many('load.week.hours.line','wizard_id','Líneas')

    def load_hours(self):
        context = self._context
        today = date.today()
        project = self.env['bim.project'].browse(context['active_id'])
        working_hours = self.env.user.company_id.working_hours
        project_timesheet = self.env['bim.project.employee.timesheet']
        year = self.week_date.year
        month = self.week_date.month
        day = self.week_date.day
        week_number = date(int(year), int(month), int(day)).strftime("%V")
        week_date = datetime.strptime(str(self.week_date), '%Y-%m-%d')
        start = datetime.strptime(str(self.week_date), '%Y-%m-%d') - timedelta(days=week_date.weekday())
        for line in self.line_ids:
            values = line.get_hours_line_data()
            total = line.hours1 + line.hours2 + line.hours3 + line.hours4 + line.hours5
            total_extra = line.extra1 + line.extra2 + line.extra3 + line.extra4 + line.extra5 + line.hours6 + line.hours7
            timesheets = project_timesheet.search([
                ('employee_id','=',values['employee_id']),
                ('week_number','=',week_number)
            ])
            ts_hours = sum(x.total_hours for x in timesheets)
            if (ts_hours + total) > 45:
                raise ValidationError('No es posible cargar mas de 45 horas en la misma semana al empleado %s. Esta intentando cargarle %dh y actualmente posee %dh cargadas para la semana del %s/%s/%s'%(line.employee_id.name, total, ts_hours, day, month, year))
            existing_timesheet = timesheets.filtered(lambda r: r.project_id.id == project.id)
            if existing_timesheet:
                existing_timesheet.write({
                    'total_hours': total,
                    'total_extra_hours': total_extra,
                })
            else:
                project_timesheet.create({
                    'employee_id': values['employee_id'],
                    'date': self.week_date,
                    'week_start': datetime.strftime(start, '%Y-%m-%d'),
                    'week_end': datetime.strftime((start + timedelta(days=6)), '%Y-%m-%d'),
                    'total_hours': total,
                    'total_extra_hours': total_extra,
                    'project_id': project.id
                })
        return True


class LoadWeekHoursLine(models.TransientModel):
    _name = "load.week.hours.line"
    _description = 'Detalles de Carga de Horas Semanales'

    wizard_id = fields.Many2one('load.week.hours', 'Wizard')
    employee_id = fields.Many2one('hr.employee', 'Empleado')
    hours1 = fields.Float('Lunes')
    hours2 = fields.Float('Martes')
    hours3 = fields.Float('Miércoles')
    hours4 = fields.Float('Jueves')
    hours5 = fields.Float('Viernes')
    hours6 = fields.Float('Sábado')
    hours7 = fields.Float('Domingo')
    extra1 = fields.Float('Lunes Extra')
    extra2 = fields.Float('Martes Extra')
    extra3 = fields.Float('Miércoles Extra')
    extra4 = fields.Float('Jueves Extra')
    extra5 = fields.Float('Viernes Extra')

    def get_hours_line_data(self):
        self.ensure_one()
        return {
            'employee_id': self.employee_id.id,
            'hours1': self.hours1,
            'hours2': self.hours2,
            'hours3': self.hours3,
            'hours4': self.hours4,
            'hours5': self.hours5,
            'hours6': self.hours6,
            'hours7': self.hours7,
            'extra1': self.extra1,
            'extra2': self.extra2,
            'extra3': self.extra3,
            'extra4': self.extra4,
            'extra5': self.extra5,

        }
