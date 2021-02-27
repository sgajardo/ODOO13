# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class BimMasterChecklist(models.Model):
    _name = 'bim.master.checklist'
    _description = 'Plantilla Checklist'

    code = fields.Char(string='Código', readonly=True, index=True, default=lambda self: 'Nuevo', required=True)
    name = fields.Char(string='Nombre', required=True)
    checklist_line_ids = fields.One2many("bim.master.checklist.line", "checklist_id", string="Lista", required=True)

    @api.model
    def create(self, vals):
        if vals.get('code', "Nuevo") == "Nuevo":
            vals['code'] = self.env['ir.sequence'].next_by_code('bim.master.checklist') or "Nuevo"
        return super(BimMasterChecklist, self).create(vals)

class BimMasterChecklistLine(models.Model):
    _name = 'bim.master.checklist.line'
    _description = 'Líneas Plantilla Checklist'

    item_id = fields.Many2one(comodel_name="bim.checklist.items", string='Descripción', required=True)
    type = fields.Selection(string="Tipo", selection=[('check', 'Check'),
                                                      ('yesno', 'Si / No'),
                                                      ('txt', 'Texto'),
                                                      ('int', 'Valor Numerico')], default="check")
    checklist_id = fields.Many2one("bim.master.checklist", string="Checklist")
    sequence = fields.Integer(string='Sequence', default=10)

class BimChecklist(models.Model):
    _name = 'bim.checklist'
    _description = 'Bim Checklist'

    name = fields.Char(string='Nombre')
    code = fields.Char(string='Código', readonly=True, index=True, default=lambda self: 'Nuevo', required=True)
    date = fields.Date('Fecha',default=fields.Date.today)
    user_id = fields.Many2one(comodel_name='res.users', string='Responsable')
    project_id = fields.Many2one("bim.project", string="Obra")
    checklist_line_ids = fields.One2many("bim.checklist.line", "checklist_id", string="Lista")
    checklist_image_ids = fields.One2many("bim.checklist.images", "checklist_id", string="Imagenes")
    obs = fields.Text(string="Observaciones")
    digital_signature = fields.Binary(string='Signature')

    @api.model
    def create(self, vals):
        if vals.get('code', "Nuevo") == "Nuevo":
            vals['code'] = self.env['ir.sequence'].next_by_code('bim.checklist') or "Nuevo"
        return super(BimChecklist, self).create(vals)

    def action_checklist_send(self):
        '''
        Esta función abre una ventana con una plantilla de correo para enviar el Checklist por correo
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('base_bim_2', 'email_template_checklist')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'bim.checklist',
            'active_model': 'bim.checklist',
            'active_id': self.ids[0],
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_email': True,
            'mark_so_as_sent': True,
        })

        # In the case of a RFQ or a PO, we want the "View..." button in line with the state of the
        # object. Therefore, we pass the model description in the context, in the language in which
        # the template is rendered.
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_template(template.lang, ctx['default_model'], ctx['default_res_id'])

        self = self.with_context(lang=lang)

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

class BimChecklistLine(models.Model):
    _name = 'bim.checklist.line'
    _description = 'Lista Checklist'

    @api.model
    def default_get(self, default_fields):
        values = super(BimChecklistLine, self).default_get(default_fields)
        values['sequence'] = len(self.checklist_id.checklist_line_ids) + 1
        return values

    item_id = fields.Many2one("bim.checklist.items", string='Descripción', required=True)
    is_ready = fields.Boolean(string='Status')
    is_ready_c = fields.Char(string='Valor')
    #notes_id = fields.Many2one(comodel_name="bim.checklist.notes", string="Observaciones")
    checklist_id = fields.Many2one("bim.checklist", string="Checklist")
    sequence = fields.Integer(string='Sequence')
    type = fields.Selection([
        ('check', 'Check'),
        ('yesno', 'Si / No'),
        ('txt', 'Texto'),
        ('int', 'Valor Numerico')],string="Tipo")


class BimChecklistImages(models.Model):
    _name = 'bim.checklist.images'
    _description = 'Imagenes Checklist'
    _inherit = ['image.mixin']

    name = fields.Char(string='Descripción')
    checklist_id = fields.Many2one('bim.checklist', string='Checklist')

class BimChecklistNotes(models.Model):
    _name = 'bim.checklist.items'
    _description = 'Items Checklist'

    name = fields.Text(string='Descripción')
