# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WorkorderInstallerWizard(models.TransientModel):
    _name = "workorder.installer.wzd"

    project_id = fields.Many2one('bim.project', "Obra")
    installer_id = fields.Many2one("bim.workorder.installer", string="Instalador", required=True)
    location_id = fields.Many2one('stock.location', string="Locación",related='installer_id.location_id')
    line_ids = fields.One2many('workorder.installer.line.wzd','wizard_id',string="Lineas")

    @api.model
    def default_get(self, fields):
        res = super(WorkorderInstallerWizard, self).default_get(fields)
        context = self._context
        pick = self.env['stock.picking'].browse(context['active_id'])
        lines = []
        for line in pick.move_ids_without_package:
            lines.append((0,0,{
                'product_id': line.product_id.id,
                'quantity': line.product_uom_qty,
                'uom_id': line.product_uom.id,
                'cost': line.price_unit,
                'departure_id': line.workorder_departure_id.id,
            }))
        if not lines:
            raise UserError('No hay líneas nuevas para procesar')
        res['line_ids'] = lines
        res['project_id'] = pick.bim_project_id.id
        return res


    @api.onchange('installer_id')
    def onchange_installer_id(self):
        installer_list = []
        #if self.installer_id:
        installer_list = self.project_id.install_location_ids.ids
        return {'domain': {'installer_id': [('id','in',installer_list)]}}


    def create_installer_move(self):
        project = self.project_id
        company = self.env.company
        pick = self.env['stock.picking'].browse(self._context['active_id'])
        picking_type_obj = self.env['stock.picking.type']

        location_id = pick.location_dest_id.id
        location_dest_id = self.location_id.id

        if not location_id or not location_dest_id:
            raise ValidationError(u'No existe una Ubicacion de Stock.')

        move_lines = []
        for line in self.line_ids:
            if not line.quantity:
                continue
            move_lines.append([0, False, {
                'workorder_departure_id': line.departure_id and line.departure_id.id or False,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'price_unit': line.cost,
                'name': line.name }])

        picking_type = picking_type_obj.search([
            ('default_location_dest_id', '=', location_dest_id),
            ('code','=','internal')],limit=1)
        if not picking_type:
            picking_type = picking_type_obj.search([
            ('default_location_src_id', '=', location_dest_id),
            ('code', '=', 'internal')],limit=1)
            if not picking_type:
                picking_type = project.warehouse_id.int_type_id

        dicc = {}
        dicc.update({
            'picking_type_id': picking_type.id,
            'location_id': location_id,
            'move_lines': move_lines,
            'company_id': company.id,
            'origin': project.name,
            'partner_id': project.customer_id.id,
            'location_dest_id': location_dest_id,
            'bim_workorder_id': pick.bim_workorder_id and pick.bim_workorder_id.id or False,
            'bim_requisition_id': pick.bim_requisition_id and pick.bim_requisition_id.id or False,
            'bim_concept_id': pick.bim_concept_id and pick.bim_concept_id.id or False,
            'bim_project_id': project.id,
            'bim_space_id': pick.bim_space_id and pick.bim_space_id.id or False,
            'bim_object_id': pick.bim_object_id and pick.bim_object_id.id or False,
            'move_type': 'direct',
        })
        picking = self.env['stock.picking'].create(dicc)
        if company.validate_stock:
            if picking.state == 'draft':
                picking._check_company()
                picking.mapped('package_level_ids').filtered(lambda pl: pl.state == 'draft' and not pl.move_ids)._generate_moves()
                picking.mapped('move_lines').filtered(lambda move: move.state == 'draft')._action_confirm(False)
                picking.filtered(lambda pick: not pick.immediate_transfer and pick.location_id.usage in ('supplier', 'inventory', 'production') and pick.state == 'confirmed').mapped('move_lines')._action_assign()
            if picking.state != 'assigned':
                picking.action_assign()
            for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty
            picking.action_done()
        pick.message_post(body=_('La Entrega a Instaladores REF: %s ha sido creada') % picking.name)
        pick.purchase_id.picking_ids = [(4,picking.id,None)]
        return {'type': 'ir.actions.act_window_close'}

            #validacion
            # ~ if picking_out.state == 'draft':
                # ~ picking_out.action_confirm()
                # ~ if picking_out.state != 'assigned':
                    # ~ picking_out.action_assign()
                    # ~ if picking_out.state != 'assigned':
                        # ~ picking_out.action_force_assign()
            # ~ for move in picking_out.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                # ~ for move_line in move.move_line_ids:
                    # ~ move_line.qty_done = move_line.product_uom_qty
            # ~ picking_out.action_done()
    # ~ def action_confirm(self):
        # ~ self._check_company()
        # ~ self.mapped('package_level_ids').filtered(lambda pl: pl.state == 'draft' and not pl.move_ids)._generate_moves()
        # ~ # llamar a "_action_confirm" en cada movimiento de borrador
        # ~ self.mapped('move_lines').filtered(lambda move: move.state == 'draft')._action_confirm()
        # ~ # llamar  "_action_assign" en cada movimiento confirmado que location_id pasa por alto la reserva
        # ~ self.filtered(lambda picking: not picking.immediate_transfer and picking.location_id.usage in ('supplier', 'inventory', 'production') and picking.state == 'confirmed')\
            # ~ .mapped('move_lines')._action_assign()
        # ~ return True

class WorkorderInstallerLineWizard(models.TransientModel):
    _name = "workorder.installer.line.wzd"

    name = fields.Char('Detalle',related='product_id.display_name')
    quantity = fields.Float('Cantidad')
    cost = fields.Float('Costo')
    uom_id = fields.Many2one('uom.uom', 'U.M')
    product_id = fields.Many2one("product.product", string="Producto")
    wizard_id = fields.Many2one("workorder.installer.wzd", string="Parent")
    departure_id = fields.Many2one("bim.concepts", string="Partida")





