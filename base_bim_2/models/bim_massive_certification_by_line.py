# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BimMasCertification(models.Model):
    _name = 'bim.massive.certification.by.line'
    _description = 'Massive Certification'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    _order = 'id desc'

    name = fields.Char(string='Sequence',required=True,  default=_('New'), copy=False)
    user_id = fields.Many2one('res.users', string='Responsable', readonly=True, index=True, tracking=True,
                              required=True,
                              default=lambda self: self.env.user)
    type = fields.Selection([('current_stage','Etapa Actual'),('fixed','Manual')], string='Tipo Certificación',required=True, default='current_stage', readonly=True)
    state = fields.Selection([('draft','Borrador'),('ready','Cargado'),('done','Aplicado'),('cancelled','Cancelado')], tracking=True, default='draft', string='Estado',required=True)
    project_id = fields.Many2one('bim.project', string='Obra', required=True)
    budget_id = fields.Many2one('bim.budget', string='Presupuesto', required=True, domain="[('project_id', '=', project_id)]")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, readonly=True)
    certification_date = fields.Date(string='Fecha Certificación', readonly=True, index=True, copy=False, default=fields.Date.context_today)
    creation_date = fields.Date(string='Fecha Creación', readonly=True, index=True, copy=False, default=fields.Date.context_today)
    note = fields.Text(copy=False)
    certification_stage_ids = fields.Many2many('bim.certification.stage.certification', 'certification_line_rel',string='Certificacion', copy=False)
    concept_ids = fields.Many2many('bim.certification.fixed.certification','certification_fixed_rel', string='Medición', copy=False)
    total_certif = fields.Float(string='Importe Certif.', compute='_compute_total_certif')
    percent_certif = fields.Float(string='(%) Certif.', compute='_compute_total_certif')

    @api.depends('concept_ids.amount_certif','certification_stage_ids.amount_certif')
    def _compute_total_certif(self):
        for record in self:
            amount = 0
            if record.type == 'current_stage':
                for line in record.certification_stage_ids:
                    amount += line.amount_certif
            else:
                for line in record.concept_ids:
                    amount += line.amount_certif
            record.total_certif = amount
            record.percent_certif = record.total_certif / record.budget_id.balance * 100 if record.budget_id.balance > 0 else 0

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.massive.certification') or _('New')
        return super(BimMasCertification, self).create(vals)

    def action_ready(self):
        if self.type == 'current_stage':
            if not self.stage_id:
                raise UserError('Debe seleccionar Etapa para Certificar')
        self.state = 'ready'

    def action_cancel(self):
        self.state='cancelled'

    def action_convert_to_draft(self):
        self.state='draft'

    def action_load_lines(self):
        if self.type == 'current_stage':
            self.load_line_by_stage('process')
        else:
            self.load_line_by_fixed()
        self.state = 'ready'

    def load_line_by_stage(self, stage):
        for record in self:
            for line in record.certification_stage_ids:
                line.unlink()
            certification_lines = []
            error = False
            sorted_concepts = sorted(record.budget_id.concept_ids, key=lambda s: s.parent_id.id)
            for concept in sorted_concepts:
                if concept.type == 'departure' and concept.parent_id.type == 'chapter':
                    if concept.quantity_cert > 0:
                        if concept.type_cert == 'stage':
                            for cert_stage in concept.certification_stage_ids:
                                if cert_stage.stage_id.state == stage:
                                    vals = {
                                        'certification_line_id': cert_stage.id,
                                        'budget_qty': concept.quantity,
                                        'stage_id': cert_stage.stage_id.id,
                                        'certif_qty': cert_stage.certif_qty,
                                        'concept_id': cert_stage.concept_id.id,
                                        'amount_budget': concept.balance,
                                        'parent_id': cert_stage.parent_id.id,
                                        'percent_acc': concept.percent_cert,
                                    }
                                    certification_lines.append((0, 0, vals))
                        else:
                            error = True
                    else:
                        concept.type_cert = 'stage'
                        concept.generate_stage_list()
                        for cert_stage in concept.certification_stage_ids:
                            if cert_stage.stage_id.state == stage:
                                vals = {
                                    'certification_line_id': cert_stage.id,
                                    'budget_qty': concept.quantity,
                                    'stage_id': cert_stage.stage_id.id,
                                    'certif_qty': cert_stage.certif_qty,
                                    'concept_id': cert_stage.concept_id.id,
                                    'amount_budget': concept.balance,
                                    'parent_id': cert_stage.parent_id.id,
                                    'percent_acc': concept.percent_cert,
                                }
                                certification_lines.append((0, 0, vals))
            if error and len (certification_lines) == 0:
                raise UserError(
                    'No es posible la certificación por Etapa porque este Presupuesto tiene todas sus partidas certificadas por de forma Manual')
            record.certification_stage_ids = certification_lines

    def load_line_by_fixed(self):
        for record in self:
            error = False
            for line in record.concept_ids:
                line.unlink()
            certification_lines = []
            sorted_concepts = sorted(record.budget_id.concept_ids, key=lambda s: s.parent_id.id)
            for concept in sorted_concepts:
                if concept.type == 'departure' and concept.parent_id.type == 'chapter':
                    if concept.quantity_cert > 0:
                        if concept.type_cert == 'fixed':
                            vals = {
                                'quantity_cert': concept.quantity_cert,
                                'concept_id': concept.id,
                                'balance': concept.balance,
                                'quantity_cert': concept.quantity_cert,
                                'amount_cert': concept.amount_compute_cert,
                                'quantity': concept.quantity,
                                'percent_acc': concept.percent_cert,
                            }
                            certification_lines.append((0, 0, vals))
                        else:
                            error = True
                    else:
                        concept.type_cert = 'fixed'
                        vals = {
                            'quantity_cert': concept.quantity_cert,
                            'concept_id': concept.id,
                            'balance': concept.balance,
                            'quantity_cert': concept.quantity_cert,
                            'amount_cert': concept.amount_compute_cert,
                            'quantity': concept.quantity,
                            'percent_acc': concept.percent_cert,
                        }
                        certification_lines.append((0, 0, vals))
            if error and len (certification_lines) == 0:
                raise UserError(
                    'No es posible la certificación Manual porque este Presupuesto tiene todas sus partidas certificadas por Etapa')
            record.concept_ids = certification_lines

    def action_massive_certification(self):
        if self.type =='current_stage':
            self.certify_by_stage()
        else:
            self.certify_by_fixed()
        self.state = 'done'

    def action_fix(self):
        if self.type =='current_stage':
            self.rectify_by_stage()
        else:
            self.rectify_by_fixed()
        self.state = 'ready'

    def certify_by_stage(self):
        for line in self.certification_stage_ids:
            line.certification_line_id.certif_qty = line.certification_line_id.certif_qty + line.quantity_to_cert
            line.certification_line_id.certif_percent = line.certification_line_id.certif_percent + line.certif_percent
            line.certification_line_id.onchange_percent()
            line.concept_id.onchange_percent_certification()
            line.concept_id.onchange_qty_certification()

    def certify_by_fixed(self):
        for line in self.concept_ids:
            line.concept_id.update_budget_type()
            line.concept_id.quantity_cert = line.concept_id.quantity_cert + line.quantity_to_cert
            line.concept_id.percent_cert = line.concept_id.percent_cert + line.percent_cert



    def rectify_by_stage(self):
        for line in self.certification_stage_ids:
            if line.stage_id.state == 'approved':
                raise UserError('No es posible Deshacer esta Certificación porque contiene Etapa Aprobada')
            line.certification_line_id.certif_qty = line.certification_line_id.certif_qty - line.quantity_to_cert if (line.certification_line_id.certif_qty - line.quantity_to_cert) >= 0 else 0
            line.certification_line_id.certif_percent = line.certification_line_id.certif_percent - line.certif_percent if(line.certification_line_id.certif_percent - line.certif_percent) >= 0 else 0
            line.certification_line_id.onchange_percent()
            line.concept_id.onchange_percent_certification()
            line.concept_id.onchange_qty_certification()
            line.quantity_to_cert = 0
            line.certif_percent = 0

    def rectify_by_fixed(self):
        for line in self.concept_ids:
            line.concept_id.quantity_cert = line.concept_id.quantity_cert - line.quantity_to_cert if (line.concept_id.quantity_cert - line.quantity_to_cert) > 0 else 0
            line.concept_id.percent_cert = line.concept_id.percent_cert - line.percent_cert if (line.concept_id.percent_cert - line.percent_cert) >= 0 else 0
            line.quantity_to_cert = 0
            line.percent_cert = 0

    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError('No es posible eliminar una Certificación Aplicada. Debe primero Deshacerla y luego Eliminarla')
        return super(BimMasCertification, self).unlink()


