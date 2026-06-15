"""
main.py
Entry point utama AMT Liquidation Analysis System.
Menghubungkan semua komponen: streams → processors → analytics → signals → display.

Cara menjalankan:
  pip install -r requirements.txt
  python main.py --symbol BTCUSDT
  python main.py --symbol ETHUSDT --refresh 2
"""

import asyncio
import argparse
import logging
import signal
import sys
import time

# Core
from core.order_book import OrderBook
from core.trade_processor import TradeProcessor
from core.liquidation_collector import LiquidationCollector
from core.oi_calculator import OICalculator

# Streams
from streams.binance_ws import BinanceWebSocket
from streams.bybit_ws import BybitWebSocket

# Analytics
from analytics.order_book_analysis import OrderBookAnalyzer
from analytics.liquidation_analysis import LiquidationAnalyzer
from analytics.order_flow import OrderFlowAnalyzer
from analytics.market_profile import MarketProfile
from analytics.amt_confluence import AMTConfluence
from analytics.bookmap_stats import BookmapStats

# Signals
from signals.signal_engine import SignalEngine

# Output
from output.terminal_display import TerminalDisplay
from output.state_snapshot import build_snapshot

# Setup logging (ke file agar tidak mengganggu terminal display)
logging.basicConfig(
    filename="amt_system.log",
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class AMTSystem:
    """
    Sistem analisis utama yang mengintegrasikan semua komponen.
    """

    def __init__(self, symbol: str, refresh_rate: float = 1.0):
        self.symbol = symbol.upper()
        self.refresh_rate = refresh_rate

        # ── Core components ──────────────────────────────────────────
        self.ob_binance = OrderBook(symbol=self.symbol, exchange="binance", depth=200)
        self.ob_bybit = OrderBook(symbol=self.symbol, exchange="bybit", depth=200)

        self.liq_collector = LiquidationCollector(symbol=self.symbol)
        self.oi_calc = OICalculator(symbol=self.symbol, exchange="bybit")

        # ── Analytics ────────────────────────────────────────────────
        self.ob_analyzer_binance = OrderBookAnalyzer(symbol=self.symbol)
        self.ob_analyzer_bybit = OrderBookAnalyzer(symbol=self.symbol)
        self.liq_analyzer = LiquidationAnalyzer(collector=self.liq_collector)
        self.flow_analyzer = OrderFlowAnalyzer(symbol=self.symbol)
        self.market_profile = MarketProfile(symbol=self.symbol)
        self.confluence_analyzer = AMTConfluence(symbol=self.symbol)
        self.bookmap_stats = BookmapStats(symbol=self.symbol)

        # ── Signal engine ─────────────────────────────────────────────
        self.signal_engine = SignalEngine(symbol=self.symbol)

        # ── Display ───────────────────────────────────────────────────
        self.display = TerminalDisplay(symbol=self.symbol, refresh_rate=refresh_rate)

        # State harga untuk divergence detection
        self._prev_price: float = 0.0
        self._current_price: float = 0.0

        self.latest_snapshot: dict = {}

        self._running = False

    # ------------------------------------------------------------------
    # WebSocket Callbacks — Binance
    # ------------------------------------------------------------------
    async def on_binance_orderbook(self, data: dict):
        """Update order book Binance dari stream."""
        bids = [[p, q] for p, q in data["bids"]]
        asks = [[p, q] for p, q in data["asks"]]

        if not self.ob_binance.is_ready:
            self.ob_binance.apply_snapshot(bids, asks, data.get("update_id", 0))
        else:
            self.ob_binance.apply_update(bids, asks, data.get("update_id", 0))

    async def on_binance_trade(self, data: dict):
        """Proses trade dari Binance."""
        price = data["price"]
        qty = data["qty"]
        side = data["side"]
        ts = data["timestamp"]

        self.flow_analyzer.add_trade("binance", price, qty, side, ts)
        self.market_profile.add_trade(price, qty, side)

        # Update harga current
        self._prev_price = self._current_price if self._current_price else price
        self._current_price = price

    async def on_binance_liquidation(self, data: dict):
        """Proses liquidation event dari Binance."""
        self.liq_collector.add_event(
            exchange="binance",
            side=data["side"],
            price=data["price"],
            qty=data["qty"],
            timestamp=data["timestamp"],
        )
        logger.warning(
            f"[LIQUIDATION][Binance] {data['side'].upper()} "
            f"${data['value_usd']:,.0f} @ {data['price']}"
        )

    # ------------------------------------------------------------------
    # WebSocket Callbacks — Bybit
    # ------------------------------------------------------------------
    async def on_bybit_orderbook(self, data: dict):
        """Update order book Bybit dari stream."""
        bids = [[p, q] for p, q in data["bids"]]
        asks = [[p, q] for p, q in data["asks"]]

        if not self.ob_bybit.is_ready or data.get("type") == "snapshot":
            self.ob_bybit.apply_snapshot(bids, asks, data.get("update_id", 0))
        else:
            self.ob_bybit.apply_update(bids, asks, data.get("update_id", 0))

    async def on_bybit_trade(self, data: dict):
        """Proses trade dari Bybit."""
        self.flow_analyzer.add_trade(
            "bybit", data["price"], data["qty"],
            data["side"], data["timestamp"]
        )

    async def on_bybit_liquidation(self, data: dict):
        """Proses liquidation event dari Bybit."""
        self.liq_collector.add_event(
            exchange="bybit",
            side=data["side"],
            price=data["price"],
            qty=data["qty"],
            timestamp=data["timestamp"],
        )
        logger.warning(
            f"[LIQUIDATION][Bybit] {data['side'].upper()} "
            f"${data['value_usd']:,.0f} @ {data['price']}"
        )

    async def on_bybit_open_interest(self, data: dict):
        """Update Open Interest dari Bybit ticker."""
        self.oi_calc.update(
            open_interest=data["open_interest"],
            price=data["price"],
            timestamp=data["timestamp"],
        )

    # ------------------------------------------------------------------
    # Main analysis loop
    # ------------------------------------------------------------------
    async def analysis_loop(self):
        """Loop analisis dan render display secara periodik."""
        while self._running:
            try:
                price = self._current_price or 0

                # Jalankan semua analitik
                ob_data_binance = self.ob_analyzer_binance.analyze(self.ob_binance)
                ob_data_bybit = self.ob_analyzer_bybit.analyze(self.ob_bybit)

                # Gunakan data Binance sebagai primary untuk display
                # (gabungkan imbalance dari kedua exchange)
                ob_display = ob_data_binance
                if ob_data_bybit.get("ready") is not False and ob_data_binance.get("ready") is not False:
                    # Average imbalance dari dua exchange
                    avg_imbalance = (
                        ob_data_binance.get("imbalance_ratio", 0.5) +
                        ob_data_bybit.get("imbalance_ratio", 0.5)
                    ) / 2
                    ob_display = {**ob_data_binance, "imbalance_ratio": avg_imbalance}

                liq_data = self.liq_analyzer.analyze(price) if price else {}
                flow_data = self.flow_analyzer.summary(price, self._prev_price)
                mp_data = self.market_profile.auction_state(price) if price else {}
                oi_data = self.oi_calc.summary()

                # ── Bookmap Stats (Binance order book + trade)
                bookmap_data = None
                binance_tp = self.flow_analyzer.processors.get("binance")
                if self.ob_binance.is_ready and binance_tp is not None:
                    self.bookmap_stats.update(self.ob_binance, binance_tp)
                    bookmap_data = self.bookmap_stats.snapshot(self.ob_binance, binance_tp)

                # ── AMT Confluence Analysis (master analyzer)
                confluence_data = None
                if price and ob_display and flow_data and liq_data and mp_data:
                    confluence_setup = self.confluence_analyzer.analyze(
                        ob_data=ob_display,
                        flow_data=flow_data,
                        liq_data=liq_data,
                        mp_data=mp_data,
                        current_price=price,
                        prev_price=self._prev_price,
                    )
                    confluence_data = {
                        "confluence_score": confluence_setup.confluence_score,
                        "bias": confluence_setup.bias,
                        "strength": confluence_setup.strength,
                        "auction_control": confluence_setup.auction_control,
                        "auction_strength": confluence_setup.auction_strength,
                        "cascade_risk": confluence_setup.cascade_risk,
                        "cascade_prob": confluence_setup.cascade_prob,
                        "va_reaction": confluence_setup.va_reaction,
                        "va_strength": confluence_setup.va_strength,
                        "stop_hunt_detected": confluence_setup.stop_hunt_detected,
                        "stop_hunt_confidence": confluence_setup.stop_hunt_confidence,
                        "entry": confluence_setup.suggested_entry,
                        "stop": confluence_setup.suggested_stop,
                        "target": confluence_setup.suggested_target,
                    }

                # Generate sinyal
                all_signals = []
                if liq_data:
                    all_signals += self.signal_engine.evaluate_liquidation(liq_data)
                if ob_display:
                    all_signals += self.signal_engine.evaluate_order_book(ob_display, "binance+bybit")
                if flow_data:
                    all_signals += self.signal_engine.evaluate_order_flow(flow_data)
                if mp_data:
                    all_signals += self.signal_engine.evaluate_market_profile(mp_data)
                if oi_data:
                    all_signals += self.signal_engine.evaluate_oi(oi_data, "bybit")

                # Render display
                self.display.render(
                    ob_data=ob_display,
                    liq_data=liq_data,
                    flow_data=flow_data,
                    mp_data=mp_data,
                    oi_data=oi_data,
                    confluence_data=confluence_data,
                    bookmap_data=bookmap_data,
                    signals=self.signal_engine.active_signals(),
                )

                # Store latest JSON-safe snapshot for web/API polling.
                self.latest_snapshot = build_snapshot(
                    symbol=self.symbol,
                    price=price,
                    ob_data=ob_display,
                    liq_data=liq_data,
                    flow_data=flow_data,
                    mp_data=mp_data,
                    oi_data=oi_data,
                    confluence_data=confluence_data,
                    bookmap_data=bookmap_data,
                    signals=self.signal_engine.active_signals(),
                    connected=bool(price) and (self.ob_binance.is_ready or self.ob_bybit.is_ready),
                )

            except Exception as e:
                logger.error(f"Analysis loop error: {e}")

            await asyncio.sleep(self.refresh_rate)

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------
    async def start(self):
        """Mulai semua WebSocket streams dan analysis loop secara concurrent."""
        self._running = True

        # Inisialisasi WebSocket clients
        binance_ws = BinanceWebSocket(
            symbol=self.symbol,
            on_orderbook=self.on_binance_orderbook,
            on_trade=self.on_binance_trade,
            on_liquidation=self.on_binance_liquidation,
        )

        bybit_ws = BybitWebSocket(
            symbol=self.symbol,
            on_orderbook=self.on_bybit_orderbook,
            on_trade=self.on_bybit_trade,
            on_liquidation=self.on_bybit_liquidation,
            on_open_interest=self.on_bybit_open_interest,
        )

        print(f"\n  Connecting to Binance Futures + Bybit Linear for {self.symbol}...")
        print(f"  Starting AMT Liquidation Analysis System...\n")

        # Jalankan semua tasks secara concurrent
        await asyncio.gather(
            binance_ws.connect(),
            bybit_ws.connect(),
            self.analysis_loop(),
        )

    def stop(self):
        """Hentikan sistem."""
        self._running = False
        print("\n\n  System stopped. Goodbye.\n")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="AMT Liquidation Analysis System — Binance + Bybit"
    )
    parser.add_argument(
        "--symbol", type=str, default="BTCUSDT",
        help="Trading pair symbol (default: BTCUSDT)"
    )
    parser.add_argument(
        "--refresh", type=float, default=1.0,
        help="Display refresh rate in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path ke file config threshold eksternal (JSON/YAML). Opsional."
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Muat config threshold eksternal bila diberikan (sebelum sistem dibuat,
    # agar BookmapStats mengambil nilai yang sudah ditimpa).
    if args.config:
        from config import load_config_file
        try:
            loaded = load_config_file(args.config)
            print(f"  Config dimuat dari {args.config}: {', '.join(loaded.keys()) or 'tidak ada symbol'}")
        except (FileNotFoundError, ValueError, ImportError) as e:
            print(f"  [config] Gagal memuat '{args.config}': {e}")
            print(f"  Lanjut dengan threshold default bawaan.")

    system = AMTSystem(symbol=args.symbol, refresh_rate=args.refresh)

    # Handle Ctrl+C dengan graceful shutdown
    def handle_exit(sig, frame):
        system.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    try:
        asyncio.run(system.start())
    except KeyboardInterrupt:
        system.stop()


if __name__ == "__main__":
    main()
