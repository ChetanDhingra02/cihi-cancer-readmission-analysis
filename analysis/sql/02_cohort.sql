-- ============================================================
-- Build the analysis cohort.
--
--   1. cancer_flags     which malignancy, and where it started
--   2. comorbidity      conditions the patient already had on arrival
--   3. care_flags       post-admission conditions, palliative care, COVID
--   4. all_admissions   one tidy row per DAD abstract
--   5. episodes         abstracts joined into continuous episodes of care
--   6. episode_level    one row per episode of care
--   7. with_readmit     look ahead to the patient's next episode
--   8. cohort           episodes eligible for the readmission analysis
--
-- Layers 5 and 6 exist because a DAD abstract is NOT a hospital episode. When a
-- patient is transferred between facilities, each facility files its own
-- abstract. Treating those as separate admissions counts a single continuous
-- episode of care as an admission plus a "readmission".
-- ============================================================

-- ------------------------------------------------------------
-- 1. Cancer flags
--
-- The study population is C00-C97, invasive malignant neoplasms.
--
-- D00-D09 (carcinoma in situ) and D45-D47 (uncertain behaviour) are recorded
-- but deliberately excluded. They are clinically distinct from invasive cancer.
--
-- The site a cancer STARTED in is taken from the earliest code that is not
-- C77-C79 (secondary deposits), C80 (unknown primary) or C97 (multiple
-- primaries). Without that rule, a bowel cancer that had spread to the liver
-- would be labelled a liver cancer.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE cancer_dx AS
SELECT
    d.record_id,
    d.dx_code,
    d.dx_seq,
    SUBSTR(d.dx_code, 1, 3) AS code_3char
FROM diagnoses d
WHERE regexp_matches(d.dx_code, '^C[0-9][0-9]');

CREATE OR REPLACE TABLE cancer_flags AS
SELECT
    c.record_id,
    TRUE AS has_cancer,
    MAX(CASE WHEN c.dx_seq = 1 THEN 1 ELSE 0 END) = 1 AS cancer_is_main_reason,
    MAX(CASE WHEN m.cancer_site = 'Secondary (spread)' THEN 1 ELSE 0 END) = 1
        AS cancer_has_spread,
    -- Best site on THIS abstract. Episode-level selection happens later, in
    -- episode_cancer_site, because a primary site may be coded on any abstract
    -- in a multi-facility episode.
    MIN(m.site_rank) AS best_site_rank
FROM cancer_dx c
LEFT JOIN cancer_site_map m ON m.code_3char = c.code_3char
GROUP BY c.record_id;

CREATE OR REPLACE TABLE non_invasive_flags AS
SELECT
    record_id,
    MAX(CASE WHEN regexp_matches(dx_code, '^D0[0-9]') THEN 1 ELSE 0 END) = 1
        AS carcinoma_in_situ,
    MAX(CASE WHEN regexp_matches(dx_code, '^D4[567]') THEN 1 ELSE 0 END) = 1
        AS uncertain_behaviour
FROM diagnoses
WHERE regexp_matches(dx_code, '^D0[0-9]') OR regexp_matches(dx_code, '^D4[567]')
GROUP BY record_id;


