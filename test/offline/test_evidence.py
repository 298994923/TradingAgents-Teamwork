"""Actual Version 1 test draft, revision 2; independent human approval is pending.

Intended destination: test/offline/test_evidence.py. No application implementation
is included. Direct loading avoids the package initializer's personal dotenv reads.
The same file can be reviewed here and moved unchanged to its intended destination.
"""

import copy
import hashlib
import importlib.util
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """A-EV-01: standalone deterministic tests deny Python network access."""
    def refuse(*args, **kwargs):
        raise AssertionError("Evidence tests must not access the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


@pytest.fixture
def ev(no_network):
    """A-EV-01: import only the standalone module, never package initialization."""
    for parent in Path(__file__).resolve().parents:
        candidates = (parent, parent / "TradingAgents-Teamwork")
        repo = next((p for p in candidates if (p / "src/tradingagents").is_dir()), None)
        if repo is not None:
            break
    else:
        pytest.fail("Active source checkout not found")
    target = repo / "src/tradingagents/evidence.py"
    if not target.is_file():
        pytest.fail("evidence.py is not implemented; this is the expected initial red state")
    name = "_evidence_v1_under_test"
    spec = importlib.util.spec_from_file_location(name, target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def cases():
    nearby = Path(__file__).with_name("evidence_cases.json")
    published = Path(__file__).resolve().parents[1] / "fixtures/evidence_cases.json"
    return json.loads((nearby if nearby.is_file() else published).read_text(encoding="utf-8"))


@pytest.fixture
def inputs(cases):
    return copy.deepcopy(cases["complete"]["registration"])


def codes(diagnostics):
    return {item.code for item in diagnostics}


def fail_code(ev, expected, operation):
    with pytest.raises(ev.EvidenceError) as exc:
        operation()
    assert exc.value.code == expected
    assert isinstance(exc.value.path, str)


def write_artifact(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_complete_registration_matches_fixed_vector(ev, inputs, cases):
    """A-EV-01/02: full payload and fixed digest match the reviewed fixture."""
    result = ev.register_reports(**inputs)
    assert result.snapshot.to_dict() == cases["complete"]["expected_snapshot"]
    assert not ({"MISSING_REPORT", "EMPTY_REPORT"} & codes(result.diagnostics))
    payload = result.snapshot.to_dict()
    identity = payload.pop("snapshot_id")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False)
    assert canonical == cases["complete"]["canonical_payload_utf8"]
    assert identity == "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_lookup_returns_exact_report(ev, inputs):
    """A-EV-01: lookup retrieves the requested analyst's original content."""
    snapshot = ev.register_reports(**inputs).snapshot
    for key, text in inputs["analyst_outputs"].items():
        assert ev.lookup_report(snapshot, key).content == text


@pytest.mark.parametrize("selection,code", [
    ([], "INVALID_SELECTION"), ("market", "INVALID_SELECTION"),
    (["market", "market"], "DUPLICATE_ANALYST"),
    (["macro"], "UNKNOWN_ANALYST"), ([1], "INVALID_SELECTION"),
])
def test_invalid_selections_are_errors(ev, inputs, selection, code):
    """A-EV-01: malformed selections are not incomplete snapshots."""
    inputs["selected_analysts"] = selection
    fail_code(ev, code, lambda: ev.register_reports(**inputs))


def test_unselected_output_is_rejected(ev, inputs):
    """A-EV-01: stale or unselected outputs cannot enter the snapshot."""
    inputs["selected_analysts"] = ["market"]
    fail_code(ev, "UNSELECTED_OUTPUT", lambda: ev.register_reports(**inputs))


@pytest.mark.parametrize("value", [None, 1, False, [], {}, b"text"])
def test_invalid_report_type_is_not_missing(ev, inputs, value):
    """A-EV-01/06: explicit invalid values are not silently coerced or omitted."""
    inputs["analyst_outputs"]["news"] = value
    fail_code(ev, "INVALID_REPORT_TYPE", lambda: ev.register_reports(**inputs))


def test_missing_empty_whitespace_and_unavailable_prose(ev, inputs, cases):
    """A-EV-06: missing slots differ from exact empty strings and present prose."""
    inputs.update(copy.deepcopy(cases["incomplete"]))
    result = ev.register_reports(**inputs)
    missing = result.snapshot.reports["news"]
    assert missing.content is None and missing.content_sha256 is None
    assert result.snapshot.reports["market"].content == ""
    assert result.snapshot.reports["social"].content == " \t\r\n"
    assert result.snapshot.reports["fundamentals"].content == inputs["analyst_outputs"]["fundamentals"]
    pairs = {(item.code, item.path) for item in result.diagnostics}
    expected = {
        ("MISSING_REPORT", "/reports/news"),
        ("EMPTY_REPORT", "/reports/market"),
        ("EMPTY_REPORT", "/reports/social"),
    }
    assert expected <= pairs
    completeness = {(code, path) for code, path in pairs
                    if code in {"MISSING_REPORT", "EMPTY_REPORT"}}
    assert completeness == expected
    for key, text in inputs["analyst_outputs"].items():
        assert result.snapshot.reports[key].content == text
        assert result.snapshot.reports[key].content_sha256 == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert ev.lookup_report(result.snapshot, "news").content is None


def test_unselected_slot_is_absent(ev, inputs):
    """A-EV-06: selected report keys are the entire stored manifest."""
    inputs["selected_analysts"] = ["news"]
    inputs["analyst_outputs"] = {"news": "Present"}
    snapshot = ev.register_reports(**inputs).snapshot
    assert set(snapshot.reports) == {"news"}
    fail_code(ev, "ANALYST_NOT_SELECTED", lambda: ev.lookup_report(snapshot, "market"))


def test_exact_text_hash_and_round_trip(ev, inputs, cases, tmp_path):
    """A-EV-02/05: whitespace, CRLF, Unicode and final newline survive exactly."""
    text = cases["exact_text"]
    inputs["analyst_outputs"]["market"] = text
    snapshot = ev.register_reports(**inputs).snapshot
    path = tmp_path / "snapshot.json"
    assert ev.save_snapshot(snapshot, path).status == "created"
    loaded = ev.load_snapshot(path, expected_snapshot_id=snapshot.snapshot_id)
    assert loaded.expected_identity == "matched"
    assert loaded.snapshot.to_dict() == snapshot.to_dict()
    assert loaded.snapshot.reports["market"].content == text
    assert loaded.snapshot.reports["market"].content_sha256 == hashlib.sha256(text.encode("utf-8")).hexdigest()
    payload = loaded.snapshot.to_dict()
    identity = payload.pop("snapshot_id")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False)
    assert identity == "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_identical_registration_and_order_are_stable(ev, inputs):
    """A-EV-02: identical payloads stay identical despite input mapping/order."""
    first = ev.register_reports(**inputs).snapshot
    inputs["selected_analysts"].reverse()
    inputs["analyst_outputs"] = dict(reversed(list(inputs["analyst_outputs"].items())))
    second = ev.register_reports(**inputs).snapshot
    assert first.to_dict() == second.to_dict()


@pytest.mark.parametrize("change", ["run", "capture", "text", "context", "selection"])
def test_payload_changes_change_identity(ev, inputs, change):
    """A-EV-02: source/capture/context/selection participate, not just text."""
    first = ev.register_reports(**inputs).snapshot
    if change == "run":
        inputs["source_run_id"] = "synthetic-source-002"
    elif change == "capture":
        inputs["captured_at"] = "2026-11-21T08:00:00.000001Z"
    elif change == "text":
        inputs["analyst_outputs"]["news"] += " "
    elif change == "context":
        inputs["context"]["instrument_context"] += " Changed."
    else:
        inputs["selected_analysts"].remove("news")
        inputs["analyst_outputs"].pop("news")
    assert ev.register_reports(**inputs).snapshot.snapshot_id != first.snapshot_id


def test_equal_text_keeps_distinct_slots(ev, inputs):
    """A-EV-02: deduplication cannot erase analyst provenance."""
    inputs["analyst_outputs"]["news"] = inputs["analyst_outputs"]["market"]
    snapshot = ev.register_reports(**inputs).snapshot
    assert "market" in snapshot.reports and "news" in snapshot.reports
    assert snapshot.reports["market"].content_sha256 == snapshot.reports["news"].content_sha256


def test_input_and_export_mutation_are_detached(ev, inputs):
    """A-EV-02: caller mutations cannot alter the registered value."""
    snapshot = ev.register_reports(**inputs).snapshot
    before = snapshot.to_dict()
    inputs["analyst_outputs"]["news"] = "Changed input"
    inputs["context"]["instrument"]["symbol"] = "CHANGED"
    exported = snapshot.to_dict()
    exported["reports"]["news"]["content"] = "Changed export"
    exported["context"]["instrument"]["symbol"] = "CHANGED"
    assert snapshot.to_dict() == before


def test_nested_values_are_immutable(ev, inputs):
    """A-EV-02: public nested state cannot be edited in place."""
    snapshot = ev.register_reports(**inputs).snapshot
    with pytest.raises((TypeError, AttributeError)):
        snapshot.reports["news"] = snapshot.reports["market"]
    with pytest.raises((TypeError, AttributeError)):
        snapshot.reports["news"].content = "Changed"
    with pytest.raises((TypeError, AttributeError)):
        snapshot.context["instrument"]["symbol"] = "CHANGED"


@pytest.mark.parametrize("timestamp", [
    "2026-11-21T08:00:00Z", "2026-11-21T08:00:00.000000+00:00",
    "2026-02-30T08:00:00.000000Z", "2026-11-21T08:00:60.000000Z", 1,
])
def test_capture_time_requires_exact_format(ev, inputs, timestamp):
    """A-EV-04: capture timestamp has one representation and valid calendar time."""
    inputs["captured_at"] = timestamp
    fail_code(ev, "INVALID_TIMESTAMP", lambda: ev.register_reports(**inputs))


def test_unknown_time_metadata_remains_null(ev, inputs, tmp_path):
    """A-EV-04: historical analysis is not certified by present-day capture."""
    snapshot = ev.register_reports(**inputs).snapshot
    path = tmp_path / "times.json"
    ev.save_snapshot(snapshot, path)
    payload = ev.load_snapshot(path).snapshot.to_dict()
    assert payload["context"]["analysis_cutoff_at"] is None
    assert all(r["report_generated_at"] is None and r["source_available_at"] is None
               for r in payload["reports"].values())
    assert payload["source_run_id"] == inputs["source_run_id"]
    assert payload["captured_at"] == inputs["captured_at"]


@pytest.mark.parametrize("location", ["cutoff", "generated", "available"])
def test_nonnull_unknown_times_are_rejected_in_v1(ev, inputs, tmp_path, location):
    """A-EV-04: Version 1 does not admit unsupported known time semantics."""
    payload = ev.register_reports(**inputs).snapshot.to_dict()
    if location == "cutoff":
        payload["context"]["analysis_cutoff_at"] = inputs["captured_at"]
    else:
        field = "report_generated_at" if location == "generated" else "source_available_at"
        payload["reports"]["news"][field] = inputs["captured_at"]
    path = tmp_path / "bad-time.json"
    write_artifact(path, payload)
    fail_code(ev, "INVALID_SCHEMA", lambda: ev.load_snapshot(path))


@pytest.mark.parametrize("reference,expected", [
    ({}, "MALFORMED_REFERENCE"),
    ({"snapshot_id": "bad", "evidence_id": "news"}, "MALFORMED_REFERENCE"),
    ({"snapshot_id": "sha256:" + "0" * 64, "evidence_id": "news"}, "SNAPSHOT_MISMATCH"),
])
def test_bad_references_return_explicit_dimensions(ev, inputs, reference, expected):
    """A-EV-03: malformed and wrong-snapshot references never resolve by text."""
    snapshot = ev.register_reports(**inputs).snapshot
    result = ev.validate_reference(snapshot, reference)
    assert expected in result.reasons
    assert result.slot == "not_checked"
    assert result.availability == "not_checked"


@pytest.mark.parametrize("content,availability", [("Present", "present"), ("", "empty"), (" \n", "empty"), (None, "missing")])
def test_reference_resolution_is_separate_from_availability(ev, inputs, content, availability):
    """A-EV-03/06: selected missing/empty slots still resolve correctly."""
    if content is None:
        inputs["analyst_outputs"].pop("news")
    else:
        inputs["analyst_outputs"]["news"] = content
    snapshot = ev.register_reports(**inputs).snapshot
    result = ev.validate_reference(snapshot, {"snapshot_id": snapshot.snapshot_id, "evidence_id": "news"})
    assert (result.structure, result.binding, result.slot, result.availability) == (
        "conformant", "matched", "found", availability)


@pytest.mark.parametrize("key,reason", [("social", "ANALYST_NOT_SELECTED"), ("unknown", "UNKNOWN_EVIDENCE_ID")])
def test_unresolved_reference_is_structurally_conformant(ev, inputs, key, reason):
    """A-EV-03: absence differs from malformed reference syntax."""
    inputs["selected_analysts"] = ["news"]
    inputs["analyst_outputs"] = {"news": "Present"}
    snapshot = ev.register_reports(**inputs).snapshot
    result = ev.validate_reference(snapshot, {"snapshot_id": snapshot.snapshot_id, "evidence_id": key})
    assert result.structure == "conformant" and result.binding == "matched"
    assert result.slot == "not_found" and result.availability == "not_checked"
    assert reason in result.reasons


def test_loading_without_expected_id_is_explicit(ev, inputs, tmp_path):
    """A-EV-05: internal consistency does not assert external binding."""
    path = tmp_path / "snapshot.json"
    ev.save_snapshot(ev.register_reports(**inputs).snapshot, path)
    assert ev.load_snapshot(path).expected_identity == "not_supplied"
    fail_code(ev, "EXPECTED_SNAPSHOT_MISMATCH", lambda: ev.load_snapshot(
        path, expected_snapshot_id="sha256:" + "0" * 64))


@pytest.mark.parametrize("field,code", [("content", "CONTENT_HASH_MISMATCH"), ("run", "SNAPSHOT_HASH_MISMATCH")])
def test_content_and_payload_inconsistency_are_distinct(ev, inputs, tmp_path, field, code):
    """A-EV-05: content and whole-payload changes have explicit failure reasons."""
    payload = ev.register_reports(**inputs).snapshot.to_dict()
    if field == "content":
        payload["reports"]["news"]["content"] += " altered"
    else:
        payload["source_run_id"] = "altered-run"
    path = tmp_path / "altered.json"
    write_artifact(path, payload)
    fail_code(ev, code, lambda: ev.load_snapshot(path))


@pytest.mark.parametrize("text,code", [
    ('{"schema_version":"1","schema_version":"1"}', "DUPLICATE_JSON_KEY"),
    ('{"x":{"content":"a","content":"b"}}', "DUPLICATE_JSON_KEY"),
    ('{"x":NaN}', "INVALID_JSON"), ('{', "INVALID_JSON"),
    ('\ufeff{}', "INVALID_JSON"),
])
def test_strict_json_parser(ev, tmp_path, text, code):
    """A-EV-05: ambiguous duplicate keys and nonstandard JSON are rejected."""
    path = tmp_path / "invalid.json"
    path.write_bytes(text.encode("utf-8"))
    fail_code(ev, code, lambda: ev.load_snapshot(path))


@pytest.mark.parametrize("change,code", [
    ("version", "UNSUPPORTED_VERSION"), ("unknown_top", "INVALID_SCHEMA"),
    ("unknown_report", "INVALID_SCHEMA"), ("unknown_key", "INVALID_SCHEMA"),
    ("missing_field", "INVALID_SCHEMA"), ("type", "INVALID_SCHEMA"),
])
def test_strict_stored_schema(ev, inputs, tmp_path, change, code):
    """A-EV-05: version, required fields, types and versioned keys are enforced."""
    payload = ev.register_reports(**inputs).snapshot.to_dict()
    if change == "version":
        payload["schema_version"] = "2"
    elif change == "unknown_top":
        payload["consumer_run_id"] = "must-not-enter-source-snapshot"
    elif change == "unknown_report":
        payload["reports"]["news"]["vendor"] = "inferred-vendor"
    elif change == "unknown_key":
        payload["reports"]["macro"] = payload["reports"].pop("news")
    elif change == "missing_field":
        payload.pop("captured_at")
    else:
        payload["reports"]["news"]["content"] = 1
    path = tmp_path / "schema.json"
    write_artifact(path, payload)
    fail_code(ev, code, lambda: ev.load_snapshot(path))


def test_duplicate_save_and_conflicting_destination(ev, inputs, tmp_path):
    """A-EV-05: duplicates are idempotent; different/malformed files survive."""
    path = tmp_path / "snapshot.json"
    snapshot = ev.register_reports(**inputs).snapshot
    assert ev.save_snapshot(snapshot, path).status == "created"
    original = path.read_bytes()
    assert ev.save_snapshot(snapshot, path).status == "already_present"
    assert path.read_bytes() == original
    inputs["source_run_id"] = "other-source"
    other = ev.register_reports(**inputs).snapshot
    fail_code(ev, "DESTINATION_CONFLICT", lambda: ev.save_snapshot(other, path))
    assert path.read_bytes() == original
    path.write_text("incomplete artifact", encoding="utf-8")
    fail_code(ev, "DESTINATION_CONFLICT", lambda: ev.save_snapshot(snapshot, path))
    assert path.read_text() == "incomplete artifact"


def test_failed_write_does_not_publish_partial_destination(ev, inputs, tmp_path):
    """A-EV-05: an oversized write under zero file-size limit cannot publish partial JSON."""
    # Fault injection uses a subprocess so its resource limit cannot affect pytest.
    snapshot = ev.register_reports(**inputs).snapshot
    source = tmp_path / "source.json"
    source.write_text(json.dumps(snapshot.to_dict()), encoding="utf-8")
    destination = tmp_path / "destination.json"
    program = '''
import importlib.util, resource, signal, sys
spec = importlib.util.spec_from_file_location("_ev_child", sys.argv[1])
ev = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ev
spec.loader.exec_module(ev)
snapshot = ev.load_snapshot(sys.argv[2]).snapshot
signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
try:
    ev.save_snapshot(snapshot, sys.argv[3])
except ev.EvidenceError as exc:
    if exc.code == "IO_ERROR":
        sys.exit(0)
sys.exit(1)
'''
    result = subprocess.run([sys.executable, "-B", "-c", program, ev.__file__, str(source), str(destination)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert not destination.exists()


def test_concurrent_different_saves_do_not_overwrite(ev, inputs, tmp_path):
    """A-EV-05: two writers publish at most one artifact without replacement."""
    run_publication_scenario(ev, inputs, tmp_path, "concurrent_saves")


@pytest.mark.parametrize("scenario", ["publication_race", "reader_visibility", "failed_writer"])
def test_controlled_publication_boundaries(ev, inputs, tmp_path, scenario):
    """A-EV-05: force the publication window and inspect visibility mid-write."""
    run_publication_scenario(ev, inputs, tmp_path, scenario)


def run_publication_scenario(ev, inputs, tmp_path, scenario):
    # The subprocess owns the audit hook and patched stdlib I/O. No production
    # hook or particular publication primitive is required from evidence.py.
    helper = Path(__file__).with_name("publication_checks.py")
    request = tmp_path / "request.json"
    request.write_text(json.dumps(inputs), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-B", str(helper), "--module", ev.__file__,
         "--inputs", str(request), "--scenario", scenario],
        capture_output=True, text=True, timeout=25,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["scenario"] == scenario and report["observed_boundary"]
    assert report["assertions_passed"]


def test_complete_snapshot_is_technically_ready(ev, inputs):
    """A-EV-07: complete matching inputs are ready without historical certification."""
    snapshot = ev.register_reports(**inputs).snapshot
    result = ev.assess_replay(snapshot, required_analysts=inputs["selected_analysts"],
                              expected_context=inputs["context"], expected_snapshot_id=snapshot.snapshot_id)
    assert result.ready and result.expected_identity == "matched"
    assert snapshot.to_dict()["context"]["analysis_cutoff_at"] is None


@pytest.mark.parametrize("case,reason", [
    ("missing", "MISSING_REPORT"), ("empty", "EMPTY_REPORT"),
    ("selection", "ANALYST_SELECTION_MISMATCH"), ("context", "CONTEXT_MISMATCH"),
    ("source", "SOURCE_RUN_MISMATCH"), ("snapshot", "EXPECTED_SNAPSHOT_MISMATCH"),
])
def test_replay_requires_complete_exact_inputs(ev, inputs, case, reason):
    """A-EV-07: partial reuse, incomplete reports and mismatched expectations fail."""
    expected_context = copy.deepcopy(inputs["context"])
    required = list(inputs["selected_analysts"])
    extra = {}
    if case == "missing":
        inputs["analyst_outputs"].pop("news")
    elif case == "empty":
        inputs["analyst_outputs"]["news"] = " \n"
    elif case == "selection":
        required.remove("news")
    elif case == "context":
        expected_context["analysis_date"] = "2026-11-19"
    elif case == "source":
        extra["expected_source_run_id"] = "another-source"
    else:
        extra["expected_snapshot_id"] = "sha256:" + "0" * 64
    snapshot = ev.register_reports(**inputs).snapshot
    result = ev.assess_replay(snapshot, required_analysts=required,
                              expected_context=expected_context, **extra)
    assert not result.ready and reason in codes(result.findings)


def test_load_and_assess_reuse_preserve_original_source(ev, inputs, tmp_path):
    """A-EV-07: standalone reuse does not relabel source or prove graph skipping."""
    original = ev.register_reports(**inputs).snapshot
    path = tmp_path / "reuse.json"
    ev.save_snapshot(original, path)
    loaded = ev.load_snapshot(path).snapshot
    assessment = ev.assess_replay(loaded, required_analysts=inputs["selected_analysts"],
                                 expected_context=inputs["context"])
    assert assessment.ready and assessment.expected_identity == "not_supplied"
    assert loaded.snapshot_id == original.snapshot_id
    assert loaded.source_run_id == original.source_run_id
    assert "consumer_run_id" not in loaded.to_dict()


@pytest.mark.parametrize("case,code", [
    ("source", "INVALID_CONTEXT"), ("symbol", "INVALID_CONTEXT"),
    ("date", "INVALID_CONTEXT"), ("asset", "INVALID_CONTEXT"),
    ("context_extra", "INVALID_CONTEXT"), ("surrogate", "INVALID_REPORT_TYPE"),
])
def test_invalid_registration_context_is_explicit(ev, inputs, case, code):
    """A-EV-01/02: identity/context and strict UTF-8 are not silently coerced."""
    if case == "source":
        inputs["source_run_id"] = " "
    elif case == "symbol":
        inputs["context"]["instrument"]["symbol"] = ""
    elif case == "date":
        inputs["context"]["analysis_date"] = "2026-02-30"
    elif case == "asset":
        inputs["context"]["instrument"]["asset_type"] = "unknown"
    elif case == "context_extra":
        inputs["context"]["inferred_vendor"] = "not-allowed"
    else:
        inputs["analyst_outputs"]["news"] = "\ud800"
    fail_code(ev, code, lambda: ev.register_reports(**inputs))


def test_extra_reference_fields_are_rejected(ev, inputs):
    """A-EV-03: reference shape is exact, with no ambiguous extra routing data."""
    snapshot = ev.register_reports(**inputs).snapshot
    result = ev.validate_reference(snapshot, {
        "snapshot_id": snapshot.snapshot_id, "evidence_id": "news", "source_run_id": "other"})
    assert result.structure == "malformed"
    assert "MALFORMED_REFERENCE" in result.reasons


def test_equivalent_json_layout_preserves_identity(ev, inputs, tmp_path):
    """A-EV-05: identity uses canonical payload, not incidental file formatting."""
    snapshot = ev.register_reports(**inputs).snapshot
    path = tmp_path / "layout.json"
    path.write_text(json.dumps(snapshot.to_dict(), indent=4, sort_keys=True) + "\n", encoding="utf-8")
    loaded = ev.load_snapshot(path, expected_snapshot_id=snapshot.snapshot_id)
    assert loaded.snapshot.to_dict() == snapshot.to_dict()


def test_invalid_utf8_and_io_failure_are_explicit(ev, inputs, tmp_path):
    """A-EV-05: unreadable bytes and missing destinations produce explicit errors."""
    path = tmp_path / "bad-encoding.json"
    path.write_bytes(b"\xff")
    fail_code(ev, "INVALID_JSON", lambda: ev.load_snapshot(path))
    snapshot = ev.register_reports(**inputs).snapshot
    fail_code(ev, "IO_ERROR", lambda: ev.save_snapshot(snapshot, tmp_path / "absent/snapshot.json"))
    fail_code(ev, "IO_ERROR", lambda: ev.load_snapshot(tmp_path / "missing.json"))


def test_invalid_replay_expectations_are_input_errors(ev, inputs):
    """A-EV-07: malformed expectations differ from legitimate mismatches."""
    snapshot = ev.register_reports(**inputs).snapshot
    fail_code(ev, "INVALID_SELECTION", lambda: ev.assess_replay(
        snapshot, required_analysts="news", expected_context=inputs["context"]))
    fail_code(ev, "INVALID_CONTEXT", lambda: ev.assess_replay(
        snapshot, required_analysts=inputs["selected_analysts"], expected_context={}))


def test_incomplete_snapshot_round_trip_does_not_become_ready(ev, inputs, cases, tmp_path):
    """A-EV-05/06/07: persistence preserves incompleteness without live fallback."""
    inputs.update(copy.deepcopy(cases["incomplete"]))
    registered = ev.register_reports(**inputs)
    path = tmp_path / "incomplete.json"
    ev.save_snapshot(registered.snapshot, path)
    loaded = ev.load_snapshot(path)
    assert loaded.snapshot.to_dict() == registered.snapshot.to_dict()
    assert {"MISSING_REPORT", "EMPTY_REPORT"} <= codes(loaded.diagnostics)
    readiness = ev.assess_replay(loaded.snapshot, required_analysts=inputs["selected_analysts"],
                                expected_context=inputs["context"])
    assert not readiness.ready
