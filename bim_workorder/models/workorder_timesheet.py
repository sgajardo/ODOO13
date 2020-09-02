# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WorkorderTimesheet(models.Model):
    _name = 'workorder.timesheet'

    @api.depends('employee_id')
    def _compute_department_id(self):
        for line in self:
            line.department_id = line.employee_id.department_id

    name = fields.Char(string='Detalle')
    date = fields.Date("Fecha", required=True, default=fields.Date.today)
    unit_amount = fields.Float('Duracion', default=0.0)
    resource_id = fields.Many2one('bim.workorder.resources', 'Recurso')
    workorder_id = fields.Many2one('bim.workorder', 'Orden de Trabajo')#, domain=[('allow_timesheets', '=', True)]
    user_id = fields.Many2one('res.users', string="Aprobado por")
    job_id = fields.Many2one('hr.job', string="Puesto de Trabajo")
    employee_id = fields.Many2one('hr.employee', "Empleado", check_company=True)
    department_id = fields.Many2one('hr.department', "Department", compute='_compute_department_id', store=True, compute_sudo=True)
    company_id = fields.Many2one('res.company', string="Compañía", required=True, default=lambda self: self.env.company, readonly=True)

    # ~ @api.onchange('workorder_id')
    # ~ def onchange_workorder_id(self):
        # ~ # force domain on task when project is set
        # ~ if self.workorder_id:
            # ~ if self.workorder_id != self.resource_id.workorder_id:
                # ~ # reset task when changing project
                # ~ self.resource_id = False
            # ~ return {'domain': {
                # ~ 'resource_id': [('workorder_id', '=', self.workorder_id.id)]
            # ~ }}
        # ~ return {'domain': {
            # ~ 'resource_id': [('workorder_id.allow_timesheets', '=', True)]
        # ~ }}


    # ~ @api.onchange('resource_id')
    # ~ def _onchange_resource_id(self):
        # ~ if not self.workorder_id:
            # ~ self.workorder_id = self.resource_id.workorder_id

    # ~ @api.onchange('employee_id')
    # ~ def _onchange_employee_id(self):
        # ~ if self.employee_id:
            # ~ self.user_id = self.employee_id.user_id
        # ~ else:
            # ~ self.user_id = self._default_user()



    # ----------------------------------------------------
    # ORM overrides
    # ----------------------------------------------------

    # ~ @api.model
    # ~ def create(self, values):
        # ~ # compute employee only for timesheet lines, makes no sense for other lines
        # ~ if not values.get('employee_id') and values.get('project_id'):
            # ~ if values.get('user_id'):
                # ~ ts_user_id = values['user_id']
            # ~ else:
                # ~ ts_user_id = self._default_user()
            # ~ values['employee_id'] = self.env['hr.employee'].search([('user_id', '=', ts_user_id)], limit=1).id

        # ~ values = self._timesheet_preprocess(values)
        # ~ result = super(AccountAnalyticLine, self).create(values)
        # ~ if result.project_id:  # applied only for timesheet
            # ~ result._timesheet_postprocess(values)
        # ~ return result

    # ~ def write(self, values):
        # ~ values = self._timesheet_preprocess(values)
        # ~ result = super(AccountAnalyticLine, self).write(values)
        # ~ # applied only for timesheet
        # ~ self.filtered(lambda t: t.project_id)._timesheet_postprocess(values)
        # ~ return result

    # ~ @api.model
    # ~ def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        # ~ """ Set the correct label for `unit_amount`, depending on company UoM """
        # ~ result = super(AccountAnalyticLine, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        # ~ result['arch'] = self._apply_timesheet_label(result['arch'])
        # ~ return result

    # ~ @api.model
    # ~ def _apply_timesheet_label(self, view_arch):
        # ~ doc = etree.XML(view_arch)
        # ~ encoding_uom = self.env.company.timesheet_encode_uom_id
        # ~ for node in doc.xpath("//field[@name='unit_amount'][@widget='timesheet_uom'][not(@string)]"):
            # ~ node.set('string', _('Duration (%s)') % (re.sub(r'[\(\)]', '', encoding_uom.name or '')))
        # ~ return etree.tostring(doc, encoding='unicode')

    # ----------------------------------------------------
    # Business Methods
    # ----------------------------------------------------

    # ~ def _timesheet_get_portal_domain(self):
        # ~ return ['|', '&',
                # ~ ('task_id.project_id.privacy_visibility', '=', 'portal'),
                # ~ ('task_id.project_id.message_partner_ids', 'child_of', [self.env.user.partner_id.commercial_partner_id.id]),
                # ~ '&',
                # ~ ('task_id.project_id.privacy_visibility', '=', 'portal'),
                # ~ ('task_id.message_partner_ids', 'child_of', [self.env.user.partner_id.commercial_partner_id.id])]

    # ~ def _timesheet_preprocess(self, vals):
        # ~ """ Deduce other field values from the one given.
            # ~ Overrride this to compute on the fly some field that can not be computed fields.
            # ~ :param values: dict values for `create`or `write`.
        # ~ """
        # ~ # project implies analytic account
        # ~ if vals.get('project_id') and not vals.get('account_id'):
            # ~ project = self.env['project.project'].browse(vals.get('project_id'))
            # ~ vals['account_id'] = project.analytic_account_id.id
            # ~ vals['company_id'] = project.analytic_account_id.company_id.id
            # ~ if not project.analytic_account_id.active:
                # ~ raise UserError(_('The project you are timesheeting on is not linked to an active analytic account. Set one on the project configuration.'))
        # ~ # employee implies user
        # ~ if vals.get('employee_id') and not vals.get('user_id'):
            # ~ employee = self.env['hr.employee'].browse(vals['employee_id'])
            # ~ vals['user_id'] = employee.user_id.id
        # ~ # force customer partner, from the task or the project
        # ~ if (vals.get('project_id') or vals.get('task_id')) and not vals.get('partner_id'):
            # ~ partner_id = False
            # ~ if vals.get('task_id'):
                # ~ partner_id = self.env['project.task'].browse(vals['task_id']).partner_id.id
            # ~ else:
                # ~ partner_id = self.env['project.project'].browse(vals['project_id']).partner_id.id
            # ~ if partner_id:
                # ~ vals['partner_id'] = partner_id
        # ~ # set timesheet UoM from the AA company (AA implies uom)
        # ~ if 'product_uom_id' not in vals and all([v in vals for v in ['account_id', 'project_id']]):  # project_id required to check this is timesheet flow
            # ~ analytic_account = self.env['account.analytic.account'].sudo().browse(vals['account_id'])
            # ~ vals['product_uom_id'] = analytic_account.company_id.project_time_mode_id.id
        # ~ return vals

    # ~ def _timesheet_postprocess(self, values):
        # ~ """ Hook to update record one by one according to the values of a `write` or a `create`. """
        # ~ sudo_self = self.sudo()  # this creates only one env for all operation that required sudo() in `_timesheet_postprocess_values`override
        # ~ values_to_write = self._timesheet_postprocess_values(values)
        # ~ for timesheet in sudo_self:
            # ~ if values_to_write[timesheet.id]:
                # ~ timesheet.write(values_to_write[timesheet.id])
        # ~ return values

    # ~ def _timesheet_postprocess_values(self, values):
        # ~ """ Get the addionnal values to write on record
            # ~ :param dict values: values for the model's fields, as a dictionary::
                # ~ {'field_name': field_value, ...}
            # ~ :return: a dictionary mapping each record id to its corresponding
                # ~ dictionnary values to write (may be empty).
        # ~ """
        # ~ result = {id_: {} for id_ in self.ids}
        # ~ sudo_self = self.sudo()  # this creates only one env for all operation that required sudo()
        # ~ # (re)compute the amount (depending on unit_amount, employee_id for the cost, and account_id for currency)
        # ~ if any([field_name in values for field_name in ['unit_amount', 'employee_id', 'account_id']]):
            # ~ for timesheet in sudo_self:
                # ~ cost = timesheet.employee_id.timesheet_cost or 0.0
                # ~ amount = -timesheet.unit_amount * cost
                # ~ amount_converted = timesheet.employee_id.currency_id._convert(
                    # ~ amount, timesheet.account_id.currency_id, self.env.company, timesheet.date)
                # ~ result[timesheet.id].update({
                    # ~ 'amount': amount_converted,
                # ~ })
        # ~ return result
