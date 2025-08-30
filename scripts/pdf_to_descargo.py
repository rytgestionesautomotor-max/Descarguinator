# -*- coding: utf-8 -*-
"""
pdf_to_descargo.py
------------------
Uso:
  pip install pdfplumber python-docx
  python pdf_to_descargo.py --pdf "C:\\ruta\\tu_archivo.pdf" --plantilla "..\\plantillas\\MODELO_DESCARGO_INTEGRAL_EXTENSO.docx" --salida "..\\salidas\\DESCARGO_auto.docx"

Hace:
  1) Lee el PDF, extrae campos.
  2) Crea un JSON (en memoria) con keys que espera tu plantilla.
  3) Llama al renderizador v2 (descargos_render_v2.py) para producir el .docx.
"""

from __future__ import annotations
import argparse
import io
import json
import re
from datetime import date
from pathlib import Path

import pdfplumber

# Intento de importar renderizador
def _try_import_renderer():
    try:
        from descargos_render_v2 import render_docx  # type: ignore
        from descargos_render_v2 import doc_to_text  # type: ignore
        return render_docx, doc_to_text
    except Exception:
        return None, None

# Expresiones regulares para extraer datos del acta
RE = {
    "causa": re.compile(r"Causa\s*Nro:\s*([0-9\-]+)"),
    "fecha_hora": re.compile(r"Fecha y Hora:\s*([0-9\/]{2,}[^ \n]*\s+[0-9:]{4,5})"),
    "lugar": re.compile(r"Lugar de la Infracción:\s*(.+)"),
    "dominio": re.compile(r"Dominio:\s*([A-Z0-9]+)"),
    "marca": re.compile(r"Marca:\s*([A-ZÁÉÍÓÚÑ0-9\s\.\-]+)"),
    "modelo": re.compile(r"Modelo:\s*([A-Z0-9ÁÉÍÓÚÑ\.\- ]+)"),
    "anio": re.compile(r"Año:\s*([0-9]{4})"),
    "jurisdiccion": re.compile(r"Jurisdicción Constatación:\s*([A-ZÁÉÍÓÚÑ\(\)\s0-9\-]+)"),
    "tipo": re.compile(r"Tipo:\s*([A-ZÁÉÍÓÚÑ]+)"),
    "equipo_serie": re.compile(r"Nro Serie:\s*([A-Z0-9]+)"),
    "equipo_marca": re.compile(r"Equipo Marca:\s*([A-Z0-9ÁÉÍÓÚÑ\-\s]+)"),
    "equipo_modelo": re.compile(r"Modelo:\s*([A-Z0-9ÁÉÍÓÚÑ\-\s]+)"),
    "articulo_line": re.compile(r"([0-9]{1,3})\s+No respetar luces de semáforo", re.IGNORECASE),
    "desc_line": re.compile(r"No respetar luces de semáforo", re.IGNORECASE),
}

def read_pdf_text(pdf_path: Path) -> str:
    txt_parts = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            txt_parts.append(txt)
    return "\n".join(txt_parts)

