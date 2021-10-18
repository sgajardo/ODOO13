# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WorkorderTimesheet(models.Model):
    _name = 'workorder.timesheet'

    @api.depends('employee_id')
    def _compute_department_id(self):
        for line in self:
            line.department_id = line.employee_id.department_id

    name = fields.Char(string='Detalle')
    date = fields.Date("Fecha", required=True, default=fields.Date.today)
    unit_amount = fields.Float('Duracion (dias)', default=0.0)
    unit_execute = fields.Float('Cant Ejecutada', default=0.0)
    resource_id = fields.Many2one('bim.workorder.resources', 'Recurso')
    workorder_id = fields.Many2one('bim.workorder', 'Orden de Trabajo')
    user_id = fields.Many2one('res.users', string="Aprobado por")
    job_id = fields.Many2one('hr.job', string="Puesto de Trabajo")
    employee_id = fields.Many2one('hr.employee', "Empleado", check_company=True)
    department_id = fields.Many2one('hr.department', "Department", compute='_compute_department_id', store=True, compute_sudo=True)
    company_id = fields.Many2one('res.company', string="Compañía", required=True, default=lambda self: self.env.company, readonly=True)

