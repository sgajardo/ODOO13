from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, RedirectWarning

from ..report.amount_to_text_es import amount_to_text_es


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'mail.thread']
    _description = 'Pay Slip'
    _order = 'id desc'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        struct = self.env.ref('l10n_cl_hr_payroll.hr_struct_cl', raise_if_not_found=False)
        if not res.get('struct_id') and struct:
            res['struct_id'] = struct.id
        if not res.get('stats_id'):
            stats = self.env['hr.stats'].search([], limit=1, order='id desc')
            action = self.env.ref('l10n_cl_hr_payroll.hr_stats_previsionales_action', raise_if_not_found=False)
            if not stats and action:
                raise RedirectWarning('No se han cargado los indicadores Previred, ¿desea crearlos ahora?', action.id, 'Crear indicadores previred')
            elif not stats:
                raise UserError('No se han cargado los indicadores Previred')
            res['stats_id'] = stats.id
        return res

    notas = fields.Text(tracking=True)
    state = fields.Selection(tracking=True)
    stats_id = fields.Many2one('hr.stats', string='Indicadores',
                               readonly=True, states={'draft': [('readonly', False)]},
                               ondelete="restrict",
                               help='Defines Previred Forecast Indicators')

    paid_leaves_count = fields.Integer(compute='_compute_leaves')
    unpaid_leaves_count = fields.Integer(compute='_compute_leaves')
    vacations_taken_count = fields.Integer(compute='_compute_leaves')
    vacations_pending_count = fields.Integer(compute='_compute_leaves')
    cuota_ids = fields.One2many('hr.borrow.line', 'payslip_id', 'Cuotas de préstamos', help='Cuotas de préstamos que fueron pagadas con esta nómina.')
    sequence = fields.Integer(compute='_compute_sequence')

    # Datos Histórico
    afp_id = fields.Many2one('hr.afp', 'AFP', ondelete="restrict", tracking=True)
    isapre_id = fields.Many2one('hr.isapre', 'Salud', ondelete="restrict", tracking=True)
    isapre_cotizacion_uf = fields.Float("Plan Salud (UF)", digits=(3, 4), tracking=True)

    report_show_50_por = fields.Boolean(compute='_compute_report_show_50_por')
    report_show_100_por = fields.Boolean(compute='_compute_report_show_100_por')
    report_show_dom_por = fields.Boolean(compute='_compute_report_show_dom_por')
    report_note_payslip = fields.Text(compute='_compute_report_note_payslip')
    report_show_referencia = fields.Boolean(compute='_compute_report_show_referencia')

    def exe_historic(self):
        for p in self:
            if p.employee_id:
                if p.employee_id.afp_id:
                    p.afp_id = p.employee_id.afp_id.id
                if p.employee_id.isapre_id:
                    p.isapre_id = p.employee_id.isapre_id.id
                    p.isapre_cotizacion_uf = p.employee_id.isapre_cotizacion_uf
                p.message_post(body='Guardando Histórico.')

    def _compute_report_show_50_por(self):
        adv_var = self.env['ir.config_parameter'].sudo().get_param('report.show.50.por')
        if adv_var == 'True':
            self.report_show_50_por = True
        else:
            self.report_show_50_por = False

    def _compute_report_show_100_por(self):
        adv_var = self.env['ir.config_parameter'].sudo().get_param('report.show.100.por')
        if adv_var == 'True':
            self.report_show_100_por = True
        else:
            self.report_show_100_por = False

    def _compute_report_show_dom_por(self):
        adv_var = self.env['ir.config_parameter'].sudo().get_param('report.show.dom.por')
        if adv_var == 'True':
            self.report_show_dom_por = True
        else:
            self.report_show_dom_por = False

    def _compute_report_note_payslip(self):
        self.report_note_payslip = self.env['ir.config_parameter'].sudo().get_param('report.note.payslip')

    def _compute_report_show_referencia(self):
        adv_var = self.env['ir.config_parameter'].sudo().get_param('report.show.referencia')
        if adv_var == 'True':
            self.report_show_referencia = True
        else:
            self.report_show_referencia = False

    def _compute_sequence(self):
        for i, record in enumerate(self.sorted('id', reverse=True), 1):
            record.sequence = i

    def _compute_leaves(self):
        licencia = self.env.ref('l10n_cl_hr_payroll.LC02')
        vacations1 = self.env.ref('l10n_cl_hr_payroll.LC05')
        vacations2 = self.env.ref('l10n_cl_hr_payroll.LC06')
        total_leaves = self.env['hr.leave'].search([
            ('employee_id', 'in', self.mapped('employee_id.id')),
            ('state', '=', 'validate')
        ])
        add_leaves = self.env['hr.leave.allocation'].search([
            ('employee_id', 'in', self.mapped('employee_id.id')),
            ('holiday_status_id', 'in', [vacations1.id, vacations2.id]),
            ('state', '=', 'validate')
        ])
        for record in self:
            feriados = self.env['hr.holidays.chile'].search([('date', '>=', record.date_from), ('date', '<=', record.date_to)])
            constantes = [f.date[5:] for f in feriados.filtered('constant') if f.date]
            feriados = feriados.filtered(lambda f: (len(f.region_ids) == 0) or record.employee_id.region_id in f.region_ids).mapped('date')
            current_leaves = total_leaves.filtered(lambda l: l.date_from.date() <= record.date_to and l.date_to.date() >= record.date_from and l.employee_id == record.employee_id)
            paid = unpaid = taken = 0
            for leave in current_leaves:
                dt_start = leave.date_from.date() if leave.date_from.date() > record.date_from else record.date_from
                dt_end = leave.date_to.date() if leave.date_to.date() < record.date_to else record.date_to
                weekdays = record.contract_id and record.contract_id.resource_calendar_id and record.contract_id.resource_calendar_id.get_weekdays() or []
                while dt_start <= dt_end:
                    if leave.holiday_status_id == licencia:
                        paid += 1
                    elif dt_start.weekday() in weekdays and (fields.Date.to_string(dt_start) not in feriados) and (fields.Date.to_string(dt_start)[5:] not in constantes):
                        if leave.holiday_status_id not in (vacations1, vacations2, licencia):
                            unpaid += 1
                        elif leave.holiday_status_id in (vacations1, vacations2):
                            taken += 1
                    dt_start += relativedelta(days=1)
            record.paid_leaves_count = paid
            record.unpaid_leaves_count = unpaid
            record.vacations_taken_count = taken
            record.vacations_pending_count = sum(add_leaves.filtered(lambda l: l.employee_id == record.employee_id).mapped('remaining_vacations'))

    def compute_sheet(self):
        self.exe_historic()
        for record in self:
            record.message_post(body=_('Calculada hoja de nómina.'))
        return super(HrPayslip, self).compute_sheet()

    # def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
    @api.onchange('employee_id', 'struct_id', 'contract_id', 'date_from', 'date_to')
    def _onchange_employee(self):
        # defaults
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return {
                'value': {
                    'line_ids': [],
                    'input_line_ids': [(2, x) for x in self.input_line_ids.ids],
                    'worked_days_line_ids': [(2, x) for x in self.worked_days_line_ids.ids],
                    'name': '',
                }
            }
        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        contracts = employee._get_contracts(date_from, date_to)
        input_line_ids = self.get_inputs(contracts, self.date_from, self.date_to)
        super()._onchange_employee()
        self.update({'input_line_ids': [(5, 0, 0)] + [(0, 0, input_line_data) for input_line_data in input_line_ids]})
        self.name = 'Nómina de %s para %s' % (employee.display_name, self.date_from)

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        res = []
        inicio_horas_extras = self.env['ir.config_parameter'].get_param('extra.hours.start', '0')
        if inicio_horas_extras.isdigit():
            inicio_horas_extras = int(inicio_horas_extras)
            if inicio_horas_extras < 0 or inicio_horas_extras > 28:
                raise UserError(_('Parámetro extra.hours.start debe estar entre 0 y 28 (actualmente %d).') % inicio_horas_extras)
        else:
            raise UserError(_('Parámetro extra.hours.start debe ser un número del 0 al 28 (actualmente contiene %s.') % inicio_horas_extras)

        if inicio_horas_extras > 0:
            date_from_he = date_from + relativedelta(months=-1, day=inicio_horas_extras)
            date_to_he = date_from + relativedelta(day=inicio_horas_extras)
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
                hehd_ids = contract.employee_id.balance_ids.filtered(lambda hd: hd.balance_id == he and hd.date_from <= date_to and (not hd.date_to or hd.date_to >= date_from))
                if hehd_ids:
                    # Si existen, usamos solo uno de ese mismo tipo y le modificamos el monto.
                    hehd_ids.write({'amount': horas_extras[he]})
                    # Si son varios del mismo tipo, dejamos solo uno:
                    hehd_ids[1:].unlink()
                else:
                    # Si no existe, lo creamos
                    hehd_ids.create({
                        'employee_id': contract.employee_id.id,
                        'balance_id': he.id,
                        'amount': horas_extras[he],
                        'date_from': date_from,
                        'date_to': date_to
                    })
            for inp in contract.struct_id.input_line_type_ids:
                habydesc = self.env['hr.balance'].search([('inputs_id', '=', inp.id)])
                amount = 0.0

                for hyd in habydesc:
                    hdemployees = self.env['hr.hd'].search([('employee_id', '=', employee_id), ('balance_id', '=', hyd.id),
                                                            ('date_from', '<=', date_to), ('date_to', '=', False)])
                    hdemployees += self.env['hr.hd'].search([('employee_id', '=', employee_id), ('balance_id', '=', hyd.id),
                                                             ('date_from', '<=', date_to), ('date_to', '>=', date_from)])

                    for emphyd in hdemployees:
                        amount += emphyd.amount

                prestamos = self.env['hr.borrow'].search([('inputs_id', '=', inp.id), ('employee_id', '=', employee_id)])
                cuotas = prestamos.mapped('line_ids').filtered(lambda l: date_from <= l.date_due <= date_to and not l.cobrado)
                amount += sum(cuotas.mapped('amount'))
                res.append({
                    'input_type_id': inp.id,
                    'amount': amount,
                    'contract_id': contract.id,
                })
        return res

    def action_payslip_done(self):
        rule_input_obj = self.env['hr.payslip.input.type']
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
        """ Se sobrecarga para excluir los roles privados a usuarios que no
        tengan permisos de gerente de nómina (group_hr_manager) """
        res = super(HrPayslip, self).search(*args, **kargs)
        if not self.env.user.has_group('hr.group_hr_manager'):
            res = res.filtered(lambda s: not s.employee_id.private_role)
        return res

    @api.model
    def convert(self, *args, **kwargs):
        """ Movido acá para conveniencia de llamarlo en los reportes """
        return amount_to_text_es(*args, **kwargs)
