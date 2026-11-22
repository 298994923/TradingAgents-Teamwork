"""B-owned adapters for E's CLI and C's selected Evidence V1 snapshot."""
import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock

ROLES = {"bull", "bear", "research_manager"}


class PromptReceipts:
    """Create one collector per run. Pass record as the nodes' on_prompt."""
    def __init__(self, run_id):
        if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
            raise ValueError("invalid run identifier")
        self.run_id = run_id
        self._roles = {}
        self._calls = []
        self._lock = Lock()

    def record(self, receipt):
        role = receipt["role"]
        if role not in ROLES or receipt.get("run_id") not in (None, self.run_id):
            raise ValueError("unexpected role or run")
        hashes = receipt["prompt_hashes"]
        if set(hashes) != {"b." + role}:
            raise ValueError("template identifier mismatch")
        digest = hashes["b." + role]
        if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
            raise ValueError("invalid template digest")
        actual = receipt.get("input_sha256") or None
        if actual is not None and (not isinstance(actual, str) or not re.fullmatch("[0-9a-f]{64}", actual)):
            raise ValueError("invalid input digest")
        with self._lock:
            if self._roles.get(role, digest) != digest:
                raise ValueError("template changed during run")
            self._roles[role] = digest
            self._calls.append(dict(role=role, run_id=self.run_id,
                                    round_index=receipt.get("round_index"), input_sha256=actual))

    def finish(self, runs_dir, *, expected_calls):
        """After all callbacks, persist evidence and return the observed manifest guard."""
        if type(expected_calls) is not int or expected_calls < 0:
            raise ValueError("invalid expected call count")
        with self._lock:
            calls = list(self._calls)
            hashes = self._roles.copy()
        complete = bool(calls) and len(calls) == expected_calls and all(c["input_sha256"] for c in calls)
        payload = dict(run_id=self.run_id, expected_calls=expected_calls, calls=calls,
                       input_evidence="完整" if complete else "输入取证不完整")
        directory = Path(runs_dir) / self.run_id
        directory.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as temp:
            try:
                json.dump(payload, temp, ensure_ascii=False, indent=2)
                temp.flush()
                os.replace(temp.name, directory / "prompt_receipts.json")
            finally:
                Path(temp.name).unlink(missing_ok=True)
        return hashes


def bind_evidence(api, snapshot, references, *, historical=True):
    """Freeze V1 alias bindings at node creation and use B's existing checker."""
    from tradingagents.review import snapshot_evidence_checker

    if type(historical) is not bool:
        raise ValueError("historical must be boolean")
    import copy
    return snapshot_evidence_checker(api, snapshot, copy.deepcopy(references), historical=historical)
