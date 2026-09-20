

import pandas as pd

# ---------------------------------------------------------------
# Age bands
#
# The reference category used to be a single "Under 50" group. In this cohort
# that group contains newborns and infants alongside 49-year-olds, so every age
# odds ratio was reported against a band spanning the whole of childhood and
# most of adult life. Paediatric episodes are split out so the reference is
# interpretable and the children are visible rather than hidden inside it.
# ---------------------------------------------------------------
PAEDIATRIC = ["newborn", "0 days to 11 months", "1-7 yrs", "8-12 yrs", "13-17 yrs"]
YOUNG_ADULT = ["18-24 yrs", "25-29 yrs", "30-34 yrs", "35-39 yrs",
               "40-44 yrs", "45-49 yrs"]

AGE_REFERENCE = "18-49"


def age_band(group):
    g = str(group).strip()
    if g == "80+ yrs":
        return "80 plus"
    if g in ("70-74 yrs", "75-79 yrs"):
        return "70-79"
    if g in ("60-64 yrs", "65-69 yrs"):
        return "60-69"
    if g in ("50-54 yrs", "55-59 yrs"):
        return "50-59"
    if g in PAEDIATRIC:
        return "Under 18"
    if g in YOUNG_ADULT:
        return AGE_REFERENCE
    return "Unknown age"


def add_age_band(d):
    d = d.copy()
    d["age_band"] = d["age_group"].apply(age_band)
    return d


# ---------------------------------------------------------------
# Disclosure control
#
# The README told the reader to check output tables for small cells before
# release and then shipped tables containing counts of 31, 42, 10 and 6. This
# is licensed microdata, so naming the safeguard and not applying it is the
# problem, not the cell sizes themselves. Released tables are passed through
# here; full-precision versions stay in output/tables/internal/ and are excluded
# from release.
# ---------------------------------------------------------------
MIN_CELL = 10       # any count of 1-9 is suppressed
MIN_DENOMINATOR = 50  # a breakdown row this small is suppressed outright

_suppressed_log = []
_REPORT_PATH = "output/tables/small_cell_report.csv"


def suppress_small_cells(df, count_cols, label_col=None, source="",
                         min_cell=MIN_CELL, min_denominator=MIN_DENOMINATOR,
                         denominator_col=None, also_blank=()):
    """
    Blank any count below min_cell, and blank the statistics derived from it.

    Two rules, because they protect against different things:

      min_cell         a count of 1-9 is suppressed outright
      min_denominator  a breakdown row with a very small GROUP TOTAL is
                       suppressed even when its counts clear min_cell, because
                       a rate published against a tiny denominator lets the
                       count be reconstructed, and small geographies and rare
                       cancer sites are exactly where re-identification risk
                       concentrates

    A percentage or confidence interval computed from a suppressed count would
    give the count straight back, so those columns are blanked on the same rows.
    """
    out = df.copy()
    present = [c for c in count_cols if c in out.columns]
    if not present:
        return out

    denom = denominator_col if denominator_col in out.columns else present[0]

    mask = pd.Series(False, index=out.index)
    for c in present:
        mask |= out[c].fillna(0).between(1, min_cell - 1)
    small_denom = out[denom].fillna(0).between(1, min_denominator - 1)
    mask |= small_denom

    if mask.any():
        for _, row in out[mask].iterrows():
            why = ("group total below %d" % min_denominator
                   if small_denom.get(row.name, False)
                   else "count below %d" % min_cell)
            _suppressed_log.append({
                "table": source,
                "row": str(row[label_col]) if label_col else "",
                "reason": why,
            })
        for c in list(present) + [c for c in also_blank if c in out.columns]:
            out.loc[mask, c] = pd.NA

    return out


def write_suppression_report(path=_REPORT_PATH, reset=False):
    """
    Append rather than overwrite. Each analysis step runs in its own process, so
    an overwriting report would only ever show whatever the last script
    suppressed and would silently hide the rest.
    """
    import os
    rep = pd.DataFrame(_suppressed_log, columns=["table", "row", "reason"])
    if not reset and os.path.exists(path):
        prior = pd.read_csv(path)
        rep = pd.concat([prior, rep], ignore_index=True)
    rep = rep.drop_duplicates().sort_values(["table", "row"], kind="stable")
    rep.to_csv(path, index=False)
    return rep
