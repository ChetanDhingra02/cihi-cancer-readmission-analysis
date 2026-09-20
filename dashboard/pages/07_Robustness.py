"""Page 7 — what happens to the findings when the assumptions change."""

from __future__ import annotations

import streamlit as st

from src import charts, data_loader, ui
from src import formatting as fmt
from src.metrics import get_key_number, get_key_text


def _width(interval_text: str):
    bounds = fmt.parse_interval(interval_text)
    return None if bounds is None else bounds[1] - bounds[0]


def render() -> None:
    ui.page_header(
        eyebrow="Method",
        title="How much would the answers change?",
        standfirst=(
            "Every study rests on judgement calls. This page changes the biggest "
            "ones on purpose, recalculates the findings from scratch each time, and "
            "reports what moved."
        ),
    )

    rule_rates = data_loader.load("transfer_rule_sensitivity")
    rules = data_loader.load("rule_robustness")
    merge = data_loader.load("transfer_merge_diagnostic")
    contamination = data_loader.load("transfer_contamination")
    los = data_loader.load("q1_los_assumption_sensitivity")
    definitions = data_loader.load("q1_sensitivity")
    cohorts = data_loader.load("cohort_definition_sensitivity")

    q1_ci = fmt.parse_interval(get_key_text("q1_risk_ratio_ci"))
    q2_ci = fmt.parse_interval(get_key_text("q2_risk_ratio_ci"))
    q1_width = _width(get_key_text("q1_risk_ratio_ci"))
    q2_width = _width(get_key_text("q2_risk_ratio_ci"))

    ui.answer(
        "One of the two headline findings barely moves. The other one moves a lot — "
        "and this page says so rather than burying it.",
        label="The short answer",
        sub=(
            "The readmission finding shifts by "
            f"{fmt.number(get_key_number('rule_q1_rr_spread'))} across five "
            "defensible ways of building the data, less than its own margin of "
            f"error. The mortality finding shifts by "
            f"{fmt.number(get_key_number('rule_q2_rr_spread'))}, about as much as "
            "its entire margin of error."
        ),
        viz=ui.viz_duo(
            [
                ("Readmission", get_key_number("rule_q1_rr_spread"),
                 fmt.number(get_key_number("rule_q1_rr_spread")), "b"),
                ("Mortality", get_key_number("rule_q2_rr_spread"),
                 fmt.number(get_key_number("rule_q2_rr_spread")), "a"),
            ],
            caption="How far each ratio moves",
        ),
    )

    ui.section(
        "The judgement call that matters most",
        "When someone is transferred between hospitals, the records show two "
        "separate stays. Treating that as a readmission would count one continuous "
        "episode of care twice — so records are joined when the coding shows a "
        "transfer. How much tolerance to allow when joining them is a choice.",
    )

    rule_names = rules["transfer_rule"].tolist()
    chosen_rule = st.selectbox("Rebuild the study using this rule", options=rule_names)
    row = rules[rules["transfer_rule"] == chosen_rule].iloc[0]
    ui.stat_grid(
        [
            {
                "value": fmt.pct(row["readmit_pct"]),
                "label": "Urgent/emergent readmission rate",
                "note": f"From {fmt.count(row['cohort_n'])} stays under this rule.",
            },
            {
                "value": fmt.number(row["q1_risk_ratio"]),
                "label": "Readmission: times the risk",
                "note": f"Main analysis reports "
                        f"{fmt.number(get_key_number('q1_risk_ratio'))}.",
            },
            {
                "value": fmt.number(row["q2_risk_ratio"]),
                "label": "Mortality: times the risk",
                "note": f"Main analysis reports "
                        f"{fmt.number(get_key_number('q2_risk_ratio'))}.",
                "tone": "accent",
            },
        ]
    )

    ui.figure(
        charts.rule_robustness(
            rules, "q1_risk_ratio", interval=q1_ci,
            primary=get_key_number("q1_risk_ratio"),
            x_title="Readmission finding, recalculated on each rule's data",
        ),
        "Question 1 is relatively stable",
        "Across the transfer-linking rules tested, every recalculated estimate lands "
        "inside the confidence interval around the main estimate.",
        note_text="Source: rule_robustness.csv.",
    )
    ui.figure(
        charts.rule_robustness(
            rules, "q2_risk_ratio", interval=q2_ci,
            primary=get_key_number("q2_risk_ratio"),
            x_title="Mortality finding, recalculated on each rule's data",
        ),
        "Question 2 is more sensitive",
        "Using the same model specifications across alternative transfer-linking rules, "
        "two of the five recalculated estimates land outside the main confidence interval.",
        note_text="Source: rule_robustness.csv.",
    )

    ui.stat_grid(
        [
            {
                "value": fmt.number(get_key_number("rule_q1_rr_spread")),
                "label": "Readmission finding moved",
                "note": (f"{fmt.number(get_key_number('rule_q1_rr_min'))} to "
                         f"{fmt.number(get_key_number('rule_q1_rr_max'))}, inside a "
                         f"margin of error {fmt.number(q1_width)} wide."
                         if q1_width else ""),
                "small": True,
            },
            {
                "value": fmt.number(get_key_number("rule_q2_rr_spread")),
                "label": "Mortality finding moved",
                "note": (f"{fmt.number(get_key_number('rule_q2_rr_min'))} to "
                         f"{fmt.number(get_key_number('rule_q2_rr_max'))}, against a "
                         f"margin of error {fmt.number(q2_width)} wide."
                         if q2_width else ""),
                "small": True,
                "tone": "accent",
            },
            {
                "value": fmt.number(get_key_number("transfer_spread_pts"), 2) + " pts",
                "label": "Raw rate moved",
                "note": "The reassuring-looking check that turned out to prove very "
                        "little.",
                "small": True,
                "tone": "quiet",
            },
        ]
    )

    ui.plain(
        "Why the difference? The readmission comparison follows stays ending in "
        "discharge home, where the joining rule changes relatively little. The mortality "
        "comparison includes long, complicated stays ending in death, which are "
        "exactly the ones the joining rule handles worst. So the mortality figure "
        "should be read as a large difference of uncertain size, and the "
        "readmission figure can be read closer to face value."
    )

    ui.section("What else was varied")
    transfers, other, detail = st.tabs(
        ["The joining rule in full", "Other assumptions", "Technical detail"]
    )

    with transfers:
        ui.figure(
            charts.transfer_rule_rate(rule_rates),
            "The raw readmission rate changes little across the rules",
            "Each rule rebuilds every stay and the whole group from the records.",
            note_text="Source: transfer_rule_sensitivity.csv.",
        )
        ui.callout(
            "This flat line is weaker evidence than it looks. The first three rules "
            "differ by only a day or two of tolerance, and the arrival day they "
            "compare is itself an estimate that can be weeks out for a long stay — "
            "so shifting the tolerance by a day cannot detect the failure it is "
            "meant to rule out. The interval-aware rules, which ask whether a stay "
            "<i>could</i> have started inside the window given its length band, are "
            "the informative comparison.",
            title="Why a flat line proves little here",
            tone="caution",
        )
        ui.figure(
            charts.merge_diagnostic(merge),
            "Joining works well for short stays and badly for long ones",
            "Records following a transfer, by how long the receiving stay lasted",
            note_text=(
                f"{fmt.pct(get_key_number('transfer_merge_pct_1day'))} of one-day "
                "receiving stays are joined to the earlier stay against "
                f"{fmt.pct(get_key_number('transfer_merge_pct_10plus'))} of stays of "
                "ten days or more. Source: transfer_merge_diagnostic.csv."
            ),
        )
        ui.figure(
            charts.contamination(contamination),
            "And the leftover error is not evenly spread",
            "Stays discharged home, by how the first stay was recorded",
            note_text=(
                f"{fmt.pct(get_key_number('transfer_contamination_urgent_pct'))} of "
                "urgent/emergent stays could be unjoined continuations against "
                f"{fmt.pct(get_key_number('transfer_contamination_planned_pct'))} of "
                "planned ones, which is why it matters. Source: "
                "transfer_contamination.csv."
            ),
        )

    with other:
        ui.figure(
            charts.los_assumption_strip(los),
            "Alternative arrival-day assumptions change the estimate little",
            "The whole group rebuilt under four assumptions about length of stay",
            note_text=(
                "The rate stays between "
                f"{fmt.pct(get_key_number('los_assumption_min_pct'), 2)} and "
                f"{fmt.pct(get_key_number('los_assumption_max_pct'), 2)}. Note the "
                "narrow axis: the whole span is under one and a half percentage "
                "points. Source: q1_los_assumption_sensitivity.csv."
            ),
        )
        ui.figure(
            charts.definition_sensitivity(definitions),
            "Six reasonable ways to define the outcome",
            "These are different questions, not six attempts at one answer",
            note_text="Source: q1_sensitivity.csv.",
        )
        ui.figure(
            charts.cohort_definition(cohorts),
            "Everyone who left alive, against only those who went home",
            "Three outcome definitions, two groups",
            note_text="Source: cohort_definition_sensitivity.csv.",
        )
        ui.plain(
            "Restricting to stays ending with discharge home lowers the readmission rate and "
            "raises the ED-entry figure, because people discharged to "
            "another facility differ systematically from those who go home. The "
            "study uses the narrower group, which is the more conservative choice."
        )

    with detail:
        ui.callout(
            "Joining fails more often for long receiving stays, and no rule "
            "available here fixes it: the records hold no admission dates, and "
            "nothing in the analysis can recover them. What could be done instead "
            "was to measure how much the failure matters, which is how the "
            "difference between the two headline findings became visible. An "
            "earlier version of this project reported a "
            f"{fmt.number(get_key_number('historical_v6_transfer_spread_pts'), 2)}"
            "-point spread on the raw rate and concluded the boundary did not "
            "matter; on the quantities the analysis actually leans on, it does.",
            title="A limitation, not a solved problem",
            tone="strong",
        )
        ui.table(
            rule_rates.rename(
                columns={
                    "transfer_rule": "Rule",
                    "kind": "Kind",
                    "episodes_total": "Stays in file",
                    "primary_cohort_n": "Main group",
                    "urgent_readmissions": "Readmissions",
                    "urgent_readmit_pct": "Readmission %",
                }
            ),
            note_text="Source: transfer_rule_sensitivity.csv.",
        )
        ui.table(
            rules.rename(
                columns={
                    "transfer_rule": "Rule",
                    "cohort_n": "Group size",
                    "readmit_pct": "Readmission %",
                    "q1_risk_ratio": "Q1 risk ratio",
                    "q1_risk_difference_pts": "Q1 difference (pts)",
                    "q2_risk_ratio": "Q2 risk ratio",
                    "q2_risk_difference_pts": "Q2 difference (pts)",
                }
            ),
            note_text="Source: rule_robustness.csv.",
        )


ui.run_page(render)
