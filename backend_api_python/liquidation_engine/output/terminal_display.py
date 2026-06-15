"""
output/terminal_display.py
Tampilan terminal real-time dengan color coding untuk AMT Liquidation Analysis.
Menggunakan colorama untuk cross-platform color support.
"""

import os
import time
from datetime import datetime
from typing import List, Optional

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
except ImportError:
    # colorama is a CLI-only dependency. When this module is imported in a
    # headless web backend that never renders to a terminal, fall back to
    # no-op color codes so importing AMTSystem does not require colorama.
    class _NoColor:
        def __getattr__(self, _):
            return ""
    Fore = Back = Style = _NoColor()
    def init(*_args, **_kwargs):
        return None

from signals.signal_engine import Signal


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def severity_color(severity: str) -> str:
    return {
        "LOW": Fore.CYAN,
        "MEDIUM": Fore.YELLOW,
        "HIGH": Fore.RED,
        "CRITICAL": Fore.WHITE + Back.RED,
    }.get(severity, Fore.WHITE)


def side_color(side: str) -> str:
    s = side.upper()
    if s in ("BUY", "LONG", "LONG_BUILDUP", "SHORT_COVERING"):
        return Fore.GREEN
    if s in ("SELL", "SHORT", "SHORT_BUILDUP", "LONG_UNWINDING"):
        return Fore.RED
    return Fore.YELLOW


def format_usd(val: float) -> str:
    if val >= 1_000_000:
        return f"${val/1_000_000:.2f}M"
    if val >= 1_000:
        return f"${val/1_000:.1f}K"
    return f"${val:.2f}"


def format_bar(ratio: float, width: int = 20) -> str:
    """
    Render imbalance bar.
    ratio: 0.0 (full ask) → 1.0 (full bid)
    Kiri = ask (merah), Kanan = bid (hijau)
    """
    bid_len = int(ratio * width)
    ask_len = width - bid_len
    bar = Fore.RED + "█" * ask_len + Fore.GREEN + "█" * bid_len + Style.RESET_ALL
    return bar


