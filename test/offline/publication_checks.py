"""Revision 2 test-only publication checks and standalone strength probes.

Not evidence.py, not a storage implementation, and not acceptance evidence.
Run each real-module scenario in a subprocess: audit hooks cannot be removed.
No pytest dependency; the draft pytest tests invoke this same harness.
"""

import argparse
import builtins
import copy
import errno
import hashlib
import importlib.util
import io
import json
import os
import socket
import sys
import tempfile
import threading
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

WAIT_SECONDS = 5


def verify_artifact(data, expected):
    """Independent oracle: exact payload, every content hash, then full digest."""
    payload = json.loads(data.decode("utf-8"))
    assert payload == expected, "published artifact differs from expected winner"
    for slot in payload["reports"].values():
        content = slot["content"]
        digest = None if content is None else hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert slot["content_sha256"] == digest, "content hash is inconsistent"
    payload = dict(payload)
    identity = payload.pop("snapshot_id")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False).encode("utf-8")
    assert identity == "sha256:" + hashlib.sha256(canonical).hexdigest(), "snapshot hash is inconsistent"


class Worker:
    """Daemon worker with bounded waits, exception capture and explicit release."""

    def __init__(self, operation):
        self.done = threading.Event()
        self.error = None
        self.result = None

        def run():
            try:
                self.result = operation()
            except BaseException as exc:
                self.error = exc
            finally:
                self.done.set()

        self.thread = threading.Thread(target=run, daemon=True)

    def finish(self):
        assert self.done.wait(WAIT_SECONDS), "writer did not finish within the bounded wait"
        self.thread.join(timeout=WAIT_SECONDS)
        assert not self.thread.is_alive(), "writer remained alive"


def is_path(value, expected):
    if not isinstance(value, (str, bytes, os.PathLike)):
        return False
    return os.path.abspath(os.fsdecode(value)) == str(expected)


