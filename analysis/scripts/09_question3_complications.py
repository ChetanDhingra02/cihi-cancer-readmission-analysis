

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import age_band, add_age_band, AGE_REFERENCE, \
    suppress_small_cells, write_suppression_report, MIN_CELL

import duckdb
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf



df = pd.read_parquet("output/episode_level.parquet")
df = df[df["has_cancer"]].reset_index(drop=True)

for col in ["post_admission_condition", "died_in_hospital", "urgent_admission",
            "intensive_care", "cancer_has_spread", "palliative_care"]:
    df[col] = df[col].astype(int)

df["had_procedure"] = (df["n_procedures"] > 0).astype(int)
# Named for WHICH length of stay this is. Question 1 uses the FINAL abstract's
# stay band and calls it final_abstract_long_stay. This one sums the stay-band
# floors across every abstract in the episode. Both were previously called
# "episode_long_stay", so two different quantities shared one name across the project.
df["episode_long_stay"] = (df["episode_los_floor"] >= 6).astype(int)



df["age_band"] = df["age_group"].apply(age_band)

n = len(df)
n_pac = int(df["post_admission_condition"].sum())
print(f"POPULATION: all invasive-cancer episodes of care")
print(f"Cancer episodes of care: {n:,}")
print(f"At least one condition coded as arising after admission: "
      f"{n_pac:,} ({100*n_pac/n:.1f}%)")

# ---------------------------------------------------------------
# A. Which conditions
# ---------------------------------------------------------------
con = duckdb.connect("output/dad.duckdb", read_only=True)
# Count type-2 diagnoses across EVERY abstract belonging to a cancer episode,
# not only abstracts that themselves carry a cancer code. In a transfer episode
# the cancer may be coded at hospital A while the post-admission condition is
# coded at hospital B; requiring cancer on the same abstract would drop the
# hospital B diagnosis and make this table inconsistent with the episode-level
# outcome it is meant to describe.
top = con.execute("""
    WITH cancer_episodes AS (
        SELECT patient_id, episode_no FROM episode_full WHERE has_cancer
    ),
    episode_records AS (
        SELECT e.record_id, e.patient_id, e.episode_no
        FROM episodes e
        JOIN cancer_episodes ce
          ON ce.patient_id = e.patient_id AND ce.episode_no = e.episode_no
    )
    -- Count DISTINCT EPISODES, not diagnosis occurrences. The same code can
    -- appear on several abstracts of one transfer-linked episode, or twice on
    -- one abstract; counting rows and then dividing by episodes would report a
    -- percentage above the true share of episodes affected.
    SELECT SUBSTR(d.dx_code, 1, 3) AS code,
           COUNT(DISTINCT r.patient_id || '_' || r.episode_no) AS n_episodes,
           COUNT(*) AS n_occurrences
    FROM diagnoses d
    JOIN episode_records r ON r.record_id = d.record_id
    WHERE d.dx_type = '2'
    GROUP BY code ORDER BY n_episodes DESC LIMIT 15
""").df()
con.close()

plain = {
    "T81": "Complication of a procedure, not elsewhere classified",
    "E87": "Fluid, electrolyte and acid-base disturbance",
    "K91": "Post-procedural disorder of the digestive system",
    "F05": "Delirium",
    "D70": "Neutropenia (low white cell count)",
    "N39": "Urinary tract infection",
    "I95": "Hypotension (low blood pressure)",
    "N17": "Acute kidney injury",
    "R50": "Fever of unknown origin",
    "U07": "COVID-19",
    "I48": "Atrial fibrillation and flutter",
    "J18": "Pneumonia",
    "R11": "Nausea and vomiting",
    "J96": "Respiratory failure",
    "E83": "Mineral metabolism disorder",
    "A41": "Sepsis",
    "D64": "Anaemia",
    "E86": "Volume depletion",
}
top["condition"] = top["code"].map(plain).fillna("Other")
top["pct_of_episodes"] = (100 * top["n_episodes"] / n).round(2)
os.makedirs("output/tables/internal", exist_ok=True)
top.to_csv("output/tables/internal/q3_common_conditions_full.csv", index=False)
suppress_small_cells(
    top, ["n_episodes", "n_occurrences"], "code", "q3_common_conditions",
    denominator_col="n_episodes", also_blank=("pct_of_episodes",),
).to_csv("output/tables/q3_common_conditions.csv", index=False)

print("\n" + "=" * 72)
print("A. MOST FREQUENT CONDITIONS ARISING AFTER ADMISSION")
print("=" * 72)
print(top[["code", "condition", "n_episodes", "n_occurrences",
           "pct_of_episodes"]].to_string(index=False))
