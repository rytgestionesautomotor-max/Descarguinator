# wizard_casos.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
from datetime import date
import re

ROOT = Path(__file__).resolve().parent          # ./Descargos
DIR_CASOS = ROOT / "casos"
DIR_PLANTILLAS = ROOT / "plantillas"
DIR_SALIDAS = ROOT / "salidas"

TIPOS_INFRACCION = ["semaforo", "velocidad", "senda", "luces", "celular"]  # podés ampliar

def ask(prompt:str, default:str=""):
    s = input(f"{prompt}{' ['+default+']' if default else ''}: ").strip()
    return s or default

def ask_bool(prompt:str, default:bool=False):
    d = "s" if default else "n"
    s = input(f"{prompt} (s/n) [{d}]: ").strip().lower()
    if s == "":
        return default
    return s in ("s","si","sí","y","yes","true","1")

def ask_date(prompt:str):
    while True:
        s = input(f"{prompt} [YYYY-MM-DD]: ").strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return s
        print("Formato inválido. Ej: 2025-08-19")

def ask_time(prompt:str):
    while True:
        s = input(f"{prompt} [HH:MM 24h]: ").strip()
        if re.fullmatch(r"\d{2}:\d{2}", s):
            return s
        print("Formato inválido. Ej: 17:19")

def pick_tipo():
    print("Tipo de infracción:")
    for i,t in enumerate(TIPOS_INFRACCION, start=1):
        print(f"  {i}) {t}")
    while True:
        s = input("Elegí opción (1..{}): ".format(len(TIPOS_INFRACCION))).strip()
        if s.isdigit() and 1 <= int(s) <= len(TIPOS_INFRACCION):
            return TIPOS_INFRACCION[int(s)-1]
        print("Opción inválida.")

def ensure_dirs():
    DIR_CASOS.mkdir(exist_ok=True)
    DIR_PLANTILLAS.mkdir(exist_ok=True)
    DIR_SALIDAS.mkdir(exist_ok=True)

