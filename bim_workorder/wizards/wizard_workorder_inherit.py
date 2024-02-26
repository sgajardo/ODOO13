# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CreatePurchaseWizard(models.TransientModel):
    _inherit = "create.purchase.wizard"

    def _prepare_purchase_line(self,line,req):
        return {
            'name': line.product_id.name,
            'product_id': line.product_id.id,
            'product_uom': line.um_id.id or line.product_id.uom_po_id.id,
            'product_qty': line.quant,
            'price_unit': line.cost,
            'taxes_id': [(6, 0, line.product_id.supplier_taxes_id.ids)],
            'date_planned': req.date_prevista,
            'bim_req_line_id': line.bim_req_line_id.id,
            'account_analytic_id': line.analytic_id.id,
            'analytic_tag_ids': line.analytic_tag_ids,
            'workorder_resource_id': line.bim_req_line_id.workorder_resource_id.id,
            'workorder_departure_id': line.bim_req_line_id.workorder_departure_id.id
            }


class ResourceRequisitionwizard(models.TransientModel):
    _inherit = "resource.requisition.wzd"

    filter_categ = fields.Boolean(string="Filtro Categoría")
    category_id = fields.Many2one('product.category', "Categoría")
    workorder_ids = fields.Many2many("bim.workorder", string="Ordenes de Trabajo")


    def load_resources(self):
        if not self.budget_ids:
            raise UserError(_('Por favor seleccione al menos un presupuesto.'))
        product_ids = []
        requisition_id = self._context.get('active_id')
        ProductList = self.env['product.list']

        # ... Agregado ...#
        if self.workorder_ids:
            for wo in self.workorder_ids:
                material_list = self.filter_categ and wo.material_ids.filtered(lambda m: m.resource_id.product_id.categ_id.id == self.category_id.id) or wo.material_ids
                #for resource in wo.material_ids:
                for resource in material_list:
                    product = resource.resource_id.product_id
                    if product.id in product_ids:
                        line_product = ProductList.search([('product_id','=',product.id),('requisition_id','=',requisition_id)])
                        line_product.write({'quant':line_product.quant+resource.qty_ordered})
                    else:
                        product_ids.append(product.id)
                        line_val = {
                            'requisition_id': requisition_id,
                            'product_id': product.id,
                            'um_id': resource.resource_id.uom_id.id,
                            'quant': resource.qty_ordered,
                            'analytic_id': resource.budget_id.project_id.analytic_id.id or False  }
                        ProductList.create(line_val)

                material_extra = self.filter_categ and wo.material_extra_ids.filtered(lambda m: m.product_id.categ_id.id == self.category_id.id) or wo.material_extra_ids
                #for resource in wo.material_extra_ids:
                for resource in material_extra:
                    if resource.product_id.id in product_ids:
                        line_product = ProductList.search([('product_id','=',resource.product_id.id),('requisition_id','=',requisition_id)])
                        line_product.write({'quant':line_product.quant+resource.qty_ordered})
                    else:
                        product_ids.append(resource.product_id.id)
                        line_val = {
                            'requisition_id': requisition_id,
                            'product_id': resource.product_id.id,
                            'um_id': resource.product_id.uom_id.id,
                            'quant': resource.qty_ordered,
                            'analytic_id': resource.budget_id.project_id.analytic_id.id or False  }
                        ProductList.create(line_val)
        #.................#
        else:
            concept_ids = []
            for budget in self.budget_ids:
                for concept in budget.concept_ids:
                    concept_ids.append(concept.id)

            concepts = self.env['bim.concepts'].browse(concept_ids)
            resources = self.get_resources(concepts)
            if self.filter_categ:
                resources = resources.filtered(lambda p: p.categ_id.id == self.category_id.id)

            for resource in resources:
                if resource.resource_type == 'M':
                    quantity = self.get_quantity(concepts,resource)
                    if resource.id in product_ids:
                        line_product = ProductList.search([('product_id','=',resource.id),('requisition_id','=',requisition_id)])
                        line_product.write({'quant':line_product.quant+quantity})
                    else:
                        product_ids.append(resource.id)
                        val = {
                            'requisition_id': requisition_id,
                            'product_id': resource.id,
                            'um_id': resource.uom_id.id,
                            'cost': resource.standard_price,
                            'quant': quantity,
                            'analytic_id': self.project_id.analytic_id.id or False  }
                        ProductList.create(val)

    @api.onchange('budget_ids')
    def onchange_budgets_id(self):
        budget_list = []
        if self.budget_ids:
            budget_list = self.budget_ids.ids
        return {'domain': {'workorder_ids': [('budget_id','in',budget_list)]}}






