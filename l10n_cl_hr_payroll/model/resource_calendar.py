from odoo import models


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def get_weekdays(self):
        return [int(i) for i in set(self.attendance_ids.mapped('dayofweek'))]
