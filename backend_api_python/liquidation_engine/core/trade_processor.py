"""
core/trade_processor.py
Memproses real-time trade stream untuk menghitung:
- Delta (buy vol - sell vol)
- Cumulative Volume Delta (CVD)
- VWAP
- Trade absorption detection
"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Deque


@dataclass
class Trade:
    """Representasi satu transaksi."""
    symbol: str
    exchange: str
    price: float
    qty: float
    side: str          # 'buy' atau 'sell'
    timestamp: float   # unix seconds
    is_liquidation: bool = False


@dataclass
class TradeWindow:
    """Statistik agregat dalam window waktu tertentu."""
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    buy_count: int = 0
    sell_count: int = 0
    vwap_num: float = 0.0   # sum(price * qty)
    vwap_den: float = 0.0   # sum(qty)
    high: float = 0.0
    low: float = float('inf')

    @property
    def delta(self) -> float:
        return self.buy_volume - self.sell_volume

    @property
    def total_volume(self) -> float:
        return self.buy_volume + self.sell_volume

    @property
    def vwap(self) -> Optional[float]:
        if self.vwap_den == 0:
            return None
        return self.vwap_num / self.vwap_den

    @property
    def delta_ratio(self) -> float:
        """Rasio delta: +1.0 = semua beli, -1.0 = semua jual."""
        if self.total_volume == 0:
            return 0.0
        return self.delta / self.total_volume


class TradeProcessor:
    """
    Proses aliran trade secara real-time.
    Menyimpan window 60 detik terakhir untuk analisis rolling.
    """

    def __init__(self, symbol: str, exchange: str, window_seconds: int = 60):
        self.symbol = symbol
        self.exchange = exchange
        self.window_seconds = window_seconds

        # Rolling buffer trade (deque dengan maxlen mencegah memory overflow)
        self.trades: Deque[Trade] = deque(maxlen=10000)

        # Cumulative Volume Delta (CVD) sejak awal session
        self.cvd: float = 0.0

        # Total volume sejak awal
        self.total_buy: float = 0.0
        self.total_sell: float = 0.0

        # Absorpsi: track harga yang tidak bergerak meski ada volume besar
        self._absorption_buffer: Deque[Trade] = deque(maxlen=500)
        self._last_price: float = 0.0
        self._price_stable_vol: float = 0.0

    def add_trade(self, price: float, qty: float, side: str,
                  timestamp: float = None, is_liquidation: bool = False) -> Trade:
        """Tambah satu trade ke processor."""
        ts = timestamp or time.time()
        trade = Trade(
            symbol=self.symbol,
            exchange=self.exchange,
            price=price,
            qty=qty,
            side=side.lower(),
            timestamp=ts,
            is_liquidation=is_liquidation,
        )
        self.trades.append(trade)
        self._absorption_buffer.append(trade)

        # Update CVD
        if side.lower() == 'buy':
            self.cvd += qty
            self.total_buy += qty
        else:
            self.cvd -= qty
            self.total_sell += qty

        # Track pergerakan harga untuk absorpsi
        if self._last_price == 0:
            self._last_price = price

        price_move = abs(price - self._last_price)
        if price_move < price * 0.0001:  # harga hampir tidak bergerak (< 0.01%)
            self._price_stable_vol += qty
        else:
            self._price_stable_vol = 0.0
            self._last_price = price

        return trade

    def get_window(self, seconds: int = None) -> TradeWindow:
        """Hitung statistik untuk window N detik terakhir."""
        secs = seconds or self.window_seconds
        cutoff = time.time() - secs
        window = TradeWindow()

        for trade in reversed(self.trades):
            if trade.timestamp < cutoff:
                break
            if trade.side == 'buy':
                window.buy_volume += trade.qty
                window.buy_count += 1
            else:
                window.sell_volume += trade.qty
                window.sell_count += 1

            window.vwap_num += trade.price * trade.qty
            window.vwap_den += trade.qty
            window.high = max(window.high, trade.price)
            window.low = min(window.low, trade.price)

        if window.low == float('inf'):
            window.low = 0.0

        return window

    def detect_absorption(self, vol_threshold: float = 100.0) -> dict:
        """
        Deteksi absorpsi: volume besar masuk tapi harga tidak bergerak.
        Ini sinyal bahwa ada pihak kuat yang menyerap order (accumulation/distribution).
        vol_threshold: minimum volume yang dianggap 'besar' (dalam base currency)
        """
        absorbed = self._price_stable_vol >= vol_threshold
        window = self.get_window(10)  # 10 detik terakhir

        return {
            "absorbed": absorbed,
            "stable_volume": round(self._price_stable_vol, 4),
            "delta_10s": round(window.delta, 4),
            "delta_ratio_10s": round(window.delta_ratio, 4),
            "interpretation": (
                "BUYER ABSORPTION — seller diserap kuat"
                if absorbed and window.delta > 0
                else "SELLER ABSORPTION — buyer diserap kuat"
                if absorbed and window.delta < 0
                else "Normal flow"
            ),
        }

    def large_trades(self, min_qty: float = 10.0, seconds: int = 60) -> List[Trade]:
        """Return daftar trade besar dalam window waktu."""
        cutoff = time.time() - seconds
        return [t for t in self.trades if t.qty >= min_qty and t.timestamp >= cutoff]

    def liquidation_trades(self, seconds: int = 60) -> List[Trade]:
        """Return trade yang berasal dari liquidation event."""
        cutoff = time.time() - seconds
        return [t for t in self.trades if t.is_liquidation and t.timestamp >= cutoff]

    def summary(self) -> dict:
        w60 = self.get_window(60)
        w10 = self.get_window(10)
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "cvd": round(self.cvd, 4),
            "delta_60s": round(w60.delta, 4),
            "delta_ratio_60s": round(w60.delta_ratio, 4),
            "delta_10s": round(w10.delta, 4),
            "vwap_60s": round(w60.vwap, 2) if w60.vwap else None,
            "buy_vol_60s": round(w60.buy_volume, 4),
            "sell_vol_60s": round(w60.sell_volume, 4),
            "total_vol_60s": round(w60.total_volume, 4),
        }
