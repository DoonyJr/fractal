# Indicator IDE — AI Generate: Technical Flow

## Overview

Indicator IDE memungkinkan user membuat trading indicator/strategy menggunakan natural language. Backend menggunakan LLM (via OpenRouter) untuk generate kode Python yang kompatibel dengan Fractal sandbox.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND (indicator-ide/index.vue)                               │
│                                                                   │
│  ┌──────────────┐    ┌───────────────────┐    ┌──────────────┐  │
│  │ AI Prompt    │───▶│ POST /api/indicator│───▶│ CodeMirror   │  │
│  │ (textarea)   │    │ /aiGenerate (SSE)  │    │ Editor       │  │
│  └──────────────┘    └───────────────────┘    └──────────────┘  │
│                              │                        ▲          │
│                              │ stream chunks          │          │
│                              ▼                        │          │
│                       parse SSE events ──────────────▶│          │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ BACKEND (app/routes/indicator.py)                                 │
│                                                                   │
│  1. Auth check (login_required)                                   │
│  2. Billing check (check_and_consume: 'ai_code_gen')             │
│  3. LLM Call → generate code                                      │
│  4. Validate code (_validate_indicator_code_internal)             │
│  5. Auto-fix if needed (_repair_code_via_llm)                    │
│  6. Stream response as SSE                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend Flow

**File:** `Fractal-Vue/src/views/indicator-ide/index.vue`

### 1. User Input
- User menulis deskripsi indicator di `<a-textarea v-model="aiPrompt">`
- Submit via tombol "Generate" atau `Ctrl+Enter`

### 2. Request
```javascript
POST /api/indicator/aiGenerate
Headers: {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer <token>',
  'X-App-Lang': 'en-US' // atau locale aktif
}
Body: {
  "prompt": "user's natural language description",
  "existingCode": "current code in editor (optional context)"
}
```

### 3. SSE Stream Processing
Frontend membaca stream menggunakan `ReadableStream` API:

```javascript
const reader = response.body.getReader()
const decoder = new TextDecoder()

while (true) {
  const { done, value } = await reader.read()
  if (done) break
  
  // Parse SSE format: "data: {...}\n\n"
  buffer += decoder.decode(value, { stream: true })
  const lines = buffer.split('\n\n')
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.substring(6)
      if (data === '[DONE]') break
      
      const json = JSON.parse(data)
      if (json.error) throw new Error(json.error)
      if (json.debug) → show AI debug summary card
      if (json.content) → append to editor realtime
    }
  }
}
```

### 4. Post-Generation
- Kode di-clean dari markdown blocks (`cleanMarkdownCodeBlocks`)
- Run `fetchCodeQualityHints(code)` → POST `/api/indicator/codeQualityHints`
- Sync strategy annotations ke UI (`syncTradeUiFromStrategyCode`)
- Mark `codeDirty = true`

---

## Backend Flow

**File:** `backend_api_python/app/routes/indicator.py`

### Endpoint: `POST /api/indicator/aiGenerate`

#### Step 1: Billing Check
```python
billing.check_and_consume(
    user_id=user_id,
    feature='ai_code_gen',
    reference_id=f"ai_code_gen_{user_id}_{timestamp}"
)
```
- Jika kredit tidak cukup → stream error `{"error": "积分不足"}`

#### Step 2: LLM Code Generation (`_generate_code_via_llm`)
- **System Prompt** — sangat detail, mendefinisikan:
  - Fractal sandbox constraints (no network, no file I/O, no `import os`)
  - Allowed imports: `numpy`, `pandas`, `math`, `json`, `datetime`, etc.
  - Input contract: `df` (OHLCV DataFrame), `params` dict
  - Output contract: `output` dict dengan `name`, `plots`, `signals`
  - Signal columns: `df['buy']`, `df['sell']` (boolean) atau `df['open_long']`, `df['close_long']`, `df['open_short']`, `df['close_short']`
  - `@param` dan `@strategy` annotation format
  - Series vs ndarray rules (common AI bug prevention)
- **Model:** configurable via `LLMService.get_code_generation_model()`
- **Temperature:** 0.4 (first pass), 0.2 (repair pass)

#### Step 3: Validation (`_validate_indicator_code_internal`)
Setelah LLM generate kode, backend run validation:
- Syntax check
- Sandbox compliance (no banned imports)
- Contract compliance (output structure, signal lengths)
- Runtime smoke test (execute in sandboxed environment)

#### Step 4: Auto-Fix (`_repair_code_via_llm`)
Jika validation gagal, backend otomatis:
1. Format validation issues
2. Kirim kode + issues ke LLM lagi dengan repair prompt
3. Re-validate repaired code
4. Pilih candidate terbaik (initial vs repaired)

