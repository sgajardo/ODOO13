from odoo import fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    account_id = fields.Many2one('account.account', 'Cuenta Contable')
    expense = fields.Boolean('Gasto')
    account_type = fields.Selection([('dcr', 'Debe'), ('acr', 'Haber')], 'Debe/Haber')

    use_type = fields.Selection(
        [('N', 'Nomina'),
         ('C', 'Centralizacion'),
         ('A', 'Ambos'),
         ('S', 'Sin uso')],
        'Uso', size=1, default='N')
