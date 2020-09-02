from odoo import api, fields, models


class CopyMeasuresWizard(models.TransientModel):
    _name = 'copy.measures.wizard'
    _description = 'Asistente para copiar mediciones entre partidas'

    concept_id = fields.Many2one('bim.concepts', 'Origen', required=True)
    dest_concept_id = fields.Many2one('bim.concepts', 'Destino', required=True)
    budget_id = fields.Many2one('bim.budget', 'Presupuesto')

    @api.onchange('concept_id')
    def _onchange_concept(self):
        for record in self:
            record.budget_id = record.concept_id.budget_id

    @api.onchange('budget_id')
    def _onchange_budget(self):
        return {
            'domain': {
                'dest_concept_id': [('budget_id', '=', self.budget_id.id)] if self.budget_id else []
            },
            'value': {
                'dest_concept_id': self.dest_concept_id if self.dest_concept_id.budget_id == self.budget_id else None
            }
        }

    def action_copy(self):
        space_obj = self.env['bim.budget.space']
        for measure in self.concept_id.measuring_ids:
            space = measure.space_id
            dest_budget = self.dest_concept_id.budget_id
            if measure.space_id.budget_id != dest_budget:
                space = space_obj.search([('budget_id', '=', dest_budget.id), ('code', '=', measure.space_id.code)])
                if not space:
                    space = measure.space_id.copy({'budget_id': dest_budget.id})
            measure.copy({'concept_id': self.dest_concept_id.id, 'space_id': space.id})

        self.dest_concept_id._compute_measure()
        self.dest_concept_id.onchange_qty()
        self.dest_concept_id.onchange_qty_certification()
        return {'type': 'ir.actions.act_window_close'}
