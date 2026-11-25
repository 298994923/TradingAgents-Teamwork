# Report-level evidence contract — Version 1 review draft 2

Status: Version 1 standalone implementation contract, approved by the requesting
human in chat together with the plan and revision 2 test package. The reviewed
draft and its fingerprints are retained in the personal review package. This
status annotation changes no reviewed payload or behavior. Graph integration and
end-to-end replay remain separate work; this document is not runtime evidence.

## Stored payload and identity

All fields below are required. Unknown fields are rejected at every level.

| Object | Fields and types |
|---|---|
| Snapshot | schema_version: exact string `1`; snapshot_id: `sha256:` + 64 lowercase hex; source_run_id: nonempty non-whitespace string; captured_at: exact UTC time; context: object; reports: nonempty object |
| context | instrument: object; instrument_context: string (empty allowed); analysis_date: calendar date `YYYY-MM-DD`; analysis_cutoff_at: null |
| instrument | symbol: nonempty non-whitespace string; asset_type: `stock` or `crypto` |
| reports[key] | content: string or null; content_sha256: 64 lowercase hex or null; report_generated_at: null; source_available_at: null |

Version 1 keys have fixed meanings independent of future graph code:
market = Market Analyst / market_report; social = Sentiment Analyst /
sentiment_report; news = News Analyst / news_report; fundamentals = Fundamentals
Analyst / fundamentals_report. Keys are local evidence IDs. Report source type is
implicitly analyst_report. Repeated equal text never merges distinct slots.

`captured_at` must be exactly `YYYY-MM-DDTHH:mm:ss.ffffffZ`, a valid calendar time
with six fractional digits. No offsets, omitted fractions, or leap seconds. No
date/time normalization or rewriting. Capturing today for a past analysis is valid.
All other stored time fields MUST be null in Version 1; admitting non-null values
requires a reviewed new version. They must not be inferred from prose or other dates.

`content_sha256` is SHA-256 of the exact content UTF-8 bytes, no BOM. Null content
requires null hash; every string, including empty/whitespace text, has a hash.
All strings must contain Unicode scalar values encodable as UTF-8. No stripping,
newline conversion, or Unicode normalization is applied to preserved strings.

Canonical payload encoding is defined as Python JSON serialization with
`ensure_ascii=False`, `sort_keys=True`, `separators=(",", ":")`, `allow_nan=False`,
followed by strict UTF-8 encoding, without BOM or trailing newline. This is a
version-specific encoding, not a claim of RFC canonicalization compliance. The
schema contains objects, strings and null only. Keys sort by Unicode code points;
JSON control-character escaping follows that encoder. A fixed independent vector
in the fixture pins the expected ID. JSON file indentation/key order need not
match this encoding; reconstructed string values must match exactly.

snapshot_id = `sha256:` + SHA-256 of the entire canonical snapshot object with
only the top-level snapshot_id field excluded. Identity therefore includes schema,
source run, capture time, full context, report selection, content and metadata.
Equal text alone does not imply equal IDs or equivalent provenance. Hashes check
recorded consistency, not truth, credibility, authenticity or semantic support.

## Explicit registration boundary

`register_reports(*, selected_analysts, analyst_outputs, source_run_id,
captured_at, context) -> RegistrationResult`

- selected_analysts is a list or tuple of distinct supported strings, nonempty.
  Reject a scalar string, duplicate/unknown keys, or invalid element types.
- analyst_outputs is a mapping from selected canonical keys to strings. C maps
  existing report fields using the versioned table; unselected output keys fail.
  Absence of a selected key becomes null content/hash; present None or any other
  non-string fails INVALID_REPORT_TYPE. Whitespace-only strings remain exact.
- C provides the existing context object with analysis_cutoff_at null. E/C provide
  identity and capture time. A adds no clock reads, randomness or external calls.
- Result has `.snapshot` and `.diagnostics` (immutable Diagnostic tuple). Diagnostic
  has `.code` and `.path`. Propose MISSING_REPORT, EMPTY_REPORT per affected slot
  and TIME_METADATA_UNKNOWN for unavailable temporal metadata.
- Diagnostic paths use JSON Pointer notation: the root is the empty string;
  segments are prefixed with `/`, with `~` escaped as `~0` and `/` as `~1`.
  Report-completeness findings point to the slot, e.g. `/reports/news`, not its
  content field. Each missing/empty selected slot has its own code/path finding.
  Unknown-time and other unrelated diagnostics may coexist. A nonempty report
  describing DATA_UNAVAILABLE does not receive missing/empty findings.
