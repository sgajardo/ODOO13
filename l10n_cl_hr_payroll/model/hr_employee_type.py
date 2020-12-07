from odoo import fields, models

class HrEmployeeType(models.Model):
    _name = 'hr.employee.type'
    _description = 'Tipo de Empleado'

    name = fields.Char('Nombre', required=True)
    code = fields.Integer('Código', required=True)
    active = fields.Boolean(default=True)
