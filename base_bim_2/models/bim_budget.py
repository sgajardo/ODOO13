import base64
import io
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

import xlwt
from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError

inconsistency = {
    '0': 'No se encontraron inconsistecias en el Presupuesto.',
    '1': '-El Recurso %s no tiene Producto asignado (Error en Concepto).',
    '2': '-El Producto %s, asignado al Recurso %s, no es de Tipo Recurso Material (Error en Producto).',
    '3': '-El Producto %s, asignado al Recurso %s, no es de Tipo Recurso Equipo (Error en Producto).',
    '4': '-El Producto %s, asignado al Recurso %s, no es de Tipo Recurso Mano de Obra (Error en Producto),',
    '5': '-El Producto %s, asignado al Recurso %s, es un Servicio (Error en Producto).' ,
    '6': '-El Producto %s, asignado al Recurso %s, es Almacenable (Error en Producto).',
    '7': '-El importe del Recurso %s es cero (0)',
    '8': '-El Capítulo %s tiene cantidad superior a 1.',
    '9': '-El Recurso %s tiene Hijo asignado (Error en Concepto).',
    '10': '-La UoM del Recurso %s es diferente a la UoM del Producto %s relacionado.(Padre %s)',
}

class BimBudget(models.Model):
    _name = 'bim.budget'
    _description = 'Presupuestos'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('concept_ids.balance')
    def _compute_amount(self):
        for budget in self:
            balance = 0
            certified = 0
            for concept in budget.concept_ids:
                if not concept.parent_id:
                    balance += concept.balance
                    certified += concept.balance_cert
            budget.balance = balance
            budget.certified = certified

    @api.depends('concept_ids')
    def _compute_execute(self):
        for budget in self:
            concept_ids = budget.concept_ids.ids

            concepts = budget.concept_ids
            equipments = concepts.filtered(lambda c: c.type == 'equip')
            materials = concepts.filtered(lambda c: c.type == 'material')
            labors = concepts.filtered(lambda c: c.type == 'labor')
            functions = concepts.filtered(lambda c: c.type == 'aux')
            departures = concepts.filtered(lambda c: c.type == 'departure')

            budget.amount_executed_equip = sum(e.amount_execute_equip for e in departures)    #sum(e.amount_execute for e in equipments)
            budget.amount_executed_labor = sum(l.amount_execute_labor for l in departures)        #sum(l.amount_execute for l in labors)
            budget.amount_executed_material = sum(m.amount_execute_material for m in departures)  #sum(m.amount_execute for m in materials)
            budget.amount_executed_other = sum(f.amount_execute for f in functions)     #sum(f.amount_execute for f in functions)


    def _get_value(self, quantity, product):
        if product.cost_method == 'fifo':
            quantity = product.quantity_svl
            if float_is_zero(quantity, precision_rounding=product.uom_id.rounding):
                value = 0.0
            average_cost = product.value_svl / quantity
            value = quantity * average_cost
        else:
            value = quantity * product.standard_price
        return float(value)

    def recursive_certified(self, resource, parent, amount=None):
        amount = amount is None and resource.balance_cert or amount or 0.0
        if parent.parent_id.type == 'departure':
            amount_partial = amount * parent.quantity_cert
            return self.recursive_amount(resource,parent.parent_id,amount_partial)
        else:
            return amount * parent.quantity_cert

    def recursive_amount(self, resource, parent, amount=None):
        amount = amount is None and resource.balance or amount or 0.0
        if parent.type == 'departure':
            amount_partial = amount * parent.quantity
            return self.recursive_amount(resource,parent.parent_id,amount_partial)
        else:
            return amount * parent.quantity

    def get_total(self,resource_id):
        records = self.concept_ids.filtered(lambda c: c.product_id.id == resource_id)
        total = 0
        for rec in records:
            total += self.recursive_amount(rec,rec.parent_id,None)
        return total


    @api.depends('balance','certified','concept_ids.balance')
    def _get_amount_total(self):
        for budget in self:
            concepts = budget.concept_ids
            equipments = concepts.filtered(lambda c: c.type == 'equip')
            materials = concepts.filtered(lambda c: c.type == 'material')
            labors = concepts.filtered(lambda c: c.type == 'labor')
            functions = concepts.filtered(lambda c: c.type == 'aux')

            budget.amount_total_equip = sum(self.get_total(e.id) for e in equipments.mapped('product_id'))
            budget.amount_total_labor = sum(self.get_total(l.id) for l in labors.mapped('product_id'))
            budget.amount_total_material = sum(self.get_total(m.id) for m in materials.mapped('product_id'))
            budget.amount_total_other =  sum(self.recursive_amount(f,f.parent_id,None) for f in functions)

            budget.amount_certified_equip = sum(e.balance_cert for e in equipments)     #sum(self.recursive_certified(e,e.parent_id,None) for e in equipments)   #
            budget.amount_certified_labor = sum(l.balance_cert for l in labors)         #sum(self.recursive_certified(l,l.parent_id,None) for l in labors)       #
            budget.amount_certified_material = sum(m.balance_cert for m in materials)      #sum(self.recursive_certified(m,m.parent_id,None) for m in materials) #
            budget.amount_certified_other =   sum(f.balance_cert for f in functions)      #sum(self.recursive_certified(f,f.parent_id,None) for f in functions)  #

    @api.model
    def create(self, vals):
        if vals.get('code', "New") == "New":
            vals['code'] = self.env['ir.sequence'].next_by_code('bim.budget') or "New"
            vals['space_ids'] = [(0, 0, {'name': vals['code'],'code': '00'})]
        budget = super(BimBudget, self).create(vals)

        if not vals.get('template_id'):
            template = self.env.company.asset_template_id
            self._create_assets(template)

        #if vals.get('template_id'):
        #    template = self.env['bim.assets.template'].browse(vals['template_id'])

        return budget

    def write(self, vals):
        res = super(BimBudget, self).write(vals)
        if 'type' in vals:
            for concept in self.concept_ids:
                concept.update_budget_type()
        return res

    @api.depends('project_id')
    def _compute_surface(self):
        for budget in self:
            budget.surface = 0

    @api.depends('concept_ids')
    def _get_concept_count(self):
        for budget in self:
            budget.concept_count = len(budget.concept_ids)

    @api.depends('stage_ids')
    def _get_stage_count(self):
        for budget in self:
            budget.stage_count = len(budget.stage_ids)

    @api.depends('space_ids')
    def _get_space_count(self):
        for budget in self:
            budget.space_count = len(budget.space_ids)

    @api.depends('concept_ids')
    def _compute_balance_surface(self):
        for record in self:
            concepts = record.env['bim.concepts'].search([('budget_id', '=', record.id),('parent_id', '=', False)])
            total = 0.0
            for concept in concepts:
                total += concept.balance
            if record.surface != 0:
                balace_surface = total / record.surface
            else:
                balace_surface = 0.0
            record.balace_surface = balace_surface

    name = fields.Char('Descripción', required=True, index=True)
    code = fields.Char('Código', size=64, required=True, index=True, default="New")
    note = fields.Text('Resumen', copy=True)
    balace_surface = fields.Monetary(string="Importe /m2", compute=_compute_balance_surface, help="Importe por m2")
    balance = fields.Monetary(string="Importe", compute='_compute_amount', help="Importe General del Presupuesto.")
    certified = fields.Monetary(string="Certificado", compute='_compute_amount', help="Importe Certificado del Presupuesto.")
    surface = fields.Float(string="Superficie m2", help="Superficie Construida (m2).", copy=True)
    project_id = fields.Many2one('bim.project', string='Obra', tracking=True)
    template_id = fields.Many2one('bim.assets.template', string='Plantilla', tracking=True)
    user_id = fields.Many2one('res.users', string='Responsable', tracking=True, default=lambda self: self.env.user)
    indicator_ids = fields.One2many('bim.budget.indicator', 'budget_id', 'Indicadores comparativos')
    concept_ids = fields.One2many('bim.concepts', 'budget_id', 'Concepto')
    stage_ids = fields.One2many('bim.budget.stage', 'budget_id', 'Etapas')
    space_ids = fields.One2many('bim.budget.space', 'budget_id', 'Espacios')
    asset_ids = fields.One2many('bim.budget.assets', 'budget_id', string='Haberes y Descuentos')
    concept_count = fields.Integer('N° Conceptos', compute="_get_concept_count")
    stage_count = fields.Integer('N° Etapas', compute="_get_stage_count")
    space_count = fields.Integer('N° Espacios', compute="_get_space_count")
    company_id = fields.Many2one('res.company', string="Compañía", required=True, default=lambda self: self.env.company, readonly=True)
    currency_id = fields.Many2one('res.currency', string="Moneda", required=True, copy=True)
    date_start = fields.Date('Fecha Inicio', required=True, copy=True, default=fields.Date.today)
    date_end = fields.Date('Fecha Fin', copy=True)
    obs = fields.Text('Notas', copy=True)
    incidents = fields.Text('Incidencias', copy=False)
    order_mode = fields.Selection([
        ('sequence', 'Por secuencia'),
        ('code', 'Por códigos')],
         'Generar precedencias',
         required=True, default='sequence', copy=True)
    type = fields.Selection([
        ('budget', 'Presupuesto'),
        ('certification', 'Certificación'),
        ('execution', 'Ejecución'),
        ('target', 'Objetivo'),
        ('planning', 'Planificación'),
        ('entire', 'Completo'),
        ('nature', 'Naturalezas'),
        ('user', 'Usuario')],
        string='Tipo', default='budget', tracking=True, copy=True)
    state = fields.Selection([
        ('draft', 'Nuevo'),
        ('done', 'Presupuesto'),
        ('approved', 'Aprobado'),
        ('reject', 'Rechazado'),
        ('building', 'Construcción'),
        ('quality', 'Calidad'),
        ('delivery', 'Entregado'),
        ('cancel', 'Cancelado')],
        string='Estado', default='draft', copy=True, tracking=True)

    amount_total_equip = fields.Monetary('Total equipos', compute="_get_amount_total")
    amount_total_labor = fields.Monetary('Total mano de obra', compute="_get_amount_total")
    amount_total_material = fields.Monetary('Total material', compute="_get_amount_total")
    amount_total_other = fields.Monetary('Total otros', compute="_get_amount_total")

    amount_certified_equip = fields.Monetary('Certificado equipos',digits='BIM price', compute="_get_amount_total")
    amount_certified_labor = fields.Monetary('Certificado mano de obra',digits='BIM price', compute="_get_amount_total")
    amount_certified_material = fields.Monetary('Certificado material',digits='BIM price', compute="_get_amount_total")
    amount_certified_other = fields.Monetary('Certificado otros',digits='BIM price', compute="_get_amount_total")

    amount_executed_equip = fields.Monetary('Ejecutado equipos', compute="_compute_execute")
    amount_executed_labor = fields.Monetary('Ejecutado mano de obra', compute="_compute_execute")
    amount_executed_material = fields.Monetary('Ejecutado material', compute="_compute_execute")
    amount_executed_other = fields.Monetary('Ejecutado otros', compute="_compute_execute")

    product_rectify_ids = fields.One2many('bim.product.rectify', 'budget_id', 'Rectificaciones de productos')

    def print_budget_notes(self):
        return self.env.ref('base_bim_2.notes_report_budget').report_action(self)

    @api.onchange('project_id')
    def onchange_project_id(self):
        if self.project_id:
            self.currency_id = self.project_id.currency_id.id

    @api.onchange('template_id')
    def onchange_template_id(self):
        if self.template_id:
            self.asset_ids = [(5,)]
            self._create_assets(self.template_id)


    #@api.onchange('date_end','date_start')
    #def onchange_date(self):
        #project_date_start = self.project_id.date_ini
        #project_date_end = self.project_id.date_end

        #if self.date_start and self.date_end and self.date_end <= self.date_start:
        #    warning = {
        #        'title': _('Warning!'),
        #        'message': _(u'La fecha de finalizacion no puede ser menor o igual a la fecha de inicio del presupuesto!'),
        #    }
        #    self.date_end = False
        #    return {'warning': warning}

        #if self.date_end and project_date_end and self.date_end > project_date_end:
        #    warning = {
        #        'title': _('Warning!'),
        #        'message': _(u'La fecha de finalización no puede ser mayor a la fecha final de la Obra!'),
        #    }
        #    self.date_end = False
        #    return {'warning': warning}


        #if self.date_start and project_date_start and self.date_start < project_date_start:
        #    warning = {
        #        'title': _('Warning!'),
        #        'message': _(u'La fecha de inicio no puede ser menor a la fecha de inicio de la Obra!'),
        #    }
        #    self.date_start = False
        #    return {'warning': warning}

    def action_view_concepts(self):
        concepts = self.mapped('concept_ids')
        action = self.env.ref('base_bim_2.action_bim_concepts').read()[0]
        if concepts:
            action['domain'] = [('budget_id', '=', self.id)]#('parent_id', '=', False),
            action['context'] = {'default_budget_id': self.id}
        else:
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Nuevo Concepto',
                'res_model': 'bim.concepts',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current',
                'context': {'default_budget_id': self.id, 'default_type': 'chapter'}
            }
        action['context'].update({'budget_type': self.type})
        return action

    def action_view_stages(self):
        stages = self.mapped('stage_ids')
        action = self.env.ref('base_bim_2.action_bim_budget_stage').read()[0]
        if len(stages) > 0:
            action['domain'] = [('id', 'in', stages.ids),('budget_id', '=', self.id)]
            action['context'] = {'default_budget_id': self.id}
        else:
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Nueva Eatapa',
                'res_model': 'bim.budget.stage',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current',
                'context': {'default_budget_id': self.id}
            }
        return action

    def action_view_spaces(self):
        spaces = self.mapped('space_ids')
        action = self.env.ref('base_bim_2.action_bim_budget_space').read()[0]
        if len(spaces) > 0:
            action['domain'] = [('id', 'in', spaces.ids),('budget_id', '=', self.id)]
            action['context'] = {'default_budget_id': self.id}
        else:
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Nuevo',
                'res_model': 'bim.budget.space',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current',
                'context': {'default_budget_id': self.id}
            }
        return action

    def print_certification(self):
        return self.env.ref('base_bim_2.bim_budget_certification').report_action(self)

    def name_get(self):
        reads = self.read(['name', 'code'])
        res = []
        for record in reads:
            name = record['name']
            if record['code']:
                name = "[" + record['code'] + '] ' + name
            res.append((record['id'], name))
        return res

    def _create_assets(self,template):
        assets = []
        assets_obj = self.env['bim.budget.assets']
        for tmpl_line in template.line_ids:
            vals = {'budget_id':self.id,'asset_id':tmpl_line.asset_id.id,'value':tmpl_line.value,'sequence':tmpl_line.sequence}
            asset_line = assets_obj.create(vals)
            assets.append(asset_line.id)

            # Actualizamos los afectos
            if tmpl_line.affect_ids:
                af_ids = [af.asset_id.id for af in tmpl_line.affect_ids]
                line_ids =[l.id for l in self.asset_ids if l.asset_id.id in af_ids]
                asset_line.affect_ids = [(6,0,line_ids)]

        return True

    def compute_indicators(self):
        list_vals = ['M','Q','H','S']
        indicator_obj = self.env['bim.budget.indicator']
        for budget in self:
            if not budget.indicator_ids:
                for type in list_vals:
                    indicator_obj.create({'budget_id': budget.id,'type': type})

    def update_amount(self):
        for budget in self:
            last_level = budget.concept_ids.filtered(lambda r: r.type in ['labor','equip','material','aux'])

            for res in last_level:
                res.update_amount()

            for res in last_level:
                parent = res.parent_id
                while parent:
                    parent.update_amount()
                    if parent.parent_id:
                        parent = parent.parent_id
                    else:
                        parent = False

    def incident_review(self):
        for budget in self:
            incidents = []
            chapters = budget.concept_ids.filtered(lambda r: r.type in ['chapter'])
            resources = budget.concept_ids.filtered(lambda r: r.type in ['labor','equip','material'])
            for res in resources:
                if not res.product_id:
                    incidents.append(inconsistency['1']%res.display_name)
                if res.child_ids:
                    incidents.append(inconsistency['9']%res.display_name)
                if res.balance == 0:
                    incidents.append(inconsistency['7']%res.display_name)
                if res.type == 'labor' and res.product_id and res.product_id.resource_type != 'H':
                    incidents.append(inconsistency['4']%(res.product_id.display_name,res.display_name))
                if res.type == 'equip' and res.product_id and res.product_id.resource_type != 'Q':
                    incidents.append(inconsistency['3']%(res.product_id.display_name,res.display_name))
                if res.type == 'material' and res.product_id and res.product_id.resource_type != 'M':
                    incidents.append(inconsistency['2']%(res.product_id.display_name,res.display_name))
                if res.type == 'material' and res.product_id and res.product_id.type == 'service':
                    incidents.append(inconsistency['5']%(res.product_id.display_name,res.display_name))
                if res.type == 'labor' and res.product_id and res.product_id.type == 'product':
                    incidents.append(inconsistency['6']%(res.product_id.display_name,res.display_name))
                if res.uom_id and res.product_id and res.uom_id != res.product_id.uom_id:
                    incidents.append(inconsistency['10']%(res.display_name,res.product_id.display_name,res.parent_id.display_name))

            for cap in chapters:
                if cap.quantity > 1:
                    incidents.append(inconsistency['8']%(cap.display_name))

            if not incidents:
                incidents.append(inconsistency['0'])
            budget.incidents = '\n'.join(incidents)

    def create_stage(self, interval=1): #3 Trimestral, 2 Bimensual, 6 Semestral
        stage_obj = self.env['bim.budget.stage']
        for budget in self:
            bstart = budget.date_start
            bend = budget.date_end

            if not bend:
                raise UserError('Para la creación de las etapas debe ingresar una fecha final')
            if bend <= bstart:
                raise UserError('Para la creación de las etapas debe ingresar una fecha Fin superior a la fecha Inicio')

            stage = 1
            while bstart < bend:
                if interval == 15:
                    next_date = bstart + relativedelta(days=interval)
                    next_date = next_date - relativedelta(days=1)
                else:
                    next_date = bstart + relativedelta(months=interval, days=-1)

                if next_date > bend:
                    next_date = bend

                stage_obj.create({
                    'name': "Etapa %s"%str(stage),
                    'code': str(stage),#.zfill(3)
                    'date_start': bstart,
                    'date_stop':  next_date,
                    'budget_id': budget.id,
                    'state': 'process' if stage == 1 else 'draft',
                })
                stage += 1
                if interval == 15:
                    bstart = bstart + relativedelta(days=interval)
                else:
                    bstart = bstart + relativedelta(months=interval)
        return True

    def create_measures(self, measure_ids, concept):
        meobj = self.env['bim.concept.measuring']
        for record in measure_ids:
            data_me = record.copy_data()[0]
            data_me['space_id'] = False #vacios ya que se generan luego
            data_me['concept_id'] = concept.id
            meobj.create(data_me)

    def recursive_create(self, child_ids, budget, parent, cobj):
        for record in child_ids:
            data_rec = record.copy_data()[0]
            data_rec['budget_id'] = budget.id
            data_rec['parent_id'] = parent.id
            next_level = cobj.create(data_rec)
            if record.measuring_ids:
                self.create_measures(record.measuring_ids,next_level)
            if record.child_ids:
                self.recursive_create(record.child_ids, budget, next_level, cobj)

    def rectify_products(self):
        def get_origin_name(concept):
            if not concept.parent_id:
                return concept.display_name.replace(";", ".")
            return get_origin_name(concept.parent_id) + ' - ' + concept.display_name.replace(";", ".")

        if not self.env.user.has_group('base_bim_2.group_rectify_products'):
            raise ValidationError('No tienes permisos para rectificar productos.')

        types = dict(self.env['bim.concepts']._fields['type'].selection)
        products_by_code = {}
        product_obj = self.env['product.product']
        changes = []
        not_created = []
        not_changed = []
        for concept in self.concept_ids:
            if concept.type in ['chapter', 'departure']:
                continue
            if not concept.product_id or not concept.code:
                not_changed.append((get_origin_name(concept), types.get(concept.type, ''), concept.product_id.default_code or '', '', concept.uom_id.name or '', ''))
                continue
            if concept.code != concept.product_id.default_code:
                product = products_by_code.get(concept.code)
                if not product:
                    product = product_obj.search([('default_code', '=', concept.code)], limit=1)
                    if product:
                        products_by_code[concept.code] = product
                if product:
                    changes.append((get_origin_name(concept), types.get(concept.type, ''), concept.product_id.default_code or '', product.default_code or '', concept.uom_id.name or '', product.uom_id.name or ''))
                    concept.product_id = product
                else:
                    not_created.append(concept.display_name)
                    not_changed.append((get_origin_name(concept), types.get(concept.type, ''), concept.product_id.default_code or '', product.default_code or '', concept.uom_id.name or '', product.uom_id.name or ''))
        if not changes and not_created:
            raise ValidationError('No se rectificaron los siguientes conceptos por no existir el producto:\n%s' % '\n'.join(not_created))
        elif not changes:
            raise ValidationError('No hay productos para rectificar')

        workbook = xlwt.Workbook()
        head = xlwt.easyxf('align: wrap yes, horiz center; font: bold on;')
        head2 = xlwt.easyxf('align: wrap no; font: bold on;')
        sheet = workbook.add_sheet('Rectificaciones')
        # header
        sheet.write_merge(0, 0, 0, 5, f'Rectificaciones {self.display_name}', head)
        sheet.write(1, 0, 'Recurso', head2)
        sheet.write(1, 1, 'Concepto Presupuesto', head2)
        sheet.write(1, 2, 'Código que está en BIM', head2)
        sheet.write(1, 3, 'Código que se remplaza', head2)
        sheet.write(1, 4, 'Unidad en presupuesto', head2)
        sheet.write(1, 5, 'Unidad en producto', head2)
        for i, line in enumerate(changes, 2):
            for j, data in enumerate(line):
                sheet.write(i, j, data)
        for i, line in enumerate(not_changed, len(changes) + 2):
            for j, data in enumerate(line):
                sheet.write(i, j, data)

        stream = io.BytesIO()
        workbook.save(stream)
        stream.seek(0)

        now = fields.Datetime.now()
        self.product_rectify_ids.create({
            'budget_id': self.id,
            'csv_file': base64.b64encode(stream.getvalue()),
            'filename': f'Rectificaciones {now.strftime("%d-%m-%y %H:%M")} por {self.env.user.display_name}.xls',
        })
        return True

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        cobj = self.env['bim.concepts']
        sobj = self.env['bim.budget.space']
        default = dict(default or {})
        default.update(
            code = "New",
            name =_("%s (copy)") % (self.name or '')
        )
        new_copy = super(BimBudget, self).copy(default)

        #Carga de conceptos
        for cap in self.concept_ids.filtered(lambda b: not b.parent_id):
            data_cap = cap.copy_data()[0]
            data_cap['budget_id'] = new_copy.id
            new_cap = cobj.create(data_cap)
            if cap.child_ids:
                self.recursive_create(cap.child_ids,new_copy,new_cap,cobj)

        #Generacion de Haberes y descuentos
        new_copy._create_assets(new_copy.template_id)

        #Generacion de Indicadores
        if self.indicator_ids:
            new_copy.compute_indicators()

        #Generacion de Etapas
        if self.stage_ids:
            new_copy.create_stage()

        # completar espacios
        if self.space_ids:
            new_copy.space_ids = [(5,)]
            for space in self.space_ids:
                data_space = space.copy_data()[0]
                data_space['budget_id'] = new_copy.id
                sobj.create(data_space)

        # Asociar espacios en mediciones
        space_obj = self.env['bim.budget.space']
        departures = new_copy.concept_ids.filtered(lambda x:x.type == 'departure')
        for dep in departures:
            for m in dep.measuring_ids:
                if not m.space_id:
                    space = space_obj.search([('budget_id','=',new_copy.id),('name','=',m.name)],limit=1)
                    m.space_id = space and space.id or False

        return new_copy

    def unlink(self):
        for record in self:
            if record.type == 'certification':
                raise ValidationError('No puede borrar presupuestos en certificación.')
        self.concept_ids.filtered(lambda c: not c.parent_id).unlink()
        return super().unlink()


