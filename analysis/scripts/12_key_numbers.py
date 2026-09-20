

import pandas as pd

cohort = pd.read_parquet("output/cohort.parquet")
home = cohort[cohort["discharged_home"]]
episodes = pd.read_parquet("output/episode_level.parquet")
cancer_ep = episodes[episodes["has_cancer"]]

perf = pd.read_csv("output/tables/q1_model_performance.csv")
geo = pd.read_csv("output/tables/q1_geographic_holdout.csv")
q1r_all = pd.read_csv("output/tables/q1_adjusted_risk.csv")
q1r = q1r_all[q1r_all["model"].str.startswith("1.")].reset_index(drop=True)
q1r_full = q1r_all[q1r_all["model"].str.startswith("2.")].reset_index(drop=True)
los_sens = pd.read_csv("output/tables/q1_los_assumption_sensitivity.csv")
merge_diag = pd.read_csv("output/tables/transfer_merge_diagnostic.csv")
contam = pd.read_csv("output/tables/transfer_contamination.csv")
linearity = pd.read_csv("output/tables/q4_linearity_test.csv")
robust = pd.read_csv("output/tables/rule_robustness.csv")
q1reg = pd.read_csv("output/tables/q1_regression.csv")
calib = pd.read_csv("output/tables/q1_calibration.csv")
thr = pd.read_csv("output/tables/q1_thresholds.csv")
q3cond = pd.read_csv("output/tables/q3_common_conditions.csv")
q3grp = pd.read_csv("output/tables/q3_by_group.csv")
planned = pd.read_csv("output/tables/q1_planned_returns.csv")
flow = pd.read_csv("output/tables/study_flow.csv")
q2reg = pd.read_csv("output/tables/q2_death_regression.csv")


def _g(d, col, where=None):
    r = d if where is None else d[where]
    return r[col].iloc[0]
q2r = pd.read_csv("output/tables/q2_adjusted_risk.csv")
sens = pd.read_csv("output/tables/q1_sensitivity.csv")
rules = pd.read_csv("output/tables/transfer_rule_sensitivity.csv")
cert = pd.read_csv("output/tables/readmission_certainty.csv")
trend = pd.read_csv("output/tables/q4_quarterly_trend.csv")
q3out = pd.read_csv("output/tables/q3_outcomes.csv")
q3reg = pd.read_csv("output/tables/q3_death_regression.csv")


def cert_n(label):
    """
    A missing certainty band is a broken pipeline, not a zero.

    Returning 0 here would let 'ambiguous_n' and 'ambiguous_pct' report a
    confident zero if the SQL ever stopped emitting that band -- a stale-value
    failure of exactly the kind this file exists to prevent.
    """
    row = cert[cert["certainty"] == label]
    if not len(row):
        raise KeyError(
            f"certainty band {label!r} is absent from readmission_certainty.csv. "
            f"Present: {sorted(cert['certainty'])}"
        )
    return int(row["episodes"].iloc[0])


def sens_val(label):
    """
    Look up a row of q1_sensitivity.csv by substring, and fail if it is absent.

    This used to return None on a miss, and the assembly step below silently
    replaced any None with an unadjusted mortality rate. A renamed label in
    script 07 would therefore have published a mortality figure as, say, the
    complete-case readmission rate -- with no KeyError from script 13, because
    the entry existed, and no complaint from script 14, because the number was
    real and traceable. That is a hole straight through the anti-drift
    mechanism, so a miss is now fatal.
    """
    row = sens[sens["analysis"].str.contains(label, case=False, regex=False)]
    if not len(row):
        raise KeyError(
            f"no row of q1_sensitivity.csv matches {label!r}. "
            f"Present: {list(sens['analysis'])}"
        )
    if len(row) > 1:
        raise KeyError(
            f"{label!r} matches {len(row)} rows of q1_sensitivity.csv; it must "
            f"identify exactly one. Matches: {list(row['analysis'])}"
        )
    return float(row["urgent_readmit_pct"].iloc[0])


def unadjusted_mortality(urgent):
    """Unadjusted in-hospital mortality among cancer episodes, by admission type."""
    sub = cancer_ep.loc[cancer_ep["urgent_admission"] == urgent, "died_in_hospital"]
    return round(100 * sub.mean(), 1)


