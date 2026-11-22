"""Shared helpers for the CS5351 blocking gates (D7).

Stdlib + PyYAML only. Each gate script imports ``changed`` / ``gated`` from here so
the diff logic is identical across gates and cannot drift.
"""

from __future__ import annotations

import subprocess

import yaml

GATED_PREFIXES = ("src/", "scripts/", "test/")


def changed(base: str, head: str, repo: str = ".") -> list[str]:
    """Paths changed between base and head (three-dot diff; includes deletions)."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRD", f"{base}...{head}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def gated(paths: list[str]) -> list[str]:
    return [p for p in paths if any(p.startswith(prefix) for prefix in GATED_PREFIXES)]


def load_yaml(text: str) -> object:
    return yaml.safe_load(text) or {}
