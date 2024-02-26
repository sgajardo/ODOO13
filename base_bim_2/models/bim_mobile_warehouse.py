# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
import xlwt
import base64
import re

class BimMobileWarehouse(models.Model):
    _description = "Almacen Movil"
    _name = 'bim.mobile.warehouse'
    _order = "id desc"

    @api.model
    def default_get(self, default_fields):
        values = super(BimMobileWarehouse, self).default_get(default_fields)
        active_id = self._context.get('active_id')
        return values

    @api.model
    def create(self, vals):
        if vals.get('name', "Nuevo") == "Nuevo":
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.mobile.warehouse') or "Nuevo"
        result = super(BimMobileWarehouse, self).create(vals)
        result.create_warehouse()
        return result

    name = fields.Char('Código', translate=True, default="Nuevo")
    reference = fields.Char('Descripción', required=True)
    user_id = fields.Many2one('res.users', string='Responsable', default=lambda self: self.env.user)
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company, required=True)
    warehouse_id = fields.Many2one('stock.warehouse','Ubicación')
    date = fields.Date('Fecha',default=fields.Date.context_today)
    picking_ids = fields.Many2many('stock.picking', string='Transferencias')
    picking_in_count = fields.Integer('Cantidad Entradas', compute="_compute_picking")
    picking_out_count = fields.Integer('Cantidad Salidas', compute="_compute_picking")

    # ~ state = fields.Selection(
        # ~ [('nuevo', 'Nuevo'),
         # ~ ('aprobado', 'Aprobado'),
         # ~ ('finalizado', 'Finalizado'),
         # ~ ('cancelado', 'Cancelado')],
        # ~ 'Estado', size=1, default='nuevo', track_visibility='onchange')
    # ~ product_ids = fields.One2many('product.list', 'requisition_id', string='Listado Productos')
    # ~

    def _compute_picking(self):
        for record in self:
            record.picking_in_count = len(record.picking_ids.filtered(lambda pk: pk.picking_type_id.code == 'incoming'))
            record.picking_out_count = len(record.picking_ids.filtered(lambda pk: pk.picking_type_id.code == 'outgoing'))

    def create_warehouse(self):
        for record in self:
            warehouse = self.env['stock.warehouse'].create({
                'name': record.reference,
                'code': record.name,
            })
            record.warehouse_id = warehouse.id
            #warehouse.lot_stock_id.id

    def action_view_pickings_in(self):
        pickings = self.picking_ids.filtered(lambda pk: pk.picking_type_id.code == 'incoming')
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if len(pickings) > 0:
            action['domain'] = [('id', 'in', pickings.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_view_pickings_out(self):
        pickings = self.picking_ids.filtered(lambda pk: pk.picking_type_id.code == 'outgoing')
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if len(pickings) > 0:
            action['domain'] = [('id', 'in', pickings.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action


    # ~ def create_picking(self):
        # ~ if not self.project_id.stock_location_id:
            # ~ raise ValidationError('La obra %s no tiene configurada una ubicacion de inventario'%self.project_id.nombre)
        # ~ view_id = self.env.ref('stock.view_picking_form').id
        # ~ context = self._context.copy()
        # ~ context['default_bim_requisition_id'] = self.id
        # ~ picking_type = self.env['stock.picking.type'].search([('code','=','internal'),('warehouse_id','=',self.warehouse_id.id)], limit = 1)
        # ~ context['default_picking_type_id'] = picking_type.id
        # ~ context['default_location_dest_id'] = self.project_id.stock_location_id.id
        # ~ return {
            # ~ 'name':'Nuevo',
            # ~ 'view_mode':'tree',
            # ~ 'views' : [(view_id,'form')],
            # ~ 'res_model':'stock.picking',
            # ~ 'view_id':view_id,
            # ~ 'type':'ir.actions.act_window',
            # ~ 'target': 'current',
            # ~ 'context':context,
        # ~ }
