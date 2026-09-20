
import duckdb
import pandas as pd

con = duckdb.connect("output/dad.duckdb")

# Load the documented cancer site mapping as a lookup table
con.execute("DROP TABLE IF EXISTS cancer_site_map")
con.execute("""
    CREATE TABLE cancer_site_map AS
    SELECT * FROM read_csv_auto('reference/cancer_site_mapping.csv')
""")

SQL = open("sql/02_cohort.sql").read()

# The transfer-linking rule is a parameter, so the same SQL can be rerun under
# alternative definitions for the sensitivity analysis below.
def derived_rule(tol):
    """Merge on the DERIVED admission day (REL_DDAY minus the stay-band floor)."""
    return ("pseudo_admission_day >= prev_discharge_day "
            f"AND pseudo_admission_day <= prev_discharge_day + {tol}")


def interval_rule(tol, cap=None):
    """
    Merge when the receiving stay's POSSIBLE admission interval overlaps the
    transfer window [prev_discharge_day, prev_discharge_day + tol].

    The derived admission day is REL_DDAY minus the FLOOR of the length-of-stay
    band, so it is never earlier than the true admission and for the ">=10 days"
    band it can be arbitrarily later. A real transfer into a long stay therefore
    looks like it began weeks after the sending facility discharged the patient,
    fails the derived-day test, and the continuous episode gets split in two.

    The true admission lies somewhere in [earliest_possible, pseudo_admission_day].
    Overlap with the transfer window needs BOTH ends tested:

        earliest_possible <= prev_discharge_day + tol   (could have begun in time)
        pseudo_admission_day >= prev_discharge_day      (did not begin before the
                                                         sending discharge)

    The second condition is not optional. Version 6 identified and fixed exactly
    this case on the derived-day rule -- a receiving admission whose start
    precedes the previous discharge describes two overlapping stays, not a
    transfer -- and the interval rule added in version 7 tested only the first
    condition, silently reintroducing it for 699 transitions.

    `cap` bounds the ">=10 days" band. Left unbounded, that band permits any
    stay length whatever, so the earliest-possible test is vacuous for it and
    the rule merges abstracts separated by years: as shipped it merged 3,098
    pairs implying a receiving stay over 180 days and 1,281 implying over a
    year, the longest 1,039 days. That is a defensible upper bound on merging
    but not a defensible episode definition, so a capped variant is reported
    beside it and the conclusions are checked against both.
    """
    if cap is None:
        earliest_ok = (f"(los_unbounded OR pseudo_admission_day "
                       f"- (los_max - length_of_stay_group) <= prev_discharge_day + {tol})")
    else:
        earliest_ok = (f"(pseudo_admission_day - (CASE WHEN los_unbounded THEN {cap} "
                       f"ELSE los_max END - length_of_stay_group) "
                       f"<= prev_discharge_day + {tol})")
    return f"(pseudo_admission_day >= prev_discharge_day AND {earliest_ok})"


# Cap applied to the unbounded ">=10 days" band by the capped interval rule.
# 90 days is far beyond any ordinary acute receiving stay while still ruling out
# the multi-year merges the uncapped rule permits. The choice is a parameter, not
# a finding: script 15 reports the estimates under both.
LONG_STAY_CAP_DAYS = 90


PRIMARY_RULE = {"TRANSFER_CONDITION": "prev_was_transfer",
                "MERGE_PREDICATE": derived_rule(1)}

con.execute(SQL.format(**PRIMARY_RULE))


def one(sql):
    return con.execute(sql).fetchone()[0]


# ---------------------------------------------------------------
# Episodes of care
# ---------------------------------------------------------------
n_abstracts = one("SELECT COUNT(*) FROM all_admissions")
n_episodes = one("SELECT COUNT(*) FROM episode_level")
n_merged = one("SELECT COUNT(*) FROM episode_level WHERE n_abstracts > 1")

print("=" * 72)
print("EPISODES OF CARE")
print("=" * 72)
print(f"DAD abstracts:                      {n_abstracts:,}")
print(f"Episodes of care after merging:     {n_episodes:,}")
print(f"Episodes built from >1 abstract:    {n_merged:,}")
print(f"Abstracts absorbed by merging:      {n_abstracts - n_episodes:,}")
print()
print(con.execute("""
    SELECT n_abstracts AS abstracts_in_episode, COUNT(*) AS episodes
    FROM episode_level GROUP BY 1 ORDER BY 1 LIMIT 6
""").df().to_string(index=False))

