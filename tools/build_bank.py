# -*- coding: utf-8 -*-
"""Assemble question-bank.md (chapter-sorted) from itself + any new fragments
in tools/incoming/*.md. Then regenerate the viewer.

Usage:  python tools/build_bank.py
- Reads existing question-bank.md (canonical store).
- Reads every tools/incoming/*.md fragment (new question blocks, any order).
- Merges by Q-id (incoming wins), sorts by (chapter, Q-id), rewrites the bank.
- Moves processed fragments to tools/incoming/done/.
- Calls build_viewer.py to refresh the HTML viewer.
"""
import re, os, glob, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(ROOT, "question-bank.md")
INBOX = os.path.join(ROOT, "tools", "incoming")
DONE = os.path.join(INBOX, "done")

CHAPTERS = {
 "01":"ความปลอดภัยและทักษะปฏิบัติการ","02":"แบบจำลองอะตอมและการจัดเรียงอิเล็กตรอน",
 "03":"ตารางธาตุและสมบัติของธาตุตามตารางธาตุ","04":"พันธะเคมี","05":"โมลและสูตรเคมี",
 "06":"สารละลาย","07":"ปริมาณสารสัมพันธ์","08":"แก๊สและสมบัติของแก๊ส",
 "09":"อัตราการเกิดปฏิกิริยาเคมี","10":"สมดุลเคมี","11":"กรดเบส","12":"เคมีไฟฟ้า",
 "13":"เคมีอินทรีย์","14":"พอลิเมอร์",
}
# Biology lives in its own bucket (tagged #subject/bio #bio/N[.M]), NOT a chem chapter.
BIO_CHAPTERS = {
 "1":"ชีวเคมีและชีววิทยาของเซลล์","2":"โครงสร้างและหน้าที่ของสัตว์",
 "3":"โครงสร้างและหน้าที่ของพืช","4":"การแบ่งเซลล์และหลักพันธุศาสตร์",
 "5":"วิวัฒนาการ","6":"ความหลากหลายทางชีวภาพและหลักอนุกรมวิธาน",
 "7":"พฤติกรรมสัตว์และหลักนิเวศวิทยา",
}
def biokey(topic):
    """Sort key for a #bio/ topic like '4.2' or '2' -> (4,2) / (2,). Empty -> (99,)."""
    return tuple(int(p) for p in topic.split(".")) if topic else (99,)
# Applied-chem & biomolecules — 2551-curriculum topics with no home in the 14 chapters.
# Tagged #subject/applied #app/<topic>; own bucket like bio. Topic-agnostic: any new #app/
# slug groups under its raw name if it's not listed here (no script change needed).
APP_TOPICS = {
 "biomolecules":"ชีวโมเลกุล","petroleum":"ปิโตรเลียมและเชื้อเพลิง",
 "gemstones":"อัญมณีและแร่","fertilizer":"ปุ๋ยและสารเคมีการเกษตร",
 "industrial":"เคมีอุตสาหกรรม","ceramics":"เซรามิกส์และแก้ว",
}
META = ("**Answer:**","**Source:**","**Note:**","**Also appears:**")

def parse(md):
    out = []
    blocks = re.split(r"(?m)^### (Q-\d+)\b", md)
    for i in range(1, len(blocks), 2):
        qid = blocks[i].strip()
        lines = blocks[i+1].splitlines()
        tagline = ""; body = []; meta = {}; j = 1
        for k in range(1, len(lines)):
            if lines[k].strip().startswith("**Tags:**"):
                tagline = lines[k].strip(); j = k+1; break
        in_meta = False
        for ln in lines[j:]:
            s = ln.strip()
            lab = next((m for m in META if s.startswith(m)), None)
            if lab:
                in_meta = True
                meta[lab.strip("*: ")] = s[len(lab):].strip()
            elif not in_meta:
                body.append(ln)
            # once in the metadata section, ignore trailing structural lines
            # (chapter headings, ---, "No questions yet") that follow a question
        def tag(n):
            m = re.search(r"#%s/([^\s#]+)" % n, tagline); return m.group(1) if m else ""
        out.append({
            "id": qid, "ch": tag("ch"), "exam": tag("exam") or "posn",
            "subject": tag("subject"), "bio": tag("bio"), "app": tag("app"),
            "year": tag("year"), "ver": tag("ver"), "diff": tag("diff"),
            "type": tag("type"), "body": "\n".join(body).strip(),
            "answer": meta.get("Answer","_(no key)_"),
            "note": meta.get("Note","").strip(),
            "source": meta.get("Source","").strip(),
            "also": meta.get("Also appears","").strip(),
        })
    return out

def render_block(q):
    if q["subject"] == "bio":
        topic = q["bio"]; bName = BIO_CHAPTERS.get(topic.split(".")[0], "")
        head = f"### {q['id']} · ชีววิทยา {topic} {bName} · {q['exam'].upper()} {q['year']} · {q['diff']}"
        tags = f"**Tags:** #subject/bio #bio/{topic} #exam/{q['exam']} #year/{q['year']}"
    elif q["subject"] == "applied":
        topic = q["app"]; aName = APP_TOPICS.get(topic, topic)
        head = f"### {q['id']} · เคมีประยุกต์ · {aName} · {q['exam'].upper()} {q['year']} · {q['diff']}"
        tags = f"**Tags:** #subject/applied #app/{topic} #exam/{q['exam']} #year/{q['year']}"
    else:
        ch = q["ch"]; chName = CHAPTERS.get(ch,"")
        head = f"### {q['id']} · {int(ch)}. {chName} · {q['exam'].upper()} {q['year']} · {q['diff']}"
        tags = f"**Tags:** #ch/{ch} #exam/{q['exam']} #year/{q['year']}"
    if q["ver"]: tags += f" #ver/{q['ver']}"
    tags += f" #diff/{q['diff']} #type/{q['type']}"
    parts = [head, tags, q["body"], "", f"**Answer:** {q['answer']}"]
    if q["also"]: parts.append(f"**Also appears:** {q['also']}")
    if q["note"]: parts.append(f"**Note:** {q['note']}")
    parts.append(f"**Source:** {q['source']}")
    return "\n".join(parts)