def extract_fields(text: str) -> dict:
    def find(key, default=""):
        m = RE[key].search(text) if key in RE else None
        return (m.group(1).strip() if m else default)

    causa = find("causa")
    fecha_hora = find("fecha_hora")
    lugar = find("lugar")
    dominio = find("dominio")
    marca = find("marca")
    modelo = find("modelo")
    anio = find("anio")
    jurisdiccion = find("jurisdiccion")
    tipo_veh = find("tipo")
    equipo_serie = find("equipo_serie")
    equipo_marca = find("equipo_marca")
    equipo_modelo = find("equipo_modelo")

    articulo = ""
    m_art = RE["articulo_line"].search(text)
    if m_art:
        articulo = m_art.group(1)

    municipio = ""
    provincia = "Buenos Aires"
    if jurisdiccion:
        municipio = jurisdiccion.split("(")[0].strip().title()

    tipo_infraccion = "semaforo" if RE["desc_line"].search(text) else ""

    fecha_hecho, hora_hecho = "", ""
    if fecha_hora:
        parts = fecha_hora.split()
        if len(parts) >= 2:
            fecha_hecho, hora_hecho = parts[0], parts[1]

    ctx = {
        # Encabezado
        "NRO_CAUSA": causa,
        "MUNICIPIO": municipio or "",
        "PROVINCIA": provincia,
        "FECHA_PRESENTACION": str(date.today()),

        # Personales (a completar)
        "NOMBRE": "",
        "DNI": "",
        "NACIONALIDAD": "",
        "DOMICILIO_REAL": "",
        "DOMICILIO_PROCESAL": "",
        "JUZGADO": "",

        # Hecho
        "NRO_ACTA": causa,
        "FECHA_HECHO": fecha_hecho,
        "HORA_HECHO": hora_hecho,
        "LUGAR": lugar,

        # Vehículo
        "DOMINIO": dominio,
        "VEHICULO_MARCA": (marca or "").title(),
        "VEHICULO_MODELO": (modelo or "").strip(),
        "VEHICULO_ANIO": anio,
        "TIPO_VEHICULO": (tipo_veh or "").title(),

        # Dispositivo
        "HAY_EQUIPO_AUTOMATICO": True if (equipo_marca or equipo_modelo) else False,
        "EQUIPO_MARCA": (equipo_marca or "").strip(),
        "EQUIPO_MODELO": (equipo_modelo or "").strip(),
        "EQUIPO_SERIE": (equipo_serie or "").strip(),

        # Tipo/Norma
        "TIPO_INFRACCION": tipo_infraccion,
        "ART_INVOCADO": articulo,
        "ROTULO_CONDUCTA": "No respetar luces de semáforo",

        # Flags probatorios (por defecto falsos)
        "NOTIFICACION_EN_60_DIAS": False,
        "NOTIFICACION_FEHACIENTE": False,
        "AUTORIZACION_MUNICIPAL_VIGENTE": False,
        "INTI_INSPECCION_VIGENTE": False,
        "FIRMA_DIGITAL_VALIDA": False,
        "METADATOS_COMPLETOS": False,
        "CADENA_CUSTODIA_ACREDITADA": False,
        "PATENTE_LEGIBLE": False,
        "SENALIZACION_28BIS_CUMPLIDA": False,

        "PLAZO_5_ANIOS_PRESCRIPCION": False,
    }
    return ctx

# --- API para la app (Streamlit) ---
def parse_pdf(pdf_source) -> dict:
    """
    Recibe: ruta (str/Path) o un archivo en memoria (ej. st.uploaded_file).
    Devuelve: dict ctx con los campos parseados.
    """
    # 1) obtener el texto del PDF
    if isinstance(pdf_source, (str, Path)):
        text = read_pdf_text(Path(pdf_source))
    else:
        # Streamlit sube un UploadedFile (archivo en memoria)
        data = pdf_source.read()
        try:
            pdf_source.seek(0)  # por si después la app vuelve a leer el archivo
        except Exception:
            pass
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            parts = []
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
            text = "\n".join(parts)

    # 2) extraer campos
    return extract_fields(text)
# --- fin API ---

def save_json(ctx: dict, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser(description="Extrae datos de un PDF de infracción y genera descargo .docx")
    ap.add_argument("--pdf", required=True, help="Ruta al PDF (detalle de infracción)")
    ap.add_argument("--plantilla", required=True, help="Ruta a la plantilla .docx")
    ap.add_argument("--salida", default="", help="Ruta al .docx de salida")
    ap.add_argument("--json_out", default="", help="(Opcional) guardar el JSON intermedio")
    ap.add_argument("--estricto", action="store_true", help="Falla si quedan placeholders/IF sin resolver")
    args = ap.parse_args()

    pdf_path = Path(args.pdf).resolve()
    plantilla_path = Path(args.plantilla).resolve()

    text = read_pdf_text(pdf_path)
    ctx = extract_fields(text)

    if args.salida:
        out_docx = Path(args.salida).resolve()
    else:
        nro = ctx.get("NRO_ACTA") or "SIN_ACTA"
        out_docx = (Path(".") / f"DESCARGO_{nro}_{date.today()}.docx").resolve()

    if args.json_out:
        save_json(ctx, Path(args.json_out).resolve())

    render_docx, doc_to_text = _try_import_renderer()
    if not render_docx:
        raise SystemExit("No se encontró 'descargos_render_v2.py'. Colocá el archivo junto a este script.")

    render_docx(plantilla_path, ctx, out_docx, estricto=args.estricto)
    print(f"OK -> {out_docx}")

if __name__ == "__main__":
    main()
