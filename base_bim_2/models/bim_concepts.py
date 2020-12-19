# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from math import *
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re
from odoo.tools.misc import formatLang, format_date
import logging
_logger = logging.getLogger(__name__)
import sys
sys.setrecursionlimit(10000)


class BimConcepts(models.Model):
    _name = 'bim.concepts'
    _order = "sequence, id"
    #_inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Concepto (Capitulos-Subcaputulos-Partidas-Recursos)"

    """
    @api.constrains('code')
    def _check_concepts(self):
        for concept in self:
            if concept.code and len(
                    self.search([('code', '=', concept.code),('type', 'in', ['chapter', 'departure']),('budget_id','=',concept.budget_id.id)])) > 1:
                raise ValidationError(
                    "Ya existe un concepto con ese código en el presupuesto: " + str(concept.budget_id.name))"""

    
    @api.model
    def default_get(self, default_fields):
        _logger.info("---1---")
        values = super(BimConcepts, self).default_get(default_fields)
        
        
        parent_id = self._context.get('default_parent_id', False)
        budget_id = self._context.get('default_budget_id', False)
        active_id = self._context.get('active_id')
        # Agregando Hijo
        if parent_id:
            parent = self.browse(parent_id)
            values['budget_id'] = parent.budget_id.id
            values['sequence'] = len(parent.child_ids) + 1
            if parent.type in ('chapter'):
                values['type'] = 'departure'
            elif parent.type in ('departure'):
                values['type'] = 'material'
            elif parent.type in ('aux'):
                values['type'] = 'material'
            else:
                values['type'] = 'aux'
        # Agregando al mismo nivel
        else:
            values['type'] = 'chapter'
            if budget_id:
                values['budget_id'] = budget_id
            else:
                # En la recarga de vista el "active_id" esta manteniendo el id del Presupuesto
                budget = self.env['bim.budget'].browse(active_id)
                values['budget_id'] = budget.id
        _logger.info("---2---")
        return values

    @api.depends('parent_id', 'type')
    def _get_valid_certification(self):
        for rec in self:
            rec.to_certify = (rec.type == 'departure' and rec.parent_id.type == 'chapter') and True or False
            rec.auto_certify = (rec.type == 'aux' and rec.parent_id.type == 'chapter') and True or False
            rec.manual_certify = (rec.type in ['labor', 'equip', 'material'] and rec.parent_id.type == 'chapter') and True or False

    @api.depends('picking_ids')
    def _get_picking_count(self):
        for rec in self:
            rec.picking_count = len(rec.picking_ids)

    @api.depends('part_ids')
    def _get_part_count(self):
        for rec in self:
            rec.part_count = len(rec.part_ids)

    @api.depends('child_ids')
    def _get_amount_count(self):
        for rec in self:
            aux_amount = 0
            equip_amount = 0
            labor_amount = 0
            material_amount = 0
            parent = rec.parent_id

            if rec.type == 'aux':
                aux_amount = self.recursive_amount(rec, parent, None)
            elif rec.type == 'equip':
                equip_amount = self.recursive_amount(rec, parent, None)
            elif rec.type == 'labor':
                labor_amount = self.recursive_amount(rec, parent, None)
            elif rec.type == 'material':
                material_amount = self.recursive_amount(rec, parent, None)
            else:
                aux_amount = sum(child.aux_amount_count for child in rec.child_ids)
                equip_amount = sum(child.equip_amount_count for child in rec.child_ids)
                labor_amount = sum(child.labor_amount_count for child in rec.child_ids)
                material_amount = sum(child.material_amount_count for child in rec.child_ids)

            rec.aux_amount_count = aux_amount
            rec.equip_amount_count = equip_amount
            rec.labor_amount_count = labor_amount
            rec.material_amount_count = material_amount

    @api.depends('parent_id')
    def _get_level(self):
        level = 1
        for record in self:
            parent = record.parent_id
            while parent:
                level += 1
                parent = parent.parent_id
            record.level = level

    @api.depends(
        'certification_stage_ids',
        'certification_stage_ids.stage_id',
        'certification_stage_ids.budget_qty',
        'certification_stage_ids.certif_qty',
        'certification_stage_ids.certif_percent',
        'certification_stage_ids.amount_budget',
        'certification_stage_ids.stage_state')
    def _compute_stage(self):
        for record in self:
            record.amount_stage_cert = sum(stage.certif_qty for stage in record.certification_stage_ids if stage.stage_state in ['process', 'approved'])

    @api.depends(
        'measuring_ids',
        'measuring_ids.qty',
        'measuring_ids.name',
        'measuring_ids.length',
        'measuring_ids.width',
        'measuring_ids.height',
        'measuring_ids.formula',
        'measuring_ids.space_id',
        'measuring_ids.stage_id')
    def _compute_measure(self):
        for record in self:
            record.amount_measure = sum(measure.amount_subtotal for measure in record.measuring_ids if measure.characteristic != 'nulo')
            record.amount_measure_cert = sum(me.amount_subtotal for me in record.measuring_ids if me.stage_id and me.stage_state in ['process', 'approved'] and me.characteristic != 'nulo')

    @api.depends(
        'code', 'type_cert', 'parent_id', 'update', 'parent_id.update',
        'budget_type', 'quantity_cert', 'amount_fixed_cert', 'amount_compute_cert')
    def _compute_amount_cert(self):
        _logger.info("---_compute_amount_cert 1 ---")
        for record in self:
            balance_cert = 0
            if record.budget_type == 'certification':
                amount = record.amount_fixed_cert if record.type_cert == 'fixed' else record.amount_compute_cert
                balance_cert = round(record.quantity_cert * amount, 2)
                if record.type == 'chapter':
                    balance_cert = sum(child.balance_cert for child in record.child_ids)
            _logger.info("---_compute_amount_cert 2 ---")
            record.balance_cert = 100

    @api.depends('quantity', 'type', 'amount_fixed', 'amount_compute', 'product_id', 'update')
    def _compute_amount(self):
        _logger.info('_compute_amount! 1')
        for record in self:
            price = record.amount_fixed if (record.type in ['labor', 'equip', 'material'] or record.amount_type == 'fixed') else record.amount_compute
            record.balance = record.quantity * price
        _logger.info('_compute_amount! 2')

    @api.depends(
        'child_ids.type',
        'child_ids.update',
        'child_ids.quantity',
        'child_ids.currency_id',
        'child_ids.product_id',
        'child_ids.amount_fixed',
        'child_ids.amount_compute',
        'type', 'amount_fixed', 'product_id', 'parent_id', 'update', 'parent_id.update')
    def _compute_price(self):
        _logger.info('_compute_price! 1')
        
        for record in self:
            price_pres = 0
            price_cert = 0
            
            """

            # Presupuesto
            if record.type in ['labor', 'equip', 'material', 'aux'] or record.amount_type == 'fixed':
                price_pres = record.amount_fixed
            else:
                price_pres = sum(l.balance for l in record.child_ids)

                # Recalculo funciones
                if any(l.id for l in record.child_ids if l.type == 'aux'):
                    for res in record.child_ids:
                        if res.type == 'aux':
                            res.onchange_function()

            # Certificacion
            if record.budget_type == 'certification':
                if record.type in ['labor', 'equip', 'material']:
                    price_cert = price_pres
                else:
                    if record.type_cert == 'fixed':
                        price_cert = record.amount_fixed_cert if record.amount_fixed_cert != 0 else price_pres
                    else:
                        price_cert = price_pres if record.type in ['departure', 'aux'] else sum(l.balance_cert for l in record.child_ids)
                    record.set_qty_cert_child()
            """
            record.amount_compute = 1
            record.amount_compute_cert = 2
           
            _logger.info('_compute_price! 2')

    @api.depends('parent_id', 'child_ids', 'child_ids.amount_execute', 'type',
                 'aux_amount_count', 'equip_amount_count', 'labor_amount_count', 'material_amount_count')
    def _compute_execute(self):
        _logger.info('_compute_execute! 1')
        stock_obj = self.env['stock.picking']
        part_obj = self.env['bim.part']
        for record in self:
            execute_equip = execute_labor = execute_material = executed = 0
            quantity = 1
            departure = self.get_departure_parent(record.parent_id)

            if record.type == 'material':
                if departure:
                    pickings = stock_obj.search([('bim_concept_id', '=', departure.id)])
                    for pick in pickings:
                        for move in pick.move_lines:
                            if move.product_id == record.product_id:
                                quantity += move.product_uom_qty
                                executed += self._get_value(move.product_uom_qty, move.product_id)

            elif record.type == 'labor':
                if departure:
                    for part in departure.part_ids:
                        for line in part.lines_ids:
                            if line.resource_type == 'H' and line.name == record.product_id:
                                quantity += line.product_uom_qty
                                executed += line.price_subtotal

            elif record.type == 'equip':
                if departure:
                    for part in departure.part_ids:
                        for line in part.lines_ids:
                            if line.resource_type == 'Q' and line.name == record.product_id:
                                quantity += line.product_uom_qty
                                executed += line.price_subtotal

            elif record.type == 'aux':
                if departure:
                    total_indicators = departure.equip_amount_count + departure.labor_amount_count + departure.material_amount_count
                    executed = (departure.amount_execute / total_indicators * departure.aux_amount_count) if total_indicators else 0.0  # self.recursive_amount(record,record.parent_id,None)# #

            elif record.type == 'departure':
                pickings = stock_obj.search([('bim_concept_id', '=', record.id)])
                for pick in pickings:
                    for move in pick.move_lines:
                        quantity += move.product_uom_qty
                        executed += self._get_value(move.product_uom_qty, move.product_id)
                        execute_material += self._get_value(move.product_uom_qty, move.product_id)

                parts = part_obj.search([('concept_id', '=', record.id)])
                for part in parts:
                    for line in part.lines_ids:
                        if line.resource_type == 'Q':
                            quantity += line.product_uom_qty
                            executed += line.price_subtotal
                            execute_equip += line.price_subtotal

                        elif line.resource_type == 'H':
                            quantity += line.product_uom_qty
                            executed += line.price_subtotal
                            execute_labor += line.price_subtotal
            else:
                executed = sum(child.amount_execute for child in record.child_ids)
                
            

            #record.qty_execute = quantity
            record.amount_execute = executed
            record.amount_execute_equip = execute_equip
            record.amount_execute_labor = execute_labor
            record.amount_execute_material = execute_material
            record.balance_execute = execute_equip + execute_labor + execute_material
            
            _logger.info('_compute_execute! 2')

    sequence = fields.Integer('Secuencia', default=1)
    display_name = fields.Char(compute='_compute_display_name', store=True, index=True)
    name = fields.Char("Nombre", required=True, index=True)
    code = fields.Char("Código", size=64, required=True, index=True)
    to_measure = fields.Boolean('Ingresar medición')
    to_certify = fields.Boolean('Aplica certificación', compute="_get_valid_certification")
    auto_certify = fields.Boolean('Certificación Automatica', compute="_get_valid_certification")
    manual_certify = fields.Boolean('Certificación Manual', compute="_get_valid_certification")
    acs_date_start = fields.Datetime("Fecha Inicio", compute='_compute_dates', inverse='_inverse_date_start', store=True)
    acs_date_end = fields.Datetime("Fecha Fin", compute='_compute_dates', inverse='_inverse_date_end', store=True)
    duration = fields.Float('Duración', compute='_compute_duration')
    level = fields.Integer(string='Nivel', compute="_get_level")
    picking_count = fields.Integer(string='N° Salidas', compute="_get_picking_count")
    part_count = fields.Integer(string='Parte', compute="_get_part_count")
    note = fields.Text("Notas")
    hito = fields.Boolean('Hito')

    budget_id = fields.Many2one('bim.budget', "Presupuesto", required=True)
    parent_id = fields.Many2one('bim.concepts', "Padre")
    uom_id = fields.Many2one('uom.uom', string='Udm', domain="[]")  # domain="[('category_id', '=', product_uom_category_id)]"
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_id = fields.Many2one('product.product', "Producto", ondelete='restrict')
    currency_id = fields.Many2one('res.currency', related='budget_id.currency_id', required=True, readonly=True)

    filter_type_domain = fields.Char(compute='_compute_filter_type_domain',  help="Campo técnico utilizado para tener un dominio dinámico en la vista de form.")
    filter_product_domain = fields.Char(compute='_compute_filter_product_domain')
    filter_product_domain_aux = fields.Char(compute='_compute_filter_product_domain')

    equip_amount_count = fields.Monetary('Total equipos', compute="_get_amount_count")
    labor_amount_count = fields.Monetary('Total mano de obra', compute="_get_amount_count")
    material_amount_count = fields.Monetary('Total material', compute="_get_amount_count")
    aux_amount_count = fields.Monetary('Total Función', compute="_get_amount_count")

    child_ids = fields.One2many('bim.concepts', 'parent_id', 'Hijos')
    measuring_ids = fields.One2many('bim.concept.measuring', 'concept_id', 'Medición')
    certification_stage_ids = fields.One2many('bim.certification.stage', 'concept_id', 'Certificacion')
    concepts_image_ids = fields.One2many(comodel_name="bim.checklist.images", inverse_name="checklist_id", string="Imagenes")
    attachment_ids = fields.Many2many('ir.attachment', string='Imágenes')
    picking_ids = fields.One2many('stock.picking', 'bim_concept_id', 'Stock')
    part_ids = fields.One2many('bim.part', 'concept_id', 'Partes')
    bim_predecessor_concept_ids = fields.One2many('bim.predecessor.concept', 'concept_id', 'Predecesoras')
    subcon = fields.Boolean("Sub Contrato")
    id_bim = fields.Char("ID BIM")

    gantt_type = fields.Selection([('begin', 'Inicio Calculado'),
                                   ('end', 'Término Calculado'),
                                   ('time', 'Duración Calculada')], default='end', related='budget_id.gantt_type')
    available = fields.Integer('Disponibilidad', default=1)

    quantity = fields.Float("Cantidad", default=1, digits='BIM qty')
    weight = fields.Float('Peso', compute="_compute_weight", store=True, digits=(10, 2))
    balance = fields.Monetary(string='Importe', compute="_compute_amount", store=True, digits='BIM price')
    amount_fixed = fields.Monetary("Precio", digits='BIM price')
    amount_compute = fields.Monetary("Precio", compute="_compute_price", digits='BIM price')
    amount_measure = fields.Float("Total Cantidad", compute="_compute_measure", store=True, digits='BIM qty')
    budget_type = fields.Selection(related='budget_id.type', store=True, readonly=True)
    update = fields.Selection([
        ('stop', 'Stop'),
        ('start', 'Start')], default='stop')
    amount_type = fields.Selection([
        ('compute', 'Calculado'),
        ('fixed', 'Manual'),
        ('locked', 'Bloqueado')], string="Tipo precio", default='compute')
    type = fields.Selection([
        ('chapter', 'CAPÍTULO'),
        ('departure', 'PARTIDA'),
        ('labor', 'MANO DE OBRA'),
        ('equip', 'EQUIPO'),
        ('material', 'MATERIAL'),
        ('aux', 'FUNCION / ADMINISTRATIVO')], string="Concepto", required=True, tracking=True)

    # Ejecucion
    amount_execute = fields.Float("Precio Ejec", compute="_compute_execute", digits='BIM price')
    qty_execute = fields.Float("Cant Ejec",  digits='BIM qty')  # compute="_compute_execute",
    balance_execute = fields.Monetary(string="Importe Ejec", compute="_compute_execute", store=True)
    amount_execute_equip = fields.Monetary('Ejecutado equipos', compute="_compute_execute")
    amount_execute_labor = fields.Monetary('Ejecutado mano de obra', compute="_compute_execute")
    amount_execute_material = fields.Monetary('Ejecutado material', compute="_compute_execute")

    # Certificacion
    amount_fixed_cert = fields.Monetary("Precio Cert", digits='BIM price', copy=False)
    amount_compute_cert = fields.Monetary("Precio Cert", compute="_compute_price", copy=False)
    balance_cert = fields.Monetary(string="Importe Cert", compute="_compute_amount_cert", store=True, copy=False)
    quantity_cert = fields.Float("Cant Cert", default=0, digits='BIM qty', copy=False)
    amount_measure_cert = fields.Float("Total Certificacion x medidas", compute="_compute_measure", digits='BIM qty', copy=False)
    amount_stage_cert = fields.Float("Total Etapas", compute="_compute_stage", digits='BIM qty', copy=False)
    percent_cert = fields.Float("(%) Cert Pres", digits='BIM price', default=0, copy=False)
    type_cert = fields.Selection([
        ('measure', 'Medición'),
        ('stage', 'Etapas'),
        ('fixed', 'Manual')], string="Tipo certificación", default='measure', copy=False)
    export_tmp_id = fields.Integer()

    # ----------------------------------------------------------------#
    # ---------------- ONCHANGE METHODS ------------------------------#
    # ----------------------------------------------------------------#
    @api.onchange('type')
    def onchange_concept_type(self):
        if self.type == 'chapter' and self.parent_id.id != False and self.parent_id.type != 'chapter':
            raise UserError('No es posible agregar un Capítulo como hijo de otro concepto que no sea de tipo Capítulo')

    @api.depends('measuring_ids', 'amount_measure', 'amount_measure_cert')
    @api.onchange('measuring_ids')
    def onchange_qty(self):
        _logger.info("---onchange_qty 1 ---")
        for record in self:
            if record.measuring_ids:
                record.quantity = abs(record.amount_measure)
                if record.type_cert == 'measure':
                    record.quantity_cert = abs(record.amount_measure_cert)
        _logger.info("---onchange_qty 2 ---")

    @api.depends('certification_stage_ids', 'amount_stage_cert')
    @api.onchange('certification_stage_ids')
    def onchange_stage(self):
        for record in self:
            record.quantity_cert = record.amount_stage_cert

    @api.onchange('amount_type')
    def onchange_amount_type(self):
        # Inicializando Precio Presupuesto en tipo Manual
        if self.amount_type == 'fixed' and self.amount_fixed != self.amount_compute:
            self.amount_fixed = self.amount_compute

    @api.depends('amount_compute_cert', 'amount_compute')
    @api.onchange('type_cert')
    def onchange_type_cert(self):
        # Inicializando Precio certificacion en tipo Manual
        if self.type_cert == 'fixed' and self.amount_fixed_cert != self.amount_compute_cert:
            self.amount_fixed_cert = self.amount_compute_cert

        if self.type_cert == 'stage':
            self.generate_stage_list()

    @api.onchange('parent_id')
    def onchange_parent(self):
        if self.parent_id:
            obj = self.env['bim.concepts'].search([('parent_id', '=', self.parent_id.id)])
            last = len(obj)
            self.code = self.parent_id.code + "." + str(last+1)

    @api.depends('code', 'parent_id', 'sequence')
    @api.onchange('type', 'code', 'sequence')
    def onchange_function(self):
        _logger.info("---onchange_function 1 ---")
        # Inicializacion de certificacion para recurso hijo de capitulo
        if self.type in ['labor', 'equip', 'material'] and self.parent_id.type == 'chapter':
            self.type_cert = 'fixed'

        # Validacion de orden de tipos
        elif self.type == 'chapter':
            self.quantity = 1
            if self.measuring_ids:
                self.measuring_ids = [(5,)]

        # Certificacion de Funciones
        elif self.type == 'aux':
            self.type_cert = 'measure' if self.auto_certify else 'fixed'
            if not self.uom_id:
                self.uom_id = self.env.ref('base_bim_2.product_uom_percent', raise_if_not_found=False)

            if self.code and '%' in self.code:
                pos = self.code.find('%')
                if pos == 0:
                    afecto = sum(child.balance for child in self.parent_id.child_ids if child.sequence < self.sequence)
                    afecto_cert = sum(child.balance_cert for child in self.parent_id.child_ids if child.sequence < self.sequence)
                    self.quantity = afecto * 0.01
                else:
                    pre = self.code[:pos]
                    afecto = sum(child.balance for child in self.parent_id.child_ids if child.sequence < self.sequence and child.code.find(pre) == 0)
                    afecto_cert = sum(child.balance_cert for child in self.parent_id.child_ids if child.sequence < self.sequence and child.code.find(pre) == 0)
                    self.quantity = afecto * 0.01

                if self.auto_certify:
                    self.percent_cert = (afecto_cert / afecto) * 100 if afecto > 0 else self.parent_id.percent_cert

            else:
                self.type_cert = 'fixed'
                afecto = sum(child.balance for child in self.parent_id.child_ids if child.sequence < self.sequence)
                afecto_cert = sum(child.balance for child in self.parent_id.child_ids if child.sequence < self.sequence)
                if self.quantity == 0:
                    self.quantity = afecto * 0.01

                if self.auto_certify:
                    self.percent_cert = (afecto_cert / afecto) * 100 if afecto > 0 else self.parent_id.percent_cert

            if self.code and '#' in self.code:
                afecto = self.budget_id.balance - self.balance
                afecto_cert = sum(concept.balance_cert for concept in self.budget_id.concept_ids.filtered(lambda c: c.type == 'chapter'))
                self.quantity = afecto * 0.01
                self.percent_cert = ((afecto_cert - self.balance_cert) / afecto) * 100
            _logger.info("---onchange_function 2 ---")

    @api.onchange('product_id')
    def onchange_product(self):
        if self.type in ['labor', 'equip', 'material']:
            self.name = self.product_id.name
            self.code = self.product_id.default_code or self.code
            # Buscamos el coste segun Coste/Precio
            find = False
            if self.budget_id.project_id.price_agreed_ids:
                for product in self.budget_id.project_id.price_agreed_ids:
                    if self.product_id.id == product.product_id.id:
                        self.amount_fixed = product.price_agreed
                        find = True
                        break
            if not find and self.product_id:
                if self.env.company.type_work == 'pricelist':
                    pricelist = self.budget_id.pricelist_id
                    product_context = dict(self.env.context, partner_id=self.budget_id.project_id.customer_id.id, date=self.budget_id.date_start, uom=self.uom_id.id)
                    price = pricelist.with_context(product_context).get_product_price(self.product_id, self.quantity or 1.0, self.budget_id.project_id.customer_id)
                    self.amount_fixed = pricelist.with_context(product_context).get_product_price(self.product_id, self.quantity or 1.0, self.budget_id.project_id.customer_id)
                elif self.env.company.type_work == 'cost':
                    self.amount_fixed = self.product_id.standard_price
                else:
                    self.amount_fixed = self.product_id.lst_price
            self.uom_id = self.product_id.uom_id.id

    @api.depends('percent_cert', 'type_cert', 'amount_measure_cert', 'quantity_cert')
    @api.onchange('quantity_cert', 'type_cert')
    def onchange_qty_certification(self):
        for record in self:
            # Porcentaje (%) Nivel actual y padre
            if record.quantity > 0:
                record.percent_cert = (record.quantity_cert / record.quantity) * 100
            if float_is_zero(record.parent_id.balance, precision_rounding=record.currency_id.rounding):
                record.parent_id.percent_cert = 0.0
            else:
                record.parent_id.percent_cert = (record.parent_id.balance_cert / record.parent_id.balance) * 100

    @api.depends('percent_cert', 'quantity', 'amount_measure_cert', 'amount_stage_cert')
    @api.onchange('percent_cert', 'type_cert')
    def onchange_percent_certification(self):
        for record in self:
            if record.type_cert == 'stage':
                record.quantity_cert = record.amount_stage_cert
            elif record.type_cert == 'measure':
                record.quantity_cert = record.amount_measure_cert
            else:
                record.quantity_cert = (record.quantity * record.percent_cert) / 100

            if record.auto_certify:
                record.quantity_cert = (record.quantity * record.percent_cert) / 100

            # Capitulos
            record.parent_id.quantity_cert = (record.parent_id.quantity * record.parent_id.percent_cert) / 100

    # --------------------------------------------------------------#
    # ---------------- MODELS METHODS ------------------------------#
    # --------------------------------------------------------------#

    def name_get(self):
        reads = self.read(['name', 'code'])
        res = []
        for record in reads:
            name = record['name']
            if record['code']:
                name = record['code'] + ' ' + name
            res.append((record['id'], name))
        return res

    def write(self, vals):
        res = super(BimConcepts, self).write(vals)
        if 'sequence' in vals:
            for concept in self:
                concept.onchange_function()
        return res

    def update_amount(self):
        for record in self:
            _logger.info('======================== ... =====================')
            #record.update = 'start'
            #record.update = 'stop'
            """
            record._compute_price()
            record._compute_amount()
            if record.to_certify:
                record._compute_amount_cert()"""

    def update_certify(self):
        for record in self:
            record._compute_amount_cert()

    def update_budget_type(self):
        for record in self:
            if record.budget_type == 'certification':
                if record.type_cert == 'fixed' and record.amount_fixed_cert != self.amount_compute_cert:
                    record.amount_fixed_cert = record.amount_compute_cert

    def generate_stage_list(self):
        for record in self:
            if not record.certification_stage_ids:
                if not record.budget_id.stage_ids:
                    record.budget_id.create_stage()
                cont = 1
                lines = []
                for stage in record.budget_id.stage_ids:
                    line = {
                        'stage_id': stage.id,
                        'concept_id': record.id,
                        'budget_qty': record.quantity if cont == 1 else 0.0,
                        'certif_qty': 0.0,
                        'certif_percent': 0.0,
                        'amount_budget': record.balance if cont == 1 else 0.0}
                    lines.append((0, 0, line))
                    cont += 1
                record.certification_stage_ids = lines

    @api.model
    def get_first_attachment(self, res_id):
        record = self.browse(res_id)
        return record.attachment_ids[0].datas if record.attachment_ids else False

    @api.depends('gantt_type', 'child_ids', 'duration',
                 'acs_date_start', 'acs_date_end',
                 'parent_id.acs_date_start', 'parent_id.acs_date_end',
                 'budget_id.date_start', 'budget_id.date_end',
                 'bim_predecessor_concept_ids')
    def _compute_dates(self):
        today = fields.Date.today()
        _logger.info('_compute_dates 1 !')
        
        for record in self:
            if record.type not in ['chapter', 'departure']:
                record.acs_date_start = record.parent_id.acs_date_start
                record.acs_date_end = record.parent_id.acs_date_end
                continue
            if not record.budget_id.do_compute:
                continue
            # Verificamos si tiene predecesoras
            date_start = date_end = False
            for pred in record.bim_predecessor_concept_ids:
                if pred.pred_type in 'ff':
                    date_end = pred.name.acs_date_end + timedelta(days=pred.difference)
                elif pred.pred_type == 'fs':
                    date_start = pred.name.acs_date_end + timedelta(days=pred.difference)
                elif pred.pred_type == 'sf':
                    date_end = pred.name.acs_date_start + timedelta(days=pred.difference)
                elif pred.pred_type == 'ss':
                    date_start = pred.name.acs_date_start + timedelta(days=pred.difference)

            if date_start or date_end:
                if not date_end:
                    date_end = date_start + timedelta(days=record.duration)
                elif not date_start:
                    date_start = date_end - timedelta(days=record.duration)

            if record.gantt_type == 'begin':
                record.acs_date_end = date_end or record.acs_date_end or today
                record.acs_date_start = date_start or ((date_end or record.acs_date_end) - timedelta(days=record.duration))
            elif record.gantt_type == 'end':
                record.acs_date_start = date_start or record.acs_date_start or today
                record.acs_date_end = date_end or ((date_start or record.acs_date_start) + timedelta(days=record.duration))
            else:
                record.acs_date_start = date_start or min([d for d in record.child_ids.mapped('acs_date_start') if d], default=today)
                record.acs_date_end = date_end or max([d for d in record.child_ids.mapped('acs_date_end') if d], default=today)
            _logger.info('_compute_dates 2 !')

    def _inverse_date_start(self):
        for record in self:
            if not record.budget_id.do_compute:
                continue
            if record.acs_date_start and record.duration:
                record.acs_date_end = record.acs_date_start + timedelta(days=record.duration)

    def _inverse_date_end(self):
        for record in self:
            if not record.budget_id.do_compute:
                continue
            if record.acs_date_end and record.duration:
                record.acs_date_start = record.acs_date_end - timedelta(days=record.duration)

    @api.depends('child_ids', 'acs_date_start', 'acs_date_end')
    def _compute_duration(self):
        for record in self:
            if record.child_ids:
                child_departures = record.child_ids.filtered_domain([('type', 'in', ['chapter', 'departure'])])
                if child_departures:
                    record.duration = max(child_departures.mapped('duration'))
                else:
                    duration = max([c.quantity / c.available for c in record.child_ids if c.available > 0 and c.type in ['labor', 'equip']], default=0.0)
                    record.duration = record.quantity * duration / self.env.company.working_hours if self.env.company.working_hours else 0
            elif record.acs_date_start and record.acs_date_end:
                record.duration = (record.acs_date_end - record.acs_date_start).days
            else:
                record.duration = 0

    @api.depends('product_id', 'uom_id', 'quantity')
    def _compute_weight(self):
        peso_category = self.env.ref('uom.product_uom_categ_kgm', raise_if_not_found=False)
        for record in self:
            if record.product_id and record.uom_id and record.uom_id.category_id == peso_category:
                record.weight = record.product_id.weight * record.uom_id.factor * record.quantity
            else:
                record.weight = 0.0

    @api.depends('name', 'code', 'parent_id')
    def _compute_display_name(self):
        for concept in self:
            name = '[%s] %s' % (concept.code, concept.name)
            concept.display_name = name

    @api.depends('type')
    def _compute_filter_type_domain(self):
        for move in self:
            if move.type == 'departure':
                move.filter_type_domain = 'chapter'
            else:
                move.filter_type_domain = 'departure'

    @api.depends('type')
    def _compute_filter_product_domain(self):
        for rec in self:
            if rec.type == 'equip':
                rec.filter_product_domain = 'Q'
                rec.filter_product_domain_aux = 'HR'
            elif rec.type == 'labor':
                rec.filter_product_domain = 'H'
                rec.filter_product_domain_aux = 'H'
            elif rec.type == 'material':
                rec.filter_product_domain = 'M'
                rec.filter_product_domain_aux = 'M'
            elif rec.type == 'aux':
                rec.filter_product_domain = 'A'
                rec.filter_product_domain_aux = 'F'
            else:
                rec.filter_product_domain = 'M'
                rec.filter_product_domain_aux = 'Q'

    def recursive_amount(self, concept, parent, amount=None):
        amount = amount is None and concept.balance or amount or 0.0
        if parent.type == 'departure':
            amount_partial = amount * parent.quantity
            return self.recursive_amount(concept, parent.parent_id, amount_partial)
        else:
            return amount * parent.quantity

    def _get_value(self, quantity, product):
        ''' Este metodo Retorna Retorna el Monto
        en un Movimiento del Producto (stock.move)'''
        if product.cost_method == 'fifo':
            quantity = product.quantity_svl
            if float_is_zero(quantity, precision_rounding=product.uom_id.rounding):
                value = 0.0
            average_cost = product.value_svl / quantity
            value = quantity * average_cost
        else:
            value = quantity * product.standard_price
        return float(value)

    def recursive_quantity(self, resource, parent, qty=None):
        qty = qty is None and resource.quantity_cert or qty
        if parent.type == 'departure':
            qty_partial = qty * parent.quantity_cert
            return self.recursive_quantity(resource, parent.parent_id, qty_partial)
        else:
            return qty * parent.quantity_cert

    def set_recursive_quantity_cert(self, child_ids, qty_cert):
        ''' Este metodo actualiza los Hijos de Partidas
        certificadas con la cantidad afectada'''
        for record in child_ids:

            parent = record.parent_id
            qty_afected = parent.quantity_cert * record.quantity
            record.quantity_cert = qty_afected + qty_cert

            if record.child_ids:
                qty_cert = qty_afected
                return self.set_recursive_quantity_cert(record.child_ids, qty_cert)

    def set_qty_cert_child(self):
        ''' Este metodo es llamado desde xxxxxxx
        para actualizar la cantidad certificada de los Hijos'''
        for record in self:
            if record.to_certify:
                self.set_recursive_quantity_cert(record.child_ids, 0)
                for child in record.child_ids:
                    if child.child_ids:
                        self.set_recursive_quantity_cert(child.child_ids, 0)

    def update_concept(self):
        ''' Este metodo es llamado desde el menú contextual
        en la vista hierarchy para actualizar la rama'''
        for child in self.child_ids:
            child.update_concept()
        self.update_amount()

    def cert_massive(self):
        ''' Este metodo es llamado desde el menú contextual
        en la vista hierarchy para certificación masiva'''
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Nueva Certificación Masiva',
            'res_model': 'bim.massive.certification',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_budget_id': self.budget_id.id, 'default_project_id': self.budget_id.project_id.id}
        }
        return action

    def get_resources(self, child_ids, res_ids):
        ''' Este metodo Retorna los ids de los
        recursos(concept) contenidos en los Hijos recibidos'''
        res = res_ids
        for record in child_ids:
            if record.type in ['labor', 'equip', 'material', 'aux']:
                res.append(record.id)
            if record.child_ids:
                self.get_resources(record.child_ids, res)
        return res

    def get_departure_parent(self, parent):
        ''' Este metodo Retorna partida padre del
         concepto'''
        result = False
        for cpt in parent:
            if cpt.type == 'departure':
                result = cpt
            else:
                self.get_departure_parent(cpt.parent_id)
        return result

    def get_departures(self, child_ids):
        ''' Este metodo Retorna partidas contenidos
        en el concepto'''
        res = []
        for record in child_ids:
            if record.type in ['departure']:
                res.append(record.id)
            if record.child_ids:
                self.get_departures(record.child_ids)
        return res

    def get_resource_from_type(self, child_ids, res_type):
        ''' Este metodo Retorna Recursos (Productos)
        contenidos en el concepto'''
        res = []
        for record in child_ids:
            if record.product_id and record.type == res_type:
                res.append(record.product_id.id)
            if record.child_ids:
                self.get_resource_from_type(record.child_ids, res_type)
        return res

    def move_record(self, action):
        sibblings = self.search([('parent_id', '=', self.parent_id.id), ('budget_id', '=', self.budget_id.id), ('id', '!=', self.id)])
        before = after = self.browse()
        for sibbling in sibblings:
            if (sibbling.sequence == self.sequence and sibbling.code < self.code) or (sibbling.sequence < self.sequence):
                before += sibbling
            else:
                after += sibbling
        if action == 'move_up' and before:
            self.sequence = before[-1].sequence if len(before) > 1 else 0
            before[-1].sequence = self.sequence + 1
            next_seq = self.sequence + 1
        elif action == 'move_down' and after:
            next_seq = self.sequence + 1
            after[0].sequence = self.sequence
            self.sequence = next_seq
            after = after[1:]
        else:
            next_seq = self.sequence

        for after_sib in after:
            after_sib.sequence = next_seq + 1
            next_seq += 1

        return True

    @api.model_create_multi
    def create(self, vals_list):
        # ~ if vals_list[0].get('type') == 'departure' and not vals_list[0].get('parent_id'):
            # ~ raise ValidationError('No puede Crear conceptos en la Raiz de tipo Partida.')
        concepts = super().create(vals_list)
        for concept in concepts:
            if concept.parent_id:
                sibblings = concept.parent_id.child_ids - concept
                if sibblings:
                    concept.sequence = sibblings.sorted('sequence')[-1].sequence + 1
        return concepts

    def unlink(self):
        for record in self:
            if record.picking_ids:
                raise ValidationError('No puede borrar conceptos que contengan movimientos de salida.')
            if record.part_ids:
                raise ValidationError('No puede borrar conceptos que contengan partes de mano de obra o equipos.')
            record.child_ids.unlink()
        return super().unlink()

    # --------------------------------------------------------------------#
    # ---------------- ACTION VIEWS METHODS ------------------------------#
    # --------------------------------------------------------------------#

    def action_view_equip(self):
        childs = self.mapped('child_ids')
        action = self.env.ref('base_bim_2.action_bim_concepts').read()[0]
        action['domain'] = [('id', 'in', childs.ids), ('parent_id', '=', self.id), ('type', '=', 'equip')]
        return action

    def action_view_material(self):
        childs = self.mapped('child_ids')
        action = self.env.ref('base_bim_2.action_bim_concepts').read()[0]
        action['domain'] = [('id', 'in', childs.ids), ('parent_id', '=', self.id), ('type', '=', 'material')]
        return action

    def action_view_labor(self):
        childs = self.mapped('child_ids')
        action = self.env.ref('base_bim_2.action_bim_concepts').read()[0]
        action['domain'] = [('id', 'in', childs.ids), ('parent_id', '=', self.id), ('type', '=', 'labor')]
        return action

    def action_view_departure(self):
        childs = self.mapped('child_ids')
        action = self.env.ref('base_bim_2.action_bim_concepts').read()[0]
        action['domain'] = [('id', 'in', childs.ids), ('parent_id', '=', self.id), ('type', '=', 'departure')]
        return action

    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        # Prepare the context.
        #picking_id = pickings.filtered(lambda l: l.picking_type_id.code == 'outgoing')
        # if picking_id:
        #    picking_id = picking_id[0]
        # else:
        #    picking_id = pickings[0]
        #action['context'] = dict(self._context, default_partner_id=self.partner_id.id, default_picking_id=picking_id.id, default_picking_type_id=picking_id.picking_type_id.id, default_origin=self.name, default_group_id=picking_id.group_id.id)
        return action

    def action_view_part(self):
        parts = self.mapped('part_ids')
        action = self.env.ref('base_bim_2.action_bim_part').read()[0]
        if len(parts) > 0:
            action['domain'] = [('id', 'in', parts.ids)]
            action['context'] = {'default_part_id': self.id}
            return action
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Nuevo Presupuesto',
                'res_model': 'bim.part',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current',
                'context': {'default_concept_id': self.id}
            }


    def action_view_concept(self):
        action = self.env.ref('base_bim_2.action_bim_concepts').read()[0]
        action['domain'] = [('budget_id', '=', self.budget_id.id)]
        action['context'] = {'default_budget_id': self.budget_id.id}
        action['context'].update({'budget_type': self.budget_id.type})
        return action


