---
title: Chem Exam Bank Progress Tracker
type: progress
tags: [chem, exams, posn, tracking]
created: 2026-07-01
summary: Status of every POSN chemistry exam paper in the question bank extraction pipeline.
---

# Progress tracker

Status of every source file. Update as you go: `pending → extracted → reviewed`.

| Source file | Year (B.E.) | Version | Format | Status | Q-IDs | Notes |
|-------------|------|---------|--------|--------|-------|-------|
| posn1-60-chem.pdf | 2560 | รอบ 1 | text PDF | **extracted** | Q-0376–Q-0445 | 70 Q (60 mcq + 10 อัตนัย) |
| posn1-61-chem.pdf | 2561 | รอบ 1 | text PDF | **extracted** | Q-0301–Q-0375 | 75 Q (60 mcq + 15 อัตนัย) |
| posn1-62-chem.pdf | 2562 | รอบ 1 | text PDF | **extracted** | Q-0226–Q-0300 | 75 Q (60 mcq + 15 อัตนัย) |
| posn1-64-chem.pdf | 2564 | รอบ 1 | **scanned/image** | **extracted** | Q-0446–Q-0520 | 75 Q. Transcribed from page images — **spot-check recommended** |
| posn1-65-chem.pdf | 2565 | รอบ 1 | **scanned/image** | **extracted** | Q-0521–Q-0595 | 75 Q. Transcribed from page images — **spot-check recommended** |
| posn1-66-chem.pdf | 2566 | รอบ 1 | text PDF | **extracted** | Q-0151–Q-0225 | 75 Q (60 mcq + 15 อัตนัย) |
| posn1-67-chem.pdf | 2567 | รอบ 1 | text PDF | **extracted** | Q-0076–Q-0150 | 75 Q (60 mcq + 15 อัตนัย) |
| posn1-68-chem.pdf | 2568 | รอบ 1 | text PDF | **extracted** | Q-0001–Q-0075 | 75 Q (60 mcq + 15 อัตนัย). PILOT |

(Note: year 2563 / posn1-63 not present, per Prat. All 8 source files now extracted; none yet `reviewed`.)

## Legend
- **pending** — not processed yet
- **extracted** — questions pulled into question-bank.md
- **reviewed** — Prat (or a spot-check) confirmed accuracy, especially for scans

## How the bank is built
- Author each exam as a fragment in `tools/incoming/*.md`, then run `python tools/build_bank.py`.
  It merges fragments + the existing bank, re-sorts by chapter, rewrites `question-bank.md`,
  auto-generates the "Needs review" list, archives the fragment to `tools/incoming/done/`,
  and refreshes `question-bank-viewer.html`. (Needs `pip install markdown pymupdf`.)

## Notes for this batch (สอวน. รอบ 1, ปี 2560–2568)
- **No answer keys** are included in any of these exam papers (just a blank answer sheet).
  Per Prat's instruction, every `**Answer:**` is `_(no key)_` — questions only.
- **Extraction method:** PyMuPDF (`fitz`) extracts the Thai text layer cleanly for the 6 text
  PDFs (60, 61, 62, 66, 67, 68). The 2 scanned PDFs (64, 65) have no text layer — rendered to
  PNG with PyMuPDF and transcribed by reading the page images (scans were clean/legible).
  `pdftotext` drops Thai glyphs; the Read-tool PDF path needs `pdftoppm`, which is missing here.
- **Chapter coverage:** ch09 (อัตราการเกิดปฏิกิริยา), ch10 (สมดุล), ch11 (กรดเบส), ch13 (อินทรีย์),
  ch14 (พอลิเมอร์) have **0 questions** — POSN รอบ 1 only covers ม.4 content. ch12 has 2
  (redox-balancing items; reclassify if Prat prefers).
- Figures (diagrams, Lewis structures, GHS pictograms, manometers, etc.) are **not reproduced**;
  affected questions carry a `**Note:**` and appear under "Needs review".
- Year is recorded as the Buddhist year on the paper (e.g. `#year/2568`).

## Counts
- Files done: **8 of 8 extracted** (0 reviewed — awaiting Prat spot-check)
- Questions in bank: **595**
- By chapter: ch01:20, ch02:73, ch03:72, ch04:135, ch05:51, ch06:72, ch07:125, ch08:45, ch12:2
- Items in "Needs review": **36** (figure-dependent or scanned-source caveats)
