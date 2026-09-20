"""Lookups into ``key_numbers.csv``.

Every headline figure shown anywhere in this dashboard comes through here.
Nothing is typed into a page, and a missing entry raises instead of falling
back to a default, so a rerun of the analysis that drops or renames an output
fails loudly rather than publishing a stale number.
"""

from __future__ import annotations

import difflib

import pandas as pd

from src.data_loader import DataError, key_numbers


class MissingKeyNumber(DataError):
    """Raised when a requested figure is not in key_numbers.csv."""


def _entry(name: str) -> dict[str, str]:
    table = key_numbers()
    try:
        return table[name]
    except KeyError as exc:
        close = difflib.get_close_matches(name, table.keys(), n=3, cutoff=0.6)
        hint = f" Closest names: {', '.join(close)}." if close else ""
        raise MissingKeyNumber(
            f"'{name}' is not in key_numbers.csv, so this figure cannot be "
            f"shown.{hint} Regenerate the analysis outputs or correct the name."
        ) from exc


def get_key_number(name: str) -> float:
    """Return a generated figure as a number."""
    raw = _entry(name)["value"]
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise MissingKeyNumber(
            f"'{name}' holds the non-numeric value {raw!r}. Use get_key_text() "
            f"for entries such as confidence intervals."
        ) from exc


def get_key_text(name: str) -> str:
    """Return a generated figure as text, for intervals and labels."""
    return _entry(name)["value"]


def describe(name: str) -> str:
    """The description the pipeline recorded alongside the figure."""
    return _entry(name)["description"]


def has_key_number(name: str) -> bool:
    return name in key_numbers()


def as_frame() -> pd.DataFrame:
    """Every generated figure, for the Methods page."""
    table = key_numbers()
    return pd.DataFrame(
        [
            {"name": name, "value": item["value"], "description": item["description"]}
            for name, item in table.items()
        ]
    )


def count_of_key_numbers() -> int:
    return len(key_numbers())


def peak_quarters(trend: pd.DataFrame, value_column: str = "pct_died",
                  quarter_column: str = "quarter") -> list[int]:
    """Every quarter tied at the maximum, read from the series.

    The peak is derived rather than assumed to be one quarter, or a quarter and
    the one after it: two quarters can share the maximum.
    """
    missing = [c for c in (value_column, quarter_column) if c not in trend.columns]
    if missing:
        raise DataError(
            f"peak_quarters needs column(s) {', '.join(missing)} in the quarterly "
            f"table (found: {', '.join(map(str, trend.columns))})."
        )
    peak = float(trend[value_column].max())
    tied = trend.loc[trend[value_column] >= peak - 1e-9, quarter_column]
    return sorted(int(q) for q in tied)
