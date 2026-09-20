

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import age_band, add_age_band, AGE_REFERENCE, \
    suppress_small_cells, write_suppression_report, MIN_CELL

import os

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf



df = pd.read_parquet("output/episode_level.parquet")
df = df[df["has_cancer"]].reset_index(drop=True)

for col in ["urgent_admission", "entered_via_ed", "died_in_hospital",
            "has_heart_failure", "has_diabetes",
            "intensive_care", "cancer_has_spread", "cancer_is_main_reason",
            "palliative_care", "post_admission_condition", "is_alberta"]:
    df[col] = df[col].astype(int)



df["age_band"] = df["age_group"].apply(age_band)

print(f"Cancer episodes of care: {len(df):,}")
print(f"Urgent/emergent admission category: {df['urgent_admission'].sum():,} "
      f"({100*df['urgent_admission'].mean():.1f}%)")
print(f"Entered through an emergency department: {df['entered_via_ed'].sum():,} "
      f"({100*df['entered_via_ed'].mean():.1f}%)")
print("\nThese two are related but different measures. Cross-tabulation:")
print(pd.crosstab(df["urgent_admission"], df["entered_via_ed"],
                  rownames=["urgent category"], colnames=["entered via ED"]).to_string())

# ---------------------------------------------------------------
# A. By cancer site
# ---------------------------------------------------------------
main = df[df["cancer_is_main_reason"] == 1]
by_site = main.groupby("cancer_site").agg(
    episodes=("urgent_admission", "size"),
    urgent=("urgent_admission", "sum"),
    via_ed=("entered_via_ed", "sum"),
    died=("died_in_hospital", "sum"),
).reset_index()
by_site["pct_urgent"] = (100 * by_site["urgent"] / by_site["episodes"]).round(1)
by_site["pct_via_ed"] = (100 * by_site["via_ed"] / by_site["episodes"]).round(1)
by_site["pct_died"] = (100 * by_site["died"] / by_site["episodes"]).round(1)
by_site = by_site[by_site["episodes"] >= 200].sort_values("pct_urgent", ascending=False)
# Disclosure control, applied here as it is in Table 1 and the Question 1 rate
# tables. Only those three passed through the helper, so the safeguard the
# README describes was applied to some released tables and not others; nothing
# breached the threshold today, but that was the >=200 filter's doing rather
# than the safeguard's, and an ad-hoc filter is not a disclosure control.
os.makedirs("output/tables/internal", exist_ok=True)
by_site.to_csv("output/tables/internal/q2_urgent_by_site_full.csv", index=False)
suppress_small_cells(
    by_site, ["episodes", "urgent", "via_ed", "died"], "cancer_site",
    "q2_urgent_by_site", denominator_col="episodes",
    also_blank=("pct_urgent", "pct_via_ed", "pct_died"),
).to_csv("output/tables/q2_urgent_by_site.csv", index=False)

print("\n" + "=" * 72)
print("A. URGENT ADMISSION AND MORTALITY BY CANCER SITE")
print("Episodes where cancer was the most responsible diagnosis")
print("=" * 72)
print(by_site[["cancer_site", "episodes", "pct_urgent", "pct_via_ed", "pct_died"]]
      .to_string(index=False))

corr = by_site["pct_urgent"].corr(by_site["pct_died"])
print(f"\nAcross cancer sites, urgent admission rate and in-hospital mortality")
print(f"move together (correlation {corr:.2f}). This is an ecological pattern")
print("across groups, not evidence about any individual patient, and it says")
print("nothing about when the cancer was diagnosed.")

# ---------------------------------------------------------------
# B. By province
# ---------------------------------------------------------------
by_prov = main.groupby("province").agg(
    episodes=("urgent_admission", "size"),
    urgent=("urgent_admission", "sum"),
).reset_index()
by_prov["pct_urgent"] = (100 * by_prov["urgent"] / by_prov["episodes"]).round(1)
by_prov = by_prov[by_prov["episodes"] >= 300].sort_values("pct_urgent", ascending=False)
by_prov.to_csv("output/tables/internal/q2_urgent_by_province_full.csv", index=False)
suppress_small_cells(
    by_prov, ["episodes", "urgent"], "province", "q2_urgent_by_province",
    denominator_col="episodes", also_blank=("pct_urgent",),
).to_csv("output/tables/q2_urgent_by_province.csv", index=False)
print("\n" + "=" * 72)
print("B. BY PROVINCE (the RAF does not include Quebec)")
print("=" * 72)
print(by_prov.to_string(index=False))

# ---------------------------------------------------------------
# C. Association with in-hospital mortality
# ---------------------------------------------------------------
unadj = df.groupby("urgent_admission")["died_in_hospital"].agg(["size", "mean"])
print("\n" + "=" * 72)
print("C. IN-HOSPITAL MORTALITY")
print("=" * 72)
print(f"  Planned admission:  {100*unadj.loc[0,'mean']:.1f}% "
      f"({unadj.loc[0,'size']:,} episodes)")
print(f"  Urgent/emergent:    {100*unadj.loc[1,'mean']:.1f}% "
      f"({unadj.loc[1,'size']:,} episodes)")

BASELINE = ("died_in_hospital ~ urgent_admission + baseline_cancer_has_spread "
            "+ C(baseline_cancer_site, Treatment('Breast')) + C(age_band) + C(sex) "
            "+ comorbidity_count")
FULL = BASELINE + " + palliative_care + post_admission_condition"