class BimBudgetStage(models.Model):
    _name = 'bim.budget.stage'
    _description = "Etapas de Presupuesto"
    _order = 'id asc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    def action_start(self):
        self.write({'state':'process'})
        return self.update_concept()

    def action_approve(self):
        self.write({'state':'approved'})
        pending = self.search([('state','=','draft'),('budget_id','=',self.budget_id.id)])
        list_date = [line.date_start for line in pending]
        min_date = list_date and min(list_date) or False
        if min_date:
            value = self.search([('state','=','draft'),('date_start','=',min_date),('budget_id','=',self.budget_id.id)])
            value.action_start()
        return self.update_concept()

    def action_cancel(self):
        self.write({'state':'cancel'})
        return self.update_concept()

    def action_draft(self):
        self.write({'state':'draft'})
        return self.update_concept()


    name = fields.Char("Nombre", size=100)
    code = fields.Char("Código")
    date_start = fields.Date('Fecha Inicio', copy=False)
    date_stop = fields.Date('Fecha Fin',required=True, copy=False)
    budget_id = fields.Many2one('bim.budget', "Presupuesto")
    state = fields.Selection([
        ('draft', 'Pendiente'),
        ('process', 'Actual'),
        ('approved', 'Aprobada'),
        ('cancel', 'Cancelada')],
        string='Estado', default='draft', copy=False, tracking=True)

    def update_concept(self):
        ''' Este metodo ACTUALIZA los conceptos que esten certificados
        (((Por Medicion o Por etapas))), ajustando los valores segun el
        cambio de state de la Etapa relacionada'''
        concepts = self.budget_id.concept_ids
        stage_concepts = concepts.filtered(lambda c: c.type_cert == 'stage')
        measure_concepts = concepts.filtered(lambda c: c.type_cert == 'measure')

        if stage_concepts:
            for concept in stage_concepts:
                concept._compute_stage()
                concept.onchange_stage()
                concept.onchange_qty_certification()

        if measure_concepts:
            for concept in measure_concepts:
                concept._compute_measure()
                concept.onchange_qty()
                concept.onchange_qty_certification()
        return True

