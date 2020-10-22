# -*- coding: utf-8 -*-
from odoo.tools.float_utils import float_compare
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models,_
from odoo.exceptions import ValidationError


class BimConcepts(models.Model):
    _inherit = 'bim.concepts'


    quantity_ot = fields.Float('Cantidad OT', compute="_compute_execute", digits='BIM qty')
    qty_execute_ot = fields.Float('Ejecutado OT', compute="_compute_execute", digits='BIM qty')
    qty_execute_total = fields.Float('Cantidad Total', compute="_compute_quantity_execute", digits='BIM qty')
    amount_execute_labor_ot = fields.Monetary('Total mano de obra OT', compute="_compute_execute")
    amount_execute_material_ot = fields.Monetary('Total material OT', compute="_compute_execute")

    @api.depends('qty_execute','qty_execute_ot')
    def _compute_quantity_execute(self):
        for record in self:
            record.qty_execute_total = record.qty_execute + record.qty_execute_ot

    @api.depends('parent_id','child_ids','child_ids.amount_execute','type','aux_amount_count','equip_amount_count','labor_amount_count','material_amount_count')
    def _compute_execute(self):
        wo_concept_obj = self.env['bim.workorder.concepts']
        stock_obj = self.env['stock.picking']
        part_obj = self.env['bim.part']
        for record in self:
            execute_equip = execute_labor = execute_material = executed =  balance_execute = 0
            quantity_ot = execute_ot = labor_ot = material_ot = 0
            quantity = 1
            departure = self.get_departure_parent(record.parent_id)

            if record.type == 'material':
                if departure:
                    pickings = stock_obj.search([('bim_concept_id','=',departure.id)])
                    for pick in pickings:
                        for move in pick.move_lines:
                            if move.product_id == record.product_id:
                                quantity += move.product_uom_qty
                                executed += self._get_value(move.product_uom_qty,move.product_id)

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
                    executed = (departure.amount_execute / total_indicators * departure.aux_amount_count) if total_indicators else 0.0 #self.recursive_amount(record,record.parent_id,None)# #

            elif record.type == 'departure':
                pickings = stock_obj.search([('bim_concept_id','=',record.id)])
                for pick in pickings:
                    for move in pick.move_lines:
                        quantity += move.product_uom_qty
                        executed += self._get_value(move.product_uom_qty,move.product_id)
                        execute_material += self._get_value(move.product_uom_qty,move.product_id)

                parts = part_obj.search([('concept_id','=',record.id)])
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

                # Calculo agregado de OT
                workorders_concept = wo_concept_obj.search([('concept_id','=',record.id),('workorder_id.state','not in',['draft','done'])])
                for wco in workorders_concept:
                    quantity_ot += wco.qty_worder
                    execute_ot += wco.qty_execute_mo
                    labor_ot += wco.amt_execute_mo
                    material_ot += wco.amt_execute_mt
                balance_execute = execute_equip + execute_labor + execute_material + labor_ot + material_ot
            else:
                balance_execute = sum(child.balance_execute for child in record.child_ids)

            # Update fields OT
            record.quantity_ot = quantity_ot
            record.qty_execute_ot = execute_ot
            record.amount_execute_labor_ot = labor_ot
            record.amount_execute_material_ot = material_ot

            # Original fields
            total_qty = execute_ot + record.qty_execute
            record.amount_execute_equip = execute_equip
            record.amount_execute_labor = execute_labor + labor_ot
            record.amount_execute_material = execute_material + material_ot
            record.balance_execute = balance_execute
            record.amount_execute = balance_execute / (total_qty > 0 and total_qty or 1)


class BimConceptMeasuring(models.Model):
    _inherit = 'bim.concept.measuring'

    @api.depends('qty', 'length', 'width', 'height', 'formula')
    def _compute_quantity(self):
        wo_obj = self.env['bim.workorder']
        wo_concept_obj = self.env['bim.workorder.concepts']
        for record in self:
            execute = 0
            if record.space_id:
                workorders = wo_obj.search([('space_id','=',record.space_id.id)])
                if workorders:
                    workorders_concept = wo_concept_obj.search([('concept_id','=',record.concept_id.id),('workorder_id','in',workorders.ids)])
                    for wco in workorders_concept:
                        execute += wco.qty_execute_mo
            record.qty_real = execute
            record.qty_certif = record.amount_subtotal if record.stage_id and record.stage_state in ['process', 'approved'] else 0.0


    qty_real = fields.Float(string='Cant Real', digits='BIM qty', compute="_compute_quantity")
    qty_certif = fields.Float(string='Cant Cert', digits='BIM qty', compute="_compute_quantity")