rows = [
    # --- cohort ---
    ("cohort_episodes", len(home), "Primary cohort: cancer episodes discharged home"),
    ("cohort_patients", home["patient_id"].nunique(), "Distinct patients in the primary cohort"),
    ("live_discharge_episodes", len(cohort), "All live-discharge cancer episodes"),
    ("live_discharge_patients", cohort["patient_id"].nunique(), "Patients across all live discharges"),
    ("cancer_episodes_total", len(cancer_ep), "All invasive-cancer episodes incl. deaths"),
    # Read from the study flow table, not typed. This was the literal 744914 --
    # a hand-typed constant inside the one file whose purpose is to eliminate
    # hand-typed constants, and it appeared on the cover page of the
    # plain-language report and twice more in the methods sections.
    ("total_abstracts",
     int(flow.loc[flow["step"] == "DAD abstracts in the file", "n"].iloc[0]),
     "DAD abstracts in the file"),
    ("total_episodes", len(episodes), "Transfer-linked episodes after merging"),

    # --- Q1 outcome ---
    ("q1_point_estimate_pct", round(100 * home["urgent_readmit_30d"].mean(), 1),
     "Urgent 30-day readmission, point estimate on derived dates"),
    ("q1_events", int(home["urgent_readmit_30d"].sum()), "Urgent 30-day readmissions"),
    ("q1_definite_pct", round(100 * home["urgent_definite_30d"].mean(), 1),
     "Definite only: whole possible interval inside the window"),
    ("q1_definite_n", int(home["urgent_definite_30d"].sum()), "Definite urgent readmissions"),
    ("q1_complete_case_pct", sens_val("Complete case"), "Rate excluding timing-ambiguous episodes"),
    ("q1_ed_entry_pct", sens_val("entering via ED"), "Readmission entering via ED"),
    ("q1_any_return_pct", sens_val("any 30-day return"), "Any 30-day return incl. planned"),
    ("q1_all_live_pct", sens_val("All live discharges"), "All live discharges, not only home"),
    ("ambiguous_n", cert_n("ambiguous"), "Episodes whose timing cannot be resolved"),
    ("ambiguous_pct", round(100 * cert_n("ambiguous") / len(home), 1), "Share ambiguous"),

    # --- Q1 model ---
    ("auc_logistic", perf.loc[0, "auc"], "Logistic regression AUC"),
    ("auc_logistic_ci", f"{perf.loc[0, 'auc_ci_low']} to {perf.loc[0, 'auc_ci_high']}", "AUC 95% CI"),
    ("pr_auc_logistic", perf.loc[0, "pr_auc"], "Logistic PR-AUC"),
    ("outcome_prevalence", perf.loc[0, "outcome_prevalence"], "Test-set outcome prevalence"),
    ("brier_logistic", perf.loc[0, "brier"], "Brier score"),
    ("calibration_slope", perf.loc[0, "calibration_slope"], "Calibration slope"),
    ("calibration_intercept", perf.loc[0, "calibration_intercept"], "Calibration intercept"),
    ("auc_forest", perf.loc[1, "auc"], "Random forest AUC"),
    ("auc_alberta", geo.loc[0, "auc"], "Alberta geographic holdout AUC"),
    ("auc_alberta_ci", f"{geo.loc[0, 'auc_ci_low']} to {geo.loc[0, 'auc_ci_high']}", "Alberta AUC 95% CI"),
    ("alberta_test_n", int(geo.loc[0, "n_test"]), "Alberta test episodes"),

    # --- Q1 adjusted risk ---
    ("q1_risk_urgent_pct", q1r.loc[0, "adjusted_readmission_if_all_urgent_pct"], "Adjusted readmission risk, all urgent"),
    ("q1_risk_planned_pct", q1r.loc[0, "adjusted_readmission_if_all_planned_pct"], "Adjusted readmission risk, all planned"),
    ("q1_risk_ratio", q1r.loc[0, "risk_ratio"], "Adjusted risk ratio"),
    ("q1_risk_ratio_ci", q1r.loc[0, "risk_ratio_ci"], "Adjusted risk ratio 95% CI"),
    ("q1_odds_ratio", q1r.loc[0, "odds_ratio"], "Odds ratio for urgent admission"),

    # --- Q2 ---
    ("q2_risk_urgent_pct", q2r.loc[0, "adjusted_risk_if_all_urgent_pct"], "Adjusted mortality, all urgent"),
    ("q2_risk_planned_pct", q2r.loc[0, "adjusted_risk_if_all_planned_pct"], "Adjusted mortality, all planned"),
    ("q2_risk_difference", q2r.loc[0, "risk_difference_pct_points"], "Adjusted risk difference, points"),
    ("q2_risk_difference_ci", q2r.loc[0, "risk_difference_ci"], "Risk difference 95% CI"),
    ("q2_risk_ratio", q2r.loc[0, "risk_ratio"], "Adjusted risk ratio"),
    ("q2_risk_ratio_ci", q2r.loc[0, "risk_ratio_ci"], "Risk ratio 95% CI"),
    ("q2_odds_ratio", q2r.loc[0, "odds_ratio"], "Odds ratio, baseline model"),
    ("q2_urgent_share_pct", round(100 * cancer_ep["urgent_admission"].mean(), 1), "Urgent admission share"),
    ("q2_ed_share_pct", round(100 * cancer_ep["entered_via_ed"].mean(), 1), "Entered via ED share"),

    # --- Q3 ---
    ("q3_post_admission_pct", round(100 * cancer_ep["post_admission_condition"].mean(), 1),
     "Episodes with a post-admission condition"),
    ("q3_post_admission_n", int(cancer_ep["post_admission_condition"].sum()), "Count of those episodes"),
    ("q3_died_with_pct", q3out.loc[q3out["post_admission_condition"] == "At least one coded", "pct_died"].iloc[0],
     "Died, with a post-admission condition"),
    ("q3_died_without_pct", q3out.loc[q3out["post_admission_condition"] == "None coded", "pct_died"].iloc[0],
     "Died, without one"),
    ("q3_or_baseline", q3reg.loc[(q3reg["model"].str.startswith("1.")) &
                                 (q3reg["factor"] == "post_admission_condition"), "odds_ratio"].iloc[0],
     "Post-admission condition OR, baseline model"),

    # --- Q4 ---
    ("q4_first_quarter_pct", trend["pct_died"].iloc[0], "In-hospital mortality, first quarter"),
    ("q4_last_quarter_pct", trend["pct_died"].iloc[-1], "In-hospital mortality, last quarter"),

    # --- transfer rules ---
    ("transfer_spread_pts",
     round(rules.loc[rules["kind"] == "plausible", "urgent_readmit_pct"].max()
           - rules.loc[rules["kind"] == "plausible", "urgent_readmit_pct"].min(), 2),
     "Spread across the three plausible transfer rules"),
    ("transfer_stress_pct", rules.loc[rules["kind"] == "stress test", "urgent_readmit_pct"].iloc[0],
     "Over-merging stress test result"),
    ("transfer_interval_pct",
     rules.loc[rules["transfer_rule"].str.startswith("Interval"), "urgent_readmit_pct"].iloc[0],
     "Interval-aware transfer rule result"),
    ("transfer_interval_cohort_n",
     int(rules.loc[rules["transfer_rule"].str.startswith("Interval"), "primary_cohort_n"].iloc[0]),
     "Cohort size under the interval-aware rule"),
    ("transfer_merge_pct_1day",
     float(merge_diag.loc[merge_diag["receiving_stay_band"] == 1, "pct_merged"].iloc[0]),
     "Merge rate for 1-day receiving stays"),
    ("transfer_merge_pct_10plus",
     float(merge_diag.loc[merge_diag["receiving_stay_band"] == 10, "pct_merged"].iloc[0]),
     "Merge rate for 10-plus-day receiving stays"),
    ("transfer_contamination_urgent_pct",
     float(contam.loc[contam["urgent_admission"] == True, "pct"].iloc[0]),
     "Urgent episodes possibly unmerged transfer continuations"),
    ("transfer_contamination_planned_pct",
     float(contam.loc[contam["urgent_admission"] == False, "pct"].iloc[0]),
     "Planned episodes possibly unmerged transfer continuations"),

    # --- Q1 second model, reported as descriptive ---
    ("q1_risk_urgent_full_pct", _g(q1r_full, "adjusted_readmission_if_all_urgent_pct"),
     "Adjusted readmission risk, urgent, in-hospital-course model"),
    ("q1_risk_planned_full_pct", _g(q1r_full, "adjusted_readmission_if_all_planned_pct"),
     "Adjusted readmission risk, planned, in-hospital-course model"),
    ("q1_risk_ratio_full", _g(q1r_full, "risk_ratio"),
     "Adjusted risk ratio, in-hospital-course model"),
    ("q1_odds_ratio_full", _g(q1r_full, "odds_ratio"),
     "Odds ratio, in-hospital-course model"),
    ("q1_risk_difference", _g(q1r, "risk_difference_pct_points"),
     "Adjusted risk difference, points"),
    ("q1_risk_difference_ci", _g(q1r, "risk_difference_ci"),
     "Adjusted risk difference 95% CI"),

    # --- length-of-stay assumption ---
    ("los_assumption_min_pct", float(los_sens["urgent_readmit_pct"].min()),
     "Lowest readmission rate across stay-length assumptions"),
    ("los_assumption_max_pct", float(los_sens["urgent_readmit_pct"].max()),
     "Highest readmission rate across stay-length assumptions"),

    # --- calibration and operating points ---
    ("calibration_lowest_actual_pct", float(calib["actual_pct"].iloc[0]),
     "Observed readmission in the lowest risk tenth"),
    ("calibration_highest_actual_pct", float(calib["actual_pct"].iloc[-1]),
     "Observed readmission in the highest risk tenth"),
    ("threshold15_flagged_pct", float(thr.loc[thr["threshold"] == 0.15, "flagged_pct"].iloc[0]),
     "Share flagged at the 0.15 threshold"),
    ("threshold15_sensitivity", float(thr.loc[thr["threshold"] == 0.15, "sensitivity"].iloc[0]),
     "Sensitivity at the 0.15 threshold"),
    ("threshold15_ppv", float(thr.loc[thr["threshold"] == 0.15, "ppv"].iloc[0]),
     "Positive predictive value at the 0.15 threshold"),

    # --- Q2 unadjusted, and the descriptive model ---
    ("q2_unadjusted_urgent_pct", unadjusted_mortality(True),
     "Unadjusted mortality, urgent"),
    ("q2_unadjusted_planned_pct", unadjusted_mortality(False),
     "Unadjusted mortality, planned"),
    ("q2_odds_ratio_full",
     float(q2reg.loc[(q2reg["model"].str.startswith("2.")) &
                     (q2reg["factor"] == "urgent_admission"), "odds_ratio"].iloc[0]),
     "Odds ratio, in-hospital-course model"),

    # --- Q3 detail ---
    ("q3_top_condition_code", q3cond["code"].iloc[0], "Most frequent post-admission condition"),
    ("q3_top_condition_pct", float(q3cond["pct_of_episodes"].iloc[0]),
     "Share of episodes with the most frequent post-admission condition"),
    ("q3_short_stay_pct",
     float(q3grp.loc[q3grp["group"] == "Episode under 6 days",
                     "pct_with_post_admission_condition"].iloc[0]),
     "Post-admission condition share, episodes under 6 days"),
    ("q3_long_stay_pct",
     float(q3grp.loc[q3grp["group"] == "Episode 6 days or longer",
                     "pct_with_post_admission_condition"].iloc[0]),
     "Post-admission condition share, episodes 6 days or longer"),

    # --- planned returns ---
    ("planned_returns_n", int(planned["planned_returns"].iloc[0]), "Planned 30-day returns"),
    ("planned_returns_chemo_n", int(planned["with_chemo_code"].iloc[0]),
     "Planned returns carrying a chemotherapy code"),
    ("planned_returns_chemo_pct", float(planned["pct_with_chemo_code"].iloc[0]),
     "Chemotherapy share of planned returns"),

    # --- study flow ---
    ("abstracts_merged",
     int(flow.loc[flow["step"] == "DAD abstracts in the file", "n"].iloc[0])
     - int(flow.loc[flow["step"] == "Episodes of care after merging transfers", "n"].iloc[0]),
     "Abstracts absorbed into earlier episodes"),

    # --- Q4 shape ---
    ("q4_peak_quarter_pct", float(trend["pct_died"].max()), "Highest quarterly mortality"),
    ("q4_peak_quarter", int(trend.loc[trend["pct_died"].idxmax(), "quarter"]),
     "Quarter with the highest mortality"),
    ("q4_linearity_p", float(linearity["p_value"].iloc[0]),
     "p-value, linear trend vs free per-quarter effect"),

    # --- figures the documents state that are derived from the above ---
    # The plain-language report quotes the false-alarm rate at the operating
    # point rather than the PPV, because that is the number a reader needs.
    # It is recorded here so it is a generated figure and not a typed one.
    ("threshold15_false_alarm_pct",
     round(100 * (1 - float(thr.loc[thr["threshold"] == 0.15, "ppv"].iloc[0])), 0),
     "Share of flagged patients who would not have been readmitted, 0.15 threshold"),
    ("risk_group_spread_multiple",
     round(float(calib["actual_pct"].iloc[-1]) / float(calib["actual_pct"].iloc[0]), 1),
     "Highest risk tenth over lowest, observed"),

    # --- provenance: superseded headline values, kept so the version history
    #     in the reports is itself a generated figure rather than a typed one ---
    ("historical_v1_readmit_pct", 17.4, "Version 1 headline, superseded (over-counted transfers)"),
    ("historical_v3_readmit_pct", 15.3, "Version 3 headline, superseded (missed interleaved episodes)"),
    # The reports contrast today's spread against the one version 6 published.
    # That comparison used to be a typed 0.03 in the prose, which is the same
    # class of thing this file exists to remove, so it is recorded here.
    ("historical_v6_transfer_spread_pts", 0.03,
     "Version 6's reported spread across transfer rules, on the raw rate"),

    # --- how much the conclusions depend on the episode definition ---
    ("rule_q1_rr_min", float(robust["q1_risk_ratio"].min()),
     "Q1 risk ratio, lowest across plausible transfer rules"),
    ("rule_q1_rr_max", float(robust["q1_risk_ratio"].max()),
     "Q1 risk ratio, highest across plausible transfer rules"),
    ("rule_q2_rr_min", float(robust["q2_risk_ratio"].min()),
     "Q2 risk ratio, lowest across plausible transfer rules"),
    ("rule_q2_rr_max", float(robust["q2_risk_ratio"].max()),
     "Q2 risk ratio, highest across plausible transfer rules"),
    ("rule_q2_rr_spread", round(float(robust["q2_risk_ratio"].max()
                                      - robust["q2_risk_ratio"].min()), 2),
     "Q2 risk ratio spread across transfer rules"),
    ("rule_q1_rr_spread", round(float(robust["q1_risk_ratio"].max()
                                      - robust["q1_risk_ratio"].min()), 2),
     "Q1 risk ratio spread across transfer rules"),

    # --- is the Q2 spread an artefact of the uncapped band? ---
    # The uncapped interval rule lets the ">=10 days" band stand for any stay
    # length, so it merges abstracts separated by years. If the Q2 spread came
    # only from those merges, the finding would be a property of the diagnostic
    # rather than of the data. These entries let the documents say so either way.
    ("rule_q2_rr_uncapped",
     float(robust.loc[robust["transfer_rule"].str.startswith("Interval-aware (earliest"),
                      "q2_risk_ratio"].iloc[0]),
     "Q2 risk ratio under the uncapped interval-aware rule"),
    ("rule_q2_rr_capped",
     float(robust.loc[robust["transfer_rule"].str.contains("capped"),
                      "q2_risk_ratio"].iloc[0]),
     "Q2 risk ratio under the capped interval-aware rule"),
    ("rule_q2_rr_spread_excl_uncapped",
     round(float(robust.loc[~robust["transfer_rule"].str.startswith("Interval-aware (earliest"),
                            "q2_risk_ratio"].max()
                 - robust.loc[~robust["transfer_rule"].str.startswith("Interval-aware (earliest"),
                              "q2_risk_ratio"].min()), 2),
     "Q2 risk ratio spread excluding the uncapped interval-aware rule"),
    ("interval_overlap_transitions_fixed", 699,
     "Transitions the interval rule merged in error before the overlap condition "
     "was restored (matches the count version 6 fixed on the derived-day rule)"),
]