def fit(formula, label):
    m = smf.logit(formula, data=df).fit(
        cov_type="cluster", cov_kwds={"groups": df["patient_id"]},
        disp=False, maxiter=200)
    out = pd.DataFrame({
        "model": label,
        "factor": m.params.index,
        "odds_ratio": np.exp(m.params).round(2),
        "ci_low": np.exp(m.conf_int()[0]).round(2),
        "ci_high": np.exp(m.conf_int()[1]).round(2),
        "p_value": m.pvalues.round(4),
    }).reset_index(drop=True)
    return out


m1 = fit(BASELINE, "1. Baseline variables only (primary)")
m2 = fit(FULL, "2. Adding in-hospital course (descriptive)")
adj = pd.concat([m1, m2], ignore_index=True)
adj.to_csv("output/tables/q2_death_regression.csv", index=False)

print("\nMODEL 1 (PRIMARY) -- baseline variables only")
print("Adjusts only for what was known at the start of the episode.")
print(m1[m1["factor"].isin(["urgent_admission", "baseline_cancer_has_spread",
                            "comorbidity_count"])].to_string(index=False))

print("\nMODEL 2 (DESCRIPTIVE) -- adds palliative care and post-admission conditions")
print("These occur during the episode, after the exposure.")
print(m2[m2["factor"].isin(["urgent_admission", "baseline_cancer_has_spread",
                            "palliative_care", "post_admission_condition"])]
      .to_string(index=False))

or1 = m1.loc[m1["factor"] == "urgent_admission", "odds_ratio"].values[0]
or2 = m2.loc[m2["factor"] == "urgent_admission", "odds_ratio"].values[0]
print(f"""
The urgent-admission ODDS RATIO is {or1:.2f} in the baseline model and {or2:.2f}
once palliative care and post-admission conditions are added. The primary
estimate is the baseline one. The attenuation shows that these post-exposure
variables carry much of the statistical association; it does not identify a
causal pathway, and Model 2 is not better adjusted.""")

# ---------------------------------------------------------------
# D. Odds ratios are not risk. Report adjusted probabilities.
#
# In-hospital death is common in the urgent group, so a large odds ratio must
# not be read as "that many times the chance". The average marginal effect is
# computed instead: predict each patient's probability twice from the baseline
# model, once as urgent and once as planned, and average the results.
# ---------------------------------------------------------------
m1_fit = smf.logit(BASELINE, data=df).fit(
    cov_type="cluster", cov_kwds={"groups": df["patient_id"]}, disp=False, maxiter=200)

def adjusted_risks(data, fitted=None):
    """Average marginal effect: predict everyone as urgent, then as planned."""
    if fitted is None:
        fitted = smf.logit(BASELINE, data=data).fit(disp=False, maxiter=200)
    pu = fitted.predict(data.assign(urgent_admission=1)).mean()
    pp = fitted.predict(data.assign(urgent_admission=0)).mean()
    return pu, pp


p_urgent, p_planned = adjusted_risks(df, m1_fit)

# Confidence intervals by patient-cluster bootstrap: resample patients with
# replacement, refit, and recompute the standardised risks each time.
rng = np.random.default_rng(11)
groups = df.groupby("patient_id").indices
pids = np.array(list(groups.keys()))
boot = []
for _ in range(200):
    picks = rng.integers(0, len(pids), len(pids))
    idx = np.concatenate([groups[pids[i]] for i in picks])
    sample = df.iloc[idx]
    try:
        pu, pp = adjusted_risks(sample)
        boot.append((pu, pp, pu - pp, pu / pp))
    except Exception:
        continue

boot = np.array(boot)
lo, hi = np.percentile(boot, [2.5, 97.5], axis=0)

marginal = pd.DataFrame([{
    "adjusted_risk_if_all_urgent_pct": round(100 * p_urgent, 1),
    "urgent_ci": f"{100*lo[0]:.1f} to {100*hi[0]:.1f}",
    "adjusted_risk_if_all_planned_pct": round(100 * p_planned, 1),
    "planned_ci": f"{100*lo[1]:.1f} to {100*hi[1]:.1f}",
    "risk_difference_pct_points": round(100 * (p_urgent - p_planned), 1),
    "risk_difference_ci": f"{100*lo[2]:.1f} to {100*hi[2]:.1f}",
    "risk_ratio": round(p_urgent / p_planned, 2),
    "risk_ratio_ci": f"{lo[3]:.2f} to {hi[3]:.2f}",
    "odds_ratio": round(or1, 2),
}])
marginal.to_csv("output/tables/q2_adjusted_risk.csv", index=False)

print("\n" + "=" * 72)
print("D. ADJUSTED PROBABILITIES (average marginal effect, baseline model)")
print("95% intervals from a patient-cluster bootstrap, 200 draws")
print("=" * 72)
print(marginal.T.to_string(header=False))
print(f"""
Read this rather than the odds ratio. Standardising the cohort to all-urgent
versus all-planned gives {100*p_urgent:.1f}% against {100*p_planned:.1f}% in-hospital
mortality: a risk difference of {100*(p_urgent-p_planned):.1f} percentage points and a risk
ratio of {p_urgent/p_planned:.2f}. The odds ratio of {or1:.2f} is much larger than the risk
ratio because in-hospital death is not rare in the urgent group.""")

or_u = or1
print(f"""
POPULATION: all invasive-cancer episodes of care (n={len(df):,}).

Urgent/emergent admission is ASSOCIATED WITH {or_u:.2f} times the ODDS of dying
during the episode (not the same as the chance: see the adjusted risk table
above), among the characteristics recorded in this dataset.

This is not a causal estimate. Urgent admission is a marker of how the patient
presented, not a treatment. Cancer stage, performance status, treatment intent
and disease severity are not in the RAF and are very likely to explain part of
the association.""")

write_suppression_report()
