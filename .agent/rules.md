# Project Covenant (.agent/rules.md)

> Human-only file. The coding agent must not modify this file.
> Standing rules for our safety-guard work.

## Abstraction and dependencies
- The safety guard (constraints.py) is pure deterministic code. It must not
  call any LLM, access the network, or place orders. Keep it simple.
- The guard uses only the Python standard library. A new dependency needs
  human approval.

## Tests
- Every feature has at least one negative test that fails when the rule is
  violated.
- Tests are written and approved before implementation. We never weaken or
  delete tests to make CI pass.

## Safety-critical changes
- Any change to safety-critical code needs an ADR and explicit human approval
  before it is made.

## Keeping rules fresh
- When a requirement changes, we update these rules within one sprint.

## Permissions
- The agent edits only modules in the approved whitelist.
- Protected integration files need an ADR plus human approval.
- Human-only files (.opencode/, .agent/, transcripts/) are never written by
  the agent.
- No one approves their own work.

