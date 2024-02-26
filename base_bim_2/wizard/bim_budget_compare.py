import base64
import io

import xlwt
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BimBudgetCompare(models.TransientModel):
    _name = 'bim.budget.compare.wizard'
    _description = 'Comparador de presupuestos'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ids = self.env.context.get('active_ids', [])
        budgets = self.env['bim.budget'].browse(ids)
        if len(budgets) != 2:
            raise ValidationError('Debe escoger solo 2 presupuestos para poder comparar.')
        res.update({
            'origin_budget_id': budgets[0].id,
            'compare_budget_id': budgets[1].id,
        })
        return res

    origin_budget_id = fields.Many2one('bim.budget', 'Presupuesto origen', readonly=True)
    compare_budget_id = fields.Many2one('bim.budget', 'Presupuesto a comparar', readonly=True)
    compare = fields.Selection([('chapter', 'Capítulos'),
                                ('departure', 'Partidas'),
                                ('both', 'Todo')], 'Comparar', default='both', required=True)
    budget_type = fields.Selection([('budget', 'Presupuesto'),
                                    ('cert', 'Certificación')], 'Tipo', default='budget', required=True)
    price = fields.Boolean('Precio', default=True)
    text = fields.Boolean('Texto', default=True)
    quantity = fields.Boolean('Cantidad', default=True)
    measure = fields.Boolean('Línea de medición', default=True)

    @api.onchange('measure')
    def _onchange_measure(self):
        if self.measure:
            self.quantity = True

    @api.onchange('quantity')
    def _onchange_quantity(self):
        if self.measure and not self.quantity:
            return {
                'warning': {
                    'message': '"Cantidad" es obligatoria si se marca "Línea de medición".'
                },
                'value': {
                    'quantity': True,
                }
            }

    def switch_budgets(self):
        """ Cambia entre los presupuestos a comparar """
        self.origin_budget_id, self.compare_budget_id = self.compare_budget_id, self.origin_budget_id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Comparar presupuestos',
            'res_model': 'bim.budget.compare.wizard',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }

    def print_excel(self):
        if not self.price and not self.text and not self.quantity and not self.measure:
            raise ValidationError('Debe escoger al menos una opción a comparar entre precio, texto, cantidad o línea de medición.')

        # Estilos a usar
        normal_right = xlwt.easyxf('align: wrap yes, horiz right;')
        bold_left = xlwt.easyxf('align: wrap yes, horiz left; font: bold on;')
        bold_right = xlwt.easyxf('align: wrap yes, horiz right; font: bold on;')
        red_left = xlwt.easyxf('align: wrap yes, horiz left; font: colour red;')
        red_bold_left = xlwt.easyxf('align: wrap yes, horiz left; font: colour red, bold on;')
        red_right = xlwt.easyxf('align: wrap yes, horiz right; font: colour red;')
        red_bold_right = xlwt.easyxf('align: wrap yes, horiz right; font: colour red, bold on;')
        separator = xlwt.easyxf('pattern: pattern solid, fore_colour periwinkle;')

        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('Comparación')

        # Anchos
        sheet.col(0).width = 256 * 20
        sheet.col(1).width = 256 * 20
        sheet.col(2).width = 256 * 6
        sheet.col(3).width = 256 * 6
        if self.measure:
            sheet.col(4).width = 256 * 6
            sheet.col(5).width = 256 * 3
            sheet.col(6).width = 256 * 5
            sheet.col(7).width = 256 * 5
            sheet.col(8).width = 256 * 5
            sheet.col(9).width = 256 * 6
        else:
            sheet.col(4).width = sheet.col(5).width = sheet.col(6).width = sheet.col(7).width = sheet.col(8).width = sheet.col(9).width = 1
        sheet.col(10).width = 256
        sheet.col(11).width = 256 * 20
        sheet.col(12).width = 256 * 6
        sheet.col(13).width = 256 * 6
        if self.measure:
            sheet.col(14).width = 256 * 6
            sheet.col(15).width = 256 * 3
            sheet.col(16).width = 256 * 5
            sheet.col(17).width = 256 * 5
            sheet.col(18).width = 256 * 5
            sheet.col(19).width = 256 * 6
        else:
            sheet.col(14).width = sheet.col(15).width = sheet.col(16).width = sheet.col(17).width = sheet.col(18).width = sheet.col(19).width = 1
        sheet.col(20).width = 256
        sheet.col(21).width = 256 * 20
        sheet.col(22).width = 256 * 6
        sheet.col(23).width = 256 * 6
        if self.measure:
            sheet.col(24).width = 256 * 6
            sheet.col(25).width = 256 * 3
            sheet.col(26).width = 256 * 5
            sheet.col(27).width = 256 * 5
            sheet.col(28).width = 256 * 5
            sheet.col(29).width = 256 * 6

        # Cabecera
        sheet.write(0, 2, 'Cant', bold_left)
        sheet.write(0, 3, 'Prec', bold_left)
        if self.measure:
            sheet.write(0, 4, 'Esp', bold_left)
            sheet.write(0, 5, 'n', bold_right)
            sheet.write(0, 6, 'x', bold_right)
            sheet.write(0, 7, 'y', bold_right)
            sheet.write(0, 8, 'z', bold_right)
            sheet.write(0, 9, 'total', bold_right)
        sheet.write(0, 10, '', separator)
        sheet.write(0, 12, 'Cant', bold_left)
        sheet.write(0, 13, 'Prec', bold_left)
        if self.measure:
            sheet.write(0, 14, 'Esp', bold_left)
            sheet.write(0, 15, 'n', bold_right)
            sheet.write(0, 16, 'x', bold_right)
            sheet.write(0, 17, 'y', bold_right)
            sheet.write(0, 18, 'z', bold_right)
            sheet.write(0, 19, 'total', bold_right)
        sheet.write(0, 20, '', separator)
        sheet.write(0, 22, 'Cant', bold_left)
        sheet.write(0, 23, 'Prec', bold_left)
        if self.measure:
            sheet.write(0, 24, 'Esp', bold_left)
            sheet.write(0, 25, 'n', bold_right)
            sheet.write(0, 26, 'x', bold_right)
            sheet.write(0, 27, 'y', bold_right)
            sheet.write(0, 28, 'z', bold_right)
            sheet.write(0, 29, 'total', bold_right)
        sheet.write(1, 0, self.origin_budget_id.display_name, bold_left)
        sheet.write(1, 10, '', separator)
        sheet.write(1, 11, self.compare_budget_id.display_name, bold_left)
        sheet.write(1, 20, '', separator)
        sheet.write(1, 21, 'Diferencia', bold_left)

        types = ['chapter', 'departure'] if self.compare == 'both' else [self.compare]
        row = 2
        # Buscamos códigos de conceptos en común (los repetidos dañan todo)
        for origin_concept in self.origin_budget_id.concept_ids:
            if origin_concept.type not in types:
                continue
            diferences1 = []
            diferences2 = []
            if self.budget_type == 'budget':
                origin_quantity = origin_concept.quantity
                origin_price = origin_concept.amount_fixed if origin_concept.amount_type == 'fixed' else origin_concept.amount_compute
            else:
                origin_quantity = origin_concept.quantity_cert
                origin_price = origin_concept.amount_fixed_cert if origin_concept.amount_type == 'fixed' else origin_concept.amount_compute_cert
            sheet.write(row, 0, origin_concept.code, bold_left)
            sheet.write(row, 1, origin_concept.name, bold_left)
            sheet.write(row, 2, origin_quantity, normal_right)
            sheet.write(row, 3, origin_price, normal_right)
            # No olvidemos los separadores
            sheet.write(row, 10, '', separator)
            sheet.write(row, 20, '', separator)
            # Líneas de medición
            measures = []
            if self.measure:
                for i, line in enumerate(origin_concept.measuring_ids, 1):
                    sheet.write(row + i, 4, line.name)
                    sheet.write(row + i, 5, line.qty, normal_right)
                    sheet.write(row + i, 6, line.length, normal_right)
                    sheet.write(row + i, 7, line.width, normal_right)
                    sheet.write(row + i, 8, line.height, normal_right)
                    sheet.write(row + i, 9, line.amount_subtotal, normal_right)
                    sheet.write(row + i, 10, '', separator)
                    sheet.write(row + i, 20, '', separator)
                    measures.append(line.name)
            for compare_concept in self.compare_budget_id.concept_ids:
                if compare_concept.type not in types:
                    continue
                if origin_concept.code == compare_concept.code:
                    # Hora de buscar diferencias
                    if self.text and origin_concept.name != compare_concept.name:
                        diferences1.append((compare_concept.name, red_bold_left))
                    else:
                        diferences1.append((compare_concept.name, bold_left))
                    diferences2.append((compare_concept.name, red_bold_left if (origin_concept.sequence != compare_concept.sequence or origin_concept.parent_id.code != compare_concept.parent_id.code) else bold_left))

                    if self.budget_type == 'budget':
                        compare_quantity = compare_concept.quantity
                        compare_price = compare_concept.amount_fixed if compare_concept.amount_type == 'fixed' else compare_concept.amount_compute
                    else:
                        compare_quantity = compare_concept.quantity_cert
                        compare_price = compare_concept.amount_fixed_cert if compare_concept.amount_type == 'fixed' else compare_concept.amount_compute_cert

                    if self.quantity and origin_quantity != compare_quantity:
                        diferences1.append((compare_quantity, red_right))
                        diferences2.append((compare_quantity - origin_quantity, red_right))
                    else:
                        diferences1.append((compare_quantity, normal_right))
                        diferences2.append((compare_quantity - origin_quantity, normal_right))

                    if self.price and origin_price != compare_price:
                        diferences1.append((compare_price, red_right))
                        diferences2.append((compare_price - origin_price, red_right))
                    else:
                        diferences1.append((compare_price, normal_right))
                        diferences2.append((compare_price - origin_price, normal_right))

                    # Líneas de medición
                    if self.measure:
                        for line in compare_concept.measuring_ids:
                            try:
                                i = measures.index(line.name) + 1
                            except ValueError:
                                continue
                            try:
                                sheet.write(row + i, 14, line.name)
                                sheet.write(row + i, 15, line.qty, normal_right)
                                sheet.write(row + i, 16, line.length, normal_right)
                                sheet.write(row + i, 17, line.width, normal_right)
                                sheet.write(row + i, 18, line.height, normal_right)
                                sheet.write(row + i, 19, line.amount_subtotal, normal_right)
                                sheet.write(row + i, 24, line.name)
                                sheet.write(row + i, 25, line.qty, normal_right)
                                sheet.write(row + i, 26, line.length, normal_right)
                                sheet.write(row + i, 27, line.width, normal_right)
                                sheet.write(row + i, 28, line.height, normal_right)
                                sheet.write(row + i, 29, line.amount_subtotal, normal_right)
                            except:
                                pass

                    break  # Encontré el que coincide en código, no buscaré mas...

            if diferences1:
                for i, (value, style) in enumerate(diferences1, 11):
                    sheet.write(row, i, value, style)
                for i, (value, style) in enumerate(diferences2, 21):
                    sheet.write(row, i, value, style)

            # pasamos a la siguiente fila
            row += 1 + (len(origin_concept.measuring_ids) if self.measure else 0)

        if row == 2:
            raise ValidationError('No hay conceptos en común para comparar.')

        # Unos cuantos separadores mas, hasta hacer al menos 50
        for i in range(row, 53):
            sheet.write(i, 10, '', separator)
            sheet.write(i, 20, '', separator)

        stream = io.BytesIO()
        workbook.save(stream)
        stream.seek(0)

        filename = 'Comparacion%s_%s_%s.xls' % ('_certificacion' if self.budget_type == 'cert' else '', self.origin_budget_id.code, self.compare_budget_id.code)
        attach_vals = {
            'name': filename,
            'datas': base64.b64encode(stream.getvalue()),
            'store_fname': filename,
        }
        doc_id = self.env['ir.attachment'].create(attach_vals)
        return {
            'name': filename,
            'type': 'ir.actions.act_url',
            'url': 'web/content/%d?download=true' % doc_id.id,
            'close_on_report_download': True,
            'target': 'self',
        }
