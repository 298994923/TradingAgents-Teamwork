"""Permission-sync gate (D3 / D7 §6.2).

``.opencode/permissions.jsonc`` is the course artifact describing the intended
policy; ``opencode.jsonc`` is what OpenCode actually reads. This gate fails when the
two drift in the ways that matter:

- every path the artifact marks ``human_only`` or ``protected`` must be covered by
  ``opencode.jsonc`` (its ``deny``, ``human_only`` or ``protected`` lists), and
- both files' ``default`` must be ``deny`` (default is no read, no write).

Usage::

    python scripts/check_permission_sync.py [--root <dir>]

Exit 0 in sync, 1 on drift (with each problem printed), 2 when an input file is
missing (setup defect, not a content defect). Stdlib only; JSONC is parsed with a
small comment/trailing-comma stripper that respects string literals.
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path

OPENCODE = "opencode.jsonc"
PERMISSIONS = ".opencode/permissions.jsonc"

# Lists whose paths must be covered by the enforced config, and the lists that may
# provide the coverage.
_REQUIRED_KEYS = ("human_only", "protected")
# The enforced config may express coverage in top-level lists (the artifact/stub
# shape) and/or under the real OpenCode permission model, one entry per action.
_COVER_KEYS = ("deny", "human_only", "protected")
_ACTIONS = ("read", "edit")
_DENY_EFFECTS = ("deny", "ask")  # either withholds autonomous access


def _strip_jsonc(text: str) -> str:
    """Remove ``//`` and ``/* */`` comments and trailing commas, preserving strings."""
    out = []
    i, n = 0, len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:  # keep the escaped char verbatim
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            i += 2
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    stripped = "".join(out)
    # Remove trailing commas before a closing brace/bracket (strings are intact).
    return re.sub(r",(\s*[}\]])", r"\1", stripped)


def load_jsonc(text: str) -> dict:
    """Parse JSONC text (comments + trailing commas) into a dict."""
    return json.loads(_strip_jsonc(text))


def _effect_rules(opencode: dict, action: str) -> list[tuple[str, str]]:
    """Deny/ask patterns for ``action`` from the top-level lists and the permission model.

    Top-level ``deny``/``human_only``/``protected`` lists protect a path from every
    action (so they apply to both read and edit). The real config instead nests rules
    under ``permission.<action>``: either a scalar effect (``"deny"``/``"ask"``/
    ``"allow"``) applying to every resource, or a map of pattern -> effect.
    """
    rules: list[tuple[str, str]] = []

    # Artifact / stub shape: lists at the top level deny both read and edit.
    for key in _COVER_KEYS:
        for pattern in opencode.get(key) or []:
            rules.append((pattern, "deny"))

    # Real OpenCode shape: permission.<action> (V1) or permissions[] entries (V2).
    permission = opencode.get("permission")
    if isinstance(permission, dict):
        entry = permission.get(action)
        if isinstance(entry, str):
            rules.append(("*", entry))
        elif isinstance(entry, dict):
            rules.extend((pattern, str(effect)) for pattern, effect in entry.items())

    for rule in opencode.get("permissions") or []:
        if isinstance(rule, dict) and rule.get("action") == action:
            rules.append((str(rule.get("resource", "*")), str(rule.get("effect", ""))))

    return rules


def _matches(required: str, pattern: str) -> bool:
    if pattern == required or fnmatch.fnmatchcase(required, pattern):
        return True
    # A ``dir/**`` or ``dir/*`` pattern covers everything beneath it.
    if pattern.endswith("/**") or pattern.endswith("/*"):
        prefix = pattern.rsplit("/", 1)[0]
        return required == prefix or required.startswith(prefix + "/")
    return False


def _covers_action(opencode: dict, action: str, required: str) -> bool:
    """Whether ``action`` on ``required`` is denied (or asked) by some rule."""
    return any(
        _matches(required, pattern) and effect in _DENY_EFFECTS
        for pattern, effect in _effect_rules(opencode, action)
    )


def _covers(opencode: dict, required: str) -> bool:
    """Covered means both read and edit are withheld from the agent."""
    return all(_covers_action(opencode, action, required) for action in _ACTIONS)


def check(permissions: dict, opencode: dict) -> list[str]:
    """Return human-readable drift problems (empty list means in sync)."""
    problems: list[str] = []

    if permissions.get("default") != "deny":
        problems.append(
            f"{PERMISSIONS}: default is {permissions.get('default')!r}, expected 'deny'"
        )
    if opencode.get("default") != "deny":
        problems.append(f"{OPENCODE}: default is {opencode.get('default')!r}, expected 'deny'")

    for key in _REQUIRED_KEYS:
        for required in permissions.get(key) or []:
            if not _covers(opencode, required):
                problems.append(
                    f"{OPENCODE} does not protect {key} path {required!r} for both read and edit "
                    f"from {PERMISSIONS}"
                )
    return problems


def _parse_args(argv: list[str]) -> tuple[Path | None, int]:
    """Parse args given without the program name (e.g. ``["--root", dir]``)."""
    root = Path(__file__).resolve().parents[1]
    args = list(argv)
    if "--root" in args:
        idx = args.index("--root")
        try:
            root = Path(args[idx + 1])
        except IndexError:
            print("usage: check_permission_sync.py [--root <dir>]", file=sys.stderr)
            return None, 2
    return root, 0


def main(argv: list[str]) -> int:
    root, code = _parse_args(argv)
    if root is None:
        return code

    opencode_path = root / OPENCODE
    permissions_path = root / PERMISSIONS
    for path in (opencode_path, permissions_path):
        if not path.exists():
            print(f"[permission-sync] MISSING: {path}", file=sys.stderr)
            return 2

    try:
        opencode = load_jsonc(opencode_path.read_text(encoding="utf-8"))
        permissions = load_jsonc(permissions_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"[permission-sync] BLOCKED: cannot parse JSONC: {exc}")
        return 1

    problems = check(permissions, opencode)
    if problems:
        print(f"[permission-sync] BLOCKED: {len(problems)} drift problem(s):")
        for problem in problems:
            print(f"    - {problem}")
        return 1
    print("[permission-sync] OK: opencode.jsonc covers the protected paths and both default to deny")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
