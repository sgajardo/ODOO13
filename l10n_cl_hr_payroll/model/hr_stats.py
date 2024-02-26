import base64
from datetime import datetime

import requests

from bs4 import BeautifulSoup
from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class HrStats(models.Model):

    _name = 'hr.stats'
    _description = 'Indicadores Previsionales'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('Nombre', required=True, default=lambda self: str(fields.Date.today().year))
    notas = fields.Text()

    @api.model
    def cron_act_indicadores_previred(self):
        """ Actualizamos los indicadores """
        name_ind = str(datetime.today())[:7]
        """ Revisamos que no exista el indicador """
        param_obj = self.env['ir.config_parameter'].sudo()
        day = int(param_obj.get_param('day_min_previred'))
        day_today = int(str(datetime.today())[8:10])
        if day_today > day:
            obj_indicadores_previsionales = self.env['hr.stats'].search([('name', '=', name_ind)])
            if not obj_indicadores_previsionales:
                vals = {
                    'name': name_ind,
                    'origen': 'Automático CRON'
                }
                """ Lo creamos """
                insert = self.env['hr.stats'].create(vals)
                if insert:
                    insert.upate_indicators_previred()
            else:
                if not obj_indicadores_previsionales.update_date:
                    obj_indicadores_previsionales.upate_indicators_previred()

    origen = fields.Char('Origen', default='Manual')
    asignacion_familiar_primer = fields.Float('Asignación Familiar Tramo 1', help="Asig Familiar Primer Tramo")
    asignacion_familiar_segundo = fields.Float('Asignación Familiar Tramo 2', help="Asig Familiar Segundo Tramo")
    asignacion_familiar_tercer = fields.Float('Asignación Familiar Tramo 3', help="Asig Familiar Tercer Tramo")
    asignacion_familiar_monto_a = fields.Float('Monto Tramo Uno', help="Monto A")
    asignacion_familiar_monto_b = fields.Float('Monto Tramo Dos', help="Monto B")
    asignacion_familiar_monto_c = fields.Float('Monto Tramo Tres', help="Monto C")

    # Contrato Plazo Indefinido Empleador
    contrato_plazo_indefinido_empleador = fields.Float('Contrato Plazo Indefinido Empleador')

    # Contrato Plazo Indefinido Trabajador
    contrato_plazo_indefinido_trabajador = fields.Float('Contrato Plazo Indefinido Trabajador')

    # Contrato Plazo Fijo Empleador
    contrato_plazo_fijo_empleador = fields.Float('Contrato Plazo Fijo Empleador')

    # Contrato Plazo Indefinido 11 años o más (**)
    contrato_plazo_indefinido_empleador_otro = fields.Float('Contrato Plazo Indefinido 11 anos o mas')

    caja_compensacion = fields.Float('Caja Compensación', help="Caja de Compensacion")
    deposito_convenido = fields.Float('Deposito Convenido', help="Deposito Convenido")
    fonasa = fields.Float('Fonasa', help="Fonasa")
    mutual_seguridad = fields.Float('Mutual de Seguridad')
    pensiones_ips = fields.Float('Pensiones IPS')
    sueldo_minimo = fields.Float('Sueldo Minimo')
    sueldo_minimo_otro = fields.Float('Sueldo Mínimo para Menores de 18 y Mayores a 65')
    tasa_afp_cuprum = fields.Float('Tasa AFP Cuprum')
    tasa_afp_capital = fields.Float('Tasa AFP Capital')
    tasa_afp_provida = fields.Float('Tasa AFP Provida')
    tasa_afp_modelo = fields.Float('Tasa AFP Modelo')
    tasa_afp_planvital = fields.Float('Tasa AFP PlanVital')
    tasa_afp_habitat = fields.Float('Tasa AFP Habitat')
    tasa_afp_uno = fields.Float('Tasa AFP Uno')
    tasa_sis_cuprum = fields.Float('Tasa SIS Cuprum')
    tasa_sis_capital = fields.Float('Tasa SIS Capital')
    tasa_sis_provida = fields.Float('Tasa SIS Provida')
    tasa_sis_planvital = fields.Float('Tasa SIS PlanVital')
    tasa_sis_habitat = fields.Float('Tasa SIS Habitat')
    tasa_sis_modelo = fields.Float('Tasa SIS Modelo')
    tasa_sis_uno = fields.Float('Tasa SIS Uno')
    tasa_independiente_cuprum = fields.Float('Tasa Independientes Cuprum')
    tasa_independiente_capital = fields.Float('Tasa Independientes Capital')
    tasa_independiente_provida = fields.Float('Tasa Independientes Provida')
    tasa_independiente_planvital = fields.Float('Tasa Independientes PlanVital')
    tasa_independiente_habitat = fields.Float('Tasa Independientes Habitat')
    tasa_independiente_modelo = fields.Float('Tasa Independientes Modelo')
    tasa_independiente_uno = fields.Float('Tasa Independientes Uno')
    tope_anual_apv = fields.Float('Tope Anual APV')
    tope_mensual_apv = fields.Float('Tope Mensual APV')
    tope_imponible_afp = fields.Float('Tope Imponible AFP')
    tope_imponible_ips = fields.Float('Tope Imponible IPS')
    tope_imponible_salud = fields.Float('Tope Imponible Salud')
    tope_imponible_seguro_cesantia = fields.Float('Tope Imponible Seguro de Cesantía')
    uf = fields.Float('UF', help="UF fin de Mes")
    utm = fields.Float('UTM', help="UTM Fin de Mes")
    uta = fields.Float('UTA', help="UTA Fin de Mes")
    uf_otros = fields.Float('UF Otros', help="UF Seguro Complementario")
    mutualidad_id = fields.Many2one('hr.mutual', 'MUTUAL')
    ccaf_id = fields.Many2one('hr.ccaf', 'CCAF')

    update_date = fields.Datetime('Fecha de Actualización')

    def exe_exportar(self):
        res = {}
        filename = '%s_previred.csv' % self.name

        data = "uf,utm,uta,tasa_afp_capital,tasa_sis_capital,tasa_independiente_capital,tasa_afp_cuprum,tasa_sis_cuprum,tasa_independiente_cuprum"
        data += ",tasa_afp_habitat,tasa_sis_habitat,tasa_independiente_habitat,tasa_afp_planvital,tasa_sis_planvital,tasa_independiente_planvital"
        data += ",tasa_afp_provida,tasa_sis_provida,tasa_independiente_provida,tasa_afp_modelo,tasa_sis_modelo,tasa_independiente_modelo"
        data += ",tope_imponible_afp,tope_imponible_ips,tope_imponible_seguro_cesantia"
        data += ",asignacion_familiar_monto_a,asignacion_familiar_primer,asignacion_familiar_monto_b,asignacion_familiar_segundo,asignacion_familiar_monto_c,asignacion_familiar_tercer"
        data += ",sueldo_minimo,sueldo_minimo_otro"
        data += ",deposito_convenido"
        data += ",tope_anual_apv,tope_mensual_apv"
        data += ",contrato_plazo_indefinido_empleador,contrato_plazo_indefinido_trabajador,contrato_plazo_fijo_empleador,contrato_plazo_indefinido_empleador_otro"
        data += ",name\n"

        data += str(self.uta) + "," + \
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

        data = base64.b64encode(data.encode('utf-8'))
        attach_vals = {'name': filename, 'datas': data, 'store_fname': filename}
        doc_id = self.env['ir.attachment'].create(attach_vals)

        self.message_post(body=_("Descargado por : %s") % self.env.user.name)
        return {
            'name': filename,
            'type': 'ir.actions.act_url',
            'url': 'web/content/%d?download=true' % doc_id.id,
            'target': 'self',
        }

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
                cad = cad.replace("1ff8", "")
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

            self.tasa_afp_uno = clear_string(letters[7].select("strong")[26].get_text())
            self.tasa_sis_uno = clear_string(letters[7].select("strong")[27].get_text())

            self.tasa_independiente_capital = clear_string(letters[7].select("strong")[10].get_text())[:5]
            self.tasa_independiente_cuprum = clear_string(letters[7].select("strong")[13].get_text())
            self.tasa_independiente_habitat = clear_string(letters[7].select("strong")[16].get_text())
            self.tasa_independiente_planvital = clear_string(letters[7].select("strong")[19].get_text())
            self.tasa_independiente_provida = clear_string(letters[7].select("strong")[22].get_text())
            self.tasa_independiente_modelo = clear_string(letters[7].select("strong")[25].get_text())
            self.tasa_independiente_uno = clear_string(letters[7].select("strong")[28].get_text())

            """ Mutual de Seguridad """
            if self.env.company.mutualidad_id:
                self.mutualidad_id = self.env.company.mutualidad_id
                if self.env.company.mutual_seguridad:
                    self.mutual_seguridad = self.env.company.mutual_seguridad

            """ Caja """
            if self.env.company.ccaf_id:
                self.ccaf_id = self.env.company.ccaf_id
                if self.env.company.caja_compensacion:
                    self.caja_compensacion = self.env.company.caja_compensacion

            self.message_post(body=_("Actualizado por: %s") % self.env.user.name)

        except Exception as e:
            raise AccessError("Error:" + str(e))
