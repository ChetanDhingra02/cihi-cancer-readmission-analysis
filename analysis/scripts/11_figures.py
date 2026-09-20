

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BLUE, GREY, RED, AMBER = "#2c6fa8", "#9aa5ad", "#c0483f", "#d99a2b"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(f"output/figures/{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {name}.png")


print("Making charts...")

# --- Fig 1: readmission by cancer site ---
d = pd.read_csv("output/tables/q1_rate_by_cancer_site.csv")
d = d[d["episodes"] >= 150].sort_values("percent")
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(d["cancer_site"], d["percent"], color=BLUE)
ax.errorbar(d["percent"], d["cancer_site"],
            xerr=[d["percent"] - d["ci_low"], d["ci_high"] - d["percent"]],
            fmt="none", ecolor="black", capsize=3, linewidth=1)
for y, (pct, hi, n) in enumerate(zip(d["percent"], d["ci_high"], d["episodes"])):
    ax.text(hi + 0.6, y, f"{pct}%  (n={n:,})", va="center", fontsize=8.5)
ax.set_xlabel("Urgent/emergent readmission within 30 days (%)")
n_cohort = int(d["episodes"].sum())
ax.set_title("Urgent 30-day readmission after a transfer-linked cancer episode\n"
             f"(discharged home, n={n_cohort:,})",
             fontsize=12, fontweight="bold")
ax.set_xlim(0, 32)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "fig1_readmission_by_cancer_site")

# --- Fig 2: calibration ---
d = pd.read_csv("output/tables/q1_calibration.csv")
fig, ax = plt.subplots(figsize=(7.5, 5))
ax.plot(d["group"], d["predicted_pct"], "o--", color=GREY, label="Model predicted")
ax.plot(d["group"], d["actual_pct"], "o-", color=BLUE, linewidth=2, label="Observed")
ax.set_xlabel("Risk group (1 = lowest predicted risk, 10 = highest)")
ax.set_ylabel("Urgent readmission within 30 days (%)")
ax.set_title("Predicted risk against observed outcome", fontsize=12, fontweight="bold")
ax.set_xticks(range(1, 11))
ax.legend(frameon=False)
ax.grid(axis="y", alpha=0.3)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "fig2_model_calibration")

# --- Fig 3: urgent admission vs mortality ---
d = pd.read_csv("output/tables/q2_urgent_by_site.csv")
fig, ax = plt.subplots(figsize=(8.5, 6))
ax.scatter(d["pct_urgent"], d["pct_died"], s=d["episodes"] / 25,
           color=BLUE, alpha=0.65, edgecolor="black", linewidth=0.6)
nudge = {"Urinary": (7, 6), "Head and neck": (7, -12), "Skin": (7, -12),
         "Male reproductive": (-105, -4), "Female reproductive": (7, -12)}
for _, r in d.iterrows():
    ax.annotate(r["cancer_site"], (r["pct_urgent"], r["pct_died"]),
                textcoords="offset points",
                xytext=nudge.get(r["cancer_site"], (7, 4)), fontsize=8.5)
ax.set_xlabel("Urgent/emergent admission category (%)")
ax.set_ylabel("Died during the episode (%)")
ax.set_title("Urgent admission and in-hospital mortality across cancer sites\n(episodes where cancer was the most responsible diagnosis)",
             fontsize=12, fontweight="bold")
ax.grid(alpha=0.3)
ax.set_xlim(0, 80)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "fig3_urgent_vs_mortality")

# --- Fig 4: mortality trend ---
d = pd.read_csv("output/tables/q4_quarterly_trend.csv")
fig, ax = plt.subplots(figsize=(8.5, 5))
ax.plot(d["quarter"], d["pct_died"], "o-", color=RED, linewidth=2, label="Died in hospital")
ax.plot(d["quarter"], d["pct_aged_80_plus"], "s--", color=GREY, label="Aged 80 or over")
ax.plot(d["quarter"], d["pct_intensive_care"], "^--", color=BLUE, label="Special care unit")
ax.plot(d["quarter"], d["pct_palliative"], "d--", color=AMBER, label="Palliative care coded")
ax.set_xlabel("Quarter, anchored on discharge (1 = earliest)")
ax.set_ylabel("Percent of cancer episodes")
ax.set_title("In-hospital mortality rose; measured patient characteristics did not",
             fontsize=12, fontweight="bold")
