"""CLI entry point for the AI-use log gate (D7 §6.6).

Usage:
    python scripts/check_ai_use_log.py <base_sha> <head_sha>

Three checks, nothing more:
  1. A PR that changes src/, scripts/, or test/ must add a new entry
     to docs/ai-use-log.yaml.
  2. Entry ids must not duplicate one another.
  3. The newly added entry must have ``human_reviewed: true``.

Exit 0 when the PR passes, exit 1 (with a reason) when it is blocked. Docs-only PRs
pass. Stdlib + PyYAML only.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from gate_common import changed, gated, load_yaml

LOG_PATH = "docs/ai-use-log.yaml"


def _entries(text: str) -> list[dict]:
    return list(load_yaml(text).get("entries") or [])


def _ids(entries: list[dict]) -> list[str]:
    return [entry["id"] for entry in entries if entry.get("id")]


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

    gated_paths = gated(changed(base, head))
    if not gated_paths:
        print("[ai-use-log] docs-only PR: no gated changes, skipping")
        return 0

    base_ids = _ids(_entries(_read_at(base, LOG_PATH)))
    head_entries = _entries(_read_worktree(LOG_PATH))
    head_ids = _ids(head_entries)

    duplicated = sorted({i for i in head_ids if head_ids.count(i) > 1})
    if duplicated:
        print(f"[ai-use-log] BLOCKED: duplicate entry id(s): {duplicated}")
        return 1

    new_entries = [e for e in head_entries if e.get("id") not in base_ids]
    if not new_entries:
        print("[ai-use-log] BLOCKED: gated paths changed but no new log entry added.")
        for path in gated_paths:
            print(f"    - {path}")
        return 1

    unreviewed = [str(e.get("id")) for e in new_entries if e.get("human_reviewed") is not True]
    if unreviewed:
        print(f"[ai-use-log] BLOCKED: new entry not human_reviewed: {unreviewed}")
        return 1

    print(f"[ai-use-log] OK: new entry id(s) {[e.get('id') for e in new_entries]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
