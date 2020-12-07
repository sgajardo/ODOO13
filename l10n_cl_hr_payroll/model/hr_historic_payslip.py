# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _


class HrHistoricPayslip(models.Model):
    _name = 'hr.historic.payslip'

    name = fields.Char(string='Nombre', required=True)
    payslip_date = fields.Date(string='Fecha', required=True)
    note = fields.Text(string='Nota')

    _name = 'hr.historic.payslip.line'

    employees_id = fields.Many2one('hr.employee', 'Empleado', required=True)
