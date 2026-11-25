# Memory and state design

- **Status:** Source-grounded documentation draft for A/B/C/E/D review; no new runtime policy or approval.
- **Prepared:** 2026-11-25, coordinated by A.
- **Inspected main:** `63989bfd70f3aeeec35607d21bc0ac7f085a8919`.
- **Related requirements:** A-EV-01..08, C checkpoint/storage/capture families, B-REQ-06..12, REQ-E-01/02/06 and D's invariants.

This document describes what currently survives a call, run, interruption or
version change, who writes and reads it, and where retention/privacy decisions
remain unimplemented or unconfirmed. It introduces no new memory subsystem and
does not authorize changes to shared state, storage, Guard or recovery APIs.
The [blueprint](../../architecture-blueprint.md), [trace matrix](trace-matrix.md)
and individual contracts define the corresponding ownership and evidence limits.

## 1. State surfaces and persistence boundaries

| Surface | Contents and lifetime | Writer / reader and ownership | Persistence boundary |
|---|---|---|---|
| Graph state | Analyst reports; research/risk histories; plans; final result; past_context/memory_note; optional Guard, terminal and capture fields | Nodes produce deltas; graph owns transport. C integrates shared state; module owners produce their fields | In memory unless checkpointed or explicitly projected to another artifact. State declaration alone does not persist a field |
| Per-call context pack | Ordered context blocks, estimates, dropped-block reasons and protected constraints | B's context builder and researcher/manager call sites | Rebuilt for a model invocation. Compaction changes emitted context, not automatically the underlying stored histories |
| Evidence snapshot | Exact selected report text, context, source-run identity, capture time, content hashes and schema version | A owns registration/load/save; C invokes capture; E owns destination | Immutable JSON artifact with no-overwrite publication; independent of graph checkpoints |
| Memory Log | Decision entries, pending/resolved outcome, return figures, resolution date and generated reflection | Inherited memory module; graph records decisions and runs settlement. A maintains the module boundary; C owns graph invocation | Configured Markdown file across runs; outcome settlement updates it atomically under locks |
| Ordinary graph checkpoint | Intermediate execution state and pending writes by thread | Framework saver and C's graph/checkpointer lifecycle | Per-ticker SQLite database in data_cache_dir/checkpoints; keyed threads distinguish executions |
| Run record and sidecars | Run/config/prompt identity, usage, duration, failure, stop reason and optional Evidence reference; receipt and evidence-mode files | E's CLI and recorder consume C/B/A observations | Per-run result directory; artifacts have separate publication boundaries |
| Final state projection | Selected reports, histories, plans, rating and effective run settings | Graph record_decision/_log_state | Human-readable JSON projection by ticker/date; not a full checkpoint or immutable run archive |
| Recovery locator and attempt helpers | Proposed/explicit run locator, database/thread and Evidence reference; append-only attempt lines | E's resume helper; C integration is separate | Helper files are implemented/tested, but do not establish a delivered locator-based graph recovery route |

The [state type](../../src/tradingagents/agents/state.py) and
[graph entry points](../../src/tradingagents/graph/trading_graph.py) distinguish
these surfaces. An Evidence artifact is not a learned lesson; a prompt receipt
is not a checkpoint; a final JSON projection is not complete resumable state.

## 2. Capture lifecycle and source identity

The opt-in fresh capture path is invocation-local and checkpoint-disabled:

```text
Selected analysts + Memory Log dependency, when present
    -> complete pre-Bull join
    -> freeze selected reports and explicit analysis context
    -> A registration and canonical artifact key
    -> E destination resolution and A snapshot publication
    -> expose five-field reference
    -> Bull/Bear research and remaining ordinary workflow
    -> terminal record and normal completion processing
```