class BimCertificationFixedCertification(models.Model):
    _name = 'bim.certification.fixed.certification'
    _description = "Certificacion por Manual"

    @api.depends('quantity_to_cert')
    def _compute_amount(self):
        for record in self:
            record.amount_certif = record.quantity_to_cert * record.amount_cert
            record.percent_cert = record.quantity_to_cert / record.quantity * 100 if record.quantity else 0

    @api.onchange('percent_cert')
    def _compute_percent_and_balance(self):
        for record in self:
            record.quantity_to_cert = record.percent_cert * record.quantity / 100 if (record.percent_cert * record.quantity) > 0 else 0
            # record.balance_cert = record.quantity_cert / record.quantity * 100 if record.quantity else 0

    parent_id = fields.Many2one(string='Capítulo', related='concept_id.parent_id', required=True)
    name = fields.Char(string='Nombre', related='concept_id.display_name', required=True)
    quantity_cert = fields.Float(string='Acumulado Cert', default=0, digits='BIM qty')
    percent_acc = fields.Float(string='(%) Acumulado', default=0, digits='BIM qty')
    quantity_to_cert = fields.Float(string='Cant Cert', default=0, digits='BIM qty')
    percent_cert = fields.Float(string='(%) Cert Pres', default=0, digits='BIM price')
    concept_id = fields.Many2one('bim.concepts', "Partida")
    balance = fields.Float(string='Total Pres', digits='BIM price')
    amount_certif = fields.Float(string='Importe Cert', digits='BIM price', compute='_compute_amount')
    amount_cert = fields.Float(string='Precio Cert', digits='BIM price')
    quantity = fields.Float(string='Cant Pres(N)', digits='BIM price')


