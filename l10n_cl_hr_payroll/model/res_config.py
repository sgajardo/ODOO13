# coding: utf-8
from odoo import models, fields, api, _


class HrPayrollConfigSettings(models.TransientModel):
    _inherit = 'hr.payroll.config.settings'


    conf_account_afp_id = fields.Many2one('account.account', string='Cuenta AFP/Previred')
    def set_conf_account_afp_id_defaults(self):
        return self.env['ir.values'].sudo().set_default('hr.payroll.config.settings', 'conf_account_afp_id',
                                                        self.conf_account_afp_id.id)

    conf_account_seguro_id = fields.Many2one('account.account', string='Cuenta Seguro Cesantia/Previred')
    def set_conf_account_seguro_id_defaults(self):
        return self.env['ir.values'].sudo().set_default('hr.payroll.config.settings', 'conf_account_seguro_id',
                                                        self.conf_account_seguro_id.id)

    conf_account_fonasa_id = fields.Many2one('account.account', string='Cuenta Fonasa/Previred')
    def set_conf_account_fonasa_id_defaults(self):
        return self.env['ir.values'].sudo().set_default('hr.payroll.config.settings', 'conf_account_fonasa_id',
                                                        self.conf_account_fonasa_id.id)

    conf_account_isapre_id = fields.Many2one('account.account', string='Cuenta Isapre/Previred')
    def set_conf_account_isapre_id_defaults(self):
        return self.env['ir.values'].sudo().set_default('hr.payroll.config.settings', 'conf_account_isapre_id',
                                                        self.conf_account_isapre_id.id)

    conf_account_mutual_id = fields.Many2one('account.account', string='Cuenta Mutual/Previred')

    def set_conf_account_mutual_id_defaults(self):
        return self.env['ir.values'].sudo().set_default('hr.payroll.config.settings', 'conf_account_mutual_id',
                                                        self.conf_account_mutual_id.id)

    conf_account_ccaf_id = fields.Many2one('account.account', string='Cuenta CCAF/Previred')

    def set_conf_account_ccaf_id_defaults(self):
        return self.env['ir.values'].sudo().set_default('hr.payroll.config.settings', 'conf_account_ccaf_id',
                                                        self.conf_account_ccaf_id.id)

    conf_account_multa_id = fields.Many2one('account.account', string='Cuenta Multa/Previred')
    def set_conf_account_multa_id_defaults(self):
        return self.env['ir.values'].sudo().set_default('hr.payroll.config.settings', 'conf_account_multa_id',
                                                        self.conf_account_multa_id.id)