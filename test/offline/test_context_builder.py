"""Check deduplication against B's evidence and history-priority requirements."""

import pytest

from tradingagents.context_builder import build


@pytest.mark.parametrize("priority", [{"unresolved": True}, {"disagreement": True}, {"citation_count": 1}])
def test_history_priority_survives_deduplication(priority):
    older = {"id": "old", "text": "Outstanding supply issue.", "speaker": "bull"}
    current = {**older, "id": "current", **priority}
    copy = {**current, "id": "copy"}

    pack = build({"L4": [older, current, copy]}, 500, compaction_threshold=0.01)

    assert [block.id for block in pack.blocks if block.layer == "L4"] == ["current"]
    assert [(item.id, item.reason, item.duplicate_of) for item in pack.dropped] == [
        ("copy", "duplicate", "current"),
        ("old", "routine history", None),
    ]
