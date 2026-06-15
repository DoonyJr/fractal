# AMT Liquidation Analysis System

Sistem analisis pasar crypto real-time berbasis **Auction Market Theory (AMT)**.
Membaca order book, trade, dan liquidation dari Binance Futures + Bybit Linear lewat
WebSocket, lalu mengubahnya menjadi indikator dan sinyal trading yang tampil di terminal.

---

## 1. Cara Menjalankan

```bash
# 1. Install dependencies (sekali saja)
pip install -r requirements.txt

# 2. Jalankan untuk satu coin
python main.py --symbol BTCUSDT

# Opsi lain:
python main.py --symbol ETHUSDT --refresh 2                 # refresh tiap 2 detik
python main.py --symbol ZECUSDT --config bookmap_config.json # pakai threshold dari file
```

Tekan `Ctrl+C` untuk berhenti.

**Argumen:**

| Argumen     | Default   | Arti                                                   |
|-------------|-----------|--------------------------------------------------------|
| `--symbol`  | BTCUSDT   | Pair yang dipantau (mis. ETHUSDT, ZECUSDT, HYPEUSDT)   |
| `--refresh` | 1.0       | Seberapa sering layar diperbarui (detik)               |
| `--config`  | (kosong)  | Path file threshold eksternal (JSON/YAML). Opsional.   |

---

## 2. Arsitektur Singkat

Data mengalir satu arah lewat 6 layer:

```
WebSocket Streams  →  Core (state)  →  Analytics  →  Signals  →  Terminal Display
   (Binance/Bybit)     order book        AMT logic    alert        dashboard
                       trade, liq, OI
```

### Struktur folder

```
liquidation/
├── main.py                 # Entry point — wiring semua komponen + analysis loop
├── config.py               # Threshold per-coin (logic terpisah dari angka)
├── bookmap_config.json     # Contoh file config eksternal
├── requirements.txt
│
├── streams/                # Koneksi WebSocket (sumber data mentah)
│   ├── binance_ws.py       #   Binance Futures: depth, aggTrade, forceOrder
│   └── bybit_ws.py         #   Bybit Linear: orderbook, trade, liquidation, OI
│
├── core/                   # Menjaga STATE dari data mentah
│   ├── order_book.py       #   Snapshot order book + imbalance, wall
│   ├── trade_processor.py  #   CVD, delta, VWAP, absorpsi
│   ├── liquidation_collector.py  # Kumpulkan & cluster liquidation per zona
│   └── oi_calculator.py    #   Open Interest delta + interpretasi
│
├── analytics/              # MENGUBAH state jadi insight (otak sistem)
│   ├── order_book_analysis.py  # Imbalance, wall, iceberg detector
│   ├── liquidation_analysis.py # Cascade risk, squeeze, heatmap
│   ├── order_flow.py           # CVD gabungan, divergence, large trades
│   ├── market_profile.py       # POC, Value Area, auction state (inti AMT)
│   ├── bookmap_stats.py        # 5 statistik gaya Bookmap (lihat bagian 4)
│   └── amt_confluence.py       # MASTER: gabung semua → skor 0-100 + bias
│
├── signals/
│   └── signal_engine.py    # Generate alert dari semua analitik + cooldown
│
└── output/
    └── terminal_display.py # Dashboard berwarna real-time
```

**Kenapa terpisah begini?** Tiap layer punya satu tugas. `core` cuma menjaga data,
`analytics` cuma menghitung, `output` cuma menampilkan. Kalau mau ganti tampilan,
kamu sentuh `output` saja — logic tidak terganggu.

---

## 3. Modul Analitik (apa yang dihitung)

### Market Profile (`market_profile.py`) — inti AMT
- **POC (Point of Control):** harga dengan volume tertinggi — magnet harga.
- **Value Area (VA):** rentang harga yang memuat 70% volume — zona "wajar".
- **Auction State:** apakah pasar sedang *balancing* (rotasi di dalam VA) atau
  *trending* (mencari value baru di luar VA).

### Order Flow (`order_flow.py`)
- **CVD (Cumulative Volume Delta):** akumulasi (volume beli − volume jual).
  Naik = buyer agresif; turun = seller agresif.
- **Divergence:** harga vs CVD berlawanan arah → sinyal potensi reversal.

### Liquidation Analysis (`liquidation_analysis.py`)
- **Cluster:** kelompokkan liquidation per zona harga.
- **Cascade Risk:** probabilitas liquidation beruntun (0-100).
- **Squeeze:** deteksi long/short yang terjebak → potensi squeeze.

### AMT Confluence (`amt_confluence.py`) — master analyzer
Menggabungkan 4 analisis (Auction Imbalance, Cascade, VA Reaction, Stop Hunt)
menjadi satu **Confluence Score 0-100**, lengkap dengan **bias** (LONG/SHORT/NEUTRAL)
dan saran level **entry / stop / target**.

---

