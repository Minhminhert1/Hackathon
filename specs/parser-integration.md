# Feature: FXVN parser integration

## Problem
The repo previously only collected raw FXVN chat messages into daily JSONL files. No downstream parsing existed in the repo — `CLAUDE.md` explicitly stated the parser (`bank_resolver.py`, `bank_mapping.json`, `classify.py`, `deal_matcher.py`, `run_parser.py`) was external/future work. The user has now provided that parser bundle and extracted it into `fxvn_parser/` at the repo root.

## Goal
Bring the already-written parser bundle into the repo's documented workflow: confirm it runs correctly against real collected data in `data/`, and document it so `CLAUDE.md` accurately reflects the repo's contents.

## Non-Goals
- Do not modify the classification/deal-matching business logic in `classify.py` / `deal_matcher.py` (the "20% khó" gaps listed in `fxvn_parser/README.md` are separate future work: nickname matching, big-figure rollover, NHNN band checks, quote lifecycle, LLM fallback, swap pipeline split).
- Do not wire `fxvn_dashboard.html` to real `deals.json`/`quotes.json` output (dashboard currently has its own simplified JS classifier and file-upload flow; connecting it is a separate future step per `tom_tat_du_an_FXVN.md` §10.5).
- Do not touch golden-set labeling.
- Do not delete `aa.zip` or any files (deletion of redundant extraction leftovers was attempted and blocked by the permission classifier; left for the user to do manually).

## Functional Requirements
- FR-1: `python run_parser.py <path-to-jsonl>` (run from inside `fxvn_parser/`) MUST process a real collected JSONL file from `data/` without raising an exception.
- FR-2: The run MUST produce `quotes.json` and `deals.json` in `fxvn_parser/`, and the console summary counts MUST be captured as evidence (not assumed).
- FR-3: `CLAUDE.md` MUST be updated to describe `fxvn_parser/` as present in the repo, replacing the now-incorrect statement that the downstream parser is absent.

## Acceptance Criteria
- AC-1: Running the parser against `data/data-2026-09-05.jsonl` (1823 lines) exits without error and prints non-zero quote/deal counts.
- AC-2: `fxvn_parser/quotes.json` and `fxvn_parser/deals.json` are regenerated (mtime updated) after the run.
- AC-3: `CLAUDE.md`'s Architecture section documents `fxvn_parser/`'s five modules, how to run it, and its known limitations; the "not present in this repo" sentence is removed or corrected.
- AC-4: A repeatable smoke-test script exists at `scratch/run_test_parser.py` following the existing ad-hoc test convention (no formal assertions, pass/fail by eye).

## Edge Cases
- EC-1: Data file path contains non-ASCII characters (Vietnamese folder name "Máy tính") — must open correctly with UTF-8 on Windows.
- EC-2: `run_parser.py` writes outputs to the current working directory, not necessarily next to the script — must invoke it in a way that lands `quotes.json`/`deals.json` in a predictable location (`fxvn_parser/`).
- EC-3: Larger dataset (1823 lines) than the original sample (1077 lines) it was authored/tested against — parser must not assume a fixed size.

## Interfaces / Contracts
- CLI: `python run_parser.py <file.jsonl>` (unchanged, pre-existing contract from the provided bundle).
- Input: JSONL records as written by `server.py` (`message_id`, `sender_name`, `bank_full`, `timestamp`, `date`, `text`, `room_name`, `direction`, `seq`, `captured_at`).
- Output: `quotes.json`, `deals.json` (pre-existing schema from the provided bundle, unchanged).

## Constraints
- No new dependencies (parser uses stdlib only: `json`, `re`, `os`, `sys`, `unicodedata`).
- Repo is not a git repository — avoid destructive/irreversible file operations; the leftover duplicate files from extraction (root `README.md`, `deals.json`, `fxvn_parser.zip`) are flagged for the user rather than deleted by the agent (blocked by permission classifier).

## Assumptions
- The parser code itself is correct/complete as provided (not authored in this task) — this task validates integration/execution, not the business logic.
- Overwriting the sample `quotes.json`/`deals.json` already present in `fxvn_parser/` (outputs from a prior run on older data) is acceptable, since they are just example outputs, not authoritative records.

## Open Questions
- None blocking. (Whether to eventually wire the dashboard to real parser output, and whether to delete the redundant root-level extraction leftovers, are left to the user.)

## Test Design

| Test ID | Requirement | Level | Scenario | Expected Result |
|---|---|---|---|---|
| T-01 | FR-1/AC-1 | Integration | Run `run_parser.py` on `data/data-2026-09-05.jsonl` | Exits 0, prints non-zero quote/deal counts |
| T-02 | FR-2/AC-2 | Integration | Inspect `fxvn_parser/quotes.json` & `deals.json` after run | Files updated, valid JSON, non-empty arrays |
| T-03 | EC-1 | Unit/Manual | Path includes Vietnamese diacritics | File opens/reads without `UnicodeDecodeError` |
| T-04 | FR-4/AC-4 | Manual | Run `scratch/run_test_parser.py` | Prints summary + sample records, no traceback |
| T-05 | — | Regression | Existing collector (`server.py`, `extension/`) untouched | No behavior change (no files in those paths modified) |
| Security | — | N/A | No network/DB/user-input boundary introduced by this change | N/A — parser only reads local files |
| Performance | — | N/A | 1823-line file is small; no performance concern | N/A |
