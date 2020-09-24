# -*- coding: utf-8 -*-
from odoo.tools.float_utils import float_compare
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models,_
from odoo.exceptions import ValidationError


class BimConcepts(models.Model):
    _inherit = 'bim.concepts'

    @api.depends('parent_id','child_ids','child_ids.amount_execute','type',
    'aux_amount_count','equip_amount_count','labor_amount_count','material_amount_count')
    def _compute_execute(self):
        workorder_obj = self.env['bim.workorder']
        wo_concept_obj = self.env['bim.workorder.concepts']
        wo_timesheet_obj = self.env['workorder.timesheet']
        for record in self:

            execute_equip = execute_labor = executed = amount_labor = amount_material = 0
            quantity = 1
            departure = self.get_departure_parent(record.parent_id)

            # ~ if record.type == 'material':
                # ~ if departure:
                    # ~ pickings = stock_obj.search([('bim_concept_id','=',departure.id)])
                    # ~ for pick in pickings:
                        # ~ for move in pick.move_lines:
                            # ~ if move.product_id == record.product_id:
                                # ~ quantity += move.product_uom_qty
                                # ~ executed += self._get_value(move.product_uom_qty,move.product_id)

            # ~ elif record.type == 'labor':
                # ~ if departure:
                    # ~ for part in departure.part_ids:
                        # ~ for line in part.lines_ids:
                            # ~ if line.resource_type == 'H' and line.name == record.product_id:
                                # ~ quantity += line.product_uom_qty
                                # ~ executed += line.price_subtotal

            # ~ elif record.type == 'equip':
                # ~ if departure:
                    # ~ for part in departure.part_ids:
                        # ~ for line in part.lines_ids:
                            # ~ if line.resource_type == 'Q' and line.name == record.product_id:
                                # ~ quantity += line.product_uom_qty
                                # ~ executed += line.price_subtotal

            # ~ elif record.type == 'aux':
                # ~ if departure:
                    # ~ total_indicators = departure.equip_amount_count + departure.labor_amount_count + departure.material_amount_count
                    # ~ executed = (departure.amount_execute / total_indicators * departure.aux_amount_count) if total_indicators else 0.0 #self.recursive_amount(record,record.parent_id,None)# #

            if record.type == 'chapter':
                executed = sum(child.amount_execute for child in record.child_ids)

            elif record.type == 'departure':
                workorders_concept = wo_concept_obj.search([('concept_id','=',record.id)]) #Falta Filtro OT workorder_id.state=delivered
                for wco in workorders_concept:
                    quantity += wco.qty_worder
                    execute_labor += wco.qty_execute_mo
                    amount_labor += wco.amt_execute_mo
                    amount_material += wco.amt_execute_mt
            else:
                executed = 0

            record.qty_execute = quantity
            record.amount_execute = execute_labor / quantity
            record.balance_execute = amount_material
            record.amount_execute_equip = execute_equip
            record.amount_execute_labor = execute_labor
            record.amount_execute_material = 0
