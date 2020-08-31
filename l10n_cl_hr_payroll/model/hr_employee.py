from calendar import monthrange
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _get_region_domain(self):
        """ Devuelve dominio con regiones chilenas """
        return [('country_id', '=', self.env.ref('base.cl').id), ('type', '=', 'view')]

    first_name = fields.Char('Primer Nombre')
    last_name = fields.Char('Primer Apellido')
    middle_name = fields.Char('Segundo Nombre', help='Employees middle name')
    mothers_name = fields.Char('Segundo Apellido', help='Employees mothers name')
    resource_calendar_id = fields.Many2one('resource.calendar', related='contract_id.resource_calendar_id', default=lambda self: self.env.ref('l10n_cl_hr_payroll.hr_resource_monthly', raise_if_not_found=False))
    region_id = fields.Many2one('res.country.state', 'Región', domain=_get_region_domain)
    city_id = fields.Many2one('res.country.state.city', 'Ciudad')
    address = fields.Char('Dirección')
    calculate_payroll = fields.Boolean('Cálculo de Nómina')
    acc_number = fields.Char('Cuenta Bancaria', related='bank_account_id.acc_number')
    bank_id = fields.Many2one('res.bank', 'Banco', related='bank_account_id.bank_id', ondelete='restrict')
    # leave_ids = fields.One2many('hr.holidays', 'employee_id', 'Ausencias')
    vacations_count = fields.Float('Vacaciones', compute='_compute_vacations_count', help='Vacaciones pendientes.')
    # leaves_on_month = fields.Float('Ausencias del mes', compute='_compute_leaves_month')
    hired = fields.Boolean('Contratado', compute='_compute_hired', search='_search_hired')
    last_payroll = fields.Char('Última nómina', compute='_compute_last_payroll')

    no_salud = fields.Boolean('No Tiene Salud')
    no_afp = fields.Boolean('No paga AFP')
    file_afp_name = fields.Char('Nombre Adjunto')
    file_afp = fields.Binary('Adjunto', copy=False, help='Comprobante AFP')

    tramo_asig = fields.Selection(
        [('A', 'A'),
         ('B', 'B'),
         ('C', 'C'),
         ('D', 'D')],
        'Tramo de Asignación Familiar', size=1, default='D')

    tipo_trabajador = fields.Selection(
        [('0', 'Activo'),
         ('1', 'Pensionado y Cotiza'),
         ('2', 'Pensionado y No Cotiza'),
         ('3', 'Activo > 65 años')],
        'Tipo de Trabajador', size=1, default='0')

    haberes_descuentos_ids = fields.One2many('hr.hd', 'employee_id', 'Asignaciones y Descuentos')
    horas_extras_ids = fields.One2many('hr.he', 'employee_id', string='Horas Extras')
    rh_cargas_ids = fields.One2many('l.cargas', 'employee_id', string='Cargas')
    cant_carga_familiar = fields.Integer('Carga Familiar Simple', compute="_compute_cargas")
    cant_carga_familiar_maternal = fields.Integer('Carga Familiar Simple', compute="_compute_cargas")
    cant_carga_familiar_invalida = fields.Integer('Carga Familiar Simple', compute="_compute_cargas")
    cantidad_de_carga = fields.Integer('Cantidad de Cargas', default=0)
    private_role = fields.Boolean('Rol Privado', default=False)

    afp_id = fields.Many2one('hr.afp', 'AFP', ondelete="restrict")
    isapre_id = fields.Many2one('hr.isapre', 'Salud', ondelete="restrict")
    isapre_cotizacion_uf = fields.Float("Plan Salud (UF)", digits=(3, 4))
    isapre_moneda = fields.Selection((('uf', 'UF'), ('clp', 'Pesos')), 'Moneda Isapre', default="uf")
    isapre_fun = fields.Char('Número de FUN', help="Indicar N° Contrato de Salud a Isapre")
    trabajo_pesado = fields.Selection(
        [('0', '0%'),
         ('2', '2%'),
         ('4', '4%')],
        'Cotización trabajo pesado', size=1, default='0')

    tiene_centro_costo = fields.Boolean('Centro de Costo')
    centro_costo_id = fields.Many2one('hr.centroscostos', 'Centros Costos', ondelete="restrict")
    # full_name = fields.Char(compute='full_name_func')
    aporte_voluntario = fields.Float('Ahorro Previsional Voluntario (APV)', help='Ahorro Previsional Voluntario (APV)')

    aporte_voluntario_moneda = fields.Selection((('uf', 'UF'), ('clp', 'Pesos')), 'Moneda Aporte Voluntario', default='uf')
    seguro_complementario = fields.Float('Cotización UF', help='Seguro Complementario')
    seguro_complementario_moneda = fields.Selection((('uf', 'UF'), ('clp', 'Pesos')), 'Moneda Seguro Complementario', default='uf')
    mutual_seguridad = fields.Boolean('Mutual Seguridad')
    pension = fields.Boolean('Pensionado')
    gratificacion_legal = fields.Boolean('Gratificación Legal Anual', help='Si esta marcado es Anual, sino es Mensual')
    gratificacion_legal_fija = fields.Float('Gratificación Legal', help='Gratificación Legal Fija')
    contracts = fields.Char('Contratos', compute='_compute_contracts')
    borrow_ids = fields.Many2many('hr.borrow.line', string='Préstamos', compute='_compute_prestamos')

    @api.onchange('pension')
    def onchange_pension(self):
        if self.pension:
            self.tipo_trabajador = '2'
        else:
            self.tipo_trabajador = '0'

    @api.onchange('rh_cargas_ids')
    def _compute_cargas(self):
        for record in self:
            c_familiar = 0
            c_maternal = 0
            c_invalida = 0

            for cargas in record.rh_cargas_ids:
                if cargas.list_tipo == '1':
                    c_familiar = c_familiar + 1
                if cargas.list_tipo == '2':
                    c_maternal = c_maternal + 1
                if cargas.list_tipo == '3':
                    c_invalida = c_invalida + 1

            record.cant_carga_familiar = c_familiar
            record.cant_carga_familiar_maternal = c_maternal
            record.cant_carga_familiar_invalida = c_invalida

            record.cantidad_de_carga = c_familiar + c_maternal + c_invalida

    @api.onchange('region_id')
    def onchange_region(self):
        res = {
            'value': {
                'city_id': False
            }
        }
        if self.region_id:
            res.update({
                'domain': {
                    'city_id': [('state_id.parent_id', '=', self.region_id.id)]
                }
            })
        return res

    # Colocando las mayusculas
    @api.onchange('first_name')
    def first_name_capital(self):
        if self.company_id.capital_text and self.first_name:
            self.first_name = self.first_name.upper()

    @api.onchange('last_name')
    def last_name_capital(self):
        if self.company_id.capital_text and self.last_name:
            self.last_name = self.last_name.upper()

    @api.onchange('middle_name')
    def middle_name_capital(self):
        if self.company_id.capital_text and self.middle_name:
            self.middle_name = self.middle_name.upper()

    @api.onchange('mothers_name')
    def mothers_name_capital(self):
        if self.company_id.capital_text and self.mothers_name:
            self.mothers_name = self.mothers_name.upper()

    def _compute_contracts(self):
        for record in self:
            record.contracts = ', '.join(record.mapped('contract_ids.name'))

    def _compute_leaves_month(self):
        day_end = monthrange(*map(int, fields.Date.today()[:7].split('-')))[-1]
        date_from, date_to = ('%s-%.2d' % (fields.Date.today()[:7], day) for day in [1, day_end])
        for record in self:
            record.leaves_on_month = sum(record.leave_ids.filtered(lambda l: l.date_from <= date_to and l.date_to >= date_from and l.state == 'validate').mapped('number_of_days_temp'))

    def _compute_vacations_count(self):
        # vac_common = self.env.ref('l10n_cl_hr_payroll.LC05')
        # vac_prog = self.env.ref('l10n_cl_hr_payroll.LC06')
        # vacations = self.env['hr.holidays'].search([('employee_id', 'in', self.ids), ('type', '=', 'add'), ('holiday_status_id', 'in', [vac_common.id, vac_prog.id]), ('state', '=', 'validate')])
        for record in self:
            record.vacations_count = 0  # TODO
            # record.vacations_count = round(sum(vacations.filtered(lambda v: v.employee_id == record).mapped('remaining_vacations')), 2)

    def _compute_hired(self):
        today = fields.Date.today()
        for record in self:
            record.hired = bool(record.contract_ids.filtered(lambda c: c.date_start <= today and ((c.date_end and c.date_end >= today) or not c.date_end)))

    def _search_hired(self, operator, value):
        if operator not in ['=', '!=']:
            raise ValidationError(_('El operator "%s" no es soportado para el campo "Contratado"') % operator)
        today = fields.Date.today()
        contracts = self.env['hr.contract'].search(['&', ('date_start', '<=', today), '|', ('date_end', '>=', today), ('date_end', '=', False)])
        operator = 'in' if value else 'not in'
        return [('id', operator, contracts.mapped('employee_id.id'))]

    def _compute_last_payroll(self):
        payslip_obj = self.env['hr.payslip']
        meses = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
        for record in self:
            payslip = payslip_obj.search([('employee_id', '=', record.id)], order='date_from desc', limit=1)
            if payslip:
                year, month = payslip.date_from[:7].split('-')
                record.last_payroll = '%s/%s' % (meses[int(month) - 1], year)
            else:
                record.last_payroll = False

    def _compute_prestamos(self):
        day_end = monthrange(*map(int, fields.Date.today()[:7].split('-')))[-1]
        date_from, date_to = ('%s-%.2d' % (fields.Date.today()[:7], day) for day in [1, day_end])
        prestamo_obj = self.env['hr.borrow.line']
        for record in self:
            record.borrow_ids = prestamo_obj.search([('borrow_id.employee_id', '=', record.id), ('date_due', '>=', date_from), ('date_due', '<=', date_to)])

    @api.depends('first_name', 'mothers_name', 'middle_name', 'last_name')
    def full_name_func(self):
        for record in self:
            record.full_name = ' '.join(name for name in (record.first_name,
                                                          record.middle_name,
                                                          record.last_name,
                                                          record.mothers_name) if name)

    @api.onchange('first_name', 'mothers_name', 'middle_name', 'last_name')
    def get_name(self):
        for employee in self:
            employee.name = ' '.join(p for p in (employee.last_name,
                                                 employee.mothers_name,
                                                 employee.first_name,
                                                 employee.middle_name) if p)

    @api.model
    def _get_computed_name(self, last_name, first_name):
        """Compute the 'name' field according to splitted data.
        You can override this method to change the order of lastname and
        first_name the computed name"""
        return " ".join((p for p in (last_name, mothers_name, first_name, middle_name) if p))

    @api.onchange('identification_id')
    def _comprueba_rut(self):
        if self.identification_id:
            int_rut = self.identification_id
            int_rut = int_rut.replace('-', '').replace('.', '').replace(',', '')
            rut = int_rut[:-1]
            dig = int_rut[-1]
            resto = ""
            ok = False
            if len(int_rut) > 8 and int_rut != '555555555':
                n1, n2, n3, n4, n5, n6, n7, n8 = rut
                m1 = int(n1) * 3
                m2 = int(n2) * 2
                m3 = int(n3) * 7
                m4 = int(n4) * 6
                m5 = int(n5) * 5
                m6 = int(n6) * 4
                m7 = int(n7) * 3
                m8 = int(n8) * 2
                suma = m1 + m2 + m3 + m4 + m5 + m6 + m7 + m8
                resto = suma / 11
                resto = 11 - (suma - resto * 11)
                if resto == 10 or resto == 11:
                    resto = 'K'
                    ok = True
                if dig == str(resto):
                    ok = True
            else:
                ok = True
            # Formateamos el RUT con el estandar 24.063.888-6
            position = len(int_rut) - 1
            int_rut = int_rut[:position] + '-' + int_rut[position:]
            int_rut = int_rut[:-5] + '.' + int_rut[-5:]
            if len(int_rut) > 9:
                int_rut = int_rut[:-9] + '.' + int_rut[-9:]
            if not ok:
                self.identification_id = ''
            else:
                self.identification_id = int_rut

    def get_workable_days_count(self, date_start, date_end):
        """ Devuelve un entero con la cantidad de días trabajables en el periodo."""
        dt_start, dt_end = map(fields.Date.from_string, [date_start, date_end])
        weekdays = self.contract_id and self.contract_id.working_hours and self.contract_id.working_hours.get_weekdays() or []
        feriados = self.env['hr.holidays.chile'].search([('date', '>=', date_start), ('date', '<=', date_end)])
        constantes = [f.date[5:] for f in feriados.filtered('constant') if f.date]
        feriados = feriados.filtered(lambda f: (len(f.region_ids) == 0) or self.region_id in f.region_ids).mapped('date')
        count = 0
        while dt_start <= dt_end:
            count += dt_start.weekday() in weekdays and (fields.Date.to_string(dt_start) not in feriados) and (fields.Date.to_string(dt_start)[5:] not in constantes) and 1 or 0
            dt_start += timedelta(days=1)
        return count

    def get_worked_days_count(self, date_start, date_end):
        """ Devuelve un entero con la cantidad de días trabajados en el periodo,
        estos días trabajados se conforman de los días que aparecen en la
        `Planificación de Trabajo` de su contrato, adicionalmente, se restan
        los días feriados en el periodo y los días de ausencia justificados """
        dt_start, dt_end = map(fields.Date.from_string, [date_start, date_end])
        weekdays = self.contract_id and self.contract_id.working_hours and self.contract_id.working_hours.get_weekdays() or []
        feriados = self.env['hr.holidays.chile'].search([('date', '>=', date_start), ('date', '<=', date_end)])
        constantes = [f.date[5:] for f in feriados.filtered('constant') if f.date]
        feriados = feriados.filtered(lambda f: (len(f.region_ids) == 0) or self.region_id in f.region_ids).mapped('date')
        holidays = self.env['hr.holidays'].search([
            ('date_from', '<=', date_end),
            ('date_to', '>=', date_start),
            ('state', '=', 'validate'),
            ('type', '=', 'remove'),
            ('employee_id', '=', self.id),
            ('holiday_status_id.affects_payslip', '=', True)])
        ausencias = set()
        for holiday in holidays:
            holiday_start, holiday_end = map(fields.Date.from_string, [holiday.date_from, holiday.date_to])
            while holiday_start <= holiday_end:
                ausencias.add(fields.Date.to_string(holiday_start))
                holiday_start += timedelta(days=1)
        count = 0
        while dt_start <= dt_end:
            count += (dt_start.weekday() in weekdays) and (fields.Date.to_string(dt_start) not in feriados) and (fields.Date.to_string(dt_start)[5:] not in constantes) and (fields.Date.to_string(dt_start) not in ausencias) and 1 or 0
            dt_start += timedelta(days=1)
        return count

    def get_semana_corrida(self, date_start, date_end, day=None):
        """ Devuelve la cantidad de días domingos y feriados en el periodo,
        usado para los cálculos de Semana Corrida, además de los días que sí
        debió trabajar. """
        if day:
            dt_end = fields.Date.from_string('%s%.2d' % (date_start[:-2], day))
            dt_start = dt_end - relativedelta(months=1, days=-1)
        else:
            dt_start, dt_end = map(fields.Date.from_string, [date_start, date_end])
        feriados = self.env['hr.holidays.chile'].search([('date', '>=', dt_start.strftime('%Y-%m-%d')), ('date', '<=', dt_end.strftime('%Y-%m-%d'))])
        constantes = [f.date[5:] for f in feriados.filtered('constant') if f.date]
        feriados = feriados.filtered(lambda f: (len(f.region_ids) == 0) or self.region_id in f.region_ids).mapped('date')
        workable = range(5)
        worked = non_worked = 0
        while dt_start <= dt_end:
            if (dt_start.weekday() == 6) or (fields.Date.to_string(dt_start) in feriados) or (fields.Date.to_string(dt_start)[5:] in constantes):
                non_worked += 1
            elif dt_start.weekday() in workable:
                worked += 1
            dt_start += timedelta(days=1)
        return worked, non_worked

    def get_vacations_grouped(self):
        self.ensure_one()
        vac_common = self.env.ref('l10n_cl_hr_payroll.LC05')
        vac_prog = self.env.ref('l10n_cl_hr_payroll.LC06')
        years = {}
        vacations_common = self.env['hr.holidays'].search([('employee_id', '=', self.id),
                                                           ('type', '=', 'add'),
                                                           ('holiday_status_id', '=', vac_common.id),
                                                           ('state', '=', 'validate')])
        vacations_prog = self.env['hr.holidays'].search([('employee_id', '=', self.id),
                                                         ('type', '=', 'add'),
                                                         ('holiday_status_id', '=', vac_prog.id),
                                                         ('state', '=', 'validate')])
        saldo_common = sum(vacations_common.mapped('number_of_days_temp'))
        saldo_prog = sum(vacations_prog.mapped('number_of_days_temp'))
        date_start = self.contract_id and self.contract_id.vacation_date_start or min(self.contract_ids.mapped('date_start'))
        date_end = self.contract_id and self.contract_id.date_end or fields.Date.today()
        total_days = (fields.Date.from_string(date_end) - fields.Date.from_string(date_start)).days + 1
        total_common, total_prog = 0.0, 0.0
        while date_start < date_end:
            dt_start = fields.Date.from_string(date_start)
            new_date_end = '%s-12-31' % date_start[:4]
            dt_end = fields.Date.from_string(new_date_end if new_date_end < date_end else date_end)
            days_on_period = ((dt_end - dt_start).days + 1)
            common = round(saldo_common / float(total_days) * float(days_on_period), 2)
            if common > 15:
                common = 15.0
            prog = round(saldo_prog / float(total_days) * float(days_on_period), 2)
            if prog > 15:
                prog = 15.0
            total_common += common
            total_prog += prog
            years[date_start[:4]] = [common, prog]
            date_start = '%d-01-01' % (int(date_start[:4]) + 1)
        if (total_common + total_prog) != round(saldo_common + saldo_prog, 2):
            total_estimated = total_common + total_prog
            saldo_total = round(saldo_common + saldo_prog, 2)
            if total_estimated > saldo_total:
                difference = total_estimated - saldo_total
                years[str(int(date_start[:4]) - 1)][0] -= difference
            else:
                difference = saldo_total - total_estimated
                years[str(int(date_start[:4]) - 1)][0] += difference
        return sorted(years.items())

    @api.model
    def factor_isapre(self, contract, date_from, date_to):
        """ Devuelve un float que representa el factor por el que se debe multiplicar
        el monto adicional isapre, tomando en cuenta los días de ausencia por licencia """
        if contract.type_id.codigo == 'diario':
            wdf = date_from if date_from >= contract.date_start else contract.date_start
            wdt = date_to if (not contract.date_end or date_to <= contract.date_end) else contract.date_end
            nod = contract.employee_id.get_workable_days_count(wdf, wdt)
        # Si el contrato empieza antes del periodo de nómina y termina después del periodo de nómina: 30 días
        elif contract.date_start <= date_from and (not contract.date_end or contract.date_end >= date_to):
            nod = 30.0
        # Si el contrato empieza después del periodo de nómina y termina después del periodo: 31 - día que comenzó el contrato
        elif contract.date_start > date_from and (not contract.date_end or contract.date_end >= date_to):
            nod = 31.0 - int(contract.date_start.split('-')[2])
        # Si el contrato empieza antes del periodo de nómina y termina antes del periodo: día en que termina el contrato
        elif contract.date_start <= date_from and (contract and contract.date_end < date_to):
            nod = int(contract.date_end.split('-')[2])
        # Si el contrato empieza después y termina antes del periodo de nómina: días entre el periodo del contrato
        else:
            dt_start, dt_end = map(fields.Date.from_string, [contract.date_start, contract.date_end])
            nod = (dt_end - dt_start).days + 1
        # Buscamos los días de licencia
        # licencias = self.env['hr.holidays'].search([
        #     ('employee_id', '=', contract.employee_id.id),
        #     ('date_from', '<=', date_to),
        #     ('date_to', '>=', date_from),
        #     ('state', '=', 'validate'),
        #     ('type', '=', 'remove'),
        #     ('holiday_status_id', '=', self.env.ref('l10n_cl_hr_payroll.LC02').id)
        # ])
        dias_licencia = set()
        # for licencia in licencias:
        #     dt_start, dt_end = map(fields.Date.from_string, [licencia.date_from, licencia.date_to])
        #     while dt_start <= dt_end:
        #         actual = fields.Date.to_string(dt_start)
        #         if date_from <= actual <= date_to:
        #             dias_licencia.add(actual)
        #         dt_start += timedelta(days=1)
        return round((nod - len(dias_licencia)) / nod, 5)

    @property
    def worked_months(self):
        contract = self.contract_id.parent_id or self.contract_id
        worked_time = contract and relativedelta(fields.Date.from_string(self.contract_id.date_end or fields.Date.today()), fields.Date.from_string(contract.date_start))
        return worked_time and (worked_time.years * 12) + worked_time.months

    def name_get(self):
        """ Todos los empleados deberían tener primer nombre y primer apellido
        definidos, ya que son campos requeridos. Se sobrecarga éste método para
        que por defecto muestre estos nombres del empleado en vez del nombre de
        usuario. Si no tiene nombre y apellido definidos (ej. Administrador) se
        tomará el nombre de usuario, en caso de tener usuario definido. Y si
        tampoco tiene usuario entonces... ¿se rompe? No se muestra nada.
        """
        return [(rec.id, '%s %s' % (rec.first_name or '', rec.last_name or '') if rec.first_name or rec.last_name else rec.user_id and rec.user_id.name or '') for rec in self]

    @api.model
    def get_nombre_mes_espanol(self, fecha):
        """ Ya que no se puede confiar en que configuren bien el servidor en
        español, se creará un arreglo con los meses en español y se usará para
        llenar el nombre a partir de ahí.
        """
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        return '%s de %s de %s' % (fecha[-2:], meses[int(fecha[5:7]) - 1], fecha[:4])

    def mostrar_todos_hd(self):
        """ Muestra todos los haberes y descuentos que están inactivos. """
        return self.haberes_descuentos_ids.search([('employee_id', 'in', self.ids), ('active', '=', False)]).write({'active': True})

    @property
    def last30days_wage(self):
        nominas = self.env['hr.payslip'].search([('employee_id', '=', self.id)])
        ganadora = False
        for nomina in nominas:
            for wdl in nomina.worked_days_line_ids:
                if wdl.code == 'WORK100' and wdl.number_of_days == 30.0:
                    ganadora = nomina
                    break
            if ganadora:
                break
        if ganadora:
            return sum(ganadora.line_ids.filtered(lambda l: l.code == 'TOTIM').mapped('total'))
        # Si no encuentro ninguna nómina donde haya trabajado 30 días, devuelvo su salario base, ¿estará bien?
        return 0

    def write(self, vals):
        res = super(HrEmployee, self).write(vals)
        for record in self:
            full_name = ' '.join(name for name in (record.first_name,
                                                   record.middle_name,
                                                   record.last_name,
                                                   record.mothers_name) if name)
            super(HrEmployee, record).write({'name': full_name})
        return res