-- ------------------------------------------------------------
-- 2. Comorbidity
--
-- Only diagnoses flagged type '1' count. Type '1' means the patient already had
-- that condition on arrival. Conditions that appeared after admission (type '2')
-- must be excluded, or we would be using something that happened after
-- admission to predict what happens after admission.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE comorbidity AS
WITH tagged AS (
    SELECT
        record_id,
        CASE
            WHEN regexp_matches(dx_code, '^I2[0-5]') THEN 'heart_disease'
            WHEN regexp_matches(dx_code, '^I50')     THEN 'heart_failure'
            WHEN regexp_matches(dx_code, '^I4[4-9]') THEN 'irregular_heartbeat'
            WHEN regexp_matches(dx_code, '^I1[0-5]') THEN 'high_blood_pressure'
            WHEN regexp_matches(dx_code, '^I6[0-9]') THEN 'stroke'
            WHEN regexp_matches(dx_code, '^E1[0-4]') THEN 'diabetes'
            WHEN regexp_matches(dx_code, '^J4[0-7]') THEN 'lung_disease'
            WHEN regexp_matches(dx_code, '^N1[789]') THEN 'kidney_disease'
            WHEN regexp_matches(dx_code, '^K7[0-4]') THEN 'liver_disease'
            WHEN regexp_matches(dx_code, '^F0[0-3]') THEN 'dementia'
            WHEN regexp_matches(dx_code, '^D5') OR regexp_matches(dx_code, '^D6[0-4]')
                THEN 'anaemia'
            WHEN regexp_matches(dx_code, '^E4[0-6]') THEN 'malnutrition'
            ELSE NULL
        END AS condition
    FROM diagnoses
    WHERE dx_type = '1'
)
SELECT
    record_id,
    COUNT(DISTINCT condition) AS comorbidity_count,
    MAX(CASE WHEN condition='heart_failure'  THEN 1 ELSE 0 END)=1 AS has_heart_failure,
    MAX(CASE WHEN condition='diabetes'       THEN 1 ELSE 0 END)=1 AS has_diabetes,
    MAX(CASE WHEN condition='kidney_disease' THEN 1 ELSE 0 END)=1 AS has_kidney_disease,
    MAX(CASE WHEN condition='lung_disease'   THEN 1 ELSE 0 END)=1 AS has_lung_disease,
    MAX(CASE WHEN condition='dementia'       THEN 1 ELSE 0 END)=1 AS has_dementia,
    MAX(CASE WHEN condition='anaemia'        THEN 1 ELSE 0 END)=1 AS has_anaemia
FROM tagged
WHERE condition IS NOT NULL
GROUP BY record_id;


-- ------------------------------------------------------------
-- 3. Care flags
--
-- Diagnosis type '2' means the condition arose AFTER admission. That is not the
-- same as harm, error or poor care: it also covers expected treatment effects
-- and natural progression of the disease. The variable is named for what it
-- actually records.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE care_flags AS
SELECT
    record_id,
    MAX(CASE WHEN dx_type = '2' THEN 1 ELSE 0 END) = 1 AS post_admission_condition,
    MAX(CASE WHEN dx_code LIKE 'Z515%' THEN 1 ELSE 0 END) = 1 AS palliative_care,
    MAX(CASE WHEN dx_code LIKE 'Z511%' THEN 1 ELSE 0 END) = 1 AS chemo_code,
    MAX(CASE WHEN dx_code LIKE 'U071%' THEN 1 ELSE 0 END) = 1 AS covid
FROM diagnoses
GROUP BY record_id;


-- ------------------------------------------------------------
-- 4. One tidy row per DAD abstract
--
-- NOTE ON TIMING. REL_ADAY is a *pseudo* admission day: CIHI derives it as
-- REL_DDAY minus the CATEGORISED length of stay. Because the category is the
-- floor of its band, the derived admission day is never earlier than the true
-- one, and for the "10 or more days" band the error has no upper limit.
-- REL_DDAY (discharge) is exact. Wherever timing matters, prefer discharge.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE all_admissions AS
SELECT
    a.record_id,
    a.PATNT_ID AS patient_id,
    CASE a.SUB_PROV
        WHEN '0' THEN 'Newfoundland and Labrador'
        WHEN '1' THEN 'Prince Edward Island'
        WHEN '2' THEN 'Nova Scotia'
        WHEN '3' THEN 'New Brunswick'
        WHEN '5' THEN 'Ontario'
        WHEN '6' THEN 'Manitoba'
        WHEN '7' THEN 'Saskatchewan'
        WHEN '8' THEN 'Alberta'
        WHEN '9' THEN 'British Columbia'
        ELSE 'Territories'
    END AS province,
    a.SUB_PROV = '8' AS is_alberta,
    a.AGRP_F_D       AS age_group,
    a.GENDER         AS sex,

    -- ADM_CAT 'U' is the Emergent/Urgent admission CATEGORY. It is not the same
    -- as walking in through an emergency department: that is ENT_CODE 'E'.
    a.ADM_CAT = 'U'  AS urgent_admission,
    a.ENT_CODE = 'E' AS entered_via_ed,
    a.ADM_CAT        AS admit_category,
    a.ENT_CODE       AS entry_point,

    a.TLOS_CAT       AS length_of_stay_group,
    CASE a.TLOS_CAT WHEN 1 THEN 1 WHEN 2 THEN 2 WHEN 3 THEN 3
                    WHEN 4 THEN 5 WHEN 6 THEN 9 ELSE NULL END AS los_max,
    a.TLOS_CAT = 10  AS los_unbounded,

    a.ALC_LCAT > 0   AS waited_for_other_care,
    a.REL_ADAY       AS pseudo_admission_day,
    a.REL_DDAY       AS discharge_day,
    a.DIS_GRP        AS discharge_destination,
    a.DIS_GRP = 'DEATH'    AS died_in_hospital,
    a.DIS_GRP = 'TRANSFER' AS discharged_by_transfer,
    a.DIS_GRP = 'HOME'     AS discharged_home,
    a.SCU_C_1 IS NOT NULL AND a.SCU_C_1 <> '' AS intensive_care,

    COALESCE(cf.has_cancer, FALSE)            AS has_cancer,
    COALESCE(cf.cancer_is_main_reason, FALSE) AS cancer_is_main_reason,
    COALESCE(cf.cancer_has_spread, FALSE)     AS cancer_has_spread,
    COALESCE(ni.carcinoma_in_situ, FALSE)     AS carcinoma_in_situ,
    COALESCE(ni.uncertain_behaviour, FALSE)   AS uncertain_behaviour,

    COALESCE(cm.comorbidity_count, 0)         AS comorbidity_count,
    COALESCE(cm.has_heart_failure, FALSE)     AS has_heart_failure,
    COALESCE(cm.has_diabetes, FALSE)          AS has_diabetes,
    COALESCE(cm.has_kidney_disease, FALSE)    AS has_kidney_disease,
    COALESCE(cm.has_lung_disease, FALSE)      AS has_lung_disease,
    COALESCE(cm.has_dementia, FALSE)          AS has_dementia,
    COALESCE(cm.has_anaemia, FALSE)           AS has_anaemia,

    COALESCE(k.post_admission_condition, FALSE) AS post_admission_condition,
    COALESCE(k.palliative_care, FALSE)          AS palliative_care,
    COALESCE(k.chemo_code, FALSE)               AS chemo_code,
    COALESCE(k.covid, FALSE)                    AS covid,

    (SELECT COUNT(*) FROM interventions i WHERE i.record_id = a.record_id)
        AS n_procedures