def check_publication_race(save, destination, winner):
    """Publish a fixture winner after the contender's checks, before its effect.

    This competing publisher deliberately does not call save_snapshot: it must
    not inherit the candidate's lock/scheduler behavior. It installs a complete,
    already-verified artifact while the candidate writer is paused. The contract
    requires no replacement when an existing artifact appears at publication.
    """
    entered, release = threading.Event(), threading.Event()
    active = True
    winner_bytes = json.dumps(winner, ensure_ascii=False).encode("utf-8")
    donor = destination.with_name("fixture-winner.json")
    donor.write_bytes(winner_bytes)
    verify_artifact(winner_bytes, winner)
    worker = Worker(lambda: save(destination))

    def audit(event, args):
        if not active or threading.current_thread() is not worker.thread:
            return
        mutation = False
        if event == "open":
            path, _mode, flags = args
            mutation = is_path(path, destination) and bool(
                flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        elif event in {"os.rename", "os.link"}:
            mutation = is_path(args[1], destination)
        if mutation and not entered.is_set():
            entered.set()
            if not release.wait(WAIT_SECONDS):
                raise AssertionError("publication controller did not release writer")

    sys.addaudithook(audit)
    worker.thread.start()
    try:
        assert entered.wait(WAIT_SECONDS), "destination mutation boundary was not exercised"
        os.link(donor, destination)  # Test-side competing publication, not a production requirement.
        assert destination.read_bytes() == winner_bytes
    finally:
        release.set()
        worker.finish()
        active = False
    assert destination.read_bytes() == winner_bytes, "competing writer overwrote the published winner"
    verify_artifact(destination.read_bytes(), winner)
    assert getattr(worker.error, "code", None) == "DESTINATION_CONFLICT", (
        "competing writer did not report DESTINATION_CONFLICT", repr(worker.error))
    return {"observed_boundary": entered.is_set(), "assertions_passed": True}


class PausedStream:
    def __init__(self, stream, pause):
        self.stream = stream
        self.pause = pause

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def __enter__(self):
        self.stream.__enter__()
        return self

    def __exit__(self, *args):
        return self.stream.__exit__(*args)

    def write(self, data):
        if data and self.pause.should_pause(self.stream.name):
            count = self.stream.write(data[:1])
            self.stream.flush()
            self.pause.wait_for_reader()
            return count + self.stream.write(data[1:])
        return self.stream.write(data)

    def writelines(self, lines):
        for line in lines:
            self.write(line)


class WritePause:
    """Split the first staged/destination write at stdlib I/O boundaries.

    Cover builtins.open, io.open (Path.open), os.fdopen and os.write. This does
    not assume a temporary filename or a link/rename publication primitive.
    Native writes bypassing these boundaries are not claimed as covered; such
    a candidate must adapt the test-side instrumentation before claiming a pass.
    """

    def __init__(self, directory, *, inject_failure=False):
        self.directory = directory
        self.entered = threading.Event()
        self.release = threading.Event()
        self.owner = None
        self.fds = {}
        self.inject_failure = inject_failure

    def should_pause(self, name):
        if threading.current_thread() is not self.owner or self.entered.is_set():
            return False
        if isinstance(name, int):
            name = self.fds.get(name)
        if not isinstance(name, (str, bytes, os.PathLike)):
            return False
        return Path(os.path.abspath(os.fsdecode(name))).parent == self.directory

    def wait_for_reader(self):
        self.entered.set()
        if not self.release.wait(WAIT_SECONDS):
            raise AssertionError("reader controller did not release writer")
        if self.inject_failure:
            raise OSError(errno.EIO, "synthetic test-only write failure")

    def install(self, stack):
        for module, name in [(builtins, "open"), (io, "open"), (os, "fdopen")]:
            original = getattr(module, name)

            def opened(*args, _original=original, **kwargs):
                stream = _original(*args, **kwargs)
                return PausedStream(stream, self)

            stack.enter_context(patch.object(module, name, opened))

        original_open, original_write = os.open, os.write

        def opened_fd(path, *args, **kwargs):
            fd = original_open(path, *args, **kwargs)
            self.fds[fd] = path
            return fd

        def written_fd(fd, data):
            if data and self.should_pause(fd):
                count = original_write(fd, data[:1])
                self.wait_for_reader()
                return count + original_write(fd, data[1:])
            return original_write(fd, data)

        stack.enter_context(patch.object(os, "open", opened_fd))
        stack.enter_context(patch.object(os, "write", written_fd))


def check_reader_visibility(save, destination, expected):
    """Read while the first write is physically partial; destination must be safe."""
    pause = WritePause(destination.parent)
    worker = Worker(lambda: save(destination))
    pause.owner = worker.thread
    with ExitStack() as stack:
        pause.install(stack)
        worker.thread.start()
        try:
            assert pause.entered.wait(WAIT_SECONDS), "partial-write boundary was not exercised"
            if destination.exists():
                try:
                    verify_artifact(destination.read_bytes(), expected)
                except (AssertionError, ValueError, UnicodeError) as exc:
                    raise AssertionError("reader observed partial or invalid destination content") from exc
        finally:
            pause.release.set()
            worker.finish()
    assert worker.error is None, repr(worker.error)
    verify_artifact(destination.read_bytes(), expected)
    return {"observed_boundary": pause.entered.is_set(), "assertions_passed": True}


def check_failed_writer(save, destination, winner):
    """Publish winner during staging; inject an I/O failure in its contender."""
    winner_bytes = json.dumps(winner, ensure_ascii=False).encode("utf-8")
    donor = destination.with_name("fixture-winner.json")
    donor.write_bytes(winner_bytes)
    pause = WritePause(destination.parent, inject_failure=True)
    worker = Worker(lambda: save(destination))
    pause.owner = worker.thread
    with ExitStack() as stack:
        pause.install(stack)
        worker.thread.start()
        try:
            assert pause.entered.wait(WAIT_SECONDS), "write-failure boundary was not exercised"
            assert not destination.exists(), "failing writer exposed destination before publication"
            os.link(donor, destination)
            verify_artifact(destination.read_bytes(), winner)
        finally:
            pause.release.set()
            worker.finish()
    assert getattr(worker.error, "code", None) == "IO_ERROR", repr(worker.error)
    assert destination.read_bytes() == winner_bytes, "failed writer changed the published winner"
    verify_artifact(destination.read_bytes(), winner)
    return {"observed_boundary": pause.entered.is_set(), "assertions_passed": True}


class ProbeConflict(Exception):
    code = "DESTINATION_CONFLICT"


class ProbeIOError(Exception):
    code = "IO_ERROR"


def fixture_publisher(payload, *, unsafe):
    """Minimal test-strength doubles, NOT implementations of the evidence API."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def publish(destination):
        if destination.exists():
            raise ProbeConflict()
        if unsafe:
            # Representative defect: check then direct/truncating destination write.
            # Harness pauses AFTER the check, so preprocessing speed is irrelevant.
            destination.write_bytes(data)
            return
        fd, name = tempfile.mkstemp(dir=destination.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            try:
                os.link(name, destination)
            except FileExistsError as exc:
                raise ProbeConflict() from exc
        finally:
            os.unlink(name)

    def probe_save(destination):
        try:
            return publish(destination)
        except OSError as exc:
            raise ProbeIOError() from exc

    return probe_save


def changed_probe_payload(payload):
    """Change fixture identity solely to construct a different probe contender."""
    changed = copy.deepcopy(payload)
    changed["source_run_id"] = "unsafe-probe-contender"
    changed.pop("snapshot_id")
    canonical = json.dumps(changed, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False).encode("utf-8")
    changed["snapshot_id"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return changed


def load_module(path):
    spec = importlib.util.spec_from_file_location("_publication_candidate", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def check_concurrent_saves(module, first, second, destination):
    """Keep the ordinary two-saver check, with bounded process/thread waits."""
    barrier = threading.Barrier(2)

    def save(snapshot):
        barrier.wait(timeout=WAIT_SECONDS)
        return module.save_snapshot(snapshot, destination)

    workers = [Worker(lambda: save(first)), Worker(lambda: save(second))]
    for worker in workers:
        worker.thread.start()
    for worker in workers:
        worker.finish()
    outcomes = [getattr(w.error, "code", None) if w.error else w.result.status for w in workers]
    assert sorted(outcomes) == ["DESTINATION_CONFLICT", "created"], repr(outcomes)
    published = module.load_snapshot(destination).snapshot
    assert published.to_dict() in (first.to_dict(), second.to_dict())
    original = destination.read_bytes()
    verify_artifact(original, published.to_dict())
    loser = second if published.snapshot_id == first.snapshot_id else first
    try:
        module.save_snapshot(loser, destination)
    except module.EvidenceError as exc:
        assert exc.code == "DESTINATION_CONFLICT"
    else:
        raise AssertionError("failed competing writer was not rejected")
    assert destination.read_bytes() == original, "failed competing writer changed winner"
    assert module.load_snapshot(destination, expected_snapshot_id=published.snapshot_id).snapshot.to_dict() == published.to_dict()
    return {"observed_boundary": True, "assertions_passed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--module")
    parser.add_argument("--inputs")
    parser.add_argument("--scenario", choices=["publication_race", "reader_visibility", "failed_writer", "concurrent_saves"])
    args = parser.parse_args()
    scenarios = {"publication_race": check_publication_race,
                 "reader_visibility": check_reader_visibility, "failed_writer": check_failed_writer}
    if args.probe:
        fixture = json.loads(Path(__file__).with_name("evidence_cases.json").read_text(encoding="utf-8"))
        winner = fixture["complete"]["expected_snapshot"]
        contender = changed_probe_payload(winner)
        reports = []
        for unsafe in [False, True]:
            for name, check in scenarios.items():
                with tempfile.TemporaryDirectory(prefix="evidence-strength-") as directory:
                    path = Path(directory) / "snapshot.json"
                    expected = contender if name == "reader_visibility" else winner
                    try:
                        check(fixture_publisher(contender, unsafe=unsafe), path, expected)
                    except AssertionError as exc:
                        assert unsafe, f"positive control failed: {exc}"
                        expected_reason = {
                            "publication_race": "competing writer overwrote the published winner",
                            "reader_visibility": "reader observed partial or invalid destination content",
                            "failed_writer": "failing writer exposed destination before publication",
                        }[name]
                        assert str(exc) == expected_reason, f"probe failed for an unintended reason: {exc}"
                        reports.append({"scenario": name, "double": "unsafe", "rejected": True, "reason": str(exc)})
                    else:
                        assert not unsafe, f"unsafe double escaped {name}"
                        reports.append({"scenario": name, "double": "staged_no_replace_control", "assertions_passed": True})
        print(json.dumps({"kind": "test-strength probe; NOT evidence.py acceptance", "results": reports}))
        return
    if not all([args.module, args.inputs, args.scenario]):
        parser.error("--module, --inputs and --scenario are required")

    def refuse_network(*unused_args, **unused_kwargs):
        raise AssertionError("Publication test subprocess must not access the network")

    socket.socket.connect = refuse_network
    socket.socket.connect_ex = refuse_network
    socket.getaddrinfo = refuse_network
    module = load_module(args.module)
    inputs = json.loads(Path(args.inputs).read_text(encoding="utf-8"))
    winner = module.register_reports(**inputs).snapshot
    inputs["source_run_id"] += "-contender"
    contender = module.register_reports(**inputs).snapshot
    with tempfile.TemporaryDirectory(prefix="evidence-publication-") as directory:
        path = Path(directory) / "snapshot.json"
        if args.scenario == "concurrent_saves":
            report = check_concurrent_saves(module, winner, contender, path)
            print(json.dumps({"scenario": args.scenario, **report}))
            return
        expected = contender if args.scenario == "reader_visibility" else winner
        report = scenarios[args.scenario](lambda p: module.save_snapshot(contender, p), path, expected.to_dict())
        loaded = module.load_snapshot(path, expected_snapshot_id=expected.snapshot_id).snapshot
        assert loaded.to_dict() == expected.to_dict()
        print(json.dumps({"scenario": args.scenario, **report}))


if __name__ == "__main__":
    main()
