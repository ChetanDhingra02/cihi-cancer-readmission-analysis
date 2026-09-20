"""Render every page through Streamlit's test harness and report problems.

Run from the repository root:

    python tools/smoke_test.py

Each page is loaded in a fresh session and checked for uncaught exceptions and
for the error message the pages raise when a published table or a generated
figure is missing. Exit status is non-zero if any page fails, so this can gate a
deployment alongside tools/check_release.py.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PAGES = [
    "pages/01_Overview.py",
    "pages/02_Readmission.py",
    "pages/03_Mortality.py",
    "pages/04_Post_Admission_Conditions.py",
    "pages/05_Mortality_Trends.py",
    "pages/06_Prediction_Model.py",
    "pages/07_Robustness.py",
    "pages/08_Methods_and_Data.py",
]


def main() -> int:
    failures = 0
    for page in PAGES:
        started = time.time()
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
        app.run()
        try:
            app.switch_page(page)
            app.run()
        except Exception as exc:  # noqa: BLE001 - reporting, not handling
            print(f"FAIL  {page}: {type(exc).__name__}: {exc}")
            failures += 1
            continue

        if app.exception:
            for problem in app.exception:
                print(f"FAIL  {page}: {problem.type}: {problem.message}")
            failures += 1
            continue

        errors = [element.value for element in app.error]
        if errors:
            for message in errors:
                print(f"FAIL  {page}: page stopped with: {message[:160]}")
            failures += 1
            continue

        charts = len(app.get("plotly_chart"))
        print(
            f"OK    {page}  ({time.time() - started:4.1f}s) "
            f"charts={charts} tables={len(app.dataframe)} blocks={len(app.markdown)}"
        )
        for warning in app.warning:
            print(f"      warning: {warning.value[:160]}")

    if failures:
        print(f"\nFAILED — {failures} page(s) did not render.")
        return 1
    print(f"\nPASSED — {len(PAGES)} pages rendered without error.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
