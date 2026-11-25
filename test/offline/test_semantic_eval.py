"""Keyword-scoring semantic-eval gate (GOV-002).

Replays the bull, bear, and research_manager nodes with a fake LLM and scores each
rendered prompt against a fixed evaluation set defined in this file. No YAML or
separate config: ``EVAL_SET`` is the whole eval definition.

Scoring (per case):
  score = sum(weight of each required phrase present) / sum(all required weights)
  if any forbidden phrase appears, the score is 0.
A case fails only when ``score < threshold``. This is advisory in CI
(``continue-on-error``): it reports, it does not block.

GOV-002 in every docstring. Network only in the real-model case; stdlib + the package only.
"""

from __future__ import annotations

import os
import re

import pytest

from tradingagents.agents.managers.research_manager import create_research_manager
from tradingagents.agents.researchers.bear_researcher import create_bear_researcher
from tradingagents.agents.researchers.bull_researcher import create_bull_researcher
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.llm_clients.api_key_env import get_api_key_env
from tradingagents.llm_clients.factory import create_llm_client

# The whole fixed evaluation set. Each role: required phrase -> weight, forbidden
# phrases, and the threshold the weighted score must reach to pass.
EVAL_SET = {
    "bull": {
        "required": {
            "growth": 2.0,
            "evidence": 1.0,
            "counter": 1.0,
            "counterpoints": 1.0,
        },
        "forbidden": ["sell everything", "ignore the risks"],
        "threshold": 0.5,
    },
    "bear": {
        "required": {
            "risk": 2.0,
            "evidence": 1.0,
            "counter": 1.0,
            "counterpoints": 1.0,
        },
        "forbidden": ["guaranteed profit", "ignore the risks"],
        "threshold": 0.5,
    },
    "research_manager": {
        "required": {
            "recommendation": 2.0,
            "rationale": 1.0,
            "strategic actions": 1.0,
        },
        "forbidden": ["ignore the evidence"],
        "threshold": 0.5,
    },
}


class FakeLLM:
    """Records the exact prompt sent; returns a canned reply.

    ``with_structured_output`` raises so the research manager uses its free-text
    path, matching ``tests/test_prompt_integrity.py``'s fake LLM.
    """

    def __init__(self, reply="argument"):
        self._reply = reply
        self.prompts: list[str] = []

    def invoke(self, prompt, *args, **kwargs):
        self.prompts.append(prompt if isinstance(prompt, str) else str(prompt))
        from langchain_core.messages import AIMessage

        return AIMessage(self._reply)

    def with_structured_output(self, *args, **kwargs):
        raise NotImplementedError


def _state() -> dict:
    """The fixed eval state, mirroring tests/test_prompt_integrity.py."""
    return {
        "company_of_interest": "NVDA",
        "trade_date": "2026-08-14",
        "asset_type": "stock",
        "instrument_context": "",
        "portfolio_context": "",
        "past_context": "",
        "market_report": "RSI 61, price 178.",
        "sentiment_report": "",
        "news_report": "",
        "fundamentals_report": "",
        "investment_plan": "P",
        "trader_investment_plan": "T",
        "investment_debate_state": {
            "bull_history": "",
            "bear_history": "",
            "history": "",
            "current_response": "",
            "count": 0,
        },
        "risk_debate_state": {
            "history": "",
            "latest_speaker": "",
            "count": 0,
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
        },
    }


def _render(factory) -> str:
    """Run one node with a fake LLM; return the rendered prompt it sent."""
    llm = FakeLLM()
    factory(llm, on_prompt=[].append)(_state())
    assert llm.prompts, "the node did not invoke the model"
    return llm.prompts[0]


def score(prompt: str, case: dict) -> float:
    """GOV-002: weighted keyword score in [0, 1]; a forbidden hit forces 0."""
    lowered = prompt.lower()
    if any(phrase.lower() in lowered for phrase in case["forbidden"]):
        return 0.0
    required = case["required"]
    total = sum(required.values())
    if total <= 0:
        return 0.0
    matched = sum(weight for phrase, weight in required.items() if phrase.lower() in lowered)
    return matched / total


FACTORIES = {
    "bull": create_bull_researcher,
    "bear": create_bear_researcher,
    "research_manager": create_research_manager,
}