# ---------------------------------------------------------------
# Study flow
# ---------------------------------------------------------------
cancer_ep = one("SELECT COUNT(*) FROM episode_full WHERE has_cancer")
alive = one("SELECT COUNT(*) FROM episode_full WHERE has_cancer AND NOT died_in_hospital")
final = one("SELECT COUNT(*) FROM cohort")
home = one("SELECT COUNT(*) FROM cohort WHERE discharged_home")
patients = one("SELECT COUNT(DISTINCT patient_id) FROM cohort WHERE discharged_home")
live_patients = one("SELECT COUNT(DISTINCT patient_id) FROM cohort")
insitu_only = one("""
    SELECT COUNT(*) FROM episode_full
    WHERE NOT has_cancer AND (carcinoma_in_situ OR uncertain_behaviour)
""")

flow = pd.DataFrame([
    ["DAD abstracts in the file", n_abstracts, ""],
    ["Episodes of care after merging transfers", n_episodes,
     f"{n_abstracts - n_episodes:,} abstracts merged into earlier episodes"],
    ["Episodes with invasive cancer (C00-C97)", cancer_ep,
     f"{insitu_only:,} episodes with only in-situ or uncertain-behaviour codes excluded"],
    ["Ended in a live discharge", alive,
     f"removed {cancer_ep - alive:,} episodes ending in death"],
    ["At least 30 days of follow-up remaining", final,
     f"removed {alive - final:,} ending too near the end of the data window"],
    ["PRIMARY COHORT: discharged home", home,
     f"removed {final - home:,} discharged to another facility or absent"],
], columns=["step", "n", "note"])
flow.to_csv("output/tables/study_flow.csv", index=False)

print()
print("=" * 72)
print("STUDY FLOW")
print("=" * 72)
print(flow.to_string(index=False))
print(f"\nPrimary cohort: {home:,} episodes, {patients:,} distinct patients")
print(f"All live discharges: {final:,} episodes, {live_patients:,} distinct patients")

# ---------------------------------------------------------------
# How the definition changes the answer
# ---------------------------------------------------------------
sens = con.execute("""
    SELECT 'All live discharges' AS cohort_definition,
           COUNT(*) AS episodes,
           ROUND(100.0*AVG(CAST(returned_30d AS INT)), 1)       AS any_return_pct,
           ROUND(100.0*AVG(CAST(urgent_readmit_30d AS INT)), 1) AS urgent_pct,
           ROUND(100.0*AVG(CAST(ed_readmit_30d AS INT)), 1)     AS ed_entry_pct
    FROM cohort
    UNION ALL
    SELECT 'Discharged home only',
           COUNT(*),
           ROUND(100.0*AVG(CAST(returned_30d AS INT)), 1),
           ROUND(100.0*AVG(CAST(urgent_readmit_30d AS INT)), 1),
           ROUND(100.0*AVG(CAST(ed_readmit_30d AS INT)), 1)
    FROM cohort WHERE discharged_home
""").df()
sens.to_csv("output/tables/cohort_definition_sensitivity.csv", index=False)

print()
print("=" * 72)
print("HOW THE COHORT DEFINITION CHANGES THE ANSWER")
print("=" * 72)
print(sens.to_string(index=False))

# ---------------------------------------------------------------
# Timing uncertainty
# ---------------------------------------------------------------
cert = con.execute("""
    SELECT urgent_readmit_certainty AS certainty,
           COUNT(*) AS episodes,
           ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (), 1) AS pct
    FROM cohort WHERE discharged_home
    GROUP BY 1 ORDER BY episodes DESC
""").df()
cert.to_csv("output/tables/readmission_certainty.csv", index=False)

print()
print("=" * 72)
print("TIMING CERTAINTY (primary cohort)")
print("=" * 72)
print("Certainty of the PRIMARY outcome (urgent/emergent 30-day readmission).")
print("The admission day is derived from a categorised length of stay, so some")
print("classifications cannot be resolved exactly.")
print()
print(cert.to_string(index=False))

amb = one("SELECT COUNT(*) FROM cohort WHERE discharged_home AND urgent_readmit_certainty='ambiguous'")
print(f"\nAmbiguous cases: {amb:,} of {home:,} ({100*amb/home:.1f}%).")
print("Sensitivity analysis in step 7 excludes these and reports whether the")
print("conclusions change.")

