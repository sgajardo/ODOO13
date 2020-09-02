# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime

class stock_warehouse(models.Model):
    _inherit = 'stock.warehouse'
    ###### FIELDS ######
    code = fields.Char('Short Name', required=True, size=16, help="Short name used to identify your warehouse")

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    bim_requisition_id = fields.Many2one('bim.purchase.requisition','Requisición')
    bim_concept_id = fields.Many2one('bim.concepts','Concepto')
    bim_project_id = fields.Many2one('bim.project','Obra')
    bim_space_id = fields.Many2one('bim.budget.space','Espacio')
    bim_object_id = fields.Many2one('bim.object','Objeto de Obra')
    check_to_rewrite = fields.Boolean('Sobreescribir destino')

    @api.onchange('bim_requisition_id')
    def bim_req_change(self):
        new_lines = self.env['stock.move']
        self.move_lines = False
        req = self.bim_requisition_id
        for line in req.product_ids:
            if not line.realizado:
                new_line = new_lines.new({
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uom_qty': line.despachado,
                    'date': req.date_begin,
                    'date_expected': req.date_prevista and req.date_prevista or datetime.today(),
                    'state': 'draft',
                    'price_unit': line.product_id.standard_price,
                    'picking_type_id': self.picking_type_id.id,
                    'origin': req.name,
                    'location_id': self.picking_type_id.default_location_src_id and self.picking_type_id.default_location_src_id.id or False,
                    'location_dest_id': req.project_id.stock_location_id and req.project_id.stock_location_id.id or False,
                    'warehouse_id': self.picking_type_id and self.picking_type_id.warehouse_id.id or False,
                })
                new_lines += new_line
        self.move_lines += new_lines
        return {}

    @api.onchange('picking_type_id', 'partner_id')
    def onchange_picking_type(self):
        super(StockPicking, self).onchange_picking_type()
        if self.bim_requisition_id:
            self.location_dest_id = self.bim_requisition_id.project_id.stock_location_id \
                and self.bim_requisition_id.project_id.stock_location_id.id or False

    def action_force_assign(self):
        for picking in self:
            for move in picking.move_ids_without_package:
                if move.product_uom_qty != move.quantity_done:
                    move.quantity_done = move.product_uom_qty
        return True

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    resource_type = fields.Selection(related='product_tmpl_id.resource_type', string="Tipo de Recurso", store=True)
