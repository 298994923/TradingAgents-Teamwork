import json

import pytest

from tradingagents.b_interfaces import PromptReceipts


@pytest.mark.parametrize(("expected", "digests", "complete"), [
    (None, ["b" * 64], True), (1, ["b" * 64], True),
    (2, ["b" * 64], False), (0, ["b" * 64], False),
    (None, [], False), (0, [], False),
    (None, ["b" * 64, None], False), (2, ["b" * 64, None], False),
])
def test_receipt_completeness(tmp_path, expected, digests, complete):
    collector = PromptReceipts("fixture")
    for digest in digests:
        collector.record({"role": "bull", "prompt_hashes": {"b.bull": "a" * 64},
                          "input_sha256": digest})
    collector.finish(tmp_path, expected_calls=expected)
    payload = json.loads((tmp_path / "fixture/prompt_receipts.json").read_text())
    assert payload["expected_calls"] == expected
    assert payload["input_evidence"] == ("完整" if complete else "输入取证不完整")
