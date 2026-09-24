# -*- coding: utf-8 -*-
"""Parse question-bank.md -> self-contained interactive HTML viewer.
Design (2026-09-24, Prat's picks): Bauhaus grid-board landing page to choose a chapter (circle-reveal
into the bank), poster-deck question layout, kinetic animated background (toggleable, off under
prefers-reduced-motion). Features: 4 switchable layouts (poster deck / cards / list / two-pane),
present mode, random pick, full filters incl. subject/exam/solution status, collapsed solutions with
in-browser ✓/✗ review marks exported for tools/apply_review.py. No AI-disclaimer banner (personal use)."""
import re, json, markdown, os
from formulas import FORMULAS

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

# $$...$$ LaTeX (used in some worked solutions) must reach the browser untouched: the chem pass would
# turn K_b / H2PO4 into <sub> tags and markdown would eat _ and \ inside it, so KaTeX got garbage.
# Stash each block behind a lowercase placeholder (no chem formula can start lowercase), render, restore.
import html as _html
_MATH = re.compile(r"\$\$.+?\$\$", re.S)
def md_render(t):
    keep = []
    def stash(m):
        keep.append(m.group(0)); return "@@mathblock%dzz@@" % (len(keep) - 1)
    out = markdown.markdown(chem_notation(_MATH.sub(stash, t)), extensions=["tables", "nl2br"])
    for i, m in enumerate(keep):
        out = out.replace("@@mathblock%dzz@@" % i, _html.escape(m, quote=False))
    return out

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
        "bodyHtml": md_render(body_md),
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
                "html":   md_render(body) if body else "",
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
 "formulas": FORMULAS,
}

