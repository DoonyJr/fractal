"""
analytics/bookmap_stats.py
Statistik gaya Bookmap dari data Binance Futures (order book L2 + aggTrade).
Mengubah visualisasi Bookmap menjadi angka terukur yang siap dipakai sebagai indikator AMT.

5 statistik:
  1. Liquidity Heatmap Persistence  — dwell time level likuiditas besar
  2. Absorption Ratio                — volume tereksekusi vs pergerakan harga
  3. Liquidity Depletion Speed       — laju depth dimakan per detik
  4. Iceberg Refill Rate             — berapa kali level diisi ulang
  5. Delta vs Heatmap Divergence     — CVD agresif tapi diserap wall pasif

CATATAN KEJUJURAN DATA (Binance L2, resolusi ~100ms, agregat per level):
  - accurate : Absorption Ratio, Depletion Speed, Delta/Heatmap Divergence
  - estimate : Heatmap Persistence (presisi ~100ms), Iceberg Refill (inferensi,
               tidak ada order-id; refill < 100ms bisa terlewat)
  Setiap metrik membawa field "confidence" agar pemakai tahu seberapa jauh
  angka itu bisa dipercaya.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from core.order_book import OrderBook
from core.trade_processor import TradeProcessor
from config import get_config, BookmapConfig


# Confidence label per metrik — jujur soal keterbatasan data Binance L2
CONFIDENCE = {
    "persistence": "estimate",   # presisi terbatas pada interval update ~100ms
    "absorption": "accurate",    # aggTrade + price move, full support
    "depletion": "accurate",     # delta depth antar-snapshot
    "iceberg": "estimate",       # inferensi pola refill, tanpa order-id
    "divergence": "accurate",    # CVD + posisi wall
}


@dataclass
class LevelTracker:
    """Melacak satu level harga likuiditas besar dari waktu ke waktu."""
    price: float
    side: str                       # 'bid' atau 'ask'
    first_seen: float               # timestamp pertama terlihat sebagai wall
    last_seen: float                # timestamp terakhir masih ada
    peak_qty: float                 # qty terbesar yang pernah tercatat
    refill_count: int = 0           # berapa kali diisi ulang setelah berkurang
    last_qty: float = 0.0

    @property
    def dwell_seconds(self) -> float:
        return self.last_seen - self.first_seen


class BookmapStats:
    """
    Menghitung 5 statistik Bookmap dari satu OrderBook + satu TradeProcessor
    (umumnya sumber Binance). Panggil update() tiap cycle, lalu snapshot()
    untuk membaca hasil.
    """

    def __init__(
        self,
        symbol: str,
        config: Optional[BookmapConfig] = None,
    ):
        self.symbol = symbol
        # Threshold dibaca dari config per-coin (fallback ke DEFAULT bila tak terdaftar)
        self.cfg = config or get_config(symbol)
        self.wall_multiplier = self.cfg.wall_multiplier
        self.track_levels = self.cfg.track_levels
        self.persistence_window = self.cfg.persistence_window

        # Pelacak level likuiditas besar: key=(side, price)
        self._levels: Dict[Tuple[str, float], LevelTracker] = {}

        # Snapshot depth sebelumnya untuk depletion speed
        self._prev_bid_depth: Optional[float] = None
        self._prev_ask_depth: Optional[float] = None
        self._prev_depth_ts: Optional[float] = None
        self._depletion_history: deque = deque(maxlen=50)  # (bid_rate, ask_rate, ts)

        # Untuk absorption: jejak harga saat update terakhir
        self._prev_mid: Optional[float] = None

    # ------------------------------------------------------------------
    # UPDATE — dipanggil tiap cycle dengan order book + trade terbaru
    # ------------------------------------------------------------------
    def update(self, ob: OrderBook, tp: TradeProcessor):
        if not ob.is_ready:
            return
        now = time.time()
        self._update_levels(ob, now)
        self._update_depletion(ob, now)
        self._prev_mid = ob.mid_price()
        self._prune(now)

    def _update_levels(self, ob: OrderBook, now: float):
        """Lacak level besar untuk persistence + iceberg refill."""
        walls = ob.find_walls(self.wall_multiplier, self.track_levels)
        current_keys = set()

        for side, data in (("bid", walls["bid_walls"]), ("ask", walls["ask_walls"])):
            for price, qty in data:
                key = (side, price)
                current_keys.add(key)
                tracker = self._levels.get(key)
                if tracker is None:
                    self._levels[key] = LevelTracker(
                        price=price, side=side,
                        first_seen=now, last_seen=now,
                        peak_qty=qty, last_qty=qty,
                    )
                else:
                    # Refill: qty turun lalu naik lagi mendekati peak
                    if tracker.last_qty > 0 and qty > tracker.last_qty * 1.2 \
                            and tracker.last_qty < tracker.peak_qty * 0.7:
                        tracker.refill_count += 1
                    tracker.last_seen = now
                    tracker.peak_qty = max(tracker.peak_qty, qty)
                    tracker.last_qty = qty

    def _update_depletion(self, ob: OrderBook, now: float):
        """Hitung laju perubahan depth per detik (bid & ask)."""
        bid_depth = ob.total_bid_volume(self.track_levels)
        ask_depth = ob.total_ask_volume(self.track_levels)

        if self._prev_depth_ts is not None:
            dt = now - self._prev_depth_ts
            if dt > 0:
                bid_rate = (bid_depth - self._prev_bid_depth) / dt
                ask_rate = (ask_depth - self._prev_ask_depth) / dt
                self._depletion_history.append((bid_rate, ask_rate, now))

        self._prev_bid_depth = bid_depth
        self._prev_ask_depth = ask_depth
        self._prev_depth_ts = now

    def _prune(self, now: float):
        """Buang tracker level yang sudah lama tidak terlihat."""
        cutoff = now - self.persistence_window
        stale = [k for k, t in self._levels.items() if t.last_seen < cutoff]
        for k in stale:
            del self._levels[k]

    # ------------------------------------------------------------------
    # 1. HEATMAP PERSISTENCE
    # ------------------------------------------------------------------
    def heatmap_persistence(self, min_dwell: float = None) -> dict:
        """Level likuiditas asli = bertahan lama. Return top by dwell time."""
        if min_dwell is None:
            min_dwell = self.cfg.min_dwell
        now = time.time()
        active = [t for t in self._levels.values() if (now - t.last_seen) < 2.0]
        persistent = [t for t in active if t.dwell_seconds >= min_dwell]
        persistent.sort(key=lambda t: -t.dwell_seconds)

        top = [{
            "price": round(t.price, 2),
            "side": t.side,
            "dwell_seconds": round(t.dwell_seconds, 1),
            "peak_qty": round(t.peak_qty, 4),
            "refill_count": t.refill_count,
        } for t in persistent[:5]]

        # Skor 0-100: dwell time terlama dinormalisasi (persistence_norm = penuh)
        score = min(persistent[0].dwell_seconds / self.cfg.persistence_norm * 100, 100) if persistent else 0.0

        return {
            "score": round(score, 1),
            "confidence": CONFIDENCE["persistence"],
            "persistent_levels": top,
            "count": len(persistent),
        }

    # ------------------------------------------------------------------
    # 2. ABSORPTION RATIO
    # ------------------------------------------------------------------
    def absorption_ratio(self, tp: TradeProcessor, seconds: int = 10) -> dict:
        """
        volume tereksekusi / pergerakan harga.
        Rasio tinggi = banyak volume diserap dengan gerak harga minim.
        """
        window = tp.get_window(seconds)
        volume = window.total_volume
        price_range = max(window.high - window.low, 0.0)

        mid = self._prev_mid or window.vwap or 0
        if mid <= 0:
            return {"score": 0.0, "confidence": CONFIDENCE["absorption"], "ratio": 0.0}

        # Normalisasi price move ke persen agar lintas-harga konsisten
        move_pct = (price_range / mid) * 100 if mid else 0.0
        # Rasio: volume per 0.1% gerak. move kecil + volume besar = absorpsi tinggi.
        ratio = volume / (move_pct + 0.01)

        # Arah absorpsi dari delta
        if window.delta > 0:
            direction = "BUYERS_ABSORBED_SELL"   # buyer menyerap tekanan jual
        elif window.delta < 0:
            direction = "SELLERS_ABSORBED_BUY"
        else:
            direction = "NEUTRAL"

        # Skor 0-100 dengan skala log-ish sederhana
        score = min(ratio / self.cfg.absorption_scale, 100)

        return {
            "score": round(score, 1),
            "confidence": CONFIDENCE["absorption"],
            "ratio": round(ratio, 2),
            "volume": round(volume, 4),
            "price_move_pct": round(move_pct, 4),
            "direction": direction,
        }

    # ------------------------------------------------------------------
    # 3. LIQUIDITY DEPLETION SPEED
    # ------------------------------------------------------------------
    def depletion_speed(self, lookback: int = 10) -> dict:
        """
        Laju satu sisi book dimakan. Depletion ask cepat + harga naik = momentum beli asli.
        """
        if not self._depletion_history:
            return {"score": 0.0, "confidence": CONFIDENCE["depletion"], "signal": "NO_DATA"}

        recent = list(self._depletion_history)[-lookback:]
        avg_bid_rate = sum(r[0] for r in recent) / len(recent)
        avg_ask_rate = sum(r[1] for r in recent) / len(recent)

        # Rate negatif = depth berkurang (dimakan)
        bid_depleting = avg_bid_rate < 0
        ask_depleting = avg_ask_rate < 0

        if ask_depleting and not bid_depleting:
            signal = "ASK_DEPLETION"   # ask dimakan → tekanan beli
            desc = "Ask side cepat dimakan — momentum beli asli"
        elif bid_depleting and not ask_depleting:
            signal = "BID_DEPLETION"   # bid dimakan → tekanan jual
            desc = "Bid side cepat dimakan — momentum jual asli"
        else:
            signal = "BALANCED"
            desc = "Kedua sisi depth relatif stabil"

        intensity = max(abs(avg_bid_rate), abs(avg_ask_rate))
        score = min(intensity / self.cfg.depletion_strong * 100, 100)

        return {
            "score": round(score, 1),
            "confidence": CONFIDENCE["depletion"],
            "signal": signal,
            "description": desc,
            "bid_rate_per_s": round(avg_bid_rate, 4),
            "ask_rate_per_s": round(avg_ask_rate, 4),
        }

    # ------------------------------------------------------------------
    # 4. ICEBERG REFILL RATE
    # ------------------------------------------------------------------
    def iceberg_refill(self, min_refills: int = None) -> dict:
        """Level dengan banyak refill = kemungkinan iceberg institusional."""
        if min_refills is None:
            min_refills = self.cfg.iceberg_min_refills
        now = time.time()
        candidates = [
            t for t in self._levels.values()
            if t.refill_count >= min_refills and (now - t.last_seen) < 5.0
        ]
        candidates.sort(key=lambda t: -t.refill_count)

        top = [{
            "price": round(t.price, 2),
            "side": t.side,
            "refill_count": t.refill_count,
            "dwell_seconds": round(t.dwell_seconds, 1),
            "peak_qty": round(t.peak_qty, 4),
        } for t in candidates[:5]]

        score = min(candidates[0].refill_count / self.cfg.iceberg_norm * 100, 100) if candidates else 0.0

        return {
            "score": round(score, 1),
            "confidence": CONFIDENCE["iceberg"],
            "icebergs": top,
            "count": len(candidates),
        }

    # ------------------------------------------------------------------
    # 5. DELTA vs HEATMAP DIVERGENCE
    # ------------------------------------------------------------------
    def delta_heatmap_divergence(self, ob: OrderBook, tp: TradeProcessor,
                                 seconds: int = 10) -> dict:
        """
        CVD agresif ke satu arah tapi harga mentok di wall pasif yang tidak berkurang.
        Sinyal absorpsi pasif — sering mendahului reversal.
        """
        window = tp.get_window(seconds)
        delta = window.delta
        walls = ob.find_walls(self.wall_multiplier, self.track_levels)

        divergence = None
        if delta > 0 and walls["ask_walls"]:
            # Buyer agresif tapi ada ask wall besar menahan
            divergence = {
                "type": "BULLISH_ABSORBED",
                "description": "Buyer agresif (CVD+) tapi ditahan ask wall pasif — potensi reversal turun",
                "wall_price": round(walls["ask_walls"][0][0], 2),
            }
        elif delta < 0 and walls["bid_walls"]:
            divergence = {
                "type": "BEARISH_ABSORBED",
                "description": "Seller agresif (CVD-) tapi ditahan bid wall pasif — potensi reversal naik",
                "wall_price": round(walls["bid_walls"][0][0], 2),
            }

        score = min(abs(delta) / (window.total_volume + 1) * 100, 100) if divergence else 0.0

        return {
            "score": round(score, 1),
            "confidence": CONFIDENCE["divergence"],
            "divergence": divergence,
            "delta": round(delta, 4),
        }

    # ------------------------------------------------------------------
    # SNAPSHOT — gabungan semua statistik untuk display/signal
    # ------------------------------------------------------------------
    def snapshot(self, ob: OrderBook, tp: TradeProcessor) -> dict:
        persistence = self.heatmap_persistence()
        absorption = self.absorption_ratio(tp)
        depletion = self.depletion_speed()
        iceberg = self.iceberg_refill()
        divergence = self.delta_heatmap_divergence(ob, tp)

        # Composite score: rata-rata tertimbang (akurat diberi bobot lebih besar)
        composite = (
            absorption["score"] * 0.30 +
            depletion["score"] * 0.25 +
            divergence["score"] * 0.20 +
            persistence["score"] * 0.15 +
            iceberg["score"] * 0.10
        )

        return {
            "symbol": self.symbol,
            "composite_score": round(composite, 1),
            "persistence": persistence,
            "absorption": absorption,
            "depletion": depletion,
            "iceberg": iceberg,
            "divergence": divergence,
            "timestamp": time.time(),
        }
