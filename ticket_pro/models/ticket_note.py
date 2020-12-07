# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class TicketNotes(models.Model):
    _description = "Ticket Notes"
    _name = 'ticket.notes'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    _order = 'id desc'

    name = fields.Char(string='Secuencia', default="Nuevo", copy=False)
    title = fields.Char(string='Título')
    date_note = fields.Date(string='Fecha', default=fields.Date.today)
    note = fields.Text(string='Nota')

    @api.model
    def create(self, vals):
        if vals.get('name', "Nuevo") == "Nuevo":
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'ticket.notes') or "Nuevo"
        return super(TicketNotes, self).create(vals)