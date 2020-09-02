# coding: utf-8
from odoo import api, fields, models
from odoo.exceptions import ValidationError
import xlwt
from io import BytesIO
import base64
from datetime import datetime

class BimPaidstateWizard(models.TransientModel):
    _name = 'bim.paidstate.wizard'
    _description = 'Asistente Estado de Pago'

    def _default_budget(self):
        return self.env['bim.paidstate'].browse(self._context.get('active_id')).budget_id

    def _default_currency(self):
        record = self.env['bim.paidstate'].browse(self._context.get('active_id'))
        return record.currency_id or record.budget_id.currency_id


    type = fields.Selection([
        ('all', 'Acumulado'),
        ('stage', 'Etapas'),],
        string="En base a", default='all')
    budget_id = fields.Many2one('bim.budget', "Presupuesto", required=True, default=_default_budget)
    stage_id = fields.Many2one('bim.budget.stage', "Etapa")
    amount = fields.Monetary("Monto Calculado",compute='_amount_compute')
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True, default=_default_currency)

    @api.depends('stage_id', 'type','budget_id')
    def _amount_compute(self):
        date = fields.Date.today()
        paid_id = self._context.get('active_id')
        for record in self:
            budget = record.budget_id
            amount_stage = amount_all = 0
            prev_paid = self.env['bim.paidstate'].search([('id','!=',paid_id),('budget_id','=',budget.id)])#,('date','<',date)
            accumulated = sum(paid.amount for paid in prev_paid)

            if record.type == 'stage':
                for concept in budget.concept_ids.filtered(lambda c: c.type_cert == 'stage'):
                    amount_stage += sum(csta.amount_certif for csta in concept.certification_stage_ids if csta.stage_id.id == record.stage_id.id)#in ['approved']
            else:
                for concept in record.budget_id.concept_ids.filtered(lambda c: not c.parent_id and c.balance_cert > 0):
                    amount_all += concept.balance_cert
            record.amount = amount_stage if record.type == 'stage' else amount_all - accumulated

    def process(self):
        paid = self.env['bim.paidstate'].browse(self._context.get('active_id'))
        paid.amount = self.amount
        if self.type == 'stage':
            paid.stage_id = self.stage_id.id




