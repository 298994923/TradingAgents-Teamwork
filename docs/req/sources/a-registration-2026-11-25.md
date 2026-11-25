# A component requirement registration — 2026-11-25, r9

Baseline: `main@2f99c3adaee870a18dc85b62089667954eddcf2b`. The requesting member A asked to register
A's requirements first and defer B's material until received. This record is a
retrospective consolidation, not a new implementation approval, a backdated
requirement decision or a claim that the requirements first appeared today.

## Provenance

- Primary adopted specification: `docs/contracts/evidence.md` (Evidence Version 1
  and additive artifact-key contract). The fresh-capture addition belongs to the
  separate C-owned runtime integration scope.
- Original component delivery: PR #16, merge
  `61402afa740f0345fc5e36c8e338a1cc88d268b9`. Existing approval provenance remains
  recorded in the earlier trace and approval ledger; no approval is reopened or
  assigned to E by this registration.
- Prior A planning input: `member-a-requirements.yaml`, retained outside the
  repository in the personal delivery-planning directory, SHA-256
  `e8c13623ddcf4e0045a18d5dab35984838edbb30d01b816500a46bd6b4199b8e`. Its seven requirement objects
  are copied without semantic changes. Source and tests already use A-EV-01..08;
  those IDs remain canonical and no REQ-A aliases are invented.
- A-EV-08 is already registered and remains byte-for-byte equivalent as a parsed
  requirement object. Other members' requirements and aliases are preserved.

## Requirement scope

### A-EV-01

Register explicit selected analyst reports and expose exact report lookup, rejecting malformed selections and report types.

Tradeoff: Keep only report-level slots; vendor histories remain outside scope.

### A-EV-02

Preserve exact UTF-8 report content, analyst/run provenance and immutable payload-derived snapshot identity.

Tradeoff: No normalization fingerprint or storage deduplication in Version 1.

### A-EV-03

Return separate reference-structure, snapshot-binding, slot-resolution and content-availability results with explicit reasons.

Tradeoff: No factual-support or historical-availability verdict is inferred from resolution.

### A-EV-04

Preserve explicit capture and analysis context while keeping unsupported cutoff, generation and source-availability metadata null in Version 1.

Tradeoff: Supporting known values for those temporal fields requires reviewed version semantics.

### A-EV-05

Save and load internally consistent immutable JSON snapshots with optional external identity binding and atomic no-overwrite publication.

Tradeoff: Local hard-link publication only; unsupported filesystem operations return an error; no arbitrary power-loss guarantee.

### A-EV-06

Preserve selected missing and empty reports with a diagnostic identifying each affected report slot.

Tradeoff: Preserve incomplete inputs; workflow actions remain with C/D.

### A-EV-07

Assess technical all-or-nothing snapshot reuse against complete required analyst selection, exact source context and optional expected identities.

Tradeoff: No partial reuse, selective regeneration, hidden live fallback or acquisition skipping is implemented by A.

## Verification and limits

The registry records real existing test functions. Metrics count assertion
violations in the fixed cases, not a production-wide rate or an authenticity
score. Invariants A-EV-02 and A-EV-04 include rejection/mutation negative cases.
A-EV-06's single referenced function contains missing, empty, whitespace and
unavailable-prose assertions; its selection does not claim malformed None is a
missing report. The complete A selector list is checked statically against the
unchanged test files; execution evidence is kept separately from that check.

EvidenceError codes/paths, registration/load diagnostics, reference dimensions
and replay findings are the component's observable results. This registration
adds no runtime alerting service or monitoring hook. A full project trace matrix
must distinguish these API observations from C/E's graph and run monitoring.

No new behavior, performance/cost promise, raw-data collection, historical
suitability verdict, partial replay or end-to-end replay is added. No source,
test, fixture, shared contract, schema, approval ledger or AI-use log is changed.
The test-file review-draft headers are historical pinned text; this registration
does not rewrite those bytes or infer an approval from such a header.

## Registration verification receipt

On 2026-11-25 A reran the two unchanged standalone suites with a credential-free
environment and external pytest plugin auto-loading disabled:

```sh
python -m pytest -q -p pytest_subtests.plugin test/offline/test_evidence.py test/offline/test_evidence_artifact_keys.py
```

Result: **128 passed in 1.46s** (83 Evidence V1 cases and 45 artifact-key cases).
Both suites load the standalone module directly and deny Python network access.
This is new component verification, not a rerun of the full inherited suite,
a live-model evaluation or new graph/CLI acceptance. The seven added requirement
objects equal the prior A draft; the previous 27 objects, including A-EV-08,
remain unchanged. Schema, all 41 unique A test-function references, aliases,
source/test/fixture fingerprints, repository Ruff and diff whitespace checks
passed during preparation. No previous approval date is changed by this receipt.

## Rebase receipt

The original A registration commit `0da0872fddfc75ac6548ba5fbff7c27950329682`
was rebased onto `63989bfd70f3aeeec35607d21bc0ac7f085a8919`.
The conflict involved upstream's removed GOV-001 entry and B/E additions at the
end of the registry. Resolution retains the current upstream file and appends
only the original seven A objects. All 58 upstream entries are unchanged; the
result has 65 unique IDs, including eight A entries. Upstream removal of GOV-001
is preserved. Original preparation/test counts above retain their recorded
baseline; no new runtime test or B/E acceptance is implied by this rebase.

## Baseline file fingerprints

- `src/tradingagents/evidence.py`: `717a24977fe8acad551470231dbb0f4a93cb79a40f2d250e0221123835dbaf88`.
- `docs/contracts/evidence.md`: `e6b7de73c51b7dfe2e1782840fce93554dde8d348bd1e36df273723838ff97ba`.
- `test/offline/test_evidence.py`: `b003fb96fa008d57a604c38aa28acbc3ff7335d1b6500d1dec61394ae967cdd9`.
- `test/offline/test_evidence_artifact_keys.py`: `357a736ac87a8fb699ea02eaa7e9655d205c9eb3345255045cfd2ebd2c72e0ce`.
- `test/offline/publication_checks.py`: `76a09ba660ad1a9731a37357ed6a190f3283bd409dacce831994240f984723d4`.
- `test/fixtures/evidence_cases.json`: `68b5d28b92b8545b8b672046ceb2c42d9ea20396c264a492107ca0d74902967c`.
