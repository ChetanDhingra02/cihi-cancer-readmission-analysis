# Urgent readmission and mortality after cancer hospitalisation — dashboard

A Streamlit research dashboard for a retrospective cohort study of transfer-linked
hospital episodes of care for people with invasive cancer, built from the CIHI
Discharge Abstract Database Research Analytic File (FY2021-22 to FY2023-24).

**Raw CIHI data are not distributed with this repository.** This repository
contains application code and derived, disclosure-checked aggregate tables only.
**Users must obtain the source data independently through an eligible
institutional DLI arrangement.**

---

## Overview

The analysis pipeline that produces the underlying results lives in a separate
repository. This repository is the presentation layer: it reads a fixed
allow-list of cleared aggregate tables and rebuilds every figure from them.
Nothing is trained, recomputed from record-level data, or typed in by hand.

The dashboard is a research-communication and portfolio artefact. It is not
clinical decision support, and it deliberately offers no way to enter individual
patient characteristics and receive a personalised risk.

## Research questions

1. **Readmission.** After an episode of cancer care that ends in a discharge
   home, how often does an urgent/emergent readmission follow within 30 days,
   and how does that risk differ by how the index episode began?
2. **Mortality.** Is an urgent/emergent admission associated with higher
   in-hospital mortality once baseline characteristics are adjusted for?
3. **Post-admission conditions.** How often is a condition coded as arising
   after admission (diagnosis type 2), and what goes with it?
4. **Trend.** Did in-hospital mortality among cancer episodes change across the
   twelve quarters, and do the measured characteristics explain the change?

A prediction model for question 1 is reported separately, with calibration,
operating points and a geographic holdout.

## Data source

Canadian Institute for Health Information, Discharge Abstract Database, Research
Analytic File, clinical research sample, sampled from fiscal years 2021-2022,
2022-2023 and 2023-2024.

- Coverage: Canadian provinces and territories **excluding Quebec**.
- Sampling: approximately a 10% research sample of discharge abstracts. Rates
  and percentages describe this research sample; sample counts are not Canadian
  national totals.
- Unit of analysis: the approximated episode of care — one or more abstracts
  joined where the coding indicates a transfer between facilities.

This is **not** open data, **not** Alberta Health Services data, **not** Alberta
Health data, **not** Cancer Care Alberta production data, and **not**
health-system production data.

## Access and licensing

The file was accessed through the University of Alberta's institutional access
under Statistics Canada's Data Liberation Initiative arrangement. The RAF is
licensed, not public.

### How an eligible researcher obtains the data

1. Confirm that your institution participates in Statistics Canada's Data
   Liberation Initiative.
2. Contact your institution's DLI contact or data librarian and request the CIHI
   DAD Research Analytic File for the fiscal years you need.
3. Obtain the file under your own institution's Terms. It cannot be
   redistributed by this project, and no part of it is reachable from this
   repository or the deployed application.
4. Confirm with the same contact before publishing any derived output of your
   own.

No credentials of any kind belong in this repository: no institutional login, no
CCID, no password, no access token, no cookies and no library session
information. The application does not access the restricted data at all, so
deployment secrets should contain no data-access credentials.

## Required CIHI accreditation

> Parts of this material are based on the Canadian Institute for Health
> Information Discharge Abstract Database Research Analytic Files (sampled from
> fiscal years 2021-2022, 2022-2023 and 2023-2024). However the analysis,
> conclusions, opinions and statements expressed herein are those of the author
> and not those of the Canadian Institute for Health Information.

This wording is reproduced without modification here, on the dashboard's
Methods, data and licensing page, and in the footer of every page. The CIHI logo
is not used.

## Methodology overview

- **Episodes, not abstracts.** A transfer between facilities generates a second
  abstract. Counting it as a readmission would split one continuous episode in
  two. Abstracts are joined when the coding indicates a transfer and the timing
  is compatible.
