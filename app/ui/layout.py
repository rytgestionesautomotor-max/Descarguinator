from pathlib import Path
import streamlit as st
from . import theme

def sidebar() -> None:
    """Render the fixed sidebar with navigation and actions."""
    logo = Path("app/assets/logo_rt.png")
    if logo.exists():
        st.sidebar.image(str(logo), use_column_width=True)
    st.sidebar.title("Navegación")
    st.sidebar.toggle("Modo oscuro", key="dark_mode")


def header() -> None:
    """Render the page header."""
    st.title("R&T — Panel de Gestión")
    st.caption("Gestor de descargos")
