# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2017 Marlon Falcón Hernandez
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
    'name': 'BASE BIM 2.0',
    'version': '13.0.0.1',
    'author': "Ynext",
    'maintainer': 'Ynext',
    'website': 'http://www.ynext.cl',
    'license': 'AGPL-3',
    'category': 'Construction',
    'summary': 'Módulo de cálculo de presupuesto',
    'depends': [
        'account',
        'analytic',
        'base',
        'hr',
        'mail',
        'product',
        'purchase',
        'stock',
        'sale',
        'sale_management',
        'hr_attendance',
        'uom',
        'folder_view',
        'hierarchy_view',
        'web_digital_sign',
        'purchase_requisition',
    ],
    'description': """
BIM 2.0
============================
* Obras
* Presupuestos
* Departamentos
        """,
    'data': [
        'data/ir_cron.xml',
        'data/ir_sequence.xml',
        'data/ir_config_parameter.xml',
        'data/product_data.xml',
        'data/dp_data.xml',
        'data/formula_data.xml',
        'data/bim_assets_data.xml',
        'data/bim_budget_space.xml',
        'data/maintenance_mail_template.xml',
        'data/data_tags_day_maintenance.xml',
        'security/security_groups_bim.xml',
        'wizard/bim_project_stock_location_view.xml',
        'wizard/create_purchase_wizard_view.xml',
        'wizard/load_employees_view.xml',
        'wizard/load_week_hours_view.xml',
        'wizard/bim_budget_report.xml',
        'wizard/bim_certification_report.xml',
        'wizard/bim_resource_report.xml',
        'wizard/bim_clone_budget.xml',
        'wizard/bim_budget_stage_generate.xml',
        'wizard/bim_certification_msg_wizard.xml',
        'wizard/load_template_checklist.xml',
        'wizard/copy_measures.xml',
        'wizard/load_resource_purchase_requisition.xml',
        'wizard/bim_purchase_requisition_space.xml',
        'wizard/bim_ajust_budget_wzd.xml',
        'wizard/bim_in_out_stock_mobile.xml',
        'wizard/bim_price_massive_wzd.xml',
        'views/menuitems_view.xml',
        'wizard/bim_import.xml',
        'wizard/bim_export.xml',
        'wizard/bim_stock_report.xml',
        'wizard/bim_paidstate_wizard.xml',
        'views/bim_miscellaneous_view.xml',
        'views/bim_project_view.xml',
        'views/bim_department_view.xml',
        'views/bim_documentation_view.xml',
        'views/bim_budget_view.xml',
        'views/bim_purchase_requisition_view.xml',
        'views/uom_view.xml',
        'views/stock_view.xml',
        'views/account_move_view.xml',
        'views/paidstate_view.xml',
        'views/bim_maintenance_view.xml',
        'views/product_view.xml',
        'views/bim_project_employee_view.xml',
        'views/bim_project_timesheet_view.xml',
        'views/bim_project_outsourcing_view.xml',
        'views/bim_ite_view.xml',
        'wizard/bim_bc3.xml',
        'wizard/bim_ite.xml',
        'views/bim_concepts_view.xml',
        'views/bim_assets_views.xml',
        'security/ir.model.access.csv',
        'views/bim_config.xml',
        'views/bim_task_view.xml',
        'views/assets.xml',
        'views/bim_checklist_views.xml',
        'views/bim_mobile_warehouse_view.xml',
        'views/work_order_views.xml',
        # 'views/bim_massive_certification_view.xml',
        'views/bim_massive_certification_by_line_view.xml',
        'reports/reports.xml',
        'reports/budget_report.xml',
        'reports/summary_report.xml',
        'reports/resource_report.xml',
        'reports/checklist_report.xml',
        'reports/certification_report.xml',
        'reports/origin_cert_report.xml',
        'reports/compare_cert_report.xml',
        'reports/real_execute_report.xml',
        'reports/report_work_order.xml',
        'reports/maintenance_report.xml',
        'data/mail_template_checklist.xml',
        'reports/budget_notes_report.xml',
        'reports/document_notes_report.xml',
        'views/ticket_bim_view.xml',
        'views/ticket_bim_category_view.xml',
        'data/ticket_bim_data.xml',
        'views/bim_object_view.xml',
        'views/bim_part_view.xml',
        'views/hr_employee_view.xml',
        'views/hr_attendance_view.xml',
        'views/res_partner_view.xml',
        'wizard/bim_budget_compare.xml',
        'wizard/bim_gantt_export.xml',
        'wizard/bim_gantt_import.xml',

    ],
    'qweb': [
        'static/src/xml/*.xml'
    ],
    'installable': True,
    'auto_install': False,
    'demo': [],
    'test': [],
}
