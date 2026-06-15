"""
core/liquidation_collector.py
Mengumpulkan dan memproses force liquidation events dari Binance dan Bybit.
Mendeteksi liquidation cluster berdasarkan zona harga.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Deque


@dataclass
class LiquidationEvent:
    """Satu event liquidation dari exchange."""
    symbol: str
    exchange: str
    side: str           # 'buy' (short diliquidasi) atau 'sell' (long diliquidasi)
    price: float
    qty: float
    value_usd: float
    timestamp: float


@dataclass
class LiquidationCluster:
    """Cluster liquidation dalam zona harga tertentu."""
    zone_low: float
    zone_high: float
    total_value_usd: float = 0.0
    long_liq_usd: float = 0.0    # long yang diliquidasi (side=sell)
    short_liq_usd: float = 0.0   # short yang diliquidasi (side=buy)
    count: int = 0
    last_timestamp: float = 0.0

    @property
    def zone_mid(self) -> float:
        return (self.zone_low + self.zone_high) / 2

    @property
    def dominant_side(self) -> str:
        if self.long_liq_usd > self.short_liq_usd:
            return "LONG"
        elif self.short_liq_usd > self.long_liq_usd:
            return "SHORT"
        return "MIXED"

    @property
    def cascade_risk(self) -> float:
        """
        Skor risiko cascade 0-100.
        Makin besar nilai liquidation di zona, makin tinggi risiko.
        """
        base = min(self.total_value_usd / 1_000_000, 100)  # per $1M
        return round(base, 1)


class LiquidationCollector:
    """
    Mengumpulkan liquidation events dan membangun cluster map.
    Zone size menentukan resolusi heatmap (default 0.1% dari harga).
    """

    def __init__(self, symbol: str, zone_pct: float = 0.001, window_seconds: int = 300):
        self.symbol = symbol
        self.zone_pct = zone_pct          # ukuran zona: 0.1% dari harga
        self.window_seconds = window_seconds  # window analisis (default 5 menit)

        self.events: Deque[LiquidationEvent] = deque(maxlen=5000)
        self._clusters: Dict[float, LiquidationCluster] = {}  # key = zone_low

    def _get_zone_low(self, price: float) -> float:
        """Snap harga ke grid zona."""
        zone_size = price * self.zone_pct
        return round(price - (price % zone_size), 8)

    def add_event(self, exchange: str, side: str, price: float,
                  qty: float, timestamp: float = None) -> LiquidationEvent:
        """Tambah satu liquidation event."""
        ts = timestamp or time.time()
        value_usd = price * qty

        event = LiquidationEvent(
            symbol=self.symbol,
            exchange=exchange,
            side=side.lower(),
            price=price,
            qty=qty,
            value_usd=value_usd,
            timestamp=ts,
        )
        self.events.append(event)
        self._update_cluster(event)
        return event

    def _update_cluster(self, event: LiquidationEvent):
        zone_low = self._get_zone_low(event.price)
        zone_high = zone_low + zone_low * self.zone_pct

        if zone_low not in self._clusters:
            self._clusters[zone_low] = LiquidationCluster(
                zone_low=zone_low,
                zone_high=zone_high,
            )

        cluster = self._clusters[zone_low]
        cluster.total_value_usd += event.value_usd
        cluster.count += 1
        cluster.last_timestamp = event.timestamp

        # side='buy' artinya short position diliquidasi
        # side='sell' artinya long position diliquidasi
        if event.side == 'buy':
            cluster.short_liq_usd += event.value_usd
        else:
            cluster.long_liq_usd += event.value_usd

    def get_clusters(self, min_value_usd: float = 10_000,
                     seconds: int = None) -> List[LiquidationCluster]:
        """
        Return cluster yang aktif, diurutkan dari terbesar.
        """
        cutoff = time.time() - (seconds or self.window_seconds)

        # Rebuild clusters hanya dari events dalam window
        fresh_clusters: Dict[float, LiquidationCluster] = defaultdict(
            lambda: LiquidationCluster(zone_low=0, zone_high=0)
        )

        for event in self.events:
            if event.timestamp < cutoff:
                continue
            zone_low = self._get_zone_low(event.price)
            zone_high = zone_low + zone_low * self.zone_pct

            if zone_low not in fresh_clusters:
                fresh_clusters[zone_low] = LiquidationCluster(
                    zone_low=zone_low,
                    zone_high=zone_high,
                )
            c = fresh_clusters[zone_low]
            c.total_value_usd += event.value_usd
            c.count += 1
            c.last_timestamp = event.timestamp
            if event.side == 'buy':
                c.short_liq_usd += event.value_usd
            else:
                c.long_liq_usd += event.value_usd

        result = [c for c in fresh_clusters.values() if c.total_value_usd >= min_value_usd]
        return sorted(result, key=lambda c: -c.total_value_usd)

    def total_liquidated(self, seconds: int = 60) -> dict:
        """Total nilai liquidation dalam window terakhir."""
        cutoff = time.time() - seconds
        long_liq = sum(e.value_usd for e in self.events
                       if e.timestamp >= cutoff and e.side == 'sell')
        short_liq = sum(e.value_usd for e in self.events
                        if e.timestamp >= cutoff and e.side == 'buy')
        return {
            "long_liquidated_usd": round(long_liq, 2),
            "short_liquidated_usd": round(short_liq, 2),
            "total_usd": round(long_liq + short_liq, 2),
            "dominant": "LONG SQUEEZE" if long_liq > short_liq else "SHORT SQUEEZE",
        }

    def top_clusters(self, n: int = 5, seconds: int = None) -> List[LiquidationCluster]:
        """Return N cluster terbesar."""
        return self.get_clusters(seconds=seconds)[:n]

    def summary(self) -> dict:
        totals_60 = self.total_liquidated(60)
        totals_300 = self.total_liquidated(300)
        clusters = self.top_clusters(3)
        return {
            "symbol": self.symbol,
            "liq_60s_usd": totals_60["total_usd"],
            "liq_300s_usd": totals_300["total_usd"],
            "dominant_60s": totals_60["dominant"],
            "top_clusters": [
                {
                    "zone": f"{c.zone_low:.2f}-{c.zone_high:.2f}",
                    "value_usd": round(c.total_value_usd, 2),
                    "dominant_side": c.dominant_side,
                    "cascade_risk": c.cascade_risk,
                }
                for c in clusters
            ],
        }