FROM admissions a
LEFT JOIN cancer_flags       cf ON cf.record_id = a.record_id
LEFT JOIN non_invasive_flags ni ON ni.record_id = a.record_id
LEFT JOIN comorbidity        cm ON cm.record_id = a.record_id
LEFT JOIN care_flags          k ON  k.record_id = a.record_id;


-- ------------------------------------------------------------
-- 5. Join abstracts into episodes of care
--
-- An abstract continues the previous one when the previous abstract ended in a
-- transfer AND this admission begins on or before the day after that discharge.
-- Anything else starts a new episode.
--
-- The one-day tolerance absorbs the imprecision in the derived admission day.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE episodes AS
WITH ordered AS (
    SELECT
        *,
        LAG(discharge_day)          OVER w AS prev_discharge_day,
        LAG(discharged_by_transfer) OVER w AS prev_was_transfer
    FROM all_admissions
    WINDOW w AS (PARTITION BY patient_id ORDER BY discharge_day, record_id)
),
marked AS (
    SELECT
        *,
        CASE
            WHEN prev_discharge_day IS NULL THEN 1
            -- The receiving admission must begin ON OR AFTER the previous
            -- discharge. A derived admission day already BEFORE it cannot
            -- represent a receiving facility, because the true admission is
            -- earlier still.
            -- {MERGE_PREDICATE} is either the derived-date rule or the
            -- interval-aware rule. The derived rule compares prev_discharge_day
            -- against pseudo_admission_day, which is REL_DDAY minus the FLOOR of
            -- the stay band. For the ">=10 days" band that derived day can sit
            -- weeks after the true admission, so a genuine transfer into a long
            -- stay fails the test and the episode is wrongly split. The
            -- interval-aware rule instead asks whether the EARLIEST admission the
            -- band allows falls within tolerance of the previous discharge.
            WHEN {TRANSFER_CONDITION} AND {MERGE_PREDICATE} THEN 0
            ELSE 1
        END AS starts_new_episode
    FROM ordered
)
SELECT
    *,
    SUM(starts_new_episode) OVER (
        PARTITION BY patient_id ORDER BY discharge_day, record_id
        ROWS UNBOUNDED PRECEDING
    ) AS episode_no
FROM marked;


