

import os
import pandas as pd

os.makedirs("reference", exist_ok=True)

# (first code, last code, site label, note)
RANGES = [
    (0,  14, "Head and neck",              "Lip, oral cavity, pharynx, larynx-adjacent sites"),
    (15, 26, "Digestive",                  "Oesophagus, stomach, colon, rectum, liver, pancreas"),
    (30, 39, "Respiratory and intrathoracic", "Nasal, larynx, trachea, lung, thymus, heart, mediastinum"),
    (40, 41, "Bone and cartilage",         "Bone and articular cartilage"),
    (43, 44, "Skin",                       "Melanoma and other malignant skin neoplasms"),
    (45, 49, "Soft tissue",                "Mesothelium, Kaposi sarcoma, peripheral nerve, connective tissue"),
    (50, 50, "Breast",                     "Breast"),
    (51, 58, "Female reproductive",        "Vulva, vagina, cervix, uterus, ovary, placenta"),
    (60, 63, "Male reproductive",          "Penis, prostate, testis"),
    (64, 68, "Urinary",                    "Kidney, renal pelvis, ureter, bladder, urethra"),
    (69, 72, "Eye, brain and nervous system", "Eye, meninges, brain, spinal cord, cranial nerves"),
    (73, 75, "Thyroid and endocrine",      "Thyroid, adrenal, other endocrine glands"),
    (76, 76, "Ill-defined site",           "Malignant neoplasm of other and ill-defined sites"),
    (77, 79, "Secondary (spread)",         "Metastatic deposits; NOT where the cancer began"),
    (80, 80, "Unknown primary",            "Malignant neoplasm without specification of site"),
    (81, 96, "Haematologic",               "Lymphoma, leukaemia, myeloma and related"),
    (97, 97, "Multiple primaries",         "Independent primary sites at more than one location"),
]

rows = []
for lo, hi, label, note in RANGES:
    for n in range(lo, hi + 1):
        rows.append({
            "code_3char": f"C{n:02d}",
            "cancer_site": label,
            # Secondary, unknown and multiple-primary codes must never be used to
            # decide where a cancer started.
            "is_primary_site": label not in (
                "Secondary (spread)", "Unknown primary", "Multiple primaries"
            ),
            # Precedence when several cancer codes appear across one episode of
            # care. A genuine primary site always wins over a secondary deposit
            # or an unknown primary, wherever in the episode it was recorded.
            "site_rank": (
                1 if label not in ("Secondary (spread)", "Unknown primary",
                                   "Multiple primaries")
                else 2 if label == "Multiple primaries"
                else 3 if label == "Secondary (spread)"
                else 4
            ),
            "note": note,
        })

mapping = pd.DataFrame(rows)
mapping.to_csv("reference/cancer_site_mapping.csv", index=False)

scope = pd.DataFrame([
    {"code_range": "C00-C97", "description": "Malignant neoplasms",
     "in_cohort": True,
     "reason": "Invasive cancer. This is the study population."},
    {"code_range": "D00-D09", "description": "Carcinoma in situ",
     "in_cohort": False,
     "reason": "Non-invasive. Flagged separately. These are solid-organ sites, "
               "not blood or lymph."},
    {"code_range": "D45-D47", "description": "Neoplasms of uncertain behaviour",
     "in_cohort": False,
     "reason": "Includes polycythaemia vera and myelodysplastic syndromes. "
               "Clinically distinct from invasive malignancy; flagged separately."},
])
scope.to_csv("reference/cancer_scope.csv", index=False)

print(f"Wrote {len(mapping)} code-to-site rows covering C00-C97")
print()
print(mapping.groupby("cancer_site").agg(
    codes=("code_3char", "size"),
    counts_as_primary_site=("is_primary_site", "first"),
    site_rank=("site_rank", "first"),
).sort_values(["site_rank", "codes"], ascending=[True, False]).to_string())
print()
print("site_rank sets precedence when one episode of care carries several "
      "cancer codes:\n  1 primary site  2 multiple primaries  "
      "3 secondary deposit  4 unknown primary")
print()
print("Cohort scope:")
print(scope[["code_range", "description", "in_cohort"]].to_string(index=False))
