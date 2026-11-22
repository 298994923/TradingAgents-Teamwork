"""Deterministic report evidence, contract Version 1 (A-EV-01 through A-EV-08).

Authority and scope: docs/contracts/evidence.md. This module preserves reports;
it neither acquires data nor certifies truth, historical suitability or actions.
Only explicit save/load operations perform I/O. No application imports are needed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from types import MappingProxyType

# These meanings belong to schema 1, independently of future execution planners.
ANALYST_REPORT_FIELDS = MappingProxyType({
    "market": "market_report",
    "social": "sentiment_report",
    "news": "news_report",
    "fundamentals": "fundamentals_report",
})
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")
_ARTIFACT_KEY = re.compile(r"v1/[0-9a-f]{64}\.json\Z")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z\Z")
_SLOT_FIELDS = {"content", "content_sha256", "report_generated_at", "source_available_at"}


class EvidenceError(ValueError):
    """A contract error with a stable reason and JSON Pointer, without report text."""

    def __init__(self, code: str, path: str = ""):
        self.code = code
        self.path = path
        super().__init__(f"{code} at {path or '<root>'}")


def artifact_key_for(snapshot_id: str) -> str:
    """A-EV-08: convert a complete canonical ID to a key without accessing storage."""
    if not isinstance(snapshot_id, str) or not _ID.fullmatch(snapshot_id):
        raise EvidenceError("INVALID_CONTEXT", "/snapshot_id")
    return "v1/" + snapshot_id[7:] + ".json"


def parse_artifact_key(artifact_key: str) -> str:
    """A-EV-08: parse canonical key syntax without asserting stored content identity."""
    if not isinstance(artifact_key, str) or not _ARTIFACT_KEY.fullmatch(artifact_key):
        raise EvidenceError("INVALID_CONTEXT", "/artifact_key")
    return "sha256:" + artifact_key[3:-5]


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    path: str


@dataclass(frozen=True, slots=True)
class ReportSlot:
    content: str | None
    content_sha256: str | None
    report_generated_at: None = None
    source_available_at: None = None


def _pointer(path, key):
    return path + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _string(value, code, path, *, nonempty=False):
    if not isinstance(value, str) or (nonempty and not value.strip()):
        raise EvidenceError(code, path)
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise EvidenceError(code, path) from exc


def _shape(value, fields, code, path):
    if not isinstance(value, Mapping) or set(value) != fields:
        raise EvidenceError(code, path)


def _context(value, code):
    _shape(value, {"instrument", "instrument_context", "analysis_date", "analysis_cutoff_at"}, code, "/context")
    instrument = value["instrument"]
    _shape(instrument, {"symbol", "asset_type"}, code, "/context/instrument")
    _string(instrument["symbol"], code, "/context/instrument/symbol", nonempty=True)
    if not isinstance(instrument["asset_type"], str) or instrument["asset_type"] not in {"stock", "crypto"}:
        raise EvidenceError(code, "/context/instrument/asset_type")
    _string(value["instrument_context"], code, "/context/instrument_context")
    analysis_date = value["analysis_date"]
    if not isinstance(analysis_date, str) or not _DATE.fullmatch(analysis_date):
        raise EvidenceError(code, "/context/analysis_date")
    try:
        date.fromisoformat(analysis_date)
    except ValueError as exc:
        raise EvidenceError(code, "/context/analysis_date") from exc
    if value["analysis_cutoff_at"] is not None:
        raise EvidenceError(code, "/context/analysis_cutoff_at")
    return {
        "instrument": dict(instrument),
        "instrument_context": value["instrument_context"],
        "analysis_date": analysis_date,
        "analysis_cutoff_at": None,
    }


def _timestamp(value, code):
    if not isinstance(value, str) or not _TIME.fullmatch(value):
        raise EvidenceError(code, "/captured_at")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as exc:
        raise EvidenceError(code, "/captured_at") from exc


def _selection(value):
    if not isinstance(value, (list, tuple)) or not value:
        raise EvidenceError("INVALID_SELECTION", "/selected_analysts")
    seen = set()
    for index, key in enumerate(value):
        path = _pointer("/selected_analysts", index)
        if not isinstance(key, str):
            raise EvidenceError("INVALID_SELECTION", path)
        if key not in ANALYST_REPORT_FIELDS:
            raise EvidenceError("UNKNOWN_ANALYST", path)
        if key in seen:
            raise EvidenceError("DUPLICATE_ANALYST", path)
        seen.add(key)
    return seen


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _content_hash(content):
    return None if content is None else hashlib.sha256(content.encode("utf-8")).hexdigest()


def _snapshot_id(payload):
    return "sha256:" + hashlib.sha256(_canonical({k: v for k, v in payload.items() if k != "snapshot_id"})).hexdigest()


def _validate_payload(payload):
    """A-EV-05: schema first, then content hashes, then the complete payload hash."""
    _shape(payload, {"schema_version", "snapshot_id", "source_run_id", "captured_at", "context", "reports"}, "INVALID_SCHEMA", "")
    if not isinstance(payload["schema_version"], str):
        raise EvidenceError("INVALID_SCHEMA", "/schema_version")
    if payload["schema_version"] != "1":
        raise EvidenceError("UNSUPPORTED_VERSION", "/schema_version")
    identity = payload["snapshot_id"]
    if not isinstance(identity, str) or not _ID.fullmatch(identity):
        raise EvidenceError("INVALID_SCHEMA", "/snapshot_id")
    _string(payload["source_run_id"], "INVALID_SCHEMA", "/source_run_id", nonempty=True)
    _timestamp(payload["captured_at"], "INVALID_SCHEMA")
    _context(payload["context"], "INVALID_SCHEMA")
    reports = payload["reports"]
    if not isinstance(reports, Mapping) or not reports:
        raise EvidenceError("INVALID_SCHEMA", "/reports")
    for key, slot in reports.items():
        path = _pointer("/reports", key)
        if not isinstance(key, str) or key not in ANALYST_REPORT_FIELDS:
            raise EvidenceError("INVALID_SCHEMA", path)
        _shape(slot, _SLOT_FIELDS, "INVALID_SCHEMA", path)
        content, digest = slot["content"], slot["content_sha256"]
        if content is not None:
            _string(content, "INVALID_SCHEMA", path + "/content")
            if not isinstance(digest, str) or not _HEX.fullmatch(digest):
                raise EvidenceError("INVALID_SCHEMA", path + "/content_sha256")
        elif digest is not None:
            raise EvidenceError("INVALID_SCHEMA", path + "/content_sha256")
        for field in ("report_generated_at", "source_available_at"):
            if slot[field] is not None:
                raise EvidenceError("INVALID_SCHEMA", path + "/" + field)
    for key, slot in reports.items():
        if slot["content_sha256"] != _content_hash(slot["content"]):
            raise EvidenceError("CONTENT_HASH_MISMATCH", _pointer("/reports", key) + "/content_sha256")
    if identity != _snapshot_id(payload):
        raise EvidenceError("SNAPSHOT_HASH_MISMATCH", "/snapshot_id")


@dataclass(frozen=True, slots=True, init=False)
class Snapshot:
    """A-EV-02: validated, detached, deeply immutable Version 1 report snapshot."""

    snapshot_id: str
    source_run_id: str
    captured_at: str
    context: Mapping
    reports: Mapping
    schema_version: str

    def __init__(self, payload):
        _validate_payload(payload)
        context = _context(payload["context"], "INVALID_SCHEMA")
        context["instrument"] = MappingProxyType(context["instrument"])
        object.__setattr__(self, "context", MappingProxyType(context))
        object.__setattr__(self, "reports", MappingProxyType({
            key: ReportSlot(**dict(slot)) for key, slot in payload["reports"].items()
        }))
        for field in ("snapshot_id", "source_run_id", "captured_at", "schema_version"):
            object.__setattr__(self, field, payload[field])

    def to_dict(self):
        """Return a detached JSON-ready copy; edits cannot change this snapshot."""
        context = dict(self.context)
        context["instrument"] = dict(context["instrument"])
        return {
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "source_run_id": self.source_run_id,
            "captured_at": self.captured_at,
            "context": context,
            "reports": {key: {field: getattr(slot, field) for field in _SLOT_FIELDS}
                        for key, slot in self.reports.items()},
        }


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    snapshot: Snapshot
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True, slots=True)
class LoadResult:
    snapshot: Snapshot
    diagnostics: tuple[Diagnostic, ...]
    expected_identity: str


@dataclass(frozen=True, slots=True)
class SaveResult:
    status: str
    path: Path


@dataclass(frozen=True, slots=True)
class ReferenceResult:
    structure: str
    binding: str = "not_checked"
    slot: str = "not_checked"
    availability: str = "not_checked"
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReplayAssessment:
    ready: bool
    findings: tuple[Diagnostic, ...]
    expected_identity: str


def _require_snapshot(snapshot):
    if not isinstance(snapshot, Snapshot):
        raise EvidenceError("INVALID_SCHEMA", "")


def _diagnostics(snapshot):
    findings = [Diagnostic("TIME_METADATA_UNKNOWN", "/context/analysis_cutoff_at")]
    for key in sorted(snapshot.reports):
        slot = snapshot.reports[key]
        path = _pointer("/reports", key)
        if slot.content is None:
            findings.append(Diagnostic("MISSING_REPORT", path))
        elif not slot.content.strip():
            findings.append(Diagnostic("EMPTY_REPORT", path))
        findings.extend(Diagnostic("TIME_METADATA_UNKNOWN", path + "/" + field)
                        for field in ("report_generated_at", "source_available_at"))
    return tuple(findings)


def register_reports(*, selected_analysts, analyst_outputs, source_run_id, captured_at, context):
    """A-EV-01/02/04/06: register explicit reports without acquisition or clock reads."""
    selected = _selection(selected_analysts)
    if not isinstance(analyst_outputs, Mapping):
        raise EvidenceError("INVALID_REPORT_TYPE", "/analyst_outputs")
    for key, content in analyst_outputs.items():
        path = _pointer("/analyst_outputs", key)
        if key not in selected:
            raise EvidenceError("UNSELECTED_OUTPUT", path)
        _string(content, "INVALID_REPORT_TYPE", path)
    _string(source_run_id, "INVALID_CONTEXT", "/source_run_id", nonempty=True)
    _timestamp(captured_at, "INVALID_TIMESTAMP")
    context = _context(context, "INVALID_CONTEXT")
    payload = {
        "schema_version": "1", "source_run_id": source_run_id,
        "captured_at": captured_at, "context": context,
        "reports": {key: {
            "content": analyst_outputs.get(key),
            "content_sha256": _content_hash(analyst_outputs.get(key)),
            "report_generated_at": None, "source_available_at": None,
        } for key in sorted(selected)},
    }
    payload["snapshot_id"] = _snapshot_id(payload)
    snapshot = Snapshot(payload)
    return RegistrationResult(snapshot, _diagnostics(snapshot))


def lookup_report(snapshot, evidence_id):
    """A-EV-01/03: resolve a slot independently of content availability."""
    _require_snapshot(snapshot)
    _string(evidence_id, "MALFORMED_REFERENCE", "/evidence_id", nonempty=True)
    if evidence_id not in snapshot.reports:
        code = "ANALYST_NOT_SELECTED" if evidence_id in ANALYST_REPORT_FIELDS else "UNKNOWN_EVIDENCE_ID"
        raise EvidenceError(code, "/evidence_id")
    return snapshot.reports[evidence_id]


def validate_reference(snapshot, reference):
    """A-EV-03: report structure, binding, resolution and availability separately."""
    _require_snapshot(snapshot)
    try:
        _shape(reference, {"snapshot_id", "evidence_id"}, "MALFORMED_REFERENCE", "")
        _string(reference["evidence_id"], "MALFORMED_REFERENCE", "/evidence_id", nonempty=True)
        identity = reference["snapshot_id"]
        if not isinstance(identity, str) or not _ID.fullmatch(identity):
            raise EvidenceError("MALFORMED_REFERENCE", "/snapshot_id")
    except EvidenceError:
        return ReferenceResult("malformed", reasons=("MALFORMED_REFERENCE",))
    if identity != snapshot.snapshot_id:
        return ReferenceResult("conformant", "mismatched", reasons=("SNAPSHOT_MISMATCH",))
    try:
        slot = lookup_report(snapshot, reference["evidence_id"])
    except EvidenceError as exc:
        return ReferenceResult("conformant", "matched", "not_found", reasons=(exc.code,))
    if slot.content is None:
        availability, reasons = "missing", ("MISSING_REPORT",)
    elif not slot.content.strip():
        availability, reasons = "empty", ("EMPTY_REPORT",)
    else:
        availability, reasons = "present", ()
    return ReferenceResult("conformant", "matched", "found", availability, reasons)


def assess_replay(snapshot, *, required_analysts, expected_context,
                  expected_source_run_id=None, expected_snapshot_id=None):
    """A-EV-07: technical whole-selection readiness, never a workflow decision."""
    _require_snapshot(snapshot)
    selected = _selection(required_analysts)
    context = _context(expected_context, "INVALID_CONTEXT")
    _expected_id(expected_snapshot_id)
    if expected_source_run_id is not None:
        _string(expected_source_run_id, "INVALID_CONTEXT", "/expected_source_run_id", nonempty=True)
    findings = [d for d in _diagnostics(snapshot) if d.code in {"MISSING_REPORT", "EMPTY_REPORT"}]
    if selected != set(snapshot.reports):
        findings.append(Diagnostic("ANALYST_SELECTION_MISMATCH", "/reports"))
    if context != snapshot.to_dict()["context"]:
        findings.append(Diagnostic("CONTEXT_MISMATCH", "/context"))
    if expected_source_run_id is not None and expected_source_run_id != snapshot.source_run_id:
        findings.append(Diagnostic("SOURCE_RUN_MISMATCH", "/source_run_id"))
    binding = "not_supplied" if expected_snapshot_id is None else "matched"
    if expected_snapshot_id is not None and expected_snapshot_id != snapshot.snapshot_id:
        binding = "mismatched"
        findings.append(Diagnostic("EXPECTED_SNAPSHOT_MISMATCH", "/snapshot_id"))
    return ReplayAssessment(not findings, tuple(findings), binding)


def _expected_id(value):
    if value is not None and (not isinstance(value, str) or not _ID.fullmatch(value)):
        raise EvidenceError("INVALID_CONTEXT", "/expected_snapshot_id")


def _path(value):
    if not isinstance(value, (str, os.PathLike)) or value == "":
        raise EvidenceError("INVALID_CONTEXT", "/path")
    try:
        return Path(value)
    except (TypeError, ValueError) as exc:
        raise EvidenceError("INVALID_CONTEXT", "/path") from exc


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            # The parser has no full ancestor path; locate the ambiguous document
            # at its root rather than inventing a misleading nested pointer.
            raise EvidenceError("DUPLICATE_JSON_KEY", "")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise EvidenceError("INVALID_JSON", "")


def load_snapshot(path, *, expected_snapshot_id=None):
    """A-EV-05: load strict JSON, verify internal hashes, then external identity."""
    _expected_id(expected_snapshot_id)
    path = _path(path)
    try:
        data = path.read_bytes()
    except (OSError, ValueError) as exc:
        raise EvidenceError("IO_ERROR", "/path") from exc
    try:
        payload = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_keys,
                             parse_constant=_invalid_constant)
    except EvidenceError:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise EvidenceError("INVALID_JSON", "") from exc
    snapshot = Snapshot(payload)
    if expected_snapshot_id is not None and snapshot.snapshot_id != expected_snapshot_id:
        raise EvidenceError("EXPECTED_SNAPSHOT_MISMATCH", "/snapshot_id")
    return LoadResult(snapshot, _diagnostics(snapshot),
                      "not_supplied" if expected_snapshot_id is None else "matched")


def _existing_snapshot(snapshot, path):
    try:
        existing = load_snapshot(path).snapshot
    except EvidenceError as exc:
        if exc.code == "IO_ERROR":
            raise
        raise EvidenceError("DESTINATION_CONFLICT", "/path") from exc
    if existing.to_dict() != snapshot.to_dict():
        raise EvidenceError("DESTINATION_CONFLICT", "/path")
    return SaveResult("already_present", path)


def save_snapshot(snapshot, path):
    """A-EV-05: complete staging then atomic no-replace publication on local FS.

    A hard link publishes the completed temporary inode without replacing another
    artifact. Unsupported filesystem operations fail explicitly, without fallback
    to direct destination writes. Directory choice and retention belong to E.
    """
    _require_snapshot(snapshot)
    path = _path(path)
    temporary = None
    try:
        if path.exists():
            return _existing_snapshot(snapshot, path)
        fd, name = tempfile.mkstemp(prefix=".evidence-", suffix=".tmp", dir=path.parent)
        temporary = Path(name)
        try:
            stream = os.fdopen(fd, "wb")
        except BaseException:
            os.close(fd)
            raise
        with stream:
            stream.write(_canonical(snapshot.to_dict()))
            stream.flush()
        try:
            os.link(temporary, path)
        except FileExistsError:
            return _existing_snapshot(snapshot, path)
        return SaveResult("created", path)
    except (OSError, ValueError) as exc:
        if isinstance(exc, EvidenceError):
            raise
        raise EvidenceError("IO_ERROR", "/path") from exc
    finally:
        if temporary is not None:
            # A leftover stage file is preferable to changing a publication
            # result or deleting a destination that this call does not own.
            with suppress(OSError):
                temporary.unlink()
