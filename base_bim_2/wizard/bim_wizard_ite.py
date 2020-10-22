# coding: utf-8
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BimIteWizard(models.TransientModel):
    _name = 'bim.ite.wizard'
    _description = 'Indices Técnicos'

    ite_id = fields.Many2one(comodel_name="bim.ite", string="ITE", required=True)
    obs = fields.Text('Notas')

    concept_id = fields.Many2one('bim.concepts', "Concepto", required=True)

    @api.model
    def default_get(self, fields):
        res = super(BimIteWizard, self).default_get(fields)
        res['concept_id'] = self._context.get('active_id', False)
        return res

    val_a = fields.Float("A")
    val_b = fields.Float("B")
    val_c = fields.Float("C")
    val_d = fields.Float("D")

    @api.onchange('ite_id')
    def onchange_ite_id(self):
        for record in self:
            record.val_a = record.ite_id.val_a
            record.val_b = record.ite_id.val_b
            record.val_c = record.ite_id.val_c
            record.val_d = record.ite_id.val_d
            record.obs = record.ite_id.obs


    def do_action(self):
        self.concept_id.obs = self.ite_id.obs
        for line in self.ite_id.line_ids:
            if line.product_id.resource_type == 'M':
                type = 'material'

            if line.product_id.resource_type == 'H':
                type = 'labor'

            if line.product_id.resource_type == 'Q':
                type = 'equip'

            if line.product_id.resource_type == 'S':
                type = 'subcon'

            for record in line:
                formula = record.formula
                _formula = formula.replace("A", str(self.val_a)).replace("a", str(self.val_a)).replace("B", str(self.val_b)).replace("b", str(self.val_c)).replace("C", str(self.val_c)).replace("c", str(self.val_c))
                qty = float(eval(_formula))

            vals = {
                'name': line.name,
                'code': line.code,
                'parent_id': self.concept_id.id,
                'type' : type,
                'budget_id' : self.concept_id.budget_id.id,
                'amount_type': 'fixed',
                'amount_fixed' : line.price,
                'quantity': qty,
                'product_uom': line.product_uom.id,
            }
            insert = self.env['bim.concepts'].create(vals)