**Auto-fix trigger codes:**
- `DECLARED_PARAMS_NOT_READ_VIA_PARAMS_GET`
- `SIGNAL_MARKERS_USE_WHERE_NONE`
- `MISSING_OUTPUT`
- `MISSING_BUY_SELL_COLUMNS`
- `MISSING_DF_COPY`
- `MISSING_INDICATOR_NAME`
- `MISSING_INDICATOR_DESCRIPTION`
- `UNKNOWN_STRATEGY_KEY`

#### Step 5: Stream Response
```python
def stream():
    # 1. Debug info (validation summary)
    yield "data: " + json.dumps({"debug": debug_info}) + "\n\n"
    
    # 2. Code in 200-char chunks
    for i in range(0, len(code_text), 200):
        chunk = code_text[i : i + 200]
        yield "data: " + json.dumps({"content": chunk}) + "\n\n"
    
    # 3. Done signal
    yield "data: [DONE]\n\n"

return Response(stream(), mimetype="text/event-stream")
```

---

## Endpoint: `POST /api/indicator/codeQualityHints`

Frontend memanggil ini setelah AI generate selesai, dan juga saat user klik "Check current code".

### Request
```json
{ "code": "full indicator source code" }
```

### Process
1. **Static analysis** (`analyze_indicator_code_quality`):
   - Structural checks (missing output, missing columns, bad imports)
   - Returns hints with severity: `error`, `warn`, `info`

2. **Runtime dry-run** (jika tidak ada static error):
   - Execute kode di sandbox
   - Jika crash → append `RUNTIME_ERROR_ON_VERIFY` hint

### Response
```json
{
  "code": 1,
  "data": {
    "hints": [
      {
        "severity": "error",
        "code": "MISSING_BUY_SELL_COLUMNS",
        "params": {}
      },
      {
        "severity": "warn",
        "code": "SIGNAL_MARKERS_USE_WHERE_NONE",
        "params": { "detail": "..." }
      }
    ]
  }
}
```

---

## SSE Event Types

| Event | Format | Description |
|-------|--------|-------------|
| Error | `{"error": "message"}` | Billing/auth/LLM failure |
| Debug | `{"debug": {...}}` | Validation summary + auto-fix status |
| Content | `{"content": "code chunk"}` | Incremental code (200 chars/chunk) |
| Done | `[DONE]` | Stream selesai |

---

## Debug Summary (AI QA Card)

Ditampilkan sebagai card di bawah editor:

```json
{
  "title": "AI Code Quality Check",
  "auto_fix_applied": true,
  "auto_fix_succeeded": true,
  "fixed_messages": ["Added df.copy()", "Added missing output dict"],
  "remaining_messages": ["Consider adding stop-loss annotation"]
}
```

States:
- **success** — code passed all checks
- **warning** — non-blocking issues remain
- **error** — blocking issues that user must fix manually

---

## Indicator Code Contract

```python
# @name My Indicator
# @description Short description
# @param period int 14 Lookback period
# @strategy stopLossPct 0.03
# @strategy tradeDirection long

df = df.copy()
df['buy'] = False
df['sell'] = False

# ... indicator logic using df['open'], df['high'], df['low'], df['close'], df['volume']

output = {
    'name': 'My Indicator',
    'plots': [
        {'name': 'SMA', 'data': sma_values.tolist(), 'overlay': True}
    ],
    'signals': [
        {'type': 'buy', 'text': 'BUY', 'color': '#26a69a', 'data': buy_markers}
    ]
}
```

### Rules:
- `pd` dan `np` sudah tersedia (jangan import)
- `df['buy']`/`df['sell']` harus boolean Series
- Semua `plot['data']` dan `signal['data']` length == `len(df)`
- Gunakan vectorized pandas operations (hindari row-by-row loops)
- No banned imports (`os`, `sys`, `subprocess`, dll)

---

## Sequence Diagram

```
User                    Frontend                 Backend                  LLM
  │                        │                        │                       │
  │─── type prompt ───────▶│                        │                       │
  │─── click Generate ────▶│                        │                       │
  │                        │── POST /aiGenerate ───▶│                       │
  │                        │                        │── billing check ──────│
  │                        │                        │── build system prompt ─│
  │                        │                        │── call LLM ──────────▶│
  │                        │                        │◀── generated code ────│
  │                        │                        │── validate code ──────│
  │                        │                        │── [if bad] repair ───▶│
  │                        │                        │◀── repaired code ─────│
  │                        │                        │── re-validate ────────│
  │                        │◀─ SSE: debug info ─────│                       │
  │                        │◀─ SSE: content chunks ─│                       │
  │                        │◀─ SSE: [DONE] ─────────│                       │
  │◀── editor updates ────│                        │                       │
  │                        │── POST /codeQuality ──▶│                       │
  │                        │◀── hints response ─────│                       │
  │◀── quality card ──────│                        │                       │
```