-- ------------------------------------------------------------
-- 6. One row per episode of care
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE episode_level AS
SELECT
    patient_id,
    episode_no,
    COUNT(*)                     AS n_abstracts,
    -- The episode starts when its FIRST abstract starts. MIN() across
    -- component abstracts could pick a later abstract whose derived admission
    -- day happens to be smaller, which is not the episode's beginning.
    FIRST(pseudo_admission_day ORDER BY discharge_day, record_id)
                                 AS episode_start_day,
    MAX(discharge_day)           AS episode_end_day,

    FIRST(province             ORDER BY discharge_day, record_id) AS province,
    FIRST(is_alberta           ORDER BY discharge_day, record_id) AS is_alberta,
    FIRST(age_group            ORDER BY discharge_day, record_id) AS age_group,
    FIRST(sex                  ORDER BY discharge_day, record_id) AS sex,
    FIRST(urgent_admission     ORDER BY discharge_day, record_id) AS urgent_admission,
    FIRST(entered_via_ed       ORDER BY discharge_day, record_id) AS entered_via_ed,
    FIRST(record_id ORDER BY discharge_day, record_id) AS first_record_id,

    LAST(discharge_destination ORDER BY discharge_day, record_id) AS discharge_destination,
    LAST(died_in_hospital      ORDER BY discharge_day, record_id) AS died_in_hospital,
    LAST(discharged_home       ORDER BY discharge_day, record_id) AS discharged_home,
    LAST(length_of_stay_group  ORDER BY discharge_day, record_id) AS final_los_group,

    FIRST(los_max              ORDER BY discharge_day, record_id) AS first_los_max,
    FIRST(length_of_stay_group ORDER BY discharge_day, record_id) AS first_los_group,
    FIRST(los_unbounded        ORDER BY discharge_day, record_id) AS first_los_unbounded,

    MAX(CAST(has_cancer               AS INT)) = 1 AS has_cancer,
    MAX(CAST(cancer_is_main_reason    AS INT)) = 1 AS cancer_is_main_reason,
    MAX(CAST(cancer_has_spread        AS INT)) = 1 AS cancer_has_spread,
    MAX(CAST(carcinoma_in_situ        AS INT)) = 1 AS carcinoma_in_situ,
    MAX(CAST(uncertain_behaviour      AS INT)) = 1 AS uncertain_behaviour,
    MAX(CAST(intensive_care           AS INT)) = 1 AS intensive_care,
    MAX(CAST(palliative_care          AS INT)) = 1 AS palliative_care,
    MAX(CAST(chemo_code               AS INT)) = 1 AS chemo_code,
    MAX(CAST(covid                    AS INT)) = 1 AS covid,
    MAX(CAST(post_admission_condition AS INT)) = 1 AS post_admission_condition,
    MAX(CAST(waited_for_other_care    AS INT)) = 1 AS waited_for_other_care,
    SUM(n_procedures)                              AS n_procedures,
    SUM(length_of_stay_group)                      AS episode_los_floor
FROM episodes
GROUP BY patient_id, episode_no;


-- ------------------------------------------------------------
-- 6b. Cancer site chosen across the WHOLE episode
--
-- A primary site coded on the second abstract of a transfer episode must beat
-- a "secondary deposit" or "unknown primary" code on the first. Selecting the
-- earliest non-null value, as an earlier version did, got this wrong for 54
-- episodes. Precedence comes from site_rank in the reference table:
--   1 primary site   2 multiple primaries   3 secondary   4 unknown primary
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE episode_cancer_site AS
WITH per_code AS (
    SELECT
        e.patient_id,
        e.episode_no,
        m.cancer_site,
        m.site_rank,
        c.dx_seq,
        e.discharge_day,
        e.record_id
    FROM episodes e
    JOIN cancer_dx c       ON c.record_id = e.record_id
    JOIN cancer_site_map m ON m.code_3char = c.code_3char
)
SELECT
    patient_id,
    episode_no,
    FIRST(cancer_site ORDER BY site_rank, discharge_day, record_id, dx_seq)
        AS cancer_site
FROM per_code
GROUP BY patient_id, episode_no;


