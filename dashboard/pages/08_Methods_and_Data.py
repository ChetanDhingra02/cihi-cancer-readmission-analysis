"""Page 8 — where the data came from and what may be published from it."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import data_loader, licensing, metrics, ui
from src import formatting as fmt
from src.constants import (
    ALLOWED_TABLES,
    FISCAL_YEARS,
    GEOGRAPHIC_COVERAGE,
    GLOSSARY,
    NEVER_PUBLISHED,
    SAMPLE_DESCRIPTION,
)


def render() -> None:
    ui.page_header(
        eyebrow="Method",
        title="Where the data comes from",
        standfirst=(
            "The short version: this is licensed Canadian hospital data, used with "
            "permission, and only summary tables are published here. The tabs below "
            "hold the detail."
        ),
    )

    ui.stat_grid(
        [
            {
                "value": "3 years",
                "label": "Period covered",
                "note": f"{FISCAL_YEARS}.",
            },
            {
                "value": "~10%",
                "label": "Research sample",
                "note": "Rates and percentages describe this sample; counts are not "
                        "national totals.",
            },
            {
                "value": f"{len(ALLOWED_TABLES)}",
                "label": "Summary tables published",
                "note": "Named one by one. Nothing else can be read by this app.",
                "tone": "quiet",
            },
        ]
    )

    source, access, publish, limits, words, files = st.tabs(
        ["The data", "Getting it yourself", "What may be published",
         "Limitations", "Words used here", "Files and checks"]
    )

    with source:
        ui.definition_list(
            [
                ("What it is", "Canadian Institute for Health Information, "
                               "Discharge Abstract Database, Research Analytic File. "
                               "A summary record filled in when someone leaves "
                               "hospital."),
                ("When", FISCAL_YEARS + " (fiscal years 2021-2022, 2022-2023 and "
                                        "2023-2024)."),
                ("Where", GEOGRAPHIC_COVERAGE + ". Quebec does not submit to this "
                                                "collection, so it is absent "
                                                "throughout."),
                ("How much", SAMPLE_DESCRIPTION.capitalize() + " of hospital "
                             "records. Rates and percentages describe this research "
                             "sample; sample counts are not Canadian national totals."),
                ("What one row means", "One approximated episode of care: one or "
                                       "more hospital records joined where the "
                                       "coding shows a transfer between hospitals."),
                ("What it is not", "This is " +
                                   ", ".join(licensing.WHAT_IT_IS_NOT) + "."),
            ]
        )
        ui.callout(licensing.CIHI_ATTRIBUTION, title="Required attribution",
                   tone="strong")
        ui.note(
            "Reproduced word for word as the licence requires. It also appears in "
            "the repository README and at the foot of every page here."
        )

    with access:
        ui.plain(licensing.DATA_ACCESS)
        ui.callout(
            "If you want this data yourself: check that your institution takes part "
            "in Statistics Canada's Data Liberation Initiative, then ask your data "
            "librarian or DLI contact for the CIHI Discharge Abstract Database "
            "Research Analytic File for the years you need. It cannot be passed on "
            "by this project, and nothing in this repository gives a route to it.",
            title="How to obtain it",
        )
        ui.plain(
            "No credentials of any kind belong in a project like this: no "
            "institutional login, no password, no access token, no saved session. "
            "This application never touches the licensed file, so it has no need "
            "of any."
        )

    with publish:
        ui.definition_list(
            [
                ("Summary tables only", licensing.PUBLIC_RELEASE),
                ("Suppression stays suppressed", licensing.SUPPRESSION),
                ("No slicing your own way", licensing.NO_INTERACTIVE_REAGGREGATION),
                ("Never deployed", "The repository and this application exclude " +
                                   "; ".join(NEVER_PUBLISHED) + "."),
            ]
        )
        small_cells = data_loader.load("small_cell_report")
        ui.table(
            small_cells.rename(
                columns={"table": "Table", "row": "Row withheld", "reason": "Reason"}
            ),
            note_text=(
                "Every row held back from the published tables, and why. The app "
                "never reconstructs one. The cell-size rule in the reason column is "
                "this project's own conservative choice, not a numeric threshold "
                "stated in the CIHI or DLI terms available here. Source: "
                "small_cell_report.csv."
            ),
        )

    with limits:
        ui.callout(licensing.CAUSAL_LANGUAGE_NOTE, title="On cause and effect",
                   tone="strong")
        ui.definition_list(licensing.LIMITATIONS)

    with words:
        ui.definition_list(GLOSSARY)
        scope = data_loader.load("cancer_scope")
        display = scope.copy()
        display["in_cohort"] = display["in_cohort"].map(
            lambda value: "In the study" if bool(value) else "Excluded"
        )
        ui.table(
            display.rename(
                columns={
                    "code_range": "Codes",
                    "description": "Description",
                    "in_cohort": "Status",
                    "reason": "Reason",
                }
            ),
            note_text="Which cancer codes count. Source: cancer_scope.csv.",
        )

    with files:
        ui.definition_list(
            [
                (
                    "Figures are generated, not typed",
                    f"All {metrics.count_of_key_numbers()} reported figures are read "
                    "from key_numbers.csv when the page loads. A missing or renamed "
                    "entry stops the page and names the entry rather than falling "
                    "back to a default, so a stale number cannot survive a rerun.",
                ),
                (
                    "The file list is fixed",
                    "The app loads only the tables named in its allow-list. The data "
                    "folder is never scanned, so a file dropped in there is "
                    "unreachable from every page.",
                ),
                (
                    "The parse was checked",
                    "The fixed-width parse is checked field by field against the "
                    "SPSS version of the same file, including deep diagnosis slots.",
                ),
            ]
        )

        present = set(data_loader.present_tables())
        inventory = pd.DataFrame(
            [
                {
                    "File": spec.filename,
                    "Contents": spec.description,
                    "Status": "loaded" if key in present else "declared, missing",
                }
                for key, spec in sorted(ALLOWED_TABLES.items(),
                                        key=lambda kv: kv[1].filename)
            ]
        )
        ui.table(inventory, height=420)

        missing = data_loader.missing_tables()
        if missing:
            st.warning(
                "Declared but not present: "
                + ", ".join(ALLOWED_TABLES[key].filename for key in missing)
                + ". Pages depending on these stop with an explanation rather than "
                "drawing a partial figure."
            )
        unlisted = data_loader.unlisted_files()
        if unlisted:
            st.warning(
                "Files present in the data folder that the allow-list does not "
                "name, and that no page can read: " + ", ".join(unlisted)
                + ". Remove them unless they have been cleared for release."
            )

        verification = data_loader.load("document_verification")
        if verification.empty:
            ui.plain(
                "Every number in the generated reports traced back to an analysis "
                "output; none failed the check."
            )
        else:
            ui.table(verification)

        with st.expander("Parse validation detail"):
            validation = data_loader.load("validation_report")
            passing = int((validation["result"].astype(str).str.upper() == "PASS").sum())
            ui.table(
                validation.rename(
                    columns={
                        "variable": "Field",
                        "n_rows": "Rows",
                        "n_matching": "Matching",
                        "pct_matching": "% matching",
                        "result": "Result",
                    }
                ),
                note_text=(
                    f"{passing} of {len(validation)} checked fields matched exactly. "
                    "Source: validation_report.csv."
                ),
                height=380,
            )

        with st.expander("Key methodological decisions"):
            ui.definition_list(
                [
                    ("Episodes, not records",
                     "A transfer generates a second record. Counting it as a "
                     "readmission would split one continuous stay in two."),
                    ("Existing conditions from type 1 only",
                     "Type 2 conditions arose after admission; including them would "
                     "leak the outcome into the predictors."),
                    ("Baseline from the first record",
                     "A condition arising at one hospital is recorded as present on "
                     "arrival at the next, so using the whole episode would "
                     "contaminate the starting picture."),
                    ("Split by person, not by stay",
                     "Splitting by stay would let one person appear on both sides "
                     "of the train/test divide."),
                    ("Periods anchored on discharge",
                     "The discharge day is exact; the arrival day is estimated and "
                     "is least reliable for long stays, which is where death is "
                     "most likely."),
                    ("Margins of error allow for repeat stays",
                     "People appear more than once, so resampling stays would "
                     "understate uncertainty."),
                ]
            )

        with st.expander("Cancer group mapping"):
            mapping = data_loader.load("cancer_site_mapping")
            ui.table(
                mapping.rename(
                    columns={
                        "code_3char": "Code",
                        "cancer_site": "Group",
                        "is_primary_site": "Primary site",
                        "site_rank": "Rank",
                        "note": "Note",
                    }
                ),
                note_text=(
                    f"{len(mapping)} diagnosis codes mapped to documented groups. "
                    "Source: cancer_site_mapping.csv."
                ),
                height=380,
            )

        with st.expander("Every generated figure"):
            ui.table(
                metrics.as_frame().rename(
                    columns={"name": "Name", "value": "Value",
                             "description": "Description"}
                ),
                note_text=(
                    "The lookup table behind every number on this site. Source: "
                    "key_numbers.csv."
                ),
                height=420,
            )


ui.run_page(render)
