#!/usr/bin/env python
"""
triage_pages.py <ocr_dir>            # evaluate against labelled pages
triage_pages.py <ocr_dir> --manifest # emit keep/bin manifest

PAT2 (รหัสวิชา 72 ความถนัดทางวิทยาศาสตร์) mixes physics + chemistry + biology +
earth science in one paper. Prat keeps chem + bio and discards physics + earth,
which is ~35-45% of every paper. The expensive step is a vision agent reading
page images (~1,500 tok/page). This filter's ONLY job is to drop obvious
physics/earth pages BEFORE that agent runs, so it never pays for them.

## The design rule that matters: THIS FILTER IS KEEP-BIASED ON PURPOSE.

The two errors are wildly asymmetric:
  - wrongly KEEPING a physics page  -> costs ~1,500 tokens. Annoying.
  - wrongly BINNING a chem/bio page -> those questions are lost from the bank
    silently, and nobody ever finds out. Unacceptable.

So a page is binned ONLY on positive, clear evidence that it is physics/earth
AND no meaningful chem/bio evidence. Ties, blanks, and anything ambiguous are
KEPT. "UNKNOWN" always means KEEP. Do not "improve" this into a plain argmax
classifier -- that is what failed the first evaluation (it sent a nitric-acid
page to physics on a 2-2 tie).

## Why the matching is this defensive

EasyOCR on these scans is BAD (measured 2026-07-28): it captures roughly a
third of the page, drops whole answer options, lowercases chemistry
(`SO2` -> `so,`), and reads the same token two ways on one page (`pH` -> `ph`
AND `pii`). So: match case-insensitively, never rely on capitalisation, and
lean on Thai prose keywords, which survive better than any formula does.
"""
import sys
import re
from pathlib import Path

# Ground truth for the 9 pages OCR'd from 2017112152259.pdf (2553 ต.ค.),
# labelled by reading the OCR text. Used only by the evaluation mode.
LABELS = {
    8: "chemistry",   # นitric acid conc/density, gas constant, SO2 cylinder
    14: "chemistry",  # chitosan polymer solubility, amino acids, pH
    20: "biology",    # pedigree, genotype, inherited disease probability
    26: "physics",    # velocity-time graph, displacement, deceleration
    30: "physics",    # resonance in an open pipe, sound waves, newtons
    31: "physics",    # why sound shows no polarization, kelvin
    32: "physics",    # capacitor, potential difference, switch
    38: "chemistry",  # lab safety: acid spill, alcohol lamp fire
    42: "biology",    # shell-length sampling by water depth (ecology/stats)
}
KEEP_SUBJECTS = {"chemistry", "biology"}

# Thai prose terms. Weighted: some words are decisive, some merely suggestive.
# `มวล`/`ความดัน`/`พลังงาน` are DELIBERATELY absent from physics -- they appear
# constantly in chemistry (molar mass, gas pressure) and caused the p8 misfire.
PHYSICS = {
    "คลื่น": 3, "สั่นพ้อง": 3, "โพลาไรเซชั่น": 3, "ตัวเก็บประจุ": 3, "สนามแม่เหล็ก": 3,
    "ความต่างศักย์": 3, "โมเมนตัม": 3, "ความหน่วง": 3, "การกระจัด": 3, "เลนส์": 3,
    "ความต้านทาน": 3, "แรงเสียดทาน": 3, "หักเห": 2, "แอมแปร์": 2, "โวลต์": 2,
    "โอห์ม": 2, "ความเร่ง": 2, "วงจรไฟฟ้า": 2, "สวิตช์": 2, "เสียง": 2,
    "ความเร็ว": 1, "แรง": 1, "นิวตัน": 1, "การเคลื่อนที่": 1, "ความถี่": 1,
}
EARTH = {
    "ธรณี": 3, "แผ่นเปลือกโลก": 3, "ภูเขาไฟ": 3, "แผ่นดินไหว": 3, "ชั้นหิน": 3,
    "ดาวเคราะห์": 3, "กาแล็กซี": 3, "ตะกอน": 2, "บรรยากาศ": 2, "เมฆ": 2,
    "ภูมิอากาศ": 2, "แร่": 1, "หิน": 1,
}
CHEMISTRY = {
    "โมล": 3, "พอลิเมอร์": 3, "กรดอะมิโน": 3, "ตัวทำละลาย": 3, "ความเข้มข้น": 3,
    "สารละลาย": 3, "ออกซิเดชัน": 3, "รีดักชัน": 3, "ไฮโดรคาร์บอน": 3, "ตารางธาตุ": 3,
    "พันธะ": 3, "ไอออน": 3, "อะตอม": 3, "โมเลกุล": 3, "ค่าคงที่ของแก๊ส": 3,
    "กรด": 2, "เบส": 2, "ธาตุ": 2, "สารประกอบ": 2, "ปฏิกิริยา": 2, "อิเล็กตรอน": 2,
    "แก๊ส": 1, "ละลาย": 1, "ผลึก": 1,
}
BIOLOGY = {
    # The first evaluation missed BOTH biology pages because these were absent.
    "พันธุกรรม": 3, "พงศาวลี": 3, "โครโมโซม": 3, "เอนไซม์": 3, "ดีเอ็นเอ": 3,
    "สังเคราะห์แสง": 3, "ระบบประสาท": 3, "ฮอร์โมน": 3, "เนื้อเยื่อ": 3, "เซลล์": 3,
    "วิวัฒนาการ": 3, "แบคทีเรีย": 3, "สิ่งมีชีวิต": 3, "ยีน": 2, "โปรตีน": 2,
    "การหายใจ": 2, "พืช": 2, "สัตว์": 2, "เปลือกหอย": 2, "แหล่งน้ำ": 1, "ตัวอย่าง": 1,
}
# Latin/ASCII tokens that survive OCR reasonably and are strong signals.
ASCII_SIGNALS = {
    "genotype": ("biology", 3), "pedigree": ("biology", 3),
    "generation": ("biology", 2), "dna": ("biology", 3),
    "ph": ("chemistry", 2), "mol": ("chemistry", 2),
}


