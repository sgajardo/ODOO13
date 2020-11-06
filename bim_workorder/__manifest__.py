# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'WORK ORDER BIM 2.0',
    'version': '13.0.0.1',
    'author': "Ynext",
    'maintainer': 'Ynext',
    'website': 'http://www.ynext.cl',
    'license': 'AGPL-3',
    'category': 'Construction',
    'summary': 'Ordenes de trabajo para BIM',
    'depends': [
        'base_bim_2','hr','purchase_requisition'
    ],
    'description': """
BIM 2.0
============================
* Orden de Trabajo
        """,
    'data': [
        'security/ir.model.access.csv',
        'security/groups.xml',
        'data/ir_sequence.xml',
        'wizards/wizard_create_purchase_view.xml',
        'views/bim_workorder_view.xml',
        'views/workorder_timesheet_views.xml',
        'views/bim_project_view.xml',
        'wizards/wizard_workorder_inherit.xml',
        'wizards/wizard_installer.xml',
        'wizards/wizard_mark_all_view.xml',
        'views/stock_picking_view.xml',
        'views/bim_concept_view.xml',
        'views/bim_report_inherit.xml',
        'views/bim_workorder_installers_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'demo': [],
    'test': [],
}
