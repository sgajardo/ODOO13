# -*- coding: utf-8 -*-
from odoo.tools.float_utils import float_compare
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models,_
from odoo.exceptions import ValidationError


class BimWorkorderInstaller(models.Model):
    _name = 'bim.workorder.installer'
    _description = "Instaladores Orden de Trabajo BIM"


    name = fields.Char(string='Instalador', required=True)
    location_id = fields.Many2one('stock.location', string="Locación")
    project_id = fields.Many2one('bim.project', string="Obra")



class BimProject(models.Model):
    _inherit = 'bim.project'

    install_location_ids = fields.One2many('bim.workorder.installer', 'project_id', string='Instaladores')


