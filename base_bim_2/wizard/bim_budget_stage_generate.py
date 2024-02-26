# coding: utf-8
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BimBudgetStageWizard(models.TransientModel):
    _name = 'bim.budget.stage.wizard'
    _description = 'Etapas del Presupuesto'

    name = fields.Selection([
        ('Q', 'Quincenal'),
        ('M', 'Mensual'),
        ('B', 'Bimensual'),
        ('T', 'Trimestral'),
        ('S', 'Semestral') ], string="Frecuencia", default='M')

    def do_generate(self):
        values = []
        budget_id = self._context.get('active_id')
        interval = self.name == 'S' and 6 or \
                   self.name == 'T' and 3 or \
                   self.name == 'B' and 2 or \
                   self.name == 'M' and 1 or 15

        budget = self.env['bim.budget'].browse(budget_id)
        budget.create_stage(interval)

        stages = budget.mapped('stage_ids')
        action = self.env.ref('base_bim_2.action_bim_budget_stage').read()[0]
        if len(stages) > 0:
            action['domain'] = [('id', 'in', stages.ids),('budget_id', '=', budget.id)]
            action['context'] = {'default_budget_id': budget.id}
        return action

