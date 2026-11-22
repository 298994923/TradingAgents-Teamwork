"""Gate 2 — static analysis (D7 §6.2).

Runs on every PR/push. This script covers the *dependency* check that ruff does not:
it verifies every installed top-level third-party import used by ``src/`` and
``scripts/`` is declared in ``pyproject.toml`` (no hallucinated/undeclared
dependencies). Ruff and compileall run as separate steps in the ``lint`` job.

Usage:
    python scripts/check_dependencies.py

Exit 0 when clean, exit 1 (with the offending modules) when an undeclared dependency
is imported. Stdlib modules and the project's own packages are always allowed.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWN_PACKAGES = {"tradingagents", "cli"}
# Distribution names whose import name differs, plus local script modules.
ALIASES = {
    "yaml": "pyyaml",
    "dotenv": "python-dotenv",
}
LOCAL_MODULES = {
    "gate_common",
    "check_ai_use_log",
    "check_test_approval",
    "check_dependencies",
    "check_req_schema",
}
# Packages imported directly by the baseline but provided transitively by declared
# dependencies (e.g. pydantic via langchain-core). Listed here so the gate catches
# *new* undeclared imports without red-lighting the existing tree. Adding a name is
# a reviewed decision: prefer declaring the dependency in pyproject.toml instead.
KNOWN_TRANSITIVE = {
    "anthropic",
    "dateutil",
    "markdown_it",
    "prompt_toolkit",
    "pydantic",
}


def declared_dependencies() -> set[str]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    names: set[str] = set()
    for spec in project.get("dependencies", []):
        names.add(_dist_name(spec))
    for group in project.get("optional-dependencies", {}).values():
        for spec in group:
            names.add(_dist_name(spec))
    return names


def _dist_name(spec: str) -> str:
    for sep in (">=", "==", "<=", "~=", "!=", ">", "<", "[", ";", " "):
        spec = spec.split(sep, 1)[0]
    return spec.strip().lower()


def imported_toplevels(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def main() -> int:
    declared = declared_dependencies()
    stdlib = set(sys.stdlib_module_names)
    allowed = declared | stdlib | OWN_PACKAGES | LOCAL_MODULES | KNOWN_TRANSITIVE

    offenders: dict[str, set[str]] = {}
    targets = list((ROOT / "src").rglob("*.py")) + list((ROOT / "scripts").rglob("*.py"))
    for path in targets:
        for module in imported_toplevels(path):
            dist = ALIASES.get(module, module).lower().replace("_", "-")
            if module in allowed or dist in declared:
                continue
            offenders.setdefault(module, set()).add(str(path.relative_to(ROOT)))

    if offenders:
        print("[dependencies] BLOCKED: undeclared top-level imports:")
        for module, files in sorted(offenders.items()):
            print(f"    - {module}: {sorted(files)}")
        return 1

    print(f"[dependencies] OK: {len(targets)} files, all imports declared or stdlib")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
