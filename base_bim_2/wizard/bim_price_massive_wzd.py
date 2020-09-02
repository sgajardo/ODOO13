# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class BimPriceMassiveWzd(models.TransientModel):
    _name = 'bim.price.massive.wzd'

    def _get_default_budget(self):
        active_id = self._context.get('active_id')
        budget = self.env['bim.budget'].browse(active_id)
        return budget

    budget_id = fields.Many2one('bim.budget', string='Presupuesto', default=_get_default_budget)
    product_id = fields.Many2one('product.template', string='Recurso')
    new_price = fields.Float('Precio Nuevo')
    type_update = fields.Selection([('cost', 'Actualizar conceptos masivos según coste actual'),
                                    ('sale', 'Actualizar conceptos masivos según precio actual'),
                                    ('manual', 'Actualizar conceptos masivos manualmente'),
                                    ('agreed', 'Actualizar conceptos masivos según precios acordados')
                                    ], string="Tipo",  default='cost')
    def update_price(self):
        if self.type_update == 'cost':
            resources = self.budget_id.concept_ids.filtered(lambda self: self.type in ['material', 'labor', 'equip'])
            for resource in resources:
                resource.amount_fixed = resource.product_id.standard_price

        elif self.type_update == 'sale':
            resources = self.budget_id.concept_ids.filtered(lambda self: self.type in ['material', 'labor', 'equip'])
            for resource in resources:
                resource.amount_fixed = resource.product_id.lst_price

        elif self.type_update == 'agreed':
            project = self.budget_id.project_id
            if not project.price_agreed_ids:
                raise ValidationError(_('No existen registros de Productos con precios acordados para la Obra'))
            for line in project.price_agreed_ids:
                resources = self.budget_id.concept_ids.filtered(lambda x: x.product_id == line.product_id)
                for resource in resources:
                    resource.amount_fixed = line.price_agreed
        else:
            concepts = self.env['bim.concepts'].search([('budget_id', '=', self.budget_id.id), ('product_id', '=', self.product_id.id)])
            if self.new_price > 0.0:
                for concept in concepts:
                    concept.write({'amount_fixed': self.new_price})
            else:
                raise ValidationError(_('El precio debe ser mayor que 0.0'))