print("\nn_episodes is the number of distinct episodes with that condition.")
print("n_occurrences is the raw diagnosis count and is always higher, because")
print("one episode can carry the same code on more than one abstract.")
print("\nSeveral of these (neutropenia, nausea, fever) are recognised effects of")
print("cancer treatment rather than failures of care.")

# ---------------------------------------------------------------
# B. Who
# ---------------------------------------------------------------
groups = {
    "Planned admission": df["urgent_admission"] == 0,
    "Urgent/emergent admission": df["urgent_admission"] == 1,
    "No procedure recorded": df["had_procedure"] == 0,
    "Procedure recorded": df["had_procedure"] == 1,
    "Episode under 6 days": df["episode_long_stay"] == 0,
    "Episode 6 days or longer": df["episode_long_stay"] == 1,
    "Single facility": df["n_abstracts"] == 1,
    "More than one facility": df["n_abstracts"] > 1,
}
by_group = pd.DataFrame([
    {"group": k, "episodes": int(m.sum()),
     "pct_with_post_admission_condition":
         round(100 * df.loc[m, "post_admission_condition"].mean(), 1)}
    for k, m in groups.items()
])
by_group.to_csv("output/tables/internal/q3_by_group_full.csv", index=False)
suppress_small_cells(
    by_group, ["episodes"], "group", "q3_by_group", denominator_col="episodes",
    also_blank=("pct_with_post_admission_condition",),
).to_csv("output/tables/q3_by_group.csv", index=False)

print("\n" + "=" * 72)
print("B. BY GROUP")
print("=" * 72)
print(by_group.to_string(index=False))
print("\nLength of stay shows the strongest gradient. The direction cannot be")
print("determined here: a condition arising after admission extends a stay, and")
print("a longer stay provides more time for one to arise and be coded. Both")
print("mechanisms are plausible and this data cannot separate them.")

# ---------------------------------------------------------------
# C. Outcomes
# ---------------------------------------------------------------
outcomes = df.groupby("post_admission_condition").agg(
    episodes=("died_in_hospital", "size"),
    pct_died=("died_in_hospital", lambda x: round(100 * x.mean(), 1)),
    pct_intensive_care=("intensive_care", lambda x: round(100 * x.mean(), 1)),
    pct_long_stay=("episode_long_stay", lambda x: round(100 * x.mean(), 1)),
).reset_index()
outcomes["post_admission_condition"] = outcomes["post_admission_condition"].map(
    {0: "None coded", 1: "At least one coded"})
outcomes.to_csv("output/tables/q3_outcomes.csv", index=False)

print("\n" + "=" * 72)
print("C. OUTCOMES")
print("=" * 72)
print(outcomes.to_string(index=False))

# Two models, for the same reason as Question 2. Palliative-care coding is
# recorded DURING the episode, so relative to a condition that also arose after
# admission it is a post-exposure variable, not a baseline confounder. It may
# reflect severity, treatment intent, end-of-life decisions or deterioration.
# Adjusting for it changes what the coefficient means.
BASELINE = ("died_in_hospital ~ post_admission_condition + urgent_admission "
            "+ baseline_cancer_has_spread "
            "+ C(baseline_cancer_site, Treatment('Breast')) + C(age_band) "
            "+ C(sex) + comorbidity_count")
FULL = BASELINE + " + palliative_care"


def fit(formula, label):
    m = smf.logit(formula, data=df).fit(
        cov_type="cluster", cov_kwds={"groups": df["patient_id"]},
        disp=False, maxiter=200)
    return pd.DataFrame({
        "model": label,
        "factor": m.params.index,
        "odds_ratio": np.exp(m.params).round(2),
        "ci_low": np.exp(m.conf_int()[0]).round(2),
        "ci_high": np.exp(m.conf_int()[1]).round(2),
    }).reset_index(drop=True)


m1 = fit(BASELINE, "1. Baseline variables only (primary)")
m2 = fit(FULL, "2. Adding palliative-care coding (descriptive)")
adj = pd.concat([m1, m2], ignore_index=True)
adj.to_csv("output/tables/q3_death_regression.csv", index=False)

print("\nMODEL 1 (PRIMARY) -- baseline variables only:")
print(m1[m1["factor"] == "post_admission_condition"].to_string(index=False))
print("\nMODEL 2 (DESCRIPTIVE) -- adds palliative-care coding, a post-exposure")
print("variable recorded during the episode:")
print(m2[m2["factor"] == "post_admission_condition"].to_string(index=False))
print("\nNeither is a causal estimate, and Model 2 is not better adjusted.")
print("Sicker patients both accumulate more post-admission conditions and are")
print("more likely to die; severity of illness is not measured in the RAF.")

write_suppression_report()
