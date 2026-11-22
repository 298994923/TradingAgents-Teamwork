"""Deterministic run manifest recorder (docs/contracts/run-event.md).

Records one analysis run as a JSON manifest so runs can be compared and
prompt/model changes can be gated. The recorder never reads the wall clock or a
random source: ``created_at``, ``run_id`` and ``version`` are supplied by the
caller, so identical inputs produce byte-identical output ("byte-stable
manifest"). Fields owned by other members (``stop_reason`` for C,
``prompt_hashes`` for B, ``evidence_snapshot`` for A) are stored opaquely and are
not validated here.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1

RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]{0,62}$")

_STRING_FIELDS = ("run_id", "created_at", "version", "ticker", "trade_date", "asset_type")

_REQUIRED_FIELDS = (
    "schema_version",
    "run_id",
    "created_at",
    "version",
    "ticker",
    "trade_date",
    "asset_type",
    "outcome",
    "config_snapshot",
    "prompt_hashes",
    "evidence_snapshot",
    "usage",
    "duration_seconds",
    "failure",
    "stop_reason",
)

# Keys that must never reach disk: their names carry credentials or endpoints.
_SECRET_SUFFIXES = ("_api_key", "_key", "_token", "_password")
_SECRET_EXACT = ("backend_url",)


def _is_secret_key(name: str) -> bool:
    return name in _SECRET_EXACT or name.endswith(_SECRET_SUFFIXES)


@dataclass(frozen=True)
class RunEvent:
    """One run's record. Every field is required except ``schema_version``.

    Omitting a required field raises ``TypeError`` at construction, so the
    manifest cannot be built half-formed. ``frozen`` keeps a recorded event
    immutable; adjust by constructing a new one.
    """

    run_id: str
    created_at: str
    version: str
    ticker: str
    trade_date: str
    asset_type: str
    outcome: str | None
    config_snapshot: dict
    prompt_hashes: dict
    evidence_snapshot: dict | None
    usage: dict
    duration_seconds: float | None
    failure: str | None
    stop_reason: str | None
    schema_version: int = SCHEMA_VERSION


def build_run_id(variant: str, ticker: str, trade_date: str, repeat: int, at: datetime) -> str:
    """A stable, filename-safe run id: ``<variant>-<ticker>-<trade_date>-r<n>-<stamp>``.

    ``at`` is passed in; the clock is never read here. Inputs are **lowercased**
    (not rejected) so the id always satisfies ``RUN_ID_PATTERN`` regardless of
    how the caller spelled the variant or ticker. ``at`` is normalized to UTC and
    rendered ``YYYYMMDDtHHMM`` (e.g. ``20261121t1200``). ``repeat`` is a 1-based
    index, so values below 1 are rejected.
    """
    if repeat < 1:
        raise ValueError(f"repeat must be >= 1, got {repeat!r}")
    if at.tzinfo is None:
        at = at.replace(tzinfo=UTC)
    stamp = at.astimezone(UTC).strftime("%Y%m%dt%H%M")
    return f"{variant.lower()}-{ticker.lower()}-{trade_date}-r{repeat}-{stamp}"


def _validated_manifest(event: RunEvent) -> dict:
    """Validate ``event`` and return the dict that is written to disk."""
    if event.schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema_version {event.schema_version!r}; expected {SCHEMA_VERSION}"
        )
    if not RUN_ID_PATTERN.match(event.run_id):
        raise ValueError(f"invalid run_id {event.run_id!r}; must match {RUN_ID_PATTERN.pattern}")
    for name in _STRING_FIELDS:
        value = getattr(event, name)
        if not isinstance(value, str) or not value:
            raise ValueError(f"required field {name!r} must be a non-empty string")

    manifest = asdict(event)
    manifest["config_snapshot"] = {
        key: value
        for key, value in event.config_snapshot.items()
        if not _is_secret_key(key)
    }
    return manifest


def write_manifest(event: RunEvent, path) -> Path:
    """Write ``event`` as a JSON manifest to ``path``; never overwrite.

    Raises ``ValueError`` for an unsupported schema version, an invalid
    ``run_id``, or an empty required string, and ``FileExistsError`` if ``path``
    already exists.
    """
    path = Path(path)
    manifest = _validated_manifest(event)
    payload = json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2)
    # "x" refuses to overwrite an existing file atomically.
    with open(path, "x", encoding="utf-8") as handle:
        handle.write(payload)
    return path


def read_manifest(path) -> dict:
    """Read a manifest, rejecting an unsupported ``schema_version`` or a missing key."""
    with open(Path(path), encoding="utf-8") as handle:
        manifest = json.load(handle)
    version = manifest.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version {version!r}; expected {SCHEMA_VERSION}")
    missing = [name for name in _REQUIRED_FIELDS if name not in manifest]
    if missing:
        raise ValueError(f"manifest missing required fields: {', '.join(missing)}")
    return manifest
