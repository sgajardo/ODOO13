from odoo import models


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    def _get_duration(self, date_start, date_stop):
        if not date_start or not date_stop:
            return 0
        wet05 = self.env.ref('l10n_cl_hr_payroll.hr_work_entry_type_05')
        wet06 = self.env.ref('l10n_cl_hr_payroll.hr_work_entry_type_06')
        if self.work_entry_type_id and self.work_entry_type_id.is_leave or self.leave_id or self.work_entry_type_id in [wet05, wet06]:
            calendar = self.contract_id.resource_calendar_id
            if not calendar:
                return 0
            contract_data = self.contract_id.employee_id._get_work_days_data(date_start, date_stop, compute_leaves=False, calendar=calendar)
            return contract_data.get('hours', 0)
        return super()._get_duration(date_start, date_stop)
