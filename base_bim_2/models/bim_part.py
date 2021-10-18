# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError,ValidationError

class BimPart(models.Model):
    _description = "Partes BIM"
    _name = 'bim.part'
    _order = "id desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def default_get(self, fields):
        res = super(BimPart, self).default_get(fields)
        active_id = self._context.get('active_id')
        if active_id:
            concept = self.env['bim.concepts'].browse(active_id)
            res['concept_id'] = concept.id
            res['budget_id'] = concept.budget_id.id
            res['project_id'] = concept.budget_id.project_id.id
        return res

    @api.model
    def create(self, vals):
        if vals.get('name', "Nuevo") == "Nuevo":
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.part') or "Nuevo"
        return super(BimPart, self).create(vals)


    name = fields.Char('Código', translate=True, default="Nuevo")
    obs = fields.Text('Notas', translate=True)
    date = fields.Date(string='Fecha', required=True, readonly=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    concept_id = fields.Many2one('bim.concepts', 'Concepto', ondelete="cascade")
    budget_id = fields.Many2one('bim.budget', string='Presupuesto')#, related='concept_id.budget_id'
    project_id = fields.Many2one('bim.project', string='Obra')
    space_id = fields.Many2one('bim.budget.space', string='Espacio')
    partner_id = fields.Many2one('res.partner', string='Proveedor', tracking=True)
    user_id = fields.Many2one('res.users', string='Responsable', tracking=True, default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string="Compañía", required=True, default=lambda self: self.env.company, readonly=True)
    lines_ids = fields.One2many('bim.part.line', 'part_id', 'Líneas')
    purchase_ids = fields.One2many('purchase.order', 'part_id', 'Compras')
    purchase_count = fields.Integer('N° Compras', compute="_compute_purchases_count")
    state = fields.Selection(
        [('draft', 'Borrador'),
         ('validated', 'Validado'),
         ('cancel', 'Cancelado')],
        'Estatus', readonly=True, copy=False,
        tracking=True, default='draft')
    type = fields.Selection(selection=[
        ('per_document', 'Por Documento'),
        ('per_lines', 'Por Línea')],
        string='Tipo', required=True,
        copy=False, tracking=True, default='per_document')


    def action_validate(self):
        self.write({'state': 'validated'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def create_purchase_order(self):
        self.ensure_one()
        suppliers = []
        add = False
        if self.type == 'per_lines':
            for line in self.lines_ids:
                supp = {
                    'id': line.partner_id.id
                }
                if suppliers:
                    for supplier in suppliers:
                        if supplier['id'] == supp['id']:
                            add = False
                            break
                        else:
                            add = True
                else:
                    add = True
                if add:
                    suppliers.append(supp)
        else:
            supp = {
                    'id': self.partner_id.id
                }
            suppliers.append(supp)
        context = self._context
        PurchaseOrd = self.env['purchase.order']
        purchases = []
        for supplier in suppliers:
            purchase_lines = []
            order = PurchaseOrd.create({
                    'partner_id': supplier['id'],
                    'origin': self.name,
                    'date_order': fields.Datetime.now(),
                    'part_id': self.id
                })
            if self.type == 'per_lines':
                for line in self.lines_ids.filtered(lambda l: l.partner_id.id == supplier['id']):
                    purchase_lines.append((0,0,{
                        'name': line.name.name,
                        'product_id': line.name.id,
                        'product_uom': line.product_uom.id,
                        'product_qty': line.product_uom_qty,
                        'price_unit': line.price_unit,
                        'taxes_id': [(6, 0, line.name.supplier_taxes_id.ids)],
                        'date_planned': self.date,
                        'account_analytic_id': self.project_id.analytic_id.id,
                    }))
            else:
                for line in self.lines_ids:
                    purchase_lines.append((0,0,{
                        'name': line.name.name,
                        'product_id': line.name.id,
                        'product_uom': line.product_uom.id,
                        'product_qty': line.product_uom_qty,
                        'price_unit': line.price_unit,
                        'taxes_id': [(6, 0, line.name.supplier_taxes_id.ids)],
                        'date_planned': self.date,
                        'account_analytic_id': self.project_id.analytic_id.id,
                    }))
            order.order_line = purchase_lines
            self.write({'purchase_ids': [(4, order.id, None)]})
        return True

    @api.depends('purchase_ids')
    def _compute_purchases_count(self):
        for part in self:
            part.purchase_count = len(part.purchase_ids)

    def action_view_purchase_order(self):
        purchases = self.mapped('purchase_ids')
        action = self.env.ref('purchase.purchase_rfq').read()[0]
        if len(purchases) > 0:
            action['domain'] = [('id', 'in', purchases.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

class BimPartLine(models.Model):
    _description = "Partes de Obra"
    _name = 'bim.part.line'


    partner_id = fields.Many2one('res.partner', string='Proveedor', tracking=True)
    name = fields.Many2one('product.product', string='Producto', domain=[('purchase_ok', '=', True)], change_default=True)
    description = fields.Char('Descripción')
    product_uom_qty = fields.Float(string='Cantidad', digits='BIM qty', required=True)
    product_uom = fields.Many2one('uom.uom', string='UdM', domain="[('category_id', '=', product_uom_category_id)]")
    price_unit = fields.Float(string='Precio', required=True, digits='BIM price')
    price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal')
    part_id = fields.Many2one('bim.part', 'Parte de Obra')
    product_uom_category_id = fields.Many2one(related='name.uom_id.category_id')
    resource_type = fields.Selection(
        [('M', 'Material'),
         ('H', 'Mano de Obra'),
         ('Q', 'Equipo'),
         ('S', 'Sub-Contrato'),
         ('HR', 'Herramienta'),
         ('A', 'Administrativo'),
         ('F', 'Función')],
        'Tipo de Recurso', size=1, default='M')
    filter_type = fields.Char(compute='_compute_parent_type')

    @api.onchange('name')
    def onchange_product(self):
        if self.name and self.name.type != 'service':
            warning = {
                'title': _('Warning!'),
                'message': _(u'No puede seleccionar un Producto de Tipo diferente a Servicio!'),
            }
            self.name = False
            return {'warning': warning}

    @api.depends('price_unit', 'product_uom_qty')
    def _compute_amount(self):
        for record in self:
            record.price_subtotal = record.price_unit * record.product_uom_qty

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self._compute_parent_type()
        if self.partner_id:
            if self.part_id.partner_id != self.partner_id and self.part_id.type == 'per_document':
                raise ValidationError(u'No se puede seleccionar un proveedor distinto')

    @api.onchange('name')
    def _onchange_name(self):
        self.product_uom = self.name.uom_id.id
        self.resource_type = self.name.resource_type
        self.price_unit = self.name.standard_price

    @api.depends('part_id.type','part_id.partner_id','part_id.lines_ids')
    def _compute_parent_type(self):
        for rec in self:
            if rec.part_id.type == 'per_document':
                rec.filter_type = 'doc'
            else:
                rec.filter_type = 'line'
