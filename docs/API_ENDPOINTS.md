# Fractal API Endpoints

> Auto-generated reference dari source code `backend_api_python/app/routes/`.
> Last updated: 2026-06-12

---

## Health & Root

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/` | GET | Info API (nama, versi) |
| `/health` | GET | Health check |
| `/api/health` | GET | Health check (alias) |

---

## Auth (`/api/auth`)

Autentikasi, registrasi, OAuth, dan manajemen password.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/auth/register` | POST | Registrasi user baru |
| `/api/auth/login` | POST | Login (email/password) |
| `/api/auth/logout` | POST | Logout, invalidasi session |
| `/api/auth/me` | GET | Info user yang sedang login |
| `/api/auth/send-code` | POST | Kirim verification code via email (type: register, reset_password, change_password, change_email) |
| `/api/auth/change-password` | POST | Ganti password (hanya butuh `new_password`) |
| `/api/auth/change-email` | POST | Ganti email (butuh verification code) |
| `/api/auth/oauth/google` | GET | URL redirect OAuth Google |
| `/api/auth/oauth/github` | GET | URL redirect OAuth GitHub |
| `/api/auth/oauth/callback/google` | GET | Callback OAuth Google |
| `/api/auth/oauth/callback/github` | GET | Callback OAuth GitHub |

---

## User (`/api/users`)

Manajemen profil dan admin user management.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/users/profile` | GET | Ambil profil user |
| `/api/users/profile` | PUT | Update profil (nickname, avatar, dll) |
| `/api/users/change-password` | POST | Ganti password (versi legacy) |
| `/api/users/list` | GET | List semua user (admin only) |
| `/api/users/membership` | GET | Info membership user |
| `/api/users/<id>/role` | PUT | Update role user (admin only) |
| `/api/users/<id>/status` | PUT | Enable/disable user (admin only) |

---

## Settings (`/api/settings`)

Konfigurasi sistem dan branding.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/settings` | GET | Ambil semua settings |
| `/api/settings` | PUT | Update settings (admin only) |
| `/api/settings/brand` | GET | Ambil branding/contact config (publik) |

---

## Market Data (`/api/market`)

Data pasar real-time, sentimen, dan watchlist.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/market/overview` | GET | Overview pasar (indeks, heatmap) |
| `/api/market/sentiment` | GET | Sentimen pasar |
| `/api/market/calendar` | GET | Kalender ekonomi |
| `/api/market/opportunities` | GET | Peluang trading |
| `/api/market/watchlist` | GET | Ambil watchlist user |
| `/api/market/watchlist` | POST | Tambah simbol ke watchlist |
| `/api/market/watchlist` | DELETE | Hapus simbol dari watchlist |
| `/api/market/search` | GET | Cari simbol/ticker |

---

## Global Market (`/api/global-market`)

Data pasar global (indeks, heatmap, berita).

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/global-market/indices` | GET | Data indeks global |
| `/api/global-market/heatmap` | GET | Heatmap sektor/saham |
| `/api/global-market/news` | GET | Berita pasar |

---

## Kline (`/api/indicator`)

Data candlestick untuk charting.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/indicator/kline` | GET | Data candlestick/kline |

---

## Indicator (`/api/indicator`)

CRUD indikator teknikal, eksekusi, dan publish.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/indicator/indicators` | GET | List semua indikator user |
| `/api/indicator/indicators` | POST | Buat indikator baru |
| `/api/indicator/indicators/<id>` | GET | Detail indikator |
| `/api/indicator/indicators/<id>` | PUT | Update indikator |
| `/api/indicator/indicators/<id>` | DELETE | Hapus indikator |
| `/api/indicator/indicators/<id>/run` | POST | Jalankan indikator (hitung sinyal) |
| `/api/indicator/indicators/<id>/publish` | POST | Publish indikator ke community |

---

## Backtest (`/api/indicator`)

Backtesting strategi terhadap data historis.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/indicator/backtest` | POST | Jalankan backtest |
| `/api/indicator/backtest/history` | GET | Riwayat backtest |
| `/api/indicator/backtest/<id>` | GET | Detail hasil backtest |
| `/api/indicator/backtest/<id>` | DELETE | Hapus backtest |

---

## Strategy (`/api`)

Manajemen strategi trading (live & paper).

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/strategies` | GET | List semua strategi |
| `/api/strategies` | POST | Buat strategi baru |
| `/api/strategies/<id>` | GET | Detail strategi |
| `/api/strategies/<id>` | PUT | Update strategi |
| `/api/strategies/<id>` | DELETE | Hapus strategi |
| `/api/strategies/<id>/start` | POST | Mulai strategi (live/paper) |
| `/api/strategies/<id>/stop` | POST | Stop strategi |
| `/api/strategies/<id>/status` | GET | Status strategi running |

