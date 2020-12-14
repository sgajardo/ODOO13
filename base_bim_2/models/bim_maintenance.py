# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo.tools.misc import formatLang, format_date, get_lang

class BimMaintenance(models.Model):
    _name = "bim.maintenance"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = "Ordenes Mantenimiento BIM"
    _order = 'id desc'

    @api.depends('line_ids.price_subtotal')
    def _compute_total(self):
        for record in self:
            record.amount_total = sum(x.price_subtotal for x in record.line_ids)

    @api.depends('requisition_ids')
    def _compute_req_count(self):
        for project in self:
            project.req_count = len(project.requisition_ids)

    def _compute_invoice(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    name = fields.Char(string='Referencia', required=True, copy=False,
        readonly=True, states={'draft': [('readonly', False)]},
        index=True, default=lambda self: 'Nuevo')
    state = fields.Selection([
        ('draft', 'Nuevo'),
        ('planned', 'Programado'),
        ('done', 'Ejecutado'),
        ('invoiced', 'Facturado'),
        ('cancel', 'Cancelado'),
        ], string='Estado', readonly=True, copy=False, index=True,
        track_visibility='onchange', default='draft')
    date_planned = fields.Datetime(string='Fecha Estimada', required=True,
        readonly=True, index=True, states={'draft': [('readonly', False)]},
        copy=False, default=fields.Datetime.now)
    date_done = fields.Datetime(string='Fecha Ejecución',
        readonly=True, index=True, states={'draft': [('readonly', False)]},
        copy=False, default=fields.Datetime.now)
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True,
        states={'draft': [('readonly', False)]}, required=True, change_default=True,
        index=True, track_visibility='always')
    project_id = fields.Many2one('bim.project', 'Obra', readonly=True,
        required=True, copy=False, states={'draft': [('readonly', False)]})
    invoice_ids = fields.One2many('account.move', 'maintenance_id', 'Facturas')
    invoice_count = fields.Integer('Facturas', compute=_compute_invoice)
    invoice_id = fields.Many2one('account.move', string='Factura', readonly=True)
    note = fields.Text('Observaciones')
    user_id = fields.Many2one('res.users', string='Responsable',
        states={'draft': [('readonly', False)]}, index=True,
        track_visibility='onchange', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', 'Compañía', default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", related='company_id.currency_id',
        string="Moneda", readonly=True, required=True)
    line_ids = fields.One2many('bim.maintenance.line', 'maintenance_id',
        string='Líneas', states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    amount_total = fields.Monetary('Total', compute="_compute_total", store=True)
    requisition_ids = fields.One2many('bim.purchase.requisition','maintenance_id','Sol. de Materiales')
    req_count = fields.Integer('Cantidad Sol Materiales', compute="_compute_req_count")
    maintenance_duration = fields.Integer('Duración Estimada (días)', default=1)
    department_id = fields.Many2one('bim.department', 'Departamento', related="project_id.department_id", store=True)
    invoice_amount = fields.Monetary('Monto a Facturar')
    maintenance_currency_id = fields.Many2one('res.currency', 'Moneda', related="project_id.maintenance_currency_id",
                                              store=True)
    reminder = fields.Boolean('recordatorio', compute='compute_reminder')
    days_reminder = fields.Integer('dias recordatorio', compute='compute_days_reminder')

    def compute_days_reminder(self):
        for record in self:
            today = fields.Datetime.now()
            rest = 0
            if format_date(record.env, today) <= format_date(record.env, record.date_planned):
                rest = record.date_planned - today
            if record.name == "Nuevo":
                record.days_reminder = rest.days + 1
            else:
                record.days_reminder = 0

    def compute_reminder(self):
        for record in self:
            today = fields.Datetime.now()
            reminder = False
            for day in record.company_id.array_day_ids:
                date_reminder = today + timedelta(days=day.name)
                date_reminder = format_date(self.env, date_reminder)
                date_planned = format_date(self.env, record.date_planned)
                if date_reminder == date_planned:
                    reminder = True
                    break
            if reminder:
                record.reminder = reminder
            else:
                record.reminder = False

    def action_send(self):
        maintenances = self.env['bim.maintenance'].search([])
        for mant in maintenances:
            if mant.reminder:
                template = mant.company_id.template_mant_id
                mail = template.send_mail(mant.id, force_send=True)
                if mail:
                    mant.message_post(
                        body=_("Enviado email a Soporte: %s" % mant.project_id.customer_id.name))

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.maintenance') or 'Nuevo'
        maintenance = super(BimMaintenance, self).create(vals)
        return maintenance

    @api.onchange('project_id')
    def onchange_project_id(self):
        if self.project_id:
            self.partner_id = self.project_id.customer_id.id

    def action_programmed(self):
        self.write({'state': 'planned'})

    def action_executed(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_view_req(self):
        reqs = self.mapped('requisition_ids')
        action = self.env.ref('base_bim_2.action_bim_purchase_requisition').read()[0]
        action['domain'] = [('id', 'in', reqs.ids)]
        return action

    def generate_bim_req(self):
        self.ensure_one()
        req_lines = []
        for line in self.line_ids:
            if line.product_id.type != 'service' and line.product_id.resource_type in ['HR','M','Q'] and line.quantity > 0.0:
                req_lines.append((0,0,{
                    'product_id': line.product_id.id,
                    'um_id': line.uom_id.id,
                    'quant': line.quantity
                }))
        if len(req_lines) == 0:
            raise UserError(u'No hay productos por realizar solicitud')
        requisition = self.env['bim.purchase.requisition'].create({
            'user_id': self.user_id.id,
            'project_id': self.project_id.id,
            'date_begin': datetime.now(),
            'product_ids': req_lines,
            'maintenance_id': self.id
        })
        action = self.env.ref('base_bim_2.action_bim_purchase_requisition')
        result = action.read()[0]
        res = self.env.ref('base_bim_2.view_form_bim_purchase_requisition', False)
        result['views'] = [(res and res.id or False, 'form')]
        result['res_id'] = requisition.id
        return result

    def generate_paidstate(self):
        self.ensure_one()
        order_lines = []
        line_vals = {
            'name': 'Mantenimiento' + self.project_id.name,
            'price_unit': self.amount_total,
            'quantity': 1,
        }
        order_lines.append((0, 0, line_vals))

        epaid = self.env['bim.paidstate'].create({
            'project_id': self.project_id.id,
            'amount': self.invoice_amount,
            'currency_id': self.maintenance_currency_id.id,
            'maintenance_id': self.id,
            'lines_ids': order_lines
        })
        self.state = 'invoiced'
        action = self.env.ref('base_bim_2.action_bim_paidstate')
        result = action.read()[0]
        res = self.env.ref('base_bim_2.view_form_bim_paidstate', False)
        result['views'] = [(res and res.id or False, 'form')]
        result['res_id'] = epaid.id
        return result

    def action_view_invoices(self):
        invoices = []
        for inv in self.invoice_ids:
            if inv.type == 'out_invoice':
                invoices.append(inv.id)
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(invoices) > 0:
            action['domain'] = [('id', 'in', invoices)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

class BimMaintenanceLine(models.Model):
    _name = 'bim.maintenance.line'
    _description = 'Lineas de mantenimiento'

    @api.depends('quantity','price_unit')
    def _compute_subtotal(self):
        for record in self:
            record.price_subtotal = record.quantity * record.price_unit

    name = fields.Char('Descripción')
    product_id = fields.Many2one('product.product', string='Producto')
    uom_id = fields.Many2one('uom.uom', 'UdM', related="product_id.uom_id", readonly=True)
    quantity = fields.Float("Cantidad")
    price_unit = fields.Float("Precio")
    price_subtotal = fields.Float("Importe", compute='_compute_subtotal')
    maintenance_id = fields.Many2one('bim.maintenance', string="Mantenimiento", ondelete='cascade')

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.name = self.product_id.name

class BimMaintenanceTagsDays(models.Model):
    _name = "bim.maintenance.tags.days"
    _description = "Dias restantes mantenimiento"

    name = fields.Integer('Días')