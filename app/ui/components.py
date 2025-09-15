import streamlit as st


def render_dashboard() -> None:
    """Render cards and call-to-action buttons for the dashboard."""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Casos", 0)
    with col2:
        st.metric("JSONs", 0)
    with col3:
        st.metric("Descargos", 0)

    st.button("Nuevo caso")
    st.button("Actualizar")
