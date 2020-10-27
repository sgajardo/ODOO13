# coding: utf-8
from odoo import api, fields, models


class BimConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    journal_id = fields.Many2one('account.journal', string='Diario', related="company_id.journal_id", readonly=False)
    working_hours = fields.Float('Jornada Laboral', related ="company_id.working_hours", readonly=False)
    extra_hour_factor = fields.Float('Factor Hora Extra', related ="company_id.extra_hour_factor", readonly=False)
    paidstate_product = fields.Many2one('product.product', string='Producto Estado Pago', related ="company_id.paidstate_product", readonly=False)
    paidstate_product_mant = fields.Many2one('product.product', string='Producto Mantenimiento', related="company_id.paidstate_product_mant", readonly=False)

    # ~ retention_product = fields.Many2one('product.product', string='Producto Retención',
                                             # ~ related="company_id.retention_product", readonly=False)

    validate_stock =fields.Boolean(related="company_id.validate_stock")
    asset_template_id = fields.Many2one('bim.assets.template', related='company_id.asset_template_id', readonly=False)
    stock_location_mobile = fields.Many2one('stock.location', related='company_id.stock_location_mobile', readonly=False)
    type_work = fields.Selection([
        ('cost', 'Coste'),
        ('price', 'Precio'),
        ('pricelist', 'Tarifa')], string="Precio en Presupuesto", required=True, default='cost', related="company_id.type_work", readonly=False)
    array_day_ids = fields.Many2many('bim.maintenance.tags.days', related="company_id.array_day_ids", readonly=False)
    template_mant_id = fields.Many2one('mail.template', related="company_id.template_mant_id", string='Plantilla Mail', readonly=False)
    product_category_id = fields.Many2one('product.category', 'Categoría de producto', related='company_id.bim_product_category_id', readonly=False, required=True)

    # generate_mrp = fields.Boolean('Generar Producción desde Sol. de Materiales', related ="company_id.generate_mrp")
    # expense_type_ids = fields.Many2many('bim.expense.type', string="Gastos Logísticos", related="company_id.expense_type_ids")
    # calendar_id = fields.Many2one('resource.calendar', string='Calendario', related='company_id.bim_calendar_id')
    # follower_ids = fields.Many2many('res.users', string="Seguidores Sol. Materiales", related="company_id.bim_req_follower_ids", help="Seguidores por defecto en las solicitudes de materiales")
