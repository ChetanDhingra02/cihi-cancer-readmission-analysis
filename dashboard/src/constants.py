"""Labels, palette, terminology and the explicit allow-list of publishable tables.

Nothing in this module reads data or draws anything. It exists so that wording
and ordering are defined once.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Project identity
# --------------------------------------------------------------------------

APP_TITLE = "Urgent readmission and mortality after cancer hospitalisation"
APP_SHORT_TITLE = "Cancer episodes, CIHI DAD"
APP_TAGLINE = (
    "A retrospective cohort study of transfer-linked hospital episodes of care, "
    "built from the CIHI Discharge Abstract Database Research Analytic File."
)

DATA_SOURCE_SHORT = "CIHI DAD Research Analytic File (clinical sample)"
FISCAL_YEARS = "FY2021-22 to FY2023-24"
GEOGRAPHIC_COVERAGE = "Canadian provinces and territories excluding Quebec"
SAMPLE_DESCRIPTION = "approximately a 10% research sample"

SAMPLE_CAVEAT = (
    "Counts refer to the CIHI RAF sample and are not national totals."
)

# --------------------------------------------------------------------------
# Palette - the chart half of the design system in assets/styles.css.
# Names are unchanged so that no chart has to be rewritten; only the values
# move, which is a presentation change.
# --------------------------------------------------------------------------

INK = "#0e1526"          # primary text
MUTED = "#4b566b"        # secondary text
FAINT = "#8792a6"        # tertiary text, axis labels
RULE = "#e8ebf1"         # hairlines, gridlines
PANEL = "#f6f7fa"        # rare fills

BLUE = "#4c7bf4"         # primary series
BLUE_DEEP = "#1f3a8f"    # emphasis within the primary series
BLUE_LIGHT = "#c5d3fa"   # de-emphasised primary series
RED = "#f0674a"          # outcome / adverse series (coral)
AMBER = "#f2a93b"        # attention, sensitivity analyses
GREY = "#b4bdcc"         # comparison series (cool grey)
GREEN = "#16a394"        # reference / ideal lines (teal)

SEQUENCE = [BLUE, RED, AMBER, GREY, GREEN, BLUE_LIGHT]

FONT_STACK = (
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
)

PLOTLY_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": False,
    "staticPlot": False,
    "responsive": True,
}

# --------------------------------------------------------------------------
# Terminology
# --------------------------------------------------------------------------

TERM_EPISODE = "approximated episode of care"
TERM_URGENT = "urgent/emergent admission"
TERM_ED = "entered through an emergency department"
TERM_TYPE2 = "condition coded as arising after admission"

GLOSSARY: list[tuple[str, str]] = [
    (
        "Approximated episode of care",
        "One or more discharge abstracts linked together when the coding indicates "
        "a transfer between facilities. After the term is defined it is shortened "
        "to episode. These are not CIHI's official episodes of care.",
    ),
    (
        "Urgent/emergent admission",
        "Admission category ADM_CAT = U on the first abstract of the episode. "
        "This is an administrative category recorded by the submitting facility.",
    ),
    (
        "Entered through an emergency department",
        "Entry code ENT_CODE = E. Related to the admission category but a distinct "
        "field: an episode can be urgent without an ED entry code and vice versa.",
    ),
    (
        "Invasive malignancy",
        "ICD-10-CA codes C00-C97. Carcinoma in situ (D00-D09) and neoplasms of "
        "uncertain behaviour (D45-D47) are outside the cohort.",
    ),
    (
        "Condition coded as arising after admission",
        "Diagnosis type 2. It records when a condition was coded, not whether it "
        "was preventable, expected, or caused by care.",
    ),
    (
        "REL_ADAY",
        "A derived pseudo-admission day equal to REL_DDAY minus the floor of the "
        "length-of-stay band. It is never earlier than the true admission day, and "
        "for the 10-or-more-day band the error has no upper bound.",
    ),
    (
        "Urgent 30-day readmission",
        "A project-defined outcome: a later episode with ADM_CAT = U beginning "
        "within 30 days of discharge home. It is not CIHI's official 30-day "
        "readmission indicator.",
    ),
]

# --------------------------------------------------------------------------
# Ordering
# --------------------------------------------------------------------------

CANCER_SITE_ORDER = [
    "Digestive",
    "Secondary (spread)",
    "Haematologic",
    "Respiratory and intrathoracic",
    "Urinary",
    "Female reproductive",
    "Male reproductive",
    "Breast",
    "Thyroid and endocrine",
    "Eye, brain and nervous system",
    "Head and neck",
    "Skin",
    "Soft tissue",
    "Bone and cartilage",
    "Ill-defined site",
    "Unknown primary",
]

PROVINCE_ORDER = [
    "Ontario",
    "British Columbia",
    "Alberta",
    "Nova Scotia",
    "Saskatchewan",
    "Manitoba",
    "New Brunswick",
    "Newfoundland and Labrador",
    "Prince Edward Island",
    "Territories",
]

# Display emphasis only. This is NOT a disclosure threshold: suppression is
# carried in the source tables and is never recomputed here.
SMALL_GROUP_DISPLAY_N = 500

TRANSFER_RULE_ORDER = [
    "Same-day transfer",
    "Same or next day (primary)",
    "Within two days",
    "Interval-aware (earliest possible admission)",
    "Interval-aware, 10+ band capped at 90 days",
    "Transfer coding ignored",
]

PRIMARY_TRANSFER_RULE = "Same or next day (primary)"

# --------------------------------------------------------------------------
# The allow-list
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TableSpec:
    """One aggregate table that is cleared for publication."""

    filename: str
    description: str
    required_columns: tuple[str, ...] = field(default=())
    allow_empty: bool = False


ALLOWED_TABLES: dict[str, TableSpec] = {
    "key_numbers": TableSpec(
        "key_numbers.csv",
        "Every reported figure, generated by the analysis pipeline.",
        ("name", "value", "description"),
    ),
    "study_flow": TableSpec(
        "study_flow.csv",
        "Cohort construction, abstracts through to the primary cohort.",
        ("step", "n", "note"),
    ),
    "table1_characteristics": TableSpec(
        "table1_characteristics.csv",
        "Study population, readmitted against not readmitted.",
        ("characteristic", "overall_n", "overall_pct",
         "not_readmitted_pct", "readmitted_pct", "difference"),
    ),
    "q1_rate_by_cancer_site": TableSpec(
        "q1_rate_by_cancer_site.csv",
        "Urgent 30-day readmission by cancer site, with intervals.",
        ("cancer_site", "episodes", "patients", "readmitted",
         "percent", "ci_low", "ci_high"),
    ),
    "q1_rate_by_province": TableSpec(
        "q1_rate_by_province.csv",
        "Urgent 30-day readmission by province, with intervals.",
        ("province", "episodes", "patients", "readmitted",
         "percent", "ci_low", "ci_high"),
    ),
    "q1_adjusted_risk": TableSpec(
        "q1_adjusted_risk.csv",
        "Adjusted readmission risk under urgent and planned index admission.",
        ("adjusted_readmission_if_all_urgent_pct", "urgent_ci",
         "adjusted_readmission_if_all_planned_pct", "planned_ci",
         "risk_difference_pct_points", "risk_difference_ci",
         "risk_ratio", "risk_ratio_ci", "odds_ratio", "model"),
    ),
    "q1_regression": TableSpec(
        "q1_regression.csv",
        "Readmission logistic regression coefficients.",
        ("model", "factor", "odds_ratio", "ci_low", "ci_high", "p_value"),
    ),
    "q1_sensitivity": TableSpec(
        "q1_sensitivity.csv",
        "Readmission rate under alternative cohort and outcome definitions.",
        ("analysis", "episodes", "urgent_readmit_pct"),
    ),
    "q1_model_performance": TableSpec(
        "q1_model_performance.csv",
        "Prediction model discrimination and calibration on the held-out test set.",
        ("model", "auc", "auc_ci_low", "auc_ci_high", "pr_auc", "brier",
         "calibration_slope", "calibration_intercept", "outcome_prevalence"),
    ),
    "q1_calibration": TableSpec(
        "q1_calibration.csv",
        "Predicted against observed readmission by risk tenth.",
        ("group", "episodes", "predicted_pct", "actual_pct"),
    ),
    "q1_thresholds": TableSpec(
        "q1_thresholds.csv",
        "Operating characteristics at selected probability thresholds.",
        ("threshold", "flagged_pct", "sensitivity", "specificity", "ppv", "npv"),
    ),
    "q1_geographic_holdout": TableSpec(
        "q1_geographic_holdout.csv",
        "Alberta geographic holdout, patient-separated.",
        ("trained_on", "tested_on", "n_test", "auc",
         "auc_ci_low", "auc_ci_high", "calibration_slope",
         "calibration_intercept"),
    ),
    "q1_feature_importance": TableSpec(
        "q1_feature_importance.csv",
        "Random forest feature importance for the readmission model.",
        ("feature", "importance"),
    ),
    "q1_los_assumption_sensitivity": TableSpec(
        "q1_los_assumption_sensitivity.csv",
        "Readmission rate under alternative length-of-stay assumptions.",
        ("stay_length_assumption", "urgent_readmit_pct"),
    ),
    "q1_planned_returns": TableSpec(
        "q1_planned_returns.csv",
        "Planned 30-day returns and the chemotherapy share.",
        ("planned_returns", "with_chemo_code", "pct_with_chemo_code"),
    ),
    "readmission_certainty": TableSpec(
        "readmission_certainty.csv",
        "Whether readmission timing can be resolved from derived admission days.",
        ("certainty", "episodes", "pct"),
    ),
    "cohort_definition_sensitivity": TableSpec(
        "cohort_definition_sensitivity.csv",
        "Outcome rates under two cohort definitions.",
        ("cohort_definition", "episodes", "any_return_pct",
         "urgent_pct", "ed_entry_pct"),
    ),
    "q2_adjusted_risk": TableSpec(
        "q2_adjusted_risk.csv",
        "Adjusted in-hospital mortality under urgent and planned admission.",
        ("adjusted_risk_if_all_urgent_pct", "urgent_ci",
         "adjusted_risk_if_all_planned_pct", "planned_ci",
         "risk_difference_pct_points", "risk_difference_ci",
         "risk_ratio", "risk_ratio_ci", "odds_ratio"),
    ),
    "q2_urgent_by_site": TableSpec(
        "q2_urgent_by_site.csv",
        "Urgent share, ED entry and mortality by cancer site.",
        ("cancer_site", "episodes", "urgent", "via_ed", "died",
         "pct_urgent", "pct_via_ed", "pct_died"),
    ),
    "q2_urgent_by_province": TableSpec(
        "q2_urgent_by_province.csv",
        "Urgent admission share by province.",
        ("province", "episodes", "urgent", "pct_urgent"),
    ),
    "q2_death_regression": TableSpec(
        "q2_death_regression.csv",
        "In-hospital mortality logistic regression coefficients.",
        ("model", "factor", "odds_ratio", "ci_low", "ci_high", "p_value"),
    ),
    "q3_outcomes": TableSpec(
        "q3_outcomes.csv",
        "Outcomes by whether a post-admission condition was coded.",
        ("post_admission_condition", "episodes", "pct_died",
         "pct_intensive_care", "pct_long_stay"),
    ),
    "q3_by_group": TableSpec(
        "q3_by_group.csv",
        "Share of episodes with a post-admission condition, by group.",
        ("group", "episodes", "pct_with_post_admission_condition"),
    ),
    "q3_common_conditions": TableSpec(
        "q3_common_conditions.csv",
        "Most frequently coded post-admission conditions.",
        ("code", "n_episodes", "n_occurrences", "condition", "pct_of_episodes"),
    ),
    "q3_death_regression": TableSpec(
        "q3_death_regression.csv",
        "Post-admission condition and mortality, regression coefficients.",
        ("model", "factor", "odds_ratio", "ci_low", "ci_high"),
    ),
    "q4_quarterly_trend": TableSpec(
        "q4_quarterly_trend.csv",
        "Quarterly in-hospital mortality and measured characteristics.",
        ("quarter", "episodes", "deaths", "pct_died", "pct_urgent",
         "pct_spread", "pct_aged_80_plus", "pct_intensive_care",
         "pct_palliative", "pct_episode_long_stay"),
    ),
    "q4_trend_models": TableSpec(
        "q4_trend_models.csv",
        "Odds ratio per quarter under three model specifications.",
        ("model", "odds_ratio_per_quarter", "ci_low", "ci_high", "p_value"),
    ),
    "q4_anchor_comparison": TableSpec(
        "q4_anchor_comparison.csv",
        "Discharge-anchored against admission-anchored quarters.",
        ("quarter", "discharge_anchored_pct", "admission_anchored_pct"),
    ),
    "q4_linearity_test": TableSpec(
        "q4_linearity_test.csv",
        "Likelihood-ratio test, linear trend against free per-quarter effects.",
        ("test", "lr_chi2", "df", "p_value"),
    ),
    "transfer_rule_sensitivity": TableSpec(
        "transfer_rule_sensitivity.csv",
        "Cohort size and readmission rate under alternative transfer rules.",
        ("transfer_rule", "kind", "episodes_total", "primary_cohort_n",
         "urgent_readmissions", "urgent_readmit_pct"),
    ),
    "rule_robustness": TableSpec(
        "rule_robustness.csv",
        "Adjusted estimates refitted on each transfer rule's cohort.",
        ("transfer_rule", "cohort_n", "readmit_pct", "q1_risk_ratio",
         "q1_risk_difference_pts", "q2_risk_ratio", "q2_risk_difference_pts"),
    ),
    "transfer_merge_diagnostic": TableSpec(
        "transfer_merge_diagnostic.csv",
        "Merge rate by the length of the receiving stay.",
        ("receiving_stay_band", "abstracts_after_a_transfer",
         "merged", "pct_merged"),
    ),
    "transfer_contamination": TableSpec(
        "transfer_contamination.csv",
        "Possible unmerged transfer continuations, by exposure.",
        ("urgent_admission", "episodes", "possible_continuation", "pct"),
    ),
    "small_cell_report": TableSpec(
        "small_cell_report.csv",
        "Rows withheld from the released tables and why.",
        ("table", "row", "reason"),
        allow_empty=True,
    ),
    "validation_report": TableSpec(
        "validation_report.csv",
        "Parse validation against the SPSS version of the file.",
        ("variable", "n_rows", "n_matching", "pct_matching", "result"),
    ),
    "document_verification": TableSpec(
        "document_verification.csv",
        "Numbers asserted in the generated documents that could not be traced.",
        ("document", "value", "context"),
        allow_empty=True,
    ),
    "cancer_scope": TableSpec(
        "cancer_scope.csv",
        "Which neoplasm code ranges are in the cohort.",
        ("code_range", "description", "in_cohort", "reason"),
    ),
    "cancer_site_mapping": TableSpec(
        "cancer_site_mapping.csv",
        "Documented ICD-10-CA three-character code to cancer site mapping.",
        ("code_3char", "cancer_site", "is_primary_site", "site_rank", "note"),
    ),
}

# Files that must never be read by this application, recorded so the Methods
# page can state the rule rather than merely imply it.
NEVER_PUBLISHED = [
    "record-level abstracts (clin_sample_ascii.dat, clin_sample_spss.sav)",
    "parsed record-level Parquet (dad_parsed, cohort, episode_level, "
    "analysis_all_admissions)",
    "the analysis database (dad.duckdb)",
    "unsuppressed internal tables (output/tables/internal/)",
    "the CIHI record layout, documentation PDFs and manuals",
]
