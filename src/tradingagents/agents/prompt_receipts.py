import hashlib


def legacy_prompt_observer(on_prompt, role, template, state):
    """Hash the exact static template used to render this legacy role."""
    if on_prompt is None:
        return None
    digest = hashlib.sha256(template.encode("utf-8")).hexdigest()

    def observe(prompt):
        on_prompt({"role": role, "run_id": state.get("run_id"),
                       "round_index": state["investment_debate_state"].get("round_index"),
                       "prompt_hashes": {"b." + role: digest},
                       "input_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest()})
    return observe