class BimConceptMeasuring(models.Model):
    _name = 'bim.concept.measuring'
    _description = "Medición del Presupuesto"

    @api.depends('qty', 'length', 'width', 'height', 'formula')
    def _compute_amount(self):
        for record in self:
            if record.formula:
                X = x = b = B = record.length
                Y = y = c = C = record.width
                Z = z = d = D = record.height
                record.amount_subtotal = record.qty * eval(str(record.formula.formula))
            else:
                record.amount_subtotal = record.qty * ((record.length > 0 and record.length or 1) * (record.width > 0 and record.width or 1) * (record.height > 0 and record.height or 1))

    name = fields.Char(string='Descripción', required=True)
    space_id = fields.Many2one('bim.budget.space', string='Espacio')
    qty = fields.Integer(string='Cant (N)', default=0)
    length = fields.Float(string='Largo (X)')
    width = fields.Float(string='Ancho (Y)')
    height = fields.Float(string='Alto (Z)')
    formula = fields.Many2one('bim.formula', string='Fórmula')
    amount_subtotal = fields.Float(string='Subtotal', store=True, digits='BIM qty', compute="_compute_amount")
    stage_id = fields.Many2one('bim.budget.stage', "Etapa")
    concept_id = fields.Many2one('bim.concepts', "Partida")
    budget_id = fields.Many2one('bim.budget', related="concept_id.budget_id", string='Presupuesto')
    to_certify = fields.Boolean(related="concept_id.to_certify", string='Certificable')
    type_certify = fields.Selection(related="concept_id.type_cert", string='Tipo')
    stage_state = fields.Selection(related='stage_id.state', store=True, readonly=True)
    characteristic = fields.Selection([
        ('acordado', 'Acordado'),
        ('nulo', 'Nulo'),
        ('modificado_aprobado', 'Modificado Aprobado'),
        ('modificado_pendiente', 'Modificado Pendiente')],
        string='Característica', default='acordado', tracking=True)
    massively_certified = fields.Boolean(default=False)
    parent_id = fields.Many2one('bim.concepts', "Padre", related='concept_id.parent_id')

    @api.onchange('space_id')
    def onchange_group(self):
        if self.space_id:
            self.name = self.space_id.name


    # ~ @api.onchange('stage_id')
    # ~ def onchange_stage(self):
        # ~ if self.stage_id:
            # ~ if self.to_certify:
            # ~ warning = {
            # ~ 'title': _('Warning!'),
            # ~ 'message': _(u'No se puede agregar Etapas en ambiente de Certificacion!'), }
            # ~ self.stage_id = False
            # ~ return {'warning': warning}


