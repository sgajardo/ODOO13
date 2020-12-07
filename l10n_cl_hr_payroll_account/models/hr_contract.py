from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    account_analytic_tag_id = fields.Many2one('account.analytic.tag', 'Etiqueta analítica')
