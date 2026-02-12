"""Black-Scholes style probability model utilities."""

from __future__ import annotations

import math

from scipy.stats import norm


def probability_finish_above_strike(spot: float, strike: float, sigma: float, time_to_expiry_years: float) -> float:
    """
    Estimate the risk-neutral probability that BTC will finish above strike.

    Formula:
        d = (ln(S/K) + (σ² / 2)T) / (σ√T)
        probability = N(d)
    """

    if spot <= 0 or strike <= 0:
        raise ValueError("Spot and strike must both be positive.")
    if sigma <= 0:
        raise ValueError("Sigma must be positive.")
    if time_to_expiry_years <= 0:
        raise ValueError("Time to expiry must be positive.")

    d = (math.log(spot / strike) + ((sigma**2) / 2.0) * time_to_expiry_years) / (sigma * math.sqrt(time_to_expiry_years))
    return float(norm.cdf(d))
