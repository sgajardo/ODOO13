# -*- coding: utf-8 -*-
from odoo import fields, models, api


class BimListPriceAgreed(models.Model):
    _name = 'bim.list.price.agreed'
    _description = 'Lista de Precios Acordados'

    product_id = fields.Many2one('product.product', 'Producto')
    price_agreed = fields.Float('Precio Acordado')
    project_id = fields.Many2one('bim.project', string='Obra')


