

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


RAW = "data/raw/clin_sample_ascii.dat"
JOINED = "output/dad_joined.txt"
OUT = "output/dad_parsed.parquet"


# Read the field positions we created in Step 1
layout = pd.read_csv("output/layout.csv")


# ---------------------------------------------------------------
# Part 1: Rebuild each pair of physical lines into one record
# ---------------------------------------------------------------

print("Joining line pairs...")

n_written = 0

with open(RAW, "r", encoding="latin-1") as fin, \
     open(JOINED, "w") as fout:

    for line_no, line in enumerate(fin):

        text = line.rstrip("\r\n")

        # line_no starts from 0.
        # Even-numbered lines are the first half of a record.
        if line_no % 2 == 0:

            first_half = text

        # Odd-numbered lines are the second half.
        else:

            record = first_half.ljust(801) + " " + text

            fout.write(
                record.ljust(810) + "\n"
            )

            n_written += 1


# Make sure the raw file did not end halfway through a record
if line_no % 2 == 0:

    raise SystemExit(
        f"The raw file has an odd number of lines "
        f"({line_no + 1:,}). "
        f"The last record has no second half."
    )


print(f"Records rebuilt: {n_written:,}")


# ---------------------------------------------------------------
# Part 2: Use the layout to split each record into 159 columns
# ---------------------------------------------------------------

print("Reading fixed-width file...")


# Example:
# [(0, 1), (2, 21), (22, 23), ...]
colspecs = list(
    zip(
        layout["start_pos"],
        layout["end_pos"]
    )
)


# Column names:
# SUB_PROV, AGRP_F_D, GENDER, ...
names = list(layout["variable"])


# Fields that should actually be numeric
numeric_cols = [
    "TLOS_CAT",
    "ACT_LCAT",
    "ALC_LCAT",
    "REL_DDAY",
    "REL_ADAY",
    "PATNT_ID",
] + [
    f"S_L_HR_{i}" for i in range(1, 7)
]


def tidy(chunk):

    # Remove padding spaces from every string column
    for col in chunk.columns:
        chunk[col] = chunk[col].str.strip()

    # Convert selected fields to numbers
    for col in numeric_cols:
        chunk[col] = pd.to_numeric(
            chunk[col],
            errors="coerce"
        )

    return chunk


# Process 100,000 records at a time
CHUNK = 100_000

writer = None
n_rows = 0


try:

    for chunk in pd.read_fwf(
        JOINED,
        colspecs=colspecs,
        names=names,
        dtype=str,
        header=None,
        chunksize=CHUNK
    ):

        # Convert the pandas chunk to a Parquet-compatible table
        table = pa.Table.from_pandas(
            tidy(chunk),
            preserve_index=False
        )

        # Create the Parquet file when we process the first chunk
        if writer is None:
            writer = pq.ParquetWriter(
                OUT,
                table.schema
            )

        # Add this chunk to the file
        writer.write_table(table)

        n_rows += len(chunk)

        print(
            f"  parsed {n_rows:,} rows",
            end="\r"
        )


finally:

    if writer is not None:
        writer.close()


print()


# ---------------------------------------------------------------
# Validation
# ---------------------------------------------------------------

if n_rows != n_written:

    raise SystemExit(
        f"Parsed {n_rows:,} rows but rebuilt "
        f"{n_written:,} records. "
        f"Do not trust anything downstream."
    )


# We only need the patient ID column for this final check
df = pd.read_parquet(
    OUT,
    columns=["PATNT_ID"]
)


print(
    f"Rows: {n_rows:,}   "
    f"Columns: {len(names)}"
)

print(
    f"Unique patients: "
    f"{df['PATNT_ID'].nunique():,}"
)

print(f"Saved to {OUT}")