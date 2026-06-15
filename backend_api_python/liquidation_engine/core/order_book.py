"""
core/order_book.py
Maintains real-time order book state dari WebSocket stream.
Supports Binance dan Bybit format.
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


class OrderBook:
    """
    Maintains sorted order book snapshot + incremental updates.
    Menyimpan bid/ask sebagai dict {price: quantity}.
    """

    def __init__(self, symbol: str, exchange: str, depth: int = 200):
        self.symbol = symbol
        self.exchange = exchange
        self.depth = depth

        # {float(price): float(qty)} — qty=0 berarti hapus level
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}

        self.last_update_id: int = 0
        self.timestamp: float = 0.0
        self.is_ready: bool = False  # True setelah snapshot pertama diterima

    # ------------------------------------------------------------------
    # Snapshot (data awal penuh dari REST atau snapshot WebSocket)
    # ------------------------------------------------------------------
    def apply_snapshot(self, bids: List[List], asks: List[List], update_id: int = 0):
        """
        Terapkan snapshot penuh. Format list: [[price, qty], ...]
        """
        self.bids = {float(p): float(q) for p, q in bids if float(q) > 0}
        self.asks = {float(p): float(q) for p, q in asks if float(q) > 0}
        self.last_update_id = update_id
        self.timestamp = time.time()
        self.is_ready = True

    # ------------------------------------------------------------------
    # Incremental update (delta dari WebSocket)
    # ------------------------------------------------------------------
    def apply_update(self, bids: List[List], asks: List[List], update_id: int = 0):
        """
        Terapkan delta update. qty=0 berarti hapus level tersebut.
        """
        if not self.is_ready:
            return

        for price, qty in bids:
            p, q = float(price), float(qty)
            if q == 0:
                self.bids.pop(p, None)
            else:
                self.bids[p] = q

        for price, qty in asks:
            p, q = float(price), float(qty)
            if q == 0:
                self.asks.pop(p, None)
            else:
                self.asks[p] = q

        self.last_update_id = update_id
        self.timestamp = time.time()

        # Trim ke depth maksimum agar memory tidak membengkak
        self._trim()

    def _trim(self):
        if len(self.bids) > self.depth:
            sorted_bids = sorted(self.bids.keys(), reverse=True)
            for p in sorted_bids[self.depth:]:
                del self.bids[p]

        if len(self.asks) > self.depth:
            sorted_asks = sorted(self.asks.keys())
            for p in sorted_asks[self.depth:]:
                del self.asks[p]

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def best_bid(self) -> Optional[Tuple[float, float]]:
        if not self.bids:
            return None
        p = max(self.bids)
        return (p, self.bids[p])

    def best_ask(self) -> Optional[Tuple[float, float]]:
        if not self.asks:
            return None
        p = min(self.asks)
        return (p, self.asks[p])

    def mid_price(self) -> Optional[float]:
        bb = self.best_bid()
        ba = self.best_ask()
        if bb and ba:
            return (bb[0] + ba[0]) / 2
        return None

    def spread(self) -> Optional[float]:
        bb = self.best_bid()
        ba = self.best_ask()
        if bb and ba:
            return ba[0] - bb[0]
        return None

    def sorted_bids(self, n: int = 50) -> List[Tuple[float, float]]:
        """Return top-n bids sorted descending by price."""
        return sorted(self.bids.items(), key=lambda x: -x[0])[:n]

    def sorted_asks(self, n: int = 50) -> List[Tuple[float, float]]:
        """Return top-n asks sorted ascending by price."""
        return sorted(self.asks.items(), key=lambda x: x[0])[:n]

    def total_bid_volume(self, levels: int = 20) -> float:
        return sum(q for _, q in self.sorted_bids(levels))

    def total_ask_volume(self, levels: int = 20) -> float:
        return sum(q for _, q in self.sorted_asks(levels))

    def imbalance_ratio(self, levels: int = 20) -> float:
        """
        Rasio imbalance order book.
        > 0.6  = bid dominan (tekanan beli)
        < 0.4  = ask dominan (tekanan jual)
        ~ 0.5  = balance
        """
        bid_vol = self.total_bid_volume(levels)
        ask_vol = self.total_ask_volume(levels)
        total = bid_vol + ask_vol
        if total == 0:
            return 0.5
        return bid_vol / total

    def find_walls(self, multiplier: float = 5.0, levels: int = 50) -> Dict:
        """
        Deteksi 'wall' — level dengan qty jauh di atas rata-rata.
        multiplier: berapa kali rata-rata untuk dianggap wall.
        """
        bid_data = self.sorted_bids(levels)
        ask_data = self.sorted_asks(levels)

        def detect(data):
            if not data:
                return []
            avg = sum(q for _, q in data) / len(data)
            threshold = avg * multiplier
            return [(p, q) for p, q in data if q >= threshold]

        return {
            "bid_walls": detect(bid_data),
            "ask_walls": detect(ask_data),
        }

    def __repr__(self):
        bb = self.best_bid()
        ba = self.best_ask()
        return (
            f"OrderBook({self.exchange}:{self.symbol} | "
            f"bid={bb[0] if bb else 'N/A'} ask={ba[0] if ba else 'N/A'} | "
            f"ready={self.is_ready})"
        )
