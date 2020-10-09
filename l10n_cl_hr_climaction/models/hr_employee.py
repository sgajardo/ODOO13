from datetime import timedelta

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

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
        licencias = self.env['hr.holidays'].search([
            ('employee_id', '=', contract.employee_id.id),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
            ('state', '=', 'validate'),
            ('type', '=', 'remove'),
            ('holiday_status_id', '=', self.env.ref('l10n_cl_hr_payroll.LC02').id)
        ])
        dias_licencia = set()
        for licencia in licencias:
            dt_start, dt_end = map(fields.Date.from_string, [licencia.date_from, licencia.date_to])
            while dt_start <= dt_end:
                actual = fields.Date.to_string(dt_start)
                if date_from <= actual <= date_to:
                    dias_licencia.add(actual)
                dt_start += timedelta(days=1)
        return round((nod - len(dias_licencia)) / 30, 5)
