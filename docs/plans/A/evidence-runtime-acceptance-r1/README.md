# A's Evidence runtime acceptance preparation

Revision: **2026-11-25-tests-r1**. Status: tests-for-review; no production edits
or graph/CLI acceptance claim. Baseline: main@47fdde3602ba7a58df0486f03facc5248ccd0980,
branch `test/a-evidence-runtime-acceptance`.

The earlier integration plan inspected 18090cf. This preparation uses the newer
baseline containing B compression, prompt receipts and C terminal stop_reason.
Preserve those behaviors during subsequent C/E integration.

## Review files

- `inputs.json`: fixed, synthetic reports/context and two valid run-ID examples.
  These are test inputs, not E reservations or actual V0/V1 runs. Source times
  remain unknown; capture time is a fixed fixture, not analysis availability.
- `assertions.py`: reusable observations-only oracle for the five-field reference,
  expected run/capture identity, canonical key, real artifact load and exact
  selected report content. It creates no state or manifest.
- `test_contract_draft.py`: ten sample/oracle checks using real A registration,
  save/load and E's low-level RunEvent/write_manifest. Sample state/envelopes are
  deliberately constructed by the test; this does NOT exercise graph capture,
  CLI forwarding, early run reservation or E destination preparation.

Each test cites an existing Evidence review handle. These citations do not
adopt new requirements or claim that broader runtime acceptance is completed.
No fixed C or inherited tests are edited.

## Local result

In a dotenv-free isolated baseline copy with no provider credentials:
**10 passed**; Ruff over these draft files passed. Test fixtures deny Python
network calls. This is a targeted draft check, not a new whole-repository result.
Logs and hashes are retained outside the application checkout under
delivery-planning/evidence-runtime-tests-2026-11-25-r1.

Drafts stay in A's personal plan directory, outside normal pytest discovery.
Run explicitly only in an isolated source snapshot:

```sh
python -m pytest -q -p pytest_subtests.plugin docs/plans/A/evidence-runtime-acceptance-r1/test_contract_draft.py
```

## Actual joint tests still required

| Actual boundary | Owner / dependency | Required observation |
|---|---|---|
| Early identity and destination | E confirms real interfaces | Collision-safe ID reserved once; validated path/root prepared; writer reuses identity |
| Analyst join to Evidence publication | C confirms context/hook and reviewed protected scope | Actual node invokes registration/save before research; actual final state enters oracle |
| State through CLI finalizer | E/C forwarding | Real CLI writer's manifest enters oracle; populated and legitimate-null paths |
| Capture failure | C/E | Real injected save/destination failure remains observable and publishes no usable reference |
| Manifest failure | E/C | Actual writer exception prevents checkpoint cleanup and preserves original error/identity |
| Retry and V0/V1 execution | Joint | Real capture reuses frozen inputs; both graph variants preserve existing behavior |

Do not satisfy these rows by invoking `sample()` or by supplying fabricated state.
The current ten checks intentionally validate only the oracle and sample contract.
After interfaces and actual tests are reviewed, move/compose approved tests into
test/offline with fixtures under test/fixtures. Keep the existing Evidence contract
and RunEvent schema unchanged. No new A wrapper is proposed.

## Short C/E handoff

A's fixed inputs and artifact/reference oracle are ready for review on the pinned
baseline. Please confirm E's ID-reservation/destination/writer interfaces and C's
capture context/hook so the real combined test can supply actual outputs. No
proposed E function names are encoded in these drafts. Existing source/approval
records are unchanged; this package is preparation, not implementation approval.
