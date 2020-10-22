# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError

class bim_paidstate(models.Model):
    _description = "Estado Pagos"
    _name = 'bim.paidstate'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    """
    @api.depends('project_id')
    def compute_progress(self):
        for record in self:
            record.progress = 0.0"""

    name = fields.Char('Nombre', required=True, copy=False,
        readonly=True, index=True, default=lambda self: 'Nuevo')
    project_id = fields.Many2one('bim.project', 'Obra',
        states={'draft': [('readonly', False)]}, required=True, readonly=True,
        change_default=True, index=True)
    budget_id = fields.Many2one('bim.budget', 'Presupuesto',
        states={'draft': [('readonly', False)]}, required=True, readonly=True,
        change_default=True, index=True)
    stage_id = fields.Many2one('bim.budget.stage', "Etapa",
        states={'draft': [('readonly', False)]}, readonly=True)
    state = fields.Selection(
        [('draft', 'Borrador'),
         ('validated', 'Validado'),
         ('invoiced', 'Facturado')],
        'Estatus', readonly=True, copy=False,
        index=True, track_visibility='onchange', default='draft')
    amount = fields.Monetary('Importe', states={'draft': [('readonly', False)]},
        required=True, readonly=True)
    progress = fields.Float('% Avance', help="Porcentaje de avance")
    date = fields.Date(string='Fecha', required=True,
        readonly=True, index=True, states={'draft': [('readonly', False)]},
        copy=False, default=fields.Datetime.now)
    currency_id = fields.Many2one('res.currency', string='Moneda',
        required=True, default=lambda r: r.env.user.company_id.currency_id,
        track_visibility='always')
    invoice_id = fields.Many2one('account.move', string='Factura', readonly=True)
    maintenance_id = fields.Many2one('bim.maintenance', string='Mantenimiento de Obra', readonly=True)
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company, required=True )

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
        if not record.project_id.customer_id:
            raise UserError('De agregarle un cliente a la obra para facturar')
        if not product:
            raise UserError('Defina un producto para facturar los Estados de Pago directamente en la Obra. Tambien puede ingresar en BIM / Configuracion / Ajustes y configurar uno predeterminado')
        income_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        if not income_account:
            raise UserError('No existe una cuenta de ingresos en el producto o en su categoria')
        journal = self.env.user.company_id.journal_id.id
        if not journal:
            raise UserError('No ha configurado un Diario de Ventas')
        invoice_vals = {
            'type': 'out_invoice',
            'partner_id': record.project_id.customer_id.id,
            'partner_shipping_id': record.project_id.customer_id.id,
            'journal_id': journal,
            'currency_id': self.env.user.company_id.currency_id.id,
            'invoice_date': record.date,
            'invoice_user_id': self.env.user.id,
            #'document_class_id': class_id.id,
            'invoice_line_ids': [(0,0,{
                'name': '%s - %s'%(record.name, record.project_id.nombre[0:40]),
                'sequence': 1,
                'account_id': income_account.id,
                'analytic_account_id': record.project_id.analytic_id and record.project_id.analytic_id.id or False,
                'price_unit': record.currency_id.with_context(date=record.date).compute(record.amount, self.env.user.company_id.currency_id, round=False),
                'quantity': 1.0,
                'product_uom_id': product.uom_id.id,
                'product_id': product.id,
                'tax_ids': [(6, 0, product.taxes_id.ids)],
            })]
        }
        invoice = invoice_obj.create(invoice_vals)
        record.invoice_id = invoice.id
        record.project_id.write({'invoice_ids': [(4, invoice.id)]})
        if record.maintenance_id:
            record.maintenance_id.invoice_id = invoice.id
            record.maintenance_id.write({'invoice_ids': [(4, invoice.id)]})
        self.write({'state': 'invoiced'})
        action = self.env.ref('account.action_move_out_invoice_type')
        result = action.read()[0]
        res = self.env.ref('account.invoice_form', False)
        result['views'] = [(res and res.id or False, 'form')]
        result['res_id'] = invoice.id
        return result

    lines_ids = fields.One2many('bim.paidstate.line', 'paidstate_id', 'Líneas')

    @api.onchange('lines_ids')
    def onchange_lines_ids(self):
        for record in self:
            record.amount = sum(x.amount for x in record.lines_ids)

class BimPaidstateLine(models.Model):
    _description = "Indicadores comparativos"
    _name = 'bim.paidstate.line'

    name = fields.Many2one('bim.object', string='Objeto de Obra', track_visibility='onchange')
    note = fields.Char('Notas')
    percent = fields.Float('%', help="Porcentaje dado por el valor real entre valor estimado")
    amount = fields.Float('Importe', help="Monto")

    paidstate_id = fields.Many2one('bim.paidstate', 'Estado Pago', ondelete="cascade")
