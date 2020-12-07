# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta

class LoadEmployees(models.TransientModel):
    _name = "load.employees"
    _description = 'Carga de empleados'

    @api.model
    def default_get(self, fields):
        res = super(LoadEmployees, self).default_get(fields)
        context = self._context
        project = self.env['bim.project'].browse(context['active_id'])
        lines = []
        working_hours = self.env.user.company_id.working_hours
        for line in project.employee_line_ids:
            lines.append((0,0,{
                'employee_id': line.employee_id.id,
                'start_date': line.start_date,
                'end_date': line.end_date,
            }))
        res['line_ids'] = lines
        return res

    line_ids = fields.One2many('load.employees.line','wizard_id','Líneas')

    def load_employees(self):
        context = self._context
        today = date.today()
        project = self.env['bim.project'].browse(context['active_id'])
        project_employee_obj = self.env['bim.project.employee']
        for line in self.line_ids:
            employee_line = project_employee_obj.search([
                ('project_id','=',project.id),
                ('employee_id','=',line.employee_id.id),
            ])
            if employee_line:
                employee_line.write({
                    'start_date': line.start_date,
                    'end_date': line.end_date,
                })
            else:
                project_employee_obj.create({
                    'employee_id': line.employee_id.id,
                    'project_id': project.id,
                    'start_date': line.start_date,
                    'end_date': line.end_date,
                })
        return True

class LoadEmployeesLine(models.TransientModel):
    _name = "load.employees.line"
    _description = 'Detalles de carga de empleados'

    wizard_id = fields.Many2one('load.employees', 'Wizard')
    employee_id = fields.Many2one('hr.employee', 'Empleado')
    start_date = fields.Date('Fecha Inicio')
    end_date = fields.Date('Fecha Fin')
