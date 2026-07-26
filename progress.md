---
title: Chem Exam Bank Progress Tracker
type: progress
tags: [chem, exams, posn, pat2, samanya, tracking]
created: 2026-07-01
summary: Status of every source exam paper (POSN, 9 วิชาสามัญ, PAT2) in the question bank extraction pipeline. Verified against reality 2026-07-26 — question-bank.md now has 1,104 questions.
---

# Progress tracker

Status of every source file. Update as you go: `pending → extracted → reviewed`.
Rebuilt 2026-07-07 against reality: `question-bank.md` has **922 questions** (was 595 when this
file was last accurate) — the samanya and most-of-PAT2 rows below were simply never added after
those batches landed.

## สอวน. (POSN), รอบ 1 — all 8 done

| Source file | Year (B.E.) | Format | Status | Q-IDs | Notes |
|-------------|------|--------|--------|-------|-------|
| posn1-60-chem.pdf | 2560 | text PDF | **extracted** | Q-0376–Q-0445 | 70 Q (60 mcq + 10 อัตนัย) |
| posn1-61-chem.pdf | 2561 | text PDF | **extracted** | Q-0301–Q-0375 | 75 Q (60 mcq + 15 อัตนัย) |
| posn1-62-chem.pdf | 2562 | text PDF | **extracted** | Q-0226–Q-0300 | 75 Q (60 mcq + 15 อัตนัย) |
| posn1-64-chem.pdf | 2564 | **scanned/image** | **extracted** | Q-0446–Q-0520 | 75 Q. Transcribed from page images — spot-check recommended |
| posn1-65-chem.pdf | 2565 | **scanned/image** | **extracted** | Q-0521–Q-0595 | 75 Q. Transcribed from page images — spot-check recommended |
| posn1-66-chem.pdf | 2566 | text PDF | **extracted** | Q-0151–Q-0225 | 75 Q (60 mcq + 15 อัตนัย) |
| posn1-67-chem.pdf | 2567 | text PDF | **extracted** | Q-0076–Q-0150 | 75 Q (60 mcq + 15 อัตนัย) |
| posn1-68-chem.pdf | 2568 | text PDF | **extracted** | Q-0001–Q-0075 | 75 Q (60 mcq + 15 อัตนัย). PILOT |

(Year 2563 / posn1-63 not present, per Prat.) **595 questions, 0 reviewed** — none spot-checked yet.
No answer keys in any of these papers — every `**Answer:**` is `_(no key)_`, don't invent one.

## 9 วิชาสามัญ เคมี (samanya) — 3 source files, but 4 years merged in the bank

| Source file | Year (B.E.) | Format | Status | Q-IDs | Notes |
|-------------|------|--------|--------|-------|-------|
| 9_common_58_Chemistry.pdf | 2558 | text PDF | **extracted, merged** | Q-0596–Q-0645 | 50 Q |
| 9_common_59_Chemistry.pdf | 2559 | text PDF | **extracted, merged** | Q-0823–Q-0872 | 50 Q |
| 9_common_61_Chemistry.pdf | 2561 | text PDF | **extracted, merged** | Q-0873–Q-0922 | 50 Q |
| _(no source PDF present)_ | 2555 | ? | **extracted, merged** | Q-0646–Q-0695 | 50 Q. `tools/incoming/done/samanya-55.md` was already merged into the bank, but no `9_common_55*`-style PDF exists in `source/` today — flagging so Prat can confirm whether the file was moved/renamed/deleted, or extracted from elsewhere. |

**200 questions total, 0 reviewed.**

## PAT2 (สอบตรง, combined science: bio+chem only extracted here) — 12 source files, 6 done

Full file→paper→Q-id map lives in `tools/PAT2-EXTRACTION-METHOD.md` (source of truth, last updated
2026-07-06) — this table is the merge-status cross-check against the actual bank + `tools/incoming/`.