-- ------------------------------------------------------------
-- 6c. Baseline comorbidity: FIRST abstract of the episode only
--
-- Type '1' means present on admission to THAT facility. In a transfer episode,
-- a condition that developed at hospital A is legitimately coded type '1' on
-- arrival at hospital B. Aggregating type '1' across the whole episode
-- therefore lets mid-episode events enter a variable that is supposed to
-- describe the patient at the START of the episode -- a small but real leak
-- into a predictor of what happens after the episode ends.
--
-- Conditions documented later in the episode are kept separately so the
-- difference can still be examined.
-- ------------------------------------------------------------
-- Cancer variables as they stood on the FIRST abstract of the episode.
-- The episode-wide versions (episode_cancer_site, cancer_has_spread) may draw
-- on a metastatic or primary-site code recorded only after a transfer, which
-- was not known when the episode began. Question 2's baseline model needs the
-- first-abstract versions.
CREATE OR REPLACE TABLE episode_baseline_cancer AS
SELECT
    el.patient_id,
    el.episode_no,
    COALESCE(cf.cancer_has_spread, FALSE) AS baseline_cancer_has_spread,
    m.cancer_site                         AS baseline_cancer_site
FROM episode_level el
LEFT JOIN cancer_flags cf ON cf.record_id = el.first_record_id
LEFT JOIN (
    SELECT c.record_id,
           FIRST(m.cancer_site ORDER BY m.site_rank, c.dx_seq) AS cancer_site
    FROM cancer_dx c
    JOIN cancer_site_map m ON m.code_3char = c.code_3char
    GROUP BY c.record_id
) m ON m.record_id = el.first_record_id;


CREATE OR REPLACE TABLE episode_baseline AS
SELECT
    el.patient_id,
    el.episode_no,
    COALESCE(c.comorbidity_count, 0)      AS comorbidity_count,
    COALESCE(c.has_heart_failure, FALSE)  AS has_heart_failure,
    COALESCE(c.has_diabetes, FALSE)       AS has_diabetes,
    COALESCE(c.has_kidney_disease, FALSE) AS has_kidney_disease,
    COALESCE(c.has_lung_disease, FALSE)   AS has_lung_disease,
    COALESCE(c.has_dementia, FALSE)       AS has_dementia,
    COALESCE(c.has_anaemia, FALSE)        AS has_anaemia
FROM episode_level el
LEFT JOIN comorbidity c ON c.record_id = el.first_record_id;


-- ------------------------------------------------------------
-- 6d. Assemble the episode table
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE episode_full AS
SELECT
    el.*,
    cs.cancer_site,
    b.comorbidity_count,
    b.has_heart_failure,
    b.has_diabetes,
    b.has_kidney_disease,
    b.has_lung_disease,
    b.has_dementia,
    b.has_anaemia,
    bc.baseline_cancer_has_spread,
    -- NO fallback to the episode-wide site. If the first abstract carries no
    -- cancer code, that fact is recorded explicitly rather than quietly
    -- borrowing a site recorded later in the episode, which would put
    -- post-baseline information into a variable documented as baseline.
    COALESCE(bc.baseline_cancer_site, 'Not recorded on first abstract')
        AS baseline_cancer_site
FROM episode_level el
LEFT JOIN episode_cancer_site cs
       ON cs.patient_id = el.patient_id AND cs.episode_no = el.episode_no
LEFT JOIN episode_baseline b
       ON  b.patient_id = el.patient_id AND  b.episode_no = el.episode_no
LEFT JOIN episode_baseline_cancer bc
       ON bc.patient_id = el.patient_id AND bc.episode_no = el.episode_no;


-- ------------------------------------------------------------
-- 7. Search for the FIRST QUALIFYING readmission in the 30-day window
--
-- An earlier version used LEAD() to look only at the immediately next episode.
-- That misses a patient who has a planned admission and THEN an urgent one,
-- both inside 30 days: the planned episode sits in between and hides the
-- urgent one. It affected 83 index episodes.
--
-- Every subsequent episode inside the window is therefore examined, and the
-- first qualifying urgent episode is taken.
--
-- Two gaps are computed because the candidate episode's start day is derived
-- from a categorised length of stay:
--   gap_latest    uses the derived start day; the true gap can only be shorter
--   gap_earliest  uses the widest stay the band allows; unbounded for the
--                 "10 or more days" band, so treated as zero there
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE candidates AS
SELECT
    i.patient_id,
    i.episode_no,
    c.episode_no        AS candidate_no,
    c.urgent_admission  AS candidate_urgent,
    c.entered_via_ed    AS candidate_via_ed,
    c.chemo_code        AS candidate_chemo,
    c.episode_start_day - i.episode_end_day AS gap_latest,
    -- Earliest the candidate could truly have begun, relative to the index
    -- discharge. NOT clamped at zero: a negative value is meaningful and says
    -- the candidate might have begun BEFORE the index discharge, in which case
    -- it is not a post-discharge readmission at all.
    -- NULL means the "10 or more days" band, where there is no lower bound.
    CASE
        WHEN c.first_los_unbounded THEN NULL
        ELSE c.episode_start_day - i.episode_end_day
             - (c.first_los_max - c.first_los_group)
    END AS gap_earliest
