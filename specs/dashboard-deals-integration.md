# Feature: Dashboard deal-table integration

## Problem
`fxvn_dashboard.html` only re-implemented a simplified, standalone JS classifier (bid/offer counts from raw text) and had no way to show actual matched deals. The real deal-matching logic already lives in `fxvn_parser/deal_matcher.py` (verified working — see `specs/parser-integration.md`), but its output (`deals.json`: price, buyer/seller bank, confidence) was never surfaced in the dashboard.

## Goal
Let the dashboard load a `deals.json` file produced by `fxvn_parser/run_parser.py` and display the matched deals (confirm order, A/B parties, buyer/seller bank, price, volume, confidence) in a new table panel, without touching the existing quote-based charts/cards/filters.

## Non-Goals
- Do not replace the existing JS-side quote classifier (`classify()`, price chart, bank-net chart, trader table) — those still work standalone from a raw `.jsonl` upload and are out of scope.
- Do not share bank/dealer filters between the existing quote view and the new deals table.
- Do not auto-fetch `deals.json` via `fetch()` (blocked by browser file:// restrictions in the common case); reuse the existing FileReader-based file-input pattern already used for the raw `.jsonl` loader.
- Do not modify `fxvn_parser/` output schema.

## Functional Requirements
- FR-1: A new file input ("Nạp deals.json (từ parser)") MUST let the user pick a `deals.json` file produced by `run_parser.py` and load it via `FileReader`, matching the existing `.jsonl` loader's pattern.
- FR-2: On successful load, a new panel MUST render one row per deal: confirm order, A trader+bank+side, B target+bank, buyer bank, seller bank, price (`price_full` falling back to `price_short`), volume, confidence (colored pill), and the raw confirmation text.
- FR-3: The panel MUST show a summary line with total deal count and counts by confidence (high/medium/low), and MUST show a placeholder message before any file is loaded.
- FR-4: Malformed/non-array JSON MUST show an alert with the error message and MUST NOT throw an uncaught exception or leave the page in a broken state.

## Acceptance Criteria
- AC-1: Loading `fxvn_parser/deals.json` (217 records, high=23/medium=136/low=58) renders exactly 217 `<tr>` rows in `#dealsTable tbody` and the summary text `"217 deal spot đã khớp (high=23, medium=136, low=58)"`.
- AC-2: Confidence values map to distinct pill colors (`conf-high` green, `conf-medium` amber, `conf-low` red).
- AC-3: Before loading, `#dealsSub` shows the placeholder text referencing `fxvn_parser/run_parser.py`.
- AC-4: Existing quote-based cards/charts/trader-table behavior is visually unchanged (regression).

## Edge Cases
- EC-1: `deals.json` is valid JSON but not an array → error alert, no partial render.
- EC-2: A deal record has `price_full: null` and `price_short: null` → price column shows `—`, not `null`/`NaN`.
- EC-3: `buyer_bank`/`seller_bank`/`B_bank` are `null` (common — "20% khó" nickname-matching gap) → shows `—`/`(?)` rather than the literal string `"null"`.

## Interfaces / Contracts
- Input file: `fxvn_parser/deals.json` schema (unchanged, produced by `run_parser.py`): `confirm_order, kind, A_trader, A_bank, A_side, B_target, B_bank, buyer_bank, seller_bank, price_short, volume, confidence, confirm_text, a_quote_order, b_order, price_full`.
- New DOM: `#dealsIn` (file input), `#dealsSub` (summary text), `#dealsTable` (table container).
- New globals in the dashboard's inline script: `DEALS` (array), `renderDeals()`, `confPill()`, `sidePill()`.

## Constraints
- No build step / bundler / new dependencies — must stay a single self-contained HTML file (existing project convention).
- Must keep working when opened directly as `file://` (existing usage pattern), not just via a server.

## Assumptions
- The user will manually export/copy `deals.json` next to wherever they open the dashboard from, same as the existing raw-`.jsonl` workflow.

## Open Questions
- None blocking. (Whether to eventually merge deal rows into the trader table/filters is left for a future iteration.)

## Test Design

| Test ID | Requirement | Level | Scenario | Expected Result |
|---|---|---|---|---|
| T-01 | FR-1/AC-1 | Integration | Simulate real `change` event on `#dealsIn` with `fxvn_parser/deals.json` (217 records) inside an iframe harness | `#dealsTable tbody tr` count = 217; summary text matches `high=23, medium=136, low=58` |
| T-02 | FR-3/AC-3 | Manual/DOM | Page loaded, no file picked | `#dealsSub` shows placeholder referencing `run_parser.py` |
| T-03 | FR-4/EC-1 | Manual | Load a non-array JSON file | Alert shown, `DEALS`/table unchanged, no thrown exception (verified by continued script execution/log) |
| T-04 | AC-2 | Visual | Screenshot after load | High/medium/low pills render in 3 distinct colors (screenshot inspected) |
| T-05 | AC-4 | Visual | Screenshot of default (baked-in sample) view before touching deals loader | Cards/price chart/bank chart/trader table unchanged from pre-change baseline screenshot |
| Security | — | N/A | No network calls; file content only ever read via user-initiated `FileReader`, rendered via template-literal into `innerHTML` (existing pattern already used for jsonl loader; data originates from the user's own local parser output, not an external/untrusted source) | N/A |
| Performance | — | N/A | 217 rows renders instantly; no pagination needed at this scale | N/A |
