from pathlib import Path
import streamlit as st


def metric_card(label: str, value: int | str) -> None:
    """Render a single metric card."""
    st.metric(label, value)


def _collect_stats(cases_root: Path) -> tuple[int, int, int]:
    """Return counts for cases, json files and generated descargos."""
    cases = [p for p in cases_root.iterdir() if p.is_dir()] if cases_root.exists() else []
    jsons = list(cases_root.glob("*/json/*.json")) if cases_root.exists() else []
    descargos = list(cases_root.glob("*/salidas/*.docx")) if cases_root.exists() else []
    return len(cases), len(jsons), len(descargos)


def render_dashboard() -> None:
    """Render cards and call-to-action buttons for the dashboard."""
    base_dir = Path(__file__).resolve().parents[2]
    cases_dir = base_dir / "casos"
    cases, jsons, descargos = _collect_stats(cases_dir)

    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card("Casos", cases)
    with col2:
        metric_card("JSONs", jsons)
    with col3:
        metric_card("Descargos", descargos)

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        st.button("Nuevo caso")
    with col_btn2:
        st.button("Actualizar")
