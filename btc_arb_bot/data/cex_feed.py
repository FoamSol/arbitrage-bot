"""CEX spot feed aggregation using ccxt."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import ccxt.async_support as ccxt


@dataclass
class SpotSnapshot:
    """CEX spot prices and aggregate value."""

    binance: float
    coinbase: float

    @property
    def mid(self) -> float:
        return (self.binance + self.coinbase) / 2


class CEXFeed:
    """Async BTC/USD spot aggregator for Binance and Coinbase."""

    def __init__(self, binance_key: str, binance_secret: str, coinbase_key: str, coinbase_secret: str):
        self.binance = ccxt.binance(
            {
                "apiKey": binance_key,
                "secret": binance_secret,
                "enableRateLimit": True,
            }
        )
        self.coinbase = ccxt.coinbase(
            {
                "apiKey": coinbase_key,
                "secret": coinbase_secret,
                "enableRateLimit": True,
            }
        )

    async def fetch_spot(self) -> SpotSnapshot:
        """Fetch the latest BTC/USDT and BTC/USD prices concurrently."""

        binance_ticker, coinbase_ticker = await asyncio.gather(
            self.binance.fetch_ticker("BTC/USDT"),
            self.coinbase.fetch_ticker("BTC/USD"),
        )
        return SpotSnapshot(binance=float(binance_ticker["last"]), coinbase=float(coinbase_ticker["last"]))

    async def close(self) -> None:
        """Close network sessions for both exchanges."""

        await asyncio.gather(self.binance.close(), self.coinbase.close())
