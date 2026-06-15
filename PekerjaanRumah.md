# PekerjaanRumah — Integrasi Liquidation Dashboard

> Status per 2026-06-14. Catatan lanjutan untuk integrasi modul `liquidation/`
> (AMT Liquidation Analysis System) ke QuantDinger sebagai menu web.

## Keputusan Arsitektur (sudah disepakati)

- **Polling dulu**, bukan WebSocket push (lebih ringan, cukup untuk beban kecil)
- **1 user = max 3 symbol** bersamaan
- **User saat ini:** hanya owner + 1 asisten (beban sangat ringan, jangan over-engineer)
- **API eksternal** (tradermap.io, cryptoquant): TUNDA — pakai data exchange langsung dulu
- **Data source:** Binance Futures + Bybit Linear WebSocket (sudah ada di `liquidation/streams/`)

## Yang SUDAH selesai (Fase 1)

- [x] `liquidation/output/state_snapshot.py` — serializer JSON-safe
  - `build_snapshot()` mirror semua dict dari `analysis_loop`
  - `liquidation_map()` ekstrak long/short cluster per zona harga (chart-ready)
  - `_num()` guard NaN/inf/None → 0.0 (JSON-safe)
- [x] `main.py` wire `self.latest_snapshot` di analysis loop (in-memory, siap dibaca API)
- [x] Verified: syntax OK, JSON serializable, liq map terbentuk, NaN aman

## Fase 2 — Backend Flask integration (BELUM)

Lokasi: `backend_api_python/app/`

### SUDAH selesai (sesi 2026-06-14)

- [x] `services/liquidation_service.py` — `LiquidationManager` + `_SymbolRunner`
  - AMTSystem jalan di daemon thread + event loop sendiri (pola sama PostRestorePositionSync)
  - Registry max 3 symbol (`LIQUIDATION_MAX_SYMBOLS`), idle reap (`LIQUIDATION_IDLE_TIMEOUT`=300s)
  - On-demand spawn via `ensure(symbol)`, auto-stop saat idle / thread mati
- [x] `routes/liquidation.py` — blueprint `/api/liquidation`:
  - `GET /snapshot?symbol=` → `latest_snapshot`
  - `GET /map?symbol=` → `liquidation_map(...)`
  - `GET /active` → daftar symbol aktif
  - `POST /stop` {symbol} → stop runner
  - semua `@login_required`
- [x] Registrasi blueprint di `openapi/register.py` + tag `Liquidation` di `tags.py`
- [x] `liquidation/output/__init__.py` lazy import colorama (backend import state_snapshot bersih)
- [x] Verified: syntax OK, path resolution benar, import isolation tanpa colorama works

### BLOCKER — SUDAH diselesaikan (sesi 2026-06-14)

- [x] **Docker build context** — RESOLVED via opsi 1: `liquidation/` dipindah ke
      `backend_api_python/liquidation_engine/`. `_LIQ_ROOT` di service + route diubah
      ke `../../liquidation_engine`. Sekarang ter-copy via `COPY . .` di Dockerfile.
- [x] Tambah `websockets>=12.0`, `aiohttp>=3.9.5`, `colorama>=0.4.6` ke requirements.txt
- [x] colorama dibuat OPTIONAL di `terminal_display.py` (fallback no-op shim) — backend
      headless import AMTSystem tanpa colorama. Verified end-to-end.

### Sisa verifikasi sebelum production (belum bisa lokal)

- [ ] Test koneksi WebSocket NYATA ke Binance/Bybit di gunicorn gthread (1 worker + 4 thread).
      Pola async-in-thread sudah ada (ib_insync patchAsyncio) tapi WS liquidation belum diuji live.
- [ ] Reconnect logic: cek `liquidation_engine/streams/binance_ws.py` + `bybit_ws.py` —
      apakah ada auto-reconnect saat koneksi exchange putus (penting untuk runner long-lived).
- [ ] Verifikasi `recent_events`/`events` key benar-benar ada di output LiquidationAnalyzer
      (LiquidationFeed.vue mengharapkan `liquidation.recent_events` — perlu cek shape nyata).

## Fase 3 — Frontend Vue (SELESAI sesi 2026-06-14)

- [x] Route `/liquidation` + menu (icon `fire`) di router.config.js
- [x] i18n `liquidation.*` + `menu.dashboard.liquidation` (en-US + zh-CN)
- [x] `views/liquidation/index.vue` — parent, polling 2 detik, keep-alive aware
      (pause polling saat deactivated, resume saat activated)
- [x] `components/LiquidationMap.vue` — ladder long/short per zona harga + mark line
- [x] `components/LiquidationFeed.vue` — feed event liquidation real-time
- [x] Signals panel inline (severity-colored)
- [x] Build frontend clean
- [ ] BELUM dibuat (lanjutan opsional): OrderBookLadder.vue, WhaleTrades.vue,
      ConfluencePanel.vue (data sudah ada di snapshot, tinggal render)

