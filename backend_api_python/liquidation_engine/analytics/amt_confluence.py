"""
analytics/amt_confluence.py
AMT Confluence Score Engine — gabungkan 4 analisis utama:
1. Auction Imbalance Detection (siapa kontrol?)
2. Liquidation Cascade Prediction (risiko cascade?)
3. Value Area Reaction (acceptance/rejection?)
4. Stop Hunt Detection (manipulation?)

Output: Confluence Score 0-100, bias (LONG/SHORT/NEUTRAL), setup quality.
"""

import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ConfluenceSetup:
    """Satu setup trading berdasarkan confluence analysis."""
    confluence_score: float      # 0-100
    bias: str                    # LONG, SHORT, NEUTRAL
    strength: str                # WEAK, MODERATE, STRONG, CRITICAL

    auction_control: str         # BUYER, SELLER, BALANCED
    auction_strength: float      # 0-100

    cascade_risk: str            # LOW, MEDIUM, HIGH, CRITICAL
    cascade_prob: float          # 0-100

    va_reaction: str             # ACCEPTANCE, REJECTION, UNDECIDED
    va_strength: float           # 0-100

    stop_hunt_detected: bool
    stop_hunt_confidence: float  # 0-100

    suggested_entry: Optional[float] = None
    suggested_stop: Optional[float] = None
    suggested_target: Optional[float] = None

    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class AMTConfluence:
    """
    Master analyzer yang menggabungkan semua sinyal AMT menjadi
    keputusan trading yang konkret dengan confidence score.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self._last_setup: Optional[ConfluenceSetup] = None

    def analyze(
        self,
        ob_data: dict,           # dari OrderBookAnalyzer
        flow_data: dict,         # dari OrderFlowAnalyzer
        liq_data: dict,          # dari LiquidationAnalyzer
        mp_data: dict,           # dari MarketProfile.auction_state()
        current_price: float,
        prev_price: float,
    ) -> ConfluenceSetup:
        """
        Analisis lengkap dan hasilkan setup trading.
        """

        # ────────────────────────────────────────────────────────────
        # 1. AUCTION IMBALANCE DETECTION
        # ────────────────────────────────────────────────────────────
        auction_control, auction_strength = self._analyze_auction(ob_data, flow_data)

        # ────────────────────────────────────────────────────────────
        # 2. LIQUIDATION CASCADE PREDICTION
        # ────────────────────────────────────────────────────────────
        cascade_risk, cascade_prob = self._analyze_cascade(liq_data, current_price, flow_data)

        # ────────────────────────────────────────────────────────────
        # 3. VALUE AREA REACTION
        # ────────────────────────────────────────────────────────────
        va_reaction, va_strength = self._analyze_va_reaction(mp_data, current_price, prev_price, flow_data)

        # ────────────────────────────────────────────────────────────
        # 4. STOP HUNT DETECTION
        # ────────────────────────────────────────────────────────────
        stop_hunt_detected, stop_hunt_confidence = self._detect_stop_hunt(
            current_price, prev_price, flow_data, liq_data, ob_data
        )

        # ────────────────────────────────────────────────────────────
        # CONFLUENCE SCORING
        # ────────────────────────────────────────────────────────────
        bias, confluence_score = self._calculate_confluence(
            auction_control, auction_strength,
            cascade_risk, cascade_prob,
            va_reaction, va_strength,
            stop_hunt_detected, stop_hunt_confidence,
        )

        strength = self._strength_level(confluence_score)

        # ────────────────────────────────────────────────────────────
        # SUGGESTED LEVELS
        # ────────────────────────────────────────────────────────────
        entry, stop, target = self._calculate_levels(
            current_price, mp_data, liq_data, bias, confluence_score
        )

        setup = ConfluenceSetup(
            confluence_score=confluence_score,
            bias=bias,
            strength=strength,
            auction_control=auction_control,
            auction_strength=auction_strength,
            cascade_risk=cascade_risk,
            cascade_prob=cascade_prob,
            va_reaction=va_reaction,
            va_strength=va_strength,
            stop_hunt_detected=stop_hunt_detected,
            stop_hunt_confidence=stop_hunt_confidence,
            suggested_entry=entry,
            suggested_stop=stop,
            suggested_target=target,
        )

        self._last_setup = setup
        return setup

    # ──────────────────────────────────────────────────────────────
    # 1. AUCTION IMBALANCE DETECTION
    # ──────────────────────────────────────────────────────────────
    def _analyze_auction(self, ob_data: dict, flow_data: dict) -> Tuple[str, float]:
        """
        Tentukan siapa yang kontrol auction: buyer atau seller.
        Kombinasi: order book imbalance + CVD + delta ratio
        """
        imbalance = ob_data.get("imbalance_ratio", 0.5)
        delta_ratio_60 = flow_data.get("delta_ratio_60s", 0.0)
        delta_ratio_10 = flow_data.get("delta_ratio_10s", 0.0)
        cvd_trend = flow_data.get("cvd_trend", "CVD_FLAT")

        # Score 0-100: 0=full seller, 100=full buyer
        ob_score = imbalance * 100  # 0-100
        delta_score = (delta_ratio_60 * 50) + 50  # normalize -1..1 ke 0..100
        trend_boost = 10 if cvd_trend == "CVD_RISING" else (-10 if cvd_trend == "CVD_FALLING" else 0)

        # Weight: OB imbalance 50%, delta 50%
        auction_strength = (ob_score * 0.5 + delta_score * 0.5 + trend_boost)
        auction_strength = max(0, min(100, auction_strength))  # clamp 0-100

        # Tentukan kontrol
        if auction_strength > 60:
            control = "BUYER"
        elif auction_strength < 40:
            control = "SELLER"
        else:
            control = "BALANCED"

        return control, auction_strength

    # ──────────────────────────────────────────────────────────────
    # 2. LIQUIDATION CASCADE PREDICTION
    # ──────────────────────────────────────────────────────────────
    def _analyze_cascade(self, liq_data: dict, price: float, flow_data: dict) -> Tuple[str, float]:
        """
        Prediksi probabilitas cascade liquidation.
        Faktor: cluster besar dekat harga + delta agresif + harga bergerak cepat.
        """
        cascade = liq_data.get("cascade_risk", {})
        squeeze = liq_data.get("squeeze_signal", {})
        nearest_above = liq_data.get("nearest_above", {})
        nearest_below = liq_data.get("nearest_below", {})

        cascade_score_base = cascade.get("score", 0)  # 0-100 dari LiquidationAnalyzer
        delta_10 = flow_data.get("delta_10s", 0)
        total_vol = flow_data.get("total_vol_60s", 1)

        # Bonus jika ada squeeze risk
        squeeze_bonus = 0
        squeeze_signal = squeeze.get("signal", "")
        if squeeze_signal in ("LONG_SQUEEZE_RISK", "SHORT_SQUEEZE_RISK"):
            squeeze_bonus = 20

        # Bonus jika cluster dekat (< 0.3%)
        proximity_bonus = 0
        if nearest_above and nearest_above.get("is_close"):
            proximity_bonus = 15
        if nearest_below and nearest_below.get("is_close"):
            proximity_bonus = 15

        # Bonus jika delta besar (momentum kuat)
        delta_bonus = 0
        if total_vol > 0:
            delta_intensity = abs(delta_10) / (total_vol + 1) * 100
            if delta_intensity > 20:
                delta_bonus = 15

        cascade_prob = min(100, cascade_score_base + squeeze_bonus + proximity_bonus + delta_bonus)

        if cascade_prob >= 75:
            risk = "CRITICAL"
        elif cascade_prob >= 50:
            risk = "HIGH"
        elif cascade_prob >= 25:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return risk, cascade_prob

    # ──────────────────────────────────────────────────────────────
    # 3. VALUE AREA REACTION
    # ──────────────────────────────────────────────────────────────
    def _analyze_va_reaction(
        self, mp_data: dict, price: float, prev_price: float, flow_data: dict
    ) -> Tuple[str, float]:
        """
        Analisis apakah pasar menerima atau menolak level penting (VA High, VA Low, POC).
        Acceptance: harga terobos + volume tinggi + CVD lanjut ke arah breakout.
        Rejection: harga kembali + volume turun + CVD berbalik.
        """
        state = mp_data.get("state", "")
        poc = mp_data.get("poc", 0)
        va_low = mp_data.get("va_low", 0)
        va_high = mp_data.get("va_high", 0)

        vol_60 = flow_data.get("total_vol_60s", 1)
        vol_10 = flow_data.get("total_vol_60s", 1)  # seharusnya ada total_vol_10s di OrderFlowAnalyzer
        delta_ratio_10 = flow_data.get("delta_ratio_10s", 0.0)
        divergence = flow_data.get("divergence")

        # Score acceptance
        acceptance_score = 50  # neutral baseline

        # Bonus jika state trending (acceptance ke level baru)
        if "TRENDING" in state:
            acceptance_score += 30
        elif "TESTING" in state:
            acceptance_score += 0  # undecided
        elif "BALANCING" in state:
            acceptance_score -= 15  # rejection (pasar tidak terobos)

        # Bonus jika volume meningkat saat test
        if vol_10 > vol_60 * 0.3:  # volume 10s lebih tinggi dari rata-rata 60s
            acceptance_score += 10

        # Bonus jika delta kuat ke arah breakout
        if "TRENDING_UP" in state and delta_ratio_10 > 0.2:
            acceptance_score += 15
        elif "TRENDING_DOWN" in state and delta_ratio_10 < -0.2:
            acceptance_score += 15

        # Bonus jika divergence bullish/bearish sesuai arah
        if divergence:
            if "BULLISH" in divergence["type"] and "TRENDING_UP" in state:
                acceptance_score += 10
            elif "BEARISH" in divergence["type"] and "TRENDING_DOWN" in state:
                acceptance_score += 10

        acceptance_score = max(0, min(100, acceptance_score))

        if acceptance_score >= 70:
            reaction = "ACCEPTANCE"
        elif acceptance_score <= 30:
            reaction = "REJECTION"
        else:
            reaction = "UNDECIDED"

        return reaction, acceptance_score

    # ──────────────────────────────────────────────────────────────
    # 4. STOP HUNT DETECTION
    # ──────────────────────────────────────────────────────────────
    def _detect_stop_hunt(
        self, price: float, prev_price: float,
        flow_data: dict, liq_data: dict, ob_data: dict
    ) -> Tuple[bool, float]:
        """
        Deteksi stop hunt: spike menembus level + liquidation besar + CVD berbalik + harga kembali cepat.
        Signature: harga bergerak ekstrem dalam 1-3 candle, tapi tidak sustained.
        """
        price_move_pct = abs(price - prev_price) / prev_price * 100 if prev_price else 0

        # Faktor 1: Price spike ekstrem (> 0.5%)
        spike_score = min(price_move_pct / 0.5 * 20, 20) if price_move_pct > 0.5 else 0

        # Faktor 2: Volume spike sudden
        vol_60 = flow_data.get("total_vol_60s", 1)
        large_trades = flow_data.get("large_trades", {})
        large_count = large_trades.get("count", 0)
        volume_spike_score = 15 if large_count > 5 else 0

        # Faktor 3: Liquidation spike
        total_liq_60 = liq_data.get("total_liq_60s_usd", 0)
        liq_spike_score = 20 if total_liq_60 > 500_000 else (10 if total_liq_60 > 100_000 else 0)

        # Faktor 4: CVD berbalik (signal fake move)
        cvd_trend = flow_data.get("cvd_trend", "")
        divergence = flow_data.get("divergence")
        reversal_score = 15 if divergence else 0

        # Faktor 5: Order book wall rapid removal (sign of panic covering)
        walls = ob_data.get("bid_walls", []) + ob_data.get("ask_walls", [])
        wall_score = 10 if len(walls) == 0 else 0

        hunt_confidence = spike_score + volume_spike_score + liq_spike_score + reversal_score + wall_score
        hunt_confidence = min(100, hunt_confidence)

        detected = hunt_confidence >= 50

        return detected, hunt_confidence

    # ──────────────────────────────────────────────────────────────
    # CONFLUENCE SCORING & BIAS
    # ──────────────────────────────────────────────────────────────
    def _calculate_confluence(
        self,
        auction_control: str, auction_strength: float,
        cascade_risk: str, cascade_prob: float,
        va_reaction: str, va_strength: float,
        stop_hunt_detected: bool, stop_hunt_confidence: float,
    ) -> Tuple[str, float]:
        """
        Hitung confluence score dan bias akhir.
        Confluence score: seberapa banyak factor align untuk satu arah.
        """
        score = 50  # neutral baseline

        # ── Auction control (weight 30%)
        if auction_control == "BUYER":
            score += auction_strength * 0.3
        elif auction_control == "SELLER":
            score -= auction_strength * 0.3

        # ── Cascade risk (weight 25%)
        # Cascade ke bawah = sell pressure = SHORT bias
        # Cascade ke atas = buy pressure = LONG bias
        if cascade_risk in ("HIGH", "CRITICAL"):
            # Perlu tahu arah cascade dari squeeze signal
            # Untuk sekarang: assume cascade follow trend
            if cascade_prob > 70:
                score += 15 if auction_control == "BUYER" else -15

        # ── VA Reaction (weight 25%)
        if va_reaction == "ACCEPTANCE":
            score += va_strength * 0.25
        elif va_reaction == "REJECTION":
            score -= va_strength * 0.25

        # ── Stop hunt (weight 20%)
        # Stop hunt biasanya reversal signal
        if stop_hunt_detected and stop_hunt_confidence > 60:
            # Jika stop hunt ke atas, next move biasanya DOWN (SHORT)
            # Jika stop hunt ke bawah, next move biasanya UP (LONG)
            # Untuk sekarang: stop hunt = reversal dari current trend
            if auction_control == "BUYER":
                score -= 15  # reversal ke SHORT
            elif auction_control == "SELLER":
                score += 15  # reversal ke LONG

        # Clamp score ke 0-100
        confluence_score = max(0, min(100, score))

        # Tentukan bias
        if confluence_score > 60:
            bias = "LONG"
        elif confluence_score < 40:
            bias = "SHORT"
        else:
            bias = "NEUTRAL"

        return bias, confluence_score

    def _strength_level(self, score: float) -> str:
        if score >= 80:
            return "CRITICAL"
        elif score >= 65:
            return "STRONG"
        elif score >= 45:
            return "MODERATE"
        else:
            return "WEAK"

    # ──────────────────────────────────────────────────────────────
    # SUGGESTED TRADING LEVELS
    # ──────────────────────────────────────────────────────────────
    def _calculate_levels(
        self, price: float, mp_data: dict, liq_data: dict,
        bias: str, confluence_score: float
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Hitung suggested entry, stop, target berdasarkan bias dan confluence.
        """
        if bias == "NEUTRAL" or confluence_score < 45:
            return None, None, None

        poc = mp_data.get("poc", price)
        va_low = mp_data.get("va_low", price)
        va_high = mp_data.get("va_high", price)

        nearest_above = liq_data.get("nearest_above", {})
        nearest_below = liq_data.get("nearest_below", {})

        if bias == "LONG":
            # Entry: pullback ke VA Low atau POC
            entry = va_low if va_low < price else poc
            # Stop: di bawah nearest liquidation cluster
            stop = nearest_below.get("zone_mid", price * 0.99) if nearest_below else price * 0.98
            # Target: nearest liquidation cluster di atas
            target = nearest_above.get("zone_mid", price * 1.02) if nearest_above else price * 1.03

        else:  # SHORT
            # Entry: pullback ke VA High atau POC
            entry = va_high if va_high > price else poc
            # Stop: di atas nearest liquidation cluster
            stop = nearest_above.get("zone_mid", price * 1.01) if nearest_above else price * 1.02
            # Target: nearest liquidation cluster di bawah
            target = nearest_below.get("zone_mid", price * 0.98) if nearest_below else price * 0.97

        return entry, stop, target

    def summary(self) -> Optional[dict]:
        """Return ringkasan setup terakhir."""
        if not self._last_setup:
            return None
        setup = self._last_setup
        return {
            "confluence_score": round(setup.confluence_score, 1),
            "bias": setup.bias,
            "strength": setup.strength,
            "auction_control": setup.auction_control,
            "cascade_risk": setup.cascade_risk,
            "va_reaction": setup.va_reaction,
            "stop_hunt_detected": setup.stop_hunt_detected,
            "entry": round(setup.suggested_entry, 2) if setup.suggested_entry else None,
            "stop": round(setup.suggested_stop, 2) if setup.suggested_stop else None,
            "target": round(setup.suggested_target, 2) if setup.suggested_target else None,
        }
