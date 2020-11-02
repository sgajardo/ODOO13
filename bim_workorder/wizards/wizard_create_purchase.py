# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta

class WizardCreatePurchaseWorkorder(models.TransientModel):
    _name = "wizard.create.purchase.workorder"
    _description = 'Asistente de Creacion de Pedidos de Compra'

    @api.model
    def default_get(self, fields):
        res = super(WizardCreatePurchaseWorkorder, self).default_get(fields)
        context = self._context
        workorder = self.env['bim.workorder'].browse(context['active_id'])
        material_lines =  workorder.material_ids.filtered(lambda l: l.order_assign)
        extra_mat_lines = workorder.material_extra_ids.filtered(lambda l: l.order_assign)
        resource_lines = material_lines + extra_mat_lines
        lines = []
        for line in resource_lines:
            product = line.resource_id.product_id if line.type == 'budget_in' else line.product_id
            departure = line.concept_id if line.type == 'budget_in' else line.departure_id
            if product:
                lines.append((0,0,{
                    'product_id': product.id,
                    'quantity': line.qty_ordered,
                    'cost_price': line.price_unit,
                    'um_id': product.uom_po_id.id,
                    'partner_id': line.vendor_first_id.id,
                    'resource_id': line.id,
                    'departure_id': departure.id,
                }))
        if not lines:
            raise UserError('No hay líneas nuevas para comprar')
        res['line_ids'] = lines
        return res

    line_ids = fields.One2many('wizard.create.purchase.workorder.line','wizard_id','Líneas')
    filter_categ = fields.Boolean(string="Agrupar por Categoría")

    def create_purchase(self):
        self.ensure_one()
        context = self._context
        lines_purchase = self.line_ids

        if any(not line.partner_id for line in lines_purchase):
            raise UserError('Existen líneas sin Proveedor asignado')

        suppliers = lines_purchase.mapped('partner_id')
        PurchaseOrd = self.env['purchase.order']
        PurchaseReq = self.env['purchase.requisition']
        workorder = self.env['bim.workorder'].browse(context['active_id'])
        purchases = []

        if workorder.project_id.warehouse_id:
            picking_type = self.env['stock.picking.type'].search([('warehouse_id', '=', workorder.project_id.warehouse_id.id),('code', '=', 'incoming')]).id
        else:
            picking_type = self.env['stock.picking.type'].search([], limit=1).id

        # Si esta marcado Agrupar por Categoria
        if self.filter_categ:
            for categ in self.line_ids.mapped('product_id.categ_id'):
                for supplier in suppliers:
                    purchase_lines = []
                    for line in lines_purchase.filtered(lambda l: l.partner_id.id == supplier.id and l.product_id.categ_id.id == categ.id):
                        line_vals = self._prepare_purchase_line(line,workorder)
                        purchase_lines.append((0,0,line_vals))
                    if purchase_lines:
                        order = PurchaseOrd.create({
                            'partner_id': supplier.id,
                            'bim_workorder_id': workorder.id,
                            'origin': workorder.name,
                            'date_order': fields.Datetime.now(),
                            'picking_type_id': picking_type
                        })
                        order.order_line = purchase_lines
                        workorder.write({'order_ids': [(4, order.id, None)]})

        else:
            for supplier in suppliers:
                purchase_lines = []
                order = PurchaseOrd.create({
                        'partner_id': supplier.id,
                        'bim_workorder_id': workorder.id,
                        'origin': workorder.name,
                        'date_order': fields.Datetime.now(),
                        'picking_type_id': picking_type
                })
                for line in lines_purchase.filtered(lambda l: l.partner_id.id == supplier.id):
                    line_vals = self._prepare_purchase_line(line,workorder)
                    purchase_lines.append((0,0,line_vals))
                order.order_line = purchase_lines
                workorder.write({'order_ids': [(4, order.id, None)]})

        return True


    def _prepare_purchase_line(self,line,workorder):
        return {
            'name': line.product_id.name,
            'product_id': line.product_id.id,
            'product_uom': line.um_id.id or line.product_id.uom_po_id.id,
            'product_qty': line.quantity,
            'price_unit': line.cost_price,
            'taxes_id': [(6, 0, line.product_id.supplier_taxes_id.ids)],
            'date_planned': fields.Date.today(),
            'workorder_resource_id': line.resource_id.id,
            'workorder_departure_id': line.departure_id.id
            }

class WizardCreatePurchaseWorkorderLine(models.TransientModel):
    _name = "wizard.create.purchase.workorder.line"
    _description = 'Lineas del asistente de Creacion de Pedidos de Compra'

    wizard_id = fields.Many2one('wizard.create.purchase.workorder', 'Wizard')
    product_id = fields.Many2one('product.product', 'Producto')
    partner_id = fields.Many2one('res.partner', 'Proveedor')
    quantity = fields.Float('Cantidad')
    cost_price = fields.Float('Coste')
    um_id = fields.Many2one('uom.uom', 'U.M')
    resource_id = fields.Many2one('bim.workorder.resources', string="Recurso")
    departure_id = fields.Many2one('bim.concepts', string="Concepto/Partida")

