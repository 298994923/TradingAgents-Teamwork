"""Gate 1 — test-approval gate (D7 §6.1). PARTIAL: covers src/ only.

A PR that changes a ``src/`` file must have that file covered by an approval record
in ``docs/approvals.yaml``: a human approved the source path, with an approver id and
a date, before implementation. A record is valid only if it has a non-empty
``approver`` and an ISO ``date`` (``YYYY-MM-DD``).

Scope: this gate checks ``src/`` only. Changes to ``scripts/`` and ``test/`` are
handled by the AI-use log gate, not here.

Usage:
    python scripts/check_test_approval.py <base_sha> <head_sha>

Exit 0 when every changed src file is covered (or no src file changed), exit 1 (with
the uncovered paths) otherwise.
"""

from __future__ import annotations

import sys
from datetime import date

from gate_common import changed, load_yaml

APPROVALS_PATH = "docs/approvals.yaml"


def load_approvals(text: str) -> list[dict]:
    """Return the approval records listed in the approvals file."""
    data = load_yaml(text) or {}
    return list(data.get("approvals") or [])


def _valid_record(record: dict) -> bool:
    """A record counts only with a source path, approver id, and ISO date."""
    if not record.get("src") or not record.get("approver"):
        return False
    try:
        date.fromisoformat(str(record.get("date")))
    except (TypeError, ValueError):
        return False
    return True


def is_covered(src_path: str, approvals: list[dict]) -> bool:
    """True if a valid record covers ``src_path`` (exact, or directory prefix)."""
    for record in approvals:
        if not _valid_record(record):
            continue
        approved = str(record["src"]).rstrip("/")
        if src_path == approved or src_path.startswith(approved + "/"):
            return True
    return False


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: check_test_approval.py <base_sha> <head_sha>", file=sys.stderr)
        return 2
    base, head = argv[1], argv[2]

    src_changed = [p for p in changed(base, head) if p.startswith("src/")]
    if not src_changed:
        print("[test-approval] no src changes: skipping")
        return 0

    try:
        with open(APPROVALS_PATH, encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError:
        print(f"[test-approval] BLOCKED: {APPROVALS_PATH} is missing.")
        return 1

    approvals = load_approvals(text)
    uncovered = [p for p in src_changed if not is_covered(p, approvals)]
    if uncovered:
        print("[test-approval] BLOCKED: changed src files with no approval record:")
        for path in uncovered:
            print(f"    - {path}")
        return 1

    print(f"[test-approval] OK: all {len(src_changed)} changed src file(s) approved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
