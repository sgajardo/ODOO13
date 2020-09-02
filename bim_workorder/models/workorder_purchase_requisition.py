# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BimPurchaseRequisition(models.Model):
    _inherit = 'bim.purchase.requisition'

    workorder_id = fields.Many2one('bim.workorder', string="Orden de Trabajo")

class BimProductList(models.Model):
    _inherit = 'product.list'

    workorder_resource_id = fields.Many2one('bim.workorder.resources', string="Recurso")

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    workorder_resource_id = fields.Many2one('bim.workorder.resources', string="Recurso")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            print (vals)
            if vals.get('workorder_resource_id'):
                resource = self.env['bim.workorder.resources'].browse(vals['workorder_resource_id'])
                resource.write({'order_ids': [(4, vals['order_id'], None)]})
        return super(PurchaseOrderLine, self).create(vals_list)

class CreatePurchaseWizard(models.TransientModel):
    _inherit = "create.purchase.wizard"

    #def _prepare_purchase_line(self,line,req):
    #    result = super(CreatePurchaseWizard, self)._prepare_purchase_line(line,req)
    #    result['workorder_resource_id'] =  line.bim_req_line_id.workorder_resource_id.id
    #    return result

    def _prepare_purchase_line(self,line,req):
        return {
            'name': line.product_id.name,
            'product_id': line.product_id.id,
            'product_uom': line.um_id.id or line.product_id.uom_po_id.id,
            'product_qty': line.quant,
            'price_unit': line.product_id.standard_price,
            'taxes_id': [(6, 0, line.product_id.supplier_taxes_id.ids)],
            'date_planned': req.date_prevista,
            'bim_req_line_id': line.bim_req_line_id.id,
            'account_analytic_id': line.analytic_id.id,
            'analytic_tag_ids': line.analytic_tag_ids,
            'workorder_resource_id': line.bim_req_line_id.workorder_resource_id.id
            }
