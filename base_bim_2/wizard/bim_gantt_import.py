import base64
import datetime
from bs4 import BeautifulSoup

from odoo import fields, models
from odoo.exceptions import ValidationError

MS_PREDECESSOR_MAPPING = {
    '0': 'ff',
    '1': 'fs',
    '2': 'sf',
    '3': 'ss',
}


class BimGanttImport(models.TransientModel):
    _name = 'bim.gantt.import'
    _description = 'Importador de Gantt'

    budget_id = fields.Many2one('bim.budget', 'Presupuesto')
    filename = fields.Char('Nombre archivo XML')
    xml_file = fields.Binary('Archivo XML', required=True)
    gantt_type = fields.Selection([('ms', 'Microsoft Project')], 'Tipo de Gantt', default='ms', required=True)

    def print_xml(self):
        if self.gantt_type == 'ms':
            return self.load_gantt_ms()
        else:
            raise ValidationError('Debe escoger algún formato de gantt para importar.')

    def load_gantt_ms(self):
        dt_format = '%Y-%m-%dT%H:%M:%S'
        working_hours = self.env.company.working_hours
        file_content = base64.b64decode(self.xml_file)
        content = BeautifulSoup(file_content, 'lxml')
        tasks = content.find_all('task')
        errors = []
        self.budget_id.do_compute = False
        for task in tasks[::-1]:
            wbs = task.find('wbs')
            # Saltando las 2 primeras tareas
            if wbs and wbs.text in ['0', '1']:
                continue
            concept_id = int(task.find('uid').text)
            concept = self.budget_id.concept_ids.filtered_domain([('export_tmp_id', '=', concept_id), ('type', 'in', ['chapter','departure'])])
            if not concept:
                errors.append('<p>El archivo XML contiene la tarea de ID %d, de nombre %s, y no se encuentra en el presupuesto.</p>' % (concept_id, task.find('name').text))
                continue
            predecessors_vals = []
            predecessors = task.find_all('predecessorlink')
            for pred in predecessors:
                pred_concept_id = int(pred.find('predecessoruid').text)
                pred_concept = self.env['bim.concepts'].search([('budget_id', '=', self.budget_id.id),('export_tmp_id', '=', pred_concept_id), ('type', 'in', ['chapter','departure'])])
                if not pred_concept:
                    pred_name = 'N/A'
                    for ptask in tasks:
                        if ptask.find('uid').text == pred.find('predecessoruid').text:
                            pred_name = ptask.find('name').text
                            break
                    errors.append('<p>El archivo XML indica tener la tarea de ID %d de nombre %s como predecesora de la tarea de ID %d y nombre %s, y esta predecesora no existe en el presupuesto.</p>' % (pred_concept_id, pred_name, concept_id, task.find('name').text))
                    continue
                predecessors_vals.append((0, 0, {
                    'name': pred_concept.id,
                    'difference': (float(pred.find('linklag').text) / 600 / working_hours) if working_hours else 0,
                    'pred_type': MS_PREDECESSOR_MAPPING.get(pred.find('type').text)
                }))
            concept.bim_predecessor_concept_ids.unlink()
            concept.write({
                'acs_date_start': datetime.datetime.strptime(task.find('start').text, dt_format),
                'acs_date_end': datetime.datetime.strptime(task.find('finish').text, dt_format),
                'bim_predecessor_concept_ids': predecessors_vals,
            })
        if errors:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Importación con detalles',
                    'message': ''.join(errors) + '<b>Cierra el wizard para ver los cambios.</b>',
                    'sticky': True,
                    'type': 'warning',
                }
            }
        return {'type': 'ir.actions.act_window_close'}