---

## Trading Bot / Dashboard (`/api/dashboard`)

Ringkasan dashboard dan pending orders.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/dashboard/summary` | GET | Ringkasan dashboard (PnL, posisi aktif) |
| `/api/dashboard/pendingOrders` | GET | List pending orders |
| `/api/dashboard/pendingOrders/<id>` | DELETE | Cancel pending order |

---

## Broker Credentials (`/api/credentials`)

Manajemen kredensial broker (Alpaca, IBKR, MT5).

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/credentials` | GET | List kredensial tersimpan |
| `/api/credentials` | POST | Simpan kredensial baru |
| `/api/credentials/<id>` | PUT | Update kredensial |
| `/api/credentials/<id>` | DELETE | Hapus kredensial |
| `/api/credentials/<id>/test` | POST | Test koneksi broker |

---

## Alpaca Broker (`/api/alpaca`)

Integrasi broker Alpaca (US stocks & crypto).

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/alpaca/status` | GET | Status koneksi Alpaca |
| `/api/alpaca/connect` | POST | Hubungkan akun Alpaca |
| `/api/alpaca/disconnect` | POST | Putuskan koneksi |
| `/api/alpaca/account` | GET | Info akun Alpaca |
| `/api/alpaca/positions` | GET | Posisi terbuka |
| `/api/alpaca/orders` | GET | List orders |
| `/api/alpaca/order` | POST | Buat order baru |
| `/api/alpaca/order/<order_id>` | DELETE | Cancel order |
| `/api/alpaca/quote/<symbol>` | GET | Quote harga real-time |

---

## Interactive Brokers (`/api/ibkr`)

Integrasi broker IBKR (multi-market global).

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/ibkr/status` | GET | Status koneksi IBKR |
| `/api/ibkr/connect` | POST | Hubungkan IBKR |
| `/api/ibkr/disconnect` | POST | Putuskan koneksi |
| `/api/ibkr/account` | GET | Info akun |
| `/api/ibkr/positions` | GET | Posisi terbuka |
| `/api/ibkr/orders` | GET | List orders |
| `/api/ibkr/order` | POST | Buat order |
| `/api/ibkr/order/<id>` | DELETE | Cancel order |

---

## MetaTrader 5 (`/api/mt5`)

Integrasi broker MT5 (forex, CFD).

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/mt5/status` | GET | Status koneksi MT5 |
| `/api/mt5/connect` | POST | Hubungkan MT5 |
| `/api/mt5/disconnect` | POST | Putuskan koneksi |
| `/api/mt5/account` | GET | Info akun |
| `/api/mt5/positions` | GET | Posisi terbuka |
| `/api/mt5/orders` | GET | List orders |
| `/api/mt5/order` | POST | Buat order |

---

## Quick Trade (`/api/quick-trade`)

Eksekusi order cepat tanpa strategi.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/quick-trade/order` | POST | Eksekusi order cepat |
| `/api/quick-trade/positions` | GET | Posisi aktif |
| `/api/quick-trade/close` | POST | Tutup posisi |

---

## Portfolio (`/api/portfolio`)

Monitoring portofolio dan riwayat transaksi.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/portfolio/summary` | GET | Ringkasan portofolio |
| `/api/portfolio/positions` | GET | Semua posisi |
| `/api/portfolio/history` | GET | Riwayat transaksi |

---

## AI Chat (`/api/ai`)

Chat dengan AI untuk analisis dan tanya jawab trading.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/ai/chat` | POST | Chat dengan AI |
| `/api/ai/chat/history` | GET | Riwayat chat |
| `/api/ai/chat/<id>` | DELETE | Hapus chat |

---

## Fast Analysis (`/api/fast-analysis`)

Analisis cepat aset berbasis AI.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/fast-analysis/analyze` | POST | Analisis cepat aset (AI-powered) |
| `/api/fast-analysis/history` | GET | Riwayat analisis user |
| `/api/fast-analysis/history/all` | GET | Semua riwayat (admin) |
| `/api/fast-analysis/history/<id>` | DELETE | Hapus riwayat analisis |
| `/api/fast-analysis/feedback` | POST | Kirim feedback kualitas analisis |
| `/api/fast-analysis/performance` | GET | Performa prediksi analisis |
| `/api/fast-analysis/similar-patterns` | GET | Pola serupa dari histori |

---

## Community / Indicator Market (`/api/community`)

Marketplace indikator — jual beli, review, komentar.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/community/indicators` | GET | Browse indikator di marketplace |
| `/api/community/indicators/<id>` | GET | Detail indikator |
| `/api/community/indicators/<id>/purchase` | POST | Beli indikator |
| `/api/community/indicators/<id>/sync` | POST | Sync indikator yang dibeli |
| `/api/community/my-purchases` | GET | Indikator yang sudah dibeli |
| `/api/community/author/summary` | GET | Ringkasan author (pendapatan) |
| `/api/community/author/published` | GET | Indikator yang dipublish |
| `/api/community/author/sales` | GET | Data penjualan |
| `/api/community/indicators/<id>/comments` | GET | List komentar |
| `/api/community/indicators/<id>/comments` | POST | Tambah komentar |
| `/api/community/indicators/<id>/comments/<cid>` | PUT | Edit komentar |
| `/api/community/indicators/<id>/my-comment` | GET | Komentar saya |
| `/api/community/indicators/<id>/performance` | GET | Performa indikator |
| `/api/community/admin/pending-indicators` | GET | Indikator menunggu review (admin) |
| `/api/community/admin/review-stats` | GET | Statistik review (admin) |
| `/api/community/admin/indicators/<id>/review` | POST | Approve/reject indikator (admin) |