ax.set_xticks(range(1, 13))
ax.set_ylim(0, 26)
ax.legend(frameon=False, fontsize=9)
ax.grid(axis="y", alpha=0.3)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "fig4_mortality_trend")

# --- Fig 5: post-admission conditions ---
d = pd.read_csv("output/tables/q3_outcomes.csv")
labels = ["Died in hospital", "Special care unit", "Episode 6 days or longer"]
no = d.loc[d["post_admission_condition"] == "None coded",
           ["pct_died", "pct_intensive_care", "pct_long_stay"]].values[0]
yes = d.loc[d["post_admission_condition"] == "At least one coded",
            ["pct_died", "pct_intensive_care", "pct_long_stay"]].values[0]
x = range(len(labels))
fig, ax = plt.subplots(figsize=(8.5, 5))
ax.bar([i - 0.2 for i in x], no, width=0.4, label="No post-admission condition coded", color=GREY)
ax.bar([i + 0.2 for i in x], yes, width=0.4, label="At least one coded", color=RED)
for i, (a, b) in enumerate(zip(no, yes)):
    ax.text(i - 0.2, a + 1.2, f"{a}%", ha="center", fontsize=9)
    ax.text(i + 0.2, b + 1.2, f"{b}%", ha="center", fontsize=9)
ax.set_xticks(list(x)); ax.set_xticklabels(labels)
ax.set_ylabel("Percent of cancer episodes")
ax.set_title("Outcomes by whether a condition was coded as arising after admission",
             fontsize=12, fontweight="bold")
ax.set_ylim(0, 95)
ax.legend(frameon=False, fontsize=9)
ax.grid(axis="y", alpha=0.3)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "fig5_post_admission_outcomes")

# --- Fig 6: provinces ---
d = pd.read_csv("output/tables/q1_rate_by_province.csv")
d = d[d["episodes"] >= 300].sort_values("percent")
colours = [RED if p == "Alberta" else BLUE for p in d["province"]]
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(d["province"], d["percent"], color=colours)
ax.errorbar(d["percent"], d["province"],
            xerr=[d["percent"] - d["ci_low"], d["ci_high"] - d["percent"]],
            fmt="none", ecolor="black", capsize=3, linewidth=1)
# Read from the analysis output, not typed. This annotation was the literal
# 15.6, which is the same class of error as the hand-written report figures the
# audit found: a released artefact asserting a number nothing checked.
_sens = pd.read_csv("output/tables/q1_sensitivity.csv")
national = float(_sens.loc[_sens["analysis"].str.startswith("Primary"),
                           "urgent_readmit_pct"].iloc[0])
ax.axvline(national, color="black", linestyle=":", linewidth=1.2)
ax.text(national + 0.15, -0.65, f"Cohort average {national}%", fontsize=8.5)
ax.set_xlabel("Urgent/emergent readmission within 30 days (%)")
ax.set_title("Provinces compared, Alberta in red\n(the RAF does not include Quebec)",
             fontsize=12, fontweight="bold")
ax.set_xlim(0, 24)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "fig6_province_comparison")

# --- Fig 7: how definitions change the answer ---
d = pd.read_csv("output/tables/q1_sensitivity.csv").sort_values("urgent_readmit_pct")
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.barh(d["analysis"], d["urgent_readmit_pct"], color=BLUE)
for y, v in enumerate(d["urgent_readmit_pct"]):
    ax.text(v + 0.2, y, f"{v}%", va="center", fontsize=9)
ax.set_xlabel("30-day readmission (%)")
# The title said "five" while the chart drew six bars, and the rows are not all
# definitions of one quantity: three vary the cohort or the timing treatment and
# three vary the outcome. Counted from the data and described for what it is.
_words = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"}
ax.set_title(f"The same data, {_words.get(len(d), len(d))} defensible "
             f"cohort and outcome definitions",
             fontsize=12, fontweight="bold")
ax.set_xlim(0, 23)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "fig7_definition_sensitivity")

print("\nAll charts written to output/figures/")
