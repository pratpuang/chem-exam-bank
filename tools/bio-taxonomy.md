---
title: Biology Tag Taxonomy (for PAT2 / mixed-science exams)
type: reference
tags: [bio, taxonomy, tagging, exam-bank]
created: 2026-07-04
summary: The biology chapter/sub-topic taxonomy Prat set, used to tag biology questions pulled from PAT2 (and any future mixed-science paper). Biology lives in its own bucket, separate from the 14 chemistry chapters.
---

# Biology tag taxonomy

Biology questions (from PAT2 ชีววิทยา sections, etc.) are tagged **separately** from the 14
chemistry chapters so the chem chapter counts stay clean. They go in their own **ชีววิทยา / Biology**
bucket in the bank + viewers.

## Tag scheme
- Every bio question carries **`#subject/bio`** (the bucket key the build script filters on).
- Plus a topic tag: **`#bio/<chapter>`** or, when the sub-topic is identifiable, **`#bio/<chapter>.<sub>`**.
  - e.g. a Mendelian-genetics question → `#subject/bio #bio/4.2`
  - a general cell-membrane question where the sub-topic is clear → `#subject/bio #bio/1.4`
  - if only the main topic is clear, use the top-level tag → `#subject/bio #bio/2`
- Same `#year/<BE>`, `#exam/<slug>`, `#diff/<...>`, `#type/<...>` as chemistry questions.
- Figure-dependent bio questions: same rule as chem — add a `**Note:**`, land in "Needs review", figure not reproduced.

## The taxonomy (7 chapters)

### 1. ชีวเคมีและชีววิทยาของเซลล์ (biochem & cell biology)
- 1.1 บทนำเกี่ยวกับชีววิทยา
- 1.2 เคมีในสิ่งมีชีวิต
- 1.3 โครงสร้างและการทำงานของเซลล์
- 1.4 เมมเบรนและการลำเลียงสารผ่านเข้าออกเซลล์
- 1.5 พลังงาน เอนไซม์ และเมทาบอลิซึม
- 1.6 การหายใจระดับเซลล์
- 1.7 การสังเคราะห์ด้วยแสง

### 2. โครงสร้างและหน้าที่ของสัตว์ (animal structure & function)
- 2.1 เนื้อเยื่อสัตว์และการรักษาสมดุลยภาพ
- 2.2 การรักษาความเข้มข้นในร่างกายและการขับถ่าย
- 2.3 การย่อยอาหารในสัตว์
- 2.4 การลำเลียงสารในสัตว์
- 2.5 ระบบภูมิคุ้มกัน
- 2.6 การแลกเปลี่ยนแก๊ส
- 2.7 ระบบประสาทและอวัยวะรับสัมผัส
- 2.8 ฮอร์โมนและระบบต่อมไร้ท่อ
- 2.9 การเคลื่อนไหวในสัตว์
- 2.10 การสืบพันธุ์และการเจริญในสัตว์

### 3. โครงสร้างและหน้าที่ของพืช (plant structure & function)
- 3.1 โครงสร้างและหน้าที่ของพืชดอก
- 3.2 การลำเลียงน้ำและอาหารในพืช
- 3.3 การสืบพันธุ์และการเจริญของพืชดอก
- 3.4 การตอบสนองและฮอร์โมนพืช

### 4. การแบ่งเซลล์และหลักพันธุศาสตร์ (cell division & genetics)
- 4.1 การแบ่งเซลล์แบบไมโทซิสและไมโอซิส
- 4.2 หลักการถ่ายทอดลักษณะทางพันธุกรรม
- 4.3 หลักพันธุศาสตร์โมเลกุล
- 4.4 พันธุวิศวกรรมและเทคโนโลยี DNA

### 5. วิวัฒนาการ (evolution)

### 6. ความหลากหลายทางชีวภาพและหลักอนุกรมวิธาน (biodiversity & taxonomy)

### 7. พฤติกรรมสัตว์และหลักนิเวศวิทยา (animal behavior & ecology)
- 7.1 พฤติกรรมสัตว์
- 7.2 หลักนิเวศวิทยา

## Applied-chem & biomolecules bucket (Prat chose "b", 2026-07-04)
Older exams (2551 curriculum) carry chemistry topics with no home in the fixed 14-chapter (2560)
scheme. Instead of best-fitting them into ch03/ch13, they get their OWN bucket — same mechanism as
biology, a separate filterable section, kept out of the 14 chem chapters so chapter counts stay clean.
- Bucket key tag: **`#subject/applied`** + a topic tag **`#app/<topic>`**. Same `#year #exam #diff #type`.
- Section title in bank/viewers: **เคมีประยุกต์และชีวโมเลกุล (Applied chem & biomolecules)**.
- Topic tags:
  - `#app/biomolecules` — ชีวโมเลกุล: ไขมัน/กรดไขมัน, โปรตีน/เพปไทด์, คาร์โบไฮเดรต, กรดนิวคลีอิก, เอนไซม์
  - `#app/petroleum` — ปิโตรเลียม / เชื้อเพลิงซากดึกดำบรรพ์ / การกลั่น
  - `#app/gemstones` — อัญมณี / แร่ / รัตนชาติ
  - `#app/fertilizer` — ปุ๋ย / สารเคมีการเกษตร
  - add new `#app/<topic>` slugs if a genuinely new misfit appears; keep them lowercase ascii.
- Figure rule + `_(no key)_` policy identical to everything else in this batch.
- **Only** route to this bucket when a question genuinely has no fit in the 14 chapters. Don't dump
  normal organic chemistry here — real ch13 organic stays `#ch/13`.

## Pipeline note
The existing `build_bank.py` sorts by chemistry `#ch/NN`. Biology questions have no `#ch/NN`, so the
build script needs a small tweak: route `#subject/bio` questions into a dedicated Biology section
(sorted by `#bio/` topic then Q-id) instead of the chem chapter sort. Until that tweak lands, do NOT
run bio fragments through the build — stage them and hold.
