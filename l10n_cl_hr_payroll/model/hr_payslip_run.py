from odoo import _, fields, models


class HrPayslipRun(models.Model):
    _name = 'hr.payslip.run'
    _inherit = ['hr.payslip.run', 'mail.thread']
    _order = 'date_start desc'

    stats_id = fields.Many2one('hr.stats', 'Indicadores', states={'draft': [('readonly', False)]}, readonly=True, required=True)
    state = fields.Selection(selection_add=[('validate', 'Validar nóminas')], tracking=True)
    employees_count = fields.Char('Empleados', compute='_compute_employees_count')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    amount_total = fields.Monetary('Total a pagar', compute='_compute_amount_total')
    all_validate = fields.Boolean(compute='_compute_all_validate')
    corre_ids = fields.One2many('list.105.corre', 'template_id', string='Listado Correcciones')
    afp_ids = fields.One2many('list.afp', 'template_id', string='Listado AFP')
    isapre_ids = fields.One2many('list.isapre', 'template_id', string='Listado Isapre')
    fonasa_ids = fields.One2many('list.fonasa', 'template_id', string='Listado Fonasa')
    ccaf_ids = fields.One2many('hr.payslip.run.ccaf', 'payslip_run_id', 'Listado CCAF')
    pres_emp_ids = fields.One2many('hr.payslip.run.pres.emp', 'payslip_run_id', 'Listado Préstamos Empresa')
    mutual = fields.Float()
    ccaf_valor = fields.Float('Valor ccaf')
    ccaf_credito = fields.Float('Valor Crédito')
    ccaf = fields.Float('Total ccaf')
    salario_liquido = fields.Float('Salario Líquido')
    mov_emp_ids = fields.One2many('hr.move.run', 'payslip_run_id', 'Movimientos')
    account_analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de costo', readonly=True)

    def exe_historic_all(self):
        for nominas in self.slip_ids:
            nominas.exe_historic()
        self.message_post(body=_("Se guardó el histórico"))

    def crear_pago_previred(self):
        pago_afp = 0
        pago_seguro_cesantia = 0
        pago_fonasa = 0
        asignacion_familiar = 0

        if self.slip_ids:
            for id in self.slip_ids:
                for id_line in id.line_ids:
                    if id_line.code == 'AFP':
                        pago_afp = pago_afp + id_line.amount
                    if id_line.code == 'SECE' or id_line.code == 'SECEEMP':
                        pago_seguro_cesantia = pago_seguro_cesantia + id_line.amount
                    if id_line.code == 'SALUD':
                        pago_fonasa = pago_fonasa + id_line.amount
                    if id_line.code == 'ASIGFAM':
                        asignacion_familiar = asignacion_familiar + id_line.amount

        vals = {
            'journal_imposiciones_id': self.journal_imposiciones_id.id,
            'pago_afp': (pago_afp - pago_seguro_cesantia) if pago_afp > 0 else 0,
            'pago_seguro_cesantia': pago_seguro_cesantia if pago_seguro_cesantia > 0 else 0,
            'pago_fonasa': (pago_fonasa - asignacion_familiar) if pago_fonasa > 0 else 0,
            'origen': self.name,
            'state': 'borrador',
        }
        insert = self.env['pago.previred'].create(vals)
        if insert:
            self.message_post(body=_("Se ha creado el Pago de Previred"))

    def calcular_masivo(self):
        if self.slip_ids:
            contador = 0
            for slip in self.slip_ids:
                contador += 1
                slip.action_payslip_draft()
                slip.action_payslip_done()
            if contador > 0:
                self.message_post(body=_("Se han Calculado masivamente %s Nóminas de Empleado") % contador)

    def _compute_employees_count(self):
        total_employees = self.env['hr.employee'].search_count([('hired', '=', True)])
        for record in self:
            record.employees_count = '%d/%d' % (len(record.slip_ids.mapped('employee_id')), total_employees)

    def _compute_amount_total(self):
        for record in self:
            record.amount_total = round(sum(record.mapped('slip_ids.line_ids').filtered(lambda l: l.code == 'LIQ').mapped('total')))

    def _compute_all_validate(self):
        for record in self:
            record.all_validate = all(slip.state not in ['draft', 'verify', 'cancel'] for slip in record.slip_ids)

    # def validate(self):
    #     self.slip_ids.action_payslip_done()
    #     return self.write({'state': 'validate'})

    def draft_payslip_run(self):
        self.slip_ids.action_payslip_draft()
        return super(HrPayslipRun, self).draft_payslip_run()

    def view_employees_action(self):
        """ Retorna vista kanban de empleados en el procesamiento """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Empleados',
            'res_model': 'hr.employee',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', self.mapped('slip_ids.employee_id.id'))]
        }

    def view_payslips_action(self):
        """ Retorna vista tree de nóminas en el procesamiento """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nóminas',
            'res_model': 'hr.payslip',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.mapped('slip_ids.id'))]
        }


