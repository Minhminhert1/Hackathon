# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A two-part FX chat-scraping tool built for the MSB AI Hackathon 2026 (Treasury division): a Chrome MV3 extension scrapes the "FXVN" chat room in LSEG Refinitiv Workspace Messenger, and a local FastAPI server receives the scraped messages over HTTP and appends them to daily JSONL files.

The downstream parser described in `tom_tat_du_an_FXVN.md` — `bank_resolver.py`, `bank_mapping.json`, `classify.py`, `deal_matcher.py`, `run_parser.py` — now lives in `fxvn_parser/` (see Architecture below). `fxvn_dashboard.html` at the repo root is a self-contained, standalone dashboard: its quote cards/charts/trader-table still run their own simplified JS-side classifier over a raw `.jsonl` upload, but it can now also load `fxvn_parser/deals.json` directly (a separate file input) to show the parser's actual matched deals in a dedicated table — see Architecture below.

`FX_COLLECTOR_CODEBASE.md` is an auto-generated dump of the source (via `scratch/bundle_code.py`) meant for pasting into a review tool — it is not documentation to maintain by hand.

## Commands

- Install deps: `pip install -r requirements.txt`
- Run server: `python server.py` (or `run_server.bat`, which also kills any process already listening on port 8000 before starting). Server binds `127.0.0.1:8000`.
  - Health/stats: `GET /`
  - Live dashboard (auto-refreshes every 5s): `GET /status`
  - Manually trigger the heartbeat alert for testing: `GET /test-heartbeat`
- Load the extension: load `extension/` unpacked in Chrome (`chrome://extensions` → Developer mode → Load unpacked). Requires being logged into LSEG Refinitiv Workspace and viewing the "FXVN" room.
- Run the parser on a collected JSONL file: `cd fxvn_parser && python run_parser.py ..\data\data-YYYY-MM-DD.jsonl` — writes `quotes.json` and `deals.json` into `fxvn_parser/` (overwriting whatever was there before) and prints a one-line summary of quote/deal counts by confidence.

There is no formal test framework, no lint/format config, and no CI in this repo. "Tests" are ad-hoc scripts in `scratch/` that launch headless Chrome against static HTML fixtures and grep the console/stderr output for expected strings (no assertions — pass/fail is judged by eye), e.g.:

```
python scratch\run_test_switch.py
python scratch\run_test_multiroom.py
python scratch\run_debug.py
```

Every script in `scratch/` resolves paths to files inside the repo relative to its own location, so they all run from a fresh clone anywhere. The Chrome-driven ones above plus `check_syntax.py` still hardcode the Chrome binary path (`C:\Program Files\Google\Chrome\Application\chrome.exe`), so those are Windows-only as written; `bundle_code.py` and `run_test_parser.py` need no browser and run anywhere.

## Architecture / data flow

Refinitiv Messenger page DOM → `extension/content.js` (MutationObserver scrape) → batched `fetch` POST → `server.py` `/api/messages` → append-only `data/data-YYYY-MM-DD.jsonl`.

- **`extension/manifest.json`** — MV3 config; `host_permissions` cover `*.refinitiv.com`/`*.lseg.com` plus `http://localhost:8000`/`http://127.0.0.1:8000`; injects `config.js` then `content.js` as content scripts into the page's `"world": "MAIN"` at `document_start`, `all_frames: true`.
- **`extension/config.js`** — single source of truth for `window.FX_CONFIG`: server URL, batch interval (3000ms), and every CSS selector / `data-*` attribute name used to find the chat container and read message fields (`data-message-id`, `data-sender-name`, `data-company`, `data-timestamp`, `data-date`, `[data-testid="parsed-raw-message"]`). **This is the file to change first if Refinitiv's UI/DOM changes.**
- **`extension/content.js`** — the scraper:
  - `isViewingFXVN()` — heuristics to only collect from the "FXVN" room, not other rooms (e.g. "MSB Swap").
  - `checkAndBindContainer()` — finds `#conversation-container` and attaches a `MutationObserver` (`childList`, `subtree`) since the page uses virtual scrolling (old messages vanish from the DOM).
  - `processMessageElement()` — extracts message fields, dedupes via in-memory `seenMessageIds`, assigns an incrementing `seq`, pushes to `pendingQueue`.
  - `flushBatch()` — POSTs the queue as `{ messages: [...] }` every `BATCH_INTERVAL_MS` (3s), trying the configured server URL then `127.0.0.1`/`localhost` fallbacks; undelivered items just stay queued for the next flush.
  - A second interval (1.5s) re-checks container binding/FXVN status and rescans visible messages; a root-level `MutationObserver` on `document.body` detects SPA navigation and re-binds the container.
