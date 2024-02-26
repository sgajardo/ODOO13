# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError
import time
from datetime import datetime
from calendar import monthrange
import csv
import base64
from odoo.tools import float_is_zero, float_compare

class HrBonusEmployee(models.TransientModel):
    _name = 'hr.bonus.employee'

    @api.model
    def _get_default_start_date(self):
        date = fields.Date.from_string(fields.Date.today())
        start = '%s-%s-01'%(date.year, str(date.month).zfill(2))
        return start

    @api.model
    def _get_default_end_date(self):
        date = fields.Date.from_string(fields.Date.today())
        end_of_month = monthrange(date.year, date.month)[1]
        end = '%s-%s-%s'%(date.year, str(date.month).zfill(2), end_of_month)
        return end

    start_date = fields.Date(string='Fecha Inicio', default=_get_default_start_date, help="Ingrese la fecha inicio")
    end_date = fields.Date(string='Fecha Fin', default=_get_default_end_date, help="Ingrese la fecha")
    bonus_id = fields.Many2one('hr.balance','Haber / Descuento',help="Seleccione el haber / descuento a asignar")
    load_employees = fields.Boolean('Cargar Todos',help="Cargar todos los empleados activos")
    line_ids = fields.One2many('hr.bonus.employee.line', 'wizard_id', 'Líneas')

    def assign(self):
        hd_obj = self.env['hr.hd']
        account_precision = self.env['decimal.precision'].precision_get('Account')
        for line in self.line_ids:
            if not float_is_zero(line.amount, account_precision):
                bonus = hd_obj.search([
                    ('name', '=', self.bonus_id.id),
                    ('employee_id', '=', line.employee_id.id),
                    ('date_from', '=', self.start_date),
                    ('date_to', '=', self.end_date)
                ])
                if bonus:
                    bonus.write({
                        'monto': line.amount,
                        'date_from': self.start_date,
                        'date_to': self.end_date,
                    })
                else:
                    hd_obj.with_context(origen='single').create({
                        'name': self.bonus_id.id,
                        'employee_id': line.employee_id.id,
                        'monto': line.amount,
                        'date_from': self.start_date,
                        'date_to': self.end_date,
                    })

    @api.onchange('load_employees')
    def onchange_load_employees(self):
        if self.load_employees:
            employees = self.env['hr.employee'].search([('active','=',True)])
            self.line_ids = [(0,0,{'employee_id': e.id}) for e in employees]
        else:
            self.line_ids = False
            
class HrBonusEmployeeLine(models.TransientModel):
    _name = 'hr.bonus.employee.line'

    employee_id = fields.Many2one('hr.employee',string="Empleado")
    department_id = fields.Many2one('hr.department',related="employee_id.department_id",string="Departamento",readonly=True)
    parent_id = fields.Many2one('hr.employee',related="employee_id.parent_id",string="Director",readonly=True)
    wizard_id = fields.Many2one('hr.bonus.employee',string="Wizard Padre",readonly=True)
    amount = fields.Float('Monto',help="Monto del haber/descuento a asignar")
