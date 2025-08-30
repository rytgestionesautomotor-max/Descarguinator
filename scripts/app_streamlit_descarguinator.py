# Streamlit app para crear JSONs dinámicos de Descarguinator y disparar la generación de descargos
# Guardar este archivo como app_streamlit_descarguinator.py y ejecutar con:
#   streamlit run app_streamlit_descarguinator.py

import os
import sys
import json
import datetime as dt
import subprocess
from pathlib import Path
from typing import List, Literal, Optional

import streamlit as st
from pydantic import BaseModel, Field, validator
from slugify import slugify

try:
    import pdf_to_descargo
    _PDF_IMPORT_ERROR = ""
except Exception as e:  # pragma: no cover - optional dependency
    pdf_to_descargo = None
    _PDF_IMPORT_ERROR = str(e)

# =============================
# Configuración
# =============================

# /Descargos (root del proyecto) -> este archivo está en /Descargos/scripts/
BASE_ROOT = Path(__file__).resolve().parents[1]

BASE_DIR        = BASE_ROOT / "casos"
TEMPLATE_DOCX   = BASE_ROOT / "plantillas" / "MODELO_DESCARGO_INTEGRAL_EXTENSO.docx"
RENDER_SCRIPT   = BASE_ROOT / "scripts" / "descargos_render_v2.py"
SALIDAS_DIRNAME = "salidas"
JSON_DIRNAME    = "json"
ADJUNTOS_DIR    = BASE_ROOT / "adjuntos"

# asegurar estructura
BASE_DIR.mkdir(parents=True, exist_ok=True)
ADJUNTOS_DIR.mkdir(parents=True, exist_ok=True)

# =============================
# Modelos de datos (Pydantic)
# =============================
TipoInfraccion = Literal["semaforo", "velocidad", "senda_peatonal", "luces", "cinturon"]

class Infraccion(BaseModel):
    TIPO_INFRACCION: TipoInfraccion
    NRO_ACTA: str = Field(..., description="Número de acta")
    FECHA_HECHO: str  # DD/MM/AAAA
    HORA_HECHO: str   # HH:MM
    LUGAR: str
    JUZGADO: str
    MUNICIPIO: str
    # Datos técnicos (opcionales)
    EQUIPO_MARCA: Optional[str] = None
    EQUIPO_MODELO: Optional[str] = None
    EQUIPO_SERIE: Optional[str] = None

    PATENTE_LEGIBLE: Optional[bool] = None
    INTI_INSPECCION_VIGENTE: Optional[bool] = None
    AUTORIZACION_MUNICIPAL_VIGENTE: Optional[bool] = None
    SENALIZACION_28BIS_CUMPLIDA: Optional[bool] = None

    # Notificación / validez probatoria
    NOTIFICACION_EN_60_DIAS: bool = False
    NOTIFICACION_FEHACIENTE: bool = False
    IMPUTACION_INDICA_NORMA: bool = False
    FIRMA_DIGITAL_VALIDA: bool = False
    METADATOS_COMPLETOS: bool = False
    CADENA_CUSTODIA_ACREDITADA: bool = False
    AGENTE_IDENTIFICADO: bool = False

    @validator("FECHA_HECHO")
    def validar_fecha(cls, v):
        try:
            dt.datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Usá formato DD/MM/AAAA")
        return v

    @validator("HORA_HECHO")
    def validar_hora(cls, v):
        try:
            dt.datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Usá formato HH:MM (24h)")
        return v

class Cliente(BaseModel):
    NOMBRE: str
    DNI: str
    NACIONALIDAD: str
    DOMICILIO_REAL: str
    DOMICILIO_PROCESAL: Optional[str] = None
    DOMINIO: str
    VEHICULO_MARCA: str
    VEHICULO_MODELO: str
    ADJUNTA_DNI_IMG: bool = True
    ADJUNTA_CEDULA_IMG: bool = True
    ADJUNTA_FIRMA_IMG: bool = True
    ADJUNTA_ACTA_IMG: bool = True

