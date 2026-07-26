# -*- coding: utf-8 -*-
"""Parse question-bank.md -> self-contained interactive HTML viewer.
Features: 3 switchable layouts (list / cards / two-pane), focus/present mode,
random pick, full filters incl. exam-type, responsive for iPad + laptop."""
import re, json, markdown, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "question-bank.md")
OUT = os.path.join(ROOT, "index.html")  # the viewer IS the site root (live web app)

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
# exam-type taxonomy: slug -> (Thai label, badge color)
EXAMS = {
 "posn":   ("สอวน.",        "#4338ca"),
 "alevel": ("A-Level",      "#0d9488"),
 "samanya":("9 วิชาสามัญ",  "#7c3aed"),
 "pat2":   ("PAT2",         "#db2777"),
 "onet":   ("O-NET",        "#16a34a"),
 "school": ("โรงเรียน",     "#d97706"),
 "unknown":("ยังไม่ระบุ",   "#64748b"),
}

txt = open(SRC, encoding="utf-8").read()
blocks = re.split(r"(?m)^### (Q-\d+)\b", txt)
questions = []
META = ("**Answer:**","**Source:**","**Note:**","**Also appears:**","**Figure:**")
for i in range(1, len(blocks), 2):
    qid = blocks[i].strip()
    lines = blocks[i+1].splitlines()
    header = lines[0].strip().lstrip("· ").strip()
    tagline = ""; body_lines = []; meta = {}; j = 1
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
            body_lines.append(ln)
    def tag(name):
        m = re.search(r"#%s/([^\s#]+)" % name, tagline); return m.group(1) if m else ""
    ch = tag("ch"); exam = tag("exam") or "unknown"
    subject = tag("subject"); bio = tag("bio"); app = tag("app")
    if subject == "bio":
        top = bio.split(".")[0] if bio else "?"
        chName = BIO_CHAPTERS.get(top, "")
        groupKey = "bio-" + top
        groupLabel = f"ชีววิทยา · {top}. {chName}"
    elif subject == "applied":
        chName = APP_TOPICS.get(app, app)
        groupKey = "app-" + app
        groupLabel = f"เคมีประยุกต์ · {chName}"
    else:
        chName = CHAPTERS.get(ch, "")
        groupKey = "ch-" + ch
        groupLabel = f"บทที่ {int(ch)} · {chName}" if ch else "บทที่ ?"
    body_md = "\n".join(body_lines).strip()
    # short snippet for list/two-pane rows: first non-empty body line, stripped of md
    snip = ""
    for bl in body_lines:
        t = bl.strip()
        if t and not t.startswith(("-","*","#")):
            snip = re.sub(r"[*_`]","",t); break
    questions.append({
        "id": qid, "ch": ch, "chName": chName,
        "subject": subject, "bio": bio, "app": app, "groupKey": groupKey, "groupLabel": groupLabel,
        "exam": exam, "year": tag("year"), "ver": tag("ver"),
        "diff": tag("diff"), "type": tag("type"),
        "bodyHtml": markdown.markdown(body_md, extensions=["tables"]),
        "snippet": snip[:90],
        "answer": meta.get("Answer",""), "source": meta.get("Source",""),
        "note": meta.get("Note",""), "figure": meta.get("Figure",""),
        "search": (body_md+" "+header).lower(),
    })

def _sortkey(q):  # chem by chapter, then bio bucket, then applied bucket, then Q-id
    if q["subject"] == "bio":
        return (100, list(biokey(q["bio"])), q["id"])
    if q["subject"] == "applied":
        return (200, [q["app"]], q["id"])
    return (int(q["ch"] or 99), [], q["id"])
questions.sort(key=_sortkey)
present = {}
for q in questions:
    if q["subject"] not in ("bio","applied"): present[q["ch"]] = present.get(q["ch"],0)+1
biocount = sum(1 for q in questions if q["subject"]=="bio")
appcount = sum(1 for q in questions if q["subject"]=="applied")
chemcount = sum(1 for q in questions if q["subject"] not in ("bio","applied"))
biocounts = {}
for q in questions:
    if q["subject"]=="bio":
        top = q["bio"].split(".")[0] if q["bio"] else "?"
        biocounts[top] = biocounts.get(top,0)+1
appcounts = {}
for q in questions:
    if q["subject"]=="applied":
        appcounts[q["app"]] = appcounts.get(q["app"],0)+1
examcount = {}
for q in questions: examcount[q["exam"]] = examcount.get(q["exam"],0)+1

# ---------- solutions (solutions/chNN.md) ----------
# AI-derived worked solutions, keyed by Q-id. Deliberately a SEPARATE store:
# build_bank.py's META whitelist silently deletes any **Solution:** line written
# into question-bank.md, and body-level text would show the answer to the student.
SOLDIR = os.path.join(ROOT, "solutions")
SOLMETA = ("**Answer:**", "**Confidence:**", "**Checked:**", "**Solution:**")
solutions = {}
if os.path.isdir(SOLDIR):
    for fn in sorted(os.listdir(SOLDIR)):
        if not fn.endswith(".md"): continue
        stxt = open(os.path.join(SOLDIR, fn), encoding="utf-8").read()
        sblocks = re.split(r"(?m)^### (Q-\d+)\b", stxt)
        for i in range(1, len(sblocks), 2):
            sqid = sblocks[i].strip()
            slines = sblocks[i+1].splitlines()[1:]   # drop the header remainder
            fields, cur = {}, None
            for ln in slines:
                s = ln.strip()
                lab = next((m for m in SOLMETA if s.startswith(m)), None)
                if lab:
                    cur = lab.strip("*: ")
                    fields[cur] = [s[len(lab):].strip()]
                elif cur:
                    fields[cur].append(ln)
            if not fields: continue
            body = "\n".join(fields.get("Solution", [])).strip()
            solutions[sqid] = {
                "answer": " ".join(fields.get("Answer", [])).strip(),
                "conf":   " ".join(fields.get("Confidence", [])).strip(),
                "checked":" ".join(fields.get("Checked", [])).strip().lower(),
                "html":   markdown.markdown(body, extensions=["tables"]) if body else "",
            }
