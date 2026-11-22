"""Run with PYTHONPATH=src and the path to A's Evidence V1 1.0.0 handoff."""
import hashlib
import json
from pathlib import Path
import runpy
import sys
from tradingagents.review import snapshot_evidence_checker

directory = Path(sys.argv[1])
assert hashlib.sha256((directory/"evidence.py").read_bytes()).hexdigest() == "aa906486e082eb22aacb21c5a5b0096247f4ccfb52fbe7b6a33fcde24d2e21b6"
api = runpy.run_path(str(directory/"demo.py"))["load_evidence"](directory)
fixture = json.loads((directory/"evidence_cases.json").read_text())
snapshot = api.register_reports(**fixture["complete"]["registration"]).snapshot
refs = {"news": {"snapshot_id": snapshot.snapshot_id, "evidence_id": "news"},
        "wrong": {"snapshot_id": "sha256:"+"0"*64,"evidence_id":"news"}}
regular = snapshot_evidence_checker(api,snapshot,refs,historical=False)
assert regular("news") == (True,"OK")
assert regular("wrong") == (False,"SNAPSHOT_MISMATCH")
assert regular("missing") == (False,"MISSING")
assert snapshot_evidence_checker(api,snapshot,refs)("news") == (False,"UNKNOWN_TIME")
print("4/4 A-B boundary checks passed against Evidence V1 1.0.0")
