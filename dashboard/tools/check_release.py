"""Pre-deployment check: is this repository safe to make public?

Run from the repository root:

    python tools/check_release.py

Checks, in order:

1. every file in app_data/ is named on the allow-list, and every allow-listed
   table is present and has its declared columns;
2. nothing in the working tree matches a restricted filename or extension;
3. if this is a git checkout, nothing restricted is tracked now, and nothing
   restricted appears anywhere in the object history of any branch or tag —
   because deleting a file and adding a .gitignore leaves it in the history, and
   pushing that history publishes it;
4. no result is hard-coded in the application code.

Exit status is non-zero if anything fails, so it can gate a deployment.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.constants import ALLOWED_TABLES  # noqa: E402

RESTRICTED_SUFFIXES = {
    ".dat", ".sav", ".sas7bdat", ".parquet", ".duckdb", ".wal",
    ".xls", ".xlsx", ".pdf", ".db", ".sqlite", ".pem", ".key", ".p12",
}
RESTRICTED_NAMES = {
    "clin_sample_ascii.dat", "clin_sample_spss.sav", "dad_parsed.parquet",
    "cohort.parquet", "episode_level.parquet", "analysis_all_admissions.parquet",
    "dad.duckdb", "layout.csv", "secrets.toml", ".env",
    "credentials.json", "service-account.json", "service_account.json",
    "data_specs.docx", "spec.docx",
}
RESTRICTED_DIRECTORIES = {"internal", "output", "raw"}

SKIP_DIRECTORIES = {".git", ".venv", "venv", "__pycache__", ".ipynb_checkpoints"}

# Literals that must never appear in the application code: every reported figure
# is read from key_numbers.csv at runtime.
HARD_CODED = re.compile(
    r"(?<![\w.])(0\.6\d{2}|0\.7\d{2}|15\.6|2\.47|5\.52|16\.0|22\.3|"
    r"744914|744,914|32301|32,301|43565|43,565|25495|25,495)(?![\w.])"
)
CODE_DIRECTORIES = ("src", "pages")

failures: list[str] = []
notes: list[str] = []


def check_allow_list() -> None:
    data_dir = ROOT / "app_data"
    if not data_dir.exists():
        failures.append("app_data/ does not exist.")
        return

    allowed = {spec.filename for spec in ALLOWED_TABLES.values()}
    present = {p.name for p in data_dir.iterdir() if p.is_file()
               and not p.name.startswith(".")}

    for unexpected in sorted(present - allowed):
        failures.append(
            f"app_data/{unexpected} is not on the allow-list. Remove it, or add "
            f"it to constants.ALLOWED_TABLES if it has been cleared for release."
        )
    for missing in sorted(allowed - present):
        failures.append(f"app_data/{missing} is declared on the allow-list but absent.")

    import pandas as pd

    for key, spec in ALLOWED_TABLES.items():
        path = data_dir / spec.filename
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        columns = set(frame.columns)
        if frame.empty and not spec.allow_empty:
            failures.append(
                f"app_data/{spec.filename} is empty but is expected to contain data."
            )
        gaps = [c for c in spec.required_columns if c not in columns]
        if gaps:
            failures.append(
                f"app_data/{spec.filename} is missing declared column(s): "
                f"{', '.join(gaps)}."
            )
    notes.append(f"Allow-list: {len(allowed)} tables declared, {len(present)} present.")


def _walk() -> list[Path]:
    found = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        if path.is_file():
            found.append(path)
    return found


def check_working_tree() -> None:
    for path in _walk():
        relative = path.relative_to(ROOT)
        if path.suffix.lower() in RESTRICTED_SUFFIXES:
            failures.append(f"Restricted file type in the working tree: {relative}")
        if path.name.lower() in {name.lower() for name in RESTRICTED_NAMES}:
            failures.append(f"Restricted file in the working tree: {relative}")
        if path.name.lower().startswith(".env."):
            failures.append(f"Restricted environment file in the working tree: {relative}")
        if any(part.lower() in {d.lower() for d in RESTRICTED_DIRECTORIES} for part in relative.parts[:-1]):
            failures.append(f"Restricted directory in the working tree: {relative}")


def _is_restricted(entry: str) -> bool:
    path = Path(entry)
    restricted_names = {name.lower() for name in RESTRICTED_NAMES}
    restricted_dirs = {name.lower() for name in RESTRICTED_DIRECTORIES}
    return (path.suffix.lower() in RESTRICTED_SUFFIXES
            or path.name.lower() in restricted_names
            or path.name.lower().startswith(".env.")
            or any(part.lower() in restricted_dirs for part in path.parts[:-1]))


def _git(*arguments: str) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", *arguments], cwd=ROOT,
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.splitlines()


def check_git() -> None:
    tracked = _git("ls-files")
    if tracked is None:
        notes.append("Not a git checkout (or git unavailable): git checks skipped.")
        return

    for entry in tracked:
        if _is_restricted(entry):
            failures.append(
                f"Restricted file is TRACKED BY GIT: {entry}. Removing it from the "
                f"working tree is not enough."
            )
    notes.append(f"Git: {len(tracked)} tracked files checked.")

    # Everything any branch or tag has ever contained. A file deleted in a later
    # commit is still in the history, and pushing the history publishes it.
    history = _git("rev-list", "--objects", "--all")
    if history is None:
        notes.append(
            "Git history could not be listed (no commits yet?): history check skipped."
        )
        return

    seen: set[str] = set()
    for line in history:
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue  # a commit or tree object, which carries no path
        entry = parts[1].strip()
        if entry and entry not in seen and _is_restricted(entry):
            seen.add(entry)
            failures.append(
                f"Restricted file exists in GIT HISTORY: {entry}. It is still "
                f"published if this history is pushed. Rewrite the history "
                f"(git filter-repo, or a fresh repository) before making this "
                f"repository public."
            )
    notes.append(f"Git history: {len(history)} objects across all refs checked.")



def check_hard_coded_results() -> None:
    for directory in CODE_DIRECTORIES:
        for path in (ROOT / directory).rglob("*.py"):
            source = path.read_text()
            for number, line in enumerate(source.splitlines(), start=1):
                if line.lstrip().startswith("#"):
                    continue
                match = HARD_CODED.search(line)
                if match:
                    failures.append(
                        f"{path.relative_to(ROOT)}:{number} looks like a hard-coded "
                        f"result ({match.group(0)}). Read it from key_numbers.csv."
                    )
    notes.append("Application code, including user-facing prose, checked for hard-coded headline results.")


def main() -> int:
    check_allow_list()
    check_working_tree()
    check_git()
    check_hard_coded_results()

    for note in notes:
        print(f"  {note}")
    if failures:
        print(f"\nFAILED — {len(failures)} problem(s):\n")
        for problem in failures:
            print(f"  - {problem}")
        print("\nDo not deploy until these are resolved.")
        return 1
    print("\nPASSED — nothing restricted found, allow-list intact, no flagged hard-coded headline results.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
