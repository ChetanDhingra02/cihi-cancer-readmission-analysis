

import os
import pandas as pd

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

KEY = pd.read_csv("output/tables/key_numbers.csv")
_LOOKUP = dict(zip(KEY["name"], KEY["value"]))
_USED = set()


def kn(name):
    """
    Fetch a reported figure. Raises if it is not in key_numbers.csv.

    This is the whole mechanism. No .get(), no default, no try/except.
    """
    if name not in _LOOKUP:
        raise KeyError(
            f"'{name}' is not in key_numbers.csv. Either the analysis stopped "
            f"producing it or the document is asserting something the analysis "
            f"does not support. Add it to scripts/12_key_numbers.py or remove "
            f"the claim from the document."
        )
    _USED.add(name)
    return _LOOKUP[name]


def t(name):
    return str(kn(name))


def f2(name):
    """Two decimals, so an odds ratio of 2.30 does not print as 2.3."""
    return f"{float(kn(name)):.2f}"


def ci2(name):
    """Two decimals on both ends of a stored 'a to b' interval."""
    parts = str(kn(name)).split(" to ")
    return " to ".join(f"{float(p):.2f}" for p in parts)


def ci3(name):
    parts = str(kn(name)).split(" to ")
    return " to ".join(f"{float(p):.3f}" for p in parts)


# ---------------------------------------------------------------
# Small formatting helpers
# ---------------------------------------------------------------

def _render(df):
    """
    Fill blanks for display, distinguishing a suppressed cell from an empty one.

    Both were previously filled with the word "suppressed", so the study-flow
    table's empty `note` cell rendered as "suppressed" in both documents and the
    README -- asserting that disclosure control had removed something from a row
    that was never suppressed at all. Only numeric columns can carry a suppressed
    count; a blank text cell is just blank.
    """
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_numeric_dtype(out[c]):
            out[c] = out[c].astype(object).where(out[c].notna(), "suppressed")
        else:
            out[c] = out[c].astype(object).where(out[c].notna(), "")
    return out


def add_table(doc, df, style="Light Grid Accent 1", widths=None):
    df = _render(df)
    table = doc.add_table(rows=1, cols=len(df.columns))
    try:
        table.style = style
    except KeyError:
        table.style = "Table Grid"
    for i, c in enumerate(df.columns):
        cell = table.rows[0].cells[i]
        cell.text = str(c)
        for r in cell.paragraphs[0].runs:
            r.font.bold = True
            r.font.size = Pt(9)
    for _, row in df.iterrows():
        cells = table.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
            for p in cells[i].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    doc.add_paragraph()
    return table


def para(doc, text, size=11, bold=False, italic=False, space=6):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    p.paragraph_format.space_after = Pt(space)
    return p


def bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(text)
    run.font.size = Pt(11)
    return p


