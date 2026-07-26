# Answer key + solutions — LOCKED SPEC (scoped 2026-07-26)

> **STATUS: GREEN-LIT and IN PROGRESS (2026-07-26, ~20:00).**
> **ch07 ปริมาณสารสัมพันธ์ is DONE — all 146 questions solved → `solutions/ch07.md`.**
> Prat picked ch07 first (not ch10) and merged this with the น้องมิล problem-set job: the solutions
> ARE the source of her sheet, "so it's not a separate job."
>
> **Two amendments he made after the original spec was written:**
> 1. **Depth override (his words: "make the solution in details i want to read it all of it i change
>    my mind not 1 liner do one liner only if it suppppperrrr easy").** The tiered depth below is
>    superseded — **every question gets full step-by-step วิธีทำ**, including easy/medium MCQ.
>    One-liners only for genuinely trivial items.
> 2. **Language split.** The **เฉลย + วิธีทำ bodies are Thai**; every other line in the file —
>    headers, status, notes-to-self, review queues — is **English**.
>
> **Still outstanding on ch07:** the second independent solve on POSN hard+calc has NOT been run.
> 5 questions are flagged `⚠️` — the list is at the top of `solutions/ch07.md`.

## The frame (this governs everything)

Prat's words: *"i just need this ai solving thing to be the guide to lower my brain workload."*

This is **a draft he adjudicates, not a published answer key.** I solve, he rules. Every derived
answer is explicitly labelled derived and never presented as official. The workspace rule stands:
**never invent an answer key.**

## Why this is harder than it sounds

All **1,104** questions carry `**Answer:** _(no key)_` — verified, zero exceptions. POSN/PAT2/สามัญ
papers ship no key. So this is not "add the key", it's **produce 1,104 original solutions and vouch
for them**, and Prat teaches from the result. Confidently-wrong is his #1 red flag.

## Bank composition (measured 2026-07-26)

| Cut | Numbers |
|---|---|
| Total | 1,104 · all `_(no key)_` |
| Type | mcq 885 · calc 176 · short 43 |
| Difficulty | hard 488 · medium 584 · easy 34 |
| Exam | posn 596 · pat2 309 · samanya 200 · alevel 1 |
| Has `**Note:**` | 144 |
| Has `**Figure:**` | 127 (real PNGs in `images/` — readable, so these are IN scope) |
| Chapters | 01:21 02:99 03:102 04:165 05:61 06:86 07:147 08:67 09:27 10:25 11:40 12:35 13:47 14:10 |
| `question-bank.md` | 1,195 KB · 15,009 lines |

## ⚠️ THE TECHNICAL HAZARD — proved empirically, do not forget this

`build_bank.py` has a metadata whitelist:
`META = ("**Answer:**","**Source:**","**Note:**","**Also appears:**")`

Round-trip test (`parse()` → `render_block()`) on a synthetic block proved:

| Label | Survives a rebuild? |
|---|---|
| `**Answer:** / **Note:** / **Source:**` | ✅ |
| `**Figure:**` | ✅ **but only by accident** — it sits *before* `**Answer:**` so it gets swept into `body` |
| `**Solution:**` | ❌ **SILENTLY DELETED** |
| `**Verified:**` | ❌ **SILENTLY DELETED** |

So: **putting solutions in `question-bank.md` after `**Answer:**` destroys them on the next
`python tools/build_bank.py`** — no error, no warning. And exploiting the `**Figure:**` accident is
disqualified too: body content renders as part of the question, so **the student would see the
solution**, killing attempt-before-instruction.

→ **This is why solutions live in separate files. The bank is not touched.**

## Locked decisions

**Storage**
- `solutions/ch01.md` … `solutions/ch14.md`, keyed by Q-id.
- **`question-bank.md` untouched** — no parser change, no risk to the 182 questions merged today.
- Bank keeps `**Answer:** _(no key)_` **permanently**. It records what the paper shipped: nothing.

**Per-question record — two separate axes** (Prat wanted a binary for himself; the confidence
signal needed a home so the doubled verification spend stays visible)

| Field | Owner | Values |
|---|---|---|
| answer + solution | me | tiered depth (below) |
| `**Confidence:**` | me — Prat never touches it | `ok` / `⚠️ disagreed` |
| `**Checked:**` | Prat — the only field he edits | `no` / `yes` |

**Depth — tiered by difficulty**
- easy / medium MCQ → answer + one-line why
- hard + **all 176 calc** → full worked steps, in his order-of-thinking teaching voice

**Verification**
- **PAT2 + สามัญ (509 q):** public keys likely exist. Hunt the key, solve independently anyway,
  **flag every mismatch.** Prat's explicit instruction: *"if the publish key can be found compare
  and derive it we not gonna copy paste it at all."* **Never copy-paste a key.**
- **POSN (596 q):** no key exists anywhere. **Two independent cold solves on hard + calc**; single
  solve + confidence tag on easy/medium MCQ. Disagreement → `⚠️`, **never silently resolved.**
- Cost rationale for the tiering: error rate lives in hard/calc, not easy MCQ. Roughly half the
  cost of two-solving everything, catching most of the risk.

**Viewer**
- Solution **collapsed behind a click** (protects attempt-before-instruction in present mode).
- **Filter by `⚠️` and by `not checked`** so the review queue sorts worst-first. Without the filter
  the whole thing is unreviewable in practice.

**Order:** chapter by chapter, driven by what he's teaching next.

## Out of scope
- Rewriting `question-bank.md` or changing `build_bank.py`'s parser.
- Inventing an answer for anything unsolvable — those ship `⚠️` with the reason stated.

## Assumptions made without asking (correct these if wrong)
- Solutions written in **Thai**.
- Hard-question solutions in **his teaching voice** (step-by-step order of thinking, the *why*).
- The **127 figure questions are attempted** by opening the PNGs; any image too unclear to solve
  honestly gets `⚠️` rather than a guess.

## Dependencies / things Prat should know
1. **The viewer work is a separate build job** — merging `solutions/*.md` into `build_viewer.py`,
   the reveal toggle, the status filter. Hazel/Mocha task. **Arguably must happen FIRST**, or he
   ends up with solution files and no comfortable way to review them.
2. **`build_offline.py` is MISSING.** `CLAUDE.md` still documents it; the file does not exist (part
   of the uncommitted changes in the repo). Unrelated to this project but it will bite eventually.
3. **The repo is still dirty and unpushed** — the 182 new questions aren't live on the site yet.

## ▶️ RESUME HERE — recommended first move

**Pilot ch10 สมดุลเคมี — 25 questions.** Smallest chapter, he just built that deck, he's teaching
สมดุลเคมี now. Enough to prove the format, the tiering and the review workflow end-to-end before
committing to the other 1,079. If the shape is wrong he finds out after 25, not 400.

**Awaiting: his go, and which chapter he actually wants first.**
