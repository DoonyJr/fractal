"""
analytics/order_flow.py
Agregasi dan analisis order flow dari multiple sources:
- Combined CVD (Cumulative Volume Delta) Binance + Bybit
- Delta divergence detection
- Large trade tracking
- Absorption confirmation
"""

import time
from collections import deque
from typing import Dict, List, Optional
from core.trade_processor import TradeProcessor, TradeWindow


class OrderFlowAnalyzer:
    """
    Mengagregasi order flow dari beberapa exchange dan
    menghasilkan sinyal berdasarkan analisis delta, CVD, dan absorpsi.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol

        # Satu TradeProcessor per exchange
        self.processors: Dict[str, TradeProcessor] = {}

        # History CVD gabungan untuk trend detection
        self._cvd_history: deque = deque(maxlen=500)
        self._last_cvd_snapshot: float = 0.0
        self._cvd_snapshot_interval: float = 5.0  # snapshot setiap 5 detik

    def get_or_create_processor(self, exchange: str) -> TradeProcessor:
        if exchange not in self.processors:
            self.processors[exchange] = TradeProcessor(
                symbol=self.symbol,
                exchange=exchange,
                window_seconds=300,
            )
        return self.processors[exchange]

    def add_trade(self, exchange: str, price: float, qty: float,
                  side: str, timestamp: float = None, is_liquidation: bool = False):
        """Tambah trade ke processor exchange yang sesuai."""
        proc = self.get_or_create_processor(exchange)
        proc.add_trade(price, qty, side, timestamp, is_liquidation)

        # Snapshot CVD setiap interval
        now = time.time()
        if now - self._last_cvd_snapshot >= self._cvd_snapshot_interval:
            combined_cvd = self.combined_cvd()
            self._cvd_history.append((combined_cvd, now))
            self._last_cvd_snapshot = now

    def combined_cvd(self) -> float:
        """CVD gabungan dari semua exchange."""
        return sum(p.cvd for p in self.processors.values())

    def combined_window(self, seconds: int = 60) -> TradeWindow:
        """Gabungkan TradeWindow dari semua exchange."""
        from core.trade_processor import TradeWindow
        combined = TradeWindow()
        for proc in self.processors.values():
            w = proc.get_window(seconds)
            combined.buy_volume += w.buy_volume
            combined.sell_volume += w.sell_volume
            combined.buy_count += w.buy_count
            combined.sell_count += w.sell_count
            combined.vwap_num += w.vwap_num
            combined.vwap_den += w.vwap_den
            combined.high = max(combined.high, w.high)
            if w.low > 0:
                combined.low = min(combined.low, w.low)
        return combined

    def cvd_trend(self, lookback: int = 10) -> str:
        """
        Tentukan arah tren CVD.
        Rising CVD = buyer lebih agresif (bullish)
        Falling CVD = seller lebih agresif (bearish)
        """
        if len(self._cvd_history) < lookback:
            return "INSUFFICIENT_DATA"

        recent = [x[0] for x in list(self._cvd_history)[-lookback:]]
        first_half = recent[:lookback // 2]
        second_half = recent[lookback // 2:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        diff = avg_second - avg_first

        if diff > 0:
            return "CVD_RISING"    # buyer makin agresif
        elif diff < 0:
            return "CVD_FALLING"   # seller makin agresif
        return "CVD_FLAT"

    def detect_divergence(self, current_price: float, prev_price: float) -> Optional[dict]:
        """
        Deteksi divergensi antara harga dan CVD.
        Bullish divergence: harga turun tapi CVD naik → potensi reversal naik
        Bearish divergence: harga naik tapi CVD turun → potensi reversal turun
        """
        if len(self._cvd_history) < 5:
            return None

        current_cvd = self.combined_cvd()
        old_cvd = self._cvd_history[-5][0] if len(self._cvd_history) >= 5 else current_cvd

        price_up = current_price > prev_price
        cvd_up = current_cvd > old_cvd

        if not price_up and cvd_up:
            return {
                "type": "BULLISH_DIVERGENCE",
                "description": "Harga turun tapi CVD naik — buyer menyerap tekanan jual, potensi reversal UP",
                "price_delta": round(current_price - prev_price, 4),
                "cvd_delta": round(current_cvd - old_cvd, 4),
            }
        elif price_up and not cvd_up:
            return {
                "type": "BEARISH_DIVERGENCE",
                "description": "Harga naik tapi CVD turun — kenaikan tidak didukung buyer, potensi reversal DOWN",
                "price_delta": round(current_price - prev_price, 4),
                "cvd_delta": round(current_cvd - old_cvd, 4),
            }
        return None

    def large_trades_summary(self, min_qty: float = 5.0, seconds: int = 60) -> dict:
        """Ringkasan large trades dari semua exchange."""
        all_large = []
        for proc in self.processors.values():
            all_large.extend(proc.large_trades(min_qty, seconds))

        buy_large = sum(t.qty * t.price for t in all_large if t.side == 'buy')
        sell_large = sum(t.qty * t.price for t in all_large if t.side == 'sell')

        return {
            "count": len(all_large),
            "buy_value_usd": round(buy_large, 2),
            "sell_value_usd": round(sell_large, 2),
            "dominance": "BUYER" if buy_large > sell_large else "SELLER",
        }

    def absorption_check(self, vol_threshold: float = 50.0) -> dict:
        """Cek absorpsi dari semua exchange."""
        results = {}
        for exchange, proc in self.processors.items():
            results[exchange] = proc.detect_absorption(vol_threshold)
        absorbed = any(r["absorbed"] for r in results.values())
        return {"any_absorbed": absorbed, "per_exchange": results}

    def summary(self, current_price: float = 0.0, prev_price: float = 0.0) -> dict:
        """Ringkasan lengkap order flow analysis."""
        w60 = self.combined_window(60)
        w10 = self.combined_window(10)
        cvd_trend = self.cvd_trend()
        divergence = self.detect_divergence(current_price, prev_price) if current_price and prev_price else None
        large = self.large_trades_summary()
        absorption = self.absorption_check()

        return {
            "symbol": self.symbol,
            "combined_cvd": round(self.combined_cvd(), 4),
            "cvd_trend": cvd_trend,
            "delta_60s": round(w60.delta, 4),
            "delta_ratio_60s": round(w60.delta_ratio, 4),
            "delta_10s": round(w10.delta, 4),
            "delta_ratio_10s": round(w10.delta_ratio, 4),
            "vwap_60s": round(w60.vwap, 2) if w60.vwap else None,
            "total_vol_60s": round(w60.total_volume, 4),
            "divergence": divergence,
            "large_trades": large,
            "absorption": absorption,
        }
