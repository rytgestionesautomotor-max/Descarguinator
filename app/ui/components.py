from typing import List, Optional

import streamlit as st


def metric_card(title: str, value: str, delta: Optional[str] = None) -> None:
    """Display a metric inside a styled card."""
    delta_html = f"<span>{delta}</span>" if delta else ""
    st.markdown(
        f"<div class='rt-card'><h3>{value}</h3><p>{title}</p>{delta_html}</div>",
        unsafe_allow_html=True,
    )


def cta(label: str, icon: str, on_click=None) -> None:
    """Big call-to-action button."""
    st.button(f"{icon} {label}", on_click=on_click, use_container_width=True, key=label)


def pdf_uploader(key: str):
    """PDF uploader with helper text."""
    return st.file_uploader(
        "📄 Arrastrá tu PDF o hacé click para subirlo",
        type=["pdf"],
        accept_multiple_files=True,
        key=key,
        help="Tamaño máx. 200 MB. Formato: PDF.",
    )


def cliente_form(state) -> None:
    """Simple cliente form writing to session_state."""
    with st.form("cliente_form"):
        nombre = st.text_input("Nombre", value=state.get("nombre", ""))
        dni = st.text_input("DNI", value=state.get("dni", ""))
        domicilio = st.text_input("Domicilio", value=state.get("domicilio", ""))
        dominio = st.text_input("Dominio", value=state.get("dominio", ""))
        vehiculo = st.text_input("Vehículo", value=state.get("vehiculo", ""))
        submitted = st.form_submit_button("Guardar y continuar")
        if submitted:
            st.session_state.cliente = {
                "nombre": nombre,
                "dni": dni,
                "domicilio": domicilio,
                "dominio": dominio,
                "vehiculo": vehiculo,
            }
            st.success("Listo, se subió tu PDF ✅")


def infracciones_accordion(items: List[dict]) -> None:
    """Render infracciones as accordion items."""
    if not items:
        st.info("No hay infracciones cargadas. Agregá la primera con ➕")
        return
    for idx, item in enumerate(items, 1):
        with st.expander(f"{idx}. {item.get('articulo', 'Infracción')}"):
            st.write(item)


def result_panel(json_ready: bool, doc_ready: bool) -> None:
    """Sticky panel with result actions."""
    st.markdown("<div class='rt-card'>", unsafe_allow_html=True)
    st.button("Guardar JSON", disabled=not json_ready)
    st.button("Generar DOCX", disabled=not doc_ready)
    st.button("Enviar al cliente", disabled=not doc_ready)
    st.markdown("</div>", unsafe_allow_html=True)


def alert_success(msg: str) -> None:
    st.success(msg)


def alert_warn(msg: str) -> None:
    st.warning(msg)