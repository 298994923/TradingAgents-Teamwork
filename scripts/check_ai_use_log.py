"""CLI entry point for the AI-use log gate (D7 §6.6).

Usage:
    python scripts/check_ai_use_log.py <base_sha> <head_sha>

The gate runs when the PR changes src/, scripts/ or test/, OR changes
docs/ai-use-log.yaml. If neither changed, it skips.

When it runs:
  1. No entry may be deleted: every id present at base must still be present at head.
  2. The total entry count must not drop below the base count.
  3. Entry ids must not duplicate one another at head.
  4. Every added-or-modified entry must have ``agent: opencode`` and
     ``human_reviewed: true``. Unchanged, carried-over entries are not re-validated.

Only when src/, scripts/ or test/ changed is a NEW entry required (an id not present
at base). A docs-only PR that edits the log does not need a new entry.

Exit 0 when the PR passes, exit 1 (with a reason) when it is blocked. Stdlib + PyYAML.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from gate_common import changed, gated, load_yaml

LOG_PATH = "docs/ai-use-log.yaml"
AGENT = "opencode"


def _entries(text: str) -> list[dict]:
    return list(load_yaml(text).get("entries") or [])


def _ids(entries: list[dict]) -> list[str]:
    return [entry["id"] for entry in entries if entry.get("id")]


def _by_id(entries: list[dict]) -> dict[str, dict]:
    return {entry["id"]: entry for entry in entries if entry.get("id")}


def _read_at(ref: str, path: str) -> str:
    result = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def _read_worktree(path: str) -> str:
    file_path = Path(path)
    return file_path.read_text(encoding="utf-8") if file_path.exists() else ""


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: check_ai_use_log.py <base_sha> <head_sha>", file=sys.stderr)
        return 2
    base, head = argv[1], argv[2]

    all_changed = changed(base, head)
    code_changed = bool(gated(all_changed))
    if not (code_changed or LOG_PATH in all_changed):
        print("[ai-use-log] no code or log changes, skipping")
        return 0

    base_entries = _entries(_read_at(base, LOG_PATH))
    head_entries = _entries(_read_worktree(LOG_PATH))
    base_ids = _ids(base_entries)
    head_ids = _ids(head_entries)
    base_map = _by_id(base_entries)

    duplicated = sorted({i for i in head_ids if head_ids.count(i) > 1})
    if duplicated:
        print(f"[ai-use-log] BLOCKED: duplicate entry id(s): {duplicated}")
        return 1

    deleted = sorted(set(base_ids) - set(head_ids))
    if deleted:
        print(f"[ai-use-log] BLOCKED: entry id(s) deleted: {deleted}")
        return 1

    if len(head_entries) < len(base_entries):
        print(f"[ai-use-log] BLOCKED: entry count dropped {len(base_entries)} -> {len(head_entries)}")
        return 1

    touched = [e for e in head_entries if e.get("id") not in base_map or e != base_map[e["id"]]]

    problems: list[str] = []
    for entry in touched:
        entry_id = str(entry.get("id"))
        if entry.get("agent") != AGENT:
            problems.append(f"{entry_id}: agent must be '{AGENT}'")
        if entry.get("human_reviewed") is not True:
            problems.append(f"{entry_id}: human_reviewed must be true")
    if problems:
        print("[ai-use-log] BLOCKED: added/changed entries fail validation:")
        for problem in problems:
            print(f"    - {problem}")
        return 1

    if code_changed:
        new_ids = set(head_ids) - set(base_ids)
        if not new_ids:
            print("[ai-use-log] BLOCKED: code changed but no new log entry id added.")
            for path in gated(all_changed):
                print(f"    - {path}")
            return 1

    print(f"[ai-use-log] OK: added/changed entry id(s) {_ids(touched)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
