# ============================================================
# Fractal Indicator: Rolling Volume Profile (POC / VAH / VAL)
# ------------------------------------------------------------
# A true TPO/Volume-Profile histogram draws horizontal bars on the
# PRICE axis. The Fractal plot contract is one value PER BAR on the
# TIME axis, so the histogram bars themselves cannot be drawn from an
# indicator script (that needs a frontend overlay).
#
# What this indicator DOES deliver — the actionable part traders use:
#   - POC  (Point of Control): price level with the most traded volume
#   - VAH  (Value Area High)  : top of the 70% value area
#   - VAL  (Value Area Low)   : bottom of the 70% value area
# computed over a rolling lookback window, plotted as evolving levels.
#
# Signals: long when price reclaims the value area from below (crosses
# up through VAL); short when price loses the value area (crosses down
# through VAH). Fixed risk handled by the engine via @strategy.
#
# Docs: docs/SIGNAL_EXECUTION_STANDARD_CN.md
# ============================================================

my_indicator_name = "Volume Profile (POC/VAH/VAL)"
my_indicator_description = "Rolling volume profile levels: Point of Control and 70% value area (VAH/VAL), with value-area breakout entries."

# --- Fractal execution contract (v1) ---
# signal_form: four_way
# exit_owner: engine
# flip_mode: R2

# @strategy stopLossPct 0.03
# @strategy takeProfitPct 0.06
# @strategy entryPct 0.25
# @strategy trailingEnabled false
# @strategy tradeDirection both

# @param lookback int 120 Bars in the rolling profile window
# @param bins int 24 Number of price buckets in the profile
# @param value_area float 0.7 Value area fraction (0.7 = 70%)


def edge(s):
    s = s.fillna(False).astype(bool)
    return s & ~s.shift(1).fillna(False)


lookback = int(params.get("lookback", 120))
bins = int(params.get("bins", 24))
value_area = float(params.get("value_area", 0.7))

# Guard rails so bad params can't crash the sandbox.
if lookback < 10:
    lookback = 10
if bins < 4:
    bins = 4
if value_area <= 0 or value_area >= 1:
    value_area = 0.7

df = df.copy()

high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
volume = df["volume"].astype(float).fillna(0.0)
typical = (high + low + close) / 3.0

n = len(df)
poc = [float("nan")] * n
vah = [float("nan")] * n
val = [float("nan")] * n


def _profile_levels(win_low, win_high, win_typ, win_vol):
    """Return (poc, vah, val) for one window, or None if degenerate."""
    lo = float(win_low.min())
    hi = float(win_high.max())
    if not (hi > lo):
        return None

    # Bucket every bar's volume by its typical price.
    edges = np.linspace(lo, hi, bins + 1)
    # np.digitize returns 1..bins; clamp into 0..bins-1.
    idx = np.digitize(win_typ.to_numpy(), edges) - 1
    idx = np.clip(idx, 0, bins - 1)

    hist = np.zeros(bins, dtype=float)
    vols = win_vol.to_numpy()
    for b, v in zip(idx, vols):
        hist[b] += v

    total = hist.sum()
    if total <= 0:
        return None

    centers = (edges[:-1] + edges[1:]) / 2.0
    poc_bin = int(hist.argmax())
    poc_price = float(centers[poc_bin])

    # Grow the value area outward from the POC until it covers `value_area`
    # of total volume (standard Market Profile expansion rule).
    target = total * value_area
    covered = hist[poc_bin]
    lo_bin = poc_bin
    hi_bin = poc_bin
    while covered < target and (lo_bin > 0 or hi_bin < bins - 1):
        below = hist[lo_bin - 1] if lo_bin > 0 else -1.0
        above = hist[hi_bin + 1] if hi_bin < bins - 1 else -1.0
        if above >= below:
            hi_bin += 1
            covered += hist[hi_bin]
        else:
            lo_bin -= 1
            covered += hist[lo_bin]

    vah_price = float(edges[hi_bin + 1])
    val_price = float(edges[lo_bin])
    return poc_price, vah_price, val_price


# Rolling window: recompute the profile as the window slides. Loop is
# unavoidable here (each window is an independent aggregation), but it
# stays O(n * lookback) which is fine for chart-length series.
for i in range(n):
    start = i - lookback + 1
    if start < 0:
        continue
    sl = slice(start, i + 1)
    levels = _profile_levels(low.iloc[sl], high.iloc[sl], typical.iloc[sl], volume.iloc[sl])
    if levels is None:
        continue
    poc[i], vah[i], val[i] = levels

poc_s = pd.Series(poc, index=df.index, dtype="float64")
vah_s = pd.Series(vah, index=df.index, dtype="float64")
val_s = pd.Series(val, index=df.index, dtype="float64")

# --- Signals: value-area breakout (edge-triggered, confirm on close) ---
prev_close = close.shift(1)

cross_up_val = (close > val_s) & (prev_close <= val_s)
cross_down_vah = (close < vah_s) & (prev_close >= vah_s)

raw_open_long = cross_up_val & (close < poc_s)   # reclaiming value from below
raw_open_short = cross_down_vah & (close > poc_s)  # losing value from above
raw_close_long = cross_down_vah
raw_close_short = cross_up_val

df["open_long"] = edge(raw_open_long.fillna(False))
df["open_short"] = edge(raw_open_short.fillna(False))
df["close_long"] = edge(raw_close_long.fillna(False))
df["close_short"] = edge(raw_close_short.fillna(False))

open_long_marks = [
    low.iloc[i] * 0.995 if bool(df["open_long"].iloc[i]) else None for i in range(n)
]
open_short_marks = [
    high.iloc[i] * 1.005 if bool(df["open_short"].iloc[i]) else None for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {
            "name": "POC",
            "data": poc_s.ffill().fillna(0).tolist(),
            "color": "#FFB300",
            "overlay": True,
        },
        {
            "name": "VAH",
            "data": vah_s.ffill().fillna(0).tolist(),
            "color": "#26A69A",
            "overlay": True,
        },
        {
            "name": "VAL",
            "data": val_s.ffill().fillna(0).tolist(),
            "color": "#EF5350",
            "overlay": True,
        },
    ],
    "signals": [
        {"type": "buy", "text": "L", "data": open_long_marks, "color": "#00E676"},
        {"type": "sell", "text": "S", "data": open_short_marks, "color": "#FF5252"},
    ],
}