class List105Corre(models.Model):
    _name = 'list.105.corre'
    _description = 'Listado 105 Corregido'

    employee_id = fields.Many2one('hr.employee', 'Empleado')
    colum105 = fields.Selection([('29', '[29] Aporte Seguro Invalidez y Sobrev. Futuro (SIS)'),
                                 ('83', '[83] Código CCAF'),
                                 ('85', '[85] Créditos Personales CCAF'),
                                 ('88', '[88] Descuentos por Seguro de Vida CCAF'),
                                 ('89', '[89] Otros descuentos CCAF'),
                                 ('105', '[105] Centro de Costos-Sucursal-Agencia-Obra-Región')],
                                'Columna')
    notas = fields.Text()
    valor = fields.Float('Valor Corregido')
    template_id = fields.Many2one('hr.payslip.run', 'Payslip_Run', ondelete='cascade')


class ListAfp(models.Model):
    _name = 'list.afp'
    _description = 'Listado AFP'
    _rec_name = 'nombre'

    nombre = fields.Char()
    cantidad = fields.Integer()
    monto = fields.Float()
    template_id = fields.Many2one('hr.payslip.run', 'Payslip_Run', ondelete='cascade')


class ListIsapre(models.Model):
    _name = 'list.isapre'
    _description = 'Listado Isapre'
    _rec_name = 'nombre'

    nombre = fields.Char()
    cantidad = fields.Integer()
    monto = fields.Float()
    template_id = fields.Many2one('hr.payslip.run', 'Payslip_Run', ondelete='cascade')


class ListFonasa(models.Model):
    _name = 'list.fonasa'
    _description = 'Listado Fonasa'
    _rec_name = 'nombre'

    nombre = fields.Char()
    cantidad = fields.Integer()
    monto = fields.Float()
    template_id = fields.Many2one('hr.payslip.run', 'Payslip_Run', ondelete='cascade')


class HrPayslipRunCCAF(models.Model):
    _name = 'hr.payslip.run.ccaf'
    _description = 'Listado CCAF'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', 'Empleado')
    payslip_run_id = fields.Many2one('hr.payslip.run')
    currency_id = fields.Many2one('res.currency', related='payslip_run_id.currency_id')
    amount = fields.Monetary('Monto')


class HrPayslipRunPresEmp(models.Model):
    _name = 'hr.payslip.run.pres.emp'
    _description = 'Listado Préstamo Empresa'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', 'Empleado')
    payslip_run_id = fields.Many2one('hr.payslip.run')
    currency_id = fields.Many2one('res.currency', related='payslip_run_id.currency_id')
    amount = fields.Monetary('Monto')


class HrMoveRun(models.Model):
    _name = 'hr.move.run'
    _description = 'Movimientos'
    _order = 'id desc'

    employee_id = fields.Many2one('hr.employee', 'Empleado')
    date_start = fields.Date('Fecha de Inicio')
    date_end = fields.Date('Fecha de Término')
    tipo = fields.Many2one('hr.move.type', domain=[('is_holiday', '=', False)])
    payslip_run_id = fields.Many2one('hr.payslip.run', 'Payslip_Run', ondelete='cascade')
