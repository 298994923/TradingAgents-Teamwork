# Project startup prompt

## 1. Plan
Read AGENTS.md and its listed project documents. Identify the change owner.
Present a plan before editing. Map requirements, invariants and ADRs to tests.
Specify interface inputs, outputs, failure behavior and compatibility.
Name the allowed paths, shared dependencies and owners of frozen files.
List positive and negative tests, ordered steps and measurable exit conditions.

## 2. Approval
Stop for explicit human approval of the identified plan version.
If the reviewer requests changes, revise the plan and submit it again.
Write tests first. Run them, report the observed failures and obtain independent
approval of that test version before implementing the change.

## 3. Execute one approved stage
Run the relevant tests, implement the approved step, then run its self-check.
Paste the actual command and key output, including failures and skipped work.
Report changed paths, coverage, deviations and outstanding decisions.
Stop for human review before moving to the next stage.

## 4. Record and stop
At each stage, update the AI-use log and trace matrix through their designated
owners; provide pending entries when another owner must merge them.
Link evidence to the stage, requirement, invariant and reviewed version.
Stop immediately at a scope, architecture or contract boundary and request review.
Keep the process human-gated through submission; never run unattended to completion.
