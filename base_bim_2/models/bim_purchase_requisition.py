# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
import xlwt
import base64
import re
#from cStringIO import StringIO
from odoo.exceptions import UserError,ValidationError

class BimPurchaseRequisition(models.Model):
    _inherit = ['mail.thread']
    _description = "Solicitud de Materiales"
    _name = 'bim.purchase.requisition'
    _order = "id desc"

    @api.model
    def default_get(self, default_fields):
        values = super(BimPurchaseRequisition, self).default_get(default_fields)
        active_id = self._context.get('active_id')
        project = self.env['bim.project'].browse(active_id)
        values['warehouse_id'] = project.warehouse_id.id
        return values

    @api.model
    def _default_warehouse_id(self):
        active_id = self._context.get('active_id')
        project = self.env['bim.project'].browse(active_id)
        return project.warehouse_id.id

    name = fields.Char('Código', translate=True, default="Nuevo")
    user_id = fields.Many2one('res.users', string='Responsable', track_visibility='onchange', default=lambda self: self.env.user)
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company, required=True)
    date_begin = fields.Date('Fecha Inicio', default = lambda self: datetime.today())
    date_prevista = fields.Date('Fecha Prevista')
    project_id = fields.Many2one('bim.project', string='Obra')
    obs = fields.Text('Notas')
    warehouse_id = fields.Many2one('stock.warehouse','Bodega', default=_default_warehouse_id)
    maintenance_id = fields.Many2one('bim.maintenance','Mantenimiento')
    analytic_id = fields.Many2one('account.analytic.account', 'Cuenta Analítica')
    state = fields.Selection(
        [('nuevo', 'Nuevo'),
         ('aprobado', 'Aprobado'),
         ('finalizado', 'Finalizado'),
         ('cancelado', 'Cancelado')],
        'Estado', size=1, default='nuevo', track_visibility='onchange')
    product_ids = fields.One2many('product.list', 'requisition_id', string='Listado Productos')
    picking_ids = fields.One2many('stock.picking', 'bim_requisition_id', string='Transferencias')
    picking_count = fields.Integer('Cantidad Transf', compute="_compute_picking")
    purchase_ids = fields.One2many('purchase.order', 'bim_requisition_id', string='Compras')
    purchase_count = fields.Integer('Cantidad Compras', compute="_compute_purchases")
    amount_total = fields.Float('Total', compute="_compute_total")
    space_id = fields.Many2one('bim.budget.space', 'Espacio')

    @api.onchange('project_id')
    def onchange_project_id(self):
        self.analytic_id = self.project_id.analytic_id.id
        self.warehouse_id = self.project_id.warehouse_id.id

    def action_approve(self):
        self.write({'state': 'aprobado'})

    def action_done(self):
        self.write({'state': 'finalizado'})

    def action_cancel(self):
        self.write({'state': 'cancelado'})

    def action_draft(self):
        self.write({'state': 'nuevo'})

    @api.model
    def create(self, vals):
        if vals.get('name', "Nuevo") == "Nuevo":
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.purchase.requisition') or "Nuevo"
        return super(BimPurchaseRequisition, self).create(vals)

    def _compute_picking(self):
        for req in self:
            req.picking_count = len(req.picking_ids)

    def _compute_purchases(self):
        for req in self:
            req.purchase_count = len(req.purchase_ids)

    def _compute_total(self):
        for record in self:
            record.amount_total = sum(pd.subtotal for pd in record.product_ids)

    def create_picking(self):
        if not self.project_id.stock_location_id:
            raise ValidationError('La obra %s no tiene configurada una ubicacion de inventario'%self.project_id.nombre)
        view_id = self.env.ref('stock.view_picking_form').id
        context = self._context.copy()
        context['default_bim_requisition_id'] = self.id
        picking_type = self.env['stock.picking.type'].search([('code','=','internal'),('warehouse_id','=',self.warehouse_id.id)], limit = 1)
        context['default_picking_type_id'] = picking_type.id
        context['default_location_dest_id'] = self.project_id.stock_location_id.id
        return {
            'name':'Nuevo',
            'view_mode':'tree',
            'views' : [(view_id,'form')],
            'res_model':'stock.picking',
            'view_id':view_id,
            'type':'ir.actions.act_window',
            'target': 'current',
            'context':context,
        }

    def action_view_pickings(self):
        pickings = self.mapped('picking_ids')
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if len(pickings) > 0:
            action['domain'] = [('id', 'in', pickings.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_view_purchases(self):
        purchases = self.mapped('purchase_ids')
        action = self.env.ref('purchase.purchase_rfq').read()[0]
        if len(purchases) > 0:
            action['domain'] = [('id', 'in', purchases.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action


    # def button_print_xls(self):
    #     self.ensure_one
    #     today = datetime.today().strftime("%d-%m-%Y")
    #     workbook = xlwt.Workbook(encoding="utf-8")
    #     style_title = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center")
    #     worksheet = workbook.add_sheet('Solicitudes de Materiales')
    #     k = 0
    #     j = 0
    #     worksheet.write_merge(k, k, j, j, 'Código', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Obra', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Fecha Inicio', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Fecha Prevista', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Responsable', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Estado', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Código', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Producto', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Etiquetas', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'U.M', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Cantidad', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Coste', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Sub Total', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Despachado', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Notas', style_title);j += 1
    #     worksheet.write_merge(k, k, j, j, 'Realizado', style_title);j += 1
    #     row_index = 1
    #     for req in self:
    #         for req_prod in req.product_ids:
    #             j = 0
    #             tags = [x.name for x in req_prod.product_id.tag_ids]
    #             subtotal = req_prod.quant * req_prod.product_id.standard_price
    #             worksheet.write(row_index, j, req.name, );j += 1
    #             worksheet.write(row_index, j, req.project_id.nombre, );j += 1
    #             worksheet.write(row_index, j, req.date_begin, );j += 1
    #             worksheet.write(row_index, j, req.date_prevista, );j += 1
    #             worksheet.write(row_index, j, req.user_id.name, );j += 1
    #             worksheet.write(row_index, j, req.state, );j += 1
    #             worksheet.write(row_index, j, req_prod.product_id.default_code, );j += 1
    #             worksheet.write(row_index, j, req_prod.product_id.name, );j += 1
    #             worksheet.write(row_index, j, ','.join(tags), );j += 1
    #             worksheet.write(row_index, j, req_prod.product_id.uom_id.name, );j += 1
    #             worksheet.write(row_index, j, req_prod.quant, );j += 1
    #             worksheet.write(row_index, j, req_prod.product_id.standard_price, );j += 1
    #             worksheet.write(row_index, j, subtotal, );j += 1
    #             worksheet.write(row_index, j, req_prod.despachado, );j += 1
    #             worksheet.write(row_index, j, req_prod.notas, );j += 1
    #             worksheet.write(row_index, j, req_prod.realizado, );j += 1
    #             row_index += 1
    #     fp = StringIO()
    #     workbook.save(fp)
    #     fp.seek(0)
    #     data = fp.read()
    #     fp.close()
    #     data_b64 = base64.encodestring(data)
    #     doc = self.env['ir.attachment'].create({
    #         'name': 'Detalle Solicitudes Materiales %s.xls'%today,
    #         'datas': data_b64,
    #         'datas_fname': 'Detalle Solicitudes Materiales %s.xls'%today,
    #     })
    #     return {
    #             'type' : "ir.actions.act_url",
    #             'url': "web/content/?model=ir.attachment&id="+str(doc.id)+"&filename_field=datas_fname&field=datas&download=true&filename="+str(doc.name),
    #             'target': "self",
    #             'no_destroy': False,
    #     }

class ProductList(models.Model):
    _name = 'product.list'
    _description = 'Listado de Productos'
    _rec_name = 'product_id'

    solo_lectura = fields.Boolean('Solo lectura', default=False, compute='_compute_giveme_state')

    def _compute_giveme_state(self):
        if self.requisition_id.state == 'nuevo':
            self.solo_lectura = False
        else:
            self.solo_lectura = True

    @api.depends('requisition_id.picking_ids')
    def _compute_qty_done(self):
        for record in self:
            moves = record.requisition_id.picking_ids.mapped('move_lines').filtered(lambda m: m.state == 'done' and m.product_id.id == record.product_id.id)
            record.qty_done = sum(x.product_uom_qty for x in moves)

    @api.depends('qty_done','quant')
    def _compute_qty_to_process(self):
        for record in self:
            record.qty_to_process = record.quant - record.qty_done
            record.subtotal = record.quant * record.cost

    @api.depends('requisition_id.purchase_ids')
    def _compute_qty_purchase(self):
        for record in self:
            purchase_lines = record.requisition_id.purchase_ids.mapped('order_line').filtered(lambda r: r.bim_req_line_id.id == record.id and r.state != 'cancel')
            record.qty_purchase = sum(x.product_qty for x in purchase_lines)

    product_id = fields.Many2one('product.product', 'Producto')
    quant = fields.Float('Cantidad')
    cost = fields.Float('Coste')
    subtotal = fields.Float('Subtotal', compute="_compute_qty_to_process")
    despachado = fields.Float('Despachado')
    obs = fields.Text('Notas')
    um_id = fields.Many2one('uom.uom', 'U.M')
    done = fields.Boolean('Realizado')
    qty_to_process = fields.Float('Por procesar', compute="_compute_qty_to_process")
    qty_done = fields.Float('Despachado', compute="_compute_qty_done")
    qty_purchase = fields.Float('Comprado', compute="_compute_qty_purchase")
    sent_to_production = fields.Boolean('Enviado a producción')
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company, required=True)
    analytic_id = fields.Many2one('account.analytic.account', 'Cuenta analítica')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Etiquetas analíticas')
    partner_id = fields.Many2one('res.partner','Proveedor')
    requisition_id = fields.Many2one('bim.purchase.requisition', 'Requisition', ondelete='cascade')
    project_id = fields.Many2one('bim.project', string="Obra")

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.um_id = self.product_id.uom_id.id
        self.analytic_id = self.requisition_id.analytic_id.id
        self.project_id = self.requisition_id.project_id.id
        self.cost = self.product_id.standard_price

    @api.constrains('product_id')
    def _check_product_id(self):
        if not self.requisition_id.state == 'nuevo':
            raise ValidationError("No puede Agregar Líneas en este Estado")

    def unlink(self):
        for requisition_list in self:
            if requisition_list.solo_lectura:
                raise UserError(_('No puede eliminar una Lineas en este diferente a Nuevo!'))
        return super(ProductList, self).unlink()

    # @api.model
    # def create(self, values):
    #     res = super(ProductList, self).create(values)
    #     if 'requisition_id' in values:
    #         res['analytic_id'] = self.requisition_id.analytic_id
    #     return res
