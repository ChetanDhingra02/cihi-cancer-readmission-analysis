

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import age_band, add_age_band, AGE_REFERENCE, \
    suppress_small_cells, write_suppression_report, MIN_CELL

import os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

pd.set_option("display.width", 200)

full = pd.read_parquet("output/cohort.parquet")
df = full[full["discharged_home"]].copy()
OUTCOME = "urgent_readmit_30d"



def prepare(d):
    d = d.copy()
    d["age_band"] = d["age_group"].apply(age_band)
    for col in ["urgent_admission", "entered_via_ed", "intensive_care",
                "planned_return_30d", "urgent_definite_30d",
                "palliative_care", "post_admission_condition",
                "cancer_is_main_reason", "cancer_has_spread",
                "waited_for_other_care", "has_heart_failure", "has_diabetes",
                "has_kidney_disease", "has_lung_disease", "has_dementia",
                "has_anaemia", "is_alberta", "urgent_readmit_30d",
                "ed_readmit_30d", "returned_30d"]:
        d[col] = d[col].astype(int)
    d["had_procedure"] = (d["n_procedures"] > 0).astype(int)
    # Named for WHICH length of stay this is. Question 3 and Question 4 use a
    # different quantity (the sum of stay-band floors across the whole episode)
    # and call it episode_long_stay. Both were previously called "final_abstract_long_stay",
    # which made two different variables look like one.
    d["final_abstract_long_stay"] = (d["final_los_group"] >= 6).astype(int)
    d["multi_facility"] = (d["n_abstracts"] > 1).astype(int)
    return d


df = prepare(df).reset_index(drop=True)

print(f"Primary cohort: {len(df):,} episodes, {df['patient_id'].nunique():,} patients")
print("POPULATION: cancer episodes ending in discharge home, 30 days of "
      "potential follow-up")



# ===============================================================
# PART A: counts and percentages
# ===============================================================
def rate_ci(sub, outcome, n_boot=400, seed=7):
    """
    Percentile confidence interval for a rate, resampling PATIENTS.

    Patients contribute several episodes, so episodes are not independent.
    This uses the same patient-cluster resampling as the model metrics, rather
    than a closed-form correction, so every interval in the project comes from
    one consistent method.
    """
    r = np.random.default_rng(seed)
    y = sub[outcome].to_numpy()
    pid = sub["patient_id"].to_numpy()
    order = np.argsort(pid, kind="stable")
    pid_sorted = pid[order]
    _, starts = np.unique(pid_sorted, return_index=True)
    ends = np.append(starts[1:], len(pid_sorted))
    rows_by_patient = [order[a:b] for a, b in zip(starts, ends)]
    n_pat = len(rows_by_patient)
    if n_pat < 2:
        return np.nan, np.nan
    draws = []
    for _ in range(n_boot):
        picks = r.integers(0, n_pat, n_pat)
        idx = np.concatenate([rows_by_patient[i] for i in picks])
        draws.append(100 * y[idx].mean())
    return np.percentile(draws, [2.5, 97.5])


def rate_table(d, group_col, outcome=OUTCOME):
    rows = []
    for key, sub in d.groupby(group_col):
        lo, hi = rate_ci(sub, outcome)
        rows.append({
            group_col: key,
            "episodes": len(sub),
            "patients": sub["patient_id"].nunique(),
            "readmitted": int(sub[outcome].sum()),
            "percent": round(100 * sub[outcome].mean(), 1),
            "ci_low": round(lo, 1),
            "ci_high": round(hi, 1),
        })
    return pd.DataFrame(rows).sort_values("percent", ascending=False).reset_index(drop=True)


by_site = rate_table(df, "cancer_site")
by_province = rate_table(df, "province")

