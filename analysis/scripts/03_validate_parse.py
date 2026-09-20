

import os
import pandas as pd
import pyreadstat


os.makedirs(
    "output/tables",
    exist_ok=True
)


CHECK_COLS = [
    "SUB_PROV",
    "AGRP_F_D",
    "GENDER",
    "ADM_CAT",
    "ENT_CODE",
    "DIS_GRP",
    "TLOS_CAT",
    "ALC_LCAT",
    "REL_ADAY",
    "REL_DDAY",
    "PATNT_ID",
    "SCU_C_1",

    # Diagnosis fields from different parts of the record
    "D_I10_1",
    "D_TYP_1",
    "D_I10_2",
    "D_TYP_2",
    "D_I10_5",
    "D_TYP_5",
    "D_I10_10",
    "D_TYP_10",
    "D_I10_17",
    "D_TYP_17",
    "D_I10_25",
    "D_TYP_25",

    # Intervention fields from beginning, middle and end
    "I_CCI_1",
    "I_CCI_10",
    "I_CCI_20",
]


# Read our parsed version
ours = pd.read_parquet(
    "output/dad_parsed.parquet"
)


# Read only the columns we need from the SPSS file
theirs, metadata = pyreadstat.read_sav(
    "data/raw/clin_sample_spss.sav",
    usecols=CHECK_COLS
)


# Remove padding spaces from SPSS string columns
for col in theirs.columns:

    if theirs[col].dtype == object:

        theirs[col] = theirs[col].str.strip()


results = []


for col in CHECK_COLS:

    a = ours[col]
    b = theirs[col]

    # Numeric variables need numeric comparison
    if pd.api.types.is_numeric_dtype(b):

        a = pd.to_numeric(
            a,
            errors="coerce"
        )

        matches = (
            (a == b)
            |
            (a.isna() & b.isna())
        ).sum()

    else:

        # Make missing string values comparable
        a = a.fillna("").astype(str)
        b = b.fillna("").astype(str)

        matches = (
            a == b
        ).sum()


    results.append(
        {
            "variable": col,
            "n_rows": len(ours),
            "n_matching": int(matches),
            "pct_matching": round(
                100 * matches / len(ours),
                4
            ),
            "result": (
                "PASS"
                if matches == len(ours)
                else "REVIEW"
            )
        }
    )


report = pd.DataFrame(results)


report.to_csv(
    "output/tables/validation_report.csv",
    index=False
)


print(
    f"Row count -- parsed: {len(ours):,}   "
    f"SPSS: {len(theirs):,}"
)

print()

print(
    report.to_string(index=False)
)

print()


n_pass = (
    report["result"] == "PASS"
).sum()


print(
    f"{n_pass} of {len(report)} "
    f"fields match exactly."
)


if n_pass != len(report):

    raise SystemExit(
        "Parse validation failed: "
        "see validation_report.csv"
    )