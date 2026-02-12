"""Risk constraints and portfolio accounting."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PortfolioState:
    cash_usd: float
    yes_qty: float = 0.0
    no_qty: float = 0.0
    yes_avg_entry: float = 0.0
    no_avg_entry: float = 0.0
    realized_pnl: float = 0.0
    peak_equity: float = 0.0

    def mark_to_market(self, yes_mid: float, no_mid: float) -> float:
        return self.cash_usd + self.yes_qty * yes_mid + self.no_qty * no_mid


class RiskManager:
    """Validates exposure and drawdown limits before order placement."""

    def __init__(self, max_exposure_usd: float, max_drawdown_pct: float):
        self.max_exposure_usd = max_exposure_usd
        self.max_drawdown_pct = max_drawdown_pct

    def update_peak(self, state: PortfolioState, yes_mid: float, no_mid: float) -> None:
        equity = state.mark_to_market(yes_mid, no_mid)
        if equity > state.peak_equity:
            state.peak_equity = equity

    def within_drawdown(self, state: PortfolioState, yes_mid: float, no_mid: float) -> bool:
        if state.peak_equity <= 0:
            return True
        equity = state.mark_to_market(yes_mid, no_mid)
        drawdown = (state.peak_equity - equity) / state.peak_equity
        return drawdown <= self.max_drawdown_pct

    def within_exposure(self, state: PortfolioState, add_notional_usd: float, yes_mid: float, no_mid: float) -> bool:
        current_exposure = abs(state.yes_qty * yes_mid) + abs(state.no_qty * no_mid)
        return (current_exposure + add_notional_usd) <= self.max_exposure_usd
