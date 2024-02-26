# coding: utf-8
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BimCloneBudgetWizard(models.TransientModel):
    _name = 'bim.clone.budget.wizard'
    _description = 'Clonacion del Presupuesto'

    name = fields.Char(string="Desripción")
    budget_id = fields.Many2one('bim.budget', "Plantilla")

    def recursive_create(self, child_ids, budget, parent):
        cobj = self.env['bim.concepts']
        for record in child_ids:
            data_rec = record.copy_data()[0]
            data_rec['budget_id'] = budget.id
            data_rec['parent_id'] = parent.id
            next_level = cobj.create(data_rec)

            if record.child_ids:
                self.recursive_create(record.child_ids, budget, next_level)

    def do_action(self):
        cobj = self.env['bim.concepts']
        project_id = self._context.get('active_id')
        new_budget = self.budget_id.copy(default={'project_id': project_id})
        if self.name:
            new_budget.name = self.name

        # ~ for cap in self.budget_id.concept_ids.filtered(lambda b: not b.parent_id):
            # ~ data_cap = cap.copy_data()[0]
            # ~ data_cap['budget_id'] = new_budget.id
            # ~ new_cap = cobj.create(data_cap)
            # ~ if cap.child_ids:
                # ~ self.recursive_create(cap.child_ids,new_budget,new_cap)

        # Limpieza en valores que deben estar vacios
        departures = new_budget.concept_ids.filtered(lambda x:x.type == 'departure')
        for dep in departures:
            for m in dep.measuring_ids:
                if m.stage_id:
                    m.stage_id = False
            if dep.percent_cert > 0:
                dep.percent_cert = 0
            if dep.quantity_cert > 0:
                dep.quantity_cert = 0
            if dep.amount_fixed_cert > 0:
                dep.amount_fixed_cert = 0

        new_budget.update_amount()
        action = {
            'name': _('%s'%self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'bim.budget',
            'view_mode': 'form',
            'res_id': new_budget.id,
        }
        return action

