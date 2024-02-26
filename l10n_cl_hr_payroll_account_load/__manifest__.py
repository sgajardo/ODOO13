##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2018 Marlon Falcón Hernandez
#    (<http://www.ynext.cl>).
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
    'name': 'Carga de Cuentas para Centralización MFH',
    'version': '13.0.1.0.0',
    'author': 'Ynext SpA',
    'maintainer': 'Ynext SpA',
    'website': 'http://www.ynext.cl',
    'license': 'AGPL-3',
    'category': 'Human Resources',
    'summary': 'Wizard para cargar en formato Excel las cuentas en las reglas salariales, usado para centralización.',
    'depends': ['l10n_cl_hr_payroll_account'],
    'data': [
        'wizard/hr_salary_rule_account_load.xml',
    ],
    'images': ['static/description/banner.jpg'],
}
