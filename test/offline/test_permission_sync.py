"""Offline tests for the permission-sync gate (D3 / D7 §6.2).

``scripts/check_permission_sync.py`` keeps ``opencode.jsonc`` (the enforced config)
in sync with ``.opencode/permissions.jsonc`` (the course artifact): every path the
artifact marks ``human_only`` or ``protected`` must be covered by opencode.jsonc, and
both files' ``default`` must be ``deny``.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_permission_sync as gate  # noqa: E402


def _perms(**overrides):
    base = {
        "default": "deny",
        "allow": [],
        "deny": ["**/.env"],
        "human_only": [".agent/rules.md"],
        "protected": ["src/tradingagents/dataflows/**"],
    }
    base.update(overrides)
    return base


def _opencode(**overrides):
    base = {
        "default": "deny",
        "allow": [],
        "deny": ["**/.env", "src/tradingagents/dataflows/**"],
        "human_only": [".agent/rules.md"],
    }
    base.update(overrides)
    return base


# --- JSONC loading -----------------------------------------------------------


def test_load_jsonc_strips_line_comments_and_trailing_commas():
    text = """
    {
      // a line comment
      "default": "deny",
      "list": ["a", "b",],  /* trailing comma + block comment */
    }
    """
    data = gate.load_jsonc(text)
    assert data == {"default": "deny", "list": ["a", "b"]}


def test_load_jsonc_keeps_comment_markers_inside_strings():
    text = '{"url": "https://example.test/a//b", "note": "not /* a comment */"}'
    data = gate.load_jsonc(text)
    assert data["url"] == "https://example.test/a//b"
    assert data["note"] == "not /* a comment */"


# --- happy path --------------------------------------------------------------


def test_in_sync_passes():
    assert gate.check(_perms(), _opencode()) == []


# --- default must be deny ----------------------------------------------------


def test_permissions_default_not_deny_blocks():
    problems = gate.check(_perms(default="allow"), _opencode())
    assert any("permissions" in p and "default" in p for p in problems)


def test_opencode_default_not_deny_blocks():
    problems = gate.check(_perms(), _opencode(default="ask"))
    assert any("opencode" in p and "default" in p for p in problems)


# --- coverage of human_only / protected -------------------------------------


def test_uncovered_human_only_blocks():
    perms = _perms(human_only=[".agent/rules.md", "transcripts/**"])
    problems = gate.check(perms, _opencode())  # opencode lacks transcripts/**
    assert any("transcripts/**" in p for p in problems)


def test_uncovered_protected_blocks():
    perms = _perms(protected=["docs/req/requirements.yaml"])
    problems = gate.check(perms, _opencode())  # opencode doesn't deny it
    assert any("docs/req/requirements.yaml" in p for p in problems)


def test_covered_by_deny_glob_passes():
    perms = _perms(protected=["src/tradingagents/dataflows/router.py"])
    opencode = _opencode(deny=["**/.env", "src/tradingagents/dataflows/**"])
    # a concrete file under a denied glob directory is covered
    assert gate.check(perms, opencode) == []


def test_covered_by_human_only_list_passes():
    perms = _perms(human_only=[".agent/rules.md"])
    opencode = _opencode(human_only=[".agent/rules.md"])
    assert gate.check(perms, opencode) == []


def test_fnmatch_glob_coverage():
    perms = _perms(human_only=["transcripts/alice.md"])
    opencode = _opencode(human_only=["transcripts/**"])
    assert gate.check(perms, opencode) == []


# --- real schema: rules live under permission.read / permission.edit ---------


def _real_opencode(edit=None, read=None, **top):
    """An OpenCode-shaped config: nested permission.read / permission.edit maps."""
    base = {
        "default": "deny",
        "permission": {
            "edit": edit if edit is not None else {},
            "read": read if read is not None else {},
        },
    }
    base.update(top)
    return base


def test_nested_permission_edit_and_read_cover_human_only():
    perms = _perms(human_only=[".opencode/rules.md"], protected=[])
    opencode = _real_opencode(
        edit={".opencode/rules.md": "deny"},
        read={".opencode/rules.md": "deny"},
    )
    assert gate.check(perms, opencode) == []


def test_nested_permission_glob_covers_transcripts():
    perms = _perms(human_only=["transcripts/alice.md"], protected=[])
    opencode = _real_opencode(
        edit={"transcripts/*": "deny"},
        read={"transcripts/*": "deny"},
    )
    assert gate.check(perms, opencode) == []


def test_nested_missing_edit_protection_blocks():
    perms = _perms(human_only=[".agent/rules.md"])
    # Read is denied but edit is not: still writable, so not protected.
    opencode = _real_opencode(edit={}, read={".agent/rules.md": "deny"})
    problems = gate.check(perms, opencode)
    assert any(".agent/rules.md" in p for p in problems)


def test_nested_missing_read_protection_blocks():
    perms = _perms(protected=["docs/req/requirements.yaml"])
    opencode = _real_opencode(
        edit={"docs/req/requirements.yaml": "deny"},
        read={},  # readable
    )
    problems = gate.check(perms, opencode)
    assert any("docs/req/requirements.yaml" in p for p in problems)


def test_nested_allow_does_not_cover():
    perms = _perms(human_only=[".agent/rules.md"])
    opencode = _real_opencode(
        edit={".agent/rules.md": "allow"},
        read={".agent/rules.md": "allow"},
    )
    assert gate.check(perms, opencode) != []


def test_nested_scalar_permission_deny_covers_all():
    # permission.read: "deny" is a blanket; edit likewise.
    opencode = {"default": "deny", "permission": {"read": "deny", "edit": "deny"}}
    perms = _perms(human_only=["anything/at/all.md"])
    assert gate.check(perms, opencode) == []


# --- CLI: main() against real files -----------------------------------------


def _write_repo(tmp_path, opencode_text, perms_text):
    (tmp_path / "opencode.jsonc").write_text(opencode_text, encoding="utf-8")
    (tmp_path / ".opencode").mkdir()
    (tmp_path / ".opencode" / "permissions.jsonc").write_text(perms_text, encoding="utf-8")
    return tmp_path


def test_main_passes_on_in_sync_repo(tmp_path, capsys):
    repo = _write_repo(
        tmp_path,
        '{"default": "deny", "deny": ["**/.env"], "human_only": [".agent/rules.md"]}',
        '{"default": "deny", "deny": ["**/.env"], "human_only": [".agent/rules.md"]}',
    )
    assert gate.main(["--root", str(repo)]) == 0


def test_main_blocks_on_drift(tmp_path, capsys):
    repo = _write_repo(
        tmp_path,
        '{"default": "deny", "deny": [], "human_only": []}',
        '{"default": "deny", "deny": [], "human_only": ["transcripts/**"]}',
    )
    assert gate.main(["--root", str(repo)]) == 1
    assert "transcripts/**" in capsys.readouterr().out


def test_main_missing_file_exits_two(tmp_path):
    assert gate.main(["--root", str(tmp_path)]) == 2