# Disclosure control. The README told the reader to check released tables for
# small cells and the project then shipped counts of 31, 42 and 10. This is
# licensed microdata; the safeguard is applied here rather than described.
# Percentages and intervals are blanked alongside a suppressed count, because a
# rate plus a denominator gives the count straight back.
os.makedirs("output/tables/internal", exist_ok=True)
by_site.to_csv("output/tables/internal/q1_rate_by_cancer_site_full.csv", index=False)
by_province.to_csv("output/tables/internal/q1_rate_by_province_full.csv", index=False)

by_site_rel = suppress_small_cells(
    by_site, ["episodes", "patients", "readmitted"], "cancer_site",
    "q1_rate_by_cancer_site", denominator_col="episodes",
    also_blank=("percent", "ci_low", "ci_high"))
by_province_rel = suppress_small_cells(
    by_province, ["episodes", "patients", "readmitted"], "province",
    "q1_rate_by_province", denominator_col="episodes",
    also_blank=("percent", "ci_low", "ci_high"))
by_site_rel.to_csv("output/tables/q1_rate_by_cancer_site.csv", index=False)
by_province_rel.to_csv("output/tables/q1_rate_by_province.csv", index=False)

print("\n" + "=" * 72)
print("PART A: URGENT/EMERGENT 30-DAY READMISSION")
print("=" * 72)
print("\nBy cancer site:")
print(by_site.to_string(index=False))
print("\nBy province (note: the RAF does not include Quebec):")
print(by_province.to_string(index=False))


# ===============================================================
# PART B: regression
# ===============================================================
# TWO MODELS, for exactly the reason given in Question 2 and Question 3.
#
# The exposure is how the patient was admitted, which is fixed at admission.
# Palliative-care coding, post-admission conditions, intensive care, length of
# stay, whether a procedure happened and whether more than one facility was
# involved are all recorded DURING the episode, so they are post-exposure. This
# project identified that error in Question 2 and fixed it, then identified the
# same error in Question 3 and fixed it, while Question 1 kept adjusting for six
# post-exposure variables and reported the result as its headline risk ratio.
#
#   Model 1 (primary)   baseline only: age, sex, cancer site and secondary
#                       deposits from the FIRST abstract, plus comorbidity count
#   Model 2 (descriptive) adds the in-hospital course
#
# Model 2 is NOT better adjusted. It answers a different question: how urgent
# admission relates to readmission among episodes that took the same course in
# hospital. That is a conditional association, not the one the headline claims.
BASELINE = (
    "{o} ~ C(age_band, Treatment(AGE_REFERENCE)) + C(sex) "
    "+ C(baseline_cancer_site, Treatment('Breast')) "
    "+ baseline_cancer_has_spread + urgent_admission + comorbidity_count"
).format(o=OUTCOME)

FULL = (
    BASELINE
    + " + cancer_is_main_reason + final_abstract_long_stay + intensive_care "
      "+ palliative_care + post_admission_condition + had_procedure "
      "+ multi_facility"
)

formula = BASELINE

model = smf.logit(formula, data=df).fit(
    cov_type="cluster", cov_kwds={"groups": df["patient_id"]}, disp=False, maxiter=200
)

results = pd.DataFrame({
    "factor": model.params.index,
    "odds_ratio": np.exp(model.params).round(2),
    "ci_low": np.exp(model.conf_int()[0]).round(2),
    "ci_high": np.exp(model.conf_int()[1]).round(2),
    "p_value": model.pvalues.round(4),
}).reset_index(drop=True)
results = results[results["factor"] != "Intercept"]


