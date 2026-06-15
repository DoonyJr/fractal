"""
analytics/market_profile.py
Implementasi Market Profile berbasis AMT (Auction Market Theory):
- Volume Profile: distribusi volume per level harga
- Point of Control (POC): harga dengan volume tertinggi
- Value Area (VA): zona 70% total volume
- Market Profile letters (TPO sederhana)
- Auction state: balancing vs trending
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from core.trade_processor import Trade


@dataclass
class VolumeNode:
    """Satu node dalam Volume Profile."""
    price: float
    buy_volume: float = 0.0
    sell_volume: float = 0.0

    @property
    def total_volume(self) -> float:
        return self.buy_volume + self.sell_volume

    @property
    def delta(self) -> float:
        return self.buy_volume - self.sell_volume


class MarketProfile:
    """
    Membangun Volume Profile dan Market Profile dari aliran trade.
    Tick size menentukan resolusi profil (default 0.1% dari harga awal).
    """

    def __init__(self, symbol: str, tick_pct: float = 0.001):
        self.symbol = symbol
        self.tick_pct = tick_pct          # ukuran bucket harga
        self._tick_size: Optional[float] = None

        # {rounded_price: VolumeNode}
        self._nodes: Dict[float, VolumeNode] = defaultdict(lambda: VolumeNode(price=0.0))
        self._total_volume: float = 0.0
        self._trade_count: int = 0
        self._session_high: float = 0.0
        self._session_low: float = float('inf')
        self._start_time: float = time.time()

    def _round_price(self, price: float) -> float:
        """Snap harga ke tick grid."""
        if self._tick_size is None:
            self._tick_size = round(price * self.tick_pct, 8)
        if self._tick_size == 0:
            return price
        return round(round(price / self._tick_size) * self._tick_size, 8)

    def add_trade(self, price: float, qty: float, side: str):
        """Tambahkan trade ke profil."""
        rounded = self._round_price(price)

        node = self._nodes[rounded]
        node.price = rounded

        if side.lower() == 'buy':
            node.buy_volume += qty
        else:
            node.sell_volume += qty

        self._total_volume += qty
        self._trade_count += 1
        self._session_high = max(self._session_high, price)
        self._session_low = min(self._session_low, price)

    def poc(self) -> Optional[VolumeNode]:
        """Point of Control: node dengan volume tertinggi."""
        if not self._nodes:
            return None
        return max(self._nodes.values(), key=lambda n: n.total_volume)

    def value_area(self, pct: float = 0.70) -> Optional[Tuple[float, float, float]]:
        """
        Value Area: rentang harga yang mencakup pct% dari total volume.
        Return: (VA_Low, VA_High, POC_price)
        """
        if not self._nodes or self._total_volume == 0:
            return None

        poc_node = self.poc()
        if poc_node is None:
            return None

        sorted_nodes = sorted(self._nodes.values(), key=lambda n: n.price)
        prices = [n.price for n in sorted_nodes]
        poc_idx = prices.index(poc_node.price)

        target_vol = self._total_volume * pct
        accumulated = poc_node.total_volume

        lo_idx = poc_idx
        hi_idx = poc_idx

        # Expand ke atas dan bawah secara bergantian (sesuai algoritma VA standar)
        while accumulated < target_vol:
            can_go_up = hi_idx + 1 < len(sorted_nodes)
            can_go_down = lo_idx - 1 >= 0

            if not can_go_up and not can_go_down:
                break

            vol_up = sorted_nodes[hi_idx + 1].total_volume if can_go_up else 0
            vol_down = sorted_nodes[lo_idx - 1].total_volume if can_go_down else 0

            if vol_up >= vol_down:
                hi_idx += 1
                accumulated += vol_up
            else:
                lo_idx -= 1
                accumulated += vol_down

        return (
            sorted_nodes[lo_idx].price,   # VA Low
            sorted_nodes[hi_idx].price,   # VA High
            poc_node.price,               # POC
        )

    def auction_state(self, current_price: float) -> dict:
        """
        Tentukan kondisi auction saat ini berdasarkan posisi harga vs Value Area.
        Ini adalah inti dari AMT analysis.
        """
        va = self.value_area()
        poc_node = self.poc()

        if va is None or poc_node is None:
            return {"state": "INSUFFICIENT_DATA"}

        va_low, va_high, poc_price = va
        va_width = va_high - va_low

        # Tentukan state
        if va_low <= current_price <= va_high:
            # Harga di dalam Value Area → balancing/rotasi
            poc_distance = abs(current_price - poc_price) / va_width if va_width > 0 else 0
            if poc_distance < 0.2:
                state = "BALANCING_AT_POC"
                desc = "Harga sangat dekat POC — pasar dalam keseimbangan penuh"
            else:
                state = "BALANCING"
                desc = f"Harga di dalam Value Area ({va_low:.2f} - {va_high:.2f}) — rotasi normal"
        elif current_price > va_high:
            # Harga di atas VA → potensi trend naik atau rejection
            excess_pct = (current_price - va_high) / va_width * 100 if va_width > 0 else 0
            if excess_pct > 50:
                state = "TRENDING_UP"
                desc = f"Harga jauh di atas VA High ({va_high:.2f}) — trending up, pasar mencari value baru"
            else:
                state = "TESTING_VA_HIGH"
                desc = f"Harga menguji VA High ({va_high:.2f}) — observasi apakah diterima atau ditolak"
        else:
            # Harga di bawah VA → potensi trend turun atau rejection
            excess_pct = (va_low - current_price) / va_width * 100 if va_width > 0 else 0
            if excess_pct > 50:
                state = "TRENDING_DOWN"
                desc = f"Harga jauh di bawah VA Low ({va_low:.2f}) — trending down, pasar mencari value baru"
            else:
                state = "TESTING_VA_LOW"
                desc = f"Harga menguji VA Low ({va_low:.2f}) — observasi apakah diterima atau ditolak"

        return {
            "state": state,
            "description": desc,
            "current_price": current_price,
            "poc": round(poc_price, 4),
            "va_low": round(va_low, 4),
            "va_high": round(va_high, 4),
            "va_width": round(va_width, 4),
            "session_high": round(self._session_high, 4),
            "session_low": round(self._session_low, 4) if self._session_low != float('inf') else None,
            "total_volume": round(self._total_volume, 4),
            "trade_count": self._trade_count,
        }

    def top_nodes(self, n: int = 10) -> List[VolumeNode]:
        """Return N node dengan volume tertinggi."""
        return sorted(self._nodes.values(), key=lambda x: -x.total_volume)[:n]

    def profile_ascii(self, width: int = 30, rows: int = 20) -> str:
        """
        Render Volume Profile sebagai bar chart ASCII di terminal.
        """
        if not self._nodes:
            return "No data"

        sorted_nodes = sorted(self._nodes.values(), key=lambda n: -n.price)
        # Ambil sample rows teratas
        sampled = sorted_nodes[:rows]
        max_vol = max(n.total_volume for n in sampled) if sampled else 1

        poc_node = self.poc()
        va = self.value_area()
        va_low = va[0] if va else 0
        va_high = va[1] if va else 0

        lines = []
        for node in sampled:
            bar_len = int(node.total_volume / max_vol * width)
            bar = "█" * bar_len + "░" * (width - bar_len)

            tag = ""
            if poc_node and node.price == poc_node.price:
                tag = " ◄ POC"
            elif va_low <= node.price <= va_high:
                tag = " [VA]"

            lines.append(f"{node.price:>10.2f} | {bar} {node.total_volume:>10.2f}{tag}")

        return "\n".join(lines)

    def reset(self):
        """Reset profil untuk session baru."""
        self._nodes.clear()
        self._total_volume = 0.0
        self._trade_count = 0
        self._session_high = 0.0
        self._session_low = float('inf')
        self._start_time = time.time()
