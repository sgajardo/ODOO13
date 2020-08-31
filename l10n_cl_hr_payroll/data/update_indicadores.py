# -*- coding: utf-8 -*-
import urllib
from bs4 import BeautifulSoup
html_doc = urllib.urlopen('https://www.previred.com/web/previred/indicadores-previsionales').read()
soup = BeautifulSoup(html_doc, 'html.parser')


letters = soup.find_all("table")

def clear_string(cad):
    cad = cad.replace(".", '').replace("$", '').replace(" ", '')
    cad= cad.replace("Renta", '').replace("<", '').replace(">", '')
    cad = cad.replace("=", '').replace("R", '').replace("I", '').replace("%", '')
    cad = cad.replace(",", '.')
    return cad

def divide_cadena(cad,cad2,redondeo):
    return round(float(cad)/float(cad2),redondeo)


# 0 VALOR UF
uf = clear_string(letters[0].select("strong")[1].get_text())


# Obtenemos la UTM
utm = clear_string(letters[1].select("strong")[3].get_text())

# Obtenemos la UTA
uta = clear_string(letters[1].select("strong")[4].get_text())


# 2 RENTAS TOPES IMPONIBLES
tope_imponible_afp = divide_cadena(clear_string(letters[2].select("strong")[1].get_text()),uf,2)

tope_imponible_ips = clear_string(letters[2].select("strong")[2].get_text())
tope_imponible_seguro_cesantia = clear_string(letters[2].select("strong")[3].get_text())


# 3 RENTAS TOPES IMPONIBLES
sueldo_minimo = clear_string(letters[3].select("strong")[1].get_text())
sueldo_minimo_otro = clear_string(letters[3].select("strong")[2].get_text())



# 4 RENTAS TOPES IMPONIBLES
tope_mensual_apv = clear_string(letters[4].select("strong")[1].get_text())
tope_anual_apv = clear_string(letters[4].select("strong")[2].get_text())



# 5 DEPÓSITO CONVENIDO
deposito_convenido = clear_string(letters[5].select("strong")[1].get_text())



# 6 RENTAS TOPES IMPONIBLES
contrato_plazo_indefinido_empleador = clear_string(letters[6].select("strong")[5].get_text())
contrato_plazo_indefinido_trabajador = clear_string(letters[6].select("strong")[6].get_text())
contrato_plazo_fijo_empleador  = clear_string(letters[6].select("strong")[7].get_text())
contrato_plazo_indefinido_empleador_otro = clear_string(letters[6].select("strong")[9].get_text())


# 7 TASA COTIZACIÓN OBLIGATORIO AFP
tasa_afp_capital = clear_string(letters[7].select("strong")[8].get_text())
tasa_sis_capital = clear_string(letters[7].select("strong")[9].get_text())
tasa_independiente_capital = clear_string(letters[7].select("strong")[10].get_text())




tasa_afp_cuprum = clear_string(letters[7].select("strong")[11].get_text())
tasa_sis_cuprum = clear_string(letters[7].select("strong")[12].get_text())
tasa_independiente_cuprum = clear_string(letters[7].select("strong")[13].get_text())

tasa_afp_habitat = clear_string(letters[7].select("strong")[14].get_text())
tasa_sis_habitat = clear_string(letters[7].select("strong")[15].get_text())
tasa_independiente_habitat = clear_string(letters[7].select("strong")[16].get_text())

tasa_afp_planvital = clear_string(letters[7].select("strong")[17].get_text())
tasa_sis_planvital = clear_string(letters[7].select("strong")[18].get_text())
tasa_independiente_planvital = clear_string(letters[7].select("strong")[19].get_text())

tasa_afp_provida = clear_string(letters[7].select("strong")[20].get_text())
tasa_sis_provida = clear_string(letters[7].select("strong")[21].get_text())
tasa_independiente_provida = clear_string(letters[7].select("strong")[22].get_text())

tasa_afp_modelo = clear_string(letters[7].select("strong")[23].get_text())
tasa_sis_modelo = clear_string(letters[7].select("strong")[24].get_text())
tasa_independiente_modelo = clear_string(letters[7].select("strong")[25].get_text())



# 8 ASIGNACIÓN FAMILIAR
asignacion_familiar_monto_a  = clear_string(letters[8].select("strong")[4].get_text())
asignacion_familiar_monto_b  = clear_string(letters[8].select("strong")[6].get_text())
asignacion_familiar_monto_c  = clear_string(letters[8].select("strong")[8].get_text())

asignacion_familiar_primer = clear_string(letters[8].select("strong")[5].get_text())[1:]
asignacion_familiar_segundo = clear_string(letters[8].select("strong")[7].get_text())[6:]
asignacion_familiar_tercer = clear_string(letters[8].select("strong")[9].get_text())[6:]








