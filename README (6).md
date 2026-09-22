# Urgent readmission and in-hospital mortality after cancer hospitalisation

A retrospective cohort study of transfer-linked hospital episodes of care, built from the CIHI
Discharge Abstract Database Research Analytic File, with a Streamlit dashboard for the results.

**[Live dashboard →](https://cihi-cancer-readmission.streamlit.app/)**

![Streamlit](https://img.shields.io/badge/Streamlit-1.64-FF4B4B?logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-5.22-3F4F75?logo=plotly&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Data](https://img.shields.io/badge/data-licensed%2C%20not%20included-8792a6)

**Deployment runtime:** Python 3.13. The badge URL above is retained unchanged from the supplied package.

> Parts of this material are based on the Canadian Institute for Health Information Discharge
> Abstract Database Research Analytic Files (sampled from fiscal years 2021-2022, 2022-2023 and
> 2023-2024). However the analysis, conclusions, opinions and statements expressed herein are
> those of the author and not those of the Canadian Institute for Health Information.

That wording is required and is reproduced without modification here, on the dashboard's
*Methods, data and licensing* page, and in the footer of every page. The CIHI logo is not used.

---

## What this is about

Someone finishes a cancer hospitalisation, goes home, and two weeks later has an urgent or
emergent hospital readmission. How often does that happen, and was there anything in the record of
the index stay associated with that outcome?

I went looking in a research sample of Canadian hospital discharge records. Of the eligible
episodes ending in discharge home, 15.6% were followed by an urgent/emergent readmission within
30 days. After adjustment for age, sex, cancer site, spread and comorbidity count, the standardized
readmission risk was 22.3% for urgent index admissions and 9.0% for planned admissions, a risk ratio
of 2.47. This is an association, not a causal effect.

Getting there took longer than the analysis did, because the data doesn't hand you a hospital
stay. It hands you discharge abstracts, and one stay can be several of them. Most of what follows
is about that problem and what it does to the answers.

**Contents:** [the data](#the-data) · [building an episode](#building-an-episode-of-care) ·
[the cohort](#who-ended-up-in-the-study) · [the admission-date problem](#the-admission-date-problem) ·
[findings](#finding-1-how-often-people-come-back) · [prediction](#can-you-predict-it) ·
[robustness](#what-happens-if-you-change-the-rules) · [limitations](#what-this-cant-tell-you) ·
[disclosure](#disclosure-and-what-gets-published) · [running it](#running-it-yourself)

---

## What it isn't

Worth getting out of the way early, because the topic invites misreading.

This is not clinical decision support. There's no way to enter patient characteristics and get a
personalised risk, and nothing here has undergone prospective clinical validation. It isn't a
national estimate either — every count is a count inside this research sample. It's also not
CIHI's official 30-day readmission indicator, which uses its own episode construction,
denominators and exclusions. The outcome here is project-defined.

The data is not open data, not Alberta Health Services data, not Alberta Health data, not Cancer
Care Alberta production data, and not health-system production data.

And nothing here is causal. Urgent admission is a marker of how an episode began, not a treatment
anyone assigned.

---

## The data

Canadian Institute for Health Information, Discharge Abstract Database, Research Analytic File,
clinical research sample, sampled from fiscal years 2021-2022, 2022-2023 and 2023-2024. Coverage
is Canadian provinces and territories excluding Quebec, at approximately a 10% research sample of
discharge abstracts. Rates and percentages describe that sample. The counts are not Canadian
national totals.

Each row is a discharge abstract: one patient, one stay, one facility, with diagnoses,
interventions, a discharge disposition, and a patient identifier that persists across stays. The
unit of analysis here isn't the abstract though. It's the approximated episode of care, meaning
one or more abstracts joined where the coding indicates a transfer between facilities.

### Getting the data yourself

The file was accessed through the University of Alberta's institutional access under Statistics
Canada's Data Liberation Initiative arrangement. The RAF is licensed, not public, and it is not in
this repository.

1. Confirm your institution participates in Statistics Canada's Data Liberation Initiative.
2. Contact your institution's DLI contact or data librarian and request the CIHI DAD Research
   Analytic File for the fiscal years you need.
3. Obtain the file under your own institution's Terms. It can't be redistributed by this project,
   and no part of it is reachable from this repository or the deployed application.
4. Check with the same contact before publishing any derived output of your own.

No credentials of any kind belong in this repository — no institutional login, no CCID, no
password, no access token, no cookies, no library session information. The application never
touches the restricted data, so deployment secrets should contain no data-access credentials at
all.

---

## Building an episode of care

Here's the problem that shapes everything downstream. When a hospital transfers a patient
somewhere else, the system writes a second abstract. Count abstracts and that transfer looks
exactly like a readmission — same patient, new admission, a couple of days later. It isn't one.
It's the middle of a single continuous stay.

```mermaid
flowchart LR
    A["Abstract 1<br/>Community hospital<br/>discharged BY TRANSFER"] --> B["Abstract 2<br/>Cancer centre<br/>admitted from transfer"]
    B --> C["Abstract 3<br/>Cancer centre<br/>discharged HOME"]
    A -.-> D
    B -.-> D
    C -.-> D
    D["ONE episode of care<br/>Baseline from abstract 1<br/>Outcome from abstract 3"]
    D ==> E["30-day clock<br/>starts HERE"]

    style D fill:#e8f0fe,stroke:#1f3a8f,stroke-width:2px
    style E fill:#fde8e4,stroke:#f0674a,stroke-width:2px
```

Two abstracts get joined when the discharge coding says transfer and the timing is compatible.
Under the primary rule that means the receiving stay began the same day as the sending discharge,
or the day after.

A few other decisions follow from treating the episode as the unit. Baseline characteristics for
the association models come from the first abstract only. A condition that develops at the first
hospital can be coded as *present on admission* at a receiving hospital, so aggregating diagnoses
across a transfer-linked episode can quietly move post-exposure information into a baseline
covariate.

Comorbidities therefore come from diagnosis type 1 on the first abstract for the baseline models.
Type 2 conditions are recorded as arising after admission and are not treated as baseline
characteristics.

Baseline-only models are the primary association models. Palliative care, post-admission
conditions, special care, length of stay, procedures and multi-facility care occur during the
episode, so models that add them are reported as descriptive rather than as better-adjusted versions
of the same question. The separate prediction model is different by design: it is explicitly a
**discharge-time/end-of-index-stay research model**, so it intentionally uses information available
by the end of the stay.

Time periods are anchored on discharge rather than admission, which the next section explains.

---

## Who ended up in the study

```mermaid
flowchart TD
    A["744,914 discharge abstracts"] --> B["724,591 episodes of care<br/><i>20,323 abstracts merged into earlier episodes</i>"]
    B --> C["43,565 episodes with invasive cancer<br/><i>C00-C97; in-situ and uncertain behaviour excluded</i>"]
    C --> D["38,657 ended in a live discharge<br/><i>4,908 ended in death</i>"]
    D --> E["37,511 with 30 days of follow-up left<br/><i>1,146 too close to the end of the data window</i>"]
    E --> F["<b>32,301 primary cohort: discharged home</b><br/><i>5,210 discharged elsewhere or absent</i><br/>25,495 patients"]

    style F fill:#e8f0fe,stroke:#1f3a8f,stroke-width:3px
```

Research-sample counts throughout, not national totals.

Notice that 32,301 episodes come from 25,495 patients. People contribute more than one episode.
Rate and prediction-performance intervals therefore use patient-level resampling, regression models
use patient-cluster robust covariance where applicable, and the train/test split for the prediction
model is by patient rather than by episode.

---

## The admission-date problem

The file has no admission date. It has a discharge day and a length-of-stay band: 1 day, 2 days,
3 days, 4 to 5, 6 to 9, or 10 or more.

So the admission day gets derived as discharge day minus the floor of the band. For short stays
that's exact. For the "10 or more" band it's barely a bound at all — a 10-day stay and a 300-day
stay both get their admission placed 10 days before discharge.

Which matters enormously for a 30-day window. Sometimes the possible range of admission days sits
entirely inside it and the readmission is provable. Sometimes it sits entirely outside. And
sometimes it straddles the boundary and there's no answer to be had.

![Timing certainty](docs/img/timing_certainty.png)

The ambiguous cases could have been assigned one way or the other and nobody would have noticed.
Instead the share is reported: roughly one in six primary-cohort episodes cannot be resolved on
urgent-readmission timing. The readmission analysis therefore includes a complete-case sensitivity
analysis that drops those timing-ambiguous episodes.

There's a subtler version of the same problem, which the robustness section comes back to.
Transfer merging fails more often for long stays, and long stays aren't independent of how sick
someone is. So the leftover error isn't sprinkled evenly across the cohort. It's correlated with
the exposure being studied.

---

## Finding 1: how often people come back

Of 32,301 episodes ending in a discharge home, 5,027 were followed by an urgent or emergent
readmission within 30 days. That's 15.6%.

It's nowhere near uniform:

![Readmission by cancer site](docs/img/readmission_by_site.png)

Among cancer-site groups with at least 200 episodes, haematologic cancers and secondary (spread)
were above 21%, while thyroid and endocrine, male reproductive and breast were below 9%. These are
descriptive group rates, not adjusted site effects, and the variation is worth remembering whenever
a single readmission figure is quoted for cancer care generally.

The comparison this study is actually built around is how the index episode began. Adjusting for
age band, sex, cancer site, spread and comorbidity count:

| | Adjusted 30-day readmission risk |
|---|---|
| Index episode began urgently | 22.3% |
| Index episode was planned | 9.0% |
| Risk ratio | **2.47** (95% CI 2.32 to 2.64) |
| Risk difference | 13.3 percentage points |
| Odds ratio | 2.94 |

Two and a half times. But urgent admission is a marker here, not a cause — whatever sent someone in
urgently the first time is plausibly still going on when they're discharged, and most of it isn't
written down anywhere in this file.

---

## Finding 2: urgent admission and in-hospital death

Same comparison, different outcome, wider population: all 43,565 cancer episodes rather than only
those discharged home.

| | Adjusted in-hospital mortality |
|---|---|
| Urgent admission | 16.0% |
| Planned admission | 2.9% |
| Risk ratio | **5.52** (95% CI 4.93 to 6.13) |

A risk ratio above five is a big number and it would make a good headline. I'd hold off, for
reasons in the robustness section. This is the least stable of the four findings.

---

## Finding 3: conditions recorded as arising after admission

Diagnosis type 2 marks a condition recorded as arising after admission. It shows up in 23.7% of
cancer episodes, and what it travels with is striking:

| | No type 2 condition coded | At least one coded |
|---|---|---|
| Episodes | 33,235 | 10,330 |
| Died in hospital | 9.0% | 18.7% |
| Special care unit | 8.1% | 24.0% |
| Long stay | 39.6% | 81.9% |

Strong and consistent, and not interpretable in one direction. A condition arising after admission
may well worsen the outcome. A long, complicated stay also gives far more opportunity for
conditions to get recorded in the first place. Both are happening at once and this file can't pull
them apart.

---

## Finding 4: mortality over time

In-hospital mortality was 9.6% in quarter 1 and 12.2% in quarter 12, but the observed series was
non-monotonic. It peaked at 12.8% in quarters 7 and 8, fell to 11.1% in quarter 9, and then rose
again.

![Mortality trend](docs/img/mortality_trend.png)

Obvious next question: did the cohort just get sicker? So the trend was refit three ways.

| Model | Odds ratio per quarter |
|---|---|
| Time only | 1.0225 |
| Time plus measured characteristics | 1.0234 |
| Time plus measured characteristics and COVID coding | 1.0228 |

The fitted per-quarter association remained similar after adjustment for the measured
characteristics and after adding COVID coding. The conclusion has to stay narrow: the measured
characteristics included in these models did not explain the fitted time association. The observed
quarterly series is not a steady rise, and this analysis does not identify the cause of the change.

---

## Can you predict it?

If readmission is that much more common in some groups, can you flag it at discharge?

The model predicts urgent 30-day readmission from information available at the end of the index
stay. It's a discharge-time research model, not an admission-time clinical tool, and it isn't
clinical decision support.

| Metric | Value |
|---|---|
| AUC, logistic | 0.697 (0.682 to 0.709) |
| Geographic holdout, Alberta, patient-separated | 0.687 (0.663 to 0.709) |
| PR-AUC | 0.244, against an outcome prevalence of 0.143 |
| Brier score | 0.1158 |
| Calibration slope | 0.982 |

![Calibration](docs/img/calibration.png)

Discrimination and calibration are different properties. An AUC of 0.697 indicates modest
discrimination in the held-out test set. The calibration slope of 0.982 is close to 1, indicating
that predicted risks were not substantially over- or under-dispersed overall; the calibration
intercept was -0.135. The decile plot above provides the more direct comparison of predicted and
observed risks across risk groups. These results describe this internal test set and do not establish
clinical usefulness.

The Alberta result is an internal geographic split within the same file. It is not external
validation, and no external validation has been done.

---

## What happens if you change the rules

This is the part I'd want a reviewer to look at.

The transfer rule decides where one approximated episode ends and the next begins, and there is no
single observable gold-standard linkage in these RAF fields. The Q1 readmission and Q2 mortality
comparisons were therefore refit from scratch on the cohort produced by each prespecified rule.

![Rule robustness](docs/img/rule_robustness.png)

| Transfer rule | Cohort | Readmission | Q1 risk ratio | Q2 risk ratio |
|---|---|---|---|---|
| Same-day transfer | 32,222 | 15.55% | 2.44 | 5.41 |
| **Same or next day (primary)** | **32,301** | **15.56%** | **2.47** | **5.52** |
| Within two days | 32,350 | 15.58% | 2.50 | 5.66 |
| Interval-aware (earliest possible admission) | 32,644 | 15.58% | 2.52 | 6.55 |
| Interval-aware, 10+ band capped at 90 days | 32,595 | 15.59% | 2.52 | 6.55 |

Question 1 varied little across these transfer rules: the risk ratio ranged from 2.44 to 2.52,
and the readmission rate ranged from 15.55% to 15.59%. That supports the stability of the Q1 result
under the episode-linkage definitions examined here.

Question 2 was more sensitive. Its risk ratio ranged from 5.41 to 6.55 across the same rules. That
variation is substantial relative to the primary estimate's sampling interval, so the mortality
comparison should be read with episode-definition uncertainty in mind as well as sampling
uncertainty.

---

## What this can't tell you

| | |
|---|---|
| Inpatient care only | No outpatient care, and no emergency department visit that didn't end in an admission |
| Deaths after discharge are unobserved | Mortality is in-hospital only, so death after discharge is an unobserved competing event for readmission |
| No cancer stage | Stage, exact diagnosis date and performance status aren't in the DAD, so severity is only partly captured |
| Quebec is absent | "Provinces" here means the rest of Canada |
| A research sample, not a census | Approximately 10% of abstracts; sample counts are not Canadian national totals |
| Banded age and length of stay | Both arrive banded, so models use bands rather than continuous values |
| Timing isn't always resolvable | See the certainty chart above |
| Episodes are approximations | Transfer-linked episodes approximate episodes of care from the fields available in the RAF. They are not CIHI's official episode methodology |
| Transfer-linking error is differential | Merging fails more often for long receiving stays, and long stays aren't independent of severity, so the residual error correlates with the exposure |
| Patients contribute several episodes | Intervals use a patient-cluster bootstrap, but the unit of analysis is the episode |
| Observational throughout | Urgent admission is a marker of how the episode began, not an assigned intervention, and the unmeasured severity that sends someone in urgently is plausibly related to the outcome too |

---

## Disclosure and what gets published

```mermaid
flowchart TD
    A["CIHI DAD RAF<br/>licensed, obtained separately"] --> B["Public analysis code<br/>restricted inputs and record-level intermediates stay local"]
    B --> C["Cleared aggregate tables<br/>+ key_numbers.csv"]
    C --> D["Disclosure check<br/>suppression applied<br/>full-precision copies quarantined"]
    D --> E["Cleared tables copied BY NAME<br/>into app_data/"]
    E --> F["This Streamlit app"]

    style A fill:#fde8e4,stroke:#f0674a,stroke-width:2px
    style D fill:#fdf3e0,stroke:#f2a93b,stroke-width:2px
    style F fill:#e8f0fe,stroke:#1f3a8f,stroke-width:2px
```

Only derived aggregate tables are deployed with the application, from an explicit allow-list rather
than a directory scan. No record-level file, analysis database, internal full-precision table or
CIHI documentation is in the repository, and none is reachable from the running app. The copy step
into `app_data/` is deliberate and manual — the application never points at the analysis output
directory.

Suppression is carried in the source tables and never reversed in the dashboard. A withheld value
shows as *Suppressed*, stays out of every chart, and is never recoverable by subtracting the visible
rows from a total. `small_cell_report.csv` lists every suppressed row and the reason.

One thing to be precise about: the rule that produced those withheld cells is the project's own
conservative safeguard. The CIHI and DLI Terms available to this project state no numeric threshold,
so nothing here should be read as a CIHI-mandated minimum cell size. The application adds no
threshold of its own, the cleared tables govern, and any change to the rule should come from the
institutional DLI contact.

Filtering in the dashboard only switches between tables that were aggregated and cleared in advance.
There's deliberately no cross-tabulation of province by site by age by quarter, because combining
otherwise-safe aggregates can produce a cell nobody cleared. No record-level data is queried at any
point.

Two build-time checks guard the numbers in the written reports. The document builder pulls every
figure from `key_numbers.csv` and raises on a missing entry, and a verification step reads the
finished documents back and fails the build if any number in them can't be traced to an analysis
output.

---

## Running it yourself

```bash
git clone <this-repository>
cd cihi-cancer-readmission-analysis/dashboard
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

No data setup needed. The cleared aggregate tables ship in `app_data/` and the app never reads the
licensed file.

`requirements.txt` pins Streamlit to the 1.64 line deliberately. Some of the CSS targets Streamlit's
internal markup, which moves between minor releases.

```bash
python tools/check_release.py    # pre-deployment repository check
python tools/smoke_test.py       # runs every page through Streamlit's test harness
```

---

## How the code is organised

```
analysis/
    scripts/            pipeline, 00 to 15, run in order
    sql/                episode reshaping and cohort construction
    reference/          cancer scope and site mapping
    public_outputs/     cleared aggregate tables

dashboard/
    app.py              navigation only
    pages/              the eight dashboard pages
    assets/
        styles.css      design tokens, cards, motion, responsive rules
        motion.js       scroll-triggered chart reveal, presentation only
    src/
        constants.py    chart palette, ordering, terminology, the allow-list
        data_loader.py  allow-listed loading, schema validation, caching
        charts.py       every figure; returns Plotly objects, calls no st.*
        metrics.py      lookups into key_numbers.csv
        formatting.py   numbers, intervals, model-label tidying
        ui.py           hero, KPI cards, finding cards, chart cards, callouts
        art.py          decorative page-header scene, no data
        licensing.py    attribution, access and release wording
    app_data/           cleared aggregate tables only
    tools/              release check and smoke test
    requirements.txt

docs/img/               figures used in this README
.streamlit/config.toml
```

The interface is a small design system rather than default Streamlit. Tokens live in
`assets/styles.css`, the components using them live in `src/ui.py`, and the chart half of the same
palette sits in `src/constants.py` and gets applied centrally in `src/charts.py`. Charts return
Plotly objects and never call Streamlit directly, so they're testable on their own. The JavaScript
in `motion.js` handles scroll-triggered reveals and touches no data.

Built with Streamlit and Plotly, plus custom CSS and a little JavaScript. The analysis pipeline
behind it uses pandas, DuckDB, statsmodels and scikit-learn.

---

## Citation and attribution

If you refer to this work, please reproduce the CIHI accreditation statement at the top of this
README without modification, and note that the analysis, conclusions, opinions and statements are
the author's own.

No open-source code licence is currently declared in this repository. The CIHI Discharge Abstract
Database Research Analytic Files remain licensed separately and must be obtained through an eligible
institutional DLI arrangement.
