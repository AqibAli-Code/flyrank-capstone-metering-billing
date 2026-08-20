from app.pricing.config import calculate_token_cost, PRICING


def test_zero_usage_costs_zero():
    usage = {"input": 0, "cached_input": 0, "output": 0, "reasoning": 0}
    assert calculate_token_cost(usage) == 0


def test_cached_input_cheaper_than_fresh_input():
    fresh = calculate_token_cost({"input": 1000, "cached_input": 0, "output": 0, "reasoning": 0})
    cached = calculate_token_cost({"input": 0, "cached_input": 1000, "output": 0, "reasoning": 0})
    assert cached < fresh


def test_reasoning_tokens_bill_at_output_rate():
    only_output = calculate_token_cost({"input": 0, "cached_input": 0, "output": 500, "reasoning": 0})
    only_reasoning = calculate_token_cost({"input": 0, "cached_input": 0, "output": 0, "reasoning": 500})
    assert only_output == only_reasoning == 500 * PRICING["output_per_token"]


def test_categories_are_not_simply_summed_before_pricing():
    input_heavy = calculate_token_cost({"input": 1000, "cached_input": 0, "output": 0, "reasoning": 0})
    output_heavy = calculate_token_cost({"input": 0, "cached_input": 0, "output": 1000, "reasoning": 0})
    assert input_heavy != output_heavy


def test_exact_pinned_total():
    usage = {"input": 500, "cached_input": 200, "output": 300, "reasoning": 50}
    assert calculate_token_cost(usage) == 15900


def test_missing_keys_default_to_zero():
    assert calculate_token_cost({"input": 100}) == 1000
    assert calculate_token_cost({}) == 0

