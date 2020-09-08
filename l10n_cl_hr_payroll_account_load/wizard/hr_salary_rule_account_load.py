import base64

import xlrd
from odoo import fields, models
from odoo.exceptions import ValidationError


class HrSalaryRuleAccountLoad(models.TransientModel):
    _name = 'hr.salary.rule.account.load.wizard'
    _description = 'Carga de cuentas en reglas salariales'

    name = fields.Char('Nombre de archivo')
    xls_file = fields.Binary('Archivo Excel', required=True)

    def load_accounts(self):
        data = base64.b64decode(self.xls_file)
        work_book = xlrd.open_workbook(file_contents=data)
        sheet = work_book.sheet_by_index(0)
        index = [sheet.cell_value(0, i) for i in range(sheet.ncols)]
        accounts = {}
        account_obj = self.env['account.account'].sudo()
        rule_obj = self.env['hr.salary.rule']
        account_errors = []
        acc_type_map = {'Debe': 'dcr', 'Haber': 'acr'}
        try:
            rule_code_index = index.index('code')
        except ValueError:
            raise ValidationError('El archivo Excel no tiene la columna "code" (código de regla salarial)')
        try:
            acc_type_index = index.index('Tipo (Debe/Haber)')
        except ValueError:
            raise ValidationError('El archivo Excel no tiene la columna "Tipo (Debe/Haber)"')
        try:
            account_index = index.index('Codigo')
        except ValueError:
            raise ValidationError('El archivo Excel no tiene la columna "Cuenta Contable"')
        for row in range(1, sheet.nrows):
            rule_code = sheet.cell_value(row, rule_code_index)
            acc_type = acc_type_map.get(sheet.cell_value(row, acc_type_index))
            account_name = sheet.cell_value(row, account_index)
            account = accounts.get(account_name)
            if not account and account_name:
                account = account_obj.search([('code', '=', account_name)])
                if not account:
                    if account_name not in account_errors:
                        account_errors.append(account_name)
                    continue
                accounts[account_name] = account
            if rule_code and acc_type and account:
                rule = rule_obj.search([('code', '=', rule_code)], limit=1)
                if not rule:
                    raise ValidationError('La regla salarial con código %s no existe' % rule_code)
                rule.write({'account_type': acc_type, 'account_id': account.id})
        if account_errors:
            raise ValidationError('Las siguientes cuentas contables no existen: \n%s' % '\n'.join(account_errors))
        return {'type': 'ir.actions.act_window_close'}