## 4. Bookmap Stats — 5 statistik & kejujuran data

Modul `bookmap_stats.py` mengubah visual Bookmap jadi angka. **Penting:** tidak semua
metrik sama akuratnya dengan data Binance L2 (agregat per level, resolusi ~100ms).
Tiap metrik membawa label `confidence`:

| Statistik                    | Confidence  | Arti                                                            |
|------------------------------|-------------|-----------------------------------------------------------------|
| **Absorption Ratio**         | `accurate`  | Volume diserap tanpa harga bergerak → ada pihak besar menyerap  |
| **Depletion Speed**          | `accurate`  | Laju satu sisi book "dimakan" → konfirmasi momentum asli         |
| **Delta/Heatmap Divergence** | `accurate`  | CVD agresif tapi ditahan wall pasif → potensi reversal           |
| **Heatmap Persistence**      | `estimate`  | Berapa lama wall bertahan (dwell time) — presisi terbatas ~100ms |
| **Iceberg Refill**           | `estimate`  | Level yang terus diisi ulang — inferensi, tanpa order-id         |

**Kenapa ada yang cuma `estimate`?** Binance L2 tidak memberi identitas order individual
(tidak tahu ada berapa order terpisah di satu harga), dan update tiap ~100ms. Jadi
deteksi iceberg & dwell time adalah inferensi statistik yang reasonable, bukan kepastian.
Label `[estimate]` muncul di terminal supaya kamu tahu seberapa jauh bisa percaya tiap angka.

---

## 5. Config Threshold (`config.py` + `bookmap_config.json`)

Tiap coin punya karakter likuiditas beda: BTC dalam & tebal, ZEC/HYPE tipis & volatil.
Threshold yang sama tidak cocok untuk semua. Config memisahkan **angka** dari **logic**.

### Field yang bisa disetel

| Field                 | Arti                                                       |
|-----------------------|------------------------------------------------------------|
| `wall_multiplier`     | qty ≥ (multiplier × rata-rata) dianggap "wall". Naikkan untuk coin tebal. |
| `track_levels`        | Berapa level kedalaman yang dilacak.                       |
| `persistence_window`  | Umur maksimum pelacakan sebuah level (detik).              |
| `min_dwell`           | Detik minimum agar level dianggap "persisten".             |
| `persistence_norm`    | Dwell time (detik) yang dipetakan ke skor 100.             |
| `absorption_scale`    | Pembagi skor absorpsi. Lebih kecil = lebih sensitif.       |
| `depletion_strong`    | unit/detik yang dianggap depletion "kuat" (skor 100).      |
| `iceberg_min_refills` | Minimal refill agar dianggap iceberg.                      |
| `iceberg_norm`        | Jumlah refill yang dipetakan ke skor 100.                  |

### Cara setel tanpa sentuh kode Python

Edit `bookmap_config.json` dengan text editor:

```json
{
  "default": { "depletion_strong": 50.0 },
  "ZECUSDT": { "wall_multiplier": 4.0, "absorption_scale": 5.0 }
}
```

- Key `default` jadi basis semua coin — cukup tulis field yang mau diubah, sisanya ikut default.
- Jalankan: `python main.py --symbol ZECUSDT --config bookmap_config.json`
- Salah ketik field? Diabaikan dengan warning, sistem tetap jalan.

### Cara kalibrasi
1. Jalankan sistem live beberapa menit, amati nilai mentah di terminal (ratio, rate/s, dwell).
2. Sesuaikan `absorption_scale` & `depletion_strong` sampai skor 0-100 tersebar wajar.
3. Simpan file, jalankan ulang. Tidak perlu sentuh logic.

---

## 6. Catatan & Batasan

- **Butuh internet & koneksi WebSocket** ke Binance + Bybit (gratis, tanpa API key).
- **Data liquidation** = liquidation yang SUDAH terjadi (dari stream exchange), bukan
  estimasi level liquidasi ala Coinglass (yang butuh API berbayar).
- **Skor normalisasi** (angka di config) adalah titik awal berdasarkan asumsi — kalibrasi
  sendiri per coin untuk hasil terbaik.
- Untuk menambah coverage exchange (OKX, Gate, Bitget) bisa ditambahkan stream baru di
  folder `streams/` dengan pola yang sama.

---

## 7. Ringkasan Alur (TL;DR)

1. `streams/` connect ke Binance + Bybit, terima data mentah real-time.
2. Callback di `main.py` masukkan data ke `core/` (order book, trade, liquidation, OI).
3. `analysis_loop()` tiap cycle menjalankan semua `analytics/`, termasuk `bookmap_stats`
   dan master `amt_confluence`.
4. `signals/` menghasilkan alert dari hasil analitik (dengan cooldown anti-spam).
5. `output/terminal_display.py` menggambar semuanya jadi dashboard berwarna.
6. Threshold tiap coin diambil dari `config.py` / `bookmap_config.json`.
```
