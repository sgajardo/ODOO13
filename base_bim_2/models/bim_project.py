# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import xlwt
import re
import io
import tempfile
from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.modules.module import get_module_resource
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang
from xlwt import easyxf, Workbook
from io import StringIO

class BimTag(models.Model):
    _name = 'bim.tag'
    _description = 'Bim Tag'

    active = fields.Boolean(default=True)
    color = fields.Integer(required=True, default=0)
    name = fields.Char(required=True)

class bim_project(models.Model):
    _description = "Obra"
    _name = 'bim.project'
    _order = "id desc"
    _rec_name = 'nombre'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    @api.depends('timesheet_ids')
    def _compute_timesheet_count(self):
        for project in self:
            project.timesheet_count = len(project.timesheet_ids)

    @api.depends('document_ids')
    def _compute_count_docs(self):
        for project in self:
            project.count_docs = len(project.document_ids)

    @api.depends('objects_ids')
    def _compute_count_objects(self):
        for project in self:
            project.count_objects = len(project.objects_ids)

    @api.depends('task_ids')
    def _compute_count_tasks(self):
        for project in self:
            project.task_done_count = len(project.task_ids.filtered(lambda r: r.state == 'end'))
            project.count_tasks = len(project.task_ids.filtered(lambda r: r.state != 'cancel'))

    @api.depends('ticket_ids')
    def _compute_count_tickets(self):
        for project in self:
            project.ticket_done_count = len(project.ticket_ids.filtered(lambda r: r.state == 'calificado'))
            project.count_tickets = len(project.ticket_ids.filtered(lambda r: r.state != 'cancel'))

    @api.depends('employee_line_ids')
    def _compute_employee_count(self):
        for project in self:
            project.employee_count = len(project.employee_line_ids)

    def _compute_requisition(self):
        for project in self:
            project.requisition_count = len(self.env['bim.purchase.requisition'].search([('project_id','=',project.id)]))

    @api.depends('paidstate_ids')
    def _compute_paidstate(self):
        for project in self:
            project.paidstatus_count = len(project.paidstate_ids)

    @api.depends('budget_ids')
    def _get_budget_count(self):
        for project in self:
            project.budget_count = len(project.budget_ids)

    @api.depends('maintenance_ids')
    def _compute_maintenance(self):
        for project in self:
            project.maintenance_done_count = len(project.maintenance_ids.filtered(lambda r: r.state == 'done' or r.state == 'invoiced'))
            project.maintenance_count = len(project.maintenance_ids)

    @api.depends('invoice_ids')
    def _compute_invoice(self):
        for project in self:
            invoices = project.invoice_ids
            out_invoices = invoices.filtered(lambda i: i.state != 'cancel' and i.type == 'out_invoice')
            in_invoices = invoices.filtered(lambda i: i.state != 'cancel' and i.type == 'in_invoice')
            refunds = invoices.filtered(lambda i: i.state != 'cancel' and i.type == 'out_refund')
            in_refunds = invoices.filtered(lambda i: i.state != 'cancel' and i.type == 'in_refund')
            project.out_invoice_count = len(out_invoices)
            project.in_invoice_count = len(in_invoices)
            project.out_invoiced_amount = sum(x.amount_total for x in out_invoices) - sum(x.amount_total for x in refunds)
            project.in_invoiced_amount = sum(x.amount_total for x in in_invoices) - sum(x.amount_total for x in in_refunds)

    @api.depends('budget_ids')
    def _compute_amount(self):
        for project in self:
            project.balance = sum(x.balance for x in project.budget_ids)
            project.surface = sum(x.surface for x in project.budget_ids)

    @api.depends('budget_ids')
    def _compute_hh(self):
        for project in self:
            project.hh_planificadas = 0

    @api.depends('stock_location_id')
    def _compute_valuation(self):
        quant_obj = self.env['stock.quant']
        for project in self:
            if project.stock_location_id:
                quants = quant_obj.search([('location_id', '=', project.stock_location_id.id)])
                project.inventory_valuation = sum(q.value for q in quants)
            else:
                project.inventory_valuation = 0

    @api.depends('stock_location_id')
    def _compute_outgoing_val(self):
        picking_type_obj = self.env['stock.picking.type']
        picking_obj = self.env['stock.picking']
        for project in self:
            if project.stock_location_id:
                pickings = picking_obj.search([
                    ('location_id','=',project.stock_location_id.id),
                    ('location_dest_id.usage','=','customer'), ])
                if pickings:
                    stock_moves = pickings.mapped('move_lines')
                    project.outgoing_val = sum(m.price_unit * m.product_uom_qty for m in stock_moves)
                else:
                    project.outgoing_val = 0
            else:
                project.outgoing_val = 0
    @api.model
    def _default_image(self):
        image_path = get_module_resource('base_bim_2', 'static/src/img', 'default_image.png')
        return base64.b64encode(open(image_path, 'rb').read())

    @api.depends('state')
    def _get_project_state(self):
        for record in self:
            if record.state in ['5','6','8','9']:
                record.project_state = 'in_process'
            elif record.state == '7':
                record.project_state = 'cancel'

    @api.depends('outsourcing_ids')
    def _compute_outsourcing_count(self):
        for project in self:
            project.outsourcing_count = len(project.outsourcing_ids)

    @api.depends('checklist_ids')
    def _compute_chekclist_count(self):
        for project in self:
            project.checklist_count = len(project.checklist_ids)

    @api.depends('workorder_ids')
    def _compute_workorder_count(self):
        for project in self:
            project.workorder_count = len(project.workorder_ids)

    @api.depends('balance', 'surface')
    def _compute_balance_surface(self):
        for record in self:
            if record.surface != 0:
                balace_surface = record.balance / record.surface
            else:
                balace_surface = 0.0
            record.balace_surface = balace_surface

    def compute_executed_attendance_and_cost(self):
        for record in self:
            executed = 0
            cost = 0
            for line in record.project_attendance_ids:
                executed += line.worked_hours
                cost += line.attendance_cost
            record.executed_attendance = executed
            record.attendance_cost = cost
    # Datos
    name = fields.Char('Código', translate=True, default="Nuevo", track_visibility='onchange', copy=False)
    nombre = fields.Char('Nombre', translate=True, track_visibility='onchange', copy=True)
    notes = fields.Text(string="Observaciones")
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company, required=True )
    user_id = fields.Many2one('res.users', string='Supervisor', track_visibility='onchange',  default=lambda self: self.env.user)
    task_ids = fields.One2many('bim.task', 'project_id', 'Tareas')
    ticket_ids = fields.One2many('ticket.bim', 'project_id', 'Ticket')
    obs = fields.Text('Notas')

    retention = fields.Float('Retención %', default=lambda self: self.env.company.retention)

    image_1920 = fields.Image("Imagen", max_width=1920, max_height=1920, default=_default_image)
    image_128 = fields.Image("Image 128", max_width=128, max_height=128, store=True, default=_default_image)

    budget_count = fields.Integer('N° Presupuestos', compute="_get_budget_count")
    budget_ids = fields.One2many('bim.budget','project_id','Presupuestos')
    hh_planificadas = fields.Float('HH Planificadas', compute="_compute_hh")
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True, default=lambda r: r.env.company.currency_id)
    customer_id = fields.Many2one('res.partner', string='Cliente', track_visibility='onchange')
    warehouse_id = fields.Many2one('stock.warehouse', string='Bodega')
    stock_location_id = fields.Many2one('stock.location', string='Ubicación Stock')
    country_id = fields.Many2one('res.country', string='Pais')
    street_id = fields.Many2one('res.partner', string='Dirección')

    date_ini = fields.Date('Fecha Inicio', default=fields.Date.today)
    date_end = fields.Date('Fecha de Fin')
    date_ini_real = fields.Date('Fecha Inicio Real')
    date_end_real = fields.Date('Fecha de Fin Real')

    expedient = fields.Char('Expediente', translate=True)
    date_contract = fields.Date('Fecha Contrato', help="Fecha de contrato")
    adjudication_date = fields.Date('Fecha de Adjudicación')
    document_ids = fields.One2many('bim.documentation','project_id','Documentos')
    objects_ids = fields.One2many('bim.object', 'project_id', 'Objects')
    count_docs = fields.Integer('Cantidad Documentos', compute="_compute_count_docs")
    count_objects = fields.Integer('Cantidad Objetos', compute="_compute_count_objects")
    count_tasks = fields.Integer('Cantidad Tareas', compute="_compute_count_tasks")
    count_tickets = fields.Integer('Cantidad Tickets', compute="_compute_count_tickets")
    task_done_count = fields.Integer('Cantidad Tareas Ejecutadas', compute="_compute_count_tasks")
    ticket_done_count = fields.Integer('Cantidad Tickets Ejecutados', compute="_compute_count_tickets")
    timesheet_count = fields.Integer('Cantidad Hoja de Tiempo', compute="_compute_timesheet_count")
    timesheet_ids = fields.One2many('bim.project.employee.timesheet', 'project_id', 'Horas Empleados')
    employee_count = fields.Integer('Cantidad Empleados', compute="_compute_employee_count")
    employee_line_ids = fields.One2many('bim.project.employee', 'project_id', 'Líneas de Empleados')
    requisition_count = fields.Integer('Cantidad Solicitud Materiales', compute="_compute_requisition")
    paidstate_ids = fields.One2many('bim.paidstate','project_id','Estados de Pago')
    paidstatus_count = fields.Integer('Cantidad EP', compute="_compute_paidstate")
    paidstate_product = fields.Many2one('product.product', string='Producto Estado Pago', default=lambda self: self.env.company.paidstate_product)
    retetion_product = fields.Many2one('product.product', string='Producto para Retención', default=lambda self: self.env.company.retention_product)
    department_id = fields.Many2one('bim.department', string='Departamento')
    maintenance_ids = fields.One2many('bim.maintenance', 'project_id', 'Mantenimientos')
    maintenance_done_count = fields.Integer('Cantidad Mantenimientos Ejecutados', compute="_compute_maintenance")
    maintenance_count = fields.Integer('Cantidad Total Mantenimientos', compute="_compute_maintenance")
    invoice_ids = fields.One2many('account.move', 'project_id', 'Facturas')
    out_invoice_count = fields.Integer('Cantidad Facturas Ventas', compute="_compute_invoice")
    in_invoice_count = fields.Integer('Cantidad Facturas Compras', compute="_compute_invoice")
    out_invoiced_amount = fields.Monetary('Monto Facturado Ventas', compute="_compute_invoice")
    in_invoiced_amount = fields.Monetary('Monto Facturado Compras', compute="_compute_invoice")
    outgoing_val = fields.Monetary('Ingreso por Salidas', compute="_compute_outgoing_val")
    inventory_valuation = fields.Monetary('Valoración Inventario', compute="_compute_valuation")
    expense_val = fields.Monetary('Calculo Rendiciones',)# compute="_compute_expenses")
    amount_award = fields.Monetary('Monto Adjudicación',)
    amount_tender = fields.Monetary('Monto Licitación',)
    analytic_created = fields.Boolean('Centro Costo Creado', help="Indica si los centros de costos de la project ya han sido creados")
    maintenance_contract = fields.Boolean('Contrato Mantenimiento')
    analytic_id = fields.Many2one('account.analytic.account','Centro de Costo')
    tag_ids = fields.Many2many('bim.tag', string='Etiquetas')
    outsourcing_count = fields.Integer('Subcontratos', compute="_compute_outsourcing_count")
    outsourcing_ids = fields.One2many('bim.project.outsourcing', 'project_id', 'Gastos Subcontratos')
    maintenance = fields.Boolean("Mantenimiento Creado", default=False)
    maintenance_amount = fields.Monetary('Monto Total Contrato', help="Monto total del contrato de mantenimiento")
    maintenance_duration = fields.Integer('Duración de mantenimiento', help="Duración estimada de cada mantenimiento en días", default=1)
    maintenance_start_date = fields.Date('Fecha Inicial', help="Fecha inicio de contrato mantenimiento")
    maintenance_end_date = fields.Date('Fecha Final', help="Fecha fin de contrato de mantenimiento")
    maintenance_currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda r: r.env.user.company_id.currency_id)
    surface = fields.Float(string="Superficie m2", compute='_compute_amount', help="Superficie Construida (m2).")
    balance = fields.Monetary(string="Importe", compute='_compute_amount', help="Importe General del Presupuesto.", store=True)
    balace_surface = fields.Monetary(string="Importe /m2", compute=_compute_balance_surface, help="Importe por m2")
    indicator_ids = fields.One2many('bim.project.indicator', 'project_id', 'Indicadores comparativos')
    color = fields.Integer('Color Index', default=0)
    priority = fields.Selection(
        [('1', 'Baja'),
         ('2', 'Media'),
         ('3', 'Alta'),
         ('4', 'Muy Alta'),
         ('5', 'Urgente'),
         ], 'Prioridad', default='1', help="Prioridad de la Obra")

    maintenance_period = fields.Selection(
        [('12', 'Mensual'),
         ('2', 'Semestral'),
         ('1', 'Anual'),
         ('3', 'Trimestral'),
         ('6', 'Bimensual'),
         ], 'Frecuencia', default='12', help="Frecuencia de cobro del contrato de mantenimiento")
    project_state = fields.Selection(
        [('in_process', 'Adjudicado'),('cancel', 'Perdido')],
        string='Estado Seguimiento',compute="_get_project_state", store=True)
    state = fields.Selection(
        [('1', 'Nuevo'),
         ('2', 'Estudio'),
         ('3', 'Licitación'),
         ('4', 'Revisión'),
         ('5', 'Adjudicado'),
         ('6', 'Ejecución'),
         ('7', 'Perdido'),
         ('8', 'Calidad'),
         ('9', 'Terminado')],
        'Estado', size=1, default='1',track_visibility='onchange')
    checklist_ids = fields.One2many('bim.checklist', 'project_id', 'Checklists')
    checklist_count = fields.Integer('N° Checklists', compute="_compute_chekclist_count")
    workorder_ids = fields.One2many('bim.work.order', 'project_id', 'Ordenes de Trabajo')
    workorder_count = fields.Integer('N° Ordenes de Trabajo', compute="_compute_workorder_count")
    price_agreed_ids = fields.One2many('bim.list.price.agreed', 'project_id', string='Precios Acordados')
    project_attendance_ids = fields.One2many('hr.attendance', 'project_id')
    executed_attendance = fields.Float(compute='compute_executed_attendance_and_cost')
    attendance_cost = fields.Float(compute='compute_executed_attendance_and_cost')

    @api.onchange('warehouse_id','stock_location_id')
    def onchange_stock(self):
        if not self.stock_location_id and self.warehouse_id:
            self.stock_location_id = self.warehouse_id.lot_stock_id.id

        if not self.warehouse_id:
            self.stock_location_id = False

        if self.stock_location_id:
            warehouse = self.env['stock.warehouse'].search([('lot_stock_id','=',self.stock_location_id.id)],limit=1)
            if warehouse and self.warehouse_id != warehouse:
                self.warehouse_id = warehouse.id

    @api.onchange('date_end','date_ini')
    def onchange_date(self):
        if not self.date_ini:
           datetime.now()

        if self.date_end and self.date_end <= self.date_ini:
            warning = {
                'title': _('Warning!'),
                'message': _(u'La fecha de finalización no puede ser menor a la fecha de inicio!'),
            }
            self.date_end = False
            return {'warning': warning}

    def action_estudio(self):
        #self.compute_indicators()
        self.write({'state': '2', 'date_end': False})

    def action_nuevo(self):
        #self.compute_indicators()
        self.write({'state': '1', 'date_end': False})

    def action_licitacion(self):
        #self.compute_indicators()
        self.write({'state': '3'})

    def action_revision(self):
        #self.compute_indicators()
        self.write({'state': '4'})

    def action_adjudicar(self):
        #self.compute_indicators()
        self.write({'state': '5', 'adjudication_date': datetime.now()})

    def action_perdido(self):
        #self.compute_indicators()
        self.write({'state': '7', 'date_end': datetime.now()})

    def action_proceso(self):
        #self.compute_indicators()
        self.write({'state': '6', 'date_ini': datetime.now()})

    def action_calidad(self):
        #self.compute_indicators()
        self.write({'state': '8'})

    def action_entregar(self):
        #self.compute_indicators()
        self.write({'state': '9', 'date_end': datetime.now()})

    def action_create_maintenance(self):
        fmt = '%Y-%m-%d'
        for project in self:
            if project.maintenance_amount <= 0.0:
                raise ValidationError('El monto del contrato de mantenimiento no puede ser cero (0)')
            if not project.maintenance_period:
                raise ValidationError('Seleccione la periodicidad del contrato de mantenimiento')
            if not project.maintenance_start_date:
                raise ValidationError('Ingrese una fecha de inicio de los mantenimientos')
            date_start = datetime.strptime(str(project.maintenance_start_date), fmt).replace(hour=8, minute=00)
            date_end = datetime.strptime(str(project.maintenance_end_date), fmt).replace(hour=23, minute=59)
            maintenance_obj = self.env['bim.maintenance']
            dif = date_end - date_start
            frequency = int(dif.days/30.417)/int(project.maintenance_period)
            for i in range(int(project.maintenance_period)):
                index = i+1
                maintenance_date = index == 1 and date_start or date_start + relativedelta(months=round(frequency))
                maintenance_obj.create({
                    'project_id': project.id,
                    'partner_id': project.customer_id.id,
                    'maintenance_duration': project.maintenance_duration,
                    'date_planned': maintenance_date,
                    'date_done': maintenance_date + relativedelta(days=project.maintenance_duration),
                    'invoice_amount': project.maintenance_amount/int(project.maintenance_period)
                })
                date_start = maintenance_date
            project.maintenance = True

    def create_warehouse(self):
        for project in self:
            warehouse = self.env['stock.warehouse'].create({
                'name': project.nombre,
                'code': project.nombre,
                'partner_id': project.customer_id and project.customer_id.id or False,
            })
            project.warehouse_id = warehouse.id
            project.stock_location_id = warehouse.lot_stock_id.id

    @api.model
    def create(self, vals):
        if vals.get('name', "Nuevo") == "Nuevo":
            vals['name'] = self.env['ir.sequence'].next_by_code('bim.project') or "Nuevo"

            # Creamos la cuenta anaitica por cada proyecto creado
            analytic = self.env['account.analytic.account'].create({'name': vals['nombre'],
                                                                    'partner_id': vals['customer_id'],
                                                                    'code': vals['name']})
            vals['analytic_id'] = analytic.id

        return super(bim_project, self).create(vals)

    def name_get(self):
        res = super(bim_project, self).name_get()
        result = []
        for element in res:
            project_id = element[0]
            cod = self.browse(project_id).name
            desc = self.browse(project_id).nombre
            name = cod and '[%s] %s' % (cod, desc) or '%s' % desc
            result.append((project_id, name))
        return result


    def action_view_budgets(self):
        budgets = self.mapped('budget_ids')
        action = self.env.ref('base_bim_2.action_bim_budget').read()[0]
        if len(budgets) > 0:
            action['domain'] = [('id', 'in', budgets.ids)]
            action['context'] = {'default_project_id': self.id,'default_currency_id': self.currency_id.id}
            return action
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Nuevo Presupuesto',
                'res_model': 'bim.budget',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current',
                'context': {'default_project_id': self.id,'default_currency_id': self.currency_id.id}
            }

    def action_view_attendance(self):
        project_attendance_ids = self.mapped('project_attendance_ids')
        action = self.env.ref('hr_attendance.hr_attendance_action').sudo().read()[0]
        if len(project_attendance_ids) == 0:
            action['context'] = {'default_project_id': self.id}
            action['views'] = [(False, 'form')]
        else:
            action['domain'] = [('id', 'in', project_attendance_ids.ids)]
            action['context'] = {'default_project_id': self.id}
        return action

    def action_view_requisitions(self):
        requsitions = self.env['bim.purchase.requisition'].search([('project_id','=',self.id)])
        action = self.env.ref('base_bim_2.action_bim_purchase_requisition').read()[0]
        action['domain'] = [('id', 'in', requsitions.ids)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_timesheets(self):
        timesheets = self.mapped('timesheet_ids')
        action = self.env.ref('base_bim_2.action_bim_project_timesheet').read()[0]
        if len(timesheets) > 0:
            action['domain'] = [('id', 'in', timesheets.ids)]
        else:
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'bim.project.employee.timesheet',
                'view_mode': 'form',
                'target': 'current',
                'context': {'default_projects_id': self.id}
            }
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_outsourcing(self):
        outsourcings = self.mapped('outsourcing_ids')
        action = self.env.ref('base_bim_2.action_bim_project_outsourcing').read()[0]
        action['domain'] = [('id', 'in', outsourcings.ids)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_employees(self):
        employees = self.mapped('employee_line_ids')
        action = self.env.ref('base_bim_2.action_bim_project_employee').read()[0]
        action['domain'] = [('id', 'in', employees.ids)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_documents(self):
        documents = self.mapped('document_ids')
        action = self.env.ref('base_bim_2.action_bim_documentation').read()[0]
        action['domain'] = [('id', 'in', documents.ids)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_objects(self):
        bim_objects = self.mapped('objects_ids')
        action = self.env.ref('base_bim_2.action_bim_object').read()[0]
        action['domain'] = [('id', 'in', bim_objects.ids)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_checklist(self):
        checklists = self.mapped('checklist_ids')
        action = self.env.ref('base_bim_2.bim_checklist_action').read()[0]
        action['domain'] = [('id', 'in', checklists.ids)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_workorder(self):
        workorders = self.mapped('workorder_ids')
        action = self.env.ref('base_bim_2.action_work_orders_project').read()[0]
        action['domain'] = [('id', 'in', workorders.ids)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_tasks(self):
        tasks = self.mapped('task_ids')
        action = self.env.ref('base_bim_2.action_bim_task').read()[0]
        action['domain'] = [('id', 'in', tasks.ids)]
        action['context'] = {'default_project_id': self.id}
        return action


    def action_view_tickets(self):
        tickets = self.mapped('ticket_ids')
        action = self.env.ref('base_bim_2.action_ticket_bim').read()[0]
        action['domain'] = [('id', 'in', tickets.ids)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_out_invoices(self):
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

    def action_view_in_invoices(self):
        invoices = []
        for inv in self.invoice_ids:
            if inv.type == 'in_invoice':
                invoices.append(inv.id)
        action = self.env.ref('account.action_move_in_invoice_type').read()[0]
        if len(invoices) > 0:
            action['domain'] = [('id', 'in', invoices)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_view_outgoings(self):
        action = {'type': 'ir.actions.act_window_close'}
        picking_type_obj = self.env['stock.picking.type']
        if self.stock_location_id:
            pickings = self.env['stock.picking'].search([
                ('location_id','=',self.stock_location_id.id),
                ('location_dest_id.usage','=','customer'),
            ])
            if len(pickings) > 0:
                action = self.env.ref('stock.action_picking_tree_all').read()[0]
                action['domain'] = [('id', 'in', pickings.ids)]
        return action

    def action_view_quants(self):
        action = self.env.ref('stock.product_template_open_quants').read()[0]
        action['domain'] = [('location_id', '=', self.stock_location_id.id)]
        action['context'] = {'search_default_productgroup': 1, 'search_default_internal_loc': 1}
        return action

    def action_view_paidstate(self):
        paidstate = self.mapped('paidstate_ids')
        action = self.env.ref('base_bim_2.action_bim_paidstate').read()[0]
        action['domain'] = [('id', 'in', paidstate.ids)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_maintenance(self):
        maintenance = self.mapped('maintenance_ids')
        action = self.env.ref('base_bim_2.action_bim_maintenance').read()[0]
        action['domain'] = [('id', 'in', maintenance.ids)]
        action['context'] = {'default_project_id': self.id}
        return action


class BimProjectOutsourcing(models.Model):
    _description = "Gastos Subcontratos Obra"
    _name = 'bim.project.outsourcing'
    _rec_name = 'partner_id'

    name = fields.Char('Descripción')
    partner_id = fields.Many2one('res.partner', 'Proveedor')
    project_id = fields.Many2one('bim.project', 'Obra')
    reference = fields.Char('Referencia EP')
    date = fields.Date('Fecha', default=fields.Date.today())
    amount = fields.Monetary('Importe')
    outsourcing_amount = fields.Monetary('Total')
    currency_id = fields.Many2one('res.currency', string='Moneda',
        readonly=True, default=lambda r: r.env.user.company_id.currency_id)


class bim_project_employee(models.Model):
    _description = "Empleados de Obra"
    _name = 'bim.project.employee'
    _order = 'start_date asc'

    project_id = fields.Many2one('bim.project', 'Obra')
    employee_id = fields.Many2one('hr.employee', 'Empleado')
    start_date = fields.Date('Fecha Inicio')
    end_date = fields.Date('Fecha Fin')
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía",
        default=lambda self: self.env.company, required=True)


class bim_project_employee_timesheet(models.Model):
    _description = "Empleados de Obra"
    _name = 'bim.project.employee.timesheet'
    _rec_name = 'employee_id'
    _order = 'week_start desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id and self.task_id:
            self.project_id = self.task_id.project_id.id

    @api.model
    def default_get(self, fields):
        res = super(bim_project_employee_timesheet, self).default_get(fields)
        today = date.today()
        start = today - timedelta(days=today.weekday())
        res['week_start'] = datetime.strftime(start, '%Y-%m-%d')
        res['week_end'] = datetime.strftime((start + timedelta(days=6)), '%Y-%m-%d')
        return res

    project_id = fields.Many2one('bim.project', 'Obra')
    task_id = fields.Many2one('bim.task', 'Tarea')
    date = fields.Date('Fecha', default=fields.Date.today)
    week_start = fields.Date('Inicio Semana')
    week_end = fields.Date('Fin Semana')
    employee_id = fields.Many2one('hr.employee', 'Empleado')
    total_hours = fields.Float('Total Horas')
    total_extra_hours = fields.Float('Total Horas Extras')
    week_number = fields.Integer('Número de Semana', compute='compute_week_number', store=True)
    work_cost = fields.Float('Costo Mano de Obra', compute='compute_work_cost')
    extra_work_cost = fields.Float('Costo Mano de Obra HE', help="Costo mano de obra de las horas extras", compute='compute_work_cost')
    comment = fields.Text('Comentarios')
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company, required=True )

    @api.depends('employee_id', 'total_hours')
    def compute_work_cost(self):
        for record in self:
            wage = record.employee_id.wage_bim
            hour_wage = (wage / 30) / self.env.user.company_id.working_hours
            record.work_cost = hour_wage * record.total_hours
            record.extra_work_cost = wage * self.env.user.company_id.extra_hour_factor * record.total_extra_hours

    @api.depends('week_start')
    def compute_week_number(self):
        for record in self:
            if record.week_start:
                today = date.today()
                year = int(record.week_start.year)
                month = int(record.week_start.month)
                day = int(record.week_start.day)
                number_week = date(year, month, day).strftime("%V")
                record.week_number = number_week


class bim_obra_indicator(models.Model):
    _description = "Indicadores comparativos"
    _name = 'bim.project.indicator'

    @api.depends('projected', 'budget')
    def _compute_percent(self):
        for record in self:
            record.percent = record.budget > 0.0 and (record.projected / record.budget * 100) or 0.0

    @api.depends('real', 'projected')
    def _compute_diff(self):
        for record in self:
            record.projected = record.budget - record.real

    project_id = fields.Many2one('bim.project', 'Obra', ondelete="cascade")
    currency_id = fields.Many2one('res.currency', 'Moneda', related="project_id.currency_id")
    type = fields.Selection(
        [('M', 'Costo Materiales'),
         ('Q', 'Costo Equipos'),
         ('H', 'Costo Mano de Obra'),
         ('S', 'Costo Sub-Contrato'),
         ('HR', 'Costo Herramientas'),
         ('LO', 'Costo Logístico'),
         ('T', 'Totales'), ],
        'Tipo Indicador', readonly=True)

    budget = fields.Monetary('Presupuesto', help="Valor Presupuestado", readonly=True)
    real = fields.Monetary('Real Certificado', help="Valor real representado en el presupuesto adjudicado", readonly=True)
    projected = fields.Float('Proyectado', help="Diferencia entre el proyectado y el real", compute="_compute_diff")
    percent = fields.Float('%', help="Porcentaje dado por el valor real entre valor estimado", compute="_compute_percent")
