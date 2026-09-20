"""Page 2 — the main question: who comes back urgently within 30 days."""

from __future__ import annotations

import streamlit as st

from src import charts, data_loader, ui
from src import formatting as fmt
from src.licensing import PROJECT_DEFINED_OUTCOME
from src.metrics import get_key_number, get_key_text


def render() -> None:
    ui.page_header(
        eyebrow="Question 1",
        title="Urgent/emergent readmission within 30 days",
        standfirst=(
            "Someone is treated in hospital for cancer and goes home. Within the "
            "next 30 days, are they readmitted with an urgent/emergent admission category?"
        ),
    )

    by_site = data_loader.load("q1_rate_by_cancer_site")
    by_province = data_loader.load("q1_rate_by_province")
    adjusted = data_loader.load("q1_adjusted_risk")
    certainty = data_loader.load("readmission_certainty")
    small_cells = data_loader.load("small_cell_report")

    cohort_n = fmt.count(get_key_number("cohort_episodes"))
    patients_n = fmt.count(get_key_number("cohort_patients"))
    rate = get_key_number("q1_point_estimate_pct")

    ui.answer(
        f"<em>{fmt.pct(rate)}</em> of cancer hospital stays that ended at home were "
        "followed by an urgent/emergent readmission within 30 days.",
        sub=(
            f"That is {fmt.count(get_key_number('q1_events'))} readmissions among "
            f"{cohort_n} stays, from {patients_n} people. Counting any return at "
            f"all, planned ones included, the figure is "
            f"{fmt.pct(get_key_number('q1_any_return_pct'))}."
        ),
        viz=ui.viz_duo(
            [
                ("Urgent/emergent", rate, fmt.pct(rate), "a"),
                ("Any return", get_key_number("q1_any_return_pct"),
                 fmt.pct(get_key_number("q1_any_return_pct")), "b"),
            ],
            caption="Back within 30 days",
        ),
    )

    with ui.card():
        st.markdown(
            '<div class="fig-head"><div class="t">If 100 cancer hospital stays ended with discharge home</div>'
            '<div class="s">Each circle is one stay. '
            "Filled circles came back urgently within 30 days.</div></div>",
            unsafe_allow_html=True,
        )
        ui.dots(
            rate,
            f"Came back urgently — {fmt.pct(rate)}",
            "Did not",
        )

    ui.section("The same question, asked of different groups")
    site_names = by_site.dropna(subset=["percent"])["cancer_site"].tolist()
    chosen_site = st.selectbox(
        "Show the figure for one cancer group",
        options=["All cancer groups"] + site_names,
    )
    if chosen_site == "All cancer groups":
        ui.stat_grid(
            [
                {
                    "value": fmt.pct(rate),
                    "label": "All groups together",
                    "note": f"{cohort_n} stays.",
                    "tone": "accent",
                },
                {
                    "value": fmt.pct(get_key_number("q1_ed_entry_pct")),
                    "label": "Readmission entered via ED",
                    "note": "Recorded separately from the admission category, so the "
                            "two figures differ.",
                },
                {
                    "value": fmt.pct(get_key_number("q1_any_return_pct")),
                    "label": "Came back for any reason",
                    "note": "Planned returns such as chemotherapy included.",
                },
            ]
        )
    else:
        row = by_site[by_site["cancer_site"] == chosen_site].iloc[0]
        ui.stat_grid(
            [
                {
                    "value": fmt.pct(row["percent"]),
                    "label": f"{chosen_site}",
                    "note": f"{fmt.count(row['readmitted'])} readmissions among "
                            f"{fmt.count(row['episodes'])} stays.",
                    "tone": "accent",
                },
                {
                    "value": f"{fmt.number(row['ci_low'], 1)}–{fmt.number(row['ci_high'], 1)}%",
                    "label": "Plausible range",
                    "note": "A wider range means fewer stays and less certainty.",
                },
                {
                    "value": fmt.pct(rate),
                    "label": "All groups, for comparison",
                    "note": f"{cohort_n} stays.",
                    "tone": "quiet",
                },
            ]
        )

    ui.figure(
        charts.readmission_by_site(by_site),
        "Urgent/emergent readmission by cancer group",
        f"Stays discharged home, {cohort_n} in total. The horizontal line through "
        "each dot is the range the true figure plausibly sits in; the dot size is "
        "how many stays that group had.",
        note_text="Source: q1_rate_by_cancer_site.csv.",
    )
    ui.plain(
        "The groups at the top are not reliably worse than the ones just below "
        "them: where the lines overlap, the ordering could easily swap. The small "
        "groups — bone and cartilage at "
        f"{fmt.count(by_site.loc[by_site['cancer_site'] == 'Bone and cartilage', 'episodes'].iloc[0])} "
        "stays, ill-defined sites at "
        f"{fmt.count(by_site.loc[by_site['cancer_site'] == 'Ill-defined site', 'episodes'].iloc[0])} "
        "— have the widest lines and should be read as rough indications only."
    )
    ui.suppression_notice(small_cells, "q1_rate_by_cancer_site")

    ui.section(
        "Does it matter how the first stay began?",
        "Some stays begin as planned admissions, for surgery or treatment. Others "
        "begin as urgent/emergent admissions. Comparing those groups fairly means "
        "accounting for the fact that they differ in age, cancer type and other "
        "recorded conditions.",
    )
    ui.figure(
        charts.adjusted_readmission_comparison(adjusted),
        "Readmission risk if every stay had begun the same way",
        f"Stays discharged home, {cohort_n} in total, adjusted for age band, sex, "
        "cancer group, whether the cancer had spread and recorded conditions.",
        note_text="Source: q1_adjusted_risk.csv, model 1 (primary).",
    )
    ui.plain(
        "Read it as two what-ifs on the same group of stays. If every stay had "
        f"begun as urgent/emergent, <b>{fmt.pct(get_key_number('q1_risk_urgent_pct'))}</b> "
        "would be followed by an urgent/emergent readmission. If every stay had been planned, "
        f"<b>{fmt.pct(get_key_number('q1_risk_planned_pct'))}</b> would — roughly "
        f"{fmt.number(get_key_number('q1_risk_ratio'))} times the risk, or "
        f"{fmt.points(get_key_number('q1_risk_difference'))} more in absolute terms."
    )

    ui.stat_grid(
        [
            {
                "value": fmt.number(get_key_number("q1_risk_ratio")),
                "label": "Times the risk",
                "note": fmt.interval(get_key_text("q1_risk_ratio_ci")),
                "small": True,
            },
            {
                "value": fmt.points(get_key_number("q1_risk_difference")),
                "label": "Extra per 100 stays",
                "note": fmt.interval(get_key_text("q1_risk_difference_ci")),
                "small": True,
            },
            {
                "value": fmt.number(get_key_number("q1_odds_ratio")),
                "label": "Odds ratio",
                "note": "Reported for readers who expect it; the figures above are "
                        "the ones described in the text.",
                "small": True,
                "tone": "quiet",
            },
        ]
    )

    ui.section("The fine print")
    how, limits, detail = st.tabs(
        ["How this was measured", "What it does not prove", "Technical detail"]
    )

    with how:
        ui.population(
            f"Cancer-related hospital stays ending in a discharge home with at "
            f"least 30 days of potential follow-up: <b>{cohort_n} stays</b> among "
            f"{patients_n} people. Stays ending in death, ending too close to the "
            "end of the data, or ending in a transfer elsewhere are not in this group."
        )
        ui.callout(
            "A readmission counts when a later stay is recorded as urgent or "
            f"emergent and begins within 30 days of going home. "
            f"{PROJECT_DEFINED_OUTCOME}",
            title="What counts as a readmission",
            tone="caution",
        )
        ui.plain(
            "The records give the day someone left hospital exactly, but the day "
            "they arrived has to be worked back from a banded length of stay. For "
            "some returns that makes the 30-day question impossible to settle, so "
            "the study reports three figures side by side rather than one."
        )
        ui.stat_grid(
            [
                {
                    "value": fmt.pct(get_key_number("q1_definite_pct")),
                    "label": "Provably within 30 days",
                    "note": f"{fmt.count(get_key_number('q1_definite_n'))} returns "
                            "that fall inside 30 days whatever the true arrival day was.",
                    "tone": "quiet",
                },
                {
                    "value": fmt.pct(get_key_number("ambiguous_pct")),
                    "label": "Cannot be settled",
                    "note": f"{fmt.count(get_key_number('ambiguous_n'))} stays where "
                            "the arrival day is too uncertain to say.",
                    "tone": "quiet",
                },
                {
                    "value": fmt.pct(get_key_number("q1_complete_case_pct")),
                    "label": "Counting only the clear cases",
                    "note": "Unsettled stays dropped from the calculation entirely.",
                    "tone": "quiet",
                },
            ]
        )
        ui.figure(
            charts.certainty_breakdown(certainty),
            "How much of the outcome can be pinned down on timing",
            f"Stays discharged home, {cohort_n} in total",
            note_text="Source: readmission_certainty.csv.",
        )

    with limits:
        ui.callout(
            "An urgent/emergent admission category is a marker of how the stay began, not "
            "something that was done to the person. Whatever led to an urgent admission — how "
            "advanced the cancer is, how well they were coping at home — is "
            "plausibly the same thing that brings them back. The comparison above "
            "is an association, and the wording throughout says so.",
            title="Not cause and effect",
            tone="strong",
        )
        ui.plain(
            "The records hold no cancer stage, no measure of how well someone was "
            "functioning, and nothing about care received outside hospital. "
            "Adjusting for age, sex and cancer type narrows the gap but cannot "
            "close it, so some of what is left is the difference between the "
            "people rather than the difference between the routes in."
        )
        ui.callout(
            "Deaths after discharge are not in these records. Someone who died at "
            "home could not be readmitted, which quietly lowers the readmission "
            "figure in the sickest groups.",
            title="One outcome hides another",
            tone="caution",
        )

    with detail:
        ui.figure(
            charts.readmission_by_province(
                by_province,
                reference=get_key_number("q1_point_estimate_pct"),
                highlight="Alberta",
            ),
            "Urgent/emergent readmission by province",
            f"Stays discharged home, {cohort_n} in total. Alberta is marked because "
            "it is held back entirely when the prediction model is tested.",
            note_text="Source: q1_rate_by_province.csv.",
        )
        ui.suppression_notice(small_cells, "q1_rate_by_province")

        st.markdown(
            f"{fmt.count(get_key_number('planned_returns_n'))} stays were followed "
            "by a planned return within 30 days, of which "
            f"{fmt.count(get_key_number('planned_returns_chemo_n'))} "
            f"({fmt.pct(get_key_number('planned_returns_chemo_pct'))}) carried a "
            "chemotherapy code. Planned returns are excluded from the main figure "
            "and counted only in the any-return figure."
        )

        with st.expander("A second model, reported as descriptive"):
            st.markdown(
                "Adding what happened during the stay — palliative care, conditions "
                "arising after admission, special care, length of stay, procedures, "
                "multi-facility care — gives adjusted risks of "
                f"{fmt.pct(get_key_number('q1_risk_urgent_full_pct'))} against "
                f"{fmt.pct(get_key_number('q1_risk_planned_full_pct'))}, a risk "
                f"ratio of {fmt.number(get_key_number('q1_risk_ratio_full'))} and an "
                f"odds ratio of {fmt.number(get_key_number('q1_odds_ratio_full'))}.\n\n"
                "Those variables are consequences of how the stay began, so "
                "conditioning on them answers a different question rather than a "
                "better-adjusted version of the same one. It is shown because it "
                "was run, not because it improves the estimate."
            )

        with st.expander("Who was in the study, readmitted against not"):
            table_one = data_loader.load("table1_characteristics")
            display = table_one.copy()
            display["overall_n"] = display["overall_n"].map(fmt.count)
            for column in ("overall_pct", "not_readmitted_pct", "readmitted_pct"):
                display[column] = display[column].map(fmt.pct)
            display["difference"] = display["difference"].map(
                lambda value: fmt.points(value, sign=True)
            )
            ui.table(
                display.rename(
                    columns={
                        "characteristic": "Characteristic",
                        "overall_n": "n",
                        "overall_pct": "Overall",
                        "not_readmitted_pct": "Not readmitted",
                        "readmitted_pct": "Readmitted",
                        "difference": "Difference",
                    }
                ),
                note_text=(
                    "Percentages are column shares within each group. Rows withheld "
                    "in the released table read Suppressed. Source: "
                    "table1_characteristics.csv."
                ),
                height=420,
            )

        with st.expander("Readmission model coefficients"):
            regression = data_loader.load("q1_regression")
            ui.figure(
                charts.odds_ratio_forest(regression),
                "Adjusted odds ratios, baseline-variables-only model",
                f"Stays discharged home, {cohort_n} in total. Reference categories: "
                "age 18-49, female, breast primary.",
                note_text="Source: q1_regression.csv, model 1.",
            )
            display = regression.copy()
            display["factor"] = display["factor"].map(fmt.tidy_factor)
            display["p_value"] = display["p_value"].map(fmt.p_value)
            ui.table(
                display.rename(
                    columns={
                        "model": "Model",
                        "factor": "Factor",
                        "odds_ratio": "OR",
                        "ci_low": "CI low",
                        "ci_high": "CI high",
                        "p_value": "p",
                    }
                ),
                height=380,
            )


ui.run_page(render)
