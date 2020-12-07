# -*- coding: utf-8 -*-
##############################################################################
# Chilean Payroll
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################


from odoo import api, fields, models, tools, _
from datetime import datetime
from odoo.exceptions import UserError


class PagoPrevired(models.Model):
    _name = 'pago.previred'
    _description = 'Pago Previred'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('Código', translate=True, default='Nuevo', readonly=True)

    pago_afp = fields.Float('Pago AFP')
    pago_seguro_cesantia = fields.Float('Pago Seguro Cesantia')

    total_afp = fields.Float('Total AFP', compute='_calcular_afp')

    @api.depends('pago_afp', 'pago_seguro_cesantia')
    def _calcular_afp(self):
        for record in self:
            record.total_afp = record.pago_afp + record.pago_seguro_cesantia

    pago_isapre = fields.Float('Pago Isapre')
    pago_fonasa = fields.Float('Pago Fonasa')
    pago_mutual = fields.Float('Pago Mutual')
    pago_ccaf = fields.Float('Pago CCAF')

    origen = fields.Char('Origen')

    entry_date = fields.Datetime('Fecha de Contable', default=lambda self: datetime.today())

    total_pagar = fields.Float('Total Pagar',compute='_calcular_total')

    state = fields.Selection([('borrador', 'Borrador'),
                              ('pagado', 'Pagado'),
                              ('cancelado', 'Cancelado')], 'Estado', required=True, default='borrador',
                             tracking=True)

    journal_imposiciones_id = fields.Many2one('account.journal', 'Diario Pago Imposiciones',
                                              default=lambda self: self._get_default_journal(), )

    @api.model
    def _get_default_journal(self):
        return self.env['ir.values'].get_defaults_dict('hr.payroll.config.settings').get(
            'journal_id')

    move_id = fields.Many2one('account.move', 'Asiento')

    def exe_next(self):
        if self.state == 'borrador':
            self._create_moves()
            self.state = 'pagado'

    def exe_cancelar(self):
        self.state = 'cancelado'

    def exe_borrador(self):
        self.state = 'borrador'

    @api.depends('total_afp', 'pago_isapre', 'pago_fonasa', 'pago_mutual', 'pago_ccaf')
    def _calcular_total(self):
        for record in self:
            record.total_pagar = record.total_afp + record.pago_isapre + record.pago_fonasa + record.pago_mutual + record.pago_ccaf


    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('pago.previred') or 'Nuevo'
        return super(PagoPrevired, self).create(vals)

    def _create_moves(self):
        """
        Acción que se ejecuta al presionar el botón pagara Previred
        """

        for record in self:
            if not record.journal_imposiciones_id:
                raise UserError(_('No se ha especificado el diario'))
            if not record.entry_date:
                raise UserError(_('No se ha especificado la Fecha contable'))

            """ AFP """
            move_lines = []
            if record.pago_afp:
                move_lines.append((0, 0, {
                    'name': 'AFP',
                    'account_id': record.env['ir.values'].get_defaults_dict('hr.payroll.config.settings').get(
                        'conf_account_afp_id'),
                    'credit': 0.0,
                    'debit': abs(record.pago_afp),
                    'journal_id': record.journal_imposiciones_id.id,
                    'payment_date': record.entry_date,
                }))

            """ Seguro Cesantia """
            if record.pago_seguro_cesantia:
                move_lines.append((0, 0, {
                    'name': 'Seguro Cesantia',
                    'account_id': record.env['ir.values'].get_defaults_dict('hr.payroll.config.settings').get(
                        'conf_account_seguro_id'),
                    'credit': 0.0,
                    'debit': abs(record.pago_seguro_cesantia),
                    'journal_id': record.journal_imposiciones_id.id,
                    'payment_date': record.entry_date,
                }))

            """ Fonasa """
            if record.pago_fonasa:
                move_lines.append((0, 0, {
                    'name': 'Fonasa',
                    'account_id': record.env['ir.values'].get_defaults_dict('hr.payroll.config.settings').get(
                        'conf_account_fonasa_id'),
                    'credit': 0.0,
                    'debit': abs(record.pago_fonasa),
                    'journal_id': record.journal_imposiciones_id.id,
                    'payment_date': record.entry_date,
                }))

            """ Isapre """
            if record.pago_isapre:
                move_lines.append((0, 0, {
                    'name': 'Isapre',
                    'account_id': record.env['ir.values'].get_defaults_dict('hr.payroll.config.settings').get(
                        'conf_account_isapre_id'),
                    'credit': 0.0,
                    'debit': abs(record.pago_isapre),
                    'journal_id': record.journal_imposiciones_id.id,
                    'payment_date': record.entry_date,
                }))

            """ Mutual """
            if record.pago_mutual:
                move_lines.append((0, 0, {
                    'name': 'Mutual',
                    'account_id': record.env['ir.values'].get_defaults_dict('hr.payroll.config.settings').get(
                        'conf_account_mutual_id'),
                    'credit': 0.0,
                    'debit': abs(record.pago_mutual),
                    'journal_id': record.journal_imposiciones_id.id,
                    'payment_date': record.entry_date,
                }))

            """ CCAF """
            if record.pago_ccaf:
                move_lines.append((0, 0, {
                    'name': 'CCAF',
                    'account_id': record.env['ir.values'].get_defaults_dict('hr.payroll.config.settings').get(
                        'conf_account_ccaf_id'),
                    'credit': 0.0,
                    'debit': abs(record.pago_ccaf),
                    'journal_id': record.journal_imposiciones_id.id,
                    'payment_date': record.entry_date,
                }))

            """ BANCO """
            if record.total_pagar:
                move_lines.append((0, 0, {
                    'name': 'PAGO',
                    'account_id': record.journal_imposiciones_id.default_credit_account_id.id,
                    'credit': abs(record.total_pagar),
                    'debit': 0.0,
                    'journal_id': record.journal_imposiciones_id.id,
                    'payment_date': record.entry_date,
                }))

            vals = {
                'name':'PAGO PREVIRED: ' + record.name,
                'ref': record.name,
                'journal_id': record.journal_imposiciones_id.id,
                'date': record.entry_date,
                'narration':'Pago Previred',
                'line_ids': move_lines,
            }
            # vals['line_ids'] = record.group_by_rules(record.slip_ids)
            record.move_id = record.env['account.move'].create(vals)
            record.move_id.post()
        return True