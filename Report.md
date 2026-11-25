# Member A: Contribution to the Software Engineering Process Report

- **Name:** Zhang Ruiqi
- **Student number:** 58924242
- **Role:** Evidence management, requirements coordination and traceability
- **Status:** Individual contribution draft for integration into the team report
- **Prepared:** 2026-11-25
- **Inspected repository revision:** `2f99c3adaee870a18dc85b62089667954eddcf2b`

This document contains my contribution only. It describes the work and review
activities supported by available records, distinguishes completed implementation
from proposed registration, and includes a personal reflection for my review.

## 1. Responsibilities and delivered contribution

My main implementation responsibility was report-level Evidence management. I
also coordinated requirement registration and traceability, prepared technical
handoffs, reviewed a teammate's context-compression changes, and contributed to
demo and presentation preparation. These activities connected a small software
component to the wider development process.

The Evidence component provides deterministic registration and lookup, immutable
snapshots, content hashing, reference validation, strict save/load operations,
technical reuse assessment and canonical artifact-key conversion. The main module
and its fixed tests were delivered through
[PR #16](https://github.com/298994923/TradingAgents-Teamwork/pull/16).
The component adds no model call or vendor dependency.

I supplied the component contract and acceptance material to the workflow and
runtime-recording owners. I did not independently modify their graph, shared
state or terminal-writer modules. Integration ownership remained explicit so that
several contributors did not implement competing versions of the same boundary.

## 2. Requirements refinement and acceptance criteria

### 2.1 Establishing an achievable evidence boundary

I began by tracing how the analysts obtain information and what survives their
output boundary. Their acquisition mechanisms differ, but their common external
product is report text. The available boundary therefore supports preserving
reports and explicit execution context; it does not expose every original vendor
response or establish the historical availability of every source.

This finding narrowed the requirement. Evidence V1 preserves the exact reports
used in an execution, resolves snapshot-qualified references, checks consistency
and assesses whether a complete recorded input set can be reused. It does not
certify facts, semantic support, source credibility or identical future model
output. Unknown source availability remains null instead of being inferred from
analysis or capture dates.

I also separated missing, empty and malformed inputs. An absent selected report
creates a missing slot and diagnostic. An empty or whitespace-only string is
preserved exactly and classified separately. A supplied non-string value fails
validation. A nonempty report describing unavailable data remains report content,
not proof that its underlying data is available.

### 2.2 Requirement families and registration

| ID | Required behavior | Verification focus |
|---|---|---|
| A-EV-01 | Register selected reports and expose exact lookup | Fixed payload, selections, report types and lookup results |
| A-EV-02 | Preserve exact text, provenance and immutable identity | Hash vectors, changed inputs, detached exports and mutation rejection |
| A-EV-03 | Separate reference structure, binding, resolution and availability | Explicit dimensions and reason codes for invalid or incomplete references |
| A-EV-04 | Preserve explicit capture context and unknown temporal metadata | Exact UTC format and rejection of unsupported non-null times |
| A-EV-05 | Save/load strict snapshots without overwriting conflicts | Parsing, hashes, expected identity, publication races and I/O failure |
| A-EV-06 | Diagnose selected missing and empty reports per slot | Missing, empty, whitespace and unavailable-prose distinctions |
| A-EV-07 | Assess technical whole-selection reuse | Exact selection/context, completeness and optional identity expectations |
| A-EV-08 | Convert canonical snapshot IDs and artifact keys without I/O | Exact round trips and rejection of noncanonical inputs |

Each requirement has an owner, type, statement, priority, source, tradeoff and
machine-checkable fit criterion. The Evidence fixed-case metrics require zero
assertion violations. Detailed chronology belongs in linked records rather than
being repeated in every compact YAML entry.

A-EV-08 is already in the inspected main registry. I prepared the missing seven
entries in registration r9, preserving the IDs already cited by source and tests.
R9 was initially prepared as a 27-to-34-entry candidate. The registration
commit was subsequently rebased onto main revision
`63989bfd70f3aeeec35607d21bc0ac7f085a8919`, after B/E registration. It now
preserves all 58 upstream entries and adds only the seven A entries, for 65
total. It is committed locally but not yet adopted by a merge. This is
retrospective consolidation, not a claim that the final registry existed before
implementation. B/E entries remain their owners' responsibility; retaining them
does not independently endorse their fit criteria or acceptance evidence.

## 3. Design decisions and integration work

### 3.1 Explicit inputs and immutable identity

`register_reports` receives selected report values, source-run identity, capture
time and context explicitly. It does not read a clock, access environment
variables or obtain live data. Identical complete inputs produce identical
snapshot identity, making the component testable independently of agent behavior.

A snapshot stores exact report strings and content hashes. Its ID is derived from
the complete versioned payload, excluding the ID field itself. Analyst keys act
as snapshot-local evidence IDs, so a reference consists of the snapshot ID and
analyst key. Equal text does not merge different analyst slots or erase their
provenance. Immutable nested values and detached exports prevent later caller
mutation from changing the registered artifact.

Including source identity and capture metadata means that recording the same
text at another capture time legitimately produces a different snapshot. I made
this consequence explicit in the handoff: callers must preserve the original
capture context when continuity is intended.

### 3.2 Persistence and failure behavior

`save_snapshot` writes complete JSON to a temporary file beside the destination,
then uses an atomic hard link to publish without replacing an existing artifact.
An already-present, verified identical snapshot is an idempotent result. A
conflicting or malformed destination remains untouched. This design avoids a
check-then-overwrite race and allows readers to observe complete published data.

`load_snapshot` checks strict UTF-8 JSON, schema structure, content hashes and
snapshot identity before comparing an optional externally recorded expected ID.
A self-consistent replacement cannot be detected without that external binding.
Hashes establish recorded consistency, not authenticity. Atomic visibility is
the supported guarantee; arbitrary power-loss durability is not promised.

Failures expose stable codes and paths. File-system exceptions retain their
original cause, allowing callers to classify missing, unreadable or other I/O
problems without parsing an error message or inventing a second exception scheme.

### 3.3 Small shared helpers and ownership

I implemented `artifact_key_for` and `parse_artifact_key` as pure syntax helpers.
They accept only the exact versioned canonical form and perform no storage or
network access. A key does not prove that an artifact exists or that its contents
match. The storage owner retains responsibility for root containment and symlinks.
This keeps one shared key format while avoiding a second storage abstraction.

| Handoff recipient | My supplied material | Responsibility retained by the recipient |
|---|---|---|
| B | Snapshot-qualified reference format, validation dimensions and examples | Research/context representation and prompt consumers |
| C | Registration inputs, report mapping, identity rules, component tests and contract oracle | Graph ordering, state transport and execution paths |
| D | Explicit findings and limits of reference/time checks | Authoritative safety and fallback decisions |
| E | Key helpers, save/load contract, error causes and artifact examples | Reserved run identity, destinations, manifests and presentation |

The fresh-capture integration uses the analyst/Memory Log barrier before Bull.
I supplied Evidence operations and verification material; C/E implemented their
runtime seams. Contract adoption, requirement registration and producer delivery
were tracked separately in PRs #46, #47 and #48. Their separation prevented a
registered requirement or a manually constructed state value from being mistaken
for a working runtime path.

`assess_replay` checks whole-selection technical readiness only. It does not skip
analysts, invoke research or provide partial regeneration. I kept that boundary
explicit so component reuse was not reported as completed end-to-end replay.

## 4. Human-agent supervision and review

I used an AI coding agent for source inspection, design exploration, test drafting,
implementation, verification and document preparation. My role was to define and
refine scope, challenge unsupported guarantees, review the proposed contract and
results, redirect work and control publication. The agent's explanation was a
review input, not independent approval.

My interventions included narrowing Evidence to report-level preservation,
rejecting invented source timestamps, requiring whole-selection reuse, separating
component tests from real graph acceptance, and strengthening publication tests.
The original missing-module red run showed that implementation was absent; it
was a setup failure, not a behavioral assertion failure. Later persistence tests
exercised the actual module, including concurrency and injected write failures.

I also kept approval chronology explicit. Scope acceptance, test approval,
postimplementation review and permission to publish are distinct decisions.
Existing Evidence approval remains attributed to the actual reviewer and date;
consolidating requirements does not create a new signature or backdate an earlier
review. I manually controlled Git publication through selected files and PRs.

### 4.1 Cross-review of context compression

I reviewed candidate `76b12c0` and identified two defects despite its passing
examples. A normalization rule could collapse `Forecast EPS 5` and
`Forecast EPS -5`, removing a meaningful distinction from the actual Bull input.
Another path discarded later unresolved/disagreement/citation metadata during
deduplication; routine pruning could then remove the surviving copy.

The review requested preservation of meaningful distinctions before priority
selection and verification through the actual model-send path. Revised candidate
`3106f1d` required exact text and matching metadata for deduplication. Independent
Bull/Bear checks retained both signs and priority-bearing blocks, and prompt
receipt hashes matched actual model input. I explicitly approved the reviewed
candidate on 2026-11-25 after implementation and re-review. This was not described
as preimplementation test approval.

The episode changed my review method: I looked for counterexamples to an
optimization's assumptions and checked the consumer boundary, rather than relying
on a plausible renderer output or aggregate test count.

## 5. Verification and traceability

The standalone Evidence tests load the module directly, use synthetic fixtures
and temporary files, and deny Python network access. This avoids depending on
live providers for deterministic registration and persistence checks. Existing
inherited tests were retained alongside the new tests.

| Verification record | Result | Interpretation |
|---|---|---|
| Original standalone milestone | 83 Evidence cases passed; historical combined run had 1,495 passes, one skip and one deselection | Earlier component/baseline evidence, not current system acceptance |
| Current r9 component check | 128 passes in 1.46s across Evidence and artifact-key suites | Unchanged standalone component behavior |
| Requirement consistency | 41 unique A test-function references resolve; schema validates 34 candidate entries; previous 27 objects unchanged | Concrete bindings and registry structure, not whole-project coverage |
| Static and publication checks | Repository Ruff and diff whitespace checks passed | Recorded preparation checks; no new source or test changes |
| Compression re-review | Seven supplied cases and independent reproductions passed; historical regression had 1,942 passes, one skip and one deselection | Candidate-specific defect closure, not measured token savings |

The 128 cases comprise 83 Evidence V1 cases and 45 artifact-key cases. No full
regression, live evaluation or graph/CLI acceptance was rerun for r9's
documentation-only registration. Historical counts refer to their recorded
versions and must not be combined into a new total or treated as a performance
trend.

I maintain the distinction between application evidence and engineering evidence.
Application Evidence preserves analyst reports. Engineering evidence links
requirements, design, code, tests, reviews and versions. My coordination role is
to make those links inspectable; each module owner remains accountable for the
accuracy of their own claims and results.

The final whole-project trace matrix still needs each owner's enforcing
components, tests and runtime observations. Existing diagnostics, reference
results and replay findings are observable API outcomes; I do not invent an
alerting service to fill a monitoring column. Original records remain unchanged,
with dated updates identifying later adoption or verification.

## 6. Challenges, learning and remaining delivery work

The largest coordination challenge was distinguishing implementation presence
from integration readiness. Early packages could demonstrate a working component
or a synthetic manifest reference without showing that the real CLI invoked the
component. I responded by preparing a contract oracle, fixed inputs and specific
handoff obligations, while reserving actual graph acceptance for the integrating
owners.

Documentation also lagged behind code. The source and tests cited eight A IDs,
but the inspected shared registry initially included only one. The r9 update
repairs that gap while preserving the historical record. I would improve this
process by updating requirement and test links at each accepted change and using
a short, versioned integration checklist for every handoff.

Remaining A work includes obtaining adoption of the r9 registration, consolidating
incoming requirement packs, completing the Evidence architecture decision and
snapshot/state material, contributing the whole-project trace matrix, and
preparing my annotated original session record and final demo evidence. These
are documentation and delivery tasks; they do not establish additional runtime
capabilities.

I do not claim token or latency savings for Evidence itself. Fixed workflow
reduction, character-based context budgets and provider-reported token usage
are different measurements. Any team-level performance claim needs a comparable
experiment and quality assessment supplied by its responsible owners.

## 7. Personal reflection

**Zhang Ruiqi (58924242). Draft for personal review.**

I began by trying to understand where I could contribute most effectively: project
coordination, implementation, or architectural work. Taking responsibility for
Evidence gave me a concrete development problem while also exposing the
coordination work required to make a small module useful. I learned that being
responsible for traceability does not mean personally validating every teammate's
technical conclusion. My responsibility is to make the source, version, test and
remaining limitation inspectable, while each owner remains accountable for the
accuracy of their contribution.

The most useful design step was tracing what actually survives the analyst output
boundary. I initially associated evidence with original news or vendor data, but
the accessible boundary primarily exposes generated reports. That changed the
promise we could responsibly make. We could preserve exact content, identify a
snapshot, validate references and assess whether a complete recorded input set
could be reused. We could not infer historical availability or guarantee that a
later model would reach the same conclusion. Recording these limits helped us
avoid expanding the component beyond the available data.

Using an AI coding assistant also changed how I approached review. A clear-looking
implementation and a green test summary were useful starting points, but neither
was sufficient. During B's compression review, a normalization rule removed the
difference between positive and negative EPS text, and another path lost metadata
that should have protected an unresolved item. Counterexamples through the actual
model-send path exposed both problems. I came to see review as testing the
assumptions behind an optimization rather than checking whether the code matched
its own explanation.

I also saw the cost of delayed documentation. Source, tests and review material
could exist in different folders while the shared requirement registry remained
incomplete. Consolidating them near submission required careful reconstruction
of versions and approval dates. I would improve the next project by updating the
requirement-to-test links at each accepted change and using a short integration
checklist before handing work to another owner. I would retain the original
records and add dated updates, rather than making history appear cleaner than it
was.

My main lesson is that effective AI-assisted development depends on precise
boundaries and deliberate human decisions. The assistant accelerated exploration,
implementation and verification, but I still had to decide what a result meant,
challenge unsupported guarantees and ensure that publication matched the reviewed
scope. Those decisions are a substantive part of my engineering contribution.

## 8. Supporting material for report integration

| Material | Contribution supported |
|---|---|
| [Evidence contract](docs/contracts/evidence.md) and [module](src/tradingagents/evidence.py) | Guarantees, interfaces and limits |
| [Evidence suite](test/offline/test_evidence.py), [artifact-key suite](test/offline/test_evidence_artifact_keys.py), [publication helper](test/offline/publication_checks.py), [fixtures](test/fixtures/evidence_cases.json) | Positive, negative and persistence verification |
| [Requirements](docs/req/requirements.yaml), [aliases](docs/req/aliases.json), [registration trace](docs/req/evidence-registration-trace.md), [A r9 source record](docs/req/sources/a-registration-2026-11-25.md) | Requirement provenance, preserved IDs and current local candidate status |
| [Approval ledger](docs/approvals.yaml) | Recorded reviewer, date, candidate and scope; no new approval inferred |
| [PR #16](https://github.com/298994923/TradingAgents-Teamwork/pull/16) | Evidence component delivery |
| [PR #47](https://github.com/298994923/TradingAgents-Teamwork/pull/47) | C capture requirement/test mapping coordinated by A |

The original plan, execution logs, handoff packages and compression review
reproductions are retained in my personal delivery-planning material. Relevant
originals or adopted references must accompany the final shared evidence index;
this chapter is not a substitute for raw transcripts or review records. My
relative contribution is to be agreed from verifiable work rather than assigned
an unsupported default weight here.
