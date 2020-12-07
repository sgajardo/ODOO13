import base64
import csv
import io

from odoo import models
from odoo.exceptions import ValidationError


class HrRemunerationReportWizard(models.TransientModel):
    _inherit = 'hr.remuneration.report.wizard'

    def print_txt(self):
        payslips = self.env['hr.payslip'].search([
            ('date_to', '>=', self.start_date),
            ('date_from', '<=', self.end_date),
            ('contract_id.account_analytic_account_id', '=?', self.account_analytic_account_id.id)
        ])
        if not payslips:
            raise ValidationError('No existen recibos de pago validados para este periodo')
        fname = 'odoo-informe-remuneracion-%s.csv' % self.end_date.strftime('%m-%d')

        txt_file = io.StringIO()
        writer = csv.writer(txt_file, delimiter=str(self.type_delimitador), quoting=csv.QUOTE_NONE)
        row = ['RUT', 'NOMBRE', 'CENTRO COSTOS', 'AFP', 'SALUD', 'CARGO', 'DIAS', 'S. BASE', 'AJUSTE LEY SUELDO BASE', 'DESCUENTO DIAS NO TRABAJADOS', 'DESCUENTO ATRASOS',
               'S. MES', 'GRATIFICACION LEGAL', 'No. HORAS EXTRAS (50%)', 'MONTO HORAS EXTRAS 50%', 'No. HORAS EXTRAS (100%)', 'MONTO HORAS EXTRAS 100%',
               'BONO DE PRODUCCION', 'COMISIONES', 'SEMANA CORRIDA', 'AGUINALDO DE FIESTAS PATRIAS', 'AGUINALDO DE NAVIDAD', 'BONO TURNO', 'BONO DESEMPEÑO',
               'BONO INCENTIVOS MINEROS', 'BONO RIESGO', 'BONO SUPERVISION (10%)', 'BONO ZONA (10%)', 'OTROS BONOS', 'HIGIENE', 'RESPONSABILIDAD Y COMPROMISO', 'COSTO',
               'ESTANDAR', 'VENTAS', 'RECLAMOS CLIENTES', 'PRODUCCION', 'CUMPLIMIENTO', 'HORAS DOMINGO', 'TRABAJO PESADO', 'OTROS IMPONIBLES', 'TOTAL IMPONIBLE',
               'ASIGNACION FAMILIAR', 'ASIGNACION FAMILIAR RETROACTIVA', 'COLACION', 'MOVILIZACION', 'VIATICO', 'OTROS NO IMPONIBLE', 'TOTAL HABERES', 'COTIZACION AFP',
               'SEGURO CESANTIA TRABAJADOR', 'AHORRO PREVISIONAL VOLUNTARIO', 'SALUD', 'ADICIONAL ISAPRE', 'IMPUESTO UNICO', 'ANTICIPO DE SUELDO', 'ANTICIPO VIATICO',
               'ANTICIPO DE AGUINALDO', 'PRESTAMO EMPRESA', 'CREDITO CAJA COMPENSACION', 'PRESTAMO C.C.A.F', 'DESCUENTO DENTAL CCAF', 'DESCUENTO SEGURO DE VIDA CCAF',
               'DESCUENTOS POR LEASING', 'OTROS DESCUENTOS CCAF', 'CUENTA 2 (AHORRO VOLUNTARIO)', 'OTROS DESCUENTOS', 'TOTAL DECUENTOS', 'ALCANCE LIQUIDO',
               'SEGURO CESANTIA APORTE EMPRESA', 'SIS APORTE EMPRESA', 'MUTUAL SEGURIDAD', 'SEGURO COMPLEMENTARIO', 'TOTAL COSTO EMPRESA']
        writer.writerow(row)

        for p in payslips:
            emp = p.employee_id
            complete_name = '%s %s %s %s' % (emp.last_name and emp.last_name or '', emp.mothers_name and emp.mothers_name or '', emp.first_name and emp.first_name or '', emp.middle_name and emp.middle_name or '')

            row = [
                emp.identification_id, complete_name, emp.contract_id.account_analytic_account_id.name or '',
                # AFP
                emp.afp_id.display_name if not emp.no_afp and emp.afp_id else '',
                # Salud
                emp.isapre_id.display_name if not emp.no_salud and emp.isapre_id else '',
                # Cargo
                emp.contract_id.job_id.display_name or '',
                # Dias
                int(self.get_total_worked_days(p)),
                # Sueldo Base
                int(self.get_rule_value('SUELDO', p.id)),
                # Ajuste de ley Sueldo Base
                int(self.get_rule_value('ALSB', p.id)),
                # Descuento días no trabajados
                int(self.get_rule_value('DDNT', p.id)),
                # Descuento atrasos
                int(self.get_rule_value('DSCAT', p.id)),
                # Sueldo del mes (Base menos DDNT)
                int(self.get_rule_value('SUELDO', p.id)) + int(self.get_rule_value('DDNT', p.id)),
                # Gratificación legal
                int(self.get_rule_value('GRAT', p.id)),
                # No. Horas Extras 50%
                int(self.get_input_value('HEX', p.id)),
                # Monto Horas Extras 50%
                int(self.get_rule_value('HEX', p.id)),
                # No. Horas Extras 100%
                int(self.get_input_value('HEX100', p.id)),
                # Monto Horas Extras 100%
                int(self.get_rule_value('HEX100', p.id)),
                # BONO DE PRODUCCION
                int(self.get_rule_value('PROD', p.id)),
                # COMISIONES
                int(self.get_rule_value('COMI', p.id)),
                # SEMANA CORRIDA
                int(self.get_rule_value('SEMC', p.id)),
                # AGUINALDO DE FIESTAS PATRIAS
                int(self.get_rule_value('AGUI', p.id)),
                # AGUINALDO DE NAVIDAD
                int(self.get_rule_value('AGUIN', p.id)),
                # BONO TURNO
                int(self.get_rule_value('BTURN', p.id)),
                # BONO DESEMPEÑO
                int(self.get_rule_value('BDESEMP', p.id)),
                # BONO INCENTIVOS MINEROS
                int(self.get_rule_value('BINCM', p.id)),
                # BONO RIESGO
                int(self.get_rule_value('BRIESG', p.id)),
                # BONO SUPERVISION (10%)
                int(self.get_rule_value('BSUP10', p.id)),
                # BONO ZONA (10%)
                int(self.get_rule_value('BZON10', p.id)),
                # OTROS BONOS
                int(self.get_rule_value('OBONOS', p.id)),
                # HIGIENE
                int(self.get_rule_value('HIG', p.id)),
                # RESPONSABILIDAD Y COMPROMISO
                int(self.get_rule_value('RYC', p.id)),
                # COSTO
                int(self.get_rule_value('COS', p.id)),
                # ESTANDAR
                int(self.get_rule_value('EST', p.id)),
                # VENTAS
                int(self.get_rule_value('VEN', p.id)),
                # RECLAMOS CLIENTES
                int(self.get_rule_value('REC', p.id)),
                # PRODUCCION
                int(self.get_rule_value('PRO', p.id)),
                # CUMPLIMIENTO
                int(self.get_rule_value('CUM', p.id)),
                # HORAS DOMINGO
                int(self.get_rule_value('HXD', p.id)),
                # TRABAJO PESADO
                int(self.get_rule_value('TRABPES', p.id)),
                # OTROS IMPONIBLES
                int(self.get_rule_value('BONO', p.id)),
                # TOTAL IMPONIBLE
                int(self.get_rule_value('TOTIM', p.id)),
                # ASIGNACION FAMILIAR
                int(self.get_rule_value('ASIGFAM', p.id)),
                # ASIGNACION FAMILIAR RETROACTIVA
                int(self.get_rule_value('ASFR', p.id)),
                # COLACION
                int(self.get_rule_value('COL', p.id)),
                # MOVILIZACION
                int(self.get_rule_value('MOV', p.id)),
                # VIATICO
                int(self.get_rule_value('VIASAN', p.id)),
                # OTROS NO IMPONIBLE
                int(self.get_rule_value('OTRONOIMP', p.id)),
                # TOTAL HABERES
                int(self.get_rule_value('HAB', p.id)),
                # COTIZACION AFP
                int(self.get_rule_value('AFP', p.id)),
                # SEGURO CESANTIA TRABAJADOR
                int(self.get_rule_value('SECE', p.id)),
                # AHORRO PREVISIONAL VOLUNTARIO
                int(self.get_rule_value('APV', p.id)),
                # SALUD
                int(self.get_rule_value('SALUD', p.id)),
                # ADICIONAL ISAPRE
                int(self.get_rule_value('ADISA', p.id)),
                # IMPUESTO UNICO
                int(self.get_rule_value('IMPUNI', p.id)),
                # ANTICIPO DE SUELDO
                int(self.get_rule_value('ASUE', p.id)),
                # ANTICIPO VIATICO
                int(self.get_rule_value('DVIAT', p.id)),
                # ANTICIPO DE AGUINALDO
                int(self.get_rule_value('ANTAGUI', p.id)),
                # PRESTAMO EMPRESA
                int(self.get_rule_value('PRESTEMP', p.id)),
                # CREDITO CAJA COMPENSACION
                int(self.get_rule_value('CREDCAJCOMP', p.id)),
                # PRESTAMO C.C.A.F
                int(self.get_rule_value('PRESTEMPCCAF', p.id)),
                # DESCUENTO DENTAL CCAF
                int(self.get_rule_value('DDCCAF', p.id)),
                # DESCUENTO SEGURO DE VIDA CCAF
                int(self.get_rule_value('DSVCCAF', p.id)),
                # DESCUENTOS POR LEASING
                int(self.get_rule_value('DLEASING', p.id)),
                # OTROS DESCUENTOS CCAF
                int(self.get_rule_value('DESCCAF', p.id)),
                # CUENTA 2 (AHORRO VOLUNTARIO)
                int(self.get_rule_value('AHVOL', p.id)),
                # OTROS DESCUENTOS
                int(self.get_rule_value('OTDESC', p.id)),
                # TOTAL DECUENTOS
                int(self.get_rule_value('TDE', p.id)),
                # ALCANCE LIQUIDO
                int(self.get_rule_value('LIQ', p.id)),
                # SEGURO CESANTIA APORTE EMPRESA
                int(self.get_rule_value('SECEEMP', p.id)),
                # SIS APORTE EMPRESA
                int(self.get_rule_value('SIS', p.id)),
                # MUTUAL SEGURIDAD
                int(self.get_rule_value('MUT', p.id)),
                # SEGURO COMPLEMENTARIO
                int(self.get_rule_value('SECOMP', p.id)),
                # TOTAL COSTO EMPRESA
                int(self.get_rule_value('HAB', p.id) + self.get_rule_value('SIS', p.id) + self.get_rule_value('MUT', p.id) + self.get_rule_value('TRABPES', p.id)),
            ]
            writer.writerow(row)
        data = base64.b64encode(txt_file.getvalue().encode('utf-8'))
        txt_file.close()
        attach_vals = {'name': fname, 'datas': data, 'store_fname': fname}
        attachment = self.env['ir.attachment'].create(attach_vals)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new'
        }
