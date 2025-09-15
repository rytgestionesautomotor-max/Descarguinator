from pathlib import Path
import streamlit as st


def _logo_path() -> Path:
    """Return the path to the sidebar logo."""
    return Path(__file__).resolve().parents[1] / "assets" / "logo_rt.png"


def sidebar() -> None:
    """Render the fixed sidebar with navigation and actions."""
    logo = _logo_path()
    if logo.exists():
        st.sidebar.image(str(logo), use_column_width=True)
    st.sidebar.title("Navegación")
    st.sidebar.toggle("Modo oscuro", key="dark_mode")


def header() -> None:
    """Render the page header."""
    st.title("R&T — Panel de Gestión")
    st.caption("Gestor de descargos")
