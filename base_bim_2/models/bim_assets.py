from odoo import api, fields, models


class BimAsset(models.Model):
    _name = 'bim.assets'
    _description = 'Haberes y Descuentos'

    name = fields.Char('Código', translate=True, default='Nuevo')
    desc = fields.Char('Glosa', required=True)
    default_value = fields.Float('Valor por Defecto')

    type = fields.Selection([('M', 'Total Materiales'),
                             ('H', 'Total de Mano de Obra'),
                             ('Q', 'Total de Equipo'),
                             ('S', 'Total de Sub-contratos'),
                             ('T', 'Total de Costos Directos'),
                             ('N', 'Total Neto'),
                             ('O', 'Otros')], size=1, default='N')

    obs = fields.Text('Observación')
    show_on_report = fields.Boolean('Mostrar en reporte', default=True,
                                    help="Indica si desea mostrar el haber/descuento en el informe de presupuesto")

    @api.model_create_multi
    def create(self, vals_list):
        sec_obj = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = sec_obj.next_by_code('bim.assets') or 'Nuevo'
        return super().create(vals_list)

    def name_get(self):
        res = super().name_get()
        result = []
        for element in res:
            haberesydesr_id = element[0]
            glosa = self.browse(haberesydesr_id).desc
            name = element[1] and '[%s] %s' % (element[1], glosa) or '%s' % element[1]
            result.append((haberesydesr_id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        records = self.search((args or []) + [('desc', operator, name)])
        if records:
            return records.name_get()
        return super().name_search(name, args, operator, limit)


class BimHaberesydescTemplateLine(models.Model):
    _name = 'bim.assets.template.line'
    _description = 'Línea de plantilla de Haberes y Descuentos'
    _rec_name = 'asset_id'
    _order = 'sequence'


    @api.model
    def default_get(self, default_fields):
        values = super(BimHaberesydescTemplateLine, self).default_get(default_fields)
        values['sequence'] = len(self.template_id.line_ids) + 1
        return values

    sequence = fields.Integer('Secuencia')
    template_id = fields.Many2one('bim.assets.template', 'Plantilla', ondelete="restrict")
    asset_id = fields.Many2one('bim.assets', 'Haber o Descuento', required=True)
    type = fields.Selection(related='asset_id.type', readonly=True)
    value = fields.Float('Valor')
    affect_ids = fields.Many2many(
        string='Afecta a',
        comodel_name='bim.assets.template.line',
        relation='template_line_assets_afect_rel',
        column1='parent_id',
        column2='child_id',
    )

    _sql_constraints = [
        ('unique_asset_template_line', 'unique(template_id, asset_id)', 'No puede repetirse un Haber o Descuento en la misma plantilla')
    ]

    @api.onchange('asset_id')
    def _onchange_assets(self):
        for record in self:
            record.value = record.asset_id and record.asset_id.default_value or 0.0
            record.sequence = len(record.template_id.line_ids)


class BimHaberesydescTemplate(models.Model):
    _name = 'bim.assets.template'
    _description = 'Plantilla de Haberes y Descuentos'

    @api.model
    def _default_lines(self):
        return [(0, 0, {
            'sequence': i,
            'asset_id': self.env.ref('base_bim_2.had0000%d' % i)
        }) for i in range(1, 5)]

    name = fields.Char('Nombre', required=True)
    desc = fields.Text('Descripción')
    line_ids = fields.One2many('bim.assets.template.line', 'template_id', string='Líneas', required=True, default=_default_lines)
