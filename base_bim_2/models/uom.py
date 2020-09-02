from odoo import fields, models


class UomUom(models.Model):
    _inherit = 'uom.uom'

    alt_names = fields.Char('Nombres alternativos', help='Posibles nombres con los que se puede buscar esta unidad de medida.')
