# -*- coding: utf-8 -*-

from odoo import api, fields, models

class TicketProWizard(models.TransientModel):
    _name = 'ticket.pro.wizard'
    _description = 'Ticket Pro Wizard'

    @api.model
    def default_get(self, fields):
        res = super(TicketProWizard, self).default_get(fields)
        tickets = self._context.get('active_ids', [])
        res.update({
            'tickets_ids': tickets
        })
        return res
    tickets_ids = fields.Many2many('ticket.pro', string='Tickets')

    def check_report(self):
        self.ensure_one()
        data = {}
        data['id'] = self._context.get('active_id', [])
        data['docs'] = self._context.get('active_ids', [])
        data['model'] = self._context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read([])[0]
        return self.print_report(data)

    def print_report(self, data):
        action = self.env.ref('ticket_pro.ticket_pro_report').report_action(self)
        action.update({'close_on_report_download': True})
        return action
