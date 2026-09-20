"""Page 1 — what this study asked, on whom, and what it found."""

from __future__ import annotations

import streamlit as st

from src import charts, data_loader, ui
from src import formatting as fmt
from src.constants import (
    FISCAL_YEARS,
    GEOGRAPHIC_COVERAGE,
    SAMPLE_CAVEAT,
    SAMPLE_DESCRIPTION,
)
from src.metrics import get_key_number, get_key_text, peak_quarters


def render() -> None:
    flow = data_loader.load("study_flow")
    trend = data_loader.load("q4_quarterly_trend")

    ui.hero(
        kicker="Hospital data research · portfolio project",
        title="What happens after a cancer hospital stay?",
        lede=(
            "When someone is admitted to hospital with cancer and later sent home, "
            "how often are they readmitted urgently or emergently within a month? And "
            "does it matter whether that first stay began as a planned or an "
            "urgent/emergent admission? This project follows "
            f"{fmt.count(get_key_number('cancer_episodes_total'))} cancer hospital "
            "stays across three years of Canadian records to find out."
        ),
        chips=[
            ("CIHI Discharge Abstract Database", "blue"),
            (FISCAL_YEARS, "sage"),
            (GEOGRAPHIC_COVERAGE, "beige"),
            (SAMPLE_DESCRIPTION.capitalize(), "sage"),
        ],
    )

    ui.answer(
        "About <em>1 in 6</em> cancer hospital stays that ended at home was "
        "followed by an urgent/emergent readmission within 30 days — and stays that "
        "began as urgent/emergent admissions were much more likely to be followed by one.",
        label="The headline",
        viz=ui.viz_ring(
            get_key_number("q1_point_estimate_pct"),
            fmt.pct(get_key_number("q1_point_estimate_pct")),
            "of stays: urgent return within 30 days",
        ),
        sub=(
            f"Exactly {fmt.pct(get_key_number('q1_point_estimate_pct'))} of "
            f"{fmt.count(get_key_number('cohort_episodes'))} stays, which is "
            f"{fmt.count(get_key_number('q1_events'))} readmissions. Every number "
            "on this site is read straight from the analysis outputs, and each page "
            "shows the working behind it."
        ),
    )

    ui.section("The study at a glance")
    ui.stat_grid(
        [
            {
                "value": fmt.count(get_key_number("cancer_episodes_total")),
                "label": "Cancer hospital stays studied",
                "note": "Each one is a stay involving an invasive cancer diagnosis.",
            },
            {
                "value": fmt.count(get_key_number("cohort_patients")),
                "label": "People in the main group",
                "note": "One person can have more than one stay.",
            },
            {
                "value": fmt.pct(get_key_number("q1_point_estimate_pct")),
                "label": "Came back urgently",
                "note": f"Within 30 days. {fmt.count(get_key_number('q1_events'))} urgent/emergent "
                        "readmissions after going home.",
                "tone": "accent",
            },
        ]
    )

    ui.section(
        "Who is counted",
        "The study starts with every hospital record in the file and narrows down "
        "to the group it can follow properly. Most of the drop is simply that most "
        "hospital stays are not about cancer.",
    )
    ui.figure(
        charts.cohort_flow(flow),
        "From all hospital records to the group we follow",
        "Each bar is the number of hospital stays left after one exclusion",
    )
    ui.plain(
        "Reading down: the file holds "
        f"<b>{fmt.count(get_key_number('total_abstracts'))}</b> hospital records. "
        "Records are joined together when someone was transferred between "
        "hospitals, because that is one continuous stay rather than two — "
        f"{fmt.count(get_key_number('abstracts_merged'))} records were absorbed into "
        f"an earlier one, leaving "
        f"<b>{fmt.count(get_key_number('total_episodes'))}</b> stays. "
        f"<b>{fmt.count(get_key_number('cancer_episodes_total'))}</b> of those "
        "involved an invasive cancer. The study then keeps the ones that ended with "
        "the person going home, with enough time left in the data to watch for "
        f"30 days — <b>{fmt.count(get_key_number('cohort_episodes'))}</b> stays."
    )

    with st.expander("Every exclusion, in order"):
        ui.table(
            flow.rename(columns={"step": "Step", "n": "Stays remaining",
                                 "note": "Why stays were removed"}),
            note_text="Source: study_flow.csv.",
        )

    ui.callout(
        f"{SAMPLE_CAVEAT} The file is roughly a tenth of Canadian hospital records "
        "outside Quebec, so the percentages are the meaningful part; the counts "
        "are not national totals. The largest number above is the size of the "
        "whole hospital file, not a count of cancer admissions.",
        title="What the counts mean",
    )

    ui.section(
        "What we found",
        "Five questions, each with its own page. The numbers below are the short "
        "version; the pages show how each one was worked out and how much to trust it.",
    )
    quarterly_death_share = trend.sort_values("quarter")["pct_died"]
    ui.findings(
        [
            {
                "title": "Urgent/emergent admissions were followed by more readmissions",
                "body": "After standardizing for measured baseline characteristics, "
                f"{fmt.pct(get_key_number('q1_risk_urgent_pct'))} of stays would be "
                "followed by an urgent/emergent readmission if every stay had begun as "
                "urgent/emergent, against "
                f"{fmt.pct(get_key_number('q1_risk_planned_pct'))} if every stay had "
                "been planned — about "
                f"{fmt.number(get_key_number('q1_risk_ratio'))} times the risk.",
                "go": "30-day readmission",
                "viz": ui.viz_duo(
                    [
                        ("Urgent/emergent", get_key_number("q1_risk_urgent_pct"),
                         fmt.pct(get_key_number("q1_risk_urgent_pct")), "a"),
                        ("Planned", get_key_number("q1_risk_planned_pct"),
                         fmt.pct(get_key_number("q1_risk_planned_pct")), "b"),
                    ]
                ),
            },
            {
                "title": "They were also far more likely to end in death",
                "body": f"{fmt.pct(get_key_number('q2_risk_urgent_pct'))} against "
                f"{fmt.pct(get_key_number('q2_risk_planned_pct'))} once age, sex, "
                "cancer type and other recorded conditions are accounted for. This "
                "figure is the least certain in the study, and the Robustness page "
                "explains why.",
                "go": "Urgent admission and mortality",
                "viz": ui.viz_duo(
                    [
                        ("Urgent/emergent", get_key_number("q2_risk_urgent_pct"),
                         fmt.pct(get_key_number("q2_risk_urgent_pct")), "a"),
                        ("Planned", get_key_number("q2_risk_planned_pct"),
                         fmt.pct(get_key_number("q2_risk_planned_pct")), "b"),
                    ]
                ),
            },
            {
                "title": "A quarter of stays recorded a post-admission condition",
                "body": f"{fmt.pct(get_key_number('q3_post_admission_pct'))} of cancer "
                "stays had at least one condition recorded as starting after the "
                "person was admitted. That is a record of timing, not a sign that "
                "anything went wrong.",
                "go": "Post-admission conditions",
                "viz": ui.viz_ring(
                    get_key_number("q3_post_admission_pct"),
                    fmt.pct(get_key_number("q3_post_admission_pct")),
                    "of stays",
                ),
            },
            {
                "title": "Deaths in hospital drifted upwards",
                "body": f"{fmt.pct(get_key_number('q4_first_quarter_pct'))} of cancer "
                "stays ended in death in the first three months of the data and "
                f"{fmt.pct(get_key_number('q4_last_quarter_pct'))} in the last, "
                f"peaking at {fmt.pct(get_key_number('q4_peak_quarter_pct'))} in "
                f"{fmt.quarter_phrase(peak_quarters(trend))}. The rise is bumpy, "
                "not steady.",
                "go": "Mortality over time",
                "viz": ui.viz_spark(
                    quarterly_death_share,
                    fmt.pct(get_key_number("q4_first_quarter_pct")),
                    fmt.pct(get_key_number("q4_last_quarter_pct")),
                    "First quarter",
                    "Last quarter",
                ),
            },
            {
                "title": "Readmission can be anticipated, not predicted",
                "body": "A statistical model scores "
                f"{fmt.number(get_key_number('auc_logistic'), 3)} out of 1 at telling "
                "apart who came back and who did not. That is useful for spotting "
                "groups at higher risk and not good enough to make a call about any "
                "one person.",
                "go": "Prediction model",
                "viz": ui.viz_gauge(
                    get_key_number("auc_logistic"),
                    fmt.number(get_key_number("auc_logistic"), 3),
                ),
            },
        ]
    )

    ui.section("Before you read on")
    honest, careful, deeper = st.tabs(
        ["What this can show", "What it cannot", "Where the detail lives"]
    )
    with honest:
        ui.plain(
            "This is real hospital administrative data covering three years and "
            "every province except Quebec. It is large enough to describe many patterns "
            "in this research sample with useful precision, and every figure on this site is regenerated from the "
            "analysis rather than typed in by hand."
        )
    with careful:
        ui.plain(
            "Nothing here shows cause and effect. An urgent/emergent admission category is a sign "
            "of how the stay began, not a treatment that was given, and "
            "whatever made them arrive that way may be the same thing that brings "
            "them back. The records also do not include cancer stage, which is one "
            "of the strongest things you would want to adjust for."
        )
    with deeper:
        ui.plain(
            "Each page opens with a plain-English answer, then the chart, then "
            "tabs holding the method and the caveats. The Robustness page is the "
            "honest stress test: it reports which findings survive changing the "
            "assumptions and which do not."
        )


ui.run_page(render)