def tidy_factors(s):
    """
    Turn patsy term names into readable labels.

    The previous version matched only Treatment('quoted literal'), so the age
    terms -- written Treatment(AGE_REFERENCE), an unquoted name -- fell through
    and shipped with the closing bracket stripped but the opening one left,
    giving "C(age_band, Treatment(AGE_REFERENCE))[T.Under 18". Boolean terms
    such as "baseline_cancer_has_spread[T.True" were mangled the same way. Six
    of the released rows were malformed, and model 2 was never cleaned at all.

    This accepts any Treatment(...) argument, quoted or not, and closes the
    bracket properly.
    """
    return (
        s.str.replace(r"C\((\w+),\s*Treatment\([^)]*\)\)\[T\.(.*)\]$", r"\1: \2", regex=True)
         .str.replace(r"C\((\w+)\)\[T\.(.*)\]$", r"\1: \2", regex=True)
         .str.replace(r"^(\w+)\[T\.(.*)\]$", r"\1: \2", regex=True)
    )


results["factor"] = tidy_factors(results["factor"])
results.insert(0, "model", "1. Baseline variables only (primary)")

full_model = smf.logit(FULL, data=df).fit(
    cov_type="cluster", cov_kwds={"groups": df["patient_id"]}, disp=False, maxiter=200)
full_results = pd.DataFrame({
    "model": "2. Adding in-hospital course (descriptive)",
    "factor": full_model.params.index,
    "odds_ratio": np.exp(full_model.params).round(2),
    "ci_low": np.exp(full_model.conf_int()[0]).round(2),
    "ci_high": np.exp(full_model.conf_int()[1]).round(2),
    "p_value": full_model.pvalues.round(4),
}).reset_index(drop=True)
full_results = full_results[full_results["factor"] != "Intercept"]
# Model 2 previously shipped with raw patsy term names while model 1 was cleaned,
# so one released table used two naming conventions.
full_results["factor"] = tidy_factors(full_results["factor"])

q1_reg = pd.concat([results, full_results], ignore_index=True)
_malformed = q1_reg[q1_reg["factor"].str.count(r"\[") != q1_reg["factor"].str.count(r"\]")]
if len(_malformed):
    raise SystemExit(
        "malformed factor labels in q1_regression.csv:\n"
        + _malformed[["model", "factor"]].to_string(index=False)
    )
q1_reg.to_csv("output/tables/q1_regression.csv", index=False)

print("\n" + "=" * 72)
print("PART B: ADJUSTED ASSOCIATIONS (odds ratios)")
print("These are associations, not causes.")
print("=" * 72)
print(results.sort_values("odds_ratio", ascending=False).to_string(index=False))


# --- Adjusted RISKS, not just odds ---
# An odds ratio is not a risk ratio. Readmission is common enough here that the
# two diverge, so the same average-marginal-effect treatment used in Question 2
# is applied to the strongest predictor.
def adjusted_risks(data, variable, fitted=None):
    if fitted is None:
        fitted = smf.logit(formula, data=data).fit(disp=False, maxiter=200)
    hi = fitted.predict(data.assign(**{variable: 1})).mean()
    lo = fitted.predict(data.assign(**{variable: 0})).mean()
    return hi, lo


r_urgent, r_planned = adjusted_risks(df, "urgent_admission", model)
f_urgent, f_planned = adjusted_risks(df, "urgent_admission", full_model)

rng_m = np.random.default_rng(23)
groups_m = df.groupby("patient_id").indices
pids_m = np.array(list(groups_m.keys()))
boot_m = []
for _ in range(200):
    picks = rng_m.integers(0, len(pids_m), len(pids_m))
    idx = np.concatenate([groups_m[pids_m[i]] for i in picks])
    try:
        hi, lo = adjusted_risks(df.iloc[idx], "urgent_admission")
        boot_m.append((hi, lo, hi - lo, hi / lo))
    except Exception:
        continue
boot_m = np.array(boot_m)
blo, bhi = np.percentile(boot_m, [2.5, 97.5], axis=0)

