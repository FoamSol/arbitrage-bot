"""Application configuration for the BTC arbitrage bot."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Config:
    """Strongly-typed runtime configuration loaded from environment variables."""

    binance_api_key: str
    binance_api_secret: str
    coinbase_api_key: str
    coinbase_api_secret: str
    coinbase_passphrase: str

    polymarket_api_base: str
    polymarket_market_slug: str
    polymarket_token_id_yes: str
    polymarket_token_id_no: str

    polygon_rpc_url: str
    polygon_private_key: str
    polygon_chain_id: int
    clob_exchange_address: str
    clob_contract_abi_path: str

    edge_threshold: float
    check_interval_seconds: int
    max_notional_per_trade_usd: float
    max_total_exposure_usd: float
    max_drawdown_pct: float
    kelly_fraction: float

    annualized_volatility: float
    strike_price: float
    expiry_days: float

    log_file: str
    backtest_fee_bps: float


    @classmethod
    def from_env(cls) -> "Config":
        """Create a configuration object from process environment variables."""

        abi_path = os.getenv("CLOB_CONTRACT_ABI_PATH", "btc_arb_bot/data/clob_exchange_abi.json")
        if not Path(abi_path).exists():
            raise FileNotFoundError(
                f"CLOB contract ABI file not found: {abi_path}. "
                "Set CLOB_CONTRACT_ABI_PATH to a valid JSON ABI file."
            )

        return cls(
            binance_api_key=os.getenv("BINANCE_API_KEY", ""),
            binance_api_secret=os.getenv("BINANCE_API_SECRET", ""),
            coinbase_api_key=os.getenv("COINBASE_API_KEY", ""),
            coinbase_api_secret=os.getenv("COINBASE_API_SECRET", ""),
            coinbase_passphrase=os.getenv("COINBASE_PASSPHRASE", ""),
            polymarket_api_base=os.getenv("POLYMARKET_API_BASE", "https://clob.polymarket.com"),
            polymarket_market_slug=os.getenv("POLYMARKET_MARKET_SLUG", "btc-above-strike"),
            polymarket_token_id_yes=os.getenv("POLYMARKET_TOKEN_ID_YES", ""),
            polymarket_token_id_no=os.getenv("POLYMARKET_TOKEN_ID_NO", ""),
            polygon_rpc_url=os.getenv("POLYGON_RPC_URL", ""),
            polygon_private_key=os.getenv("POLYGON_PRIVATE_KEY", ""),
            polygon_chain_id=int(os.getenv("POLYGON_CHAIN_ID", "137")),
            clob_exchange_address=os.getenv("CLOB_EXCHANGE_ADDRESS", ""),
            clob_contract_abi_path=abi_path,
            edge_threshold=float(os.getenv("EDGE_THRESHOLD", "0.03")),
            check_interval_seconds=int(os.getenv("CHECK_INTERVAL_SECONDS", "60")),
            max_notional_per_trade_usd=float(os.getenv("MAX_NOTIONAL_PER_TRADE_USD", "500")),
            max_total_exposure_usd=float(os.getenv("MAX_TOTAL_EXPOSURE_USD", "3000")),
            max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.20")),
            kelly_fraction=float(os.getenv("KELLY_FRACTION", "0.5")),
            annualized_volatility=float(os.getenv("ANNUALIZED_VOLATILITY", "0.65")),
            strike_price=float(os.getenv("STRIKE_PRICE", "90000")),
            expiry_days=float(os.getenv("EXPIRY_DAYS", "7")),
            log_file=os.getenv("LOG_FILE", "logs/btc_arb_bot.log"),
            backtest_fee_bps=float(os.getenv("BACKTEST_FEE_BPS", "8")),
        )
