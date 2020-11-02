# coding: utf-8
from odoo import api, fields, models
from odoo.exceptions import ValidationError
import xlwt
from io import BytesIO
import base64
from datetime import datetime
from odoo.exceptions import RedirectWarning, UserError, ValidationError
class BimPaidstateWizard(models.TransientModel):
    _name = 'bim.paidstate.wizard'
    _description = 'Asistente Estado de Pago'

    def _default_budgets(self):
        project_id = self.env['bim.paidstate'].browse(self._context.get('active_id')).project_id
        budgets = self.env['bim.budget'].search([('project_id','=',project_id.id)])
        paidstate_id = self.env['bim.paidstate'].browse(self._context.get('active_id'))
        list =[]
        for budget in budgets:
            found = False
            for line in paidstate_id.lines_ids:
                if line.budget_id.id == budget.id:
                    found = True
                    break
            if not found and budget.balance_certified_residual > 0:
                list.append(budget.id)
        if len(list) == 0:
            raise UserError('No hay Prespuestos Certificados para Cargar')

        return list

    def _default_paidstate_id(self):
        return self.env['bim.paidstate'].browse(self._context.get('active_id')).id

    paidstate_id = fields.Many2one('bim.paidstate', required=True, default=_default_paidstate_id)
    budget_ids = fields.Many2many('bim.budget', string= "Presupuestos", required=True, default=_default_budgets)


    def process(self):
       for budget in self.budget_ids:
           vals = {
               'budget_id': budget.id,
               'price_unit': budget.balance_certified_residual,
               'paidstate_id': self.paidstate_id.id,
               'name': budget.name,
               'loaded': True
           }
           self.env['bim.paidstate.line'].create(vals)





