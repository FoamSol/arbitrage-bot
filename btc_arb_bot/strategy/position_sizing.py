"""Position sizing utilities based on fractional Kelly criterion."""

from __future__ import annotations


def fractional_kelly_size(
    bankroll_usd: float,
    win_probability: float,
    price: float,
    kelly_fraction: float,
    max_notional_usd: float,
) -> float:
    """Calculate bounded position size in contracts (1 contract ~= $1 payout)."""

    if bankroll_usd <= 0:
        return 0.0
    if not 0 < win_probability < 1:
        return 0.0
    if not 0 < price < 1:
        return 0.0

    b = (1 - price) / price
    q = 1 - win_probability
    kelly_f = ((b * win_probability) - q) / b
    kelly_f = max(kelly_f, 0.0) * max(min(kelly_fraction, 1.0), 0.0)

    notional = min(bankroll_usd * kelly_f, max_notional_usd)
    return notional / price if price > 0 else 0.0