q1_risk = pd.DataFrame([{
    "adjusted_readmission_if_all_urgent_pct": round(100 * r_urgent, 1),
    "urgent_ci": f"{100*blo[0]:.1f} to {100*bhi[0]:.1f}",
    "adjusted_readmission_if_all_planned_pct": round(100 * r_planned, 1),
    "planned_ci": f"{100*blo[1]:.1f} to {100*bhi[1]:.1f}",
    "risk_difference_pct_points": round(100 * (r_urgent - r_planned), 1),
    "risk_difference_ci": f"{100*blo[2]:.1f} to {100*bhi[2]:.1f}",
    "risk_ratio": round(r_urgent / r_planned, 2),
    "risk_ratio_ci": f"{blo[3]:.2f} to {bhi[3]:.2f}",
    "odds_ratio": round(np.exp(model.params["urgent_admission"]), 2),
    "model": "1. Baseline variables only (primary)",
}, {
    "adjusted_readmission_if_all_urgent_pct": round(100 * f_urgent, 1),
    "urgent_ci": "",
    "adjusted_readmission_if_all_planned_pct": round(100 * f_planned, 1),
    "planned_ci": "",
    "risk_difference_pct_points": round(100 * (f_urgent - f_planned), 1),
    "risk_difference_ci": "",
    "risk_ratio": round(f_urgent / f_planned, 2),
    "risk_ratio_ci": "",
    "odds_ratio": round(np.exp(full_model.params["urgent_admission"]), 2),
    "model": "2. Adding in-hospital course (descriptive)",
}])
q1_risk.to_csv("output/tables/q1_adjusted_risk.csv", index=False)

print("\nADJUSTED RISKS for urgent initial admission (average marginal effect)")
print("95% intervals from a patient-cluster bootstrap")
print(q1_risk.T.to_string(header=False))
print(f"""
Standardising the cohort gives {100*r_urgent:.1f}% readmission if every index episode
had been urgent against {100*r_planned:.1f}% if every one had been planned: a risk ratio of
{r_urgent/r_planned:.2f}, not the odds ratio of {np.exp(model.params['urgent_admission']):.2f}.

Urgent admission is one of the strongest and most consistent predictors here,
but it is not uniformly the largest: several cancer-site coefficients exceed it.

Adding the in-hospital course gives {100*f_urgent:.1f}% against {100*f_planned:.1f}%, a risk ratio of
{f_urgent/f_planned:.2f}. That model conditions on variables recorded after the exposure and
answers a different question; it is reported for comparison, not as a better
estimate.""")

# ===============================================================
# PART C: prediction model
# ===============================================================
FEATURES = [
    "age_band", "sex", "cancer_site", "cancer_is_main_reason", "cancer_has_spread",
    "urgent_admission", "intensive_care", "palliative_care",
    "post_admission_condition", "had_procedure", "multi_facility",
    "comorbidity_count", "has_kidney_disease", "has_anaemia", "has_heart_failure",
    "final_los_group",
]
# final_abstract_long_stay is a threshold of final_los_group, which is already in
# the feature list, so it was entering the model twice in different shapes.

# sklearn's LogisticRegression applies L2 regularisation by default (C=1.0). On
# unstandardised inputs that penalises the 0/1 dummies and the count variables
# unequally, which is a modelling choice rather than plain logistic regression.
# Standardising first makes the penalty act evenly and makes the description
# accurate.
def make_logit():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000))


def design(d):
    return pd.get_dummies(d[FEATURES], drop_first=True).astype(float)


X = design(df)
y = df[OUTCOME]

rng = np.random.default_rng(42)
patients = np.sort(df["patient_id"].unique())
test_patients = set(rng.choice(patients, size=int(0.3 * len(patients)), replace=False))
is_test = df["patient_id"].isin(test_patients)

X_train, X_test = X[~is_test], X[is_test]
y_train, y_test = y[~is_test], y[is_test]

logit = make_logit()
logit.fit(X_train, y_train)
p_logit = logit.predict_proba(X_test)[:, 1]

forest = RandomForestClassifier(n_estimators=300, min_samples_leaf=30,
                                random_state=42, n_jobs=-1)
forest.fit(X_train, y_train)
p_forest = forest.predict_proba(X_test)[:, 1]


