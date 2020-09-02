from odoo import models, fields, api
import xlwt
from io import BytesIO
import base64
from datetime import datetime

class BimCertificationReportWizard(models.TransientModel):
    _name = "bim.certification.report.wizard"
    _description = "Wizard Report Certification"

    @api.model
    def default_get(self, fields):
        res = super(BimCertificationReportWizard, self).default_get(fields)
        res['budget_id'] = self._context.get('active_id', False)
        return res


    budget_id = fields.Many2one('bim.budget', "Presupuesto", required=True)
    text = fields.Boolean('Notas', default=True)
    display_type = fields.Selection([
        ('general', 'Certificación General'),
        ('compare', 'Comparativo'),
        ('summary', 'Resumen'),
        ('origin', 'Certificación a Origen'),#
    ], string="Tipo de impresión", default='general', help="Forma de agrupacion del Reporte.")
    total_type = fields.Selection([
        ('asset', 'Haberes y descuentos'),
        ('normal','Totales Regulares'),
    ], string="Totalización", default='asset')



    ### TOTALES POR CAPITULO ###
    # Origen
    @api.model
    def get_origin_total(self, chapter):
        records = chapter.child_ids.filtered(lambda c: c.balance_cert > 0)
        total = 0
        for child in records:
            if child.type_cert == 'stage':
                total += sum(stage.amount_certif for stage in child.certification_stage_ids if stage.stage_state in ['approved'])
            else:
                total += child.balance_cert
        return total

    # Anterior
    @api.model
    def get_previous_total(self, chapter):
        records = chapter.child_ids.filtered(lambda c: c.balance_cert > 0)
        total = 0
        for child in records:
            total += float(self.get_previous_cert(child)['amount'])
        return total

    @api.model
    def get_current_total(self, chapter):
        records = chapter.child_ids.filtered(lambda c: c.balance_cert > 0)
        total = 0
        for child in records:
            total += float(self.get_current_cert(child)['amount'])
        return total

    ### TOTALES POR CONCEPTO ###
    # Origen
    @api.model
    def get_origin_cert(self, concept):
        qty_total = 0
        mnt_total = 0
        if concept.balance_cert > 0 and concept.type_cert == 'stage':
            qty_total = sum(stage.certif_qty for stage in concept.certification_stage_ids if stage.stage_state in ['approved','process'])
            mnt_total = sum(stage.amount_certif for stage in concept.certification_stage_ids if stage.stage_state in ['approved','process'])

        elif concept.balance_cert > 0 and concept.type_cert != 'stage':
            qty_total = concept.quantity_cert
            mnt_total = concept.balance_cert
        return {'qty':qty_total, 'amount': mnt_total}

    # Anterior
    @api.model
    def get_previous_cert(self, concept):
        qty_total = 0
        mnt_total = 0

        if concept.balance_cert > 0 and concept.type_cert == 'stage':
            #count = len([stage.id for stage in concept.certification_stage_ids if stage.stage_state in ['approved']])
            #if (count - 1) > 0:
                #cont = count - 1
            for stage in concept.certification_stage_ids:
                if stage.stage_state in ['approved']:# and cont > 0
                    qty_total += stage.certif_qty
                    mnt_total += stage.amount_certif
                    #cont -= 1

        elif concept.balance_cert > 0 and concept.type_cert == 'measure':
            #count = len([me.id for me in concept.measuring_ids if me.stage_id and me.stage_state in ['approved']])
            #if (count - 1) > 0:
            #    cont = count - 1
            for meas in concept.measuring_ids:
                if meas.stage_state in ['approved']:# and cont > 0
                    qty_total += meas.amount_subtotal
                    mnt_total += meas.amount_subtotal * concept.amount_compute_cert
                    #cont -= 1
        else:
            qty_total = concept.quantity_cert
            mnt_total = concept.balance_cert

        return {'qty':qty_total, 'amount': mnt_total}

    # Actual
    @api.model
    def get_current_cert(self, concept):
        qty_total = 0
        mnt_total = 0
        if concept.balance_cert > 0 and concept.type_cert == 'stage':
            if concept.certification_stage_ids:
                stage_ids = [stage.id for stage in concept.certification_stage_ids if stage.stage_state in ['process']]
                stage_id = stage_ids and max(stage_ids) or False
                if stage_id:
                    stage = self.env['bim.certification.stage'].browse(stage_id)
                    qty_total = stage.certif_qty
                    mnt_total = stage.amount_certif

        elif concept.balance_cert > 0 and concept.type_cert == 'measure':
            if concept.measuring_ids:
                meas_ids = [me.id for me in concept.measuring_ids if me.stage_id and me.stage_state in ['process']]
                if meas_ids:
                    stages = self.env['bim.concept.measuring'].browse(meas_ids)
                    for stage in stages:
                        qty_total += stage.amount_subtotal
                        mnt_total += stage.amount_subtotal * concept.amount_compute_cert

                # Solo funciona para una linea
                #meas_id = meas_ids and max(meas_ids) or False
                #if meas_id:
                #    stage = self.env['bim.concept.measuring'].browse(meas_id)
                #    qty_total = stage.amount_subtotal
                #    mnt_total = stage.amount_subtotal * concept.amount_compute_cert

        return {'qty':qty_total, 'amount': mnt_total}

    def check_report(self):
        self.ensure_one()
        data = {}
        data['id'] = self._context.get('active_id', [])
        data['docs'] = self._context.get('active_ids', [])
        data['model'] = self._context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read([])[0]
        return self._print_report(data)

    def _print_report(self, data):
        if self.display_type == 'general':
            action = self.env.ref('base_bim_2.bim_budget_certification').report_action(self)
        elif self.display_type == 'compare':
            action = self.env.ref('base_bim_2.bim_budget_compare').report_action(self)
        else:
            action = self.env.ref('base_bim_2.bim_origin_certification').report_action(self)
        action.update({'close_on_report_download': True})
        return action

    def check_report_xls(self):
        budget = self.budget_id
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet('Reporte certificación')
        file_name = 'Certificación'
        style_title = xlwt.easyxf('font: name Times New Roman 180, color-index black, bold on; align: wrap yes, horiz left')
        style_border_table_top = xlwt.easyxf('borders: left thin, right thin, top thin, bottom thin; font: bold on;')
        style_border_table_details_chapters = xlwt.easyxf('borders: bottom thin; pattern: pattern solid, pattern_fore_colour light_blue;')
        style_border_table_details_departed = xlwt.easyxf('borders: bottom thin; pattern: pattern solid, pattern_fore_colour pale_blue;')
        style_border_table_details = xlwt.easyxf('borders: bottom thin;')
        if self.display_type == 'general':
            worksheet.write_merge(0, 0, 0, 4, "REPORTE DE CERTIFICACIÓN GENERAL", style_title)
            worksheet.write_merge(1,1,0,2, "Obra")
            worksheet.write_merge(1,1,3,5, budget.name)
            worksheet.write_merge(1,1,6,8, "Fecha de Impresión")
            worksheet.write_merge(2,2,0,2, budget.project_id.nombre)
            worksheet.write_merge(2,2,3,5, budget.code)
            worksheet.write_merge(2,2,6,8, datetime.now().strftime('%d-%m-%Y'))

            # Header table
            worksheet.write_merge(4,4,0,1, "Código", style_border_table_top)
            worksheet.write_merge(4,4,2,7, "Concepto", style_border_table_top)
            worksheet.write_merge(4,4,8,8, "Unidad", style_border_table_top)
            worksheet.write_merge(4,4,9,9, "Cantidad", style_border_table_top)
            worksheet.write_merge(4,4,10,10, "Precio", style_border_table_top)
            worksheet.write_merge(4,4,11,11, "Importe", style_border_table_top)
            chapters = budget.concept_ids.filtered(lambda c: not c.parent_id and c.balance_cert > 0)
            row = 5
            total = 0
            for chapter in chapters:
                worksheet.write_merge(row,row,0,1, chapter.code, style_border_table_details_chapters)
                worksheet.write_merge(row,row,2,7, chapter.name, style_border_table_details_chapters)
                worksheet.write_merge(row,row,8,8, "-", style_border_table_details_chapters)
                worksheet.write_merge(row,row,9,9, "-", style_border_table_details_chapters)
                worksheet.write_merge(row,row,10,10, "-", style_border_table_details_chapters)
                worksheet.write_merge(row,row,11,11, chapter.balance_cert, style_border_table_details_chapters)
                row += 1
                total += chapter.balance_cert
                childs = chapter.child_ids.filtered(lambda c: c.to_certify and c.balance_cert > 0)
                for child in childs:
                    if child.type == 'departure':
                        worksheet.write_merge(row,row,0,1, child.code, style_border_table_details_departed)
                        worksheet.write_merge(row,row,2,7, child.name, style_border_table_details_departed)
                        worksheet.write_merge(row,row,8,8, child.uom_id.name, style_border_table_details_departed)
                        worksheet.write_merge(row,row,9,9, child.quantity, style_border_table_details_departed)
                        worksheet.write_merge(row,row,10,10, child.amount_compute, style_border_table_details_departed)
                        worksheet.write_merge(row,row,11,11, child.balance_cert, style_border_table_details_departed)
                        row += 1
                        if self.text and child.note:
                            worksheet.write_merge(row,row,0,11, child.note, style_border_table_details)
                            row += 1
                    else:
                        worksheet.write_merge(row,row,0,1, child.code, style_border_table_details)
                        worksheet.write_merge(row,row,2,7, child.name, style_border_table_details)
                        worksheet.write_merge(row,row,8,8, child.uom_id.name, style_border_table_details)
                        worksheet.write_merge(row,row,9,9, child.quantity, style_border_table_details)
                        worksheet.write_merge(row,row,10,10, child.amount_compute, style_border_table_details)
                        worksheet.write_merge(row,row,11,11, child.balance_cert, style_border_table_details)
                        row += 1

            worksheet.write_merge(row,row,0,10, "TOTAL", style_border_table_top)
            worksheet.write_merge(row,row,11,11, total, style_border_table_top)

        elif self.display_type == 'compare':
            worksheet.write_merge(0, 0, 0, 4, "COMPARATIVO  CERTIFICACIÓN - PRESUPUESTO", style_title)
            worksheet.write_merge(1,1,0,2, "Obra")
            worksheet.write_merge(1,1,3,5, budget.name)
            worksheet.write_merge(1,1,6,8, "Fecha de Impresión")
            worksheet.write_merge(2,2,0,2, budget.project_id.nombre)
            worksheet.write_merge(2,2,3,5, budget.code)
            worksheet.write_merge(2,2,6,8, datetime.now().strftime('%d-%m-%Y'))

            # Header table
            worksheet.write_merge(4,4,8,8, "PRECIO", style_border_table_top)
            worksheet.write_merge(4,4,9,11, "CANTIDAD", style_border_table_top)
            worksheet.write_merge(4,4,12,14, "IMPORTE", style_border_table_top)
            worksheet.write_merge(5,5,0,1, "Código", style_border_table_top)
            worksheet.write_merge(5,5,2,7, "Concepto", style_border_table_top)
            worksheet.write_merge(5,5,8,8, "Pres", style_border_table_top)
            worksheet.write_merge(5,5,9,9, "Pres", style_border_table_top)
            worksheet.write_merge(5,5,10,10, "Cert", style_border_table_top)
            worksheet.write_merge(5,5,11,11, "Diferencia", style_border_table_top)
            worksheet.write_merge(5,5,12,12, "Pres", style_border_table_top)
            worksheet.write_merge(5,5,13,13, "Cert", style_border_table_top)
            worksheet.write_merge(5,5,14,14, "Diferencia", style_border_table_top)
            chapters = budget.concept_ids.filtered(lambda c: not c.parent_id and c.balance_cert > 0)
            row = 6
            total = 0
            for chapter in chapters:
                worksheet.write_merge(row,row,0,1, chapter.code, style_border_table_details_chapters)
                worksheet.write_merge(row,row,2,7, chapter.name, style_border_table_details_chapters)
                worksheet.write_merge(row,row,8,8, "-", style_border_table_details_chapters)
                worksheet.write_merge(row,row,9,9, "-", style_border_table_details_chapters)
                worksheet.write_merge(row,row,10,10, "-", style_border_table_details_chapters)
                worksheet.write_merge(row,row,11,11, "-", style_border_table_details_chapters)
                worksheet.write_merge(row,row,12,12, chapter.balance, style_border_table_details_chapters)
                worksheet.write_merge(row,row,13,13, chapter.balance_cert, style_border_table_details_chapters)
                worksheet.write_merge(row,row,14,14, chapter.balance-chapter.balance_cert, style_border_table_details_chapters)
                row += 1
                total += chapter.balance_cert
                childs = chapter.child_ids.filtered(lambda c: c.to_certify and c.balance_cert > 0)
                for child in childs:
                    worksheet.write_merge(row,row,0,1, child.code, style_border_table_details_departed)
                    worksheet.write_merge(row,row,2,7, child.name, style_border_table_details_departed)
                    worksheet.write_merge(row,row,8,8, child.amount_compute, style_border_table_details_departed)
                    worksheet.write_merge(row,row,9,9, child.quantity, style_border_table_details_departed)
                    worksheet.write_merge(row,row,10,10, child.quantity_cert, style_border_table_details_departed)
                    worksheet.write_merge(row,row,11,11, round(child.quantity-child.quantity_cert,3), style_border_table_details_departed)
                    worksheet.write_merge(row,row,12,12, child.balance, style_border_table_details_departed)
                    worksheet.write_merge(row,row,13,13, child.balance_cert, style_border_table_details_departed)
                    worksheet.write_merge(row,row,14,14, round(child.balance-child.balance_cert,2), style_border_table_details_departed)
                    row += 1
                    if self.text and child.note:
                        worksheet.write_merge(row,row,0,14, child.note, style_border_table_details)
                        row += 1

        else:
            worksheet.write_merge(0, 0, 0, 4, "REPORTE CERTIFICACIÓN ACTUAL Y A ORIGEN", style_title)
            worksheet.write_merge(1,1,0,2, "Obra")
            worksheet.write_merge(1,1,3,5, budget.name)
            worksheet.write_merge(1,1,6,8, "Fecha de Impresión")
            worksheet.write_merge(2,2,0,2, budget.project_id.nombre)
            worksheet.write_merge(2,2,3,5, budget.code)
            worksheet.write_merge(2,2,6,8, datetime.now().strftime('%d-%m-%Y'))

            # Header table
            worksheet.write_merge(4,4,9,10, "Orígen", style_border_table_top)
            worksheet.write_merge(4,4,11,12, "Anteriores", style_border_table_top)
            worksheet.write_merge(4,4,13,14, "Actual", style_border_table_top)

            worksheet.write_merge(5,5,0,1, "Código", style_border_table_top)
            worksheet.write_merge(5,5,2,7, "Concepto", style_border_table_top)
            worksheet.write_merge(5,5,8,8, "Unidad", style_border_table_top)
            worksheet.write_merge(5,5,9,9, "Cantidad", style_border_table_top)
            worksheet.write_merge(5,5,10,10, "Importe", style_border_table_top)
            worksheet.write_merge(5,5,11,11, "Cantidad", style_border_table_top)
            worksheet.write_merge(5,5,12,12, "Importe", style_border_table_top)
            worksheet.write_merge(5,5,13,13, "Cantidad", style_border_table_top)
            worksheet.write_merge(5,5,14,14, "Importe", style_border_table_top)
            chapters = budget.concept_ids.filtered(lambda c: not c.parent_id and c.balance_cert > 0)
            row = 6
            total_origin = 0
            total_previous = 0
            total_current = 0
            for chapter in chapters:
                origin = self.get_origin_total(chapter)
                previous = self.get_previous_total(chapter)
                current = self.get_current_total(chapter)
                total_origin += origin
                total_previous += previous
                total_current += current
                worksheet.write_merge(row,row,0,1, chapter.code, style_border_table_details_chapters)
                worksheet.write_merge(row,row,2,7, chapter.name, style_border_table_details_chapters)
                worksheet.write_merge(row,row,8,8, "-", style_border_table_details_chapters)
                worksheet.write_merge(row,row,9,9, "", style_border_table_details_chapters)
                worksheet.write_merge(row,row,10,10, round(origin,2), style_border_table_details_chapters)
                worksheet.write_merge(row,row,11,11, "", style_border_table_details_chapters)
                worksheet.write_merge(row,row,12,12, round(previous,2), style_border_table_details_chapters)
                worksheet.write_merge(row,row,13,13, "", style_border_table_details_chapters)
                worksheet.write_merge(row,row,14,14, round(current,2), style_border_table_details_chapters)
                row += 1
                for child in chapter.child_ids:
                    if child.type == 'departure':
                        origin = self.get_origin_cert(child)
                        previous = self.get_previous_cert(child)
                        current = self.get_current_cert(child)
                        worksheet.write_merge(row,row,0,1, child.code, style_border_table_details_departed)
                        worksheet.write_merge(row,row,2,7, child.name, style_border_table_details_departed)
                        worksheet.write_merge(row,row,8,8, child.uom_id.name, style_border_table_details_departed)
                        worksheet.write_merge(row,row,9,9, origin['qty'], style_border_table_details_departed)
                        worksheet.write_merge(row,row,10,10, round(origin['amount'],2), style_border_table_details_departed)
                        worksheet.write_merge(row,row,11,11, previous['qty'], style_border_table_details_departed)
                        worksheet.write_merge(row,row,12,12, round(previous['amount'],2), style_border_table_details_departed)
                        worksheet.write_merge(row,row,13,13, current['qty'], style_border_table_details_departed)
                        worksheet.write_merge(row,row,14,14, round(current['amount'],2), style_border_table_details_departed)
                        row += 1
                        if self.text and child.note:
                            worksheet.write_merge(row,row,0,11, child.note, style_border_table_details)
                            row += 1
                    else:
                        origin = self.get_origin_cert(child)
                        previous = self.get_previous_cert(child)
                        current = self.get_current_cert(child)
                        worksheet.write_merge(row,row,0,1, child.code, style_border_table_details)
                        worksheet.write_merge(row,row,2,7, child.name, style_border_table_details)
                        worksheet.write_merge(row,row,8,8, child.uom_id.name, style_border_table_details)
                        worksheet.write_merge(row,row,9,9, origin['qty'], style_border_table_details)
                        worksheet.write_merge(row,row,10,10, round(origin['amount'],2), style_border_table_details)
                        worksheet.write_merge(row,row,11,11, previous['qty'], style_border_table_details)
                        worksheet.write_merge(row,row,12,12, round(previous['amount'],2), style_border_table_details)
                        worksheet.write_merge(row,row,13,13, current['qty'], style_border_table_details)
                        worksheet.write_merge(row,row,14,14, round(current['amount'],2), style_border_table_details)
                        row += 1

            worksheet.write_merge(row,row,0,8, "TOTALES", style_border_table_top)
            worksheet.write_merge(row,row,9,9, "", style_border_table_top)
            worksheet.write_merge(row,row,10,10, round(total_origin,2), style_border_table_top)
            worksheet.write_merge(row,row,11,11, "", style_border_table_top)
            worksheet.write_merge(row,row,12,12, round(total_previous,2), style_border_table_top)
            worksheet.write_merge(row,row,13,13, "", style_border_table_top)
            worksheet.write_merge(row,row,14,14, round(total_current,2), style_border_table_top)
        fp = BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        data_b64 = base64.encodestring(data)
        doc = self.env['ir.attachment'].create({
            'name': '%s.xls' % (file_name),
            'datas': data_b64,
        })

        return {
            'type': "ir.actions.act_url",
            'url': "web/content/?model=ir.attachment&id=" + str(
                doc.id) + "&filename_field=name&field=datas&download=true&filename=" + str(doc.name),
            'target': "self",
            'no_destroy': False,
        }
