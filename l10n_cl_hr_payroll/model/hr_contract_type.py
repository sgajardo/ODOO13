from odoo import api, fields, models, tools, _


class HrContractType(models.Model):
    _name = 'hr.contract.type'
    _description = 'Contract Type'

    name = fields.Char('Nombre')
    codigo = fields.Char('Codigo')
    fijo = fields.Boolean(default=False)
