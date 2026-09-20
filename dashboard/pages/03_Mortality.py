"""Page 3 — how the stay began, and whether it ended in death."""

from __future__ import annotations

import streamlit as st

from src import charts, data_loader, ui
from src import formatting as fmt
from src.metrics import get_key_number, get_key_text


def render() -> None:
    ui.page_header(
        eyebrow="Question 2",
        title="Urgent/emergent admission and in-hospital mortality",
        standfirst=(
            "Cancer stays with an urgent/emergent admission category end in death far more often "
            "than planned ones. How much of that gap remains after adjustment for the "
            "baseline characteristics recorded on the first abstract?"
        ),
    )

    adjusted = data_loader.load("q2_adjusted_risk")
    by_site = data_loader.load("q2_urgent_by_site")
    rules = data_loader.load("rule_robustness")

    episodes_n = fmt.count(get_key_number("cancer_episodes_total"))

    ui.answer(
        "After standardizing for measured baseline characteristics, <em>"
        f"{fmt.pct(get_key_number('q2_risk_urgent_pct'))}</em> of cancer stays would "
        "end in death if every one had begun as urgent/emergent, against <em>"
        f"{fmt.pct(get_key_number('q2_risk_planned_pct'))}</em> if every one had been "
        "planned.",
        sub=(
            f"All {episodes_n} cancer hospital stays, adjusted for age band, sex, "
            "cancer group, whether the cancer had spread, and recorded conditions. "
            "This is the least certain finding in the study — the Robustness page "
            "explains why, and the warning below is not a formality."
        ),
        viz=ui.viz_duo(
            [
                ("Urgent/emergent", get_key_number("q2_risk_urgent_pct"),
                 fmt.pct(get_key_number("q2_risk_urgent_pct")), "a"),
                ("Planned", get_key_number("q2_risk_planned_pct"),
                 fmt.pct(get_key_number("q2_risk_planned_pct")), "b"),
            ],
            caption="Risk of death, adjusted",
        ),
    )

    ui.section("Before adjusting for anything")
    ui.stat_grid(
        [
            {
                "value": fmt.pct(get_key_number("q2_unadjusted_urgent_pct")),
                "label": "Urgent/emergent stays",
                "note": "Ended in death. Raw figure, no adjustment.",
            },
            {
                "value": fmt.pct(get_key_number("q2_unadjusted_planned_pct")),
                "label": "Planned stays",
                "note": "Raw figure, no adjustment.",
            },
            {
                "value": fmt.pct(get_key_number("q2_urgent_share_pct")),
                "label": "Urgent/emergent admission",
                "note": f"{fmt.pct(get_key_number('q2_ed_share_pct'))} came through "
                        "an emergency department, which is a different record.",
                "tone": "quiet",
            },
        ]
    )

    ui.figure(
        charts.mortality_urgent_vs_planned(adjusted),
        "Risk of dying in hospital if every stay had begun the same way",
        f"All cancer hospital stays, {episodes_n} in total, adjusted for measured "
        "baseline characteristics recorded on the first abstract.",
        note_text="Source: q2_adjusted_risk.csv.",
    )
    ui.plain(
        "The gap narrows once age, cancer type and recorded conditions are taken "
        "into account, but it stays large: about "
        f"<b>{fmt.number(get_key_number('q2_risk_ratio'))} times the risk</b>, or "
        f"<b>{fmt.points(get_key_number('q2_risk_difference'))}</b> more deaths per "
        "100 stays."
    )

    ui.stat_grid(
        [
            {
                "value": fmt.number(get_key_number("q2_risk_ratio")),
                "label": "Times the risk",
                "note": fmt.interval(get_key_text("q2_risk_ratio_ci")),
                "small": True,
            },
            {
                "value": fmt.points(get_key_number("q2_risk_difference")),
                "label": "Extra per 100 stays",
                "note": fmt.interval(get_key_text("q2_risk_difference_ci")),
                "small": True,
            },
            {
                "value": fmt.number(get_key_number("q2_odds_ratio")),
                "label": "Odds ratio",
                "note": "Larger than the figure above because dying is common in "
                        "the urgent/emergent group.",
                "small": True,
                "tone": "quiet",
            },
        ]
    )

    interval = fmt.parse_interval(get_key_text("q2_risk_ratio_ci"))
    ui.callout(
        "Rebuilding the study under five defensible ways of deciding where one "
        "hospital stay ends and the next begins moves this figure between "
        f"{fmt.number(get_key_number('rule_q2_rr_min'))} and "
        f"{fmt.number(get_key_number('rule_q2_rr_max'))} — a spread of "
        f"{fmt.number(get_key_number('rule_q2_rr_spread'))}"
        + (f", about as wide as its own confidence interval of {interval[0]:g} to "
           f"{interval[1]:g}" if interval else "")
        + ". Read it as a large difference of uncertain size rather than a precise "
        "multiple. The readmission finding on the previous page behaves much better.",
        title="Treat the exact number with caution",
        tone="caution",
    )
    ui.figure(
        charts.rule_robustness(
            rules, "q2_risk_ratio",
            interval=interval,
            primary=get_key_number("q2_risk_ratio"),
            x_title="Risk ratio, recalculated on each rule's version of the data",
        ),
        "The same finding, recalculated five ways",
        "The shaded band is the range reported for the main figure. Two of the five "
        "rules land outside it.",
        note_text="Source: rule_robustness.csv.",
    )

    ui.section("The fine print")
    how, limits, detail = st.tabs(
        ["How this was measured", "What it does not prove", "Technical detail"]
    )

    with how:
        ui.population(
            f"All cancer hospital stays: <b>{episodes_n} stays</b>, including those "
            "ending in death. This is a wider group than the readmission page, "
            "which only follows people who went home."
        )
        ui.callout(
            "Two different records are easy to confuse. The admission category says "
            "whether a stay was urgent or planned. The entry code says whether the "
            "person came in through an emergency department. A stay can be urgent "
            "without an emergency-department entry, and the two figures on this "
            "page differ by several points. They are kept separate throughout.",
            title="Urgent/emergent admission is not the same as ED entry",
            tone="caution",
        )
        ui.plain(
            "The primary model adjusts only for measured baseline characteristics from the first abstract. "
            "Palliative care coding and conditions recorded as arising during the stay are "
            "deliberately left out, because they happen after the point being "
            "compared and would absorb part of the very difference being measured."
        )

    with limits:
        ui.callout(
            "The records hold no cancer stage, no measure of how well someone was "
            "functioning, and nothing about how sick they were on arrival. Those "
            "are exactly the kinds of factors that can influence whether an admission is urgent/emergent, "
            "so a good part of this gap is likely to be the difference between the "
            "people rather than the difference between the routes in. Adjusting for "
            "age and cancer type does not fix that.",
            title="What is missing matters here",
            tone="strong",
        )
        ui.plain(
            "Deaths are counted only if they happen in hospital. Someone who is "
            "discharged and dies at home does not appear, so this is a measure of "
            "dying during the stay, not of survival."
        )

    with detail:
        ui.figure(
            charts.urgent_share_vs_mortality(by_site),
            "Cancer groups with more urgent/emergent admissions also had more deaths",
            "Stays where cancer was the main reason for admission, "
            f"{fmt.count(by_site['episodes'].sum())} in total. Dot size is the "
            "number of stays.",
            note_text=("Displayed cancer groups have at least 200 eligible episodes. "
                       "This is a project analysis/display filter, not a CIHI suppression "
                       "threshold. Source: q2_urgent_by_site.csv."),
        )
        ui.callout(
            "This compares group averages, not people. Cancer groups differ in far "
            "more than their admission route, and a pattern across group averages "
            "need not hold between individuals within any group.",
            title="A comparison of groups",
            tone="caution",
        )

        with st.expander("Urgent/emergent share and deaths by cancer group"):
            ui.table(
                by_site.rename(
                    columns={
                        "cancer_site": "Cancer group",
                        "episodes": "Stays",
                        "urgent": "Urgent/emergent",
                        "via_ed": "Via ED",
                        "died": "Died",
                        "pct_urgent": "Urgent/emergent %",
                        "pct_via_ed": "Via ED %",
                        "pct_died": "Died %",
                    }
                ),
                note_text=("Displayed cancer groups have at least 200 eligible episodes. "
                           "This is a project analysis/display filter, not a CIHI suppression "
                           "threshold. Source: q2_urgent_by_site.csv."),
            )

        with st.expander("Urgent/emergent share by province"):
            provinces = data_loader.load("q2_urgent_by_province")
            ui.table(
                provinces.rename(
                    columns={
                        "province": "Province",
                        "episodes": "Stays",
                        "urgent": "Urgent/emergent",
                        "pct_urgent": "Urgent/emergent %",
                    }
                ),
                note_text=(
                    "Displayed provinces have at least 300 eligible episodes. This is a project "
                    "analysis/display filter, not a CIHI suppression threshold. The file "
                    "does not include Quebec. Source: q2_urgent_by_province.csv."
                ),
            )

        with st.expander("Mortality model coefficients"):
            regression = data_loader.load("q2_death_regression")
            ui.figure(
                charts.odds_ratio_forest(regression),
                "Adjusted odds ratios for dying in hospital, baseline model",
                f"All cancer hospital stays, {episodes_n} in total.",
                note_text="Source: q2_death_regression.csv, model 1.",
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