class Caso(BaseModel):
    FECHA_PRESENTACION: str = Field(default_factory=lambda: dt.date.today().strftime('%d/%m/%Y'))
    cliente: Cliente
    infracciones: List[Infraccion]

    HAY_EQUIPO_AUTOMATICO: bool = True
    INCOMPETENCIA_TERRITORIAL: bool = False
    PLAZO_5_ANIOS_PRESCRIPCION: bool = True

    @validator("PLAZO_5_ANIOS_PRESCRIPCION", always=True)
    def calc_prescripcion(cls, v, values):
        try:
            hoy = dt.date.today()
            excede = False
            for inf in values.get("infracciones", []):
                f = dt.datetime.strptime(inf.FECHA_HECHO, "%d/%m/%Y").date()
                if (hoy - f).days >= 5 * 365:
                    excede = True
                    break
            return excede
        except Exception:
            return v

# =============================
# Helpers de almacenamiento
# =============================

def cliente_dir(nombre: str) -> Path:
    safe = slugify(nombre)
    d = BASE_DIR / safe
    (d / JSON_DIRNAME).mkdir(parents=True, exist_ok=True)
    (d / SALIDAS_DIRNAME).mkdir(parents=True, exist_ok=True)
    return d

def guardar_json(caso: Caso, nombre_cliente: str) -> Path:
    d = cliente_dir(nombre_cliente) / JSON_DIRNAME
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = slugify(caso.infracciones[0].NRO_ACTA) if caso.infracciones else "sin_acta"
    fname = f"{ts}__{base}.json"
    path = d / fname
    with open(path, "w", encoding="utf-8") as f:
        json.dump(caso.dict(), f, ensure_ascii=False, indent=2)
    return path


def guardar_adjuntos(base_name: str, dni_file, cedula_file, firma_file) -> None:
    """Guarda imágenes de adjuntos en la carpeta global de adjuntos."""
    if not base_name:
        return
    for upl, suf in [
        (dni_file, "dni"),
        (cedula_file, "cedula"),
        (firma_file, "firma"),
    ]:
        if upl is None:
            continue
        ext = Path(upl.name).suffix or ".jpg"
        dest = ADJUNTOS_DIR / f"{base_name}_{suf}{ext}"
        dest.write_bytes(upl.getvalue())

def listar_jsons(nombre_cliente: str) -> List[Path]:
    d = cliente_dir(nombre_cliente) / JSON_DIRNAME
    return sorted(d.glob("*.json"))

def cargar_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# =============================
# Render DOCX
# =============================

def ejecutar_render(json_path: Path):
    """Genera el DOCX para el JSON dado. Devuelve (ok, out_file_path)."""
    # Validaciones de rutas
    if not RENDER_SCRIPT.exists():
        st.error("No se encontró descargos_render_v2.py. Colocalo en /scripts o ajustá la ruta.")
        return False, None
    if not TEMPLATE_DOCX.exists():
        st.error(f"No se encontró la plantilla: {TEMPLATE_DOCX}")
        return False, None
    if not json_path.exists():
        st.error(f"No se encontró el JSON: {json_path}")
        return False, None

    # salidas = carpeta del JSON / ../salidas
    cliente_root = json_path.parent.parent          # .../casos/<cliente>/
    out_dir = cliente_root / SALIDAS_DIRNAME
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / (json_path.stem + ".docx")

    cmd = [
        sys.executable,              # usa el mismo intérprete que corre Streamlit
        str(RENDER_SCRIPT),
        "--plantilla", str(TEMPLATE_DOCX),
        "--caso", str(json_path),
        "--salida", str(out_file),
        "--estricto",
    ]

    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if completed.stdout:
            st.code(completed.stdout)
        if completed.stderr:
            st.warning(completed.stderr)

        if out_file.exists():
            st.success(f"Generado: {out_file}")
            return True, out_file
        else:
            st.error("El render no reportó error pero el archivo no apareció. Revisá rutas/permisos.")
            return False, None

    except subprocess.CalledProcessError as e:
        st.error(f"Fallo ejecutando el render.\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}")
        return False, None