HTML = r"""<!doctype html><html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5">
<title>คลังข้อสอบเคมี · Chem Question Bank</title>
<link rel="icon" href="icons/icon.svg" type="image/svg+xml"><link rel="icon" href="icons/favicon-32.png" sizes="32x32" type="image/png">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" onload="window.texReady&&texReady()"></script>
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png"><link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#141414"><meta name="apple-mobile-web-app-title" content="คลังเคมี">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anuphan:wght@400;500;600;700;800&family=Sarabun:wght@400;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root{--sh:#141414;--paper:#efe9dc;--card:#fffdf7;--ink:#141414;--red:#e4412b;--blue:#1f3fbf;--yel:#f2b705;--mut:#6b6457;--line:#141414}
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
@media(min-width:561px){#landing{padding:0 16px 60px 50px}}   /* room for the side tabs */
.lwrap{max-width:1180px;margin:0 auto}
.lhead{display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap;padding:26px 0 18px}
.lhead h1{margin:0;font-size:2.4rem;font-weight:800;line-height:1;letter-spacing:-.01em;display:flex;align-items:center;gap:12px}
.shapes{display:inline-flex;gap:6px;align-items:center}
.shapes i{display:inline-block;width:18px;height:18px}
.shapes .c{background:var(--red);border-radius:50%}.shapes .s{background:var(--yel)}.shapes .t{background:var(--blue);clip-path:polygon(50% 0,100% 100%,0 100%)}
.lhead p{margin:0 0 4px;color:var(--mut);font-size:.9rem}
.lhead .sp{flex:1}
.lsearch{display:flex;flex:0 1 260px;min-width:200px;border:3px solid var(--ink);background:var(--card);box-shadow:4px 4px 0 var(--sh);transition:box-shadow .15s}
.lsearch:focus-within{box-shadow:6px 6px 0 var(--blue)}
.lsearch input{flex:1;min-width:0;border:0;background:transparent;font:600 1rem "Anuphan",sans-serif;padding:9px 12px;outline:none}
.lsearch .lct{align-self:center;padding:0 10px;font:700 .8rem "JetBrains Mono",monospace;color:var(--mut);white-space:nowrap}
.lsearch button{border:0;border-left:3px solid var(--ink);background:var(--ink);color:var(--yel);font-weight:800;font-size:1.1rem;padding:0 16px;cursor:pointer}
.lsearch.shake{animation:lshake .35s}
@keyframes lshake{20%,60%{transform:translateX(-6px)}40%,80%{transform:translateX(6px)}}
.lbtn{border:3px solid var(--ink);background:var(--card);font-weight:700;padding:8px 14px;box-shadow:4px 4px 0 var(--sh);transition:transform .1s,box-shadow .1s;font-size:.88rem}
.lbtn:hover{transform:translate(-2px,-2px);box-shadow:6px 6px 0 var(--sh)}
.lbtn:active{transform:translate(4px,4px);box-shadow:0 0 0 var(--sh)}
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
.tile.deco{cursor:default}
.d0{background:radial-gradient(circle at 100% 100%,var(--blue) 0 58%,transparent 59%),var(--paper)}
.d1{background:repeating-linear-gradient(45deg,var(--yel) 0 18px,var(--ink) 18px 36px)}
.d2{background:radial-gradient(circle at 50% 50%,var(--red) 0 32%,transparent 33%),var(--card)}
.d3{background:linear-gradient(var(--yel),var(--yel)) center/40% 40% no-repeat,var(--ink)}
.d4{background:var(--card)}.d4:after{content:"";position:absolute;inset:24%;background:var(--blue);clip-path:polygon(50% 0,100% 100%,0 100%)}
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
.btn{padding:6px 11px;border:2px solid var(--ink);background:var(--card);font-size:.82rem;font-weight:700;box-shadow:3px 3px 0 var(--sh);transition:transform .08s,box-shadow .08s}
.btn:hover{transform:translate(-1px,-1px);box-shadow:4px 4px 0 var(--sh)}
.btn:active{transform:translate(3px,3px);box-shadow:0 0 0 var(--sh)}
#exportbtn{background:var(--yel)}
.volbox{display:inline-flex;align-items:center;gap:6px;border:2px solid var(--ink);background:var(--card);padding:2px 8px 2px 2px;box-shadow:3px 3px 0 var(--sh)}
.volbox .sfxbtn{border:0;background:none;font-size:1rem;width:30px;height:28px;padding:0}
.vol{width:92px;accent-color:var(--red);cursor:pointer;height:4px}
.vol.off{opacity:.35}
.lvol{border-width:3px;box-shadow:4px 4px 0 var(--sh);padding:5px 10px 5px 4px}
.lvol .vol{width:110px}
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
.present-btn{margin-left:auto;border:2px solid var(--ink);background:var(--card);padding:4px 11px;font-size:.8rem;font-weight:700;box-shadow:3px 3px 0 var(--sh)}
.present-btn:hover{background:var(--yel)}
code{background:#efe6d2;padding:1px 5px;font-size:.92em}
.empty{text-align:center;color:var(--mut);padding:60px 10px;font-weight:600}
/* ---------- solutions ---------- */
.solbtn{margin-top:12px;border:2px solid var(--ink);background:var(--card);padding:6px 14px;font-size:.84rem;font-weight:800;box-shadow:3px 3px 0 var(--sh);transition:transform .08s,box-shadow .08s}
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
.dbtn{border:3px solid var(--ink);background:var(--card);font-weight:800;font-size:1.1rem;width:48px;height:44px;box-shadow:4px 4px 0 var(--sh);transition:transform .08s,box-shadow .08s}
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
.poster.lv-medium:after{background:var(--yel)}.poster.lv-easy:after{background:var(--blue)}
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
.card{position:relative;background:var(--card);border:3px solid var(--ink);box-shadow:7px 7px 0 var(--sh);padding:18px 20px 16px 32px;margin-bottom:22px;overflow:hidden}
.card.anim{animation:cardIn .5s cubic-bezier(.2,1.1,.4,1) both;animation-delay:calc(var(--i,0)*50ms)}
@keyframes cardIn{from{opacity:0;transform:translateY(20px)}}
.card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:10px;background:var(--red)}
.card.lv-medium:before{background:var(--yel)}.card.lv-easy:before{background:var(--blue)}
.card .cnum{position:absolute;right:14px;top:0;font-size:3.6rem;font-weight:800;color:transparent;-webkit-text-stroke:2px #e1d8c4;line-height:1;pointer-events:none}
.card-top{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:10px;position:relative;padding-right:70px}
/* ---------- LIST view ---------- */
.row{background:var(--card);border:3px solid var(--ink);margin-bottom:8px;overflow:hidden;transition:box-shadow .15s,transform .15s}
.row:hover{box-shadow:5px 5px 0 var(--sh);transform:translate(-2px,-2px)}
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
.sheet.lv-medium{box-shadow:12px 12px 0 var(--yel)}.sheet.lv-medium:before{background:var(--yel)}
.sheet.lv-easy{box-shadow:12px 12px 0 var(--blue)}.sheet.lv-easy:before{background:var(--blue)}
.sheet .mtop{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:16px;padding-right:50px}
.sheet .body{font-size:1.38rem;line-height:1.85}
.sheet .body li{padding:9px 14px;font-size:1.02em}
.sheet .fig{max-height:52vh;width:auto}
.sheet .solbody{font-size:1.05rem}
.x{position:absolute;top:14px;right:16px;border:3px solid var(--ink);background:var(--ink);color:var(--paper);width:42px;height:42px;font-size:1.1rem;font-weight:800}
.mctrl{display:flex;gap:10px;align-items:center;margin-top:20px;flex-wrap:wrap}
.mctrl button{padding:10px 18px;border:3px solid var(--ink);background:var(--card);font-size:1rem;font-weight:800;box-shadow:4px 4px 0 var(--sh)}
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
.exprow button{border:2px solid var(--ink);background:var(--card);padding:7px 13px;font-size:.84rem;font-weight:700;box-shadow:3px 3px 0 var(--sh)}
.exprow button.pri{background:var(--ink);color:var(--paper)}
.exprow button.dan{color:var(--red)}
@media(max-width:640px){.poster{padding:20px 16px 18px 26px}.poster .pnum{font-size:4.2rem}.poster .body,.poster .solbox{max-width:100%}.poster .phead,.poster .pmeta{max-width:78%}.sheet{padding:22px 16px 18px 28px}.sheet .body{font-size:1.15rem}}

.katex-display{overflow-x:auto;overflow-y:hidden;padding:4px 0;margin:.6em 0}
.katex{font-size:1.08em}
/* ---------- periodic table drawer + Mw calculator ---------- */
#pdtab{position:fixed;left:0;top:28%;z-index:45;writing-mode:vertical-rl;background:var(--red);color:#fff;border:3px solid var(--ink);border-left:0;padding:14px 8px;font:800 .9rem "Anuphan",sans-serif;box-shadow:4px 4px 0 var(--sh);cursor:pointer;display:none;transition:transform .2s}
#pdtab{display:block!important}
#pdtab:hover{transform:translateX(4px)}
#pdscrim{position:fixed;inset:0;z-index:70;background:rgba(20,20,20,.35);opacity:0;pointer-events:none;transition:opacity .35s}
#pd{position:fixed;left:0;top:0;bottom:0;z-index:71;width:min(1240px,97vw);background:var(--paper);border-right:4px solid var(--ink);box-shadow:10px 0 0 var(--sh);transform:translateX(calc(-100% - 20px));visibility:hidden;transition:transform .6s cubic-bezier(.34,1.35,.64,1),visibility 0s .6s;padding:14px 18px 28px;overflow:auto}
body.pdopen #pd{transform:none;visibility:visible;transition:transform .6s cubic-bezier(.34,1.35,.64,1),visibility 0s}
body.pdopen #pdscrim{opacity:1;pointer-events:auto}
.pdh{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:12px}
.pdh>b{font-size:1.3rem;font-weight:800}
.pdq{font-size:.8rem;background:var(--card);border:2px solid var(--ink);padding:3px 8px}
.pdq:empty{display:none}
.pdq button{border:0;background:none;font:800 .85rem "Anuphan",sans-serif;color:var(--red);padding:0 3px;cursor:pointer;text-decoration:underline dotted}
.pdq button:hover{background:var(--red);color:#fff}
.pdhov{font:600 .8rem "JetBrains Mono",monospace;color:var(--mut)}
.pdmwt{margin-left:auto;border:3px solid var(--ink);background:var(--card);font:800 .85rem "Anuphan",sans-serif;padding:6px 12px;cursor:pointer;box-shadow:3px 3px 0 var(--sh)}
.pdmwt.on{background:var(--blue);color:#fff}
.pdmwt:active{transform:translate(3px,3px);box-shadow:none}
#pd.nomw .pdcalc,#pd.nomw .pdbrk,#pd.nomw .pdq{display:none}
.pdx{background:var(--ink);color:var(--paper);border:0;width:36px;height:36px;font-weight:800;cursor:pointer}
.pdw{container-type:inline-size;overflow-x:auto}
.pdg{--u:calc(max(100cqi,600px)/18);display:grid;grid-template-columns:repeat(18,minmax(0,1fr));gap:3px;min-width:600px}
.pde{aspect-ratio:1/1;border:2px solid var(--ink);display:flex;flex-direction:column;align-items:center;justify-content:space-between;padding:3px 3px 4px;cursor:pointer;user-select:none;-webkit-user-select:none;min-width:0;overflow:hidden;position:relative;line-height:1;transition:transform .15s,box-shadow .15s}
.pde i{align-self:flex-start;font-style:normal;font-weight:500;opacity:.75;font-size:calc(var(--u)*.16)}
.pde b{font-weight:800;font-size:calc(var(--u)*.33);margin-top:-6%}
.pde s{text-decoration:none;font-family:"JetBrains Mono",monospace;font-size:calc(var(--u)*.15);opacity:.85}
.pde:hover{transform:translate(-2px,-2px);box-shadow:3px 3px 0 var(--sh);z-index:2}
.pde.inq::after{content:"";position:absolute;inset:-2px;border:3px solid var(--red);animation:pdpulse 1.2s infinite}
@keyframes pdpulse{50%{inset:3px;opacity:.3}}
.pde.inf{outline:3px solid var(--blue);outline-offset:-3px}
.pde.pdflash{animation:pdfl .35s}
@keyframes pdfl{0%{background:var(--ink);color:var(--yel)}}
.k-alk{background:var(--red);color:#fff}.k-ae{background:#f28c28}.k-tm{background:var(--card)}.k-pt{background:#d9d2c1}.k-md{background:#9fb0e8}.k-nm{background:var(--yel)}.k-hal{background:var(--blue);color:#fff}.k-ng{background:var(--ink);color:var(--paper)}.k-ln{background:#f3c3b8}.k-an{background:#e39c8c}
.pdph{display:flex;align-items:center;justify-content:center;font:600 calc(var(--u)*.17) "JetBrains Mono",monospace;opacity:.55;aspect-ratio:1/1}
.pdinfo{grid-row:1/4;grid-column:3/13;display:flex;gap:16px;align-items:flex-start;padding:0 6px;overflow:auto}
.pdbig{flex:none;position:relative;width:calc(var(--u)*2.3);height:calc(var(--u)*2.3);border:4px solid var(--ink);background:var(--card);box-shadow:6px 6px 0 var(--sh);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:calc(var(--u)*1.2);padding-bottom:30px;line-height:1}
.pdbig i{position:absolute;left:6px;top:4px;font:700 .8rem "JetBrains Mono",monospace;font-style:normal}
.pdbig u{position:absolute;left:0;right:0;bottom:22px;text-align:center;font:700 .8rem "Anuphan",sans-serif;text-decoration:none}
.pdbig s{position:absolute;left:0;right:0;bottom:5px;text-align:center;font:700 .85rem "JetBrains Mono",monospace;text-decoration:none}
.pdbrk{flex:1;min-width:0}
.pdbrk table{border-collapse:collapse;font:600 .78rem "JetBrains Mono",monospace;width:100%;background:var(--card)}
.pdbrk th,.pdbrk td{border:2px solid var(--ink);padding:2px 7px;text-align:right;white-space:nowrap}
.pdbrk th{background:var(--ink);color:var(--paper);font-weight:700}
.pdbrk td:first-child{text-align:left;font-weight:800}
.pdbrk .pc{background-image:linear-gradient(90deg,var(--yel) var(--p),transparent var(--p))}
.pdbrk .hint{opacity:.6;font-size:.88rem}
.pdbrk .err{color:var(--red);font-weight:700}
.pdcalc{border:3px solid var(--ink);background:var(--card);box-shadow:6px 6px 0 var(--sh);padding:12px;margin-top:18px;display:flex;flex-wrap:wrap;gap:10px;align-items:stretch}
.pdcalc input{flex:1 1 220px;min-width:0;font:700 1.45rem "JetBrains Mono",monospace;border:3px solid var(--ink);padding:6px 12px;background:var(--paper);outline:none}
.pdcalc input:focus{border-color:var(--blue)}
.pdmw{background:var(--ink);color:var(--yel);padding:6px 16px;font:800 1.5rem "JetBrains Mono",monospace;min-width:210px;text-align:right;display:flex;flex-direction:column;justify-content:center}
.pdmw small{font:600 .75rem "Anuphan",sans-serif;color:#bbb}
.pdkeys{display:flex;flex-wrap:wrap;gap:4px;width:100%;align-items:center}
.pdkeys button{border:2px solid var(--ink);background:var(--paper);font:800 .95rem "JetBrains Mono",monospace;min-width:36px;height:34px;padding:0 8px;cursor:pointer}
.pdkeys button:hover{background:var(--yel)}
.pdkeys button:active{transform:translate(2px,2px)}
.pdkeys .kp{background:var(--blue);color:#fff}.pdkeys .kx{background:var(--red);color:#fff}
.pdkeys .sep{width:10px}
.pdkeys .tip{margin-left:auto;font-size:.75rem;color:var(--mut)}
@media (prefers-reduced-motion:reduce){#pd,#pdscrim{transition:none}.pde.inq::after{animation:none}}

/* ---------- tools drawer (constants · unit converter · ions) ---------- */
#tdtab{position:fixed;left:0;top:calc(28% + 128px);z-index:45;writing-mode:vertical-rl;background:var(--yel);color:#141414;border:3px solid var(--ink);border-left:0;padding:14px 8px;font:800 .9rem "Anuphan",sans-serif;box-shadow:4px 4px 0 var(--sh);cursor:pointer;display:none;transition:transform .2s}
#tdtab{display:block!important}
#tdtab:hover{transform:translateX(4px)}
#td{position:fixed;left:0;top:0;bottom:0;z-index:71;width:min(1040px,97vw);background:var(--paper);border-right:4px solid var(--ink);box-shadow:10px 0 0 var(--yel);transform:translateX(calc(-100% - 20px));visibility:hidden;transition:transform .6s cubic-bezier(.34,1.35,.64,1),visibility 0s .6s;padding:14px 18px 28px;overflow:auto}
body.tdopen #td{transform:none;visibility:visible;transition:transform .6s cubic-bezier(.34,1.35,.64,1),visibility 0s}
body.tdopen #pdscrim,body.tmopen #pdscrim{opacity:1;pointer-events:auto}
.tdtabs{display:flex;border:3px solid var(--ink);margin-bottom:14px;box-shadow:4px 4px 0 var(--sh)}
.tdtabs button{flex:1;border:0;border-right:3px solid var(--ink);background:var(--card);font:800 .95rem "Anuphan",sans-serif;padding:9px 6px;cursor:pointer}
.tdtabs button:last-child{border-right:0}
.tdtabs button.on{background:var(--ink);color:var(--paper)}
.tdpane{display:none}.tdpane.on{display:block;animation:pIn .35s cubic-bezier(.2,1.2,.4,1)}
.kgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.kcard{border:3px solid var(--ink);background:var(--card);box-shadow:4px 4px 0 var(--sh);padding:10px 12px 10px 18px;position:relative}
.kcard:before{content:"";position:absolute;left:0;top:0;bottom:0;width:7px;background:var(--c,var(--red))}
.kcard .ks{font:800 1.05rem "JetBrains Mono",monospace}
.kcard .kval{font:800 1.2rem "JetBrains Mono",monospace;margin:4px 0 2px;color:var(--blue)}
.kcard .kval small{font-size:.72rem;color:var(--ink);font-weight:600}
.kcard .kn{font-size:.8rem;color:var(--mut)}
.cvcat{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.cvcat button{border:2px solid var(--ink);background:var(--card);font:700 .88rem "Anuphan",sans-serif;padding:6px 12px;cursor:pointer;box-shadow:3px 3px 0 var(--sh)}
.cvcat button.on{background:var(--blue);color:#fff}
.cvin{display:flex;gap:8px;margin-bottom:12px}
.cvin input{flex:1;min-width:0;font:700 1.4rem "JetBrains Mono",monospace;border:3px solid var(--ink);padding:6px 12px;background:var(--card);outline:none}
.cvin input:focus{border-color:var(--blue)}
.cvin select{font:700 1rem "JetBrains Mono",monospace;max-width:none;border-width:3px}
.cvout{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:6px}
.cvout div{border:2px solid var(--ink);background:var(--card);padding:8px 12px;display:flex;justify-content:space-between;align-items:baseline;gap:10px;font-family:"JetBrains Mono",monospace}
.cvout div.src{background:var(--ink);color:var(--paper)}
.cvout b{font-size:1.05rem}.cvout span{opacity:.7}
.iontbl{width:100%;border-collapse:collapse;background:var(--card);border:3px solid var(--ink)}
.iontbl th{background:var(--ink);color:var(--paper);text-align:left;padding:5px 10px;font-size:.82rem}
.iontbl td{border-bottom:2px solid var(--ink);padding:5px 10px;font-size:.92rem}
.iontbl tr.grp td{background:var(--paper);font-weight:800;font-size:.78rem;letter-spacing:.08em}
.iontbl tr.io{cursor:pointer}
.iontbl tr.io:hover td{background:var(--yel);color:#141414}
.iontbl .f{font:700 1rem "JetBrains Mono",monospace;white-space:nowrap}
.tdnote{font-size:.78rem;color:var(--mut);margin-top:10px}
/* สูตร: formula sheet by chapter; the chapter on screen floats to the top */
.fxbar{position:sticky;top:-14px;z-index:3;background:var(--paper);padding:10px 0 12px;margin:-6px 0 4px;border-bottom:3px solid var(--ink)}
.fxbar input{width:100%;font:700 1.02rem "Anuphan",sans-serif;border:3px solid var(--ink);padding:8px 12px;background:var(--card);color:var(--ink);outline:none;box-shadow:4px 4px 0 var(--sh)}
.fxbar input:focus{border-color:var(--blue)}
.fxchips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.fxchips button{min-width:38px;height:34px;padding:0 10px;border:3px solid var(--ink);background:var(--card);color:var(--ink);font:700 .88rem "Anuphan",sans-serif;white-space:nowrap;cursor:pointer;border-bottom:6px solid var(--c)}
.fxchips button:hover{background:var(--c);color:#141414}
.fxchips button.cur{background:var(--ink);color:var(--paper)}
.fxchips button.dim{opacity:.3}
.fxchips button b{font:800 .95rem "JetBrains Mono",monospace;margin-right:2px}
.fsec{margin:20px 0 6px;scroll-margin-top:118px}
.fsh{display:flex;align-items:center;gap:14px;margin-bottom:12px}
.fno{flex:none;width:54px;height:54px;display:grid;place-items:center;background:var(--c);border:3px solid var(--ink);font:800 1.6rem "JetBrains Mono",monospace;color:#141414;box-shadow:4px 4px 0 var(--sh)}
.fsh b{font-size:1.18rem;display:block;line-height:1.3}
.fcur{display:inline-block;background:var(--red);color:#fff;font-size:.72rem;font-weight:800;padding:2px 9px;margin-top:4px}
.fct{margin-left:auto;font-size:.8rem;color:var(--mut);white-space:nowrap}
.fsec.cur{padding:12px 12px 14px;border:3px solid var(--ink);box-shadow:8px 8px 0 var(--c);background:color-mix(in srgb,var(--c) 7%,var(--paper))}
.fgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.fc{border:3px solid var(--ink);background:var(--card);box-shadow:4px 4px 0 var(--sh);display:flex;flex-direction:column;min-width:0}
.fc .fm{padding:12px;border-bottom:3px solid var(--ink);background:color-mix(in srgb,var(--c) 16%,var(--card));font:600 1rem "JetBrains Mono",monospace;overflow-x:auto;min-height:78px;display:flex;align-items:center;justify-content:center;text-align:center}
.fc .fm{flex-direction:column;gap:6px}.fc .fl{max-width:100%}
.fc .fm .katex-display{margin:0;overflow:visible;padding:0}.fc .fm .katex{font-size:1.18em}
@media(max-width:520px){.fc .fp .katex{font-size:1.12em}}
.fc .fn{font-weight:800;padding:9px 12px 2px;font-size:1rem}
.fc .fn i{font-style:normal;font-size:.68rem;border:2px solid var(--ink);padding:0 6px;margin-left:8px;vertical-align:2px;background:var(--yel);color:#141414;white-space:nowrap}
.fc .fk{padding:2px 12px 11px;font-size:.86rem;color:var(--mut);line-height:1.55}
.fc.wide{grid-column:1/-1;border-left:10px solid var(--c)}
.fc.fhero{grid-column:1/-1;box-shadow:7px 7px 0 var(--c)}
.fc .fl.chain{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;column-gap:.4em;row-gap:10px}
.fc .fp{white-space:nowrap}.fc .fp .katex{font-size:1.3em}.fc.fhero .fm{min-height:120px;padding:18px 14px}.fc.fhero .fp .katex{font-size:1.75em}
.fc.wide .fn{padding-top:10px}
.fc ul{margin:6px 0 11px;padding:0 14px 0 30px;line-height:1.7;font-size:.93rem}
.fc li::marker{color:var(--c)}
.ftw{overflow-x:auto;margin:6px 12px 8px}
.ftbl{width:100%;border-collapse:collapse;font-size:.9rem}
.ftbl th{background:var(--ink);color:var(--paper);text-align:left;padding:5px 10px;font-size:.8rem;white-space:nowrap}
.ftbl td{border-bottom:2px solid var(--ink);padding:5px 10px}
.fxnone{padding:40px 10px;text-align:center;color:var(--mut);font-weight:700}
/* desktop (mouse) only: the sheet read small at arm's length; iPad (touch) keeps the base size */
@media (hover:hover) and (pointer:fine) and (min-width:900px){
  #td{width:min(1500px,96vw)}
  .fxbar input{font-size:1.15rem;padding:10px 14px}
  .fxchips{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}
  .fxchips button{height:40px;font-size:1rem;padding:0 10px;text-align:left}.fxchips button b{font-size:1.05rem;margin-right:6px}
  .fno{width:60px;height:60px;font-size:1.8rem}
  .fsh b{font-size:1.38rem}.fcur{font-size:.82rem}.fct{font-size:.92rem}
  .fgrid{grid-template-columns:repeat(auto-fill,minmax(320px,1fr))}
  .fc .fm{min-height:90px}.fc .fp .katex{font-size:1.5em}
  .fc .fn{font-size:1.16rem;padding-top:11px}.fc .fn i{font-size:.76rem}
  .fc .fk{font-size:1rem;line-height:1.6}
  .fc ul{font-size:1.07rem;line-height:1.75}
  .ftbl{font-size:1.04rem}.ftbl th{font-size:.92rem}
  #td-fx .tdnote{font-size:.9rem}
}

/* ---------- simple timer: right-side panel ---------- */
#tmtab{position:fixed;left:0;top:calc(28% + 256px);z-index:45;writing-mode:vertical-rl;background:var(--blue);color:#fff;border:3px solid var(--ink);border-left:0;padding:14px 8px;font:800 .9rem "Anuphan",sans-serif;box-shadow:4px 4px 0 var(--sh);cursor:pointer;display:block;transition:transform .2s}
#tmtab:hover{transform:translateX(4px)}
#tmtab.run{background:var(--red);font-family:"JetBrains Mono",monospace}
#tm{position:fixed;left:0;top:0;bottom:0;z-index:72;width:min(560px,94vw);background:var(--paper);border-right:4px solid var(--ink);box-shadow:10px 0 0 var(--blue);transform:translateX(calc(-100% - 20px));visibility:hidden;transition:transform .55s cubic-bezier(.34,1.35,.64,1),visibility 0s .55s;padding:14px 18px 24px;overflow:auto}
body.tmopen #tm{transform:none;visibility:visible;transition:transform .55s cubic-bezier(.34,1.35,.64,1),visibility 0s}
.tmseg{display:flex;border:3px solid var(--ink);margin-bottom:14px}
.tmseg button{flex:1;border:0;border-right:3px solid var(--ink);background:var(--card);font:800 .95rem "Anuphan",sans-serif;padding:9px 4px;cursor:pointer}
.tmseg button:last-child{border-right:0}
.tmseg button.on{background:var(--ink);color:var(--paper)}
.tmface{position:relative;border:4px solid var(--ink);background:var(--card);box-shadow:6px 6px 0 var(--sh);padding:26px 10px 20px;text-align:center;overflow:hidden}
.tmface:before{content:"";position:absolute;right:-50px;top:-50px;width:130px;height:130px;border-radius:50%;background:var(--yel);opacity:.9}
.tmdig{position:relative;font:800 clamp(4.4rem,7vw,6.4rem) "JetBrains Mono",monospace;line-height:1;letter-spacing:-.02em}
.tmbar{position:relative;height:10px;border:2px solid var(--ink);background:var(--paper);margin:18px 6px 0;overflow:hidden}
.tmbar i{display:block;height:100%;background:var(--blue);transition:width .25s linear}
.tmface.done{animation:tmflash .5s 6 alternate}
.tmface.done .tmdig{color:var(--red)}
@keyframes tmflash{to{background:var(--red);color:#fff}}
.tmpre{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:16px}
.tmpre button,.tmadj button{border:2px solid var(--ink);background:var(--card);font:800 .95rem "Anuphan",sans-serif;padding:8px 4px;cursor:pointer;box-shadow:3px 3px 0 var(--sh)}
.tmpre button:active,.tmadj button:active,.tmctl button:active{transform:translate(3px,3px);box-shadow:none}
.tmpre button.on{background:var(--ink);color:var(--paper)}
.tmadj{display:flex;gap:6px;margin-top:8px}.tmadj button{flex:1}
.tmctl{display:flex;gap:10px;margin-top:18px}
.tmctl button{flex:1;border:3px solid var(--ink);font:800 1.15rem "Anuphan",sans-serif;padding:12px 6px;cursor:pointer;box-shadow:4px 4px 0 var(--sh);background:var(--card)}
.tmctl .go{background:var(--red);color:#fff;flex:2}
.tmctl .go.pause{background:var(--yel);color:#141414}
.tmcd{display:block}.tm-up .tmcd{display:none}
.tmfull{display:block;width:100%;margin-top:12px;border:3px solid var(--ink);background:var(--ink);color:var(--paper);font:800 1rem "Anuphan",sans-serif;padding:11px;cursor:pointer;box-shadow:4px 4px 0 var(--blue)}
.tmfull:active{transform:translate(4px,4px);box-shadow:none}
.tmfull.on{background:var(--blue);box-shadow:4px 4px 0 var(--ink)}
/* floating corner timer */
#tmmini{position:fixed;left:14px;bottom:14px;z-index:46;width:230px;background:var(--card);border:4px solid var(--ink);box-shadow:7px 7px 0 var(--sh);padding:10px 12px 12px 18px;display:none}
#tmmini:before{content:"";position:absolute;left:0;top:0;bottom:0;width:8px;background:var(--blue)}
#tmmini.show{display:block;animation:pIn .4s cubic-bezier(.2,1.2,.4,1)}
#tmmini.run:before{background:var(--red)}
.tmmd{font:800 2.9rem "JetBrains Mono",monospace;line-height:1;letter-spacing:-.03em;text-align:center;cursor:pointer}
.tmmb{height:8px;border:2px solid var(--ink);background:var(--paper);margin:8px 0 10px;overflow:hidden}
.tmmb i{display:block;height:100%;background:var(--blue);transition:width .25s linear}
#tmmini.up .tmmb{visibility:hidden}
.tmmc{display:flex;gap:6px}
.tmmc button{flex:1;border:2px solid var(--ink);background:var(--card);font:800 1rem "Anuphan",sans-serif;padding:6px 0;cursor:pointer;box-shadow:2px 2px 0 var(--sh)}
.tmmc button:active{transform:translate(2px,2px);box-shadow:none}
.tmmc .go{flex:2;background:var(--red);color:#fff}
.tmmc .go.pause{background:var(--yel);color:#141414}
#tmmini.done{animation:tmflash .5s 6 alternate}
#tmmini.done .tmmd{color:var(--red)}

/* ---------- landing: recent tile + difficulty bar ---------- */
.tile.recent{cursor:default}
.recent .rl{display:flex;flex-wrap:wrap;gap:5px;margin-top:auto}
.recent .rl button{border:2px solid var(--ink);background:var(--card);color:var(--ink);font:700 .74rem "JetBrains Mono",monospace;padding:3px 8px;cursor:pointer;box-shadow:2px 2px 0 var(--sh)}
.recent .rl button:hover{background:var(--ink);color:var(--paper)}
.recent .empty-r{font-size:.8rem;opacity:.7;margin-top:auto}
.btn.on{background:var(--ink);color:var(--paper)}

/* ---------- night mode: ink-black surfaces, cream text, black offset shadows ---------- */
body.dark{--paper:#18181b;--card:#232327;--ink:#e8e2d4;--mut:#9c958a;--sh:#050506;--blue:#3b57d6;--red:#e2492f;--yel:#e8ae06;color-scheme:dark}
body.dark .board{background:#050506;border-color:#050506}
body.dark .d1{background:repeating-linear-gradient(45deg,var(--yel) 0 18px,#050506 18px 36px)}
body.dark .d3{background:linear-gradient(var(--yel),var(--yel)) center/40% 40% no-repeat,#050506}
body.dark .c-ink,body.dark .b-id,body.dark .sec-t,body.dark .pane-item.sel,body.dark .seg button.on,body.dark .tmseg button.on,body.dark .tdtabs button.on,body.dark .tmpre button.on,body.dark .cvout div.src,body.dark .iontbl th,body.dark .ftbl th,body.dark .fxchips button.cur,body.dark .pdbrk th,body.dark .pdx,body.dark .x,body.dark .exprow button.pri,body.dark .pdmw{background:#050506;color:#e8e2d4}
body.dark .k-ng{background:#050506;color:#e8e2d4;border-color:#e8e2d4}
body.dark header{background:#050506;color:#e8e2d4}
body.dark #q,body.dark .hbtn{background:#050506;color:#e8e2d4;border-left-color:#3a3a40}
body.dark #q:focus,body.dark .hbtn:hover{background:#1c1c20}
body.dark .hbtn.on{background:var(--yel);color:#141414}
body.dark .lsearch button{background:#050506}
body.dark .c-yel,body.dark .k-nm,body.dark .k-ae,body.dark .k-pt,body.dark .k-md,body.dark .k-ln,body.dark .k-an,body.dark .chap-h.app b,body.dark #exportbtn,body.dark .tmctl .go.pause{color:#141414}
body.dark .k-tm{background:#2c2c32}
body.dark .body li:hover,body.dark .pane-item:hover{background:#2a2a30;border-color:#3a3a40}
body.dark .body li.mk{background:var(--yel);color:#141414;border-color:var(--yel)}
body.dark .note,body.dark .soldis,body.dark .ans-box{background:#3a3212;color:#f3ead0}
body.dark code{background:#2c2c32}
body.dark .solbtn.done,body.dark .chk{background:#1f3a26}
body.dark .solbtn.wrong{background:#43201a}
body.dark .revnote,body.dark .expbox textarea{background:var(--card);color:var(--ink)}
body.dark .card .cnum{-webkit-text-stroke-color:#34343a}
body.dark .foot,body.dark .revbar,body.dark .row-body{border-color:#34343a}
body.dark .solbody hr{border-top-color:#34343a}
body.dark .pane-item{border-bottom-color:#2e2e34}
body.dark .dbtn:hover,body.dark .solbtn:hover,body.dark .present-btn:hover,body.dark .pdkeys button:hover{color:#141414}
body.dark .fig{background:#fff}
body.dark .tile .cov{background:rgba(255,255,255,.14)}
body.dark .modal,body.dark .expwrap{background:rgba(0,0,0,.8)}
body.dark .kin .k2{border-color:#2c2c32}body.dark .kin .k4{opacity:.25}
</style></head><body>
<div class="kin" aria-hidden="true"><i class="k1"></i><i class="k2"></i><i class="k3"></i><i class="k4"></i><i class="k5"></i></div>

<!-- ================= LANDING ================= -->
<section id="landing"><div class="lwrap">
  <div class="lhead"><h1><span class="shapes"><i class="c"></i><i class="s"></i><i class="t"></i></span>คลังข้อสอบเคมี</h1>
    <p id="lsub"></p>
    <div class="lsearch" id="lsearch"><input id="lq" placeholder="ค้นหา · สูตร · Q-id  ( / )" autocomplete="off" spellcheck="false"><span class="lct" id="lct"></span><button id="lgo" title="ค้นหา (Enter)">→</button></div>
    <span class="volbox lvol"><button class="sfxbtn" id="lsfx">🔊</button><input type="range" class="vol" min="0" max="100" aria-label="ระดับเสียง"></span>
    <button class="lbtn" id="lbg" title="เปิด/ปิดพื้นหลังเคลื่อนไหว">◐</button>
    <button class="lbtn" id="ldark" title="โหมดกลางคืน / กลางวัน">🌙</button></div>
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
   <button class="btn" id="darkbtn" title="โหมดกลางคืน">🌙</button>
   <span class="volbox"><button class="sfxbtn" id="sfxbtn">🔊</button><input type="range" class="vol" min="0" max="100" aria-label="ระดับเสียง"></span>
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
    <button id="mpt" title="ตารางธาตุ">เปิดตารางธาตุ</button>
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

<button id="pdtab" title="ตารางธาตุ + คำนวณ Mw">ตารางธาตุ</button>
<button id="tdtab" title="ค่าคงที่ · แปลงหน่วย · ไอออน · สูตร">เครื่องมือ</button>
<aside id="td" aria-label="เครื่องมือ">
  <div class="pdh"><b>🧰 เครื่องมือ</b><span class="pdhov">ค่าคงที่ · แปลงหน่วย · ไอออน · สูตร</span><button class="pdx" id="tdx" title="ปิด (Esc)">✕</button></div>
  <div class="tdtabs" id="tdtabs"><button data-t="k" class="on">ค่าคงที่</button><button data-t="cv">แปลงหน่วย</button><button data-t="io">ไอออน</button><button data-t="fx" id="fxtabb">สูตร</button></div>
  <div class="tdpane on" id="td-k"></div><div class="tdpane" id="td-cv"></div><div class="tdpane" id="td-io"></div><div class="tdpane" id="td-fx"></div>
</aside>
<button id="tmtab" title="จับเวลา">จับเวลา</button>
<div id="tmmini" aria-label="นาฬิกาจับเวลา"><div class="tmmd" id="tmmd" title="เปิดแผงจับเวลา">05:00</div><div class="tmmb"><i id="tmmbar"></i></div>
  <div class="tmmc"><button class="go" id="tmmgo">▶</button><button id="tmmreset" title="รีเซ็ต">↺</button><button id="tmmx" title="ซ่อน">✕</button></div></div>
<aside id="tm" aria-label="จับเวลา">
  <div class="pdh"><b>⏱ จับเวลา</b><button class="pdx" id="tmx" title="ปิด">✕</button></div>
  <div class="tmseg" id="tmseg"><button data-m="down" class="on">นับถอยหลัง</button><button data-m="up">นับขึ้น</button></div>
  <div class="tmface" id="tmface"><div class="tmdig" id="tmdig">05:00</div><div class="tmbar tmcd"><i id="tmbar"></i></div></div>
  <div class="tmcd"><div class="tmpre" id="tmpre"></div><div class="tmadj"><button data-a="-60">− 1 นาที</button><button data-a="-10">− 10 วิ</button><button data-a="10">+ 10 วิ</button><button data-a="60">+ 1 นาที</button></div></div>
  <div class="tmctl"><button class="go" id="tmgo">▶ เริ่ม</button><button id="tmreset">↺ รีเซ็ต</button></div>
  <button class="tmfull" id="tmfull">⧉ แสดงนาฬิกามุมจอ</button>
  <p class="tdnote">เปิดทิ้งไว้ข้างโจทย์ได้ ปิดแผงแล้วเวลายังเดินต่อ (ดูเวลาที่แถบซ้าย)</p>
</aside>
<div id="pdscrim"></div>
<aside id="pd" aria-label="ตารางธาตุ">
  <div class="pdh"><b>ตารางธาตุ</b><span class="pdq" id="pdq"></span><span class="pdhov" id="pdhov"></span><button class="pdmwt" id="pdmwt" title="เปิด/ปิดเครื่องคิด Mw">🧮 คิด Mw</button><button class="pdx" id="pdx" title="ปิด (Esc)">✕</button></div>
  <div class="pdw"><div class="pdg" id="pdg"></div></div>
  <div class="pdcalc"><input id="pdin" spellcheck="false" autocomplete="off" placeholder="พิมพ์สูตร เช่น Al2(SO4)3 หรือแตะธาตุ">
    <div class="pdmw"><small id="pdfd"></small><span id="pdmw">Mw = —</span></div>
    <div class="pdkeys" id="pdkeys"></div></div>
</aside>

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
/* worked solutions carry LaTeX ($$\frac{...}$$); KaTeX loads deferred from the CDN, so typeset whatever
   is on screen now and again once it arrives. Without the CDN the raw text simply stays. */
function tex(el){if(!el||!window.renderMathInElement)return;
  try{renderMathInElement(el,{delimiters:[{left:"$$",right:"$$",display:true},{left:"\\(",right:"\\)",display:false}],throwOnError:false,strict:false});}catch(e){}}
window.texReady=()=>{tex($("#root"));tex($("#msol"));};

/* ---------- sound fx: synthesized with Web Audio (no files to host), muteable, remembered ---------- */
const SFX=(()=>{let ctx=null,master=null,verb=null,on=ls.get("cqb_sfx","1")!=="0",vol=Math.max(0,Math.min(100,parseInt(ls.get("cqb_vol","70"),10)||0));
  const gainFor=v=>Math.pow(v/100,1.6)*1.35;   // perceptual-ish curve: the slider feels even across its range
  /* signal chain: every voice -> master -> soft lowpass -> compressor -> out, plus a send into a small
     generated-impulse room reverb. Voices are layered (low "body" + tiny transient) and pitch-varied
     a few % per hit so repeats never sound robotic. */
  function ac(){
    if(!ctx){const A=window.AudioContext||window.webkitAudioContext;if(!A)return null;ctx=new A();
      const comp=ctx.createDynamicsCompressor();comp.threshold.value=-20;comp.knee.value=14;comp.ratio.value=4;comp.attack.value=.003;comp.release.value=.18;
      const lp=ctx.createBiquadFilter();lp.type="lowpass";lp.frequency.value=8500;
      master=ctx.createGain();master.gain.value=gainFor(vol);master.connect(lp);lp.connect(comp);comp.connect(ctx.destination);
      const len=Math.floor(ctx.sampleRate*1.2),ir=ctx.createBuffer(2,len,ctx.sampleRate);
      for(let c=0;c<2;c++){const d=ir.getChannelData(c);for(let i=0;i<len;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/len,3.4);}
      const cv=ctx.createConvolver();cv.buffer=ir;verb=ctx.createGain();verb.gain.value=.9;verb.connect(cv);cv.connect(master);}
    if(ctx.state==="suspended")ctx.resume();return ctx;}
  const vary=(x,p=.03)=>x*(1+(Math.random()*2-1)*p);
  function route(g,wet){g.connect(master);if(wet){const s=ctx.createGain();s.gain.value=wet;g.connect(s);s.connect(verb);}}
  function env(g,t,vol,a,dur){g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(vol,t+a);g.gain.exponentialRampToValueAtTime(.0001,t+dur);}
  function tone(f,dur,o={}){const c=ac();if(!c)return;const t=c.currentTime+(o.delay||0),os=c.createOscillator(),g=c.createGain();
    os.type=o.type||"sine";os.frequency.setValueAtTime(f,t);
    if(o.slide)os.frequency.exponentialRampToValueAtTime(Math.max(20,f*o.slide),t+(o.slideT||dur));
    let n=os;if(o.lp){const fl=c.createBiquadFilter();fl.type="lowpass";fl.frequency.value=o.lp;os.connect(fl);n=fl;}
    env(g,t,o.vol||.12,o.attack||.004,dur);n.connect(g);route(g,o.wet);os.start(t);os.stop(t+dur+.05);}
  function noise(dur,o={}){const c=ac();if(!c)return;const t=c.currentTime+(o.delay||0),n=Math.max(1,Math.floor(c.sampleRate*dur)),
    b=c.createBuffer(1,n,c.sampleRate),d=b.getChannelData(0);for(let i=0;i<n;i++)d[i]=Math.random()*2-1;
    const src=c.createBufferSource();src.buffer=b;const f=c.createBiquadFilter();f.type=o.type||"bandpass";
    f.frequency.setValueAtTime(o.freq||1800,t);if(o.sweep)f.frequency.exponentialRampToValueAtTime((o.freq||1800)*o.sweep,t+dur);f.Q.value=o.q||.8;
    const g=c.createGain();env(g,t,o.vol||.1,o.attack||.002,dur);src.connect(f);f.connect(g);route(g,o.wet);src.start(t);src.stop(t+dur+.05);}
  function bell(f,dur,o={}){const c=ac();if(!c)return;const t=c.currentTime+(o.delay||0),car=c.createOscillator(),mod=c.createOscillator(),mg=c.createGain(),g=c.createGain();
    car.frequency.value=f;mod.frequency.value=f*(o.ratio||3.5);mg.gain.setValueAtTime(f*(o.index||1.6),t);mg.gain.exponentialRampToValueAtTime(1,t+dur);
    mod.connect(mg);mg.connect(car.frequency);env(g,t,o.vol||.08,.003,dur);car.connect(g);route(g,o.wet==null?.5:o.wet);
    car.start(t);mod.start(t);car.stop(t+dur+.05);mod.stop(t+dur+.05);}
  function mallet(f,o={}){const v=o.vol||.14;tone(f,.42,{vol:v,wet:.25,delay:o.delay,attack:.002});tone(f*3.98,.07,{vol:v*.22,delay:o.delay,attack:.001});noise(.012,{vol:v*.3,freq:3000,q:1,delay:o.delay});}
  function thock(o={}){const v=o.vol||.15,d=o.delay||0;
    tone(vary(o.f||190),.1,{vol:v,slide:.5,slideT:.07,attack:.001,delay:d,lp:1400});
    noise(.016,{vol:v*.55,freq:vary(3600,.1),q:1.3,delay:d});}
  const P={
    click:()=>thock({f:240,vol:.1}),
    preview:()=>thock({f:210,vol:.14}),
    tile:()=>{mallet(vary(523,.015));mallet(vary(784,.015),{delay:.065,vol:.12});},
    whoosh:()=>{noise(.62,{freq:260,sweep:9,q:.7,vol:.12,attack:.26,wet:.35});tone(95,.45,{vol:.16,slide:.65,delay:.42,lp:320,attack:.01,wet:.2});},
    swish:d=>{noise(.26,{freq:d>0?650:2700,sweep:d>0?4.2:.28,q:.9,vol:.11,attack:.07,wet:.12});thock({f:140,vol:.11,delay:.18});},
    open:()=>{tone(vary(360),.13,{vol:.15,slide:2.3,slideT:.045,attack:.001,wet:.18});noise(.02,{vol:.04,freq:2600,q:2});},
    close:()=>tone(vary(640),.12,{vol:.11,slide:.48,slideT:.06,attack:.001,wet:.1}),
    ok:()=>{mallet(523,{vol:.08});bell(1046.5,1,{vol:.085,delay:.02});bell(1568,1.25,{vol:.075,delay:.11});},
    bad:()=>{tone(172,.34,{vol:.17,slide:.6,slideT:.22,lp:520,attack:.002,wet:.22});tone(115,.3,{vol:.08,delay:.025,lp:400});},
    mark:i=>{const f=[523.25,587.33,659.25,783.99,880][((i|0)%5+5)%5];
      thock({f:vary(230),vol:.13});mallet(f,{vol:.13,delay:.01});bell(f*2,.45,{vol:.028,delay:.035,index:1.1,wet:.35});},
    unmark:()=>{thock({f:vary(170),vol:.09});tone(vary(620),.11,{vol:.06,slide:.62,slideT:.09,attack:.002,wet:.12});},
    dice:()=>{[0,.075,.14,.195,.24,.275].forEach((t,i)=>{noise(.032,{freq:vary(1900,.3),q:6,vol:.15-i*.012,delay:t});tone(vary(720,.25),.045,{vol:.05,type:"triangle",delay:t,attack:.001});});
      [1046.5,1318.5,1568].forEach((f,i)=>bell(f,.7,{vol:.055,delay:.4+i*.075}));},
    present:()=>{mallet(392);mallet(587,{delay:.075,vol:.12});bell(1175,.7,{vol:.035,delay:.16});},
    home:()=>{noise(.42,{freq:2800,sweep:.14,q:.7,vol:.1,attack:.05,wet:.3});mallet(440,{delay:.24,vol:.1});mallet(330,{delay:.32,vol:.1});},
    toggle:()=>{thock({f:300,vol:.08});thock({f:430,vol:.07,delay:.06});},
    tick:()=>tone(vary(2400,.02),.016,{vol:.02,type:"triangle",attack:.001})
  };
  let lastTick=0,lastPrev=0;
  return {play(k,a){if(!on||vol===0)return;const n=Date.now();
            if(k==="tick"){if(n-lastTick<45)return;lastTick=n;}
            if(k==="preview"){if(n-lastPrev<110)return;lastPrev=n;}
            try{P[k]&&P[k](a);}catch(e){}},
          get on(){return on;},set(v){on=v;ls.set("cqb_sfx",v?"1":"0");},
          get vol(){return vol;},
          setVol(v){vol=Math.max(0,Math.min(100,v|0));ls.set("cqb_vol",String(vol));
            if(master)master.gain.setTargetAtTime(gainFor(vol),ctx.currentTime,.015);}};
})();
function syncSfxBtns(){const v=SFX.vol,live=SFX.on&&v>0,ic=!live?"🔇":v<34?"🔈":v<67?"🔉":"🔊";
  document.querySelectorAll(".sfxbtn").forEach(b=>{b.textContent=ic;b.title=SFX.on?"ปิดเสียง (M)":"เปิดเสียง (M)";});
  document.querySelectorAll(".vol").forEach(r=>{r.value=v;r.classList.toggle("off",!SFX.on);r.title=`ระดับเสียง ${v}%`;});}
function toggleSfx(){SFX.set(!SFX.on);syncSfxBtns();SFX.play("toggle");}
document.querySelectorAll(".sfxbtn").forEach(b=>b.onclick=toggleSfx);
document.querySelectorAll(".vol").forEach(r=>r.addEventListener("input",()=>{
  if(!SFX.on)SFX.set(true);                       // dragging the slider un-mutes
  SFX.setVol(+r.value);syncSfxBtns();SFX.play("preview");}));
syncSfxBtns();

/* ---------- background toggle ---------- */
function setBg(on){document.body.classList.toggle("nobg",!on);ls.set("cqb_bg",on?"1":"0");}
setBg(ls.get("cqb_bg","1")!=="0");
$("#lbg").onclick=$("#bgbtn").onclick=()=>{setBg(document.body.classList.contains("nobg"));SFX.play("toggle");};

/* ---------- night mode + teaching (screen-share) mode ---------- */
function setDark(on){document.body.classList.toggle("dark",on);ls.set("cqb_dark",on?"1":"0");
  $("#ldark").textContent=on?"☀":"🌙";$("#darkbtn").textContent=on?"☀":"🌙";}
setDark(ls.get("cqb_dark","0")==="1");
$("#ldark").onclick=$("#darkbtn").onclick=()=>{setDark(!document.body.classList.contains("dark"));SFX.play("toggle");};

/* ---------- recently viewed questions (landing tile) ---------- */
let RECENT=[];try{RECENT=JSON.parse(ls.get("cqb_recent","[]"))||[];}catch(e){RECENT=[];}
function seen(q){if(!q)return;RECENT=[q.id,...RECENT.filter(x=>x!==q.id)].slice(0,8);ls.set("cqb_recent",JSON.stringify(RECENT));}

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
  tex(R);
}
/* ---- POSTER (one question at a time, deck) ---- */
function posterHtml(q,i,anim){return `<article class="poster lv-${q.diff} ${anim||""}" data-i="${i}">
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
  const q=filtered[pIdx];if(!q)return;seen(q);
  $("#deck").innerHTML=posterHtml(q,pIdx,anim);tex($("#deck"));
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
  $("#detail").innerHTML=posterHtml(filtered[i],i,"enter");seen(filtered[i]);tex($("#detail"));
}

/* ---- present modal ---- */
let mIdx=0;
function openModal(i){mIdx=i;fillModal();$("#modal").classList.add("show");SFX.play("present");}
function closeModal(){if(!$("#modal").classList.contains("show"))return;$("#modal").classList.remove("show");SFX.play("close");}
function fillModal(){
  const q=filtered[mIdx];seen(q);
  $("#mtop").innerHTML=`${idBadge(q)}${chBadge(q)}${examBadge(q)}${diffBadge(q)}`;
  $("#mbody").innerHTML=q.bodyHtml+figHtml(q);
  $("#mfoot").innerHTML=footHtml(q);
  const nb=$("#mnote");if(q.note){nb.style.display="block";nb.innerHTML="📌 "+q.note;}else nb.style.display="none";
  const ans=$("#mans");ans.classList.remove("show");
  ans.innerHTML=keyTxt(q)?`<b>เฉลยทางการ:</b> ${keyTxt(q)}`:q.solAnswer?`<b>ตอบ:</b> ${q.solAnswer}`:`ข้อนี้ไม่มีเฉลยทางการ และยังไม่มีวิธีทำ`;
  $("#msol").innerHTML=solHtml(q);tex($("#msol"));
  $("#mpos").textContent=`${mIdx+1} / ${filtered.length}`;
  const sh=$("#modal .sheet");sh.classList.remove("lv-easy","lv-medium","lv-hard");if(q.diff)sh.classList.add("lv-"+q.diff);sh.style.animation="none";void sh.offsetWidth;sh.style.animation="";
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
// one mark per question: marking a line clears any other mark in that question; tapping the marked one clears it
function markChoice(e){const li=e.target.closest(".body li");if(!li)return false;
  const on=!li.classList.contains("mk");
  li.closest(".body").querySelectorAll("li.mk").forEach(x=>x.classList.remove("mk"));
  if(on)li.classList.add("mk");SFX.play(on?"mark":"unmark",[...li.parentElement.children].indexOf(li));return true;}
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
  if(e.target.classList&&e.target.classList.contains("vol"))return;   // arrows on the volume slider adjust volume only
  const typing=/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)&&e.target.type!=="range";
  if(PD.isOpen()){if(e.key==="Escape")PD.close();return;}   // drawer open: keys stay inside it
  if(TD.isOpen()){if(e.key==="Escape")TD.close();return;}
  if(TM.isOpen()&&!typing){if(e.key==="Escape"){TM.close();return;}if(e.key===" "){e.preventDefault();TM.toggle();return;}}
  if($("#modal").classList.contains("show")){
    if(e.key==="Escape")closeModal();
    if(e.key==="ArrowLeft")step(-1);if(e.key==="ArrowRight")step(1);
    return;
  }
  if($("#expwrap").classList.contains("show")){if(e.key==="Escape")$("#expwrap").classList.remove("show");return;}
  if(typing){if(e.key==="Escape")e.target.blur();return;}
  if(!document.body.classList.contains("inapp")){if(e.key==="/"){e.preventDefault();$("#lq").focus();}else if(e.key==="m"||e.key==="M")toggleSfx();return;}
  if(e.key==="/"){e.preventDefault();$("#q").focus();return;}
  if(e.key==="m"||e.key==="M"){toggleSfx();return;}
  if(view==="poster"){
    if(e.key==="ArrowRight"){e.preventDefault();pstep(1);}
    else if(e.key==="ArrowLeft"){e.preventDefault();pstep(-1);}
    else if(e.key==="Enter"){const b=$("#deck .solbtn");if(b){e.preventDefault();b.click();}}
  }
});

/* ================= PERIODIC TABLE DRAWER + Mw CALCULATOR ================= */
const PD=(()=>{
  const RAW="H,Hydrogen,1.008|He,Helium,4.0026|Li,Lithium,6.94|Be,Beryllium,9.0122|B,Boron,10.81|C,Carbon,12.011|N,Nitrogen,14.007|O,Oxygen,15.999|F,Fluorine,18.998|Ne,Neon,20.180|Na,Sodium,22.990|Mg,Magnesium,24.305|Al,Aluminium,26.982|Si,Silicon,28.085|P,Phosphorus,30.974|S,Sulfur,32.06|Cl,Chlorine,35.45|Ar,Argon,39.948|K,Potassium,39.098|Ca,Calcium,40.078|Sc,Scandium,44.956|Ti,Titanium,47.867|V,Vanadium,50.942|Cr,Chromium,51.996|Mn,Manganese,54.938|Fe,Iron,55.845|Co,Cobalt,58.933|Ni,Nickel,58.693|Cu,Copper,63.546|Zn,Zinc,65.38|Ga,Gallium,69.723|Ge,Germanium,72.630|As,Arsenic,74.922|Se,Selenium,78.971|Br,Bromine,79.904|Kr,Krypton,83.798|Rb,Rubidium,85.468|Sr,Strontium,87.62|Y,Yttrium,88.906|Zr,Zirconium,91.224|Nb,Niobium,92.906|Mo,Molybdenum,95.95|Tc,Technetium,98|Ru,Ruthenium,101.07|Rh,Rhodium,102.91|Pd,Palladium,106.42|Ag,Silver,107.87|Cd,Cadmium,112.41|In,Indium,114.82|Sn,Tin,118.71|Sb,Antimony,121.76|Te,Tellurium,127.60|I,Iodine,126.90|Xe,Xenon,131.29|Cs,Caesium,132.91|Ba,Barium,137.33|La,Lanthanum,138.91|Ce,Cerium,140.12|Pr,Praseodymium,140.91|Nd,Neodymium,144.24|Pm,Promethium,145|Sm,Samarium,150.36|Eu,Europium,151.96|Gd,Gadolinium,157.25|Tb,Terbium,158.93|Dy,Dysprosium,162.50|Ho,Holmium,164.93|Er,Erbium,167.26|Tm,Thulium,168.93|Yb,Ytterbium,173.05|Lu,Lutetium,174.97|Hf,Hafnium,178.49|Ta,Tantalum,180.95|W,Tungsten,183.84|Re,Rhenium,186.21|Os,Osmium,190.23|Ir,Iridium,192.22|Pt,Platinum,195.08|Au,Gold,196.97|Hg,Mercury,200.59|Tl,Thallium,204.38|Pb,Lead,207.2|Bi,Bismuth,208.98|Po,Polonium,209|At,Astatine,210|Rn,Radon,222|Fr,Francium,223|Ra,Radium,226|Ac,Actinium,227|Th,Thorium,232.04|Pa,Protactinium,231.04|U,Uranium,238.03|Np,Neptunium,237|Pu,Plutonium,244|Am,Americium,243|Cm,Curium,247|Bk,Berkelium,247|Cf,Californium,251|Es,Einsteinium,252|Fm,Fermium,257|Md,Mendelevium,258|No,Nobelium,259|Lr,Lawrencium,266|Rf,Rutherfordium,267|Db,Dubnium,268|Sg,Seaborgium,269|Bh,Bohrium,270|Hs,Hassium,277|Mt,Meitnerium,278|Ds,Darmstadtium,281|Rg,Roentgenium,282|Cn,Copernicium,285|Nh,Nihonium,286|Fl,Flerovium,289|Mc,Moscovium,290|Lv,Livermorium,293|Ts,Tennessine,294|Og,Oganesson,294";
  const cat=z=>[2,10,18,36,54,86,118].includes(z)?"ng":[3,11,19,37,55,87].includes(z)?"alk":[4,12,20,38,56,88].includes(z)?"ae":[5,14,32,33,51,52].includes(z)?"md":[9,17,35,53,85,117].includes(z)?"hal":[1,6,7,8,15,16,34].includes(z)?"nm":(z>=57&&z<=71)?"ln":(z>=89&&z<=103)?"an":((z>=21&&z<=30)||(z>=39&&z<=48)||(z>=72&&z<=80)||(z>=104&&z<=112))?"tm":"pt";
  const pg=z=>{const B=[0,2,10,18,36,54,86,118];let p=1;while(z>B[p])p++;const s=z-B[p-1];let g=null,f=null;
    if(p==1)g=z==1?1:18;else if(p<=3)g=s<=2?s:s+10;else if(p<=5)g=s;else{if(s<=2)g=s;else if(s<=17)f=s-3;else g=s-14;}return{p,g,f};};
  const ELS=RAW.split("|").map((r,i)=>{const[s,n,m]=r.split(",");const z=i+1;return{z,s,n,m:+m,cat:cat(z),...pg(z)};});
  const BY={},SYM={};ELS.forEach(e=>{BY[e.z]=e;SYM[e.s]=e;});
  const fm=e=>{if(Number.isInteger(e.m))return`(${e.m})`;const d=e.m<10?3:2,f=10**d;return(Math.round(e.m*f+1e-6)/f).toFixed(d);};
  // formula -> {symbol:count}; nested ( ) [ ], leading coefficients, hydrates split by · . * •
  function parseF(str){
    const s=str.replace(/\s+/g,"").replace(/[•*.]/g,"·");if(!s)return null;const total={};
    for(const part of s.split("·")){
      if(!part)throw"มีจุด · เกินมา";let i=0;
      const num=()=>{const m=part.slice(i).match(/^\d+/);if(!m)return 1;i+=m[0].length;return +m[0];};
      const grp=close=>{const c={};
        while(i<part.length){const ch=part[i];
          if(ch=="("||ch=="["){i++;const inner=grp(ch=="("?")":"]");const n=num();for(const k in inner)c[k]=(c[k]||0)+inner[k]*n;}
          else if(ch==")"||ch=="]"){if(ch!==close)throw`วงเล็บ ${ch} ไม่มีคู่`;i++;return c;}
          else if(/[A-Z]/.test(ch)){const nx=part[i+1]||"";let sym=ch;
            if(/[a-z]/.test(nx)){if(SYM[ch+nx])sym=ch+nx;else throw`ไม่รู้จักธาตุ ${ch+nx}`;}
            if(!SYM[sym])throw`ไม่รู้จักธาตุ ${sym}`;i+=sym.length;const n=num();c[sym]=(c[sym]||0)+n;}
          else if(/\d/.test(ch))throw"ตัวเลขต้องตามหลังธาตุหรือวงเล็บ";
          else throw`อ่านไม่ออกตรง "${ch}"`;}
        if(close)throw`ขาดวงเล็บปิด ${close}`;return c;};
      const coef=num();const c=grp(null);if(!Object.keys(c).length)throw"ยังไม่มีธาตุ";
      for(const k in c)total[k]=(total[k]||0)+c[k]*coef;}
    return total;}
  const fHTML=str=>str.replace(/\s+/g,"").replace(/[•*.]/g,"·").split("·").map(p=>{const m=p.match(/^\d+/);const co=m?m[0]:"";return co+p.slice(co.length).replace(/(\d+)/g,"<sub>$1</sub>");}).join(" · ");
  let built=false,last=null;const inp=$("#pdin"),G=$("#pdg");
  function build(){
    let h="";
    ELS.forEach(e=>{const[r,c]=e.f!==null?[e.p==6?9:10,3+e.f]:[e.p,e.g];
      h+=`<div class="pde k-${e.cat}" data-z="${e.z}" style="grid-row:${r};grid-column:${c}"><i>${e.z}</i><b>${e.s}</b><s>${fm(e)}</s></div>`;});
    h+=`<div class="pdph" style="grid-row:6;grid-column:3">57–71</div><div class="pdph" style="grid-row:7;grid-column:3">89–103</div><div style="grid-row:8;grid-column:1;height:10px"></div>`;
    h+=`<div class="pdinfo"><div class="pdbig" id="pdbig"></div><div class="pdbrk" id="pdbrk"></div></div>`;
    G.innerHTML=h;
    $("#pdkeys").innerHTML=["(",")","[","]","·"].map(k=>`<button class="kp" data-k="${k}">${k}</button>`).join("")+`<span class="sep"></span>`+[..."1234567890"].map(k=>`<button data-k="${k}">${k}</button>`).join("")+`<span class="sep"></span><button class="kx" data-k="bk" title="ลบตัวสุดท้าย">⌫</button><button class="kx" data-k="clr">ล้าง</button><span class="tip">คลิกซ้าย = เพิ่มธาตุ · คลิกขวา = ลดทีละ 1</span>`;
    big(BY[1]);update();built=true;}
  const big=e=>{last=e;$("#pdbig").innerHTML=`<i>${e.z}</i>${e.s}<u>${e.n}</u><s>${fm(e)}</s>`;};
  const r2=x=>(Math.round(x*100+1e-6)/100).toFixed(2);   // half-up, so 55.845 -> 55.85 like the tile
  function update(){
    let c;G.querySelectorAll(".pde.inf").forEach(t=>t.classList.remove("inf"));
    try{c=parseF(inp.value);}catch(err){$("#pdmw").textContent="Mw = —";$("#pdfd").textContent="";$("#pdbrk").innerHTML=`<span class="err">⚠ ${err}</span>`;return;}
    if(!c){$("#pdmw").textContent="Mw = —";$("#pdfd").textContent="";$("#pdbrk").innerHTML=`<span class="hint">แตะธาตุหรือพิมพ์สูตรด้านล่าง เพื่อคำนวณมวลโมเลกุล (Mw)<br>คลิกซ้าย = เพิ่มธาตุ · คลิกขวา = ลดทีละ 1</span>`;return;}
    const tot=Object.entries(c).reduce((a,[k,n])=>a+SYM[k].m*n,0);
    $("#pdmw").textContent="Mw = "+r2(tot);$("#pdfd").innerHTML=fHTML(inp.value);
    $("#pdbrk").innerHTML=`<table><tr><th>ธาตุ</th><th>จำนวน</th><th>มวลอะตอม</th><th>รวม</th><th>% มวล</th></tr>${Object.entries(c).map(([k,n])=>{const sub=SYM[k].m*n,p=sub/tot*100;return`<tr><td>${k}</td><td>${n}</td><td>${fm(SYM[k])}</td><td>${r2(sub)}</td><td class="pc" style="--p:${p.toFixed(1)}%">${p.toFixed(2)}%</td></tr>`;}).join("")}</table>`;
    Object.keys(c).forEach(k=>{const t=G.querySelector(`.pde[data-z="${SYM[k].z}"]`);if(t)t.classList.add("inf");});}
  const put=v=>{inp.value=v;update();};
  const flash=z=>{const t=G.querySelector(`.pde[data-z="${z}"]`);if(!t)return;t.classList.remove("pdflash");void t.offsetWidth;t.classList.add("pdflash");};
  function addSym(sym){const v=inp.value,m=v.match(/([A-Z][a-z]?)(\d*)$/);
    if(m&&m[1]==sym)put(v.slice(0,v.length-m[0].length)+sym+((+m[2]||1)+1));else put(v+sym);}
  // right-click: take ONE atom of that element off its last occurrence; drop brackets left empty
  function decSym(sym){const v=inp.value,re=new RegExp(sym+"(?![a-z])(\\d*)","g");let m,hit=null;while((m=re.exec(v)))hit=m;
    if(!hit)return false;const n=+hit[1]||1;
    let nv=v.slice(0,hit.index)+(n>2?sym+(n-1):n==2?sym:"")+v.slice(hit.index+hit[0].length);
    let prev;do{prev=nv;nv=nv.replace(/\(\)\d*|\[\]\d*/g,"");}while(nv!==prev);
    put(nv.replace(/^[·.*•]+|[·.*•]+$/g,""));return true;}
  // formulas in the question on screen -> one-tap chips + pulsing elements
  function curQ(){if($("#modal").classList.contains("show"))return filtered[mIdx];
    if(!document.body.classList.contains("inapp"))return null;   // on the landing board there's no question on screen
    if(view==="poster")return filtered[pIdx];
    if(view==="pane"){const s=document.querySelector(".pane-item.sel");return s?filtered[+s.dataset.i]:null;}
    return null;}
  function refreshQ(){
    G.querySelectorAll(".pde.inq").forEach(t=>t.classList.remove("inq"));
    const q=curQ();let out=[];
    if(q){const d=document.createElement("div");d.innerHTML=(q.bodyHtml||"").replace(/<sup>[\s\S]*?<\/sup>/g," ");
      const txt=d.textContent.replace(/[₀-₉]/g,c=>"₀₁₂₃₄₅₆₇₈₉".indexOf(c)).replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]/g," ");
      for(let m of (txt.match(/[A-Z][A-Za-z0-9()\[\]]*/g)||[])){
        while(/[)\]]$/.test(m)&&(m.match(/[)\]]/g)||[]).length>(m.match(/[(\[]/g)||[]).length)m=m.slice(0,-1);
        if(m.length<2||/^[IVX]+$/.test(m)||/^K\d$/.test(m)||out.includes(m))continue;   // skip roman numerals and K1/K2 (equilibrium constants, not potassium)
        try{if(parseF(m))out.push(m);}catch(e){}}
      out=out.slice(0,8);}
    $("#pdq").innerHTML=out.length?"ในโจทย์: "+out.map(f=>`<button data-f="${f}">${fHTML(f)}</button>`).join(""):"";
    const zs=new Set();out.forEach(f=>Object.keys(parseF(f)).forEach(k=>zs.add(SYM[k].z)));
    zs.forEach(z=>{const t=G.querySelector(`.pde[data-z="${z}"]`);if(t)t.classList.add("inq");});}
  const isOpen=()=>document.body.classList.contains("pdopen");
  function open(){if(TD.isOpen())TD.close();if(!built)build();refreshQ();document.body.classList.add("pdopen");SFX.play("open");}
  function close(){if(!isOpen())return;document.body.classList.remove("pdopen");SFX.play("close");}
  // Mw on: a tap adds the element to the formula. Mw off: a tap only shows it in the big tile.
  let mwOn=ls.get("cqb_mw2","0")==="1";   // off by default; new key so the old saved "on" does not stick
  function setMw(on){mwOn=on;ls.set("cqb_mw2",on?"1":"0");$("#pd").classList.toggle("nomw",!on);
    $("#pdmwt").classList.toggle("on",on);$("#pdmwt").textContent=on?"🧮 คิด Mw: เปิด":"🧮 คิด Mw: ปิด";}
  setMw(mwOn);
  $("#pdmwt").onclick=()=>{setMw(!mwOn);SFX.play("toggle");};
  G.addEventListener("click",e=>{const t=e.target.closest(".pde");if(!t)return;const el=BY[t.dataset.z];
    if(mwOn){addSym(el.s);SFX.play("tick");}else SFX.play("click");big(el);flash(el.z);});
  G.addEventListener("contextmenu",e=>{const t=e.target.closest(".pde");if(!t||!mwOn)return;e.preventDefault();const el=BY[t.dataset.z];big(el);
    if(decSym(el.s)){flash(el.z);SFX.play("unmark");}else SFX.play("bad");});
  G.addEventListener("mouseover",e=>{const t=e.target.closest(".pde");if(t){const el=BY[t.dataset.z];$("#pdhov").textContent=`${el.s} · ${el.n} · Z ${el.z} · ${fm(el)}`;}});
  inp.addEventListener("input",update);
  $("#pdkeys").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;const k=b.dataset.k;SFX.play("click");
    if(k=="bk")put(inp.value.slice(0,-1));else if(k=="clr")put("");else put(inp.value+k);});
  $("#pdq").addEventListener("click",e=>{const b=e.target.closest("button");if(b){put(b.dataset.f);SFX.play("click");}});
  $("#pdtab").onclick=open;$("#pdx").onclick=close;$("#pdscrim").onclick=close;
  return{open,close,isOpen,parseF,curQ,load(v){open();if(!mwOn)setMw(true);put(v);}};
})();
$("#mpt").onclick=()=>PD.open();


/* ================= TOOLS DRAWER: constants · unit converter · ions ================= */
const TD=(()=>{
  let built=false;
  const K=[["N<sub>A</sub>","6.02 × 10<sup>23</sup>","mol<sup>−1</sup>","เลขอาโวกาโดร"],
    ["R","0.0821","L·atm/mol·K","ค่าคงที่ของแก๊ส"],["R","8.314","J/mol·K","ค่าคงที่ของแก๊ส (หน่วย SI)"],
    ["V<sub>m</sub>","22.4","L/mol","แก๊ส 1 mol ที่ STP (0 °C, 1 atm)"],["K<sub>w</sub>","1.0 × 10<sup>−14</sup>","","ผลคูณไอออนของน้ำ ที่ 25 °C"],
    ["F","96,500","C/mol","ค่าคงที่ฟาราเดย์"],["h","6.626 × 10<sup>−34</sup>","J·s","ค่าคงที่ของพลังค์"],
    ["c","3.00 × 10<sup>8</sup>","m/s","ความเร็วแสง"],["e","1.602 × 10<sup>−19</sup>","C","ประจุของอิเล็กตรอน"],
    ["1 atm","760","mmHg = 101.325 kPa","ความดันบรรยากาศ"],["0 °C","273.15","K","อุณหภูมิ"],
    ["1 cal","4.184","J","พลังงาน"],["1 u","1.66 × 10<sup>−24</sup>","g","หน่วยมวลอะตอม"]];
  const CV={p:{n:"ความดัน",u:{atm:1,mmHg:760,torr:760,kPa:101.325,Pa:101325,bar:1.01325}},
    t:{n:"อุณหภูมิ",temp:1,u:{"°C":0,"K":0,"°F":0}},
    v:{n:"ปริมาตร",u:{L:1,mL:1000,"cm³":1000,"dm³":1,"m³":0.001}},
    e:{n:"พลังงาน",u:{J:1,kJ:0.001,cal:1/4.184,kcal:1/4184,eV:1/1.602176634e-19}},
    m:{n:"มวล",u:{g:1,kg:0.001,mg:1000,"µg":1e6}}};
  const IONS=[["ไอออนบวก",[["NH4","+","แอมโมเนียม"],["H3O","+","ไฮโดรเนียม"],["Hg2","2+","ปรอท(I)"]]],
    ["ไอออนลบ ประจุ −1",[["OH","−","ไฮดรอกไซด์"],["CN","−","ไซยาไนด์"],["SCN","−","ไทโอไซยาเนต"],["NO3","−","ไนเทรต"],["NO2","−","ไนไทรต์"],
      ["HCO3","−","ไฮโดรเจนคาร์บอเนต"],["HSO4","−","ไฮโดรเจนซัลเฟต"],["H2PO4","−","ไดไฮโดรเจนฟอสเฟต"],["CH3COO","−","แอซีเทต"],
      ["MnO4","−","เพอร์แมงกาเนต"],["ClO","−","ไฮโพคลอไรต์"],["ClO2","−","คลอไรต์"],["ClO3","−","คลอเรต"],["ClO4","−","เพอร์คลอเรต"]]],
    ["ไอออนลบ ประจุ −2",[["CO3","2−","คาร์บอเนต"],["SO4","2−","ซัลเฟต"],["SO3","2−","ซัลไฟต์"],["HPO4","2−","ไฮโดรเจนฟอสเฟต"],
      ["CrO4","2−","โครเมต"],["Cr2O7","2−","ไดโครเมต"],["C2O4","2−","ออกซาเลต"],["S2O3","2−","ไทโอซัลเฟต"],["O2","2−","เพอร์ออกไซด์"]]],
    ["ไอออนลบ ประจุ −3",[["PO4","3−","ฟอสเฟต"]]]];
  const sub=f=>f.replace(/(\d+)/g,"<sub>$1</sub>");
  const fmtN=x=>{if(!isFinite(x))return"—";if(x===0)return"0";const a=Math.abs(x);
    if(a>=1e6||a<1e-3){const[m,e]=x.toExponential(4).split("e");return`${+m} × 10<sup>${String(+e).replace("-","−")}</sup>`;}
    return(+x.toPrecision(6)).toLocaleString("en-US",{maximumFractionDigits:6});};
  let cat="p",unit="atm";
  function cvRender(){const c=CV[cat];
    $("#cvcat").querySelectorAll("button").forEach(b=>b.classList.toggle("on",b.dataset.c===cat));
    const sel=$("#cvu");sel.innerHTML=Object.keys(c.u).map(u=>`<option${u===unit?" selected":""}>${u}</option>`).join("");cvCalc();}
  function cvCalc(){const c=CV[cat],x=parseFloat($("#cvx").value);let out="";
    if(isNaN(x)){$("#cvout").innerHTML=`<div><span>ใส่ตัวเลขด้านบน</span></div>`;return;}
    if(c.temp){const C=unit==="°C"?x:unit==="K"?x-273.15:(x-32)*5/9;const r={"°C":C,"K":C+273.15,"°F":C*9/5+32};
      for(const u in r)out+=`<div class="${u===unit?"src":""}"><b>${fmtN(r[u])}</b><span>${u}</span></div>`;}
    else{const base=x/c.u[unit];for(const u in c.u)out+=`<div class="${u===unit?"src":""}"><b>${fmtN(base*c.u[u])}</b><span>${u}</span></div>`;}
    $("#cvout").innerHTML=out;}
  function build(){
    const cols=["var(--red)","var(--blue)","var(--yel)"];
    $("#td-k").innerHTML=`<div class="kgrid">${K.map((k,i)=>`<div class="kcard" style="--c:${cols[i%3]}"><div class="ks">${k[0]}</div><div class="kval">${k[1]} <small>${k[2]}</small></div><div class="kn">${k[3]}</div></div>`).join("")}</div>
      <p class="tdnote">ค่าที่ใช้บ่อยในข้อสอบ ม.ปลาย · ถ้าโจทย์กำหนดค่าให้ ใช้ค่าตามโจทย์เสมอ</p>`;
    $("#td-cv").innerHTML=`<div class="cvcat" id="cvcat">${Object.entries(CV).map(([k,c])=>`<button data-c="${k}">${c.n}</button>`).join("")}</div>
      <div class="cvin"><input id="cvx" type="number" step="any" value="1" inputmode="decimal"><select id="cvu"></select></div><div class="cvout" id="cvout"></div>`;
    let rows="";IONS.forEach(([g,list])=>{rows+=`<tr class="grp"><td colspan="3">${g}</td></tr>`;
      list.forEach(([f,ch,n])=>{rows+=`<tr class="io" data-f="${f}"><td class="f">${sub(f)}<sup>${ch}</sup></td><td>${n}</td><td class="f">${ch}</td></tr>`;});});
    $("#td-io").innerHTML=`<table class="iontbl"><tr><th>ไอออน</th><th>ชื่อ</th><th>ประจุ</th></tr>${rows}</table>
      <p class="tdnote">แตะไอออนเพื่อส่งสูตรไปคิด Mw ในตารางธาตุ</p>`;
    $("#cvcat").onclick=e=>{const b=e.target.closest("button");if(!b)return;cat=b.dataset.c;unit=Object.keys(CV[cat].u)[0];SFX.play("click");cvRender();};
    $("#cvx").addEventListener("input",cvCalc);$("#cvu").onchange=()=>{unit=$("#cvu").value;SFX.play("click");cvCalc();};
    $("#td-io").onclick=e=>{const r=e.target.closest("tr.io");if(!r)return;close();setTimeout(()=>PD.load(r.dataset.f),120);};
    cvRender();built=true;}
  /* ----- สูตร ----- */
  const FX=DATA.formulas,FXK=Object.keys(FX).sort(),FXC=["var(--red)","var(--blue)","var(--yel)"];
  const fcol=k=>FXC[(parseInt(k)-1)%3];
  const FXS={"01":"ปลอดภัย","02":"อะตอม","03":"ตารางธาตุ","04":"พันธะ","05":"โมล","06":"สารละลาย","07":"ปริมาณสาร",
    "08":"แก๊ส","09":"อัตรา","10":"สมดุล","11":"กรดเบส","12":"ไฟฟ้า","13":"อินทรีย์","14":"พอลิเมอร์"};
  const esc=t=>String(t).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  const plain=t=>String(t).replace(/<[^>]+>/g,"").toLowerCase();
  // the chemistry chapter on screen: the open question first, else the chapter filter
  function curCh(){const q=PD.curQ();
    if(q)return q.subject!=="bio"&&q.subject!=="applied"&&FX[q.ch]?q.ch:null;
    if(!document.body.classList.contains("inapp"))return null;
    const sj=$("#fsubj").value,c=$("#fch").value;return(sj===""||sj==="chem")&&FX[c]?c:null;}
  // "a = b = c" -> ["a","= b","= c"], splitting only outside braces so fractions stay whole
  function eqParts(t){const out=[];let d=0,st=0;
    for(let i=0;i<t.length;i++){const ch=t[i];if(ch==="{")d++;else if(ch==="}")d--;
      else if(d===0&&t.startsWith(" = ",i)){out.push(t.slice(st,i).trim());st=i+1;i+=2;}}
    out.push(t.slice(st).trim());return out.map(x=>x.replace(/^=\s*/,"= ")).filter(Boolean);}
  function fcard(c){const x=c.x?`<i>เพิ่มเติม</i>`:"",srch=esc(plain([c.n,c.key,c.note,c.tex||"",(c.lines||[]).join(" "),(c.rows||[]).flat().join(" ")].join(" ")));
    if(c.k==="f")return `<div class="fc${c.w?" fhero":""}" data-s="${srch}"><div class="fm">${c.tex.split(/\\qquad/).map(t=>`<div class="fl chain">${eqParts(t.trim()).map(p=>`<span class="fp" data-tex="${esc(p)}">${esc(p)}</span>`).join("")}</div>`).join("")}</div>
      <div class="fn">${c.n}${x}</div>${c.key||c.note?`<div class="fk">${[c.key,c.note].filter(Boolean).join("<br>")}</div>`:""}</div>`;
    if(c.k==="t")return `<div class="fc wide" data-s="${srch}"><div class="fn">${c.n}${x}</div><div class="ftw"><table class="ftbl">
      <tr>${c.head.map(h=>`<th>${h}</th>`).join("")}</tr>${c.rows.map(r=>`<tr>${r.map(d=>`<td>${d}</td>`).join("")}</tr>`).join("")}</table></div>
      ${c.note?`<div class="fk">${c.note}</div>`:""}</div>`;
    return `<div class="fc wide" data-s="${srch}"><div class="fn">${c.n}${x}</div><ul>${c.lines.map(l=>`<li>${l}</li>`).join("")}</ul>
      ${c.note?`<div class="fk">${c.note}</div>`:""}</div>`;}
  function fxTex(){if(!window.katex)return;
    document.querySelectorAll("#td-fx .fp[data-tex]:not(.done)").forEach(el=>{
      try{katex.render(el.dataset.tex,el,{displayMode:false,throwOnError:false,strict:false});el.classList.add("done");}catch(e){}});fxFit();}
  // a long formula shrinks to fit its card instead of scrolling sideways (only measurable while visible)
  function fxFit(){const pane=$("#td-fx");if(!pane||!pane.classList.contains("on")||!isOpen())return;
    pane.querySelectorAll(".fm").forEach(fm=>{if(fm.offsetParent===null)return;fm.querySelectorAll(".fl").forEach(l=>l.style.fontSize="");
      let k=1;while(fm.scrollWidth>fm.clientWidth+1&&k>.62){k-=.06;fm.querySelectorAll(".fl").forEach(l=>l.style.fontSize=k+"em");}});}
  addEventListener("resize",()=>{clearTimeout(fxFit.t);fxFit.t=setTimeout(fxFit,150);});
  const texWas=window.texReady;window.texReady=()=>{texWas&&texWas();fxTex();};
  let fxFor;
  function fxRender(){const cur=curCh();
    $("#fxtabb").textContent=cur?`สูตร · บท ${+cur}`:"สูตร";
    if(fxFor===cur&&$("#fxlist"))return;fxFor=cur;
    const order=cur?[cur,...FXK.filter(k=>k!==cur)]:FXK;
    $("#td-fx").innerHTML=`<div class="fxbar"><input id="fxq" placeholder="ค้นหาสูตร เช่น pH · แก๊ส · Ka · ครึ่งชีวิต" autocomplete="off" spellcheck="false">
      <div class="fxchips" id="fxchips">${FXK.map(k=>`<button data-j="${k}" class="${k===cur?"cur":""}" style="--c:${fcol(k)}" title="${DATA.chapters[k]}"><b>${+k}</b> ${FXS[k]||""}</button>`).join("")}</div></div>
      <div id="fxlist">${order.map(k=>`<section class="fsec${k===cur?" cur":""}" id="fx-${k}" style="--c:${fcol(k)}">
        <div class="fsh"><span class="fno">${+k}</span><div><b>${DATA.chapters[k]}</b>${k===cur?`<span class="fcur">บทที่กำลังดูอยู่</span>`:""}</div>
        <span class="fct">${FX[k].length} รายการ</span></div><div class="fgrid">${FX[k].map(fcard).join("")}</div></section>`).join("")}</div>
      <div class="fxnone" id="fxnone" style="display:none">ไม่พบสูตรที่ค้นหา</div>
      <p class="tdnote">แท็ก <b>เพิ่มเติม</b> = เกินหลักสูตรแกน ใช้ในสอวน. / ข้อสอบที่ยากขึ้น · ถ้าโจทย์กำหนดค่าคงที่ให้ ใช้ค่าตามโจทย์</p>`;
    fxTex();fxFit();
    $("#fxq").addEventListener("input",fxFilter);
    $("#fxchips").onclick=e=>{const b=e.target.closest("button");if(!b)return;SFX.play("click");
      const sec=$("#fx-"+b.dataset.j);if(sec&&sec.style.display!=="none")sec.scrollIntoView({behavior:"smooth",block:"start"});};}
  function fxFilter(){const t=$("#fxq").value.trim().toLowerCase();let any=false;
    document.querySelectorAll("#fxlist .fsec").forEach(sec=>{let n=0;
      sec.querySelectorAll(".fc").forEach(c=>{const on=!t||c.dataset.s.includes(t);c.style.display=on?"":"none";if(on)n++;});
      const on=n>0||(!!t&&plain(DATA.chapters[sec.id.slice(3)]).includes(t));
      if(on&&!n)sec.querySelectorAll(".fc").forEach(c=>c.style.display="");
      sec.style.display=on?"":"none";any=any||on;
      const chip=$(`#fxchips [data-j="${sec.id.slice(3)}"]`);chip&&chip.classList.toggle("dim",!on);});
    $("#fxnone").style.display=any?"none":"";}

  const isOpen=()=>document.body.classList.contains("tdopen");
  function open(){if(PD.isOpen())PD.close();if(!built)build();
    const was=fxFor;fxRender();if(was!==fxFor)$("#td").scrollTop=0;
    document.body.classList.add("tdopen");fxFit();SFX.play("open");}
  function close(){if(!isOpen())return;document.body.classList.remove("tdopen");SFX.play("close");}
  $("#tdtabs").onclick=e=>{const b=e.target.closest("button");if(!b)return;SFX.play("click");
    $("#tdtabs").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x===b));
    document.querySelectorAll(".tdpane").forEach(p=>p.classList.toggle("on",p.id==="td-"+b.dataset.t));fxFit();};
  $("#tdtab").onclick=open;$("#tdx").onclick=close;
  $("#pdscrim").onclick=()=>{PD.close();close();TM.close();};
  return{open,close,isOpen};
})();

/* ================= SIMPLE TIMER (right panel) ================= */
const TM=(()=>{
  let mode="down",total=300,left=300,up=0,running=false,t0=0,base=0,iv=null,rang=false;
  const fmt=x=>{x=Math.max(0,Math.round(x));const h=Math.floor(x/3600),m=Math.floor(x%3600/60),sec=x%60;
    return(h?h+":"+String(m).padStart(2,"0"):String(m).padStart(2,"0"))+":"+String(sec).padStart(2,"0");};
  const PRE=[1,3,5,10,15,30];
  $("#tmpre").innerHTML=PRE.map(m=>`<button data-m="${m}">${m} นาที</button>`).join("");
  function cur(){const el=running?(Date.now()-t0)/1000:0;return mode==="down"?Math.max(0,left-el):up+el;}
  function draw(){const v=cur();$("#tmdig").textContent=fmt(mode==="down"?Math.ceil(v-1e-9):Math.floor(v));
    $("#tmbar").style.width=(mode==="down"&&total?v/total*100:0)+"%";
    $("#tmpre").querySelectorAll("button").forEach(b=>b.classList.toggle("on",mode==="down"&&+b.dataset.m*60===total));
    const tab=$("#tmtab");tab.classList.toggle("run",running);tab.textContent=running?"⏱ "+$("#tmdig").textContent:"จับเวลา";
    $("#tmgo").textContent=running?"⏸ พัก":"▶ เริ่ม";$("#tmgo").classList.toggle("pause",running);
    const mi=$("#tmmini");$("#tmmd").textContent=$("#tmdig").textContent;$("#tmmbar").style.width=$("#tmbar").style.width;
    $("#tmmgo").textContent=running?"⏸":"▶";$("#tmmgo").classList.toggle("pause",running);mi.classList.toggle("up",mode==="up");mi.classList.toggle("run",running);
    if(running&&mode==="down"&&v<=0)ring();}
  function ring(){running=false;clearInterval(iv);left=0;rang=true;$("#tmface").classList.remove("done");void $("#tmface").offsetWidth;$("#tmface").classList.add("done");
    $("#tmmini").classList.remove("done");void $("#tmmini").offsetWidth;$("#tmmini").classList.add("done");
    [0,380,760].forEach(d=>setTimeout(()=>SFX.play("ok"),d));draw();}
  function start(){if(mode==="down"&&left<=0)left=total;rang=false;$("#tmface").classList.remove("done");$("#tmmini").classList.remove("done");
    running=true;t0=Date.now();clearInterval(iv);iv=setInterval(draw,200);SFX.play("click");draw();}
  function pause(){const el=(Date.now()-t0)/1000;if(mode==="down")left=Math.max(0,left-el);else up+=el;running=false;clearInterval(iv);SFX.play("click");draw();}
  function reset(){running=false;clearInterval(iv);left=total;up=0;$("#tmface").classList.remove("done");$("#tmmini").classList.remove("done");SFX.play("unmark");draw();}
  function setMode(m){if(running)pause();mode=m;document.getElementById("tm").classList.toggle("tm-up",m==="up");
    $("#tmseg").querySelectorAll("button").forEach(b=>b.classList.toggle("on",b.dataset.m===m));SFX.play("toggle");draw();}
  function setTotal(sec){if(running)return;total=Math.max(10,Math.min(5*3600,sec));left=total;$("#tmface").classList.remove("done");SFX.play("click");draw();}
  const isOpen=()=>document.body.classList.contains("tmopen");
  function open(){document.body.classList.add("tmopen");SFX.play("open");}
  function close(){if(!isOpen())return;document.body.classList.remove("tmopen");SFX.play("close");}
  $("#tmgo").onclick=()=>running?pause():start();$("#tmreset").onclick=reset;
  $("#tmseg").onclick=e=>{const b=e.target.closest("button");if(b&&b.dataset.m!==mode)setMode(b.dataset.m);};
  $("#tmpre").onclick=e=>{const b=e.target.closest("button");if(b)setTotal(+b.dataset.m*60);};
  document.querySelector(".tmadj").onclick=e=>{const b=e.target.closest("button");if(b)setTotal(total+ +b.dataset.a);};
  $("#tmtab").onclick=()=>isOpen()?close():open();$("#tmx").onclick=close;
  // corner widget: a bigger always-visible clock, switched from the panel, remembered
  function setMini(on){$("#tmmini").classList.toggle("show",on);$("#tmfull").classList.toggle("on",on);
    $("#tmfull").textContent=on?"✓ นาฬิกามุมจอ (กดเพื่อซ่อน)":"⧉ แสดงนาฬิกามุมจอ";ls.set("cqb_tmmini",on?"1":"0");}
  $("#tmfull").onclick=()=>{setMini(!$("#tmmini").classList.contains("show"));SFX.play("toggle");};
  $("#tmmx").onclick=()=>{setMini(false);SFX.play("close");};
  $("#tmmgo").onclick=()=>running?pause():start();$("#tmmreset").onclick=reset;$("#tmmd").onclick=()=>isOpen()?close():open();
  setMini(ls.get("cqb_tmmini","0")==="1");
  draw();
  return{open,close,isOpen,toggle:()=>running?pause():start()};
})();

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
  });
  if(DATA.biocount){const qs=Q.filter(q=>q.subject==="bio"),cv=cov(qs);
    h+=`<button class="tile c-blue w2" data-go="bio" style="--i:${i++}"><span class="no">ชีวะ</span><span class="nm">ชีววิทยา</span><span class="ct">${DATA.biocount} ข้อ${cv?` · วิธีทำ ${cv}%`:""}</span><span class="cov"><i style="width:${cv}%"></i></span></button>`;}
  if(DATA.appcount){const qs=Q.filter(q=>q.subject==="applied"),cv=cov(qs);
    h+=`<button class="tile c-red" data-go="applied" style="--i:${i++}"><span class="no">✦</span><span class="nm">เคมีประยุกต์</span><span class="ct">${DATA.appcount} ข้อ</span><span class="cov"><i style="width:${cv}%"></i></span></button>`;}
  if(SC.flag) h+=`<button class="tile c-card" data-go="flag" style="--i:${i++}"><span class="no">⚠</span><span class="nm">วิธีทำไม่ฟันธง</span><span class="ct">${SC.flag} ข้อ</span></button>`;
  if(SC.unchecked) h+=`<button class="tile c-yel" data-go="unchecked" style="--i:${i++}"><span class="no">✓?</span><span class="nm">ยังไม่ตรวจวิธีทำ</span><span class="ct">${SC.unchecked} ข้อ</span></button>`;
  const rq=RECENT.map(id=>DATA.questions.find(x=>x.id===id)).filter(Boolean);
  h+=`<div class="tile c-card w2 recent" style="--i:${i++}"><span class="no">🕘</span><span class="nm">เพิ่งดู</span>${rq.length
    ?`<div class="rl">${rq.map(q=>`<button data-go="qid" data-q="${q.id}" title="${(q.snippet||"").replace(/<[^>]+>/g,"").replace(/"/g,"&quot;").slice(0,90)}">${q.id.slice(2)} · ${q.subject==="bio"?"ชีวะ":q.subject==="applied"?"ประยุกต์":"บท "+parseInt(q.ch)}</button>`).join("")}</div>`
    :`<span class="empty-r">เปิดข้อไหนก็ได้ แล้วจะมาอยู่ที่นี่</span>`}</div>`;
  $("#board").innerHTML=h;packBoard();
}
/* Place tiles in order (same rule as CSS sparse auto-placement) at explicit cells, then fill
   every cell left empty -- a wide tile that doesn't fit at a row end leaves one -- with a filler. */
let boardCols=0;
function packBoard(){
  const B=$("#board");B.querySelectorAll(".tile.deco").forEach(x=>x.remove());
  const cols=getComputedStyle(B).gridTemplateColumns.split(" ").filter(Boolean).length;boardCols=cols;
  const occ=[],used=(r,c)=>occ[r]&&occ[r][c];
  const fits=(r,c,w,h)=>{if(c+w>cols)return false;for(let y=r;y<r+h;y++)for(let x=c;x<c+w;x++)if(used(y,x))return false;return true;};
  let r=0,c=0;
  [...B.children].forEach(el=>{const cl=el.classList,big=cl.contains("hero")||cl.contains("big");
    const w=Math.min(cols,big||cl.contains("w2")?2:1),h=big||cl.contains("h2")?2:1;
    let pr=r,pc=c;while(!fits(pr,pc,w,h)){if(++pc>=cols){pc=0;pr++;}}
    for(let y=pr;y<pr+h;y++){occ[y]=occ[y]||[];for(let x=pc;x<pc+w;x++)occ[y][x]=1;}
    el.style.gridRow=`${pr+1} / span ${h}`;el.style.gridColumn=`${pc+1} / span ${w}`;
    r=pr;c=pc+w;if(c>=cols){c=0;r++;}});
  let k=0,f="";
  for(let y=0;y<occ.length;y++)for(let x=0;x<cols;x++)if(!used(y,x)){
    f+=`<div class="tile deco d${(k*2+y)%5}" style="grid-row:${y+1};grid-column:${x+1};--i:${y*cols+x}"></div>`;k++;}
  B.insertAdjacentHTML("beforeend",f);
}
window.addEventListener("resize",()=>{if(document.body.classList.contains("inapp"))return;
  const n=getComputedStyle($("#board")).gridTemplateColumns.split(" ").filter(Boolean).length;if(n!==boardCols)packBoard();});
/* ---- search straight from the board: text / formula / Q-id ("38" or "q38" -> Q-0038) ---- */
function lsNorm(v){v=v.trim();const m=v.match(/^(?:q-?)?0*(\d{1,4})$/i);
  if(m){const id="Q-"+m[1].padStart(4,"0");if(DATA.questions.some(x=>x.id===id))return id;}return v;}
function lsCount(v){const t=v.trim().toLowerCase();if(!t)return -1;return DATA.questions.filter(x=>x.search.includes(t)||x.id.toLowerCase().includes(t)).length;}
function lsGo(){
  const v=lsNorm($("#lq").value),n=lsCount(v),box=$("#lsearch");if(n<0)return;
  if(!n){SFX.play("bad");box.classList.remove("shake");void box.offsetWidth;box.classList.add("shake");return;}
  const r=box.getBoundingClientRect();SFX.play("tile");setTimeout(()=>SFX.play("whoosh"),70);
  enterApp(r.left+r.width/2,r.top+r.height/2,()=>{resetFilters();$("#q").value=v;apply();});
  $("#lq").value="";$("#lct").textContent="";$("#lq").blur();}
$("#lq").addEventListener("input",()=>{const v=lsNorm($("#lq").value),n=lsCount(v);$("#lct").textContent=n<0?"":v!==$("#lq").value.trim()?v:`${n} ข้อ`;});
$("#lq").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();lsGo();}});
$("#lgo").onclick=lsGo;
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
    else if(g==="qid"){$("#q").value=t.dataset.q;}
    apply();
    if(g==="random"&&filtered.length){setTimeout(()=>SFX.play("dice"),250);setTimeout(()=>openModal(Math.floor(Math.random()*filtered.length)),650);}
  });
});
$("#home").onclick=()=>{SFX.play("home");document.body.classList.remove("inapp");$("#app").classList.remove("show");window.scrollTo(0,0);buildBoard();};
buildBoard();
</script></body></html>"""

open(OUT,"w",encoding="utf-8").write(HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False)))
print("wrote", OUT, "-", len(questions), "questions -", len(examcount), "exam type(s)")