C's `_capture_evidence` maps the selected report fields into A's canonical keys:
`market`, `social`, `news`, `fundamentals`. It supplies the reserved run ID and
one UTC capture instant. Missing selected fields are omitted from registration
inputs, allowing the artifact to preserve a null slot. A supplied empty string
remains distinct. The capture node subsequently supplies empty missing report
fields to downstream legacy consumers; the snapshot retains the original
missing-versus-empty distinction and separate diagnostics.

The stored snapshot contains schema version, snapshot ID, source_run_id,
captured_at, instrument/context/date and report slots. Its identity includes
all these values except the ID field itself. Each non-null report has a hash of
its exact UTF-8 content, without trimming, newline conversion or normalization.
Unsupported analysis cutoff, report-generation and source-availability times
remain null in Version 1. Capture time is not source-availability time.

Only successful creation or verified identical reuse exposes `evidence_snapshot`
with exactly `snapshot_id`, `artifact_key`, `store`, `source_run_id` and
`captured_at`. Diagnostics and activation controls are separate state fields.
An ID reserved by E does not by itself enable capture. The path rejects enabled
checkpointing, so this artifact capture does not claim restart/resume idempotency
for an interrupted graph. Re-registering with a new capture timestamp produces
a different snapshot even if the text is identical.

The [Evidence contract](../contracts/evidence.md),
[module](../../src/tradingagents/evidence.py) and
[storage locator](../../src/tradingagents/evidence_store.py) define the detailed
payload, errors and destination boundary.

## 3. Snapshot retrieval, consistency and reuse

`load_snapshot` decodes strict UTF-8 JSON, validates the versioned structure,
recomputes report and payload hashes, and optionally checks an externally supplied
expected snapshot ID. Loading preserves source identity and timestamps; it does
not re-register the reports. Internal hashes establish consistency with recorded
values, not author authenticity or truth. The externally retained ID binds the
artifact to the intended record and must not be silently replaced with a new ID
read from the candidate artifact itself.

`lookup_report` and `validate_reference` resolve the pair `{snapshot_id,
evidence_id}` against an explicitly bound snapshot. Structure, snapshot binding,
slot resolution and content availability remain separate results. Missing and
empty slots may exist in a structurally consistent saved artifact. A nonempty
report does not certify that its data was available on the analysis date.

`assess_replay` requires the complete exact analyst set, usable report contents,
matching full context and any supplied expected identities. It provides technical
readiness only. Partial reuse, selective regeneration and hidden live fallback
are excluded. A later consumer must preserve source_run_id/captured_at and record
its own execution identity separately rather than relabeling the artifact.

No delivered graph path is claimed here to skip acquisition and directly start
research. The snapshot also excludes vendor/tool histories, model configuration,
full prompt text, complete graph state, past_context and Memory Log contents.
Consequently it cannot alone reproduce a later research/manager execution or
identical model output. Those inputs and the consumer route need separate
versioned contracts and acceptance before such a guarantee could be made.

## 4. Context assembly and short-lived memory

B's [context builder](../../src/tradingagents/context_builder.py) organizes layers
L0 through L5: identity, hard constraints, evidence, current task, necessary
history and resume context. A missing L5 input can become an explicit `unknown`
block; that marker is not a restored checkpoint. The generic builder's ability
to accept six layers does not prove every current call site supplies all of them.
The [B trace](../plans/B/B-trace-matrix.md) records that integration distinction.

The current main builder deduplicates eligible L2/L4 blocks only when exact text
and serialized metadata match. This preserves signs and priority distinctions
that normalized punctuation fingerprints could erase. Character-based estimates
and threshold-triggered whole-block pruning constrain emitted context; they are
not provider billing measurements. Routine history is removed first, while
protected identity/constraint text is checked during reassembly. Mandatory
context that cannot fit raises ContextBudgetError rather than emitting an
incomplete prompt. Source histories and model-send receipts require their own
checks; discarding a prompt block is not a deletion from the persistent memory.

