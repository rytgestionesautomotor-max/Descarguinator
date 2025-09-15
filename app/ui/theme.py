import streamlit as st

LIGHT_CSS = """
<style>
:root {
    --bg-color: #FFFFFF;
    --text-color: #31333F;
}
</style>
"""

DARK_CSS = """
<style>
:root {
    --bg-color: #0E1117;
    --text-color: #FAFAFA;
}
</style>
"""


def inject_theme() -> None:
    """Inject basic CSS variables for light/dark modes."""
    dark = st.session_state.get("dark_mode", False)
    css = DARK_CSS if dark else LIGHT_CSS
    st.markdown(css, unsafe_allow_html=True)
    st.markdown(
        """
        <style>
        body, .stApp {
            background-color: var(--bg-color);
            color: var(--text-color);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