- Malformed input raises `EvidenceError` with stable `.code` and `.path`, returning
  no partial snapshot. It is not an incomplete-report diagnostic.
- Snapshot, ReportSlot, results and nested collections are immutable. Snapshot
  exposes `.snapshot_id`, `.source_run_id`, `.captured_at`, `.reports`, `.context`,
  and `.to_dict()` returning a detached mutable JSON-ready copy. Slot exposes the
  four stored fields. Do not retain mutable aliases to caller inputs.

Identical complete inputs produce identical identity. C must preserve the original
selection, content, context, source_run_id and captured_at across retry/resume, or
retain the registered snapshot itself. A cannot infer retries from ticker/date.

## Lookup and reference dimensions

`lookup_report(snapshot, evidence_id) -> ReportSlot` returns an existing slot even
when missing/empty. Unknown/unselected keys raise UNKNOWN_EVIDENCE_ID or
ANALYST_NOT_SELECTED. Invalid argument types raise MALFORMED_REFERENCE.

`validate_reference(snapshot, reference) -> ReferenceResult` accepts exactly
snapshot_id and evidence_id, both nonempty strings; snapshot_id follows its hash
format. Results have `.structure` (conformant/malformed), `.binding`
(matched/mismatched/not_checked), `.slot` (found/not_found/not_checked),
`.availability` (present/missing/empty/not_checked), `.reasons` (tuple of codes).
Only checks whose prerequisites succeed run. A syntactically well-formed unknown
evidence_id is unresolved, not structurally malformed. Known unselected keys get
ANALYST_NOT_SELECTED; unknown keys get UNKNOWN_EVIDENCE_ID. Missing/empty slots
resolve correctly and produce MISSING_REPORT/EMPTY_REPORT. No ambiguous valid bit.
Nonempty prose describing unavailable data is present content, not a data-quality
certification. Whitespace classification uses str.strip only to classify, never
to change stored content.

## Local-file persistence

`save_snapshot(snapshot, path) -> SaveResult` with `.status` created/already_present
and `.path`. A implements the helper, E chooses directories/retention and C/E invoke
it. Parent directory must exist. Write a temporary file in that directory, finish
the write, then atomically publish without replacing an existing destination.
Cleanup temporary files best effort. An existing verified identical payload means
already_present; a different or malformed artifact means DESTINATION_CONFLICT and
is untouched. A check-then-overwrite race is not allowed. Atomic visibility is
promised; arbitrary power-loss durability is not. Other filesystem errors become
IO_ERROR with the original exception chained, without sensitive artifact content
in public messages. After ambiguous errors, callers may load/retry; do not claim
rollback or silently fall back to another location.

`load_snapshot(path, *, expected_snapshot_id=None) -> LoadResult` exposes `.snapshot`,
`.diagnostics`, `.expected_identity` matched/not_supplied. It reads strict UTF-8
JSON, rejects BOM, duplicate keys at all nesting levels, unknown fields, missing
fields, nonstandard numeric constants, invalid types, unsupported versions and
noncanonical dates/timestamps. It verifies per-content hashes and the snapshot
digest. Preserve source_run_id, captured_at and all content; never re-register.

Expected identity, when supplied, must match after internal verification. Without
it, internal consistency is checked but expected_identity is explicitly not_supplied.
A self-consistent replacement is detected only when compared to an external expected
ID. E's run record holds that expectation. Hashes do not authenticate the author.
Fatal errors return no usable snapshot; no partial loading or automatic migration.

Stable proposed error codes: INVALID_SELECTION, UNKNOWN_ANALYST,
DUPLICATE_ANALYST, UNSELECTED_OUTPUT, INVALID_REPORT_TYPE, INVALID_CONTEXT,
INVALID_TIMESTAMP, INVALID_SCHEMA, UNSUPPORTED_VERSION, INVALID_JSON,
DUPLICATE_JSON_KEY, CONTENT_HASH_MISMATCH, SNAPSHOT_HASH_MISMATCH,
EXPECTED_SNAPSHOT_MISMATCH, MALFORMED_REFERENCE, UNKNOWN_EVIDENCE_ID,
ANALYST_NOT_SELECTED, DESTINATION_CONFLICT, IO_ERROR. Validate the schema before
hash consistency; check content hashes before payload hash; expected ID last.

## Technical replay assessment

`assess_replay(snapshot, *, required_analysts, expected_context,
expected_source_run_id=None, expected_snapshot_id=None) -> ReplayAssessment`
has `.ready` (technical readiness only), `.findings` (Diagnostic tuple), and
`.expected_identity` matched/not_supplied/mismatched.

