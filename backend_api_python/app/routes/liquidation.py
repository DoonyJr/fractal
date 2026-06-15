"""
Liquidation dashboard APIs (polling model).

Frontend ``/liquidation`` page polls these endpoints. Data comes from the AMT
Liquidation Analysis System (Binance Futures + Bybit Linear WebSocket), hosted
in background threads by ``liquidation_service``.

Endpoints:
- GET  /api/liquidation/snapshot?symbol=BTCUSDT  - Full state snapshot
- GET  /api/liquidation/map?symbol=BTCUSDT       - Long/short liquidation map
- GET  /api/liquidation/active                   - Currently active symbols
- POST /api/liquidation/stop                      - Stop a symbol's runner
"""
from __future__ import annotations

import os
import sys

from flask import jsonify, request
from app.openapi.blueprint import HumanBlueprint as Blueprint

from app.utils.logger import get_logger
from app.utils.auth import login_required
from app.services.liquidation_service import get_liquidation_manager

logger = get_logger(__name__)

liquidation_blp = Blueprint("liquidation", __name__)

_LIQ_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "liquidation_engine")
)


def _liquidation_map(liq_data):
    """Lazy import of the snapshot helper (avoids colorama at module load)."""
    if _LIQ_ROOT not in sys.path:
        sys.path.insert(0, _LIQ_ROOT)
    from output.state_snapshot import liquidation_map
    return liquidation_map(liq_data)


def _normalize_symbol(raw: str) -> str:
    s = (raw or "BTCUSDT").upper().replace("/", "").replace("-", "").strip()
    return s or "BTCUSDT"


@liquidation_blp.route("/snapshot", methods=["GET"])
@login_required
def snapshot():
    symbol = _normalize_symbol(request.args.get("symbol", "BTCUSDT"))
    mgr = get_liquidation_manager()
    err = mgr.ensure(symbol)
    if err:
        return jsonify({"code": 0, "msg": err, "data": {"active": mgr.active_symbols()}})
    return jsonify({"code": 1, "msg": "ok", "data": mgr.snapshot(symbol)})


@liquidation_blp.route("/map", methods=["GET"])
@login_required
def liq_map():
    symbol = _normalize_symbol(request.args.get("symbol", "BTCUSDT"))
    mgr = get_liquidation_manager()
    err = mgr.ensure(symbol)
    if err:
        return jsonify({"code": 0, "msg": err, "data": {"active": mgr.active_symbols()}})
    snap = mgr.snapshot(symbol)
    liq_data = snap.get("liquidation", {}) if isinstance(snap, dict) else {}
    try:
        data = _liquidation_map(liq_data)
    except Exception as e:
        logger.error("liquidation_map failed: %s", e)
        data = {"long": [], "short": [], "clusters": []}
    data["symbol"] = symbol
    data["price"] = snap.get("price", 0) if isinstance(snap, dict) else 0
    return jsonify({"code": 1, "msg": "ok", "data": data})


@liquidation_blp.route("/active", methods=["GET"])
@login_required
def active():
    mgr = get_liquidation_manager()
    return jsonify({"code": 1, "msg": "ok", "data": {"active": mgr.active_symbols()}})


@liquidation_blp.route("/stop", methods=["POST"])
@login_required
def stop():
    body = request.get_json(silent=True) or {}
    symbol = _normalize_symbol(body.get("symbol", ""))
    mgr = get_liquidation_manager()
    mgr.stop_symbol(symbol)
    return jsonify({"code": 1, "msg": "stopped", "data": {"active": mgr.active_symbols()}})


@liquidation_blp.route("/levels", methods=["GET"])
@login_required
def levels():
    """Coinglass-style modelled liquidation levels (from OI + leverage estimation)."""
    symbol = _normalize_symbol(request.args.get("symbol", "BTCUSDT"))
    mgr = get_liquidation_manager()
    err = mgr.ensure(symbol)
    if err:
        return jsonify({"code": 0, "msg": err, "data": {"active": mgr.active_symbols()}})
    snap = mgr.snapshot(symbol)
    price = snap.get("price", 0) if isinstance(snap, dict) else 0
    oi_data = snap.get("open_interest", {}) if isinstance(snap, dict) else {}
    oi_usd = float(oi_data.get("current_oi", 0)) * price if price else 0

    if _LIQ_ROOT not in sys.path:
        sys.path.insert(0, _LIQ_ROOT)
    from analytics.liquidation_levels import model_liquidation_levels

    entry_prices = None
    flow = snap.get("order_flow", {}) if isinstance(snap, dict) else {}
    if flow.get("recent_prices"):
        entry_prices = flow["recent_prices"]

    data = model_liquidation_levels(
        current_price=price,
        open_interest_usd=oi_usd,
        price_range_pct=0.15,
        bins=60,
        entry_prices=entry_prices,
    )
    return jsonify({"code": 1, "msg": "ok", "data": data})
