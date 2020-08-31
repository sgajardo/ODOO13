# coding: utf-8
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    date_start = fields.Date(track_visibility='onchange')
    date_end = fields.Date(track_visibility='onchange')
    complete_name = fields.Char(related='employee_id.display_name')
    last_name = fields.Char(related='employee_id.last_name')
    working_hours = fields.Many2one('resource.calendar', default=lambda self: self.env.ref('l10n_cl_hr_payroll.hr_resource_monthly', raise_if_not_found=False))
    struct_id = fields.Many2one('hr.payroll.structure', default=lambda self: self.env.ref('l10n_cl_hr_payroll.hr_struct_cl', raise_if_not_found=False))
    type_id = fields.Many2one('hr.contract.type', 'Tipo de Contrato', default=lambda self: self.env.ref('l10n_cl_hr_payroll.hr_contract_type_not_defined', raise_if_not_found=False))
    parent_id = fields.Many2one('hr.contract', 'Anexado a', track_visibility='onchange')
    child_ids = fields.One2many('hr.contract', 'parent_id', 'Anexos', copy=False)
    # date_exp = fields.Date(track_visibility='onchange', string='Fecha Vencimiento', compute='_compute_giveme_date_exp')
    rut = fields.Char(related='employee_id.identification_id')

    # @api.depends('type_id')
    # def _compute_giveme_date_exp(self):
    #     for record in self:
    #         if record.type_id and 'Indefinido' not in record.type_id.name:
    #             record.date_exp = record.date_start + relativedelta(months=3)

    # Campos para vacaciones
    vacation_date_start = fields.Date(u'Fecha Inicial de Cálculo',
                                      help=u'Fecha desde la que se empezará a '
                                     'tomar en cuenta el cálculo de sus vacaciones. '
                                     'Si no se indica, se tomará la fecha inicial'
                                     ' de este contrato.', track_visibility='onchange')
    progressive_days = fields.Float(u'Días progresivos', default=0.0,
                                    help=u'Días que se otorgan anualmente como'
                                   ' vacaciones extras por antigüedad. Los días'
                                   ' que se carguen acá serán asignados automáticamente'
                                   ' por la acción planificada y volverán ser llevados'
                                   ' a cero una vez ejecutada la misma.', track_visibility='onchange')

    @api.constrains('vacation_date_start')
    def _check_vacation_start(self):
        today = fields.Date.today()
        for record in self:
            if record.vacation_date_start > today:
                raise ValidationError(_('Fecha inicial de vacaciones no puede ser mayor al día de hoy.'))

    @api.onchange('employee_id')
    def _onchange_employee_anexo(self):
        return {
            'value': {
                'parent_id': False
            }
        }
