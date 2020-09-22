import base64
import csv
import io
import random
import unicodedata

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

dicc_salud = {}
dicc_afp = {}


class HrPreviredReportWizard(models.TransientModel):
    _name = 'hr.previred.report.wizard'
    _description = 'Informe Previred'

    @api.model
    def _get_default_start_date(self):
        return fields.Date.today() + relativedelta(day=1)

    @api.model
    def _get_default_end_date(self):
        return fields.Date.today() + relativedelta(months=1, day=1, days=-1)

    start_date = fields.Date('Fecha Inicio', default=_get_default_start_date, help='Ingrese la fecha inicio del periodo')
    end_date = fields.Date('Fecha Fin', default=_get_default_end_date, help='Ingrese la fecha fin del periodo')
    encabezado = fields.Boolean("Imprimir Encabezado (CSV) Solo Pruebas")
    muestra_nombres = fields.Boolean("Muestra AFP/SALUD")
    correcciones = fields.Boolean("Utilizar Correcciones", default=True)
    centro_costo_id = fields.Many2one('hr.centroscostos', 'Centros Costos', ondelete="restrict")

    type_delimitador = fields.Selection([(';', 'Punto y Coma'), (',', 'Coma')], 'Tipo de Delimitador', size=1, default=';')

    @api.onchange('start_date')
    def _onchange_dates(self):
        if self.start_date:
            self.end_date = self.start_date + relativedelta(months=1, day=1, days=-1)

    def get_worked_days(self, code=None, payslip_id=None, emp_id=None, date_from=None, date_to=None):
        sql = """select coalesce(sum(number_of_days),0) from hr_payslip_worked_days as p
                 left join hr_payslip as r on r.id = p.payslip_id
                 left join hr_work_entry_type as w on w.id = p.work_entry_type_id
                 where 1 = 1"""

        if payslip_id:
            sql += ' and r.id = %s' % payslip_id

        if emp_id:
            sql += ' and r.employee_id = %s' % emp_id

        if date_from:
            sql += ' and r.date_from >= %s' % date_from

        if date_to:
            sql += ' and r.date_to <= %s' % date_to

        if code:
            sql += " and w.code = '%s'" % code

        self.env.cr.execute(sql)

        results = self.env.cr.fetchone()

        if results:
            return results[0]
        else:
            return 0

    def cot_salud(self, value):
        value1 = str(value).replace(".", ",")
        pos = value1.find(',')
        if pos == 1:
            value2 = "000" + value1
            return value2
        else:
            return value1

    def get_rule_value(self, code=None, payslip_id=None, emp_id=None, date_from=None, date_to=None):

        sql = """select COALESCE(sum(pl.total),0) from hr_payslip_line as pl
                 left join hr_payslip as p on pl.slip_id = p.id
                 where 1 = 1"""

        if payslip_id:
            sql += ' and p.id = %s' % payslip_id

        if emp_id:
            sql += ' and p.employee_id = %s' % emp_id

        if date_from:
            sql += ' and p.date_from >= %s' % date_from

        if date_to:
            sql += ' and p.date_to <= %s' % date_to

        if code:
            sql += " and pl.code = '%s'" % code

        self.env.cr.execute(sql)

        results = self.env.cr.fetchone()

        if results:
            return results[0]
        else:
            return 0

    def get_input_value(self, code=None, payslip_id=None, emp_id=None, date_from=None, date_to=None):

        sql = """select COALESCE(sum(pl.amount),0) from hr_payslip_input as pl
                 left join hr_payslip as p on pl.payslip_id = p.id
                 where 1 = 1"""

        if payslip_id:
            sql += ' and p.id = %s' % payslip_id

        if emp_id:
            sql += ' and p.employee_id = %s' % emp_id

        if date_from:
            sql += ' and p.date_from >= %s' % date_from

        if date_to:
            sql += ' and p.date_to <= %s' % date_to

        if code:
            sql += " and pl.code = '%s'" % code

        self.env.cr.execute(sql)

        results = self.env.cr.fetchone()

        if results:
            return results[0]
        else:
            return 0

    def print_txt(self):
        holidays = self.env['hr.leave'].search([('holiday_status_id.move_type_id', '!=', False),  # y sólo las que tengan movimientos involucrados
                                                ('date_from', '<=', self.end_date),  # dentro del periodo
                                                ('date_to', '>=', self.start_date)])
        res = {}
        gender_map = {'male': 'M', 'female': 'F', 'other': 'O'}
        payslips = self.env['hr.payslip'].search([
            ('state', 'not in', ['draft', 'verify', 'cancel']),
            ('date_to', '>=', self.start_date),
            ('date_from', '<=', self.end_date)
        ])
        if not payslips:
            raise ValidationError(_('No existen recibos de pago validados para este periodo'))
        if self.centro_costo_id:
            payslips = payslips.filtered(lambda p: p.employee_id.centro_costo_id == self.centro_costo_id)
        if not payslips:
            raise ValidationError(_('No existen recibos de pago validados para éste periodo y el centro de costo seleccionado.'))
        ran = random.randint(1000, 9000)
        fname = 'odoo_previred_%s_%s.txt' % (self.end_date, ran)

        ccaf_list = []
        prestamo_list = []

        if self.encabezado:
            fname = 'odoo_prueba_previred_%s_%s.csv' % (self.end_date, ran)

        txt_file = io.StringIO()

        fonasa_sum = 0
        mutual_sum = 0

        ccaf_valor = 0
        ccaf_credito = 0
        ccaf_sum = 0
        salario_liquido = 0

        # Fijamos el delimitador por ;
        self.type_delimitador = ';'
        writer = csv.writer(txt_file, delimiter=str(self.type_delimitador), quoting=csv.QUOTE_NONE)

        asignacion_familiar = 0

        row1 = [str(i) for i in range(1, 106)]

        row2 = ['RUT', 'DV', 'Apellido Paterno', 'Apellido Materno', 'Nombres', 'Sexo', 'Nacionalidad',
                'tipo pago', 'periodo rem Desde', 'periodo rem Hasta', 'Régimen Previsional', 'Tipo de Trabajador',
                'Días Trabajados', 'Tipo de Linea', 'Código Movimiento de Personal', 'Fecha Desde', 'Fecha Hasta', 'Tramo Asigna. Familiar',
                '# Cargas Simples', '# Cargas Maternales', '# Cargas Inválidas', 'Asignación Familiar', 'Asignación Familiar Retroactiva',
                'Reintegro Cargas Fam.', 'Solicitud Sub. Trabajador Joven', 'Código de la AFP', 'Renta Imponible AFP', 'Cotización Obligatoria AFP',
                'Aporte Seguro Invalidez y Sobrev. Futuro (SIS)', 'Cuenta de Ahorro Voluntario AFP', 'Renta Imp. Sust. AFP', 'Tasa Pactada (Sustitutivo)',
                'Aporte Indemn. (Sustitutivo)', 'Nº Periodos (Sustitutivos)', 'Período desde (Sustitutivo) ', 'Período Hasta (Sustitutivo)',
                'Puesto de Trabajo pesado', '% Cotización Trabajo Pesado', 'Cotización Trabajo Pesado', 'Cod. De la Institución APVI',
                'Número de Contrato APVI', 'Forma de Pago APVI', 'Cotización APVI', 'Cotización Depósitos Convenidos', 'Código Inst. Autorizada APVC',
                'Número de Contrato APVC', 'Forma de Pago APVC', 'Cotización Trabajador APVC', 'Cotización Empleador APVC',
                'Rut Afiliado Voluntario', 'DV Afiliado Voluntario', 'Apellido Paterno', 'Apellido Materno', 'Nombres', 'Código Movimiento de Personal',
                'Fecha Desde', 'Fecha Hasta', 'Código de la AFP', 'Monto de Capitalización Voluntaria', 'Monto Ahorro Voluntario', 'Número de períodos de Cotización',
                'Código Ex Caja Régimen', 'Tasa Cotización Ex Caja Previsión', 'Renta Imponible IPS. ISL', 'Cotización Obligatoria IPS', 'Renta Imponible Desahucio',
                'Código Ex Caja Régimen Desahucio', 'Tasa Cotización Desahucio Ex Cajas de Previsión', 'Cotización Desahucio', 'Cotización Fonasa',
                'Cotización Acc. Trabajo (ISL)', 'Bonificación Ley 15.386', 'Descuento por Cargas Familiares del ISL', 'Bonos Gobierno',
                'Código Isapre', 'Número del Fun', 'Renta Imponible Isapre', 'Moneda del Plan Pactado Isapre', 'Cotización Pactada',
                'Cotización Obligatoria Isapre', 'Cotización Adicional Voluntaria', 'Monto GES (Futuro)', 'Código CCAF', 'Renta Imponible CCAF',
                'Créditos Personales CCAF', 'Descuento Dental CCAF', 'Descuentos por Leasing (Programa de Ahorro)', 'Descuentos por Seguro de Vida CCAF',
                'Otros descuentos CCAF', 'Cotización a CCAF de no Afiliados a Isapre', 'Descuento Cargas Familiares CCAF', 'Otros Descuentos CCAF 1 (Futuro)',
                'Otros Descuentos CCAF 2 (Futuro)', 'Bonos Gobierno (Futuro)', 'Código de Sucursal (Futuro)', 'Código Mutual', 'Renta Imponible Mutual',
                'Cotización Accidente del Trabajo', 'Sucursal para Pago Mutual', 'Renta Imponible Seguro de Cesantía', 'Aporte Trabajador Seguro de Cesantía',
                'Aporte Empleador Seguro Cesantía', 'Rut Pagadora Subsidio', 'DV Pagadora Subsidio', 'Centro de Costos-Sucursal-Agencia-Obra-Región']

        if self.encabezado:
            writer.writerow(row1)
            writer.writerow(row2)

        for p in payslips:
            tope_imponible_sc = int(round(p.stats_id.tope_imponible_seguro_cesantia * p.stats_id.uf))
            emp = p.employee_id
            nac = emp.country_id and emp.country_id.code != 'CL' and 1 or 0
            complete_name = '%s %s' % (emp.first_name or '', emp.middle_name or '')
            if not emp.identification_id:
                raise ValidationError(_('El empleado %s no tiene número de RUT.') % emp.display_name)
            rut_split = emp.identification_id.split('-')
            tope_afp = round(p.stats_id.tope_imponible_afp * p.stats_id.uf)
            total_imponible = self.get_rule_value('TOTIM', p.id)
            if len(rut_split) < 2:
                raise ValidationError(_('RUT de empleado %s mal formateado: %s') % (emp.display_name, emp.identification_id))

            centro_costo = 0

            if emp.tiene_centro_costo:
                centro_costo = int(emp.centro_costo_id.name)

            # Calculamos todos los movimientos de tipo ausencia
            movimientos = [{
                'mov': h.holiday_status_id.move_type_id.code,
                'inicio': h.date_from.date() if h.date_from and h.date_from.date() > self.start_date else self.start_date,
                'fin': h.date_to.date() if h.date_to and h.date_to.date() < self.end_date else self.end_date
            } for h in holidays.filtered(lambda s: s.employee_id == emp)]
            # Calculamos todos los movimientos referente a contratos
            # for contract in contracts.filtered(lambda c: c.employee_id == emp).sorted('date_start'):
            #     if contract.date_start < self.start_date and (not contract.date_end or contract.date_end > self.end_date):
            #         # Si el contrato es de antes del periodo y termina luego del periodo o es indefinido, continuamos con el siguiente
            #         continue
            #     elif contract.date_end <= self.end_date:
            #         # Si el contrato termina en este periodo, es un movimiento "Retiro", código 2
            #         movimientos.append({
            #             'mov': '2',
            #             'inicio': contract.date_start if contract.date_start > self.start_date else self.start_date,
            #             'fin': contract.date_end
            #         })
            if not movimientos:
                movimientos.append({'mov': 0, 'inicio': False, 'fin': False})
            dt_start = self.start_date
            fixed_movs = []
            for mov in sorted(movimientos, key=lambda m: m['inicio']):
                if mov['inicio'] and mov['fin']:
                    dt_start_mov = mov['inicio']
                    # Llenamos los vacíos
                    if dt_start < dt_start_mov:
                        fixed_movs.append({
                            'mov': 0,
                            'inicio': dt_start,
                            'fin': dt_start_mov - relativedelta(days=1)
                        })
                else:
                    fixed_movs.append(mov)
                    continue
                # Agregamos el movimiento
                fixed_movs.append(mov)
                # Dejamos la fecha un día después del final del último movimiento que tocamos
                dt_start = mov['fin'] + relativedelta(days=1)
            # Debemos verificar que el último movimiento llegue hasta el final del periodo, sino, agregamos un movimiento 0 para finalizar el periodo
            if fixed_movs[-1]['fin'] and fixed_movs[-1]['fin'] < self.end_date:
                fixed_movs.append({
                    'mov': 0,
                    'inicio': fixed_movs[-1]['fin'] + relativedelta(days=1),
                    'fin': self.end_date
                })
            # Sustituimos los movimientos:
            movimientos = fixed_movs
            for i, mov in enumerate(movimientos):
                last_name = ""
                if emp.last_name:
                    last_name = emp.last_name.replace(" ", '')

                mothers_name = ""
                if emp.mothers_name:
                    mothers_name = emp.mothers_name.replace(" ", '')

                dias_trabajados = relativedelta(mov['fin'] or self.end_date, mov['inicio'] or self.start_date).days + 1
                mes = str(self.start_date)[5:7]
                if dias_trabajados == 28 and mes == '02':
                    dias_trabajados = 30

                # renta_impobible_seguro_cesantia = (int(self.get_rule_value('TOTIM', p.id)) if tope_imponible_sc > int(self.get_rule_value('TOTIM', p.id)) else tope_imponible_sc) if not p.contract_id.type_id.fijo and i == 0 else 0

                renta_impobible_seguro_cesantia = 0
                if tope_imponible_sc > int(self.get_rule_value('TOTIM', p.id)):
                    renta_impobible_seguro_cesantia = int(self.get_rule_value('TOTIM', p.id))
                else:
                    renta_impobible_seguro_cesantia = tope_imponible_sc

                cotizacion_ccaf = int(self.get_rule_value('CAJACOMP', p.id))

                # Buscamos la AFP
                if p.afp_id:
                    afp_codigo = p.afp_id.codigo if not self.muestra_nombres else p.afp_id.name
                else:
                    afp_codigo = emp.afp_id.codigo if not self.muestra_nombres else emp.afp_id.name

                # Buscamos la ISAPRE
                if p.isapre_id:
                    isapre_codigo = int(p.isapre_id.codigo) if not self.muestra_nombres else p.isapre_id.name
                else:
                    isapre_codigo = int(emp.isapre_id.codigo) if not self.muestra_nombres else emp.isapre_id.name

                row = [rut_split[0].replace(".", ''), rut_split[1], elimina_tildes(last_name.replace(" ", '') and last_name.replace(" ", '') or ''), elimina_tildes(mothers_name.replace(" ", '') and mothers_name.replace(" ", '') or ''),
                       elimina_tildes(complete_name), gender_map[emp.gender], nac, 1,
                       # 9,10  periodo rem Desde, periodo rem Desde
                       p.date_from.strftime('%-m%Y'), p.date_to.strftime('%-m%Y'),
                       # 11 - Todos los trabajadores tienen AFP
                       'AFP',
                       # 12 - Tipo de Trabajador
                       # 0 - Activo (No Pensionado)
                       # 1 - Pensionado y Cotiza
                       # 2 - Pensionado y no cotiza
                       # 3 - Activo > 65 años (nunca pensionado)
                       '0' if not emp.pension else emp.tipo_trabajador,
                       # 13 - Días Trabajados
                       dias_trabajados,
                       # 14 - Tipo de Linea
                       # 00 - Línea Principal o Base
                       # 01 - Línea Adicional
                       # 02 - Segundo Contrato
                       # 03 - Movimiento de Personal Afiliado Voluntario
                       '00' if i == 0 else '01',
                       # 15 - Código Movimiento de Personal
                       str(mov['mov']),
                       # 16 - Fecha movimiento desde
                       mov['inicio'].strftime('%d-%m-%Y') if mov['inicio'] else '',
                       # 17 - Fecha movimiento hasta
                       mov['fin'].strftime('%d-%m-%Y') if mov['fin'] else '',
                       # 18 - Tramo Asigna. Familiar
                       # A
                       # B
                       # C
                       # D
                       emp.tramo_asig,
                       # 19 - Cargas Simples
                       int(emp.cant_carga_familiar),
                       # 20 - Cargas Maternales
                       int(emp.cant_carga_familiar_maternal),
                       # 21 - Cargas Inválidas
                       int(emp.cant_carga_familiar_invalida),
                       # 22 - Asignación Familiar
                       int(self.get_rule_value('ASIGFAM', p.id)),
                       # 23 - Asignación Familiar Retroactiva
                       int(self.get_rule_value('ASFR', p.id)),
                       # 24 - Reintegro Cargas Familiar
                       '',
                       # 25 - Solicitud de trabajador Joven
                       'N',
                       # 26 - Código de la AFP
                       afp_codigo,
                       # 27 Renta Imponible AFP
                       int(total_imponible if total_imponible < tope_afp else tope_afp),
                       # 28 Cotización Obligatoria AFP
                       int(self.get_rule_value('PREV', p.id)),
                       # 29 Aporte Seguro Invalidez y Sobrev. Futuro (SIS)
                       int(self.get_rule_value('SIS', p.id)),
                       # 30 Cuenta de Ahorro Voluntario AFP
                       int(self.get_rule_value('AHVOL', p.id)),
                       # 31 Renta Imp. Sust. AFP
                       '0',
                       # 32 Tasa Pactada (Sustitutivo)
                       '0',
                       # 33 Aporte Indemn. (Sustitutivo)
                       '0',
                       # 34 Nº Periodos (Sustitutivos)
                       '0',
                       # 35 Nº Período desde (Sustitutivo)
                       '',
                       # 36 Período Hasta (Sustitutivo)
                       '',
                       # 37 Puesto de Trabajo pesado  ! dame el nombre del cargo del trabajador pesado
                       '',
                       # 38 % Cotización Trabajo Pesado
                       int(emp.trabajo_pesado),
                       # 39 Cotización Trabajo Pesado
                       int(self.get_rule_value('TRABPES', p.id)),
                       # 40 Cod. De la Institución APVI
                       '0',
                       # 41 Número de Contrato APVI
                       '0',
                       # 42 Forma de Pago APVI
                       '0',
                       # 43 Cotización APVI
                       '0',
                       # 44 Cotización Depósitos Convenidos
                       '0',
                       # 45 Código Inst. Autorizada APVC
                       '0',
                       # 46 Número de Contrato APVC
                       '0',
                       # 47 Forma de Pago APVC
                       '0',
                       # 48 Cotización Trabajador APVC
                       '0',
                       # 49 Cotización Empleador APVC
                       '0',
                       # 50 Rut Afiliado Voluntario
                       '',
                       # 51 DV Afiliado Voluntario
                       '',
                       # 52 Apellido Paterno
                       '',
                       # 53 Apellido Materno
                       '',
                       # 54 Nombres
                       '',
                       # 55 Código Movimiento de Personal
                       '0',
                       # 56 Fecha Desde
                       '',
                       # 57 Fecha Hasta
                       '',
                       # 58 Código de la AFP
                       '0',
                       # 59 Monto de Capitalización Voluntaria
                       '0',
                       # 60 Monto Ahorro Voluntario
                       '0',
                       # 61 Número de períodos de Cotización
                       '0',
                       # 62 Código Ex Caja Régimen
                       '0',
                       # 63 Tasa Cotización Ex Caja Previsión
                       '0',
                       # 64 Renta Imponible IPS. ISL
                       int(total_imponible if total_imponible < tope_afp else tope_afp),
                       # 65 Cotización Obligatoria IPS
                       '0',
                       # 66 Renta Imponible Desahucio
                       '0',
                       # 67 Código Ex Caja Régimen Desahucio
                       '0',
                       # 68 Tasa Cotización Desahucio Ex Cajas de Previsión
                       '0',
                       # 69 Cotización Desahucio
                       '0',
                       # 70 Cotización Fonasa ---------------------------------------- Hacer Funcion regla FONASA
                       int(self.get_rule_value('SALUD', p.id) - cotizacion_ccaf) if emp.isapre_id.name == 'FONASA' else 0,
                       # 71 Cotización Acc. Trabajo (ISL)
                       '0',
                       # 72 Bonificación Ley 15.386
                       '0',
                       # 73 Descuento por Cargas Familiares del ISL
                       int(self.get_rule_value('ASIGFAM', p.id)) if cotizacion_ccaf else 0,
                       # 74 Bonos Gobierno
                       '0',
                       # 75 Código Isapre
                       isapre_codigo,
                       # 76 Número del Fun
                       int(emp.isapre_fun),
                       # 77 Renta Imponible Isapre ----------------------   buscar la isapre
                       int(total_imponible if total_imponible < tope_afp else tope_afp) if not emp.isapre_id.name == 'FONASA' else 0,
                       # 78 Moneda del Plan Pactado Isapre
                       '1' if emp.isapre_id.codigo == '07' else '2',
                       # 79 Cotización Pactada
                       self.cot_salud(emp.isapre_cotizacion_uf) if not emp.isapre_id.name == 'FONASA' else 0,
                       # 80 Cotización Obligatoria Isapre ------------------------ hacer funcion por la UF
                       int(self.get_rule_value('SALUD', p.id)) if not emp.isapre_id.name == 'FONASA' else 0,
                       # 81 Cotización Adicional Voluntaria
                       int(self.get_rule_value('ADISA', p.id)),
                       # 82 Monto GES (Futuro)
                       '0',
                       # 83 Código CCAF
                       str(p.stats_id.ccaf_id.codigo or '') if emp.isapre_id.name == 'FONASA' else 0,
                       # -----------------------------------------
                       # 84 Renta Imponible CCAF
                       int(total_imponible if total_imponible < tope_afp else tope_afp),
                       # 85 Créditos Personales CCAF
                       int(self.get_rule_value('PRESTEMPCCAF', p.id)) if i == 0 else 0,
                       # 86 Descuento Dental CCAF
                       int(self.get_rule_value('DDCCAF', p.id)),
                       # 87 Descuentos por Leasing (Programa de Ahorro)
                       int(self.get_rule_value('DLEASING', p.id)),
                       # 88 Descuentos por Seguro de Vida CCAF
                       int(self.get_rule_value('DSVCCAF', p.id)),
                       # 89 Otros descuentos CCAF
                       int(self.get_rule_value('DESCCAF', p.id)),
                       # 90 Cotización a CCAF de no Afiliados a Isapre. ----------------------------
                       cotizacion_ccaf if emp.isapre_id.name == 'FONASA' else 0,
                       # int(self.get_rule_value('AFP', p.id) * 0.6 / 100),  # el 0.6 sale del indicador
                       # 91 Descuento Cargas Familiares CCAF
                       '0',
                       # 92 Otros Descuentos CCAF 1 (Futuro)
                       '0',
                       # 93 Otros Descuentos CCAF 2 (Futuro)
                       '0',
                       # 94 Bonos Gobierno (Futuro)
                       '0',
                       # 95 Código de Sucursal (Futuro)
                       '0',
                       # 96 Código Mutual
                       str(p.stats_id.mutualidad_id.codigo) if p.stats_id.mutualidad_id else '0',
                       # 97 Renta Imponible Mutual
                       int(total_imponible if total_imponible < tope_afp else tope_afp),
                       # 98 Cotización Accidente del Trabajo
                       int(self.get_rule_value('MUT', p.id)) if i == 0 else 0,
                       # 99 Sucursal para Pago Mutual
                       '0',
                       # 100 Renta Imponible Seguro de Cesantía
                       # renta_impobible_seguro_cesantia,  # Revisr y no usar afp
                       renta_impobible_seguro_cesantia if i == 0 else 0,
                       # 101 Aporte Trabajador Seguro de Cesantía
                       int(self.get_rule_value('SECE', p.id)) if i == 0 else 0,
                       # 102 Aporte Empleador Seguro Cesantía
                       int(self.get_rule_value('SECEEMP', p.id)) if i == 0 else 0,
                       # 103 Rut Pagadora Subsidioa
                       '0',
                       # 104 DV Pagadora Subsidio
                       '',
                       # 105 Centro de Costos,Sucursal,Agencia,Obra,Región
                       centro_costo]
                # Validamos que los días trabajados no pase de 31 dias
                if emp.tipo_trabajador == '2':
                    row[26] = 0
                    row[99] = 0

                # Corregimos la AFP de los pensionados
                if row[12] > 30:
                    row[12] = 30

                if row[25] == False:
                    row[25] = 0

                if self.encabezado:
                    row[78] = str(row[78]).replace(',', '.')

                if row[84] > 0:
                    row[82] = str(p.stats_id.ccaf_id.codigo)

                # Función para remplazar valores con problemas del 10 columnas
                obj_hr_payslip_run = self.env['hr.payslip.run'].search([('date_start', '=', self.start_date)], limit=1)
                if self.correcciones and obj_hr_payslip_run:
                    if obj_hr_payslip_run.corre_ids:
                        for corr in obj_hr_payslip_run.corre_ids:
                            rut = corr.employee_id.identification_id.replace(".", "")
                            rut105 = row[0] + "-" + row[1]
                            if rut == rut105:
                                colum105 = int(corr.colum105) - 1
                                valor = corr.valor
                                if '.' in str(valor):
                                    valor = int(str(valor).replace(".0", ""))
                                row[colum105] = valor

                # Funcion que Inserta el Resultado de la descarga
                if emp.isapre_id:
                    var = emp.isapre_id.name
                    if row[13] == '00':
                        valor = int(self.get_rule_value('SALUD', p.id)) + int(self.get_rule_value('ADISA', p.id))

                        if var not in dicc_salud:
                            dicc_salud[var] = valor
                        else:
                            dicc_salud[var] = valor + dicc_salud[var]

                if emp.afp_id:
                    var_afp = emp.afp_id.name
                    if row[13] == '00':
                        valor_afp = int(self.get_rule_value('PREV', p.id)) + int(self.get_rule_value('SIS', p.id))

                        if var_afp not in dicc_afp:
                            dicc_afp[var_afp] = valor_afp
                        else:
                            dicc_afp[var_afp] = valor_afp + dicc_afp[var_afp]

                if row[13] == '00':
                    asignacion_familiar = asignacion_familiar + int(self.get_rule_value('ASIGFAM', p.id))
                    fonasa_sum = fonasa_sum + row[69]

                    mutual_sum = mutual_sum + row[97]

                    ccaf_valor = ccaf_valor + row[89]
                    ccaf_credito = ccaf_credito + row[84]
                    ccaf_sum = ccaf_sum + row[84] + row[89]
                    salario_liquido = salario_liquido + int(self.get_rule_value('LIQ', p.id))

                if row[84]:
                    ccaf_list.append((0, 0, {
                        'employee_id': emp.id,
                        'amount': row[84]
                    }))
                if self.get_rule_value('PRESTEMP', p.id):
                    prestamo_list.append((0, 0, {
                        'employee_id': emp.id,
                        'amount': self.get_rule_value('PRESTEMP', p.id)
                    }))
                writer.writerow(row)

        # if self.encabezado:
        #     txt_file.write('\n')
        #     txt_file.write('\n')
        #     txt_file.write("AFP" + '\n')

        # suma_afp = 0
        # for y in dicc_afp:
        #     row_afp = str(y) + "," + str(dicc_afp[y]) + '\n'
        #     suma_afp = suma_afp + 1
        #     if self.encabezado:
        #         txt_file.write(row_afp)
        # if self.encabezado:
        #     txt_file.write("Total" + "," + str(suma_afp) + '\n')
        #     txt_file.write('\n')

        # suma_salud = 0
        # if self.encabezado:
        #     txt_file.write('\n')
        #     txt_file.write("SALUD"+'\n')
        # for x in dicc_salud:
        #     row_isapre = str(x) + "," + str(dicc_salud[x])+'\n'
        #     suma_salud = suma_salud + 1
        # if self.encabezado:
        #         txt_file.write(row_isapre)
        # if self.encabezado:
        #     txt_file.write("Total" + "," + str(suma_salud) + '\n')
        #     txt_file.write('\n')
        #     txt_file.write("Asignación Familiar (IPS)"  +  "," + str(asignacion_familiar) + '\n')

        data = base64.b64encode(txt_file.getvalue().encode('utf-8'))
        txt_file.close()
        attach_vals = {'name': fname, 'datas': data, 'store_fname': fname}
        attachment = self.env['ir.attachment'].create(attach_vals)
        res = {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new'
        }
        if self.env.context.get('payslip_run_id'):
            # Guardamos mensaje en procesamiento de nómina (si se llamó el wizard desde ahí)
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context['payslip_run_id'])
            payslip_run.mutual = mutual_sum
            payslip_run.ccaf_valor = ccaf_valor
            payslip_run.ccaf_credito = ccaf_credito
            payslip_run.ccaf = ccaf_sum
            payslip_run.salario_liquido = salario_liquido
            payslip_run.message_post(body=_('Se imprimió Formato Previred 105: %s') % salario_liquido)
            # Recalculamos listado AFP
            payslip_run.afp_ids.unlink()
            payslip_run.afp_ids = [(0, 0, {
                'nombre': afp,
                'monto': dicc_afp[afp],
            }) for afp in dicc_afp]
            # Recalculamos listado Isapre
            payslip_run.isapre_ids.unlink()
            payslip_run.isapre_ids = [(0, 0, {
                'nombre': salud,
                'monto': dicc_salud[salud],
            }) for salud in dicc_salud if salud != 'FONASA']
            # Recalculamos listado Fonasa
            payslip_run.fonasa_ids.unlink()
            payslip_run.fonasa_ids = [(0, 0, {
                'nombre': 'FONASA',
                'monto': fonasa_sum
            }), (0, 0, {
                'nombre': 'Asignación Familiar (IPS)',
                'monto': -asignacion_familiar
            })]
            # Recalculamos listado CCAF
            payslip_run.ccaf_ids.unlink()
            payslip_run.ccaf_ids = ccaf_list
            # Recalculamos listado Préstamos Empresa
            payslip_run.pres_emp_ids.unlink()
            payslip_run.pres_emp_ids = prestamo_list
        return res


def elimina_tildes(cadena):
    return ''.join((c for c in unicodedata.normalize('NFD', cadena) if unicodedata.category(c) != 'Mn'))
