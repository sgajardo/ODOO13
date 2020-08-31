# -*- coding: utf-8 -*-

from odoo import fields, models, tools, api, _


class HrPayrollHistoric(models.Model):
    _name = 'hr.payroll.historic'
    _description = 'Histórico de nóminas'
    _order = 'name'

    name = fields.Char(string="Período")
    date_from = fields.Date(string="Fecha inicio")
    date_to = fields.Date(string="Fecha fin")
    company_id = fields.Many2one('res.company', string="Compañia", default=lambda self: self.env.company.id)
    line_ids = fields.One2many('hr.payroll.historic.lines', 'historic_id', string="Documents")

    _sql_constraints = [('unique_historic', 'unique(name,date_from,date_to)', _('Error! Ya existe un historico cargado para el período seleccionado!'))]


class HrPayrollHistoricLine(models.Model):
    _name = 'hr.payroll.historic.lines'
    _description = 'Líneas de histórico de nóminas'

    origin = fields.Char(string="Origen")
    historic_id = fields.Many2one('hr.payroll.historic', string="Padre")
    employee_id = fields.Many2one('hr.employee', string="Empleado")
    afp_id = fields.Many2one('hr.afp', string="AFP")
    job_id = fields.Many2one('hr.job', string="Puesto de trabajo")
    struct_id = fields.Many2one('hr.payroll.structure', string="Estructura de trabajo")
    contract_id = fields.Many2one('hr.contract', string="Contrato")
    centro_costo_id = fields.Many2one('hr.centroscostos', string="Centro de costo")
    amount = fields.Float(string="Monto")
    contract_ids = fields.Many2many(
        comodel_name="hr.contract",
        relation='hr_payslip_employee_historic_rel',
        id1='line_id',
        id2='contract_id',
        string='Contratos')
