<div align="center">
  <a href="https://github.com/brokermr810/Fractal">
    <img src="screenshots/logo.jpg" alt="Fractal Logo" width="220" height="220">
  </a>

  <h1>Fractal</h1>
  <h3>Hệ điều hành giao dịch định lượng AI riêng tư của bạn</h3>
  <p><strong>Một stack Docker cho biểu đồ, nghiên cứu đa LLM, chiến lược Python, backtest cấp tổ chức và live đa venue—tự host hoàn toàn, khóa của bạn, dữ liệu của bạn.</strong></p>
  <p><em>quant OS mã nguồn mở: AI hỗ trợ code → backtest → paper → live (crypto/IBKR/MT5/Alpaca), tích hợp Agent Gateway &amp; MCP.</em></p>

  <div align="center" style="max-width: 680px; margin: 1.25rem auto 0; padding: 20px 22px 22px; border: 1px solid #d1d9e0; border-radius: 16px;">
    <p style="margin: 0 0 14px; line-height: 1.65;">
      <a href="../README.md"><strong>English</strong></a>
      <span style="color: #afb8c1;"> · </span>
      <a href="README_CN.md"><strong>简体中文</strong></a>
      <span style="color: #afb8c1;"> · </span>
      <a href="README_JA.md"><strong>日本語</strong></a>
      <span style="color: #afb8c1;"> · </span>
      <a href="README_KO.md"><strong>한국어</strong></a>
      <span style="color: #afb8c1;"> · </span>
      <a href="README_TH.md"><strong>ไทย</strong></a>
      <span style="color: #afb8c1;"> · </span>
      <a href="README_VI.md"><strong>Tiếng Việt</strong></a>
      <span style="color: #afb8c1;"> · </span>
      <a href="README_AR.md"><strong>العربية</strong></a>
    </p>
    <p style="margin: 0 0 18px; padding-bottom: 16px; border-bottom: 1px solid #eaeef2; line-height: 2;">
      <a href="https://ai.fractal.com"><strong>SaaS</strong></a>
      <span style="color: #d8dee4;"> &nbsp;·&nbsp; </span>
      <a href="https://www.youtube.com/watch?v=tNAZ9uMiUUw"><strong>Video demo</strong></a>
      <span style="color: #d8dee4;"> &nbsp;·&nbsp; </span>
      <a href="https://www.fractal.com"><strong>Trang web</strong></a>
      <span style="color: #d8dee4;"> &nbsp;·&nbsp; </span>
      <a href="https://aws.amazon.com/marketplace/pp/prodview-naanrb7d2mbc6"><strong>AWS Marketplace</strong></a>
    </p>
    <p style="margin: 0; line-height: 2;">
      <a href="https://t.me/fractal"><img src="https://img.shields.io/badge/Telegram-Join-26A5E4?style=flat-square&logo=telegram&logoColor=white" alt="Telegram"></a>
      &nbsp;
      <a href="https://discord.com/invite/tyx5B6TChr"><img src="https://img.shields.io/badge/Discord-Server-5865F2?style=flat-square&logo=discord&logoColor=white" alt="Discord"></a>
      &nbsp;
      <a href="https://youtube.com/@fractal"><img src="https://img.shields.io/badge/YouTube-%40fractal-FF0000?style=flat-square&logo=youtube&logoColor=white" alt="YouTube"></a>
      &nbsp;
      <a href="https://x.com/Fractal_EN"><img src="https://img.shields.io/badge/X-%40Fractal_EN-000000?style=flat-square&logo=x&logoColor=white" alt="X"></a>
    </p>
  </div>

  <p style="margin-top: 1.45rem; margin-bottom: 10px;">
    <a href="../LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=flat-square&logo=apache" alt="License"></a>
    <img src="https://img.shields.io/github/v/release/brokermr810/Fractal?style=flat-square&color=orange&label=Version" alt="Version">
    <img src="https://img.shields.io/badge/Python-3.10%2B%20%7C%20Docker%203.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
    <img src="https://img.shields.io/badge/Agent%20Gateway-MCP%20Ready-6f42c1?style=flat-square" alt="Agent Gateway">
    <img src="https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL">
    <img src="https://img.shields.io/github/stars/brokermr810/Fractal?style=flat-square&logo=github" alt="Stars">
  </p>
</div>

---

## Mục lục

