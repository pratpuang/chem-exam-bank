# -*- coding: utf-8 -*-
"""Build a STATIC, no-JavaScript HTML (question-bank-offline.html) that renders
in iPad Files / OneDrive preview (which don't run JS). Chapters are collapsible
via native <details>; each question is a styled card. Run after build_bank.py."""
import re, os, html, markdown, base64

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(ROOT, "question-bank.md")
OUT  = os.path.join(ROOT, "question-bank-offline.html")

CHAPTERS = {
 "01":"ความปลอดภัยและทักษะปฏิบัติการ","02":"แบบจำลองอะตอมและการจัดเรียงอิเล็กตรอน",
 "03":"ตารางธาตุและสมบัติของธาตุตามตารางธาตุ","04":"พันธะเคมี","05":"โมลและสูตรเคมี",
 "06":"สารละลาย","07":"ปริมาณสารสัมพันธ์","08":"แก๊สและสมบัติของแก๊ส",
 "09":"อัตราการเกิดปฏิกิริยาเคมี","10":"สมดุลเคมี","11":"กรดเบส","12":"เคมีไฟฟ้า",
 "13":"เคมีอินทรีย์","14":"พอลิเมอร์",
}
BIO_CHAPTERS = {
 "1":"ชีวเคมีและชีววิทยาของเซลล์","2":"โครงสร้างและหน้าที่ของสัตว์",
 "3":"โครงสร้างและหน้าที่ของพืช","4":"การแบ่งเซลล์และหลักพันธุศาสตร์",
 "5":"วิวัฒนาการ","6":"ความหลากหลายทางชีวภาพและหลักอนุกรมวิธาน",
 "7":"พฤติกรรมสัตว์และหลักนิเวศวิทยา",
}
def biokey(topic):
    return tuple(int(p) for p in topic.split(".")) if topic else (99,)
APP_TOPICS = {
 "biomolecules":"ชีวโมเลกุล","petroleum":"ปิโตรเลียมและเชื้อเพลิง",
 "gemstones":"อัญมณีและแร่","fertilizer":"ปุ๋ยและสารเคมีการเกษตร",
 "industrial":"เคมีอุตสาหกรรม","ceramics":"เซรามิกส์และแก้ว",
}
EXAMS = {"posn":("สอวน.","#4338ca"),"alevel":("A-Level","#0d9488"),
 "samanya":("9 วิชาสามัญ","#7c3aed"),"pat2":("PAT2","#db2777"),
 "onet":("O-NET","#16a34a"),"school":("โรงเรียน","#d97706"),"unknown":("ยังไม่ระบุ","#64748b")}
DIFF_TH={"easy":"ง่าย","medium":"ปานกลาง","hard":"ยาก"}
META=("**Answer:**","**Source:**","**Note:**","**Also appears:**","**Figure:**")

_datauri_cache={}
def datauri(relpath):
    """Embed images/Q-NNNN.png as a base64 data URI so the offline file
    renders with no external files (iPad Files / OneDrive preview)."""
    if not relpath: return ""
    if relpath in _datauri_cache: return _datauri_cache[relpath]
    p=os.path.join(ROOT, relpath)
    if not os.path.exists(p):
        print("  WARN missing figure:", relpath); _datauri_cache[relpath]=""; return ""
    b=base64.b64encode(open(p,"rb").read()).decode()
    uri=f"data:image/png;base64,{b}"; _datauri_cache[relpath]=uri; return uri

