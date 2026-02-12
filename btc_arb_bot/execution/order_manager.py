"""Order orchestration, fill bookkeeping, and PnL accounting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from btc_arb_bot.data.polymarket_client import PolymarketClient
from btc_arb_bot.risk.risk_manager import PortfolioState


@dataclass
class Fill:
    side: str
    qty: float
    price: float
    tx_hash: str


@dataclass
class OrderManager:
    """Manages order lifecycle and portfolio updates."""

    client: PolymarketClient
    yes_token_id: int
    no_token_id: int
    fills: list[Fill] = field(default_factory=list)

    def submit_limit(self, side: str, qty: float, price: float) -> str:
        """Submit a limit buy order for YES or NO token and return tx hash."""

        token_id = self.yes_token_id if side == "YES" else self.no_token_id
        tx_hash = self.client.submit_limit_order(token_id=token_id, is_buy=True, price=price, size=qty)
        self.fills.append(Fill(side=side, qty=qty, price=price, tx_hash=tx_hash))
        return tx_hash

    def cancel(self, order_hash_hex: str) -> str:
        """Cancel a previously placed order."""

        return self.client.cancel_order(order_hash_hex)

    def apply_fill(self, state: PortfolioState, side: str, qty: float, price: float) -> None:
        """Apply a fill to portfolio state using weighted-average entry logic."""

        cost = qty * price
        state.cash_usd -= cost

        if side == "YES":
            new_qty = state.yes_qty + qty
            state.yes_avg_entry = (
                ((state.yes_avg_entry * state.yes_qty) + (price * qty)) / new_qty if new_qty > 0 else state.yes_avg_entry
            )
            state.yes_qty = new_qty
        else:
            new_qty = state.no_qty + qty
            state.no_avg_entry = (
                ((state.no_avg_entry * state.no_qty) + (price * qty)) / new_qty if new_qty > 0 else state.no_avg_entry
            )
            state.no_qty = new_qty

    def snapshot(self, state: PortfolioState, yes_mid: float, no_mid: float) -> dict[str, Any]:
        """Return current exposure and PnL snapshot."""

        mtm = state.mark_to_market(yes_mid=yes_mid, no_mid=no_mid)
        exposure = abs(state.yes_qty * yes_mid) + abs(state.no_qty * no_mid)
        unrealized = (state.yes_qty * (yes_mid - state.yes_avg_entry)) + (state.no_qty * (no_mid - state.no_avg_entry))
        return {
            "cash_usd": state.cash_usd,
            "yes_qty": state.yes_qty,
            "no_qty": state.no_qty,
            "yes_avg_entry": state.yes_avg_entry,
            "no_avg_entry": state.no_avg_entry,
            "exposure_usd": exposure,
            "unrealized_pnl": unrealized,
            "realized_pnl": state.realized_pnl,
            "equity": mtm,
        }
