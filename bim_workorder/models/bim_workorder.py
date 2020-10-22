# -*- coding: utf-8 -*-
from odoo.tools.float_utils import float_compare
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models,_
from odoo.exceptions import ValidationError
#from tkinter import messagebox

class BimWorkorder(models.Model):
    _name = 'bim.workorder'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _order = 'id desc'
    _description = "Ordenes de Trabajo BIM"

    def set_access_name(self):
        self.modify_name =  self.env.user.has_group('bim_workorder.workorder_bim_security_name')


    modify_name = fields.Boolean(compute=set_access_name, string='Usuario Modifica Nombre?')
    name = fields.Char(string='Nombre', required=True, default="/")
    advance = fields.Float(string='% Avance', compute="_get_advance_percent")
    description_act = fields.Char(string='Descripción Actividad', copy=True)
    project_id = fields.Many2one('bim.project', string="Obra")
    budget_id = fields.Many2one('bim.budget', "Presupuesto", domain="[('project_id', '=', project_id)]")
    space_id = fields.Many2one('bim.budget.space', string="Espacio", domain="[('budget_id', '=', budget_id)]")
    object_id = fields.Many2one('bim.object', "Objeto", domain="[('project_id', '=', project_id)]")
    speciality_id = fields.Many2one('bim.workorder.speciality', string="Especialidad")
    #requisition_ids = fields.One2many('bim.purchase.requisition', 'workorder_id', "Solicitud Materiales")
    order_count = fields.Integer(string='N° Compras', compute="_get_order_count")
    restriction_ids = fields.One2many('bim.workorder.restriction', 'workorder_id', string="Restricciones", copy=True)
    concept_ids = fields.One2many('bim.workorder.concepts', 'workorder_id', string="Conceptos", copy=True, ondelete="cascade")
    material_ids = fields.One2many('bim.workorder.resources', 'workorder_id', string="Materiales", copy=True, domain=[('resource_type','=','material')])
    material_extra_ids = fields.One2many('bim.workorder.resources', 'workorder_id', string="Materiales Adicionales", copy=True, domain=[('product_type','=','M'),('workorder_concept_id','=',False)])
    labor_ids = fields.One2many('bim.workorder.resources', 'workorder_id', string="Mano de Obra", copy=True, domain=[('resource_type','=','labor')])
    labor_extra_ids = fields.One2many('bim.workorder.resources', 'workorder_id', string="Mano de Obra Adicional", copy=True, domain=[('product_type','=','H'),('workorder_concept_id','=',False)])
    user_id = fields.Many2one('res.users', string="Solicitado por", tracking=True, default=lambda self: self.env.user)
    date_start = fields.Date("Fecha Inicio", required=True, copy=True, default=fields.Date.today)
    order_ids = fields.Many2many('purchase.order', string="Ordenes")
    picking_ids = fields.Many2many('stock.picking', string="Recepciones", compute="_compute_pickings")
    date_end = fields.Date("Fecha Termino", copy=True)
    note = fields.Text('Comentarios')
    priority = fields.Char(string='Prioridad')
    supply = fields.Char(string='Abastecimiento')
    amount_labor = fields.Float(string='Coste MO', compute="_get_total_timesheet")
    amount_material = fields.Float(string='Coste MAT', compute="_get_total_inventory")
    #qty_labor_execute = fields.Float(string='MO Ejecutada', compute="_get_total_timesheet")
    #qty_material_execute = fields.Float(string='MAT Ejecutado', compute="_get_total_inventory")
    #priority = fields.Selection([
    #    ('1', '1'),
    #    ('2', '2'),
    #    ('3', '3')], string='Prioridad',
    #    index=True, default='1', tracking=True)
    #supply = fields.Selection([
    #    ('hold', 'Bloqueado'),
    #    ('wait', 'Falta información'),
    #    ('done', 'Recibido comletamente')],
    #    string='Abastecimiento', default='hold', tracking=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Aprobado'),
        ('close', 'Terminado'),
        ('delivered', 'Entregado'),
        ('cancel', 'Cancelado')],
        string='Estado', default='draft', tracking=True)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('order_ids')
    def _get_order_count(self):
        for rec in self:
            rec.order_count = len(rec.order_ids)

    @api.depends('concept_ids')
    def _get_advance_percent(self):
        timesheet = self.env['workorder.timesheet']
        for record in self:
            qty_exe = sum(line.qty_execute_mo for line in record.concept_ids)
            qty_ot = sum(line.qty_worder for line in record.concept_ids)
            record.advance = (qty_exe / qty_ot) if qty_ot > 0 else 0

    @api.depends('order_ids')
    def _compute_pickings(self):
        stock_picking = self.env['stock.picking']
        for record in self:
            # Movimiento de Entrada
            picks = [pick.id for order in record.order_ids for pick in order.picking_ids if pick.picking_type_id.code == 'incoming' and pick.state == 'done']
            record.picking_ids = picks and [(6,0,picks)] or []

    @api.depends('labor_ids','labor_extra_ids','concept_ids')
    def _get_total_timesheet(self):
        for record in self:
            record.amount_labor = sum(line.amt_execute_mo for line in record.concept_ids)

    @api.depends('material_ids','material_extra_ids','concept_ids')
    def _get_total_inventory(self):
        for record in self:
            record.amount_material = sum(line.amt_execute_mt for line in record.concept_ids)

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

    @api.onchange('labor_extra_ids')
    def onchange_extra_labor(self):
        if self.labor_extra_ids:
            for extra in self.labor_extra_ids:
                if extra.sequence == 0:
                    extra.sequence = len(self.labor_extra_ids)

    @api.onchange('material_extra_ids')
    def onchange_extra_material(self):
        if self.material_extra_ids:
            for extra in self.material_extra_ids:
                if extra.sequence == 0:
                    extra.sequence = len(self.material_extra_ids)

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

    def action_confirm(self):
        #messagebox.showinfo(message="Mensaje", title="Título")
        return self.write({'state': 'done'})

    def action_delivery(self):
        return self.write({'state': 'delivered'})

    def action_close(self):
        return self.write({'state': 'close'})

    def action_cancel(self):
        return self.write({'state': 'cancel'})

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
                sequence = max(record.labor_ids.mapped('sequence')) + 1 if record.labor_ids else 1
            else:
                vals = [l.resource_id.id for l in record.material_ids]
                sequence = max(record.material_ids.mapped('sequence')) + 1 if record.material_ids else 1

            for res_id in resource_ids:
                resource = concept_ob.browse(res_id)
                # Cantidad a Ordenar
                if resource and resource.product_id:
                    qty_ordered = (resource.quantity * line_parent.qty_worder) - self._get_product_stock(resource.product_id)

                if not res_id in vals:
                    line = {'workorder_id': record.id,
                            'resource_id': res_id,
                            'type': 'budget_in',
                            'sequence': sequence,
                            'workorder_concept_id': line_parent.id,
                            'category_id': resource.product_id.categ_id.id,
                            'qty_ordered': qty_ordered > 0 and qty_ordered or 0
                            }
                    if type == 'material':
                        # Busqueda de Acuerdo y/o Proveedores de Material
                        purch_vals = self.get_purchase_history(resource.product_id)
                        line.update(purch_vals)
                    lines.append((0, 0, line))
                    sequence += 1

                # Actualizar las lineas existentes
                else:
                    for mat in record.material_ids:
                        if mat.resource_id.id == res_id:
                            mat.qty_ordered = qty_ordered > 0 and qty_ordered or 0

            #Creacion de Nuevas Lineas si existen
            print (lines)
            if lines:
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
        self.ensure_one()
        material_ids = False
        show = self._context.get('show')
        domain = [('workorder_id','=',self.id)]

        if show == 'budget':
            material_ids = self.material_ids.ids
            action = self.env.ref('bim_workorder.action_material_budget_tree_all').read()[0]
        else:
            material_ids = self.material_extra_ids.ids
            action = self.env.ref('bim_workorder.action_material_extra_tree_all').read()[0]

        if material_ids:
            domain.append(('id','in',material_ids))
            action['domain'] = domain
            return action

        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Nuevo',
                'res_model': 'bim.workorder.resources',
                'view_type': 'tree',
                'view_mode': 'tree',
                'target': 'current',
                'context': {'default_workorder_id': self.id}
            }

    def create_purchase_requisition(self):
        search_ids = []
        for record in self:
            context = self._context
            project = record.project_id
            material_lines =  record.material_ids.filtered(lambda l: l.order_assign)
            extra_mat_lines = record.material_extra_ids.filtered(lambda l: l.order_assign)
            product_lines = []

            for line in material_lines:
                partner_ids = []
                if line.vendor_first_id:
                    partner_ids.append(line.vendor_first_id.id)
                #if line.vendor_second_id:
                #    partner_ids.append(line.vendor_second_id.id)

                resource = line.resource_id
                product_lines.append((0,0,{
                    'product_id': resource.product_id.id,
                    'um_id': resource.uom_id.id,
                    'quant': line.qty_ordered,
                    'cost': line.price_unit,
                    'obs': line.note,
                    'partner_ids': partner_ids and [(6,0,partner_ids)] or [],
                    'analytic_id': project.analytic_id.id or False,
                    'workorder_resource_id': line.id,
                    'workorder_departure_id': line.concept_id.id,
                }))

            for line in extra_mat_lines:
                partner_ids = []
                if line.vendor_first_id:
                    partner_ids.append(line.vendor_first_id.id)
                #if line.vendor_second_id:
                #    partner_ids.append(line.vendor_second_id.id)
                product_lines.append((0,0,{
                    'product_id': line.product_id.id,
                    'um_id': line.product_id.uom_id.id,
                    'quant': line.qty_ordered,
                    'cost': line.price_unit,
                    'obs': line.note,
                    'partner_ids': partner_ids and [(6,0,partner_ids)] or [],
                    'analytic_id': project.analytic_id.id or False,
                    'workorder_resource_id': line.id,
                    'workorder_departure_id': line.departure_id.id,
                }))

            if not product_lines:
                 raise ValidationError(u'No existen Materiales a procesar')

            requisition = self.with_context(active_id=project.id,uid=lambda s: s.env.user).env['bim.purchase.requisition'].create({
                'project_id': project.id,
                'analytic_id': project.analytic_id.id or False,
                'date_begin': fields.Datetime.now(),
                'space_id': record.space_id.id,
                'product_ids': product_lines })
            search_ids.append(requisition.id)
            record.requisition_ids = [(4,requisition.id,None)]


        # Retorno
        action = {
            'name': _('Solicitud de Materiales'),
            'type': 'ir.actions.act_window',
            'res_model': 'bim.purchase.requisition'
        }
        if len(search_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': search_ids[0],
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', search_ids)],
            })
        return action

    def action_view_purchases(self):
        purchases = self.mapped('order_ids')
        action = self.env.ref('purchase.purchase_rfq').read()[0]
        if len(purchases) > 0:
            action['domain'] = [('id', 'in', purchases.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    # ~ def action_view_requisitions(self):
        # ~ action = self.env.ref('base_bim_2.action_bim_purchase_requisition').read()[0]
        # ~ requisitions = self.mapped('requisition_ids')
        # ~ if len(requisitions) > 1:
            # ~ action['domain'] = [('id', 'in', requisitions.ids)]
        # ~ elif requisitions:
            # ~ form_view = [(self.env.ref('base_bim_2.view_form_bim_purchase_requisition').id, 'form')]
            # ~ if 'views' in action:
                # ~ action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            # ~ else:
                # ~ action['views'] = form_view
            # ~ action['res_id'] = requisitions.id
        # ~ return action


class BimWorkorderConcepts(models.Model):
    _name = 'bim.workorder.concepts'
    _description = "Partidas y Mediciones Orden de Trabajo BIM"

    @api.depends('concept_id')
    def _get_execute(self):
        res_obj = self.env['bim.workorder.resources']
        for record in self:
            exe_qty_mo = 0
            exe_amt_mo = exe_amt_mt = 0
            if record.concept_id:
                #lines_with = res_obj.search([('workorder_concept_id','=',record.id)])
                lines_with = res_obj.search([('workorder_id','=',record.workorder_id.id),('concept_id','=',record.concept_id.id)])
                lines_out = res_obj.search([('workorder_id','=',record.workorder_id.id),('departure_id','=',record.concept_id.id)])
                lines = lines_with + lines_out
                lines_mo = lines.filtered(lambda x:x.qty_execute > 0)
                lines_mt = lines.filtered(lambda x:x.picking_out)
                exe_qty_mo = lines_mo and max([line.qty_execute for line in lines_mo]) or 0.0 #sum(line.qty_execute for line in lines_mo)#
                exe_amt_mo = sum(line.price_cost * line.duration_real  for line in lines_mo)
                exe_amt_mt = sum(line.total_picking_out for line in lines_mt)

            record.qty_execute_mo = exe_qty_mo
            record.amt_execute_mo = exe_amt_mo
            record.amt_execute_mt = exe_amt_mt

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
    qty_execute_mo = fields.Float(string='Cant.Eje MO', compute="_get_execute")
    amt_execute_mo = fields.Float(string='Total MO', compute="_get_execute")
    amt_execute_mt = fields.Float(string='Total MT', compute="_get_execute")
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
    difficulty = fields.Float(string='Dificultad(%)')
    date_start = fields.Date("Inicio", required=True, default=fields.Date.today)
    date_stop = fields.Date("Termino", required=True, compute="_get_factors")
    duration_cmpt = fields.Float(string='Duración calculada', compute="_get_factors") # Cantidad Calculada Materiales
    duration_real = fields.Float(string='Duración real', compute="_compute_timesheet")
    qty_execute = fields.Float(string='Cantidad ejecutada', compute="_compute_timesheet")
    efficiency_cmpt = fields.Float(string='Rendimiento',related="resource_id.quantity") # cantidad del recurso
    efficiency_real = fields.Float(string='Rendimiento real', compute="_get_factors")
    efficiency_extra = fields.Float(string='Rendimiento extra')
    deviance_real = fields.Float(string='Desviación real', compute="_get_factors")
    qty_available = fields.Float(string='Stock', compute="_get_material_stock")
    qty_ordered = fields.Float(string='Cant a Pedir')
    price_cost = fields.Float(string='Costo Producto',compute='_compute_cost_price')
    price_unit = fields.Float(string='Menor Costo')
    order_assign = fields.Boolean(string='Sol Cotización')
    order_ids = fields.Many2many('purchase.order', string="N° ODC")
    order_confirm_ids = fields.Many2many('purchase.order', string="Ordenes", compute='_compute_purchases')
    order_agree_id = fields.Many2one('purchase.requisition', string="Acuerdo ODC")
    vendor_first_id = fields.Many2one('res.partner', string="Proveedor #1")
    vendor_second_id = fields.Many2one('res.partner', string="Proveedor #2")
    category_id = fields.Many2one('product.category', string="Categoria")
    workorder_id = fields.Many2one('bim.workorder', string="Orden")
    workorder_concept_id = fields.Many2one('bim.workorder.concepts', string="Partida/Medición")
    budget_id = fields.Many2one('bim.budget',related='workorder_id.budget_id', string="Presupuesto")
    space_id = fields.Many2one('bim.budget.space',related='workorder_id.space_id', string="Espacio")
    concept_id = fields.Many2one('bim.concepts', string="Partida",related='workorder_concept_id.concept_id')
    resource_id = fields.Many2one('bim.concepts', string="Recurso")
    picking_in = fields.Many2many('stock.picking', string="Recepciones", compute='_compute_pickings')
    picking_out = fields.Many2many('stock.picking', string="Entrega Instaladores", compute='_compute_pickings')
    total_picking_out = fields.Float(string="Total Entrega Instaladores", compute='_compute_pickings')
    resource_type = fields.Selection(related='resource_id.type', string="Tipo Recurso")
    reason = fields.Char(string='Motivo')
    sequence = fields.Integer(string='N°')
    user_id = fields.Many2one('res.users', string="Aprobado por")
    note = fields.Text('Notas')
    supply = fields.Selection([
        ('quotation', 'Cotización'),
        ('ordered', 'Orden de compra'),
        ('invoiced','Facturado')],
        string='Abastecimiento', compute='_get_state_picking', readonly=True, copy=False, default='quotation')# store=True,
    type = fields.Selection([
        ('budget_in', 'Presupuestado'),
        ('budget_out','No Presupuestado')],
        string='Tipo', default='budget_out', tracking=True)
    #Extra
    departure_id = fields.Many2one('bim.concepts', string="Otra Partida", domain="[('budget_id','=',budget_id),('type','=','departure')]")
    product_id = fields.Many2one('product.product', string="Recurso adicional")
    product_type = fields.Selection(related='product_id.resource_type', string="Tipo Producto")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('product_id','resource_id')
    def _compute_cost_price(self):
        for record in self:
            cost = 0
            if record.resource_id:
                cost = record.resource_id.product_id.standard_price
            elif record.product_id:
                cost = record.product_id.standard_price
            record.price_cost = cost

    @api.depends('type')
    def _compute_name(self):
        for record in self:
            field_ref = record.resource_id if record.type == 'budget_in' else record.product_id
            record.name = field_ref.name

    @api.depends('order_ids')
    def _get_state_picking(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for record in self:
            record.supply = 'quotation'
            for order in record.order_ids:
                if any(float_compare(line.qty_invoiced, line.product_qty if line.product_id.purchase_method == 'purchase' else line.qty_received, precision_digits=precision)
                    == -1
                    for line in order.order_line.filtered(lambda l: not l.display_type)):
                    record.supply = 'ordered'

                elif (all(
                        float_compare(
                            line.qty_invoiced,
                            line.product_qty if line.product_id.purchase_method == "purchase" else line.qty_received,
                            precision_digits=precision,) >= 0
                        for line in order.order_line.filtered(lambda l: not l.display_type)) and order.invoice_ids):

                    record.supply = 'invoiced'
                else:
                    record.supply = 'quotation'

    @api.depends('workorder_concept_id','efficiency_cmpt','efficiency_extra','duration_real','departure_id','difficulty','date_start','qty_execute')
    def _get_factors(self):
        for record in self:
            difficulty = record.difficulty / 100
            efficiency = record.efficiency_cmpt if record.type == 'budget_in' else record.efficiency_extra # Rendimiento
            qty_worder = record.workorder_concept_id.qty_worder if record.workorder_concept_id else record.get_quantity_departure(record.departure_id)
            record.duration_cmpt = (efficiency + (efficiency * difficulty)) * qty_worder if (record.resource_type == 'labor' or record.product_type == 'H') else (efficiency * qty_worder)
            record.efficiency_real = (record.duration_real / record.qty_execute) if record.qty_execute > 0 else 0.0
            record.deviance_real = record.duration_real - record.duration_cmpt
            record.date_stop = record.date_start + relativedelta(days=record.duration_cmpt)

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
            record.qty_execute = sum(line.unit_execute for line in lines) #lines and max([line.unit_execute for line in lines]) or 0.0

    @api.depends('order_ids')
    def _compute_purchases(self):
        for record in self:
            record.order_confirm_ids = record.order_ids.filtered(lambda o: o.state == 'purchase')

    @api.depends('order_ids')
    def _compute_pickings(self):
        for record in self:
            project = record.budget_id.project_id
            departure = record.concept_id if record.type == 'budget_in' else record.departure_id
            product = record.resource_id.product_id if record.type == 'budget_in' else record.product_id

            stock_picking = record.order_ids.mapped('picking_ids')
            # Movimiento de Entrada
            picks_in = stock_picking.filtered(lambda p: p.picking_type_id.code == 'incoming' and p.state == 'done')
            # Movimientos internos
            installer_location_ids = project.install_location_ids.mapped('location_id').ids
            picks_out = stock_picking.filtered(lambda p: p.state == 'done' and p.picking_type_id.code == 'internal' and p.location_dest_id.id in installer_location_ids)
            # valores
            record.picking_in = picks_in
            record.picking_out = picks_out
            record.total_picking_out = sum(
                move.quantity_done * move.price_unit
                for pick in picks_out for move in pick.move_ids_without_package
                if move.workorder_departure_id and move.workorder_departure_id.id == departure.id)


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
    def onchange_purchase(self):
        depart_list = []
        if self.workorder_id and self.product_id:
            self.category_id = self.product_id.categ_id.id
            purch_vals = self.workorder_id.get_purchase_history(self.product_id)
            self.write(purch_vals)

    @api.onchange('product_id','departure_id','efficiency_extra')
    def onchange_qty_ordered_extra(self):
        qty_ordered = self.duration_cmpt - self.qty_available
        self.qty_ordered = qty_ordered > 0 and qty_ordered or 0

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
        action['domain'] = [('resource_id', '=', id_res)]
        action['context'] = {'default_resource_id': id_res,'default_workorder_id': self.workorder_id.id}
        return action

    def open_picking_view(self):
        pickings = [pick.id for order in self.order_ids for pick in order.picking_ids]
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if len(pickings) > 0:
            action['domain'] = [('id', 'in', pickings)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def open_purchase_view(self):
        purchases = self.mapped('order_ids')
        action = self.env.ref('purchase.purchase_rfq').read()[0]
        if len(purchases) > 0:
            action['domain'] = [('id', 'in', purchases.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def unlink(self):
        for record in self:
            if record.order_ids or record.picking_out:
                raise ValidationError('No puede eliminar un material que posee Ordenes asociadas.')
        #self.order_ids..unlink()
        return super().unlink()

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