# ---------------------------------------------------------------
# Save
# ---------------------------------------------------------------
con.execute("COPY cohort TO 'output/cohort.parquet' (FORMAT PARQUET)")
con.execute("COPY episode_full TO 'output/episode_level.parquet' (FORMAT PARQUET)")
con.execute("COPY all_admissions TO 'output/analysis_all_admissions.parquet' (FORMAT PARQUET)")
# ---------------------------------------------------------------
# Does the transfer-linking rule change the ANSWER?
#
# Counting how many abstracts get merged only shows that episode counts move.
# What matters is whether the readmission estimate moves. The whole cohort is
# therefore rebuilt under each rule and the primary outcome recomputed.
# ---------------------------------------------------------------
print()
print("=" * 72)
print("TRANSFER-RULE SENSITIVITY (full cohort rebuilt under each rule)")
print("=" * 72)

# The first three are clinically defensible ways to draw the transfer boundary.
# The fourth deliberately over-merges by ignoring transfer coding altogether: it
# is a stress test showing what happens if the rule is wrong, not an equally
# reasonable definition, and is labelled as such.
RULES = [
    ("Same-day transfer", "plausible",
     {"TRANSFER_CONDITION": "prev_was_transfer", "MERGE_PREDICATE": derived_rule(0)}),
    ("Same or next day (primary)", "plausible",
     {"TRANSFER_CONDITION": "prev_was_transfer", "MERGE_PREDICATE": derived_rule(1)}),
    ("Within two days", "plausible",
     {"TRANSFER_CONDITION": "prev_was_transfer", "MERGE_PREDICATE": derived_rule(2)}),
    # Not a tolerance variant. This one changes WHICH DAY is compared, and is the
    # only rule here capable of detecting the long-stay merge failure, because
    # widening a tolerance by one or two days cannot correct an error of thirty.
    ("Interval-aware (earliest possible admission)", "plausible",
     {"TRANSFER_CONDITION": "prev_was_transfer", "MERGE_PREDICATE": interval_rule(1)}),
    # The uncapped interval rule treats the ">=10 days" band as permitting any stay
    # length at all, so its earliest-possible test is vacuous for that band and it
    # merges abstracts separated by years. This variant bounds the band, keeping the
    # rule's purpose -- catching the long-stay merge failure -- without those merges.
    (f"Interval-aware, 10+ band capped at {LONG_STAY_CAP_DAYS} days", "plausible",
     {"TRANSFER_CONDITION": "prev_was_transfer",
      "MERGE_PREDICATE": interval_rule(1, cap=LONG_STAY_CAP_DAYS)}),
    ("Transfer coding ignored", "stress test",
     {"TRANSFER_CONDITION": "TRUE", "MERGE_PREDICATE": derived_rule(1)}),
]

rule_rows = []
for label, kind, params in RULES:
    con.execute(SQL.format(**params))
    r = con.execute("""
        SELECT COUNT(*) AS cohort_n,
               SUM(CAST(urgent_readmit_30d AS INT)) AS urgent,
               ROUND(100.0*AVG(CAST(urgent_readmit_30d AS INT)), 2) AS pct
        FROM cohort WHERE discharged_home
    """).df()
    n_ep = con.execute("SELECT COUNT(*) FROM episode_level").fetchone()[0]
    rule_rows.append({
        "transfer_rule": label,
        "kind": kind,
        "episodes_total": n_ep,
        "primary_cohort_n": int(r.loc[0, "cohort_n"]),
        "urgent_readmissions": int(r.loc[0, "urgent"]),
        "urgent_readmit_pct": float(r.loc[0, "pct"]),
    })

rules = pd.DataFrame(rule_rows)
rules.to_csv("output/tables/transfer_rule_sensitivity.csv", index=False)
print(rules.to_string(index=False))
plaus = rules[rules["kind"] == "plausible"]
spread = plaus["urgent_readmit_pct"].max() - plaus["urgent_readmit_pct"].min()
stress = rules.loc[rules["kind"] == "stress test", "urgent_readmit_pct"].iloc[0]
# Select the derived-day rules by name, not by a substring. Matching on "day"
# also caught "Interval-aware, 10+ band capped at 90 days", which is not a
# tolerance variant, and quietly reported its spread as the derived-day spread.
DERIVED_DAY_RULES = ["Same-day transfer", "Same or next day (primary)",
                     "Within two days"]
derived_only = rules[rules["transfer_rule"].isin(DERIVED_DAY_RULES)]
assert len(derived_only) == len(DERIVED_DAY_RULES), "derived-day rule names drifted"
derived_spread = (derived_only["urgent_readmit_pct"].max()
                  - derived_only["urgent_readmit_pct"].min())
n_plausible = int((rules["kind"] == "plausible").sum())

