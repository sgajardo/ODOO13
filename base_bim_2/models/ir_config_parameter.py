from odoo import api, models


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    @api.model
    def set_param_sudo(self, key, value):
        return self.sudo().set_param(key, value)
