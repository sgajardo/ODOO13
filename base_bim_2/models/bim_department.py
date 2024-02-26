# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime


class BimDepartment(models.Model):
    _description = "Departamento de Obra"
    _name = 'bim.department'
    _order = "id desc"

    def count_projects(self):
        for record in self:
            record.count_project_new = len(record.project_ids.filtered(lambda r: r.estado == '1'))
            record.count_project_estudy = len(record.project_ids.filtered(lambda r: r.estado == '2'))
            record.count_project_bidding = len(record.project_ids.filtered(lambda r: r.estado == '3'))
            record.count_project_revision = len(record.project_ids.filtered(lambda r: r.estado == '4'))
            record.count_project_awarded = len(record.project_ids.filtered(lambda r: r.project_state == 'in_process'))
            record.count_project_process = len(record.project_ids.filtered(lambda r: r.estado == '6'))
            record.count_project_lost = len(record.project_ids.filtered(lambda r: r.estado == '7'))
            record.count_project_quality = len(record.project_ids.filtered(lambda r: r.estado == '8'))
            record.count_project_delivered = len(record.project_ids.filtered(lambda r: r.estado == '9'))
    #         record.count_project_contracts_maintenance = len(record.project_ids.filtered(lambda r: r.maintenance_contract is True))

    name = fields.Char('Nombre', translate=True)
    project_ids = fields.One2many('bim.project','department_id','projects')
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company,
                                 required=True)
    count_project_new = fields.Integer('Obras Nuevas', compute="count_projects")
    count_project_estudy = fields.Integer('Obras Estudio', compute="count_projects")
    count_project_bidding = fields.Integer('Obras Licitación', compute="count_projects")
    count_project_revision = fields.Integer('Obras Revisión', compute="count_projects")
    count_project_awarded = fields.Integer('Obras Adjudicadas', compute="count_projects")
    count_project_process = fields.Integer('Obras Proceso', compute="count_projects")
    count_project_lost = fields.Integer('Obras Perdido', compute="count_projects")
    count_project_quality = fields.Integer('Obras Calidad', compute="count_projects")
    count_project_delivered = fields.Integer('Obras Entregado', compute="count_projects")
    count_project_contracts_maintenance = fields.Integer('Contratos Mantenimiento',)# compute="count_projects")
