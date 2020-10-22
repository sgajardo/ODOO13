# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from datetime import datetime

class BimIte(models.Model):
    _description = "Bim ITE"
    _name = 'bim.ite'
    _order = "id desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char('Código', translate=True, default="Nuevo")
    desc = fields.Char('Descripción')
    obs = fields.Text('Notas')
    val_n = fields.Float("N")
    val_x = fields.Float("X")
    val_y = fields.Float("Y")
    val_z = fields.Float("Z")
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company, required=True)
    amount = fields.Float('Total', required=True, readonly=True)
    line_ids = fields.One2many(comodel_name="bim.ite.line", inverse_name="ite_ide", string="Líneas")

    @api.model
    def create(self, vals):
        if vals.get('name', "Nuevo") == "Nuevo":
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.ite') or "Nuevo"
        return super(BimIte, self).create(vals)

    @api.onchange('line_ids','val_n','val_x','val_y','val_z')
    def onchange_lines_ids(self):
        for record in self:
            record.amount = sum(x.amount for x in record.line_ids)

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

    code = fields.Char("Código")
    name = fields.Char("Descripción")
    concept = fields.Char("Concepto")
    sequence = fields.Integer(string='Sequence', default=10)
    formula = fields.Char("Fórmulas/Valor")
    product_id = fields.Many2one(comodel_name="product.product", string="Producto")
    price = fields.Float("Precio")
    amount = fields.Float('Importe', help="Monto", compute='_compute_amount')
    qty_calc = fields.Float('Cantidad', help="Cantidad", compute='_compute_quantity')
    ite_ide = fields.Many2one(comodel_name="bim.ite", string="Bim Ite")
    product_uom = fields.Many2one('uom.uom', string='UdM')
    type = fields.Selection([
        ('product','Producto'),
        ('concept','Partida')],
        string='Tipo')

    @api.onchange('name')
    def _onchange_name(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id
            self.price = self.product_id.standard_price

    # ~ @api.depends('price', 'formula')
    # ~ def compute_amount(self):
        # ~ for record in self:
            # ~ formula = record.formula
            # ~ _formula = formula.replace("A",str(record.ite_ide.val_a)).replace("a",str(record.ite_ide.val_a)).replace("B",str(record.ite_ide.val_b)).replace("b",str(record.ite_ide.val_c)).replace("C",str(record.ite_ide.val_c)).replace("c",str(record.ite_ide.val_c))
            # ~ qty = float(eval(_formula))
            # ~ record.qty_calc = qty
            # ~ record.amount = qty * record.price

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.name = self.product_id.name
        if self.product_id.default_code:
            self.code = self.product_id.default_code
        else:
            self.code = "00"

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

    @api.depends('price', 'formula', 'ite_ide')
    def _compute_amount(self):
        for record in self:
            record.amount = 1


