# -*- coding: utf-8 -*-

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    raise_ticket = fields.Boolean(
        'Tickets automáticos', default=True,
        help='Levanta un ticket automáticamente al encontrar un error.')
