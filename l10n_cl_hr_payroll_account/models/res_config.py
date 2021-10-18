from odoo import fields, models


class HrPayrollConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_journal_id = fields.Many2one('account.journal', 'Diario Pago Nómina', default_model='hr.payslip.run')
