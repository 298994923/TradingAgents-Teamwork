"""Running one analysis from the CLI: build the graph, stream it into the live view, save the report."""

import inspect
import json
import os
import re
import sys
import time
import webbrowser
from dataclasses import replace
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path

import typer
from rich.live import Live

from cli.display import (
    ANALYST_ORDER,
    AnalystWallTimeTracker,
    classify_message_type,
    console,
    create_layout,
    display_complete_report,
    message_buffer,
    update_analyst_statuses,
    update_display,
    update_research_team_status,
)
from cli.selections import depth_from_env, get_user_selections, unattended_gaps
from cli.stats_handler import StatsCallbackHandler
from tradingagents import __version__
from tradingagents.agents.rating import is_review, run_rating
from tradingagents.dataflows.symbols import safe_ticker_component
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.analyst_execution import (
    build_analyst_execution_plan,
)
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.run_recorder import RUN_ID_PATTERN, RunEvent, build_run_id, write_manifest

_VALID_VARIANTS = ("v0", "v1", "v2")


def _validate_variant(value: str) -> str:
    """Accept only a known, lowercase architecture variant slug (``v0``/``v1``/``v2``).

    The value becomes the first segment of the manifest ``run_id`` and a directory
    name under the results root, so an unknown or unsafe value is rejected rather
    than interpolated.
    """
    if value not in _VALID_VARIANTS:
        raise ValueError(
            f"invalid variant {value!r}; expected one of {', '.join(_VALID_VARIANTS)}"
        )
    return value



# The roles whose static-prompt digests gate a run comparison. A manifest must
# carry all three, non-empty, for compare_runs.py to accept the run.
REQUIRED_PROMPT_ROLES = ("bull", "bear", "research_manager")
# B's producers tag each template digest under ``b.<role>``; the manifest wants
# the plain role key. Same digest, relabelled.
_PROMPT_HASH_PREFIX = "b."


class _PromptReceiptCollector:
    """Collect B's ``on_prompt`` receipts and aggregate the three role digests.

    The sink is ``sink``: each receipt is kept verbatim in ``raw_receipts()`` for
    the sidecar (audit trail, original ``b.<role>`` keys) while its template
    digest is recorded under the plain ``<role>`` key. ``prompt_hashes()`` fails
    closed: a missing required role, an empty/None digest, or one role whose
    digests disagree across rounds raises ``ValueError`` rather than writing a
    partial or guessed manifest.
    """

    def __init__(self):
        self._raw: list[dict] = []
        self._digests: dict[str, set[str]] = {}

    def sink(self, receipt: dict) -> None:
        self._raw.append(receipt)
        for key, digest in (receipt.get("prompt_hashes") or {}).items():
            role = key[len(_PROMPT_HASH_PREFIX):] if key.startswith(_PROMPT_HASH_PREFIX) else key
            if role not in REQUIRED_PROMPT_ROLES:
                continue
            self._digests.setdefault(role, set()).add(digest)

    def raw_receipts(self) -> list[dict]:
        return list(self._raw)

    def prompt_hashes(self) -> dict:
        if not self._raw:
            # No receipts at all: a legacy or fake-graph run never attaches the sink.
            # Default to empty (compare_runs refuses it) rather than failing the write.
            return {}
        missing = [role for role in REQUIRED_PROMPT_ROLES if role not in self._digests]
        if missing:
            raise ValueError(
                "cannot write prompt_hashes: no receipt for required role(s) "
                + ", ".join(missing)
            )
        result: dict[str, str] = {}
        for role in REQUIRED_PROMPT_ROLES:
            digests = self._digests[role]
            if any(not digest for digest in digests):
                raise ValueError(
                    f"cannot write prompt_hashes: role {role!r} has an empty hash"
                )
            if len(digests) > 1:
                raise ValueError(
                    f"cannot write prompt_hashes: role {role!r} has disagreeing "
                    f"hashes across receipts ({len(digests)} distinct)"
                )
            result[role] = next(iter(digests))
        return result


def _collect_prompt_receipts() -> _PromptReceiptCollector:
    return _PromptReceiptCollector()


def _run_directory(config: dict, ticker: str, trade_date: str) -> Path:
    """Where this run writes, with the ticker validated as a path component.

    Every other path that interpolates a ticker checks it first; a value of
    ".." here would place the run outside the results directory.
    """
    return Path(config["results_dir"]) / safe_ticker_component(ticker) / trade_date


