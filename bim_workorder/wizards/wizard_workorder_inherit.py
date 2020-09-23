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
            'workorder_resource_id': line.bim_req_line_id.workorder_resource_id.id
            }


class ResourceRequisitionwizard(models.TransientModel):
    _inherit = "resource.requisition.wzd"

    filter_categ = fields.Boolean(string="Filtro Categoría")
    workorder_ids = fields.Many2many("bim.workorder", string="Ordenes de Trabajo")

    # ~ def load_resources(self):
        # ~ result = super(ResourceRequisitionwizard, self).load_resources()

        # ~ requisition_id = self._context.get('active_id')
        # ~ ProductList = self.env['product.list']

        # ~ if self.workorder_ids:
            # ~ for wo in self.workorder_ids:
                # ~ for resource in wo.material_ids:
                    # ~ line_val = {
                        # ~ 'requisition_id': requisition_id,
                        # ~ 'product_id': resource.resource_id.product_id.id,
                        # ~ 'um_id': resource.resource_id.uom_id.id,
                        # ~ 'quant': resource.qty_ordered,
                        # ~ 'analytic_id': resource.budget_id.project_id.analytic_id.id or False  }
                    # ~ ProductList.create(line_val)

                # ~ for resource in wo.material_extra_ids:
                    # ~ line_val = {
                        # ~ 'requisition_id': requisition_id,
                        # ~ 'product_id': resource.product_id.id,
                        # ~ 'um_id': resource.product_id.uom_id.id,
                        # ~ 'quant': resource.qty_ordered,
                        # ~ 'analytic_id': resource.budget_id.project_id.analytic_id.id or False  }
                    # ~ ProductList.create(line_val)
        # ~ return result


    def load_resources(self):
        if not self.budget_ids:
            raise UserError(_('Por favor seleccione al menos un presupuesto.'))

        requisition_id = self._context.get('active_id')
        ProductList = self.env['product.list']

        # ... Agregado ...#
        if self.workorder_ids:
            for wo in self.workorder_ids:
                for resource in wo.material_ids:
                    line_val = {
                        'requisition_id': requisition_id,
                        'product_id': resource.resource_id.product_id.id,
                        'um_id': resource.resource_id.uom_id.id,
                        'quant': resource.qty_ordered,
                        'analytic_id': resource.budget_id.project_id.analytic_id.id or False  }
                    ProductList.create(line_val)

                for resource in wo.material_extra_ids:
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
            for resource in resources:
                if resource.resource_type == 'M':
                    quantity = self.get_quantity(concepts,resource)
                    val = {
                        'requisition_id': requisition_id,
                        'product_id': resource.id,
                        'um_id': resource.uom_id.id,
                        'quant': quantity,
                        'analytic_id': self.project_id.analytic_id.id or False  }
                    ProductList.create(val)

    @api.onchange('budget_ids')
    def onchange_budgets_id(self):
        budget_list = []
        if self.budget_ids:
            budget_list = self.budget_ids.ids
        return {'domain': {'workorder_ids': [('budget_id','in',budget_list)]}}






