import streamlit as st
from app.ui import components, layout, theme

def main() -> None:
    """Run the Descarguinator dashboard."""
    st.set_page_config(page_title="R&T Gestiones Automotor", page_icon="📄")
    layout.sidebar()
    theme.inject_theme()
    layout.header()
    components.render_dashboard()

if __name__ == "__main__":
    main()
