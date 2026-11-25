"""Exercise fixed pruning through the real graph, state log, and report writer."""

import hashlib
import json
import os
import socket
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from curl_cffi import requests as curl_requests
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

pytestmark = pytest.mark.unit

TICKER = "NVDA"
TRADE_DATE = "2026-01-09"
ASSET = "stock"
TEXT = "Report.\n\n**Rating**: Overweight\n\nFINAL TRANSACTION PROPOSAL: **BUY**"
RISK_ROLES = ["Aggressive Analyst", "Conservative Analyst", "Neutral Analyst"]
OMITTED = object()


class RouteModel(BaseChatModel):
    """Like TimedModel in tests/test_graph_end_to_end.py, trace the actual model calls."""

    calls: list[str | None] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fixed-pruning-script"

    def bind_tools(self, tools, **kwargs):
        # The bound model returns a report directly without requesting a tool.
        return self.model_copy()

    def with_structured_output(self, schema, **kwargs):
        raise NotImplementedError  # Use the existing free-text fallback.

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        metadata = (run_manager.metadata or {}) if run_manager is not None else {}
        self.calls.append(metadata.get("langgraph_node"))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=TEXT))])


@pytest.fixture
def offline(monkeypatch):
    network_attempts = []

    def refuse(*args, **kwargs):
        network_attempts.append(True)
        raise AssertionError("fixed-pruning test attempted network access")

    def connect(sock, *args, **kwargs):
        # Keep local UNIX sockets usable; block IPv4 and IPv6.
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            refuse()
        return real_connect(sock, *args, **kwargs)

    def connect_ex(sock, *args, **kwargs):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            refuse()
        return real_connect_ex(sock, *args, **kwargs)

    real_connect, real_connect_ex = socket.socket.connect, socket.socket.connect_ex
    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    # yfinance uses libcurl, not Python sockets.
    monkeypatch.setattr(curl_requests.Session, "request", refuse)
    monkeypatch.setattr(curl_requests.AsyncSession, "request", refuse)
    for name in tuple(os.environ):
        if name.startswith("TRADINGAGENTS_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")

    from tradingagents.dataflows import config as data_config
    from tradingagents.default_config import build_default_config
    from tradingagents.graph import trading_graph

    monkeypatch.setattr(data_config, "_config", build_default_config())
    model = RouteModel(cache=False)
    client_factory = Mock(return_value=SimpleNamespace(get_llm=lambda: model))
    monkeypatch.setattr(trading_graph, "create_tier_client", client_factory)
    monkeypatch.setattr(
        trading_graph, "resolve_instrument_identity", lambda ticker: {"company_name": "NVIDIA"}
    )
    yield trading_graph, build_default_config, model, client_factory
    # Fail even when a best-effort application path swallowed the exception.
    assert not network_attempts


def _config(offline, root, **overrides):
    config = offline[1]()
    config.update(
        results_dir=str(root / "results"),
        data_cache_dir=str(root / "cache"),
        memory_log_path=str(root / "memory" / "trading_memory.md"),
        checkpoint_enabled=False,
    )
    config.update(overrides)
    return config


def _graph(offline, config, variant=OMITTED):
    kwargs = {} if variant is OMITTED else {"workflow_variant": variant}
    return offline[0].TradingAgentsGraph(selected_analysts=("market",), config=config, **kwargs)