class BimBudgetSpace(models.Model):
    _name = 'bim.budget.space'
    _description = "Espacios en Presupuesto"
    _order = 'id asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_code(self):
        budget_id = self._context.get('default_budget_id')
        budget = self.env['bim.budget'].browse(budget_id)
        return 'S'+str(len(budget.space_ids)+1)

    name = fields.Char("Nombre", size=100)
    code = fields.Char("Código",readonly=True,default=_get_code)
    budget_id = fields.Many2one('bim.budget', "Presupuesto")
    object_id = fields.Many2one('bim.object', "Objeto")
    project_id = fields.Many2one('bim.project', "Obra",related='budget_id.project_id')
    note = fields.Text('Resumen')
    purchase_req_ids = fields.One2many('bim.purchase.requisition', 'space_id', 'Solicitud de Materiales')
    purchase_req_count = fields.Integer('N° Solicitudes', compute="_compute_purchase_req_count")

    @api.depends('purchase_req_ids')
    def _compute_purchase_req_count(self):
        for space in self:
            space.purchase_req_count = len(space.purchase_req_ids)

    def action_view_purchase_requisition(self):
        purchases = self.mapped('purchase_req_ids')
        action = self.env.ref('base_bim_2.action_bim_purchase_requisition').read()[0]
        if len(purchases) > 0:
            action['domain'] = [('id', 'in', purchases.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def name_get(self):
        reads = self.read(['name', 'code'])
        res = []
        for record in reads:
            name = record['name']
            if record['code']:
                name = "[" + record['code'] + '] ' + name
            res.append((record['id'], name))
        return res

class BimBudgetAssets(models.Model):
    _name = 'bim.budget.assets'
    _description = 'Haber o descuento de presupuesto'
    _rec_name = 'asset_id'
    _order = 'sequence'

    sequence = fields.Integer('Secuencia')
    asset_id = fields.Many2one('bim.assets', "Haber o Descuento", ondelete='cascade')
    value = fields.Float('Valor')
    #affects_id = fields.Many2one('bim.budget.assets', "Haber o Descuento Afectado")
    budget_id = fields.Many2one('bim.budget', "Presupuesto", ondelete='cascade')
    total = fields.Float(compute='_compute_total')
    to_invoice = fields.Boolean('Facturar', default=True)
    affect_ids = fields.Many2many(
        string='Afecta a',
        comodel_name='bim.budget.assets',
        relation='budget_assets_afect_rel',
        column1='parent_id',
        column2='child_id',
    )

    @api.depends('value', 'asset_id', 'affect_ids')
    def _compute_total(self):
        amount = 0
        for record in self:
            budget = record.budget_id
            if record.asset_id.type == 'M':
                value = budget.amount_total_material
            elif record.asset_id.type == 'H':
                value = budget.amount_total_labor
            elif record.asset_id.type == 'Q':
                value = budget.amount_total_equip
            elif record.asset_id.type == 'S':
                value = budget.amount_total_other
            elif record.asset_id.type == 'T':
                value = budget.balance
            elif record.asset_id.type == 'N':
                value = amount
            else:
                value = 0.0

            if record.affect_ids:
                total_af = sum(af.total for af in record.affect_ids)
                value = total_af * (record.value / 100)
            if record.asset_id.type in ['O','T']:
                amount += value
            record.total = value


    # ~ @api.onchange('asset_id')
    # ~ def _onchange_asset(self):
        # ~ if self.date_end and project_date_end and self.date_end > project_date_end:
            # ~ warning = {
                # ~ 'title': _('Warning!'),
                # ~ 'message': _(u'La fecha de finalización no puede ser mayor a la fecha final de la Obra!'),
            # ~ }
            # ~ self.date_end = False
            # ~ return {'warning': warning}


class BimBudgetIndicator(models.Model):
    _description = "Indicadores comparativos"
    _name = 'bim.budget.indicator'

    @api.depends('amount_projected', 'amount_budget')
    def _compute_percent(self):
        for record in self:
            record.percent = record.amount_budget > 0.0 and (record.amount_projected / record.amount_budget) or 0.0


    budget_id = fields.Many2one('bim.budget', 'Presupuesto', ondelete="cascade")
    currency_id = fields.Many2one('res.currency', 'Moneda', related="budget_id.currency_id")
    amount_budget = fields.Monetary('Presupuesto', help="Valor Presupuestado", compute="_compute_total")
    amount_executed = fields.Monetary('Real Ejecutado', help="Salidas de Almacen + Partes", compute="_compute_total")
    amount_projected = fields.Monetary('Real Proyectado', help="Diferencia entre el Presupuestado y el Real ejecutado", compute="_compute_total")
    amount_certified = fields.Monetary('Certificado', help="Valor certificado", compute="_compute_total")
    amount_proj_cert = fields.Float('Certificado Proyectado', help="Diferencia entre el Presupuestado y el Certificado", compute="_compute_total")
    percent = fields.Float('Porcentaje', help="Porcentaje dado por el valor real entre valor estimado", compute="_compute_percent")
    type = fields.Selection(
        [('M', 'Costo Materiales'),
         ('Q', 'Costo Equipos'),
         ('H', 'Costo Mano de Obra'),
         ('S', 'Costo Otros') ],
        'Tipo Indicador', readonly=True)

    @api.depends('budget_id', 'type')
    def _compute_total(self):
        amount = 0
        for record in self:
            budget = record.budget_id
            if record.type == 'M':
                diff_proj_cert = budget.amount_total_material - budget.amount_certified_material
                record.amount_budget = budget.amount_total_material
                record.amount_certified = budget.amount_certified_material + diff_proj_cert if (diff_proj_cert > 0.0 and diff_proj_cert <=  1.0) else budget.amount_certified_material
                record.amount_proj_cert = 0.0 if (diff_proj_cert > 0.0 and diff_proj_cert <=  1.0) else diff_proj_cert
                record.amount_executed = budget.amount_executed_material
                record.amount_projected = budget.amount_total_material - budget.amount_executed_material
            elif record.type == 'H':
                diff_proj_cert = budget.amount_total_labor - budget.amount_certified_labor
                record.amount_budget = budget.amount_total_labor
                record.amount_certified = budget.amount_certified_labor + diff_proj_cert if (diff_proj_cert > 0.0 and diff_proj_cert <=  1.0) else budget.amount_certified_labor
                record.amount_proj_cert = 0.0 if (diff_proj_cert > 0.0 and diff_proj_cert <=  1.0) else diff_proj_cert
                record.amount_executed = budget.amount_executed_labor
                record.amount_projected = budget.amount_total_labor - budget.amount_executed_labor
            elif record.type == 'Q':
                diff_proj_cert = budget.amount_total_equip - budget.amount_certified_equip
                record.amount_budget = budget.amount_total_equip
                record.amount_certified = budget.amount_certified_equip + diff_proj_cert if (diff_proj_cert > 0.0 and diff_proj_cert <=  1.0) else budget.amount_certified_equip
                record.amount_proj_cert = 0.0 if (diff_proj_cert > 0.0 and diff_proj_cert <=  1.0) else diff_proj_cert
                record.amount_executed = budget.amount_executed_equip
                record.amount_projected = budget.amount_total_equip - budget.amount_executed_equip
            elif record.type == 'S':
                diff_proj_cert = budget.amount_total_other - budget.amount_certified_other
                record.amount_budget = budget.amount_total_other
                record.amount_certified = budget.amount_certified_other  + diff_proj_cert if (diff_proj_cert > 0.0 and diff_proj_cert <=  1.0) else budget.amount_certified_other
                record.amount_proj_cert = 0.0 if (diff_proj_cert > 0.0 and diff_proj_cert <=  1.0) else diff_proj_cert
                record.amount_executed = budget.amount_executed_other
                record.amount_projected = budget.amount_total_other - budget.amount_executed_other
            else:
                record.amount_budget = 0
                record.amount_certified = 0
                record.amount_proj_cert = 0
                record.amount_executed = 0
                record.amount_projected = 0


class BimProductRectify(models.Model):
    _name = 'bim.product.rectify'
    _description = 'Rectificación de productos en presupuesto'
    _order = 'id desc'
    _rec_name = 'filename'

    budget_id = fields.Many2one('bim.budget', 'Presupuesto', ondelete='cascade')
    user_id = fields.Many2one('res.users', 'Usuario', default=lambda self: self.env.user)
    date = fields.Datetime('Fecha', default=fields.Datetime.now)
    csv_file = fields.Binary('Archivo', required=True)
    filename = fields.Char('Nombre archivo')
