"""Offline checks for pre-construction checkpoint signature and thread identity."""

import hashlib
import json
import sqlite3
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest

from tradingagents.graph import checkpointer, trading_graph
from tradingagents.portfolio import PortfolioContext

pytestmark = pytest.mark.unit

ANALYSTS = ("market", "news")
TICKER = "NVDA"
DATE = "2026-01-09"


@pytest.fixture
def config(tmp_path, monkeypatch):
    config = deepcopy(trading_graph.DEFAULT_CONFIG)
    config.update(
        max_debate_rounds=3,
        max_risk_discuss_rounds=2,
        max_tool_rounds=2,
        max_recur_limit=20,
        results_dir=str(tmp_path / "results"),
        data_cache_dir=str(tmp_path / "cache"),
        memory_log_path=str(tmp_path / "memory" / "log.md"),
        checkpoint_enabled=True,
        llm_max_retries=7,
    )
    monkeypatch.setattr(trading_graph, "DEFAULT_CONFIG", deepcopy(config))
    return config


@pytest.fixture
def graph_factory(monkeypatch):
    monkeypatch.setattr(trading_graph, "create_tier_client", Mock())
    monkeypatch.setattr(trading_graph, "set_config", Mock())
    return trading_graph.TradingAgentsGraph


@pytest.fixture
def legacy_signature():
    """Independent reference for the pre-extraction signature bytes."""
    excluded = {
        "results_dir", "data_cache_dir", "memory_log_path", "checkpoint_enabled", "llm_max_retries",
    }

    def expected(config, analysts, asset_type, portfolio_tag):
        settings = {key: value for key, value in config.items() if key not in excluded}
        digest = hashlib.sha256(json.dumps(settings, sort_keys=True, default=str).encode()).hexdigest()[:12]
        return (
            f"analysts={','.join(analysts)}|debate={config['max_debate_rounds']}"
            f"|risk={config['max_risk_discuss_rounds']}|asset={asset_type}|portfolio={portfolio_tag}"
            f"|analysts=parallel|memory=parallel|settings={digest}"
        )

    return expected


@pytest.mark.parametrize(
    "kwargs", [{}, {"config": None}, {"config": {}}], ids=["omitted", "none", "empty"]
)
def test_signature_uses_graph_defaults(config, graph_factory, legacy_signature, kwargs):
    """Provisional: INV-C-LOCAL-CKPT-002."""
    graph = graph_factory(ANALYSTS, **kwargs)
    signature = trading_graph.checkpoint_run_signature(selected_analysts=ANALYSTS, **kwargs)
    assert signature == graph._run_signature("stock")
    assert signature == legacy_signature(config, ANALYSTS, "stock", "none")


@pytest.mark.parametrize(("variant", "depth"), [(None, 3), ("v0", 2), ("v1", 1)])
def test_signature_preserves_variant_and_effective_depths(
    config, graph_factory, legacy_signature, variant, depth
):
    """Provisional: INV-C-LOCAL-CKPT-002."""
    original = deepcopy(config)
    graph = graph_factory(ANALYSTS, config=config, workflow_variant=variant)
    signature = trading_graph.checkpoint_run_signature(
        selected_analysts=ANALYSTS, config=config, workflow_variant=variant
    )
    at_depth = {**original, "max_debate_rounds": depth}
    expected = legacy_signature(at_depth, ANALYSTS, "stock", "none")
    if variant is not None:
        assert signature != trading_graph.checkpoint_run_signature(
            selected_analysts=ANALYSTS, config=at_depth
        )
        expected += f"|workflow_variant={variant}"
    assert signature == graph._run_signature("stock")
    assert signature == expected
    assert config == original


def test_signature_preserves_analyst_order_asset_type_and_portfolio(
    config, graph_factory, legacy_signature
):
    """Provisional: INV-C-LOCAL-CKPT-002."""
    flat = PortfolioContext()
    held = PortfolioContext.model_validate({"positions": [{"ticker": TICKER, "quantity": 2}]})
    signatures = set()
    for analysts, asset_type, portfolio in (
        (ANALYSTS, "stock", None),
        (ANALYSTS[::-1], "stock", None),
        (ANALYSTS, "crypto", None),
        (ANALYSTS, "stock", flat),
        (ANALYSTS, "stock", held),
    ):
        graph = graph_factory(analysts, config=config)
        signature = trading_graph.checkpoint_run_signature(
            selected_analysts=analysts, config=config, asset_type=asset_type, portfolio=portfolio
        )
        portfolio_tag = "none" if portfolio is None else portfolio.fingerprint()
        assert signature == legacy_signature(config, analysts, asset_type, portfolio_tag)
        assert signature == graph._run_signature(asset_type, portfolio)
        signatures.add(signature)
    assert len(signatures) == 5


def test_preconstruction_thread_id_uses_signature_and_run_key(config, graph_factory):
    """Provisional: REQ-C-LOCAL-CKPT-002."""
    graph = graph_factory(ANALYSTS, config=config, workflow_variant="v1")
    signature = graph._run_signature("stock")
    kwargs = {"selected_analysts": ANALYSTS, "config": config, "workflow_variant": "v1"}
    unkeyed = trading_graph.checkpoint_thread_id(TICKER, DATE, **kwargs)
    first = trading_graph.checkpoint_thread_id(TICKER, DATE, run_key="r1", **kwargs)
    second = trading_graph.checkpoint_thread_id(TICKER, DATE, run_key="r2", **kwargs)
    assert unkeyed == checkpointer.thread_id(TICKER, DATE, signature)
    assert first == checkpointer.thread_id(TICKER, DATE, signature, run_key="r1")
    assert second == checkpointer.thread_id(TICKER, DATE, signature, run_key="r2")
    assert first == trading_graph.checkpoint_thread_id(TICKER, DATE, run_key="r1", **kwargs)
    assert len({unkeyed, first, second}) == 3


def test_public_entry_points_have_no_side_effects(config, tmp_path, monkeypatch):
    """Provisional: REQ-C-LOCAL-CKPT-002."""
    def forbidden(*args, **kwargs):
        pytest.fail("pure checkpoint calculation attempted a side effect")

    with monkeypatch.context() as guard:
        guard.setattr(trading_graph.os, "makedirs", forbidden)
        guard.setattr(Path, "mkdir", forbidden)
        guard.setattr(sqlite3, "connect", forbidden)
        for name in ("set_config", "create_tier_client", "get_checkpointer", "checkpoint_step"):
            guard.setattr(trading_graph, name, forbidden)
        guard.setattr(trading_graph.TradingAgentsGraph, "__init__", forbidden)

        kwargs = {"selected_analysts": ANALYSTS, "config": config}
        assert trading_graph.checkpoint_run_signature(**kwargs, workflow_variant="v0")
        assert trading_graph.checkpoint_thread_id(TICKER, DATE, **kwargs, run_key="r1")
        for variant, reason in (("v2", "unavailable"), ("V1", "Invalid"), (1, "Invalid")):
            with pytest.raises(ValueError, match=reason):
                trading_graph.checkpoint_run_signature(**kwargs, workflow_variant=variant)
            with pytest.raises(ValueError, match=reason):
                trading_graph.checkpoint_thread_id(TICKER, DATE, **kwargs, workflow_variant=variant)

    assert list(tmp_path.iterdir()) == []
