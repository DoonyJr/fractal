"""
config.py
Threshold per-coin untuk Bookmap Stats.

Tiap coin punya karakter likuiditas berbeda: BTC dalam dan tebal, sedangkan
coin kecil seperti ZEC/HYPE lebih tipis dan volatil. Threshold yang sama tidak
cocok untuk semua. File ini memisahkan ANGKA dari LOGIC — ubah di sini saja,
tidak perlu sentuh bookmap_stats.py.

Cara pakai:
    from config import get_config
    cfg = get_config("BTCUSDT")   # otomatis fallback ke DEFAULT jika tak terdaftar

Cara kalibrasi:
    Jalankan sistem beberapa saat, amati nilai mentah (ratio, rate/s, dwell).
    Sesuaikan *_scale dan *_strong agar skor 0-100 tersebar wajar untuk coin itu.
"""

from dataclasses import dataclass, field, replace
from typing import Dict


@dataclass(frozen=True)
class BookmapConfig:
    """Semua threshold yang dipakai BookmapStats. Frozen agar tidak diubah tak sengaja saat runtime."""

    # ── Deteksi level besar ───────────────────────────────────────────
    wall_multiplier: float = 5.0       # qty >= multiplier * rata-rata = "wall"
    track_levels: int = 50             # kedalaman level yang dilacak
    persistence_window: int = 300      # umur maksimum tracker (detik)

    # ── 1. Heatmap Persistence ────────────────────────────────────────
    min_dwell: float = 10.0            # detik minimum agar level dianggap "persisten"
    persistence_norm: float = 300.0    # dwell (detik) yang dipetakan ke skor 100

    # ── 2. Absorption Ratio ───────────────────────────────────────────
    absorption_scale: float = 10.0     # ratio dibagi nilai ini -> skor (lebih kecil = lebih sensitif)

    # ── 3. Liquidity Depletion Speed ──────────────────────────────────
    depletion_strong: float = 50.0     # unit/detik yang dianggap "kuat" (skor 100)

    # ── 4. Iceberg Refill Rate ────────────────────────────────────────
    iceberg_min_refills: int = 3       # minimal refill agar dianggap iceberg
    iceberg_norm: float = 10.0         # refill count yang dipetakan ke skor 100


# Default untuk coin yang tidak punya override khusus.
DEFAULT = BookmapConfig()

# Override per-symbol. Pakai replace() agar hanya field yang relevan diubah.
# Catatan: ini titik awal berdasarkan profil likuiditas umum — kalibrasi sendiri
# setelah mengamati data nyata tiap coin.
_OVERRIDES: Dict[str, BookmapConfig] = {
    # BTC: likuiditas paling dalam, butuh ambang besar agar tak kebanyakan noise.
    "BTCUSDT": replace(
        DEFAULT,
        wall_multiplier=6.0,
        depletion_strong=80.0,     # depth besar, laju makan tinggi itu normal
        absorption_scale=15.0,     # volume besar, skala dinaikkan
    ),
    # ETH: dalam tapi di bawah BTC.
    "ETHUSDT": replace(
        DEFAULT,
        wall_multiplier=5.0,
        depletion_strong=60.0,
        absorption_scale=12.0,
    ),
    # ZEC: likuiditas tipis, wall kecil pun signifikan; lebih sensitif.
    "ZECUSDT": replace(
        DEFAULT,
        wall_multiplier=4.0,
        depletion_strong=15.0,
        absorption_scale=5.0,
        min_dwell=8.0,
    ),
    # HYPE: coin baru/volatil, likuiditas tipis & cepat berubah.
    "HYPEUSDT": replace(
        DEFAULT,
        wall_multiplier=4.0,
        depletion_strong=20.0,
        absorption_scale=6.0,
        min_dwell=6.0,
        persistence_norm=180.0,    # level jarang bertahan selama coin besar
    ),
}


def get_config(symbol: str) -> BookmapConfig:
    """
    Ambil config untuk symbol. Cocokkan case-insensitive; fallback ke DEFAULT
    jika symbol tidak terdaftar.
    """
    if not symbol:
        return DEFAULT
    return _OVERRIDES.get(symbol.upper(), DEFAULT)


def register_config(symbol: str, config: BookmapConfig) -> None:
    """Tamb/timpa config untuk symbol secara programatik (mis. dari file user)."""
    _OVERRIDES[symbol.upper()] = config


# Field valid yang boleh muncul di file config eksternal.
_VALID_FIELDS = set(BookmapConfig.__dataclass_fields__.keys())


def _config_from_dict(data: dict, base: BookmapConfig = DEFAULT) -> BookmapConfig:
    """
    Bangun BookmapConfig dari dict, mulai dari `base` lalu timpa field yang ada.
    Field tak dikenal diabaikan dengan peringatan agar typo tidak diam-diam terlewat.
    """
    clean = {}
    for k, v in data.items():
        if k in _VALID_FIELDS:
            clean[k] = v
        else:
            print(f"[config] WARNING: field tak dikenal '{k}' diabaikan")
    return replace(base, **clean)


def load_config_file(path: str) -> Dict[str, BookmapConfig]:
    """
    Muat threshold dari file eksternal dan daftarkan ke _OVERRIDES.
    Mendukung JSON (built-in) dan YAML (jika PyYAML terpasang).

    Struktur file (key = symbol, nilai = dict threshold):
        {
          "default": { "wall_multiplier": 5.0 },      # opsional, jadi basis semua
          "BTCUSDT": { "depletion_strong": 90.0 },
          "ZECUSDT": { "wall_multiplier": 3.5, "absorption_scale": 4.0 }
        }

    Hanya field yang disebut yang ditimpa; sisanya ikut default. Return dict
    {symbol: BookmapConfig} yang baru didaftarkan.
    """
    import os

    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file tidak ditemukan: {path}")

    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    if ext in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError:
            raise ImportError(
                "File YAML butuh PyYAML. Install dengan 'pip install pyyaml' "
                "atau pakai format JSON."
            )
        data = yaml.safe_load(raw) or {}
    else:
        import json
        data = json.loads(raw) if raw.strip() else {}

    if not isinstance(data, dict):
        raise ValueError("Isi config harus berupa object/dict {symbol: {field: nilai}}")

    # 'default' (case-insensitive) jadi basis untuk semua symbol di file ini.
    base = DEFAULT
    for key in list(data.keys()):
        if key.lower() == "default":
            base = _config_from_dict(data.pop(key), DEFAULT)
            break

    loaded: Dict[str, BookmapConfig] = {}
    for symbol, fields in data.items():
        if not isinstance(fields, dict):
            print(f"[config] WARNING: entri '{symbol}' bukan object, dilewati")
            continue
        cfg = _config_from_dict(fields, base)
        register_config(symbol, cfg)
        loaded[symbol.upper()] = cfg

    return loaded
