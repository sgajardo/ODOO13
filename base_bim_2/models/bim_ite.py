# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from odoo import api, fields, models, _
from datetime import datetime
from odoo.modules.module import get_module_resource

class BimIte(models.Model):
    _description = "Bim ITE"
    _name = 'bim.ite'
    _order = "id desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    @api.model
    def _default_image(self):
        image_path = get_module_resource('bim_workorder', 'static/src/img', 'default_image.png')
        return base64.b64encode(open(image_path, 'rb').read())

    name = fields.Char('Código', translate=True, default="Nuevo")
    desc = fields.Char('Descripción')
    obs = fields.Text('Notas')
    val_n = fields.Float("N")
    val_x = fields.Float("X")
    val_y = fields.Float("Y")
    val_z = fields.Float("Z")
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company, required=True)
    amount = fields.Float('Total', compute='_compute_amount')
    image = fields.Image("Imagen", max_width=1920, max_height=1920, default=_default_image)
    line_ids = fields.One2many(comodel_name="bim.ite.line", inverse_name="ite_ide", string="Líneas", copy=True)

    @api.model
    def create(self, vals):
        if vals.get('name', "Nuevo") == "Nuevo":
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.ite') or "Nuevo"
        return super(BimIte, self).create(vals)


    @api.depends('line_ids')
    def _compute_amount(self):
        for record in self:
            record.amount = sum(x.amount for x in record.line_ids)

    @api.onchange('line_ids')
    def onchange_set_lines(self):
        if self.line_ids:
            line_parent = False
            for line in self.line_ids:
                if line.type == 'concept':
                    line_parent = line.id
                else:
                    line.parent_id = line_parent

                if line.sequence == 0:
                    line.sequence = len(self.line_ids)

    def name_get(self):
        res = super(BimIte, self).name_get()
        result = []
        for element in res:
            project_id = element[0]
            cod = self.browse(project_id).name
            desc = self.browse(project_id).desc
            name = cod and '[%s] %s' % (cod, desc) or '%s' % desc
            result.append((project_id, name))
        return result

class BimIteLine(models.Model):
    _name = 'bim.ite.line'
    _description = 'Líneas de ITE'
    _order = 'sequence'

    code = fields.Char("Código")
    name = fields.Char("Descripción")
    #concept = fields.Char("Concepto")
    sequence = fields.Integer(string='Sequence',required=True, default=0)
    formula = fields.Char("Fórmulas/Valor")
    product_id = fields.Many2one(comodel_name="product.product", string="Producto")
    price = fields.Float("Precio")
    amount = fields.Float('Importe', help="Monto", compute='_compute_amount')
    qty_calc = fields.Float('Cantidad', help="Cantidad", compute='_compute_quantity')
    ite_ide = fields.Many2one(comodel_name="bim.ite", string="Bim Ite")
    product_uom = fields.Many2one('uom.uom', string='UdM')
    parent_id = fields.Many2one('bim.ite.line', string='Padre', compute='_compute_parent')
    children_ids = fields.One2many(string="Children Lines", comodel_name='bim.ite.line', inverse_name='parent_id')
    type = fields.Selection([
        ('product','Producto'),
        ('concept','Partida')],
        string='Tipo')

    @api.onchange('name')
    def _onchange_name(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id
            self.price = self.product_id.standard_price

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.name = self.product_id.name
        if self.product_id.default_code:
            self.code = self.product_id.default_code
        else:
            self.code = "00"

    @api.depends('type', 'ite_ide')
    def _compute_parent(self):
        for record in self:
            lines_parent = record.ite_ide.line_ids.filtered(lambda l: l.type == 'concept')
            if record.type == 'product':
                list_res = []
                for parent in lines_parent:
                    if parent.sequence < record.sequence:
                        tuple_vals = (parent.sequence, parent.id)
                        list_res.append(tuple_vals)
                if list_res:
                    list_res.sort(key=lambda tup: tup[0],reverse=True)
                    record.parent_id = list_res[0][1]
                else:
                    record.parent_id = False
            else:
                record.parent_id = False

    @api.depends('price', 'formula', 'ite_ide')
    def _compute_quantity(self):
        for record in self:
            if record.formula:
                N = n = record.ite_ide.val_n
                X = x = record.ite_ide.val_x
                Y = y = record.ite_ide.val_y
                Z = z = record.ite_ide.val_z
                record.qty_calc = eval(str(record.formula))
            else:
                record.qty_calc = 1

    @api.depends('price', 'type', 'ite_ide','sequence','qty_calc')
    def _compute_amount(self):
        for record in self:
            if record.type == 'concept':
                record.amount =  sum(line.price*line.qty_calc for line in self.ite_ide.line_ids if record.sequence < line.sequence and line.parent_id.id == record.id)
            else:
                record.amount = record.price * record.qty_calc