These mechanisms should not be described as a vector database, semantic retrieval
platform, semantic-equivalence guarantee or automatic cross-session memory.
Typed claim/reply/resume structures described in B's historical coursework
contract remain scoped to their delivered implementation and main coverage.

## 5. Persistent Memory Log

### 5.1 Write, settlement and concurrency

The inherited [TradingMemoryLog](../../src/tradingagents/memory/log.py) uses
`memory_log_path`. With no configured path, writes are no-ops and reads return
no entries. The shipped configuration normally supplies a path; the configured
parent directory is created at initialization.

`store_decision` appends a pending decision under a file lock. Its idempotency
key is ticker plus trade date, not E's run ID or the snapshot ID. Any existing
pending or resolved entry for that pair prevents another append. Thus multiple
experimental runs of the same ticker/date do not automatically become distinct
lessons in this log. Matched experiments need a controlled memory starting point;
this document does not change the inherited key.

Settlement obtains applicable prices and asks a model for a reflection through
the [settlement](../../src/tradingagents/memory/settlement.py) and
[reflection](../../src/tradingagents/memory/reflection.py) modules. It changes a
pending entry into an outcome/reflection record when the holding window can be
resolved. Updates write a temporary file and replace the log under the write
lock. A separate settlement lock avoids two concurrent passes paying for the
same reflections; a graph pass can use nonblocking acquisition and continue if
another pass is already settling.

The log is append-oriented for new decisions, but is not physically immutable:
settlement and configured rotation rewrite it. Those semantics differ from
Evidence's atomic no-replace publication. The Memory Log's model reflection is
also a separate AI call; A's Evidence registration itself has no AI call.

### 5.2 Retrieval and historical filtering

`get_past_context` retrieves resolved entries only. By default it selects up to
five same-ticker decisions and three cross-ticker lessons, ordered by decision
date and later file position for ties. Same-ticker entries include fuller
analysis; cross-ticker context focuses on reflections. This is explicit ranked
selection from the file, not embedding-based retrieval.

For a historical graph run, `_memory_as_of` supplies the requested analysis date.
Only entries with a known resolution date on or before that date are eligible;
legacy entries without a resolution date are excluded. For current-date runs,
the helper returns no cutoff and the inherited unfiltered resolved behavior
remains. This Memory Log cutoff does not establish the historical availability
of analyst report sources or convert null Evidence times into known times.

`_memory_step` settles pending decisions and loads context beside the analysts.
Settlement/read errors are caught and reflected in memory_note; already available
lessons may still be used, or past_context may be empty if reading fails. This is
a degraded memory path, not evidence that the stored file was repaired or that
all pending work succeeded. The Portfolio Manager consumes past_context through
its existing prompt construction.

### 5.3 Retention

`memory_log_max_entries` defaults to None, disabling rotation. When configured
with a positive cap, outcome updates invoke rotation that drops the oldest
resolved blocks by decision date/position. Pending blocks are always retained.
It is not a TTL, does not run as a background deletion job and does not cap all
entries or all disk consumption. No deletion period should be inferred from the
presence of the option.

## 6. Checkpoints, interruption and compatibility

C's [checkpointer](../../src/tradingagents/graph/checkpointer.py) uses SQLite under
`data_cache_dir/checkpoints` and stores framework checkpoint/write rows by thread.
Ordinary execution looks up the saved step and continues with None input only
when the selected thread has a checkpoint. An empty run key retains legacy
thread identity; a nonempty key separates executions without weakening their
compatibility signature. Exact lookup/cleanup primitives use the specified
original database and thread and preserve sibling threads.

The current signature includes ordered analysts, effective research/risk depths,
asset mode, portfolio fingerprint, layout markers and a digest of effective
configuration excluding specified location/retry settings. Explicit V0/V1 adds
the preset identity, while omission preserves legacy semantics. This is a
specific compatibility mechanism, not automatic migration across arbitrary code,
Prompt or serialization changes. Prompt receipt hashes and Evidence identities
must not be assumed to be signature components merely because they exist in
other records. Fresh capture remains incompatible with checkpointing.

