"""Compare run manifests across architecture variants (E-owned; D4 / §6.5).

Reads v1 run manifests (``docs/contracts/run-event.md``) produced by
``run_recorder`` and reports measured quantities per variant. It **refuses** to
compare runs that are not comparable: ``ticker``, ``trade_date``, ``asset_type``,
the model (quick/deep tier LLMs), the provider (``llm_provider`` and any tier
code/endpoint selectors), the output ``language``, and ``prompt_hashes`` must all
match the baseline. When any of them differs the comparison raises
``IncomparableRunsError`` rather than presenting a misleading table.

This tool never invents quality scores. It reports only what the manifest records
(outcome, usage, duration, failure, stop reason) and per-variant averages of the
numeric fields. Semantic/quality thresholds are owned by B/D and are out of scope
here (see ``docs/evaluation/protocol.md``).

Usage:
    python scripts/compare_runs.py <manifest> [<manifest> ...] [--json]

Exit 0 when the runs are comparable, 1 (with a reason on stderr) when they are
refused, 2 on a usage error. Stdlib + ``run_recorder`` only.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from tradingagents.run_recorder import read_manifest

_TOP_LEVEL_GUARD = ("ticker", "trade_date", "asset_type")
_MODEL_KEYS = ("quick_think_llm", "deep_think_llm")
_PROVIDER_KEYS = ("llm_provider", "quick_think_provider", "deep_think_provider")
_REQUIRED_CONFIG_KEYS = _MODEL_KEYS + ("llm_provider",)
_LANGUAGE_KEY = "output_language"
_USAGE_METRICS = ("llm_calls", "tool_calls", "tokens_in", "tokens_out")


class IncomparableRunsError(ValueError):
    """The supplied manifests cannot be compared (a guard key differs)."""


@dataclass(frozen=True)
class Comparison:
    """Comparable-run report. ``variants`` is per-run; ``averages`` is per-variant."""

    baseline_run_id: str
    guard: dict
    variants: list[dict]
    averages: dict
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "baseline_run_id": self.baseline_run_id,
            "guard": self.guard,
            "variants": self.variants,
            "averages": self.averages,
            "notes": self.notes,
        }


def _guard_of(manifest: dict) -> dict:
    """Extract the keys that must match for a comparison to be valid.

    ``llm_provider``, the tier models, and ``output_language`` are required; a
    missing required key is refused rather than guessed, so a malformed snapshot
    cannot silently look comparable. The optional per-tier provider selectors are
    collected when present; ``_provider_keys`` unions them across every manifest so
    a tier provider set in *any* run is compared everywhere (a manifest that omits
    it compares as ``None``, the config default).
    """
    config = manifest.get("config_snapshot") or {}
    guard = {key: manifest.get(key) for key in _TOP_LEVEL_GUARD}
    required = _REQUIRED_CONFIG_KEYS + (_LANGUAGE_KEY,)
    for key in required:
        if key not in config:
            raise IncomparableRunsError(
                f"manifest {manifest.get('run_id')!r} is missing config key {key!r}; "
                "cannot compare without it"
            )
        guard[key] = config[key]
    for key in _PROVIDER_KEYS:
        if key in config:
            guard[key] = config[key]
    prompt_hashes = manifest.get("prompt_hashes")
    if not prompt_hashes:
        # An empty/None prompt fingerprint leaves the comparison unfounded: two runs
        # cannot be shown to use the same prompts without a real hash (C-to-E
        # variant response: keep the real hashes). Refuse rather than guess.
        raise IncomparableRunsError(
            f"manifest {manifest.get('run_id')!r} has empty prompt_hashes; "
            "cannot compare without prompt fingerprints"
        )
    guard["prompt_hashes"] = prompt_hashes
    return guard


def _provider_keys(manifests: list[dict]) -> list[str]:
    """Provider keys present in *any* manifest, so they are compared everywhere."""
    present: set[str] = set()
    for manifest in manifests:
        config = manifest.get("config_snapshot") or {}
        present.update(key for key in _PROVIDER_KEYS if key in config)
    return sorted(present)


def _check_comparable(guard: dict, baseline: dict) -> None:
    # Compare the guard keys the manifest actually contributes. ``evidence_mode`` is
    # validated once for the whole set (see compare_manifests), not per manifest.
    diffs = [key for key in guard if key in baseline and guard.get(key) != baseline[key]]
    if diffs:
        raise IncomparableRunsError(
            "runs are not comparable; these guard keys differ from the baseline: "
            + ", ".join(sorted(diffs))
        )


def _variant_of(run_id: str) -> str:
    """The variant segment of a run id (``<variant>-<ticker>-...``)."""
    return run_id.split("-", 1)[0]


def _variant_row(manifest: dict, evidence_mode: str | None = None) -> dict:
    usage = manifest.get("usage")
    row = {
        "run_id": manifest.get("run_id"),
        "variant": _variant_of(str(manifest.get("run_id", ""))),
        "outcome": manifest.get("outcome"),
        "usage": usage,
        "duration_seconds": manifest.get("duration_seconds"),
        "failure": manifest.get("failure"),
        "stop_reason": manifest.get("stop_reason"),
        "evidence_mode": evidence_mode,
    }
    # Surface each numeric metric explicitly. A missing value stays None (null),
    # never coerced to 0: an unreported count is unknown, not zero.
    for metric in _USAGE_METRICS:
        row[metric] = usage.get(metric) if isinstance(usage, dict) else None
    return row


def _format_metric(value) -> str:
    """Render a metric for humans: ``--`` for null/unknown, else the number."""
    return "--" if value is None else str(value)


def _counts(values: list) -> dict:
    """Count occurrences of each value (``None`` counted as ``null``)."""
    counts: dict = {}
    for value in values:
        key = "null" if value is None else str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _averages(rows: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["variant"], []).append(row)

    result: dict[str, dict] = {}
    for variant, group in grouped.items():
        summary: dict = {"runs": len(group)}
        for metric in _USAGE_METRICS:
            values = [
                row["usage"][metric]
                for row in group
                if isinstance(row.get("usage"), dict) and row["usage"].get(metric) is not None
            ]
            summary[metric] = sum(values) / len(values) if values else None
        durations = [row["duration_seconds"] for row in group if row["duration_seconds"] is not None]
        summary["duration_seconds"] = sum(durations) / len(durations) if durations else None
        summary["outcome_counts"] = _counts([row["outcome"] for row in group])
        summary["stop_reason_counts"] = _counts([row["stop_reason"] for row in group])
        result[variant] = summary
    return result


def compare_manifests(manifests: list[dict], evidence_modes: list[str | None] | None = None) -> Comparison:
    """Compare already-loaded manifests; raise ``IncomparableRunsError`` if invalid.

    ``evidence_modes`` aligns with ``manifests`` (E4 ``evidence-mode.json``): the mode
    is a control that must match across every run, so strict and report_reference
    runs are never compared together. When omitted, every mode is ``None`` (no
    sidecar), which is itself required to be uniform.
    """
    if not manifests:
        raise IncomparableRunsError("no manifests supplied")
    modes = list(evidence_modes) if evidence_modes is not None else [None] * len(manifests)
    if len(modes) != len(manifests):
        raise IncomparableRunsError("evidence_modes must align with manifests")
    if len(set(modes)) > 1:
        raise IncomparableRunsError(
            "runs are not comparable; evidence_mode differs (strict vs report_reference "
            "are never compared together): " + ", ".join(repr(m) for m in modes)
        )
    shared_mode = modes[0]

    baseline_guard = _guard_of(manifests[0])
    baseline_guard["evidence_mode"] = shared_mode
    for manifest in manifests[1:]:
        _check_comparable(_guard_of(manifest), baseline_guard)

    # Union the provider keys across all runs so a tier provider set in any run
    # (not just the baseline) is verified to match everywhere.
    for key in _provider_keys(manifests):
        values = {(m.get("config_snapshot") or {}).get(key) for m in manifests}
        if len(values) > 1:
            raise IncomparableRunsError(
                "runs are not comparable; these guard keys differ from the baseline: " + key
            )
        baseline_guard.setdefault(key, (manifests[0].get("config_snapshot") or {}).get(key))

    rows = [_variant_row(manifest, modes[i]) for i, manifest in enumerate(manifests)]
    return Comparison(
        baseline_run_id=manifests[0].get("run_id"),
        guard=baseline_guard,
        variants=rows,
        averages=_averages(rows),
        notes=[
            "Reported quantities are measured from run manifests; no quality score is "
            "computed or inferred here.",
            "Runs are only compared when ticker, trade_date, asset_type, model, provider, "
            "language, prompt hashes, and evidence_mode all match the baseline.",
        ],
    )


def _evidence_mode_of(manifest_path: Path) -> str | None:
    """Read the E4 ``evidence-mode.json`` beside a manifest; ``None`` when absent.

    A missing sidecar means the run predates E4 or recorded no mode; it compares
    as ``None`` and so is only comparable with other sidecar-less runs.
    """
    sidecar = Path(manifest_path).parent / "evidence-mode.json"
    if not sidecar.exists():
        return None
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise IncomparableRunsError(f"cannot read evidence-mode {str(sidecar)!r}: {exc}") from exc
    return data.get("evidence_mode")


def compare_manifest_files(paths: list[str | Path]) -> Comparison:
    manifests = []
    modes = []
    for path in paths:
        try:
            manifests.append(read_manifest(path))
        except (OSError, ValueError) as exc:
            # read_manifest raises ValueError for a bad/unsupported/short manifest
            # and OSError (e.g. FileNotFoundError) for an unreadable path.
            raise IncomparableRunsError(f"cannot read manifest {str(path)!r}: {exc}") from exc
        modes.append(_evidence_mode_of(Path(path)))
    return compare_manifests(manifests, evidence_modes=modes)


def main(argv: list[str]) -> int:
    args = [arg for arg in argv[1:] if not arg.startswith("-")]
    as_json = "--json" in argv[1:]
    if not args:
        print("usage: compare_runs.py <manifest> [<manifest> ...] [--json]", file=sys.stderr)
        return 2
    try:
        comparison = compare_manifest_files(args)
    except IncomparableRunsError as exc:
        print(f"[compare-runs] REFUSED: {exc}", file=sys.stderr)
        return 1

    if as_json:
        print(json.dumps(comparison.to_dict(), sort_keys=True, ensure_ascii=False, indent=2))
    else:
        print(f"[compare-runs] baseline={comparison.baseline_run_id} runs={len(comparison.variants)}")
        header = ("runs",) + _USAGE_METRICS + ("duration_seconds",)
        print("  variant        " + "  ".join(f"{name:>16}" for name in header))
        for variant, summary in sorted(comparison.averages.items()):
            cells = "  ".join(f"{_format_metric(summary.get(name)):>16}" for name in header)
            print(f"  {variant:<14} {cells}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
