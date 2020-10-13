from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    date = fields.Date('Fecha contable', default=fields.Date.today)
    state = fields.Selection(selection_add=[('accounted', 'Centralizado'), ('pago_imposiciones', 'Pago Imposiciones')])
    move_id = fields.Many2one('account.move', 'Asiento')
    journal_id = fields.Many2one('account.journal', 'Diario Pago Nómina')

    def create_moves(self):
        """
        Acción que se ejecuta al presionar el botón ``Centralizar``, creará los
        asientos contables y marcará el proceso de nómina como ``Centralizado``
        """
        for record in self:
            if not record.journal_id:
                raise UserError(_('No se ha especificado el diario'))
            if not record.date:
                raise UserError(_('No se ha especificado la Fecha contable'))
            vals = {
                'name': 'CENTRALIZACION REMUNERACIONES: ' + record.name,
                'ref': record.name,
                'journal_id': record.journal_id.id,
                'date': record.date,
                'narration': 'Nómina de los empleados:\n- {employees}'.format(employees=u'\n- '.join(record.slip_ids.mapped('employee_id.name')))
            }
            vals['line_ids'] = record.group_by_rules(record.slip_ids)
            record.move_id = record.env['account.move'].create(vals)
            record.move_id.post()
        return self.write({'state': 'accounted'})

    def group_by_rules(self, slip_ids):
        """
        Crea los apuntes contables ``account.move.line`` agrupándolos por
        *partner*, *cuenta* y *debe/haber*, si no llega a cuadrar el asiento
        contable, se crea un asiento de ajuste por el total de la diferencia.
        """
        precision = self.env['decimal.precision'].precision_get('Payroll')
        vals = {}
        debit_sum = credit_sum = 0.0
        contract_obj = self.env['hr.contract']
        for slip in slip_ids:
            for line in slip.line_ids.filtered(lambda l: l.total and l.salary_rule_id.account_id):
                # Se toma el partner de la regla salarial, sino del empleado
                if line.salary_rule_id.partner_id:
                    partner = line.salary_rule_id.partner_id.id
                else:
                    partner = slip.employee_id.user_id.partner_id and slip.employee_id.user_id.partner_id.id or None
                # Definiendo la cuenta contable
                account = line.salary_rule_id.account_id and line.salary_rule_id.account_id.id or None
                # Si es gasto, lleva cuenta analítica, tomada de la regla salarial si tiene partner, sino se toma del contrato del empleado
                if line.salary_rule_id.expense:
                    contract = slip.employee_id.contract_id or contract_obj.search([('employee_id', '=', slip.employee_id.id)], limit=1)
                    analytic_account = contract and contract.account_analytic_account_id and contract.account_analytic_account_id.id or None
                    analytic_tag = contract and contract.account_analytic_tag_id and contract.account_analytic_tag_id.id or None
                else:
                    analytic_account = None
                    analytic_tag = None
                if line.salary_rule_id.account_type:
                    account_type = line.salary_rule_id.account_type
                else:
                    raise UserError(_('Debe definir si la regla %s entra por Debe o por Haber') % line.salary_rule_id.name)
                key = '%s/%s/%s' % (partner, account, account_type)
                if key in vals:
                    vals[key][2][account_type == 'dcr' and 'debit' or 'credit'] += line.total
                else:
                    vals.update({key: (0, 0, {
                        'name': line.name or '',
                        'partner_id': partner,
                        'account_id': account,
                        'journal_id': self.journal_id and self.journal_id.id or None,
                        'date_maturity': slip.date_to,
                        'debit': account_type == 'dcr' and line.total or 0.0,
                        'credit': account_type == 'acr' and line.total or 0.0,
                        'analytic_account_id': analytic_account,
                        'analytic_tag_ids': [(4, analytic_tag)],
                    })})
                debit_sum += account_type == 'dcr' and line.total or 0.0
                credit_sum += account_type == 'acr' and line.total or 0.0

        if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
            acc_id = self.journal_id.default_credit_account_id.id
            if not acc_id:
                raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (self.journal_id.name))
            adjust_credit = (0, 0, {
                'name': _('Adjustment Entry'),
                'partner_id': False,
                'account_id': acc_id,
                'journal_id': self.journal_id.id,
                'date': self.date,
                'debit': 0.0,
                'credit': debit_sum - credit_sum,
            })
            vals.update({'ajuste': adjust_credit})

        elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
            acc_id = self.journal_id.default_debit_account_id.id
            if not acc_id:
                raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (self.journal_id.name))
            adjust_debit = (0, 0, {
                'name': _('Adjustment Entry'),
                'partner_id': False,
                'account_id': acc_id,
                'journal_id': self.journal_id.id,
                'date': self.date,
                'debit': credit_sum - debit_sum,
                'credit': 0.0,
            })
            vals.update({'ajuste': adjust_debit})
        if not vals:
            raise UserError(_('No se encontraron reglas configuradas, nada que centralizar'))
        return list(vals.values())

    def cancel_moves(self):
        """
        Devuelve el proceso de nómina a estado *Validar nóminas* y borra los asientos
        contables asociados al mismo.
        """
        for record in self:
            if not record.move_id:
                raise UserError(_('No existe asiento asociado al proceso de nómina'))
            record.move_id.button_cancel()
            record.move_id.with_context(force_delete=True).unlink()
        return self.action_validate()


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    account_analytic_account_id = fields.Many2one('account.analytic.account', related='contract_id.account_analytic_account_id')

    def action_payslip_draft(self):
        """ Se sobrecarga para evitar que se envíen a borrador nóminas que ya
        fueron centralizadas """
        for record in self:
            if record.payslip_run_id and record.payslip_run_id.state == 'accounted':
                raise UserError(_('No se puede devolver a borrador la nómina "%s" ya '
                                  'que pertenece a un Procesamiento de Nómina que está '
                                  'centralizado (%s)') % (record.name, record.payslip_run_id.name))
        return super(HrPayslip, self).action_payslip_draft()
