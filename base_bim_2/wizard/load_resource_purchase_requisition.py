# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError

class ResourceRequisitionwizard(models.TransientModel):
    _name = 'resource.requisition.wzd'
    _description = 'Cargar Recursos Obra'

    def _get_default_project_id(self):
        active_id = self._context.get('active_id')
        req = self.env['bim.purchase.requisition'].browse(active_id)
        return req.project_id and req.project_id.id or False


    project_id = fields.Many2one("bim.project", string="Obra", default=_get_default_project_id)
    budget_ids = fields.Many2many("bim.budget", string="Presupuestos")
    type = fields.Selection([
        ('wo_stock', 'Comprar sin stock'),
        ('wi_stock', 'Comprar con stock'),
        ('wo_req', 'Comprar no solicitudes')],
        'Tipo', default='wo_stock')

    def load_resources(self):
        if not self.budget_ids:
            raise UserError(_('Por favor seleccione al menos un presupuesto.'))

        requisition_id = self._context.get('active_id')
        ProductList = self.env['product.list']
        concept_ids = []
        for budget in self.budget_ids:
            for concept in budget.concept_ids:
                concept_ids.append(concept.id)

        concepts = self.env['bim.concepts'].browse(concept_ids)
        resources = self.get_resources(concepts)
        for resource in resources:
            if resource.resource_type == 'M':
                quantity = self.get_quantity(concepts,resource)
                val = {
                    'requisition_id': requisition_id,
                    'product_id': resource.id,
                    'um_id': resource.uom_id.id,
                    'quant': quantity,
                    'analytic_id': self.project_id.analytic_id.id or False  }
                ProductList.create(val)

    def get_resources(self,concepts):
        domain = ['material','equip','labor','subcon']
        resources = concepts.filtered(lambda c: c.type in domain).mapped('product_id')
        return resources

    def get_quantity(self,concepts,resource):
        records = concepts.filtered(lambda c: c.product_id.id == resource.id)
        total_qty = 0
        for rec in records:
            if rec.quantity > 0 and rec.parent_id.quantity > 0:
                total_qty += self.recursive_quantity(rec,rec.parent_id,None)
        return total_qty

    def recursive_quantity(self, resource, parent, qty=None):
        qty = qty is None and resource.quantity or qty
        if parent.type == 'departure':
            qty_partial = qty * parent.quantity
            return self.recursive_quantity(resource,parent.parent_id,qty_partial)
        else:
            return qty * parent.quantity

