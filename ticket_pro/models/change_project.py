# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ChangeProject(models.Model):
    _description = "Change Project"
    _name = 'change.project'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    _order = 'id desc'

    @api.model
    def _needaction_domain_get(self):
        return [('state', '!=', 'resuelto')]

    name = fields.Char('Código', default="Nuevo", copy=False)
    title = fields.Char('Título', default="Reunión")
    obs = fields.Text('Observación')
    obs_solucion = fields.Text('Observación Solución')
    entry_date = fields.Datetime(
        'Fecha de Entrada', default=fields.Datetime.now)
    end_date = fields.Datetime('Fecha de Salida')
    end_will_end = fields.Datetime('Fecha Prevista')
    user_id = fields.Many2one('res.users', string='Creado',
                              default=lambda self: self.env.user)

    notas = fields.Char('Notas')

    category_id = fields.Many2one('ticket.category', string='Categoría')
    ticket_id = fields.Many2one('ticket.pro', string='Ticket Soporte')

    total_horas = fields.Float('Horas', compute='_total_price_sum')
    total_price = fields.Float('Precio Total', compute='_total_price_sum')

    api.depends('hours_ids')
    def _total_price_sum(self):
        suma = 0
        suma_horas = 0

        for move in self:
            for line in move.hours_ids:
                suma += line.total_price
                suma_horas += line.cant_horas

            move.total_price = suma
            move.total_horas = suma_horas

    user_error_id = fields.Many2one(
        'res.users', string='Usuario', default=lambda self: self.env.user)

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

    def exe_autorizar_2(self):
        for record in self:
            record.state = 'aprobado'
            record.message_post(
                body=_("Ticket Aprobado por: %s") % record.env.user.name)

    def exe_work_2(self):
        for record in self:
            record.user_work_id = record.env.user
            record.state = 'trabajando'
            record.message_post(
                body=_("Iniciando el trabajo: %s") % record.env.user.name)

    def exe_resuelto_2(self):
        for record in self:
            record.user_work_id = record.env.user
            record.state = 'resuelto'
            record.message_post(body=_("Nota Solución: %s") %
                                record.obs_solucion)
            record.end_date = fields.Datetime.now()

    def exe_abrir_2(self):
        for record in self:
            # record.numero_veces = record.numero_veces + 1
            record.state = 'borrador'
            record.message_post(body=_("Se Abre de nuevo: %s") %
                                record.env.user.name)

    def exe_close_2(self):
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
                'change.project') or "Nuevo"
        ticket = super(ChangeProject, self).create(vals)
        template = self.env.ref('ticket_pro.email_change_project')
        if ticket.comprobante_01:
            attachment = self.env['ir.attachment'].create({
                'name': ticket.comprobante_01_name,
                'datas': ticket.comprobante_01,
                'datas_fname': ticket.comprobante_01_name,
                'res_model': 'change.project',
                'type': 'binary'
            })
            template.attachment_ids = [(6, 0, attachment.ids)]
        mail = template.send_mail(ticket.id, force_send=True)  # envia mail
        if mail:
            ticket.message_post(
                body=_("Enviado email al Cliente: %s" % ticket.category_id.name))
        return ticket

    hours_ids = fields.One2many(
        'hours.task', 'cambios_id', string='Listado Horas')


class HoursTask(models.Model):
    _name = 'hours.task'
    _description = 'Horas de Tareas'
    user_id = fields.Many2one(
        'res.users', string='Usuario', default=lambda self: self.env.user)
    cant_horas = fields.Float('Cantidad Horas')
    entry_date = fields.Datetime(
        'Fecha de Entrada', default=fields.Datetime.now)
    cambios_id = fields.Many2one(
        'change.project', 'cambios', ondelete='cascade')

    calificacion = fields.Selection([
        ('0', 'Desarrollo'),
        ('1', 'QA'),
        ('2', 'Reunión'),
        ('3', 'Otros')],
        string='Tipo', default='0', copy=False)

    unit_price = fields.Float('Precio Unitario')
    total_price = fields.Float('Precio Total', compute='_total_price')

    def _total_price(self):
        for row in self:
            price = row.unit_price * row.cant_horas
            row.total_price = price