- **Cohort.** Episodes with an invasive malignancy (ICD-10-CA C00-C97). In-situ
  (D00-D09) and uncertain-behaviour (D45-D47) neoplasms are outside the cohort.
- **Primary readmission cohort.** Episodes ending in a live discharge home with
  at least 30 days of potential follow-up remaining.
- **Baseline variables from the first abstract only.** A condition arising at one
  facility is coded as present on admission at the next, so episode-wide
  aggregation would contaminate the baseline.
- **Comorbidities from diagnosis type 1 only.** Type 2 conditions arose after
  admission; including them would leak the outcome into the predictors.
- **Baseline-only models are primary.** Palliative care, post-admission
  conditions, special care, length of stay, procedures and multi-facility care
  all follow the exposure. Models including them are reported as descriptive,
  answering a different question rather than a better-adjusted version of the
  same one.
- **Discharge-anchored time periods.** The discharge day is recorded exactly; the
  derived admission day is least reliable for long stays, which is where death is
  most likely.
- **Patient-cluster bootstrap intervals**, because episodes repeat within
  patients.
- **Train and test split by patient**, so no individual appears on both sides.

## Project flow

```
CIHI DAD RAF (licensed, obtained separately)
    -> analysis pipeline (separate repository, not deployed)
         parse -> validate -> episode construction -> cohort
         -> Q1..Q4 analyses -> sensitivity and robustness
         -> key_numbers.csv + aggregate tables
    -> disclosure check: suppression applied, small_cell_report.csv written,
       full-precision copies quarantined in output/tables/internal/
    -> cleared aggregate tables copied BY NAME into app_data/
    -> this Streamlit application
```

The copy step is deliberate and manual. The application never points at the
analysis `output/` directory.

## Repository structure

```
app.py                     navigation only
pages/
    01_Overview.py
    02_Readmission.py
    03_Mortality.py
    04_Post_Admission_Conditions.py
    05_Mortality_Trends.py
    06_Prediction_Model.py
    07_Robustness.py
    08_Methods_and_Data.py
assets/
    styles.css             the design system: tokens, cards, motion, responsive
    motion.js              scroll-triggered chart reveal and card highlight (presentation only)
src/
    constants.py           chart palette, ordering, terminology, the allow-list
    data_loader.py         allow-listed loading, schema validation, caching
    charts.py              every figure; returns Plotly objects, calls no st.*
    metrics.py             lookups into key_numbers.csv
    formatting.py          numbers, intervals, model-label tidying
    ui.py                  hero, KPI cards, finding cards, chart cards, callouts
    art.py                 the animated scene beside each page header (decorative, no data)
    licensing.py           attribution, access and release wording
app_data/                  cleared aggregate tables only
tools/
    check_release.py       pre-deployment repository check
    smoke_test.py          runs every page through Streamlit's test harness
.streamlit/config.toml
requirements.txt
```

Everything in `app_data/` is an aggregate table that has been through the
project's disclosure check. No record-level file, analysis database, internal
full-precision table, record layout or CIHI documentation is present.

## Navigating the dashboard

A floating top navigation bar links the eight pages, grouped as **Findings**
(Overview, 30-day readmission, Urgent admission and mortality, Post-admission conditions,
Mortality over time, Prediction model) and **Method** (Robustness and
uncertainty, Methods, data and licensing). A recruiter-facing reading order is
the order they appear: the Overview states the problem, the cohort and the
headline findings; the four question pages give the evidence; the prediction
page reports what can and cannot be predicted; and the two method pages cover
how much of it survives changing the assumptions, and under what licence the
data was used.

## Design and presentation

The interface is a small design system rather than default Streamlit. Tokens
(colour, radius, spacing, shadow, motion) live in `assets/styles.css`; the
components that use them live in `src/ui.py`; the chart half of the same palette
lives in `src/constants.py` and is applied centrally in `src/charts.py`.

Three conventions are worth knowing before editing it:

