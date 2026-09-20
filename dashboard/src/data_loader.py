"""Loading and validation for the published aggregate tables.

Two rules are enforced here and nowhere else:

1. Only files named in ``constants.ALLOWED_TABLES`` are ever opened. The
   directory is never globbed, so dropping a new file into ``app_data/`` does
   not make it reachable from the application.
2. A table that is missing, empty where it should not be, or missing a required
   column raises. Nothing is silently defaulted.

No chart logic and no Streamlit output belongs in this module.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.constants import ALLOWED_TABLES

DATA_DIR = Path(__file__).resolve().parents[1] / "app_data"


class DataError(RuntimeError):
    """Raised when a published table is missing or does not match its schema."""


def table_path(key: str) -> Path:
    """Resolve a logical table name against the allow-list."""
    try:
        spec = ALLOWED_TABLES[key]
    except KeyError as exc:  # pragma: no cover - programming error
        raise DataError(
            f"'{key}' is not on the published-table allow-list. "
            f"Add it to constants.ALLOWED_TABLES if it has been cleared for release."
        ) from exc
    return DATA_DIR / spec.filename


@st.cache_data(show_spinner=False)
def _read(path_str: str, mtime: float) -> pd.DataFrame:
    """Read one CSV.

    ``mtime`` is not used in the body: it is passed so that Streamlit hashes it
    into the cache key. It must not be named with a leading underscore, because
    Streamlit excludes underscore-prefixed arguments from hashing and the cache
    would then never notice a regenerated file."""
    return pd.read_csv(path_str)


def load(key: str) -> pd.DataFrame:
    """Load one allow-listed table and check it against its declared schema."""
    path = table_path(key)
    spec = ALLOWED_TABLES[key]

    if not path.exists():
        raise DataError(
            f"Expected published table '{spec.filename}' in app_data/ and it is "
            f"not there. Copy it from the analysis outputs, or remove the page "
            f"that depends on it."
        )

    frame = _read(str(path), path.stat().st_mtime)

    if frame.empty and not spec.allow_empty:
        raise DataError(
            f"'{spec.filename}' is empty but is expected to contain data."
        )

    missing = [c for c in spec.required_columns if c not in frame.columns]
    if missing:
        raise DataError(
            f"'{spec.filename}' is missing required column(s): "
            f"{', '.join(missing)}. Found: {', '.join(map(str, frame.columns))}."
        )
    return frame.copy()


@st.cache_data(show_spinner=False)
def _key_number_map(path_str: str, mtime: float) -> dict[str, dict[str, str]]:
    """``mtime`` is hashed into the cache key; see ``_read``."""
    frame = pd.read_csv(path_str, dtype={"name": str, "value": str})
    if frame.empty:
        raise DataError("key_numbers.csv is empty; the dashboard cannot resolve any results.")
    duplicated = frame["name"][frame["name"].duplicated()].tolist()
    if duplicated:
        raise DataError(
            "key_numbers.csv contains duplicated names, so a lookup would be "
            f"ambiguous: {', '.join(sorted(set(duplicated)))}."
        )
    return {
        str(row["name"]): {
            "value": str(row["value"]),
            "description": str(row.get("description", "")),
        }
        for _, row in frame.iterrows()
    }


def key_numbers() -> dict[str, dict[str, str]]:
    """Every generated figure, keyed by name."""
    path = table_path("key_numbers")
    if not path.exists():
        raise DataError(
            "key_numbers.csv is missing. Every headline figure in this "
            "dashboard is read from it, so the app cannot start without it."
        )
    return _key_number_map(str(path), path.stat().st_mtime)


def present_tables() -> list[str]:
    """Allow-listed tables that are actually present in app_data/."""
    return sorted(k for k, s in ALLOWED_TABLES.items() if (DATA_DIR / s.filename).exists())


def missing_tables() -> list[str]:
    """Allow-listed tables that are declared but absent."""
    return sorted(
        k for k, s in ALLOWED_TABLES.items() if not (DATA_DIR / s.filename).exists()
    )


def unlisted_files() -> list[str]:
    """Anything sitting in app_data/ that the allow-list does not name.

    Nothing here is ever read. It is surfaced on the Methods page so that a
    file copied into the deployment by accident is visible rather than quiet.
    """
    if not DATA_DIR.exists():
        return []
    allowed = {s.filename for s in ALLOWED_TABLES.values()}
    return sorted(
        p.name
        for p in DATA_DIR.iterdir()
        if p.is_file() and not p.name.startswith(".") and p.name not in allowed
    )
