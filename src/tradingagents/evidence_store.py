"""E-owned evidence destination preparation (no publication).

Role A owns evidence *publication* (``evidence.save_snapshot`` writes the
snapshot). This module only answers one E-side question: given a run and A's
canonical artifact key, *where* under that run's directory does the artifact
belong? The answer is ``<results_dir>/runs/<run_id>/evidence/<artifact_key>``.

The canonical key grammar is ``v1/<64 lowercase hex>.json`` (see
``evidence._ARTIFACT_KEY`` / ``artifact_key_for``). Anything else -- an absolute
path, a ``..`` segment, a backslash, a different version, an upper-case or wrong
length digest -- is rejected rather than interpreted. The joined path is then
resolved and asserted to stay inside the evidence root, so a symlinked
``evidence``/version directory cannot redirect the write outside the run.

This module deliberately imports neither ``cli.run`` nor the graph: it is
importable by the graph as a plain path helper.
"""

from __future__ import annotations

import re
from pathlib import Path

# The one canonical artifact-key grammar (v1 schema). Mirrors
# ``evidence._ARTIFACT_KEY`` without importing the heavy evidence module.
_ARTIFACT_KEY = re.compile(r"v1/[0-9a-f]{64}\.json\Z")

# A run id is used as a single directory component; reject separators and the
# traversal token so the root cannot be escaped before the key is even joined.
_RUN_ID_FORBIDDEN = ("/", "\\", "..")


def _validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_id must be a non-empty string")
    if any(token in run_id for token in _RUN_ID_FORBIDDEN):
        raise ValueError(f"unsafe run_id {run_id!r} for an evidence path component")
    return run_id


def _validate_artifact_key(artifact_key: str) -> str:
    if not isinstance(artifact_key, str) or not _ARTIFACT_KEY.fullmatch(artifact_key):
        raise ValueError(
            f"invalid artifact_key {artifact_key!r}; expected 'v1/<64 hex>.json'"
        )
    return artifact_key


def evidence_destination(config: dict, run_id: str, artifact_key: str) -> Path:
    """Return (and create) the on-disk path for ``artifact_key`` in this run.

    Path: ``<results_dir>/runs/<run_id>/evidence/<artifact_key>``. The parent
    directories are created. ``local-fs`` is nowhere in the path: it is a
    conceptual backend name, not a filesystem component. The final path is
    resolved and must remain inside the evidence root, so an absolute key, a
    ``..`` segment, or a symlinked directory that points outside is refused with
    ``ValueError`` instead of being followed.
    """
    run_id = _validate_run_id(run_id)
    artifact_key = _validate_artifact_key(artifact_key)

    root = (Path(config["results_dir"]) / "runs" / run_id / "evidence").resolve()
    destination = (root / artifact_key).resolve()

    # Containment: the resolved destination must sit strictly inside the root.
    try:
        destination.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"artifact_key {artifact_key!r} escapes the evidence root"
        ) from exc
    if destination == root:
        raise ValueError(f"artifact_key {artifact_key!r} resolves to the evidence root")

    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination
