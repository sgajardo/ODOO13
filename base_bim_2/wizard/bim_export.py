import base64

from odoo import _, fields, models
from odoo.exceptions import ValidationError

CNPT_TYPES = ['not_used', 'labor', 'equip', 'material']


class BimExportWizard(models.TransientModel):
    _name = 'bim.export.wizard'
    _description = 'Exportador de presupuestos'

    version = fields.Selection([('bc3', 'BC3 2012')], 'Versión', default='bc3', required=True)
    budget_id = fields.Many2one('bim.budget', 'Presupuesto', required=True)

    def export_file(self):
        if self.version == 'bc3':
            return self.export_bc3()
        raise ValidationError(_('No implementado'))

    def export_bc3(self):
        data = '~V|%s|FIEBDC-3/2012|Odoo13.0||ANSI|\n' % self.env.company.name
        data += '~K|\\2\\2\\3\\2\\2\\2\\2\\%s\\|0|\n' % self.budget_id.currency_id.name
        chapters = self.env['bim.concepts'].search([('type', '=', 'chapter'),
                                                    ('parent_id', '=', False),
                                                    ('budget_id', '=', self.budget_id.id)])
        added_concepts = []
        for chapter in chapters:
            data += self.recursive_concept_data(chapter, added_concepts, root_chapter=True)

        data += '~C|%s##|||%s|%s|0|\n' % (self.budget_id.name.replace(" ", "_"),
                                          self.budget_id.balance,
                                          fields.Date.today().strftime('%d%m%Y'))
        data += '~D|%s##|%s|\n' % (self.budget_id.name, ''.join('%s\\1\\%.0f\\' % (concpt.code, concpt.quantity) for concpt in self.budget_id.concept_ids if not concpt.parent_id))

        attach_vals = {
            'name': '%s.bc3' % self.budget_id.name,
            'datas': base64.b64encode(data.encode('latin-1')),
            'res_model': 'bim.budget',
            'res_id': self.budget_id.id,
            'store_fname': '%s.bc3' % self.budget_id.name,
        }
        doc_id = self.env['ir.attachment'].create(attach_vals)
        return {
            'name': 'Facturas',
            'type': 'ir.actions.act_url',
            'url': 'web/content/%d?download=true' % doc_id.id,
            'close_on_report_download': True,
            'target': 'self',
        }

    def recursive_concept_data(self, concept, added_concepts, root_chapter=False):
        if concept.code in added_concepts:
            return ''
        today = fields.Date.today().strftime('%d%m%Y')
        data = '~C|%s%s|%s|%s|%.2f|%s|%d|\n' % (concept.code,
                                                '#' if root_chapter else '',
                                                concept.uom_id.name or '',
                                                concept.name,
                                                concept.amount_fixed,
                                                today,
                                                concept.type in CNPT_TYPES and CNPT_TYPES.index(concept.type) or 0)
        added_concepts.append(concept.code)
        if concept.child_ids:
            children_data = ''.join('%s\\1\\%.3f\\' % (child.code, child.quantity) for child in concept.child_ids)
            data += '~D|%s#|%s|\n' % (concept.code, children_data)
            for child in concept.child_ids:
                data += self.recursive_concept_data(child, added_concepts)
        if concept.note:
            data += '~T|%s%s|%s|\n' % (concept.code, '#' if concept.type == 'chapter' else '', concept.note)
        if concept.measuring_ids:
            data += '~M|%s%s\\%s|%d\\%d\\|%d|%s\\|\n' % (concept.parent_id and concept.parent_id.code, '#' if concept.parent_id.type == 'chapter' else '', concept.code,
                                                         concept.parent_id.sequence, concept.sequence, round(sum(concept.measuring_ids.mapped('amount_subtotal'))),
                                                         '\\'.join('%s\\%s\\%.0f\\%.0f\\%.0f\\%.0f' % ('3' if m.formula else '', m.name, m.qty, m.length, m.width, m.height) for m in concept.measuring_ids))
        return data