[Bắt đầu nhanh](#bắt-đầu-nhanh) · [Điểm nổi bật kỹ thuật](#điểm-nổi-bật-kỹ-thuật) · [Kho liên quan](#kho-liên-quan) · [MCP / Agent](#mcp--agent-gateway) · [Tổng quan](#tổng-quan-sản-phẩm) · [Tính năng](#điểm-nổi-bật) · [Ảnh màn hình](#tour-hình-ảnh) · [Kiến trúc](#kiến-trúc) · [Cài đặt](#cài-đặt-và-chạy-lần-đầu) · [Tài liệu](#danh-sách-tài-liệu) · [FAQ](#câu-hỏi-thường-gặp) · [Giấy phép](#giấy-phép)

---

> Fractal là **quant OS tự lưu trữ, ưu tiên cục bộ** — không phải chatbot có nút mua. Gom **nghiên cứu đa LLM**, **chiến lược Python gốc**, **backtest phía server** và **live đa broker** (10+ crypto venue, IBKR, MT5, Alpaca) trong một stack production bạn kiểm soát hoàn toàn.

<div align="center">
  <img src="screenshots/ezgif.com-animated-gif-maker.gif" alt="Fractal demo" width="920" style="border-radius: 12px; border: 1px solid #eaeef2;">
  <p><sub><em>Từ zero đến chạy được—biểu đồ, AI nghiên cứu và workflow chiến lược trong vài phút.</em></sub></p>
</div>

<div align="center">
  <img src="screenshots/architecture.png" alt="Kiến trúc Fractal" width="960">
  <p><sub><em>Vòng lặp 5 tầng: <strong>Ý tưởng → Chỉ báo → Chiến lược → Backtest → Tối ưu → Thực thi → Giám sát</strong></em></sub></p>
</div>

## Điểm nổi bật kỹ thuật

| | Điểm khác biệt của Fractal |
|---|-------------------------------|
| **quant OS full-stack** | Biểu đồ, IDE, AI, backtest, bot live, quick trade, quản lý broker—một sản phẩm |
| **Agent-native** | **Agent Gateway** + PyPI [`fractal-mcp`](https://pypi.org/project/fractal-mcp/) — Cursor / Claude Code / Codex, audit log |
| **Hai runtime chiến lược** | `IndicatorStrategy` (tín hiệu vector) và `ScriptStrategy` (`on_bar`) |
| **Đa venue** | CCXT crypto, IBKR, MT5, Alpaca — trang tài khoản broker thống nhất |
| **Hạ tầng production** | PostgreSQL 16 + Redis 7, Worker, ảnh GHCR multi-arch |
| **Bảo mật** | Từ chối `SECRET_KEY` mặc định, token hash, mặc định chỉ paper |

## Bắt đầu nhanh

**Yêu cầu:** [Docker](https://docs.docker.com/get-docker/) + Compose v2. **Không cần Node.js** (kéo frontend từ GHCR).

### Cài đặt một dòng (Linux / macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/brokermr810/Fractal/main/install.sh | bash
```

Mặc định `~/fractal`. Chạy lại để pull ảnh mới. → **`http://localhost:8888`** (`fractal` / `123456`, đổi mật khẩu ngay).

### Chuẩn: clone kho (macOS / Linux)

```bash
git clone https://github.com/brokermr810/Fractal.git && cd Fractal && cp backend_api_python/env.example backend_api_python/.env && chmod +x scripts/generate-secret-key.sh && ./scripts/generate-secret-key.sh && docker-compose up -d --build
```

Nếu không có `docker-compose`, dùng `docker compose`.

### Windows (PowerShell)

Bật **Docker Desktop**, rồi trong PowerShell:

```powershell
git clone https://github.com/brokermr810/Fractal.git
Set-Location Fractal
Copy-Item backend_api_python\env.example -Destination backend_api_python\.env
$key = & python -c "import secrets; print(secrets.token_hex(32))" 2>$null
if (-not $key) { $key = & py -c "import secrets; print(secrets.token_hex(32))" 2>$null }
if (-not $key) { Write-Error "Thêm Python 3 vào PATH." }
(Get-Content backend_api_python\.env) -replace '^SECRET_KEY=.*$', "SECRET_KEY=$key" | Set-Content backend_api_python\.env -Encoding utf8
docker-compose up -d --build
```

### Windows (Git Bash)

Trong Bash của Git for Windows có thể dùng lệnh một dòng như trên macOS/Linux.

---

Mở **`http://localhost:8888`**, đăng nhập **`fractal` / `123456`**, rồi **đổi mật khẩu quản trị ngay**. Chi tiết xem [Cài đặt và chạy lần đầu](#cài-đặt-và-chạy-lần-đầu).

## Kho liên quan

| Kho | Nội dung |
|-----|----------|
| **[Fractal](https://github.com/brokermr810/Fractal)** (kho này) | Backend, Compose, tài liệu, web đã build |
| **[Fractal-Vue](https://github.com/brokermr810/Fractal-Vue)** | **Mã nguồn web** (Vue) — tag `v*` tự động phát hành `ghcr.io/brokermr810/fractal-frontend` |
| **[Fractal-Mobile](https://github.com/brokermr810/Fractal-Mobile)** | **Ứng dụng di động** (mã nguồn mở) |

<h2 id="mcp--agent-gateway">MCP / Agent Gateway</h2>

Dành cho **Cursor / Claude Code / Codex**: **Model Context Protocol (MCP)** và **Agent Gateway** (`/api/agent/v1`). Tài liệu chi tiết bằng tiếng Anh là nguồn chính:

- **Hướng dẫn kết nối:** [**MCP_SETUP.md**](agent/MCP_SETUP.md) — Hosted / tự host, stdio cục bộ, HTTP từ xa, Claude Code CLI gộp trong một trang.
- [AGENT_QUICKSTART.md](agent/AGENT_QUICKSTART.md) · [AI_INTEGRATION_DESIGN.md](agent/AI_INTEGRATION_DESIGN.md) · [agent-openapi.json](agent/agent-openapi.json)
- Máy chủ MCP: [`../mcp_server/README.md`](../mcp_server/README.md) · PyPI [`fractal-mcp`](https://pypi.org/project/fractal-mcp/)

**Bảo mật:** Mọi lệnh gọi Agent được ghi vào nhật ký kiểm toán. Token giao dịch (T) mặc định chỉ **giấy**; giao dịch thực cần cả `AGENT_LIVE_TRADING_ENABLED=true` trên máy chủ và `paper_only=false` trên token.

## Tổng quan sản phẩm

Môi trường **AI + chiến lược Python + backtest + live** tự host. Thay bộ TradingView + Notebook + chat AI + bot sàn bằng **một stack Docker có thể kiểm toán**. Thông tin xác thực trong **PostgreSQL** và **`.env`**.

## Điểm nổi bật

- **Nghiên cứu & AI** — Đa LLM, NL→code, Agent / MCP (scoped token, SSE).
- **Xây dựng** — `IndicatorStrategy` / `ScriptStrategy`, UI K-line chuyên nghiệp.
- **Xác minh** — Backtest phía server (equity, drawdown, nhật ký lệnh).
- **Vận hành** — 10+ crypto, IBKR / MT5 / Alpaca, trang broker thống nhất, Telegram / Discord / Webhook.
- **Nền tảng** — Docker + GHCR, Postgres 16, Redis 7, OAuth, đa người dùng, billing, AWS Marketplace.

## Kiến trúc

**Nguyên tắc:** Tách dữ liệu thị trường · chiến lược/backtest · thực thi. Nginx + Vue SPA, Flask + Gunicorn, PostgreSQL 16, Redis 7. Triển khai: `install.sh` một dòng, GHCR zero-repo, full repo Compose, AWS AMI, [SaaS](https://ai.fractal.com).

## Tour hình ảnh

<table align="center" width="100%">
  <tr>
    <td colspan="2" align="center">
      <a href="https://www.youtube.com/watch?v=wHIvvv6fmHA">
        <img src="screenshots/video_demo.png" alt="Video" width="80%" style="border-radius: 12px;">
      </a>
      <br/><sub><a href="https://www.youtube.com/watch?v=wHIvvv6fmHA"><strong>▶ Xem video demo</strong></a></sub>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="screenshots/v31.png" alt="IDE" style="border-radius: 6px;"><br/><sub>IDE chỉ báo, biểu đồ, kiểm thử lùi</sub></td>
    <td width="50%" align="center"><img src="screenshots/v32.png" alt="AI" style="border-radius: 6px;"><br/><sub>Phân tích tài sản bằng AI</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="screenshots/v33.png" alt="Bots" style="border-radius: 6px;"><br/><sub>Bot giao dịch</sub></td>
    <td align="center"><img src="screenshots/v34.png" alt="Live" style="border-radius: 6px;"><br/><sub>Chiến lược thực &amp; hiệu suất</sub></td>
  </tr>
</table>

## Cài đặt và chạy lần đầu

1. Clone rồi `cp backend_api_python/env.example backend_api_python/.env`
2. **Phải đặt `SECRET_KEY`** (giữ placeholder thì backend không khởi động). Linux/macOS: `./scripts/generate-secret-key.sh`
3. `docker-compose up -d --build`
   - **Tùy chọn (không cần clone repo)**: kéo image backend + frontend đa kiến trúc (amd64/arm64) sẵn từ GHCR:
     ```bash
     curl -O https://raw.githubusercontent.com/brokermr810/Fractal/main/docker-compose.ghcr.yml
     curl -o backend.env https://raw.githubusercontent.com/brokermr810/Fractal/main/backend_api_python/env.example
     docker compose -f docker-compose.ghcr.yml up -d
     ```
     Image mặc định: `ghcr.io/brokermr810/fractal-{backend,frontend}:latest`. Ghim đồng thời cả hai bằng `IMAGE_TAG=v3.0.9` trong `.env` cục bộ, hoặc ghim từng bên với `BACKEND_TAG` / `FRONTEND_TAG`.
   - **Phát triển frontend cục bộ**: clone `Fractal-Vue` vào `./Fractal-Vue/` (đã gitignore) rồi chạy `docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build`. Chi tiết xem [README tiếng Anh](../README.md#alternative-build-the-frontend-from-vue-source).
4. **Web:** `http://localhost:8888` · **Sức khỏe API:** `http://localhost:5000/api/health`
5. Đổi mật khẩu quản trị mặc định trước production. Đặt **`FRONTEND_URL`** trong `backend_api_python/.env` đúng URL thực tế.

Tính năng AI: sao chép mục **AI / LLM** từ `env.example` sang `.env`, rồi khởi động lại backend. Danh sách đầy đủ xem [README tiếng Anh](../README.md) hoặc [简体中文](README_CN.md).

## Danh sách tài liệu

| Tài liệu | Mô tả |
|----------|--------|
| [English README](../README.md) | Bản đầy đủ (Anh) |
| [简体中文](README_CN.md) | Bản đầy đủ (Tiếng Trung giản thể) |
| [CHANGELOG](CHANGELOG.md) | Lịch sử phiên bản |
| [Agent nhanh](agent/AGENT_QUICKSTART.md) (Anh) | Agent Gateway / ví dụ curl |
| [Hướng dẫn chiến lược (Anh)](STRATEGY_DEV_GUIDE.md) | Phát triển chiến lược chỉ báo·script |

Khác: [multi-user-setup.md](multi-user-setup.md) · [IBKR](IBKR_TRADING_GUIDE_EN.md) · [MT5](MT5_TRADING_GUIDE_EN.md) — chi tiết chủ yếu bằng tiếng Anh.

## Câu hỏi thường gặp

**Có thật sự tự host được không?** Có, triển khai bằng Docker Compose trên hạ tầng của bạn.

**Chỉ tiền mã hóa?** Không. Hỗ trợ IBKR / Alpaca (cổ Mỹ · ETF · tiền mã hóa) và MT5 (FX).

**Viết chiến lược bằng Python được không?** Có, hỗ trợ `IndicatorStrategy` và `ScriptStrategy`.

**Thương mại?** Backend **Apache 2.0**. Frontend [Fractal-Vue](https://github.com/brokermr810/Fractal-Vue) có giấy phép riêng—đọc kỹ trước khi dùng thương mại. Di động theo [Fractal-Mobile](https://github.com/brokermr810/Fractal-Mobile).

**Có ứng dụng di động không?** Xem [Fractal-Mobile](https://github.com/brokermr810/Fractal-Mobile).

## Liên kết giới thiệu sàn (tham khảo)

| Sàn | Liên kết |
|-----|----------|
| Binance | [Đăng ký](https://www.bsmkweb.cc/register?ref=FRACTAL) |
| OKX | [Đăng ký](https://www.xqmnobxky.com/join/FRACTAL) |
| Bybit | [Đăng ký](https://partner.bybit.com/b/DINGER) |

## Giấy phép

- Backend: **Apache License 2.0** ([`../LICENSE`](../LICENSE))
- Web UI đi kèm: phân phối dựng sẵn. Mã nguồn tại [Fractal-Vue](https://github.com/brokermr810/Fractal-Vue) (giấy phép riêng)
- Thương hiệu: [`../TRADEMARKS.md`](../TRADEMARKS.md)

## Tuyên bố miễn trừ

Fractal dành cho nghiên cứu, giáo dục và giao dịch tuân thủ **hợp pháp**. **Không phải tư vấn đầu tư.** Bạn tự chịu trách nhiệm khi sử dụng.

## Cộng đồng

- [Telegram](https://t.me/fractal) · [Discord](https://discord.com/invite/tyx5B6TChr) · [Issues](https://github.com/brokermr810/Fractal/issues)
- Email: [support@fractal.com](mailto:support@fractal.com)

## Xu hướng Star

[![Star History Chart](https://api.star-history.com/svg?repos=brokermr810/Fractal&type=Date)](https://star-history.com/#brokermr810/Fractal&Date)

## Lời cảm ơn

Cảm ơn cộng đồng mã nguồn mở: Flask, Pandas, CCXT, Vue.js, KLineCharts, ECharts và nhiều dự án khác.

<p align="center"><sub>Nếu hữu ích, hãy cho một ngôi sao trên GitHub.</sub></p>
