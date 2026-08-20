"""
Pricing constants and cost calculation for AI token usage.

All amounts are integer micro-cents (1 cent = 10_000 micro-cents here — the exact
scale doesn't matter as long as it's consistent and never a float). Integer math
only, everywhere. Convert to display currency (e.g. dollars) only at the API edge,
never inside this module.
"""

PRICING = {
    "input_per_token": 10,          # fresh input tokens
    "cached_input_per_token": 2,    # cached input is cheaper than fresh input
    "output_per_token": 30,         # reasoning tokens are billed at this same rate
}


def calculate_token_cost(usage: dict) -> int:
    """
    usage = {"input": int, "cached_input": int, "output": int, "reasoning": int}

    Returns total cost in integer micro-cents.

    Pricing rules encoded here (the "gotchas" from the capstone brief):
      1. Cached input tokens are billed at a cheaper rate than fresh input tokens.
      2. Reasoning tokens are NOT a separate line item — they are billed at the
         output token rate.
      3. Token categories are never summed together before pricing; each category
         is priced individually at its own rate, then the totals are summed.
    """
    input_tokens = usage.get("input", 0)
    cached_tokens = usage.get("cached_input", 0)
    reasoning_tokens = usage.get("reasoning", 0)
    output_tokens = usage.get("output", 0) + reasoning_tokens  # rule 2

    cost = (
        input_tokens * PRICING["input_per_token"]
        + cached_tokens * PRICING["cached_input_per_token"]
        + output_tokens * PRICING["output_per_token"]
    )
    return cost