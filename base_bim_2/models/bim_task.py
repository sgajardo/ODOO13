# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from datetime import datetime

STATE_TASK = [
        ('0', '0'),
        ('5', '5'),
        ('10', '10'),
        ('15', '15'),
        ('20', '20'),
        ('25', '25'),
        ('30', '30'),
        ('35', '35'),
        ('40', '40'),
        ('45', '45'),
        ('50', '50'),
        ('65', '65'),
        ('70', '70'),
        ('75', '75'),
        ('80', '80'),
        ('85', '85'),
        ('90', '90'),
        ('95', '95'),
        ('100', '100')
    ]

class BimTask(models.Model):
    _description = "Tareas BIM"
    _name = 'bim.task'
    _order = "id desc"
    _rec_name = 'desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Código', translate=True, default="Nuevo")
    desc = fields.Char('Descripción', translate=True, size=100)
    obs = fields.Text('Notas', translate=True)
    project_id = fields.Many2one('bim.project', 'Obra', ondelete="cascade")
    user_id = fields.Many2one('res.users', string='Creado', track_visibility='onchange',
        default=lambda self: self.env.user)
    user_resp_id = fields.Many2one('res.users', string='Responsable', track_visibility='onchange')
    date_ini = fields.Datetime('Fecha Inicio')
    date_end = fields.Datetime('Fecha de Fin')
    load_work = fields.Integer('Horas Etimadas (H)')
    prog_declarada = fields.Selection( STATE_TASK , string='Prog. Declarada %', copy=False, index=True,
        track_visibility='onchange', default='0')
    prog_calculada = fields.Integer('Prog. Cálculada %',)# compute="_compute_total")
    state = fields.Selection([
        ('draft', 'Nuevo'),
        ('work', 'Trabajando'),
        ('end', 'Finalizada'),
        ('cancel', 'Cancelado'),
    ], string='Estado', readonly=True, copy=False, index=True,
        track_visibility='onchange', default='draft')
    bim_timesheet_ids = fields.One2many('bim.project.employee.timesheet', 'task_id', 'Hojas de Tiempo')

    amount_total = fields.Float('Horas Reales (H)', compute="_compute_total")
    dif_total = fields.Float('Horas Pendientes (H)', compute="_compute_total")
    cost_mo_total = fields.Float('Costo Mano de Obra', compute="_compute_total")

    @api.depends('bim_timesheet_ids')
    def _compute_total(self):
        expense_line_obj = self.env['bim.project.employee.timesheet']
        for record in self:
            timesheet_lines = expense_line_obj.search([('task_id', '=', record.id)])
            record.amount_total = sum(e.total_hours for e in timesheet_lines)
            record.dif_total = record.load_work - record.amount_total
            if record.load_work > 0:
                record.prog_calculada = record.amount_total / record.load_work * 100
            record.cost_mo_total = sum(e.work_cost for e in timesheet_lines)

    def action_work(self):
        self.write({'state': 'work'})

    def action_end(self):
        self.write({'state': 'end'})

    @api.model
    def create(self, vals):
        if vals.get('name', "Nuevo") == "Nuevo":
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.task') or "Nuevo"
        return super(BimTask, self).create(vals)

    def action_cancel(self):
        self.write({'state': 'cancel'})
