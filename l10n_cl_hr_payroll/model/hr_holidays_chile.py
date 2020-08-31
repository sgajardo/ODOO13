# coding: utf-8
from odoo import fields, models


class HrHolidaysChile(models.Model):
    _name = 'hr.holidays.chile'
    _description = 'Feriados'

    def _get_region_domain(self):
        u""" Devuelve dominio con regiones chilenas """
        return [('country_id', '=', self.env.ref('base.cl').id), ('type', '=', 'view')]

    name = fields.Char('Nombre', required=True)
    date = fields.Date('Fecha', required=True)
    constant = fields.Boolean('Constante', default=True)
    region_ids = fields.Many2many('res.country.state', string='Regiones', domain=_get_region_domain,
                                         help=u'Indica las regiones en las que es válido este feriado,'
                                        ' si no se indica región, es un feriado nacional.')

    _sql_constraints = [
        ('unique_date', 'unique(date)','No pueden haber feriados con la misma fecha')
    ]
