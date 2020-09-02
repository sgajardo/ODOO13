# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from datetime import datetime

class BimDocumentation(models.Model):
    _description = "Documentacion BIM"
    _name = 'bim.documentation'
    _order = "id desc"
    _rec_name = 'desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char('Código', translate=True, default="Nuevo", copy=False)
    desc = fields.Char('Descripción', copy=True)
    obs = fields.Text('Notas')
    project_id = fields.Many2one('bim.project', 'Obra', ondelete="cascade", copy=True)
    user_id = fields.Many2one('res.users', string='Responsable', track_visibility='onchange',
        default=lambda self: self.env.user, copy=False)
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company,
                                 required=True, copy=False)
    file_name = fields.Char("Nombre Archivo", copy=False)
    file_01 = fields.Binary(string='Archivo', copy=False)
    image_medium = fields.Binary("Tamaño imagen", copy=False)

    def _set_image_medium(self):
        self._set_image_value(self.image_medium)

    @api.model
    def create(self, vals):
        if vals.get('name', "Nuevo") == "Nuevo":
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.documentation') or "Nuevo"
        return super(BimDocumentation, self).create(vals)

    def print_document_notes(self):
        return self.env.ref('base_bim_2.notes_report_document').report_action(self)