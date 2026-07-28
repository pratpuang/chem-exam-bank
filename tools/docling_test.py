#!/usr/bin/env python
"""
docling_test.py <pdf> <start> <end>

Answers exactly two questions about a local-OCR pass over the PAT2 scans,
WITHOUT ever making anyone look at a page image (that's the expensive path):

  Q1 "Does chemistry notation survive EasyOCR?"  -> the notation probes.
  Q2 "Can it tell physics pages from chem pages?" -> the keyword classifier.

Writes full markdown per page to scratchpad/ocr/docling_pNN.md for reading
later; prints only counts, probes and short samples.

Docling does NOT OCR itself -- it delegates. The default registered engine is
rapidocr, whose models are CN+EN, so it is NOT the Thai engine. This script
forces EasyOCR with lang=["th","en"]. Do not "simplify" that away.
force_full_page_ocr=True is REQUIRED: these pages have no text layer at all,
so without it docling finds nothing to OCR around and returns empty.
"""
import sys
import re
import io
import time
from pathlib import Path

# Windows consoles default to cp874/cp1252 and die on Thai. Force UTF-8.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions

OUT = Path(__file__).parent / "ocr"
OUT.mkdir(exist_ok=True)

# ---- Q2: subject classifier -------------------------------------------------
# PAT2 = รหัสวิชา 72 ความถนัดทางวิทยาศาสตร์ = physics + chem + bio + earth in
# one paper. ~35-45% of each paper is physics/earth that Prat discards. A page
# only has to be classified well enough to BIN it -- mis-OCR on a discarded
# page costs nothing.
KEYWORDS = {
    "physics": ["คลื่น", "แรง", "ความเร็ว", "สนามแม่เหล็ก", "กระแส", "ประจุ", "เลนส์",
                "แสง", "พลังงานจลน์", "โมเมนตัม", "ความถี่", "เสียง", "วงจร",
                "ความต้านทาน", "ความดัน", "มวล", "ความเร่ง", "โวลต์", "แอมแปร์",
                "โอห์ม", "การเคลื่อนที่", "แม่เหล็ก", "หักเห", "สะท้อน"],
    "chemistry": ["โมล", "สารประกอบ", "ปฏิกิริยา", "กรด", "เบส", "อิเล็กตรอน", "ธาตุ",
                  "พันธะ", "สมการเคมี", "ความเข้มข้น", "ไอออน", "ออกซิเดชัน",
                  "สารละลาย", "โมเลกุล", "อะตอม", "วาเลนซ์", "ตารางธาตุ", "สมดุล",
                  "รีดักชัน", "ไฮโดรคาร์บอน", "พอลิเมอร์", "เลขออกซิเดชัน", "ตัวทำละลาย"],
    "biology": ["เซลล์", "เอนไซม์", "ดีเอ็นเอ", "โครโมโซม", "พืช", "สัตว์", "ฮอร์โมน",
                "การหายใจ", "สังเคราะห์แสง", "ยีน", "โปรตีน", "เนื้อเยื่อ", "ระบบประสาท",
                "วิวัฒนาการ", "แบคทีเรีย", "ไวรัส", "ราก", "ลำต้น", "ใบ"],
    "earth": ["ธรณี", "หิน", "แร่", "ดาว", "บรรยากาศ", "โลก", "ลม", "เมฆ", "ภูเขาไฟ",
              "แผ่นเปลือกโลก", "แผ่นดินไหว", "ดาวเคราะห์", "กาแล็กซี", "ตะกอน",
              "ชั้นหิน", "ฝน", "ภูมิอากาศ"],
}

# ---- Q1: notation probes ----------------------------------------------------
SUPERS = "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻"
SUBS = "₀₁₂₃₄₅₆₇₈₉₊₋"
# What a FLATTENED formula looks like -- if these show up but the unicode
# classes above don't, notation did not survive and we build the filter, not
# the extractor.
FLAT_FORMULA = re.compile(r"\b(?:[A-Z][a-z]?\d+){1,}[A-Z]?[a-z]?\d*\b")
FLAT_CHARGE = re.compile(r"[A-Z][a-z]?\d*\s?[0-9]?[+-]")
ARROWS = ["→", "⇌", "←", "->", "<->"]


def classify(text):
    scores = {}
    for subj, words in KEYWORDS.items():
        scores[subj] = sum(text.count(w) for w in words)
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "UNKNOWN", scores
    return best, scores


def probe(text):
    sup = [c for c in text if c in SUPERS]
    sub = [c for c in text if c in SUBS]
    return {
        "unicode_superscript": len(sup),
        "unicode_subscript": len(sub),
        "sup_chars": "".join(sorted(set(sup))),
        "sub_chars": "".join(sorted(set(sub))),
        "degree_sign": text.count("°"),
        "arrows": sum(text.count(a) for a in ARROWS),
        "flat_formulas": len(set(FLAT_FORMULA.findall(text))),
        "flat_formula_samples": sorted(set(FLAT_FORMULA.findall(text)))[:12],
        "flat_charges": len(set(FLAT_CHARGE.findall(text))),
    }


def junk_ratio(text):
    """Bleed-through / ghost-text sanity check. p31 of 2553 ต.ค. has visible
    reverse-side bleed, the classic OCR-hallucination trigger. A high ratio of
    1-char orphan tokens is the tell."""
    toks = text.split()
    if not toks:
        return 0.0, 0
    orphans = [t for t in toks if len(t) == 1 and not t.isdigit() and not t.isalpha()]
    return len(orphans) / len(toks), len(toks)


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    pdf, start, end = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

    opts = PdfPipelineOptions()
    opts.do_ocr = True
    opts.do_table_structure = True
    # THE critical two lines -- see module docstring.
    opts.ocr_options = EasyOcrOptions(lang=["th", "en"], force_full_page_ocr=True)

    conv = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )

    print(f"pdf     : {pdf}")
    print(f"pages   : {start}-{end}")
    print(f"engine  : easyocr lang=['th','en'] force_full_page_ocr=True")
    print("=" * 72)

    for p in range(start, end + 1):
        t0 = time.time()
        try:
            res = conv.convert(pdf, page_range=(p, p))
            md = res.document.export_to_markdown()
        except Exception as e:
            print(f"\n[p{p}] FAILED: {type(e).__name__}: {e}")
            continue
        dt = time.time() - t0

        (OUT / f"docling_p{p:02d}.md").write_text(md, encoding="utf-8")

        subj, scores = classify(md)
        pr = probe(md)
        jr, ntok = junk_ratio(md)

        print(f"\n[p{p}]  {dt:.1f}s  {len(md)} chars  {ntok} tokens")
        print(f"  CLASS -> {subj}   {scores}")
        print(f"  notation: sup={pr['unicode_superscript']}({pr['sup_chars']}) "
              f"sub={pr['unicode_subscript']}({pr['sub_chars']}) "
              f"deg={pr['degree_sign']} arrows={pr['arrows']}")
        print(f"  flattened: {pr['flat_formulas']} formula-shaped, "
              f"{pr['flat_charges']} charge-shaped")
        if pr["flat_formula_samples"]:
            print(f"    samples: {pr['flat_formula_samples']}")
        print(f"  junk/bleed ratio: {jr:.3f}")
        head = " ".join(md.split())[:300]
        print(f"  head: {head}")

    print("\n" + "=" * 72)
    print(f"markdown written to {OUT}")


if __name__ == "__main__":
    main()
