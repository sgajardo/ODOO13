from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class HrSalaryRule(models.Model):

    _inherit = 'hr.salary.rule'
    _description = 'Salary Rule'

    date_start = fields.Date('Fecha Inicio',  help="Fecha de inicio de la regla salarial")
    date_end = fields.Date('Fecha Fin',  help="Fecha del fin de la regla salarial")

    chile_type = fields.Selection([('FI', 'Fijo Imponible'),
                                   ('VI', 'Variable Imponible'),
                                   ('ANI', 'Asignaciones No Imponible')],
                                  'Tipo Chile')

    def _satisfy_condition(self, localdict):
        self.ensure_one()
        if self.condition_select == 'none':
            return True
        if self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range, localdict)
                return self.condition_range_min <= result <= self.condition_range_max
            except Exception as e:
                raise UserError(_('Wrong range condition defined for salary rule %s (%s).\nError: %s') % (self.name, self.code, e))
        else:  # python code
            try:
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return localdict.get('result', False)
            except Exception as e:
                raise UserError(_('Código python erróneo en condición de la regla salarial %s (%s).\nError: %s') % (self.name, self.code, e))