solcount = {"have": 0, "flag": 0, "unchecked": 0}
for q in questions:
    s = solutions.get(q["id"])
    q["solHtml"]   = s["html"]   if s else ""
    q["solAnswer"] = s["answer"] if s else ""
    # flagged = I wasn't sure, OR Prat marked it wrong via apply_review.py
    q["solFlag"]   = bool(s and ("⚠" in s["conf"] or "⚠" in s["checked"]))
    q["solChecked"]= bool(s and s["checked"].startswith("yes"))
    if s:
        solcount["have"] += 1
        if q["solFlag"]: solcount["flag"] += 1
        if not q["solChecked"]: solcount["unchecked"] += 1
print("solutions loaded:", solcount["have"], "| flagged:", solcount["flag"],
      "| unchecked:", solcount["unchecked"])

data = {
 "questions": questions, "chapters": CHAPTERS, "solcount": solcount,
 "bioChapters": BIO_CHAPTERS, "appTopics": APP_TOPICS,
 "exams": {k:{"label":v[0],"color":v[1]} for k,v in EXAMS.items()},
 "years": sorted({q["year"] for q in questions if q["year"]}),
 "types": sorted({q["type"] for q in questions if q["type"]}),
 "counts": present, "examcount": examcount,
 "chemcount": chemcount, "biocount": biocount, "appcount": appcount,
 "biocounts": biocounts, "appcounts": appcounts,
}

