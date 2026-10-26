"""Price per million tokens (input, output) in USD, to turn token counts into a cost."""

from smart_extractor.providers import Usage

# Claude: first-party prices, prompts up to 100K tokens. Re-check the pricing page now and then.
_PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-fable-5-1": (10.00, 50.00),
    # Gemini, paid tier, prompts up to 200K tokens. gemini-3.8-flash doubles on 2027-01-01.
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.1-pro-preview": (2.00, 12.00),
}


def cost_usd(model: str, usage: Usage) -> float | None:
    """None for a model without a known price, so a report never shows a made-up cost."""
    if model not in _PRICES:
        return None
    price_in, price_out = _PRICES[model]
    return (usage.input_tokens * price_in + usage.output_tokens * price_out) / 1_000_000