class HrHd(models.Model):
    _name = 'hr.hd'
    _description = 'Haber / Descuento Empleado'
    _order = 'id desc'
    _rec_name = 'haberesydesc_id'

    origen = fields.Selection([
        ('manual', 'Manual'),
        ('single', 'PT'),
        ('multi', 'Multi')
    ], default='manual')
    haberesydesc_id = fields.Many2one('hr.balance', string='Asignaciones y Descuentos', ondelete="restrict")
    date_from = fields.Date('Desde', default=fields.Date.today)
    date_to = fields.Date('Hasta')
    moneda = fields.Selection('Tipo', related='haberesydesc_id.moneda')
    um = fields.Selection('UM', related='haberesydesc_id.um')
    del_mes = fields.Boolean(compute='_compute_del_mes')
    active = fields.Boolean(default=True)
    amount = fields.Float('Monto')
    employee_id = fields.Many2one('hr.employee', "Empleado", ondelete='cascade')
    r_tipo = fields.Selection('Tipo', related='haberesydesc_id.tipo')

    @api.constrains('haberesydesc_id', 'date_from', 'date_to', 'employee_id', 'amount')
    def _check_unique(self):
        for record in self:
            if record.date_to and record.date_from > record.date_to:
                raise ValidationError(_('Fecha inicio en %s no puede ser mayor a fecha fin.') % record.haberesydesc_id.desc)

            if record.amount <= 0:
                raise ValidationError(_('Monto en %s debe ser mayor a 0.') % record.haberesydesc_id.desc)

            if record.date_to:
                repetidos = self.search_count([
                    ('id', '!=', record.id),
                    ('haberesydesc_id', '=', record.haberesydesc_id.id),
                    ('date_from', '<=', record.date_to),
                    ('date_to', '>=', record.date_from),
                    ('employee_id', '=', record.employee_id.id)])
            else:
                repetidos = self.search_count([
                    ('id', '!=', record.id),
                    ('haberesydesc_id', '=', record.haberesydesc_id.id),
                    ('date_from', '<=', record.date_from),
                    ('date_to', '=', False),
                    ('employee_id', '=', record.employee_id.id)])

            if repetidos:
                raise ValidationError(_('Ya existe el bono %s dentro del mismo rango de fechas para %s') % (record.haberesydesc_id.desc, record.employee_id.haberesydesc_id))

    @api.model
    def cron_hr_hd(self):
        today = fields.Date.today()
        meses_hyd = self.env['ir.config_parameter'].get_param('meses.haberes.descuentos', '3')
        if meses_hyd.isdigit():
            meses_hyd = int(meses_hyd)
        else:
            raise ValidationError(_('Parámetro "meses.haberes.descuentos" debe ser un número entero positivo.'))
        today -= relativedelta(months=meses_hyd)
        for record in self.search(['|', ('active', '=', True), ('active', '=', False)]):
            record.active = record.date_to and (record.date_to >= today) or not record.date_to

    @api.depends('date_from', 'date_to')
    def _compute_del_mes(self):
        today = fields.Date.today()
        self.del_mes = self.date_from < today and (self.date_to and self.date_to > today or not self.date_to)

    @api.model
    def create(self, vals):
        origen = self.env.context.get('origen')
        vals['origen'] = origen or 'manual'
        record = super().create(vals)
        record.employee_id.message_post(body=_('Creado el Haber y Descuento %s, de monto %.0f, desde %s%s.') % (record.haberesydesc_id.desc, record.amount, '/'.join(record.date_from.isoformat().split('-')[::-1]), record.date_to and (', hasta: %s' % '/'.join(record.date_to.isoformat().split('-')[::-1])) or ''))
        return record

    def write(self, vals):
        for record in self:
            campos = self._fields
            listado = 'Modificado un Haber y Descuento: %s<ul>' % record.haberesydesc_id.display_name
            for key, value in vals.items():
                campo = campos.get(key)
                old_value = getattr(record, key)
                if campo.type == 'many2one':
                    old_value = old_value.display_name if old_value else 'No definido'
                    value = self.env[campo.comodel_name].browse(value).display_name
                elif campo.type == 'date':
                    old_value = '/'.join(old_value.isoformat().split('-')[::-1]) if old_value else 'No definido'
                    value = '/'.join(value.isoformat().split('-')[::-1])
                elif not old_value:
                    old_value = 'No definido'
                listado += '<li>%s: %s &rarr; %s</li>' % (campo.string, old_value, value)
            listado += '</ul>'
            record.employee_id.message_post(body=listado)
        return super().write(vals)

    def unlink(self):
        for record in self:
            record.employee_id.message_post(body=_('Borrado el Haber y Descuento %s, de monto %.0f, desde %s%s.') % (record.haberesydesc_id.desc, record.amount, '/'.join(record.date_from.isoformat().split('-')[::-1]), record.date_to and (', hasta: %s' % '/'.join(record.date_to.isoformat().split('-')[::-1])) or ''))
        return super().unlink()


