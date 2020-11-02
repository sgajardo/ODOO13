# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from odoo import api, fields, models, _
from datetime import datetime
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError


class BimMasCertification(models.Model):
    _name = 'bim.massive.certification'
    _description = 'Massive Certification'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char(string='Sequence',required=True,  default=_('New'), copy=False)
    user_id = fields.Many2one('res.users', string='Responsable', readonly=True, index=True, tracking=True,
                              required=True,
                              default=lambda self: self.env.user)
    type = fields.Selection([('measure','Medición'),('stage','Etapa'),('fixed','Manual')], string='Tipo Certificación',required=True, default='measure', readonly=True)
    state = fields.Selection([('draft','Borrador'),('ready','Cargado'),('done','Aplicado'),('cancelled','Cancelado')], tracking=True, default='draft', string='Estado',required=True)
    project_id = fields.Many2one('bim.project', string='Obra', required=True)
    budget_id = fields.Many2one('bim.budget', string='Presupuesto', required=True, domain="[('project_id', '=', project_id)]")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, readonly=True)
    certification_date = fields.Date(string='Fecha Creación', readonly=True, index=True, copy=False, default=fields.Date.context_today)
    creation_date = fields.Date(string='Fecha Certificación', readonly=True, index=True, copy=False, default=fields.Date.context_today)
    percent = fields.Integer(string='Porciento (%)')
    stage_id = fields.Many2one('bim.budget.stage', string='Etapa', domain="[('budget_id', '=', budget_id), ('state','in',['draft','process'])]")
    space_id = fields.Many2one('bim.budget.space', string='Espacio', domain="[('budget_id', '=', budget_id)]")
    note = fields.Text()

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.massive.certification') or _('New')
        return super(BimMasCertification, self).create(vals)

    def action_ready(self):
        self.state='ready'

    def action_cancel(self):
        self.state='cancelled'

    def action_convert_to_draft(self):
        self.state='draft'

    def action_massive_certification(self):
        if self.type == 'measure':
            self.certify_by_measure()
        elif self.type == 'stage':
            self.certify_by_stage()
        else:
            self.certify_fixed()
        self.date = datetime.now()

    def certify_by_measure(self):
        for concept in self.budget_id.concept_ids:
            if concept.type == 'departure' and concept.parent_id.type == 'chapter':
                if concept.type_cert != 'measure':
                    type = 'Manual'
                    if concept.type_cert == 'stage':
                        type = 'Etapa'
                    raise UserError('No es posible la certificación masiva porque el concepto '+concept.name+ ' tiene certificación tipo ' + type)
                for measure in concept.measuring_ids:
                    if measure.space_id == self.space_id:
                        measure.stage_id = self.stage_id.id

    def certify_by_stage(self):
        for concept in self.budget_id.concept_ids:
            if concept.type == 'departure' and concept.parent_id.type == 'chapter':
                if concept.type_cert != 'stage':
                    type = 'Manual'
                    if concept.type_cert == 'measure':
                        type = 'Medición'
                    raise UserError('No es posible la certificación masiva porque el concepto '+concept.name+ ' tiene certificación tipo ' + type)
                for cert_stage in concept.certification_stage_ids:
                    if cert_stage.stage_id == self.stage_id:
                        cert_stage.certif_percent += self.percent

    def certify_fixed(self):
        for concept in self.budget_id.concept_ids:
            if concept.type == 'departure' and concept.parent_id.type == 'chapter':
                if concept.type_cert != 'fixed':
                    type = 'Etapa'
                    if concept.type_cert == 'measure':
                        type = 'Medición'
                    raise UserError('No es posible la certificación masiva porque el concepto '+concept.name+ ' tiene certificación tipo ' + type)
                concept.percent_cert += self.percent