def _manifest_config_snapshot(config: dict) -> dict:
    """Scalars from ``config`` that are safe to record in a run manifest.

    The recorder already drops secret-pattern keys; keeping only scalar values
    here also excludes nested objects and lists that are not comparable settings.
    ``results_dir`` is a machine-local output path, not a comparable setting, so it
    is left out of the manifest.
    """
    return {
        key: value
        for key, value in config.items()
        if key != "results_dir"
        and (isinstance(value, (str, int, float, bool)) or value is None)
    }


def write_run_manifest(
    *,
    config: dict,
    ticker: str,
    trade_date: str,
    asset_type: str,
    outcome: str | None,
    usage: dict,
    failure: str | None,
    variant: str,
    repeat: int,
    at: datetime,
    version: str,
    duration_seconds: float | None = None,
    started_at: float | None = None,
    clock=None,
    stop_reason: str | None = None,
    evidence_mode: str = "strict",
    prompt_hashes: dict | None = None,
    prompt_receipts: list | None = None,
) -> Path:
    """Write this run's manifest to ``<results_dir>/runs/<run_id>/manifest.json``.

    ``stop_reason`` is read from the run's final state by the caller (C owns the
    value domain); it is ``None`` when the graph did not reach a terminal state.
    ``prompt_hashes`` (B) holds the three role template digests collected from
    ``on_prompt`` and lands in the manifest; ``prompt_receipts`` (the raw receipts)
    are written to a ``prompt-receipts.jsonl`` sidecar beside the manifest for
    audit. Both default to empty when no receipts were collected (e.g. legacy
    runs). ``evidence_snapshot`` (A) is ``None`` until that contract lands.
    ``duration_seconds`` is measured from ``started_at`` and ``clock``
    (``time.time`` by default) when not supplied; passing both keeps it testable.

    A per-run ``evidence-mode.json`` sidecar (E4) is written next to the manifest
    recording the evidence mode and the facts the run observed. It does not change
    the RunEvent v1 15 fields.
    """
    run_id = build_run_id(variant, ticker, trade_date, repeat, at)
    if duration_seconds is None and started_at is not None:
        now = (clock or time.time)()
        duration_seconds = max(0.0, now - started_at)

    event = RunEvent(
        run_id=run_id,
        created_at=at.astimezone(UTC).isoformat(),
        version=version,
        ticker=ticker,
        trade_date=trade_date,
        asset_type=asset_type,
        outcome=outcome,
        config_snapshot=_manifest_config_snapshot(config),
        prompt_hashes=prompt_hashes or {},
        evidence_snapshot=None,
        usage=usage,
        duration_seconds=duration_seconds,
        failure=failure,
        stop_reason=stop_reason,
    )
    runs_dir = Path(config["results_dir"]) / "runs"
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError(f"invalid run_id {run_id!r}")
    while True:
        candidate = _unique_run_id(runs_dir, run_id)
        manifest_dir = runs_dir / candidate
        try:
            manifest_dir.mkdir(parents=True)
            break
        except FileExistsError:
            continue
    run_id = candidate
    event = replace(event, run_id=run_id)
    path = write_manifest(event, manifest_dir / "manifest.json")
    write_evidence_mode(manifest_dir / "evidence-mode.json", run_id, evidence_mode)
    write_prompt_receipts(manifest_dir / "prompt-receipts.jsonl", prompt_receipts, run_id)
    return path


