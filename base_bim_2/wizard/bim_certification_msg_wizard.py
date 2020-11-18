# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class BimCertificatoinMsgWizard(models.TransientModel):
    _name = 'bim.certification.msg.wizard'
    _description = 'Deshacer presupuesto'

    @api.model
    def default_get(self, fields_list):
        res = super(BimCertificatoinMsgWizard, self).default_get(fields_list)
        massive_id = self.env['bim.massive.certification'].search([('id', '=', self._context.get('active_id'))])
        if massive_id.type in ['stage','measure'] and massive_id.stage_id.state == 'approved':
            res['show_stage_alert'] = True
        res['massive_id'] = massive_id.id
        return res

    massive_id = fields.Many2one(comodel_name="bim.massive.certification", string="Certificación")
    show_stage_alert = fields.Boolean()

    def undo_certification(self):
        return self.massive_id.action_rectify()