FROM episode_full i
JOIN episode_full c
  ON  c.patient_id = i.patient_id
  AND c.episode_no > i.episode_no
WHERE i.has_cancer
  AND NOT i.died_in_hospital
  AND i.episode_end_day <= 1065;
-- NOTE: no distance cutoff. An earlier version discarded candidates whose
-- derived start day was more than 60 days out. That is unsafe: for the "10 or
-- more days" band the derived start day can be arbitrarily later than the true
-- one, so a candidate appearing 90 days out could genuinely have begun inside
-- the 30-day window. Dropping those silently converted unresolved timing into
-- a definite non-readmission for 3,205 episodes.

-- Whether the patient has ANY later episode at all, regardless of distance.
-- Kept as an explicit flag so a patient whose next episode falls far outside the
-- window is distinguishable from a patient who never came back at all.
CREATE OR REPLACE TABLE has_later AS
SELECT patient_id, episode_no,
       EXISTS (SELECT 1 FROM episode_full l
               WHERE l.patient_id = e.patient_id AND l.episode_no > e.episode_no)
           AS has_later_episode
FROM episode_full e;

CREATE OR REPLACE TABLE readmit_summary AS
SELECT
    patient_id,
    episode_no,
    -- Point estimate, using the derived admission day as recorded. This is the
    -- headline outcome: the best single estimate available, not a claim that
    -- every one of these is certain.
    MAX(CASE WHEN gap_latest BETWEEN 0 AND 30 THEN 1 ELSE 0 END) = 1
        AS returned_30d,
    MAX(CASE WHEN gap_latest BETWEEN 0 AND 30 AND candidate_urgent
             THEN 1 ELSE 0 END) = 1 AS urgent_readmit_30d,
    -- DEFINITE requires the candidate's ENTIRE possible admission interval to
    -- sit after the index discharge and inside 30 days. A pseudo-gap of +2 days
    -- with a 6-9 day band could truly have begun 1 day BEFORE discharge, so it
    -- is not definite even though the derived gap looks comfortably inside.
    MAX(CASE WHEN candidate_urgent
              AND gap_latest BETWEEN 0 AND 30
              AND gap_earliest IS NOT NULL AND gap_earliest >= 0
             THEN 1 ELSE 0 END) = 1 AS urgent_definite_30d,
    MAX(CASE WHEN gap_latest BETWEEN 0 AND 30 AND candidate_via_ed
             THEN 1 ELSE 0 END) = 1 AS ed_readmit_30d,
    -- ANY-return definiteness, defined the same way as the urgent version below:
    -- the candidate's ENTIRE possible admission interval must sit after the index
    -- discharge and inside 30 days. Without this, readmit_certainty called an
    -- episode 'definite' merely because the DERIVED gap landed in the window,
    -- which is the point estimate under a different name, not a definiteness
    -- claim -- and it labelled 5,999 episodes definite where only the urgent
    -- outcome had ever been tested properly.
    MAX(CASE WHEN gap_latest BETWEEN 0 AND 30
              AND gap_earliest IS NOT NULL AND gap_earliest >= 0
             THEN 1 ELSE 0 END) = 1 AS any_definite_30d,
    MAX(CASE WHEN gap_latest >= 0 THEN 1 ELSE 0 END) = 1 AS has_later_any,
    MIN(CASE WHEN gap_latest BETWEEN 0 AND 30 AND candidate_urgent
             THEN gap_latest END) AS days_to_first_urgent,
    -- Was the first qualifying NON-urgent return a chemotherapy episode?
    -- The CASE inside FIRST() matters: ordering alone put non-qualifying
    -- candidates last but still returned one of them when NO planned return
    -- existed, so 15,553 episodes with no planned return carried some unrelated
    -- candidate's chemo flag. Only qualifying candidates contribute a value now,
    -- and the column is NULL when there was no planned return.
    FIRST(CASE WHEN gap_latest BETWEEN 0 AND 30 AND NOT candidate_urgent
               THEN candidate_chemo END
          ORDER BY
          CASE WHEN gap_latest BETWEEN 0 AND 30 AND NOT candidate_urgent
               THEN gap_latest ELSE 9999 END) AS first_planned_return_chemo,
    MAX(CASE WHEN gap_latest BETWEEN 0 AND 30 AND NOT candidate_urgent
             THEN 1 ELSE 0 END) = 1 AS planned_return_30d,
    -- Could any candidate fall inside 30 days once timing slack is allowed?
    -- Computed separately for ANY return and for URGENT returns, because the
    -- primary outcome is specifically an urgent readmission: a planned return
    -- resolving cleanly says nothing about whether a later urgent one falls
    -- inside the window.
    -- POSSIBLE means the candidate's interval [gap_earliest, gap_latest]
    -- overlaps the window [0, 30] at all. NULL gap_earliest (unbounded band)
    -- has no lower limit, so it overlaps whenever gap_latest >= 0.
    MAX(CASE WHEN gap_latest >= 0
              AND (gap_earliest IS NULL OR gap_earliest <= 30)
             THEN 1 ELSE 0 END) = 1 AS any_possible_30d,
    MAX(CASE WHEN candidate_urgent AND gap_latest >= 0
              AND (gap_earliest IS NULL OR gap_earliest <= 30)
             THEN 1 ELSE 0 END) = 1 AS urgent_possible_30d,
    MAX(CASE WHEN candidate_urgent AND gap_latest >= 0 THEN 1 ELSE 0 END) = 1
        AS has_later_urgent,
    COUNT(*) AS n_candidates