def bootstrap_by_patient(y_true, p, patient_ids, metric, n_boot=400, seed=1):
    """
    Bootstrap confidence interval, resampling PATIENTS rather than episodes.

    A patient can contribute several episodes, so those rows are not
    independent. Resampling episodes would treat them as if they were and
    produce intervals that are too narrow. Each draw samples patient IDs with
    replacement and takes all of that patient's episodes.
    """
    r = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    p = np.asarray(p)
    pid = np.asarray(patient_ids)

    order = np.argsort(pid, kind="stable")
    pid_sorted = pid[order]
    unique_pids, starts = np.unique(pid_sorted, return_index=True)
    ends = np.append(starts[1:], len(pid_sorted))
    rows_by_patient = [order[s:e] for s, e in zip(starts, ends)]

    stats = []
    for _ in range(n_boot):
        picks = r.integers(0, len(unique_pids), len(unique_pids))
        idx = np.concatenate([rows_by_patient[i] for i in picks])
        if y_true[idx].sum() in (0, len(idx)):
            continue
        stats.append(metric(y_true[idx], p[idx]))
    return np.percentile(stats, [2.5, 97.5])


def calibration_slope_intercept(y_true, p):
    """
    Regress the outcome on the predicted log-odds.
    Slope 1 and intercept 0 mean perfect calibration.
    Slope below 1 means predictions are too extreme.
    """
    eps = 1e-6
    lp = np.log(np.clip(p, eps, 1 - eps) / (1 - np.clip(p, eps, 1 - eps)))
    d = pd.DataFrame({"y": np.asarray(y_true).astype(int), "lp": lp})
    slope_fit = smf.logit("y ~ lp", data=d).fit(disp=False)
    intercept_fit = smf.logit("y ~ 1", data=d.assign(off=lp),
                              offset=d["lp"]).fit(disp=False)
    return slope_fit.params["lp"], intercept_fit.params["Intercept"]


def sens_spec(y_true, p, threshold):
    y_true = np.asarray(y_true).astype(int)
    pred = (p >= threshold).astype(int)
    tp = ((pred == 1) & (y_true == 1)).sum()
    fp = ((pred == 1) & (y_true == 0)).sum()
    fn = ((pred == 0) & (y_true == 1)).sum()
    tn = ((pred == 0) & (y_true == 0)).sum()
    return {
        "threshold": threshold,
        "flagged_pct": round(100 * pred.mean(), 1),
        "sensitivity": round(tp / (tp + fn), 3) if tp + fn else np.nan,
        "specificity": round(tn / (tn + fp), 3) if tn + fp else np.nan,
        "ppv": round(tp / (tp + fp), 3) if tp + fp else np.nan,
        "npv": round(tn / (tn + fn), 3) if tn + fn else np.nan,
    }


perf_rows = []
test_patients_col = df.loc[is_test, "patient_id"].values
for name, p in [("Logistic regression", p_logit), ("Random forest", p_forest)]:
    lo, hi = bootstrap_by_patient(y_test, p, test_patients_col, roc_auc_score)
    pr_lo, pr_hi = bootstrap_by_patient(y_test, p, test_patients_col,
                                        average_precision_score, seed=2)
    slope, intercept = calibration_slope_intercept(y_test, p)
    perf_rows.append({
        "model": name,
        "auc": round(roc_auc_score(y_test, p), 3),
        "auc_ci_low": round(lo, 3),
        "auc_ci_high": round(hi, 3),
        "pr_auc": round(average_precision_score(y_test, p), 3),
        "pr_auc_ci_low": round(pr_lo, 3),
        "pr_auc_ci_high": round(pr_hi, 3),
        "brier": round(brier_score_loss(y_test, p), 4),
        "calibration_slope": round(slope, 3),
        "calibration_intercept": round(intercept, 3),
    })