- **`server.py`** — single-file FastAPI/Uvicorn app (`uvicorn.run(app, host='127.0.0.1', port=8000)`):
  - Custom PNA (Private Network Access) middleware + permissive `CORSMiddleware`, needed for Chrome's private-network preflight when the extension calls `http://127.0.0.1:8000` from a `https://*.refinitiv.com` page.
  - `lifespan()` calls `load_existing_ids()` on startup to rehydrate the dedup set/counters from today's JSONL file, and spawns a background `heartbeat_monitor()` asyncio task (cancelled on shutdown).
  - `heartbeat_monitor()` — every 5s calls `flush_unsaved_buffer()`, and during work hours (`WORK_HOURS_START`–`WORK_HOURS_END`, 08:30–16:00) alerts (throttled to once per 5 min) if `HEARTBEAT_TIMEOUT_MINUTES` (30) have passed with no new message.
  - `POST /api/messages` and alias `POST /messages` (`receive_messages()`) — accepts a `BatchPayload`, a bare list, or a single `RawMessage`; dedupes by `message_id`, cleans whitespace/names, forces `room_name` to `'FXVN'`, and appends each record as one JSON line to `data/data-YYYY-MM-DD.jsonl` (UTF-8, `ensure_ascii=False`).
  - On `PermissionError` (file locked, e.g. open in Excel/Word) records are buffered in memory (`unsaved_buffer`) instead of lost, and retried by the heartbeat monitor once the file unlocks.
  - Config (data dir, heartbeat timeout, work hours, host/port) is hardcoded as constants at the top of the file — there's no `.env`/environment-variable layer.
- **`fxvn_parser/`** — offline parser that turns a collected `data/data-YYYY-MM-DD.jsonl` into structured spot deals. Pure stdlib (`json`, `re`, `os`, `sys`, `unicodedata`), no extra dependencies.
  - `bank_resolver.py` — `BankResolver` loads `bank_mapping.json` (33 banks + aliases/SWIFT/internal deal codes) and resolves a bank from `data-company` (`from_company()`) or free text (`find_in_text()`), matching accent-stripped/lowercased tokens.
  - `classify.py` — regex-based `classify(text)` labels each message `quote_spot` / `quote_swap` / `confirm` / `noise` / `partial` / `other`, extracting side (bid/offer/two_way), 2-digit spot price fragments (26.2xx convention), volume, and tenor.
  - `deal_matcher.py` — `match_deals()` implements the business rule from `fxvn_parser/README.md`: A = the original quoter, B = whoever counters in the opposite direction; a deal closes when A says "done" + counterparty name/bank; price = the last agreed number before "done"; volume comes from the done message or falls back to B's; one "done" naming multiple people splits into multiple deals. Confidence is `high`/`medium`/`low` depending on how much of that chain (A's quote, B's message, price, volume) was actually found.
  - `run_parser.py` — entry point: `python run_parser.py <file.jsonl>` loads and re-sorts rows by `(date, hh, mm, ss, seq)` (this is what fixes the virtual-scroll message-ordering bug noted in `tom_tat_du_an_FXVN.md`), then classifies + matches deals, writing `quotes.json` and `deals.json` into the **current working directory** (not necessarily `fxvn_parser/` — invoke it from inside that folder, since it also loads `bank_mapping.json` relative to the script's own location).
  - Known open gaps (see `fxvn_parser/README.md`, "CÒN CẦN HOÀN THIỆN"): Vietnamese nickname matching for B, big-figure rollover past 26.2xx (hardcoded), no NHNN band validation, no quote lifecycle (live/pulled/hit) for best-bid/offer, no LLM fallback for `other`/`partial` messages, swap pipeline not split out. Don't assume these are solved — deal confidence will legitimately be `low`/`medium` for a large fraction of output until they are.
  - `fxvn_dashboard.html`'s quote view still re-implements a much simpler bid/offer-only classifier in inline JS over a raw `.jsonl` upload; its "Giao dịch đã khớp (deal)" panel (a second file input, `#dealsIn`) loads `fxvn_parser/deals.json` directly and renders the parser's real matched deals (price, buyer/seller bank, confidence pill) — the two views are independent and don't share filters.

## AI agent workflow policy

This repo enforces `AI-rule.md`, a Spec-Driven Development policy for AI coding agents: **Discover → Specify → Design Tests → Implement → Verify → Report** is mandatory for any non-trivial change, gated by a Specification Gate (blocks and reports `SPEC BLOCKED` when requirements are ambiguous) and closed out with mandatory completion artifacts (Feature Contract, Implementation Summary, Requirement Traceability, Verification, Commands Run, Known Risks) plus a compliance status against gates C-01..C-12. Small mechanical changes (typos, formatting, comments, docs, pure renames) are exempt via the Small-Change Exception.

Read `AI-rule.md` in full before starting any non-trivial implementation work in this repo.