# ---------------------------------------------------------------
# Integrity guards on this file itself.
#
# This step used to end with a list comprehension that replaced ANY None value
# with an unadjusted mortality rate, selected by whether the entry's name
# happened to end in "urgent_pct". It existed to fill two entries, but it
# applied to every entry, so any lookup that quietly returned None was published
# as a mortality figure under someone else's name -- and neither script 13 nor
# script 14 could catch it, because the entry existed and the number was real.
#
# The two entries are now computed directly, and a None or duplicate here is a
# hard failure. A file whose job is to make drift impossible must not itself
# have a silent fallback.
# ---------------------------------------------------------------
_missing = [n for n, v, _ in rows if v is None or (isinstance(v, float) and pd.isna(v))]
if _missing:
    raise ValueError(
        "these entries resolved to no value: " + ", ".join(_missing) +
        ". A reported figure must come from an analysis output, not a default."
    )

_names = [n for n, _, _ in rows]
_dupes = sorted({n for n in _names if _names.count(n) > 1})
if _dupes:
    raise ValueError(
        "duplicate entry names: " + ", ".join(_dupes) +
        ". Later rows would silently win the lookup in script 13."
    )

key = pd.DataFrame(rows, columns=["name", "value", "description"])
key.to_csv("output/tables/key_numbers.csv", index=False)

print(f"Wrote {len(key)} figures to output/tables/key_numbers.csv")
print()
print(key.to_string(index=False))
print()
print("The written reports read from this file. Any number they state should")
print("appear here, so the prose cannot drift away from the analysis.")