FROM candidates
GROUP BY patient_id, episode_no;


-- ------------------------------------------------------------
-- 8. The analysis cohort
--
-- POPULATION: episodes of care with an invasive cancer diagnosis (C00-C97),
-- ending in a live discharge, with at least 30 days of the data window left.
-- The PRIMARY analysis restricts further to episodes discharged home.
--
-- This is a project-defined outcome. It is NOT CIHI's official 30-day
-- readmission indicator, which has its own denominator rules, exclusions and
-- episode-construction methodology.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE cohort AS
SELECT
    e.*,
    COALESCE(r.returned_30d, FALSE)               AS returned_30d,
    COALESCE(r.urgent_readmit_30d, FALSE)         AS urgent_readmit_30d,
    COALESCE(r.ed_readmit_30d, FALSE)             AS ed_readmit_30d,
    COALESCE(r.planned_return_30d, FALSE)         AS planned_return_30d,
    r.days_to_first_urgent,
    r.first_planned_return_chemo,
    COALESCE(hl.has_later_episode, FALSE) AS has_later_episode,
    -- Certainty of the ANY-return outcome, built the same way as the urgent one
    -- so the two bands mean the same thing. 'definite' requires the whole
    -- possible interval to lie inside the window; it is NOT the point estimate.
    COALESCE(r.any_definite_30d, FALSE) AS any_definite_30d,
    CASE
        WHEN COALESCE(r.any_definite_30d, FALSE)     THEN 'definite'
        WHEN NOT COALESCE(r.has_later_any, FALSE)    THEN 'no later episode'
        WHEN NOT COALESCE(r.any_possible_30d, FALSE) THEN 'definitely not'
        ELSE 'ambiguous'
    END AS readmit_certainty,
    -- Certainty of the PRIMARY outcome, urgent/emergent readmission
    COALESCE(r.urgent_definite_30d, FALSE) AS urgent_definite_30d,
    CASE
        WHEN COALESCE(r.urgent_definite_30d, FALSE)     THEN 'definite'
        WHEN NOT COALESCE(r.has_later_urgent, FALSE)    THEN 'no later urgent episode'
        WHEN NOT COALESCE(r.urgent_possible_30d, FALSE) THEN 'definitely not'
        ELSE 'ambiguous'
    END AS urgent_readmit_certainty
FROM episode_full e
LEFT JOIN readmit_summary r
       ON r.patient_id = e.patient_id AND r.episode_no = e.episode_no
LEFT JOIN has_later hl
       ON hl.patient_id = e.patient_id AND hl.episode_no = e.episode_no
WHERE e.has_cancer
  AND NOT e.died_in_hospital
  AND e.episode_end_day <= 1065;
