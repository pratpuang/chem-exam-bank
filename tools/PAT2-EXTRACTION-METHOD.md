# PAT2 extraction method — the repeatable playbook

**Purpose:** how to ingest the remaining PAT2 papers into this bank without re-deriving the process
each session. Any session (Matcha or plain) should read THIS file + `progress.md` and just go.
Last updated: 2026-07-06.

## The job
9 PAT2 papers (as of 2026-07-06; update the tracker below as they land) still need extracting into
`question-bank.md`. Each is a quota-heavy job → extract **chem + bio only** → crop figures inline →
write a fragment → (Prat) `build_bank.py` → `git push` (auto-deploys). PAT2 = combined-science, no
answer key.

## File → paper → Q-id block map (the source of truth)
Opaque source filenames were decoded in `tools/incoming/done/_INVENTORY.md`. PAT2 ran 3 sessions/year
(มี.ค./ก.ค./ต.ค.), so every question needs `#year/<BE>` **and** `#ver/<mar|jul|oct>` — year alone
doesn't identify a paper. Each paper gets a pre-assigned 100-wide Q-id block so parallel agents never
collide (gaps at the end of a block are harmless; renumber contiguously later only if Prat wants).

| Paper (year·session) | Source file | Format | Q-id block | Status |
|---|---|---|---|---|
| 2552 · มี.ค. | `2017112152132.pdf` | text | (in bank) | ✅ DONE |
| 2554 · ต.ค. | `2017112152431.pdf` | scan | (in bank) | ✅ DONE |
| 2553 · มี.ค. | `pat2 2553 .pdf` (spaces!) | text | Q-0923–0977 | ✅ DONE 2026-07-06 (55 Q, 14 figs) |
| 2552 · ก.ค. | `2017112152148.pdf` | scan | Q-1023–1094 | ✅ DONE 2026-07-06 (72 Q: 40 bio + 32 chem ข้อ 41–72; ~figs) |
| 2552 · ต.ค. | `2017112152158.pdf` | scan | Q-1123–1222 | ⏳ in progress 2026-07-06 |
| 2553 · ก.ค. | `2017112152247.pdf` | scan | Q-1223–1277 | ✅ DONE 2026-07-06 (55 Q: 30 chem + 25 bio, 12 figs) |
| 2553 · ต.ค. | `2017112152259.pdf` | scan | Q-1323–1422 | ⏳ in progress 2026-07-06 |
| 2554 · มี.ค. | `2017112152416.pdf` | scan | Q-1423–1522 | ⬜ queued |
| 2555 · มี.ค. | `2017112152455.pdf` | scan | Q-1523–1622 | ⬜ queued |
| 2555 · ต.ค. | `2017112152510.pdf` | scan | Q-1623–1722 | ⬜ queued |
| 2556 · มี.ค. | `2017112152559.pdf` | scan | Q-1723–1822 | ⬜ queued |

**Printed subject ranges** (extract these ข้อ, skip the rest): 2554·ต.ค. & 2555·มี.ค. → chem 1–30, bio 31–55.
2555·ต.ค. & 2556·มี.ค. → chem 1–25, bio 26–50. **Early papers (all 2552 + all 2553):** cover lists only
"เนื้อหา + ศักยภาพ", per-subject ranges NOT printed → locate the chem/bio blocks by reading content
(typical order bio → chem → physics → earth within the เนื้อหา block; verify each paper). Confirmed for
2553·มี.ค.: bio ข้อ 1–25, chem 26–55, skip 56–103.

## Orchestration: 2 papers at a time
Run **two `general-purpose` background agents in parallel**, one paper each, from the next two queued
rows. When one finishes, launch the next queued paper (keep 2 in flight). Each agent gets: this file's
path + the shared brief + its row's params (file, session, Q-id block, fragment name). Agents do NOT
run `build_bank.py` or `git` — Prat builds/pushes after eyeballing a batch. The full agent brief lives
at the bottom of this file (§Agent brief) — paste it + the paper's params when spawning.

## What each agent must do (the 4 non-negotiables)
1. **Scope:** chem (`#ch/NN`) + bio (`#subject/bio #bio/G.S`) ONLY. Skip physics/earth/aptitude.
   Every `**Answer:**` = `_(no key)_`.
2. **Figures cropped inline:** any figure/graph/structure/apparatus/GHS/image-choice question →
   crop the figure region from the source page to `images/Q-NNNN.png` (fitz clip-render) AND add a
   `**Figure:** images/Q-NNNN.png` line + a `**Note:**` describing it. NOT just a note — the PNG must
   exist. Convention: 84 existing figures are all `images/Q-NNNN.png` matched 1:1 to `**Figure:**` lines.
