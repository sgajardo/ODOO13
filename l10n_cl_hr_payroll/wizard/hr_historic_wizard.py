# -*- encoding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import time
from datetime import datetime, timedelta
from dateutil import relativedelta
from calendar import monthrange
import csv
import base64

class HrHistoricWizard(models.TransientModel):
    _name = 'hr.historic.wizard'
    _description = 'Historico'

    
    @api.depends('date_from','date_to')
    def _get_period(self):
        for val in self:
            date_from = datetime.strptime(val.date_from,'%Y-%m-%d')
            date_to = datetime.strptime(val.date_to,'%Y-%m-%d')
            if date_from.month == date_to.month:
                val.period = '%s-%s'%(str(date_from.month).zfill(2),date_from.year)
            else:
                val.period = '%s-%s al %s-%s'%(str(date_from.month).zfill(2),date_from.year,str(date_to.month).zfill(2),date_to.year)
    
    operation = fields.Selection([
        ('upload','Carga'),
        ('download','Descarga'),
        ],string="Operación",
        required=True)
        
    type = fields.Selection([
        ('all','Todos los empleados'),
        ('one','Un empleado'),
        ],string="Seleccione")
    
    period = fields.Char(
        string='Período', 
        readonly=True, compute="_get_period")
  
    date_from = fields.Date(
        string='Desde', required=True,
        default=time.strftime('%Y-%m-01'))
        
    date_to = fields.Date(
        string='Hasta', 
        required=True,
        default=str(datetime.now()+relativedelta.relativedelta(months=+1,day=1,days=-1))[:10],)
    
    employee_id = fields.Many2one('hr.employee', string="Empleado")

    company_id = fields.Many2one('res.company', string="Company", required=True,
                                 default=lambda self: self.env.user.company_id.id)
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(self.filtered(lambda payslip: payslip.date_from > payslip.date_to)):
            raise ValidationError(_("La fecha final no puede ser menor que la fecha inicial'."))
    
    def ask_operation(self):
        if self.operation == 'upload':
            self.upload_historic()
        else:
            self.download_historic()
        
    def upload_historic(self, payslip_process=False):
        self.company_id.hr_period = self.period

        context = dict(self._context or {})

        historic = self.env['hr.payroll.historic'].search([('name', '=', self.period)])

        if payslip_process and historic:
            historic.unlink()

        tree_id = self.env.ref('l10n_cl_hr_payroll.hr_payroll_historic_view_tree')
        #Buscamos las nóminas realizadas en el periodo seleccionado
        payslip = self.env['hr.payslip'].search(
            [('date_from','>=',self.date_from),
             ('date_to','<=',self.date_to)
             ])
        if payslip:
            #contracts = []
            details = []
            values = {'name': self.period, 'date_from': self.date_from,'date_to': self.date_to }
            for data in payslip:
                #~ for contract in data.worked_days_line_ids:
                    #~ if contract.contract_id:
                        #~ contracts.append(contract.id)
                #~ for contract in data.input_line_ids:
                    #~ if contract.contract_id:
                        #~ contracts.append(contract.id)
                vals = {
                    'origin': data.number or data.name,
                    'employee_id': data.employee_id.id,
                    'afp_id': data.employee_id.afp_id.id,
                    'job_id': data.employee_id.job_id.id,
                    'struct_id': data.struct_id.id,
                    'centro_costo_id': data.employee_id.centro_costo_id.id,
                    'contract_id': data.contract_id.id,
                    #'contract_ids': [(6, 0, contracts)],
                    }
                details.append((0,0,vals))
                vals = {}
            values.update({'line_ids': details})

            historic_id = self.env['hr.payroll.historic'].create(values)

            if not payslip_process:
                return {   'name': ('Historico'),
                           'res_model': 'hr.payroll.historic',
                           'view_mode': 'tree,form',
                           'view_id': historic_id.id,
                           'context': context,
                           'views': [(tree_id.id, 'tree')],
                           'type': 'ir.actions.act_window',
                           'target': 'current',
                           #'domain': [('id','in',[historic_id.id])],
                           'nodestroy': True
                       }
            else:
                return True
    def download_historic(self):
        employee_obj = self.env['hr.employee']
        context = dict(self._context or {})
        tree_id = self.env.ref('l10n_cl_hr_payroll.hr_payroll_historic_view_tree')

        self.company_id.hr_period = self.period
        
        #Buscamos las nóminas realizadas en el periodo seleccionado
        historic = self.env['hr.payroll.historic'].search([('name','=',self.period)])
        if len(historic) > 1:
                raise ValidationError(_("El período de nómina se encuentra duplicado en el histórico."))
        if historic:
            for employee in historic.line_ids:
                vals = {
                    'afp_id': employee.afp_id and employee.afp_id.id or False,
                    'job_id': employee.job_id and employee.job_id.id or False,
                    'struct_id': employee.struct_id and employee.struct_id.id or False,
                    'centro_costo_id': employee.centro_costo_id and employee.centro_costo_id.id or False,
                    'contract_id': employee.contract_id and employee.contract_id.id or False,
                    }
                if self.type == 'one':
                    if employee.employee_id.id == self.employee_id.id:
                        employee.employee_id.write(vals)
                else:
                    employee.employee_id.write(vals)
        
            return {   'name': ('Historico'),
                   'res_model': 'hr.payroll.historic',
                   'view_mode': 'tree,form', 
                   #'view_id': historic_id.id,
                   'context': context,
                   'views': [(tree_id.id, 'tree')],
                   'type': 'ir.actions.act_window',
                   'target': 'current',
                   'domain': [('id','in',[historic.ids])],
                   'nodestroy': True
                }
# Recomendacion: indicar si la nomina es mensual, quincenal o semanal 