Validate caller expectation types as input errors. Required analysts must equal
the snapshot's full key set; a subset is not partial reuse. All required slots
must contain non-whitespace strings. Expected context must be a complete valid
Version 1 context and match exactly, with no normalization or wildcard fields.
Optional source-run and snapshot expectations must match when supplied. Findings
include ANALYST_SELECTION_MISMATCH, CONTEXT_MISMATCH, SOURCE_RUN_MISMATCH,
EXPECTED_SNAPSHOT_MISMATCH, MISSING_REPORT and EMPTY_REPORT. Null time metadata
does not itself fail this content/context readiness check; it remains unknown and
cannot establish historical suitability. D may impose a stricter use policy.

Snapshots obtained through registration/loading are internally verified and
immutable. Operations reject an invalid snapshot object rather than accepting a
mutable unverified dict. Complete replay assessment does not require the source
run to equal the consumer run unless explicitly requested. Consumer IDs stay in
E's run records. C separately implements whole-stage skipping and records mode;
there is no partial regeneration or hidden fallback to acquisition in A's module.

## Software API addition — artifact keys, 2026-11-22-helper-r1

Development authorized by the requesting human in chat; postdevelopment review
is pending. This additive software contract leaves snapshot schema_version "1",
stored fields, canonical serialization, identity calculation and save/load APIs
unchanged. Prior approvals and verification apply to their recorded versions.

Public imports from `tradingagents.evidence`:

`artifact_key_for(snapshot_id: str) -> str`

Accept exactly `sha256:` followed by 64 lowercase ASCII hexadecimal characters
(0–9, a–f). Return exactly `v1/` + the same digest + `.json`.

`parse_artifact_key(artifact_key: str) -> str`

Accept only that exact version-1 key form. Return the complete `sha256:` ID.
Both round trips preserve accepted strings exactly. Ordinary str subclasses are
accepted; outputs are strings. Missing/extra call arguments follow normal Python
TypeError behavior. Invalid supplied values use the existing EvidenceError:

| Invalid supplied value | code | JSON Pointer path |
|---|---|---|
| Non-string or noncanonical snapshot_id | INVALID_CONTEXT | /snapshot_id |
| Non-string or noncanonical artifact_key | INVALID_CONTEXT | /artifact_key |

No coercion, trimming, lowercasing, separator normalization or URL decoding.
Wrong versions/prefixes/suffixes, uppercase, whitespace/newlines, absolute/URL
forms, extra segments and traversal-like inputs fail explicitly. No new public
error codes or missing/unreadable exception classes are introduced.

Both helpers perform pure syntax conversion: no filesystem access, root
resolution, directory creation, snapshot save/load, identity generation, network
or LLM calls. A key proves neither existence nor content identity. E's locator
owns candidate-path/root containment and symlink policy. A owns these helpers and
E consumes this single canonical format. C binds a runtime reference only after
successful archival; E remains manifest writer.

These helpers do not construct the runtime evidence_snapshot envelope and are
separate from B's alias → {snapshot_id, evidence_id} report-reference mapping.
Source/module hashes and this software addition's revision can change without
changing stored snapshot IDs or schema_version. End-to-end integration acceptance
remains separate.

## Fresh V0/V1 Evidence capture

Fresh Evidence capture is invocation-local, explicit, and limited to V0/V1 without checkpointing. A reserved `source_run_id` alone does not activate it. Malformed activation payloads, missing or blank capture identifiers, and effective checkpoint enablement are rejected before any node execution or Evidence storage access. With capture off, the existing graph state, route, checkpoint behavior and terminal output remain unchanged. With capture on, the graph waits for all selected analysts and the existing Memory Log dependency, if present, at the same barrier before Bull.

The capture node freezes the selected report inputs and analysis context with the reserved ID and one UTC capture instant. Missing selected output and emitted blank content remain distinguishable; diagnostics do not alter the reference envelope. Use the existing Evidence registration, canonical key and save APIs and the recorder's containment-checked destination. Only successful creation or verified identical reuse may publish `evidence_snapshot`, using exactly `snapshot_id`, `artifact_key`, `store`, `source_run_id`, and `captured_at`. Save or destination failure aborts before research, emits no reference and retains the original failure and reserved identity at the caller boundary.

The terminal writer copies the successful streamed reference to the existing RunEvent field; the evidence-mode sidecar projects only its snapshot ID and artifact key into `snapshot_ref`, or two nulls for absent/failed capture. This is not a change to terminal durability, cleanup ordering, Evidence or RunEvent schema, Guard, stop reasons, or prompt receipts. Checkpoint binding, replay, recovery and V2 are excluded.