| Paper (year·session) | Source file | Status | Q-IDs (as merged/drafted) | Notes |
|---|---|---|---|---|
| 2552 · มี.ค. | `2017112152132.pdf` | **extracted, merged** | 72 Q (in bank, `#exam/pat2 #year/2552 #ver/mar`) | |
| 2554 · ต.ค. | `2017112152431.pdf` | **extracted, merged** | 55 Q (in bank, `#year/2554 #ver/oct`) | Gold-standard reference fragment |
| 2553 · มี.ค. | `pat2 2553 .pdf` (spaces in name) | **extracted, merged** ✅ 2026-07-26 | Q-0923–0977 (55 Q, 14 figs) | |
| 2552 · ก.ค. | `2017112152148.pdf` | **extracted, merged** ✅ 2026-07-26 | Q-1023–1094 (72 Q: 40 bio + 32 chem) | |
| 2552 · ต.ค. | `2017112152158.pdf` | **⏳ in progress (partial)** | Q-1123–1186 drafted (64 of 72) | Fragment in `tools/incoming/_wip/pat2-2552-oct.md` — **missing Q-1187–Q-1194 (last 8)**, don't merge yet |
| 2553 · ก.ค. | `2017112152247.pdf` | **extracted, merged** ✅ 2026-07-26 | Q-1223–1277 (55 Q: 30 chem + 25 bio, 12 figs) | |
| 2553 · ต.ค. | `2017112152259.pdf` | **⏳ in progress** | Q-1323–1422 (block reserved) | No fragment file yet |
| 2554 · มี.ค. | `2017112152416.pdf` | **⬜ queued (pending)** | Q-1423–1522 (block reserved) | |
| 2555 · มี.ค. | `2017112152455.pdf` | **⬜ queued (pending)** | Q-1523–1622 (block reserved) | |
| 2555 · ต.ค. | `2017112152510.pdf` | **⬜ queued (pending)** | Q-1623–1722 (block reserved) | |
| 2556 · มี.ค. | `2017112152559.pdf` | **⬜ queued (pending)** | Q-1723–1822 (block reserved) | |
| _(unidentified)_ | `________________________ 2555.pdf` | **pending / unclassified** | — | Odd filename (looks corrupted/renamed), not in `PAT2-EXTRACTION-METHOD.md`'s inventory. Possibly a duplicate of `2017112152455.pdf` (also 2555) — needs a look before extracting to avoid double-counting a paper. |

**309 questions merged** (`#exam/pat2`, 5 papers) — **the 3 finished fragments were built in on 2026-07-26,
taking the whole bank 922 → 1,104.** 1 paper is part-drafted (2552·ต.ค., 8 questions short); 5 papers
(incl. the unidentified file) are still pending/queued and have no fragment yet.

## Legend
- **pending** — not processed yet
- **extracted** — questions pulled into a fragment or the bank
- **merged** — the fragment has actually been folded into `question-bank.md` via `build_bank.py`
- **reviewed** — Prat (or a spot-check) confirmed accuracy, especially for scans

## How the bank is built
- Author each exam as a fragment in `tools/incoming/*.md`, then run `python tools/build_bank.py`.
  It merges fragments + the existing bank, re-sorts by chapter, rewrites `question-bank.md`,
  auto-generates the "Needs review" list, archives the fragment to `tools/incoming/done/`,
  and refreshes `index.html` (the live viewer/site root). (Needs `pip install markdown pymupdf`.)
- **Not-ready fragments:** park them in `tools/incoming/_wip/` — the build's glob is top-level-only
  (non-recursive), so anything in that subfolder is ignored until you move it back up to
  `tools/incoming/`. See `tools/incoming/_wip/README.md`.

## Notes
- **No answer keys** in POSN or PAT2 papers (blank answer sheets only). Per Prat's instruction,
  every `**Answer:**` is `_(no key)_`. 9 วิชาสามัญ papers may carry a real key where present.
- **Chapter coverage (chem, all exams combined):** every one of the 14 chapters now has at least
  one question; ch09/ch10/ch11/ch13/ch14 were POSN-รอบ-1 gaps (ม.4-only content) but samanya/PAT2
  cover ม.5–ม.6 topics.
- Figures (diagrams, Lewis structures, GHS pictograms, manometers, etc.) are embedded as
  `images/Q-NNNN.png` + a `**Figure:**` line where reproduced; unreproduced figure-dependent
  questions carry a `**Note:**` and surface under "Needs review" in `question-bank.md`.
- Year is recorded as the Buddhist year on the paper (e.g. `#year/2568`).

## Counts (as of 2026-07-07)
- **922 questions** in `question-bank.md` (0 reviewed — awaiting Prat spot-check across the board).
- POSN: 595 (8/8 source files merged). Samanya: 200 (3 source files identified + 1 unaccounted-for
  source, all 4 years merged). PAT2: 127 merged (2/12 source files), 4 more drafted in `_wip/`
  awaiting merge, 1 partial, 5 pending/unclassified (incl. one odd filename needing a look).
