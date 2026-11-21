# Request to C: graph/state integration for the deterministic guard

Status: **INTEGRATION-PENDING**

Owner of this request: D  
Target owner: C (`src/tradingagents/agents/state.py`,
`src/tradingagents/graph/setup.py`, graph wiring)

## What is already done

The deterministic guard is wired inside
`src/tradingagents/agents/managers/portfolio_manager.py` only, behind the opt-in
signal `state["guard_enabled"] is True`. Both gates run there:

- Trader gate before the PM prompt/decision.
- Final PM gate after the PM decision, with the Trader-gate verdict as
  `prior_verdict`.

Guarded mode is fail-closed. Legacy mode without the flag keeps the upstream
Portfolio Manager behavior (ADR-005 compatibility addendum).

## What C must add

1. Declare these optional structured fields on `AgentState` (do not replace the
   existing rendered string fields):

   - `portfolio`: structured portfolio dict, or absent/`None` when no structured
     context was supplied. The PM node must not parse `portfolio_context`.
   - `trader_proposal`: structured proposal dict for the Trader gate.
   - `guard_enabled`: explicit boolean opt-in. Only `True` enables guard
     enforcement.

2. Populate the structured values at graph/run-state start from the same
   `PortfolioContext` and Trader proposal objects the run already uses. Do not
   derive them by parsing the rendered `portfolio_context` or
   `trader_investment_plan` strings.

3. Place or confirm the graph-level gate ordering. The current PM-node wiring
   validates at the PM node; graph-level gate placement after the Trader and
   after the final PM output remains C-owned and is not changed by D.

4. Enable `guard_enabled=True` only when the structured `portfolio` and
   `trader_proposal` are present; otherwise keep legacy mode explicitly rather
   than silently running an unvalidated guarded path.

## Verification for the integration

- `test/offline/test_guard_wiring.py` defines the guarded-mode contract.
- Full offline suite: 94 passed.
- Upstream suite: 1412 passed, 1 skipped, 1 deselected.