def write_prompt_receipts(path, prompt_receipts: list | None, run_id: str = "") -> Path | None:
    """Write the raw ``on_prompt`` receipts as sidecars (audit trail).

    ``prompt-receipts.jsonl`` keeps every receipt verbatim (B's original
    ``b.<role>`` keys) for E's own audit. A second sidecar,
    ``prompt_receipts.json``, carries the completeness view consumed by the
    shared ``b_interfaces.PromptReceipts`` contract and its tests:
    ``run_id`` / ``expected_calls`` / ``calls`` / ``input_evidence``. Nothing is
    written when no receipts were collected.
    """
    if not prompt_receipts:
        return None
    path = Path(path)
    lines = [
        json.dumps(receipt, sort_keys=True, ensure_ascii=False) for receipt in prompt_receipts
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    calls = [
        {"role": r.get("role"), "run_id": run_id,
         "round_index": r.get("round_index"), "input_sha256": r.get("input_sha256")}
        for r in prompt_receipts
    ]
    complete = bool(calls) and all(c["input_sha256"] for c in calls)
    payload = {"run_id": run_id, "expected_calls": None, "calls": calls,
               "input_evidence": "完整" if complete else "输入取证不完整"}
    path.with_name("prompt_receipts.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


_EVIDENCE_MODES = ("strict", "report_reference")


def write_evidence_mode(path, run_id: str, evidence_mode: str) -> Path:
    """Write the E4 ``evidence-mode.json`` sidecar recording this run's mode.

    E records facts only; the authoritative action and the mode approval belong to
    D/C, so those fields are ``None`` here unless a caller later fills them in.
    """
    if evidence_mode not in _EVIDENCE_MODES:
        raise ValueError(
            f"invalid evidence_mode {evidence_mode!r}; expected one of {', '.join(_EVIDENCE_MODES)}"
        )
    sidecar = {
        "schema_version": 1,
        "run_id": run_id,
        "evidence_mode": evidence_mode,
        "scenario": None,
        "policy_version": None,
        "unknown_time_fields": [],
        "limitations": [],
        "authoritative_action": None,
        "authoritative_reason": None,
        "decided_by": None,
        "snapshot_ref": {"snapshot_id": None, "artifact_key": None},
    }
    path = Path(path)
    path.write_text(json.dumps(sidecar, sort_keys=True, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _unique_run_id(runs_dir: Path, run_id: str) -> str:
    """A run_id whose directory does not exist yet, so a same-minute retry is safe.

    ``build_run_id`` has minute resolution, so two runs started in the same minute
    (or a retry) produce the same id. Appending ``-<n>`` keeps the id within the
    recorder's 64-char pattern and never overwrites an earlier manifest.
    """
    pattern = re.compile(r"^[a-z0-9][a-z0-9.-]{0,62}$")
    candidate = run_id
    suffix = 2
    while (runs_dir / candidate).exists():
        candidate = f"{run_id}-{suffix}"
        if not pattern.match(candidate):
            raise ValueError(f"no free run_id derived from {run_id!r} within 64 chars")
        suffix += 1
    return candidate


def _make_manifest_writer(config: dict, selections: dict, stats_handler, started_at=None, variant="v0", prompt_receipts=None):
    """Return a ``write(failure=..., outcome=...)`` bound to this run's inputs.

    ``variant`` selects the architecture under test and becomes the first segment
    of the manifest ``run_id``; ``repeat`` is 1 and ``created_at`` is now, both
    supplied here so the recorder never reads the clock itself. ``started_at`` is
    the run's start (``time.time()``); forwarding it lets the manifest record a
    real duration. ``prompt_receipts`` is the collector (or ``None`` when no
    receipts were gathered); its aggregated hashes and raw receipts are written
    into the manifest and the sidecar.
    """

    def write(*, failure, outcome, stop_reason=None):
        prompt_hashes = None
        raw_receipts = None
        if prompt_receipts is not None:
            prompt_hashes = prompt_receipts.prompt_hashes()
            raw_receipts = prompt_receipts.raw_receipts()
        return write_run_manifest(
            config=config,
            ticker=selections["ticker"],
            trade_date=selections["analysis_date"],
            asset_type=selections["asset_type"],
            outcome=outcome,
            usage=stats_handler.get_stats(),
            failure=failure,
            variant=variant,
            repeat=1,
            at=datetime.now(UTC),
            version=__version__,
            started_at=started_at,
            stop_reason=stop_reason,
            evidence_mode=config.get("evidence_mode", "strict"),
            prompt_hashes=prompt_hashes,
            prompt_receipts=raw_receipts,
        )

    return write


def _finalize_run_manifest(
    *,
    write,
    graph,
    ticker: str,
    trade_date: str,
    asset_type: str,
    portfolio,
    final_state,
    failure: BaseException | None,
) -> None:
    """Write the manifest, then dispose of (or keep) the checkpoint.

    The manifest is written **before** the checkpoint is cleared, so a crash in
    teardown never loses the record. A failed run still writes a manifest with
    ``failure`` set and keeps its checkpoint for resume; the failure is re-raised.
    ``stop_reason`` is read from ``final_state`` (C's field) with a ``None``
    fallback when the run did not reach a terminal state.
    """
    outcome = None if final_state is None else run_rating(final_state)
    stop_reason = (final_state or {}).get("stop_reason") if failure is None else None
    write(failure=None if failure is None else str(failure), outcome=outcome, stop_reason=stop_reason)

    if failure is not None:
        raise failure

    if final_state is not None:
        graph.record_decision(ticker, trade_date, final_state)
    graph.clear_checkpoint_on_success(ticker, trade_date, asset_type, portfolio)


def _announce_checkpoint_state(graph, ticker: str, trade_date: str) -> None:
    """Say whether this run resumed a saved one, where the user can see it.

    The graph logs this, but nothing in the CLI configures logging and the live
    view owns the screen, so a resume was invisible.
    """
    if getattr(graph, "_resuming", False):
        message_buffer.add_message(
            "System", f"Resuming the saved run for {ticker} on {trade_date}"
        )
    else:
        message_buffer.add_message("System", f"Starting fresh for {ticker} on {trade_date}")


def _build_run_config(selections: dict, checkpoint: bool | None) -> dict:
    """Assemble the run config from interactive selections, honoring env precedence.

    Round counts and checkpoint follow "explicit env/flag wins": an env-applied
    value on DEFAULT_CONFIG is preserved unless the user overrode it on the CLI.
    """
    config = DEFAULT_CONFIG.copy()
    # Research depth sets both round counts, but an explicit env override
    # (TRADINGAGENTS_MAX_DEBATE_ROUNDS / _MAX_RISK_ROUNDS) wins over the
    # interactive selection — leave the env-applied value in place (#977).
    rounds = (("TRADINGAGENTS_MAX_DEBATE_ROUNDS", "max_debate_rounds"),
              ("TRADINGAGENTS_MAX_RISK_ROUNDS", "max_risk_discuss_rounds"))
    depth_was_asked = not depth_from_env()
    for env_var, key in rounds:
        if not os.environ.get(env_var):
            config[key] = selections["research_depth"]
        elif depth_was_asked:
            # The depth question appeared (it is skipped only when both are
            # set), so say which half of the answer the environment overrode.
            console.print(
                f"[green]✓ {key} from environment:[/green] {config[key]} "
                f"(set by {env_var}, so the research depth you chose does not apply to it)"
            )
    config["quick_think_llm"] = selections["quick_think_llm"]
    config["deep_think_llm"] = selections["deep_think_llm"]
    config["backend_url"] = selections["backend_url"]
    config["llm_provider"] = selections["llm_provider"].lower()
    # Provider-specific thinking configuration. Only the main provider's is
    # asked; a tier on another provider keeps its configured value (#1440).
    for key in ("google_thinking_level", "openai_reasoning_effort", "anthropic_effort"):
        if selections.get(key) is not None:
            config[key] = selections[key]
    config["output_language"] = selections.get("output_language", "English")
    # --checkpoint/--no-checkpoint overrides only when explicitly given; omitting
    # the flag preserves TRADINGAGENTS_CHECKPOINT_ENABLED / the default (#976).
    if checkpoint is not None:
        config["checkpoint_enabled"] = checkpoint
    return config


def _graph_accepts_workflow_variant(graph_cls) -> bool:
    """Whether ``graph_cls.__init__`` has an explicit ``workflow_variant`` parameter.

    Only an explicit, named parameter counts. A bare ``**kwargs`` catch-all is *not*
    treated as support: a legacy graph that swallows unknown kwargs would otherwise be
    handed v1 and silently ignore it, mislabelling a v0-compatible run. A graph class
    that cannot introspect returns ``False`` rather than guessing.
    """
    try:
        params = inspect.signature(graph_cls.__init__).parameters
    except (TypeError, ValueError):
        return False
    return "workflow_variant" in params


def _reject_unavailable_variant(variant: str | None, graph_cls=None) -> None:
    """Refuse a variant that the workflow cannot run, before any model call.

    ``None`` means the flag was omitted: that is the legacy run and is always
    allowed. v0 is always allowed. v2 is not delivered yet and is refused
    regardless of the graph. v1 is allowed only when ``graph_cls`` accepts
    ``workflow_variant``; otherwise it is refused (a v0-compatible run must not be
    mislabelled v1).
    """
    if variant is None or variant == "v0":
        return
    if variant == "v2":
        console.print(
            "[red]Variant 'v2' is not available yet: the adaptive workflow is not "
            "delivered. Use --variant v0 (or v1 if the graph supports it).[/red]"
        )
        raise typer.Exit(code=1)
    if graph_cls is None or not _graph_accepts_workflow_variant(graph_cls):
        console.print(
            f"[red]Variant {variant!r} is not available: this graph does not accept "
            "workflow_variant. Run with --variant v0.[/red]"
        )
        raise typer.Exit(code=1)


def _build_graph(graph_cls, selected_analyst_keys, config, callbacks, *, workflow_variant, on_prompt=None):
    """Construct the graph, forwarding ``workflow_variant``/``on_prompt`` when accepted.

    ``on_prompt`` is B's receipt sink; it is forwarded only when supplied so a
    legacy run keeps the inert default (``None``) and the graph stays unchanged.
    """
    kwargs = {"config": config, "debug": True, "callbacks": callbacks}
    if _graph_accepts_workflow_variant(graph_cls):
        kwargs["workflow_variant"] = workflow_variant
    if on_prompt is not None:
        kwargs["on_prompt"] = on_prompt
    return graph_cls(selected_analyst_keys, **kwargs)


def _effective_manifest_variant(graph, requested: str) -> str:
    """The variant the graph actually enabled, from ``run_settings()``, else requested."""
    run_settings = getattr(graph, "run_settings", None)
    if not callable(run_settings):
        return requested
    try:
        settings = run_settings()
    except (TypeError, ValueError):
        return requested
    if not isinstance(settings, dict):
        return requested
    return settings.get("workflow_variant") or requested


# Settings the graph reports that describe what actually ran. The CLI config is the
# requested configuration; the manifest must record these effective values instead.
_EFFECTIVE_SETTING_KEYS = ("max_debate_rounds", "max_risk_discuss_rounds")


def _effective_config(config: dict, graph, workflow_variant: str = "v0") -> dict:
    """Overlay the graph's effective settings onto ``config`` for the manifest.

    A variant preset (or any graph-side adjustment) changes the rounds actually run.
    The manifest's ``config_snapshot`` must reflect that, not the requested config.
    Keys the graph does not report are left as configured.

    ``workflow_variant`` is the effective variant already computed for the run_id's
    first segment (``manifest_variant``), recorded here too so the snapshot and the
    run_id always agree. It is set even when the graph reports nothing.
    """
    effective = dict(config)
    effective["workflow_variant"] = workflow_variant
    run_settings = getattr(graph, "run_settings", None)
    if not callable(run_settings):
        return effective
    try:
        settings = run_settings()
    except (TypeError, ValueError):
        return effective
    if not isinstance(settings, dict):
        return effective
    for key in _EFFECTIVE_SETTING_KEYS:
        if settings.get(key) is not None:
            effective[key] = settings[key]
    return effective


def run_analysis(checkpoint: bool | None = None, portfolio=None, flags=None, variant=None):
    flags = flags or {}
    # ``None`` = the flag was omitted: the legacy run (configured rounds, no preset).
    if variant is not None:
        variant = _validate_variant(variant)
    # Refuse a variant the graph cannot run before any setup or model call: v2 is
    # not delivered, and v1 needs a graph that accepts workflow_variant.
    _reject_unavailable_variant(variant, TradingAgentsGraph)
    # With no terminal nothing can answer a prompt: name every question still
    # open before any model is called, rather than stopping at the first one.
    if not (sys.stdin and sys.stdin.isatty()):
        gaps = unattended_gaps(flags)
        if gaps:
            console.print("[red]No terminal to answer the setup questions. Set:[/red]")
            for gap in gaps:
                console.print(f"  {gap}")
            raise typer.Exit(code=1)

    selections = get_user_selections(flags)

    config = _build_run_config(selections, checkpoint)

    stats_handler = StatsCallbackHandler()

    # Normalize analyst selection to predefined order (selection is a 'set', order is fixed)
    selected_set = {analyst.value for analyst in selections["analysts"]}
    selected_analyst_keys = [a for a in ANALYST_ORDER if a in selected_set]
    analyst_execution_plan = build_analyst_execution_plan(selected_analyst_keys)
    analyst_wall_time_tracker = AnalystWallTimeTracker(analyst_execution_plan)

    # Collect B's on_prompt receipts so the three role template digests reach the
    # manifest and the raw receipts reach the sidecar (compare_runs guard).
    prompt_receipts = _collect_prompt_receipts()

    graph = _build_graph(
        TradingAgentsGraph,
        selected_analyst_keys,
        config,
        [stats_handler],
        workflow_variant=variant,
        on_prompt=prompt_receipts.sink,
    )
    # The variant the graph actually enabled drives the manifest identity, and the
    # graph's effective rounds drive the manifest config snapshot for the writers.
    manifest_variant = _effective_manifest_variant(graph, variant or "v0")
    effective_config = _effective_config(config, graph, manifest_variant)

    message_buffer.init_for_analysis(selected_analyst_keys)

    # Track start time for elapsed display
    start_time = time.time()

    results_dir = _run_directory(config, selections["ticker"], selections["analysis_date"])
    results_dir.mkdir(parents=True, exist_ok=True)
    report_dir = results_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    log_file = results_dir / "message_tool.log"
    log_file.touch(exist_ok=True)

    def save_message_decorator(obj, func_name):
        func = getattr(obj, func_name)

        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            timestamp, message_type, content = obj.messages[-1]
            content = content.replace("\n", " ")  # Replace newlines with spaces
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} [{message_type}] {content}\n")
        return wrapper

    def save_tool_call_decorator(obj, func_name):
        func = getattr(obj, func_name)

        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            timestamp, tool_name, args = obj.tool_calls[-1]
            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} [Tool Call] {tool_name}({args_str})\n")
        return wrapper

    def save_report_section_decorator(obj, func_name):
        func = getattr(obj, func_name)

        @wraps(func)
        def wrapper(section_name, content):
            func(section_name, content)
            if section_name in obj.report_sections and obj.report_sections[section_name] is not None:
                content = obj.report_sections[section_name]
                if content:
                    file_name = f"{section_name}.md"
                    text = "\n".join(str(item) for item in content) if isinstance(content, list) else content
                    with open(report_dir / file_name, "w", encoding="utf-8") as f:
                        f.write(text)
        return wrapper

    message_buffer.add_message = save_message_decorator(message_buffer, "add_message")
    message_buffer.add_tool_call = save_tool_call_decorator(message_buffer, "add_tool_call")
    message_buffer.update_report_section = save_report_section_decorator(message_buffer, "update_report_section")

    layout = create_layout()

    # The alternate screen keeps a layout taller than the window from redrawing
    # by scrolling; the final report prints after this block, on the normal screen.
    with Live(layout, refresh_per_second=4, screen=True):
        # Initial display
        update_display(layout, stats_handler=stats_handler, start_time=start_time)

        message_buffer.add_message("System", f"Selected ticker: {selections['ticker']}")
        if selections["asset_type"] != "stock":
            message_buffer.add_message("System", f"Detected asset type: {selections['asset_type']}")
        message_buffer.add_message(
            "System", f"Analysis date: {selections['analysis_date']}"
        )
        message_buffer.add_message(
            "System",
            f"Selected analysts: {', '.join(analyst.value for analyst in selections['analysts'])}",
        )
        update_display(layout, stats_handler=stats_handler, start_time=start_time)

        # The analysts start together.
        for spec in analyst_execution_plan.specs:
            message_buffer.update_agent_status(spec.agent_node, "in_progress")
            analyst_wall_time_tracker.mark_started(spec.key)
        update_display(layout, stats_handler=stats_handler, start_time=start_time)

        spinner_text = (
            f"Analyzing {selections['ticker']} on {selections['analysis_date']}..."
        )
        update_display(layout, spinner_text, stats_handler=stats_handler, start_time=start_time)

        # The same initial state propagate() builds, with the resolved
        # instrument identity; the graph's Memory Log step settles past
        # decisions and loads their lessons alongside the analysts.
        init_agent_state = graph.create_run_state(
            selections["ticker"], selections["analysis_date"], selections["asset_type"], portfolio
        )
        # Pass callbacks to graph config for tool execution tracking
        # (LLM tracking is handled separately via LLM constructor)
        args = graph.propagator.get_graph_args(callbacks=[stats_handler])

        # Recompile with a checkpointer and inject the thread_id so --checkpoint
        # actually saves and resumes on the CLI path (#1249); a no-op when
        # checkpointing is disabled. Torn down in the finally below.
        checkpoint_tid = graph.begin_checkpoint(
            selections["ticker"], selections["analysis_date"], selections["asset_type"], portfolio
        )
        if checkpoint_tid is not None:
            args.setdefault("config", {}).setdefault("configurable", {})["thread_id"] = checkpoint_tid
            _announce_checkpoint_state(graph, selections["ticker"], selections["analysis_date"])

        # Stream the analysis. On resume, feed None so LangGraph continues the
        # interrupted run instead of re-appending the initial state (#1249); the
        # try/finally tears the checkpointer down even if the stream raises.
        trace = []
        try:
            for messages, chunk in graph.stream_run(graph.checkpoint_input(init_agent_state), **args):
                for message in messages:
                    msg_id = getattr(message, "id", None)
                    if msg_id is not None:
                        if msg_id in message_buffer._processed_message_ids:
                            continue
                        message_buffer._processed_message_ids.add(msg_id)

                    msg_type, content = classify_message_type(message)
                    if content and content.strip():
                        message_buffer.add_message(msg_type, content)

                    if hasattr(message, "tool_calls") and message.tool_calls:
                        for tool_call in message.tool_calls:
                            if isinstance(tool_call, dict):
                                message_buffer.add_tool_call(tool_call["name"], tool_call["args"])
                            else:
                                message_buffer.add_tool_call(tool_call.name, tool_call.args)

                if chunk is None:   # a step inside an analyst's graph: messages only
                    update_display(layout, stats_handler=stats_handler, start_time=start_time)
                    continue

                update_analyst_statuses(
                    message_buffer,
                    chunk,
                    wall_time_tracker=analyst_wall_time_tracker,
                )

                # Research Team - Handle Investment Debate State
                if chunk.get("investment_debate_state"):
                    debate_state = chunk["investment_debate_state"]
                    bull_hist = debate_state.get("bull_history", "").strip()
                    bear_hist = debate_state.get("bear_history", "").strip()
                    judge = (chunk.get("investment_plan") or "").strip()

                    # Only update status when there's actual content
                    if bull_hist or bear_hist:
                        update_research_team_status("in_progress")
                    if bull_hist:
                        message_buffer.update_report_section(
                            "investment_plan", f"### Bull Researcher Analysis\n{bull_hist}"
                        )
                    if bear_hist:
                        message_buffer.update_report_section(
                            "investment_plan", f"### Bear Researcher Analysis\n{bear_hist}"
                        )
                    if judge:
                        message_buffer.update_report_section(
                            "investment_plan", f"### Research Manager Decision\n{judge}"
                        )
                        update_research_team_status("completed")
                        message_buffer.update_agent_status("Trader", "in_progress")

                # Trading Team
                if chunk.get("trader_investment_plan"):
                    message_buffer.update_report_section(
                        "trader_investment_plan", chunk["trader_investment_plan"]
                    )
                    if message_buffer.agent_status.get("Trader") != "completed":
                        message_buffer.update_agent_status("Trader", "completed")
                        message_buffer.update_agent_status("Aggressive Analyst", "in_progress")

                # Risk Management Team - Handle Risk Debate State
                if chunk.get("risk_debate_state"):
                    risk_state = chunk["risk_debate_state"]
                    agg_hist = risk_state.get("aggressive_history", "").strip()
                    con_hist = risk_state.get("conservative_history", "").strip()
                    neu_hist = risk_state.get("neutral_history", "").strip()
                    judge = (chunk.get("final_trade_decision") or "").strip()

                    if agg_hist:
                        if message_buffer.agent_status.get("Aggressive Analyst") != "completed":
                            message_buffer.update_agent_status("Aggressive Analyst", "in_progress")
                        message_buffer.update_report_section(
                            "final_trade_decision", f"### Aggressive Analyst Analysis\n{agg_hist}"
                        )
                    if con_hist:
                        if message_buffer.agent_status.get("Conservative Analyst") != "completed":
                            message_buffer.update_agent_status("Conservative Analyst", "in_progress")
                        message_buffer.update_report_section(
                            "final_trade_decision", f"### Conservative Analyst Analysis\n{con_hist}"
                        )
                    if neu_hist:
                        if message_buffer.agent_status.get("Neutral Analyst") != "completed":
                            message_buffer.update_agent_status("Neutral Analyst", "in_progress")
                        message_buffer.update_report_section(
                            "final_trade_decision", f"### Neutral Analyst Analysis\n{neu_hist}"
                        )
                    if judge and message_buffer.agent_status.get("Portfolio Manager") != "completed":
                        message_buffer.update_agent_status("Portfolio Manager", "in_progress")
                        message_buffer.update_report_section(
                            "final_trade_decision", f"### Portfolio Manager Decision\n{judge}"
                        )
                        message_buffer.update_agent_status("Aggressive Analyst", "completed")
                        message_buffer.update_agent_status("Conservative Analyst", "completed")
                        message_buffer.update_agent_status("Neutral Analyst", "completed")
                        message_buffer.update_agent_status("Portfolio Manager", "completed")

                update_display(layout, stats_handler=stats_handler, start_time=start_time)

                trace.append(chunk)

            # Streamed chunks are per-node deltas, not full state. Merge them
            # so every report field populated across the run is present.
            final_state = {}
            for chunk in trace:
                final_state.update(chunk)

            # Clean run: write the manifest, log the decision, then drop this run's
            # checkpoint so a later run starts fresh. The manifest is written first,
            # inside _finalize_run_manifest, so teardown can never lose the record.
            manifest_write = _make_manifest_writer(effective_config, selections, stats_handler, started_at=start_time, variant=manifest_variant, prompt_receipts=prompt_receipts)
            _finalize_run_manifest(
                write=manifest_write,
                graph=graph,
                ticker=selections["ticker"],
                trade_date=selections["analysis_date"],
                asset_type=selections["asset_type"],
                portfolio=portfolio,
                final_state=final_state,
                failure=None,
            )
        except BaseException as failure:
            # A failure mid-run still leaves a manifest; the checkpoint is kept for
            # resume and the failure is re-raised after the finally below.
            manifest_write = _make_manifest_writer(effective_config, selections, stats_handler, started_at=start_time, variant=manifest_variant, prompt_receipts=prompt_receipts)
            _finalize_run_manifest(
                write=manifest_write,
                graph=graph,
                ticker=selections["ticker"],
                trade_date=selections["analysis_date"],
                asset_type=selections["asset_type"],
                portfolio=portfolio,
                final_state=None,
                failure=failure,
            )
        finally:
            # Always restore the plain uncheckpointed graph, even on failure.
            graph.end_checkpoint()

        for agent in message_buffer.agent_status:
            message_buffer.update_agent_status(agent, "completed")

        message_buffer.add_message(
            "System", f"Completed analysis for {selections['analysis_date']}"
        )
        message_buffer.add_message("System", analyst_wall_time_tracker.format_summary())

        for section in message_buffer.report_sections:
            if section in final_state:
                message_buffer.update_report_section(section, final_state[section])

        update_display(layout, stats_handler=stats_handler, start_time=start_time)

    # Post-analysis prompts (outside Live context for clean interaction)
    console.print("\n[bold cyan]Analysis Complete![/bold cyan]\n")

    # A decision nobody can read is not a position. Say so here rather than
    # leaving the run to look like a normal result.
    if is_review(run_rating(final_state)):
        console.print(
            "[yellow]No rating could be read from the final decision, so this run "
            "is recorded for review rather than as a position. Re-run, or read the "
            "decision text below and judge it yourself.[/yellow]\n"
        )
    console.print(f"[dim]{analyst_wall_time_tracker.format_summary()}[/dim]")

    _offer_reports(final_state, graph, selections["ticker"],
                   save=flags.get("save"), show=flags.get("show"), html=flags.get("html"))


def _yes(question: str) -> bool:
    return typer.prompt(question, default="Y").strip().upper() in ("Y", "YES", "")


def _graphical_browser():
    """A browser that opens a page in its own window on this machine, or None.

    Over SSH the page sits on the remote machine, and a terminal browser (lynx,
    w3m, elinks) would take over the terminal, so neither is offered.
    """
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"):
        return None
    try:
        browser = webbrowser.get()
    except webbrowser.Error:
        return None
    if type(browser) is webbrowser.GenericBrowser or isinstance(browser, webbrowser.Elinks):
        return None
    return browser


def _open_page(page: Path) -> None:
    """Offer to open the saved page in a browser window, and say where it is if opening fails."""
    browser = _graphical_browser()
    if browser is None or not _yes("Open it in your browser?"):
        return
    try:
        opened = browser.open(page.as_uri())
    except (webbrowser.Error, OSError):
        opened = False
    if not opened:
        console.print(f"  [dim]Could not open a browser; the page is at:[/dim] {page}")


def _offer_reports(final_state, graph, ticker, save=None, show=None, html=None):
    """Save the report tree and show it; ``save``/``show``/``html`` answer the questions when given.

    A saved report includes the HTML page unless ``html`` is False. Someone
    answering the save question at the prompt is also asked about the page and
    offered to open it; a run whose flags answer the save question asks neither.
    """
    asked = save is None
    if asked:
        save = typer.prompt("Save report?", default="Y").strip().upper() in ("Y", "YES", "")
    if save:
        # Under results_dir, not the working directory: in Docker the working
        # directory is inside the container and the report goes with it, while
        # results_dir is the mounted volume the rest of the run already writes to.
        save_path = graph.default_report_path(ticker)
        if asked:   # someone at the prompt may pick another folder
            save_path = Path(typer.prompt(
                "Save path (press Enter for default)", default=str(save_path)
            ).strip())
        if html is None:
            html = _yes("Also save it as an HTML page?") if asked else True
        saved = False
        try:
            report_file = graph.save_reports(final_state, ticker, save_path, html=html)
            saved = True
            console.print(f"\n[green]✓ Report saved to:[/green] {save_path.resolve()}")
            console.print(f"  [dim]Complete report:[/dim] {report_file.name}")
        except Exception as e:
            console.print(f"[red]Error saving report: {e}[/red]")
        if saved and html:
            page = (save_path / "complete_report.html").resolve()
            console.print(f"  [dim]HTML report:[/dim] {page.name}")
            if asked:
                _open_page(page)

    if show is None:
        show = typer.prompt("\nDisplay full report on screen?", default="Y").strip().upper() in ("Y", "YES", "")
    if show:
        display_complete_report(final_state)
