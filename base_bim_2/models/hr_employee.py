# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class HrEmployeeBim(models.Model):
    _inherit = 'hr.employee'

    wage_bim = fields.Float('Salario BIM')
    default_bim_project = fields.Many2one('bim.project', string='Obra por Defecto')
    total_hours_week = fields.Float(compute='compute_total_hours_week')
    hour_cost = fields.Float(string='Costo Hora')

    def compute_total_hours_week(self):
        for record in self:
            total = 0
            for line in record.resource_calendar_id.attendance_ids:
                total += line.hour_to - line.hour_from
            record.total_hours_week = total