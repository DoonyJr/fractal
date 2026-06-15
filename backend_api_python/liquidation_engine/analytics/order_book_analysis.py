"""
analytics/order_book_analysis.py
Analisis order book untuk deteksi:
- Imbalance (tekanan beli vs jual)
- Wall detection (order besar di level tertentu)
- Iceberg detection (order tersembunyi yang terus diisi ulang)
"""

import time
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional
from core.order_book import OrderBook


class IcebergDetector:
    """
    Mendeteksi iceberg order dengan melacak level harga yang
    terus-menerus diisi ulang setelah tereksekusi.

    Logika:
    - Jika qty di level X berkurang (ada trade) tapi kemudian muncul lagi
      dengan size serupa berulang kali → kemungkinan iceberg order
    """

    def __init__(self, refill_threshold: int = 3, window_seconds: int = 60):
        self.refill_threshold = refill_threshold  # min berapa kali refill untuk dianggap iceberg
        self.window_seconds = window_seconds

        # {price: deque of (qty, timestamp)} — track history qty per level
        self._bid_history: Dict[float, deque] = defaultdict(lambda: deque(maxlen=20))
        self._ask_history: Dict[float, deque] = defaultdict(lambda: deque(maxlen=20))

        self._prev_bids: Dict[float, float] = {}
        self._prev_asks: Dict[float, float] = {}

    def update(self, orderbook: OrderBook):
        """Feed order book snapshot terbaru ke detector."""
        current_bids = dict(orderbook.bids)
        current_asks = dict(orderbook.asks)
        now = time.time()

        # Deteksi refill pada bid side
        for price, qty in current_bids.items():
            prev_qty = self._prev_bids.get(price, 0)
            if prev_qty > 0 and qty > prev_qty * 0.8:
                # Qty naik kembali setelah turun → kemungkinan refill
                self._bid_history[price].append((qty, now))

        # Deteksi refill pada ask side
        for price, qty in current_asks.items():
            prev_qty = self._prev_asks.get(price, 0)
            if prev_qty > 0 and qty > prev_qty * 0.8:
                self._ask_history[price].append((qty, now))

        self._prev_bids = current_bids
        self._prev_asks = current_asks

    def get_icebergs(self) -> Dict:
        """Return level yang terdeteksi sebagai iceberg."""
        cutoff = time.time() - self.window_seconds
        bid_icebergs = []
        ask_icebergs = []

        for price, history in self._bid_history.items():
            recent = [(q, t) for q, t in history if t >= cutoff]
            if len(recent) >= self.refill_threshold:
                avg_qty = sum(q for q, _ in recent) / len(recent)
                bid_icebergs.append({
                    "price": price,
                    "side": "bid",
                    "refill_count": len(recent),
                    "avg_qty": round(avg_qty, 4),
                    "confidence": min(len(recent) / 10, 1.0),
                })

        for price, history in self._ask_history.items():
            recent = [(q, t) for q, t in history if t >= cutoff]
            if len(recent) >= self.refill_threshold:
                avg_qty = sum(q for q, _ in recent) / len(recent)
                ask_icebergs.append({
                    "price": price,
                    "side": "ask",
                    "refill_count": len(recent),
                    "avg_qty": round(avg_qty, 4),
                    "confidence": min(len(recent) / 10, 1.0),
                })

        return {
            "bid_icebergs": sorted(bid_icebergs, key=lambda x: -x["confidence"]),
            "ask_icebergs": sorted(ask_icebergs, key=lambda x: -x["confidence"]),
            "total_detected": len(bid_icebergs) + len(ask_icebergs),
        }


class OrderBookAnalyzer:
    """
    Analisis komprehensif order book:
    - Imbalance ratio
    - Wall detection
    - Iceberg detection
    - Bid/ask pressure scoring
    """

    def __init__(self, symbol: str, imbalance_levels: int = 20, wall_multiplier: float = 5.0):
        self.symbol = symbol
        self.imbalance_levels = imbalance_levels
        self.wall_multiplier = wall_multiplier

        self.iceberg_detector = IcebergDetector()

        # History imbalance untuk trend
        self._imbalance_history: deque = deque(maxlen=100)

    def analyze(self, orderbook: OrderBook) -> dict:
        """Jalankan semua analisis pada snapshot order book terbaru."""
        if not orderbook.is_ready:
            return {"ready": False}

        # Update iceberg detector
        self.iceberg_detector.update(orderbook)

        # Hitung metrik dasar
        imbalance = orderbook.imbalance_ratio(self.imbalance_levels)
        self._imbalance_history.append((imbalance, time.time()))

        walls = orderbook.find_walls(self.wall_multiplier)
        icebergs = self.iceberg_detector.get_icebergs()

        bid_vol = orderbook.total_bid_volume(self.imbalance_levels)
        ask_vol = orderbook.total_ask_volume(self.imbalance_levels)
        mid = orderbook.mid_price()
        spread = orderbook.spread()

        # Trend imbalance (apakah makin berat ke satu sisi)
        imbalance_trend = self._imbalance_trend()

        # Pressure interpretation
        pressure = self._interpret_pressure(imbalance, walls)

        return {
            "symbol": self.symbol,
            "mid_price": round(mid, 4) if mid else None,
            "spread": round(spread, 4) if spread else None,
            "imbalance_ratio": round(imbalance, 4),
            "imbalance_trend": imbalance_trend,
            "bid_volume": round(bid_vol, 4),
            "ask_volume": round(ask_vol, 4),
            "bid_walls": walls["bid_walls"],
            "ask_walls": walls["ask_walls"],
            "icebergs": icebergs,
            "pressure": pressure,
            "timestamp": time.time(),
        }

    def _imbalance_trend(self) -> str:
        """Apakah imbalance makin meningkat ke bid atau ask?"""
        if len(self._imbalance_history) < 10:
            return "NEUTRAL"
        recent = [x[0] for x in list(self._imbalance_history)[-10:]]
        older = [x[0] for x in list(self._imbalance_history)[-20:-10]]
        if not older:
            return "NEUTRAL"
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        diff = recent_avg - older_avg
        if diff > 0.05:
            return "INCREASING_BID_PRESSURE"
        elif diff < -0.05:
            return "INCREASING_ASK_PRESSURE"
        return "NEUTRAL"

    def _interpret_pressure(self, imbalance: float, walls: dict) -> dict:
        """Interpretasi tekanan pasar dari imbalance dan walls."""
        has_bid_wall = len(walls["bid_walls"]) > 0
        has_ask_wall = len(walls["ask_walls"]) > 0

        if imbalance > 0.65:
            signal = "STRONG_BID"
            desc = "Order book berat di sisi bid — tekanan beli dominan"
        elif imbalance < 0.35:
            signal = "STRONG_ASK"
            desc = "Order book berat di sisi ask — tekanan jual dominan"
        elif imbalance > 0.55:
            signal = "MILD_BID"
            desc = "Slight bid dominance"
        elif imbalance < 0.45:
            signal = "MILD_ASK"
            desc = "Slight ask dominance"
        else:
            signal = "BALANCED"
            desc = "Order book seimbang — market dalam kondisi auction"

        # Modifikasi berdasarkan wall
        if has_bid_wall and not has_ask_wall:
            desc += " | BID WALL terdeteksi — support kuat"
        elif has_ask_wall and not has_bid_wall:
            desc += " | ASK WALL terdeteksi — resistance kuat"
        elif has_bid_wall and has_ask_wall:
            desc += " | Kedua sisi ada wall — harga mungkin terjebak dalam range"

        return {"signal": signal, "description": desc}
