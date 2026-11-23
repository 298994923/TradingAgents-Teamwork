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
8. The agent writes only modules in the approved whitelist (see
   docs/architecture/permission-model.md). Protected integration files
   (graph/setup.py, conditional_logic.py, trading_graph.py, agents/state.py,
   default_config.py) and agents/schemas.py need an ADR plus human approval
   before any edit.
9. No self-approval. Every approval in docs/approvals/ is signed by another
   human, recording the approver, time, and the exact plan/test version.
   Agents never sign approvals.
10. Deterministic verdicts are final: no LLM output may turn BLOCK into PASS.
    Unknown position is not empty position. Insufficient information yields
    REVIEW. Missing or malformed fields fail closed (BLOCK).
11. Every PR that changes code or prompts must update docs/ai-use-log.yaml
    in the same PR.