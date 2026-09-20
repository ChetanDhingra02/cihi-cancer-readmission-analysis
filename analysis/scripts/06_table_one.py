

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import age_band, add_age_band, AGE_REFERENCE, \
    suppress_small_cells, write_suppression_report, MIN_CELL

import os
import pandas as pd



df = pd.read_parquet("output/cohort.parquet")
df = df[df["discharged_home"]].copy()
OUTCOME = "urgent_readmit_30d"

rows = []


def add_row(label, series):
    rows.append({
        "characteristic": label,
        "overall_n": int(series.sum()),
        "overall_pct": round(100 * series.mean(), 1),
        "not_readmitted_pct": round(100 * series[~df[OUTCOME]].mean(), 1),
        "readmitted_pct": round(100 * series[df[OUTCOME]].mean(), 1),
    })


for group in sorted(df["age_group"].unique()):
    add_row(f"Age: {group}", df["age_group"] == group)

add_row("Sex: female", df["sex"] == "F")
add_row("Sex: male", df["sex"] == "M")

for site in df["cancer_site"].value_counts().index:
    add_row(f"Cancer site: {site}", df["cancer_site"] == site)

add_row("Cancer was the main reason for the episode", df["cancer_is_main_reason"])
add_row("Secondary (metastatic) deposits coded", df["cancer_has_spread"])
add_row("Urgent/emergent admission category", df["urgent_admission"])
add_row("Entered through an emergency department", df["entered_via_ed"])
add_row("Episode spanned more than one facility", df["n_abstracts"] > 1)
add_row("Special care unit stay", df["intensive_care"])
add_row("Palliative care coded", df["palliative_care"])
add_row("Condition coded as arising after admission", df["post_admission_condition"])
add_row("Waited in hospital for another level of care", df["waited_for_other_care"])
add_row("Had a procedure", df["n_procedures"] > 0)

add_row("Heart failure on admission", df["has_heart_failure"])
add_row("Diabetes on admission", df["has_diabetes"])
add_row("Kidney disease on admission", df["has_kidney_disease"])
add_row("Lung disease on admission", df["has_lung_disease"])
add_row("Dementia on admission", df["has_dementia"])
add_row("Anaemia on admission", df["has_anaemia"])
add_row("Two or more recorded comorbidities", df["comorbidity_count"] >= 2)

los_labels = {1: "1 day", 2: "2 days", 3: "3 days", 4: "4-5 days",
              6: "6-9 days", 10: "10 or more days"}
for code, label in los_labels.items():
    add_row(f"Final stay length band: {label}", df["final_los_group"] == code)

for prov in df["province"].value_counts().index:
    add_row(f"Province: {prov}", df["province"] == prov)

table1 = pd.DataFrame(rows)
table1["difference"] = (table1["readmitted_pct"] - table1["not_readmitted_pct"]).round(1)
# Disclosure control, applied rather than described. Table 1 previously shipped
# with rows of 6 and 31 in a licensed microdata product.
os.makedirs("output/tables/internal", exist_ok=True)
table1.to_csv("output/tables/internal/table1_characteristics_full.csv", index=False)
suppress_small_cells(
    table1, ["overall_n"], "characteristic", "table1_characteristics",
    denominator_col="overall_n",
    also_blank=("overall_pct", "not_readmitted_pct", "readmitted_pct", "difference"),
).to_csv("output/tables/table1_characteristics.csv", index=False)
write_suppression_report(reset=True)

n_total = len(df)
n_out = int(df[OUTCOME].sum())
print(f"Primary cohort: {n_total:,} episodes of care from "
      f"{df['patient_id'].nunique():,} patients")
print(f"Urgent/emergent 30-day readmission: {n_out:,} ({100*n_out/n_total:.1f}%)")
print(f"Readmission entering via ED:        {int(df['ed_readmit_30d'].sum()):,} "
      f"({100*df['ed_readmit_30d'].mean():.1f}%)")
print(f"Any 30-day return incl. planned:    {int(df['returned_30d'].sum()):,} "
      f"({100*df['returned_30d'].mean():.1f}%)")
print()
print(table1.to_string(index=False))
print("\nSaved to output/tables/table1_characteristics.csv")
