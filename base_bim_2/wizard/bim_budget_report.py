from odoo import models, fields, api
import xlwt
from io import BytesIO
import base64
from datetime import datetime

class BimBudgetReportWizard(models.TransientModel):
    _name = "bim.budget.report.wizard"
    _description = "Wizard Report Budget"

    @api.model
    def default_get(self, fields):
        res = super(BimBudgetReportWizard, self).default_get(fields)
        res['budget_id'] = self._context.get('active_id', False)
        return res

    display_type = fields.Selection([
        ('summary', 'Resumido'),
        ('detailed', 'Detallado'),
        ('full', 'Completo'),
        ('compare', 'Comparativo')
    ], string="Tipo de impresión", default='summary', help="Forma de agrupacion del Reporte.")

    summary_type = fields.Selection([
        ('chapter', 'Capítulos'),
        ('departure', 'Partidas'),
        ('resource', 'Recursos'),
    ], string="Nivel de impresión", default=False, help="Nivel de detalle del Reporte.")

    total_type = fields.Selection([
        ('asset', 'Haberes y descuentos'),
        ('normal','Totales Regulares'),
    ], string="Totalización", default='asset')

    filter_type = fields.Selection([
        ('space', 'Filtro por Espacios'),
        ('object','Filtro por Objetos'),
    ], string="Tipo de Filtro", default='space')

    budget_id = fields.Many2one('bim.budget', "Presupuesto", required=True)
    project_id = fields.Many2one('bim.project', "Obra", related='budget_id.project_id')
    text = fields.Boolean('Notas', default=True)
    measures = fields.Boolean('Medición', default=True)
    images = fields.Boolean('Imágenes', default=True)
    filter_ok = fields.Boolean('Agregar Filtro')
    space_ids = fields.Many2many('bim.budget.space', string='Espacios')
    object_ids = fields.Many2many('bim.object', string='Objetos de Obra')

    @api.onchange('display_type')
    def onchange_amount_type(self):
        if not self.summary_type:
            self.summary_type = 'chapter'

    @api.model
    def recursive_quantity(self, resource, parent, qty=None):
        qty = qty is None and resource.quantity or qty
        if parent.type == 'departure':
            qty_partial = qty * parent.quantity
            return self.recursive_quantity(resource,parent.parent_id,qty_partial)
        else:
            return qty * parent.quantity

    def recursive_amount(self, resource, parent, amount=None):
        amount = amount is None and resource.balance or amount or 0.0
        if parent.type == 'departure':
            amount_partial = amount * parent.quantity
            return self.recursive_amount(resource, parent.parent_id, amount_partial)
        else:
            return amount * parent.quantity

    def get_execute_aux(self, child_ids, amount):
        ''' Este metodo Retorna el Monto ejecutado
        de Funciones buscando recursivamente en Hijos'''
        amount_execute = 0
        for record in child_ids:
            if record.type == 'aux':
                amount = record.amount_execute
                amount_execute += amount
            if record.child_ids:
                return self.get_execute_aux(record.child_ids,amount_execute)
        return amount_execute

    def get_execute_childs(self, child_ids, amount):
        ''' Este metodo Retorna el Monto ejecutado
        de Funciones buscando recursivamente en Hijos'''
        amount_execute = amount
        con_obj = self.env['bim.concepts']
        for record in child_ids:
            if record.type == 'departure':
                for pick in record.picking_ids:
                    for move in pick.move_lines:
                        amount_execute += con_obj._get_value(move.product_uom_qty,move.product_id)
                for part in record.part_ids:
                    for line in part.lines_ids:
                        amount_execute += line.price_subtotal

            if record.child_ids:
                return self.get_execute_childs(record.child_ids,amount_execute)
        return amount_execute

    @api.model
    def get_filter_glosa(self):
        glosa = '-'
        list_val = []
        if self.filter_ok and self.filter_type == 'space':
            for space in self.space_ids:
                list_val.append(space.name)

        if self.filter_ok and self.filter_type == 'object':
            for obj in self.object_ids:
                list_val.append(obj.desc)
        if list_val:
            glosa = '-'.join(list_val)
        return glosa

    def get_execute_departure(self, concept):
        stock_obj = self.env['stock.picking']
        con_obj = self.env['bim.concepts']
        space_ids = self.space_ids.ids
        object_ids = self.object_ids.ids
        executed = 0
        aux_exe = 0
        products_exe = []

        if self.filter_type == 'space':
            parts_filter = concept.part_ids.filtered(lambda p: p.space_id.id in space_ids)
            picks_filter = concept.picking_ids.filtered(lambda p: p.bim_space_id.id in space_ids)

        elif self.filter_type == 'object':
            parts_filter = concept.part_ids.filtered(lambda p: p.space_id.object_id.id in object_ids)
            picks_filter = concept.picking_ids.filtered(lambda p: p.bim_object_id.id in object_ids)

        for pick in picks_filter:
            for move in pick.move_lines:
                products_exe.append(move.product_id.id)
                executed += con_obj._get_value(move.product_uom_qty,move.product_id)

        for part in parts_filter:
            for line in part.lines_ids:
                products_exe.append(line.name.id)
                executed += line.price_subtotal

        if any(rec.id for rec in concept.child_ids if rec.type == 'aux'):
            amount_execute = executed
            indicators = concept.equip_amount_count + concept.labor_amount_count + concept.material_amount_count
            aux_exe = (amount_execute / indicators) * concept.aux_amount_count

        if any(rec.id for rec in concept.child_ids if rec.type == 'departure'):
            executed += self.get_execute_childs(concept.child_ids,0)

        return executed + aux_exe

    @api.model
    def get_execute(self, concept):
        space_ids = self.space_ids.ids
        object_ids = self.object_ids.ids
        aux = 0
        execute_total = 0

        #FILTRO
        if self.filter_ok:
            if concept.type == 'chapter':
                for dep in concept.child_ids:
                    execute_total += self.get_execute_departure(dep)
            else:
                execute_total = self.get_execute_departure(concept)
        #TODOS
        else:
            products_exe = []
            if concept.type == 'chapter':
                aux = self.get_execute_aux(concept.child_ids,0)
                for dp in concept.child_ids:
                    execute_total += dp.amount_execute
                    if any(rec.id for rec in dp.child_ids if rec.type == 'departure'):
                        execute_total += self.get_execute_childs(dp.child_ids,0)
            else:
                aux = self.get_execute_aux(concept.child_ids,0)
                execute_total = concept.amount_execute_equip + concept.amount_execute_labor + concept.amount_execute_material
                if any(rec.id for rec in concept.child_ids if rec.type == 'departure'):
                    execute_total += self.get_execute_childs(concept.child_ids,0)

        return execute_total + aux

    @api.model
    def get_total(self, resource):
        budget = self.budget_id
        records = budget.concept_ids.filtered(lambda c: c.type == resource)
        total = 0

        for rec in records:
            total += self.recursive_amount(rec, rec.parent_id, None)
        return total

    @api.model
    def get_total_filter(self):
        space_ids = self.space_ids.ids
        object_ids = self.object_ids.ids
        budget = self.budget_id
        records = budget.concept_ids.filtered(lambda c: not c.parent_id and c.type == 'chapter')
        total_aux = total_eqp = total_lab = total_mat = 0

        for concept in records:
            lis = []
            dep_ids = self.get_departures(concept.child_ids,lis)
            dep_ids = set(dep_ids)
            for dep in self.env['bim.concepts'].browse(dep_ids):
                qty = 0
                for mea in dep.measuring_ids:
                    if self.filter_type == 'space':
                        if mea.space_id and mea.space_id.id in space_ids:
                            qty += mea.amount_subtotal

                    elif self.filter_type == 'object':
                        if mea.space_id and mea.space_id.object_id and mea.space_id.object_id.id in object_ids:
                            qty += mea.amount_subtotal

                total_aux += (dep.aux_amount_count * qty) / dep.quantity
                total_eqp += (dep.equip_amount_count * qty) / dep.quantity
                total_lab += (dep.labor_amount_count * qty) / dep.quantity
                total_mat += (dep.material_amount_count * qty) / dep.quantity
        return {'MO':total_lab,'MT':total_mat,'EQ':total_eqp,'AX':total_aux}

    @api.model
    def get_total_exe(self, chapter):
        records = chapter.concept_ids.filtered(lambda c: c.type not in resource)
        total = 0

        for rec in records:
            total += self.recursive_amount(rec, rec.parent_id, None)
        return total

    @api.model
    def get_quantity_filter(self, concept):
        """Filtro Para Reporte Detallado - Completo"""
        space_ids = self.space_ids.ids
        object_ids = self.object_ids.ids
        price = 0
        qty = 0

        if self.filter_ok:
            if concept.type == 'chapter':
                lis = []
                dep_ids = self.get_departures(concept.child_ids,lis)
                dep_ids = set(dep_ids)

                for dep in self.env['bim.concepts'].browse(dep_ids):
                    if dep.measuring_ids:
                        for mea in dep.measuring_ids:
                            if self.filter_type == 'space':
                                if mea.space_id and mea.space_id.id in space_ids:
                                    qty = 1.0
                                    price += mea.amount_subtotal * dep.amount_compute

                            if self.filter_type == 'object':
                                if mea.space_id and mea.space_id.object_id and mea.space_id.object_id.id in object_ids:
                                    qty = 1.0
                                    price += mea.amount_subtotal * dep.amount_compute


            elif concept.type == 'departure':
                if concept.measuring_ids:
                    price = concept.amount_compute
                    for mea in concept.measuring_ids:
                        if self.filter_type == 'space':
                            if mea.space_id.id in space_ids:
                                qty += mea.amount_subtotal
                        if self.filter_type == 'object':
                            if mea.space_id and mea.space_id.object_id and mea.space_id.object_id.id in object_ids:
                                qty += mea.amount_subtotal
                else:
                    qty = concept.quantity

                    for child in concept.child_ids:
                        qty_fil = 0
                        for mea in child.measuring_ids:
                            if self.filter_type == 'space':
                                if mea.space_id.id in space_ids:
                                    qty_fil += mea.amount_subtotal
                            if self.filter_type == 'object':
                                if mea.space_id and mea.space_id.object_id and mea.space_id.object_id.id in object_ids:
                                    qty_fil += mea.amount_subtotal
                        price += child.amount_compute * qty_fil

        return {'qty':qty,'price':price}


    @api.model
    def get_execute_filter(self, concept):
        """Filtro Para Reporte Comparativo (Ejecucion Real)"""
        space_ids = self.space_ids.ids
        object_ids = self.object_ids.ids
        qty = 0
        lis = []
        if self.filter_ok:
            if concept.type == 'chapter':
                dep_ids = self.get_departures(concept.child_ids,lis)
                dep_ids = set(dep_ids)
                for dep in self.env['bim.concepts'].browse(dep_ids):
                    # Revisamos las Partes
                    for part in dep.part_ids:
                        if self.filter_type == 'space':
                            if part.space_id and part.space_id.id in space_ids:
                                qty += 1
                        elif self.filter_type == 'object':
                            if part.space_id and part.space_id.object_id and part.space_id.object_id.id in object_ids:
                                qty += 1

                    # Revisamos los Picking
                    for pick in dep.picking_ids:
                        if self.filter_type == 'space':
                            if pick.bim_space_id and pick.bim_space_id.id in space_ids:
                                qty += 1
                        elif self.filter_type == 'object':
                            if pick.bim_object_id and pick.bim_object_id.id in object_ids:
                                qty += 1

            elif concept.type == 'departure':
                # Revisamos las Partes
                for part in concept.part_ids:
                    if self.filter_type == 'space':
                        if part.space_id and part.space_id.id in space_ids:
                            qty += 1
                    elif self.filter_type == 'object':
                        if part.space_id and part.space_id.object_id and part.space_id.object_id.id in object_ids:
                            qty += 1

                # Revisamos los Picking
                for pick in concept.picking_ids:
                    if self.filter_type == 'space':
                        if pick.bim_space_id and pick.bim_space_id.id in space_ids:
                            qty += 1
                    elif self.filter_type == 'object':
                        if pick.bim_object_id and pick.bim_object_id.id in object_ids:
                            qty += 1
        return qty


   # Retorna partidas contenidos en el concepto
    def get_departures(self, child_ids, dep_ids):
        res = dep_ids
        for record in child_ids:
            if record.type in ['departure']:
                res.append(record.id)
            if record.child_ids:
                self.get_departures(record.child_ids,res)
        return res


    # ~ def get_departures(self, child_ids):
        # ~ res = []
        # ~ childs = child_ids
        # ~ while childs:
            # ~ for record in childs:
                # ~ if record.type in ['departure']:
                    # ~ res.append(record.id)
                # ~ if record.child_ids:
                    # ~ childs = record.child_ids
                # ~ else:
                    # ~ childs = False
        # ~ return res

   # Retorna Recursos contenidos en el concepto
    def get_resources(self, child_ids):
        res = []
        for record in child_ids:
            if record.product_id and record.type in ['material']:
                res.append(record.product_id.id)
            if record.child_ids:
                self.get_resources(record.child_ids)
        return res

    def check_report(self):
        self.ensure_one()
        data = {}
        data['id'] = self._context.get('active_id', [])
        data['docs'] = self._context.get('active_ids', [])
        data['model'] = self._context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read([])[0]
        return self._print_report(data)

    def _print_report(self, data):
        if self.display_type == 'summary':
            action = self.env.ref('base_bim_2.bim_budget_summary').report_action(self)
        elif self.display_type == 'full':
            action = self.env.ref('base_bim_2.bim_budget_full').report_action(self)
        elif self.display_type == 'compare':
            action = self.env.ref('base_bim_2.bim_budget_real_execute').report_action(self)
        else:
            action = self.env.ref('base_bim_2.bim_budget').report_action(self)
        action.update({'close_on_report_download': True})
        return action

    def check_report_xls(self):
        budget = self.budget_id
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet('Presupuesto')
        file_name = 'Presupuesto'
        style_title = xlwt.easyxf('font: name Times New Roman 180, color-index black, bold on; align: wrap yes, horiz center;pattern: pattern solid, pattern_fore_colour gray50;')
        style_filter_title = xlwt.easyxf('font: color-index black, bold on; align: wrap yes, horiz center;pattern: pattern solid, pattern_fore_colour gray25;')
        style_filter_title2 = xlwt.easyxf('align: wrap yes, horiz center;pattern: pattern solid, pattern_fore_colour gray25;')
        style_summary = xlwt.easyxf('borders: left thin, right thin, top thin, bottom thin;')
        style_border_table_top = xlwt.easyxf('borders: left thin, right thin, top thin, bottom thin; font: bold on;pattern: pattern solid, pattern_fore_colour gray40;')
        style_border_table_bottom = xlwt.easyxf('borders: left thin, right thin, top thin, bottom thin; font: bold on;pattern: pattern solid, pattern_fore_colour light_turquoise;')
        style_border_table_details_chapters = xlwt.easyxf('borders: bottom thin; pattern: pattern solid, pattern_fore_colour bright_green;')
        style_border_table_details_departed = xlwt.easyxf('borders: bottom thin; pattern: pattern solid, pattern_fore_colour light_orange;')
        style_border_table_details = xlwt.easyxf('borders: bottom thin;')

        if self.display_type == 'summary':
            worksheet.write_merge(0, 0, 0, 11, "REPORTE DE PRESUPUESTO RESUMIDO", style_title)
            worksheet.write_merge(1,1,0,2, "Obra",style_filter_title)
            worksheet.write_merge(1,1,3,5, budget.project_id.nombre,style_filter_title2)
            worksheet.write_merge(2,2,0,2, budget.name,style_filter_title)
            worksheet.write_merge(2,2,3,3, budget.code,style_filter_title2)
            worksheet.write_merge(3,3,0,2, "Fecha de Impresión",style_filter_title)
            worksheet.write_merge(3,3,3,3, datetime.now().strftime('%d-%m-%Y'),style_filter_title2)

            if self.total_type == 'normal':
                worksheet.write_merge(5,6,0,3, "Total Materiales", style_summary)
                worksheet.write_merge(7,8,0,3, "Total Mano de Obra", style_summary)
                worksheet.write_merge(9,10,0,3, "Total Equipos", style_summary)
                worksheet.write_merge(11,12,0,3, "Otros", style_summary)
                worksheet.write_merge(13,14,0,3, "TOTAL", style_summary)

                mt = round(self.get_total('material'),2)
                mo = round(self.get_total('labor'),2)
                eq = round(self.get_total('equip'),2)
                tot = mt + mo + eq
                others = round((budget.balance - tot),2)
                total = round(budget.balance,2)

                worksheet.write_merge(5,6,4,5, mt, style_summary)
                worksheet.write_merge(7,8,4,5, mo, style_summary)
                worksheet.write_merge(9,10,4,5, eq, style_summary)
                worksheet.write_merge(11,12,4,5, others, style_summary)
                worksheet.write_merge(13,14,4,5, total, style_summary)
            else:
                row = 5
                for asset in budget.asset_ids:
                    if asset.asset_id.show_on_report:
                        worksheet.write_merge(row,row,0,3, asset.asset_id.desc, style_summary)
                        worksheet.write_merge(row,row,4,5, asset.total, style_summary)
                        row += 1

        elif self.display_type == 'compare':
            worksheet.write_merge(0, 0, 0, 11, "REPORTE EJECUCIÓN REAL", style_title)
            worksheet.write_merge(1,1,0,2, "Obra",style_filter_title)
            worksheet.write_merge(1,1,3,5, budget.name,style_filter_title)
            worksheet.write_merge(1,1,6,8, "Fecha de Impresión",style_filter_title)
            if self.filter_ok:
                worksheet.write_merge(1,1,9,11, "Filtro Agregado",style_filter_title)
            worksheet.write_merge(2,2,0,2, budget.project_id.nombre,style_filter_title2)
            worksheet.write_merge(2,2,3,5, budget.code,style_filter_title2)
            worksheet.write_merge(2,2,6,8, datetime.now().strftime('%d-%m-%Y'),style_filter_title2)
            if self.filter_ok:
                worksheet.write_merge(2,2,9,11, self.get_filter_glosa(),style_filter_title2)

            # Header table

            worksheet.write_merge(4,4,8,9, "PRESUPUESTO", style_border_table_top)
            worksheet.write_merge(4,4,10,11, "REAL EJECUTADO", style_border_table_top)
            worksheet.write_merge(5,5,0,1, "CÓDIGO", style_border_table_top)
            worksheet.write_merge(5,5,2,7, "CONCEPTO", style_border_table_top)
            worksheet.write_merge(5,5,8,8, "CANTIDAD", style_border_table_top)
            worksheet.write_merge(5,5,9,9, "PRESUPUESTO", style_border_table_top)
            worksheet.write_merge(5,5,10,10, "CANTIDAD", style_border_table_top)
            worksheet.write_merge(5,5,11,11, "REAL", style_border_table_top)
            chapters = budget.concept_ids.filtered(lambda c: not c.parent_id)
            row = 6
            total = 0
            for chapter in chapters:
                if self.filter_ok:
                    if self.get_execute_filter(chapter) > 0:
                        worksheet.write_merge(row,row,0,1, chapter.code, style_border_table_details_chapters)
                        worksheet.write_merge(row,row,2,7, chapter.name, style_border_table_details_chapters)
                        worksheet.write_merge(row,row,8,8, "-", style_border_table_details_chapters)
                        worksheet.write_merge(row,row,9,9, chapter.balance, style_border_table_details_chapters)
                        worksheet.write_merge(row,row,10,10, "-", style_border_table_details_chapters)
                        worksheet.write_merge(row,row,11,11, round(self.get_execute(chapter),2), style_border_table_details_chapters)
                        row += 1

                        for child in chapter.child_ids:
                            if self.get_execute_filter(child) > 0:
                                worksheet.write_merge(row,row,0,1, child.code, style_border_table_details_departed)
                                worksheet.write_merge(row,row,2,7, child.name, style_border_table_details_departed)
                                worksheet.write_merge(row,row,8,8, child.quantity, style_border_table_details_departed)
                                worksheet.write_merge(row,row,9,9, child.balance, style_border_table_details_departed)
                                worksheet.write_merge(row,row,10,10, "-", style_border_table_details_departed)
                                worksheet.write_merge(row,row,11,11, round(self.get_execute(child),2), style_border_table_details_departed)
                                row += 1
                else:
                    worksheet.write_merge(row,row,0,1, chapter.code, style_border_table_details_chapters)
                    worksheet.write_merge(row,row,2,7, chapter.name, style_border_table_details_chapters)
                    worksheet.write_merge(row,row,8,8, "-", style_border_table_details_chapters)
                    worksheet.write_merge(row,row,9,9, chapter.balance, style_border_table_details_chapters)
                    worksheet.write_merge(row,row,10,10, "-", style_border_table_details_chapters)
                    worksheet.write_merge(row,row,11,11, round(self.get_execute(chapter),2), style_border_table_details_chapters)
                    row += 1

                    for child in chapter.child_ids:
                        worksheet.write_merge(row,row,0,1, child.code, style_border_table_details_departed)
                        worksheet.write_merge(row,row,2,7, child.name, style_border_table_details_departed)
                        worksheet.write_merge(row,row,8,8, child.quantity, style_border_table_details_departed)
                        worksheet.write_merge(row,row,9,9, child.balance, style_border_table_details_departed)
                        worksheet.write_merge(row,row,10,10, "-", style_border_table_details_departed)
                        worksheet.write_merge(row,row,11,11, round(self.get_execute(child),2), style_border_table_details_departed)
                        row += 1


        else:# (DETALLADO - COMPLETO)
            worksheet.write_merge(0, 0, 0, 11, "REPORTE DE PRESUPUESTO", style_title)
            worksheet.write_merge(1,1,0,2, "Obra",style_filter_title)
            worksheet.write_merge(1,1,3,5, budget.name,style_filter_title)
            worksheet.write_merge(1,1,6,8, "Fecha de Impresión",style_filter_title)
            if self.filter_ok:
                worksheet.write_merge(1,1,9,11, "Filtro Agregado",style_filter_title)
            worksheet.write_merge(2,2,0,2, budget.project_id.nombre,style_filter_title2)
            worksheet.write_merge(2,2,3,5, budget.code,style_filter_title2)
            worksheet.write_merge(2,2,6,8, datetime.now().strftime('%d-%m-%Y'),style_filter_title2)
            if self.filter_ok:
                worksheet.write_merge(2,2,9,11, self.get_filter_glosa(),style_filter_title2)
            # Header table
            worksheet.write_merge(4,4,0,1, "Código", style_border_table_top)
            worksheet.write_merge(4,4,2,7, "Criterio", style_border_table_top)
            worksheet.write_merge(4,4,8,8, "Unidad", style_border_table_top)
            worksheet.write_merge(4,4,9,9, "Cantidad", style_border_table_top)
            worksheet.write_merge(4,4,10,10, "Precio", style_border_table_top)
            worksheet.write_merge(4,4,11,11, "Importe", style_border_table_top)
            parents = budget.concept_ids.filtered(lambda c: not c.parent_id)
            row = 5
            for parent in parents:
                if self.filter_ok:
                    filter_val = self.get_quantity_filter(parent)
                    if filter_val['qty'] > 0:
                        worksheet.write_merge(row,row,0,1, parent.code, style_border_table_details_chapters)
                        worksheet.write_merge(row,row,2,7, parent.name, style_border_table_details_chapters)
                        worksheet.write_merge(row,row,8,8, parent.uom_id and parent.uom_id.name or '', style_border_table_details_chapters)
                        worksheet.write_merge(row,row,9,9, parent.quantity, style_border_table_details_chapters)
                        worksheet.write_merge(row,row,10,10, filter_val['price'], style_border_table_details_chapters)
                        worksheet.write_merge(row,row,11,11, filter_val['price'], style_border_table_details_chapters)
                        row += 1
                        if self.text and parent.note and self.display_type == 'full':
                            worksheet.write_merge(row,row,0,11, parent.note, style_border_table_details)
                            row += 1
                        if self.summary_type in ['departure','resource']:
                            for child in parent.child_ids:
                                filter_child = self.get_quantity_filter(child)
                                style_child = child.type == 'departure' and style_border_table_details_departed or style_border_table_details_chapters

                                if filter_child['qty'] > 0:
                                    worksheet.write_merge(row,row,0,1, child.code, style_child)
                                    worksheet.write_merge(row,row,2,7, child.name, style_child)
                                    worksheet.write_merge(row,row,8,8, child.uom_id and child.uom_id.name or '', style_child)
                                    worksheet.write_merge(row,row,9,9, filter_child['qty'], style_child)
                                    worksheet.write_merge(row,row,10,10, filter_child['price'], style_child)
                                    worksheet.write_merge(row,row,11,11, filter_child['qty'] * filter_child['price'], style_child)
                                    row += 1

                                    # EXTRA: Si hay un hijo partida o capitulo
                                    if any(ext.type in ['departure','chapter'] for ext in child.child_ids) and self.summary_type in ['departure']:
                                        for extra in child.child_ids:
                                            filter_ext = self.get_quantity_filter(extra)
                                            style_ext = extra.type == 'departure' and style_border_table_details_departed or style_border_table_details_chapters
                                            if filter_ext['qty'] > 0:
                                                worksheet.write_merge(row,row,0,1, extra.code, style_ext)
                                                worksheet.write_merge(row,row,2,7, extra.name, style_ext)
                                                worksheet.write_merge(row,row,8,8, extra.uom_id and extra.uom_id.name or '', style_ext)
                                                worksheet.write_merge(row,row,9,9, filter_ext['qty'], style_ext)
                                                worksheet.write_merge(row,row,10,10, filter_ext['price'], style_ext)
                                                worksheet.write_merge(row,row,11,11, filter_ext['price']*filter_ext['qty'], style_ext)
                                                row += 1
                                                if self.measures and extra.measuring_ids and self.display_type == 'full':
                                                    worksheet.write_merge(row,row,1,1, "Grupo", style_border_table_bottom)
                                                    worksheet.write_merge(row,row,2,4, "Descripción", style_border_table_bottom)
                                                    worksheet.write_merge(row,row,5,5, "Cant(N)", style_border_table_bottom)
                                                    worksheet.write_merge(row,row,6,6, "Largo(X)", style_border_table_bottom)
                                                    worksheet.write_merge(row,row,7,7, "Ancho(Y)", style_border_table_bottom)
                                                    worksheet.write_merge(row,row,8,8, "Alto(Z)", style_border_table_bottom)
                                                    worksheet.write_merge(row,row,9,9, "Fórmula", style_border_table_bottom)
                                                    worksheet.write_merge(row,row,10,10, "Subtotal", style_border_table_bottom)
                                                    row += 1

                                                    if self.filter_type == 'space':
                                                        measures_filter = extra.measuring_ids.filtered(lambda m: m.space_id.id in self.space_ids.ids)
                                                    else:
                                                        measures_filter = extra.measuring_ids.filtered(lambda m: m.space_id.object_id.id in self.object_ids.ids)

                                                    for msr in measures_filter:
                                                        worksheet.write_merge(row,row,1,1, msr.space_id.display_name or '', style_border_table_details)
                                                        worksheet.write_merge(row,row,2,4, msr.name or '', style_border_table_details)
                                                        worksheet.write_merge(row,row,5,5, msr.qty, style_border_table_details)
                                                        worksheet.write_merge(row,row,6,6, msr.length, style_border_table_details)
                                                        worksheet.write_merge(row,row,7,7, msr.width, style_border_table_details)
                                                        worksheet.write_merge(row,row,8,8, msr.height, style_border_table_details)
                                                        worksheet.write_merge(row,row,9,9, msr.formula.name or '', style_border_table_details)
                                                        worksheet.write_merge(row,row,10,10, msr.amount_subtotal, style_border_table_details)
                                                        row += 1


                                    if self.text and child.note and self.display_type == 'full':
                                        worksheet.write_merge(row,row,0,11, child.note, style_border_table_details)
                                        row += 1
                                    if self.measures and child.measuring_ids and self.display_type == 'full':
                                        worksheet.write_merge(row,row,1,1, "Grupo", style_border_table_bottom)
                                        worksheet.write_merge(row,row,2,4, "Descripción", style_border_table_bottom)
                                        worksheet.write_merge(row,row,5,5, "Cant(N)", style_border_table_bottom)
                                        worksheet.write_merge(row,row,6,6, "Largo(X)", style_border_table_bottom)
                                        worksheet.write_merge(row,row,7,7, "Ancho(Y)", style_border_table_bottom)
                                        worksheet.write_merge(row,row,8,8, "Alto(Z)", style_border_table_bottom)
                                        worksheet.write_merge(row,row,9,9, "Fórmula", style_border_table_bottom)
                                        worksheet.write_merge(row,row,10,10, "Subtotal", style_border_table_bottom)
                                        row += 1

                                        if self.filter_type == 'space':
                                            measures_filter = child.measuring_ids.filtered(lambda m: m.space_id.id in self.space_ids.ids)
                                        else:
                                            measures_filter = child.measuring_ids.filtered(lambda m: m.space_id.object_id.id in self.object_ids.ids)

                                        for msr in measures_filter:
                                            worksheet.write_merge(row,row,1,1, msr.space_id.display_name or '', style_border_table_details)
                                            worksheet.write_merge(row,row,2,4, msr.name or '', style_border_table_details)
                                            worksheet.write_merge(row,row,5,5, msr.qty, style_border_table_details)
                                            worksheet.write_merge(row,row,6,6, msr.length, style_border_table_details)
                                            worksheet.write_merge(row,row,7,7, msr.width, style_border_table_details)
                                            worksheet.write_merge(row,row,8,8, msr.height, style_border_table_details)
                                            worksheet.write_merge(row,row,9,9, msr.formula.name or '', style_border_table_details)
                                            worksheet.write_merge(row,row,10,10, msr.amount_subtotal, style_border_table_details)
                                            row += 1
                                    if child.child_ids and self.summary_type in ['resource']:
                                        for resource in child.child_ids:
                                            worksheet.write_merge(row,row,0,1, resource.code, style_border_table_details)
                                            worksheet.write_merge(row,row,2,7, resource.name, style_border_table_details)
                                            worksheet.write_merge(row,row,8,8, resource.uom_id and resource.uom_id.name or '', style_border_table_details)
                                            worksheet.write_merge(row,row,9,9, resource.quantity, style_border_table_details)
                                            worksheet.write_merge(row,row,10,10, resource.amount_compute, style_border_table_details)
                                            worksheet.write_merge(row,row,11,11, resource.balance, style_border_table_details)
                                            row += 1
                                            if self.text and resource.note and self.display_type == 'full':
                                                worksheet.write_merge(row,row,0,11, resource.note, style_border_table_details)
                                                row += 1
                # (DETALLADO - COMPLETO SIN FILTRO)
                else:
                    worksheet.write_merge(row,row,0,1, parent.code, style_border_table_details_chapters)
                    worksheet.write_merge(row,row,2,7, parent.name, style_border_table_details_chapters)
                    worksheet.write_merge(row,row,8,8, parent.uom_id and parent.uom_id.name or '', style_border_table_details_chapters)
                    worksheet.write_merge(row,row,9,9, parent.quantity, style_border_table_details_chapters)
                    worksheet.write_merge(row,row,10,10, parent.amount_compute, style_border_table_details_chapters)
                    worksheet.write_merge(row,row,11,11, parent.balance, style_border_table_details_chapters)
                    row += 1
                    if self.text and parent.note and self.display_type == 'full':
                        worksheet.write_merge(row,row,0,11, parent.note, style_border_table_details)
                        row += 1
                    if self.summary_type in ['departure','resource']:
                        for child in parent.child_ids:
                            if child.type == 'departure':
                                worksheet.write_merge(row,row,0,1, child.code, style_border_table_details_departed)
                                worksheet.write_merge(row,row,2,7, child.name, style_border_table_details_departed)
                                worksheet.write_merge(row,row,8,8, child.uom_id and child.uom_id.name or '', style_border_table_details_departed)
                                worksheet.write_merge(row,row,9,9, child.quantity, style_border_table_details_departed)
                                worksheet.write_merge(row,row,10,10, child.amount_compute, style_border_table_details_departed)
                                worksheet.write_merge(row,row,11,11, child.balance, style_border_table_details_departed)
                                row += 1
                            else:
                                worksheet.write_merge(row,row,0,1, child.code, style_border_table_details)
                                worksheet.write_merge(row,row,2,7, child.name, style_border_table_details)
                                worksheet.write_merge(row,row,8,8, child.uom_id and child.uom_id.name or '', style_border_table_details)
                                worksheet.write_merge(row,row,9,9, child.quantity, style_border_table_details)
                                worksheet.write_merge(row,row,10,10, child.amount_compute, style_border_table_details)
                                worksheet.write_merge(row,row,11,11, child.balance, style_border_table_details)
                                row += 1
                            if self.text and child.note and self.display_type == 'full':
                                worksheet.write_merge(row,row,0,11, child.note, style_border_table_details)
                                row += 1
                            if self.measures and child.measuring_ids and self.display_type == 'full':
                                worksheet.write_merge(row,row,1,1, "Grupo", style_border_table_bottom)
                                worksheet.write_merge(row,row,2,4, "Descripción", style_border_table_bottom)
                                worksheet.write_merge(row,row,5,5, "Cant(N)", style_border_table_bottom)
                                worksheet.write_merge(row,row,6,6, "Largo(X)", style_border_table_bottom)
                                worksheet.write_merge(row,row,7,7, "Ancho(Y)", style_border_table_bottom)
                                worksheet.write_merge(row,row,8,8, "Alto(Z)", style_border_table_bottom)
                                worksheet.write_merge(row,row,9,9, "Fórmula", style_border_table_bottom)
                                worksheet.write_merge(row,row,10,10, "Subtotal", style_border_table_bottom)
                                row += 1
                                for msr in child.measuring_ids:
                                    worksheet.write_merge(row,row,1,1, msr.space_id.display_name or '', style_border_table_details)
                                    worksheet.write_merge(row,row,2,4, msr.name or '', style_border_table_details)
                                    worksheet.write_merge(row,row,5,5, msr.qty, style_border_table_details)
                                    worksheet.write_merge(row,row,6,6, msr.length, style_border_table_details)
                                    worksheet.write_merge(row,row,7,7, msr.width, style_border_table_details)
                                    worksheet.write_merge(row,row,8,8, msr.height, style_border_table_details)
                                    worksheet.write_merge(row,row,9,9, msr.formula.name or '', style_border_table_details)
                                    worksheet.write_merge(row,row,10,10, msr.amount_subtotal, style_border_table_details)
                                    row += 1
                            if child.child_ids and self.summary_type in ['resource']:
                                for resource in child.child_ids:
                                    worksheet.write_merge(row,row,0,1, resource.code, style_border_table_details)
                                    worksheet.write_merge(row,row,2,7, resource.name, style_border_table_details)
                                    worksheet.write_merge(row,row,8,8, resource.uom_id and resource.uom_id.name or '', style_border_table_details)
                                    worksheet.write_merge(row,row,9,9, resource.quantity, style_border_table_details)
                                    worksheet.write_merge(row,row,10,10, resource.amount_compute, style_border_table_details)
                                    worksheet.write_merge(row,row,11,11, resource.balance, style_border_table_details)
                                    row += 1
                                    if self.text and resource.note and self.display_type == 'full':
                                        worksheet.write_merge(row,row,0,11, resource.note, style_border_table_details)
                                        row += 1
            # TOTALES (CON FILTRO)
            if self.filter_ok:
                total_filter = self.get_total_filter()
                if total_filter['MT'] > 0:
                    worksheet.write_merge(row,row,8,10, "Total Materiales", style_summary)
                    worksheet.write_merge(row,row,11,11, total_filter['MT'], style_summary)
                    row += 1
                if total_filter['MO'] > 0:
                    worksheet.write_merge(row,row,8,10, "Total Mano de Obra", style_summary)
                    worksheet.write_merge(row,row,11,11, total_filter['MO'], style_summary)
                    row += 1
                if total_filter['EQ'] > 0:
                    worksheet.write_merge(row,row,8,10, "Total Equipos", style_summary)
                    worksheet.write_merge(row,row,11,11, total_filter['EQ'], style_summary)
                    row += 1
                if total_filter['AX'] > 0:
                    worksheet.write_merge(row,row,8,10, "Otros", style_summary)
                    worksheet.write_merge(row,row,11,11, total_filter['AX'], style_summary)
                    row += 1
                worksheet.write_merge(row,row,8,10, "TOTAL", style_summary)
                worksheet.write_merge(row,row,11,11, total_filter['MT']+total_filter['MO']+total_filter['EQ']+total_filter['AX'], style_summary)

            # TOTALES (SIN FILTRO)
            else:
                if self.total_type == 'normal':
                    mt = round(self.get_total('material'),2)
                    mo = round(self.get_total('labor'),2)
                    eq = round(self.get_total('equip'),2)
                    tot = mt + mo + eq
                    others = round((budget.balance - tot),2)
                    total = round(budget.balance,2)
                    if mt > 0:
                        worksheet.write_merge(row,row,8,10, "Total Materiales", style_summary)
                        worksheet.write_merge(row,row,11,11, mt, style_summary)
                        row += 1
                    if mo > 0:
                        worksheet.write_merge(row,row,8,10, "Total Mano de Obra", style_summary)
                        worksheet.write_merge(row,row,11,11, mo, style_summary)
                        row += 1
                    if eq > 0:
                        worksheet.write_merge(row,row,8,10, "Total Equipos", style_summary)
                        worksheet.write_merge(row,row,11,11, eq, style_summary)
                        row += 1
                    if others > 0:
                        worksheet.write_merge(row,row,8,10, "Otros", style_summary)
                        worksheet.write_merge(row,row,11,11, others, style_summary)
                        row += 1
                    worksheet.write_merge(row,row,8,10, "TOTAL", style_summary)
                    worksheet.write_merge(row,row,11,11, total, style_summary)
                else:
                    for asset in budget.asset_ids:
                        if asset.asset_id.show_on_report:
                            worksheet.write_merge(row,row,8,10, asset.asset_id.desc, style_summary)
                            worksheet.write_merge(row,row,11,11, asset.total, style_summary)
                            row += 1

        fp = BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        data_b64 = base64.encodestring(data)
        doc = self.env['ir.attachment'].create({
            'name': '%s.xls' % (file_name),
            'datas': data_b64,
        })

        return {
            'type': "ir.actions.act_url",
            'url': "web/content/?model=ir.attachment&id=" + str(
                doc.id) + "&filename_field=name&field=datas&download=true&filename=" + str(doc.name),
            'target': "self",
            'no_destroy': False,
        }
