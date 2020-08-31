##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Payroll Chile MFH',
    'category': 'Localization',
    'author':'''Marlon Falcón Hernández''',
    'website': 'http://www.falconsolutions.cl',
    'depends': ['hr', 'hr_payroll', 'hr_work_entry', 'analytic'],
    # 'depends': ['hr_payroll', 'l10n_cl_base', 'l10n_cl_capital', 'hr_holidays', 'hr', 'mail'],
    'license': 'AGPL-3',
    'version': '13.0.1',
    'category': 'Payroll Localization',
    'summary':'Módulo de Recursos Humanos Chile',
    'description': """
Recursos Humanos.
============================
    * Historial de Nómina.\n
    * Exportación a Previred.\n
    * Nómina Chilena.\n
    * Feriados Chile.\n
    * Vacaciones.\n
    * Finiquito.\n
    """,
    'data': [
        'data/ir_sequence.xml',
        'data/resource_calendar_data.xml',
        'data/hr_work_entry_type.xml',
        'data/hr_salary_rule_category.xml',
        'data/hr_move_type.xml',
        'security/hr_payroll_security.xml',
        'security/res_groups.xml',
        # 'security/rules.xml',
        'data/ir.config_parameter.xml',
        'data/l10n_cl_hr_payroll_data.xml',
        'data/hr_centroscostos_data.xml',
        'data/ir_cron.xml',
        'data/hr_leave_type.xml',
        'views/hr_employee.xml',
        'views/hr_balance.xml',
        'views/hr_stats.xml',
        'views/hr_salary_rule_view.xml',
        'views/hr_payslip_view.xml',
        'views/hr_afp_view.xml',
        'views/hr_payslip_run_view.xml',
        # 'views/hr_contribution_register_view.xml',
        'wizard/hr_salary_employee_month.xml',
        'views/hr_move.xml',
        'views/hr_borrow.xml',
        'views/res_company.xml',
        'views/hr_centroscostos.xml',
        'views/hr_payroll_historic_view.xml',
        'views/pago_previred_view.xml',
        'views/hr_contract_view.xml',
        'views/hr_holidays_chile_view.xml',
        'views/hr_leave.xml',
        'views/holidays_settings.xml',
        'views/hr_holidays_vacations.xml',
        # 'views/res_config.xml',
        'views/hr_bonus.xml',
        'security/ir.model.access.csv',
        # 'wizard/hr_bonus_employee_view.xml',
        # 'wizard/hr_assign_employee_view.xml',
        'wizard/hr_previred_report_wizard_view.xml',
        'wizard/hr_remuneration_report_wizard_view.xml',
        'wizard/hr_historic_wizard_view.xml',
        # 'wizard/hr_employee_leaves_summary.xml',
        'wizard/hr_payslip_employees.xml',
        'report/report_hrsalarybymonth.xml',
        # 'report/certificado_vacaciones.xml',
        # 'report/certificado_sueldo.xml',
        # 'report/report_vacations.xml',
        # 'report/report_antiquity.xml',
        'report/report_payslip.xml',
        # 'report/bonus_sheet.xml',
    ],
    'external_dependencies': {
        'python': ['beautifulsoup4']
    },
    'images': ['static/description/banner.jpg'],
    'installable': True,
}