class BimCertificationStageCertification(models.Model):
    _name = 'bim.certification.stage.certification'
    _description = "Certificacion por Etapas"

    @api.depends('stage_id', 'stage_id.state', 'budget_qty', 'quantity_to_cert', 'concept_id.amount_compute_cert')
    def _compute_amount(self):
        for record in self:
                record.amount_certif = record.quantity_to_cert * record.concept_id.amount_compute_cert

    certification_line_id = fields.Many2one('bim.certification.stage')
    name = fields.Date(string='Fecha', related='certification_line_id.name', required=True)
    certif_qty = fields.Float(string='Acumulado Cert', default=0, digits='BIM qty')
    budget_qty = fields.Float(string='Cant Pres (N)', default=0, digits='BIM qty')
    quantity_to_cert = fields.Float(string='Cant Cert (N)', default=0, digits='BIM qty')
    certif_percent = fields.Float(string='(%) Cert', default=0, digits='BIM price')
    stage_id = fields.Many2one('bim.budget.stage', "Etapa", related='certification_line_id.stage_id')
    concept_id = fields.Many2one('bim.concepts', "Partida", related='certification_line_id.concept_id')
    amount_budget = fields.Float(string='Total pres', digits='BIM price')
    amount_certif = fields.Float(string='Importe Cert', digits='BIM price', compute="_compute_amount")
    parent_id = fields.Many2one('bim.concepts', string="Capítulo")
    percent_acc = fields.Float(string='(%) Acumulado', default=0, digits='BIM qty')
    balance = fields.Float(string='Total Pres', digits='BIM price')


    @api.onchange('quantity_to_cert')
    def onchange_qty(self):
        for record in self:
            if record.concept_id.quantity <= 0:
                record.certif_percent = (record.quantity_to_cert / 1) * 100
            else:
                record.certif_percent = (record.quantity_to_cert / record.concept_id.quantity) * 100

    @api.onchange('certif_percent')
    def onchange_percent(self):
        for record in self:
            record.quantity_to_cert = (record.concept_id.quantity * record.certif_percent) / 100

    def action_next(self):
        if self.stage_state == 'draft':
            self.stage_id.state = 'process'
        elif self.stage_state == 'process':
            self.stage_id.state = 'approved'

    def action_cancel(self):
        return self.stage_id.write({'state': 'cancel'})

