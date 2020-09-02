# coding: utf-8
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    journal_id = fields.Many2one('account.journal', string='Diario')
    bim_hours = fields.Integer('Horas de Trabajo Diaria', default=8)
    validate_stock = fields.Boolean('Validar Movimientos de Stock', default=True)
    working_hours = fields.Float('Jornada Laboral', help="Indica el número de horas de un día o jornada laboral", default=9.0)
    extra_hour_factor = fields.Float('Factor Hora Extra', digits=(12, 8), help="Indica el factor para el cálculo de la hora extra", default=0.0077777)
    paidstate_product = fields.Many2one('product.product', 'Producto Estado Pago', help="Producto que se utilizará para facturar el estado de pago de la obra. Dejar precios en cero")
    paidstate_product_mant = fields.Many2one('product.product', 'Estado Pago Mantenimiento', help="Producto que se utilizará para facturar el estado de pago del mantenimiento de la obra. Dejar precios en cero")
    stock_location_mobile = fields.Many2one('stock.location', 'Ubicación Almacen Movil', help="Ubicación que se usará por defecto para la entrada de mercancia en el Almacen Movil")
    type_work = fields.Selection([
        ('cost', 'Coste'),
        ('price', 'Precio')],
        string="Precio en Presupuesto", default='cost')
    asset_template_id = fields.Many2one(
        'bim.assets.template',
        'Plantilla Haberes y Descuentos',
        default=lambda self: self.env.ref('base_bim_2.bim_asset_template_base', raise_if_not_found=False),
        help='Plantilla de Haberes y Descuentos que se usará al crear un presupuesto')
    array_day_ids = fields.Many2many('bim.maintenance.tags.days')
    template_mant_id = fields.Many2one('mail.template', string='Plantilla Mail')
    bim_product_category_id = fields.Many2one('product.category', required=True, default=lambda self: self.env.ref('product.product_category_all', raise_if_not_found=False))
    
    # bim_general_expenses = fields.Float('Gastos Generales Mínimos %', default=22.0)
    # bim_utility = fields.Float('Utilidad Obra Mínima%', default=15.0)
    # generate_mrp = fields.Boolean('Generar Producción desde Sol. de Materiales')
    # expense_type_ids = fields.Many2many('bim.expense.type', string="Gastos Logísticos", help="Defina los gastos logísticos a analizar en las Obras o Proyectos")
    # bim_calendar_id = fields.Many2one('resource.calendar',  default=lambda self: self.env.ref('base_bim_2.bim_base_calendar', raise_if_not_found=False), help='Calendario base para BIM')
    # expense_type_ids = fields.Many2many('bim.expense.type', string="Gastos Logísticos",help="Defina los gastos logísticos a analizar en las Obras o Proyectos")
    # bim_req_follower_ids = fields.Many2many('res.users',string='Seguidores requisiciones')


# class BimExpenseType(models.Model):
#     _name = 'bim.expense.type'
#     _description = 'Tipos de gastos'
#
#     name = fields.Char('Nombre', required=True)
#     tag_ids = fields.Many2many('bim.expense.type.tag', string="Palabras Clave")
#
# class BimExpenseTypeTag(models.Model):
#     _name = 'bim.expense.type.tag'
#     _description = 'Etiquetas de Gastos'
#
#     name = fields.Char('Nombre', required=True)
