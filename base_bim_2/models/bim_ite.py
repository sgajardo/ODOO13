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
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company,
                                 required=True)

    amount = fields.Float('Total',
                             required=True, readonly=True)

    """
    ite_material = fields.Float('Materiales')
    ite_mo = fields.Float('Mano de Obra')
    ite_eq = fields.Float('Equipos')
    ite_sc = fields.Float('Subcontrato')
    ite_otros = fields.Float('Otros')
    total = fields.Float('Total')
    """

    val_a = fields.Float("A")
    val_b = fields.Float("B")
    val_c = fields.Float("C")
    val_d = fields.Float("D")

    line_ids = fields.One2many(comodel_name="bim.ite.line", inverse_name="ite_ide", string="Líneas")

    @api.model
    def create(self, vals):
        if vals.get('name', "Nuevo") == "Nuevo":
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.ite') or "Nuevo"
        return super(BimIte, self).create(vals)

    @api.onchange('line_ids','val_a','val_b','val_c','val_d')
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
    name = fields.Char("Nombre")
    sequence = fields.Integer(string='Sequence', default=10)
    formula = fields.Char("Fórmulas/Valor", default="1")

    product_id = fields.Many2one(comodel_name="product.product", string="Producto")

    price = fields.Float("Precio")

    amount = fields.Float('Sub Total', help="Monto", compute='cal_amount')
    qty_calc = fields.Float('Cantidad', help="Monto", compute='cal_amount')

    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]")

    @api.onchange('name')
    def _onchange_name(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id
            self.price = self.product_id.standard_price

    @api.depends('price', 'formula')
    def cal_amount(self):
        for record in self:
            formula = record.formula
            _formula = formula.replace("A",str(record.ite_ide.val_a)).replace("a",str(record.ite_ide.val_a)).replace("B",str(record.ite_ide.val_b)).replace("b",str(record.ite_ide.val_c)).replace("C",str(record.ite_ide.val_c)).replace("c",str(record.ite_ide.val_c))
            qty = float(eval(_formula))
            record.qty_calc = qty
            record.amount = qty * record.price




    @api.onchange('product_id')
    def onchange_product_id(self):
        self.name = self.product_id.name
        if self.product_id.default_code:
            self.code = self.product_id.default_code
        else:
            self.code = "00"


    ite_ide = fields.Many2one(comodel_name="bim.ite", string="Bim Ite")
