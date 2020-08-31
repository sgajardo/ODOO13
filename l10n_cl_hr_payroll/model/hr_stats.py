
# -*- coding: utf-8 -*-
##############################################################################
# Chilean Payroll
#
# Derivative from Odoo / Odoo / Tiny SPRL
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from odoo import api, fields, models, tools, _
import requests
from bs4 import BeautifulSoup
from odoo.exceptions import UserError, RedirectWarning, ValidationError, AccessError
from datetime import datetime, timedelta, date
import base64


class HrStats(models.Model):

    _name = 'hr.stats'
    _description = 'Indicadores Previsionales'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('Nombre', required=True, default=lambda self: str(fields.Date.today().year))
    notas = fields.Text('Notas')

    @api.model
    def cron_act_indicadores_previred(self):
        u""" Actualizamos los indicadores """
        name_ind = str(datetime.today())[:7]
        u""" Revisamos que no exista el indicador """
        param_obj = self.env['ir.config_parameter']
        day = int(param_obj.get_param('day_min_previred'))
        day_today = int(str(datetime.today())[8:10])
        if day_today > day:
            obj_indicadores_previsionales = self.env['hr.stats'].search([('name', '=', name_ind)])
            if not obj_indicadores_previsionales:
                vals = {
                    'name': name_ind,
                    'origen': 'Automático CRON'
                }
                u""" Lo creamos """
                insert = self.env['hr.stats'].create(vals)
                if insert:
                    insert.upate_indicators_previred()
            else:
                if not obj_indicadores_previsionales.update_date:
                    obj_indicadores_previsionales.upate_indicators_previred()

    origen = fields.Char('Origen', default='Manual')
    asignacion_familiar_primer = fields.Float(
        'Asignación Familiar Tramo 1', 
        help="Asig Familiar Primer Tramo")
    asignacion_familiar_segundo = fields.Float(
        'Asignación Familiar Tramo 2', 
        help="Asig Familiar Segundo Tramo")
    asignacion_familiar_tercer = fields.Float(
        'Asignación Familiar Tramo 3', 
        help="Asig Familiar Tercer Tramo")
    asignacion_familiar_monto_a = fields.Float(
        'Monto Tramo Uno', help="Monto A")
    asignacion_familiar_monto_b = fields.Float(
        'Monto Tramo Dos',  help="Monto B")
    asignacion_familiar_monto_c = fields.Float(
        'Monto Tramo Tres',  help="Monto C")

    # Contrato Plazo Indefinido Empleador
    contrato_plazo_indefinido_empleador = fields.Float(
        'Contrato Plazo Indefinido Empleador')

    # Contrato Plazo Indefinido Trabajador
    contrato_plazo_indefinido_trabajador = fields.Float(
        'Contrato Plazo Indefinido Trabajador')

    # Contrato Plazo Fijo Empleador
    contrato_plazo_fijo_empleador = fields.Float(
        'Contrato Plazo Fijo Empleador')

    # Contrato Plazo Indefinido 11 años o más (**)
    contrato_plazo_indefinido_empleador_otro = fields.Float(
        'Contrato Plazo Indefinido 11 anos o mas')

    caja_compensacion = fields.Float(
        'Caja Compensación', 
        help="Caja de Compensacion")
    deposito_convenido = fields.Float(
        'Deposito Convenido', help="Deposito Convenido")
    fonasa = fields.Float('Fonasa',  help="Fonasa")
    mutual_seguridad = fields.Float(
        'Mutualidad',  help="Mutual de Seguridad")
    pensiones_ips = fields.Float(
        'Pensiones IPS',  help="Pensiones IPS")
    sueldo_minimo = fields.Float(
        'Trab. Dependientes e Independientes',  help="Sueldo Minimo")
    sueldo_minimo_otro = fields.Float(
        'Menores de 18 y Mayores de 65:', 
        help="Sueldo Mínimo para Menores de 18 y Mayores a 65")
    tasa_afp_cuprum = fields.Float(
        'Cuprum',  help="Tasa AFP Cuprum")
    tasa_afp_capital = fields.Float(
        'Capital',  help="Tasa AFP Capital")
    tasa_afp_provida = fields.Float(
        'ProVida',  help="Tasa AFP Provida")
    tasa_afp_modelo = fields.Float(
        'Modelo',  help="Tasa AFP Modelo")
    tasa_afp_planvital = fields.Float(
        'PlanVital',  help="Tasa AFP PlanVital")
    tasa_afp_habitat = fields.Float(
        'Habitat',  help="Tasa AFP Habitat")
    tasa_sis_cuprum = fields.Float(
        'SIS', help="Tasa SIS Cuprum")
    tasa_sis_capital = fields.Float(
        'SIS', help="Tasa SIS Capital")
    tasa_sis_provida = fields.Float(
        'SIS',  help="Tasa SIS Provida")
    tasa_sis_planvital = fields.Float(
        'SIS',  help="Tasa SIS PlanVital")
    tasa_sis_habitat = fields.Float(
        'SIS',  help="Tasa SIS Habitat")
    tasa_sis_modelo = fields.Float(
        'SIS',  help="Tasa SIS Modelo")
    tasa_independiente_cuprum = fields.Float(
        'SIS',  help="Tasa Independientes Cuprum")
    tasa_independiente_capital = fields.Float(
        'SIS',  help="Tasa Independientes Capital")
    tasa_independiente_provida = fields.Float(
        'SIS',  help="Tasa Independientes Provida")
    tasa_independiente_planvital = fields.Float(
        'SIS',  help="Tasa Independientes PlanVital")
    tasa_independiente_habitat = fields.Float(
        'SIS',  help="Tasa Independientes Habitat")
    tasa_independiente_modelo = fields.Float(
        'SIS',  help="Tasa Independientes Modelo")
    tope_anual_apv = fields.Float(
        'Tope Anual APV',  help="Tope Anual APV")
    tope_mensual_apv = fields.Float(
        'Tope Mensual APV',  help="Tope Mensual APV")
    tope_imponible_afp = fields.Float(
        'Tope imponible AFP',  help="Tope Imponible AFP")
    tope_imponible_ips = fields.Float(
        'Tope Imponible IPS',  help="Tope Imponible IPS")
    tope_imponible_salud = fields.Float(
        'Tope Imponible Salud')
    tope_imponible_seguro_cesantia = fields.Float(
        'Tope Imponible Seguro Cesantía', 
        help="Tope Imponible Seguro de Cesantía")
    uf = fields.Float(
        'UF', help="UF fin de Mes")
    utm = fields.Float(
        'UTM', help="UTM Fin de Mes")
    uta = fields.Float('UTA',  help="UTA Fin de Mes")
    uf_otros = fields.Float(
        'UF Otros',  help="UF Seguro Complementario")
    mutualidad_id = fields.Many2one('hr.mutual', 'MUTUAL')
    ccaf_id = fields.Many2one('hr.ccaf', 'CCAF')

    update_date = fields.Datetime('Fecha de Actualización')

    def exe_exportar(self):
        res = {}
        fname = '%s_previred.csv' % self.name
        path = '/tmp/' + fname
        txtFile = open(path, 'wb')

        line = "uf,utm,uta,tasa_afp_capital,tasa_sis_capital,tasa_independiente_capital,tasa_afp_cuprum,tasa_sis_cuprum,tasa_independiente_cuprum"
        line += ",tasa_afp_habitat,tasa_sis_habitat,tasa_independiente_habitat,tasa_afp_planvital,tasa_sis_planvital,tasa_independiente_planvital"
        line += ",tasa_afp_provida,tasa_sis_provida,tasa_independiente_provida,tasa_afp_modelo,tasa_sis_modelo,tasa_independiente_modelo"
        line += ",tope_imponible_afp,tope_imponible_ips,tope_imponible_seguro_cesantia"
        line += ",asignacion_familiar_monto_a,asignacion_familiar_primer,asignacion_familiar_monto_b,asignacion_familiar_segundo,asignacion_familiar_monto_c,asignacion_familiar_tercer"
        line += ",sueldo_minimo,sueldo_minimo_otro"
        line += ",deposito_convenido"
        line += ",tope_anual_apv,tope_mensual_apv"
        line += ",contrato_plazo_indefinido_empleador,contrato_plazo_indefinido_trabajador,contrato_plazo_fijo_empleador,contrato_plazo_indefinido_empleador_otro"
        line += ",name"
        txtFile.write(line + '\n')

        line = str(self.uta) + "," + \
               str(self.utm) + "," + \
               str(self.uta) + "," + \
               str(self.tasa_afp_capital) + "," + \
               str(self.tasa_sis_capital) + "," + \
               str(self.tasa_independiente_capital) + "," + \
               str(self.tasa_afp_cuprum) + "," + \
               str(self.tasa_sis_cuprum) + "," + \
               str(self.tasa_independiente_cuprum) + "," + \
               str(self.tasa_afp_habitat) + "," + \
               str(self.tasa_sis_habitat) + "," + \
               str(self.tasa_independiente_habitat) + "," + \
               str(self.tasa_afp_planvital) + "," + \
               str(self.tasa_sis_planvital) + "," + \
               str(self.tasa_independiente_planvital) + "," + \
               str(self.tasa_afp_provida) + "," + \
               str(self.tasa_sis_provida) + "," + \
               str(self.tasa_independiente_provida) + "," + \
               str(self.tasa_afp_modelo) + "," + \
               str(self.tasa_sis_modelo) + "," + \
               str(self.tasa_independiente_modelo) + "," + \
               str(self.tope_imponible_afp) + "," + \
               str(self.tope_imponible_ips) + "," + \
               str(self.tope_imponible_seguro_cesantia) + "," + \
               str(self.asignacion_familiar_monto_a) + "," + \
               str(self.asignacion_familiar_primer) + "," + \
               str(self.asignacion_familiar_monto_b) + "," + \
               str(self.asignacion_familiar_segundo) + "," + \
               str(self.asignacion_familiar_monto_c) + "," + \
               str(self.asignacion_familiar_tercer) + "," + \
               str(self.sueldo_minimo) + "," + \
               str(self.sueldo_minimo_otro) + "," + \
               str(self.deposito_convenido) + "," + \
               str(self.tope_anual_apv) + "," + \
               str(self.tope_mensual_apv) + "," + \
               str(self.contrato_plazo_indefinido_empleador) + "," + \
               str(self.contrato_plazo_indefinido_trabajador) + "," + \
               str(self.contrato_plazo_fijo_empleador) + "," + \
               str(self.contrato_plazo_indefinido_empleador_otro) + "," + \
               str(self.name)

        txtFile.write(line + '\n')

        txtFile.close()
        data = base64.encodestring(open(path, 'r').read())
        attach_vals = {'name': fname, 'datas': data, 'datas_fname': fname}
        doc_id = self.env['ir.attachment'].create(attach_vals)
        res['type'] = 'ir.actions.act_url'
        res['target'] = 'new'
        res['url'] = "web/content/?model=ir.attachment&id=" + str(
            doc_id.id) + "&filename_field=datas_fname&field=datas&download=true&filename=" + str(doc_id.name)

        self.message_post(body=_("Descargado por : %s") % self.env.user.name)
        return res



    # Link
    def go_to_link(self):
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.previred.com/web/previred/indicadores-previsionales',
            'target': 'new',
        }

    def upate_indicators_previred(self):
        self.update_date = datetime.today()
        try:
            html_doc = requests.get('https://www.previred.com/web/previred/indicadores-previsionales').text
            soup = BeautifulSoup(html_doc, 'html.parser')

            letters = soup.find_all("table")

            def clear_string(cad):
                cad = cad.replace(".", '').replace("$", '').replace(" ", '')
                cad = cad.replace("Renta", '').replace("<", '').replace(">", '')
                cad = cad.replace("=", '').replace("R", '').replace("I", '').replace("%", '')
                cad = cad.replace(",", '.')
                # Error encontrado 2018-02-16
                cad = cad.replace("1ff8","")
                return cad
        except Exception as e:
            raise AccessError("Error:" + str(e))

        def divide_cadena(cad, cad2, redondeo):
            return round(float(cad) / float(cad2), redondeo)


        try:
            # UF
            self.uf = clear_string(letters[0].select("strong")[1].get_text())

            # 1 UTM
            self.utm = clear_string(letters[1].select("strong")[3].get_text())

            # 1 UTA
            self.uta = clear_string(letters[1].select("strong")[4].get_text())

            # 3 RENTAS TOPES IMPONIBLES UF
            self.tope_imponible_afp = divide_cadena(clear_string(letters[2].select("strong")[1].get_text()), self.uf, 2)
            self.tope_imponible_ips = divide_cadena(clear_string(letters[2].select("strong")[2].get_text()), self.uf, 2)
            self.tope_imponible_seguro_cesantia = divide_cadena(clear_string(letters[2].select("strong")[3].get_text()),
                                                                self.uf, 2)

            # 4 RENTAS TOPES IMPONIBLES
            self.sueldo_minimo = clear_string(letters[3].select("strong")[1].get_text())
            self.sueldo_minimo_otro = clear_string(letters[3].select("strong")[2].get_text())

            # Ahorro Previsional Voluntario
            self.tope_mensual_apv = divide_cadena(clear_string(letters[4].select("strong")[2].get_text()), self.uf, 2)
            self.tope_anual_apv = divide_cadena(clear_string(letters[4].select("strong")[1].get_text()), self.uf, 2)

            # 5 DEPÓSITO CONVENIDO
            self.deposito_convenido = divide_cadena(clear_string(letters[5].select("strong")[1].get_text()), self.uf, 2)

            # 6 RENTAS TOPES IMPONIBLES
            self.contrato_plazo_indefinido_empleador = clear_string(letters[6].select("strong")[5].get_text())
            self.contrato_plazo_indefinido_trabajador = clear_string(letters[6].select("strong")[6].get_text())
            self.contrato_plazo_fijo_empleador = clear_string(letters[6].select("strong")[7].get_text())
            self.contrato_plazo_indefinido_empleador_otro = clear_string(letters[6].select("strong")[9].get_text())

            # 7 ASIGNACIÓN FAMILIAR
            self.asignacion_familiar_monto_a = clear_string(letters[8].select("strong")[4].get_text())
            self.asignacion_familiar_monto_b = clear_string(letters[8].select("strong")[6].get_text())
            self.asignacion_familiar_monto_c = clear_string(letters[8].select("strong")[8].get_text())

            self.asignacion_familiar_primer = clear_string(letters[8].select("strong")[5].get_text())[1:]
            self.asignacion_familiar_segundo = clear_string(letters[8].select("strong")[7].get_text())[6:]
            self.asignacion_familiar_tercer = clear_string(letters[8].select("strong")[9].get_text())[6:]

            # 8 TASA COTIZACIÓN OBLIGATORIO AFP
            self.tasa_afp_capital = clear_string(letters[7].select("strong")[8].get_text())
            self.tasa_sis_capital = clear_string(letters[7].select("strong")[9].get_text())

            self.tasa_afp_cuprum = clear_string(letters[7].select("strong")[11].get_text().replace(" ", '').replace("%", '').replace("1ff8", ''))
            self.tasa_sis_cuprum = clear_string(letters[7].select("strong")[12].get_text())

            self.tasa_afp_habitat = clear_string(letters[7].select("strong")[14].get_text())
            self.tasa_sis_habitat = clear_string(letters[7].select("strong")[15].get_text())

            self.tasa_afp_planvital = clear_string(letters[7].select("strong")[17].get_text())
            self.tasa_sis_planvital = clear_string(letters[7].select("strong")[18].get_text())

            self.tasa_afp_provida = clear_string(letters[7].select("strong")[20].get_text().replace(" ", '').replace("%", '').replace("1ff8", ''))
            self.tasa_sis_provida = clear_string(letters[7].select("strong")[21].get_text())

            self.tasa_afp_modelo = clear_string(letters[7].select("strong")[23].get_text())
            self.tasa_sis_modelo = clear_string(letters[7].select("strong")[24].get_text())

            self.tasa_independiente_capital = clear_string(letters[7].select("strong")[10].get_text())[:5]
            self.tasa_independiente_cuprum = clear_string(letters[7].select("strong")[13].get_text())
            self.tasa_independiente_habitat = clear_string(letters[7].select("strong")[16].get_text())
            self.tasa_independiente_planvital = clear_string(letters[7].select("strong")[19].get_text())
            self.tasa_independiente_provida = clear_string(letters[7].select("strong")[22].get_text())
            self.tasa_independiente_modelo = clear_string(letters[7].select("strong")[25].get_text())

            """ Mutual de Seguridad """
            if self.env.user.company_id.mutualidad_id:
                self.mutualidad_id = self.env.user.company_id.mutualidad_id
                if self.env.user.company_id.mutual_seguridad:
                    self.mutual_seguridad = self.env.user.company_id.mutual_seguridad

            """ Caja """
            if self.env.user.company_id.ccaf_id:
                self.ccaf_id = self.env.user.company_id.ccaf_id
                if self.env.user.company_id.caja_compensacion:
                    self.caja_compensacion = self.env.user.company_id.caja_compensacion


            self.message_post(body=_("Actualizado por: %s") % self.env.user.name)

        except Exception as e:
            raise AccessError("Error:" + str(e))



