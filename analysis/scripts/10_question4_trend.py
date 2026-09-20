

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import age_band, add_age_band, AGE_REFERENCE, \
    suppress_small_cells, write_suppression_report, MIN_CELL

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf



df = pd.read_parquet("output/episode_level.parquet")
df = df[df["has_cancer"]].reset_index(drop=True)

for col in ["died_in_hospital", "urgent_admission", "intensive_care",
            "cancer_has_spread", "palliative_care", "post_admission_condition",
            "covid"]:
    df[col] = df[col].astype(int)

# Named for WHICH length of stay this is. Question 1 uses the FINAL abstract's
# stay band and calls it final_abstract_long_stay. This one sums the stay-band
# floors across every abstract in the episode. Both were previously called
# "episode_long_stay", so two different quantities shared one name across the project.
df["episode_long_stay"] = (df["episode_los_floor"] >= 6).astype(int)
df["age_80_plus"] = (df["age_group"] == "80+ yrs").astype(int)
# Days are numbered from 1, so subtract 1 before dividing. Without this, day 91
# falls into quarter 2 instead of quarter 1.
df["quarter"] = ((df["episode_end_day"] - 1) // 91).astype(int) + 1
df["quarter_admit"] = ((df["episode_start_day"] - 1) // 91).astype(int) + 1



df["age_band"] = df["age_group"].apply(age_band)
n_before = len(df)
df = df[df["quarter"] <= 12].reset_index(drop=True)
# The window is 1095 days, which is 12 quarters of 91 days plus 3 days. Those
# three days form a stub 13th quarter and are dropped. Said out loud because a
# silently dropped remainder is exactly the kind of thing an audit should find.
print(f"Episodes in the 3-day stub after quarter 12, excluded: {n_before - len(df):,}")

# ---------------------------------------------------------------
# A. Quarter by quarter (discharge anchored)
# ---------------------------------------------------------------
trend = df.groupby("quarter").agg(
    episodes=("died_in_hospital", "size"),
    deaths=("died_in_hospital", "sum"),
    pct_died=("died_in_hospital", lambda x: round(100 * x.mean(), 1)),
    pct_urgent=("urgent_admission", lambda x: round(100 * x.mean(), 1)),
    pct_spread=("cancer_has_spread", lambda x: round(100 * x.mean(), 1)),
    pct_aged_80_plus=("age_80_plus", lambda x: round(100 * x.mean(), 1)),
    pct_intensive_care=("intensive_care", lambda x: round(100 * x.mean(), 1)),
    pct_palliative=("palliative_care", lambda x: round(100 * x.mean(), 1)),
    pct_episode_long_stay=("episode_long_stay", lambda x: round(100 * x.mean(), 1)),
).reset_index()
os.makedirs("output/tables/internal", exist_ok=True)
trend.to_csv("output/tables/internal/q4_quarterly_trend_full.csv", index=False)
suppress_small_cells(
    trend, ["episodes", "deaths"], "quarter", "q4_quarterly_trend",
    denominator_col="episodes",
    also_blank=("pct_died", "pct_urgent", "pct_spread", "pct_aged_80_plus",
                "pct_intensive_care", "pct_palliative", "pct_episode_long_stay"),
).to_csv("output/tables/q4_quarterly_trend.csv", index=False)

print("=" * 100)
print("A. QUARTER BY QUARTER, ANCHORED ON DISCHARGE")
print("=" * 100)
print(trend.to_string(index=False))

first, last = trend["pct_died"].iloc[0], trend["pct_died"].iloc[-1]
print(f"\nIn-hospital mortality: {first}% in quarter 1, {last}% in quarter 12 "
      f"({100*(last-first)/first:.0f}% relative change).")

# ---------------------------------------------------------------
# B. Does the anchor change the answer?
# ---------------------------------------------------------------
# The admission anchor can fall outside quarters 1-12 even when the discharge
# anchor does not: REL_ADAY is REL_DDAY minus the stay-band floor, so an episode
# discharged early in the window can have a derived admission day of 0 or less
# and land in "quarter 0". Reindexing to 1-12 dropped those rows without saying
# so. The count is small but it is exactly the kind of silent remainder the
# audit flagged in the stub 13th quarter, so it is reported the same way.
_out_of_range = int(((df["quarter_admit"] < 1) | (df["quarter_admit"] > 12)).sum())
print(f"\nEpisodes whose DERIVED admission day falls outside quarters 1-12 and "
      f"are therefore absent from the admission-anchored column: {_out_of_range:,}")
alt = df[(df["quarter_admit"] >= 1) & (df["quarter_admit"] <= 12)] \
        .groupby("quarter_admit")["died_in_hospital"].mean()
compare = pd.DataFrame({
    "quarter": trend["quarter"],
    "discharge_anchored_pct": trend["pct_died"],
    "admission_anchored_pct": (100 * alt.reindex(trend["quarter"]).values).round(1),
})
compare.to_csv("output/tables/q4_anchor_comparison.csv", index=False)
print("\n" + "=" * 100)
print("B. DISCHARGE ANCHOR VERSUS ADMISSION ANCHOR")
print("=" * 100)
print(compare.to_string(index=False))

# ---------------------------------------------------------------
# C. Is the trend explained by measured characteristics?
# ---------------------------------------------------------------
# Both models use patient-clustered standard errors. Patients contribute
# several episodes in either specification, so applying clustering to only one
# of them would make the two intervals non-comparable.
simple = smf.logit("died_in_hospital ~ quarter", data=df).fit(
    cov_type="cluster", cov_kwds={"groups": df["patient_id"]}, disp=False)
adjusted = smf.logit(
    "died_in_hospital ~ quarter + C(age_band) + C(sex) "
    "+ baseline_cancer_has_spread "
    "+ C(baseline_cancer_site, Treatment('Breast')) + urgent_admission "
    "+ comorbidity_count",
    data=df,
).fit(cov_type="cluster", cov_kwds={"groups": df["patient_id"]}, disp=False, maxiter=200)

# COVID was computed in the SQL, carried as far as the abstract table, and then
# never aggregated to episode level -- so it could not be used. Question 4 named
# pandemic disruption as its leading hypothesis while an available COVID
# indicator sat unusable one join away. It is aggregated now and tested here.
covid_adj = smf.logit(
    "died_in_hospital ~ quarter + C(age_band) + C(sex) "
    "+ baseline_cancer_has_spread "
    "+ C(baseline_cancer_site, Treatment('Breast')) + urgent_admission "
    "+ comorbidity_count + covid",
    data=df,
).fit(cov_type="cluster", cov_kwds={"groups": df["patient_id"]}, disp=False, maxiter=200)

comparison = pd.DataFrame([
    {"model": "Time only",
     "odds_ratio_per_quarter": round(np.exp(simple.params["quarter"]), 4),
     "ci_low": round(np.exp(simple.conf_int().loc["quarter", 0]), 4),
     "ci_high": round(np.exp(simple.conf_int().loc["quarter", 1]), 4),
     "p_value": round(simple.pvalues["quarter"], 5)},
    {"model": "Time plus measured characteristics",
     "odds_ratio_per_quarter": round(np.exp(adjusted.params["quarter"]), 4),
     "ci_low": round(np.exp(adjusted.conf_int().loc["quarter", 0]), 4),
     "ci_high": round(np.exp(adjusted.conf_int().loc["quarter", 1]), 4),
     "p_value": round(adjusted.pvalues["quarter"], 5)},
    {"model": "Time plus measured characteristics and COVID coding",
     "odds_ratio_per_quarter": round(np.exp(covid_adj.params["quarter"]), 4),
     "ci_low": round(np.exp(covid_adj.conf_int().loc["quarter", 0]), 4),
     "ci_high": round(np.exp(covid_adj.conf_int().loc["quarter", 1]), 4),
     "p_value": round(covid_adj.pvalues["quarter"], 5)},
])
comparison.to_csv("output/tables/q4_trend_models.csv", index=False)

print("\n" + "=" * 100)
print("C. TREND BEFORE AND AFTER ADJUSTMENT")
print("=" * 100)
print(comparison.to_string(index=False))

# Is a straight line the right summary? The series is not monotonic: it peaks
# around quarters 7-8, falls back, then rises again. Reporting first-versus-last
# implies a steady climb, so the linear term is tested against a free per-quarter
# effect rather than assumed.
from scipy import stats as _stats

_lin = smf.logit(
    "died_in_hospital ~ quarter + C(age_band) + C(sex) + baseline_cancer_has_spread "
    "+ C(baseline_cancer_site, Treatment('Breast')) + urgent_admission "
    "+ comorbidity_count", data=df).fit(disp=False, maxiter=200)
_fac = smf.logit(
    "died_in_hospital ~ C(quarter) + C(age_band) + C(sex) + baseline_cancer_has_spread "
    "+ C(baseline_cancer_site, Treatment('Breast')) + urgent_admission "
    "+ comorbidity_count", data=df).fit(disp=False, maxiter=200)
_lr = 2 * (_fac.llf - _lin.llf)
_p = 1 - _stats.chi2.cdf(_lr, 10)
pd.DataFrame([{"test": "linear quarter vs free per-quarter effect",
               "lr_chi2": round(_lr, 2), "df": 10, "p_value": round(_p, 4)}]).to_csv(
    "output/tables/q4_linearity_test.csv", index=False)
print(f"""
IS A STRAIGHT LINE THE RIGHT SUMMARY?

Likelihood-ratio test of the linear quarter term against a free effect for each
quarter: chi2 = {_lr:.1f} on 10 df, p = {_p:.3f}. There is no strong evidence
against linearity, so the linear model is a defensible summary. But the series
is NOT monotonic -- it peaks around quarters 7-8, falls back in quarter 9, then
rises again -- and quoting only the first and last quarters implies a steadier
climb than the data shows.""")

or_adj = comparison["odds_ratio_per_quarter"].iloc[1]
print(f"\nAdjusted odds per quarter: {or_adj:.4f}. Compounded over twelve "
      f"quarters: {or_adj**12:.2f} times the odds.")

print("""
INTERPRETATION -- stated carefully.

The observed increase was NOT explained by the measured patient characteristics
INCLUDED IN THIS MODEL. That is narrower still than "not explained by anything
the dataset records": the model adjusts for selected variables, not for every
field in the RAF.

Unmeasured and unmodelled factors may explain part or all of the trend. The RAF
does not record:
cancer stage, performance status, treatment intent or intensity, disease
severity, hospital or unit characteristics, staffing and capacity pressure,
changes in coding practice over time, referral patterns, or how end-of-life care
was delivered. Any of these could contribute.

Later stage at diagnosis, following pandemic-era disruption to screening and
referral, is ONE PLAUSIBLE HYPOTHESIS. It cannot be tested here because DAD
contains no staging information. Linkage to a cancer registry would be the
logical next step.""")

write_suppression_report()
