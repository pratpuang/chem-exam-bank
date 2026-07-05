# คลังข้อสอบเคมี · Chemistry Question Bank

A single, chapter-sorted bank of Thai chemistry past-exam questions (สอวน. / POSN,
9 วิชาสามัญ, PAT2) — **922 questions**, tagged by chapter, exam, year, and difficulty,
with figures preserved. No answer keys (these papers ship none).

## View it
- **`index.html`** — landing page.
- **`question-bank-viewer.html`** — interactive: search, filter by chapter/exam/year/difficulty,
  present mode, random pick.
- **`question-bank-offline.html`** — static, JS-free, figures embedded (opens in iPad Files / OneDrive preview).
- **`question-bank.md`** — the canonical source of every question.

## Structure
- `question-bank.md` — canonical store. Each question is a `### Q-NNNN` block tagged
  `#ch/NN #exam/<slug> #year/<BE> #diff/<...> #type/<...>`; biology and applied-chem
  questions live in their own buckets.
- `images/` — figures cropped from the source papers, referenced by Q-id.
- `tools/` — Python build scripts that assemble the bank and regenerate the viewers.

Original exam scans are not published here. Years are Buddhist era (B.E.) as printed.