@pytest.mark.parametrize("role", list(EVAL_SET))
def test_rendered_prompt_meets_threshold(role):
    """GOV-002: the rendered prompt scores at least the case threshold."""
    prompt = _render(FACTORIES[role])
    case = EVAL_SET[role]
    value = score(prompt, case)
    assert value >= case["threshold"], f"{role} scored {value:.2f} < {case['threshold']}"


def test_broken_prompt_scores_below_threshold():
    """GOV-002 negative: a prompt missing the required phrases fails its case."""
    case = EVAL_SET["bull"]
    broken = "A generic note about the market with none of the expected terms."
    assert score(broken, case) < case["threshold"]


def test_forbidden_phrase_scores_zero():
    """GOV-002 negative: any forbidden phrase collapses the score to 0."""
    case = EVAL_SET["research_manager"]
    prompt = "Recommendation: Buy. Rationale: strong. Strategic actions: add. ignore the evidence"
    assert "ignore the evidence" in prompt.lower()
    assert score(prompt, case) == 0.0


# --- One real-model semantic case (skipped when no API key) -------------------
#
# Self-contained: provider/model come from DEFAULT_CONFIG, the state is the same
# fixed ``_state()``, the expected answer and rubric are written here. This makes
# a real call to the configured provider, then asks the same model to judge its
# own research plan against the expected answer on a 0-5 scale. Skipped when the
# provider's API-key env var is unset, so it never fails a keyless run.

SEMANTIC_CASE = {
    "provider": DEFAULT_CONFIG["llm_provider"],
    "model": DEFAULT_CONFIG["deep_think_llm"],
    # The fixed state's debate history is empty; the Research Manager only sees the
    # debate (not the analyst reports), so the correct answer is a Hold taken on
    # thin evidence, not a directional call. That is the answer a good model gives.
    "expected_answer": (
        "Recommendation: Hold. Rationale: the debate history is empty, so there is "
        "no bull or bear case to weigh and the evidence is too thin to justify a "
        "directional rating; do not manufacture a Buy or Sell direction."
    ),
    "rubric": (
        "A correct answer (a) gives one recommendation from the rating scale, "
        "(b) explains the rationale is thin or absent debate/evidence, and "
        "(c) does not manufacture a directional call (Buy/Overweight or "
        "Underweight/Sell) from no arguments."
    ),
    "threshold": 3,
}


def _first_integer(text: str) -> int:
    matches = re.findall(r"\d+", text)
    return int(matches[-1]) if matches else 0


@pytest.mark.skipif(
    get_api_key_env(DEFAULT_CONFIG["llm_provider"]) is None
    or not os.environ.get(get_api_key_env(DEFAULT_CONFIG["llm_provider"])),
    reason="no API key for the configured provider; real-model case skipped",
)
def test_real_model_research_plan_scores_on_rubric():
    """GOV-002: the real model's research plan scores >= 3 against the rubric.

    Skips when the provider's API key is absent (never reads .env). Otherwise it
    calls the configured model to produce an investment plan, then asks the same
    model to judge it against the expected answer on a 0-5 scale.
    """
    env_var = get_api_key_env(SEMANTIC_CASE["provider"])
    if env_var is None or not os.environ.get(env_var):
        pytest.skip(f"no API key for provider {SEMANTIC_CASE['provider']!r} ({env_var})")

    client = create_llm_client(
        SEMANTIC_CASE["provider"],
        SEMANTIC_CASE["model"],
        DEFAULT_CONFIG.get("backend_url"),
    )
    llm = client.get_llm()

    output = create_research_manager(llm)(_state())["investment_plan"]

    judge_prompt = (
        "You are grading a research plan against an expected answer.\n\n"
        f"Expected answer:\n{SEMANTIC_CASE['expected_answer']}\n\n"
        f"Candidate output:\n{output}\n\n"
        f"Rubric:\n{SEMANTIC_CASE['rubric']}\n\n"
        "Score 0-5, 5 means same meaning, 0 means contradicts, "
        "reply with ONLY one integer."
    )
    reply = llm.invoke(judge_prompt)
    reply_text = reply if isinstance(reply, str) else getattr(reply, "content", str(reply))
    judge_score = _first_integer(reply_text)

    assert judge_score >= SEMANTIC_CASE["threshold"], (
        f"judge score {judge_score} < {SEMANTIC_CASE['threshold']}; candidate:\n{output}"
    )
