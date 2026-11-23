"""Pin the unchanged PM hook's complete opt-in result and legacy omission."""

import json

import pytest

from .test_graph_guard_opt_in import _run, offline as offline

pytestmark = pytest.mark.unit


def test_explicit_guard_opt_in_records_the_complete_pm_reason_chain(
    tmp_path, monkeypatch, offline
):
    state, _ = _run(tmp_path, monkeypatch, guard_enabled=True)
    assert state["guard_enabled"] is True
    result = state["guard_result"]
    print("guard_result=" + json.dumps(result, sort_keys=True))

    assert result["executable"] is False
    assert result == {
        "contract": "validation-decision/1.1",
        "verdict": "BLOCK",
        "reason_code": "OVERRIDE_REJECTED",
        "checkpoint": "pm",
        "executable": False,
        "rules_hit": [
            {"checkpoint": "trader", "reason_code": "MISSING_FIELD"},
            {"checkpoint": "pm", "reason_code": "OVERRIDE_REJECTED"},
        ],
    }


def test_omitted_guard_opt_in_preserves_legacy_result(tmp_path, monkeypatch, offline):
    state, signal = _run(tmp_path, monkeypatch)

    assert signal == state["final_rating"] == "Overweight"
    assert "**Rating**: Overweight" in state["final_trade_decision"]
    assert "guard_enabled" not in state
    assert "guard_result" not in state
