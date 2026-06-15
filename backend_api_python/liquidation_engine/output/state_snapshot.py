"""
output/state_snapshot.py
JSON-safe snapshot builder for web/API consumption.

The terminal display (terminal_display.py) renders analysis dicts to the CLI.
This module serializes the SAME dicts into one plain, JSON-safe structure so a
web backend can expose it via a polling endpoint without importing colorama or
touching the rendering layer. Keep this in sync with analysis_loop in main.py:
every dict passed to display.render() should appear here.
"""

import time
from typing import Any, Dict, List, Optional


def _num(value: Any, default: float = 0.0) -> float:
    """Coerce to a finite float; NaN/inf/None -> default (JSON-safe)."""
    try:
        f = float(value)
        if f != f or f in (float("inf"), float("-inf")):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _signal_to_dict(sig: Any) -> Dict[str, Any]:
    """Serialize a Signal dataclass into a JSON-safe dict."""
    return {
        "type": getattr(sig, "signal_type", ""),
        "severity": getattr(sig, "severity", "LOW"),
        "exchange": getattr(sig, "exchange", ""),
        "symbol": getattr(sig, "symbol", ""),
        "price": _num(getattr(sig, "price", 0)),
        "description": getattr(sig, "description", ""),
        "age_seconds": round(_num(getattr(sig, "age_seconds", lambda: 0)() if callable(getattr(sig, "age_seconds", None)) else 0), 1),
        "timestamp": _num(getattr(sig, "timestamp", time.time())),
    }


def build_snapshot(
    symbol: str,
    price: float,
    ob_data: Optional[Dict] = None,
    liq_data: Optional[Dict] = None,
    flow_data: Optional[Dict] = None,
    mp_data: Optional[Dict] = None,
    oi_data: Optional[Dict] = None,
    confluence_data: Optional[Dict] = None,
    bookmap_data: Optional[Dict] = None,
    signals: Optional[List] = None,
    connected: bool = False,
) -> Dict[str, Any]:
    """
    Assemble a single JSON-safe snapshot of the full liquidation/order-flow state.

    Mirrors the inputs of TerminalDisplay.render() so the web view shows the
    same information as the CLI dashboard. ``connected`` reflects whether the
    exchange WebSocket feed is live (order book ready + price ticking), so the
    UI can distinguish "connected but quiet market" from "not connected yet".
    """
    return {
        "symbol": symbol,
        "price": _num(price),
        "connected": bool(connected),
        "timestamp": time.time(),
        "order_book": ob_data or {},
        "liquidation": liq_data or {},
        "order_flow": flow_data or {},
        "market_profile": mp_data or {},
        "open_interest": oi_data or {},
        "confluence": confluence_data or {},
        "bookmap": bookmap_data or {},
        "signals": [_signal_to_dict(s) for s in (signals or [])],
    }


def liquidation_map(liq_data: Optional[Dict]) -> Dict[str, Any]:
    """
    Extract a chart-ready liquidation map (long vs short bars by price zone)
    from LiquidationAnalyzer output. The analyzer exposes zones under the
    ``heatmap`` key (list of {zone_mid, value_usd, dominant, ...}); we split
    each zone into the long/short series the frontend expects. Returns empty
    buckets when no data so the frontend renders an empty chart, not an error.
    """
    if not liq_data:
        return {"long": [], "short": [], "clusters": []}

    # Prefer the analyzer's `heatmap`; fall back to a raw `clusters` list.
    zones = liq_data.get("heatmap") or liq_data.get("clusters") or []
    long_bars: List[Dict] = []
    short_bars: List[Dict] = []
    for z in zones:
        price = _num(z.get("zone_mid", z.get("zone_low", 0)))
        if price <= 0:
            continue
        # Heatmap zones carry one `value_usd` + `dominant` side; raw clusters
        # may carry split long/short. Support both.
        long_usd = _num(z.get("long_liq_usd", 0))
        short_usd = _num(z.get("short_liq_usd", 0))
        if long_usd == 0 and short_usd == 0:
            val = _num(z.get("value_usd", 0))
            dominant = str(z.get("dominant", "")).upper()
            if dominant == "LONG":
                long_usd = val
            elif dominant == "SHORT":
                short_usd = val
            else:
                long_usd = short_usd = val / 2
        if long_usd > 0:
            long_bars.append({"price": price, "value": long_usd})
        if short_usd > 0:
            short_bars.append({"price": price, "value": short_usd})

    return {
        "long": sorted(long_bars, key=lambda x: x["price"]),
        "short": sorted(short_bars, key=lambda x: x["price"]),
        "clusters": zones,
    }
