"""Number and interval formatting. No data access, no Streamlit calls."""

from __future__ import annotations

import math
import re

SUPPRESSED = "Suppressed"

_CI_PATTERN = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*(?:to|-|–|,)\s*(-?\d+(?:\.\d+)?)\s*$"
)


def is_missing(value) -> bool:
    """True for a value withheld in the source table."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip().lower() in {"", "nan", "suppressed"}:
        return True
    return False


def count(value, *, dash_if_missing: bool = False) -> str:
    """12345 -> '12,345'."""
    if is_missing(value):
        return "—" if dash_if_missing else SUPPRESSED
    return f"{int(round(float(value))):,}"


def pct(value, dp: int = 1, *, sign: bool = False) -> str:
    """12.34 -> '12.3%'."""
    if is_missing(value):
        return SUPPRESSED
    formatted = f"{float(value):{'+' if sign else ''}.{dp}f}"
    return f"{formatted}%"


def points(value, dp: int = 1, *, sign: bool = False) -> str:
    """1.5 -> '1.5 pts' (percentage points, not percent)."""
    if is_missing(value):
        return SUPPRESSED
    return f"{float(value):{'+' if sign else ''}.{dp}f} pts"


def number(value, dp: int = 2) -> str:
    """1.23 -> '1.23'."""
    if is_missing(value):
        return SUPPRESSED
    return f"{float(value):.{dp}f}"


def parse_interval(text) -> tuple[float, float] | None:
    """'1.10 to 1.90' -> (1.10, 1.90). Returns None if it does not parse."""
    if is_missing(text):
        return None
    match = _CI_PATTERN.match(str(text))
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def interval(text, *, label: str = "95% CI", suffix: str = "") -> str:
    """'1.10 to 1.90' -> '95% CI 1.10 to 1.90'."""
    if is_missing(text):
        return ""
    match = _CI_PATTERN.match(str(text))
    if match is None:
        return f"{label} {text}"
    low, high = match.group(1), match.group(2)
    return f"{label} {low}{suffix} to {high}{suffix}"


def interval_from(low, high, *, label: str = "95% CI", dp: int = 2,
                  suffix: str = "") -> str:
    if is_missing(low) or is_missing(high):
        return ""
    return f"{label} {float(low):.{dp}f}{suffix} to {float(high):.{dp}f}{suffix}"


def p_value(value) -> str:
    """0.0623 -> 'p = 0.062'; very small values get a threshold."""
    if is_missing(value):
        return SUPPRESSED
    value = float(value)
    if value < 0.001:
        return "p < 0.001"
    return f"p = {value:.3f}"


def quarter_phrase(quarters) -> str:
    """[7] -> 'quarter 7'; [7, 8] -> 'quarters 7 and 8'."""
    quarters = [int(q) for q in quarters]
    if not quarters:
        return ""
    if len(quarters) == 1:
        return f"quarter {quarters[0]}"
    listed = ", ".join(str(q) for q in quarters[:-1])
    return f"quarters {listed} and {quarters[-1]}"


def proportion(value, dp: int = 3) -> str:
    """0.5 -> '0.500'."""
    if is_missing(value):
        return SUPPRESSED
    return f"{float(value):.{dp}f}"


# --------------------------------------------------------------------------
# label tidying for model output
# --------------------------------------------------------------------------

_PREFIXES = [
    ("baseline_cancer_site:", "Cancer site:"),
    ("cancer_site:", "Cancer site:"),
    ("age_band:", "Age"),
    ("sex:", "Sex:"),
    ("baseline_cancer_has_spread:", "Secondary deposits coded:"),
]

_PATSY = re.compile(
    r"^C\(\s*([A-Za-z0-9_]+)\s*,\s*Treatment\(\s*'?\"?(.*?)'?\"?\s*\)\s*\)"
    r"\[T\.(.*?)\]$"
)
_SIMPLE_T = re.compile(r"^([A-Za-z0-9_]+)\[T\.(.*?)\]$")

_VARIABLE_NAMES = {
    "baseline_cancer_site": "Cancer site",
    "cancer_site": "Cancer site",
    "age_band": "Age",
    "sex": "Sex",
    "province": "Province",
    "baseline_cancer_has_spread": "Secondary deposits coded",
    "cancer_is_main_reason": "Cancer was the main reason",
    "urgent_admission": "Urgent/emergent admission",
    "comorbidity_count": "Recorded comorbidities (per condition)",
    "final_los_group": "Final stay length band",
    "episode_long_stay": "Episode of 6 days or longer",
    "final_abstract_long_stay": "Final stay of 6 days or longer",
    "had_procedure": "A procedure was recorded",
    "palliative_care": "Palliative care coded",
    "post_admission_condition": "Condition coded as arising after admission",
    "intensive_care": "Special care unit stay",
    "multi_facility": "Episode spanned more than one facility",
    "quarter": "Quarter",
    "sex": "Sex",
    "cancer_has_spread": "Secondary deposits coded",
    "age_band": "Age",
    "covid_coded": "COVID-19 coded",
}


def variable_name(raw: str) -> str:
    key = str(raw).strip()
    if key in _VARIABLE_NAMES:
        return _VARIABLE_NAMES[key]
    return key.replace("_", " ").capitalize()


def tidy_factor(raw) -> str:
    """Turn a model term into something readable.

    "C(baseline_cancer_site, Treatment('Breast'))[T.Digestive]"
        -> "Cancer site: Digestive (vs Breast)"
    "age_band: 50-59" -> "Age 50-59"
    """
    if is_missing(raw):
        return ""
    text = str(raw).strip()

    match = _PATSY.match(text)
    if match:
        variable, reference, level = match.groups()
        return f"{variable_name(variable)}: {level} (vs {reference})"

    match = _SIMPLE_T.match(text)
    if match:
        variable, level = match.groups()
        if level in {"True", "T.True"}:
            return variable_name(variable)
        return f"{variable_name(variable)}: {level}"

    for prefix, replacement in _PREFIXES:
        if text.lower().startswith(prefix):
            remainder = text[len(prefix):].strip()
            remainder = {"M": "male", "F": "female"}.get(remainder, remainder)
            if replacement.endswith(":"):
                return f"{replacement} {remainder}"
            return f"{replacement} {remainder}"

    if text == "Intercept":
        return "Intercept"
    return variable_name(text)


def tidy_feature(raw) -> str:
    """Turn a one-hot model feature into something readable.

    "cancer_site_Haematologic" -> "Cancer site: Haematologic"
    "sex_M" -> "Sex: male"
    """
    if is_missing(raw):
        return ""
    text = str(raw).strip()
    if text in _VARIABLE_NAMES:
        return _VARIABLE_NAMES[text]
    for key in sorted(_VARIABLE_NAMES, key=len, reverse=True):
        if text.startswith(key + "_"):
            level = text[len(key) + 1:].replace("_", " ").strip()
            level = {"M": "male", "F": "female", "True": "", "1": ""}.get(level, level)
            if not level:
                return _VARIABLE_NAMES[key]
            return f"{_VARIABLE_NAMES[key]}: {level}"
    return variable_name(text)