# =============================
# UI
# =============================

st.set_page_config(page_title="Descarguinator · Generador de JSONs", layout="wide")
st.title("🧾 Descarguinator — Creador de JSONs dinámicos y generador de descargos")

# Sidebar: gestionar clientes
st.sidebar.header("Cliente")
modo = st.sidebar.radio(
    "¿Qué querés hacer?",
    ["Crear descargos con nuevo cliente", "Crear descargos con cliente existente"],
    horizontal=False,
)

if modo == "Crear descargos con nuevo cliente":
    if "_pdf_uploader_key" not in st.session_state:
        st.session_state._pdf_uploader_key = 0
    uploaded_pdf = st.file_uploader(
        "Acta en PDF",
        type="pdf",
        key=f"pdf_uploader_{st.session_state._pdf_uploader_key}"
    )
    if uploaded_pdf and pdf_to_descargo and st.session_state.get("_pdf_last") != uploaded_pdf.name:
        parser = getattr(pdf_to_descargo, "parse_pdf", None)
        if parser is None:
            st.error("pdf_to_descargo no tiene función parse_pdf")
        else:
            try:
                data = parser(uploaded_pdf)
                if "infrs" not in st.session_state:
                    st.session_state.infrs = []
                st.session_state.infrs.append(data.get("infracciones", [{}])[0])
                cli = data.get("cliente", {})
                cli_mapping = {
                    "cli_nombre": "NOMBRE",
                    "cli_dni": "DNI",
                    "cli_nacionalidad": "NACIONALIDAD",
                    "cli_dom_real": "DOMICILIO_REAL",
                    "cli_dom_proc": "DOMICILIO_PROCESAL",
                    "cli_dominio": "DOMINIO",
                    "cli_veh_marca": "VEHICULO_MARCA",
                    "cli_veh_modelo": "VEHICULO_MODELO",
                }
                for st_key, data_key in cli_mapping.items():
                    if data_key in cli:
                        st.session_state[st_key] = cli[data_key]
                st.session_state._pdf_last = uploaded_pdf.name
                st.session_state._pdf_uploader_key += 1
            except Exception as e:
                st.error(f"Fallo procesando PDF: {e}")
    elif uploaded_pdf and pdf_to_descargo is None:
        msg = "No se pudo importar pdf_to_descargo"
        if _PDF_IMPORT_ERROR:
            msg += f": {_PDF_IMPORT_ERROR}"
        st.warning(msg + ". Instalá sus dependencias para habilitar el parseo automático.")

    st.sidebar.subheader("Datos del cliente")
    nombre = st.sidebar.text_input("Nombre completo", key="cli_nombre")
    dni = st.sidebar.text_input("DNI", key="cli_dni")
    nacionalidad = st.sidebar.text_input("Nacionalidad", value="Argentina", key="cli_nacionalidad")
    domicilio_real = st.sidebar.text_area("Domicilio real", key="cli_dom_real")
    mismo_domicilio = st.sidebar.checkbox("Domicilio procesal = real", value=True, key="cli_same_dom")
    domicilio_procesal = st.session_state.cli_dom_real if mismo_domicilio else st.sidebar.text_area("Domicilio procesal", key="cli_dom_proc")
    dominio = st.sidebar.text_input("Dominio (patente)", key="cli_dominio")
    veh_marca = st.sidebar.text_input("Vehículo marca", key="cli_veh_marca")
    veh_modelo = st.sidebar.text_input("Vehículo modelo", key="cli_veh_modelo")

    st.sidebar.divider()
    st.sidebar.markdown("**Adjuntos**")
    adj_dni = st.sidebar.checkbox("Adjunta DNI", value=True)
    dni_file = st.sidebar.file_uploader("Archivo DNI", type=["jpg","jpeg","png"], key="dni_file")
    adj_cedula = st.sidebar.checkbox("Adjunta Cédula", value=True)
    ced_file = st.sidebar.file_uploader("Archivo Cédula", type=["jpg","jpeg","png"], key="ced_file")
    adj_firma = st.sidebar.checkbox("Adjunta Firma", value=True)
    firma_file = st.sidebar.file_uploader("Archivo Firma", type=["jpg","jpeg","png"], key="firma_file")
    adj_acta = st.sidebar.checkbox("Adjunta Acta", value=True)

    st.markdown("---")
    st.subheader("Infracciones del caso")

    if "infrs" not in st.session_state:
        st.session_state.infrs = []

    col_btn = st.columns([1,1,8])
    if col_btn[0].button("➕ Agregar infracción"):
        st.session_state.infrs.append({
            "TIPO_INFRACCION": "velocidad",
            "NRO_ACTA": "",
            "FECHA_HECHO": dt.date.today().strftime('%d/%m/%Y'),
            "HORA_HECHO": "00:00",
            "LUGAR": "",
            "JUZGADO": "",
            "MUNICIPIO": "",
            "EQUIPO_MARCA": None,
            "EQUIPO_MODELO": None,
            "EQUIPO_SERIE": None,
            "PATENTE_LEGIBLE": None,
            "INTI_INSPECCION_VIGENTE": None,
            "AUTORIZACION_MUNICIPAL_VIGENTE": None,
            "SENALIZACION_28BIS_CUMPLIDA": None,
        })

    if col_btn[1].button("🗑️ Quitar última") and st.session_state.infrs:
        st.session_state.infrs.pop()

    for idx, inf in enumerate(st.session_state.infrs):
        with st.expander(f"Infracción #{idx+1}", expanded=True):
            c1, c2, c3 = st.columns(3)
            tipo_opts = ["semaforo", "velocidad", "senda_peatonal", "luces", "cinturon"]
            inf["TIPO_INFRACCION"] = c1.selectbox(
                "Tipo",
                options=tipo_opts,
                index=tipo_opts.index(inf.get("TIPO_INFRACCION", "velocidad")),
                key=f"tipo_{idx}"
            )
            inf["NRO_ACTA"] = c2.text_input("Nro. Acta", value=inf.get("NRO_ACTA",""), key=f"acta_{idx}")
            inf["LUGAR"] = c3.text_input("Lugar", value=inf.get("LUGAR",""), key=f"lugar_{idx}")
            c4, c5, c6 = st.columns(3)
            inf["JUZGADO"] = c4.text_input("Juzgado", value=inf.get("JUZGADO",""), key=f"juz_{idx}")
            inf["MUNICIPIO"] = c5.text_input("Municipio", value=inf.get("MUNICIPIO",""), key=f"muni_{idx}")
            inf["FECHA_HECHO"] = c6.text_input("Fecha del hecho (DD/MM/AAAA)", value=inf.get("FECHA_HECHO",""), key=f"fecha_{idx}")
            c7, c8 = st.columns(2)
            inf["HORA_HECHO"] = c7.text_input("Hora del hecho (HH:MM)", value=inf.get("HORA_HECHO",""), key=f"hora_{idx}")

            if inf["TIPO_INFRACCION"] == "velocidad":
                st.markdown("**Datos del cinemómetro**")
                c9, c10, c11 = st.columns(3)
                inf["EQUIPO_MARCA"] = c9.text_input("Equipo: Marca", value=inf.get("EQUIPO_MARCA") or "", key=f"emarca_{idx}") or None
                inf["EQUIPO_MODELO"] = c10.text_input("Equipo: Modelo", value=inf.get("EQUIPO_MODELO") or "", key=f"emodelo_{idx}") or None
                inf["EQUIPO_SERIE"] = c11.text_input("Equipo: Serie", value=inf.get("EQUIPO_SERIE") or "", key=f"eserie_{idx}") or None
                st.markdown("**Chequeos de validez**")
                c12, c13, c14, c15 = st.columns(4)
                inf["INTI_INSPECCION_VIGENTE"] = c12.checkbox(
                    "INTI vigente",
                    value=bool(inf.get("INTI_INSPECCION_VIGENTE")),
                    key=f"inti_{idx}"
                )
                inf["AUTORIZACION_MUNICIPAL_VIGENTE"] = c13.checkbox(
                    "Autorización municipal vigente",
                    value=bool(inf.get("AUTORIZACION_MUNICIPAL_VIGENTE")),
                    key=f"auto_muni_{idx}"
                )
                inf["SENALIZACION_28BIS_CUMPLIDA"] = c14.checkbox(
                    "Señalización art. 28 bis",
                    value=bool(inf.get("SENALIZACION_28BIS_CUMPLIDA")),
                    key=f"28bis_{idx}"
                )
                inf["PATENTE_LEGIBLE"] = c15.checkbox(
                    "Patente legible en foto",
                    value=bool(inf.get("PATENTE_LEGIBLE")),
                    key=f"patente_{idx}"
                )

            st.markdown("**Validez formal / notificaciones**")
            c16, c17, c18, c19 = st.columns(4)
            inf["NOTIFICACION_EN_60_DIAS"] = c16.checkbox(
                "Notificación < 60 días",
                value=inf.get("NOTIFICACION_EN_60_DIAS", False),
                key=f"not60_{idx}"
            )
            inf["NOTIFICACION_FEHACIENTE"] = c17.checkbox(
                "Notificación fehaciente",
                value=inf.get("NOTIFICACION_FEHACIENTE", False),
                key=f"notfeh_{idx}"
            )
            inf["IMPUTACION_INDICA_NORMA"] = c18.checkbox(
                "Indica norma violada",
                value=inf.get("IMPUTACION_INDICA_NORMA", False),
                key=f"norma_{idx}"
            )
            inf["FIRMA_DIGITAL_VALIDA"] = c19.checkbox(
                "Firma digital válida",
                value=inf.get("FIRMA_DIGITAL_VALIDA", False),
                key=f"firma_{idx}"
            )

            c20, c21, c22 = st.columns(3)
            inf["METADATOS_COMPLETOS"] = c20.checkbox(
                "Metadatos completos",
                value=inf.get("METADATOS_COMPLETOS", False),
                key=f"metadata_{idx}"
            )
            inf["CADENA_CUSTODIA_ACREDITADA"] = c21.checkbox(
                "Cadena de custodia acreditada",
                value=inf.get("CADENA_CUSTODIA_ACREDITADA", False),
                key=f"cadena_{idx}"
            )
            inf["AGENTE_IDENTIFICADO"] = c22.checkbox(
                "Agente identificado",
                value=inf.get("AGENTE_IDENTIFICADO", False),
                key=f"agente_{idx}"
            )

    st.markdown("---")
    col_save1, col_save2 = st.columns(2)
    if col_save1.button("💾 Guardar JSON del caso"):
        faltan = (
            not nombre or not dni or not st.session_state.infrs or
            any(not i.get("JUZGADO") or not i.get("MUNICIPIO") or not i.get("NRO_ACTA") for i in st.session_state.infrs)
        )
        if faltan:
            st.error("Completá: Nombre, DNI y Juzgado/Municipio/Nro. de acta en cada infracción.")
        else:
            try:
                cliente = Cliente(
                    NOMBRE=nombre,
                    DNI=dni,
                    NACIONALIDAD=nacionalidad,
                    DOMICILIO_REAL=domicilio_real,
                    DOMICILIO_PROCESAL=domicilio_procesal,
                    DOMINIO=dominio,
                    VEHICULO_MARCA=veh_marca,
                    VEHICULO_MODELO=veh_modelo,
                    ADJUNTA_DNI_IMG=adj_dni,
                    ADJUNTA_CEDULA_IMG=adj_cedula,
                    ADJUNTA_FIRMA_IMG=adj_firma,
                    ADJUNTA_ACTA_IMG=adj_acta,
                )
                infrs = [Infraccion(**i) for i in st.session_state.infrs]
                caso = Caso(cliente=cliente, infracciones=infrs)
                path = guardar_json(caso, nombre)
                base_slug = slugify(st.session_state.infrs[0]["NRO_ACTA"]) if st.session_state.infrs else ""
                guardar_adjuntos(base_slug, dni_file, ced_file, firma_file)
                st.success(f"JSON guardado: {path}")
                st.session_state["last_json_path"] = str(path)
            except Exception as e:
                st.exception(e)

    if col_save2.button("💾 Guardar y generar descargos (.docx)"):
        faltan = (
            not nombre or not dni or not st.session_state.infrs or
            any(not i.get("JUZGADO") or not i.get("MUNICIPIO") or not i.get("NRO_ACTA") for i in st.session_state.infrs)
        )
        if faltan:
            st.error("Completá: Nombre, DNI y Juzgado/Municipio/Nro. de acta en cada infracción.")
        else:
            try:
                cliente = Cliente(
                    NOMBRE=nombre,
                    DNI=dni,
                    NACIONALIDAD=nacionalidad,
                    DOMICILIO_REAL=domicilio_real,
                    DOMICILIO_PROCESAL=domicilio_procesal,
                    DOMINIO=dominio,
                    VEHICULO_MARCA=veh_marca,
                    VEHICULO_MODELO=veh_modelo,
                    ADJUNTA_DNI_IMG=adj_dni,
                    ADJUNTA_CEDULA_IMG=adj_cedula,
                    ADJUNTA_FIRMA_IMG=adj_firma,
                    ADJUNTA_ACTA_IMG=adj_acta,
                )
                infrs = [Infraccion(**i) for i in st.session_state.infrs]
                caso = Caso(cliente=cliente, infracciones=infrs)
                path = guardar_json(caso, nombre)
                base_slug = slugify(st.session_state.infrs[0]["NRO_ACTA"]) if st.session_state.infrs else ""
                guardar_adjuntos(base_slug, dni_file, ced_file, firma_file)
                st.success(f"JSON guardado: {path}")
                st.session_state["last_json_path"] = str(path)
                ok, out_path = ejecutar_render(path)
                if ok and out_path:
                    st.success(f"Archivos generados en: {out_path.parent}")
            except Exception as e:
                st.exception(e)

    # Botón para generar descargos desde el último JSON guardado
    colg1, colg2 = st.columns([1,3])
    if colg1.button("🧩 Generar descargos (.docx) con el último JSON"):
        jp = st.session_state.get("last_json_path")
        if not jp:
            st.error("Primero guardá un JSON.")
        else:
            jpath = Path(jp)
            ok, out_path = ejecutar_render(jpath)
            if ok and out_path:
                st.success(f"Archivos generados en: {out_path.parent}")

