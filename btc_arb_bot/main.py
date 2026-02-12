"""Entry point for asynchronous BTC/Polymarket arbitrage bot."""

from __future__ import annotations

import asyncio
import signal
from dataclasses import asdict

from btc_arb_bot.config import Config
from btc_arb_bot.data.cex_feed import CEXFeed
from btc_arb_bot.data.polymarket_client import PolymarketClient
from btc_arb_bot.execution.order_manager import OrderManager
from btc_arb_bot.models.probability import probability_finish_above_strike
from btc_arb_bot.risk.risk_manager import PortfolioState, RiskManager
from btc_arb_bot.strategy.edge_detector import detect_edge
from btc_arb_bot.strategy.position_sizing import fractional_kelly_size
from btc_arb_bot.utils.logger import setup_logger


class ArbBot:
    """Coordinates data ingestion, signal generation, risk, and execution."""

    def __init__(self, config: Config):
        self.cfg = config
        self.logger = setup_logger(config.log_file)
        self.cex = CEXFeed(
            binance_key=config.binance_api_key,
            binance_secret=config.binance_api_secret,
            coinbase_key=config.coinbase_api_key,
            coinbase_secret=config.coinbase_api_secret,
        )
        self.polymarket = PolymarketClient(
            api_base=config.polymarket_api_base,
            token_id_yes=config.polymarket_token_id_yes,
            token_id_no=config.polymarket_token_id_no,
            rpc_url=config.polygon_rpc_url,
            private_key=config.polygon_private_key,
            chain_id=config.polygon_chain_id,
            exchange_address=config.clob_exchange_address,
            contract_abi_path=config.clob_contract_abi_path,
        )
        self.order_manager = OrderManager(
            client=self.polymarket,
            yes_token_id=int(config.polymarket_token_id_yes),
            no_token_id=int(config.polymarket_token_id_no),
        )
        self.risk = RiskManager(config.max_total_exposure_usd, config.max_drawdown_pct)
        self.portfolio = PortfolioState(cash_usd=10_000.0, peak_equity=10_000.0)
        self.running = True

    async def step(self) -> None:
        """Run one cycle of data pull, signal evaluation, and optional execution."""

        try:
            spot = await self.cex.fetch_spot()
            book = await self.polymarket.fetch_orderbook_top()

            t_years = max(self.cfg.expiry_days / 365.0, 1e-6)
            model_prob = probability_finish_above_strike(
                spot=spot.mid,
                strike=self.cfg.strike_price,
                sigma=self.cfg.annualized_volatility,
                time_to_expiry_years=t_years,
            )
            signal = detect_edge(
                model_probability=model_prob,
                yes_ask=book.yes_ask,
                no_ask=book.no_ask,
                threshold=self.cfg.edge_threshold,
            )

            yes_mid = (book.yes_bid + book.yes_ask) / 2
            no_mid = (book.no_bid + book.no_ask) / 2
            self.risk.update_peak(self.portfolio, yes_mid=yes_mid, no_mid=no_mid)

            if signal.should_trade and self.risk.within_drawdown(self.portfolio, yes_mid=yes_mid, no_mid=no_mid):
                contracts = fractional_kelly_size(
                    bankroll_usd=self.portfolio.cash_usd,
                    win_probability=signal.model_prob,
                    price=signal.market_prob,
                    kelly_fraction=self.cfg.kelly_fraction,
                    max_notional_usd=self.cfg.max_notional_per_trade_usd,
                )
                notional = contracts * signal.market_prob
                if contracts > 0 and self.risk.within_exposure(self.portfolio, notional, yes_mid=yes_mid, no_mid=no_mid):
                    tx_hash = self.order_manager.submit_limit(signal.side, contracts, signal.market_prob)
                    self.order_manager.apply_fill(self.portfolio, signal.side, contracts, signal.market_prob)
                    self.logger.info(
                        "order_submitted",
                        extra={
                            "event": {
                                "side": signal.side,
                                "contracts": contracts,
                                "price": signal.market_prob,
                                "edge": signal.edge,
                                "tx_hash": tx_hash,
                            }
                        },
                    )

            snapshot = self.order_manager.snapshot(self.portfolio, yes_mid=yes_mid, no_mid=no_mid)
            self.logger.info(
                "cycle_complete",
                extra={
                    "event": {
                        "spot": asdict(spot),
                        "book": asdict(book),
                        "model_prob": model_prob,
                        "signal": asdict(signal),
                        "portfolio": snapshot,
                    }
                },
            )

        except Exception:
            self.logger.exception("error_in_cycle")

    async def run(self) -> None:
        """Main scheduling loop; checks opportunities every configured interval."""

        self.logger.info("arb_bot_started")
        while self.running:
            await self.step()
            await asyncio.sleep(self.cfg.check_interval_seconds)

    async def shutdown(self) -> None:
        """Gracefully close resources."""

        self.running = False
        await self.cex.close()
        self.logger.info("arb_bot_shutdown")


def _install_signal_handlers(bot: ArbBot) -> None:
    loop = asyncio.get_event_loop()

    def stop() -> None:
        asyncio.create_task(bot.shutdown())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop)


async def _main() -> None:
    cfg = Config.from_env()
    bot = ArbBot(cfg)
    _install_signal_handlers(bot)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(_main())