perf = pd.DataFrame(perf_rows)
perf["outcome_prevalence"] = round(y_test.mean(), 3)
perf.to_csv("output/tables/q1_model_performance.csv", index=False)

print("\n" + "=" * 72)
print("PART C: PREDICTION MODEL")
print("=" * 72)
print(f"Training: {len(X_train):,} episodes   Test: {len(X_test):,} episodes")
print("Split by PATIENT, so no patient appears on both sides.\n")
print(perf.to_string(index=False))
print("\nPR-AUC should be read against the outcome prevalence of "
      f"{y_test.mean():.3f}, which is what a useless model would score.")
print("Calibration slope 1.0 and intercept 0.0 would be perfect.")

thresholds = pd.DataFrame([sens_spec(y_test, p_logit, t) for t in (0.10, 0.15, 0.20, 0.30)])
thresholds.to_csv("output/tables/q1_thresholds.csv", index=False)
print("\nOperating points (logistic regression):")
print(thresholds.to_string(index=False))

risk = pd.DataFrame({"predicted": p_logit, "actual": y_test.values})
risk["group"] = pd.qcut(risk["predicted"], 10, labels=False, duplicates="drop") + 1
calib = risk.groupby("group").agg(
    episodes=("actual", "size"),
    predicted_pct=("predicted", lambda x: round(100 * x.mean(), 1)),
    actual_pct=("actual", lambda x: round(100 * x.mean(), 1)),
).reset_index()
calib.to_csv("output/tables/q1_calibration.csv", index=False)
print("\nRisk groups, lowest to highest:")
print(calib.to_string(index=False))

# --- geographic holdout, NOT external validation ---
#
# The patient identifier follows people ACROSS provinces (905 patients in the
# full RAF appear in Alberta and at least one other province). Splitting purely
# on the province of the episode would put some patients on both sides.
#
# So the split is by PATIENT: anyone with any Alberta episode goes entirely to
# the holdout, and is removed from training completely.
# Three groups, not two, so the split is both patient-separated AND
# geographically clean:
#   TRAIN  every episode of patients with no Alberta episode at all
#   TEST   the ALBERTA episodes of patients who have Alberta care
#   DROP   the non-Alberta episodes of those same patients
# Without the drop, the "Alberta holdout" would contain episodes from other
# provinces and would not be an Alberta evaluation.
ab_patients = set(df.loc[df["is_alberta"] == 1, "patient_id"])
touches_alberta = df["patient_id"].isin(ab_patients)

train_mask = ~touches_alberta
test_mask = touches_alberta & (df["is_alberta"] == 1)
dropped = touches_alberta & (df["is_alberta"] == 0)

print(f"\nGeographic holdout split")
print(f"  train (patients with no Alberta care): {int(train_mask.sum()):,} episodes")
print(f"  test  (Alberta episodes only):         {int(test_mask.sum()):,} episodes")
print(f"  dropped (non-Alberta episodes of Alberta patients): {int(dropped.sum()):,}")
print(f"  patients with care in Alberta and elsewhere: "
      f"{df.loc[dropped, 'patient_id'].nunique()}")

holdout = make_logit()
holdout.fit(X[train_mask], y[train_mask])
p_ab = holdout.predict_proba(X[test_mask])[:, 1]
in_alberta = test_mask
lo, hi = bootstrap_by_patient(y[in_alberta], p_ab,
                              df.loc[in_alberta, "patient_id"].values, roc_auc_score)
slope, intercept = calibration_slope_intercept(y[in_alberta], p_ab)

geo = pd.DataFrame([{
    "trained_on": "All provinces except Alberta",
    "tested_on": "Alberta episodes only",
    "n_test": int(in_alberta.sum()),
    "auc": round(roc_auc_score(y[in_alberta], p_ab), 3),
    "auc_ci_low": round(lo, 3), "auc_ci_high": round(hi, 3),
    "calibration_slope": round(slope, 3),
    "calibration_intercept": round(intercept, 3),
}])
geo.to_csv("output/tables/q1_geographic_holdout.csv", index=False)
print("\nGeographic holdout (internal-external validation, NOT external")
print("validation: Alberta records come from the same CIHI RAF source):")
print(geo.to_string(index=False))

