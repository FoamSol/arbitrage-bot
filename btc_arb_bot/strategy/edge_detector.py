"""Signal extraction from model probability versus Polymarket prices."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EdgeSignal:
    """Represents an actionable edge for YES or NO token."""

    side: str
    model_prob: float
    market_prob: float
    edge: float
    should_trade: bool


def detect_edge(model_probability: float, yes_ask: float, no_ask: float, threshold: float) -> EdgeSignal:
    """Return best edge opportunity between YES and NO with threshold gating."""

    yes_edge = model_probability - yes_ask
    no_model_prob = 1 - model_probability
    no_edge = no_model_prob - no_ask

    if yes_edge >= no_edge:
        edge = yes_edge
        return EdgeSignal(
            side="YES",
            model_prob=model_probability,
            market_prob=yes_ask,
            edge=edge,
            should_trade=edge >= threshold,
        )

    return EdgeSignal(
        side="NO",
        model_prob=no_model_prob,
        market_prob=no_ask,
        edge=no_edge,
        should_trade=no_edge >= threshold,
    )
