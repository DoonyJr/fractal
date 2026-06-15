"""
core/oi_calculator.py
Menghitung Open Interest delta secara real-time.
OI naik + harga naik = long masuk (bullish confirmation)
OI turun + harga naik = short cover (kurang kuat)
OI naik + harga turun = short masuk (bearish confirmation)
OI turun + harga turun = long exit (kurang kuat)
"""

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional


@dataclass
class OISnapshot:
    open_interest: float
    price: float
    timestamp: float


class OICalculator:
    """
    Melacak perubahan Open Interest dan menginterpretasikannya
    dalam konteks pergerakan harga (AMT context).
    """

    def __init__(self, symbol: str, exchange: str, window_seconds: int = 300):
        self.symbol = symbol
        self.exchange = exchange
        self.window_seconds = window_seconds

        self.history: Deque[OISnapshot] = deque(maxlen=1000)
        self.current_oi: float = 0.0
        self.current_price: float = 0.0

    def update(self, open_interest: float, price: float, timestamp: float = None):
        """Tambah snapshot OI baru."""
        ts = timestamp or time.time()
        snap = OISnapshot(open_interest=open_interest, price=price, timestamp=ts)
        self.history.append(snap)
        self.current_oi = open_interest
        self.current_price = price

    def delta(self, seconds: int = 60) -> Optional[float]:
        """Perubahan OI dalam N detik terakhir."""
        cutoff = time.time() - seconds
        old = None
        for snap in self.history:
            if snap.timestamp >= cutoff:
                old = snap
                break
        if old is None or len(self.history) == 0:
            return None
        return self.current_oi - old.open_interest

    def delta_pct(self, seconds: int = 60) -> Optional[float]:
        """Perubahan OI dalam persen."""
        old_oi = None
        cutoff = time.time() - seconds
        for snap in self.history:
            if snap.timestamp >= cutoff:
                old_oi = snap.open_interest
                break
        if old_oi is None or old_oi == 0:
            return None
        return ((self.current_oi - old_oi) / old_oi) * 100

    def price_delta(self, seconds: int = 60) -> Optional[float]:
        """Perubahan harga dalam N detik terakhir."""
        cutoff = time.time() - seconds
        for snap in self.history:
            if snap.timestamp >= cutoff:
                return self.current_price - snap.price
        return None

    def interpret(self, seconds: int = 60) -> dict:
        """
        Interpretasi hubungan OI delta vs price delta.
        Sesuai AMT: menentukan apakah money baru masuk atau keluar.
        """
        oi_delta = self.delta(seconds)
        price_delta = self.price_delta(seconds)

        if oi_delta is None or price_delta is None:
            return {"signal": "INSUFFICIENT_DATA", "interpretation": "Data belum cukup"}

        oi_up = oi_delta > 0
        price_up = price_delta > 0

        if oi_up and price_up:
            signal = "LONG_BUILDUP"
            interpretation = "OI naik + harga naik → posisi long baru masuk (bullish)"
        elif oi_up and not price_up:
            signal = "SHORT_BUILDUP"
            interpretation = "OI naik + harga turun → posisi short baru masuk (bearish)"
        elif not oi_up and price_up:
            signal = "SHORT_COVERING"
            interpretation = "OI turun + harga naik → short cover, bukan buying baru (kurang kuat)"
        else:
            signal = "LONG_UNWINDING"
            interpretation = "OI turun + harga turun → long exit, bukan shorting baru (kurang kuat)"

        return {
            "signal": signal,
            "interpretation": interpretation,
            "oi_delta": round(oi_delta, 2),
            "oi_delta_pct": round(self.delta_pct(seconds) or 0, 4),
            "price_delta": round(price_delta, 4),
            "current_oi": round(self.current_oi, 2),
        }

    def summary(self) -> dict:
        interp = self.interpret(60)
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "current_oi": round(self.current_oi, 2),
            "oi_delta_60s": round(self.delta(60) or 0, 2),
            "oi_delta_pct_60s": round(self.delta_pct(60) or 0, 4),
            "signal": interp["signal"],
            "interpretation": interp["interpretation"],
        }