---

## Billing / Membership (`/api/billing`)

Paket langganan, pembayaran, dan kredit.

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/billing/plans` | GET | List paket membership |
| `/api/billing/subscribe` | POST | Berlangganan paket |
| `/api/billing/status` | GET | Status langganan aktif |
| `/api/billing/history` | GET | Riwayat pembayaran |
| `/api/billing/credits` | GET | Saldo kredit |

---

## Experiment (`/api/experiment`)

Fitur eksperimental (regime detection, AI optimization).

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/experiment/regime/detect` | POST | Deteksi market regime (bull/bear/sideways) |
| `/api/experiment/pipeline` | POST | Jalankan experiment pipeline |
| `/api/experiment/structured-tune` | POST | Structured parameter tuning |
| `/api/experiment/ai-optimize` | POST | AI-powered strategy optimization |

---

## Policy (`/api/policy`)

Konfigurasi platform (broker & market support).

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/policy/broker-market` | GET | Daftar broker & market yang didukung |

---

## Agent Gateway (`/api/v1/agent`)

API khusus untuk AI agent. Autentikasi via Bearer token (bukan session cookie).

### Health & Identity

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/v1/agent/health` | GET | Health check agent API |
| `/api/v1/agent/whoami` | GET | Info token yang aktif |

### Market Data

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/v1/agent/markets` | GET | List markets yang tersedia |
| `/api/v1/agent/markets/<market>/symbols` | GET | Simbol per market |
| `/api/v1/agent/klines` | GET | Data kline/candlestick |
| `/api/v1/agent/price` | GET | Harga terkini |

### Indicators

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/v1/agent/indicators/authoring-contract` | GET | Kontrak format penulisan indikator |
| `/api/v1/agent/indicators` | GET | List indikator |
| `/api/v1/agent/indicators` | POST | Buat indikator baru |
| `/api/v1/agent/indicators/<id>` | GET | Detail indikator |
| `/api/v1/agent/indicators/validate` | POST | Validasi kode indikator |
| `/api/v1/agent/indicators/link-config` | POST | Link config ke indikator |

### Strategies

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/v1/agent/strategies` | GET | List strategi |
| `/api/v1/agent/strategies` | POST | Buat strategi baru |
| `/api/v1/agent/strategies/<id>` | GET | Detail strategi |
| `/api/v1/agent/strategies/<id>` | PATCH | Update strategi |

### Backtests

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/v1/agent/backtests` | POST | Jalankan backtest |

### Portfolio

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/v1/agent/portfolio/positions` | GET | Posisi portofolio |
| `/api/v1/agent/portfolio/paper-orders` | GET | Paper trading orders |

### Quick Trade

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/v1/agent/quick-trade/orders` | POST | Eksekusi order cepat |
| `/api/v1/agent/quick-trade/kill-switch` | POST | Emergency stop (tutup semua posisi) |

### Experiments

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/v1/agent/experiments/regime/detect` | POST | Deteksi market regime |
| `/api/v1/agent/experiments/pipeline` | POST | Experiment pipeline |
| `/api/v1/agent/experiments/structured-tune` | POST | Parameter tuning |
| `/api/v1/agent/experiments/ai-optimize` | POST | AI optimization |

### Jobs

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/v1/agent/jobs` | GET | List background jobs |
| `/api/v1/agent/jobs/<id>` | GET | Status job |
| `/api/v1/agent/jobs/<id>/stream` | GET | Stream output job (SSE) |

### Admin (Token Management)

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/v1/agent/admin/tokens` | GET | List agent tokens (admin) |
| `/api/v1/agent/admin/tokens` | POST | Buat token baru (admin) |
| `/api/v1/agent/admin/tokens/<id>` | DELETE | Revoke token (admin) |
| `/api/v1/agent/admin/audit` | GET | Audit log penggunaan token |
