"""Historical simulation engine for BTC/Polymarket arbitrage strategy."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from btc_arb_bot.models.probability import probability_finish_above_strike
from btc_arb_bot.risk.risk_manager import PortfolioState, RiskManager
from btc_arb_bot.strategy.edge_detector import detect_edge
from btc_arb_bot.strategy.position_sizing import fractional_kelly_size


@dataclass
class BacktestConfig:
    initial_cash: float
    strike: float
    sigma: float
    expiry_days: float
    edge_threshold: float
    kelly_fraction: float
    max_notional_usd: float
    max_exposure_usd: float
    max_drawdown_pct: float
    fee_bps: float


class Backtester:
    """Runs vectorized-ish event-loop simulation from CSV data."""

    def __init__(self, cfg: BacktestConfig):
        self.cfg = cfg

    def run(self, btc_csv: str, odds_csv: str) -> pd.DataFrame:
        """Load CSVs, simulate fills on top-of-book asks, and return equity curve."""

        btc = pd.read_csv(btc_csv, parse_dates=["timestamp"])
        odds = pd.read_csv(odds_csv, parse_dates=["timestamp"])

        merged = pd.merge_asof(
            btc.sort_values("timestamp"),
            odds.sort_values("timestamp"),
            on="timestamp",
            direction="nearest",
        )

        state = PortfolioState(cash_usd=self.cfg.initial_cash, peak_equity=self.cfg.initial_cash)
        risk = RiskManager(self.cfg.max_exposure_usd, self.cfg.max_drawdown_pct)
        rows: list[dict] = []

        for _, row in merged.iterrows():
            spot = float(row["btc_spot"])
            yes_ask = float(row["yes_ask"])
            no_ask = float(row["no_ask"])
            yes_mid = float(row.get("yes_mid", yes_ask))
            no_mid = float(row.get("no_mid", no_ask))

            t_years = max(self.cfg.expiry_days / 365.0, 1e-6)
            model_prob = probability_finish_above_strike(spot, self.cfg.strike, self.cfg.sigma, t_years)
            signal = detect_edge(model_prob, yes_ask=yes_ask, no_ask=no_ask, threshold=self.cfg.edge_threshold)

            risk.update_peak(state, yes_mid=yes_mid, no_mid=no_mid)
            if signal.should_trade and risk.within_drawdown(state, yes_mid=yes_mid, no_mid=no_mid):
                contracts = fractional_kelly_size(
                    bankroll_usd=state.cash_usd,
                    win_probability=signal.model_prob,
                    price=signal.market_prob,
                    kelly_fraction=self.cfg.kelly_fraction,
                    max_notional_usd=self.cfg.max_notional_usd,
                )
                notional = contracts * signal.market_prob
                if contracts > 0 and risk.within_exposure(state, notional, yes_mid=yes_mid, no_mid=no_mid):
                    fee = notional * (self.cfg.fee_bps / 10_000)
                    state.cash_usd -= fee
                    if signal.side == "YES":
                        new_qty = state.yes_qty + contracts
                        state.yes_avg_entry = (
                            ((state.yes_avg_entry * state.yes_qty) + (signal.market_prob * contracts)) / new_qty
                        )
                        state.yes_qty = new_qty
                    else:
                        new_qty = state.no_qty + contracts
                        state.no_avg_entry = ((state.no_avg_entry * state.no_qty) + (signal.market_prob * contracts)) / new_qty
                        state.no_qty = new_qty
                    state.cash_usd -= notional

            equity = state.mark_to_market(yes_mid=yes_mid, no_mid=no_mid)
            rows.append(
                {
                    "timestamp": row["timestamp"],
                    "equity": equity,
                    "cash_usd": state.cash_usd,
                    "yes_qty": state.yes_qty,
                    "no_qty": state.no_qty,
                    "model_prob": model_prob,
                    "signal_side": signal.side,
                    "signal_edge": signal.edge,
                }
            )

        return pd.DataFrame(rows)