class TerminalDisplay:
    """
    Render dashboard AMT Liquidation Analysis di terminal.
    Panggil render() setiap cycle untuk update tampilan.
    """

    def __init__(self, symbol: str, refresh_rate: float = 1.0):
        self.symbol = symbol
        self.refresh_rate = refresh_rate
        self._last_render = 0.0

    def should_render(self) -> bool:
        return (time.time() - self._last_render) >= self.refresh_rate

    def render(
        self,
        ob_data: dict = None,
        liq_data: dict = None,
        flow_data: dict = None,
        mp_data: dict = None,
        oi_data: dict = None,
        confluence_data: dict = None,
        bookmap_data: dict = None,
        signals: List[Signal] = None,
    ):
        """Render full dashboard."""
        if not self.should_render():
            return

        self._last_render = time.time()
        clear_screen()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(self._header(now))

        if confluence_data:
            print(self._section_confluence(confluence_data))

        if ob_data and ob_data.get("ready") is not False:
            print(self._section_order_book(ob_data))

        if bookmap_data:
            print(self._section_bookmap(bookmap_data))

        if flow_data:
            print(self._section_order_flow(flow_data))

        if liq_data:
            print(self._section_liquidation(liq_data))

        if mp_data:
            print(self._section_market_profile(mp_data))

        if oi_data:
            print(self._section_oi(oi_data))

        if signals:
            print(self._section_signals(signals))

        print(self._footer())

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    def _header(self, now: str) -> str:
        width = 80
        title = f"  AMT LIQUIDATION ANALYZER — {self.symbol}  "
        pad = (width - len(title)) // 2
        line = "═" * width
        return (
            f"\n{Fore.CYAN}{Style.BRIGHT}{line}\n"
            f"{' ' * pad}{title}\n"
            f"{line}{Style.RESET_ALL}\n"
            f"  {Fore.WHITE}Time: {now}   "
            f"Press Ctrl+C to exit\n"
        )

    # ------------------------------------------------------------------
    # AMT Confluence Section (MASTER ANALYSIS)
    # ------------------------------------------------------------------
    def _section_confluence(self, data: dict) -> str:
        """Render AMT Confluence Score — ringkasan keputusan trading utama."""
        score = data.get("confluence_score", 0)
        bias = data.get("bias", "NEUTRAL")
        strength = data.get("strength", "WEAK")
        entry = data.get("entry")
        stop = data.get("stop")
        target = data.get("target")

        auction = data.get("auction_control", "BALANCED")
        auction_str = data.get("auction_strength", 0)
        cascade = data.get("cascade_risk", "LOW")
        cascade_prob = data.get("cascade_prob", 0)
        va_reaction = data.get("va_reaction", "UNDECIDED")
        va_str = data.get("va_strength", 0)
        stop_hunt = data.get("stop_hunt_detected", False)
        stop_hunt_conf = data.get("stop_hunt_confidence", 0)

        # Color berdasarkan bias dan strength
        bias_col = Fore.GREEN if bias == "LONG" else (Fore.RED if bias == "SHORT" else Fore.YELLOW)
        strength_col = {
            "CRITICAL": Fore.WHITE + Back.RED,
            "STRONG": Fore.RED,
            "MODERATE": Fore.YELLOW,
            "WEAK": Fore.CYAN,
        }.get(strength, Fore.WHITE)

        # Score bar visual
        filled = int(score / 10)  # 0-100 → 0-10 segments
        bar = Fore.GREEN + "█" * filled + Fore.RED + "░" * (10 - filled) + Style.RESET_ALL

        lines = [
            f"{Fore.CYAN}{'═'*80}",
            f"{Fore.WHITE}{Style.BRIGHT}  🎯 AMT CONFLUENCE SCORE (Master Analysis){Style.RESET_ALL}",
            f"  Score: {bar}  {Fore.WHITE}{score:.1f}/100{Style.RESET_ALL}  "
            f"Bias: {bias_col}{Style.BRIGHT}{bias}{Style.RESET_ALL}  "
            f"Strength: {strength_col}{strength}{Style.RESET_ALL}",
        ]

        # Component scores
        lines.append(f"  {Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")

        # Auction Imbalance
        auction_col = Fore.GREEN if auction == "BUYER" else (Fore.RED if auction == "SELLER" else Fore.YELLOW)
        lines.append(
            f"  Auction Imbalance: {auction_col}{auction}{Style.RESET_ALL} "
            f"({Fore.WHITE}{auction_str:.1f}%{Style.RESET_ALL})"
        )

        # Cascade Risk
        cascade_col = {
            "CRITICAL": Fore.WHITE + Back.RED,
            "HIGH": Fore.RED,
            "MEDIUM": Fore.YELLOW,
            "LOW": Fore.GREEN,
        }.get(cascade, Fore.CYAN)
        lines.append(
            f"  Cascade Risk: {cascade_col}{cascade}{Style.RESET_ALL} "
            f"(prob: {Fore.WHITE}{cascade_prob:.1f}%{Style.RESET_ALL})"
        )

        # VA Reaction
        va_col = Fore.GREEN if va_reaction == "ACCEPTANCE" else (Fore.RED if va_reaction == "REJECTION" else Fore.YELLOW)
        lines.append(
            f"  VA Reaction: {va_col}{va_reaction}{Style.RESET_ALL} "
            f"({Fore.WHITE}{va_str:.1f}%{Style.RESET_ALL})"
        )

        # Stop Hunt
        hunt_col = Fore.RED if stop_hunt else Fore.GREEN
        hunt_txt = f"YES ({stop_hunt_conf:.0f}% conf)" if stop_hunt else "NO"
        lines.append(f"  Stop Hunt Detected: {hunt_col}{hunt_txt}{Style.RESET_ALL}")

        # Trading Levels
        lines.append(f"  {Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
        if entry and stop and target:
            lines.append(
                f"  {Style.BRIGHT}Entry{Style.RESET_ALL}: {Fore.WHITE}{entry:.2f}{Style.RESET_ALL}  "
                f"{Style.BRIGHT}Stop{Style.RESET_ALL}: {Fore.WHITE}{stop:.2f}{Style.RESET_ALL}  "
                f"{Style.BRIGHT}Target{Style.RESET_ALL}: {Fore.WHITE}{target:.2f}{Style.RESET_ALL}"
            )
            r_r = abs(target - entry) / (entry - stop) if entry != stop else 0
            lines.append(f"  Risk/Reward Ratio: {Fore.YELLOW}{r_r:.2f}:1{Style.RESET_ALL}")
        else:
            lines.append(f"  {Fore.YELLOW}Levels not available (low confluence){Style.RESET_ALL}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Bookmap Stats Section
    # ------------------------------------------------------------------
    def _section_bookmap(self, data: dict) -> str:
        """Render statistik gaya Bookmap dengan label confidence (akurat/estimasi)."""
        composite = data.get("composite_score", 0)
        persistence = data.get("persistence", {})
        absorption = data.get("absorption", {})
        depletion = data.get("depletion", {})
        iceberg = data.get("iceberg", {})
        divergence = data.get("divergence", {})

        def conf_tag(metric: dict) -> str:
            c = metric.get("confidence", "")
            if c == "accurate":
                return f"{Fore.GREEN}[accurate]{Style.RESET_ALL}"
            if c == "estimate":
                return f"{Fore.YELLOW}[estimate]{Style.RESET_ALL}"
            return ""

        comp_col = Fore.GREEN if composite >= 60 else (Fore.YELLOW if composite >= 35 else Fore.CYAN)
        filled = int(composite / 10)
        bar = Fore.GREEN + "█" * filled + Fore.RED + "░" * (10 - filled) + Style.RESET_ALL

        lines = [
            f"{Fore.CYAN}{'─'*80}",
            f"{Fore.YELLOW}{Style.BRIGHT}  🗺  BOOKMAP STATS (Binance L2 + Trades){Style.RESET_ALL}",
            f"  Composite: {bar}  {comp_col}{composite:.1f}/100{Style.RESET_ALL}",
        ]

        # Absorption
        ab_dir = absorption.get("direction", "NEUTRAL")
        ab_col = Fore.GREEN if "BUYERS" in ab_dir else (Fore.RED if "SELLERS" in ab_dir else Fore.WHITE)
        lines.append(
            f"  Absorption {conf_tag(absorption)}: {ab_col}{absorption.get('score', 0):.0f}{Style.RESET_ALL} "
            f"(ratio {absorption.get('ratio', 0)}, {ab_dir})"
        )

        # Depletion
        dep_sig = depletion.get("signal", "NO_DATA")
        dep_col = Fore.GREEN if dep_sig == "ASK_DEPLETION" else (Fore.RED if dep_sig == "BID_DEPLETION" else Fore.WHITE)
        lines.append(
            f"  Depletion {conf_tag(depletion)}: {dep_col}{dep_sig}{Style.RESET_ALL} "
            f"({depletion.get('score', 0):.0f}) — {depletion.get('description', '')}"
        )

        # Persistence
        plist = persistence.get("persistent_levels", [])
        lines.append(
            f"  Heatmap Persistence {conf_tag(persistence)}: "
            f"{Fore.WHITE}{persistence.get('count', 0)} level bertahan{Style.RESET_ALL} "
            f"(score {persistence.get('score', 0):.0f})"
        )
        for lv in plist[:2]:
            col = Fore.GREEN if lv["side"] == "bid" else Fore.RED
            lines.append(
                f"    {col}{lv['price']:.2f} [{lv['side']}]{Style.RESET_ALL} "
                f"dwell {lv['dwell_seconds']}s, refill {lv['refill_count']}x"
            )

        # Iceberg
        ice_count = iceberg.get("count", 0)
        if ice_count > 0:
            lines.append(
                f"  {Fore.MAGENTA}🧊 Iceberg {conf_tag(iceberg)}: {ice_count} level "
                f"(score {iceberg.get('score', 0):.0f}){Style.RESET_ALL}"
            )

        # Divergence
        div = divergence.get("divergence")
        if div:
            div_col = Fore.GREEN if "BEARISH_ABSORBED" in div["type"] else Fore.RED
            lines.append(f"  {div_col}⚡ {conf_tag(divergence)} {div['description']}{Style.RESET_ALL}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Order Book Section
    # ------------------------------------------------------------------
    def _section_order_book(self, data: dict) -> str:
        imbalance = data.get("imbalance_ratio", 0.5)
        pressure = data.get("pressure", {})
        signal = pressure.get("signal", "BALANCED")
        desc = pressure.get("description", "")
        bid_vol = data.get("bid_volume", 0)
        ask_vol = data.get("ask_volume", 0)
        spread = data.get("spread", 0)
        mid = data.get("mid_price", 0)
        trend = data.get("imbalance_trend", "NEUTRAL")

        # Walls
        bid_walls = data.get("bid_walls", [])
        ask_walls = data.get("ask_walls", [])
        icebergs = data.get("icebergs", {})

        col = side_color(signal)
        bar = format_bar(imbalance)

        lines = [
            f"{Fore.CYAN}{'─'*80}",
            f"{Fore.YELLOW}{Style.BRIGHT}  📊 ORDER BOOK ANALYSIS{Style.RESET_ALL}",
            f"  Mid: {Fore.WHITE}{mid:.2f}{Style.RESET_ALL}  "
            f"Spread: {Fore.WHITE}{spread:.4f}{Style.RESET_ALL}  "
            f"Trend: {Fore.CYAN}{trend}",
            f"  Bid Vol: {Fore.GREEN}{bid_vol:.2f}{Style.RESET_ALL}  "
            f"Ask Vol: {Fore.RED}{ask_vol:.2f}{Style.RESET_ALL}  "
            f"Ratio: {col}{imbalance:.3f}",
            f"  ASK {'█'*0}  {bar}  BID   {col}{signal}{Style.RESET_ALL}",
            f"  {desc}",
        ]

        if bid_walls:
            walls_str = "  ".join([f"{p:.2f}({q:.2f})" for p, q in bid_walls[:3]])
            lines.append(f"  {Fore.GREEN}BID WALLS: {walls_str}{Style.RESET_ALL}")
        if ask_walls:
            walls_str = "  ".join([f"{p:.2f}({q:.2f})" for p, q in ask_walls[:3]])
            lines.append(f"  {Fore.RED}ASK WALLS: {walls_str}{Style.RESET_ALL}")

        total_ice = icebergs.get("total_detected", 0)
        if total_ice > 0:
            lines.append(f"  {Fore.MAGENTA}🧊 ICEBERG: {total_ice} level terdeteksi{Style.RESET_ALL}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Order Flow Section
    # ------------------------------------------------------------------
    def _section_order_flow(self, data: dict) -> str:
        cvd = data.get("combined_cvd", 0)
        cvd_trend = data.get("cvd_trend", "N/A")
        delta_60 = data.get("delta_60s", 0)
        delta_10 = data.get("delta_10s", 0)
        dr_60 = data.get("delta_ratio_60s", 0)
        vwap = data.get("vwap_60s")
        divergence = data.get("divergence")
        large = data.get("large_trades", {})

        cvd_col = Fore.GREEN if cvd > 0 else Fore.RED
        d60_col = Fore.GREEN if delta_60 > 0 else Fore.RED
        d10_col = Fore.GREEN if delta_10 > 0 else Fore.RED

        lines = [
            f"{Fore.CYAN}{'─'*80}",
            f"{Fore.YELLOW}{Style.BRIGHT}  📈 ORDER FLOW (CVD & DELTA){Style.RESET_ALL}",
            f"  CVD: {cvd_col}{cvd:+.2f}{Style.RESET_ALL}  "
            f"Trend: {Fore.CYAN}{cvd_trend}{Style.RESET_ALL}  "
            f"VWAP: {Fore.WHITE}{vwap or 'N/A'}",
            f"  Delta 60s: {d60_col}{delta_60:+.4f}{Style.RESET_ALL} "
            f"({dr_60:+.3f})  "
            f"Delta 10s: {d10_col}{delta_10:+.4f}",
        ]

        if large.get("count", 0) > 0:
            dom_col = Fore.GREEN if large.get("dominance") == "BUYER" else Fore.RED
            lines.append(
                f"  Large Trades: {large['count']} trades — "
                f"Buy: {Fore.GREEN}{format_usd(large.get('buy_value_usd', 0))}{Style.RESET_ALL}  "
                f"Sell: {Fore.RED}{format_usd(large.get('sell_value_usd', 0))}{Style.RESET_ALL}  "
                f"Dominant: {dom_col}{large.get('dominance')}{Style.RESET_ALL}"
            )

        if divergence:
            div_col = Fore.GREEN if "BULLISH" in divergence["type"] else Fore.RED
            lines.append(f"  {div_col}⚡ {divergence['description']}{Style.RESET_ALL}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Liquidation Section
    # ------------------------------------------------------------------
    def _section_liquidation(self, data: dict) -> str:
        price = data.get("current_price", 0)
        total_60 = data.get("total_liq_60s_usd", 0)
        long_liq = data.get("long_liq_60s_usd", 0)
        short_liq = data.get("short_liq_60s_usd", 0)
        dominant = data.get("dominant_60s", "")
        cascade = data.get("cascade_risk", {})
        squeeze = data.get("squeeze_signal", {})
        nearest_above = data.get("nearest_above")
        nearest_below = data.get("nearest_below")
        heatmap = data.get("heatmap", [])

        cascade_col = {
            "LOW": Fore.CYAN, "MEDIUM": Fore.YELLOW,
            "HIGH": Fore.RED, "CRITICAL": Fore.WHITE + Back.RED,
        }.get(cascade.get("level", "LOW"), Fore.CYAN)

        dom_col = Fore.RED if "LONG" in dominant else Fore.GREEN

        lines = [
            f"{Fore.CYAN}{'─'*80}",
            f"{Fore.YELLOW}{Style.BRIGHT}  💥 LIQUIDATION ANALYSIS{Style.RESET_ALL}",
            f"  Total Liq 60s: {Fore.WHITE}{format_usd(total_60)}{Style.RESET_ALL}  "
            f"Long Liq: {Fore.RED}{format_usd(long_liq)}{Style.RESET_ALL}  "
            f"Short Liq: {Fore.GREEN}{format_usd(short_liq)}{Style.RESET_ALL}",
            f"  Dominant: {dom_col}{dominant}{Style.RESET_ALL}  "
            f"Cascade Risk: {cascade_col}{cascade.get('level', 'N/A')} "
            f"({cascade.get('score', 0):.1f}/100){Style.RESET_ALL}",
        ]

        squeeze_sig = squeeze.get("signal", "")
        if squeeze_sig != "BALANCED":
            sq_col = Fore.RED if "LONG" in squeeze_sig else Fore.GREEN
            lines.append(f"  {sq_col}⚠ {squeeze.get('description', '')}{Style.RESET_ALL}")

        if nearest_above:
            prox_col = Fore.RED if nearest_above.get("is_close") else Fore.WHITE
            lines.append(
                f"  Nearest Above: {prox_col}{nearest_above['zone_mid']:.2f} "
                f"({nearest_above['distance_pct']:.2f}%) "
                f"— {format_usd(nearest_above['value_usd'])} "
                f"[{nearest_above['dominant_side']}]{Style.RESET_ALL}"
            )

        if nearest_below:
            prox_col = Fore.RED if nearest_below.get("is_close") else Fore.WHITE
            lines.append(
                f"  Nearest Below: {prox_col}{nearest_below['zone_mid']:.2f} "
                f"({nearest_below['distance_pct']:.2f}%) "
                f"— {format_usd(nearest_below['value_usd'])} "
                f"[{nearest_below['dominant_side']}]{Style.RESET_ALL}"
            )

        # Mini heatmap (top 5)
        if heatmap:
            lines.append(f"  {Fore.CYAN}Liquidation Heatmap (top zones):{Style.RESET_ALL}")
            for entry in heatmap[:5]:
                dist = entry["distance_pct"]
                bar = entry["bar"]
                dom = entry["dominant"]
                val = format_usd(entry["value_usd"])
                arrow = "▲" if dist > 0 else "▼"
                col = Fore.RED if dom == "LONG" else Fore.GREEN
                lines.append(
                    f"    {Fore.WHITE}{entry['zone_mid']:>10.2f} {arrow}{abs(dist):.2f}%  "
                    f"{col}{bar}{Style.RESET_ALL}  {val} [{dom}]"
                )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Market Profile Section
    # ------------------------------------------------------------------
    def _section_market_profile(self, data: dict) -> str:
        state = data.get("state", "N/A")
        desc = data.get("description", "")
        poc = data.get("poc", 0)
        va_low = data.get("va_low", 0)
        va_high = data.get("va_high", 0)
        price = data.get("current_price", 0)
        sh = data.get("session_high", 0)
        sl = data.get("session_low", 0)

        state_col = {
            "BALANCING_AT_POC": Fore.CYAN,
            "BALANCING": Fore.CYAN,
            "TRENDING_UP": Fore.GREEN,
            "TRENDING_DOWN": Fore.RED,
            "TESTING_VA_HIGH": Fore.YELLOW,
            "TESTING_VA_LOW": Fore.YELLOW,
        }.get(state, Fore.WHITE)

        lines = [
            f"{Fore.CYAN}{'─'*80}",
            f"{Fore.YELLOW}{Style.BRIGHT}  🏛  MARKET PROFILE (AMT){Style.RESET_ALL}",
            f"  State: {state_col}{Style.BRIGHT}{state}{Style.RESET_ALL}",
            f"  {desc}",
            f"  POC: {Fore.MAGENTA}{poc:.2f}{Style.RESET_ALL}  "
            f"VA: {Fore.CYAN}{va_low:.2f} — {va_high:.2f}{Style.RESET_ALL}  "
            f"Price: {Fore.WHITE}{price:.2f}",
            f"  Session: H={Fore.GREEN}{sh:.2f}{Style.RESET_ALL}  "
            f"L={Fore.RED}{sl:.2f}{Style.RESET_ALL}",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Open Interest Section
    # ------------------------------------------------------------------
    def _section_oi(self, data: dict) -> str:
        signal = data.get("signal", "N/A")
        interp = data.get("interpretation", "")
        oi = data.get("current_oi", 0)
        delta_pct = data.get("oi_delta_pct_60s", 0)

        col = {
            "LONG_BUILDUP": Fore.GREEN,
            "SHORT_BUILDUP": Fore.RED,
            "SHORT_COVERING": Fore.YELLOW,
            "LONG_UNWINDING": Fore.YELLOW,
        }.get(signal, Fore.WHITE)

        delta_col = Fore.GREEN if delta_pct > 0 else Fore.RED

        lines = [
            f"{Fore.CYAN}{'─'*80}",
            f"{Fore.YELLOW}{Style.BRIGHT}  📉 OPEN INTEREST{Style.RESET_ALL}",
            f"  OI: {Fore.WHITE}{oi:,.2f}{Style.RESET_ALL}  "
            f"Delta 60s: {delta_col}{delta_pct:+.4f}%{Style.RESET_ALL}  "
            f"Signal: {col}{signal}{Style.RESET_ALL}",
            f"  {interp}",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Signals Section
    # ------------------------------------------------------------------
    def _section_signals(self, signals: List[Signal]) -> str:
        if not signals:
            return ""

        lines = [
            f"{Fore.CYAN}{'─'*80}",
            f"{Fore.YELLOW}{Style.BRIGHT}  🚨 ACTIVE SIGNALS ({len(signals)}){Style.RESET_ALL}",
        ]

        # Urutkan dari severity tertinggi
        sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_sigs = sorted(signals, key=lambda s: sev_order.get(s.severity, 4))

        for sig in sorted_sigs[:8]:  # max 8 sinyal ditampilkan
            col = severity_color(sig.severity)
            age = int(sig.age_seconds())
            lines.append(
                f"  {col}[{sig.severity:>8}]{Style.RESET_ALL}  "
                f"{Fore.WHITE}{sig.signal_type:<20}{Style.RESET_ALL}  "
                f"{sig.description[:55]}  "
                f"{Fore.WHITE}({age}s ago){Style.RESET_ALL}"
            )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    def _footer(self) -> str:
        return (
            f"{Fore.CYAN}{'═'*80}{Style.RESET_ALL}\n"
            f"  {Fore.WHITE}Binance Futures + Bybit Linear | "
            f"AMT Liquidation Analysis System{Style.RESET_ALL}\n"
        )
