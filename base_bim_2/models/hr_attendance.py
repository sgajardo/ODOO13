from odoo import api, fields, models

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    project_id = fields.Many2one('bim.project', string='Obra')
    attendance_cost = fields.Float(string='Costo', compute='compute_attendance_cost', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True,
                                  default=lambda r: r.env.company.currency_id)

    @api.depends('worked_hours')
    def compute_attendance_cost(self):
        for record in self:
            if record.employee_id.hour_cost > 0:
                hour_cost = record.employee_id.hour_cost
            else:
                hour_cost = record.employee_id.wage_bim / (record.employee_id.total_hours_week * 4)
            record.attendance_cost = hour_cost * record.worked_hours

    @api.model
    def create(self, vals):
        res = super(HrAttendance, self).create(vals)
        if not 'project_id' in vals:
            res.project_id = res.employee_id.default_bim_project.id
        return res