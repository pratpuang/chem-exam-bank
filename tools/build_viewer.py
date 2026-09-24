# -*- coding: utf-8 -*-
"""Parse question-bank.md -> self-contained interactive HTML viewer.
Design (2026-09-24, Prat's picks): Bauhaus grid-board landing page to choose a chapter (circle-reveal
into the bank), poster-deck question layout, kinetic animated background (toggleable, off under
prefers-reduced-motion). Features: 4 switchable layouts (poster deck / cards / list / two-pane),
present mode, random pick, full filters incl. subject/exam/solution status, collapsed solutions with
in-browser ✓/✗ review marks exported for tools/apply_review.py. No AI-disclaimer banner (personal use)."""
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

# ---------- superscript/subscript rendering (render-time only; source stays plain ASCII) ----------
# Convention (see project CLAUDE.md): charges & exponents use ^ (Cu^2+, 10^-18, cm^3, [Kr]4d^3);
# subscripts use _ (IE_1, K_eq, A_xB_y, nuclear ^13_6A). Real Unicode super/subscript chars already
# in the bank (e.g. ⁵⁶₂₆D^2+) have no ASCII marker and are left untouched — only ^ / _ get converted.
# Subscript token = digits/lowercase letters, OR a single uppercase letter (R_A, R_B) — never more,
# so a nuclear "13_6A" subscripts only the "6", not "6A". The lookbehind requires an uppercase
# letter/digit/bracket/degree-sign immediately before "_", so lowercase prose/filenames
# (build_bank.py) never match. "°" is real corpus content (E°_cell, E°_red — standard-potential
# notation, ch12 เคมีไฟฟ้า). Checked for "'" (prime) and Greek letters in the same trailing-symbol
# position too — zero occurrences in the corpus, so they're deliberately not added here.
_SUB_RE = re.compile(r"(?<=[A-Z0-9\)\]°])_((?:[a-z0-9]+)|[A-Z])")
_SUP_RE = re.compile(r"\^([0-9+\-−]+)")
def supersub(t):
    if not t or ("_" not in t and "^" not in t): return t
    t = _SUB_RE.sub(r"<sub>\1</sub>", t)
    t = _SUP_RE.sub(r"<sup>\1</sup>", t)
    return t

# ---------- bare chemical formulas (NO ^ / _ marker at all: H2SO4, SO42-, Ca(OH)2) ----------
# The caret/underscore convention above only fires when the author explicitly marked one. Most
# formulas in the bank were never marked -- they're just plain "H2SO4" -- so this is a second,
# independent pass: recognize a formula by its SHAPE (real element symbols + digits + optional
# parens + optional trailing charge) and add the markup ourselves. Whitelist-gated: every symbol in
# a candidate token must be a real periodic-table symbol, or the WHOLE token is left untouched
# (a half-converted "Na<sub>3</sub>AO4" is worse than a plain "Na3AO4" -- see Na3AO4 in the bank,
# a genuine "element A" placeholder that must NOT be mistaken for real sodium-A-oxide).
_ELEMENTS = {
 "H","He","Li","Be","B","C","N","O","F","Ne","Na","Mg","Al","Si","P","S","Cl","Ar",
 "K","Ca","Sc","Ti","V","Cr","Mn","Fe","Co","Ni","Cu","Zn","Ga","Ge","As","Se","Br","Kr",
 "Rb","Sr","Y","Zr","Nb","Mo","Tc","Ru","Rh","Pd","Ag","Cd","In","Sn","Sb","Te","I","Xe",
 "Cs","Ba","La","Ce","Pr","Nd","Pm","Sm","Eu","Gd","Tb","Dy","Ho","Er","Tm","Yb","Lu",
 "Hf","Ta","W","Re","Os","Ir","Pt","Au","Hg","Tl","Pb","Bi","Po","At","Rn",
 "Fr","Ra","Ac","Th","Pa","U","Np","Pu","Am","Cm","Bk","Cf","Es","Fm","Md","No","Lr",
 "Rf","Db","Sg","Bh","Hs","Mt","Ds","Rg","Cn","Nh","Fl","Mc","Lv","Ts","Og",
}
_CHARGE_SIGNS = "+-−"
_ASCII_DIGITS = set("0123456789")  # NOT str.isdigit() -- that also matches ¹²³/₁₂₃, which must
                                   # never be touched (already-real Unicode super/subscript).

def _formula_element(text, i):
    """Try a 2-letter then 1-letter element symbol at i. Returns (symbol, end) or (None, i)."""
    if (i + 1 < len(text) and text[i].isupper() and text[i].isascii()
            and text[i+1].islower() and text[i+1].isascii()):
        two = text[i:i+2]
        if two in _ELEMENTS:
            return two, i + 2
    if text[i].isupper() and text[i].isascii() and text[i] in _ELEMENTS:
        return text[i], i + 1
    return None, i

def _formula_segment(text, i):
    """One element+digits, or a (...)digits group. Returns (pieces, end, has_digit) or None."""
    n = len(text)
    if i < n and text[i] == '(':
        body = _formula_body(text, i + 1)
        if body is None:
            return None
        pieces, j, has_digit = body
        if j >= n or text[j] != ')':
            return None
        j += 1
        k = j
        while k < n and text[k] in _ASCII_DIGITS: k += 1
        digits = text[j:k]
        out = [('lit', '(')] + pieces + [('lit', ')')]
        if digits: out.append(('sub', digits))
        return out, k, (has_digit or bool(digits))
    if i >= n:
        return None
    el, j = _formula_element(text, i)
    if el is None:
        return None
    k = j
    while k < n and text[k] in _ASCII_DIGITS: k += 1
    digits = text[j:k]
    out = [('lit', el)]
    if digits: out.append(('sub', digits))
    return out, k, bool(digits)

def _formula_body(text, i):
    """One-or-more segments back to back. Returns (pieces, end, has_digit), or None if zero segments."""
    pieces, has_digit, j, count = [], False, i, 0
    while True:
        r = _formula_segment(text, j)
        if r is None: break
        seg_pieces, k, seg_digit = r
        pieces.extend(seg_pieces)
        has_digit = has_digit or seg_digit
        j, count = k, count + 1
    return (pieces, j, has_digit) if count else None

def _try_bare_formula(text, i):
    """Parse+render a bare formula (+ optional trailing charge) starting at i.
    Returns (rendered_html, end_index) or None."""
    n = len(text)
    body = _formula_body(text, i)
    if body is None:
        return None
    pieces, j, has_digit = body
    # All-or-nothing: parsing stopped right at another letter/digit (e.g. the "A" in "Na3AO4" --
    # not a real element, so _formula_segment gave up, but the token clearly isn't finished) means
    # part of this candidate failed the whitelist. Reject the WHOLE token, don't half-convert it.
    if j < n and text[j].isascii() and (text[j].isalpha() or text[j] in _ASCII_DIGITS):
        return None
    seg_count = 0
    k = i
    while True:
        r = _formula_segment(text, k)
        if r is None: break
        _, k, _ = r
        seg_count += 1
    # A trailing digit run is always swallowed whole by _formula_body's own greedy consumption, so
    # the charge/subscript split (SO42- vs IO3- vs Mg2+) has to be resolved from the last piece
    # already produced, not by scanning further ahead.
    charge, end = None, j
    # A real charge is never followed by a digit (magnitude comes BEFORE the sign: "2-" not "-2");
    # element-hyphen-massnumber isotope labels (B-10, Co-60, I-131, Pb-206) look identical otherwise.
    is_isotope_hyphen = j < n and text[j] in _CHARGE_SIGNS and j+1 < n and text[j+1] in _ASCII_DIGITS
    # A "-"/"−" immediately followed by another valid element (Cl-Cl, H-Cl bond-energy notation;
    # N−C−C−N skeletal/Lewis-structure notation) is a BOND, not a charge -- real charges are always
    # terminal, never glued straight onto a second formula with no space ("+" isn't used this way).
    is_bond_hyphen = (j < n and text[j] in ('-', '−') and j+1 < n
                       and _formula_element(text, j+1)[0] is not None)
    # A "-" immediately followed by ">" is a bare reaction arrow ("->"), not a charge -- otherwise
    # the "-" gets eaten as a charge sign and only the ">" survives (e.g. "H2SO4->Al2(SO4)3").
    is_arrow_hyphen = j < n and text[j] == '-' and j+1 < n and text[j+1] == '>'
    if (j < n and text[j] in _CHARGE_SIGNS
            and not is_isotope_hyphen and not is_bond_hyphen and not is_arrow_hyphen):
        sign = text[j]
        last_sub = pieces[-1][1] if pieces and pieces[-1][0] == 'sub' else None
        if last_sub and seg_count == 1:
            # Lone single-element ion, e.g. Mg2+: the whole digit run IS the charge, no subscript.
            pieces = pieces[:-1]
            charge = (last_sub, sign)
        elif last_sub and len(last_sub) >= 2:
            # Multi-segment formula whose last digit run absorbed the charge digit too (SO42-):
            # last digit = charge magnitude, the rest stays as that segment's own subscript.
            pieces[-1] = ('sub', last_sub[:-1])
            charge = (last_sub[-1], sign)
        else:
            # Single digit (or none) right before the sign (IO3-, HSO4-, OH-): unambiguous -- that
            # digit is the subscript, and the charge is bare (magnitude 1).
            charge = ("", sign)
        end = j + 1
    html = "".join(f"<sub>{v}</sub>" if k == "sub" else v for k, v in pieces)
    if charge is not None:
        html += f"<sup>{charge[0]}{charge[1]}</sup>"
    if not has_digit and charge is None:
        return None  # nothing to actually render -> not worth touching
    return html, end