- Card and navigation styling attaches to `st.container(key=...)`, which
  Streamlit renders as a `st-key-<key>` class. KPI and finding grids are emitted
  as one block of HTML using CSS Grid, so every card in a row has the same width
  and height whatever its text length.
- The overrides for Streamlit's own widgets (tabs, radio pills, select boxes,
  expanders, data tables) do target Streamlit's internal markup. They were
  written and checked against Streamlit 1.64; `requirements.txt` keeps Streamlit
  within the 1.64 minor release so those selectors do not silently change under the UI.
  If that bound is intentionally raised, check those widgets first (the radio
  pills on the Prediction page are the most sensitive).
- Motion is layered, and all of it is presentation only. Blocks rise into view
  as they are reached, and the headline figures count up to the value the page
  already prints (they always end on that exact text). Tiles and cards tilt
  toward the cursor with a moving highlight, the nav bar's hover pill glides
  between links, presses ripple outward, the 100-dot pictures swell under the
  cursor, and a small rail of section dots follows long pages. `src/art.py`
  draws the animated scene beside each page header; those are decorative and
  carry no data. Each chart is drawn as it scrolls into view: axes fade in, bars
  grow, dots pop, lines are drawn and labels arrive last, following the
  direction the data is read in. The behaviour is `assets/motion.js`, loaded
  through `st.html(..., unsafe_allow_javascript=True)`, with a zero-height
  component as the fallback on Streamlit releases that lack the option. It
  reads no data and changes no values; if it cannot run, everything shows as
  normal. Scrolling gets a little polish too: a mouse wheel glides with gentle
  inertia (the `SMOOTH_WHEEL` constant in the scrolling section of `motion.js`
  turns this off; trackpads, touch, keyboard scrolling, pinch-zoom and any inner
  scroller such as a table are always left to the browser), the nav bar firms up
  once the page moves, the header art drifts slightly slower than the page, and
  the scrollbar is slimmed. All of it is disabled under
  `prefers-reduced-motion: reduce`, and printing shows every block and chart in
  full.
- On screens 1180px and wider, each chart card and the paragraph that explains
  it sit side by side: the page's main block becomes a 12-column grid and CSS
  (using `:has()`) places a chart in eight columns with its reading beside it.
  Below that width the page is a single column. No page file arranges this, so
  it depends on Streamlit's current markup; check it after upgrading.
- The chart reveal targets Plotly's own SVG structure (`.barlayer`,
  `.scatterlayer`, `.errorbar` and so on) and reveals marks with `clip-path`
  rather than `transform`, because Plotly positions markers with transform
  attributes. It was checked against the Plotly bundled with Streamlit 1.64; if a
  future Plotly renames those layers the worst case is that some marks appear
  without animating.

Presentation is deliberately separate from the analysis: no file under `src/`
other than `ui.py`, `art.py` and the palette and chart-display settings in
`constants.py` has any say in how the app looks, and none of those reads, filters or computes
anything.

## Running the app

macOS and Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell refuses to run the activation script, allow signed local scripts
for the current user once with
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use
`.\.venv\Scripts\activate.bat` from `cmd.exe` instead.

The deployed data are small and no model is fitted at runtime, so start-up is
fast. Four packages are required: streamlit, pandas, plotly and numpy. No
TensorFlow, no PyTorch, no scikit-learn — the dashboard displays model results
that were generated by the analysis pipeline.

To refresh the dashboard after re-running the analysis, copy the regenerated
tables into `app_data/` by name. The loader keys its cache on file modification
time, so the app picks the new values up without a restart.

Before deploying:

```bash
python tools/check_release.py     # allow-list and restricted-file check
python tools/smoke_test.py        # every page renders without error
```

## Main results are generated, not typed

No result is hard-coded in the application. Headline figures are read from
`app_data/key_numbers.csv` through `metrics.get_key_number()`, and chart values
are read from the corresponding aggregate tables. A missing or renamed entry
raises with the name of the entry and the closest matches rather than falling
back to a default, so a stale number cannot survive a re-run of the analysis.

