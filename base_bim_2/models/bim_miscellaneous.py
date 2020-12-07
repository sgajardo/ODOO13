# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime

# ~ class BimChapter(models.Model):
    # ~ _name = 'bim.chapter'
    # ~ _order = "code asc"
    # ~ _description = "Capitulos Presupuestos"

    # ~ name = fields.Char(string='Nombre', required=True)
    # ~ code = fields.Char(string='Código', required=True)

    # ~ def name_get(self):
        # ~ reads = self.read(['name', 'code'])
        # ~ res = []
        # ~ for record in reads:
            # ~ name = record['name']
            # ~ if record['code']:
                # ~ name = record['code'] + ' ' + name
            # ~ res.append((record['id'], name))
        # ~ return res

# ~ class BimPeparture(models.Model):
    # ~ _name = 'bim.departure'
    # ~ _order = "code asc"
    # ~ _description = "Partidas Presupuestos"

    # ~ name = fields.Char(string='Nombre', required=True)
    # ~ code = fields.Char(string='Código', required=True)
    # ~ chapter_id = fields.Many2one('bim.chapter', 'Capitulo', ondelete='restrict')

    # ~ def name_get(self):
        # ~ reads = self.read(['name', 'code'])
        # ~ res = []
        # ~ for record in reads:
            # ~ name = record['name']
            # ~ if record['code']:
                # ~ name = record['code'] + ' ' + name
            # ~ res.append((record['id'], name))
        # ~ return res

class BimFormula(models.Model):
    _name = 'bim.formula'
    _description = "Formulas de Mediciones"

    name = fields.Char(string='Nombre', required=True)
    length = fields.Float(string='Largo (X)')
    width = fields.Float(string='Ancho (Y)')
    height = fields.Float(string='Alto (Z)')
    formula = fields.Char(string='Fórmula')

    def name_get(self):
        reads = self.read(['name', 'formula'])
        res = []
        for record in reads:
            name = record['name']
            if record['formula']:
                name = record['formula'] + '=' + name
            res.append((record['id'], name))
        return res