HTML = r"""<!doctype html><html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5">
<title>คลังข้อสอบเคมี · Chem Question Bank</title>
<style>
:root{--bg:#f4f6fb;--card:#fff;--line:#e5e9f0;--ink:#1f2937;--mut:#6b7280;--accent:#2563eb;--radius:14px}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;font-family:"Sarabun","Segoe UI",Tahoma,sans-serif;background:var(--bg);color:var(--ink);font-size:16px}
button,select,input{font-family:inherit}
/* ---------- toolbar ---------- */
header{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.96);backdrop-filter:blur(6px);
  border-bottom:1px solid var(--line);padding:12px 16px}
.bar1{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:9px}
.title{font-size:1.05rem;font-weight:700;margin-right:auto}
.title small{font-weight:400;color:var(--mut);font-size:.8rem}
#q{flex:1;min-width:180px;padding:10px 13px;border:1px solid var(--line);border-radius:10px;font-size:1rem}
.bar2{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
select{padding:8px 10px;border:1px solid var(--line);border-radius:10px;font-size:.88rem;background:#fff;max-width:46vw}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.seg button{border:0;background:#fff;padding:8px 12px;cursor:pointer;font-size:.85rem;color:var(--mut)}
.seg button.on{background:var(--accent);color:#fff;font-weight:600}
.btn{padding:8px 13px;border:1px solid var(--line);background:#fff;border-radius:10px;cursor:pointer;font-size:.85rem}
.btn:hover{background:#f1f5f9}
#count{color:var(--mut);font-size:.82rem;margin-left:auto;white-space:nowrap}
/* ---------- badges ---------- */
.badge{font-size:.72rem;padding:2px 9px;border-radius:999px;font-weight:600;white-space:nowrap;display:inline-block}
.b-ch{background:#eef2ff;color:#3730a3}
.b-exam{color:#fff}
.b-diff{color:#fff}
.d-easy{background:#16a34a}.d-medium{background:#d97706}.d-hard{background:#dc2626}
.b-type{background:#ecfeff;color:#0e7490}
.diff-txt{font-size:.72rem;font-weight:700}
.de-easy{color:#16a34a}.de-medium{color:#d97706}.de-hard{color:#dc2626}
/* ---------- main + layouts ---------- */
main{max-width:1040px;margin:16px auto;padding:0 14px}
.chap-h{margin:26px 0 10px;font-size:1.02rem;font-weight:700;color:#334155;border-bottom:2px solid var(--line);padding-bottom:5px}
/* cards */
.card{background:var(--card);border:1px solid var(--line);border-left:5px solid #cbd5e1;border-radius:var(--radius);
  padding:15px 17px;margin-bottom:13px}
.card.lv-easy{border-left-color:#16a34a}.card.lv-medium{border-left-color:#d97706}.card.lv-hard{border-left-color:#dc2626}
.card-top{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-bottom:9px}
.qid{font-weight:800;color:var(--accent)}
.spacer{flex:1}
.body{font-size:1rem;line-height:1.7}
.body ul{margin:.5em 0;padding-left:0;list-style:none}
.body li{padding:5px 10px;border-radius:8px;margin:3px 0}
.body li:hover{background:#f8fafc}
.body p{margin:.45em 0}
.fig{display:block;max-width:100%;height:auto;margin:12px auto;border:1px solid var(--line);border-radius:10px;background:#fff;padding:6px}
.sheet .fig{max-height:52vh;width:auto}
.foot{margin-top:11px;padding-top:8px;border-top:1px dashed var(--line);font-size:.8rem;color:var(--mut);display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.note{background:#fffbeb;border:1px solid #fde68a;color:#92400e;padding:7px 11px;border-radius:9px;margin-top:9px;font-size:.85rem}
/* ---------- solutions (collapsed by default: protects attempt-before-instruction) ---------- */
.solbtn{margin-top:10px;border:1px solid #059669;color:#059669;background:#fff;padding:6px 13px;
  border-radius:9px;cursor:pointer;font-size:.82rem;font-weight:600}
.solbtn:hover{background:#059669;color:#fff}
.solbtn.flag{border-color:#d97706;color:#d97706}
.solbtn.flag:hover{background:#d97706;color:#fff}
.solwrap{display:none;margin-top:10px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:11px;padding:11px 14px}
.solwrap.show{display:block}
.solwrap.flag{background:#fffbeb;border-color:#fcd34d}
.soldis{font-size:.75rem;color:#92400e;background:#fef3c7;border:1px solid #fcd34d;
  border-radius:7px;padding:5px 9px;margin-bottom:9px;line-height:1.5}
.solans{font-weight:700;color:#065f46;margin-bottom:7px;font-size:.95rem}
.solwrap.flag .solans{color:#92400e}
.solbody{font-size:.9rem;line-height:1.75}
.solbody p{margin:.4em 0}
.solbody table{font-size:.88em;margin:.5em 0}
.solbody hr{border:0;border-top:1px dashed var(--line);margin:.7em 0}
.sheet .solbody{font-size:1rem}
.banner{background:#fef3c7;border-bottom:1px solid #fcd34d;color:#92400e;
  padding:7px 34px 7px 14px;font-size:.8rem;text-align:center;line-height:1.5;position:relative}
.banner .bx{position:absolute;right:8px;top:50%;transform:translateY(-50%);border:0;background:transparent;
  color:#92400e;font-size:1.05rem;line-height:1;cursor:pointer;padding:4px 7px;border-radius:6px;opacity:.65}
.banner .bx:hover{opacity:1;background:rgba(146,64,14,.12)}
/* re-open handle once dismissed — the disclaimer is never fully gone */
#soltab{display:none;background:#fef3c7;border-bottom:1px solid #fcd34d;color:#92400e;
  padding:3px 14px;font-size:.72rem;text-align:center;cursor:pointer}
#soltab:hover{background:#fde68a}
/* ---------- in-browser review (marks live in localStorage, exported as JSON) ---------- */
.revbar{margin-top:11px;padding-top:9px;border-top:1px dashed #bbf7d0;display:flex;gap:7px;
  flex-wrap:wrap;align-items:center;font-size:.78rem;color:var(--mut)}
.solwrap.flag .revbar{border-top-color:#fcd34d}
.revbtn{border:1px solid var(--line);background:#fff;color:#475569;padding:5px 12px;
  border-radius:8px;cursor:pointer;font-size:.78rem;font-weight:600}
.revbtn:hover{border-color:#94a3b8}
.revbtn.ok.on{background:#059669;border-color:#059669;color:#fff}
.revbtn.bad.on{background:#dc2626;border-color:#dc2626;color:#fff}
.revnote{flex:1 1 100%;margin-top:6px;border:1px solid var(--line);border-radius:8px;
  padding:7px 10px;font-size:.82rem;min-height:52px;resize:vertical;display:none;font-family:inherit}
.revnote.show{display:block}
.revmark{font-size:.9rem;margin-left:5px}
.solbtn.done{border-color:#059669;background:#ecfdf5}
.solbtn.wrong{border-color:#dc2626;color:#dc2626;background:#fef2f2}
#exportbtn{border:1px solid #7c3aed;color:#7c3aed;background:#fff;padding:6px 12px;
  border-radius:9px;cursor:pointer;font-size:.8rem;font-weight:600}
#exportbtn:hover{background:#7c3aed;color:#fff}
#exportbtn.none{opacity:.45}
.expwrap{position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:60;display:none;
  align-items:center;justify-content:center;padding:18px}
.expwrap.show{display:flex}
.expbox{background:#fff;border-radius:16px;padding:18px;max-width:620px;width:100%;max-height:86vh;
  display:flex;flex-direction:column;gap:11px}
.expbox h3{margin:0;font-size:1rem}
.expbox p{margin:0;font-size:.83rem;color:var(--mut);line-height:1.6}
.expbox textarea{width:100%;flex:1;min-height:190px;font-family:ui-monospace,Menlo,Consolas,monospace;
  font-size:.74rem;border:1px solid var(--line);border-radius:10px;padding:10px;resize:vertical}
.exprow{display:flex;gap:8px;flex-wrap:wrap}
.exprow button{border:1px solid var(--line);background:#fff;padding:7px 13px;border-radius:9px;
  cursor:pointer;font-size:.82rem;font-weight:600}
.exprow button.pri{background:var(--accent);border-color:var(--accent);color:#fff}
.exprow button.dan{color:#dc2626;border-color:#fecaca}
code{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:.92em}
table{border-collapse:collapse;font-size:.92em}td,th{border:1px solid var(--line);padding:3px 7px}
.present-btn{margin-left:auto;border:1px solid var(--accent);color:var(--accent);background:#fff;
  padding:5px 11px;border-radius:8px;cursor:pointer;font-size:.8rem;font-weight:600}
.present-btn:hover{background:var(--accent);color:#fff}
/* list (accordion) */
.row{background:#fff;border:1px solid var(--line);border-radius:11px;margin-bottom:7px;overflow:hidden}
.row-h{display:flex;align-items:center;gap:9px;padding:11px 14px;cursor:pointer}
.row-h:hover{background:#f8fafc}
.row-id{font-weight:700;color:var(--accent);font-size:.9rem;white-space:nowrap}
.row-snip{flex:1;color:#475569;font-size:.93rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.row-body{padding:0 16px 14px;display:none}
.row.open .row-body{display:block}
.chev{color:var(--mut);transition:transform .15s}
.row.open .chev{transform:rotate(90deg)}
/* two-pane */
.pane{display:grid;grid-template-columns:340px 1fr;gap:14px;align-items:start}
.pane-list{max-height:calc(100vh - 150px);overflow:auto;border:1px solid var(--line);border-radius:12px;background:#fff}
.pane-item{display:flex;gap:8px;align-items:center;padding:10px 12px;border-bottom:1px solid var(--line);cursor:pointer}
.pane-item:hover{background:#f1f5f9}
.pane-item.sel{background:#eef2ff}
.pane-detail{background:#fff;border:1px solid var(--line);border-radius:12px;padding:20px 22px;position:sticky;top:140px}
.pane-detail .body{font-size:1.06rem}
.empty{text-align:center;color:var(--mut);padding:50px}
/* ---------- focus / present modal ---------- */
.modal{position:fixed;inset:0;z-index:50;background:rgba(15,23,42,.55);display:none;align-items:center;justify-content:center;padding:16px}
.modal.show{display:flex}
.sheet{background:#fff;border-radius:18px;max-width:880px;width:100%;max-height:92vh;overflow:auto;padding:26px 30px;position:relative}
.sheet .mtop{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:14px}
.sheet .body{font-size:1.35rem;line-height:1.85}
.sheet .body li{padding:9px 14px;font-size:1.05em}
.x{position:absolute;top:14px;right:16px;border:0;background:#f1f5f9;border-radius:50%;width:38px;height:38px;font-size:1.2rem;cursor:pointer}
.mctrl{display:flex;gap:10px;align-items:center;margin-top:20px;flex-wrap:wrap}
.mctrl button{padding:10px 18px;border-radius:10px;border:1px solid var(--line);background:#fff;cursor:pointer;font-size:1rem}
.reveal{background:var(--accent)!important;color:#fff;border-color:var(--accent)!important;font-weight:700}
.ans-box{margin-top:16px;padding:14px 18px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;font-size:1.1rem;display:none}
.ans-box.show{display:block}
.mpos{margin-left:auto;color:var(--mut);font-size:.9rem}
@media(max-width:820px){
  .pane{grid-template-columns:1fr}
  .pane-detail{position:static;display:none}
  select{max-width:42vw}
  .sheet .body{font-size:1.18rem}
  main{margin-top:10px}
}
</style></head><body>
<header>
 <div class="bar1">
   <span class="title">🧪 คลังข้อสอบเคมี <small>Chem Question Bank</small></span>
   <input id="q" placeholder="🔍 ค้นหาข้อความ / สูตร / Q-id...">
 </div>
 <div class="bar2">
   <select id="fsubj"></select>
   <select id="fch"></select>
   <select id="fexam"></select>
   <select id="fyear"></select>
   <select id="fdiff"></select>
   <select id="ftype"></select>
   <select id="fsol"></select>
   <button class="btn" id="random">🎲 สุ่มข้อ</button>
   <button id="exportbtn" style="display:none">📥 ผลตรวจ</button>
   <span class="seg" id="layout">
     <button data-v="list">รายการ</button>
     <button data-v="cards">การ์ด</button>
     <button data-v="pane">2 คอลัมน์</button>
   </span>
   <span id="count"></span>
 </div>
 <div class="banner" id="soldis" style="display:none"></div>
 <div id="soltab">⚠️ เฉลยทั้งหมดเป็นเฉลยที่ AI ทำขึ้น — แตะเพื่ออ่านคำเตือนเต็ม</div>
</header>
<main id="root"></main>

<div class="modal" id="modal"><div class="sheet">
  <button class="x" id="mx">✕</button>
  <div class="mtop" id="mtop"></div>
  <div class="body" id="mbody"></div>
  <div class="note" id="mnote" style="display:none"></div>
  <div class="ans-box" id="mans"></div>
  <div id="msol"></div>
  <div class="mctrl">
    <button id="mreveal" class="reveal">👁 เฉลย / หมายเหตุ</button>
    <button id="mprev">◀ ก่อนหน้า</button>
    <button id="mnext">ถัดไป ▶</button>
    <span class="mpos" id="mpos"></span>
  </div>
  <div class="foot" id="mfoot" style="margin-top:14px"></div>
</div></div>

<div class="expwrap" id="expwrap"><div class="expbox">
  <h3>📥 ผลตรวจเฉลย</h3>
  <p id="expsum"></p>
  <textarea id="exptext" readonly></textarea>
  <p>ก๊อปข้อความนี้ส่งให้ตัวเอง (LINE / Notes) หรือกดดาวน์โหลดเป็นไฟล์ แล้วเอาไปวางในเครื่องที่มีโปรเจกต์
     สั่ง <code>python tools/apply_review.py &lt;ไฟล์&gt;</code> ระบบจะอัปเดต <code>Checked:</code> ใน
     <code>solutions/*.md</code> ให้เอง</p>
  <div class="exprow">
    <button class="pri" id="expcopy">📋 คัดลอก</button>
    <button id="expdl">💾 ดาวน์โหลดไฟล์</button>
    <button class="dan" id="expclear">🗑 ล้างผลตรวจทั้งหมด</button>
    <button id="expclose" style="margin-left:auto">ปิด</button>
  </div>
</div></div>

<script>
const DATA = __DATA__;
const DIFF_TH={easy:"ง่าย",medium:"ปานกลาง",hard:"ยาก"};
const $=s=>document.querySelector(s);
let view = localStorage.getItem("cqb_view") || "cards";
let filtered = [];

function opt(sel,val,label){const o=document.createElement("option");o.value=val;o.textContent=label;sel.appendChild(o);}
// subject selector (เคมี / ชีววิทยา / เคมีประยุกต์) — drives the topic dropdown below
opt($("#fsubj"),"",`🧪 ทุกวิชา (${DATA.questions.length})`);
if(DATA.chemcount)opt($("#fsubj"),"chem",`⚗️ เคมี (${DATA.chemcount})`);
if(DATA.biocount)opt($("#fsubj"),"bio",`🧬 ชีววิทยา (${DATA.biocount})`);
if(DATA.appcount)opt($("#fsubj"),"applied",`🧫 เคมีประยุกต์ (${DATA.appcount})`);

function populateChapters(subj){
  const sel=$("#fch"); sel.innerHTML="";
  if(subj==="bio"){
    opt(sel,"","📚 ทุกหัวข้อ");
    for(const[n,name]of Object.entries(DATA.bioChapters)){const c=DATA.biocounts[n]||0;if(c)opt(sel,n,`${n}. ${name} (${c})`);}
  }else if(subj==="applied"){
    opt(sel,"","📚 ทุกหัวข้อ");
    for(const[k,name]of Object.entries(DATA.appTopics)){const c=DATA.appcounts[k]||0;if(c)opt(sel,k,`${name} (${c})`);}
    for(const k of Object.keys(DATA.appcounts)){if(!DATA.appTopics[k])opt(sel,k,`${k} (${DATA.appcounts[k]})`);}
  }else{ // chem, or "ทุกวิชา"
    opt(sel,"","📚 ทุกบท");
    for(const[n,name]of Object.entries(DATA.chapters)){const c=DATA.counts[n]||0;if(c)opt(sel,n,`${parseInt(n)}. ${name} (${c})`);}
  }
}
populateChapters("");
opt($("#fexam"),"","🏷 ทุกสนามสอบ");
for(const[k,c]of Object.entries(DATA.examcount||{})){const e=DATA.exams[k]||{label:k};opt($("#fexam"),k,`${e.label} (${c})`);}
opt($("#fyear"),"","📅 ทุกปี");DATA.years.forEach(y=>opt($("#fyear"),y,"ปี "+y));
opt($("#fdiff"),"","📊 ทุกระดับ");["easy","medium","hard"].forEach(d=>opt($("#fdiff"),d,DIFF_TH[d]));
opt($("#ftype"),"","✏️ ทุกชนิด");DATA.types.forEach(t=>opt($("#ftype"),t,t));
const SC=DATA.solcount||{have:0,flag:0,unchecked:0};
if(SC.have){
  $("#soldis").innerHTML=`⚠️ <b>เฉลย ${SC.have} ข้อในคลังนี้เป็นเฉลยที่ AI ทำขึ้น ไม่ใช่เฉลยทางการ</b> — `
    +`ข้อสอบ สอวน. / PAT2 / 9 วิชาสามัญ ไม่มีเฉลยแจก ทุกข้อจึงเป็นการหาคำตอบเอง`
    +(SC.unchecked?` · <b>${SC.unchecked} ข้อยังไม่ผ่านการตรวจโดยพี่ปราช</b>`:``)
    +(SC.flag?` · ${SC.flag} ข้อติดธง ⚠️ (ตอบไม่ฟันธง)`:``)
    +` — ใช้เป็นแนวทาง อย่าเชื่อ 100%`
    +`<button class="bx" id="bx" title="ปิด">✕</button>`;
  // dismissible, and the choice sticks — but it collapses to a one-line tab, never to nothing.
  // The per-question disclaimer inside each solution is NOT dismissible.
  const setBanner=open=>{
    $("#soldis").style.display = open?"block":"none";
    $("#soltab").style.display = open?"none":"block";
  };
  setBanner(localStorage.getItem("cqb_banner")!=="0");
  $("#bx").onclick=()=>{localStorage.setItem("cqb_banner","0");setBanner(false);};
  $("#soltab").onclick=()=>{localStorage.removeItem("cqb_banner");setBanner(true);};
}
opt($("#fsol"),"","📖 เฉลย: ทั้งหมด");
if(SC.have){
  opt($("#fsol"),"has",`✅ มีวิธีทำ (${SC.have})`);
  opt($("#fsol"),"none",`— ยังไม่มีวิธีทำ (${DATA.questions.length-SC.have})`);
  if(SC.flag)      opt($("#fsol"),"flag",`⚠️ ต้องดูเอง (${SC.flag})`);
  if(SC.unchecked) opt($("#fsol"),"unchecked",`🕗 ยังไม่ตรวจ (${SC.unchecked})`);
  const done=SC.have-SC.unchecked;
  if(done)         opt($("#fsol"),"checked",`✅ ตรวจแล้ว (${done})`);
}

function examBadge(q){const e=DATA.exams[q.exam]||{label:q.exam.toUpperCase(),color:"#64748b"};
  return `<span class="badge b-exam" style="background:${e.color}">${e.label} ${q.year}</span>`;}
function diffBadge(q){return `<span class="badge b-diff d-${q.diff}">${DIFF_TH[q.diff]||q.diff}</span>`;}
function chBadge(q){
  if(q.subject==="bio") return `<span class="badge b-ch">ชีววิทยา ${q.bio}. ${q.chName}</span>`;
  if(q.subject==="applied") return `<span class="badge b-ch">ประยุกต์ · ${q.chName}</span>`;
  return `<span class="badge b-ch">บท ${parseInt(q.ch)}. ${q.chName}</span>`;}
function footHtml(q){return `📄 ${q.source} &nbsp;·&nbsp; เฉลย: ${q.answer||"—"}`;}
function figHtml(q){return q.figure?`<img class="fig" src="${q.figure}" alt="${q.id} figure" loading="lazy">`:"";}
/* ---- review marks: Prat ticks solutions off in the browser (iPad-friendly),
   they persist in localStorage, and get exported as JSON for tools/apply_review.py ---- */
let REV = {};
try{ REV = JSON.parse(localStorage.getItem("cqb_review")||"{}") || {}; }catch(e){ REV = {}; }
function saveRev(){
  try{ localStorage.setItem("cqb_review", JSON.stringify(REV)); }
  catch(e){ alert("บันทึกผลตรวจไม่ได้ (พื้นที่เบราว์เซอร์เต็ม) — กด 📥 ผลตรวจ แล้วเซฟออกมาก่อน"); }
  refreshExport();
}
function revCount(){ return Object.keys(REV).length; }
function refreshExport(){
  const n=revCount(), b=$("#exportbtn");
  b.style.display = (DATA.solcount&&DATA.solcount.have) ? "inline-block" : "none";
  b.textContent = n ? `📥 ผลตรวจ (${n})` : "📥 ผลตรวจ";
  b.classList.toggle("none", n===0);
}
function revBar(q){
  const r = REV[q.id] || {};
  const note = (r.note||"").replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  return `<div class="revbar" data-q="${q.id}">
      <span>ตรวจแล้วหรือยัง:</span>
      <button class="revbtn ok${r.v==="ok"?" on":""}"  data-v="ok">✓ ถูก</button>
      <button class="revbtn bad${r.v==="bad"?" on":""}" data-v="bad">✗ ผิด / ต้องแก้</button>
      ${r.v?`<span class="revmark">${r.v==="ok"?"✅ บันทึกแล้ว":"❌ ทำเครื่องหมายว่าผิด"}</span>`:""}
      <textarea class="revnote${r.v==="bad"?" show":""}" data-q="${q.id}"
        placeholder="ผิดตรงไหน / คำตอบที่ถูกคืออะไร (ไม่ใส่ก็ได้)">${note}</textarea>
    </div>`;
}

/* Solution block — ALWAYS collapsed on render. Never auto-open: the whole point of
   present mode is that the student attempts it before seeing the working. */
function solHtml(q){
  if(!q.solHtml && !q.solAnswer) return "";
  const r = REV[q.id] || {};
  const mark = r.v==="ok" ? " done" : r.v==="bad" ? " wrong" : "";
  const f = (q.solFlag ? " flag" : "") + mark;
  const label = r.v==="ok" ? "✅ ดูวิธีทำ (ตรวจแล้ว)"
              : r.v==="bad" ? "❌ ดูวิธีทำ (ทำเครื่องหมายว่าผิด)"
              : q.solFlag ? "⚠️ ดูเฉลย (มีข้อสงสัย)" : "👁 ดูวิธีทำ";
  const dis = q.solFlag
    ? "⚠️ ข้อนี้ผมไม่ฟันธง — โจทย์กำกวมหรือตัวเลือกไม่ตรง อ่านเหตุผลในวิธีทำแล้วตัดสินเอง"
    : "เฉลยนี้ AI ทำขึ้นเอง ไม่ใช่เฉลยทางการ (ข้อสอบ สอวน./PAT2/9 วิชาสามัญ ไม่มีเฉลยแจก)"
      + (q.solChecked ? " · ✅ พี่ปราชตรวจแล้ว" : " · ยังไม่ผ่านการตรวจ ใช้เป็นแนวทาง อย่าเชื่อ 100%");
  return `<button class="solbtn${f}" data-sol="1" data-label="${label}">${label}</button>
    <div class="solwrap${f}">
      <div class="soldis">${dis}</div>
      ${q.solAnswer?`<div class="solans">ตอบ: ${q.solAnswer}</div>`:""}
      <div class="solbody">${q.solHtml}</div>
      ${revBar(q)}
    </div>`;
}

function apply(){
  const t=$("#q").value.trim().toLowerCase(),subj=$("#fsubj").value,ch=$("#fch").value,
        ex=$("#fexam").value,yr=$("#fyear").value,df=$("#fdiff").value,tp=$("#ftype").value,
        sl=$("#fsol").value;
  filtered=DATA.questions.filter(x=>{
    // subject: chem = neither bio nor applied
    if(subj==="chem" && (x.subject==="bio"||x.subject==="applied")) return false;
    if(subj==="bio" && x.subject!=="bio") return false;
    if(subj==="applied" && x.subject!=="applied") return false;
    // topic within the chosen subject
    if(ch){
      if(subj==="bio"){ if((x.bio.split(".")[0]||"?")!==ch) return false; }
      else if(subj==="applied"){ if(x.app!==ch) return false; }
      else if(x.ch!==ch) return false;
    }
    if(ex && x.exam!==ex) return false;
    if(yr && x.year!==yr) return false;
    if(df && x.diff!==df) return false;
    if(tp && x.type!==tp) return false;
    const hasSol = !!(x.solHtml||x.solAnswer);
    if(sl==="has"       && !hasSol) return false;
    if(sl==="none"      &&  hasSol) return false;
    if(sl==="flag"      && !(hasSol && x.solFlag)) return false;
    if(sl==="unchecked" && !(hasSol && !x.solChecked)) return false;
    if(sl==="checked"   && !(hasSol && x.solChecked)) return false;
    if(t && !(x.search.includes(t)||x.id.toLowerCase().includes(t))) return false;
    return true;
  });
  $("#count").textContent=`${filtered.length} / ${DATA.questions.length} ข้อ`;
  render();
}

function render(){
  const R=$("#root");
  if(!filtered.length){R.innerHTML='<div class="empty">ไม่พบข้อสอบที่ตรงกับเงื่อนไข</div>';return;}
  if(view==="cards") renderCards(R);
  else if(view==="list") renderList(R);
  else renderPane(R);
}
function cardHtml(q,idx){return `<div class="card lv-${q.diff}">
   <div class="card-top">${chBadge(q)}${examBadge(q)}${diffBadge(q)}<span class="badge b-type">${q.type}</span>
     <span class="spacer"></span><span class="qid">${q.id}</span>
     <button class="present-btn" data-i="${idx}">▶ แสดงให้นักเรียน</button></div>
   <div class="body">${q.bodyHtml}${figHtml(q)}</div>
   ${q.note?`<div class="note">📌 ${q.note}</div>`:""}
   ${solHtml(q)}
   <div class="foot">${footHtml(q)}</div></div>`;}
function renderCards(R){
  // group by chapter (or biology bucket)
  let html="",lastG=null;
  filtered.forEach((q,i)=>{
    if(q.groupKey!==lastG){lastG=q.groupKey;html+=`<div class="chap-h">${q.groupLabel}</div>`;}
    html+=cardHtml(q,i);
  });
  R.innerHTML=html;
}
function renderList(R){
  let html="",lastG=null;
  filtered.forEach((q,i)=>{
    if(q.groupKey!==lastG){lastG=q.groupKey;html+=`<div class="chap-h">${q.groupLabel}</div>`;}
    html+=`<div class="row" data-i="${i}">
      <div class="row-h"><span class="chev">▸</span><span class="row-id">${q.id}</span>
        <span class="diff-txt de-${q.diff}">${DIFF_TH[q.diff]}</span>
        <span class="row-snip">${q.snippet||""}</span>${examBadge(q)}</div>
      <div class="row-body"><div class="body">${q.bodyHtml}${figHtml(q)}</div>
        ${q.note?`<div class="note">📌 ${q.note}</div>`:""}
        ${solHtml(q)}
        <div class="foot">${footHtml(q)}
        <button class="present-btn" data-i="${i}">▶ แสดงให้นักเรียน</button></div></div></div>`;
  });
  R.innerHTML=html;
}
function renderPane(R){
  let items=filtered.map((q,i)=>`<div class="pane-item" data-i="${i}">
     <span class="row-id">${q.id}</span><span class="diff-txt de-${q.diff}">${DIFF_TH[q.diff]}</span>
     <span class="row-snip">${q.snippet||""}</span></div>`).join("");
  R.innerHTML=`<div class="pane"><div class="pane-list">${items}</div>
     <div class="pane-detail" id="detail"><div class="empty">เลือกข้อทางซ้ายเพื่อดูรายละเอียด</div></div></div>`;
}
function paneShow(i){
  const q=filtered[i];const d=$("#detail");
  if(window.innerWidth<=820){openModal(i);return;}
  document.querySelectorAll(".pane-item").forEach(el=>el.classList.toggle("sel",el.dataset.i==i));
  d.style.display="block";
  d.innerHTML=`<div class="card-top">${chBadge(q)}${examBadge(q)}${diffBadge(q)}<span class="spacer"></span>
     <span class="qid">${q.id}</span><button class="present-btn" data-i="${i}">▶ แสดงให้นักเรียน</button></div>
     <div class="body">${q.bodyHtml}${figHtml(q)}</div>${q.note?`<div class="note">📌 ${q.note}</div>`:""}
     ${solHtml(q)}
     <div class="foot">${footHtml(q)}</div>`;
}

/* ---- focus / present modal ---- */
let mIdx=0;
function openModal(i){mIdx=i;fillModal();$("#modal").classList.add("show");}
function fillModal(){
  const q=filtered[mIdx];
  $("#mtop").innerHTML=`${chBadge(q)}${examBadge(q)}${diffBadge(q)}<span class="qid">${q.id}</span>`;
  $("#mbody").innerHTML=q.bodyHtml+figHtml(q);
  $("#mfoot").innerHTML=footHtml(q);
  const nb=$("#mnote");if(q.note){nb.style.display="block";nb.textContent="📌 "+q.note;}else nb.style.display="none";
  const ans=$("#mans");ans.classList.remove("show");
  ans.innerHTML=`<b>เฉลย:</b> ${q.answer||"—"}`;
  $("#msol").innerHTML=solHtml(q);   // rebuilt each step → always starts collapsed
  $("#mpos").textContent=`${mIdx+1} / ${filtered.length}`;
}
function step(d){mIdx=(mIdx+d+filtered.length)%filtered.length;fillModal();}

/* events */
$("#layout").querySelectorAll("button").forEach(b=>{
  b.classList.toggle("on",b.dataset.v===view);
  b.onclick=()=>{view=b.dataset.v;localStorage.setItem("cqb_view",view);
    $("#layout").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x.dataset.v===view));render();};
});
["input","change"].forEach(ev=>{$("#q").addEventListener(ev,apply);
  ["#fch","#fexam","#fyear","#fdiff","#ftype","#fsol"].forEach(s=>$(s).addEventListener(ev,apply));});
// subject change → rebuild the topic dropdown for that subject, then re-filter
$("#fsubj").addEventListener("change",()=>{populateChapters($("#fsubj").value);apply();});
$("#random").onclick=()=>{if(filtered.length)openModal(Math.floor(Math.random()*filtered.length));};
/* one delegated handler for every solution toggle + review button, any layout or the modal */
function solToggle(e){
  // --- review buttons ---
  const rb=e.target.closest(".revbtn");
  if(rb){
    e.stopPropagation();
    const bar=rb.closest(".revbar"), qid=bar.dataset.q, v=rb.dataset.v;
    const wrap=bar.closest(".solwrap"), sb=wrap.previousElementSibling;
    const cur=(REV[qid]||{}).v;
    if(cur===v){ const n=(REV[qid]||{}).note; if(n) REV[qid]={note:n}; else delete REV[qid]; }
    else { REV[qid]=Object.assign({}, REV[qid]||{}, {v:v}); }        // tapping the same one un-marks
    saveRev();
    // repaint ONLY this bar + its toggle button — nothing else re-renders under his finger
    const q=DATA.questions.find(x=>x.id===qid);
    const tmp=document.createElement("div"); tmp.innerHTML=revBar(q);
    bar.replaceWith(tmp.firstElementChild);
    const r=REV[qid]||{};
    sb.classList.toggle("done", r.v==="ok");
    sb.classList.toggle("wrong", r.v==="bad");
    sb.dataset.label = r.v==="ok" ? "✅ ดูวิธีทำ (ตรวจแล้ว)"
                     : r.v==="bad" ? "❌ ดูวิธีทำ (ทำเครื่องหมายว่าผิด)"
                     : sb.classList.contains("flag") ? "⚠️ ดูเฉลย (มีข้อสงสัย)" : "👁 ดูวิธีทำ";
    return true;
  }
  if(e.target.closest(".revnote")) { e.stopPropagation(); return true; }   // let him type in peace
  // --- show / hide the solution ---
  const b=e.target.closest(".solbtn");
  if(!b) return false;
  e.stopPropagation();                       // don't collapse the accordion row underneath
  const w=b.nextElementSibling;
  if(w && w.classList.contains("solwrap")){
    const open=w.classList.toggle("show");
    b.textContent = open ? "🙈 ซ่อนวิธีทำ" : (b.dataset.label || "👁 ดูวิธีทำ");
  }
  return true;
}
function noteInput(e){
  const ta=e.target.closest(".revnote");
  if(!ta) return;
  const qid=ta.dataset.q, val=ta.value;
  if(!val && !(REV[qid]||{}).v){ delete REV[qid]; }
  else REV[qid]=Object.assign({}, REV[qid]||{}, {note:val});
  saveRev();
}
$("#root").addEventListener("click",e=>{
  if(solToggle(e)) return;
  const p=e.target.closest(".present-btn");if(p){openModal(+p.dataset.i);return;}
  const item=e.target.closest(".pane-item");if(item){paneShow(+item.dataset.i);return;}
  const rh=e.target.closest(".row-h");if(rh){rh.parentElement.classList.toggle("open");}
});
$("#msol").addEventListener("click",solToggle);
$("#root").addEventListener("input",noteInput);
$("#msol").addEventListener("input",noteInput);

/* ---- export ---- */
function revPayload(){
  const items=Object.entries(REV).map(([id,r])=>({id:id, v:r.v||"", note:r.note||""}))
                                 .sort((a,b)=>a.id.localeCompare(b.id));
  return JSON.stringify({tool:"chem-exam-bank-review", version:1, items:items}, null, 1);
}
function openExport(){
  const items=Object.values(REV);
  const ok=items.filter(r=>r.v==="ok").length, bad=items.filter(r=>r.v==="bad").length;
  $("#expsum").textContent = revCount()
    ? `ตรวจแล้ว ${revCount()} ข้อ — ถูก ${ok} · ผิด/ต้องแก้ ${bad}`
    : "ยังไม่ได้ทำเครื่องหมายข้อไหนเลย — กด ✓ ถูก หรือ ✗ ผิด ใต้วิธีทำก่อน";
  $("#exptext").value = revPayload();
  $("#expwrap").classList.add("show");
}
$("#exportbtn").onclick=openExport;
$("#expclose").onclick=()=>$("#expwrap").classList.remove("show");
$("#expwrap").onclick=e=>{if(e.target.id==="expwrap")$("#expwrap").classList.remove("show");};
$("#expcopy").onclick=async()=>{
  const t=$("#exptext");
  try{ await navigator.clipboard.writeText(t.value); $("#expcopy").textContent="✅ คัดลอกแล้ว"; }
  catch(e){ t.focus(); t.select(); $("#expcopy").textContent="กด Ctrl/⌘+C"; }
  setTimeout(()=>$("#expcopy").textContent="📋 คัดลอก",1800);
};
$("#expdl").onclick=()=>{
  const blob=new Blob([revPayload()],{type:"application/json"});
  const a=document.createElement("a");
  a.href=URL.createObjectURL(blob); a.download="chem-review.json";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(a.href),1500);
};
$("#expclear").onclick=()=>{
  if(!confirm("ล้างผลตรวจทั้งหมดในเบราว์เซอร์นี้? กู้คืนไม่ได้")) return;
  REV={}; saveRev(); $("#expwrap").classList.remove("show"); render();
};
refreshExport();
$("#mx").onclick=()=>$("#modal").classList.remove("show");
$("#modal").onclick=e=>{if(e.target.id==="modal")$("#modal").classList.remove("show");};
$("#mreveal").onclick=()=>$("#mans").classList.toggle("show");
$("#mprev").onclick=()=>step(-1);$("#mnext").onclick=()=>step(1);
document.addEventListener("keydown",e=>{
  if(!$("#modal").classList.contains("show"))return;
  if(e.key==="Escape")$("#modal").classList.remove("show");
  if(e.key==="ArrowLeft")step(-1);if(e.key==="ArrowRight")step(1);
});
apply();
</script></body></html>"""

open(OUT,"w",encoding="utf-8").write(HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False)))
print("wrote", OUT, "-", len(questions), "questions -", len(examcount), "exam type(s)")
