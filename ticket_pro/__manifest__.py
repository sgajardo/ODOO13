# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2019 Marlon Falcón Hernandez
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
    'name': 'Ticket Pro - MFH',
    'version': '13.0.1.0',
    'author': 'Ynext SpA',
    'maintainer': 'Ynext SpA',
    'website': 'http://www.ynext.cl',
    'license': 'AGPL-3',
    'category': 'Settings',
    'summary': 'Ticket',
    'depends': ['base', 'mail'],
    'data': [
        'security/groups.xml',
        'reports/report_tickets_details.xml',
        'reports/report_ticket_notes.xml',
        'views/ticket_pro_view.xml',
        'views/change_project_view.xml',
        'views/ticket_category_view.xml',
        'views/res_users.xml',
        'views/assets.xml',
        'views/ticket_note_view.xml',
        'wizards/report_tickets_pro_wzd.xml',
        'data/ir_sequence.xml',
        'data/ticket_pro_data.xml',
        'data/template_response.xml',
        'data/template_response_open.xml',
        'data/template_close.xml',
        'data/template_response_change.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