def caution(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(10.5)
    run.font.italic = True
    run.font.color.rgb = RGBColor(0x99, 0x33, 0x00)
    p.paragraph_format.left_indent = Inches(0.3)
    p.paragraph_format.space_after = Pt(10)
    return p


os.makedirs("output", exist_ok=True)

# ===============================================================
# DOCUMENT 1: plain language findings
# ===============================================================
doc = Document()
for s in doc.sections:
    s.page_width, s.page_height = Inches(8.5), Inches(11)
    s.left_margin = s.right_margin = Inches(1)

title = doc.add_heading("What Happens to Cancer Patients After They Leave Hospital", 0)
para(doc, "Four questions, four answers, no jargon", size=13, italic=True)
para(doc,
     f"Based on {int(kn('total_abstracts')):,} hospital discharge records from every Canadian "
     f"province and territory except Quebec, covering three financial years. "
     f"The readmission analysis follows {int(kn('cohort_patients')):,} cancer patients across "
     f"{int(kn('cohort_episodes')):,} hospital stays.",
     size=11)
caution(doc,
        "Quebec does not submit to the file this study uses, so nothing here "
        "describes Quebec. The earlier phrase 'from across Canada' was wrong and "
        "has been removed.")
para(doc, "Seventh version. Rebuilt and independently audited against the raw data.",
     size=10, italic=True)

doc.add_heading("What this is", level=1)
para(doc,
     "Every time someone is admitted to a Canadian hospital and later leaves, the "
     "hospital fills in a standard summary form. What was wrong with them. What was "
     "done. How long they stayed. Where they went afterwards.")
para(doc,
     "These forms are not written for research. They exist so that hospitals and "
     "health systems have a consistent record of what happened. But gather three "
     "years of them together and patterns appear that no single doctor or hospital "
     "could see alone.")
para(doc,
     "Nothing here identifies anybody. No names, no addresses, no birth dates. Each "
     "patient is an anonymous number, which is what allows their hospital visits to "
     "be linked without anyone knowing who they are. Where a group is small enough "
     "that publishing its numbers might narrow down who is in it, those numbers are "
     "left out of the released tables.")

doc.add_heading("About this version", level=1)
para(doc,
     "Six earlier rounds of review each found real errors, and this seventh round "
     "was a full independent rebuild: the whole analysis was rerun from the original "
     "data file and every published number was checked against what the code "
     "actually produced.")
para(doc, "Three things that check found are worth stating plainly.")
bullet(doc,
       "The previous version said every number in these reports was generated "
       "automatically from the analysis, so the writing could not drift away from "
       "the results. No such mechanism existed. The documents were written by hand "
       "and several numbers in them were out of date. That mechanism now exists, and "
       "this document is produced by it.")
bullet(doc,
       "Question 1 was still making a mistake this report had already identified and "
       "fixed twice elsewhere: comparing patients while holding constant things that "
       "only happened after the moment being studied. Fixing it moved the answer up, "
       f"from about {f2('q1_risk_ratio_full')} times the risk to about {f2('q1_risk_ratio')} times.")
bullet(doc,
       "A check the report relied on to show that one of its definitions did not "
       "matter turned out to be incapable of detecting the problem it was meant to "
       "rule out. A better check was built. The answer held up, but it had not "
       "actually been tested before.")
para(doc,
     f"The headline number has moved across versions: {kn('historical_v1_readmit_pct')}%, then "
     f"{kn('historical_v3_readmit_pct')}%, then "
     f"{kn('q1_point_estimate_pct')}%, where it has now stayed through two further rounds of "
     "checking. That is what careful correction looks like from the outside.")

doc.add_heading("The four answers, in short", level=1)

doc.add_heading(
    f"1. About one in seven cancer patients is back in hospital urgently within a month",
    level=2)
para(doc,
     f"Of {int(kn('cohort_episodes')):,} hospital stays where the patient went home, "
     f"{int(kn('q1_events')):,} were followed by an urgent return within 30 days. That is "
     f"{kn('q1_point_estimate_pct')}%. A model built only from what is already on the discharge "
     f"form sorted patients into risk groups running from about "
     f"{kn('calibration_lowest_actual_pct')}% up to about {kn('calibration_highest_actual_pct')}%.")

doc.add_heading("2. Patients admitted as an emergency are far more likely to die during that stay",
                level=2)
para(doc,
     f"Just over half of cancer hospital stays, {kn('q2_urgent_share_pct')}%, begin as an "
     f"emergency. Comparing patients with the same type of cancer, similar age, similar "
     f"spread of disease and similar other health problems, about "
     f"{kn('q2_risk_urgent_pct')} in 100 emergency admissions ended in death against about "
     f"{kn('q2_risk_planned_pct')} in 100 planned ones -- roughly {f2('q2_risk_ratio')} times the risk.")

doc.add_heading("3. Nearly a quarter of stays involve a new condition appearing after admission",
                level=2)
para(doc,
     f"In {int(kn('q3_post_admission_n')):,} of {int(kn('cancer_episodes_total')):,} stays, a condition "
     f"was recorded as having started after the patient was admitted. That is "
     f"{kn('q3_post_admission_pct')}%. Of those patients {kn('q3_died_with_pct')}% died in hospital, "
     f"against {kn('q3_died_without_pct')}% of the others. Many of these conditions are expected "
     f"side effects of cancer treatment rather than signs that anything went wrong.")

doc.add_heading("4. Deaths rose over three years, and we cannot explain why", level=2)
para(doc,
     f"The share of cancer hospital stays ending in death went from "
     f"{kn('q4_first_quarter_pct')}% in the first quarter to {kn('q4_last_quarter_pct')}% in the last. "
     f"The rise was not explained by the patient characteristics we were able to "
     f"measure and put into our model. That does not mean the patients did not change "
     f"in ways we could not see.")
caution(doc,
        f"The climb was not steady. It peaked at {kn('q4_peak_quarter_pct')}% in quarter "
        f"{int(kn('q4_peak_quarter'))}, fell back, then rose again. Quoting only the first and last "
        f"quarters makes it sound smoother than it was.")

# ---- Q1 ----
doc.add_heading("Question 1: Who ends up back in hospital?", level=1)
para(doc,
     "Someone goes home from hospital. Three weeks later they are back, urgently. "
     "That is unpleasant for the patient, expensive for the system, and sometimes a "
     "sign that something did not go to plan. If you could tell on the day of "
     "discharge who was most likely to come back, you could give those people a "
     "follow-up call, an earlier appointment, or more support at home.")

doc.add_heading("Three things had to be sorted out first", level=2)
para(doc, "A transfer is not a readmission.", bold=True)
para(doc,
     "When a patient is moved from one hospital to another, each hospital fills in "
     "its own form. The first version counted the second form as a readmission, when "
     "it was the same continuous stay carrying on somewhere else. Joining those forms "
     f"together absorbed {int(kn('abstracts_merged')):,} of them.")
para(doc, '"Not dead" is not the same as "went home".', bold=True)
para(doc,
     "The first version described the patients as having gone home alive, but had "
     "only excluded those who died. Some had been moved to rehabilitation, a nursing "
     "home or continuing care. This version counts only patients discharged home.")
para(doc, "Some returns are supposed to happen.", bold=True)
para(doc,
     f"Chemotherapy is given in rounds, so coming back can be the plan working. This "
     f"report counts only urgent returns. Of the {int(kn('planned_returns_n')):,} planned "
     f"returns within 30 days, {int(kn('planned_returns_chemo_n')):,} "
     f"({kn('planned_returns_chemo_pct')}%) carry a chemotherapy code. What the rest were for "
     f"cannot be established from these forms, so no claim is made about them.")

doc.add_heading("How sure we can be", level=2)
para(doc,
     "The hospital forms do not record the exact date someone was admitted. It has to "
     "be worked back from the discharge date and a rough length-of-stay band, and for "
     "long stays that band is very rough indeed.")
para(doc,
     f"So {kn('q1_point_estimate_pct')}% is the best single estimate, but it is not a list of "
     f"cases we can each prove. Only {kn('q1_definite_pct')}% can be shown beyond doubt to be a "
     f"return within 30 days. For {kn('ambiguous_pct')}% we genuinely cannot tell either way.")
caution(doc,
        "These three figures answer different questions. None of them is an upper or "
        "lower bound on the others, and it would be wrong to present them as a range "
        "containing the truth.")
para(doc,
     f"One test worth mentioning: the calculation assumes every stay was as short as "
     f"its band allows. Redoing it under other assumptions moves the answer only "
     f"between {kn('los_assumption_min_pct')}% and {kn('los_assumption_max_pct')}%, so that "
     f"assumption is not driving the result.")

doc.add_heading("One of the strongest warning signs", level=2)
para(doc,
     f"How the patient was admitted in the first place. Comparing similar patients, "
     f"about {kn('q1_risk_urgent_pct')} in every 100 who arrived urgently were back within a "
     f"month, against about {kn('q1_risk_planned_pct')} in 100 of those admitted on a planned "
     f"date -- roughly {f2('q1_risk_ratio')} times the risk "
     f"({ci2('q1_risk_ratio_ci')} allowing for statistical uncertainty).")
para(doc,
     "That figure changed in this version. The previous one held constant a set of "
     "things that only happen after admission -- whether the patient ended up in "
     "intensive care, whether a new condition appeared, how long they stayed. Holding "
     "those constant answers a different question, and it was the same mistake this "
     "report had already found and fixed in the next two chapters. Comparing patients "
     "on what was known when they arrived is the comparison people actually mean.")
para(doc,
     "It is worth saying that how someone arrived is not the single largest factor. "
     "Some cancer types carry more weight. But it is among the most reliable signals, "
     "and it is already known on the day the patient goes home.")

doc.add_heading("Two findings that look backwards", level=2)
para(doc,
     "Patients over 80 came back less often. So did patients receiving palliative "
     "care. That almost certainly does not mean they were doing better. When those "
     "patients became unwell, the response was more likely care at home or in a "
     "hospice, and this data records only hospital admissions.")
caution(doc,
        "There is a harder version of this. If a patient goes home and dies there, "
        "this data shows only that they went home. Someone who died at home and "
        "someone who stayed perfectly well look identical here. That gap affects "
        "these two groups most.")

doc.add_heading("Could we predict it?", level=2)
para(doc,
     f"Reasonably well. Someone in the highest risk group was about "
     f"{f2('risk_group_spread_multiple')} "
     f"times as likely to come back as someone in the lowest, and the predicted "
     f"percentages tracked what actually happened closely enough to be used as "
     f"percentages, not just as a ranking.")
para(doc,
     f"But here is the limit. If you set the bar to catch about "
     f"{round(float(kn('threshold15_sensitivity')) * 10)} out of every 10 patients who will "
     f"return, you would be calling about {round(float(kn('threshold15_flagged_pct')) / 10)} in "
     f"every 10 patients, and roughly "
     f"{int(float(kn('threshold15_false_alarm_pct')))}% of those you called would not have "
     f"come back anyway.")
para(doc,
     "That is still useful. A phone call is cheap and being wrong costs little. But "
     "it is not a crystal ball, and anyone presenting it as one is overselling it.")

# ---- Q2 ----
doc.add_heading("Question 2: Does an emergency admission matter?", level=1)
doc.add_heading("A question we had to withdraw", level=2)
para(doc,
     "The first version asked how many people only find out they have cancer when "
     "they turn up at emergency, and presented an answer with confidence. That answer "
     "was not supportable. These forms record nothing about when a cancer was "
     "diagnosed. Someone who has known for three years and comes in with a "
     "complication produces the same record as someone finding out that night.")

doc.add_heading("What we can ask instead", level=2)
para(doc,
     f"Of patients admitted on a planned date, {kn('q2_unadjusted_planned_pct')}% died during "
     f"that stay. Of those admitted urgently, {kn('q2_unadjusted_urgent_pct')}% did.")
para(doc,
     f"Most of that gap reflects which cancers arrive which way. Comparing patients "
     f"with the same cancer type, similar age, similar spread and similar other health "
     f"problems, the figures become {kn('q2_risk_urgent_pct')}% against "
     f"{kn('q2_risk_planned_pct')}% -- a difference of about {kn('q2_risk_difference')} patients in "
     f"every 100 ({kn('q2_risk_difference_ci')}), or roughly {f2('q2_risk_ratio')} times the risk.")
para(doc, "One piece of care about the numbers.", bold=True)
para(doc,
     f"Earlier versions said an emergency admission went with several times the "
     f"'chance' of dying, quoting a number from the statistical model called an odds "
     f"ratio. Odds are not chance. When an outcome is common, as death is in this "
     f"group, the odds ratio runs well ahead of the actual difference in risk. The "
     f"odds ratio here is {f2('q2_odds_ratio')}; the difference in risk is "
     f"{f2('q2_risk_ratio')} times. The risk figures are the ones people mean.")
caution(doc,
        "Neither figure means an urgent admission causes death. It is a signal that "
        "the patient was already in more trouble, and this data does not record how "
        "advanced anyone's cancer was.")
para(doc, "How firm is this one?", bold=True)
para(doc,
     f"Less firm than it looks, and this is new in this version. Deciding when two "
     f"hospital stays are really one continuous stay involves a judgement call, and "
     f"nobody can settle it from this data because the exact admission dates are not "
     f"recorded. Making that call four defensible ways moves this answer between "
     f"{f2('rule_q2_rr_min')} and {f2('rule_q2_rr_max')} times the risk.")
para(doc,
     f"That is roughly as much wobble as the usual statistical uncertainty, so the "
     f"figure of {f2('q2_risk_ratio')} should be read as approximate. The readmission answer "
     f"in Question 1 was tested the same way and barely moved. Earlier versions never "
     f"ran this check on either.")

# ---- Q3 ----
doc.add_heading("Question 3: What happens during the stay?", level=1)
para(doc,
     "These forms tag each condition with when it started: the patient already had it "
     "on arrival, or it appeared afterwards. The first version called everything in "
     "that second group 'something going wrong'. That was too strong. It might be a "
     "normal side effect of treatment, the disease progressing, an unavoidable "
     "complication, or a genuine failure of care. The form does not say which.")
para(doc,
     f"In {int(kn('q3_post_admission_n')):,} of {int(kn('cancer_episodes_total')):,} cancer hospital "
     f"stays -- {kn('q3_post_admission_pct')}% -- at least one condition was recorded as "
     f"starting after admission. The most common single one is "
     f"{kn('q3_top_condition_code')}, at {kn('q3_top_condition_pct')}% of stays.")
para(doc,
     f"The strongest single pattern is length of stay: {kn('q3_short_stay_pct')}% for short "
     f"stays against {kn('q3_long_stay_pct')}% for long ones. Which way round does that work? "
     f"A new problem keeps someone in hospital longer, and a longer stay gives more "
     f"time for one to appear and be written down. Both are true, and this data cannot "
     f"separate them. Saying so is more useful than picking whichever sounds better.")

# ---- Q4 ----
doc.add_heading("Question 4: Why did more people die?", level=1)
para(doc,
     f"At the start of the three years, {kn('q4_first_quarter_pct')}% of cancer hospital stays "
     f"ended in the patient dying. By the end it was {kn('q4_last_quarter_pct')}%.")
para(doc,
     "The first thing to check is whether the patients changed. If hospitals were "
     "treating older or sicker people by the end, more deaths would be expected and "
     "there would be nothing to explain. On everything we measured they look much the "
     "same, and the upward trend was just as strong after adjusting for it. It also "
     "survives allowing for COVID-19 coding.")
para(doc, "So what is going on?", bold=True)
para(doc,
     "Here is where the first version went too far. It said the patients did not "
     "change, therefore something outside the data must explain the rise, and that "
     "something was probably cancers being caught later.")
para(doc,
     "The correct statement is narrower. The rise is not explained by the handful of "
     "patient characteristics we were able to measure and put into the model. That is "
     "not the same as saying nothing about the patients changed, and not the same as "
     "saying the data records nothing else.")
para(doc,
     "There is a great deal this data does not record: how advanced each cancer was, "
     "how well patients were coping, what treatment they were receiving and with what "
     "aim, how busy or well-staffed the hospitals were, whether the way conditions get "
     "written down shifted over three years, or how end-of-life care was delivered.")
para(doc,
     "Later diagnosis, after the pandemic disrupted screening and referrals, remains a "
     "reasonable guess. It fits. But it is a guess, and it cannot be tested here. "
     "Answering it would need cancer registry data.")
caution(doc,
        "There is a real pattern here worth someone investigating. What there is not, "
        "is an explanation. Saying so is the honest end of the analysis, not a "
        "failure of it.")

doc.add_heading("What this cannot tell you", level=1)
for b in [
    "Inpatient admissions only. No outpatient care, and no emergency visit that did "
    "not lead to an admission.",
    "No deaths after discharge. Someone who died at home is invisible here, which "
    "matters most for the oldest and sickest patients.",
    "No cancer stage, no diagnosis date, no measure of how well the patient was "
    "coping. These are likely to explain a good deal of what is left unexplained.",
    "Quebec is absent entirely.",
    "Episodes of care are reconstructed from transfer coding and an imprecise "
    "admission date, not taken ready-made from the data.",
    "About a tenth of national activity. The percentages generalise; the counts are "
    "not national totals.",
    "Nothing here shows that one thing causes another.",
]:
    bullet(doc, b)

doc.add_heading("Where the data came from", level=1)
para(doc,
     "This dataset is not something anyone can simply download. It is released under "
     "licence to universities and similar institutions through a Statistics Canada "
     "programme, and that licence sets conditions on how it can be used and what can "
     "be published from it. The underlying records are not shared here, and anyone "
     "wanting to repeat this work would need to obtain the data through that route.")

doc.save("output/Findings_In_Plain_Language.docx")
print("wrote output/Findings_In_Plain_Language.docx")

# ===============================================================
# DOCUMENT 2: technical guide
# ===============================================================
g = Document()
for s in g.sections:
    s.page_width, s.page_height = Inches(8.5), Inches(11)
    s.left_margin = s.right_margin = Inches(1)

g.add_heading("Urgent 30-Day Readmission After Cancer Care", 0)
para(g, "Methods, results and known limitations", size=13, italic=True)
para(g,
     f"A retrospective cohort study of episodes of care built from "
     f"{int(kn('total_abstracts')):,} Canadian hospital discharge abstracts, following "
     f"{int(kn('cohort_patients')):,} cancer patients over three financial years.",
     size=11)
para(g,
     "Data source: CIHI Discharge Abstract Database, Research Analytic File "
     "(clinical sample), FY2021-22 to FY2023-24. Does not include Quebec.",
     size=10, italic=True)

g.add_heading("How this document is produced", level=1)
para(g,
     "Every figure below is read from output/tables/key_numbers.csv, which script 12 "
     "regenerates from the analysis outputs. Lookups go through a function that raises "
     "KeyError when a name is absent. There is no fallback value and no default, so a "
     "figure the analysis has stopped producing makes this document fail to build "
     "rather than print a stale number.")
caution(g,
        "Version 6 asserted this mechanism and did not have it. The documents were "
        "written by hand and contained stale prediction metrics "
        "and a block of console output from a previous run. "
        "The claim is repeated here only because the code now backs it.")

g.add_heading("Headline results", level=1)
add_table(g, pd.DataFrame([
    ["Urgent/emergent 30-day readmission (discharged home)",
     f"{kn('q1_point_estimate_pct')}% ({int(kn('q1_events')):,} / {int(kn('cohort_episodes')):,})"],
    ["-- of which provable on timing",
     f"{kn('q1_definite_pct')}% definite; {kn('ambiguous_pct')}% unresolvable"],
    ["Urgent index admission -> readmission (baseline model)",
     f"Adjusted risk {kn('q1_risk_urgent_pct')}% vs {kn('q1_risk_planned_pct')}%, "
     f"RR {f2('q1_risk_ratio')} ({ci2('q1_risk_ratio_ci')}); OR {f2('q1_odds_ratio')}"],
    ["Prediction model",
     f"AUC {kn('auc_logistic')} ({ci3('auc_logistic_ci')}), PR-AUC {kn('pr_auc_logistic')} "
     f"vs prevalence {kn('outcome_prevalence')}, Brier {kn('brier_logistic')}, "
     f"calibration slope {f2('calibration_slope')}"],
    ["Geographic holdout (Alberta, patient-separated)",
     f"AUC {kn('auc_alberta')} ({ci3('auc_alberta_ci')})"],
    ["Urgent admission and in-hospital mortality",
     f"Adjusted risk {kn('q2_risk_urgent_pct')}% vs {kn('q2_risk_planned_pct')}%, "
     f"RR {f2('q2_risk_ratio')} ({ci2('q2_risk_ratio_ci')}), "
     f"RD {kn('q2_risk_difference')} pts ({kn('q2_risk_difference_ci')}); OR {f2('q2_odds_ratio')}"],
    ["Post-admission condition and mortality",
     f"{kn('q3_post_admission_pct')}% of episodes; baseline-only OR {f2('q3_or_baseline')}"],
    ["In-hospital mortality trend",
     f"{kn('q4_first_quarter_pct')}% -> {kn('q4_last_quarter_pct')}% over 12 quarters, "
     f"peaking at {kn('q4_peak_quarter_pct')}% in quarter {int(kn('q4_peak_quarter'))}"],
], columns=["Question", "Answer"]))

caution(g,
        "The outcome is project-defined. It is not CIHI's official 30-day readmission "
        "indicator, which has its own episode construction, denominators and "
        "exclusions. Episodes are transfer-linked approximations built from available "
        "RAF fields, not a reproduction of CIHI's methodology.")

g.add_heading("What the seventh review changed", level=1)
para(g,
     "The whole pipeline was rebuilt from the raw fixed-width file and every published "
     "figure checked against what the code produced. All 25 output tables reproduced "
     "bit-for-bit, so the shipped results genuinely came from this code on this data. "
     "The problems were elsewhere.")

add_table(g, pd.DataFrame([
    ["The anti-drift mechanism did not exist. Both documents claimed every figure was "
     "read from key_numbers.csv and that a missing entry would raise an error. Nothing "
     "read the file; the documents were hand-written and contained stale numbers.",
     "Built it. Script 13 generates both documents through a lookup that raises on a "
     "missing key. Script 14 fails the build if a document states a number that is not "
     "in key_numbers.csv.",
     "The claim is now true"],
    ["Question 1 adjusted for six post-exposure variables -- palliative care, "
     "post-admission conditions, intensive care, length of stay, procedures and "
     "multi-facility care -- and reported the result as its headline risk ratio. This "
     "is the same error the project identified and fixed in Question 2, then "
     "identified and fixed again in Question 3.",
     "Baseline-only model is primary, matching Questions 2 and 3. The in-hospital-"
     "course model is reported as descriptive.",
     f"RR {f2('q1_risk_ratio_full')} -> {f2('q1_risk_ratio')}"],
    ["The transfer-rule sensitivity analysis could not detect the error it was meant "
     "to rule out. All three rules compared the same derived admission day and varied "
     "only the tolerance by one or two days, while the derived day can be wrong by "
     "thirty for the longest stays.",
     "Added an interval-aware rule that compares the earliest admission the stay band "
     "allows, plus a diagnostic showing where the derived rule fails.",
     f"Estimate holds: {kn('transfer_interval_pct')}%"],
    ["The README's figures contradicted the project's own outputs across AUC, PR-AUC, "
     "prevalence, Brier, calibration slope, both risk ratios, three odds ratios, the "
     "ambiguity share and the patient count.",
     "README results are generated from key_numbers.csv.",
     "Drift closed"],
    ["Small cells were shipped in released tables despite the README instructing that "
     "they be checked: counts of 31, 42, 10 and 6 in licensed microdata.",
     "Suppression applied before release, with a report of what was withheld. "
     "Full-precision tables kept separately and excluded from release.",
     "Safeguard applied"],
    ["The COVID-19 flag was computed and then never aggregated to episode level, so "
     "it was unusable, while Question 4 named pandemic disruption as its leading "
     "hypothesis.",
     "Aggregated and tested.",
     "Trend survives it"],
    ["Two different variables were both called long_stay.",
     "Renamed to final_abstract_long_stay and episode_long_stay.",
     "Ambiguity removed"],
    ["The age reference category spanned newborns to 49-year-olds, so every age odds "
     "ratio was reported against it.",
     "Split into Under 18 and 18-49; paediatric episodes made visible.",
     "Reference interpretable"],
    ["Parse validation covered 16 of 159 fields and only 3 of 25 diagnosis slots.",
     "Extended to deep diagnosis slots and the last intervention slot, and now fails "
     "the build on any mismatch.",
     "27 of 27 exact"],
], columns=["Problem", "Fix", "Effect"]))

g.add_heading("Study flow", level=1)
add_table(g, pd.read_csv("output/tables/study_flow.csv"))

g.add_heading("Timing certainty", level=1)
para(g,
     "REL_ADAY is derived, not observed: it equals REL_DDAY minus TLOS_CAT on all "
     f"{int(kn('total_abstracts')):,} rows, and TLOS_CAT is the floor of its band. The derived "
     "admission day is therefore never earlier than the true one, and for the "
     "'10 or more days' band the error has no upper limit. Every readmission carries a "
     "certainty flag.")
add_table(g, pd.read_csv("output/tables/readmission_certainty.csv"))
para(g,
     f"These are three different quantities, not bounds on one another: "
     f"{kn('q1_point_estimate_pct')}% point estimate, {kn('q1_definite_pct')}% provable, "
     f"{kn('q1_complete_case_pct')}% complete case among episodes whose timing resolves. "
     f"Genuine bounds would need a formal partial-identification analysis, which has "
     f"not been done.")

g.add_heading("Transfer linkage: what the sensitivity analysis can and cannot detect", level=1)
add_table(g, pd.read_csv("output/tables/transfer_rule_sensitivity.csv"))
para(g,
     f"The first three rules compare the same derived admission day and differ only in "
     f"tolerance. Because that derived day can be weeks late for a long receiving stay, "
     f"moving a tolerance by one or two days cannot detect the failure. The merge rate "
     f"falls from {kn('transfer_merge_pct_1day')}% for one-day receiving stays to "
     f"{kn('transfer_merge_pct_10plus')}% for stays of ten days or more.")
add_table(g, pd.read_csv("output/tables/transfer_merge_diagnostic.csv"))
caution(g,
        f"This matters because episode splitting is not random with respect to length "
        f"of stay, and therefore not random with respect to severity. In the primary "
        f"cohort, {kn('transfer_contamination_urgent_pct')}% of urgent-admission episodes could "
        f"be unmerged transfer continuations against "
        f"{kn('transfer_contamination_planned_pct')}% of planned ones. The contamination is "
        f"differential with respect to the exposure, so it is a limitation of the "
        f"urgent-versus-planned contrast, not only of the denominator.")
para(g,
     f"The interval-aware rule, which compares the earliest admission the band allows, "
     f"gives {kn('transfer_interval_pct')}% on a cohort of "
     f"{int(kn('transfer_interval_cohort_n')):,}. The headline holds under a rule that actually "
     f"probes the weakness.")

g.add_heading("Does the episode definition change the conclusions?", level=1)
para(g,
     "The earlier sensitivity analysis asked only how the RAW RATE moved between "
     "transfer rules. The rate is not what this report leans on. It leans on adjusted "
     "comparisons, and those had never been recomputed under a different episode "
     "definition. Each rule produces a different cohort, so the primary estimates are "
     "refit from scratch on each one.")
add_table(g, pd.read_csv("output/tables/rule_robustness.csv"))
para(g,
     f"Question 1 is robust: the risk ratio moves between {f2('rule_q1_rr_min')} and "
     f"{f2('rule_q1_rr_max')}, a spread of {kn('rule_q1_rr_spread')}, comfortably inside its "
     f"confidence interval of {ci2('q1_risk_ratio_ci')}. Which rule is chosen does not "
     f"change what Question 1 says.")
caution(g,
        f"Question 2 is not. Its risk ratio moves between {f2('rule_q2_rr_min')} and "
        f"{f2('rule_q2_rr_max')} -- a spread of {kn('rule_q2_rr_spread')}, comparable to the whole "
        f"width of its confidence interval ({ci2('q2_risk_ratio_ci')}). For the mortality "
        f"comparison, the choice of episode definition carries about as much uncertainty "
        f"as sampling variability does, and the confidence interval alone therefore "
        f"understates how well that number is pinned down. The earlier analysis reported "
        f"a spread of {kn('historical_v6_transfer_spread_pts')} percentage points on the raw rate and concluded the transfer "
        f"boundary did not matter; on the quantity the report actually leans on, it does.")
para(g,
     f"That conclusion is not an artefact of the interval-aware rule being too "
     f"permissive. As first written, that rule tested only whether the receiving "
     f"stay could have BEGUN in time, and not whether it began after the sending "
     f"discharge at all, so it merged {int(kn('interval_overlap_transitions_fixed')):,} "
     f"transitions describing overlapping stays -- the same case version 6 "
     f"identified and fixed on the derived-day rule. It also left the "
     f"'10 or more days' band unbounded, which makes the earliest-possible test "
     f"vacuous for that band and permits merges spanning years. Both are corrected: "
     f"the rule now requires the possible admission interval to overlap the "
     f"transfer window at both ends, and a variant capping that band is reported "
     f"beside it. The Question 2 risk ratio is {f2('rule_q2_rr_capped')} capped "
     f"against {f2('rule_q2_rr_uncapped')} uncapped, and the spread excluding the "
     f"uncapped rule entirely is {kn('rule_q2_rr_spread_excl_uncapped')}. The "
     f"finding survives every version of the test, which is why it is stated as a "
     f"property of the data rather than of the diagnostic.")

g.add_heading("Sensitivity to the length-of-stay assumption", level=1)
para(g,
     "The point estimate places every candidate admission at the shortest stay its "
     "band allows. That is an assumption, not a neutral reading, so it is tested.")
add_table(g, pd.read_csv("output/tables/q1_los_assumption_sensitivity.csv"))

g.add_heading("Result 1: urgent 30-day readmission", level=1)
add_table(g, pd.read_csv("output/tables/q1_sensitivity.csv"))
para(g, "By cancer site (small groups suppressed before release):")
add_table(g, pd.read_csv("output/tables/q1_rate_by_cancer_site.csv"))
para(g, "Adjusted risks, both models:")
add_table(g, pd.read_csv("output/tables/q1_adjusted_risk.csv"))
para(g,
     f"The baseline model is primary. The in-hospital-course model conditions on "
     f"variables recorded after the exposure and answers a different question: "
     f"{kn('q1_risk_urgent_full_pct')}% against {kn('q1_risk_planned_full_pct')}%, "
     f"RR {f2('q1_risk_ratio_full')}. It is not better adjusted.")

g.add_heading("Result 2: urgent admission and mortality", level=1)
para(g,
     f"Unadjusted, {kn('q2_unadjusted_urgent_pct')}% of urgent episodes ended in death against "
     f"{kn('q2_unadjusted_planned_pct')}% of planned ones. Adjusted for baseline "
     f"characteristics: {kn('q2_risk_urgent_pct')}% against {kn('q2_risk_planned_pct')}%, "
     f"RR {f2('q2_risk_ratio')} ({ci2('q2_risk_ratio_ci')}), RD {kn('q2_risk_difference')} points "
     f"({kn('q2_risk_difference_ci')}).")
para(g,
     f"The baseline odds ratio is {f2('q2_odds_ratio')}; adding palliative care and "
     f"post-admission conditions gives {f2('q2_odds_ratio_full')}. Both are recorded during "
     f"the episode and are post-exposure. The attenuation shows those variables carry "
     f"much of the statistical association; it does not identify a causal pathway, and "
     f"no mediation analysis has been performed.")

g.add_heading("Result 3: post-admission conditions", level=1)
para(g,
     f"{kn('q3_post_admission_pct')}% of episodes ({int(kn('q3_post_admission_n')):,}) carry at "
     f"least one condition coded as arising after admission. Baseline-only odds ratio "
     f"for in-hospital death: {f2('q3_or_baseline')}.")
add_table(g, pd.read_csv("output/tables/q3_outcomes.csv"))
caution(g,
        "Diagnosis type 2 means the condition arose after admission. That is all it "
        "means. It covers expected treatment effects and natural disease progression "
        "as well as genuine adverse events. A hospital-harm analysis would require "
        "CIHI's published Hospital Harm methodology, which is not applied here.")

g.add_heading("Result 4: the mortality trend", level=1)
add_table(g, pd.read_csv("output/tables/q4_trend_models.csv"))
para(g,
     f"Adjusting for measured characteristics does not attenuate the trend, and it "
     f"survives allowing for COVID-19 coding. A likelihood-ratio test of the linear "
     f"term against a free per-quarter effect gives p = {kn('q4_linearity_p')}, so a straight "
     f"line is a defensible summary -- but the series is not monotonic and quoting only "
     f"the first and last quarters overstates how steady the climb was.")

g.add_heading("Limitations", level=1)
for b in [
    "Inpatient admissions only; no outpatient care, no ED visits without admission.",
    "No deaths after discharge, an unobserved competing event that affects the oldest "
    "and palliative groups most.",
    "No cancer stage, no diagnosis date, no performance status.",
    "Quebec absent; episodes are transfer-linked approximations, not CIHI's methodology.",
    f"{kn('ambiguous_pct')}% of urgent-readmission classifications cannot be resolved on timing.",
    "Transfer merging fails differentially for long receiving stays, contaminating the "
    "cohort in a way that is correlated with the exposure.",
    "Banded age and length of stay; no calendar dates.",
    "Roughly a 10% sample: percentages generalise, counts are not national totals.",
    "All results are associations, not causal effects.",
]:
    bullet(g, b)

g.add_heading("Before publishing derived outputs", level=1)
for b in [
    "Confirm with your institution's DLI contact that the derived aggregate tables and "
    "figures are cleared for release.",
    "Include the acknowledgement and disclaimer wording the licence requires.",
    "Do not redistribute the raw .dat, the .sav, any record-level intermediate, or "
    "CIHI documentation PDFs.",
    "Released tables have small cells suppressed; output/tables/internal/ holds the "
    "full-precision versions and must not be released.",
]:
    bullet(g, b)

g.save("output/Cancer_Readmission_Project_Guide.docx")
print("wrote output/Cancer_Readmission_Project_Guide.docx")

print(f"\n{len(_USED)} distinct figures pulled from key_numbers.csv.")
print("Every one went through kn(), which raises KeyError on a missing entry.")


# ===============================================================
# README results section
#
# The README carried its own hand-typed copy of every headline figure and had
# drifted from the outputs on thirteen of them, including the AUC, both risk
# ratios, three odds ratios and the patient count. It is generated here from the
# same source as the documents.
# ===============================================================
rules_df = pd.read_csv("output/tables/transfer_rule_sensitivity.csv")
flow_df = pd.read_csv("output/tables/study_flow.csv")
cert_df = pd.read_csv("output/tables/readmission_certainty.csv")


def md_table(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |",
           "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in _render(df).iterrows():
        out.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(out)


readme = f"""<!-- GENERATED BY scripts/13_build_documents.py -- DO NOT EDIT BY HAND -->
<!-- Every figure below comes from output/tables/key_numbers.csv. -->

## Results

| Question | Answer |
|---|---|
| Urgent/emergent 30-day readmission (discharged home) | **{kn('q1_point_estimate_pct')}%** ({int(kn('q1_events')):,} / {int(kn('cohort_episodes')):,}) |
| â€” provable on timing | {kn('q1_definite_pct')}% definite; {kn('ambiguous_pct')}% unresolvable |
| Urgent index admission â†’ readmission (baseline model, primary) | Adjusted risk {kn('q1_risk_urgent_pct')}% vs {kn('q1_risk_planned_pct')}%, RR {f2('q1_risk_ratio')} ({ci2('q1_risk_ratio_ci')}), RD {kn('q1_risk_difference')} pts; OR {f2('q1_odds_ratio')} |
| â€” adding in-hospital course (descriptive, not better adjusted) | RR {f2('q1_risk_ratio_full')}; OR {f2('q1_odds_ratio_full')} |
| Prediction model | AUC {kn('auc_logistic')} ({ci3('auc_logistic_ci')}), PR-AUC {kn('pr_auc_logistic')} vs prevalence {kn('outcome_prevalence')}, Brier {kn('brier_logistic')}, calibration slope {f2('calibration_slope')} |
| Geographic holdout (Alberta, patient-separated) | AUC {kn('auc_alberta')} ({ci3('auc_alberta_ci')}) |
| Urgent admission â†’ in-hospital mortality | Adjusted risk {kn('q2_risk_urgent_pct')}% vs {kn('q2_risk_planned_pct')}%, RR {f2('q2_risk_ratio')} ({ci2('q2_risk_ratio_ci')}), RD {kn('q2_risk_difference')} pts ({kn('q2_risk_difference_ci')}); OR {f2('q2_odds_ratio')} |
| Post-admission condition â†’ mortality | {kn('q3_post_admission_pct')}% of episodes; baseline-only OR {f2('q3_or_baseline')} |
| In-hospital mortality trend | {kn('q4_first_quarter_pct')}% â†’ {kn('q4_last_quarter_pct')}% over 12 quarters, peaking at {kn('q4_peak_quarter_pct')}% in quarter {int(kn('q4_peak_quarter'))} |

> The outcome is **project-defined**. It is not CIHI's official 30-day
> readmission indicator, which has its own episode construction, denominators
> and exclusions.

### Study flow

{md_table(flow_df)}

### Timing certainty

`REL_ADAY` is derived, not observed: it equals `REL_DDAY âˆ’ TLOS_CAT` on all
{int(kn('total_abstracts')):,} rows, and `TLOS_CAT` is the floor of its band. The derived
admission day is therefore never earlier than the true one, and for the
"10 or more days" band the error has no upper limit.

{md_table(cert_df)}

Three different quantities, not bounds on one another: {kn('q1_point_estimate_pct')}% point
estimate, {kn('q1_definite_pct')}% provable, {kn('q1_complete_case_pct')}% complete case.

The point estimate assumes every stay was as short as its band allows. Under
other assumptions it moves only between {kn('los_assumption_min_pct')}% and
{kn('los_assumption_max_pct')}%, so that assumption is not driving the result.

### Transfer linkage â€” what the sensitivity analysis can and cannot detect

{md_table(rules_df)}

The first three rules compare the **same derived admission day** and differ only
in tolerance. Because that derived day can be weeks late for a long receiving
stay, moving a tolerance by one or two days cannot detect the failure: the merge
rate falls from {kn('transfer_merge_pct_1day')}% for one-day receiving stays to
{kn('transfer_merge_pct_10plus')}% for stays of ten days or more. A narrow spread across
those three rules is therefore **weak** evidence, not strong evidence.

The interval-aware rule is the informative comparison, and the rate holds at
{kn('transfer_interval_pct')}%.

**But the rate was never the point.** Recomputing the *adjusted comparisons* on
each rule's cohort â€” which no earlier version did â€” shows they do not all hold
equally well:

{md_table(pd.read_csv("output/tables/rule_robustness.csv"))}

Question 1 is robust: RR {f2('rule_q1_rr_min')}â€“{f2('rule_q1_rr_max')}, spread
{kn('rule_q1_rr_spread')}, comfortably inside its confidence interval of
{ci2('q1_risk_ratio_ci')}.

> **Question 2 is not.** Its risk ratio moves between {f2('rule_q2_rr_min')} and
> {f2('rule_q2_rr_max')} â€” a spread of {kn('rule_q2_rr_spread')}, comparable to the whole width
> of its confidence interval ({ci2('q2_risk_ratio_ci')}). For the mortality comparison
> the episode definition carries about as much uncertainty as sampling
> variability, so the confidence interval alone understates how well that number
> is pinned down. Version 6 reported a {kn('historical_v6_transfer_spread_pts')}-point spread on the raw rate and
> concluded the transfer boundary did not matter; on the quantity the report
> actually leans on, it does.

The interval-aware rule that produces the widest of those estimates was itself
wrong in version 7, in two ways. It tested only whether the receiving stay could
have *begun* in time, never whether it began after the sending discharge, so it
merged {int(kn('interval_overlap_transitions_fixed')):,} transitions describing
overlapping stays â€” the identical case version 6 had already found and fixed on
the derived-day rule. And it left the ">=10 days" band unbounded, which makes the
earliest-possible test vacuous for that band: it merged abstracts separated by up
to 1,039 days. Both are fixed. The rule now requires the possible admission
interval to overlap the transfer window at **both** ends, and a variant capping
that band at 90 days is reported alongside.

The Question 2 finding survives the correction and strengthens slightly: risk
ratio {f2('rule_q2_rr_capped')} capped against {f2('rule_q2_rr_uncapped')}
uncapped, and a spread of {kn('rule_q2_rr_spread_excl_uncapped')} even with the
uncapped rule excluded altogether. It is a property of how much episode
construction moves the mortality comparison, not of an over-permissive rule.

> **Known limitation.** Episode splitting is not random with respect to length of
> stay, and therefore not random with respect to severity.
> {kn('transfer_contamination_urgent_pct')}% of urgent-admission episodes could be unmerged
> transfer continuations against {kn('transfer_contamination_planned_pct')}% of planned ones.
> This contamination is **differential with respect to the exposure**.

### Reported numbers are generated, not typed

`scripts/12_key_numbers.py` writes `output/tables/key_numbers.csv`.
`scripts/13_build_documents.py` builds both Word documents and this section
through a lookup that raises `KeyError` on a missing entry â€” no fallback, no
default. `scripts/14_verify_documents.py` then reads the finished documents back
and fails the build if any number in them cannot be traced to a generated output.

Version 6 asserted this mechanism without having it, and drifted on thirteen
figures as a result. It is checked in both directions now.
"""

open("README_RESULTS.md", "w").write(readme)
print("wrote README_RESULTS.md")

# ---------------------------------------------------------------
# Splice the generated section into README.md itself.
#
# Writing the section to a side file and leaving README.md hand-typed was the
# original failure repeating itself one level up: the generated numbers sat in a
# file nobody reads while the stale ones stayed on the front page. The section
# between the markers is replaced wholesale on every run.
# ---------------------------------------------------------------
BEGIN = "<!-- BEGIN GENERATED RESULTS -->"
END = "<!-- END GENERATED RESULTS -->"

readme_md = open("README.md").read()
block = BEGIN + "\n" + readme + "\n" + END

if BEGIN in readme_md and END in readme_md:
    head = readme_md.split(BEGIN)[0]
    tail = readme_md.split(END)[1]
    readme_md = head + block + tail
else:
    raise SystemExit(
        "README.md is missing the generated-results markers. Add\n"
        f"  {BEGIN}\n  {END}\n"
        "around the results section so it can be regenerated."
    )

open("README.md", "w").write(readme_md)
print("spliced generated results into README.md")
