import streamlit as st

def inject_theme() -> None:
    """Inject CSS variables for light and dark modes."""
    dark = st.session_state.get("dark_mode", False)

    light_css = """
    :root {
        --color-bg: #F8F9FA;
        --color-header: #0D1B2A;
        --color-accent: #1B4965;
        --color-bg-soft: #CAE9FF;
        --color-text: #1A1A1A;
        --color-success: #2ECC71;
        --color-warn: #E74C3C;
        --color-border: #E6EDF2;
        --radius-card: 16px;
        --radius-control: 12px;
        --shadow-card: 0 6px 24px rgba(13,27,42,0.08);
    }
    body {
        font-family: 'Montserrat','Poppins',system-ui,sans-serif;
        color: var(--color-text);
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat','Poppins',system-ui,sans-serif;
    }
    .rt-card {
        background: var(--color-bg);
        border-radius: var(--radius-card);
        box-shadow: var(--shadow-card);
        padding: 1rem;
    }
    .rt-cta {
        border-radius: var(--radius-control);
    }
    """

    dark_css = """
    :root {
        --color-bg: #0D1B2A;
        --color-header: #0D1B2A;
        --color-accent: #1B4965;
        --color-bg-soft: #1B4965;
        --color-text: #E9EEF4;
        --color-success: #2ECC71;
        --color-warn: #E74C3C;
        --color-border: #263648;
        --radius-card: 16px;
        --radius-control: 12px;
        --shadow-card: 0 8px 28px rgba(0,0,0,0.35);
    }
    body {
        font-family: 'Montserrat','Poppins',system-ui,sans-serif;
        color: var(--color-text);
        background: var(--color-bg);
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat','Poppins',system-ui,sans-serif;
    }
    .rt-card {
        background: var(--color-bg);
        border-radius: var(--radius-card);
        box-shadow: var(--shadow-card);
        padding: 1rem;
    }
    .rt-cta {
        border-radius: var(--radius-control);
    }
    """

    css = dark_css if dark else light_css
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)