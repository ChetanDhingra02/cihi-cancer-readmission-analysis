"""Entry point.

Page config, navigation, and nothing else. Every page lives in pages/ and
every reusable piece lives in src/.

Streamlit's own navigation widget is hidden so that the top bar can be styled
as part of the design system; routing still runs through st.navigation, and the
links are st.page_link, so browser history and deep links behave normally.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:  # so pages can import src/ when run by Streamlit
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from src import ui  # noqa: E402

# A half-updated copy of this project fails deep inside a page with an opaque
# AttributeError. Check the pieces this entrypoint needs and say what is wrong.
_REQUIRED_UI = ("configure", "top_nav", "run_page", "hero", "findings",
                "card", "figure", "stat_grid")
_missing = [name for name in _REQUIRED_UI if not hasattr(ui, name)]
_stylesheet = ROOT / "assets" / "styles.css"

if _missing or not _stylesheet.exists():
    st.set_page_config(page_title="Setup problem", layout="centered")
    _detail = []
    if _missing:
        _detail.append(
            f"`src/ui.py` is missing: {', '.join(_missing)}. Loaded from "
            f"`{getattr(ui, '__file__', 'unknown')}`."
        )
    if not _stylesheet.exists():
        _detail.append(f"`assets/styles.css` is not at `{_stylesheet}`.")
    st.error(
        "**This copy of the project is inconsistent.**\n\n"
        + "\n\n".join(_detail)
        + "\n\nUsual causes, in order:\n\n"
        "1. A Streamlit server that was already running when the files changed. "
        "It re-runs `app.py` but keeps modules it imported earlier, so stop it "
        "fully (Ctrl+C) and start it again.\n"
        "2. A new copy unpacked on top of an old one, leaving a mixture. Extract "
        "into an empty folder instead.\n"
        "3. Stale bytecode: delete every `__pycache__` folder in the project.\n"
        "4. More than one copy of the project, with the wrong `src/` on the "
        "import path."
    )
    st.stop()

ui.configure()

NAVIGATION = {
    "Findings": [
        st.Page("pages/01_Overview.py", title="Overview",
                icon=":material/dashboard:", default=True),
        st.Page("pages/02_Readmission.py", title="30-day readmission",
                icon=":material/replay:"),
        st.Page("pages/03_Mortality.py", title="Urgent admission and mortality",
                icon=":material/monitor_heart:"),
        st.Page("pages/04_Post_Admission_Conditions.py",
                title="Post-admission conditions",
                icon=":material/clinical_notes:"),
        st.Page("pages/05_Mortality_Trends.py", title="Mortality over time",
                icon=":material/timeline:"),
        st.Page("pages/06_Prediction_Model.py", title="Prediction model",
                icon=":material/insights:"),
    ],
    "Method": [
        st.Page("pages/07_Robustness.py", title="Robustness and uncertainty",
                icon=":material/science:"),
        st.Page("pages/08_Methods_and_Data.py",
                title="Methods, data and licensing",
                icon=":material/menu_book:"),
    ],
}

page = st.navigation(NAVIGATION, position="hidden")
ui.top_nav(NAVIGATION, current=page)
page.run()
