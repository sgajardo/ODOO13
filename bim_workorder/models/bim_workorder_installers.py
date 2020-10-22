# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
import xlwt
import base64
import re

class BimWorkorderStockInstallers(models.Model):
    _description = "Entregas a Instaladores"
    _name = 'bim.workorder.stock.installers'
    _order = "id desc"

    @api.model
    def create(self, vals):
        ctx = self._context
        if vals.get('name', _('/')) == _('/'):
            vals['name'] = self.env['ir.sequence'].with_context(ctx).next_by_code('bim.workorder.stock.installers') or _('New')
        result = super(BimWorkorderStockInstallers, self).create(vals)
        return result

    # ~ @api.model_create_multi
    # ~ def create(self, vals_list):
        # ~ records = super(BimWorkorderStockInstallers, self).create(vals_list)
        # ~ for rec in records:
            # ~ rec.name = self.env['ir.sequence'].next_by_code('bim.workorder.stock.installers') or "/"
        # ~ return records

    name = fields.Char('Código', copy=False, required=True, readonly=True, default='/')
    reference = fields.Char('Descripción', required=True)
    user_id = fields.Many2one('res.users', string='Responsable', default=lambda self: self.env.user)
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company, required=True)
    project_id = fields.Many2one('bim.project','Obra',readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date('Fecha',default=fields.Date.context_today,readonly=True, states={'draft': [('readonly', False)]})
    picking_installer_ids = fields.Many2many('stock.picking','mass_picking_installer_rel', 'picking_mass_id', 'picking_int_id', string='Entregas')
    picking_ids = fields.Many2many('stock.picking', string='Lineas', copy=False, domain=[('picking_type_code','=','internal')],readonly=True, states={'draft': [('readonly', False)]})
    picking_count = fields.Integer('Cantidad Entregas', compute="_compute_picking")
    state = fields.Selection(
        [('draft', 'Nuevo'),
         ('confirm', 'Confirmado'),
         ('done', 'Realizado'),
         ('cancel','Cancelado')],
        'Estado', default='draft', tracking=True)


    def _compute_picking(self):
        for record in self:
            record.picking_count = len(record.picking_installer_ids)

    def action_confirm(self):
        return self.write({'state':'confirm'})

    def action_cancel(self):
        return self.write({'state':'cancel'})

    def action_view_pickings_installer(self):
        pickings = self.picking_installer_ids
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


    def upload_picking(self):
        workorders = self.env['bim.workorder'].search([('project_id','=',self.project_id.id)])
        if not workorders:
            raise ValidationError('La obra %s no tiene Ordenes de Trabajo asociadas'%self.project_id.nombre)

        resources = self.env['bim.workorder.resources'].search([('workorder_id','in',workorders.ids)])
        line_ids = []
        for res in resources:
            for pick in res.picking_out.filtered(lambda pk: not pk.bim_mass_stock_installer_id):
                line_ids.append(pick.id)

        if not line_ids:
            raise ValidationError('No se encontraron registros a cargar.')
        self.picking_ids = [(6,0,line_ids)]


    def process_picking(self):
        project = self.project_id
        company = self.env.company
        picking_type_obj = self.env['stock.picking.type']
        location_dest_id = self.env['stock.location'].search([('usage', '=', 'customer')])

        if not self.picking_ids:
            raise ValidationError('No existen movimientos')

        for picking in self.picking_ids:
            location_id = picking.location_dest_id.id
            picking_type = picking_type_obj.search([
                ('default_location_src_id', '=', location_id),
                ('code', '=', 'outgoing')],limit=1)

            if not picking_type:
                warehouse = self.env['stock.warehouse'].search([('partner_id','=',company.partner_id.id)],limit=1)
                picking_type = picking_type_obj.search([('warehouse_id', '=', warehouse.id),('code', '=', 'outgoing')],limit=1)

            picking_out = picking.copy({
                    'name': '/',
                    'origin': self.name,
                    'location_id': location_id,
                    'location_dest_id': location_dest_id.id,
                    'picking_type_id': picking_type.id,
                    'move_type': 'direct',
                })
            picking.bim_mass_stock_installer_id=self.id
            self.picking_installer_ids = [(4,picking_out.id,None)]

            #validacion
            if picking_out.state == 'draft':
                picking_out.action_confirm()
                if picking_out.state != 'assigned':
                    picking_out.action_assign()
                    if picking_out.state != 'assigned':
                        picking_out.action_force_assign()
            for move in picking_out.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty
            picking_out.action_done()
        self.state = 'done'

    def _create_backorder(self):
        backorders = self.env['stock.picking']
        for picking in self:
            moves_to_backorder = picking.move_lines.filtered(lambda x: x.state not in ('done', 'cancel'))
            if moves_to_backorder:
                backorder_picking = picking.copy({
                    'name': '/',
                    'move_lines': [],
                    'move_line_ids': [],
                    'backorder_id': picking.id
                })
                picking.message_post(
                    body=_('The backorder <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> has been created.') % (
                        backorder_picking.id, backorder_picking.name))
                moves_to_backorder.write({'picking_id': backorder_picking.id})
                moves_to_backorder.mapped('package_level_id').write({'picking_id':backorder_picking.id})
                moves_to_backorder.mapped('move_line_ids').write({'picking_id': backorder_picking.id})
                backorder_picking.action_assign()
                backorders |= backorder_picking
        return backorders
