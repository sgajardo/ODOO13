# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from calendar import monthrange
import csv
import base64

class HrRemunerationReportWizard(models.TransientModel):
    _name = 'hr.remuneration.report.wizard'
    _description = 'Informe Remuneracion'

    @api.model
    def _get_default_start_date(self):
        date = fields.Date.from_string(fields.Date.today())
        start = '%s-%s-01'%(date.year, str(date.month).zfill(2))
        return start

    @api.model
    def _get_default_end_date(self):
        date = fields.Date.from_string(fields.Date.today())
        end_of_month = monthrange(date.year, date.month)[1]
        end = '%s-%s-%s'%(date.year, str(date.month).zfill(2), end_of_month)
        return end

    start_date = fields.Date(string='Fecha Inicio', default=_get_default_start_date, help="Ingrese la fecha inicio del periodo")
    end_date = fields.Date(string='Fecha Fin', default=_get_default_end_date, help="Ingrese la fecha fin del periodo")

    @api.onchange('start_date')
    def _onchange_dates(self):
        if self.start_date:
            year, month = map(int, self.start_date.split('-')[:2])
            self.end_date = '%d-%.2d-%.2d' % (year, month, monthrange(year, month)[-1])


    type_delimitador = fields.Selection(
        [(';', 'Punto y Coma'),
         (',', 'Coma')],
        'Tipo de Delimitador', size=1, default=';')

    def get_worked_days(self, code = None, payslip_id = None, emp_id = None, date_from = None, date_to = None):
        sql = '''select coalesce(sum(number_of_days),0) from hr_payslip_worked_days as p
        left join hr_payslip as r on r.id = p.payslip_id
        where 1 = 1'''

        if payslip_id:
            sql += ''' and r.id = %s'''%payslip_id

        if emp_id:
            sql += ''' and r.employee_id = %s'''%emp_id

        if date_from:
            sql += ''' and r.date_from >= %s'''%date_from

        if date_to:
            sql += ''' and r.date_to <= %s'''%date_to

        if code:
            sql += ''' and p.code = '%s' '''%code

        self.env.cr.execute(sql)

        results = self.env.cr.fetchone()

        if results:
            return results[0]
        else:
            return 0

        def get_worked_days(self, code=None, payslip_id=None, emp_id=None, date_from=None, date_to=None):
            sql = '''select coalesce(sum(number_of_days),0) from hr_payslip_worked_days as p
            left join hr_payslip as r on r.id = p.payslip_id
            where 1 = 1'''

            if payslip_id:
                sql += ''' and r.id = %s''' % payslip_id

            if emp_id:
                sql += ''' and r.employee_id = %s''' % emp_id

            if date_from:
                sql += ''' and r.date_from >= %s''' % date_from

            if date_to:
                sql += ''' and r.date_to <= %s''' % date_to

            if code:
                sql += ''' and p.code = '%s' ''' % code

            self.env.cr.execute(sql)

            results = self.env.cr.fetchone()

            if results:
                return results[0]
            else:
                return 0

    def get_total_worked_days(self, payslip_id = None, emp_id = None, date_from = None, date_to = None):

        d100 = self.get_worked_days('WORK100',payslip_id)
        if d100 < 30:
            d100 = 30

        dLic = self.get_worked_days('Licencia', payslip_id)

        dNtr = self.get_worked_days('No_Trabajado', payslip_id)

        return d100 - dLic - dNtr

    def get_rule_value(self, code=None, payslip_id=None, emp_id=None, date_from=None, date_to=None):

        sql = '''select COALESCE(sum(pl.total),0) from hr_payslip_line as pl
                left join hr_payslip as p on pl.slip_id = p.id
                where 1 = 1'''

        if payslip_id:
            sql += ''' and p.id = %s''' % payslip_id

        if emp_id:
            sql += ''' and p.employee_id = %s''' % emp_id

        if date_from:
            sql += ''' and p.date_from >= %s''' % date_from

        if date_to:
            sql += ''' and p.date_to <= %s''' % date_to

        if code:
            sql += ''' and pl.code = '%s' ''' % code

        self.env.cr.execute(sql)

        results = self.env.cr.fetchone()

        if results:
            return results[0]
        else:
            return 0

    def get_input_value(self, code=None, payslip_id=None, emp_id=None, date_from=None, date_to=None):

        sql = '''select COALESCE(sum(pl.amount),0) from hr_payslip_input as pl
                left join hr_payslip as p on pl.payslip_id = p.id
                where 1 = 1'''

        if payslip_id:
            sql += ''' and p.id = %s''' % payslip_id

        if emp_id:
            sql += ''' and p.employee_id = %s''' % emp_id

        if date_from:
            sql += ''' and p.date_from >= %s''' % date_from

        if date_to:
            sql += ''' and p.date_to <= %s''' % date_to

        if code:
            sql += ''' and pl.code = '%s' ''' % code

        self.env.cr.execute(sql)

        results = self.env.cr.fetchone()

        if results:
            return results[0]
        else:
            return 0

    def print_txt(self):
        res = {}
        payslips = self.env['hr.payslip'].search([
                ('date_to','>=',self.start_date),
                ('date_from','<=',self.end_date)
            ])
        if not payslips:
            raise ValidationError('No existen recibos de pago validados para este periodo')
        fname = 'odoo-informe-remuneracion-%s.csv'%self.end_date[5:]



        path = '/tmp/'+fname
        txtFile = open(path,'wb')
        writer = csv.writer(txtFile, delimiter=str(self.type_delimitador), quoting=csv.QUOTE_NONE)
        row = ['RUC','NOMBRE','CENTRO COSTOS','DIAS','S. BASE','No. HORAS EXTRAS (50%)','MONTO HORAS EXTRAS 50%',
               'No. HORAS EXTRAS (100%)','MONTO HORAS EXTRAS 100%','GRATIFICACION LEGAL','BONO DESEMPENO',
               'BONO INCENTIVO MINERIA','BONO TURNO','COMISION','BONO ZONA','BONO RIESGO','BONO SUPERVISION',
               'OTROS IMP.','TOTAL IMP.','ASIG. FAMILIAR','COLACION','MOVILIZACION','VIATICOS','OTROS NO IMP.',
               'TOTAL NO IMP.','TOTAL HABERES','PREVISION','% COTIZACION','COTIZACION OBLIGATORIA','SEGURO CENSATIA',
               '% TRABAJO PESADO','COTIZACION TRABAJO PESADO','A.P.Vs','CTA. AHORRO 2','INSTITUCION SALUD','PLAN PACTADO',
               'COTIZACION 7%','ADICIONAL ISAPRE','TOTAL DESCUENTOS PREVISIONALES','BASE TRIBUTABLE','IMP. UNICO',
               'PRESTAMOS INTERNOS','PRESTAMOS C.C.A.F.','ADELANTO VIATICO','ANTICIPO SUELDO','OTROS DESCTOS','TOTAL DESC.',
               'LIQUIDO A PAGAR', 'APORTE EMPLEADOR SIS','APORTE EMPLEADOR AFC','APORTE EMPLEADOR MUTUAL',
               'APORTE EMPLEADOR TRABAJO PESADO','TOTAL COSTO EMPRESA']

        writer.writerow(row)

        for p in payslips:
            emp = p.employee_id
            complete_name = '%s %s %s %s'%(emp.last_name and emp.last_name or '',emp.mothers_name and emp.mothers_name or '',emp.first_name and emp.first_name or '',emp.middle_name and emp.middle_name or '')
            rut_split = emp.identification_id

            row = [emp.identification_id,complete_name.encode("utf-8"), '',
                   #Dias
                   int(self.get_total_worked_days(p.id)),
                   #Sueldo Base
                   int(self.get_rule_value('SUELDO',p.id)),
                   #No. Horas Extras 50%
                   self.get_input_value('HEX',p.id),
                   # Monto Horas Extras 50%
                   int(self.get_rule_value('HEX',p.id)),
                   # No. Horas Extras 100%
                   self.get_input_value('HEX100', p.id),
                   # Monto Horas Extras 100%
                   int(self.get_rule_value('HEX100', p.id)),
                   # Gratificacion Legal
                   int(self.get_rule_value('GRAT', p.id)),
                   # BONO DESEMPENO
                   int(self.get_rule_value('BDESEMP', p.id)),
                   # BONO INCENTIVO MINERIA
                   int(self.get_rule_value('BINCM', p.id)),
                   # BONO TURNO
                   int(self.get_rule_value('BTURN', p.id)),
                   # COMISION
                   int(self.get_rule_value('COMI', p.id)),
                   # BONO ZONA
                   int(self.get_rule_value('BZON10', p.id)),
                   # BONO RIESGO
                   int(self.get_rule_value('BRIESG', p.id)),
                   # BONO SUPERVISION
                   int(self.get_rule_value('BSUP10', p.id)),
                   # OTROS IMPONIBLES
                   int(self.get_rule_value('BONO', p.id)),
                   # TOTAL IMPONIBLES
                   int(self.get_rule_value('TOTIM', p.id)),
                   # ASIGNACION FAMILIAR
                   int(self.get_rule_value('ASIGFAM', p.id)),
                   # COLACION
                   int(self.get_rule_value('COL', p.id)),
                   # MOVILIZACION
                   int(self.get_rule_value('MOV', p.id)),
                   # VIATICOS
                   int(self.get_rule_value('VIASAN', p.id)),
                   # OTROS NO IMPONIBLES
                   int(self.get_rule_value('OTRONOIMP', p.id)),
                   # TOTAL NO IMPONIBLE
                   int(self.get_rule_value('TOTNOI', p.id)),
                   # TOTAL HABERES
                   int(self.get_rule_value('HAB', p.id)),
                   # PREVISION
                   int(self.get_rule_value('PREV', p.id)),
                   # % COTIZACION
                   0,
                   # COTIZACION OBLIGATORIA
                   0,
                   # SEGURO CENSATIA
                   int(self.get_rule_value('SECE', p.id)),
                   # % TRABAJO PESADO
                   emp.trabajo_pesado,
                   # COTIZACION TRABAJO PESADO
                   0,
                   # A.P.Vs
                   int(self.get_rule_value('APV', p.id)),
                   # CUENTA AHORRO 2
                   int(self.get_rule_value('AHVOL', p.id)),
                   # INSTITUCION SALUD
                   int(self.get_rule_value('SALUD', p.id)),
                   # PLAN PACTADO
                   0,
                   # COTIZACION 7%
                   0,
                   # ADICIONAL ISAPRE
                   int(self.get_rule_value('ADISA', p.id)),
                   # TOTAL DESCUENTO PREVISIONALES
                   int(self.get_rule_value('TODELE', p.id)),
                   # int(self.get_rule_value('APV', p.id) + self.get_rule_value('AHVOL', p.id) + self.get_rule_value('SALUD', p.id)),
                   # BASE TRIBUTABLE
                   int(self.get_rule_value('TRIBU', p.id)),
                   # IMPUESTO UNICO
                   int(self.get_rule_value('IMPUNI', p.id)),
                   # PRESTAMOS INTERNOS
                   int(self.get_rule_value('PRESTEMP', p.id)),
                   # PRESTAMOS C.C.A.F
                   0,
                   # ADELANTO VIATICO
                   0,
                   # ANTICIPO SUELDO
                   int(self.get_rule_value('ASUE', p.id)),
                   # OTROS DESCUENTOS
                   int(self.get_rule_value('OTDESC', p.id)),
                   # TOTAL DESCUENTOS
                   int(self.get_rule_value('TDE', p.id)),
                   # LIQUIDO A PAGAR
                   int(self.get_rule_value('LIQ', p.id)),
                   # APORTE EMPLEADOR SIS
                   int(self.get_rule_value('SIS', p.id)),
                   # APORTE EMPLEADOR AFC
                   0,
                   # APORTE EMPLEADOR MUTUAL
                   int(self.get_rule_value('MUT', p.id)),
                   # APORTE EMPLEADOR TRABAJO PESADO
                   int(self.get_rule_value('TRABPES', p.id)),
                   int(self.get_rule_value('HAB', p.id) + self.get_rule_value('SIS', p.id) + self.get_rule_value('MUT', p.id) + self.get_rule_value('TRABPES', p.id)),
                   ]
            writer.writerow(row)
        txtFile.close()
        data = base64.encodestring(open(path, 'r').read())
        attach_vals = {'name':fname, 'datas':data, 'datas_fname':fname}
        doc_id = self.env['ir.attachment'].create(attach_vals)
        res['type'] = 'ir.actions.act_url'
        res['target'] = 'new'
        res['url'] = "web/content/?model=ir.attachment&id="+str(doc_id.id)+"&filename_field=datas_fname&field=datas&download=true&filename="+str(doc_id.name)
        return res
