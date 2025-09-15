"""Streamlit entry-point orchestrating the Descarguinator UI."""

import streamlit as st

from ui import components, layout, theme


st.set_page_config(page_title="R&T Gestiones Automotor", page_icon="app/assets/favicon.png")


if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False


def main() -> None:
    theme.inject_theme()
    layout.sidebar()
    layout.header()

    st.write("Dashboard")
    components.metric_card("Descargos generados", "0")
    components.metric_card("Multas reducidas", "0")
    components.metric_card("Clientes activos", "0")

    components.cta("Nuevo caso", "➕")
    components.cta("Subir PDF", "📄")
    components.cta("Generar DOCX", "🧾")


if __name__ == "__main__":
    main()