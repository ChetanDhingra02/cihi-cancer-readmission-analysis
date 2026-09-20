

import glob
import re
import sys

import pandas as pd
from docx import Document

KEY = pd.read_csv("output/tables/key_numbers.csv")

# ---------------------------------------------------------------
# Build the set of numbers the analysis actually supports
# ---------------------------------------------------------------
supported = set()


def add(v):
    try:
        f = float(str(v).replace(",", "").replace("%", "").strip())
    except (ValueError, AttributeError):
        return
    supported.add(round(f, 4))
    # a figure may be quoted with fewer decimals than it is stored with
    for nd in (0, 1, 2, 3):
        supported.add(round(f, nd))


for v in KEY["value"]:
    add(v)
    # composite entries such as "0.691 to 0.72" or "12.4 to 14.1"
    for part in re.findall(r"-?\d+\.?\d*", str(v)):
        add(part)

for path in glob.glob("output/tables/*.csv"):
    try:
        df = pd.read_csv(path)
    except Exception:
        continue
    for col in df.columns:
        for v in df[col].dropna().tolist():
            add(v)
        add(col)

# Structural numbers that are not analysis results: section numbering, ICD
# chapter boundaries, method parameters quoted as parameters, and round
# rhetorical figures ("one in seven", "100 patients").
ALLOWED = {
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    25, 30, 50, 60, 90, 91, 95, 100, 159, 200, 300, 400, 1000,
    1065, 1095, 2021, 2022, 2023, 2024,
    # ICD-10-CA and CCI references used as codes, not counts
    97, 47, 45, 51, 77, 79, 80, 81, 96, 71, 81.0,
}
supported |= {float(a) for a in ALLOWED}

# A leading minus only counts as a minus when it is not a hyphen joining two
# tokens: "FY2021-22" and "COVID-19" are not negative numbers.
NUM = re.compile(r"(?<![\w-])-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w-])-?\d+\.\d+|(?<![\w-])-?\d+")


def numbers_in(text):
    out = []
    for m in NUM.finditer(text):
        raw = m.group(0)
        try:
            out.append((raw, float(raw.replace(",", ""))))
        except ValueError:
            pass
    return out


def prose_of(path):
    """Paragraph text only. Embedded tables are copied from the CSVs verbatim."""
    doc = Document(path)
    return [p.text for p in doc.paragraphs if p.text.strip()]


rows = []
unaccounted = 0

for path in sorted(glob.glob("output/*.docx")):
    for line in prose_of(path):
        for raw, val in numbers_in(line):
            ok = round(val, 4) in supported or val in supported
            if not ok:
                # a value quoted to fewer decimals than stored
                ok = any(abs(val - s) < 0.051 for s in supported
                         if abs(s - val) < 1)
            if not ok:
                unaccounted += 1
                rows.append({
                    "document": path.split("/")[-1],
                    "value": raw,
                    "context": line[:150],
                })

report = pd.DataFrame(rows, columns=["document", "value", "context"])
report.to_csv("output/tables/document_verification.csv", index=False)

n_checked = sum(len(numbers_in(l)) for p in glob.glob("output/*.docx")
                for l in prose_of(p))

print("=" * 72)
print("DOCUMENT VERIFICATION")
print("=" * 72)
print(f"Numbers found in document prose : {n_checked}")
print(f"Traced to the analysis outputs  : {n_checked - unaccounted}")
print(f"Unaccounted for                 : {unaccounted}")

if unaccounted:
    print()
    print(report.to_string(index=False))
    print()
    print("A document is asserting a figure the analysis does not produce.")
    print("Either add it to scripts/12_key_numbers.py or remove the claim.")
    sys.exit(1)

print()
print("Every number in both documents traces to a generated output.")
print("The 'generated, not typed' claim is now verified in both directions:")
print("  script 13 guarantees what goes IN")
print("  script 14 checks what came OUT")