Successful ordinary completion removes the selected checkpoint rows. A failure
before cleanup can leave state for later continuation; it does not establish
exactly-once model calls or external side effects. Restoring a framework graph
also does not restore the same external vendor data or immutable Memory Log
starting point.

The separate [resume helper](../../src/tradingagents/resume.py) implements run
locators, attempt lines and injected manifest-before-locator-clear ordering.
Its `resolve_run` returns recorded database/thread information, and optional
snapshot checking in that helper checks file presence/readability and JSON
parsing. It does not substitute for A's strict load with an external expected
ID. Helper availability/tests do not establish integrated locator preflight,
explicit graph recovery or checkpoint-bound Evidence replay. The pending
C-CKPT-02 targets in the trace matrix preserve that distinction.

## 7. Run records, projections and terminal ordering

E reserves a run ID and publishes the [RunEvent](../contracts/run-event.md)
manifest under the run's result directory. Successful capture artifacts live at
`results_dir/runs/<run_id>/evidence/<artifact_key>`. The artifact key is canonical
`v1/<digest>.json`; E's destination helper validates containment before creating
the required directory. A's syntax helper does not perform that containment.

The manifest records configuration, prompt identity, usage, duration, failure,
stop reason and any successful Evidence reference. The evidence-mode sidecar
projects just snapshot ID/key, or null values when no reference exists. Prompt
receipts describe actual inputs/digests, not every analyst tool response or a
complete checkpoint. A config-key secret filter is not report/prompt-content
sanitization.

The [CLI finalizer](../../src/cli/run.py) writes the terminal record before
record_decision and ordinary checkpoint cleanup. On failure it records the
reserved identity and rethrows the failure without following the success cleanup
path. There is a published-manifest/sidecar error distinction; nevertheless,
there is no transaction covering Evidence, manifest, sidecar, Memory Log and
SQLite. Existing success/failure tests must not be generalized into complete
crash or cross-artifact durability. Programmatic graph completion and the
explicit locator helper are separate entry paths with their own ordering.

`_log_state` writes `results_dir/<safe_ticker>/TradingAgentsStrategy_logs/`
`full_states_log_<trade_date>.json` using overwrite mode. Repeated same-date runs
can replace this projection. It contains selected reports/histories/plans,
final rating and run_settings, not the entire AgentState. In particular, the
projection does not export capture controls, evidence_diagnostics, guard_result
or stop_reason. Use the per-run artifact/manifest for run-qualified traceability;
the projection is not a resumable or immutable archive.

## 8. Version handling and source of truth

| Surface | Implemented version/identity mechanism | Limits and change responsibility |
|---|---|---|
| Evidence | schema_version 1; canonical payload/content hashes; optional external ID | Unsupported versions fail; no automatic migration. A reviews format semantics; C/E preserve bindings |
| Context/history | Current builder output and B's own contract/version fields | Historical typed protocol documentation is not a main runtime serialization guarantee; B confirms call-site and wire compatibility |
| SQLite checkpoints | Current framework serialization plus C signature/run key | C reviews graph/layout/config compatibility; no blanket upgrade or Prompt-hash guarantee |
| RunEvent and helper records | Their own schema/identity fields and readers | E owns record evolution; a valid manifest is not a full state migration |
| Memory Log | Text tags, separators and optional resolved-date field | No general schema-version migration framework; historical entries have explicit retrieval behavior |
| Engineering records | Requirement IDs, commits, pinned test hashes and dated reviews | A coordinates trace updates; each owner maintains the accuracy of their evidence |

Stored artifacts retain their original source identity. A revised documentation
file or new software commit does not retrospectively change snapshot IDs or
claim old runs used a newer Prompt. Preserve original records and add dated
migration/adoption notes when an actual change occurs.