HEADER = """# Chemistry Question Bank

Single sorted bank of past-exam questions. Sorted by chapter; each question tagged by
year, version, and difficulty.

## How to search this file
- **By chapter** → click a chapter in the index below, or Ctrl+F `#ch/07` (number) or the Thai name
- **By exam** → Ctrl+F `#exam/posn` or `#exam/alevel`
- **By year** → Ctrl+F `#year/2568`
- **By difficulty** → Ctrl+F `#diff/hard`
- **Combine** → jump to a chapter, then Ctrl+F a tag within it (e.g. `#diff/hard`)

Tag format: `#ch/<NN>` `#exam/<slug>` `#year/<YYYY>` `#ver/<midterm|final|quiz>` `#diff/<easy|medium|hard>` `#type/<mcq|short|calc|essay>`

> **Year convention:** POSN years are recorded in the Buddhist year (B.E.) shown on the
> paper and in the filename, e.g. `#year/2568` = สอวน. รอบ 1 ปี 2568.

## Chapter index
"""

def build_md(qs):
    qs.sort(key=lambda q: (int(q["ch"] or 99), q["id"]))
    out = [HEADER]
    for n in sorted(CHAPTERS):
        out.append(f"{int(n)}. [{CHAPTERS[n]}](#{int(n)}-{CHAPTERS[n].replace(' ','-')})")
    if any(q["subject"] == "bio" for q in qs):
        out.append("- [ชีววิทยา (Biology)](#ชีววิทยา-biology)")
    if any(q["subject"] == "applied" for q in qs):
        out.append("- [เคมีประยุกต์และชีวโมเลกุล (Applied)](#เคมีประยุกต์และชีวโมเลกุล-applied)")
    out.append("\n---\n")
    for n in sorted(CHAPTERS):
        out.append(f"## {int(n)}. {CHAPTERS[n]}\n")
        chq = [q for q in qs if q["ch"] == n]
        if not chq:
            out.append("_No questions yet._\n")
        else:
            for q in chq:
                out.append(render_block(q) + "\n")
    # Biology bucket — only emitted when bio questions exist (keeps chem-only output unchanged).
    bioq = sorted((q for q in qs if q["subject"] == "bio"),
                  key=lambda q: (biokey(q["bio"]), q["id"]))
    if bioq:
        out.append("## ชีววิทยา (Biology)\n")
        last_top = None
        for q in bioq:
            top = q["bio"].split(".")[0] if q["bio"] else "?"
            if top != last_top:
                last_top = top
                out.append(f"**หมวด {top}. {BIO_CHAPTERS.get(top,'')}**\n")
            out.append(render_block(q) + "\n")
    # Applied-chem & biomolecules bucket — grouped by #app/ topic, only when applied questions exist.
    appq = sorted((q for q in qs if q["subject"] == "applied"),
                  key=lambda q: (q["app"], q["id"]))
    if appq:
        out.append("## เคมีประยุกต์และชีวโมเลกุล (Applied)\n")
        last_top = None
        for q in appq:
            top = q["app"] or "?"
            if top != last_top:
                last_top = top
                out.append(f"**หมวด {APP_TOPICS.get(top, top)}**\n")
            out.append(render_block(q) + "\n")
    out.append("---\n")
    out.append("## Needs review")
    out.append("_Questions that couldn't be cleanly read/transcribed (mostly from scans), "
               "or that depend on a figure not reproduced here. Spot-check against the source PDF._\n")
    flagged = [q for q in qs if q["note"]]
    if flagged:
        for q in flagged:
            out.append(f"- **{q['id']}** ({q['exam'].upper()} {q['year']}) — {q['note']}")
    else:
        out.append("_None._")
    return "\n".join(out) + "\n"

def main():
    qs = parse(open(BANK, encoding="utf-8").read()) if os.path.exists(BANK) else []
    by_id = {q["id"]: q for q in qs}
    frags = sorted(glob.glob(os.path.join(INBOX, "*.md")))
    added = 0
    for f in frags:
        for q in parse(open(f, encoding="utf-8").read()):
            if q["id"] not in by_id: added += 1
            by_id[q["id"]] = q
    qs = list(by_id.values())
    open(BANK, "w", encoding="utf-8").write(build_md(qs))
    for f in frags:
        shutil.move(f, os.path.join(DONE, os.path.basename(f)))
    print(f"bank: {len(qs)} questions ({added} new) from {len(frags)} fragment(s)")
    # refresh viewer
    bv = os.path.join(ROOT, "tools", "build_viewer.py")
    if os.path.exists(bv):
        subprocess.run([sys.executable, bv], check=False)

if __name__ == "__main__":
    main()
