# -*- coding: utf-8 -*-
from odoo import fields, models, _

class WizardMarkAll(models.TransientModel):
    _name = 'wizard.mark.all'
    _description = 'Wizard Mark All'

    def action_mark_all(self):
        mat_ids = self.env.context['active_ids']
        material_ids = self.env['bim.workorder.resources'].search([('id','in',mat_ids)])
        for material in material_ids:
            material.order_assign = True
            material.workorder_id.all_marked = True

class WizardUnMarkAll(models.TransientModel):
    _name = 'wizard.unmark.all'
    _description = 'Wizard UnMark All'

    def action_unmark_all(self):
        mat_ids = self.env.context['active_ids']
        material_ids = self.env['bim.workorder.resources'].search([('id', 'in', mat_ids)])
        for material in material_ids:
            material.order_assign = False
            material.workorder_id.all_marked = False