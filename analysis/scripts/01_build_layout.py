

import pandas as pd


LAYOUT_XLS = (
    "data/raw/Documentation/"
    "DAD-F2021-22 to F2023-24 RAF layouts - EN.xls"
)

OUT = "output/layout.csv"


# Read the clinical layout exactly as it appears in Excel.
raw = pd.read_excel(
    LAYOUT_XLS,
    sheet_name="DAD Layout - Clinical",
    header=None
)


rows = []

for _, r in raw.iterrows():

    field_no = r[0]
    field_name = r[1]
    var_name = r[4]

    start = r[5]
    end = r[6]

    # Keep only rows that describe real fields.
    if not str(field_no).strip().isdigit():
        continue

    if pd.isna(start) or pd.isna(end):
        continue

    rows.append(
        {
            "field_no": int(field_no),
            "field_name": str(field_name).strip(),
            "variable": str(var_name).strip(),

            # CIHI counts positions from 1.
            # Python counts positions from 0.
            "start_pos": int(start) - 1,

            # Python slicing stops BEFORE the end position,
            # so CIHI's end value can remain unchanged.
            "end_pos": int(end),

            "width": int(end) - int(start) + 1,
        }
    )


layout = pd.DataFrame(rows)

layout.to_csv(
    OUT,
    index=False
)


print(f"Fields found: {len(layout)}")

print(
    f"Record width: "
    f"{layout['end_pos'].max()} characters"
)

print("\nFirst five fields:")
print(
    layout.head().to_string(index=False)
)

print("\nLast five fields:")
print(
    layout.tail().to_string(index=False)
)

print(f"\nSaved to {OUT}")