# coding: utf-8
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BimIteWizard(models.TransientModel):
    _name = 'bim.ite.wizard'
    _description = 'Indices Técnicos'

    @api.model
    def default_get(self, fields):
        res = super(BimIteWizard, self).default_get(fields)
        res['concept_id'] = self._context.get('active_id', False)
        return res

    ite_id = fields.Many2one(comodel_name="bim.ite", string="ITE", required=True)
    concept_id = fields.Many2one('bim.concepts', "Concepto", required=True)
    obs = fields.Text('Notas')
    val_n = fields.Float("N")
    val_x = fields.Float("X")
    val_y = fields.Float("Y")
    val_z = fields.Float("Z")


    @api.onchange('ite_id')
    def onchange_ite_id(self):
        for record in self:
            record.val_n = record.ite_id.val_n
            record.val_x = record.ite_id.val_x
            record.val_y = record.ite_id.val_y
            record.val_z = record.ite_id.val_z
            record.obs = record.ite_id.obs

    def do_action(self):
        concept_obj = self.env['bim.concepts']
        self.concept_id.obs = self.ite_id.obs
        concept_parent = concept_obj.browse(self._context['active_id'])
        lines_parent = self.ite_id.line_ids.filtered(lambda l: not l.parent_id)

        for line in lines_parent:
            line_id = line.id
            vals = {
                'name': line.name,
                'code': line.code,
                'parent_id': concept_parent.id,
                'type' : self.get_type(line),
                'budget_id' : concept_parent.budget_id.id,
                'amount_fixed' : line.price,
                'quantity': self._compute_formula(line.formula),#line.qty_calc,
            }
            new_concept = concept_obj.create(vals)
            for child in self.ite_id.line_ids.filtered(lambda l: l.parent_id.id == line_id):
                child_vals = {
                'name': child.name,
                'code': child.code,
                'parent_id': new_concept.id,
                'type' : self.get_type(child),
                'budget_id' : new_concept.budget_id.id,
                'amount_type': 'fixed',
                'amount_fixed' : child.price,
                'quantity': self._compute_formula(child.formula),#line.qty_calc,
                'uom_id': child.product_uom.id,
                }
                new_child = concept_obj.create(child_vals)
        return {'type': 'ir.actions.act_window_close'}

    def get_type(self,line):
        if line.type == 'concept':
            type = 'departure'
        else:
            if line.product_id.resource_type == 'M':
                type = 'material'
            elif line.product_id.resource_type == 'H':
                type = 'labor'
            elif line.product_id.resource_type == 'Q':
                type = 'equip'
            else:
                type = 'aux'
        return type


    def _compute_formula(self,formula):
        value = 0
        if formula:
            N = n = self.val_n
            X = x = self.val_x
            Y = y = self.val_y
            Z = z = self.val_z
            value = eval(str(formula))
        return value