print(f"""
WHAT THIS TEST CAN AND CANNOT DETECT.

The three same/next/two-day rules span {derived_spread:.2f} percentage points. That
looks reassuring, but all three compare the SAME derived admission day and differ
only in tolerance. The derived day is REL_DDAY minus the FLOOR of the stay band,
so for the ">=10 days" band it can sit weeks after the true admission. Moving a
tolerance by one or two days cannot detect an error of thirty. A narrow spread
across those three rules is therefore weak evidence, not strong evidence.

The interval-aware rule is the informative comparison, because it changes which
day is compared rather than by how much. It is reported twice: once with the
">=10 days" band left unbounded, and once with that band capped, because an
unbounded band makes the earliest-possible test vacuous and permits merges
spanning years. Across all {n_plausible} plausible rules the spread is
{spread:.2f} percentage points.

The over-merging stress test gives {stress:.2f}%. That rule is not defensible as an
episode definition -- two genuinely separate admissions can be one day apart --
but it bounds the direction and size of the error if transfer coding were ignored.
""")

# ---------------------------------------------------------------
# Merge-rate diagnostic: WHERE the derived-day rule fails
# ---------------------------------------------------------------
con.execute(SQL.format(**PRIMARY_RULE))
merge_diag = con.execute("""
    WITH ordered AS (
      SELECT *, LAG(discharge_day) OVER w AS prev_dd,
                LAG(discharged_by_transfer) OVER w AS prev_tr
      FROM all_admissions
      WINDOW w AS (PARTITION BY patient_id ORDER BY discharge_day, record_id)
    )
    SELECT length_of_stay_group AS receiving_stay_band,
           COUNT(*) AS abstracts_after_a_transfer,
           SUM(CASE WHEN pseudo_admission_day >= prev_dd
                     AND pseudo_admission_day <= prev_dd + 1 THEN 1 ELSE 0 END) AS merged,
           ROUND(100.0*AVG(CASE WHEN pseudo_admission_day >= prev_dd
                     AND pseudo_admission_day <= prev_dd + 1 THEN 1.0 ELSE 0 END), 1)
               AS pct_merged
    FROM ordered WHERE prev_tr AND prev_dd IS NOT NULL
    GROUP BY 1 ORDER BY 1
""").df()
merge_diag.to_csv("output/tables/transfer_merge_diagnostic.csv", index=False)

print("=" * 72)
print("WHY THE DERIVED-DAY RULE FAILS, BY RECEIVING STAY LENGTH")
print("=" * 72)
print(merge_diag.to_string(index=False))
print("""
The merge rate collapses as the receiving stay lengthens. This is not a coding
pattern in the data; it is an artefact of the derived admission day. It means
episode splitting is NOT random with respect to length of stay, and therefore
not random with respect to severity.
""")

contam = con.execute("""
    WITH ordered AS (
      SELECT record_id, pseudo_admission_day, length_of_stay_group, los_max,
             los_unbounded,
             LAG(discharge_day) OVER w AS prev_dd,
             LAG(discharged_by_transfer) OVER w AS prev_tr
      FROM all_admissions
      WINDOW w AS (PARTITION BY patient_id ORDER BY discharge_day, record_id)
    )
    -- Same interval-OVERLAP test as interval_rule(): the possible admission
    -- interval must reach the transfer window from BOTH ends. Testing only the
    -- earliest end counts overlapping stays as possible continuations.
    SELECT c.urgent_admission,
           COUNT(*) AS episodes,
           SUM(CASE WHEN o.prev_tr AND o.pseudo_admission_day >= o.prev_dd
                AND (o.los_unbounded
                OR o.pseudo_admission_day - (o.los_max - o.length_of_stay_group)
                   <= o.prev_dd + 1) THEN 1 ELSE 0 END) AS possible_continuation,
           ROUND(100.0*AVG(CASE WHEN o.prev_tr AND o.pseudo_admission_day >= o.prev_dd
                AND (o.los_unbounded
                OR o.pseudo_admission_day - (o.los_max - o.length_of_stay_group)
                   <= o.prev_dd + 1) THEN 1.0 ELSE 0 END), 1) AS pct
    FROM cohort c JOIN ordered o ON o.record_id = c.first_record_id
    WHERE c.discharged_home GROUP BY 1
""").df()
contam.to_csv("output/tables/transfer_contamination.csv", index=False)
print("Primary-cohort episodes that could be unmerged transfer continuations:")
print(contam.to_string(index=False))
print("""
This contamination is DIFFERENTIAL with respect to the exposure, so it is a
limitation of the urgent-vs-planned contrast, not just of the denominator.
""")

# restore the primary rule before saving anything
con.execute(SQL.format(**PRIMARY_RULE))

print("\nSaved cohort.parquet, episode_level.parquet, analysis_all_admissions.parquet")

con.close()
