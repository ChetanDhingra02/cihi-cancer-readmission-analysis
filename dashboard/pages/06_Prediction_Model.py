"""Page 6 — can readmission be predicted from what the records hold?"""

from __future__ import annotations

import streamlit as st

from src import charts, data_loader, ui
from src import formatting as fmt
from src.licensing import NOT_A_CLINICAL_TOOL
from src.metrics import get_key_number, get_key_text


def render() -> None:
    ui.page_header(
        eyebrow="Prediction",
        title="Can you tell in advance who will come back?",
        standfirst=(
            "A statistical model was trained on part of the data and tested on "
            "people it had never seen. The interesting question is not how clever "
            "it is, but what a score like this could honestly be used for."
        ),
    )

    performance = data_loader.load("q1_model_performance")
    calibration = data_loader.load("q1_calibration")
    thresholds = data_loader.load("q1_thresholds")
    holdout = data_loader.load("q1_geographic_holdout")

    auc = get_key_number("auc_logistic")

    ui.answer(
        "Partly. The model sorts stays into higher and lower risk quite well — the "
        "highest-risk tenth came back <em>"
        f"{fmt.pct(get_key_number('calibration_highest_actual_pct'))}</em> of the "
        "time against <em>"
        f"{fmt.pct(get_key_number('calibration_lowest_actual_pct'))}</em> in the "
        "lowest tenth — but it cannot tell you what will happen to any one person.",
        sub=(
            f"Its overall score is {fmt.number(auc, 3)} out of 1, where 0.5 is "
            "guessing and 1 is perfect "
            f"({fmt.interval(get_key_text('auc_logistic_ci'))}). This is a research "
            "model, not a tool for use in a hospital."
        ),
        viz=ui.viz_gauge(auc, fmt.number(auc, 3)),
    )

    ui.callout(NOT_A_CLINICAL_TOOL, title="Important", tone="caution")

    ui.section(
        "What flagging stays would actually mean",
        "Suppose a hospital decided to flag every stay above a certain predicted "
        "risk for extra follow-up. Pick a cut-off to see the trade you would be "
        "making. These are the four cut-offs the analysis reported.",
    )

    options = thresholds["threshold"].tolist()
    chosen = st.radio(
        "Flag stays above a predicted risk of",
        options=options,
        index=1,
        horizontal=True,
        format_func=lambda value: f"{float(value):.0%}",
    )
    row = thresholds[thresholds["threshold"] == chosen].iloc[0]

    ui.stat_grid(
        [
            {
                "value": fmt.pct(row["flagged_pct"]),
                "label": "Stays flagged",
                "note": "The workload this cut-off creates.",
                "tone": "accent",
            },
            {
                "value": fmt.proportion(row["sensitivity"]),
                "label": "Readmissions caught",
                "note": "1.0 would be every one of them.",
            },
            {
                "value": fmt.proportion(row["ppv"]),
                "label": "Flagged and came back",
                # No arithmetic on the released figures: the complement is
                # stated in words, and the one value the pipeline computed for
                # it appears under technical detail.
                "note": "The rest of the flagged stays would not have come back.",
            },
        ]
    )

    with ui.card():
        st.markdown(
            '<div class="fig-head"><div class="t">Out of 100 stays at this '
            'cut-off</div><div class="s">Filled circles are the stays that would be '
            "flagged for extra attention.</div></div>",
            unsafe_allow_html=True,
        )
        ui.dots(
            float(row["flagged_pct"]),
            f"Flagged — {fmt.pct(row['flagged_pct'])}",
            "Not flagged",
        )

    ui.plain(
        "There is no free lunch in that table. Flagging more stays catches more of "
        "the readmissions and flags more stays that would not be followed by a "
        "readmission; flagging fewer does the reverse. Which trade is worth making "
        "depends entirely on what happens after a flag — a phone call costs very "
        "little, a bed does not — and that is a question this data cannot answer."
    )

    ui.section(
        "Is the model honest about its own confidence?",
        "A model can rank stays well and still be wrong about the actual level of "
        "risk. This checks the predicted risk against what really happened.",
    )
    ui.figure(
        charts.calibration_plot(calibration),
        "Predicted risk against what actually happened",
        "Test stays grouped into ten bands of predicted risk. Points on the dashed "
        "line are exactly right.",
        note_text="Source: q1_calibration.csv.",
    )
    ui.plain(
        "The points sit close to the line, which means the predicted percentages "
        "can be taken at roughly face value. The highest-risk band is the exception: "
        "there the model predicts more readmissions than actually occurred."
    )

    ui.section("The fine print")
    how, limits, detail = st.tabs(
        ["How this was built", "What it does not prove", "Technical detail"]
    )

    with how:
        ui.population(
            "Stays discharged home, split so that no person appears in both the "
            "training and the test data. Splitting by stay rather than by person "
            "would let the model see the same individual on both sides and flatter "
            "its own score."
        )
        ui.callout(
            "This is an <b>end-of-stay model</b>. Alongside baseline information from the first abstract, "
            "it uses what the stay itself recorded: intensive care, palliative care "
            "coding, conditions that arose after admission, procedures, care across "
            "more than one hospital, and length of stay. The earliest moment it "
            "could be calculated is the day someone is discharged — it is not a "
            "tool for triaging people as they arrive, and its score should not be "
            "read as though it were.",
            title="When this score could exist",
            tone="strong",
        )
        ui.plain(
            "Alberta is used as a geography test: people with any Alberta care are "
            "kept out of training completely, only their Alberta stays form the test "
            "set, and any stays they had in other provinces are set aside rather "
            "than used on either side. Tested that way the score is "
            f"<b>{fmt.number(get_key_number('auc_alberta'), 3)}</b> "
            f"({fmt.interval(get_key_text('auc_alberta_ci'))}) on "
            f"{fmt.count(get_key_number('alberta_test_n'))} stays."
        )

    with limits:
        ui.callout(
            "A score of this size separates groups usefully and individuals poorly. "
            "It can say that this tenth of stays returns three or four times as "
            "often as that tenth. It cannot say whether the person in front of you "
            "will come back, and it has never been tested in practice on anybody.",
            title="Groups yes, individuals no",
            tone="strong",
        )
        ui.plain(
            "The Alberta test is a check on whether the model travels between "
            "provinces, not proper external validation: those records come from the "
            "same national collection, with the same forms and the same coding "
            "rules, so the project calls it a geographic holdout rather than "
            "anything stronger."
        )

    with detail:
        ui.stat_grid(
            [
                {
                    "value": fmt.number(auc, 3),
                    "label": "ROC-AUC",
                    "note": fmt.interval(get_key_text("auc_logistic_ci")),
                    "small": True,
                },
                {
                    "value": fmt.number(get_key_number("pr_auc_logistic"), 3),
                    "label": "PR-AUC",
                    "note": "Against a test-set outcome rate of "
                            f"{fmt.number(get_key_number('outcome_prevalence'), 3)}.",
                    "small": True,
                },
                {
                    "value": fmt.number(get_key_number("brier_logistic"), 4),
                    "label": "Brier score",
                    "note": "Mean squared error of the predicted probabilities.",
                    "small": True,
                },
            ]
        )
        ui.stat_grid(
            [
                {
                    "value": fmt.number(get_key_number("calibration_slope"), 3),
                    "label": "Calibration slope",
                    "note": "1.0 is ideal.",
                    "small": True,
                    "tone": "quiet",
                },
                {
                    "value": fmt.number(get_key_number("calibration_intercept"), 3),
                    "label": "Calibration intercept",
                    "note": "0.0 is ideal.",
                    "small": True,
                    "tone": "quiet",
                },
                {
                    "value": fmt.number(get_key_number("auc_forest"), 3),
                    "label": "Random forest comparator",
                    "note": "A more flexible model finds little extra signal.",
                    "small": True,
                    "tone": "quiet",
                },
            ]
        )

        ui.figure(
            charts.threshold_operating_points(thresholds),
            "What each cut-off catches and what it costs",
            "Held-out test stays",
            note_text="Source: q1_thresholds.csv.",
        )
        display = thresholds.copy()
        display["flagged_pct"] = display["flagged_pct"].map(fmt.pct)
        for column in ("sensitivity", "specificity", "ppv", "npv"):
            display[column] = display[column].map(fmt.proportion)
        ui.table(
            display.rename(
                columns={
                    "threshold": "Threshold",
                    "flagged_pct": "Flagged",
                    "sensitivity": "Sensitivity",
                    "specificity": "Specificity",
                    "ppv": "PPV",
                    "npv": "NPV",
                }
            ),
            note_text=(
                "At a threshold of 0.15 the model flags "
                f"{fmt.pct(get_key_number('threshold15_flagged_pct'))} of stays and "
                f"finds {fmt.proportion(get_key_number('threshold15_sensitivity'))} "
                "of the readmissions, at a positive predictive value of "
                f"{fmt.proportion(get_key_number('threshold15_ppv'))}; around "
                f"{fmt.pct(get_key_number('threshold15_false_alarm_pct'))} of the "
                "episodes it flags would not have been readmitted. Source: "
                "q1_thresholds.csv."
            ),
        )

        ui.figure(
            charts.calibration_by_decile(calibration),
            "Predicted and observed readmission across the ten risk bands",
            "Held-out test stays",
            note_text=(
                "Observed readmission runs from "
                f"{fmt.pct(get_key_number('calibration_lowest_actual_pct'))} in the "
                "lowest band to "
                f"{fmt.pct(get_key_number('calibration_highest_actual_pct'))} in the "
                "highest, roughly a "
                f"{fmt.number(get_key_number('risk_group_spread_multiple'), 0)}-fold "
                "spread. Source: q1_calibration.csv."
            ),
        )

        holdout_row = holdout.iloc[0]
        with st.expander("Alberta geographic holdout"):
            ui.table(
                holdout.rename(
                    columns={
                        "trained_on": "Trained on",
                        "tested_on": "Tested on",
                        "n_test": "Test stays",
                        "auc": "AUC",
                        "auc_ci_low": "CI low",
                        "auc_ci_high": "CI high",
                        "calibration_slope": "Cal. slope",
                        "calibration_intercept": "Cal. intercept",
                    }
                ),
                note_text=(
                    "Calibration slope there is "
                    f"{fmt.number(holdout_row['calibration_slope'], 3)}. Source: "
                    "q1_geographic_holdout.csv."
                ),
            )

        with st.expander("Model comparison and variable importance"):
            comparison = performance.rename(
                columns={
                    "model": "Model",
                    "auc": "AUC",
                    "auc_ci_low": "AUC CI low",
                    "auc_ci_high": "AUC CI high",
                    "pr_auc": "PR-AUC",
                    "brier": "Brier",
                    "calibration_slope": "Cal. slope",
                    "calibration_intercept": "Cal. intercept",
                    "outcome_prevalence": "Prevalence",
                }
            )
            ui.table(
                comparison[
                    ["Model", "AUC", "AUC CI low", "AUC CI high", "PR-AUC", "Brier",
                     "Cal. slope", "Cal. intercept", "Prevalence"]
                ],
                note_text="Source: q1_model_performance.csv.",
            )
            importance = data_loader.load("q1_feature_importance")
            ui.figure(
                charts.feature_importance(importance),
                "Random forest feature importance",
                "From the random forest comparator, not from the logistic "
                "regression reported above.",
                note_text=(
                    "Random forest feature importance ranks how much a variable "
                    "contributed to splits in the fitted forest. It is not an "
                    "adjusted association, it carries no direction, it is biased "
                    "towards high-cardinality and correlated predictors, and it "
                    "should not be read as an effect. Source: "
                    "q1_feature_importance.csv."
                ),
            )

        ui.callout(
            "Every figure on this page is read from the current analysis outputs at "
            "load time. The train/test split was regenerated after a "
            "reproducibility correction, and no performance figure is written into "
            "the application, so re-running the pipeline updates this page rather "
            "than leaving a stale number behind.",
            title="Reproducibility",
        )


ui.run_page(render)
