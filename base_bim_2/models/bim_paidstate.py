# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class bim_paidstate(models.Model):
    _description = "Estado Pagos"
    _name = 'bim.paidstate'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char('Nombre', required=True, copy=False,
        readonly=True, index=True, default=lambda self: 'Nuevo')
    project_id = fields.Many2one('bim.project', 'Obra',
        states={'draft': [('readonly', False)]}, required=True, readonly=True,
        change_default=True, index=True)
    amount = fields.Monetary('Importe', compute='_amount_compute')
    progress = fields.Float('% Avance', help="Porcentaje de avance", compute='compute_progress')
    date = fields.Date(string='Fecha', required=True,
        readonly=True, index=True, states={'draft': [('readonly', False)]},
        copy=False, default=fields.Datetime.now)
    currency_id = fields.Many2one('res.currency', string='Moneda',
        required=True, default=lambda r: r.env.user.company_id.currency_id,
        track_visibility='always')
    invoice_id = fields.Many2one('account.move', string='Factura', readonly=True)
    maintenance_id = fields.Many2one('bim.maintenance', string='Mantenimiento de Obra', readonly=True)
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company, required=True)
    lines_ids = fields.One2many('bim.paidstate.line', 'paidstate_id', 'Líneas')
    state = fields.Selection(
        [('draft', 'Borrador'),
         ('validated', 'Validado'),
         ('invoiced', 'Facturado')],
        'Estatus', readonly=True, copy=False,
        index=True, track_visibility='onchange', default='draft')
    apply_retention = fields.Boolean(string='Aplicar Retención', default=True)
    paidstate_retention = fields.Float(string='Retención por Garantía', compute='compute_retention', store=True)
    paidstate_company_retention = fields.Float(string='% Retención Obra', related='project_id.retention')
    paidstate_notes = fields.Text()

    @api.depends('amount')
    def compute_progress(self):
        for record in self:
            paidstate_ids = self.env['bim.paidstate'].search([('project_id','=',record.project_id.id)])
            amount_total = 0
            for paidstate in paidstate_ids:
                amount_total += paidstate.amount
            record.progress = amount_total / record.project_id.balance * 100 if record.project_id.balance > 0 else 0

    @api.depends('lines_ids')
    def compute_retention(self):
        for record in self:
            if record.apply_retention:
                record.paidstate_retention = -0.01 * record.amount * record.project_id.retention
            else:
                record.paidstate_retention

    @api.depends('lines_ids')
    def _amount_compute(self):
        for record in self:
            record.amount = sum(line.amount for line in record.lines_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', "Nuevo") == "Nuevo":
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.paidstate') or "Nuevo"
        return super(bim_paidstate, self).create(vals)

    def action_validate(self):
        self.write({'state': 'validated'})

    def action_invoice(self):
        invoice_obj = self.env['account.move']
        record = self
        #Si el estado de pago proviene de un mantenimiento entonces toma el producto configurado en Ajustes para mantenimiento
        if not record.maintenance_id:
            if record.project_id.paidstate_product:
                product = self.project_id.paidstate_product
            else:
                product = self.env.user.company_id.paidstate_product
        else:
            product = self.env.user.company_id.paidstate_product_mant
        if record.project_id.retetion_product:
            retetion_product = self.project_id.retetion_product
        else:
            retetion_product = self.env.user.company_id.retetion_product
        if not record.project_id.customer_id:
            raise UserError('De agregarle un cliente a la obra para facturar')
        if not product:
            raise UserError('Defina un producto para facturar los Estados de Pago directamente en la Obra. Tambien puede ingresar en BIM / Configuracion / Ajustes y configurar uno predeterminado')
        if not retetion_product:
            raise UserError(
                'Defina un producto para facturar la retención en los Estados de Pago directamente en la Obra. Tambien puede ingresar en BIM / Configuracion / Ajustes y configurar uno predeterminado')
        income_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        retention_account = retetion_product.property_account_income_id or retetion_product.categ_id.property_account_income_categ_id
        if not retention_account:
            raise UserError('No existe una cuenta de ingresos en el producto de retención o en su categoria')
        if not income_account:
            raise UserError('No existe una cuenta de ingresos en el producto o en su categoria')
        journal = self.env.user.company_id.journal_id.id
        if not journal:
            raise UserError('No ha configurado un Diario de Ventas')
        ###################################################
        invoice_vals = {
            'type': 'out_invoice',
            'partner_id': record.project_id.customer_id.id,
            'partner_shipping_id': record.project_id.customer_id.id,
            'journal_id': journal,
            'currency_id': self.env.user.company_id.currency_id.id,
            'invoice_date': record.date,
            'invoice_user_id': self.env.user.id,
            'invoice_line_ids': [],
            'narration': self.paidstate_notes
        }
        for line in record.lines_ids:

            invoice_vals['invoice_line_ids'].append(
                (0, 0,
                 {
                    'name': '%s - %s'%(record.name, record.project_id.nombre[0:40]),
                    'sequence': 1,
                    'account_id': income_account.id,
                    'analytic_account_id': record.project_id.analytic_id and record.project_id.analytic_id.id or False,
                    'price_unit': record.currency_id.with_context(date=record.date).compute(line.amount, self.env.user.company_id.currency_id, round=False),
                    'quantity': line.quantity,
                    'product_uom_id': product.uom_id.id,
                    'product_id': product.id,
                    'tax_ids': [(6, 0, product.taxes_id.ids)],
                  }))
        #Agregamos el PRODUCTO DE RETENCION
        invoice_vals['invoice_line_ids'].append(
            (0, 0,
             {
                 'name': '%s - %s - %s' % (record.name, record.project_id.nombre[0:40], str(record.project_id.retention) + '%'),
                 'sequence': 1,
                 'account_id': retention_account.id,
                 'analytic_account_id': record.project_id.analytic_id and record.project_id.analytic_id.id or False,
                 'price_unit': record.paidstate_retention,
                 'quantity': 1,
                 'product_uom_id': product.uom_id.id,
                 'product_id': retetion_product.id,
                 'tax_ids': [(6, 0, retetion_product.taxes_id.ids)],
             }))
        ###################################################
        invoice = invoice_obj.create(invoice_vals)
        record.invoice_id = invoice.id
        record.project_id.write({'invoice_ids': [(4, invoice.id)]})
        if record.maintenance_id:
            record.maintenance_id.invoice_id = invoice.id
            record.maintenance_id.write({'invoice_ids': [(4, invoice.id)]})
        self.write({'state': 'invoiced'})
        action = self.env.ref('account.action_move_out_invoice_type')
        result = action.read()[0]
        res = self.env.ref('account.view_move_form', False)
        result['views'] = [(res and res.id or False, 'form')]
        result['res_id'] = invoice.id
        return result

    @api.onchange('lines_ids')
    def onchange_lines_ids(self):
        for record in self:
            record.amount = sum(x.amount for x in record.lines_ids)



class BimPaidstateLine(models.Model):
    _description = "Indicadores comparativos"
    _name = 'bim.paidstate.line'

    name = fields.Char('Descripcion', required=True)
    quantity = fields.Integer('Cantidad', default=1)
    percent = fields.Float('%', help="Porcentaje dado por el valor real entre valor estimado", store=True)
    price_unit = fields.Float("Precio")
    amount = fields.Float('Importe', compute='_amount_compute', store=True)
    paidstate_id = fields.Many2one('bim.paidstate', 'Estado Pago', ondelete="cascade")
    project_id = fields.Many2one('bim.project', 'Obra', related='paidstate_id.project_id')
    budget_id = fields.Many2one('bim.budget', 'Presupuesto')
    loaded = fields.Boolean(default=False)

    @api.onchange('budget_id')
    def onchange_budget_id(self):
        budget_list = []
        if self.paidstate_id:
            budget_list.append(self.paidstate_id.project_id.id)
        return {'domain': {'budget_id': [('project_id','in',budget_list)]}}

    @api.onchange('budget_id')
    def onchange_name(self):
        name_list = []
        if self.budget_id:
            name_list.append(self.budget_id.name)
        self.name = name_list and '-'.join(name_list) or ''

    @api.depends('quantity','price_unit')
    def _amount_compute(self):
        for record in self:
            record.amount = record.quantity * record.price_unit