This matters in particular for model performance. The patient-level train/test
split was regenerated after a reproducibility correction, and no AUC, risk ratio,
rate or count appears as a literal anywhere in `app.py`, `pages/` or `src/`. The
figures shown are whatever the current `key_numbers.csv` contains.

Numbers are deliberately **not** reproduced in this README for the same reason:
a README is not regenerated when the pipeline runs, and duplicated figures drift.
The dashboard, and the analysis repository's own generated Results section, are
the places where results appear.

## Reproducibility notes

- The analysis pipeline validates its fixed-width parse field by field against
  the SPSS version of the same file, including deep diagnosis slots, and fails
  the build on any mismatch. The result is reported on the Methods page.
- Every reported figure is collected into `key_numbers.csv` by the pipeline, and
  the generated documents are read back and checked against it; untraceable
  numbers fail that build. `document_verification.csv` records what failed.
- This dashboard adds a second layer: schema validation on load, and a lookup
  that raises rather than defaulting.

## Caveats that belong next to the results

### Episode linkage

Transfer-linked episodes approximate episodes of care from the fields the RAF
provides. They are **not** CIHI's official episode methodology.

`REL_ADAY` is derived, not observed: it equals `REL_DDAY` minus the floor of the
length-of-stay band. The derived admission day is therefore never earlier than
the true one, and for the "10 or more days" band the error has no upper limit.
Merging consequently fails more often for long receiving stays, and long stays
are not independent of severity, so the residual error is **differential with
respect to the exposure**.

The dashboard reports what this costs. The adjusted estimates were refitted from
scratch on each plausible transfer rule's cohort. The readmission risk ratio
moves by less than the width of its own confidence interval. The mortality risk
ratio does not: its spread across defensible episode definitions is comparable to
its entire confidence interval, which means the interval alone understates how
loosely that number is pinned down. That comparison is on the Robustness page and
is stated again on the mortality page.

### Readmission definition

The outcome is **project-defined**: a later episode with admission category
`ADM_CAT = U` beginning within 30 days of a discharge home. It is **not CIHI's
official 30-day readmission indicator**, which has its own episode construction,
denominators and exclusions.

`ADM_CAT = U` (urgent/emergent) and `ENT_CODE = E` (entered through an emergency
department) are related but separate fields, and the dashboard reports them
separately throughout.

Because the admission day is derived, a candidate readmission has a possible
interval rather than a date. Three distinct quantities are reported side by side
— the point estimate, the share provable on timing, and the complete case — and
they are not bounds on one another.

### Prediction model evaluation

The readmission model is an **end-of-index-stay (discharge-time) research
model**, not an admission-time one. Alongside variables recorded at or before
admission, its predictors include what the index stay recorded: special care unit
stay, palliative care coding, conditions coded as arising after admission,
procedures, multi-facility care and length of stay. The earliest point at which
it could be calculated is discharge, and its reported performance is what is
available at that point. A model restricted to admission-time information would
be a different model and is not reported.

Reported: ROC-AUC with a 95% confidence interval, PR-AUC against test-set outcome
prevalence, Brier score, calibration slope and intercept, a calibration figure
rebuilt from risk-group aggregates with an ideal-calibration reference line, and
operating characteristics at four thresholds (flagged share, sensitivity,
specificity, PPV, NPV). The unit flagged at a threshold is the **episode**, not
the person: one patient can contribute several episodes.

A random forest appears only as a comparator. `q1_feature_importance.csv` is
**random forest feature importance** — a ranking of contribution to splits in the
fitted forest. It is not an adjusted association, carries no direction, is biased
towards high-cardinality and correlated predictors, and is not an effect
estimate.

The model has **not** undergone prospective clinical validation and is not
presented as a clinical calculator. Discrimination at this level separates groups
usefully and individuals poorly.

