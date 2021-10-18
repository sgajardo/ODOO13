# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime

class ApuProductTemplate(models.Model):
    _inherit = 'product.template'

    resource_type = fields.Selection(
        [('M', 'Material'),
         ('H', 'Mano de Obra'),
         ('Q', 'Equipo'),
         ('S', 'Sub-Contrato'),
         ('HR', 'Herramienta'),
         ('A', 'Administrativo')],
        'Tipo de Recurso', size=1, default='M')

    social_law = fields.Boolean('Ley Social')
    last_sec = fields.Integer("Último reg de sec")
    document_ids = fields.One2many('product.document.line', 'product_id', string='Documentos')
    change_ids = fields.One2many('product.change.line', 'product_id', string='Cambios')
    id_bim = fields.Char("ID BIM")

    @api.onchange('resource_type')
    def onchange_resource(self):
        if self.resource_type in ['M','Q'] and self.type == 'service':
            self.type = 'product'

class BimProductProduct(models.Model):
    _inherit = 'product.product'

    @api.onchange('resource_type')
    def onchange_resource(self):
        if self.resource_type in ['M','Q'] and self.type == 'service':
            self.type = 'product'


class ProductDocumentBim(models.Model):
    _name = 'product.document.line'
    _description = "Product Document Line"

    name = fields.Char('Nombre')
    comprobante_01_name = fields.Char("Adjunto")
    comprobante_01 = fields.Binary(
        string=('Adjunto'),
        copy=False,
        attachment=True,
        help='Comprobante 01')
    entry_date = fields.Datetime('Fecha de Entrada', default=lambda self: datetime.today())
    user_id = fields.Many2one('res.users', string='Responsable', track_visibility='onchange',
                              default=lambda self: self.env.user)
    product_id = fields.Many2one('product.template', string="Producto", ondelete='cascade')


class ProductChangeBim(models.Model):
    _name = 'product.change.line'
    _description = "Product Change Line"

    product_id = fields.Many2one('product.product', string='Productos')
    qty = fields.Float("Cantidad")
    code_id = fields.Many2one('product.product', string='Código')
    position = fields.Integer("Posición")
    product_id = fields.Many2one('product.template', string="Producto", ondelete='cascade')


