# coding: utf-8
from odoo import api, fields, models


class ResPartner(models.Model):
    _description = "Partner Bim"
    _inherit = 'res.partner'


    # Proyectos ...

    retention_product = fields.Many2one('product.product', 'Producto Retención',
                                        help="Producto que se utilizará para facturar la retención")

    project_ids = fields.One2many('bim.project', 'customer_id', 'Proyectos')
    project_count = fields.Integer('Proyectos', compute="_get_project_count")


    def _get_project_count(self):
        for projects in self:
            projects.project_count = len(projects.project_ids)

    def action_view_projects(self):
        projects = self.mapped('project_ids')
        context = self.env.context.copy()
        context.update(default_customer_id=self.id)
        return {
            'type': 'ir.actions.act_window',
            'name': u'Proyectos',
            'res_model': 'bim.project',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'domain': [('id', 'in', projects.ids)],
            'context': context
        }


    # Mantenimientos ...

    maintenance_ids = fields.One2many('bim.maintenance', 'partner_id', 'Man')
    maintenance_count = fields.Integer('Mantenimiento', compute="_get_maintenance_count")

    def _get_maintenance_count(self):
        for maintenances in self:
            maintenances.maintenance_count = len(maintenances.maintenance_ids)

    def action_view_maintenances(self):
        maintenances = self.mapped('maintenance_ids')
        context = self.env.context.copy()
        context.update(default_partner_id=self.id)
        return {
            'type': 'ir.actions.act_window',
            'name': u'Mantenimientos',
            'res_model': 'bim.maintenance',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'domain': [('id', 'in', maintenances.ids)],
            'context': context
        }


