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

    @api.onchange('obs')
    def onchange_obs(self):
        if self.obs:
            self.workorder_resource_id.note = self.obs

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        result = super(PurchaseOrder, self).button_confirm()
        for order in self:
            if order.bim_requisition_id:
                requisition = order.bim_requisition_id

                for pick in order.picking_ids:
                    pick.bim_project_id = requisition.project_id.id

                    if not pick.bim_requisition_id:
                        pick.bim_requisition_id = requisitiond.id

                    # Agregado en sobrescritura actual
                    if requisition.workorder_id:
                        workorder = requisition.workorder_id
                        pick.bim_workorder_id = workorder.id
                        pick.bim_space_id = workorder.space_id.id
                        pick.bim_object_id = workorder.object_id.id
        return result

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
                resource.workorder_id.write({'order_ids': [(4, vals['order_id'], None)]})
        return super(PurchaseOrderLine, self).create(vals_list)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    bim_workorder_id = fields.Many2one('bim.workorder','Orden de Trabajo')