class payrol_he(models.Model):
    _name = 'hr.he'
    _order = 'id desc'
    name = fields.Many2one('hr.balance', string='Horas Extras', ondelete="restrict")
    date = fields.Date('Fecha', default=lambda self: datetime.today())
    monto = fields.Float('Cantidad')
    employee_id = fields.Many2one('hr.employee', "Empleado", ondelete='cascade')


class List_Cargas(models.Model):
    _name = 'l.cargas'
    identification_id = fields.Char("RUT (00.000.000-0)", size=12)
    list_name = fields.Char("Nombre y Apellido", size=25)
    list_nacimiento = fields.Date('Fecha Nac')
    list_edad_limite = fields.Integer("Edad Limite")
    list_tipo = fields.Selection(
        [('1', 'Simple'),
         ('2', 'Maternal'),
         ('3', 'Inválida')],
        'Tipo', size=1, default='1')
    list_obs = fields.Char("Observación", size=25)
    employee_id = fields.Many2one('hr.employee', "Empleado", ondelete='cascade')

    @api.onchange('identification_id')
    def _comprueba_rut(self):
        if self.identification_id:
            int_rut = self.identification_id
            int_rut = int_rut.replace("-", '')
            int_rut = int_rut.replace(".", '')
            int_rut = int_rut.replace(",", '')
            rut = int_rut[:-1]
            dig = int_rut[-1]
            resto = ""
            ok = False
            if len(int_rut) > 8 and int_rut != '555555555':
                n1 = rut[0]
                m1 = int(n1) * 3
                n2 = rut[1]
                m2 = int(n2) * 2
                n3 = rut[2]
                m3 = int(n3) * 7
                n4 = rut[3]
                m4 = int(n4) * 6
                n5 = rut[4]
                m5 = int(n5) * 5
                n6 = rut[5]
                m6 = int(n6) * 4
                n7 = rut[6]
                m7 = int(n7) * 3
                n8 = rut[7]
                m8 = int(n8) * 2
                suma = m1 + m2 + m3 + m4 + m5 + m6 + m7 + m8
                resto = suma / 11
                resto = 11 - (suma - resto * 11)
                if resto == 10 or resto == 11:
                    resto = 'K'
                    ok = True
                if dig == str(resto):
                    ok = True
            else:
                ok = True
            # Formateamos el RUT con el estandar 24.063.888-6
            position = len(int_rut) - 1
            int_rut = int_rut[:position] + '-' + int_rut[position:]
            int_rut = int_rut[:-5] + '.' + int_rut[-5:]
            if len(int_rut) > 9:
                int_rut = int_rut[:-9] + '.' + int_rut[-9:]
            if not ok:
                self.identification_id = ''
            else:
                self.identification_id = int_rut
