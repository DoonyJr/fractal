"""
streams/binance_ws.py
WebSocket client untuk Binance USDT-M Futures.
Subscribe: order book depth, aggTrade, forceOrder (liquidation)
"""

import asyncio
import json
import logging
import time
from typing import Callable, Optional

import websockets

logger = logging.getLogger(__name__)

BINANCE_WS_BASE = "wss://fstream.binance.com/stream"


class BinanceWebSocket:
    """
    Handles multiple Binance Futures WebSocket streams secara concurrent.
    Callback dipanggil setiap kali data baru diterima.
    """

    def __init__(
        self,
        symbol: str,
        on_orderbook: Optional[Callable] = None,
        on_trade: Optional[Callable] = None,
        on_liquidation: Optional[Callable] = None,
        depth_level: int = 20,          # 5, 10, atau 20
        depth_speed: str = "100ms",     # "100ms" atau "500ms"
    ):
        self.symbol = symbol.lower()
        self.on_orderbook = on_orderbook
        self.on_trade = on_trade
        self.on_liquidation = on_liquidation
        self.depth_level = depth_level
        self.depth_speed = depth_speed

        self._running = False
        self._ws = None

    def _build_url(self) -> str:
        """Bangun URL multi-stream Binance."""
        streams = [
            f"{self.symbol}@depth{self.depth_level}@{self.depth_speed}",
            f"{self.symbol}@aggTrade",
            f"{self.symbol}@forceOrder",
        ]
        stream_str = "/".join(streams)
        return f"{BINANCE_WS_BASE}?streams={stream_str}"

    async def _handle_message(self, raw: str):
        try:
            msg = json.loads(raw)
            stream = msg.get("stream", "")
            data = msg.get("data", msg)

            if "depth" in stream:
                await self._process_orderbook(data)
            elif "aggTrade" in stream:
                await self._process_trade(data)
            elif "forceOrder" in stream:
                await self._process_liquidation(data)

        except Exception as e:
            logger.error(f"[Binance] Error handling message: {e}")

    async def _process_orderbook(self, data: dict):
        """
        Format Binance depth update:
        {
          "e": "depthUpdate", "E": timestamp, "s": "BTCUSDT",
          "U": firstUpdateId, "u": finalUpdateId,
          "b": [[price, qty], ...],   # bids
          "a": [[price, qty], ...]    # asks
        }
        """
        if self.on_orderbook:
            parsed = {
                "exchange": "binance",
                "symbol": data.get("s", "").upper(),
                "bids": data.get("b", []),
                "asks": data.get("a", []),
                "update_id": data.get("u", 0),
                "timestamp": data.get("E", time.time() * 1000) / 1000,
            }
            await self._safe_callback(self.on_orderbook, parsed)

    async def _process_trade(self, data: dict):
        """
        Format Binance aggTrade:
        {
          "e": "aggTrade", "E": timestamp, "s": "BTCUSDT",
          "p": "price", "q": "qty",
          "m": true/false   # true = seller is market maker (sell trade)
        }
        """
        if self.on_trade:
            is_sell = data.get("m", False)  # maker = sell side
            parsed = {
                "exchange": "binance",
                "symbol": data.get("s", "").upper(),
                "price": float(data.get("p", 0)),
                "qty": float(data.get("q", 0)),
                "side": "sell" if is_sell else "buy",
                "timestamp": data.get("E", time.time() * 1000) / 1000,
                "is_liquidation": False,
            }
            await self._safe_callback(self.on_trade, parsed)

    async def _process_liquidation(self, data: dict):
        """
        Format Binance forceOrder:
        {
          "o": {
            "s": "BTCUSDT", "S": "SELL"/"BUY",
            "p": "price", "q": "qty",
            "T": timestamp
          }
        }
        side BUY  = short position diliquidasi (forced buy)
        side SELL = long position diliquidasi (forced sell)
        """
        if self.on_liquidation:
            order = data.get("o", {})
            parsed = {
                "exchange": "binance",
                "symbol": order.get("s", "").upper(),
                "side": order.get("S", "").lower(),
                "price": float(order.get("p", 0)),
                "qty": float(order.get("q", 0)),
                "value_usd": float(order.get("p", 0)) * float(order.get("q", 0)),
                "timestamp": order.get("T", time.time() * 1000) / 1000,
            }
            await self._safe_callback(self.on_liquidation, parsed)

    async def _safe_callback(self, cb: Callable, data: dict):
        try:
            if asyncio.iscoroutinefunction(cb):
                await cb(data)
            else:
                cb(data)
        except Exception as e:
            logger.error(f"[Binance] Callback error: {e}")

    async def connect(self):
        """Mulai koneksi WebSocket dengan auto-reconnect."""
        self._running = True
        url = self._build_url()
        reconnect_delay = 1

        while self._running:
            try:
                logger.info(f"[Binance] Connecting to {url}")
                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    reconnect_delay = 1  # reset delay setelah sukses connect
                    logger.info(f"[Binance] Connected — {self.symbol.upper()}")

                    async for message in ws:
                        if not self._running:
                            break
                        await self._handle_message(message)

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"[Binance] Connection closed: {e}. Reconnecting in {reconnect_delay}s...")
            except Exception as e:
                logger.error(f"[Binance] Connection error: {e}. Reconnecting in {reconnect_delay}s...")

            if self._running:
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)  # exponential backoff max 60s

    async def disconnect(self):
        """Hentikan koneksi."""
        self._running = False
        if self._ws:
            await self._ws.close()
        logger.info(f"[Binance] Disconnected — {self.symbol.upper()}")
