"""Polymarket CLOB market data and on-chain execution client."""

from __future__ import annotations

import asyncio
import json
import secrets
from dataclasses import dataclass
from typing import Any

import aiohttp
from web3 import Web3


@dataclass
class OrderBookTop:
    """Top-of-book representation for YES and NO outcomes."""

    yes_bid: float
    yes_ask: float
    no_bid: float
    no_ask: float


class PolymarketClient:
    """Fetches Polymarket data and signs/sends CLOB contract transactions."""

    def __init__(
        self,
        api_base: str,
        token_id_yes: str,
        token_id_no: str,
        rpc_url: str,
        private_key: str,
        chain_id: int,
        exchange_address: str,
        contract_abi_path: str,
    ):
        self.api_base = api_base.rstrip("/")
        self.token_id_yes = token_id_yes
        self.token_id_no = token_id_no

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError("Unable to connect to Polygon RPC provider")

        self.account = self.w3.eth.account.from_key(private_key)
        self.chain_id = chain_id
        with open(contract_abi_path, "r", encoding="utf-8") as f:
            abi = json.load(f)
        self.exchange = self.w3.eth.contract(address=Web3.to_checksum_address(exchange_address), abi=abi)

    async def _fetch_book(self, session: aiohttp.ClientSession, token_id: str) -> dict[str, Any]:
        url = f"{self.api_base}/book"
        params = {"token_id": token_id}
        async with session.get(url, params=params, timeout=15) as resp:
            resp.raise_for_status()
            return await resp.json()

    @staticmethod
    def _top(book: dict[str, Any]) -> tuple[float, float]:
        bids = book.get("bids", [])
        asks = book.get("asks", [])
        best_bid = float(bids[0]["price"]) if bids else 0.0
        best_ask = float(asks[0]["price"]) if asks else 1.0
        return best_bid, best_ask

    async def fetch_orderbook_top(self) -> OrderBookTop:
        """Fetch best bid/ask prices for YES and NO order books."""

        async with aiohttp.ClientSession() as session:
            yes_book, no_book = await asyncio.gather(
                self._fetch_book(session, self.token_id_yes),
                self._fetch_book(session, self.token_id_no),
            )
        yes_bid, yes_ask = self._top(yes_book)
        no_bid, no_ask = self._top(no_book)
        return OrderBookTop(yes_bid=yes_bid, yes_ask=yes_ask, no_bid=no_bid, no_ask=no_ask)

    def submit_limit_order(self, token_id: int, is_buy: bool, price: float, size: float) -> str:
        """Sign and broadcast a placeLimitOrder transaction to the CLOB contract."""

        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = self.exchange.functions.placeLimitOrder(
            int(token_id),
            bool(is_buy),
            int(price * 1_000_000),
            int(size * 1_000_000),
            secrets.randbits(128),
        ).build_transaction(
            {
                "from": self.account.address,
                "nonce": nonce,
                "chainId": self.chain_id,
                "gas": 350000,
                "maxFeePerGas": self.w3.to_wei("60", "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei("35", "gwei"),
            }
        )

        signed = self.w3.eth.account.sign_transaction(tx, private_key=self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def cancel_order(self, order_hash_hex: str) -> str:
        """Cancel an existing order by sending a signed cancelOrder transaction."""

        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = self.exchange.functions.cancelOrder(bytes.fromhex(order_hash_hex.removeprefix("0x"))).build_transaction(
            {
                "from": self.account.address,
                "nonce": nonce,
                "chainId": self.chain_id,
                "gas": 180000,
                "maxFeePerGas": self.w3.to_wei("60", "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei("35", "gwei"),
            }
        )
        signed = self.w3.eth.account.sign_transaction(tx, private_key=self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()
