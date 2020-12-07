# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class TicketBim(models.Model):
    _description = "Ticket Bim"
    _name = 'ticket.bim'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    _order = 'id desc'

    @api.model
    def _needaction_domain_get(self):
        return [('state', '!=', 'resuelto')]

    name = fields.Char('Código', default="Nuevo", copy=False)
    title = fields.Char('Título', size=100)
    obs = fields.Text('Observación')
    obs_solucion = fields.Text('Observación Solución')
    entry_date = fields.Datetime(
        'Fecha de Entrada', default=fields.Datetime.now)
    end_date = fields.Datetime('Fecha de Salida')
    end_will_end = fields.Datetime('Fecha Prevista')
    user_id = fields.Many2one('res.users', string='Creado',
                              default=lambda self: self.env.user)

    category_id = fields.Many2one('ticket.bim.category', string='Categoría')
    ticket_id = fields.Many2one('ticket.bim', string='Ticket Relacionado')
    project_id = fields.Many2one('bim.project', 'Obra', ondelete="cascade")

    numero_veces = fields.Integer('Número Veces', default=1)

    user_error_id = fields.Many2one(
        'res.users', string='Usuario', default=lambda self: self.env.user)

    user_work_id = fields.Many2one('res.users', string='Especialista')

    comprobante_01_name = fields.Char("Adjunto")
    comprobante_01 = fields.Binary(
        string='Adjunto',
        copy=False,
        help='Adjunto')

    company_id = fields.Many2one(
        'res.company', string="Compañia", required=True,
        default=lambda self: self.env.user.company_id.id)

    state = fields.Selection([
        ('borrador', 'Borrador'),
        ('aprobado', 'Aprobado'),
        ('trabajando', 'Trabajando'),
        ('resuelto', 'Resuelto'),
        ('calificado', 'Calificado')],
        string='Estatus', index=True, readonly=True, default='borrador',
        copy=False)

    clasificacion = fields.Selection([
        ('soporte', 'Soporte'),
        ('desarrollo', 'Desarrollo')],
        string='Clasificación', index=True, default='soporte', copy=False)

    calificacion = fields.Selection([
        ('0', 'Malo'),
        ('1', 'Regular'),
        ('2', 'Bueno'),
        ('3', 'Excelente')],
        string='Calificación', default='0', copy=False)

    obs_calificacion = fields.Text('Nota Calificación')

    prioridad = fields.Selection(
        [('baja', 'Baja'),
         ('media', 'Media'),
         ('alta', 'Alta')],
        default='baja', copy=False)


    def exe_autorizar(self):
        for record in self:
            record.state = 'aprobado'
            record.message_post(
                body=_("Ticket Aprobado por: %s") % record.env.user.name)

    def exe_work(self):
        for record in self:
            record.user_work_id = record.env.user
            record.state = 'trabajando'
            record.message_post(
                body=_("Iniciando el trabajo: %s") % record.env.user.name)

    def exe_resuelto(self):
        for record in self:
            record.user_work_id = record.env.user
            record.state = 'resuelto'
            record.message_post(body=_("Nota Solución: %s") %
                                record.obs_solucion)
            record.end_date = fields.Datetime.now()

            """
            template = self.env.ref('ticket_pro.email_ticket_close')
            if record.comprobante_01:
                attachment = self.env['ir.attachment'].create({
                    'name': record.comprobante_01_name,
                    'datas': record.comprobante_01,
                    'datas_fname': record.comprobante_01_name,
                    'res_model': 'ticket.pro',
                    'type': 'binary'
                })
                template.attachment_ids = [(6, 0, attachment.ids)]
            mail = template.send_mail(record.id, force_send=True)  # envia mail
            if mail:
                record.message_post(
                    body=_("Aviso Ticket Terminado: %s" % record.category_id.name))"""

    def exe_abrir(self):
        for record in self:
            record.numero_veces = record.numero_veces + 1
            record.state = 'borrador'
            record.message_post(body=_("Se Abre de nuevo: %s") %
                                record.env.user.name)
            """
            template = self.env.ref('ticket_pro.email_ticket_pro_open')
            if self.comprobante_01:
                attachment = self.env['ir.attachment'].create({
                    'name': self.comprobante_01_name,
                    'datas': self.comprobante_01,
                    'datas_fname': self.comprobante_01_name,
                    'res_model': 'ticket.pro',
                    'type': 'binary'
                })
                template.attachment_ids = [(6, 0, attachment.ids)]
            mail = template.send_mail(self.id, force_send=True)  # envia mail
            if mail:
                self.message_post(
                    body=_("Enviado email a Soporte: %s" % self.category_id.name))
                    """

    def exe_close(self):
        if self.calificacion == '0':
            raise ValidationError(
                "Por favor califica nuestro trabajo así mejoramos con tu ayuda, muchas gracias.")
        for record in self:
            record.state = 'calificado'
            record.message_post(body=_("Calificado como: %s") %
                                record.calificacion)

    @api.model
    def create(self, vals):
        if vals.get('name', "Nuevo") == "Nuevo":
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'ticket.bim') or "Nuevo"
        if 'category_id' not in vals:
            vals['category_id'] = self.env.ref('base_bim_2.ticket_proc_01').id
        ticket = super(TicketBim, self).create(vals)
        """
        template = self.env.ref('base_bim_2.email_ticket_pro')
        attachment = False
        if ticket.comprobante_01:
            attachment = self.env['ir.attachment'].create({
                'name': ticket.comprobante_01_name,
                'datas': ticket.comprobante_01,
                'datas_fname': ticket.comprobante_01_name,
                'res_model': 'ticket.pro',
                'type': 'binary'
            })
        template.attachment_ids = [
            (6, 0, attachment.ids)] if attachment else [(5,)]
        mail = template.send_mail(ticket.id, force_send=True)  # envia mail
        if mail:
            ticket.message_post(
                body=_("Enviado email a Soporte: %s" % ticket.category_id.name))
                """
        return ticket