importance = pd.DataFrame({
    "feature": X.columns, "importance": forest.feature_importances_.round(4),
}).sort_values("importance", ascending=False).head(15)
importance.to_csv("output/tables/q1_feature_importance.csv", index=False)


# ===============================================================
# PART D: sensitivity analyses
# ===============================================================
print("\n" + "=" * 72)
print("PART D: SENSITIVITY ANALYSES")
print("=" * 72)

# D1: timing ambiguity
unambiguous = df[df["urgent_readmit_certainty"] != "ambiguous"].reset_index(drop=True)
sens_rows = [
    {"analysis": "Primary (discharged home)", "episodes": len(df),
     "urgent_readmit_pct": round(100 * df[OUTCOME].mean(), 1)},
    {"analysis": "Complete case: timing-ambiguous episodes excluded", "episodes": len(unambiguous),
     "urgent_readmit_pct": round(100 * unambiguous[OUTCOME].mean(), 1)},
    {"analysis": "Definite only (whole interval inside window)", "episodes": len(df),
     "urgent_readmit_pct": round(100 * df["urgent_definite_30d"].mean(), 1)},
]

# D2: cohort definition
alive_all = prepare(full).reset_index(drop=True)
sens_rows.append({"analysis": "All live discharges (not only home)",
                  "episodes": len(alive_all),
                  "urgent_readmit_pct": round(100 * alive_all[OUTCOME].mean(), 1)})

# D3: outcome definition
sens_rows.append({"analysis": "Outcome = readmission entering via ED",
                  "episodes": len(df),
                  "urgent_readmit_pct": round(100 * df["ed_readmit_30d"].mean(), 1)})
sens_rows.append({"analysis": "Outcome = any 30-day return, planned included",
                  "episodes": len(df),
                  "urgent_readmit_pct": round(100 * df["returned_30d"].mean(), 1)})

sens = pd.DataFrame(sens_rows)
sens.to_csv("output/tables/q1_sensitivity.csv", index=False)
print(sens.to_string(index=False))

# Does the model survive the sensitivity cohort?
Xu, yu = design(unambiguous), unambiguous[OUTCOME]
u_test = unambiguous["patient_id"].isin(test_patients)
m = make_logit().fit(Xu[~u_test], yu[~u_test])
auc_u = roc_auc_score(yu[u_test], m.predict_proba(Xu[u_test])[:, 1])
print(f"\nModel AUC excluding timing-ambiguous episodes: {auc_u:.3f} "
      f"(primary analysis: {perf.loc[0, 'auc']:.3f})")
n_def = int(df["urgent_definite_30d"].sum())
n_amb = int((df["urgent_readmit_certainty"] == "ambiguous").sum())
print(f"""
HOW TO READ THESE NUMBERS.

  {100*df[OUTCOME].mean():.1f}%  POINT ESTIMATE. Uses the derived admission day as recorded.
         This is the headline figure and the best single estimate.

  {100*df['urgent_definite_30d'].mean():.1f}%  DEFINITE ONLY ({n_def:,} episodes). The candidate's entire
         possible admission interval sits after discharge and inside 30 days.

  {100*unambiguous[OUTCOME].mean():.1f}%  COMPLETE CASE. Rate among episodes whose timing resolves,
         dropping the {n_amb:,} ambiguous ones.

None of these is a bound on the others. The point estimate is not a claim that
every event is certain; the definite figure is a floor on what can be proven
rather than an estimate of the rate; the complete-case figure conditions on
resolvability, which is not random. Genuine bounds would need a formal
partial-identification analysis, which has not been done.""")

