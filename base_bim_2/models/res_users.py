from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    copied_bim_concept_id = fields.Many2one('bim.concepts', 'Concepto a copiar')
    cut_bim_concept_id = fields.Many2one('bim.concepts', 'Concepto a cortar')

    @api.model
    def copy_bim_concept(self, user_id, parent_id):
        user_id, parent_id = int(user_id), int(parent_id)
        user = self.browse(user_id)
        budget_id = self.env.context.get('default_budget_id')
        if (user.cut_bim_concept_id.type or user.copied_bim_concept_id.type) != 'chapter' and not parent_id:
            return False
        if user.copied_bim_concept_id:
            new_concept = self.recursive_create(user.copied_bim_concept_id, parent_id, budget_id)
        elif user.cut_bim_concept_id:
            new_concept = user.cut_bim_concept_id
            user.cut_bim_concept_id = False
            new_concept.write({'parent_id': parent_id or False})
            if budget_id:
                self.recursive_budget_edit(new_concept, budget_id)
        return new_concept.id

    @api.model
    def recursive_budget_edit(self, concepts, budget_id):
        concepts.write({'budget_id': budget_id})
        childs = concepts.mapped('child_ids')
        if childs:
            self.recursive_budget_edit(childs, budget_id)
        return True

    @api.model
    def recursive_create(self, to_copy, parent_id, budget_id):
        copied = to_copy.copy({'parent_id': False})
        for child in to_copy.child_ids:
            self.recursive_create(child, copied.id, budget_id)
        for measure in to_copy.measuring_ids:
            if measure.space_id.budget_id.id != budget_id:
                space = self.env['bim.budget.space'].search([('budget_id', '=', budget_id), ('code', '=', measure.space_id.code)])
                if not space:
                    space = measure.space_id.copy({'budget_id': budget_id})
            else:
                space = measure.space_id
            measure.copy({'concept_id': copied.id, 'space_id': space.id, 'stage_id': None})
        if parent_id:
            copied.write({'parent_id': parent_id})
        if budget_id:
            copied.write({'budget_id': budget_id})
        return copied
