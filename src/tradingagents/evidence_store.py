"""E-owned evidence destination preparation (no publication).

Role A owns evidence *publication* (``evidence.save_snapshot`` writes the
snapshot). This module only answers one E-side question: given a run and A's
canonical artifact key, *where* under that run's directory does the artifact
belong? The answer is ``<results_dir>/runs/<run_id>/evidence/<artifact_key>``.

The canonical key grammar is ``v1/<64 lowercase hex>.json`` (see
``evidence._ARTIFACT_KEY`` / ``artifact_key_for``). Anything else -- an absolute
path, a ``..`` segment, a backslash, a different version, an upper-case or wrong
length digest -- is rejected rather than interpreted.

Containment is anchored *before* any resolution: the intended reserved run
directory ``<results_dir>/runs/<run_id>`` is built and checked to sit inside the
configured results root, and the intended evidence directory is checked to sit
inside that run directory -- all on lexically normalized (non-``resolve``d)
paths. Only then is the path resolved for the final comparison, and any symlink
along the root chain that escapes the intended tree is refused *before* a
directory is created. ``run_id`` must satisfy the recorder contract
(``RUN_ID_PATTERN``), which also rejects dot-only ids.

This module deliberately imports neither ``cli.run`` nor the graph: it is
importable by the graph as a plain path helper.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

try:  # Reuse the recorder's canonical pattern; mirror it if import is unavailable.
    from tradingagents.run_recorder import RUN_ID_PATTERN
except Exception:  # pragma: no cover - defensive fallback, keeps the grammar identical
    RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]{0,62}$")

# The one canonical artifact-key grammar (v1 schema). Mirrors
# ``evidence._ARTIFACT_KEY`` without importing the heavy evidence module.
_ARTIFACT_KEY = re.compile(r"v1/[0-9a-f]{64}\.json\Z")


def _validate_run_id(run_id: str) -> str:
    """Validate against the recorder contract; also reject dot-only components."""
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_id must be a non-empty string")
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError(
            f"invalid run_id {run_id!r}; must match {RUN_ID_PATTERN.pattern}"
        )
    # A purely dotted id ("..", "...") matches the charset but is unsafe as a
    # directory component even though the pattern allows it.
    if set(run_id) <= {"."}:
        raise ValueError(f"unsafe run_id {run_id!r}; dot-only ids are not allowed")
    return run_id


def _validate_artifact_key(artifact_key: str) -> str:
    if not isinstance(artifact_key, str) or not _ARTIFACT_KEY.fullmatch(artifact_key):
        raise ValueError(
            f"invalid artifact_key {artifact_key!r}; expected 'v1/<64 hex>.json'"
        )
    return artifact_key


def _assert_lexically_under(path: Path, root: Path) -> None:
    """Assert ``path`` is ``root`` or beneath it on a normalized (unresolved) path."""
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{str(path)!r} is not inside {str(root)!r}") from exc


def _reject_escaping_symlink(leaf: Path, containment_root: Path, *, anchor: Path) -> None:
    """Refuse if any existing component from ``anchor`` down to ``leaf`` is a
    symlink that resolves outside ``containment_root`` (checked before mkdir)."""
    try:
        rel = leaf.relative_to(anchor)
    except ValueError:
        raise ValueError(f"{str(leaf)!r} is not inside {str(anchor)!r}") from None
    resolved_root = containment_root.resolve()
    current = anchor
    for part in (None, *rel.parts):
        if part is not None:
            current = current / part
        if not current.exists():
            # Nothing to follow yet; later components do not exist either.
            return
        if current.is_symlink():
            target = current.resolve()
            try:
                target.relative_to(resolved_root)
            except ValueError:
                raise ValueError(
                    f"refusing symlink {str(current)!r} that escapes "
                    f"{str(containment_root)!r}"
                ) from None


def evidence_destination(config: dict, run_id: str, artifact_key: str) -> Path:
    """Return (and create) the on-disk path for ``artifact_key`` in this run.

    Path: ``<results_dir>/runs/<run_id>/evidence/<artifact_key>``. The parent
    directories are created **after** all containment checks pass. ``local-fs``
    is nowhere in the path: it is a conceptual backend name, not a filesystem
    component.

    Order (containment before creation):

    1. Validate ``run_id`` (recorder contract) and ``artifact_key`` (canonical).
    2. Anchor the intended roots lexically and assert they nest:
       ``results_root`` -> ``run_root`` -> ``evidence_root``.
    3. Reject any symlink along ``results_root .. evidence_root`` (and the key's
       parent) that resolves outside the intended run directory.
    4. Only then resolve and re-check the destination stays inside ``run_root``.
    """
    run_id = _validate_run_id(run_id)
    artifact_key = _validate_artifact_key(artifact_key)

    results_root = Path(config["results_dir"])
    runs_root = results_root / "runs"
    run_root = runs_root / run_id
    evidence_root = run_root / "evidence"
    destination = evidence_root / artifact_key

    # 2. Lexical nesting checks (no resolve yet).
    _assert_lexically_under(run_root, results_root)
    _assert_lexically_under(evidence_root, run_root)
    _assert_lexically_under(destination, evidence_root)

    # 3. Reject escaping symlinks before creating anything. The reserved run
    #    directory must itself be a real directory (reserve_run_id creates one), and
    #    every component from it down to the key's parent must resolve inside it.
    if run_root.is_symlink():
        raise ValueError(
            f"refusing run directory {str(run_root)!r}: it is a symlink, not a "
            "reserved directory"
        )
    _reject_escaping_symlink(run_root, results_root, anchor=results_root)
    _reject_escaping_symlink(evidence_root, run_root, anchor=run_root)
    _reject_escaping_symlink(destination.parent, run_root, anchor=run_root)

    # 4. Resolve and re-check containment inside the intended run directory.
    resolved_run_root = run_root.resolve()
    resolved_destination = destination.resolve()
    try:
        resolved_destination.relative_to(resolved_run_root)
    except ValueError as exc:
        raise ValueError(
            f"artifact_key {artifact_key!r} escapes the run directory"
        ) from exc

    os.makedirs(destination.parent, exist_ok=True)
    return destination
