---
title: Chem Exam Bank — Project Rules
type: reference
tags: [chem, exams, pipeline, rules]
created: 2026-07-01
summary: Instructions for maintaining and building the chemistry exam question bank; extraction workflow, chapter taxonomy, and gotchas.
---

# Chemistry Exam Question Bank — Project Rules

This folder turns a pile of past chemistry exams into ONE searchable, chapter-sorted
question bank. These rules keep every session consistent. Follow them exactly.

## What we're building
- Input: original exam files (one per year/version, each mixing many chapters) in `source/`.
- Output: `question-bank.md` — a single file, sorted **by chapter**, every question
  tagged by **chapter / year / version / difficulty**.
- Tracking: `progress.md` — status of every source file.

## Workflow per source file
1. Read the file from `source/`.
   - Typed text / .txt / .md / text-PDF / .docx → read directly.
   - Scanned or image PDFs → read pages as images and transcribe. Flag these
     `needs-review` because chem symbols (subscripts, charges, →, structures) mis-OCR.
2. Extract each question, classify its chapter, judge its difficulty.
3. Append it to `question-bank.md` under the right chapter section.
4. Update `progress.md`: `pending → extracted → reviewed`.

## Chapter taxonomy (FIXED — 14 chapters, Thai names, use the number for the tag)
1. ความปลอดภัยและทักษะปฏิบัติการ
2. แบบจำลองอะตอมและการจัดเรียงอิเล็กตรอน
3. ตารางธาตุและสมบัติของธาตุตามตารางธาตุ
4. พันธะเคมี
5. โมลและสูตรเคมี
6. สารละลาย
7. ปริมาณสารสัมพันธ์
8. แก๊สและสมบัติของแก๊ส
9. อัตราการเกิดปฏิกิริยาเคมี
10. สมดุลเคมี
11. กรดเบส
12. เคมีไฟฟ้า
13. เคมีอินทรีย์
14. พอลิเมอร์

## Difficulty rubric (Claude's estimate — Prat spot-checks)
- **easy** — recall / definition / single-step lookup or one plug-in.
- **medium** — one concept, multi-step calculation or small inference.
- **hard** — multiple concepts combined, multi-step reasoning, or unusual framing.

## Tag vocabulary (exact format — searchability depends on consistency)
`#ch/<NN>` `#exam/<slug>` `#year/<YYYY>` `#ver/<midterm|final|quiz|...>` `#diff/<easy|medium|hard>` `#type/<mcq|short|calc|essay>`
- `#ch/NN` = two-digit chapter number 01–14 from the taxonomy above (e.g. ปริมาณสารสัมพันธ์ → `#ch/07`).
- `#exam/` = which exam it's from: `posn` (สอวน.), `alevel`, etc. Add new slugs as needed; keep them lowercase ascii.

## Per-question template (copy exactly)
```markdown
### Q-0001 · 7. ปริมาณสารสัมพันธ์ · A-level 2022 · hard
**Tags:** #ch/07 #exam/alevel #year/2022 #diff/hard #type/mcq
Question text. Equations as plain text or LaTeX, e.g. 2H_2 + O_2 -> 2H_2O.

- A) ...
- B) ...

**Answer:** B
**Source:** A-level 2022, Q14
```
- **Answer handling (per file):** if the source includes an answer key, fill in `**Answer:**`.
  If it doesn't, leave it as `**Answer:** _(no key)_` — do NOT guess unless Prat asks. A
  Claude-guessed answer must be marked `**Answer:** B _(my guess — unverified)_`.
- Q-IDs are global and sequential (Q-0001, Q-0002, ...), never reused.
- Duplicate question across years → keep ONE entry, add `**Also appears:** 2021 Final Q8`.
- Unreadable / uncertain → put under `## Needs review` at the bottom of question-bank.md.

## Open items to confirm with Prat before a big run
- Chapter list: CONFIRMED (14 chapters above).
- Exam-type tag (`#exam/`): CONFIRMED. Examples so far: posn (สอวน.), alevel.
- Language: assume Thai unless a file is clearly English.
- Answer keys: CONFIRMED — per file. Use the key if present; otherwise mark `_(no key)_`, don't guess.
