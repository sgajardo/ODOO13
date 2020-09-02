# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models,_
from odoo.exceptions import ValidationError

class BimWorkorder(models.Model):
    _name = 'bim.workorder'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _order = 'id desc'
    _description = "Ordenes de Trabajo BIM"

    def set_access_name(self):
        self.modify_name =  self.env.user.has_group('bim_workorder.workorder_bim_security_name')

    @api.depends('requisition_ids')
    def _get_requisition_count(self):
        for rec in self:
            rec.requisition_count = len(rec.requisition_ids)

    modify_name = fields.Boolean(compute=set_access_name, string='Usuario Modifica Nombre?')
    name = fields.Char(string='Nombre', required=True, default="/")
    description_act = fields.Char(string='Descripción Actividad', copy=True)
    project_id = fields.Many2one('bim.project', string="Obra")
    budget_id = fields.Many2one('bim.budget', "Presupuesto", domain="[('project_id', '=', project_id)]")
    space_id = fields.Many2one('bim.budget.space', string="Espacio", domain="[('budget_id', '=', budget_id)]")
    object_id = fields.Many2one('bim.object', "Objeto", domain="[('project_id', '=', project_id)]")
    speciality_id = fields.Many2one('bim.workorder.speciality', string="Especialidad")
    #purchase_req_id = fields.Many2one('bim.purchase.requisition', string="Solicitud Materiales")
    requisition_ids = fields.One2many('bim.purchase.requisition', 'workorder_id', "Solicitud Materiales")
    requisition_count = fields.Integer(string='N° Solicitides', compute="_get_requisition_count")
    restriction_ids = fields.One2many('bim.workorder.restriction', 'workorder_id', string="Restricciones", copy=True)
    concept_ids = fields.One2many('bim.workorder.concepts', 'workorder_id', string="Conceptos", copy=True, ondelete="cascade")
    material_ids = fields.One2many('bim.workorder.resources', 'workorder_id', string="Materiales", copy=True, domain=[('resource_type','=','material')])
    material_extra_ids = fields.One2many('bim.workorder.resources', 'workorder_id', string="Materiales Adicionales", copy=True, domain=[('product_type','=','M'),('workorder_concept_id','=',False)])
    labor_ids = fields.One2many('bim.workorder.resources', 'workorder_id', string="Mano de Obra", copy=True, domain=[('resource_type','=','labor')])
    labor_extra_ids = fields.One2many('bim.workorder.resources', 'workorder_id', string="Mano de Obra Adicional", copy=True, domain=[('product_type','=','H'),('workorder_concept_id','=',False)])
    user_id = fields.Many2one('res.users', string="Solicitado por", tracking=True, default=lambda self: self.env.user)
    date_start = fields.Date("Fecha Inicio", required=True, copy=True, default=fields.Date.today)
    date_end = fields.Date("Fecha Termino", copy=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Aprobado'),
        ('delivered', 'Entregado'),
        ('cancel', 'Cancelado')],
        string='Estado', default='draft', tracking=True)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------


    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('project_id')
    def onchange_project(self):
        if self.project_id:
            if self.budget_id:
                self.budget_id = False
            if self.space_id:
                self.space_id = False
            if self.object_id:
                self.object_id = False

    @api.onchange('budget_id')
    def onchange_project(self):
        if self.budget_id:
            if self.space_id:
                self.space_id = False
            if self.concept_ids:
                self.concept_ids = [(5,)]

    # -------------------------------------------------------------------------
    # MODEL METHODS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        orders = super(BimWorkorder, self).create(vals_list)
        corr = len(self.search([]))
        for order in orders:
            spc = order.speciality_id.code
            order.name = 'OT/%s/%s'%(spc,str(corr).zfill(5))
        return orders

    def update_list(self):
        res_type = self._context.get('type')
        type = res_type == 'M' and 'material' or 'labor'
        for record in self:
            for line in record.concept_ids:
                if line.concept_id.child_ids:
                    childs = line.concept_id.child_ids
                    record._update_resources(childs,line,type)

    def _update_resources(self,resources,line_parent,type):
        for record in self:
            lines = []
            concept_ob = self.env['bim.concepts']
            resource_ids = record.get_resources(resources,[],type)
            if type == 'labor':
                vals = [l.resource_id.id for l in record.labor_ids]
            else:
                vals = [l.resource_id.id for l in record.material_ids]

            for res_id in resource_ids:
                if not res_id in vals:
                    resource = concept_ob.browse(res_id)
                    line = {'workorder_id': record.id,
                            'resource_id': res_id,
                            'type': 'budget_in',
                            'workorder_concept_id': line_parent.id,
                            'category_id':resource.product_id.categ_id.id
                            }
                    if type == 'material':
                        # Cantidad a pedir
                        if resource and resource.product_id:
                            qty_ordered = (resource.quantity * line_parent.qty_worder) - self._get_product_stock(resource.product_id)
                            line['qty_ordered'] = qty_ordered > 0 and qty_ordered or 0

                        # Busqueda de Acuerdo y/o Proveedores de Material
                        purch_vals = self.get_purchase_history(resource.product_id)
                        line.update(purch_vals)

                    lines.append((0, 0, line))

            if type == 'labor':
                record.labor_ids = lines
            else:
                record.material_ids = lines

    def get_purchase_history(self, product):
        """ Returns a list of tuples
            result format: {[(precio, id partner, id acuerdo)]}
        """
        result = {'vendor_first_id': False,'vendor_second_id':False,'order_agree_id':False}
        list_res = []
        lines_purchase = self.env['purchase.order.line'].search(
            [('product_id','=',product.id),
            ('state','not in',['draft','sent','cancel'])])

        if lines_purchase:
            for line in lines_purchase:
                order = line.order_id
                requisition = order.requisition_id and order.requisition_id.id or False
                tuple_vals = (line.price_unit, line.partner_id.id, requisition)
                list_res.append(tuple_vals)

            list_res.sort(key=lambda tup: tup[0])
            if list_res and len(list_res) == 1:
                result['vendor_first_id'] = list_res[0][1]
                result['vendor_second_id'] = list_res[0][1]
                result['order_agree_id'] = list_res[0][2]
                result['price_unit'] = list_res[0][0]
            elif list_res and len(list_res) > 1:
                result['vendor_first_id'] = list_res[0][1]
                result['vendor_second_id'] = list_res[1][1]
                result['order_agree_id'] = list_res[0][2]# or list_res[1][2]
                result['price_unit'] = list_res[0][0]
        else:
            if product.seller_ids:
                supplier_info = product.seller_ids
                for line in supplier_info:
                    tuple_vals = (line.price, line.name.id, False)
                    list_res.append(tuple_vals)

                list_res.sort(key=lambda tup: tup[0])
                if list_res and len(list_res) == 1:
                    result['vendor_first_id'] = list_res[0][1]
                    result['vendor_second_id'] = list_res[0][1]
                    result['order_agree_id'] = list_res[0][2]
                    result['price_unit'] = list_res[0][0]
                elif list_res and len(list_res) > 1:
                    result['vendor_first_id'] = list_res[0][1]
                    result['vendor_second_id'] = list_res[1][1]
                    result['order_agree_id'] = list_res[0][2]# or list_res[1][2]
                    result['price_unit'] = list_res[0][0]
        return result

    def get_resources(self, child_ids, res_ids, type):
        res = res_ids
        for record in child_ids:
            if record.type == type:
                res.append(record.id)
            if record.child_ids:
                self.get_resources(record.child_ids, res, type)
        return res

    def _get_product_stock(self,product):
        StockQ = self.env['stock.quant']
        location = self.budget_id.project_id.stock_location_id
        qty_material = StockQ._get_available_quantity(product,location) if location else product.qty_available
        return qty_material

    def action_open_lines(self):
        show = self._context.get('show')
        domain = [('workorder_id','=',self.id)]
        if show == 'budget':
            action = self.env.ref('bim_workorder.action_material_budget_tree_all').read()[0]
            domain.append(('resource_type','=','material'))
            domain.append(('type','=','budget_in'))
        else:
            action = self.env.ref('bim_workorder.action_material_extra_tree_all').read()[0]
            domain.append(('product_type','=','M'))
            domain.append(('workorder_concept_id','=',False))
        action['context'] = {'default_workorder_id': self.id}
        return action

    def create_purchase_requisition(self):
        for record in self:
            context = self._context
            project = record.project_id
            material_lines =  record.material_ids.filtered(lambda l: l.order_assign)
            extra_mat_lines = record.material_extra_ids.filtered(lambda l: l.order_assign)
            product_lines = []

            for line in material_lines:
                resource = line.resource_id
                product_lines.append((0,0,{
                    'product_id': resource.product_id.id,
                    'um_id': resource.uom_id.id,
                    'quant': line.qty_ordered,
                    'cost': line.price_unit,
                    'partner_id': line.vendor_first_id.id or line.vendor_second_id.id,
                    'analytic_id': project.analytic_id.id or False,
                    'workorder_resource_id': line.id,
                }))

            for line in extra_mat_lines:
                product_lines.append((0,0,{
                    'product_id': line.product_id.id,
                    'um_id': line.product_id.uom_id.id,
                    'quant': line.qty_ordered,
                    'cost': line.price_unit,
                    'partner_id': line.vendor_first_id.id or line.vendor_second_id.id,
                    'analytic_id': project.analytic_id.id or False,
                    'workorder_resource_id': line.id,
                }))

            if not product_lines:
                 raise ValidationError(u'No existen Materiales a procesar')

            requisition = self.with_context(active_id=project.id,uid=lambda s: s.env.user).env['bim.purchase.requisition'].create({
                'project_id': project.id,
                'analytic_id': project.analytic_id.id or False,
                'date_begin': fields.Datetime.now(),
                'space_id': record.space_id.id,
                'product_ids': product_lines })
            record.requisition_ids = [(4,requisition.id,None)]
        return True

    def action_view_requisitions(self):
        action = self.env.ref('base_bim_2.action_bim_purchase_requisition').read()[0]
        requisitions = self.mapped('requisition_ids')
        if len(requisitions) > 1:
            action['domain'] = [('id', 'in', requisitions.ids)]
        elif requisitions:
            form_view = [(self.env.ref('base_bim_2.view_form_bim_purchase_requisition').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = requisitions.id
        return action

    # ~ def create_purchase(self):
        # ~ self.ensure_one()
        # ~ context = self._context
        # ~ PurchaseOrd = self.env['purchase.order']

        # ~ material_lines =  self.material_ids.filtered(lambda l: not l.order_id and l.order_assign)
        # ~ extra_mat_lines = self.material_extra_ids.filtered(lambda l: not l.order_id and l.order_assign)
        # ~ suppliers = material_lines.mapped('vendor_first_id') + extra_mat_lines.mapped('vendor_first_id')

        # ~ if not suppliers:
            # ~ raise ValidationError(_("No se encontraron lineas disponibles para crear una Orden de Compra."))

        # ~ if self.project_id.warehouse_id:
            # ~ picking_type = self.env['stock.picking.type'].search([('warehouse_id', '=', self.project_id.warehouse_id.id),('code', '=', 'incoming')]).id
        # ~ else:
            # ~ picking_type = self.env['stock.picking.type'].search([], limit=1).id

        # ~ for supplier in suppliers:
            # ~ purchase_lines = []
            # ~ order = PurchaseOrd.create({
                    # ~ 'partner_id': supplier.id,
                    # ~ 'origin': context.get('order'),
                    # ~ 'date_order': fields.Datetime.now(),
                    # ~ 'picking_type_id': picking_type
            # ~ })

            # ~ #Asignamoslas lineas
            # ~ lines = material_lines.filtered(lambda l: l.vendor_first_id.id == supplier.id)
            # ~ for line in lines:
                # ~ resource = line.resource_id
                # ~ purchase_lines.append((0,0,{
                    # ~ 'name': resource.product_id.name,
                    # ~ 'product_id': resource.product_id.id,
                    # ~ 'product_uom': resource.uom_id.id,
                    # ~ 'product_qty': line.qty_ordered,
                    # ~ 'price_unit': resource.product_id.standard_price,
                    # ~ 'date_planned': fields.Datetime.now(),
                    # ~ 'taxes_id': [(6, 0, resource.product_id.supplier_taxes_id.ids)],
                # ~ }))
            # ~ extra_lines = extra_mat_lines.filtered(lambda l: l.vendor_first_id.id == supplier.id)
            # ~ for line in extra_lines:
                # ~ purchase_lines.append((0,0,{
                    # ~ 'name': line.product_id.name,
                    # ~ 'product_id': line.product_id.id,
                    # ~ 'product_uom': line.product_id.uom_id.id,
                    # ~ 'product_qty': line.qty_ordered,
                    # ~ 'price_unit': line.product_id.standard_price,
                    # ~ 'date_planned': fields.Datetime.now(),
                    # ~ 'taxes_id': [(6, 0, line.product_id.supplier_taxes_id.ids)],
                # ~ }))
            # ~ print (purchase_lines)
            # ~ order.order_line = purchase_lines

            # ~ #Actalizacion de Lineas
            # ~ for line in lines:
                # ~ line.order_id = order.id
            # ~ for line in extra_lines:
                # ~ line.order_id = order.id

        # ~ return True

class BimWorkorderConcepts(models.Model):
    _name = 'bim.workorder.concepts'
    _description = "Partidas y Mediciones Orden de Trabajo BIM"

    @api.depends('concept_id')
    def _get_concept_quantity(self):
        for record in self:
            qty_budget = qty_execute = qty_certif = 0
            if record.concept_id:
                vals = record.get_quantities(record.concept_id)
                qty_budget = vals['budget']
                qty_certif = vals['certf']
                qty_execute = vals['budget'] - vals['certf']
            record.qty_budget = qty_budget
            record.qty_certif = qty_certif
            record.qty_execute = qty_execute

    name = fields.Char(string='Detalle', required=True)
    qty_budget = fields.Integer(string='Cant Presupuestada', compute="_get_concept_quantity")
    qty_certif = fields.Integer(string='Cant Certificada', compute="_get_concept_quantity")
    qty_execute = fields.Integer(string='Cant a Ejecutar', compute="_get_concept_quantity")
    qty_worder = fields.Integer(string='Cant OT')
    workorder_id = fields.Many2one('bim.workorder', string="Orden")
    budget_id = fields.Many2one('bim.budget',related='workorder_id.budget_id', string="Presupuesto")
    space_id = fields.Many2one('bim.budget.space',related='workorder_id.space_id', string="Espacio")
    concept_id = fields.Many2one('bim.concepts', string="Partida", domain="[('budget_id', '=', budget_id),('type', '=', 'departure')]")

    @api.onchange('concept_id')
    def onchange_concept(self):
        if not self.name:
            self.name = self.concept_id.name

    def get_quantities(self,concept):
        qty_budget = qty_certif = 0
        if concept.measuring_ids:
            for mea in concept.measuring_ids:
                if mea.space_id.id == self.space_id.id:
                    qty_budget += mea.amount_subtotal

                if mea.space_id.id == self.space_id.id and concept.type_cert == 'measure':
                    if mea.stage_id and mea.stage_state in ['process', 'approved'] and mea.characteristic != 'nulo':
                        qty_certif += mea.amount_subtotal
                #if mea.space_id.id == self.space_id.id and concept.type_cert == 'fixed':
                #    qty_certif +=  (mea.amount_subtotal * record.percent_cert) / 100

        if concept.certification_stage_ids and concept.type_cert == 'stage':
            for stage in concept.certification_stage_ids:
                if stage.stage_state in ['process', 'approved']:
                    qty_certif += stage.certif_qty

        return {'budget': qty_budget, 'certf': qty_certif}

    def unlink(self):
        """ Al eliminar una Partida eventualmente debemos eliminar
            los recursos asociados a ella.
        """
        for rec in self:
            if rec.exists():
                to_delete = rec.id
            for l in rec.workorder_id.labor_ids:
                if l.workorder_concept_id.id == to_delete:
                    l.unlink()
            for m in rec.workorder_id.material_ids:
                if m.workorder_concept_id.id == to_delete:
                    m.unlink()
        return super(BimWorkorderConcepts, self).unlink()


class BimWorkorderResources(models.Model):
    _name = 'bim.workorder.resources'
    _description = "Recursos (Equipo-Material-Mano de Obra) OT"

    name = fields.Char(string='Detalle', compute='_compute_name')
    difficulty = fields.Float(string='Dificultad')
    date_start = fields.Date("Inicio", required=True, default=fields.Date.today)
    date_stop = fields.Date("Termino", required=True, default=fields.Date.today)
    duration_cmpt = fields.Float(string='Duración calculada', compute="_get_factors") # Cantidad Calculada Materiales
    duration_real = fields.Float(string='Duración real', compute="_compute_timesheet")
    efficiency_cmpt = fields.Float(string='Rendimiento',related="resource_id.quantity") # cantidad del recurso
    efficiency_real = fields.Float(string='Rendimiento real', compute="_get_factors")
    efficiency_extra = fields.Float(string='Rendimiento extra')
    deviance_real = fields.Float(string='Desviación real', compute="_get_factors")
    qty_available = fields.Float(string='Stock', compute="_get_material_stock")
    qty_ordered = fields.Float(string='Cant a Pedir')
    price_unit = fields.Float(string='Costo')
    order_assign = fields.Boolean(string='Sol Cotización')
    order_ids = fields.Many2many('purchase.order', string="N° ODC")
    order_agree_id = fields.Many2one('purchase.requisition', string="Acuerdo ODC")
    vendor_first_id = fields.Many2one('res.partner', string="Proveedor #1")
    vendor_second_id = fields.Many2one('res.partner', string="Proveedor #2")
    category_id = fields.Many2one('product.category', string="Categoria")#, related='resource_id.product_id.categ_id'
    #job_id = fields.Many2one('hr.job', string="Puesto de Trabajo")
    workorder_id = fields.Many2one('bim.workorder', string="Orden")
    workorder_concept_id = fields.Many2one('bim.workorder.concepts', string="Partida/Medición")
    budget_id = fields.Many2one('bim.budget',related='workorder_id.budget_id', string="Presupuesto")
    space_id = fields.Many2one('bim.budget.space',related='workorder_id.space_id', string="Espacio")
    concept_id = fields.Many2one('bim.concepts', string="Partida",related='workorder_concept_id.concept_id') #domain="[('budget_id', '=', budget_id),('type', '=', 'departure')]"
    resource_id = fields.Many2one('bim.concepts', string="Recurso")
    #picking_in_id = fields.Many2one('stock.picking', string="Ref Recepción")
    picking_in = fields.Char(string="Ref Recepción", compute='_compute_pickings')
    picking_out = fields.Char(string="Ref Entrega Instaladores", compute='_compute_pickings')
    #picking_out_id = fields.Many2one('stock.picking', string="Ref Entrega Instaladores")
    resource_type = fields.Selection(related='resource_id.type', string="Tipo Recurso")
    product_type = fields.Selection(related='product_id.resource_type', string="Tipo Producto")
    supply = fields.Selection([
        ('quotation', 'Cotización'),
        ('ordered', 'Orden de compra'),
        ('invoiced','Facturado')],
        string='Abastecimiento', default='quotation', tracking=True)
    type = fields.Selection([
        ('budget_in', 'Presupuestado'),
        ('budget_out','No Presupuestado')],
        string='Tipo', default='budget_out', tracking=True)
    #Extra
    departure_id = fields.Many2one('bim.concepts', string="Otra Partida", domain="[('budget_id','=',budget_id),('type','=','departure')]")
    reason = fields.Char(string='Motivo')
    #amount_untaxed = fields.Float("Total Neto")
    user_id = fields.Many2one('res.users', string="Aprobado por")
    product_id = fields.Many2one('product.product', string="Recurso adicional")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('type')
    def _compute_name(self):
        for record in self:
            field_ref = record.resource_id if record.type == 'budget_in' else record.product_id
            record.name = field_ref.name

    @api.depends('workorder_concept_id','efficiency_cmpt','efficiency_extra','duration_real','departure_id','difficulty')
    def _get_factors(self):
        for record in self:
            efficiency = record.efficiency_cmpt if record.type == 'budget_in' else record.efficiency_extra # Rendimiento
            qty_worder = record.workorder_concept_id.qty_worder if record.workorder_concept_id else record.get_quantity_departure(record.departure_id)
            record.duration_cmpt = (efficiency + (efficiency * record.difficulty)) * qty_worder if record.resource_type == 'labor' else (efficiency * qty_worder)
            record.efficiency_real = (record.duration_real / qty_worder) if qty_worder > 0 else 0.0
            record.deviance_real = record.duration_real - record.duration_cmpt

    @api.depends('workorder_id','efficiency_cmpt','duration_real')
    def _get_material_stock(self):
        for record in self:
            product = record.resource_id.product_id if record.type == 'budget_in' else record.product_id
            record.qty_available = record.workorder_id._get_product_stock(product) if product else 0.0

    @api.depends('resource_id','product_id')
    def _compute_timesheet(self):
        timesheet = self.env['workorder.timesheet']
        for record in self:
            lines = timesheet.search([('resource_id','=',record.id)])
            record.duration_real = sum(line.unit_amount for line in lines)

    @api.depends('order_ids')
    def _compute_pickings(self):
        stock_picking = self.env['stock.picking']
        stock_picking_type = self.env['stock.picking.type']
        for record in self:
            # Movimiento de Entrada
            picks_in = [pick.name for order in record.order_ids for pick in order.picking_ids]
            picking_in_refs = ','.join(picks_in) if picks_in else '-'

            # Movimientos internos
            pick_type = stock_picking_type.search([('warehouse_id','=',record.budget_id.project_id.warehouse_id.id),('sequence_code','=','INT'),('code','=','internal')])
            picks_out = stock_picking.search([('picking_type_id','=',pick_type.id),('location_dest_id','=',record.budget_id.project_id.stock_location_id.id)])
            picking_out_refs = ','.join(picks_out.mapped('name')) if picks_out else '-'

            # valores
            record.picking_in = picking_in_refs
            record.picking_out = picking_out_refs



    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('departure_id')
    def onchange_departure_id(self):
        depart_list = []
        if self.workorder_id:
            for line in self.workorder_id.concept_ids:
                if line.concept_id:
                     depart_list.append(line.concept_id.id)
        return {'domain': {'departure_id': [('id','in',depart_list)]}}

    @api.onchange('product_id')
    def onchange_departure_id(self):
        depart_list = []
        if self.workorder_id and self.product_id:
            self.category_id = self.product_id.categ_id.id
            purch_vals = self.workorder_id.get_purchase_history(self.product_id)
            self.write(purch_vals)

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def get_quantity_departure(self, departure):
        res = 0
        for record in self:
            for line in record.workorder_id.concept_ids:
                if line.concept_id.id == departure.id:
                    res = line.qty_worder
        return res

    def open_timesheet_view(self):
        [action] = self.env.ref('bim_workorder.action_workorder_timesheet_line').read()
        id_res = self.id
        action['domain'] = [('resource_id', '=', id_res),('workorder_id', '=', self.workorder_id.id)]
        action['context'] = {'default_resource_id': id_res,'default_workorder_id': self.workorder_id.id}
        return action

class BimWorkorderRestriction(models.Model):
    _name = 'bim.workorder.restriction'
    _description = "Restricciones Orden de Trabajo BIM"

    @api.depends('date')
    def _get_days(self):
        for record in self:
            date_diff = fields.Date.today() - record.date
            record.count_day = date_diff.days

    name = fields.Char(string='Detalle', required=True)
    number_report = fields.Char(string='Informe N°')
    date = fields.Date("Fecha informe", required=True, default=fields.Date.today)
    count_day = fields.Integer(string='Dias transcurridos', compute="_get_days")
    workorder_id = fields.Many2one('bim.workorder', string="Orden")
    restriction_id = fields.Many2one('bim.restriction', string="Restricción")
    file_support = fields.Binary(string='Soporte',  attachment=True, copy=False)


class BimWorkorderSpeciality(models.Model):
    _name = 'bim.workorder.speciality'
    _description = "Especialidades Orden de Trabajo BIM"

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True)


class BimRestriction(models.Model):
    _name = 'bim.restriction'
    _description = "Restricciones BIM"

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True)