### Alberta geographic holdout

Testing on Alberta episodes is described as an **Alberta geographic holdout**, or
**internal-external geographic validation**. It is **not external validation**:
Alberta records come from the same overarching CIHI RAF source, the same abstract
structure and the same coding standards as the training data.

The split is three-way, because patients cross provinces. Any patient with
Alberta care is **excluded from training completely**. Of that patient's
episodes, **only the Alberta ones form the holdout test set**, and their episodes
in other provinces are **dropped** rather than used on either side. The patient's
episodes do not all move to the holdout.

## Limitations

- Inpatient admissions only; no outpatient care, and no ED visit that did not end
  in an admission.
- Deaths after discharge are unobserved, so post-discharge death is an unobserved
  competing event for readmission.
- No cancer stage, no exact cancer diagnosis date, no performance status.
- Quebec is absent.
- Approximately a 10% research sample. Rates and percentages describe this
  research sample; sample counts are not Canadian national totals.
- Age is banded; length of stay is banded.
- `REL_ADAY` is a derived pseudo-admission day, not an exact admission date, and
  timing uncertainty affects the readmission definition.
- Transfer-linked episodes approximate episodes of care, and the linking error is
  differential for long stays.
- One patient can contribute several episodes.
- All analyses are observational. Associations are not causal effects.

## Disclosure and public-release safeguards

The institutional DLI confirmation recorded in the project documentation permits
publishing derived aggregate tables and figures under the supplied Terms.
Disclosure safeguards still apply, and this repository implements them as
follows.

1. **Explicit allow-list.** `src/constants.ALLOWED_TABLES` names every file the
   application may open, together with the columns each must contain. The data
   directory is never scanned, so a file dropped into `app_data/` is unreachable
   from every page. The Methods page lists the inventory and warns about any
   unlisted file it finds.
2. **Aggregate tables only.** The application never reads
   `clin_sample_ascii.dat`, `clin_sample_spss.sav`, any raw CIHI file,
   `dad_parsed.parquet`, `cohort.parquet`, `episode_level.parquet`,
   `analysis_all_admissions.parquet`, `dad.duckdb`, any record-level Parquet,
   internal unsuppressed tables, `output/tables/internal/`, the derived
   `layout.csv`, CIHI documentation PDFs, CIHI layout spreadsheets or CIHI
   manuals.
3. **Suppression is carried, never reversed.** A value withheld in the source
   table is displayed as "Suppressed", is excluded from every chart, and is never
   recovered by subtracting visible rows from a total. `small_cell_report.csv`
   lists what was withheld and why, and the dashboard shows it. The numeric
   cell-size rule that produced those withheld cells is a **project-specific
   conservative safeguard chosen by this project**, not a threshold stated in the
   CIHI or DLI Terms available here: no CIHI-mandated minimum cell size is
   claimed or implied anywhere in this repository. The application adds no
   threshold of its own — the already-suppressed project tables govern — and any
   change to the rule should be confirmed with the institutional DLI contact.
4. **No interactive re-aggregation.** Filtering is limited to switching between
   tables and series that were aggregated and cleared in advance. There is no
   province-by-site-by-age-by-quarter cross-tabulation, because combining
   individually safe aggregates can produce a cell that nobody cleared. No
   record-level data is queried at any point.
5. **Repository hygiene.** `.gitignore` blocks restricted extensions and
   directories. Note that a `.gitignore` added *after* a sensitive file has been
   committed is not sufficient: if restricted data were ever committed, rewrite
   the git history before making the repository public. `tools/check_release.py`
   checks the working tree, and the tracked files if the repository is a git
   checkout, before deployment.

If a file is committed to GitHub, assume it is public even if the application
never displays it.

## Attribution for reuse

If you reuse the derived outputs, reproduce the CIHI accreditation text above
unmodified, and do not restyle it into marketing language.