3. **Kill-proof:** write the fragment file after the first 2–3 questions, append per-question, save each
   figure PNG immediately. A quota-kill must lose ≤1 question. Fixed Q-id block → clean resume.
4. **Format:** copy `tools/incoming/done/pat2-2554-oct.md` exactly (header comment, block layout, tag
   order, Figure/Answer/Note/Source lines).

## Gold-standard example
`tools/incoming/done/pat2-2554-oct.md` — the reference output. Always read it first.

---

## §Agent brief (paste this to each spawned agent, then add the paper's params)

You extract ONE PAT2 paper into the Chem Exam Bank. High-fidelity Thai transcription. Do NOT run
`build_bank.py` or any `git` command — end at: fragment written + figures cropped + `progress.md` row.

**Read first:** `tools/incoming/done/pat2-2554-oct.md` (perfect model — copy its structure exactly).

**Scope:** เคมี + ชีววิทยา ONLY. Skip ฟิสิกส์/โลก-อวกาศ/ศักยภาพ. Questions-only, `**Answer:** _(no key)_`.

**Reading the PDF** — text PDF: `python -c "import fitz; d=fitz.open(r'source/FILE.pdf'); [print(f'==PAGE {i}==', p.get_text()) for i,p in enumerate(d)]"` (never pdftotext — mangles Thai). Scan: render pages to PNG ~200dpi via fitz `p.get_pixmap(dpi=200).save(...)`, Read the PNGs, transcribe.

**Figures (hard requirement)** — for every figure-dependent question: render the page, Read it to locate
the figure, convert pixel box → points (`point = pixel*72/dpi`), clip-render to PNG:
`python -c "import fitz; d=fitz.open(r'source/FILE.pdf'); d[PAGE].get_pixmap(dpi=220, clip=fitz.Rect(X0,Y0,X1,Y1)).save(r'images/Q-NNNN.png')"` (relative path; run from the project root; points; pad a little; verify by Reading it).
Add `**Figure:** images/Q-NNNN.png` (after choices, before `**Answer:**`) + a `**Note:**` describing it.

**Per-question format:**
```
### Q-NNNN · 4. พันธะเคมี · PAT2 <BE> · <diff>
**Tags:** #ch/04 #exam/pat2 #year/<BE> #ver/<session> #diff/<easy|medium|hard> #type/<mcq|calc|short|essay>
<text; subscripts A_xB_y, arrows ->>

- 1) ...
- 2) ...

**Figure:** images/Q-NNNN.png   ← only if figure
**Answer:** _(no key)_
**Note:** <figure desc>          ← only if figure/caveat
**Source:** PAT2 (รหัส 72) <BE> <session>, ข้อ <n>
```
Bio block: header `### Q-NNNN · ชีววิทยา <G.S> <group> · PAT2 <BE> · <diff>`, tags
`#subject/bio #bio/<G.S> #exam/pat2 #year/<BE> #ver/<session> #diff/.. #type/..`.

CHEM chapters: 1 ความปลอดภัยฯ · 2 แบบจำลองอะตอมฯ · 3 ตารางธาตุฯ · 4 พันธะเคมี · 5 โมลและสูตรเคมี · 6 สารละลาย ·
7 ปริมาณสารสัมพันธ์ · 8 แก๊สฯ · 9 อัตราการเกิดปฏิกิริยาฯ · 10 สมดุลเคมี · 11 กรดเบส · 12 เคมีไฟฟ้า · 13 เคมีอินทรีย์ · 14 พอลิเมอร์.
BIO groups: 1 ชีวเคมีและชีววิทยาของเซลล์ · 2 โครงสร้างและหน้าที่ของสัตว์ · 3 โครงสร้างและหน้าที่ของพืช ·
4 การแบ่งเซลล์และหลักพันธุศาสตร์ · 5 วิวัฒนาการ · 6 ความหลากหลายทางชีวภาพฯ · 7 พฤติกรรมสัตว์และหลักนิเวศวิทยา.
diff: easy=recall/1-step, medium=one-concept multi-step, hard=multi-concept. type: calc=numeric, mcq=conceptual, short/essay=อัตนัย.

**Kill-proof:** write fragment after 2–3 Q, append per-Q, save figure PNGs immediately. Stay inside your
assigned Q-id block. **On finish:** ensure fragment in `tools/incoming/` (not `done/`), append a
`progress.md` row (Status=extracted, Q-range, chem/bio counts, #figures). **Report:** Q-range used,
chem/bio counts, #figures, illegible/ambiguous items, and if cut off the last saved Q-id.