## 9. Retention, privacy and access

| Surface | Current retention behavior | Outstanding owner decision / verification |
|---|---|---|
| Evidence, manifests and receipts | No automatic TTL or coordinated deletion established here | E/D confirm storage access, distribution, retention duration and linked-artifact deletion procedures |
| Memory Log | Optional resolved-entry cap; pending entries retained; default rotation off | A/C/E confirm intended shared versus experiment-specific log, backup and pending-entry growth handling |
| Checkpoint SQLite | Selected rows removed on ordinary success; failure can retain rows | C/E confirm interrupted-run retention and controlled cleanup; no blanket file deletion |
| Final JSON/report files | Date/ticker projection may overwrite; other artifacts depend on their writer | E confirms which records are archival evidence and which are regenerable output |
| Provider/data caches | Existing data-layer caching outside the Evidence contract | A/E confirm vendor terms, freshness and cleanup separately; no new cache policy inferred |

Report text, decisions, portfolio context and prompts may contain sensitive or
untrusted material. Hashing does not anonymize content; serialization does not
remove prompt injection; file placement does not implement authentication,
encryption or a multi-user access-control service. Existing machine file access
and coding-agent permissions are separate from application data access controls.
No such new service is implemented by this document.

For final distribution, an owner must review which fixtures, records and session
exports are shareable, remove usable credentials, and preserve any declared
redaction/omission record. A manifest's key filter alone cannot certify a whole
archive. Retention durations, privacy classification and authority to remove
shared artifacts remain explicit open decisions rather than invented policies.

## 10. Verification references and review requests

| Boundary | Existing verification reference | Evidence limit |
|---|---|---|
| Snapshot text/identity, strict load, incomplete reports and publication | [Evidence suite](../../test/offline/test_evidence.py), [key suite](../../test/offline/test_evidence_artifact_keys.py), [publication helper](../../test/offline/publication_checks.py) | 128 component passes recorded at A r9 preparation; no new run for this document |
| Actual pre-Bull capture and failure reference | [Pinned CLI capture suite](../../test/offline/fresh_evidence_capture/test_fresh_evidence_cli_review.py) | Fresh uncheckpointed V0/V1; no acquisition-skipping replay |
| Context compaction/model input and priority retention | [Wiring checks](../../test/offline/test_b_context_wiring.py), [dedup priority checks](../../test/offline/test_context_builder.py) | Partial current integration; historical coursework coverage remains separate |
| Memory writes, settlement, retrieval and concurrency | [Memory suite](../../tests/test_memory_log.py) | Inherited scripted checks, not newly executed or team-authored achievements |
| Resolution-date historical retrieval | [Point-in-time tests](../../tests/test_memory_pointintime.py) | Memory lessons only, not analyst source history |
| Ordinary checkpoint lifecycle and signature | [Lifecycle](../../tests/test_checkpoint_lifecycle.py), [resume](../../tests/test_checkpoint_resume.py), [keyed graph](../../test/offline/test_checkpoint_graph_run_key.py) | Ordinary keyed/legacy continuation, not explicit locator recovery |
| Recorder and helper failure ordering | [Recorder tests](../../test/offline/test_run_recorder.py), [resume helpers](../../test/offline/test_resume.py), [Evidence boundaries](../../test/offline/test_evidence_boundaries.py) | Separate artifact/helper boundaries, not a cross-file transaction |

Review requests: A confirms snapshot and inherited-memory descriptions; B confirms
emitted-context versus persisted-history claims and typed-protocol scope; C
confirms graph signature, interruption and cleanup boundaries; E confirms record
paths, locator/writer scope and retention; D confirms authority/privacy boundaries.
This document records no reviewer signature and grants no implementation or
publication permission. Unresolved items remain visible in the
[trace matrix](trace-matrix.md) and [runtime policy catalog](runtime-policy-catalog.md).
