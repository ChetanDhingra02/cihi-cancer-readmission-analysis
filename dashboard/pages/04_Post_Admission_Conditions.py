"""Page 4 — conditions recorded as starting after admission."""

from __future__ import annotations

import streamlit as st

from src import charts, data_loader, ui
from src import formatting as fmt
from src.metrics import get_key_number


def render() -> None:
    ui.page_header(
        eyebrow="Question 3",
        title="Conditions recorded as arising after admission",
        standfirst=(
            "Canadian hospital records note, for every diagnosis, whether it was "
            "recorded as present on admission or as arising afterwards. How often "
            "is at least one condition coded as arising after admission during a cancer stay?"
        ),
    )

    outcomes = data_loader.load("q3_outcomes")
    conditions = data_loader.load("q3_common_conditions")
    by_group = data_loader.load("q3_by_group")

    episodes_n = fmt.count(get_key_number("cancer_episodes_total"))
    share = get_key_number("q3_post_admission_pct")

    ui.answer(
        f"<em>{fmt.pct(share)}</em> of cancer hospital stays recorded at least one "
        "condition as arising after admission.",
        sub=(
            f"That is {fmt.count(get_key_number('q3_post_admission_n'))} of "
            f"{episodes_n} stays. It is a note about <b>when</b> a condition was "
            "recorded — it does not say the condition was avoidable, that anyone made "
            "a mistake, or that the hospital caused it."
        ),
    )

    with ui.card():
        st.markdown(
            '<div class="fig-head"><div class="t">If 100 cancer hospital stays were observed</div><div class="s">'
            'Each circle is one stay. Filled '
            "circles had at least one condition recorded as starting after "
            "admission.</div></div>",
            unsafe_allow_html=True,
        )
        ui.dots(share, f"At least one — {fmt.pct(share)}", "None recorded", tone="alt")

    ui.callout(
        "Expected consequences of serious illness and of treatment are recorded the "
        "same way as events a reviewer would worry about, and the record cannot "
        "tell them apart. Someone having major cancer surgery may well develop a "
        "condition recorded afterwards without anything having gone wrong. This page "
        "is not a measure of hospital harm, and the project does not call it one.",
        title="What the flag means, and what it does not",
        tone="caution",
    )

    ui.section("What tends to go with it")
    ui.figure(
        charts.post_admission_outcomes(outcomes),
        "Stays with and without a condition recorded after admission",
        f"All cancer hospital stays, {episodes_n} in total. Raw figures, not adjusted.",
        note_text="Source: q3_outcomes.csv.",
    )
    ui.plain(
        f"Stays with such a condition ended in death "
        f"<b>{fmt.pct(get_key_number('q3_died_with_pct'))}</b> of the time against "
        f"<b>{fmt.pct(get_key_number('q3_died_without_pct'))}</b> without one, and "
        "were far more likely to involve intensive care and to run past six days. "
        "Length of stay works in both directions here: a longer stay gives more "
        "time for a condition to be recorded, and conditions arising during a stay may also accompany "
        "longer, more complex care."
    )

    ui.section(
        "Which conditions",
        "Ranked by how many stays recorded the code at least once.",
    )
    ui.figure(
        charts.post_admission_conditions(conditions),
        "Most frequently recorded conditions arising after admission",
        f"Share of {episodes_n} cancer hospital stays, by diagnosis code",
        note_text=(
            "Counted once per stay however many times the code appears. Source: "
            "q3_common_conditions.csv."
        ),
    )
    ui.plain(
        "The list reads as the ordinary hazards of being seriously ill in hospital: "
        "complications of a procedure, disturbed salt and fluid balance, confusion, "
        "low blood pressure, infection, low white cells. No single code appears in "
        "more than a few per cent of stays."
    )

    ui.section("The fine print")
    how, limits, detail = st.tabs(
        ["How this was measured", "What it does not prove", "Technical detail"]
    )

    with how:
        ui.population(
            f"All cancer hospital stays: <b>{episodes_n} stays</b>. A condition is "
            "counted once per stay, however many records or diagnosis slots carry it."
        )
        ui.plain(
            "Canadian hospital records classify each diagnosis by type. Type 1 means "
            "the condition was recorded as present on admission. Type 2 means it was recorded as "
            "arising after admission. This page counts stays with at least one "
            "type 2 diagnosis. The same distinction is why the readmission model "
            "builds its count of existing conditions from type 1 only."
        )

    with limits:
        ui.callout(
            "A flag like this measures what was written down, and what gets written "
            "down depends on how long someone stayed and how closely they were "
            "watched. The gap by length of stay — "
            f"{fmt.pct(get_key_number('q3_short_stay_pct'))} for stays under six "
            f"days against {fmt.pct(get_key_number('q3_long_stay_pct'))} for six "
            "days or longer — is wider than the gap between urgent/emergent and planned "
            "admissions. More days means more opportunity to record something.",
            title="Recording follows opportunity",
            tone="strong",
        )
        ui.plain(
            "The adjusted odds ratio for dying in hospital when such a condition is "
            f"recorded is <b>{fmt.number(get_key_number('q3_or_baseline'))}</b>. That "
            "is an association between a coding flag and an outcome. It is not an "
            "estimate of harm caused, and the records cannot establish the order in "
            "which things happened within a stay."
        )

    with detail:
        ui.figure(
            charts.post_admission_by_group(by_group),
            "Share of stays with a condition recorded after admission, by group",
            f"All cancer hospital stays, {episodes_n} in total",
            note_text="Source: q3_by_group.csv.",
        )

        with st.expander("Stays against total recorded occurrences"):
            ui.table(
                conditions.rename(
                    columns={
                        "code": "Code",
                        "condition": "Condition",
                        "n_episodes": "Stays",
                        "n_occurrences": "Recorded occurrences",
                        "pct_of_episodes": "% of stays",
                    }
                ),
                note_text=(
                    "Counting occurrences rather than stays would overstate how "
                    "common these are; for T81 the difference is several hundred "
                    "records."
                ),
            )

        with st.expander("Mortality model coefficients"):
            regression = data_loader.load("q3_death_regression")
            ui.figure(
                charts.odds_ratio_forest(regression),
                "Adjusted odds ratios for dying in hospital, baseline model",
                f"All cancer hospital stays, {episodes_n} in total.",
                note_text="Source: q3_death_regression.csv, model 1.",
            )
            display = regression.copy()
            display["factor"] = display["factor"].map(fmt.tidy_factor)
            ui.table(
                display.rename(
                    columns={
                        "model": "Model",
                        "factor": "Factor",
                        "odds_ratio": "OR",
                        "ci_low": "CI low",
                        "ci_high": "CI high",
                    }
                ),
                height=380,
            )


ui.run_page(render)
