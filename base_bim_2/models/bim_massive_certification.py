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
    _order = 'id desc'

    name = fields.Char(string='Sequence',required=True,  default=_('New'), copy=False)
    user_id = fields.Many2one('res.users', string='Responsable', readonly=True, index=True, tracking=True,
                              required=True,
                              default=lambda self: self.env.user)
    type = fields.Selection([('measure','Medición'),('stage','Etapa'),('fixed','Manual')], string='Tipo Certificación',required=True, default='measure', readonly=True)
    state = fields.Selection([('draft','Borrador'),('ready','Cargado'),('done','Aplicado'),('cancelled','Cancelado')], tracking=True, default='draft', string='Estado',required=True)
    project_id = fields.Many2one('bim.project', string='Obra', required=True)
    budget_id = fields.Many2one('bim.budget', string='Presupuesto', required=True, domain="[('project_id', '=', project_id)]")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, readonly=True)
    certification_date = fields.Date(string='Fecha Certificación', readonly=True, index=True, copy=False, default=fields.Date.context_today)
    creation_date = fields.Date(string='Fecha Creación', readonly=True, index=True, copy=False, default=fields.Date.context_today)
    percent = fields.Integer(string='Porciento (%)', copy=False)
    stage_id = fields.Many2one('bim.budget.stage', string='Etapa', domain="[('budget_id', '=', budget_id), ('state','in',['draft','process'])]", copy=False)
    space_id = fields.Many2one('bim.budget.space', string='Espacio', domain="[('budget_id', '=', budget_id)]", copy=False)
    note = fields.Text(copy=False)
    data_changed = fields.Char('Certificado', compute='compute_data_change')

    def compute_data_change(self):
        for record in self:
            if record.type == 'measure':
                record.data_changed = record.space_id.name
            elif record.type == 'stage':
                record.data_changed = str(record.percent) + '%'
            else:
                record.data_changed = str(record.percent) + '%'

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.massive.certification') or _('New')
        return super(BimMasCertification, self).create(vals)

    def action_ready(self):
        if self.type == 'measure':
            if not self.stage_id:
                raise UserError('Debe seleccionar Etapa para Certificar')
            if not self.space_id:
                raise UserError('Debe seleccionar Espacio para Certificar')
            for concept in self.budget_id.concept_ids:
                if concept.type == 'departure' and concept.parent_id.type == 'chapter':
                    for measure in concept.measuring_ids:
                        if measure.space_id == self.space_id and measure.massively_certified == True:
                            raise UserError((
                                'El espacio {} ya ha sido certificado anteriormente. No es posible volver a certificarlo sin Deshacer la certificación anterior.').format(
                                measure.space_id.name))
        elif self.type == 'stage':
            if not self.stage_id:
                raise UserError('Debe seleccionar Etapa para Certificar')
        self.state = 'ready'

    def action_cancel(self):
        self.state='cancelled'

    def action_convert_to_draft(self):
        self.state='draft'

    def action_massive_certification(self):
        if self.type == 'measure':
            self.certify_by_measure()
        elif self.type == 'stage':
            self.certify_by_stage()
            self.data_changed = str(self.percent) + '%'
        else:
            self.certify_fixed()
            self.data_changed = str(self.percent) + '%'
        self.date = datetime.now()
        self.state = 'done'

    def certify_by_measure(self):
        for concept in self.budget_id.concept_ids:
            if concept.type == 'departure' and concept.parent_id.type == 'chapter':
                if concept.quantity_cert > 0:
                    if concept.type_cert != 'measure':
                        type = 'Manual'
                        if concept.type_cert == 'stage':
                            type = 'Etapa'
                        raise UserError('No es posible la certificación masiva porque el concepto '+concept.name+ ' tiene certificación tipo ' + type)
                else:
                    concept.type_cert = 'measure'

                for measure in concept.measuring_ids:
                    if measure.space_id == self.space_id:
                        measure.write({'stage_id': self.stage_id.id,
                                       'massively_certified': True})
                concept._compute_measure()
                concept.onchange_qty()
                concept.onchange_qty_certification()

    def certify_by_stage(self):
        for concept in self.budget_id.concept_ids:
            if concept.type == 'departure' and concept.parent_id.type == 'chapter':
                if concept.quantity_cert > 0:
                    if concept.type_cert != 'stage':
                        type = 'Manual'
                        if concept.type_cert == 'measure':
                            type = 'Medición'
                        raise UserError('No es posible la certificación masiva porque el concepto '+concept.name+ ' tiene certificación tipo ' + type)
                else:
                    concept.type_cert = 'stage'
                    concept.generate_stage_list()
                for cert_stage in concept.certification_stage_ids:
                    if cert_stage.stage_id == self.stage_id:
                        cert_stage.certif_percent += self.percent
                        cert_stage.onchange_percent()
                concept.onchange_percent_certification()
                concept.onchange_qty_certification()

    def certify_fixed(self):
        for concept in self.budget_id.concept_ids:
            if concept.type == 'departure' and concept.parent_id.type == 'chapter':
                if concept.quantity_cert > 0:
                    if concept.type_cert != 'fixed':
                        type = 'Etapa'
                        if concept.type_cert == 'measure':
                            type = 'Medición'
                        raise UserError('No es posible la certificación masiva porque el concepto '+concept.name+ ' tiene certificación tipo ' + type)
                else:
                    concept.type_cert = 'fixed'
                    concept.onchange_type_cert()
                concept.onchange_function()
                concept.percent_cert += self.percent
                concept.onchange_percent_certification()

    def action_undo_certification(self):
        return {
                'name': _('Deshacer Certificación'),
                'view_mode': 'form',
                'res_model': 'bim.certification.msg.wizard',
                'view_id': self.env.ref('base_bim_2.bim_certification_msg_wizard').id,
                'type': 'ir.actions.act_window',
                'context': {'default_massive_id': self.id},
                'target': 'new'
            }

    def action_rectify(self):
        if self.type == 'measure':
            self.rectify_by_measure()
        elif self.type == 'stage':
            self.rectify_by_stage()
        else:
            self.rectify_fixed()
        self.date = datetime.now()
        self.state = 'draft'


    def rectify_by_measure(self):
        for concept in self.budget_id.concept_ids:
            if concept.type == 'departure' and concept.parent_id.type == 'chapter':
                for measure in concept.measuring_ids:
                    if measure.space_id == self.space_id:
                        measure.write({'stage_id': False,
                                       'massively_certified': False})
                concept._compute_measure()
                concept.onchange_qty()
                concept.onchange_qty_certification()

    def rectify_by_stage(self):
        for concept in self.budget_id.concept_ids:
            if concept.type == 'departure' and concept.parent_id.type == 'chapter':
                for cert_stage in concept.certification_stage_ids:
                    if cert_stage.stage_id == self.stage_id:
                        if cert_stage.certif_percent >= self.percent:
                            cert_stage.certif_percent -= self.percent
                        else:
                            cert_stage.certif_percent = 0
                        cert_stage.onchange_percent()
                concept.onchange_percent_certification()
                concept.onchange_qty_certification()

    def rectify_fixed(self):
        for concept in self.budget_id.concept_ids:
            if concept.type == 'departure' and concept.parent_id.type == 'chapter':
                concept.onchange_function()
                if concept.percent_cert >= self.percent:
                    concept.percent_cert -= self.percent
                else:
                    concept.percent_cert = 0
                concept.onchange_percent_certification()

