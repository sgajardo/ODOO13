# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    bim_requisition_id = fields.Many2one('bim.purchase.requisition', 'Requisicion')
    part_id = fields.Many2one('bim.part', 'Partes')


    def action_view_invoice(self):
        result = super(PurchaseOrder, self).action_view_invoice()
        project = self.env['bim.purchase.requisition'].search([('name', '=', self.origin)])
        result['context']['default_project_id'] = project.project_id.id
        return result

    def button_confirm(self):
        result = super(PurchaseOrder, self).button_confirm()
        for order in self:
            if order.bim_requisition_id:
                project = order.bim_requisition_id.project_id
                for pick in order.picking_ids:
                    pick.bim_project_id = project.id
                    if not pick.bim_requisition_id:
                        pick.bim_requisition_id = order.bim_requisition_id.id
        return result

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    bim_req_line_id = fields.Many2one('product.list', 'Linea de Requisicion')