def bare_formulas(text):
    if not text:
        return text
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        can_start = c == '(' or (c.isupper() and c.isascii())
        prev_is_letter = i > 0 and text[i-1].isascii() and text[i-1].isalpha()
        if can_start and not prev_is_letter:
            r = _try_bare_formula(text, i)
            if r is not None:
                html, end = r
                out.append(html)
                i = end
                continue
        out.append(c)
        i += 1
    return "".join(out)

def chem_notation(t):
    """Full render-time chemistry pass: bare formulas first, then ^/_ marked notation."""
    return supersub(bare_formulas(t))

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
    # short snippet for list/two-pane rows: first non-empty body line, stripped of md.
    # Cut to 90 raw chars BEFORE running chem_notation()/strip, not after — converting first then
    # slicing can chop a generated <sup>/<sub> tag in half at the cut point.
    # (chem_notation() also runs before stripping *_` so the chem "_" markers become <sub> tags
    # first, not plain-stripped away along with genuine markdown emphasis chars)
    snip = ""
    for bl in body_lines:
        t = bl.strip()
        if t and not t.startswith(("-","*","#")):
            snip = re.sub(r"[*_`]","",chem_notation(t[:90])); break
    questions.append({
        "id": qid, "ch": ch, "chName": chName,
        "subject": subject, "bio": bio, "app": app, "groupKey": groupKey, "groupLabel": groupLabel,
        "exam": exam, "year": tag("year"), "ver": tag("ver"),
        "diff": tag("diff"), "type": tag("type"),
        "bodyHtml": markdown.markdown(chem_notation(body_md), extensions=["tables", "nl2br"]),
        "snippet": snip,
        "answer": meta.get("Answer",""), "source": meta.get("Source",""),
        "note": chem_notation(meta.get("Note","")), "figure": meta.get("Figure",""),
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
                "answer": chem_notation(" ".join(fields.get("Answer", [])).strip()),
                "conf":   " ".join(fields.get("Confidence", [])).strip(),
                "checked":" ".join(fields.get("Checked", [])).strip().lower(),
                "html":   markdown.markdown(chem_notation(body), extensions=["tables", "nl2br"]) if body else "",
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
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anuphan:wght@400;500;600;700;800&family=Sarabun:wght@400;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root{--paper:#efe9dc;--card:#fffdf7;--ink:#141414;--red:#e4412b;--blue:#1f3fbf;--yel:#f2b705;--mut:#6b6457;--line:#141414}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;font-family:"Anuphan","Sarabun","Segoe UI",Tahoma,sans-serif;background:var(--paper);color:var(--ink);font-size:16px}
button,select,input,textarea{font-family:inherit;color:inherit}
button{cursor:pointer}
/* ---------- kinetic background (B5) ---------- */
.kin{position:fixed;inset:0;pointer-events:none;z-index:0;overflow:hidden}
.kin i{position:absolute;display:block}
.kin .k1{width:460px;height:460px;border-radius:50%;background:var(--blue);right:-170px;top:90px;clip-path:polygon(0 0,100% 0,100% 50%,0 50%);animation:spin 46s linear infinite;opacity:.9}
.kin .k2{width:240px;height:240px;border:24px solid var(--ink);border-radius:50%;left:-80px;bottom:30px;animation:drift 20s ease-in-out infinite alternate;opacity:.85}
.kin .k3{width:170px;height:150px;background:var(--red);clip-path:polygon(50% 0,100% 100%,0 100%);left:4%;top:34%;animation:spin 32s linear infinite reverse;opacity:.85}
.kin .k4{width:280px;height:280px;right:6%;bottom:-70px;background:radial-gradient(var(--ink) 2px,transparent 2.5px) 0 0/18px 18px;animation:drift 24s ease-in-out infinite alternate-reverse;opacity:.5}
.kin .k5{width:120px;height:120px;background:var(--yel);right:30%;top:55%;animation:drift 28s ease-in-out infinite alternate;opacity:.9}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes drift{to{transform:translate(70px,-50px) rotate(25deg)}}
body.nobg .kin{display:none}
@media(prefers-reduced-motion:reduce){.kin i{animation:none!important}}
#landing,#app{position:relative;z-index:1}

/* ================= LANDING (B1 grid board) ================= */
#landing{min-height:100vh;padding:0 16px 60px}
.lwrap{max-width:1180px;margin:0 auto}
.lhead{display:flex;align-items:flex-end;gap:16px;flex-wrap:wrap;padding:26px 0 18px}
.lhead h1{margin:0;font-size:2.4rem;font-weight:800;line-height:1;letter-spacing:-.01em;display:flex;align-items:center;gap:12px}
.shapes{display:inline-flex;gap:6px;align-items:center}
.shapes i{display:inline-block;width:18px;height:18px}
.shapes .c{background:var(--red);border-radius:50%}.shapes .s{background:var(--yel)}.shapes .t{background:var(--blue);clip-path:polygon(50% 0,100% 100%,0 100%)}
.lhead p{margin:0 0 4px;color:var(--mut);font-size:.9rem}
.lhead .sp{flex:1}
.lbtn{border:3px solid var(--ink);background:var(--card);font-weight:700;padding:8px 14px;box-shadow:4px 4px 0 var(--ink);transition:transform .1s,box-shadow .1s;font-size:.88rem}
.lbtn:hover{transform:translate(-2px,-2px);box-shadow:6px 6px 0 var(--ink)}
.lbtn:active{transform:translate(4px,4px);box-shadow:0 0 0 var(--ink)}
.board{display:grid;grid-template-columns:repeat(6,1fr);grid-auto-rows:150px;grid-auto-flow:row;gap:6px;background:var(--ink);border:6px solid var(--ink)}
.tile{position:relative;border:0;padding:14px 16px;text-align:left;overflow:hidden;display:flex;flex-direction:column;gap:4px;background:var(--card);animation:tileIn .6s cubic-bezier(.3,1.4,.5,1) both;animation-delay:calc(var(--i,0)*45ms);transition:transform .25s}
@keyframes tileIn{from{opacity:0;transform:scale(.6) rotate(-6deg)}to{opacity:1;transform:none}}
button.tile:hover{transform:scale(.965)}
button.tile:after{content:"↗";position:absolute;right:12px;top:8px;font-size:1.25rem;font-weight:800;opacity:0;transform:translate(-6px,6px);transition:.25s}
button.tile:hover:after{opacity:1;transform:none}
.tile .no{font-size:2.8rem;font-weight:800;line-height:.95}
.tile .nm{font-weight:700;font-size:1rem;line-height:1.25}
.tile .ct{font-size:.78rem;opacity:.75;margin-top:auto}
.tile .cov{height:6px;background:rgba(0,0,0,.14);margin-top:5px;overflow:hidden}
.tile .cov i{display:block;height:100%;background:currentColor;opacity:.85}
.tile.w2{grid-column:span 2}.tile.h2{grid-row:span 2}
.tile.big .no{font-size:4.4rem}.tile.big .nm{font-size:1.3rem}
.c-red{background:var(--red);color:#fff}.c-yel{background:var(--yel)}.c-blue{background:var(--blue);color:#fff}.c-ink{background:var(--ink);color:var(--paper)}.c-card{background:var(--card)}
.hero{grid-column:span 2;grid-row:span 2;justify-content:flex-end;background:var(--card);cursor:default}
.hero b{font-size:4.6rem;font-weight:800;line-height:.9;color:var(--red)}
.hero span{font-size:1.5rem;font-weight:800;line-height:1.15}
.hero small{font-size:.8rem;color:var(--mut);margin-top:6px;line-height:1.5}
.deco1{background:radial-gradient(circle at 100% 100%,var(--blue) 0 58%,transparent 59%),var(--paper)}
.deco2{background:repeating-linear-gradient(45deg,var(--yel) 0 18px,var(--ink) 18px 36px)}
.deco3{background:radial-gradient(circle at 50% 50%,var(--red) 0 32%,transparent 33%),var(--card)}
.sec-t{grid-column:1/-1;background:var(--ink);color:var(--paper);font-weight:800;letter-spacing:.2em;font-size:.72rem;padding:6px 14px;display:flex;align-items:center;animation:none}
.board .sec-t{grid-row:span 1;height:auto}
.lfoot{margin-top:14px;font-size:.8rem;color:var(--mut)}
@media(max-width:900px){.board{grid-template-columns:repeat(4,1fr)}}
@media(max-width:560px){.board{grid-template-columns:repeat(2,1fr);grid-auto-rows:130px}.tile.w2,.hero{grid-column:span 2}.lhead h1{font-size:1.8rem}.tile.big .no{font-size:3.2rem}}

/* circle reveal between landing and app */
#app{display:none}
#app.show{display:block}
#app.opening{clip-path:circle(0 at var(--x,50%) var(--y,50%));animation:reveal .65s cubic-bezier(.7,0,.2,1) forwards}
@keyframes reveal{to{clip-path:circle(150% at var(--x,50%) var(--y,50%))}}
body.inapp #landing{display:none}

/* ================= APP HEADER ================= */
header{position:sticky;top:0;z-index:20;background:var(--ink);color:var(--paper)}
.bar1{display:flex;align-items:stretch;flex-wrap:wrap;max-width:1180px;margin:0 auto}
.home{border:0;background:var(--red);color:#fff;font-weight:800;padding:0 16px;font-size:.9rem;display:flex;align-items:center;gap:6px}
.home:hover{background:#c73621}
.title{font-weight:800;font-size:1.05rem;padding:12px 16px;display:flex;align-items:center;gap:8px;white-space:nowrap}
.title small{font-weight:400;opacity:.6;font-size:.75rem}
#q{flex:1;min-width:170px;background:var(--ink);border:0;border-left:3px solid var(--paper);color:var(--paper);padding:0 14px;font-size:.95rem;outline:none}
#q::placeholder{color:#8a8578}
#q:focus{background:#262626}
.hbtn{border:0;border-left:3px solid var(--paper);background:var(--ink);color:var(--paper);padding:0 14px;font-weight:700;font-size:.84rem;white-space:nowrap}
.hbtn:hover{background:#2a2a2a}
.hbtn.on{background:var(--yel);color:var(--ink)}
#ftoggle{display:none}
.bar2{background:var(--card);color:var(--ink);border-bottom:3px solid var(--ink)}
.bar2 .in{max-width:1180px;margin:0 auto;display:flex;align-items:center;gap:6px;flex-wrap:wrap;padding:8px 12px}
select{padding:6px 8px;border:2px solid var(--ink);background:var(--card);font-size:.84rem;font-weight:600;max-width:46vw;border-radius:0;cursor:pointer}
select:focus{outline:3px solid var(--yel);outline-offset:1px}
.seg{display:inline-flex;border:2px solid var(--ink)}
.seg button{border:0;border-right:2px solid var(--ink);background:var(--card);padding:6px 10px;font-size:.8rem;font-weight:700}
.seg button:last-child{border-right:0}
.seg button.on{background:var(--ink);color:var(--paper)}
.btn{padding:6px 11px;border:2px solid var(--ink);background:var(--card);font-size:.82rem;font-weight:700;box-shadow:3px 3px 0 var(--ink);transition:transform .08s,box-shadow .08s}
.btn:hover{transform:translate(-1px,-1px);box-shadow:4px 4px 0 var(--ink)}
.btn:active{transform:translate(3px,3px);box-shadow:0 0 0 var(--ink)}
#exportbtn{background:var(--yel)}
#exportbtn.none{opacity:.5}
#count{margin-left:auto;font-weight:700;font-size:.82rem;white-space:nowrap}
@media(max-width:760px){#ftoggle{display:block}.bar2{display:none}header.fopen .bar2{display:block}.title small{display:none}.title{padding:10px 12px}}

/* ================= MAIN / SHARED ================= */
main{max-width:1060px;margin:18px auto 60px;padding:0 14px}
.chap-h{margin:30px 0 14px;display:flex;align-items:stretch;border:3px solid var(--ink);background:var(--card);font-weight:800}
.chap-h b{background:var(--red);color:#fff;padding:6px 14px;font-size:1.2rem;border-right:3px solid var(--ink);min-width:58px;text-align:center}
.chap-h span{padding:8px 14px;font-size:1rem;display:flex;align-items:center}
.chap-h.bio b{background:var(--blue)}.chap-h.app b{background:var(--yel);color:var(--ink)}
.badge{font-size:.72rem;padding:2px 8px;font-weight:700;white-space:nowrap;display:inline-flex;align-items:center;gap:5px;border:2px solid var(--ink);background:var(--card)}
.b-id{background:var(--ink);color:var(--paper);font-family:"JetBrains Mono";font-size:.7rem}
.b-exam i{width:9px;height:9px;display:inline-block}
.b-ch{border-style:dashed}
.b-diff:before{content:"";display:inline-block;width:10px;height:10px}
.d-easy:before{background:var(--blue);border-radius:50%}
.d-medium:before{background:var(--yel)}
.d-hard:before{background:var(--red);clip-path:polygon(50% 0,100% 100%,0 100%)}
.b-type{opacity:.75}
.diff-txt{font-size:.72rem;font-weight:800;display:inline-flex;align-items:center;gap:4px;white-space:nowrap}
.diff-txt:before{content:"";display:inline-block;width:10px;height:10px}
.de-easy:before{background:var(--blue);border-radius:50%}.de-medium:before{background:var(--yel)}.de-hard:before{background:var(--red);clip-path:polygon(50% 0,100% 100%,0 100%)}
.body{font-size:1.02rem;line-height:1.8}
.body p{margin:.45em 0}
.body ul,.body ol{margin:.5em 0;padding-left:0;list-style:none}
.body li{padding:6px 12px;margin:4px 0;border:2px solid transparent;cursor:pointer;transition:background .15s,border-color .15s}
.body li:hover{background:#f6f0e2;border-color:#d8cfbb}
.body li.mk{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.body table{border-collapse:collapse;font-size:.92em;margin:.5em 0}
.body td,.body th,.solbody td,.solbody th{border:2px solid var(--ink);padding:3px 8px}
.fig{display:block;max-width:100%;height:auto;margin:12px auto;border:3px solid var(--ink);background:#fff;padding:6px}
.note{background:#fff4cc;border:2px solid var(--ink);padding:7px 11px;margin-top:10px;font-size:.86rem}
.foot{margin-top:12px;padding-top:9px;border-top:2px dashed #cfc5b0;font-size:.8rem;color:var(--mut);display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.present-btn{margin-left:auto;border:2px solid var(--ink);background:var(--card);padding:4px 11px;font-size:.8rem;font-weight:700;box-shadow:3px 3px 0 var(--ink)}
.present-btn:hover{background:var(--yel)}
code{background:#efe6d2;padding:1px 5px;font-size:.92em}
.empty{text-align:center;color:var(--mut);padding:60px 10px;font-weight:600}
/* ---------- solutions ---------- */
.solbtn{margin-top:12px;border:2px solid var(--ink);background:var(--card);padding:6px 14px;font-size:.84rem;font-weight:800;box-shadow:3px 3px 0 var(--ink);transition:transform .08s,box-shadow .08s}
.solbtn:hover{background:var(--yel)}
.solbtn:active{transform:translate(3px,3px);box-shadow:none}
.solbtn.flag{border-style:dashed}
.solbtn.done{background:#e3f1dc}
.solbtn.wrong{background:#fbe0da}
.solwrap{display:grid;grid-template-rows:0fr;transition:grid-template-rows .45s cubic-bezier(.2,.8,.2,1);overflow:hidden}
.solwrap>.solin{min-height:0;overflow:hidden;visibility:hidden;transition:visibility 0s .45s}
.solwrap.show{grid-template-rows:1fr}
.solwrap.show>.solin{visibility:visible;transition:none}
.solbox{margin-top:12px;border:3px solid var(--ink);background:var(--card);padding:12px 16px;position:relative}
.solbox:before{content:"";position:absolute;left:-3px;top:-3px;bottom:-3px;width:10px;background:var(--blue)}
.solbox{padding-left:22px}
.flag .solbox:before{background:var(--yel)}
.soldis{font-size:.78rem;background:#fff4cc;border:2px solid var(--ink);padding:5px 9px;margin-bottom:9px}
.solans{font-weight:800;margin-bottom:6px;font-size:1rem}
.chk{display:inline-block;font-size:.72rem;font-weight:700;background:#e3f1dc;border:2px solid var(--ink);padding:0 7px;margin-bottom:6px}
.solbody{font-size:.94rem;line-height:1.8}
.solbody p{margin:.4em 0}
.solbody table{border-collapse:collapse;font-size:.9em;margin:.5em 0}
.solbody hr{border:0;border-top:2px dashed #cfc5b0;margin:.7em 0}
.revbar{margin-top:12px;padding-top:10px;border-top:2px dashed #cfc5b0;display:flex;gap:7px;flex-wrap:wrap;align-items:center;font-size:.8rem;color:var(--mut)}
.revbtn{border:2px solid var(--ink);background:var(--card);padding:4px 12px;font-size:.8rem;font-weight:700;color:var(--ink)}
.revbtn.ok.on{background:#2f8f4e;border-color:#2f8f4e;color:#fff}
.revbtn.bad.on{background:var(--red);border-color:var(--red);color:#fff}
.revnote{flex:1 1 100%;margin-top:6px;border:2px solid var(--ink);padding:7px 10px;font-size:.84rem;min-height:54px;resize:vertical;display:none;background:#fff}
.revnote.show{display:block}
.revmark{font-size:.82rem;font-weight:700;color:var(--ink)}

/* ---------- POSTER view (B3) ---------- */
.deckbar{display:flex;align-items:center;gap:10px;margin:6px 0 18px;flex-wrap:wrap}
.deckbar>*:not(.deckhint){flex-shrink:0}
.deckbar #pscrub{flex:1 1 60px}
@media(max-width:640px){.deckhint{display:none}.dbtn{width:42px;height:40px}#ppos{min-width:70px;font-size:.8rem}}
.dbtn{border:3px solid var(--ink);background:var(--card);font-weight:800;font-size:1.1rem;width:48px;height:44px;box-shadow:4px 4px 0 var(--ink);transition:transform .08s,box-shadow .08s}
.dbtn:hover{background:var(--yel)}
.dbtn:active{transform:translate(4px,4px);box-shadow:none}
#pscrub{flex:1;min-width:60px;accent-color:var(--red);height:6px;cursor:pointer}
#ppos{font-family:"JetBrains Mono";font-weight:700;font-size:.9rem;min-width:96px;text-align:center}
.deckhint{font-size:.74rem;color:var(--mut);width:100%}
.deck{position:relative}
.deck:before,.deck:after{content:"";position:absolute;inset:0;background:var(--card);border:3px solid var(--ink);z-index:0}
.deck:before{transform:rotate(1.8deg) translate(8px,8px)}
.deck:after{transform:rotate(-1.2deg) translate(-6px,6px)}
.poster{position:relative;z-index:2;background:var(--card);border:3px solid var(--ink);padding:26px 30px 22px 40px;overflow:hidden;min-height:420px}
.poster:before{content:"";position:absolute;width:320px;height:320px;border-radius:50%;background:var(--blue);right:-150px;bottom:-170px;opacity:.95;z-index:0}
.poster:after{content:"";position:absolute;left:0;top:0;width:14px;height:100%;background:var(--red);z-index:0}
.poster>*{position:relative;z-index:1}
.poster .pnum{position:absolute;right:20px;top:4px;font-size:7rem;font-weight:800;line-height:1;color:transparent;-webkit-text-stroke:3px var(--red);z-index:0;pointer-events:none;font-family:"Anuphan"}
.poster .pnum.l4{font-size:4.8rem;top:10px}
.poster .phead{font-size:.72rem;font-weight:800;letter-spacing:.14em;border-bottom:3px solid var(--ink);padding-bottom:8px;margin-bottom:12px;max-width:66%}
.poster .pmeta{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px;max-width:70%}
.poster .body{max-width:88%}
.poster .body{font-size:1.08rem}
.poster.inR{animation:pInR .38s cubic-bezier(.2,1.1,.4,1)}.poster.inL{animation:pInL .38s cubic-bezier(.2,1.1,.4,1)}
.poster.enter{animation:pIn .5s cubic-bezier(.2,1.2,.4,1)}
@keyframes pIn{from{opacity:0;transform:translateY(34px) rotate(2deg) scale(.97)}}
@keyframes pInR{from{opacity:0;transform:translateX(60px) rotate(2deg)}}
@keyframes pInL{from{opacity:0;transform:translateX(-60px) rotate(-2deg)}}
.poster.outL{animation:pOutL .2s ease-in forwards}.poster.outR{animation:pOutR .2s ease-in forwards}
@keyframes pOutL{to{opacity:0;transform:translateX(-90%) rotate(-10deg)}}
@keyframes pOutR{to{opacity:0;transform:translateX(90%) rotate(10deg)}}
.poster .solbox{max-width:88%}

/* ---------- CARDS view (mini posters) ---------- */
.card{position:relative;background:var(--card);border:3px solid var(--ink);box-shadow:7px 7px 0 var(--ink);padding:18px 20px 16px 32px;margin-bottom:22px;overflow:hidden}
.card.anim{animation:cardIn .5s cubic-bezier(.2,1.1,.4,1) both;animation-delay:calc(var(--i,0)*50ms)}
@keyframes cardIn{from{opacity:0;transform:translateY(20px)}}
.card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:10px;background:var(--red)}
.card.lv-medium:before{background:var(--yel)}.card.lv-easy:before{background:var(--blue)}
.card .cnum{position:absolute;right:14px;top:0;font-size:3.6rem;font-weight:800;color:transparent;-webkit-text-stroke:2px #e1d8c4;line-height:1;pointer-events:none}
.card-top{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:10px;position:relative;padding-right:70px}
/* ---------- LIST view ---------- */
.row{background:var(--card);border:3px solid var(--ink);margin-bottom:8px;overflow:hidden;transition:box-shadow .15s,transform .15s}
.row:hover{box-shadow:5px 5px 0 var(--ink);transform:translate(-2px,-2px)}
.row-h{display:flex;align-items:center;gap:10px;padding:10px 14px;cursor:pointer}
.row-id{font-family:"JetBrains Mono";font-weight:700;font-size:.8rem;white-space:nowrap}
.row-snip{flex:1;font-size:.93rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.row-body{padding:0 18px 16px;display:none;border-top:2px dashed #cfc5b0}
.row.open .row-body{display:block}
.chev{font-weight:800;transition:transform .15s}
.row.open .chev{transform:rotate(90deg)}
.row .badge{font-size:.66rem}
/* ---------- PANE view ---------- */
.pane{display:grid;grid-template-columns:340px 1fr;gap:16px;align-items:start}
.pane-list{max-height:calc(100vh - 170px);overflow:auto;border:3px solid var(--ink);background:var(--card);position:sticky;top:130px}
.pane-item{display:flex;gap:8px;align-items:center;padding:10px 12px;border-bottom:2px solid #e3dac6;cursor:pointer}
.pane-item:hover{background:#f6f0e2}
.pane-item.sel{background:var(--ink);color:var(--paper)}
.pane-detail{position:sticky;top:130px}
.pane-detail .poster{min-height:300px}
@media(max-width:820px){.pane{grid-template-columns:1fr}.pane-detail{display:none}.pane-list{position:static;max-height:none}}

/* ---------- PRESENT modal (full-screen poster) ---------- */
.modal{position:fixed;inset:0;z-index:50;background:rgba(20,20,20,.72);display:none;align-items:center;justify-content:center;padding:18px}
.modal.show{display:flex}
.sheet{background:var(--card);border:4px solid var(--ink);box-shadow:12px 12px 0 var(--red);max-width:960px;width:100%;max-height:92vh;overflow:auto;padding:30px 34px 26px 44px;position:relative;animation:pIn .4s cubic-bezier(.2,1.2,.4,1)}
.sheet:before{content:"";position:absolute;left:0;top:0;bottom:0;width:16px;background:var(--red)}
.sheet .mtop{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:16px;padding-right:50px}
.sheet .body{font-size:1.38rem;line-height:1.85}
.sheet .body li{padding:9px 14px;font-size:1.02em}
.sheet .fig{max-height:52vh;width:auto}
.sheet .solbody{font-size:1.05rem}
.x{position:absolute;top:14px;right:16px;border:3px solid var(--ink);background:var(--ink);color:var(--paper);width:42px;height:42px;font-size:1.1rem;font-weight:800}
.mctrl{display:flex;gap:10px;align-items:center;margin-top:20px;flex-wrap:wrap}
.mctrl button{padding:10px 18px;border:3px solid var(--ink);background:var(--card);font-size:1rem;font-weight:800;box-shadow:4px 4px 0 var(--ink)}
.mctrl button:active{transform:translate(4px,4px);box-shadow:none}
.reveal{background:var(--blue)!important;color:#fff}
.ans-box{margin-top:16px;padding:12px 18px;background:#fff4cc;border:3px solid var(--ink);font-size:1.1rem;display:none}
.ans-box.show{display:block}
.mpos{margin-left:auto;font-family:"JetBrains Mono";font-weight:700}
/* ---------- export modal ---------- */
.expwrap{position:fixed;inset:0;background:rgba(20,20,20,.6);z-index:60;display:none;align-items:center;justify-content:center;padding:18px}
.expwrap.show{display:flex}
.expbox{background:var(--card);border:4px solid var(--ink);box-shadow:10px 10px 0 var(--yel);padding:20px;max-width:640px;width:100%;max-height:86vh;display:flex;flex-direction:column;gap:11px}
.expbox h3{margin:0;font-size:1.1rem}
.expbox p{margin:0;font-size:.84rem;color:var(--mut);line-height:1.6}
.expbox textarea{width:100%;flex:1;min-height:190px;font-family:"JetBrains Mono",monospace;font-size:.74rem;border:2px solid var(--ink);padding:10px;resize:vertical;background:#fff}
.exprow{display:flex;gap:8px;flex-wrap:wrap}
.exprow button{border:2px solid var(--ink);background:var(--card);padding:7px 13px;font-size:.84rem;font-weight:700;box-shadow:3px 3px 0 var(--ink)}
.exprow button.pri{background:var(--ink);color:var(--paper)}
.exprow button.dan{color:var(--red)}
@media(max-width:640px){.poster{padding:20px 16px 18px 26px}.poster .pnum{font-size:4.2rem}.poster .body,.poster .solbox{max-width:100%}.poster .phead,.poster .pmeta{max-width:78%}.sheet{padding:22px 16px 18px 28px}.sheet .body{font-size:1.15rem}}
</style></head><body>
<div class="kin" aria-hidden="true"><i class="k1"></i><i class="k2"></i><i class="k3"></i><i class="k4"></i><i class="k5"></i></div>

<!-- ================= LANDING ================= -->
<section id="landing"><div class="lwrap">
  <div class="lhead"><h1><span class="shapes"><i class="c"></i><i class="s"></i><i class="t"></i></span>คลังข้อสอบเคมี</h1>
    <p id="lsub"></p><span class="sp"></span>
    <button class="lbtn sfxbtn" id="lsfx">🔊</button>
    <button class="lbtn" id="lbg" title="เปิด/ปิดพื้นหลังเคลื่อนไหว">◐ พื้นหลัง</button></div>
  <div class="board" id="board"></div>
  <div class="lfoot">แตะบล็อกเพื่อเข้าบทนั้น · แถบใต้แต่ละบล็อก = สัดส่วนข้อที่มีวิธีทำ</div>
</div></section>

<!-- ================= APP ================= -->
<div id="app">
<header id="hdr">
 <div class="bar1">
   <button class="home" id="home" title="กลับไปเลือกบท">⌂ <span>เลือกบท</span></button>
   <span class="title"><span class="shapes"><i class="c"></i><i class="s"></i><i class="t"></i></span>คลังข้อสอบเคมี <small>Chem Question Bank</small></span>
   <input id="q" placeholder="ค้นหาข้อความ / สูตร / Q-id…  ( / )">
   <button class="hbtn" id="random">🎲 สุ่ม</button>
   <button class="hbtn" id="ftoggle">ตัวกรอง ▾</button>
 </div>
 <div class="bar2"><div class="in">
   <select id="fsubj"></select>
   <select id="fch"></select>
   <select id="fexam"></select>
   <select id="fyear"></select>
   <select id="fdiff"></select>
   <select id="ftype"></select>
   <select id="fsol"></select>
   <span class="seg" id="layout">
     <button data-v="poster">โปสเตอร์</button>
     <button data-v="cards">การ์ด</button>
     <button data-v="list">รายการ</button>
     <button data-v="pane">2 คอลัมน์</button>
   </span>
   <button class="btn" id="exportbtn" style="display:none">📥 ผลตรวจ</button>
   <button class="btn" id="bgbtn" title="เปิด/ปิดพื้นหลังเคลื่อนไหว">◐</button>
   <button class="btn sfxbtn" id="sfxbtn">🔊</button>
   <span id="count"></span>
 </div></div>
</header>
<main id="root"></main>
</div>

<div class="modal" id="modal"><div class="sheet">
  <button class="x" id="mx">✕</button>
  <div class="mtop" id="mtop"></div>
  <div class="body" id="mbody"></div>
  <div class="note" id="mnote" style="display:none"></div>
  <div class="ans-box" id="mans"></div>
  <div id="msol"></div>
  <div class="mctrl">
    <button id="mreveal" class="reveal">เฉลย / หมายเหตุ</button>
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
// chapter keys "10".."14" are integer-like, so JS object order puts them BEFORE "01".."09" -- sort explicitly
const CHS=Object.entries(DATA.chapters).sort((a,b)=>parseInt(a[0])-parseInt(b[0]));
const ls={get:(k,d)=>{try{const v=localStorage.getItem(k);return v===null?d:v;}catch(e){return d;}},set:(k,v)=>{try{localStorage.setItem(k,v);}catch(e){}},del:k=>{try{localStorage.removeItem(k);}catch(e){}}};
let view = ls.get("cqb_view","poster");
if(!["poster","cards","list","pane"].includes(view)) view="poster";
let filtered = [], pIdx = 0;
const hasSol=q=>!!(q.solHtml||q.solAnswer);

/* ---------- sound fx: synthesized with Web Audio (no files to host), muteable, remembered ---------- */
const SFX=(()=>{let ctx=null,on=ls.get("cqb_sfx","1")!=="0";
  function ac(){if(!ctx){const A=window.AudioContext||window.webkitAudioContext;if(!A)return null;ctx=new A();}
    if(ctx.state==="suspended")ctx.resume();return ctx;}
  function tone(f,dur,o={}){const c=ac();if(!c)return;const t=c.currentTime+(o.delay||0),os=c.createOscillator(),g=c.createGain();
    os.type=o.type||"sine";os.frequency.setValueAtTime(f,t);if(o.slide)os.frequency.exponentialRampToValueAtTime(Math.max(30,f*o.slide),t+dur);
    g.gain.setValueAtTime(0.0001,t);g.gain.linearRampToValueAtTime(o.vol||.12,t+(o.attack||.006));g.gain.exponentialRampToValueAtTime(.0001,t+dur);
    os.connect(g).connect(c.destination);os.start(t);os.stop(t+dur+.03);}
  function noise(dur,o={}){const c=ac();if(!c)return;const t=c.currentTime+(o.delay||0),n=Math.max(1,Math.floor(c.sampleRate*dur)),
    b=c.createBuffer(1,n,c.sampleRate),d=b.getChannelData(0);for(let i=0;i<n;i++)d[i]=Math.random()*2-1;
    const src=c.createBufferSource();src.buffer=b;const f=c.createBiquadFilter();f.type=o.type||"bandpass";
    f.frequency.setValueAtTime(o.freq||1800,t);if(o.sweep)f.frequency.exponentialRampToValueAtTime((o.freq||1800)*o.sweep,t+dur);f.Q.value=o.q||.8;
    const g=c.createGain();g.gain.setValueAtTime(o.vol||.1,t);g.gain.exponentialRampToValueAtTime(.0001,t+dur);
    src.connect(f).connect(g).connect(c.destination);src.start(t);src.stop(t+dur+.03);}
  const P={
    click:()=>tone(1400,.04,{type:"square",vol:.035}),
    tile:()=>{tone(523,.09,{type:"triangle",vol:.14});tone(784,.13,{type:"triangle",vol:.11,delay:.055});},
    whoosh:()=>noise(.55,{vol:.13,freq:350,sweep:7,q:.7}),
    swish:d=>{noise(.2,{vol:.13,freq:d>0?800:2800,sweep:d>0?3.5:.3,q:1.1});tone(d>0?196:247,.07,{vol:.05,delay:.03});},
    open:()=>tone(440,.13,{vol:.12,slide:1.7}),
    close:()=>tone(720,.11,{vol:.09,slide:.55}),
    ok:()=>{tone(784,.14,{type:"triangle",vol:.13});tone(1175,.24,{type:"triangle",vol:.12,delay:.085});},
    bad:()=>{tone(185,.24,{type:"sawtooth",vol:.06,slide:.65});noise(.14,{vol:.08,freq:260,type:"lowpass"});},
    mark:()=>{noise(.045,{vol:.07,freq:5200,q:2});tone(1050,.05,{type:"triangle",vol:.07});},
    unmark:()=>tone(620,.05,{type:"triangle",vol:.05}),
    dice:()=>{for(let i=0;i<6;i++)noise(.035,{vol:.13,freq:1500+Math.random()*1800,q:3,delay:i*.055});tone(659,.18,{type:"triangle",vol:.1,delay:.37});tone(988,.22,{type:"triangle",vol:.08,delay:.43});},
    present:()=>{tone(392,.1,{type:"triangle",vol:.1});tone(587,.18,{type:"triangle",vol:.1,delay:.07});},
    home:()=>{noise(.38,{vol:.1,freq:2600,sweep:.18,q:.7});tone(620,.13,{vol:.07,slide:.6});},
    toggle:()=>{tone(880,.045,{type:"square",vol:.03});tone(1320,.05,{type:"square",vol:.03,delay:.05});},
    tick:()=>tone(1900,.018,{type:"square",vol:.018})
  };
  let lastTick=0;
  return {play(k,a){if(!on)return;if(k==="tick"){const n=Date.now();if(n-lastTick<45)return;lastTick=n;}try{P[k]&&P[k](a);}catch(e){}},
          get on(){return on;},set(v){on=v;ls.set("cqb_sfx",v?"1":"0");}};
})();
function syncSfxBtns(){document.querySelectorAll(".sfxbtn").forEach(b=>{b.textContent=SFX.on?"🔊":"🔇";b.title=SFX.on?"ปิดเสียง (M)":"เปิดเสียง (M)";});}
function toggleSfx(){SFX.set(!SFX.on);syncSfxBtns();SFX.play("toggle");}
document.querySelectorAll(".sfxbtn").forEach(b=>b.onclick=toggleSfx);
syncSfxBtns();

/* ---------- background toggle ---------- */
function setBg(on){document.body.classList.toggle("nobg",!on);ls.set("cqb_bg",on?"1":"0");}
setBg(ls.get("cqb_bg","1")!=="0");
$("#lbg").onclick=$("#bgbtn").onclick=()=>{setBg(document.body.classList.contains("nobg"));SFX.play("toggle");};

/* ---------- filters ---------- */
function opt(sel,val,label){const o=document.createElement("option");o.value=val;o.textContent=label;sel.appendChild(o);}
opt($("#fsubj"),"",`ทุกวิชา (${DATA.questions.length})`);
if(DATA.chemcount)opt($("#fsubj"),"chem",`เคมี (${DATA.chemcount})`);
if(DATA.biocount)opt($("#fsubj"),"bio",`ชีววิทยา (${DATA.biocount})`);
if(DATA.appcount)opt($("#fsubj"),"applied",`เคมีประยุกต์ (${DATA.appcount})`);
function populateChapters(subj){
  const sel=$("#fch"); sel.innerHTML="";
  if(subj==="bio"){
    opt(sel,"","ทุกหัวข้อ");
    for(const[n,name]of Object.entries(DATA.bioChapters)){const c=DATA.biocounts[n]||0;if(c)opt(sel,n,`${n}. ${name} (${c})`);}
  }else if(subj==="applied"){
    opt(sel,"","ทุกหัวข้อ");
    for(const[k,name]of Object.entries(DATA.appTopics)){const c=DATA.appcounts[k]||0;if(c)opt(sel,k,`${name} (${c})`);}
    for(const k of Object.keys(DATA.appcounts)){if(!DATA.appTopics[k])opt(sel,k,`${k} (${DATA.appcounts[k]})`);}
  }else{
    opt(sel,"","ทุกบท");
    for(const[n,name]of CHS){const c=DATA.counts[n]||0;if(c)opt(sel,n,`${parseInt(n)}. ${name} (${c})`);}
  }
}
populateChapters("");
opt($("#fexam"),"","ทุกสนามสอบ");
for(const[k,c]of Object.entries(DATA.examcount||{})){const e=DATA.exams[k]||{label:k};opt($("#fexam"),k,`${e.label} (${c})`);}
opt($("#fyear"),"","ทุกปี");DATA.years.forEach(y=>opt($("#fyear"),y,"ปี "+y));
opt($("#fdiff"),"","ทุกระดับ");["easy","medium","hard"].forEach(d=>opt($("#fdiff"),d,DIFF_TH[d]));
opt($("#ftype"),"","ทุกชนิด");DATA.types.forEach(t=>opt($("#ftype"),t,t));
const SC=DATA.solcount||{have:0,flag:0,unchecked:0};
opt($("#fsol"),"","วิธีทำ: ทั้งหมด");
if(SC.have){
  opt($("#fsol"),"has",`มีวิธีทำ (${SC.have})`);
  opt($("#fsol"),"none",`ยังไม่มีวิธีทำ (${DATA.questions.length-SC.have})`);
  if(SC.flag)      opt($("#fsol"),"flag",`⚠ ไม่ฟันธง (${SC.flag})`);
  if(SC.unchecked) opt($("#fsol"),"unchecked",`ยังไม่ตรวจ (${SC.unchecked})`);
  const done=SC.have-SC.unchecked;
  if(done)         opt($("#fsol"),"checked",`ตรวจแล้ว (${done})`);
}

/* ---------- badges ---------- */
function examBadge(q){const e=DATA.exams[q.exam]||{label:q.exam.toUpperCase(),color:"#64748b"};
  return `<span class="badge b-exam"><i style="background:${e.color}"></i>${e.label} ${q.year}</span>`;}
function diffBadge(q){return q.diff?`<span class="badge b-diff d-${q.diff}">${DIFF_TH[q.diff]||q.diff}</span>`:"";}
function idBadge(q){return `<span class="badge b-id">${q.id}</span>`;}
function typeBadge(q){return q.type?`<span class="badge b-type">${q.type}</span>`:"";}
function chBadge(q){
  if(q.subject==="bio") return `<span class="badge b-ch">ชีววิทยา ${q.bio}. ${q.chName}</span>`;
  if(q.subject==="applied") return `<span class="badge b-ch">ประยุกต์ · ${q.chName}</span>`;
  return `<span class="badge b-ch">บท ${parseInt(q.ch)}. ${q.chName}</span>`;}
const NOKEY=/no key/i;
function keyTxt(q){return (q.answer&&!NOKEY.test(q.answer))?q.answer:"";}
function footHtml(q){const k=keyTxt(q);return `📄 ${q.source}${k?` &nbsp;·&nbsp; เฉลยทางการ: ${k}`:""}`;}
function figHtml(q){return q.figure?`<img class="fig" src="${q.figure}" alt="${q.id} figure" loading="lazy">`:"";}
function noteHtml(q){return q.note?`<div class="note">📌 ${q.note}</div>`:"";}
const qnum=q=>parseInt(q.id.slice(2),10);
function chapH(q){const cls=q.subject==="bio"?" bio":q.subject==="applied"?" app":"";
  const n=q.subject==="bio"?(q.bio.split(".")[0]||"?"):q.subject==="applied"?"✦":(q.ch?parseInt(q.ch):"?");
  const nm=q.groupLabel.replace(/^บทที่ \d+ · /,"");
  return `<div class="chap-h${cls}"><b>${n}</b><span>${nm}</span></div>`;}

/* ---- review marks: persist in localStorage, exported as JSON for tools/apply_review.py ---- */
let REV = {};
try{ REV = JSON.parse(ls.get("cqb_review","{}")) || {}; }catch(e){ REV = {}; }
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
function solLabel(q){const r=REV[q.id]||{};
  return r.v==="ok" ? "✅ ดูวิธีทำ (ตรวจแล้ว)" : r.v==="bad" ? "❌ ดูวิธีทำ (ผิด / ต้องแก้)" : q.solFlag ? "⚠ ดูวิธีทำ (ไม่ฟันธง)" : "ดูวิธีทำ →";}
/* Solution block — ALWAYS collapsed on render (attempt before seeing the working). */
function solHtml(q){
  if(!hasSol(q)) return "";
  const r = REV[q.id] || {};
  const f = (q.solFlag ? " flag" : "") + (r.v==="ok" ? " done" : r.v==="bad" ? " wrong" : "");
  const label = solLabel(q);
  return `<button class="solbtn${f}" data-sol="1" data-label="${label}">${label}</button>
    <div class="solwrap${f}"><div class="solin"><div class="solbox">
      ${q.solFlag?`<div class="soldis">⚠ ข้อนี้ไม่ฟันธง — โจทย์กำกวมหรือตัวเลือกไม่ตรง อ่านเหตุผลในวิธีทำแล้วตัดสินเอง</div>`:""}
      ${q.solChecked?`<span class="chk">✅ ตรวจแล้ว</span>`:""}
      ${q.solAnswer?`<div class="solans">ตอบ: ${q.solAnswer}</div>`:""}
      <div class="solbody">${q.solHtml}</div>
      ${revBar(q)}
    </div></div></div>`;
}

function apply(keepPos){
  const t=$("#q").value.trim().toLowerCase(),subj=$("#fsubj").value,ch=$("#fch").value,
        ex=$("#fexam").value,yr=$("#fyear").value,df=$("#fdiff").value,tp=$("#ftype").value,
        sl=$("#fsol").value;
  filtered=DATA.questions.filter(x=>{
    if(subj==="chem" && (x.subject==="bio"||x.subject==="applied")) return false;
    if(subj==="bio" && x.subject!=="bio") return false;
    if(subj==="applied" && x.subject!=="applied") return false;
    if(ch){
      if(subj==="bio"){ if((x.bio.split(".")[0]||"?")!==ch) return false; }
      else if(subj==="applied"){ if(x.app!==ch) return false; }
      else if(x.ch!==ch) return false;
    }
    if(ex && x.exam!==ex) return false;
    if(yr && x.year!==yr) return false;
    if(df && x.diff!==df) return false;
    if(tp && x.type!==tp) return false;
    const hs = hasSol(x);
    if(sl==="has"       && !hs) return false;
    if(sl==="none"      &&  hs) return false;
    if(sl==="flag"      && !(hs && x.solFlag)) return false;
    if(sl==="unchecked" && !(hs && !x.solChecked)) return false;
    if(sl==="checked"   && !(hs && x.solChecked)) return false;
    if(t && !(x.search.includes(t)||x.id.toLowerCase().includes(t))) return false;
    return true;
  });
  if(!keepPos) pIdx=0;
  $("#count").textContent=`${filtered.length} / ${DATA.questions.length} ข้อ`;
  render();
}

function render(){
  const R=$("#root");
  if(!filtered.length){R.innerHTML='<div class="empty">ไม่พบข้อสอบที่ตรงกับเงื่อนไข</div>';return;}
  if(view==="poster") renderPoster(R);
  else if(view==="cards") renderCards(R);
  else if(view==="list") renderList(R);
  else renderPane(R);
}
/* ---- POSTER (one question at a time, deck) ---- */
function posterHtml(q,i,anim){return `<article class="poster ${anim||""}" data-i="${i}">
   <div class="pnum${qnum(q)>999?" l4":""}">${qnum(q)}</div>
   <div class="phead">${q.groupLabel}</div>
   <div class="pmeta">${idBadge(q)}${examBadge(q)}${diffBadge(q)}${typeBadge(q)}</div>
   <div class="body">${q.bodyHtml}${figHtml(q)}</div>${noteHtml(q)}
   ${solHtml(q)}
   <div class="foot">${footHtml(q)}<button class="present-btn" data-i="${i}">⤢ แสดงให้นักเรียน</button></div></article>`;}
function renderPoster(R){
  if(pIdx>=filtered.length) pIdx=0;
  R.innerHTML=`<div class="deckbar"><button class="dbtn" id="pprev" title="ก่อนหน้า (←)">←</button>
    <input type="range" id="pscrub" min="1" max="${filtered.length}" value="${pIdx+1}" aria-label="เลื่อนไปข้อ">
    <span id="ppos"></span><button class="dbtn" id="pnext" title="ถัดไป (→)">→</button>
    <span class="deckhint">← → เปลี่ยนข้อ · Enter เปิดวิธีทำ · ลากแถบเพื่อกระโดด · แตะตัวเลือกเพื่อวงไว้</span></div>
    <div class="deck" id="deck"></div>`;
  fillPoster("enter");
}
function fillPoster(anim){
  const q=filtered[pIdx];if(!q)return;
  $("#deck").innerHTML=posterHtml(q,pIdx,anim);
  $("#ppos").textContent=`${pIdx+1} / ${filtered.length}`;
  $("#pscrub").value=pIdx+1;
}
let pBusy=false;
function pstep(d){
  if(view!=="poster"||!filtered.length||pBusy) return;
  const p=$("#deck .poster");pBusy=true;
  if(p) p.classList.add(d>0?"outL":"outR");
  SFX.play("swish",d);
  setTimeout(()=>{pIdx=(pIdx+d+filtered.length)%filtered.length;fillPoster(d>0?"inR":"inL");pBusy=false;},180);
}
/* ---- CARDS ---- */
function cardHtml(q,idx){return `<div class="card lv-${q.diff}${idx<12?" anim":""}" style="--i:${idx}">
   <span class="cnum">${qnum(q)}</span>
   <div class="card-top">${idBadge(q)}${chBadge(q)}${examBadge(q)}${diffBadge(q)}${typeBadge(q)}
     <button class="present-btn" data-i="${idx}">⤢ แสดง</button></div>
   <div class="body">${q.bodyHtml}${figHtml(q)}</div>${noteHtml(q)}
   ${solHtml(q)}
   <div class="foot">${footHtml(q)}</div></div>`;}
function renderCards(R){
  let html="",lastG=null;
  filtered.forEach((q,i)=>{
    if(q.groupKey!==lastG){lastG=q.groupKey;html+=chapH(q);}
    html+=cardHtml(q,i);
  });
  R.innerHTML=html;
}
/* ---- LIST (accordion) ---- */
function renderList(R){
  let html="",lastG=null;
  filtered.forEach((q,i)=>{
    if(q.groupKey!==lastG){lastG=q.groupKey;html+=chapH(q);}
    html+=`<div class="row" data-i="${i}">
      <div class="row-h"><span class="chev">▸</span><span class="row-id">${q.id}</span>
        <span class="diff-txt de-${q.diff}">${DIFF_TH[q.diff]||""}</span>
        <span class="row-snip">${q.snippet||""}</span>${examBadge(q)}</div>
      <div class="row-body"><div class="body">${q.bodyHtml}${figHtml(q)}</div>${noteHtml(q)}
        ${solHtml(q)}
        <div class="foot">${footHtml(q)}
        <button class="present-btn" data-i="${i}">⤢ แสดงให้นักเรียน</button></div></div></div>`;
  });
  R.innerHTML=html;
}
/* ---- PANE (list + poster detail) ---- */
function renderPane(R){
  let items=filtered.map((q,i)=>`<div class="pane-item" data-i="${i}">
     <span class="row-id">${q.id}</span><span class="diff-txt de-${q.diff}">${DIFF_TH[q.diff]||""}</span>
     <span class="row-snip">${q.snippet||""}</span></div>`).join("");
  R.innerHTML=`<div class="pane"><div class="pane-list">${items}</div>
     <div class="pane-detail" id="detail"><div class="empty">เลือกข้อทางซ้ายเพื่อดูรายละเอียด</div></div></div>`;
  if(window.innerWidth>820) paneShow(0);
}
function paneShow(i){
  if(window.innerWidth<=820){openModal(i);return;}
  document.querySelectorAll(".pane-item").forEach(el=>el.classList.toggle("sel",el.dataset.i==i));
  $("#detail").innerHTML=posterHtml(filtered[i],i,"enter");
}

/* ---- present modal ---- */
let mIdx=0;
function openModal(i){mIdx=i;fillModal();$("#modal").classList.add("show");SFX.play("present");}
function closeModal(){if(!$("#modal").classList.contains("show"))return;$("#modal").classList.remove("show");SFX.play("close");}
function fillModal(){
  const q=filtered[mIdx];
  $("#mtop").innerHTML=`${idBadge(q)}${chBadge(q)}${examBadge(q)}${diffBadge(q)}`;
  $("#mbody").innerHTML=q.bodyHtml+figHtml(q);
  $("#mfoot").innerHTML=footHtml(q);
  const nb=$("#mnote");if(q.note){nb.style.display="block";nb.innerHTML="📌 "+q.note;}else nb.style.display="none";
  const ans=$("#mans");ans.classList.remove("show");
  ans.innerHTML=keyTxt(q)?`<b>เฉลยทางการ:</b> ${keyTxt(q)}`:q.solAnswer?`<b>ตอบ:</b> ${q.solAnswer}`:`ข้อนี้ไม่มีเฉลยทางการ และยังไม่มีวิธีทำ`;
  $("#msol").innerHTML=solHtml(q);
  $("#mpos").textContent=`${mIdx+1} / ${filtered.length}`;
  const sh=$("#modal .sheet");sh.style.animation="none";void sh.offsetWidth;sh.style.animation="";
}
function step(d){mIdx=(mIdx+d+filtered.length)%filtered.length;fillModal();SFX.play("swish",d);}

/* ---- view switch ---- */
$("#layout").querySelectorAll("button").forEach(b=>{
  b.classList.toggle("on",b.dataset.v===view);
  b.onclick=()=>{view=b.dataset.v;ls.set("cqb_view",view);SFX.play("toggle");
    $("#layout").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x.dataset.v===view));render();};
});
["input","change"].forEach(ev=>{$("#q").addEventListener(ev,()=>apply());
  ["#fch","#fexam","#fyear","#fdiff","#ftype","#fsol"].forEach(s=>$(s).addEventListener(ev,()=>apply()));});
$("#fsubj").addEventListener("change",()=>{populateChapters($("#fsubj").value);apply();});
["#fsubj","#fch","#fexam","#fyear","#fdiff","#ftype","#fsol"].forEach(s=>$(s).addEventListener("change",()=>SFX.play("click")));
$("#random").onclick=()=>{if(!filtered.length)return;SFX.play("dice");const i=Math.floor(Math.random()*filtered.length);setTimeout(()=>openModal(i),380);};
$("#ftoggle").onclick=()=>{$("#hdr").classList.toggle("fopen");SFX.play("click");};

/* ---- solution toggle + review buttons (delegated: every view + the modal) ---- */
function solToggle(e){
  const rb=e.target.closest(".revbtn");
  if(rb){
    e.stopPropagation();
    const bar=rb.closest(".revbar"), qid=bar.dataset.q, v=rb.dataset.v;
    const wrap=bar.closest(".solwrap"), sb=wrap.previousElementSibling;
    const cur=(REV[qid]||{}).v;
    if(cur===v){ const n=(REV[qid]||{}).note; if(n) REV[qid]={note:n}; else delete REV[qid]; }
    else { REV[qid]=Object.assign({}, REV[qid]||{}, {v:v}); }        // tapping the same one un-marks
    SFX.play(cur===v?"unmark":(v==="ok"?"ok":"bad"));
    saveRev();
    const q=DATA.questions.find(x=>x.id===qid);
    const tmp=document.createElement("div"); tmp.innerHTML=revBar(q);
    bar.replaceWith(tmp.firstElementChild);
    const r=REV[qid]||{};
    sb.classList.toggle("done", r.v==="ok");
    sb.classList.toggle("wrong", r.v==="bad");
    sb.dataset.label = solLabel(q);
    if(!wrap.classList.contains("show")) sb.textContent = sb.dataset.label;
    return true;
  }
  if(e.target.closest(".revnote")) { e.stopPropagation(); return true; }
  const b=e.target.closest(".solbtn");
  if(!b) return false;
  e.stopPropagation();
  const w=b.nextElementSibling;
  if(w && w.classList.contains("solwrap")){
    const open=w.classList.toggle("show");
    SFX.play(open?"open":"close");
    b.textContent = open ? "ซ่อนวิธีทำ ↑" : (b.dataset.label || "ดูวิธีทำ →");
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
function markChoice(e){const li=e.target.closest(".body li");if(!li)return false;SFX.play(li.classList.toggle("mk")?"mark":"unmark");return true;}
$("#root").addEventListener("click",e=>{
  if(solToggle(e)) return;
  if(e.target.closest("#pprev")){pstep(-1);return;}
  if(e.target.closest("#pnext")){pstep(1);return;}
  const p=e.target.closest(".present-btn");if(p){openModal(+p.dataset.i);return;}
  const item=e.target.closest(".pane-item");if(item){SFX.play("click");paneShow(+item.dataset.i);return;}
  const rh=e.target.closest(".row-h");if(rh){SFX.play(rh.parentElement.classList.toggle("open")?"open":"close");return;}
  markChoice(e);
});
$("#root").addEventListener("input",e=>{
  if(e.target.id==="pscrub"){pIdx=(+e.target.value)-1;fillPoster("");SFX.play("tick");return;}
  noteInput(e);
});
$("#msol").addEventListener("click",solToggle);
$("#msol").addEventListener("input",noteInput);
$("#mbody").addEventListener("click",markChoice);

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
  SFX.play("open");
}
$("#exportbtn").onclick=openExport;
$("#expclose").onclick=()=>$("#expwrap").classList.remove("show");
$("#expwrap").onclick=e=>{if(e.target.id==="expwrap")$("#expwrap").classList.remove("show");};
$("#expcopy").onclick=async()=>{
  const t=$("#exptext");
  try{ await navigator.clipboard.writeText(t.value); $("#expcopy").textContent="✅ คัดลอกแล้ว"; SFX.play("ok"); }
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
$("#mx").onclick=closeModal;
$("#modal").onclick=e=>{if(e.target.id==="modal")closeModal();};
$("#mreveal").onclick=()=>SFX.play($("#mans").classList.toggle("show")?"open":"close");
$("#mprev").onclick=()=>step(-1);$("#mnext").onclick=()=>step(1);

/* ---- keyboard ---- */
document.addEventListener("keydown",e=>{
  const typing=/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)&&e.target.type!=="range";
  if($("#modal").classList.contains("show")){
    if(e.key==="Escape")closeModal();
    if(e.key==="ArrowLeft")step(-1);if(e.key==="ArrowRight")step(1);
    return;
  }
  if($("#expwrap").classList.contains("show")){if(e.key==="Escape")$("#expwrap").classList.remove("show");return;}
  if(typing){if(e.key==="Escape")e.target.blur();return;}
  if(!document.body.classList.contains("inapp")){if(e.key==="m"||e.key==="M")toggleSfx();return;}
  if(e.key==="/"){e.preventDefault();$("#q").focus();return;}
  if(e.key==="m"||e.key==="M"){toggleSfx();return;}
  if(view==="poster"){
    if(e.key==="ArrowRight"){e.preventDefault();pstep(1);}
    else if(e.key==="ArrowLeft"){e.preventDefault();pstep(-1);}
    else if(e.key==="Enter"){const b=$("#deck .solbtn");if(b){e.preventDefault();b.click();}}
  }
});

/* ================= LANDING (grid board) ================= */
const PAL=["c-red","c-yel","c-blue","c-card","c-ink","c-card","c-yel","c-red","c-card","c-blue"];
function cov(qs){const n=qs.length;return n?Math.round(qs.filter(hasSol).length/n*100):0;}
function tileSize(n,max){const r=n/max;return r>=.8?"w2 h2 big":r>=.5?"w2":"";}
function buildBoard(){
  const Q=DATA.questions, chem=Q.filter(q=>q.subject!=="bio"&&q.subject!=="applied");
  const counts=Object.entries(DATA.counts).filter(([k,c])=>c&&k);
  const max=Math.max(...counts.map(([,c])=>c));
  $("#lsub").textContent=`${Q.length} ข้อ · ${Object.keys(DATA.examcount).length} สนามสอบ · มีวิธีทำ ${SC.have} ข้อ`;
  let h=`<div class="tile hero"><b>${chem.length}</b><span>ข้อสอบเคมี<br>แยกตามบท</span><small>สอวน. · PAT2 · A-Level · 9 วิชาสามัญ<br>เลือกบทด้านข้าง หรือกด ทุกบท</small></div>`;
  let i=1;
  h+=`<button class="tile c-ink" data-go="all" style="--i:${i++}"><span class="no">∀</span><span class="nm">ทุกบท</span><span class="ct">${Q.length} ข้อ · ทุกวิชา</span></button>`;
  h+=`<button class="tile c-yel" data-go="random" style="--i:${i++}"><span class="no">🎲</span><span class="nm">สุ่ม 1 ข้อ</span><span class="ct">จากทั้งคลัง</span></button>`;
  CHS.forEach(([k,name],j)=>{
    const c=DATA.counts[k]||0;if(!c)return;
    const qs=chem.filter(q=>q.ch===k),cv=cov(qs);
    h+=`<button class="tile ${PAL[j%PAL.length]} ${tileSize(c,max)}" data-go="ch" data-ch="${k}" style="--i:${i++}">
      <span class="no">${parseInt(k)}</span><span class="nm">${name}</span>
      <span class="ct">${c} ข้อ${cv?` · วิธีทำ ${cv}%`:""}</span><span class="cov"><i style="width:${cv}%"></i></span></button>`;
    if(j===4) h+=`<div class="tile deco1" style="--i:${i++}"></div>`;
    if(j===9) h+=`<div class="tile deco2" style="--i:${i++}"></div>`;
  });
  if(DATA.biocount){const qs=Q.filter(q=>q.subject==="bio"),cv=cov(qs);
    h+=`<button class="tile c-blue w2" data-go="bio" style="--i:${i++}"><span class="no">ชีว</span><span class="nm">ชีววิทยา</span><span class="ct">${DATA.biocount} ข้อ${cv?` · วิธีทำ ${cv}%`:""}</span><span class="cov"><i style="width:${cv}%"></i></span></button>`;}
  if(DATA.appcount){const qs=Q.filter(q=>q.subject==="applied"),cv=cov(qs);
    h+=`<button class="tile c-red" data-go="applied" style="--i:${i++}"><span class="no">✦</span><span class="nm">เคมีประยุกต์</span><span class="ct">${DATA.appcount} ข้อ</span><span class="cov"><i style="width:${cv}%"></i></span></button>`;}
  if(SC.flag) h+=`<button class="tile c-card" data-go="flag" style="--i:${i++}"><span class="no">⚠</span><span class="nm">วิธีทำไม่ฟันธง</span><span class="ct">${SC.flag} ข้อ</span></button>`;
  if(SC.unchecked) h+=`<button class="tile c-yel" data-go="unchecked" style="--i:${i++}"><span class="no">✓?</span><span class="nm">ยังไม่ตรวจวิธีทำ</span><span class="ct">${SC.unchecked} ข้อ</span></button>`;
  h+=`<div class="tile deco3" style="--i:${i++}"></div>`;
  $("#board").innerHTML=h;
}
function resetFilters(){$("#q").value="";$("#fsubj").value="";populateChapters("");["#fexam","#fyear","#fdiff","#ftype","#fsol"].forEach(s=>$(s).value="");}
function enterApp(x,y,fn){
  const app=$("#app");app.style.setProperty("--x",x+"px");app.style.setProperty("--y",y+"px");
  fn();document.body.classList.add("inapp");app.classList.add("show","opening");window.scrollTo(0,0);
  setTimeout(()=>app.classList.remove("opening"),700);
}
$("#board").addEventListener("click",e=>{
  const t=e.target.closest("[data-go]");if(!t)return;
  const r=t.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2,g=t.dataset.go;
  SFX.play("tile");setTimeout(()=>SFX.play("whoosh"),70);
  enterApp(x,y,()=>{
    resetFilters();
    if(g==="ch"){$("#fsubj").value="chem";populateChapters("chem");$("#fch").value=t.dataset.ch;}
    else if(g==="bio"){$("#fsubj").value="bio";populateChapters("bio");}
    else if(g==="applied"){$("#fsubj").value="applied";populateChapters("applied");}
    else if(g==="flag"||g==="unchecked"){$("#fsol").value=g;}
    apply();
    if(g==="random"&&filtered.length){setTimeout(()=>SFX.play("dice"),250);setTimeout(()=>openModal(Math.floor(Math.random()*filtered.length)),650);}
  });
});
$("#home").onclick=()=>{SFX.play("home");document.body.classList.remove("inapp");$("#app").classList.remove("show");window.scrollTo(0,0);buildBoard();};
buildBoard();
</script></body></html>"""

open(OUT,"w",encoding="utf-8").write(HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False)))
print("wrote", OUT, "-", len(questions), "questions -", len(examcount), "exam type(s)")
