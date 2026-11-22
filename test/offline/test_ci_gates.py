"""Offline tests for the CS5351 blocking gates (D7 §6.1-6.6).

Each gate has at least one negative test (a case that must block) plus a passing
case. One test builds a real temporary git repo to exercise the three-dot diff used
by the PR-scoped gates. No network, stdlib + PyYAML + jsonschema only.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_test_approval  # noqa: E402
from check_ai_use_log import _entries, _ids  # noqa: E402
from gate_common import GATED_PREFIXES, changed, gated  # noqa: E402

# --- Gate 6: AI-use log ------------------------------------------------------

NEW_ENTRY = """
- id: "60252993-linan-ai-use-99"
  human_reviewed: true
"""
UNREVIEWED_ENTRY = """
- id: "60252993-linan-ai-use-99"
  human_reviewed: false
"""
OLD_ENTRY = """
- id: "60252993-linan-ai-use-01"
  human_reviewed: true
"""


def _log(*entries: str) -> str:
    return "entries:\n" + "".join(entries)


def _ai_use_gate(base_text: str, head_text: str, changed_paths: list[str]) -> tuple[bool, str]:
    if not gated(changed_paths):
        return True, "docs-only"
    base_ids = _ids(_entries(base_text))
    head_entries = _entries(head_text)
    head_ids = _ids(head_entries)
    if len(head_ids) != len(set(head_ids)):
        return False, "duplicate id"
    new_entries = [e for e in head_entries if e.get("id") not in base_ids]
    if not new_entries:
        return False, "no new entry"
    if any(e.get("human_reviewed") is not True for e in new_entries):
        return False, "not human_reviewed"
    return True, "ok"


def test_ai_use_missing_entry_fails():
    assert _ai_use_gate(_log(OLD_ENTRY), _log(OLD_ENTRY), ["src/x.py"]) == (False, "no new entry")


def test_ai_use_new_entry_passes():
    assert _ai_use_gate(_log(OLD_ENTRY), _log(OLD_ENTRY, NEW_ENTRY), ["src/x.py"])[0] is True


def test_ai_use_docs_only_passes():
    assert _ai_use_gate(_log(OLD_ENTRY), _log(OLD_ENTRY), ["docs/x.md"]) == (True, "docs-only")


def test_ai_use_duplicate_id_fails():
    result = _ai_use_gate(_log(OLD_ENTRY), _log(OLD_ENTRY, NEW_ENTRY, NEW_ENTRY), ["src/x.py"])
    assert result == (False, "duplicate id")


def test_ai_use_not_human_reviewed_fails():
    result = _ai_use_gate(_log(OLD_ENTRY), _log(OLD_ENTRY, UNREVIEWED_ENTRY), ["src/x.py"])
    assert result == (False, "not human_reviewed")


def test_tests_dir_is_not_gated():
    assert _ai_use_gate(_log(OLD_ENTRY), _log(OLD_ENTRY), ["tests/y.py"])[0] is True


def test_prompts_and_github_are_not_gated():
    passed, reason = _ai_use_gate(
        _log(OLD_ENTRY), _log(OLD_ENTRY), ["prompts/p.yaml", ".github/workflows/ci.yml"]
    )
    assert passed is True
    assert reason == "docs-only"


# --- Gate 1: test approval ---------------------------------------------------

APPROVAL = """
approvals:
  - src: "src/tradingagents/dataflows"
    approver: "60252993"
    date: "2026-11-21"
    tests: ["test/offline/test_router.py"]
"""


def _approvals(text: str) -> list[dict]:
    return check_test_approval.load_approvals(text)


def test_approval_covered_src_passes():
    approvals = _approvals(APPROVAL)
    assert check_test_approval.is_covered("src/tradingagents/dataflows/router.py", approvals)


def test_approval_uncovered_src_fails():
    assert not check_test_approval.is_covered("src/tradingagents/other.py", _approvals(APPROVAL))


def test_approval_missing_approver_fails():
    text = """
approvals:
  - src: "src/tradingagents/other.py"
    approver: ""
    date: "2026-11-21"
"""
    assert not check_test_approval.is_covered("src/tradingagents/other.py", _approvals(text))


def test_approval_bad_date_fails():
    text = """
approvals:
  - src: "src/tradingagents/other.py"
    approver: "60252993"
    date: "21-11-2026"
"""
    assert not check_test_approval.is_covered("src/tradingagents/other.py", _approvals(text))


def test_approval_exact_path_passes():
    text = """
approvals:
  - src: "src/tradingagents/run_recorder.py"
    approver: "60252993"
    date: "2026-11-21"
"""
    approvals = _approvals(text)
    assert check_test_approval.is_covered("src/tradingagents/run_recorder.py", approvals)
    assert not check_test_approval.is_covered("src/tradingagents/run_recorder.pyc", approvals)


def test_approval_empty_records_covers_nothing():
    assert check_test_approval.is_covered("src/x.py", []) is False


# --- Shared diff: real git repo ----------------------------------------------


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def test_real_git_repo_diff(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "e@example.com")
    _git(repo, "config", "user.name", "E")
    (repo / "src").mkdir()
    (repo / "src" / "gone.py").write_text("y = 2\n")
    (repo / "docs").mkdir()
    (repo / "docs" / "note.md").write_text("note\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "feature")
    (repo / "src" / "gone.py").unlink()
    (repo / "docs" / "note.md").write_text("note changed\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feature")
    head = _git(repo, "rev-parse", "HEAD")

    paths = changed(base, head, repo=str(repo))
    assert "src/gone.py" in paths, "deletions must be reported"
    assert "docs/note.md" in paths
    assert "src/" in GATED_PREFIXES
    assert "prompts/" not in GATED_PREFIXES and ".github/" not in GATED_PREFIXES
