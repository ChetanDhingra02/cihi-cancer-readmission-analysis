"""Page 5 — deaths in hospital across twelve quarters."""

from __future__ import annotations

import streamlit as st

from src import charts, data_loader, ui
from src import formatting as fmt
from src.metrics import get_key_number, peak_quarters


CASE_MIX_COLUMNS = {
    "pct_urgent": "Urgent/emergent admission",
    "pct_spread": "Cancer had spread",
    "pct_aged_80_plus": "Aged 80 or over",
    "pct_intensive_care": "Had intensive care",
    "pct_palliative": "Palliative care recorded",
    "pct_episode_long_stay": "Stayed six days or more",
}


def render() -> None:
    ui.page_header(
        eyebrow="Question 4",
        title="Did dying in hospital become more common?",
        standfirst=(
            "Three years of data, split into twelve three-month periods, following "
            "the share of cancer hospital stays that ended in death."
        ),
    )

    trend = data_loader.load("q4_quarterly_trend")
    models = data_loader.load("q4_trend_models")
    linearity = data_loader.load("q4_linearity_test")
    anchors = data_loader.load("q4_anchor_comparison")

    episodes_n = fmt.count(get_key_number("cancer_episodes_total"))
    adjusted_rows = models.loc[models["model"] == "Time plus measured characteristics"]
    if len(adjusted_rows) != 1:
        raise data_loader.DataError(
            "Expected exactly one Q4 model named 'Time plus measured characteristics'."
        )
    adjusted_row = adjusted_rows.iloc[0]
    peaks = peak_quarters(trend)
    final_quarter = int(trend["quarter"].max())
    change = (get_key_number("q4_last_quarter_pct")
              - get_key_number("q4_first_quarter_pct"))

    ui.answer(
        "Yes, but not steadily. Deaths in hospital rose from <em>"
        f"{fmt.pct(get_key_number('q4_first_quarter_pct'))}</em> of cancer stays in "
        f"the first three months to <em>"
        f"{fmt.pct(get_key_number('q4_last_quarter_pct'))}</em> in the last — with a "
        "peak in the middle, a fall, and another rise.",
        sub=(
            f"All {episodes_n} cancer hospital stays. The high point was "
            f"{fmt.pct(get_key_number('q4_peak_quarter_pct'))} at "
            f"{fmt.quarter_phrase(peaks)}, so the series does not simply climb, and "
            "the study does not describe it as though it does."
        ),
        viz=ui.viz_spark(
            trend.sort_values("quarter")["pct_died"],
            fmt.pct(get_key_number("q4_first_quarter_pct")),
            fmt.pct(get_key_number("q4_last_quarter_pct")),
            "First quarter",
            "Last quarter",
        ),
    )

    ui.section("The series")
    ui.stat_grid(
        [
            {
                "value": fmt.pct(get_key_number("q4_first_quarter_pct")),
                "label": "First three months",
                "note": "Share of cancer stays ending in death.",
            },
            {
                "value": fmt.pct(get_key_number("q4_peak_quarter_pct")),
                "label": "Highest point",
                "note": f"At {fmt.quarter_phrase(peaks)}. The series does not end at its "
                        "highest point.",
                "tone": "accent",
            },
            {
                "value": fmt.pct(get_key_number("q4_last_quarter_pct")),
                "label": "Final three months",
                "note": f"Period {final_quarter}. {fmt.points(change, sign=True)} against "
                        "the first period.",
            },
        ]
    )

    ui.figure(
        charts.mortality_quarterly_trend(trend),
        "Share of cancer hospital stays ending in death, by three-month period",
        f"All cancer hospital stays, {episodes_n} in total",
        note_text="Source: q4_quarterly_trend.csv.",
    )
    ui.plain(
        "The line rises through the first half, peaks at "
        f"<b>{fmt.quarter_phrase(peaks)}</b>, drops back, then climbs again. Any "
        "single straight line through this is a summary of direction, not a "
        "description of the shape."
    )

    ui.section(
        "Did the patients change?",
        "If a larger share of stays involved older patients, more spread disease, or "
        "urgent/emergent admission, that could contribute to a rising death rate. Pick a "
        "characteristic to see whether it moved.",
    )
    chosen = st.multiselect(
        "Show alongside the death rate",
        options=list(CASE_MIX_COLUMNS),
        default=["pct_urgent", "pct_spread", "pct_aged_80_plus"],
        format_func=lambda column: CASE_MIX_COLUMNS[column],
    )
    ui.figure(
        charts.trend_case_mix(trend, ["pct_died", *chosen]),
        "Deaths and the recorded characteristics over the same periods",
        f"All cancer hospital stays, {episodes_n} in total",
        note_text="Source: q4_quarterly_trend.csv.",
    )
    ui.plain(
        "The characteristics the records hold stay remarkably flat while the death "
        "rate moves. Allowing for all of them at once barely changes the trend: the "
        "increase works out at about "
        f"<b>{fmt.number(adjusted_row['odds_ratio_per_quarter'], 4)}</b> times the "
        "odds of dying per three-month period "
        f"({fmt.interval_from(adjusted_row['ci_low'], adjusted_row['ci_high'], dp=4)})."
    )

    ui.section("The fine print")
    how, limits, detail = st.tabs(
        ["How this was measured", "What it does not prove", "Technical detail"]
    )

    with how:
        ui.population(
            f"All cancer hospital stays: <b>{episodes_n} stays</b> across twelve "
            "three-month periods, each stay counted in the period it ended."
        )
        ui.plain(
            "Stays are grouped by the day the person left hospital, because that "
            "day is recorded exactly. The day they arrived has to be estimated from "
            "a banded length of stay, and the estimate is worst for long stays — "
            "which is where deaths are most likely. Grouping by the estimated "
            "arrival day instead gives almost the same picture, which is shown "
            "under technical detail."
        )

    with limits:
        ui.callout(
            "What can be said: the rise is not explained by the things these "
            "records measure.<br><br>"
            "What cannot be said from this analysis: that the patients did not "
            "change; that the pandemic caused it; that later diagnosis caused it. "
            "Cancer stage, how well someone was functioning and time since "
            "diagnosis are not in the records at all. A model that leaves out the "
            "important potential explanations cannot rule them out.",
            title="Careful with this one",
            tone="strong",
        )
        ui.plain(
            "A supplementary test comparing a straight line against letting every "
            "period go its own way gives "
            f"<b>{fmt.p_value(linearity['p_value'].iloc[0])}</b>. That means a "
            "straight line is not clearly rejected here — not that the underlying "
            "trend is a straight line."
        )

    with detail:
        ui.table(
            models.assign(p=models["p_value"].map(fmt.p_value)).rename(
                columns={
                    "model": "Model",
                    "odds_ratio_per_quarter": "Odds ratio per period",
                    "ci_low": "CI low",
                    "ci_high": "CI high",
                }
            )[["Model", "Odds ratio per period", "CI low", "CI high", "p"]],
            note_text=(
                "All three allow for the same person appearing more than once, and "
                "all three impose a straight line on a series that is not one. "
                "Source: q4_trend_models.csv."
            ),
        )
        ui.figure(
            charts.anchor_comparison(anchors),
            "Grouping by discharge day against estimated arrival day",
            f"All cancer hospital stays, {episodes_n} in total",
            note_text=(
                "The two lines track each other closely, so the trend is not an "
                "artefact of how periods were assigned. Source: "
                "q4_anchor_comparison.csv."
            ),
        )
        with st.expander("Period-by-period figures"):
            ui.table(
                trend.rename(
                    columns={
                        "quarter": "Period",
                        "episodes": "Stays",
                        "deaths": "Deaths",
                        "pct_died": "Died %",
                        "pct_urgent": "Urgent/emergent %",
                        "pct_spread": "Spread %",
                        "pct_aged_80_plus": "Aged 80+ %",
                        "pct_intensive_care": "Intensive care %",
                        "pct_palliative": "Palliative %",
                        "pct_episode_long_stay": "6+ days %",
                    }
                ),
                note_text="Source: q4_quarterly_trend.csv.",
            )


ui.run_page(render)
