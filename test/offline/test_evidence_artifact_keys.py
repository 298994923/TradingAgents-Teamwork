"""A-EV-08 proposed tests, helper-r1: unapproved and unexecuted preparation.

Intended destination: test/offline/test_evidence_artifact_keys.py.
Direct loading bypasses the application initializer. Existing approved tests and
fixtures are not altered. No artifact-key implementation is included here.
"""

import builtins
import copy
import importlib.util
import json
import socket
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
DIGEST = "0123456789abcdef" * 4
IDENTITY = "sha256:" + DIGEST
KEY = "v1/" + DIGEST + ".json"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("Artifact-key tests must not access the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


@pytest.fixture
def repo():
    for parent in Path(__file__).resolve().parents:
        for candidate in (parent, parent / "TradingAgents-Teamwork"):
            if (candidate / "src/tradingagents/evidence.py").is_file():
                return candidate
    pytest.fail("Active Evidence source checkout not found")


@pytest.fixture
def ev(repo):
    name = "_evidence_artifact_keys_under_review"
    spec = importlib.util.spec_from_file_location(name, repo / "src/tradingagents/evidence.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(name, None)


def assert_error(ev, operation, value, path):
    with pytest.raises(ev.EvidenceError) as error:
        operation(value)
    assert type(error.value) is ev.EvidenceError
    assert (error.value.code, error.value.path) == ("INVALID_CONTEXT", path)


@pytest.mark.parametrize("digest", ["0" * 64, "f" * 64, DIGEST])
def test_valid_conversion_and_both_round_trips(ev, digest):
    """A-EV-08: literal expectations avoid two mutually wrong inverse functions."""
    identity, key = "sha256:" + digest, "v1/" + digest + ".json"
    assert ev.artifact_key_for(identity) == key
    assert ev.parse_artifact_key(key) == identity
    assert ev.parse_artifact_key(ev.artifact_key_for(identity)) == identity
    assert ev.artifact_key_for(ev.parse_artifact_key(key)) == key

    class Text(str):
        pass

    assert ev.artifact_key_for(Text(identity)) == key
    assert ev.parse_artifact_key(Text(key)) == identity
    assert type(ev.artifact_key_for(identity)) is str
    assert type(ev.parse_artifact_key(key)) is str


@pytest.mark.parametrize("operation,path", [
    ("artifact_key_for", "/snapshot_id"),
    ("parse_artifact_key", "/artifact_key"),
])
@pytest.mark.parametrize("value", [None, True, 1, b"text", [], {}],
                         ids=["none", "bool", "integer", "bytes", "list", "mapping"])
def test_non_string_inputs_have_stable_errors(ev, operation, path, value):
    """A-EV-08: invalid values never coerce or leak a TypeError."""
    assert_error(ev, getattr(ev, operation), value, path)


@pytest.mark.parametrize("identity", [
    "", DIGEST, "sha512:" + DIGEST, "SHA256:" + DIGEST,
    "sha256:" + DIGEST.upper(), "sha256:" + "a" * 63, "sha256:" + "a" * 65,
    "sha256:" + "a" * 63 + "g", "sha256:" + "a" * 63 + "\uff10",
    " " + IDENTITY, IDENTITY + " ", IDENTITY + "\n",
], ids=["empty", "bare-digest", "wrong-prefix", "uppercase-prefix", "uppercase-hex",
        "short", "long", "non-hex", "non-ascii", "leading-space", "trailing-space", "newline"])
def test_noncanonical_snapshot_ids_are_rejected(ev, identity):
    """A-EV-08: exact grammar; no normalization or permissive end matching."""
    assert_error(ev, ev.artifact_key_for, identity, "/snapshot_id")


@pytest.mark.parametrize("key", [
    "v2/" + DIGEST + ".json", "v1/" + DIGEST + ".JSON",
    "v1\\" + DIGEST + ".json", "v1//" + DIGEST + ".json",
    "v1/extra/" + DIGEST + ".json", "v1/../" + DIGEST + ".json",
    "/" + KEY, "https://example.invalid/" + KEY, "v1%2f" + DIGEST + ".json",
    "v1/" + DIGEST.upper() + ".json", "v1/" + "a" * 63 + ".json",
    "v1/" + "a" * 65 + ".json", "v1/" + "a" * 63 + "g.json",
    " " + KEY, KEY + " ", KEY + "\n",
], ids=["wrong-version", "wrong-suffix", "backslash", "double-slash", "extra-segment",
        "traversal", "absolute", "url", "encoded-separator", "uppercase-hex",
        "short", "long", "non-hex", "leading-space", "trailing-space", "newline"])
def test_noncanonical_artifact_keys_are_rejected(ev, key):
    """A-EV-08: key parsing is not URL or filesystem path interpretation."""
    assert_error(ev, ev.parse_artifact_key, key, "/artifact_key")


def test_helpers_do_not_delegate_to_storage_or_identity_generation(ev, monkeypatch):
    """A-EV-08: valid syntax conversion neither looks up nor creates an artifact."""
    attempts = []

    def refuse(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Pure conversion touched storage or snapshot acquisition")

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", refuse)
        for method in ("open", "read_bytes", "write_bytes", "exists", "stat", "resolve", "mkdir"):
            guard.setattr(Path, method, refuse)
        for name in ("open", "stat", "link", "mkdir", "readlink"):
            guard.setattr(ev.os, name, refuse)
        for name in ("register_reports", "save_snapshot", "load_snapshot", "Snapshot"):
            guard.setattr(ev, name, refuse)
        key = ev.artifact_key_for(IDENTITY)
        identity = ev.parse_artifact_key(KEY)
    assert not attempts
    assert (key, identity) == (KEY, IDENTITY)


def test_existing_fixture_and_apis_remain_compatible(ev, repo, tmp_path):
    """A-EV-08 with A-EV-02/03/05/07: unchanged vector survives key-assisted use."""
    case = json.loads((repo / "test/fixtures/evidence_cases.json").read_text(encoding="utf-8"))["complete"]
    registration = copy.deepcopy(case["registration"])
    snapshot = ev.register_reports(**registration).snapshot
    assert snapshot.to_dict() == case["expected_snapshot"]
    assert snapshot.schema_version == "1"
    key = ev.artifact_key_for(snapshot.snapshot_id)
    assert key == "v1/" + snapshot.snapshot_id[len("sha256:"):] + ".json"
    assert ev.parse_artifact_key(key) == snapshot.snapshot_id

    # The caller chooses/creates this temporary root, not either helper.
    (tmp_path / "v1").mkdir()
    destination = tmp_path / key
    saved = ev.save_snapshot(snapshot, destination)
    assert (saved.status, saved.path) == ("created", destination)
    assert ev.save_snapshot(snapshot, destination).status == "already_present"
    loaded = ev.load_snapshot(destination, expected_snapshot_id=snapshot.snapshot_id)
    assert loaded.expected_identity == "matched"
    assert loaded.snapshot.to_dict() == snapshot.to_dict() == case["expected_snapshot"]
    reference = {"snapshot_id": snapshot.snapshot_id, "evidence_id": "news"}
    checked = ev.validate_reference(loaded.snapshot, reference)
    assert (checked.structure, checked.binding, checked.slot, checked.availability) == (
        "conformant", "matched", "found", "present",
    )
    assert checked.reasons == ()
    assessment = ev.assess_replay(
        loaded.snapshot, required_analysts=registration["selected_analysts"],
        expected_context=registration["context"],
        expected_source_run_id=registration["source_run_id"],
        expected_snapshot_id=snapshot.snapshot_id,
    )
    assert assessment.ready and assessment.findings == ()
