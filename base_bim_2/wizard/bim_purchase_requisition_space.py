# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import UserError,ValidationError

class BimRequisitionSpace(models.TransientModel):
    _name = 'bim.requisition.space.wzd'
    _description = 'Crear Solicitud de Materiales Espacios'

    def default_get_space(self):
        space = self.env['bim.budget.space'].browse(self._context.get('active_id'))
        return space

    categ_ids = fields.Many2many(comodel_name='product.category', string='Categorías')
    space_id = fields.Many2one('bim.budget.space', 'Espacio', default=default_get_space)
    type = fields.Selection([
        ('all', 'Todos los Recursos'),
        ('one', 'Por Categoria de Recurso')],
        'Tipo', default='all')

    def recursive_quantity(self, resource, parent, qty=None):
        qty = qty is None and resource.quantity or qty
        if parent.type == 'departure':
            qty_partial = qty * parent.quantity
            return self.recursive_quantity(resource,parent.parent_id,qty_partial)
        else:
            return qty * parent.quantity

    def get_quantity(self,concept):
        total_qty = 0
        for me in concept.measuring_ids:
            if me.space_id.id == self.space_id.id:
                total_qty += (me.amount_subtotal / concept.quantity) * self.recursive_quantity(concept,concept.parent_id)
        return total_qty

    def create_requisition(self):
        obj_concept = self.env['bim.concepts']
        budget = self.space_id.budget_id
        categs = self.categ_ids.ids
        domain = ['material']
        concepts = budget.concept_ids
        sp_con_ids = [cp.id for cp in concepts for me in cp.measuring_ids if me.space_id.id == self.space_id.id]
        space_concepts = obj_concept.browse(sp_con_ids)
        products = []
        product_ids = []
        for sc in space_concepts:
            quantity = self.get_quantity(sc)
            for resource in sc.child_ids:
                product = resource.product_id
                valid_product = True

                if self.type == 'one':
                    if product.product_tmpl_id.categ_id.id not in categs:
                        valid_product = False

                if valid_product:
                    if product.id in product_ids:
                        for val in products:
                            if val[2]['product_id'] == product.id:
                                val[2]['quant'] = val[2]['quant'] + quantity
                    else:
                        val = {
                            'product_id': product.id,
                            'um_id': resource.uom_id.id,
                            'quant': quantity,
                            'analytic_id': budget.project_id.analytic_id.id or False  }
                        # Solo puedo insertar los materiales
                        if product.resource_type == 'M':
                            products.append((0, 0, val))
                            product_ids.append(product.id)

        if not products:
             raise ValidationError(u'No existen Recursos a procesar')
        requisition_id = self.with_context(active_id=budget.project_id.id,uid=lambda s: s.env.user).env['bim.purchase.requisition'].create({
            'project_id': budget.project_id.id,
            'analytic_id': budget.project_id.analytic_id.id or False,
            'date_begin': datetime.now(),
            'space_id': self.space_id.id,
            'product_ids': products
        })
        self.space_id.write({'purchase_req_ids': [(4, requisition_id.id, None)]})
        return True
