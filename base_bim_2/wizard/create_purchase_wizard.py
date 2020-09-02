# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta

class CreatePurchaseWizard(models.TransientModel):
    _name = "create.purchase.wizard"
    _description = 'Asistente de Creacion de Pedidos de Compra'

    @api.model
    def default_get(self, fields):
        res = super(CreatePurchaseWizard, self).default_get(fields)
        context = self._context
        req = self.env['bim.purchase.requisition'].browse(context['active_id'])
        lines = []
        for line in req.product_ids:
            if not line.done and line.quant > line.qty_purchase:
                lines.append((0,0,{
                    'bim_req_line_id': line.id,
                    'product_id': line.product_id.id,
                    'quant': line.quant,# - line.qty_purchase
                    'um_id': line.um_id.id,
                    'analytic_id': line.analytic_id.id,
                    'partner_id': line.partner_id.id,
                    'analytic_tag_ids': line.analytic_tag_ids.ids
                }))
        if not lines:
            raise UserError('No hay líneas nuevas para comprar')
        res['line_ids'] = lines
        return res

    line_ids = fields.One2many('create.purchase.wizard.line','wizard_id','Líneas')
    filter_categ = fields.Boolean(string="Agrupar por Categoría")
    #category_id = fields.Many2one('product.category', "Categoría")

    def create_purchase(self):
        self.ensure_one()
        suppliers = self.line_ids.mapped('partner_id')
        context = self._context
        PurchaseOrd = self.env['purchase.order']
        req = self.env['bim.purchase.requisition'].browse(context['active_id'])
        purchases = []
        if req.project_id.warehouse_id:
            picking_type = self.env['stock.picking.type'].search([('warehouse_id', '=', req.warehouse_id.id),('code', '=', 'incoming')]).id
        else:
            picking_type = self.env['stock.picking.type'].search([], limit=1).id

        # Si esta marcado Agrupar por Categoria
        if self.filter_categ:
            for categ in self.line_ids.mapped('product_id.categ_id'):
                for supplier in suppliers:
                    purchase_lines = []
                    for line in self.line_ids.filtered(lambda l: l.partner_id.id == supplier.id and l.product_id.categ_id.id == categ.id):
                        line_vals = self._prepare_purchase_line(line,req)
                        purchase_lines.append((0,0,line_vals))
                    if purchase_lines:
                        order = PurchaseOrd.create({
                            'partner_id': supplier.id,
                            'origin': req.name,
                            'date_order': fields.Datetime.now(),
                            'picking_type_id': picking_type
                        })
                        order.order_line = purchase_lines
                        req.write({'purchase_ids': [(4, order.id, None)]})

        else:
            for supplier in suppliers:
                purchase_lines = []
                order = PurchaseOrd.create({
                        'partner_id': supplier.id,
                        'origin': req.name,
                        'date_order': fields.Datetime.now(),
                        'picking_type_id': picking_type
                })
                for line in self.line_ids.filtered(lambda l: l.partner_id.id == supplier.id):
                    line_vals = self._prepare_purchase_line(line,req)
                    purchase_lines.append((0,0,line_vals))
                order.order_line = purchase_lines
                req.write({'purchase_ids': [(4, order.id, None)]})
        return True

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
            'analytic_tag_ids': line.analytic_tag_ids
            }



class CreatePurchaseWizardLine(models.TransientModel):
    _name = "create.purchase.wizard.line"
    _description = 'Lineas del asistente de Creacion de Pedidos de Compra'

    wizard_id = fields.Many2one('create.purchase.wizard', 'Wizard')
    bim_req_line_id = fields.Many2one('product.list', 'Linea Requisicion')
    product_id = fields.Many2one('product.product', 'Producto')
    partner_id = fields.Many2one('res.partner', 'Proveedor')
    quant = fields.Float('Cantidad')
    um_id = fields.Many2one('uom.uom', 'U.M')
    analytic_id = fields.Many2one('account.analytic.account', 'Cuenta analítica')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Etiquetas analíticas')
