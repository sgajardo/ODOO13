##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2017 Marlon Falcón Hernandez
#    (<http://www.falconsolutions.cl>).
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
    'name': 'Contabilidad en Nómina MFH',
    'version': '13.0.1.0.0',
    'author': 'Falcon Solutions SpA',
    'maintainer': 'Falcon Solutions',
    'website': 'http://www.falconsolutions.cl',
    'license': 'AGPL-3',
    'category': 'Human Resources',
    'summary': 'Centralización de nómina.',
    'depends': ['account', 'hr_payroll', 'l10n_cl_hr_payroll', 'analytic'],
    'data': [
        'views/hr_salary_rule.xml',
        'views/hr_contract.xml',
        'views/hr_payslip.xml',
        'views/hr_payslip_run.xml',
        'views/res_config.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