class BimCertificationStage(models.Model):
    _name = 'bim.certification.stage'
    _description = "Certificacion por Etapas"

    @api.depends('stage_id', 'stage_id.state', 'budget_qty', 'certif_qty', 'concept_id.amount_compute_cert')
    def _compute_amount(self):
        for record in self:
            #record.amount_budget = record.budget_qty * record.concept_id.amount_compute
            record.amount_certif = record.certif_qty * record.concept_id.amount_compute_cert

    name = fields.Date(string='Fecha', related='stage_id.date_stop', required=True)
    budget_qty = fields.Float(string='Cant Pres (N)', default=0, digits='BIM qty')
    certif_qty = fields.Float(string='Cant Cert (N)', default=0, digits='BIM qty')
    certif_percent = fields.Float(string='(%) Cert', default=0, digits='BIM price')
    stage_id = fields.Many2one('bim.budget.stage', "Etapa")
    concept_id = fields.Many2one('bim.concepts', "Partida")
    budget_id = fields.Many2one('bim.budget', related="concept_id.budget_id", string='Presupuesto')
    amount_budget = fields.Float(string='Total pres', digits='BIM price')
    amount_certif = fields.Float(string='Total cert', digits='BIM price', compute="_compute_amount")
    stage_state = fields.Selection(related='stage_id.state', store=True, readonly=True)
    parent_id = fields.Many2one('bim.concepts', "Padre", related='concept_id.parent_id')

    @api.onchange('certif_qty')
    def onchange_qty(self):
        for record in self:
            if record.concept_id.quantity <= 0:
                record.certif_percent = (record.certif_qty / 1) * 100
            else:
                record.certif_percent = (record.certif_qty / record.concept_id.quantity) * 100

    @api.onchange('certif_percent')
    def onchange_percent(self):
        for record in self:
            record.certif_qty = (record.concept_id.quantity * record.certif_percent) / 100

    def action_next(self):
        if self.stage_state == 'draft':
            self.stage_id.state = 'process'
        elif self.stage_state == 'process':
            self.stage_id.state = 'approved'

    def action_cancel(self):
        return self.stage_id.write({'state': 'cancel'})