else:
    # Crear descargos con cliente existente
    st.sidebar.subheader("Crear descargos con cliente existente")
    clientes = sorted([p.name for p in BASE_DIR.iterdir() if p.is_dir()])
    if not clientes:
        st.info("No hay clientes todavía. Cambiá a 'Crear descargos con nuevo cliente'.")
    else:
        cli = st.sidebar.selectbox("Cliente", options=clientes)
        jpaths = listar_jsons(cli)
        if not jpaths:
            st.warning("Ese cliente no tiene JSONs guardados.")
        else:
            opciones = [p.name for p in jpaths]
            sel = st.selectbox("Elegí un JSON", options=opciones)
            elegido = jpaths[opciones.index(sel)]

            data = cargar_json(elegido)
            st.code(json.dumps(data, ensure_ascii=False, indent=2), language="json")

            cbtn1, cbtn2 = st.columns([1,3])
            if cbtn1.button("🧩 Generar descargos (.docx) desde este JSON"):
                ok, out_path = ejecutar_render(elegido)
                if ok and out_path:
                    st.success(f"Archivos generados en: {out_path.parent}")

            st.markdown("---")
            st.subheader("Duplicar como caso nuevo (para editar)")
            nuevo_nombre = st.text_input("Nuevo nombre de cliente (o el mismo)", value=cli)
            if st.button("📄 Duplicar JSON y pasar a edición"):
                st.session_state.infrs = data.get("infracciones", [])
                st.experimental_set_query_params(modo="Crear descargos con nuevo cliente")
                st.success("Andá a la pestaña 'Crear descargos con nuevo cliente' (sidebar) — se prellenó con este JSON.")