def _run_and_check(offline, graph, config, depth):
    final_state, rating = graph.propagate(TICKER, TRADE_DATE, asset_type=ASSET)
    assert rating == final_state["final_rating"] == "Overweight"
    # The Market Analyst subgraph's model node is named "agent".
    assert offline[2].calls == [
        "agent",
        *(["Bull Researcher", "Bear Researcher"] * depth),
        "Research Manager",
        "Trader",
        *RISK_ROLES,
        "Portfolio Manager",
    ]
    assert final_state["investment_debate_state"]["count"] == 2 * depth
    assert final_state["risk_debate_state"]["count"] == 3

    settings = graph.run_settings()
    assert settings["max_debate_rounds"] == depth
    assert settings["max_risk_discuss_rounds"] == 1
    path = (
        Path(config["results_dir"]) / TICKER / "TradingAgentsStrategy_logs"
        / f"full_states_log_{TRADE_DATE}.json"
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["run_settings"] == settings
    assert persisted["final_rating"] == "Overweight"
    assert persisted["final_trade_decision"] == final_state["final_trade_decision"]
    return final_state, settings


def _legacy_signature(config):
    """Fingerprint algorithm frozen from f4957b2, independent of the graph helper."""
    excluded = {
        "results_dir", "data_cache_dir", "memory_log_path", "checkpoint_enabled", "llm_max_retries"
    }
    settings = {key: value for key, value in config.items() if key not in excluded}
    payload = json.dumps(settings, sort_keys=True, default=str).encode()
    digest = hashlib.sha256(payload).hexdigest()[:12]
    return f"analysts=market|debate=3|risk=1|asset=stock|portfolio=none|analysts=parallel|memory=parallel|settings={digest}"


def test_omitted_variant_keeps_default_route(offline, tmp_path):
    """Provisional: INV-C-LOCAL-V1-001."""
    config = _config(offline, tmp_path)
    assert config["max_debate_rounds"] == 1
    graph = _graph(offline, config)

    _, settings = _run_and_check(offline, graph, config, depth=1)

    assert "workflow_variant" not in settings


@pytest.mark.parametrize("variant", [OMITTED, None], ids=["omitted", "none"])
def test_legacy_custom_depth_and_signature_are_preserved(offline, tmp_path, variant):
    """Provisional: INV-C-LOCAL-V1-001 and INV-C-LOCAL-V1-003."""
    config = _config(offline, tmp_path, max_debate_rounds=3)
    original = deepcopy(config)
    graph = _graph(offline, config, variant)

    _, settings = _run_and_check(offline, graph, config, depth=3)

    assert "workflow_variant" not in settings
    assert config == original
    assert graph._run_signature(ASSET) == _legacy_signature(original)


@pytest.mark.parametrize(("variant", "depth"), [("v0", 2), ("v1", 1)])
def test_explicit_variants_use_fixed_depth_and_finish_reports(offline, tmp_path, variant, depth):
    """Provisional: REQ-C-LOCAL-V1-001 and INV-C-LOCAL-V1-001."""
    config = _config(offline, tmp_path, max_debate_rounds=3)
    original = deepcopy(config)
    defaults = deepcopy(offline[0].DEFAULT_CONFIG)
    graph = _graph(offline, config, variant)

    final_state, settings = _run_and_check(offline, graph, config, depth)
    output = tmp_path / "report"
    report = graph.save_reports(final_state, TICKER, save_path=output, html=True)

    assert settings["workflow_variant"] == variant
    assert graph.config is not config
    assert config == original
    assert defaults == offline[0].DEFAULT_CONFIG
    assert report == output / "complete_report.md"
    assert "Overweight" in report.read_text(encoding="utf-8")
    assert "Overweight" in (output / "5_portfolio" / "decision.md").read_text(encoding="utf-8")
    html = (output / "complete_report.html").read_text(encoding="utf-8")
    assert "<html" in html.lower()
    assert "Overweight" in html


def test_explicit_signature_distinguishes_preset_at_equal_depth(offline, tmp_path):
    """Provisional: INV-C-LOCAL-V1-003."""
    legacy = _graph(offline, _config(offline, tmp_path / "legacy"))
    v1 = _graph(offline, _config(offline, tmp_path / "v1"), "v1")
    repeat = _graph(offline, _config(offline, tmp_path / "repeat"), "v1")

    assert legacy.run_settings()["max_debate_rounds"] == v1.run_settings()["max_debate_rounds"] == 1
    assert v1._run_signature(ASSET) != legacy._run_signature(ASSET)
    assert v1._run_signature(ASSET) == repeat._run_signature(ASSET)


@pytest.mark.parametrize(
    ("variant", "reason"),
    [("v2", "unavailable"), ("v3", "invalid"), ("V1", "invalid"), ("", "invalid"), (1, "invalid")],
    ids=["unavailable-v2", "unknown", "wrong-case", "empty", "non-string"],
)
def test_rejected_variant_has_no_construction_side_effects(
    offline, tmp_path, monkeypatch, variant, reason
):
    """Provisional: INV-C-LOCAL-V1-002."""
    trading_graph, _, model, client_factory = offline
    set_config = Mock()
    monkeypatch.setattr(trading_graph, "set_config", set_config)
    config = _config(offline, tmp_path / "rejected")

    with pytest.raises(ValueError, match=rf"(?i)\b{reason}\b"):
        _graph(offline, config, variant)

    set_config.assert_not_called()
    client_factory.assert_not_called()
    assert model.calls == []
    assert list(tmp_path.iterdir()) == []