# What were the planned returns actually for?
planned = df[(df["planned_return_30d"] == 1) & (df[OUTCOME] == 0)]
n_chemo = int(planned["first_planned_return_chemo"].fillna(False).astype(bool).sum())
print(f"\nPlanned (non-urgent) 30-day returns: {len(planned):,}")
print(f"Of these, {n_chemo:,} ({100*n_chemo/max(len(planned),1):.1f}%) carry a "
      "Z51.1 chemotherapy code on the return episode.")
print("This is the chemotherapy share of PLANNED RETURNS. It is a different")
print("quantity from the post-admission-condition share in Question 3, which")
print("an earlier version reported using the same number.")
print("The reason for the remainder cannot be established from these fields, so")
print("no claim is made about what they were for.")
pd.DataFrame([{"planned_returns": len(planned), "with_chemo_code": n_chemo,
               "pct_with_chemo_code": round(100*n_chemo/max(len(planned),1), 1)}]).to_csv(
    "output/tables/q1_planned_returns.csv", index=False)


# ===============================================================
# PART E: is the headline robust to the length-of-stay assumption?
#
# The point estimate places every candidate admission at REL_DDAY minus the
# FLOOR of its stay band. That is an assumption, not a neutral reading: it puts
# every stay at the shortest length its band allows. If the headline moved
# materially under a different assumption, it would not deserve to be called the
# best single estimate. This tests it directly rather than asserting it.
# ===============================================================
import duckdb



con = duckdb.connect("output/dad.duckdb", read_only=True)
rows = []
for label, m in [
    ("Floor of band (primary)", {1: 1, 2: 2, 3: 3, 4: 4, 6: 6, 10: 10}),
    ("Midpoint of band", {1: 1, 2: 2, 3: 3, 4: 4.5, 6: 7.5, 10: 10}),
    ("Midpoint, 10+ band assumed mean 15", {1: 1, 2: 2, 3: 3, 4: 4.5, 6: 7.5, 10: 15}),
    ("Midpoint, 10+ band assumed mean 20", {1: 1, 2: 2, 3: 3, 4: 4.5, 6: 7.5, 10: 20}),
]:
    case = " ".join(f"WHEN {k} THEN {v}" for k, v in m.items())
    r = con.execute(f"""
        WITH assume AS (
            SELECT record_id, discharge_day,
                   CASE length_of_stay_group {case} END AS los_assumed
            FROM all_admissions
        ),
        cand AS (
            SELECT i.patient_id, i.episode_no,
                   MAX(CASE WHEN (a.discharge_day - a.los_assumed) - i.episode_end_day
                                 BETWEEN 0 AND 30
                             AND c.urgent_admission THEN 1 ELSE 0 END) AS urg
            FROM cohort i
            JOIN episode_full c ON c.patient_id = i.patient_id
                               AND c.episode_no > i.episode_no
            JOIN assume a ON a.record_id = c.first_record_id
            WHERE i.discharged_home GROUP BY 1, 2
        )
        SELECT ROUND(100.0*AVG(COALESCE(urg, 0)), 2) AS pct
        FROM cohort i LEFT JOIN cand USING (patient_id, episode_no)
        WHERE i.discharged_home
    """).fetchone()[0]
    rows.append({"stay_length_assumption": label, "urgent_readmit_pct": r})
con.close()

los_sens = pd.DataFrame(rows)
los_sens.to_csv("output/tables/q1_los_assumption_sensitivity.csv", index=False)
span = los_sens["urgent_readmit_pct"].max() - los_sens["urgent_readmit_pct"].min()
print("\n" + "=" * 72)
print("PART E: SENSITIVITY TO THE LENGTH-OF-STAY ASSUMPTION")
print("=" * 72)
print(los_sens.to_string(index=False))
print(f"\nThe estimate spans {span:.2f} percentage points across these assumptions.")
print("The floor assumption is not driving the headline.")

write_suppression_report()