def parse(md):
    out=[]; blocks=re.split(r"(?m)^### (Q-\d+)\b", md)
    for i in range(1,len(blocks),2):
        qid=blocks[i].strip(); lines=blocks[i+1].splitlines()
        tag=""; body=[]; meta={}; j=1
        for k in range(1,len(lines)):
            if lines[k].strip().startswith("**Tags:**"): tag=lines[k].strip(); j=k+1; break
        in_meta=False
        for ln in lines[j:]:
            s=ln.strip(); lab=next((m for m in META if s.startswith(m)),None)
            if lab: in_meta=True; meta[lab.strip("*: ")]=s[len(lab):].strip()
            elif not in_meta: body.append(ln)
        def t(n):
            m=re.search(r"#%s/([^\s#]+)"%n,tag); return m.group(1) if m else ""
        out.append({"id":qid,"ch":t("ch"),"exam":t("exam") or "unknown","year":t("year"),
            "subject":t("subject"),"bio":t("bio"),"app":t("app"),
            "diff":t("diff"),"type":t("type"),"body":"\n".join(body).strip(),
            "answer":meta.get("Answer","_(no key)_"),"note":meta.get("Note","").strip(),
            "source":meta.get("Source","").strip(),"figure":meta.get("Figure","").strip()})
    return out

qs=parse(open(BANK,encoding="utf-8").read())
qs.sort(key=lambda q:(int(q["ch"] or 99), q["id"]))
total=len(qs)

def badges(q):
    e=EXAMS.get(q["exam"],(q["exam"].upper(),"#64748b"))
    if q["subject"]=="bio": topic=f'<span class="b ch">ชีวะ {q["bio"]}</span>'
    elif q["subject"]=="applied": topic=f'<span class="b ch">ประยุกต์</span>'
    else: topic=f'<span class="b ch">บท {int(q["ch"])}</span>'
    return (topic +
            f'<span class="b ex" style="background:{e[1]}">{e[0]} {q["year"]}</span>'
            f'<span class="b d-{q["diff"]}">{DIFF_TH.get(q["diff"],q["diff"])}</span>'
            f'<span class="b ty">{q["type"]}</span>')

def card(q):
    body=markdown.markdown(q["body"],extensions=["tables"])
    note=f'<div class="note">📌 {html.escape(q["note"])}</div>' if q["note"] else ""
    uri=datauri(q["figure"])
    fig=f'<img class="fig" src="{uri}" alt="{q["id"]}">' if uri else ""
    return (f'<div class="card lv-{q["diff"]}"><div class="top">'
            f'<span class="qid">{q["id"]}</span>{badges(q)}</div>'
            f'<div class="body">{body}{fig}</div>{note}'
            f'<div class="src">📄 {html.escape(q["source"])} · เฉลย: {html.escape(q["answer"])}</div></div>')

secs=[]; idx=[]
for n in sorted(CHAPTERS):
    chq=[q for q in qs if q["ch"]==n]
    if not chq: continue
    idx.append(f'<li><a href="#ch{n}">{int(n)}. {CHAPTERS[n]}</a> <b>({len(chq)})</b></li>')
    cards="".join(card(q) for q in chq)
    secs.append(f'<details open id="ch{n}"><summary>บทที่ {int(n)} · {CHAPTERS[n]} '
                f'<span class="cnt">{len(chq)} ข้อ</span></summary>{cards}</details>')

# Biology bucket (one collapsible per top-level bio chapter), sorted by #bio/ topic then id
from itertools import groupby
bioqs=sorted((q for q in qs if q["subject"]=="bio"),key=lambda q:(biokey(q["bio"]),q["id"]))
if bioqs:
    idx.append('<li style="margin-top:6px;font-weight:700">🧬 ชีววิทยา</li>')
    for top,grp in groupby(bioqs,key=lambda q:q["bio"].split(".")[0] if q["bio"] else "?"):
        grp=list(grp); nm=BIO_CHAPTERS.get(top,"")
        idx.append(f'<li><a href="#bio{top}">{top}. {nm}</a> <b>({len(grp)})</b></li>')
        cards="".join(card(q) for q in grp)
        secs.append(f'<details open id="bio{top}"><summary>ชีววิทยา {top} · {nm} '
                    f'<span class="cnt">{len(grp)} ข้อ</span></summary>{cards}</details>')

