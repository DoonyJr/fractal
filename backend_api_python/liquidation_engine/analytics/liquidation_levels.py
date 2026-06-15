"""
analytics/liquidation_levels.py

Coinglass-style liquidation level modelling. Estimates WHERE liquidations WILL
occur based on Open Interest + assumed leverage distribution.

Formula: liq_price_long  = entry_price * (1 - 1/leverage)
         liq_price_short = entry_price * (1 + 1/leverage)

Since we don't know the actual entry prices or leverages of all positions, we
model them: distribute the current OI across price bins (using recent trade
data as proxy for entry price distribution), then for each leverage tier
calculate where those positions would liquidate.

This is the same methodology Coinglass/Kingfisher uses (labelled "MODELLED").
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

LEVERAGE_TIERS = [10, 25, 50, 100]
LEVERAGE_WEIGHTS = {10: 0.30, 25: 0.25, 50: 0.25, 100: 0.20}


def model_liquidation_levels(
    current_price: float,
    open_interest_usd: float,
    price_range_pct: float = 0.15,
    bins: int = 60,
    entry_prices: Optional[List[float]] = None,
) -> Dict:
    """
    Model estimated liquidation levels around current price.

    Args:
        current_price: Current mark price.
        open_interest_usd: Total open interest in USD.
        price_range_pct: How far above/below to model (0.15 = ±15%).
        bins: Number of price bins.
        entry_prices: Optional list of recent trade prices for entry distribution.
                      If None, uses gaussian distribution centered on current price.

    Returns dict with:
        - price_levels: sorted list of price points
        - long_liq: list of {price, total, by_leverage: {10: val, 25: val, ...}}
        - short_liq: same structure
        - cumulative_long: running sum from current price leftward
        - cumulative_short: running sum from current price rightward
        - current_price, timestamp
    """
    if not current_price or current_price <= 0 or open_interest_usd <= 0:
        return _empty_result(current_price)

    lo = current_price * (1 - price_range_pct)
    hi = current_price * (1 + price_range_pct)
    step = (hi - lo) / bins
    price_levels = [lo + (i + 0.5) * step for i in range(bins)]

    # Model entry price distribution (gaussian around current price if no data)
    import math
    entry_dist = [0.0] * bins
    if entry_prices and len(entry_prices) > 10:
        for ep in entry_prices:
            idx = int((ep - lo) / step)
            if 0 <= idx < bins:
                entry_dist[idx] += 1
    else:
        sigma = bins * 0.2
        center = bins / 2
        for i in range(bins):
            entry_dist[i] = math.exp(-0.5 * ((i - center) / sigma) ** 2)

    total_weight = sum(entry_dist) or 1
    entry_dist = [w / total_weight for w in entry_dist]

    # Allocate OI equally between longs and shorts (simplification)
    long_oi = open_interest_usd * 0.5
    short_oi = open_interest_usd * 0.5

    # For each entry price bin + leverage tier, compute liquidation price
    long_liq_bins = [{"price": p, "total": 0.0, "by_leverage": {lev: 0.0 for lev in LEVERAGE_TIERS}} for p in price_levels]
    short_liq_bins = [{"price": p, "total": 0.0, "by_leverage": {lev: 0.0 for lev in LEVERAGE_TIERS}} for p in price_levels]

    for entry_idx in range(bins):
        entry_price = price_levels[entry_idx]
        oi_at_entry_long = long_oi * entry_dist[entry_idx]
        oi_at_entry_short = short_oi * entry_dist[entry_idx]

        for lev in LEVERAGE_TIERS:
            weight = LEVERAGE_WEIGHTS[lev]

            # Long liquidation: price drops to entry * (1 - 1/leverage)
            liq_long = entry_price * (1 - 1.0 / lev)
            liq_long_idx = int((liq_long - lo) / step)
            if 0 <= liq_long_idx < bins:
                val = oi_at_entry_long * weight
                long_liq_bins[liq_long_idx]["total"] += val
                long_liq_bins[liq_long_idx]["by_leverage"][lev] += val

            # Short liquidation: price rises to entry * (1 + 1/leverage)
            liq_short = entry_price * (1 + 1.0 / lev)
            liq_short_idx = int((liq_short - lo) / step)
            if 0 <= liq_short_idx < bins:
                val = oi_at_entry_short * weight
                short_liq_bins[liq_short_idx]["total"] += val
                short_liq_bins[liq_short_idx]["by_leverage"][lev] += val

    # Cumulative curves (Coinglass-style: long cumulates from mark leftward,
    # short cumulates from mark rightward)
    mark_idx = int((current_price - lo) / step)
    mark_idx = max(0, min(bins - 1, mark_idx))

    cumulative_long = [0.0] * bins
    running = 0.0
    for i in range(mark_idx, -1, -1):
        running += long_liq_bins[i]["total"]
        cumulative_long[i] = running

    cumulative_short = [0.0] * bins
    running = 0.0
    for i in range(mark_idx, bins):
        running += short_liq_bins[i]["total"]
        cumulative_short[i] = running

    return {
        "price_levels": [round(p, 2) for p in price_levels],
        "long_liq": [{
            "price": round(b["price"], 2),
            "total": round(b["total"], 2),
            "by_leverage": {str(k): round(v, 2) for k, v in b["by_leverage"].items()}
        } for b in long_liq_bins],
        "short_liq": [{
            "price": round(b["price"], 2),
            "total": round(b["total"], 2),
            "by_leverage": {str(k): round(v, 2) for k, v in b["by_leverage"].items()}
        } for b in short_liq_bins],
        "cumulative_long": [round(v, 2) for v in cumulative_long],
        "cumulative_short": [round(v, 2) for v in cumulative_short],
        "current_price": current_price,
        "mark_idx": mark_idx,
        "timestamp": time.time(),
    }


def _empty_result(price: float) -> Dict:
    return {
        "price_levels": [],
        "long_liq": [],
        "short_liq": [],
        "cumulative_long": [],
        "cumulative_short": [],
        "current_price": price or 0,
        "mark_idx": 0,
        "timestamp": time.time(),
    }
