# .opencode/rules.md

> HUMAN-ONLY FILE. AI agents must not modify this file.

## Always-on rules

1. Default deny: no read/write outside whitelisted paths.
2. Never read `.env`, secrets, tokens, or private keys.
3. Do not run destructive shell commands without explicit human approval.
4. Stop before code generation until the plan is approved.
5. Safety-critical changes require an ADR and human approval.
6. Do not weaken/delete tests to make CI pass.
7. Keep the AI-use log current.
8. Each agent writes only files owned by its role (see docs/architecture/permission-model.md). D owns constraints.py, portfolio_manager.py, risk_mgmt/, trader/, portfolio.py and their tests. Never write C's graph/state files or B's schemas.py.
9. No self-approval. Every approval in docs/approvals/ is signed by another human (D's reviewer: B), recording approver, time, and the exact plan/test version. Agents never sign approvals.
10. Deterministic verdicts are final: no LLM output may turn BLOCK into PASS. Unknown position is not empty position. Insufficient information yields REVIEW. Missing or malformed fields fail closed (BLOCK).
11. Every PR that changes code or prompts must update docs/ai-use-log.yaml in the same PR.