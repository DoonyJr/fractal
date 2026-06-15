"""
analytics/liquidation_analysis.py
Analisis mendalam liquidation cluster:
- Cascade risk scoring
- Long squeeze vs short squeeze detection
- Liquidation heatmap builder
- Proximity alert (harga mendekati cluster besar)
"""

import time
from typing import List, Dict, Optional
from core.liquidation_collector import LiquidationCollector, LiquidationCluster


class LiquidationAnalyzer:
    """
    Menganalisis pola liquidation untuk mendeteksi:
    - Area cluster yang berisiko memicu cascade
    - Arah tekanan (long squeeze atau short squeeze)
    - Jarak harga saat ini ke cluster terdekat
    """

    def __init__(
        self,
        collector: LiquidationCollector,
        cascade_threshold_usd: float = 500_000,   # $500K di satu zona = warning
        proximity_pct: float = 0.005,              # 0.5% dari harga = dekat
    ):
        self.collector = collector
        self.cascade_threshold_usd = cascade_threshold_usd
        self.proximity_pct = proximity_pct

    def analyze(self, current_price: float, seconds: int = 300) -> dict:
        """Analisis lengkap kondisi liquidation saat ini."""
        clusters = self.collector.get_clusters(seconds=seconds)
        totals = self.collector.total_liquidated(60)

        # Cluster di atas dan di bawah harga saat ini
        clusters_above = [c for c in clusters if c.zone_mid > current_price]
        clusters_below = [c for c in clusters if c.zone_mid <= current_price]

        # Cluster terdekat
        nearest_above = self._nearest(clusters_above, current_price, above=True)
        nearest_below = self._nearest(clusters_below, current_price, above=False)

        # Cascade risk dari cluster terdekat
        cascade_risk = self._cascade_risk(clusters, current_price)

        # Squeeze direction
        squeeze = self._detect_squeeze(clusters_above, clusters_below, current_price)

        # Heatmap data (untuk visualisasi)
        heatmap = self._build_heatmap(clusters, current_price)

        # Recent raw events (untuk feed di web; terminal display tidak pakai)
        recent_events = [
            {
                "side": e.side,
                "price": round(e.price, 4),
                "qty": e.qty,
                "value_usd": round(e.value_usd, 2),
                "exchange": e.exchange,
                "symbol": e.symbol,
                "timestamp": e.timestamp,
            }
            for e in sorted(self.collector.events, key=lambda x: x.timestamp, reverse=True)[:50]
        ]

        return {
            "current_price": current_price,
            "total_liq_60s_usd": totals["total_usd"],
            "long_liq_60s_usd": totals["long_liquidated_usd"],
            "short_liq_60s_usd": totals["short_liquidated_usd"],
            "dominant_60s": totals["dominant"],
            "nearest_above": nearest_above,
            "nearest_below": nearest_below,
            "cascade_risk": cascade_risk,
            "squeeze_signal": squeeze,
            "heatmap": heatmap,
            "recent_events": recent_events,
            "cluster_count": len(clusters),
            "timestamp": time.time(),
        }

    def _nearest(self, clusters: List[LiquidationCluster],
                 price: float, above: bool) -> Optional[dict]:
        """Return cluster terdekat di atas atau di bawah harga."""
        if not clusters:
            return None

        if above:
            c = min(clusters, key=lambda x: x.zone_mid - price)
        else:
            c = max(clusters, key=lambda x: x.zone_mid)

        distance_pct = abs(c.zone_mid - price) / price * 100

        return {
            "zone": f"{c.zone_low:.2f} - {c.zone_high:.2f}",
            "zone_mid": round(c.zone_mid, 2),
            "value_usd": round(c.total_value_usd, 2),
            "dominant_side": c.dominant_side,
            "cascade_risk_score": c.cascade_risk,
            "distance_pct": round(distance_pct, 3),
            "is_close": distance_pct <= self.proximity_pct * 100,
        }

    def _cascade_risk(self, clusters: List[LiquidationCluster], price: float) -> dict:
        """
        Hitung risiko cascade keseluruhan.
        Cluster besar yang dekat dengan harga = risiko tinggi.
        """
        proximity_range = price * self.proximity_pct * 3  # 1.5% dari harga
        nearby = [c for c in clusters
                  if abs(c.zone_mid - price) <= proximity_range]

        if not nearby:
            return {"score": 0, "level": "LOW", "nearby_value_usd": 0}

        nearby_value = sum(c.total_value_usd for c in nearby)
        score = min(nearby_value / self.cascade_threshold_usd * 100, 100)

        if score >= 75:
            level = "CRITICAL"
        elif score >= 50:
            level = "HIGH"
        elif score >= 25:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "score": round(score, 1),
            "level": level,
            "nearby_value_usd": round(nearby_value, 2),
            "nearby_cluster_count": len(nearby),
        }

    def _detect_squeeze(
        self,
        clusters_above: List[LiquidationCluster],
        clusters_below: List[LiquidationCluster],
        price: float,
    ) -> dict:
        """
        Deteksi potensi squeeze berdasarkan distribusi cluster.
        Short squeeze: banyak short cluster di atas → jika harga naik, shorts kena liquidasi
        Long squeeze: banyak long cluster di bawah → jika harga turun, longs kena liquidasi
        """
        val_above = sum(c.short_liq_usd for c in clusters_above)   # short positions di atas
        val_below = sum(c.long_liq_usd for c in clusters_below)     # long positions di bawah

        # Estimasi posisi yang belum diliquidasi (masih terjebak)
        trapped_shorts_above = sum(
            c.total_value_usd for c in clusters_above
            if c.dominant_side == "SHORT"
        )
        trapped_longs_below = sum(
            c.total_value_usd for c in clusters_below
            if c.dominant_side == "LONG"
        )

        ratio = (trapped_shorts_above / (trapped_longs_below + 1))

        if ratio > 2.0:
            signal = "SHORT_SQUEEZE_RISK"
            desc = f"Banyak short cluster di atas harga (${trapped_shorts_above:,.0f}) — jika harga naik, short squeeze potensial"
        elif ratio < 0.5:
            signal = "LONG_SQUEEZE_RISK"
            desc = f"Banyak long cluster di bawah harga (${trapped_longs_below:,.0f}) — jika harga turun, long squeeze potensial"
        else:
            signal = "BALANCED"
            desc = "Distribusi cluster relatif seimbang di kedua sisi"

        return {
            "signal": signal,
            "description": desc,
            "trapped_shorts_above_usd": round(trapped_shorts_above, 2),
            "trapped_longs_below_usd": round(trapped_longs_below, 2),
            "squeeze_ratio": round(ratio, 3),
        }

    def _build_heatmap(self, clusters: List[LiquidationCluster], price: float) -> List[dict]:
        """Bangun data heatmap untuk visualisasi terminal."""
        result = []
        for c in sorted(clusters, key=lambda x: x.zone_mid, reverse=True)[:20]:
            distance_pct = (c.zone_mid - price) / price * 100
            result.append({
                "zone_mid": round(c.zone_mid, 2),
                "value_usd": round(c.total_value_usd, 2),
                "dominant": c.dominant_side,
                "distance_pct": round(distance_pct, 3),
                "cascade_risk": c.cascade_risk,
                "bar": self._make_bar(c.total_value_usd),
            })
        return result

    def _make_bar(self, value_usd: float, max_width: int = 20) -> str:
        """Buat bar ASCII untuk visualisasi di terminal."""
        max_val = 2_000_000  # $2M = full bar
        filled = int(min(value_usd / max_val, 1.0) * max_width)
        return "█" * filled + "░" * (max_width - filled)
