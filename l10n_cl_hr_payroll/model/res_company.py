from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    hr_period = fields.Char('Periodo de Recursos Humanos')

    """Mutual de Seguridad"""
    mutualidad_id = fields.Many2one('hr.mutual', 'MUTUAL')
    mutual_seguridad = fields.Float('Mutualidad', help="Mutual de Seguridad")

    """Caja Compensación"""
    ccaf_id = fields.Many2one('hr.ccaf', 'CCAF')
    caja_compensacion = fields.Float(
        'Caja Compensación',
        help="Caja de Compensacion")
