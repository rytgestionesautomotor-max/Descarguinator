import streamlit as st

from . import theme


def sidebar() -> None:
    """Render the fixed sidebar with navigation and actions."""
    st.sidebar.image("app/assets/logo_rt.png", use_column_width=True)
    st.sidebar.radio(
        "Navegación",
        ["Clientes", "Casos", "Plantillas", "Salidas", "Historial"],
        key="nav",
    )
    st.sidebar.checkbox("🌙 Modo oscuro", key="dark_mode")
    st.sidebar.write("## Acciones rápidas")
    st.sidebar.button("➕ Nuevo caso")
    st.sidebar.button("🗂️ Abrir cliente")


def header(title: str = "R&T — Panel de Gestión", subtitle: str = "Creador de JSONs y generador de descargos") -> None:
    """Top header with title and subtitle."""
    st.title(title)
    st.caption(subtitle)