# Applied-chem & biomolecules bucket (one collapsible per #app/ topic), sorted by topic then id
appqs=sorted((q for q in qs if q["subject"]=="applied"),key=lambda q:(q["app"],q["id"]))
if appqs:
    idx.append('<li style="margin-top:6px;font-weight:700">⚗️ เคมีประยุกต์และชีวโมเลกุล</li>')
    for top,grp in groupby(appqs,key=lambda q:q["app"] or "?"):
        grp=list(grp); nm=APP_TOPICS.get(top,top)
        idx.append(f'<li><a href="#app-{top}">{nm}</a> <b>({len(grp)})</b></li>')
        cards="".join(card(q) for q in grp)
        secs.append(f'<details open id="app-{top}"><summary>เคมีประยุกต์ · {nm} '
                    f'<span class="cnt">{len(grp)} ข้อ</span></summary>{cards}</details>')

HTML=f"""<!doctype html><html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>คลังข้อสอบเคมี (offline)</title><style>
body{{font-family:"Sarabun","Segoe UI",Tahoma,sans-serif;background:#f4f6fb;color:#1f2937;margin:0;line-height:1.6}}
.wrap{{max-width:900px;margin:0 auto;padding:16px}}
h1{{font-size:1.2rem}} .sub{{color:#6b7280;font-size:.9rem;margin-bottom:10px}}
.index{{background:#fff;border:1px solid #e5e9f0;border-radius:12px;padding:12px 16px;margin-bottom:18px}}
.index ul{{margin:6px 0;padding-left:18px}} .index a{{text-decoration:none;color:#2563eb}}
details{{background:#fff;border:1px solid #e5e9f0;border-radius:12px;margin-bottom:14px;overflow:hidden}}
summary{{cursor:pointer;padding:14px 16px;font-weight:700;font-size:1.05rem;color:#334155;background:#f8fafc}}
.cnt{{color:#94a3b8;font-weight:400;font-size:.85rem}}
.card{{border-top:1px solid #eef2f7;border-left:5px solid #cbd5e1;padding:14px 16px}}
.card.lv-easy{{border-left-color:#16a34a}} .card.lv-medium{{border-left-color:#d97706}} .card.lv-hard{{border-left-color:#dc2626}}
.top{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:8px}}
.qid{{font-weight:800;color:#2563eb}}
.b{{font-size:.72rem;padding:2px 9px;border-radius:999px;font-weight:600;white-space:nowrap}}
.ch{{background:#eef2ff;color:#3730a3}} .ex{{color:#fff}} .ty{{background:#ecfeff;color:#0e7490}}
.d-easy{{background:#dcfce7;color:#166534}}.d-medium{{background:#fef3c7;color:#92400e}}.d-hard{{background:#fee2e2;color:#991b1b}}
.body{{font-size:1rem}} .body ul{{margin:.4em 0;padding-left:1.3em}} .body li{{margin:2px 0}}
.fig{{display:block;max-width:100%;height:auto;margin:12px auto;border:1px solid #e5e9f0;border-radius:10px;background:#fff;padding:6px}}
.note{{background:#fffbeb;border:1px solid #fde68a;color:#92400e;padding:6px 10px;border-radius:8px;margin-top:8px;font-size:.85rem}}
.src{{margin-top:10px;padding-top:8px;border-top:1px dashed #e5e9f0;color:#6b7280;font-size:.8rem}}
code{{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:.9em}}
table{{border-collapse:collapse}} td,th{{border:1px solid #e5e9f0;padding:3px 7px}}
</style></head><body><div class="wrap">
<h1>🧪 คลังข้อสอบเคมี <span style="font-weight:400;color:#6b7280;font-size:.85rem">— เวอร์ชันออฟไลน์ (เปิดบน iPad ได้)</span></h1>
<div class="sub">รวม {total} ข้อ · แตะหัวข้อบทเพื่อย่อ/ขยาย · ใช้ค้นหาในหน้า (Find on Page) เพื่อค้นคำหรือเลขข้อ</div>
<div class="index"><b>สารบัญบท</b><ul>{''.join(idx)}</ul></div>
{''.join(secs)}
</div></body></html>"""
open(OUT,"w",encoding="utf-8").write(HTML)
print("wrote",OUT,"-",total,"questions")
