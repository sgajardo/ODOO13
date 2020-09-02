# -*- coding: utf-8 -*-
import base64
import xlwt
import re
import io
import tempfile
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from xlwt import easyxf, Workbook
from datetime import datetime
from io import StringIO

class BimstockReportWizard(models.TransientModel):
    _name = "bim.stock.report.wizard"
    _description = "Wizard Report Budget Stock"

    @api.model
    def default_get(self, fields):
        res = super(BimstockReportWizard, self).default_get(fields)
        res['project_id'] = self._context.get('active_id', False)
        return res

    material = fields.Boolean(string="Materiales",default=True)
    equipment = fields.Boolean(string="Equipos",default=True)
    labor = fields.Boolean(string="Mano de Obra",default=True)
    resource_all = fields.Boolean(default=True,string="TODOS")
    date_beg = fields.Date('Fecha desde', default=fields.Date.today)
    date_end = fields.Date('Fecha hasta')
    project_id = fields.Many2one('bim.project', "Presupuesto", required=True)
    doc_type = fields.Selection([('csv', 'CSV'), ('xls', 'Excel')], string='Formato', default='xls')
    display_type = fields.Selection([
        ('summary', 'Resumido'),
        ('detailed', 'Detallado'),
        ('range', 'Rango de Fecha')
        ], string="Tipo de impresión", default='summary',
        help="Forma de agrupacion del Reporte.")

    @api.onchange('equipment', 'material', 'labor')
    def onchange_resource(self):
        self.resource_all = True if (self.equipment and self.material and self.labor) else False

    @api.onchange('resource_all')
    def onchange_resource_all(self):
        if not self.resource_all and (self.equipment and self.material and self.labor):
            self.equipment = self.material = self.labor = False
        elif self.resource_all:
            self.equipment = self.material = self.labor = True

    def get_space_quantity(self, concept, space):
        qty_space = 0
        if not concept.measuring_ids and concept.parent_id.type == 'departure':
            return self.get_space_quantity(concept.parent_id,space)
        qty_space = sum(m.amount_subtotal for m in concept.measuring_ids if m.space_id and m.space_id.id == space.id)
        return qty_space

    def recursive_quantity_space(self, resource, space, qty_space, qty=None):
        parent = resource.parent_id
        qty = qty is None and resource.quantity or qty

        if parent.type == 'departure':
            if not parent.measuring_ids:
                qty_partial = qty * parent.quantity
            else:
                qty_partial = qty
            return self.recursive_quantity_space(parent,space,qty_space,qty_partial)
        else:
            return qty * qty_space

    def recursive_quantity(self, resource, parent, qty=None):
        qty = qty is None and resource.quantity or qty
        if parent.type == 'departure':
            qty_partial = qty * parent.quantity
            return self.recursive_quantity(resource,parent.parent_id,qty_partial)
        else:
            return qty * parent.quantity

    def get_quantity(self,resource,concept,space):
        total_qty = 0
        if concept:
            records = concept.child_ids.filtered(lambda c: c.product_id.id == resource.id)
            if space:
                qty_space = self.get_space_quantity(concept,space)
                for rec in records:
                    if rec.quantity > 0:
                        total_qty += self.recursive_quantity_space(rec,space,qty_space,None)
            else:
                for rec in records:
                    if rec.quantity > 0:
                        total_qty += self.recursive_quantity(rec,rec.parent_id,None)
        return total_qty

    # ~ def recursive_amount(self, resource, parent, amount=None):
        # ~ amount = amount is None and resource.balance or amount or 0.0
        # ~ if parent.type == 'departure':
            # ~ amount_partial = amount * parent.quantity
            # ~ return self.recursive_amount(resource, parent.parent_id, amount_partial)
        # ~ else:
            # ~ return amount * parent.quantity

    # ~ @api.model
    # ~ def get_total(self, resource):
        # ~ budget = self.budget_id
        # ~ records = budget.concept_ids.filtered(lambda c: c.type == resource)
        # ~ total = 0
        # ~ for rec in records:
            # ~ total += self.recursive_amount(rec, rec.parent_id, None)
        # ~ return total

    def print_report(self):
        if self.display_type == 'detailed':
            print ('.....1....')
        elif self.display_type == 'range':
            print ('.....2....')
        else:
            self.print_xls()
        #action.update({'close_on_report_download': True})

    def get_stock_out(self,product,location,concept=False):
        quantity = 0
        if not concept:
            moves = self.env['stock.move'].search([
                ('product_id','=',product.id),
                ('location_id','=',location.id),
                ('picking_id.bim_concept_id','=',False)])
        else:
            moves = self.env['stock.move'].search([
                ('product_id','=',product.id),
                ('location_id','=',location.id),
                ('picking_id.bim_concept_id','=',concept.id)])
        if moves:
            quantity = sum(move.product_qty for move in moves)
        return quantity

    def get_part_out(self,product,res_type,concept):
        quantity = 0
        if concept:
            lines = self.env['bim.part.line'].search([
                ('name','=',product.id),
                ('resource_type','=',res_type),
                ('part_id.concept_id','=',concept.id)])
        if lines:
            quantity = sum(line.product_uom_qty for line in lines)
        return quantity

    def print_xls(self):
        self.ensure_one()
        project = self.project_id
        location = project.stock_location_id
        domain = [('bim_project_id','=',project.id)]
        part_domain = [('project_id','=',project.id)]

        if self.display_type == 'summary':
            header = ["Código","Nombre","Inventario General","Inventario Ubicación","Presupuesto","Partida","Uom","Salidas","Coste","Importe"]
        elif self.display_type == 'range':
            domain.append(('date','>=',self.date_beg))
            domain.append(('date','<=',self.date_end))
            part_domain.append(('date','>=',self.date_beg))
            part_domain.append(('date','<=',self.date_end))
            header = ["Código","Nombre","Inventario General","Inventario Ubicación","Presupuesto","Partida","Uom","Salidas","Coste","Importe"]
        else:
            header = ["Código","Nombre","Movimiento/Parte","Presupuesto","Partida","Objeto de Obra","Espacio","Proveedor","Descripción","Fecha","Inventario General","Inventario Ubicación","Uom","Cantidad","Coste","Importe","Cantidad","Coste","Importe","Cantidad","Importe"]

        # Buscamos los picking de la Obra
        pickings = self.env['stock.picking'].search(domain)

        #Buscamos las partidas
        departs = pickings.mapped('bim_concept_id')

        #Buscamos las Partes de la Obra
        parts = self.env['bim.part'].search(part_domain)
        dep_parts = parts.mapped('concept_id')

        # Datos Para excel
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet(_('Libro'))
        Quants = self.env['stock.quant']
        style_title = easyxf('font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center')
        style_negative = easyxf('font: color red;')

        row = 0
        index = 0
        if self.display_type == 'detailed':
            ws.write_merge(row,row,13,15, "PRESUPUESTO",style_title)
            ws.write_merge(row,row,16,18, "REAL EJECUTADO",style_title)
            ws.write_merge(row,row,19,20, "DIFERENCIA",style_title)
            row = row + 1

        for head in header:
            ws.write(row, index, head, style_title)
            index = index + 1

        row = row + 1

        # CALCULO DE LINEAS RESUMIDAS y RANGO
        if self.display_type in ['range','summary']:
            # (Partes)
            for concept in dep_parts:
                # Mano de Obra
                if self.labor:
                    product_ids = []
                    for part in parts.filtered(lambda pt: pt.concept_id.id == concept.id):
                        products = part.lines_ids.mapped('name')
                        for product in products.filtered(lambda p: p.resource_type == 'H'):
                            if not product.id in product_ids:
                                qty_location = Quants._get_available_quantity(product,location)
                                part_outs = self.get_part_out(product,'H',concept)
                                ws.write(row, 0, product.default_code or '')
                                ws.write(row, 1, product.display_name)
                                ws.write(row, 2, product.qty_available or 0)
                                ws.write(row, 3, qty_location or 0)
                                ws.write(row, 4, concept.name)
                                ws.write(row, 5, concept.budget_id.name)
                                ws.write(row, 6, product.uom_id.name)
                                ws.write(row, 7, part_outs)
                                ws.write(row, 8, product.standard_price)
                                ws.write(row, 9, part_outs*product.standard_price)
                                product_ids.append(product.id)
                                row += 1
                # Equipos
                if self.equipment:
                    product_ids = []
                    for part in parts.filtered(lambda pt: pt.concept_id.id == concept.id):
                        products = part.lines_ids.mapped('name')
                        for product in products.filtered(lambda p: p.resource_type == 'Q'):
                            if not product.id in product_ids:
                                qty_location = Quants._get_available_quantity(product,location)
                                part_outs = self.get_part_out(product,'Q',concept)
                                ws.write(row, 0, product.default_code or '')
                                ws.write(row, 1, product.display_name)
                                ws.write(row, 2, product.qty_available or 0)
                                ws.write(row, 3, qty_location or 0)
                                ws.write(row, 4, concept.name)
                                ws.write(row, 5, concept.budget_id.name)
                                ws.write(row, 6, product.uom_id.name)
                                ws.write(row, 7, part_outs)
                                ws.write(row, 8, product.standard_price)
                                ws.write(row, 9, part_outs*product.standard_price)
                                product_ids.append(product.id)
                                row += 1

            # Materiales (Picking)
            if self.material:
                for concept in departs:
                    product_ids = []
                    for pick in pickings.filtered(lambda sp: sp.bim_concept_id.id == concept.id):
                        products = pick.move_lines.mapped('product_id')
                        for product in products:
                            if not product.id in product_ids:
                                qty_location = Quants._get_available_quantity(product,location)
                                ws.write(row, 0, product.default_code or '')
                                ws.write(row, 1, product.display_name)
                                ws.write(row, 2, product.qty_available or 0)
                                ws.write(row, 3, qty_location or 0)
                                ws.write(row, 4, concept.name)
                                ws.write(row, 5, concept.budget_id.name)
                                ws.write(row, 6, product.uom_id.name)
                                ws.write(row, 7, self.get_stock_out(product,location,concept))
                                ws.write(row, 8, product.standard_price)
                                ws.write(row, 9, self.get_stock_out(product,location,concept)*product.standard_price)
                                product_ids.append(product.id)
                                row += 1
                product_ids = []
                for pick in pickings.filtered(lambda sp: not sp.bim_concept_id):
                    for product in pick.move_lines.mapped('product_id'):
                        if not product.id in product_ids:
                            qty_location = Quants._get_available_quantity(product,location)
                            ws.write(row, 0, product.default_code or '')
                            ws.write(row, 1, product.display_name)
                            ws.write(row, 2, product.qty_available or 0)
                            ws.write(row, 3, qty_location or 0)
                            ws.write(row, 4, '')
                            ws.write(row, 5, '')
                            ws.write(row, 6, product.uom_id.name)
                            ws.write(row, 7, self.get_stock_out(product,location))
                            ws.write(row, 8, product.standard_price)
                            ws.write(row, 9, self.get_stock_out(product,location,concept)*product.standard_price)
                            product_ids.append(product.id)
                            row += 1

        # CALCULO DE LINEAS DETALLADAS
        else:
            #Materiales (Picking)
            if self.material:
                for pick in pickings:
                    for move in pick.move_lines:
                        qty_location = Quants._get_available_quantity(move.product_id,location)
                        qty_budget = self.get_quantity(move.product_id,pick.bim_concept_id,pick.bim_space_id)
                        quantity_dif = qty_budget-move.product_uom_qty
                        amount_dif = (qty_budget*move.product_id.standard_price)-(move.product_uom_qty*move.product_id.standard_price)
                        ws.write(row, 0, move.product_id.default_code or '')
                        ws.write(row, 1, move.product_id.display_name)
                        ws.write(row, 2, move.reference)
                        ws.write(row, 3, pick.bim_concept_id and pick.bim_concept_id.budget_id.name or '')
                        ws.write(row, 4, pick.bim_concept_id and pick.bim_concept_id.name or '')
                        ws.write(row, 5, pick.bim_object_id and pick.bim_object_id.desc or '')
                        ws.write(row, 6, pick.bim_space_id and pick.bim_space_id.name or '')
                        ws.write(row, 7, move.product_id.seller_ids and move.product_id.seller_ids[0].name.display_name or '')
                        ws.write(row, 8, pick.note and pick.note or '')
                        ws.write(row, 9, datetime.strftime(move.date,'%Y-%m-%d'))
                        ws.write(row, 10, move.product_id.qty_available or 0)
                        ws.write(row, 11, qty_location or 0)
                        ws.write(row, 12, move.product_id.uom_id.name)
                        ws.write(row, 13, qty_budget)               #Presupuesto
                        ws.write(row, 14, move.product_id.standard_price)            #Presupuesto
                        ws.write(row, 15, qty_budget*move.product_id.standard_price) #Presupuesto
                        ws.write(row, 16, move.product_uom_qty)
                        ws.write(row, 17, move.product_id.standard_price)
                        ws.write(row, 18, move.product_uom_qty*move.product_id.standard_price)
                        if quantity_dif < 0:
                            ws.write(row, 19, quantity_dif,style_negative)
                        else:
                            ws.write(row, 19, quantity_dif)

                        if amount_dif < 0:
                            ws.write(row, 20, amount_dif,style_negative)
                        else:
                            ws.write(row, 20, amount_dif)
                        row += 1

            #  Mano de Obra
            if self.labor:
                for part in parts:
                    for line in part.lines_ids:
                        if line.resource_type == 'H':
                            product = line.name
                            qty_location = Quants._get_available_quantity(product,location)
                            qty_budget = self.get_quantity(product,part.concept_id,part.space_id)
                            quantity_dif = qty_budget-line.product_uom_qty
                            amount_dif = (qty_budget*product.standard_price)-line.price_subtotal
                            ws.write(row, 0, product.default_code or '')
                            ws.write(row, 1, product.display_name)
                            ws.write(row, 2, line.part_id.name)
                            ws.write(row, 3, part.concept_id and part.concept_id.budget_id.name or '')
                            ws.write(row, 4, part.concept_id and part.concept_id.name or '')
                            ws.write(row, 5, part.space_id.object_id and part.space_id.object_id.desc or '')
                            ws.write(row, 6, part.space_id and part.space_id.name or '')
                            ws.write(row, 7, part.partner_id and part.partner_id.name or line.partner_id.name)
                            ws.write(row, 8, line.description and line.description or '')
                            ws.write(row, 9, datetime.strftime(part.date,'%Y-%m-%d'))
                            ws.write(row, 10, product.qty_available or 0)
                            ws.write(row, 11, qty_location or 0)
                            ws.write(row, 12, line.product_uom.name)
                            ws.write(row, 13, qty_budget)          #Presupuesto
                            ws.write(row, 14, product.standard_price)     #Presupuesto
                            ws.write(row, 15, qty_budget*product.standard_price) #Presupuesto
                            ws.write(row, 16, line.product_uom_qty)
                            ws.write(row, 17, line.price_unit)
                            ws.write(row, 18, line.price_subtotal)
                            if quantity_dif < 0:
                                ws.write(row, 19, quantity_dif,style_negative)
                            else:
                                ws.write(row, 19, quantity_dif)
                            if amount_dif < 0:
                                ws.write(row, 20, amount_dif,style_negative)
                            else:
                                ws.write(row, 20, amount_dif)
                            row += 1

            # Equipos (Partes)
            if self.equipment:
                for part in parts:
                    for line in part.lines_ids:
                        if line.resource_type == 'Q':
                            product = line.name
                            qty_location = Quants._get_available_quantity(product,location)
                            qty_budget = self.get_quantity(product,part.concept_id,part.space_id)
                            quantity_dif = qty_budget-line.product_uom_qty
                            amount_dif = (qty_budget*product.standard_price)-line.price_subtotal
                            ws.write(row, 0, product.default_code or '')
                            ws.write(row, 1, product.display_name)
                            ws.write(row, 2, line.part_id.name)
                            ws.write(row, 3, part.concept_id and part.concept_id.budget_id.name or '')
                            ws.write(row, 4, part.concept_id and part.concept_id.name or '')
                            ws.write(row, 5, part.space_id.object_id and part.space_id.object_id.desc or '')
                            ws.write(row, 6, part.space_id and part.space_id.name or '')
                            ws.write(row, 7, part.partner_id and part.partner_id.name or line.partner_id.name)
                            ws.write(row, 8, line.description and line.description or '')
                            ws.write(row, 9, datetime.strftime(part.date,'%Y-%m-%d'))
                            ws.write(row, 10, product.qty_available or 0)
                            ws.write(row, 11, qty_location or 0)
                            ws.write(row, 12, line.product_uom.name)
                            ws.write(row, 13, qty_budget) #Presupuesto
                            ws.write(row, 14, product.standard_price)      #Presupuesto
                            ws.write(row, 15, qty_budget*product.standard_price)  #Presupuesto
                            ws.write(row, 16, line.product_uom_qty)
                            ws.write(row, 17, line.price_unit)
                            ws.write(row, 18, line.price_subtotal)
                            if quantity_dif < 0:
                                ws.write(row, 19, quantity_dif,style_negative)
                            else:
                                ws.write(row, 19, quantity_dif)
                            if amount_dif < 0:
                                ws.write(row, 20, amount_dif,style_negative)
                            else:
                                ws.write(row, 20, amount_dif)
                            row += 1
        #.Exportacion
        fp = io.BytesIO()
        wb.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        data_b64 = base64.encodestring(data)
        attach = self.env['ir.attachment'].create({
            'name': '%s.%s'%(project.name,self.doc_type),
            'type': 'binary',
            'datas': data_b64  })
        url = '/web/content/?model=ir.attachment'
        url += '&id={}&field=datas&download=true&filename={}'.format(attach.id,attach.name)
        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'self'}