class BimPredecessorConcept(models.Model):
    _name = 'bim.predecessor.concept'
    _description = "Tareas Antecesores"

    name = fields.Many2one('bim.concepts', 'Predecesor', required=True)
    concept_id = fields.Many2one('bim.concepts', "Partida")
    difference = fields.Integer('Días de diferencia', help='Admite valores negativos')
    pred_type = fields.Selection([('ff', 'Fin a fin'),
                                  ('fs', 'Fin a inicio'),
                                  ('sf', 'Inicio a fin'),
                                  ('ss', 'Inicio a inicio')], 'Tipo', required=True, default='fs')

    _sql_constraints = [
        ('unique_concept_predecessor', 'unique(name,concept_id)', 'No puede repetir la misma predecesora.')
    ]

    @api.constrains('name')
    def _check_loops(self):
        _logger.info("---_check_loops 1 ---")
        def in_loop(concept, predecessors, verified):
            for pred in predecessors:
                if pred.name in verified:
                    continue
                verified += pred.name
                if concept == pred.name:
                    return [pred.name]
                res = in_loop(concept, pred.name.bim_predecessor_concept_ids, verified)
                if res:
                    return res + [pred.name]
            for child in concept.child_ids:
                if child in verified:
                    continue
                verified += child
                res = in_loop(concept, child.bim_predecessor_concept_ids, verified)
                if res:
                    return res + [child]
            return []

        def get_parents(concept):
            if not concept.parent_id:
                return self.name.browse()
            return concept.parent_id + get_parents(concept.parent_id)

        def get_childs(concept):
            if not concept.child_ids:
                return self.name.browse()
            grand_childs = self.name.browse()
            for child in concept.child_ids:
                grand_childs += get_childs(child)
            return concept.child_ids + grand_childs

        for record in self:
            loops = in_loop(record.name, record.name.bim_predecessor_concept_ids, self.name.browse())
            if loops:
                loops.append(record.name)
                raise ValidationError('Se está formando un ciclo.\n%s' % ' > '.join(l.display_name for l in loops))

            if record.name in get_parents(record.concept_id):
                raise ValidationError('No puede escoger un concepto padre')
            if record.name in get_childs(record.concept_id):
                raise ValidationError('No puede escoger un concepto hijo')
        _logger.info("---_check_loops 2 ---")
