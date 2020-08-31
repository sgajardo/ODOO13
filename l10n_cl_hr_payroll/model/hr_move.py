# coding: utf-8
from odoo import api, fields, models


class HrMoveType(models.Model):
    _name = 'hr.move.type'
    _description = 'Tipos de Movimientos'

    name = fields.Char('Nombre', required=True)
    code = fields.Char(u'Código', required=True)
    is_holiday = fields.Boolean('Es Ausencia')

    _sql_constraints = [
        ('unique_name', 'unique(name)','Nombre debe ser único'),
        ('unique_code', 'unique(code)','Código debe ser único'),
    ]

    def name_get(self):
        return [(record.id, '[%s] %s' % (record.code, record.name)) for record in self]


class HrMove(models.Model):
    _name = 'hr.move'
    _description = 'Movimientos'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('Código', translate=True, default='Nuevo')
    employee_id = fields.Many2one('hr.employee', 'Empleado')
    date_start = fields.Date('Fecha de Inicio')
    date_end = fields.Date('Fecha de Término')
    rut_r = fields.Char('R.U.T', related='employee_id.identification_id')
    type_id = fields.Many2one('hr.move.type', domain=[('is_holiday', '=', False)],
                              default=lambda self: self.env.ref('l10n_cl_hr_payroll.hr_move_type_0', raise_if_not_found=False))
    # El campo de holiday_id no debe salir en ninguna vista, es solo referencial
    # y para borrar el movimiento si se borra la ausencia
    holiday_id = fields.Many2one('hr.holidays', ondelete='cascade')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('hr.move') or 'Nuevo'
        return super(HrMove, self).create(vals)