def main():
    ensure_dirs()
    print("=== Asistente para crear JSON de caso (Descarguinator) ===\n")

    # 1) Cliente
    nombre = ask("Nombre completo del cliente (ej. JUAN LAYAN)").upper()
    dni = ask("DNI")
    nacionalidad = ask("Nacionalidad", "Argentina")
    domicilio_real = ask("Domicilio real")
    dom_distinto = ask_bool("¿Constituye domicilio procesal distinto del real?", False)
    domicilio_procesal = ask("Domicilio procesal", domicilio_real if not dom_distinto else "")

    dominio = ask("Dominio (patente)")
    veh_marca = ask("Marca del vehículo")
    veh_modelo = ask("Modelo del vehículo")

    # 2) Causa/acta
    juzgado = ask("Juzgado (texto)", "Juzgado de Faltas")
    municipio = ask("Municipio")
    provincia = ask("Provincia", "Buenos Aires")
    nro_causa = ask("Nro. de causa (si no hay, repetir Nro. de acta luego)")
    nro_acta = ask("Nro. de acta")
    if not nro_causa:
        nro_causa = nro_acta

    fecha_presentacion = str(date.today())  # política: "hoy"
    fecha_hecho = ask_date("Fecha del hecho")
    hora_hecho = ask_time("Hora del hecho")
    lugar = ask("Lugar (calle/intersección/tramo)")
    tipo = pick_tipo()

    # 3) Equipo (si aplica)
    equipo_marca = ask("Equipo - Marca (opcional)", "")
    equipo_modelo = ask("Equipo - Modelo (opcional)", "")
    equipo_serie = ask("Equipo - Serie (opcional)", "")

    # 4) Toggles probatorios (defaults según tu criterio)
    hay_equipo_auto = True  # “siempre” por política acordada
    notif_60 = True
    notif_fehac = True
    imputa_norma = True
    firma_ok = True
    metadatos_ok = True
    cadena_ok = True
    patente_leg = ask_bool("¿Patente legible inequívocamente?", False)
    inti_vig = ask_bool("¿Inspección/verificación INTI vigente al hecho?", False)
    aut_mun_vig = ask_bool("¿Autorización ministerial previa/municipal vigente?", False)

    # Para velocidad, preguntamos explícitamente señalización 28 Bis
    senal_28bis = False
    if tipo == "velocidad":
        senal_28bis = ask_bool("¿Se cumplió señalización previa y límite (art. 28 Bis)?", False)

    incomp = ask_bool("¿Incompetencia territorial/materia/tiempo?", False)
    agente_id = True

    # Prescripción 5 años (true por defecto, salvo que el acta supere 5 años)
    try:
        y,m,d = map(int, fecha_hecho.split("-"))
        presc_5 = (date.today().year - y) >= 5
    except Exception:
        presc_5 = True  # conservador

    # Adjuntos (guardamos como booleanos; podés luego mapear a paths)
    adj_dni = ask_bool("¿Adjunta imagen de DNI?", True)
    adj_ced = ask_bool("¿Adjunta imagen de cédula?", True)
    adj_acta = ask_bool("¿Adjunta impresión/imagen de acta?", True)

    # 5) Armar contexto (claves alineadas a tu plantilla/ejemplo)
    ctx = {
        "JUZGADO": juzgado,
        "MUNICIPIO": municipio,
        "PROVINCIA": provincia,
        "FECHA_PRESENTACION": fecha_presentacion,
        "NRO_CAUSA": nro_causa,
        "NRO_ACTA": nro_acta,
        "FECHA_HECHO": fecha_hecho,
        "HORA_HECHO": hora_hecho,
        "LUGAR": lugar,
        "TIPO_INFRACCION": tipo,

        "NOMBRE": nombre,
        "DNI": dni,
        "NACIONALIDAD": nacionalidad,
        "DOMICILIO_REAL": domicilio_real,
        "DOMICILIO_PROCESAL": domicilio_procesal,

        "DOMINIO": dominio,
        "VEHICULO_MARCA": veh_marca,
        "VEHICULO_MODELO": veh_modelo,

        "EQUIPO_MARCA": equipo_marca,
        "EQUIPO_MODELO": equipo_modelo,
        "EQUIPO_SERIE": equipo_serie,

        "HAY_EQUIPO_AUTOMATICO": True,  # política acordada
        "NOTIFICACION_EN_60_DIAS": notif_60,
        "NOTIFICACION_FEHACIENTE": notif_fehac,
        "IMPUTACION_INDICA_NORMA": imputa_norma,
        "FIRMA_DIGITAL_VALIDA": firma_ok,
        "METADATOS_COMPLETOS": metadatos_ok,
        "CADENA_CUSTODIA_ACREDITADA": cadena_ok,
        "PATENTE_LEGIBLE": patente_leg,
        "INTI_INSPECCION_VIGENTE": inti_vig,
        "AUTORIZACION_MUNICIPAL_VIGENTE": aut_mun_vig,
        "SENALIZACION_28BIS_CUMPLIDA": senal_28bis if tipo == "velocidad" else False,
        "INCOMPETENCIA_TERRITORIAL": incomp,
        "AGENTE_IDENTIFICADO": agente_id,
        "PLAZO_5_ANIOS_PRESCRIPCION": presc_5,

        "ADJUNTA_DNI_IMG": adj_dni,
        "ADJUNTA_CEDULA_IMG": adj_ced,
        "ADJUNTA_ACTA_IMG": adj_acta
    }

    # 6) Guardar JSON (por cliente / por acta)
    carpeta_cliente = DIR_CASOS / re.sub(r"[^A-Z0-9_]+", "_", nombre.upper())
    carpeta_cliente.mkdir(parents=True, exist_ok=True)
    out_path = carpeta_cliente / f"{nro_acta}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=2, ensure_ascii=False)

    print(f"\nOK. JSON creado en: {out_path}")

    # 7) Ofrecer comando de render (tu script)
    print("\nPara generar el DOCX de descargo ahora podés correr:")
    print(f"  python descargos_render_v2.py --caso \"{out_path}\" --estricto")
    print("Si no indicás --salida, el nombre sale de NRO_ACTA + fecha.\n")

if __name__ == "__main__":
    main()
