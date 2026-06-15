"""
streams/bybit_ws.py
WebSocket client untuk Bybit Linear Perpetual (USDT).
Subscribe: order book, trade, liquidation, open interest
"""

import asyncio
import json
import logging
import time
from typing import Callable, Optional

import websockets

logger = logging.getLogger(__name__)

BYBIT_WS_URL = "wss://stream.bybit.com/v5/public/linear"


class BybitWebSocket:
    """
    Handles Bybit Linear Perpetual WebSocket streams.
    Bybit menggunakan single connection dengan subscribe/unsubscribe messages.
    """

    def __init__(
        self,
        symbol: str,
        on_orderbook: Optional[Callable] = None,
        on_trade: Optional[Callable] = None,
        on_liquidation: Optional[Callable] = None,
        on_open_interest: Optional[Callable] = None,
        depth_level: int = 200,   # 1, 50, atau 200
    ):
        self.symbol = symbol.upper()
        self.on_orderbook = on_orderbook
        self.on_trade = on_trade
        self.on_liquidation = on_liquidation
        self.on_open_interest = on_open_interest
        self.depth_level = depth_level

        self._running = False
        self._ws = None
        self._orderbook_snapshot: dict = {"bids": {}, "asks": {}}

    def _subscribe_message(self) -> str:
        """Bybit subscribe payload."""
        topics = [
            f"orderbook.{self.depth_level}.{self.symbol}",
            f"publicTrade.{self.symbol}",
            f"liquidation.{self.symbol}",
            f"tickers.{self.symbol}",   # berisi OI real-time
        ]
        return json.dumps({
            "op": "subscribe",
            "args": topics,
        })

    async def _handle_message(self, raw: str):
        try:
            msg = json.loads(raw)

            # Abaikan ping/pong dan subscribe confirmation
            if msg.get("op") in ("ping", "pong", "subscribe"):
                return

            topic = msg.get("topic", "")

            if topic.startswith("orderbook"):
                await self._process_orderbook(msg)
            elif topic.startswith("publicTrade"):
                await self._process_trade(msg)
            elif topic.startswith("liquidation"):
                await self._process_liquidation(msg)
            elif topic.startswith("tickers"):
                await self._process_ticker(msg)

        except Exception as e:
            logger.error(f"[Bybit] Error handling message: {e}")

    async def _process_orderbook(self, msg: dict):
        """
        Bybit order book format:
        type = 'snapshot' (full) atau 'delta' (incremental)
        data.b = bids [[price, qty], ...]
        data.a = asks [[price, qty], ...]
        """
        if not self.on_orderbook:
            return

        data = msg.get("data", {})
        msg_type = msg.get("type", "delta")

        bids = data.get("b", [])
        asks = data.get("a", [])

        # Maintain local snapshot untuk Bybit (delta updates)
        if msg_type == "snapshot":
            self._orderbook_snapshot["bids"] = {p: q for p, q in bids}
            self._orderbook_snapshot["asks"] = {p: q for p, q in asks}
        else:
            # Apply delta
            for price, qty in bids:
                if float(qty) == 0:
                    self._orderbook_snapshot["bids"].pop(price, None)
                else:
                    self._orderbook_snapshot["bids"][price] = qty
            for price, qty in asks:
                if float(qty) == 0:
                    self._orderbook_snapshot["asks"].pop(price, None)
                else:
                    self._orderbook_snapshot["asks"][price] = qty

        parsed = {
            "exchange": "bybit",
            "symbol": self.symbol,
            "bids": list(self._orderbook_snapshot["bids"].items()),
            "asks": list(self._orderbook_snapshot["asks"].items()),
            "update_id": data.get("u", 0),
            "timestamp": msg.get("ts", time.time() * 1000) / 1000,
            "type": msg_type,
        }
        await self._safe_callback(self.on_orderbook, parsed)

    async def _process_trade(self, msg: dict):
        """
        Bybit trade format:
        data = list of trades
        {T: timestamp, s: symbol, S: side (Buy/Sell), p: price, v: qty, L: tickDir}
        """
        if not self.on_trade:
            return

        for trade in msg.get("data", []):
            parsed = {
                "exchange": "bybit",
                "symbol": trade.get("s", "").upper(),
                "price": float(trade.get("p", 0)),
                "qty": float(trade.get("v", 0)),
                "side": trade.get("S", "Buy").lower(),
                "timestamp": trade.get("T", time.time() * 1000) / 1000,
                "is_liquidation": False,
            }
            await self._safe_callback(self.on_trade, parsed)

    async def _process_liquidation(self, msg: dict):
        """
        Bybit liquidation format:
        data = {
          symbol, side (Buy/Sell), price, size, updatedTime
        }
        side Buy  = short diliquidasi
        side Sell = long diliquidasi
        """
        if not self.on_liquidation:
            return

        data = msg.get("data", {})
        price = float(data.get("price", 0))
        qty = float(data.get("size", 0))

        parsed = {
            "exchange": "bybit",
            "symbol": data.get("symbol", "").upper(),
            "side": data.get("side", "Buy").lower(),
            "price": price,
            "qty": qty,
            "value_usd": price * qty,
            "timestamp": data.get("updatedTime", time.time() * 1000) / 1000,
        }
        await self._safe_callback(self.on_liquidation, parsed)

    async def _process_ticker(self, msg: dict):
        """
        Bybit ticker berisi Open Interest real-time.
        data = {openInterest: "value", lastPrice: "value", ...}
        """
        if not self.on_open_interest:
            return

        data = msg.get("data", {})
        oi = data.get("openInterest")
        price = data.get("lastPrice")

        if oi and price:
            parsed = {
                "exchange": "bybit",
                "symbol": self.symbol,
                "open_interest": float(oi),
                "price": float(price),
                "timestamp": msg.get("ts", time.time() * 1000) / 1000,
            }
            await self._safe_callback(self.on_open_interest, parsed)

    async def _safe_callback(self, cb: Callable, data: dict):
        try:
            if asyncio.iscoroutinefunction(cb):
                await cb(data)
            else:
                cb(data)
        except Exception as e:
            logger.error(f"[Bybit] Callback error: {e}")

    async def _heartbeat(self):
        """Kirim ping setiap 20 detik agar koneksi tetap aktif."""
        while self._running:
            await asyncio.sleep(20)
            if self._ws:
                try:
                    await self._ws.send(json.dumps({"op": "ping"}))
                except Exception:
                    pass

    async def connect(self):
        """Mulai koneksi WebSocket dengan auto-reconnect."""
        self._running = True
        reconnect_delay = 1

        while self._running:
            try:
                logger.info(f"[Bybit] Connecting — {self.symbol}")
                async with websockets.connect(
                    BYBIT_WS_URL,
                    ping_interval=None,   # kita handle sendiri via heartbeat
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    reconnect_delay = 1
                    logger.info(f"[Bybit] Connected — {self.symbol}")

                    # Subscribe ke semua topics
                    await ws.send(self._subscribe_message())

                    # Jalankan heartbeat bersamaan
                    heartbeat_task = asyncio.create_task(self._heartbeat())

                    try:
                        async for message in ws:
                            if not self._running:
                                break
                            await self._handle_message(message)
                    finally:
                        heartbeat_task.cancel()

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"[Bybit] Connection closed: {e}. Reconnecting in {reconnect_delay}s...")
            except Exception as e:
                logger.error(f"[Bybit] Connection error: {e}. Reconnecting in {reconnect_delay}s...")

            if self._running:
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)

    async def disconnect(self):
        """Hentikan koneksi."""
        self._running = False
        if self._ws:
            await self._ws.close()
        logger.info(f"[Bybit] Disconnected — {self.symbol}")
