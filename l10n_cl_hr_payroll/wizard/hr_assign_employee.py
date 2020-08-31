# coding: utf-8
from calendar import monthrange

from odoo import api, fields, models


class HrAssignEmployee(models.TransientModel):
    _name = 'hr.assign.employee'

    @api.model
    def _get_default_start_date(self):
        date = fields.Date.from_string(fields.Date.today())
        start = '%s-%s-01' % (date.year, str(date.month).zfill(2))
        return start

    @api.model
    def _get_default_end_date(self):
        date = fields.Date.from_string(fields.Date.today())
        end_of_month = monthrange(date.year, date.month)[1]
        end = '%s-%s-%s' % (date.year, str(date.month).zfill(2), end_of_month)
        return end

    start_date = fields.Date(string='Fecha Inicio', default=_get_default_start_date, help='Ingrese la fecha inicio')
    end_date = fields.Date(string='Fecha Fin', default=_get_default_end_date, help='Ingrese la fecha')
    haberes_id = fields.Many2one('hr.balance', 'Haber / Descuento', help='Seleccione el haber / descuento a asignar')
    amount = fields.Float('Monto', help='Monto del haber/descuento a asignar')
    employee_ids = fields.Many2many('hr.employee', 'hr_assign_employee_rel', 'employee_id', 'wizard_id', 'Empleados')

    @api.onchange('haberes_id')
    def onchange_haberes(self):
        self.amount = self.haberes_id.default_value

    def assign(self):
        hd_obj = self.env['hr.hd']
        for emp in self.employee_ids:
            haber = hd_obj.search([
                ('name', '=', self.haberes_id.id),
                ('employee_id', '=', emp.id),
            ])
            if haber:
                haber.write({
                    'monto': self.amount,
                    'date_from': self.start_date,
                    'date_to': self.end_date,
                })
            else:
                hd_obj.with_context(origen='multi').create({
                    'name': self.haberes_id.id,
                    'employee_id': emp.id,
                    'monto': self.amount,
                    'date_from': self.start_date,
                    'date_to': self.end_date,
                })
