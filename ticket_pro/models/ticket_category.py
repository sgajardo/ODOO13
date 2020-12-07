# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TicketCategory(models.Model):
    _description = "Ticket Category"
    _name = 'ticket.category'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    _order = 'id desc'

    @api.model
    def _needaction_domain_get(self):
        return [('name', '!=', '')]

    name = fields.Char('Nombre')
    email = fields.Char('Correo Soporte')
