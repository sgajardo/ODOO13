from odoo import api, fields, models


class HrHaberesydesc(models.Model):
    _name = 'hr.balance'
    _description = 'Haberes y Descuentos'
    _order = 'name asc'
    _rec_name = 'desc'

    name = fields.Char('Código', default='Nuevo')
    desc = fields.Char('Glosa', required=True)
    default_value = fields.Float('Valor por Defecto')
    moneda = fields.Selection([('1', 'Pesos'),
                               ('2', 'UF'),
                               ('3', 'Dolar'),
                               ('4', 'Euros')],
                              size=1, default='1')

    um = fields.Selection([('$', '$'),
                           ('u', 'u'),
                           ('%', '%')], default='$')

    por_sueldo_base = fields.Float('% del sueldo base')
    prop_dias_trab = fields.Boolean('Proporcional Días Trabajados')
    horas_extras_50 = fields.Boolean('Horas Extras al 50%')
    horas_extras_100 = fields.Boolean('Horas Extras al 100%')
    tipo = fields.Selection([('0', 'Haberes Imponible'),
                             ('1', 'Haberes No Imponible'),
                             ('2 ', 'Descuentos')], default='0')
    obs = fields.Text('Observación')
    inicializar_0 = fields.Boolean('Inicializar en 0')
    inputs_id = fields.Many2one('hr.payslip.input.type', 'Entrada', required=True)
    active = fields.Boolean('Activo', default=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.balance') or 'Nuevo'
        return super().create(vals)

    def name_get(self):
        res = super().name_get()
        result = []
        for element in res:
            haberesydesr_id = element[0]
            glosa = self.browse(haberesydesr_id).desc
            nombre = self.browse(haberesydesr_id).name
            name = nombre and '[ %s ] %s' % (nombre, glosa) or '%s' % nombre
            result.append((haberesydesr_id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        records = self.search((args or []) + [('desc', operator, name)])
        if records:
            return records.name_get()
        return super().name_search(name, args, operator, limit)
