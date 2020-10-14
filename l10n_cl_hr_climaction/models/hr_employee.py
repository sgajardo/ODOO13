from datetime import timedelta
from calendar import monthrange

from odoo import api, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'


    @api.model
    def factor_isapre(self, contract, date_from, date_to):
        """ Devuelve un float que representa el factor por el que se debe multiplicar
        el monto adicional isapre, tomando en cuenta los días de ausencia por licencia """
        days_of_month = False
        if contract.type_id.codigo == 'diario':
            wdf = date_from if date_from >= contract.date_start else contract.date_start
            wdt = date_to if (not contract.date_end or date_to <= contract.date_end) else contract.date_end
            nod = contract.employee_id.get_workable_days_count(wdf, wdt)
        # Si el contrato empieza antes del periodo de nómina y termina después del periodo de nómina: 30 días
        elif contract.date_start <= date_from and (not contract.date_end or contract.date_end >= date_to):
            nod = 30.0
        # Si el contrato empieza después del periodo de nómina y termina después del periodo: dias del mes - día que comenzó el contrato + 1
        elif contract.date_start > date_from and (not contract.date_end or contract.date_end >= date_to):
            days_of_month = monthrange(date_from.year, date_from.month)[1]
            nod = days_of_month - contract.date_start.day + 1
        # Si el contrato empieza antes del periodo de nómina y termina antes del periodo: día en que termina el contrato
        elif contract.date_start <= date_from and (contract and contract.date_end < date_to):
            nod = contract.date_end.day
        # Si el contrato empieza después y termina antes del periodo de nómina: días entre el periodo del contrato
        else:
            dt_start, dt_end = contract.date_start, contract.date_end or contract.date_start
            nod = (dt_end - dt_start).days + 1
        # Buscamos los días de licencia
        licencias = self.env['hr.leave'].search([
            ('employee_id', '=', contract.employee_id.id),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
            ('state', '=', 'validate'),
            ('holiday_status_id', '=', self.env.ref('l10n_cl_hr_payroll.LC02').id)
        ])
        dias_licencia = set()
        for licencia in licencias:
            dt_start, dt_end = licencia.date_from.date(), licencia.date_to.date()
            while dt_start <= dt_end:
                actual = dt_start
                if date_from <= actual <= date_to:
                    dias_licencia.add(actual)
                dt_start += timedelta(days=1)
        return round((nod - len(dias_licencia)) / (days_of_month or 30), 5)
