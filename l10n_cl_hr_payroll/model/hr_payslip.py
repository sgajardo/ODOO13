# coding: utf-8
import time
from datetime import datetime, timedelta

import babel

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError

from ..report.amount_to_text_es import amount_to_text_es


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'mail.thread']
    _description = 'Pay Slip'
    _order = 'id desc'

    report_show_50_por = fields.Boolean(compute='_compute_report_show_50_por')

    def _compute_report_show_50_por(self):
        adv_var = self.env['ir.config_parameter'].sudo().get_param('report.show.50.por')
        if adv_var == 'True':
            self.report_show_50_por = True
        else:
            self.report_show_50_por = False

    report_show_100_por = fields.Boolean(compute='_compute_report_show_100_por')

    def _compute_report_show_100_por(self):
        adv_var = self.env['ir.config_parameter'].sudo().get_param('report.show.100.por')
        if adv_var == 'True':
            self.report_show_100_por = True
        else:
            self.report_show_100_por = False

    report_show_dom_por = fields.Boolean(compute='_compute_report_show_dom_por')

    def _compute_report_show_dom_por(self):
        adv_var = self.env['ir.config_parameter'].sudo().get_param('report.show.dom.por')
        if adv_var == 'True':
            self.report_show_dom_por = True
        else:
            self.report_show_dom_por = False

    report_note_payslip = fields.Text(compute='_compute_report_note_payslip')

    def _compute_report_note_payslip(self):
        self.report_note_payslip = self.env['ir.config_parameter'].sudo().get_param('report.note.payslip')

    report_show_referencia = fields.Text(compute='_compute_report_show_referencia')

    def _compute_report_show_referencia(self):
        adv_var = self.env['ir.config_parameter'].sudo().get_param('report.show.referencia')
        if adv_var == 'True':
            self.report_show_referencia = True
        else:
            self.report_show_referencia = False



    notas = fields.Text(track_visibility='onchange')
    state = fields.Selection(track_visibility='onchange')
    stats_id = fields.Many2one('hr.stats', string='Indicadores',
                                     readonly=True, states={'draft': [('readonly', False)]},
                                     ondelete="restrict",
                                     help='Defines Previred Forecast Indicators')

    paid_leaves_count = fields.Integer(compute='_compute_leaves')
    unpaid_leaves_count = fields.Integer(compute='_compute_leaves')
    vacations_taken_count = fields.Integer(compute='_compute_leaves')
    vacations_pending_count = fields.Integer(compute='_compute_leaves')
    cuota_ids = fields.One2many('hr.borrow.line', 'payslip_id', 'Cuotas de préstamos', help=u'Cuotas de préstamos que fueron pagadas con esta nómina.')
    sequence = fields.Integer(compute='_compute_sequence')

    # Datos Histórico
    afp_id = fields.Many2one('hr.afp', 'AFP', ondelete="restrict", track_visibility='onchange')
    isapre_id = fields.Many2one('hr.isapre', 'Salud', ondelete="restrict", track_visibility='onchange')
    isapre_cotizacion_uf = fields.Float("Plan Salud (UF)", digits=(3, 4), track_visibility='onchange')

    def exe_historic(self):
        for p in self:
            if p.employee_id:
                if p.employee_id.afp_id:
                    p.afp_id = p.employee_id.afp_id.id
                if p.employee_id.isapre_id:
                    p.isapre_id = p.employee_id.isapre_id.id
                    p.isapre_cotizacion_uf = p.employee_id.isapre_cotizacion_uf

                p.message_post(body='Guardando Histórico.')  # TODO Ver como se hace ahora...

    def _compute_sequence(self):
        for i, record in enumerate(self.sorted('id', reverse=True), 1):
            record.sequence = i

    def _compute_leaves(self):
        licencia = self.env.ref('l10n_cl_hr_payroll.LC02')
        vacations1 = self.env.ref('l10n_cl_hr_payroll.LC05')
        vacations2 = self.env.ref('l10n_cl_hr_payroll.LC06')
        total_leaves = self.env['hr.holidays'].search([
            ('employee_id', 'in', self.mapped('employee_id.id')),
            ('type', '=', 'remove'),
            ('state', '=', 'validate')
        ])
        add_leaves = self.env['hr.holidays'].search([
            ('employee_id', 'in', self.mapped('employee_id.id')),
            ('type', '=', 'add'),
            ('holiday_status_id', 'in', [vacations1.id, vacations2.id]),
            ('state', '=', 'validate')
        ])
        for record in self:
            feriados = self.env['hr.holidays.chile'].search([('date', '>=', record.date_from), ('date', '<=', record.date_to)])
            constantes = [f.date[5:] for f in feriados.filtered('constant') if f.date]
            feriados = feriados.filtered(lambda f: (len(f.region_ids) == 0) or record.employee_id.region_id in f.region_ids).mapped('date')
            current_leaves = total_leaves.filtered(lambda l: l.date_from <= record.date_to and l.date_to >= record.date_from and l.employee_id == record.employee_id)
            paid = unpaid = taken = 0
            for leave in current_leaves:
                dt_start = fields.Date.from_string(leave.date_from if leave.date_from > record.date_from else record.date_from)
                dt_end = fields.Date.from_string(leave.date_to if leave.date_to < record.date_to else record.date_to)
                weekdays = record.contract_id and record.contract_id.working_hours and record.contract_id.working_hours.get_weekdays() or []
                while dt_start <= dt_end:
                    if leave.holiday_status_id == licencia:
                        paid += 1
                    elif dt_start.weekday() in weekdays and (fields.Date.to_string(dt_start) not in feriados) and (fields.Date.to_string(dt_start)[5:] not in constantes):
                        if leave.holiday_status_id not in (vacations1, vacations2, licencia):
                            unpaid += 1
                        elif leave.holiday_status_id in (vacations1, vacations2):
                            taken += 1
                    dt_start += timedelta(days=1)
            record.paid_leaves_count = paid
            record.unpaid_leaves_count = unpaid
            record.vacations_taken_count = taken
            record.vacations_pending_count = sum(add_leaves.filtered(lambda l: l.employee_id == record.employee_id).mapped('remaining_vacations'))

    def compute_sheet(self):
        self.exe_historic()
        for record in self:
            record.message_post(body=_('Calculada hoja de nómina.'))
        return super(HrPayslip, self).compute_sheet()

    # YTI TODO To rename. This method is not really an onchange, as it is not in any view
    # employee_id and contract_id could be browse records
    def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
        # defaults
        res = {
            'value': {
                'line_ids': [],
                # delete old input lines
                'input_line_ids': [(2, x) for x in self.input_line_ids.ids],
                # delete old worked days lines
                'worked_days_line_ids': [(2, x) for x in self.worked_days_line_ids.ids],
                # 'details_by_salary_head':[], TODO put me back
                'name': '',
                'contract_id': False,
                'struct_id': False,
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        # ttyme = datetime.fromtimestamp(time.mktime(time.strptime(date_from, "%Y-%m-%d")))
        employee = self.env['hr.employee'].browse(employee_id)
        locale = self.env.context.get('lang', 'en_US')
        res['value'].update({
            'name': _('Salary Slip of %s for %s') % (
                employee.name, tools.ustr(babel.dates.format_date(date=date_from, format='MMMM-y', locale=locale))),
            'company_id': employee.company_id.id,
        })

        if not self.env.context.get('contract'):
            # fill with the first contract of the employee
            contract_ids = self.get_contract(employee, date_from, date_to)
        else:
            if contract_id:
                # set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                # if we don't give the contract, then the input to fill should be for all current contracts of the employee
                contract_ids = self.get_contract(employee, date_from, date_to)

        if not contract_ids:
            raise UserError(_('%s no tiene contrato para el periodo %s - %s') % (employee.display_name, date_from, date_to))
        contract = self.env['hr.contract'].browse(contract_ids[0])
        res['value'].update({
            'contract_id': contract.id
        })
        struct = contract.struct_id
        if not struct:
            return res
        res['value'].update({
            'struct_id': struct.id,
        })
        # computation of the salary input
        worked_days_line_ids = self.get_worked_day_lines(contract_ids, date_from, date_to)
        input_line_ids = self.get_inputs(contract_ids, date_from, date_to)
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })
        return res

    @api.model
    def get_inputs(self, contract_ids, date_from, date_to):
        res = []

        contracts = self.env['hr.contract'].browse(contract_ids)
        structure_ids = contracts.get_all_structures()
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        sorted_rule_ids = [i for i, ___ in sorted(rule_ids, key=lambda x: x[1])]
        inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids).mapped('input_ids')
        inicio_horas_extras = self.env['ir.config_parameter'].get_param('horas.extras.inicio', '0')
        if inicio_horas_extras.isdigit():
            inicio_horas_extras = int(inicio_horas_extras)
            if inicio_horas_extras < 0 or inicio_horas_extras > 28:
                raise UserError(_('Parámetro horas.extras.inicio debe estar entre 0 y 28 (actualmente %d).') % inicio_horas_extras)
        else:
            raise UserError(_('Parámetro horas.extras.inicio debe ser un número del 0 al 28 (actualmente contiene %s.') % inicio_horas_extras)

        if inicio_horas_extras > 0:
            mes_anterior = fields.Date.from_string('%s-01' % date_from[:7]) - timedelta(days=1)
            date_from_he = '%s-%.2d-%.2d' % (date_from[:4], mes_anterior.month, inicio_horas_extras)
            date_to_he = '%s-%.2d' % (date_from[:7], inicio_horas_extras - 1)
        else:
            date_from_he, date_to_he = date_from, date_to

        for contract in contracts:
            employee_id = (self.employee_id and self.employee_id.id) or (contract.employee_id and contract.employee_id.id)
            horas_extras = {}
            for he in contract.employee_id.horas_extras_ids.filtered(lambda he: date_from_he <= he.date <= date_to_he):
                if he.name in horas_extras:
                    horas_extras[he.name] += he.monto
                else:
                    horas_extras[he.name] = he.monto
            for he in horas_extras:
                # Buscamos los haberes y descuentos de "horas extras" en el empleado para el periodo
                hehd_ids = contract.employee_id.haberes_descuentos_ids.filtered(lambda hd: hd.name == he and hd.date_from <= date_to and (not hd.date_to or hd.date_to >= date_from))
                if hehd_ids:
                    # Si existen, usamos solo uno de ese mismo tipo y le modificamos el monto.
                    hehd_ids.write({'monto': horas_extras[he]})
                    # Si son varios del mismo tipo, dejamos solo uno:
                    hehd_ids[1:].unlink()
                else:
                    # Si no existe, lo creamos
                    hehd_ids.create({
                        'employee_id': contract.employee_id.id,
                        'name': he.id,
                        'monto': horas_extras[he],
                        'date_from': date_from,
                        'date_to': date_to
                    })
            for inp in inputs:
                habydesc = self.env['hr.balance'].search([('inputs_id', '=', inp.id)])
                amount = 0.0

                for hyd in habydesc:
                    hdemployees = self.env['hr.hd'].search([('employee_id', '=', employee_id), ('haberesydesc_id', '=', hyd.id),
                                                            ('date_from', '<=', date_to), ('date_to', '=', False)])
                    hdemployees += self.env['hr.hd'].search([('employee_id', '=', employee_id), ('haberesydesc_id', '=', hyd.id),
                                                             ('date_from', '<=', date_to), ('date_to', '>=', date_from)])

                    for emphyd in hdemployees:
                        amount += emphyd.monto

                prestamos = self.env['hr.borrow'].search([('inputs_id', '=', inp.id), ('employee_id', '=', employee_id)])
                cuotas = prestamos.mapped('line_ids').filtered(lambda l: date_from <= l.date_due <= date_to and not l.cobrado)
                amount += sum(cuotas.mapped('amount'))
                res.append({
                    'name': inp.name,
                    'code': inp.code,
                    'amount': amount,
                    'contract_id': contract.id,
                })
        return res

    def action_payslip_done(self):
        rule_input_obj = self.env['hr.rule.input']
        prestamos_obj = self.env['hr.borrow']
        for record in self:
            inputs = record.input_line_ids.filtered(lambda i: i.amount > 0)
            rule_inputs = rule_input_obj.search([('code', 'in', inputs.mapped('code'))])
            prestamos = prestamos_obj.search([('inputs_id', 'in', rule_inputs.ids), ('employee_id', '=', record.employee_id.id)])
            cuotas = prestamos.mapped('line_ids').filtered(lambda l: record.date_from <= l.date_due <= record.date_to and not l.cobrado)
            prestamos_codes = prestamos.mapped('inputs_id.code')
            prestamos_inputs = inputs.filtered(lambda i: i.code in prestamos_codes)
            total_cuotas = sum(cuotas.mapped('amount'))
            total_prestamos = sum(prestamos_inputs.mapped('amount'))
            # Si el monto en las entradas de la nómina es el mismo de todas las cuotas del periodo, marcamos las cuotas como pagadas
            if total_prestamos >= total_cuotas:
                cuotas.cobrar(record)
            # else:
            #     raise UserError(_('El monto por préstamos no coincide:\nCuotas por pagar: %f\nMonto préstamo en nómina: %s') % (round(total_cuotas), round(total_prestamos)))
            vals = {
                'operation': 'upload',
                'type': 'all',
                'date_from': record.date_from,
                'date_to': record.date_to
            }
            historic = record.env['hr.historic.wizard'].create(vals)
            historic.upload_historic(payslip_process=True)
        return super(HrPayslip, self).action_payslip_done()

    def action_payslip_draft(self):
        self.mapped('cuota_ids').descobrar()
        return super(HrPayslip, self).action_payslip_draft()

    @api.model
    def create(self, vals):
        if 'stats_id' in self.env.context:
            vals['stats_id'] = self.env.context['stats_id']
        return super(HrPayslip, self).create(vals)

    @api.model
    def search(self, *args, **kargs):
        u""" Se sobrecarga para excluir los roles privados a usuarios que no
        tengan permisos de gerente de nómina (group_hr_manager) """
        res = super(HrPayslip, self).search(*args, **kargs)
        if not self.env.user.has_group('hr.group_hr_manager'):
            res = res.filtered(lambda s: not s.employee_id.private_role)
        return res

    @api.model
    def get_worked_day_lines(self, contract_ids, date_from, date_to):
        u"""
        Se sobrecarga ya que los días trabajados (WORK100) siempre deben ser 30
        en caso de no haber ausencias, y a partir de ahí, se le quita cada día
        de ausencia registrada para el empleado durante ese período
        """
        feriados = self.env['hr.holidays.chile'].search([('date', '>=', date_from), ('date', '<=', date_to)])
        constantes = [f.date[5:] for f in feriados.filtered('constant') if f.date]
        feriados = feriados.filtered(lambda f: (len(f.region_ids) == 0) or self.region_id in f.region_ids).mapped('date')
        for contract in self.env['hr.contract'].browse(contract_ids).filtered(lambda contract: contract.working_hours):
            # Si el tipo de contrato es Sueldo Diario Pactado, se calcula los días trabajables en el periodo
            if contract.type_id.codigo in ['diario', 'diariof']:
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
            # Contamos las horas trabajadas
            noh = sum(att.hour_to - att.hour_from for att in contract.working_hours.attendance_ids)
            # Horas por día
            hpd = float(noh) / len(contract.working_hours.attendance_ids)
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': nod,
                'number_of_hours': (hpd * nod) if contract.type_id.codigo == 'diario' else (noh * 4),
                'contract_id': contract.id,
            }
            leaves = {}
            holidays = []
            # holidays = self.env['hr.holidays'].search([
            #     ('employee_id', '=', contract.employee_id.id),
            #     ('date_from', '<=', date_to),
            #     ('date_to', '>=', date_from),
            #     ('state', '=', 'validate'),
            #     ('type', '=', 'remove'),
            #     ('holiday_status_id.affects_payslip', '=', True)
            # ])
            for holiday in holidays:
                if holiday.number_of_days_temp:
                    hdt_start = fields.Date.from_string(holiday.date_from if holiday.date_from > date_from else date_from)
                    hdt_end = fields.Date.from_string(holiday.date_to if holiday.date_to < date_to else date_to)
                    if holiday.holiday_status_id.corrido:
                        number_of_days = (hdt_end - hdt_start).days + 1
                    else:
                        number_of_days = 0
                        weekdays = contract.working_hours and contract.working_hours.get_weekdays() or []
                        while hdt_start <= hdt_end:
                            number_of_days += hdt_start.weekday() in weekdays and (fields.Date.to_string(hdt_start) not in feriados) and (fields.Date.to_string(hdt_start)[5:] not in constantes) and 1 or 0
                            hdt_start += timedelta(days=1)
                    if number_of_days > nod:
                        number_of_days = nod
                    attendances['number_of_days'] -= number_of_days
                    attendances['number_of_hours'] -= number_of_days * hpd
                    if holiday.holiday_status_id.name in leaves:
                        leaves[holiday.holiday_status_id.name]['number_of_days'] += number_of_days
                        leaves[holiday.holiday_status_id.name]['number_of_hours'] += number_of_days * hpd
                    else:
                        leaves[holiday.holiday_status_id.name] = {
                            'name': holiday.holiday_status_id.name,
                            'sequence': 5,
                            'code': holiday.holiday_status_id.name.split(' ')[0].upper(),
                            'number_of_days': number_of_days,
                            'number_of_hours': number_of_days * hpd,
                            'contract_id': contract.id
                        }
                if attendances['number_of_days'] < 0:
                    raise UserError(_(u'Usted está tratando de colocarle mas ausencias al empleado que la cantidad de días que por contrato está trabajando.'))
        return [attendances] + list(leaves.values())

    @api.model
    def convert(self, *args, **kwargs):
        u""" Movido acá para conveniencia de llamarlo en los reportes """
        return amount_to_text_es(*args, **kwargs)
