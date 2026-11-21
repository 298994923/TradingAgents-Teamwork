# OpenCode always-on rules (human-only)

This file is human-only. The coding agent may read it and must treat it as
binding, but it must never modify it. `opencode.jsonc` denies edits to this
path; only a human commit may change these rules.

The enforced permission rules live in `opencode.jsonc`. This file explains how
the team expects the agent to behave inside those permissions; it does not grant
anything that `opencode.jsonc` denies.

## Authority

- The agent is advisory. The deterministic safety guard is authoritative.
- A `BLOCK` from the guard cannot be argued away, regenerated away, or turned
  into `PASS` by the model. The model may explain the block; it may not override it.
- If a task, prompt, or user request conflicts with these rules, stop and ask
  the human. Do not widen permissions, disable tests, or bypass the guard to
  make a task succeed.

## Start of a session

1. Read `AGENTS.md`, `Prompt.md`, `.agent/rules.md`, this file, and the
   architecture/requirement artifacts listed in `AGENTS.md`.
2. Produce an execution plan covering traceability, interface contracts, scope
   boundaries, testing strategy, and ordered steps.
3. Stop for explicit human approval of the plan before writing any code.
4. Work in small steps and surface the evidence after each step. Do not run the
   whole build unattended.

## Permitted work

- Edit only the working paths allowed by `opencode.jsonc`: non-protected
  `src/`, `test/`, `tests/`, `scripts/`, `docs/`, `prompts/`, and the named
  root files.
- Do not look for another route around a denied path (symlinks, generated
  scripts, `bash` file readers, or writing outside the repository).
- Do not edit `opencode.jsonc`, `.opencode/**`, `.agent/**`, `AGENTS.md`,
  `Prompt.md`, `docs/review-memo.md`, or `transcripts/**`.

## Tests and verification

- Write the tests first and get human approval before implementing the behavior.
- Every feature has at least one negative test; every invariant has a test that
  fails when the invariant is violated.
- Every test cites the `REQ-...` / `INV-...` ID it verifies.
- Never weaken, skip, `xfail`, or delete a test to make CI pass. A skipped
  invariant test is not a passing invariant test.
- Run the full prior suite, not only the tests you touched:

  ```sh
  python -m pytest tests test/offline -q
  ```

- Report failures and skipped tests honestly. Do not claim a pass you did not run.

## Safety-critical and protected paths

Changing any of these needs an ADR and explicit human approval before the
change:

- `src/tradingagents/dataflows/**`
- `src/tradingagents/agents/structured.py`
- `src/tradingagents/agents/rating.py`
- `src/tradingagents/default_config.py`
- `docs/req/**`
- `docs/approvals/**`
- `docs/code-governance/**`
- `docs/evaluation/test-baseline.json`
- `scripts/ci_gates.py`, `scripts/check_*.py`
- `.github/**`
- `tests/conftest.py`, `tests/test_layering.py`
- `test/offline/conftest.py`, `test/offline/test_ci_gates.py`

If asked to change one of these, stop and produce the ADR proposal instead of
editing the file.

## Secrets and network

- Never read, print, copy, or commit `.env`, key material, tokens, or
  credentials. Do not run `cat .env`, `env`, `printenv`, or equivalent.
- Do not commit a secret, and do not paste one into a report, transcript, prompt,
  or test fixture. If one is exposed, stop and tell the human to rotate it.
- `webfetch`, `websearch`, and subagents are disabled. Ask the human if a task
  genuinely needs them; do not attempt a shell-based workaround.
- Shell use is limited to the allowlist in `opencode.jsonc` (read-only git,
  tests, lint, type-check, compile, `pip check`, `ls`, `pwd`). Do not use shell
  commands to read content that the `read` rules deny, and do not install
  packages.

## Evidence and review

- Update `docs/ai-use-log.yaml` for every change to code or prompts, with a real
  entry: what the agent did, what the human reviewed, and what was rejected.
- Record real bugs and debt in `docs/bug-diary.md` / `docs/debt-register.md`.
  Do not invent incidents, test results, or approvals.
- Every pull request needs a review memo with an explicit verdict. The author
  cannot approve their own change, and the agent cannot sign an approval.
- Approval records live in `docs/approvals/`; only a human adds them, and the
  test commit must come before the implementation commit.

## Freshness

- When a requirement or architecture decision changes, update this file and the
  related artifacts within one sprint. Stale rules are a defect.
- If a rule here is wrong or blocks legitimate work, stop and ask the human to
  change it; do not silently ignore it.
