"""Gate 3 — requirements schema gate (D7 §6.3).

Validates ``docs/req/requirements.yaml`` against ``docs/req/req-schema.json`` using
the JSON-Schema Draft 2020-12 validator. The inputs are a scaffold today: the schema
is the team's compact proposal and the registry is seeded minimal, so the gate runs
meaningfully from day one and tightens as A fills the registry in.

Usage:
    python scripts/check_req_schema.py

Exit 0 when the registry validates, exit 1 (with the validator errors) when it does
not, exit 2 when an input file is missing (setup defect, not a content defect).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "req" / "req-schema.json"
REGISTRY_PATH = ROOT / "docs" / "req" / "requirements.yaml"


def main() -> int:
    if not SCHEMA_PATH.exists():
        print(f"[req-schema] MISSING: {SCHEMA_PATH.relative_to(ROOT)}", file=sys.stderr)
        return 2
    if not REGISTRY_PATH.exists():
        print(f"[req-schema] MISSING: {REGISTRY_PATH.relative_to(ROOT)}", file=sys.stderr)
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(registry), key=lambda e: list(e.path))
    if errors:
        print(f"[req-schema] BLOCKED: {len(errors)} validation error(s):")
        for error in errors:
            location = "/".join(str(p) for p in error.path) or "<root>"
            print(f"    - {location}: {error.message}")
        return 1

    count = len(registry) if isinstance(registry, list) else "?"
    print(f"[req-schema] OK: {count} requirement(s) validate against the schema")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