## Fase 3 — Frontend Vue (BELUM)

Lokasi: `Fractal-Vue/src/`

- [ ] Route + menu "Liquidation" di `config/router.config.js` (icon: `fire` atau `thunderbolt`)
- [ ] i18n keys `liquidation.*` di `locales/lang/en-US.js` + `zh-CN.js`
- [ ] `views/liquidation/index.vue` — parent, polling 1-2 detik (pola sama OrderFlow:
      fetch sekali di parent, pass prop ke child)
- [ ] Komponen (pakai pola OrderFlow yang sudah ada):
  - `LiquidationMap.vue` — heatmap long/short per zona harga (SVG/canvas, mirip gambar Tradermap)
  - `LiquidationFeed.vue` — feed real-time event liquidation (list)
  - `OrderBookLadder.vue` — ASK/BID ladder (mirip gambar 1)
  - `WhaleTrades.vue` — large trades feed
  - `SignalAlerts.vue` — sinyal dari SignalEngine (LONG_SQUEEZE, CASCADE_WARNING, dll)
  - `ConfluencePanel.vue` — AMT confluence score + bias + entry/stop/target
- [ ] Symbol selector (max 3, sesuai keputusan)

## Fase 4 — API eksternal (TUNDA, opsional jauh)

- [ ] tradermap.io API (`https://api.tradermap.io/`) — cek dokumentasi + pricing dulu
- [ ] CryptoQuant API — on-chain metrics (MPI, exchange flows) — berbayar
- [ ] Liq map "MODELLED" (seperti gambar): butuh OI + leverage estimation.
      `oi_calculator.py` + `liquidation_analysis.py` sudah ada — cek apakah cukup
      untuk replikasi heatmap modelled, atau perlu tambahan model leverage.

## Fase 5 — Coinglass-style Liquidation Map (PARTIALLY DONE)

### SUDAH selesai (sesi 2026-06-15)

- [x] `liquidation_engine/analytics/liquidation_levels.py` — model liquidation levels:
  - Formula: `liq_long = entry * (1 - 1/lev)`, `liq_short = entry * (1 + 1/lev)`
  - 4 leverage tiers (10x/25x/50x/100x) dengan distribusi bobot
  - Entry price distribution: gaussian atau dari recent trades
  - Output: per-price bars (total + by_leverage) + cumulative curves
  - Verified: long clusters below mark (172.9M), short above (167M) ✅
- [x] `GET /api/liquidation/levels?symbol=` endpoint added (uses OI from snapshot)

### BELUM (untuk sesi berikutnya)

- [ ] Frontend `LiquidationLevelsChart.vue` — SVG/Canvas chart Coinglass-style:
  - X-axis: price levels
  - Y-axis: $ liquidation value
  - Multi-color stacked bars (10x=biru muda, 25x=biru, 50x=kuning, 100x=oranye)
  - Cumulative line (long=merah area kiri, short=hijau area kanan)
  - Dashed vertical line "Current Price" di tengah
  - Legend + pair selector + timeframe
- [ ] Wire ke Liquidation page (replace/supplement current `LiquidationMap.vue`)
- [ ] OI data enrichment: saat ini `oi_usd` diambil dari snapshot Bybit ticker.
  Binance juga punya OI via REST (`/fapi/v1/openInterest`). Gabungkan untuk
  estimate lebih akurat. Atau fetch historical OI via `/futures/data/openInterestHist`.
- [ ] Entry price enrichment: pass real `recent_prices` dari `TradeProcessor`
  ke model (saat ini model pakai gaussian fallback karena `order_flow.recent_prices`
  belum di-expose di snapshot)

## Risiko & Catatan Penting

1. **Async di Flask** — ini tantangan terbesar Fase 2. AMTSystem full async (asyncio +
   websockets). Flask default sync. Perlu strategi: background thread + own event loop,
   atau migrasi endpoint terkait ke async framework.
2. **Koneksi WebSocket ke exchange** — tiap symbol = 1 set koneksi Binance + Bybit.
   3 symbol = 6 koneksi WS persisten. Pastikan VPS handle + ada reconnect logic
   (cek `binance_ws.py` apakah sudah ada auto-reconnect).
3. **Data "estimated"** — sama seperti OrderFlow footprint/CVD, liq map modelled adalah
   estimasi. Beri label jelas di UI.
4. **Resource** — AMTSystem jalan terus selama symbol aktif. Idle timeout WAJIB supaya
   tidak ada 6 koneksi WS nganggur saat tidak ada yang polling.

## Verifikasi yang sudah dilakukan

- `python3 -c` test `state_snapshot.py`: build_snapshot + liquidation_map + NaN guard → semua pass
- JSON serializable confirmed (365 bytes untuk snapshot test)
