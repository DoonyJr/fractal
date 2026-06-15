"""
signals/signal_engine.py
Menghasilkan sinyal trading dari semua modul analitik.
Sinyal: LONG_SQUEEZE, SHORT_SQUEEZE, ABSORPTION, IMBALANCE, CASCADE_WARNING, POC_MAGNET
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from collections import deque


@dataclass
class Signal:
    """Satu sinyal yang dihasilkan engine."""
    signal_type: str        # jenis sinyal
    severity: str           # LOW, MEDIUM, HIGH, CRITICAL
    exchange: str
    symbol: str
    price: float
    description: str
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def age_seconds(self) -> float:
        return time.time() - self.timestamp


class SignalEngine:
    """
    Membaca output semua analitik dan menghasilkan sinyal actionable.
    Setiap sinyal diberi severity dan deskripsi yang jelas.
    """

    def __init__(self, symbol: str, max_signals: int = 100):
        self.symbol = symbol
        self.signal_history: deque = deque(maxlen=max_signals)
        self._last_signals: Dict[str, float] = {}  # cooldown per signal type
        self.cooldown_seconds: Dict[str, float] = {
            "LONG_SQUEEZE": 30.0,
            "SHORT_SQUEEZE": 30.0,
            "CASCADE_WARNING": 15.0,
            "ABSORPTION": 20.0,
            "IMBALANCE": 10.0,
            "POC_MAGNET": 60.0,
            "CVD_DIVERGENCE": 30.0,
            "OI_SIGNAL": 20.0,
            "ICEBERG_DETECTED": 45.0,
        }

    def _can_fire(self, signal_type: str) -> bool:
        """Cek apakah sinyal boleh difire (cooldown selesai)."""
        last = self._last_signals.get(signal_type, 0)
        cooldown = self.cooldown_seconds.get(signal_type, 10.0)
        return (time.time() - last) >= cooldown

    def _fire(self, signal_type: str, severity: str, exchange: str,
              price: float, description: str, data: dict = None) -> Optional[Signal]:
        if not self._can_fire(signal_type):
            return None
        sig = Signal(
            signal_type=signal_type,
            severity=severity,
            exchange=exchange,
            symbol=self.symbol,
            price=price,
            description=description,
            data=data or {},
        )
        self.signal_history.append(sig)
        self._last_signals[signal_type] = time.time()
        return sig

    # ------------------------------------------------------------------
    # Evaluasi setiap modul analitik
    # ------------------------------------------------------------------

    def evaluate_liquidation(self, liq_data: dict, exchange: str = "combined") -> List[Signal]:
        """Evaluasi data dari LiquidationAnalyzer."""
        signals = []
        price = liq_data.get("current_price", 0)

        # Cascade warning
        cascade = liq_data.get("cascade_risk", {})
        if cascade.get("level") in ("HIGH", "CRITICAL"):
            sig = self._fire(
                "CASCADE_WARNING",
                cascade["level"],
                exchange,
                price,
                f"CASCADE RISK {cascade['level']}: ${cascade.get('nearby_value_usd', 0):,.0f} "
                f"liquidation cluster dekat harga saat ini ({cascade.get('nearby_cluster_count', 0)} zona)",
                cascade,
            )
            if sig:
                signals.append(sig)

        # Squeeze signal
        squeeze = liq_data.get("squeeze_signal", {})
        squeeze_signal = squeeze.get("signal", "")
        if squeeze_signal == "SHORT_SQUEEZE_RISK":
            trapped = squeeze.get("trapped_shorts_above_usd", 0)
            severity = "HIGH" if trapped > 1_000_000 else "MEDIUM"
            sig = self._fire(
                "SHORT_SQUEEZE",
                severity,
                exchange,
                price,
                f"SHORT SQUEEZE RISK: ${trapped:,.0f} short terjebak di atas harga — "
                f"jika harga naik, liquidation berantai potensial",
                squeeze,
            )
            if sig:
                signals.append(sig)

        elif squeeze_signal == "LONG_SQUEEZE_RISK":
            trapped = squeeze.get("trapped_longs_below_usd", 0)
            severity = "HIGH" if trapped > 1_000_000 else "MEDIUM"
            sig = self._fire(
                "LONG_SQUEEZE",
                severity,
                exchange,
                price,
                f"LONG SQUEEZE RISK: ${trapped:,.0f} long terjebak di bawah harga — "
                f"jika harga turun, liquidation berantai potensial",
                squeeze,
            )
            if sig:
                signals.append(sig)

        return signals

    def evaluate_order_book(self, ob_data: dict, exchange: str) -> List[Signal]:
        """Evaluasi data dari OrderBookAnalyzer."""
        signals = []
        price = ob_data.get("mid_price", 0) or 0

        # Imbalance signal
        pressure = ob_data.get("pressure", {})
        pressure_signal = pressure.get("signal", "")
        if pressure_signal in ("STRONG_BID", "STRONG_ASK"):
            severity = "HIGH" if ob_data.get("imbalance_ratio", 0.5) > 0.75 or \
                                  ob_data.get("imbalance_ratio", 0.5) < 0.25 else "MEDIUM"
            sig = self._fire(
                "IMBALANCE",
                severity,
                exchange,
                price,
                f"ORDER BOOK IMBALANCE ({pressure_signal}): {pressure.get('description', '')}",
                ob_data,
            )
            if sig:
                signals.append(sig)

        # Iceberg signal
        icebergs = ob_data.get("icebergs", {})
        total_icebergs = icebergs.get("total_detected", 0)
        if total_icebergs > 0:
            sig = self._fire(
                "ICEBERG_DETECTED",
                "MEDIUM",
                exchange,
                price,
                f"ICEBERG ORDER TERDETEKSI: {total_icebergs} level harga menunjukkan "
                f"pola refill — ada order tersembunyi yang sedang bekerja",
                icebergs,
            )
            if sig:
                signals.append(sig)

        return signals

    def evaluate_order_flow(self, flow_data: dict, exchange: str = "combined") -> List[Signal]:
        """Evaluasi data dari OrderFlowAnalyzer."""
        signals = []
        price = flow_data.get("vwap_60s", 0) or 0

        # CVD divergence
        divergence = flow_data.get("divergence")
        if divergence:
            div_type = divergence.get("type", "")
            severity = "HIGH" if abs(divergence.get("cvd_delta", 0)) > 100 else "MEDIUM"
            sig = self._fire(
                "CVD_DIVERGENCE",
                severity,
                exchange,
                price,
                f"CVD DIVERGENCE ({div_type}): {divergence.get('description', '')}",
                divergence,
            )
            if sig:
                signals.append(sig)

        # Absorption
        absorption = flow_data.get("absorption", {})
        if absorption.get("any_absorbed"):
            sig = self._fire(
                "ABSORPTION",
                "MEDIUM",
                exchange,
                price,
                f"ABSORPTION TERDETEKSI: volume besar masuk tapi harga tidak bergerak — "
                f"ada pihak kuat yang menyerap order",
                absorption,
            )
            if sig:
                signals.append(sig)

        return signals

    def evaluate_market_profile(self, mp_data: dict, exchange: str = "combined") -> List[Signal]:
        """Evaluasi data dari MarketProfile.auction_state()."""
        signals = []
        price = mp_data.get("current_price", 0)
        poc = mp_data.get("poc", 0)
        state = mp_data.get("state", "")

        # POC Magnet — harga sangat dekat POC
        if poc and price:
            distance_pct = abs(price - poc) / price * 100
            if distance_pct < 0.1:  # dalam 0.1% dari POC
                sig = self._fire(
                    "POC_MAGNET",
                    "LOW",
                    exchange,
                    price,
                    f"POC MAGNET: Harga ({price}) sangat dekat POC ({poc}) — "
                    f"area keseimbangan kuat, tunggu breakout atau rejection",
                    mp_data,
                )
                if sig:
                    signals.append(sig)

        return signals

    def evaluate_oi(self, oi_data: dict, exchange: str) -> List[Signal]:
        """Evaluasi data dari OICalculator."""
        signals = []
        price = oi_data.get("current_price", 0) if hasattr(oi_data, 'get') else 0

        oi_signal = oi_data.get("signal", "")
        if oi_signal in ("LONG_BUILDUP", "SHORT_BUILDUP"):
            severity = "MEDIUM"
            if abs(oi_data.get("oi_delta_pct", 0)) > 2.0:
                severity = "HIGH"
            sig = self._fire(
                "OI_SIGNAL",
                severity,
                exchange,
                oi_data.get("current_oi", 0),
                f"OI SIGNAL ({oi_signal}): {oi_data.get('interpretation', '')} "
                f"(OI delta: {oi_data.get('oi_delta_pct', 0):.2f}%)",
                oi_data,
            )
            if sig:
                signals.append(sig)

        return signals

    def recent_signals(self, seconds: int = 300, min_severity: str = "LOW") -> List[Signal]:
        """Return sinyal terbaru dalam window waktu."""
        severity_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        min_level = severity_order.get(min_severity, 0)
        cutoff = time.time() - seconds
        return [
            s for s in self.signal_history
            if s.timestamp >= cutoff and severity_order.get(s.severity, 0) >= min_level
        ]

    def active_signals(self) -> List[Signal]:
        """Return semua sinyal dalam 60 detik terakhir."""
        return self.recent_signals(60)