def score(text):
    low = text.lower()
    s = {"physics": 0, "earth": 0, "chemistry": 0, "biology": 0}
    hits = {k: [] for k in s}
    for subj, table in (("physics", PHYSICS), ("earth", EARTH),
                        ("chemistry", CHEMISTRY), ("biology", BIOLOGY)):
        for word, w in table.items():
            n = text.count(word)
            if n:
                s[subj] += n * w
                hits[subj].append(word)
    for tok, (subj, w) in ASCII_SIGNALS.items():
        n = len(re.findall(r"\b" + tok + r"\b", low))
        if n:
            s[subj] += n * w
            hits[subj].append(tok)
    return s, hits


# Bin only on a clear, positive physics/earth signal with negligible keep signal.
DISCARD_MIN = 4      # absolute evidence required before binning anything
DISCARD_RATIO = 2.5  # ...and it must dominate chem+bio by this much


def decide(text):
    s, hits = score(text)
    keep_sig = s["chemistry"] + s["biology"]
    bin_sig = s["physics"] + s["earth"]
    if bin_sig >= DISCARD_MIN and keep_sig == 0:
        return "BIN", s, hits, "clear physics/earth, zero chem/bio"
    if bin_sig >= DISCARD_MIN and bin_sig >= keep_sig * DISCARD_RATIO:
        return "BIN", s, hits, f"physics/earth dominates {bin_sig}v{keep_sig}"
    if keep_sig == 0 and bin_sig == 0:
        return "KEEP", s, hits, "no signal at all -> keep (never bin a blank)"
    return "KEEP", s, hits, f"keep-biased: {keep_sig} keep vs {bin_sig} bin"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    ocr_dir = Path(sys.argv[1])
    manifest_mode = "--manifest" in sys.argv

    files = sorted(ocr_dir.glob("docling_p*.md"))
    if not files:
        print(f"no docling_p*.md in {ocr_dir}")
        sys.exit(1)

    right = wrong_bin = wrong_keep = 0
    print(f"{'page':<6}{'decision':<7}{'truth':<11}{'ok':<4}scores")
    print("-" * 78)
    for f in files:
        pno = int(re.search(r"p(\d+)", f.name).group(1))
        text = f.read_text(encoding="utf-8")
        dec, s, hits, why = decide(text)
        truth = LABELS.get(pno)
        mark = ""
        if truth and not manifest_mode:
            should = "KEEP" if truth in KEEP_SUBJECTS else "BIN"
            if dec == should:
                mark = "ok"
                right += 1
            elif dec == "BIN":
                mark = "LOST!"   # the unacceptable error
                wrong_bin += 1
            else:
                mark = "cost"    # merely wasteful
                wrong_keep += 1
        print(f"{pno:<6}{dec:<7}{str(truth):<11}{mark:<4}"
              f"P{s['physics']} E{s['earth']} C{s['chemistry']} B{s['biology']}  ({why})")

    if not manifest_mode:
        total = right + wrong_bin + wrong_keep
        print("-" * 78)
        print(f"correct              : {right}/{total}")
        print(f"wrongly BINNED (bad) : {wrong_bin}   <- must be 0")
        print(f"wrongly kept (cheap) : {wrong_keep}")
        kept = sum(1 for f in files if decide(f.read_text(encoding='utf-8'))[0] == "KEEP")
        print(f"pages kept           : {kept}/{len(files)} "
              f"({100*kept//len(files)}%) -> vision agent skips "
              f"{len(files)-kept} of {len(files)}")


if __name__ == "__main__":
    main()
