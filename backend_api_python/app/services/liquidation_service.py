"""
Liquidation analysis service.

Runs the AMT Liquidation Analysis System (bundled ``liquidation_engine/`` inside
backend_api_python) inside background daemon threads, mirroring the existing
background-worker pattern in ``create_app()`` (PostRestorePositionSync, etc.).

Design (per PekerjaanRumah.md decisions):
  - Polling model: web reads ``latest_snapshot``; no per-user WebSocket push.
  - Max 3 active symbols at once (small user base).
  - On-demand spawn + idle timeout: a symbol's threads/connections are torn
    down after IDLE_TIMEOUT seconds with no snapshot read, so we never keep
    idle exchange WebSocket connections alive.

Each AMTSystem is full asyncio; we host one per symbol in a dedicated thread
with its own event loop, then read the thread-safe ``latest_snapshot`` dict.
"""
from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
from typing import Dict, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Resolve the bundled ``liquidation_engine/`` package (inside backend_api_python,
# so it ships in the Docker image). Path: app/services -> app -> backend root.
_LIQ_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "liquidation_engine")
)

MAX_SYMBOLS = int(os.getenv("LIQUIDATION_MAX_SYMBOLS", 3))
IDLE_TIMEOUT = float(os.getenv("LIQUIDATION_IDLE_TIMEOUT", 300))  # 5 minutes


class _SymbolRunner:
    """Owns one AMTSystem running in its own thread + event loop."""

    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self.system = None
        self.thread: Optional[threading.Thread] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.last_access: float = time.time()
        self.started_at: float = time.time()
        self._stop = threading.Event()

    def start(self) -> None:
        self.thread = threading.Thread(
            target=self._run, name=f"Liquidation-{self.symbol}", daemon=True
        )
        self.thread.start()

    def _run(self) -> None:
        if _LIQ_ROOT not in sys.path:
            sys.path.insert(0, _LIQ_ROOT)
        try:
            from main import AMTSystem  # liquidation/main.py
        except Exception as e:  # pragma: no cover - import guard
            logger.error("Liquidation module import failed: %s", e)
            return

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.system = AMTSystem(symbol=self.symbol, refresh_rate=1.0)
        try:
            self.loop.run_until_complete(self._supervise())
        except Exception as e:  # pragma: no cover
            logger.error("Liquidation runner %s crashed: %s", self.symbol, e)
        finally:
            try:
                self.loop.close()
            except Exception:
                pass

    async def _supervise(self) -> None:
        start_task = asyncio.ensure_future(self.system.start())
        while not self._stop.is_set():
            if time.time() - self.last_access > IDLE_TIMEOUT:
                logger.info("Liquidation %s idle, stopping.", self.symbol)
                break
            await asyncio.sleep(2)
        if hasattr(self.system, "stop"):
            self.system.stop()
        start_task.cancel()
        try:
            await start_task
        except (asyncio.CancelledError, Exception):
            pass

    def stop(self) -> None:
        self._stop.set()

    def snapshot(self) -> dict:
        self.last_access = time.time()
        snap = getattr(self.system, "latest_snapshot", None) if self.system else None
        return snap or {"symbol": self.symbol, "ready": False}


class LiquidationManager:
    """Registry of active symbol runners with capacity + idle enforcement."""

    def __init__(self):
        self._runners: Dict[str, _SymbolRunner] = {}
        self._lock = threading.Lock()

    def _reap_idle(self) -> None:
        now = time.time()
        dead = [
            sym for sym, r in self._runners.items()
            if now - r.last_access > IDLE_TIMEOUT or (r.thread and not r.thread.is_alive())
        ]
        for sym in dead:
            self._runners[sym].stop()
            del self._runners[sym]
            logger.info("Liquidation reaped idle symbol %s", sym)

    def ensure(self, symbol: str) -> Optional[str]:
        """Start a runner for symbol if needed. Returns error string or None."""
        symbol = symbol.upper()
        with self._lock:
            self._reap_idle()
            if symbol in self._runners:
                self._runners[symbol].last_access = time.time()
                return None
            if len(self._runners) >= MAX_SYMBOLS:
                return f"Max {MAX_SYMBOLS} symbols active. Stop one before adding another."
            runner = _SymbolRunner(symbol)
            self._runners[symbol] = runner
            runner.start()
            logger.info("Liquidation started symbol %s", symbol)
            return None

    def snapshot(self, symbol: str) -> dict:
        symbol = symbol.upper()
        with self._lock:
            runner = self._runners.get(symbol)
        if runner is None:
            return {"symbol": symbol, "ready": False}
        return runner.snapshot()

    def active_symbols(self) -> list:
        with self._lock:
            return list(self._runners.keys())

    def stop_symbol(self, symbol: str) -> None:
        symbol = symbol.upper()
        with self._lock:
            runner = self._runners.pop(symbol, None)
        if runner:
            runner.stop()


_manager: Optional[LiquidationManager] = None
_manager_lock = threading.Lock()


def get_liquidation_manager() -> LiquidationManager:
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = LiquidationManager()
    return _manager
