# -*- encoding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError,ValidationError
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re


class BimIOStockMobile(models.TransientModel):
    _name = 'bim.stock.mobile.wizard'
    _description = "Entrada y Salida Almacen Movil"

    @api.model
    def default_get(self, fields):
        res = super(BimIOStockMobile, self).default_get(fields)
        company = self.env.company
        context = self._context
        active_id = context.get('active_id', False)

        warehouse = self.env['stock.warehouse'].search([('partner_id','=',company.partner_id.id)],limit=1)
        location = warehouse.lot_stock_id and warehouse.lot_stock_id.id or False
        res['mobile_id'] = active_id
        res['location_id'] = company.stock_location_mobile and company.stock_location_mobile.id or location
        return res

    # ========== Wizard fields ===========
    mobile_id = fields.Many2one('bim.mobile.warehouse', string='Stock Mobile')
    project_id = fields.Many2one('bim.project', string='Ubicación Destino')
    warehouse_id = fields.Many2one('stock.warehouse', string='Ubicación', related='mobile_id.warehouse_id')
    location_id = fields.Many2one('stock.location', string='Ubicación Origen')

    type = fields.Selection([
        ('in', 'Movimiento de Entrada'),
        ('out','Movimiento de Salida')],
        'Tipo de Operación', default='in')
    bim_stock_lines = fields.One2many(
        'bim.stock.mobile.lines',
        'wizard_id', string='Lineas')
    # =====================================

    @api.onchange('type')
    def _onchange_lines(self):
        if self.type == 'out':
            project = self.project_id
            location = self.warehouse_id.lot_stock_id
            quants = location.quant_ids.filtered(lambda q: q.quantity > 0 and q.product_id.resource_type in ['M'])
            lines = []
            for product in quants.mapped('product_id'):

                lines.append((0, 0, {'product_id': product.id}))

            if self.bim_stock_lines:
                self.bim_stock_lines = [(5, 0, 0)]
            self.bim_stock_lines = lines


    def action_load(self):
        mobile = self.mobile_id
        company = self.env.company
        pick_type_obj = self.env['stock.picking.type']

        if self.type == 'in':
            code_type = 'incoming'
            location_id = self.location_id.id
            location_dest = mobile.warehouse_id.lot_stock_id.id
        else:
            if not self.project_id.stock_location_id:
                raise ValidationError(u'No existe una Locacion de Stock asociada a la Obra destino')

            code_type = 'outgoing'
            location_id = mobile.warehouse_id.lot_stock_id.id
            location_dest = self.project_id.stock_location_id.id

        move_lines = []
        for i in self.bim_stock_lines:
            if not i.qty_add:
                continue
            move_lines.append([0, False, {
                'product_id': i.product_id.id,
                'product_uom_qty': i.qty_add,
                'product_uom': i.product_id.uom_id.id,
                'price_unit': i.product_id.lst_price,
                'name': i.product_id.name_get()[0][-1]}])

        picking_type = pick_type_obj.search([('default_location_src_id','=',location_id),('code','=',code_type)],limit=1)
        if not picking_type:
            warehouse = self.env['stock.warehouse'].search([('partner_id','=',company.partner_id.id)],limit=1)
            picking_type = pick_type_obj.search([('warehouse_id','=',warehouse.id),('code','=',code_type)])

        dicc = {}
        dicc.update({
            'picking_type_id': picking_type.id,
            'location_id': location_id,
            'move_lines': move_lines,
            'company_id': company.id,
            'origin': self.mobile_id.name,
           # 'partner_id': project.customer_id.id,
            'location_dest_id': location_dest,
            'move_type': 'direct',
        })
        picking = self.env['stock.picking'].create(dicc)
        mobile.picking_ids = [(4,picking.id,None)]
        if company.validate_stock:
            if picking.state == 'draft':
                picking.action_confirm()
                if picking.state != 'assigned':
                    picking.action_assign()
                    if picking.state != 'assigned':
                        picking.action_force_assign()
            for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty
            picking.action_done()
            if picking.state == 'confirmed':
                for move in picking.move_line_ids_without_package:
                    move.qty_done = move.product_qty
                picking.action_assign()
                picking.action_force_assign()
                picking.button_validate()

        return {'type': 'ir.actions.act_window_close'}

class BimIOStockMobileLines(models.TransientModel):
    _name = 'bim.stock.mobile.lines'
    _description = "Bim Stock Mobile lines wizard"

    @api.depends('product_id','wizard_id.type','wizard_id.location_id','wizard_id.project_id')
    def _get_qty_location(self):
        StockQ = self.env['stock.quant']
        for rec in self:
            qty_available = 0
            product = rec.product_id
            parent = rec.wizard_id
            location = parent.location_id if parent.type == 'in' else parent.warehouse_id.lot_stock_id #project_id.stock_location_id.id
            if product and location:
                qty_available = StockQ._get_available_quantity(product,location)
            rec.qty_available = qty_available


    wizard_id = fields.Many2one('bim.stock.mobile.wizard', 'Wizard')
    product_id = fields.Many2one('product.product', 'Producto')
    qty_available = fields.Float('Disponible',digits='BIM qty', compute="_get_qty_location")
    qty_add = fields.Float('Cantidad a Mover', required=True, default=0.0)

