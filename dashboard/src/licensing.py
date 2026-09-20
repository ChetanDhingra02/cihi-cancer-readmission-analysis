"""Attribution, data-access and release wording.

The accreditation text below is reproduced exactly as required. It is not
rewritten, shortened or restyled anywhere in the application.
"""

from __future__ import annotations

CIHI_ATTRIBUTION = (
    "Parts of this material are based on the Canadian Institute for Health "
    "Information Discharge Abstract Database Research Analytic Files (sampled "
    "from fiscal years 2021-2022, 2022-2023 and 2023-2024). However the "
    "analysis, conclusions, opinions and statements expressed herein are those "
    "of the author and not those of the Canadian Institute for Health "
    "Information."
)

DATA_SOURCE = (
    "Canadian Institute for Health Information, Discharge Abstract Database, "
    "Research Analytic File, clinical research sample, FY2021-22 to FY2023-24. "
    "Coverage is Canadian provinces and territories excluding Quebec, at "
    "approximately a 10% sample of discharge abstracts."
)

DATA_ACCESS = (
    "The file was accessed through the University of Alberta's institutional "
    "access under Statistics Canada's Data Liberation Initiative arrangement. "
    "Eligible researchers must obtain the data independently through their own "
    "participating institution's DLI contact or data librarian. No credentials, "
    "tokens or session information are held by this application, which has no "
    "route to the licensed file."
)

WHAT_IT_IS_NOT = [
    "not open data",
    "not Alberta Health Services data",
    "not Alberta Health data",
    "not Cancer Care Alberta production data",
    "not health-system production data",
]

PUBLIC_RELEASE = (
    "Only derived aggregate tables are deployed with this application, from an "
    "explicit allow-list rather than a directory scan. No record-level file, "
    "analysis database, internal full-precision table or CIHI documentation is "
    "part of the repository, and none is reachable from the running app."
)

SUPPRESSION = (
    "Suppression is carried in the source tables and is never reversed here. "
    "A withheld value is shown as Suppressed, is left out of every chart, and "
    "is never recovered by subtracting the visible rows from a total. The rule "
    "that produced those withheld cells is the project's own conservative "
    "safeguard: the CIHI and DLI Terms available to this project state no "
    "numeric threshold, so nothing here should be read as a CIHI-mandated "
    "minimum cell size. The application adds no threshold of its own — the "
    "cleared tables govern — and any change to the rule should come from the "
    "institutional DLI contact."
)

NO_INTERACTIVE_REAGGREGATION = (
    "Filtering is limited to switching between tables that were aggregated and "
    "cleared in advance. There is no cross-tabulation of province by site by "
    "age by quarter, because combining otherwise safe aggregates can produce a "
    "cell that no one cleared. No record-level data is queried at any point."
)

NOT_A_CLINICAL_TOOL = (
    "This is a research-results dashboard, not clinical decision support. The "
    "prediction model has not undergone prospective clinical validation, no "
    "individual patient characteristics can be entered, and no personalised "
    "risk is produced."
)

PROJECT_DEFINED_OUTCOME = (
    "The readmission outcome is project-defined. It is not CIHI's official "
    "30-day readmission indicator, which uses its own episode construction, "
    "denominators and exclusions."
)

LIMITATIONS: list[tuple[str, str]] = [
    ("Inpatient care only",
     "No outpatient care, and no emergency department visit that did not end "
     "in an admission."),
    ("Deaths after discharge are unobserved",
     "Mortality is in-hospital only, so death after discharge is an unobserved "
     "competing event for readmission."),
    ("No cancer stage",
     "Stage, exact diagnosis date and performance status are not recorded in "
     "the DAD, and severity is therefore only partly captured."),
    ("Quebec is absent",
     "The RAF does not include Quebec, so 'provinces' here means the rest of "
     "Canada."),
    ("A research sample, not a census",
     "Approximately 10% of abstracts. Rates and percentages describe this "
     "research sample; sample counts are not Canadian national totals."),
    ("Banded age and length of stay",
     "Both arrive banded, so models use bands rather than continuous values."),
    ("REL_ADAY is derived",
     "The pseudo-admission day equals the discharge day minus the floor of the "
     "stay band. It is never earlier than the true admission day, and for the "
     "10-or-more-day band the error has no upper limit."),
    ("Readmission timing is not always resolvable",
     "A material share of candidate readmissions cannot be proven to fall "
     "inside or outside the 30-day window. The share is reported alongside "
     "the estimate."),
    ("Episodes are approximations",
     "Transfer-linked episodes approximate episodes of care using the fields "
     "available in the RAF. They are not CIHI's official episode methodology."),
    ("Transfer-linking error is differential",
     "Merging fails more often for long receiving stays, and long stays are "
     "not independent of severity, so the residual error is correlated with "
     "the exposure."),
    ("Patients can contribute several episodes",
     "Episodes repeat within patients. Intervals use a patient-cluster "
     "bootstrap, but the unit of analysis is the episode."),
    ("Observational throughout",
     "Every estimate is an association under a specified adjustment set. None "
     "is a causal effect."),
]

CAUSAL_LANGUAGE_NOTE = (
    "Estimates are adjusted associations. Urgent admission is a marker of how "
    "the episode began, not an intervention that was assigned, and the "
    "unmeasured severity that sends someone in urgently is also plausibly "
    "related to the outcome."
)
