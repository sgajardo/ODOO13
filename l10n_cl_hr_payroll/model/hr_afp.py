from odoo import fields, models


class HrAfp(models.Model):
    _name = 'hr.afp'
    _description = 'Fondos de Pension'

    codigo = fields.Char('Código', required=True)
    name = fields.Char('Nombre', required=True)
    rut = fields.Char('RUT')
    rate = fields.Float('Tasa', required=True)
    sis = fields.Float('Aporte Empresa', required=True)
    independiente = fields.Float(required=True)
