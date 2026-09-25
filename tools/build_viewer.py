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
 "ex":     ("แบบฝึกหัด",    "#141414"),   # Prat's own exercises (worksheet-generator), not an exam paper
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

# ---------- chem sub-topics (concepts/subtopics.json) ----------
# {"chapters":{"7":{"topics":[{id,th}],"q":{"Q-NNNN":[main, extra...]}}}} -- v2 lists the MAIN sub-topic first, then
# up to 2 extras the question also needs; v1 files hold a bare "topicId" string (read as a 1-item list). Chapter keys
# have no leading zero, so they are re-keyed "07" to match CHAPTERS. q["topics"] carries the list to the page; a
# question counts under EVERY topic in it. Optional: no file -> no topics -> the stats slide + sub-topic filter hide.
SUBTOP = os.path.join(ROOT, "concepts", "subtopics.json")
subtopics = {}
for q in questions: q["topics"] = []
if os.path.isfile(SUBTOP):
    qtopic = {}
    for k, v in json.load(open(SUBTOP, encoding="utf-8")).get("chapters", {}).items():
        ck = "%02d" % int(k)
        subtopics[ck] = v["topics"]
        ids = {t["id"] for t in v["topics"]}
        for qid, ts in v.get("q", {}).items():
            ts = [t for t in dict.fromkeys([ts] if isinstance(ts, str) else ts) if t in ids]
            if ts: qtopic[qid] = (ck, ts)
    for q in questions:
        ck, ts = qtopic.get(q["id"], ("", []))
        if q["subject"] not in ("bio", "applied") and ck == q["ch"]: q["topics"] = ts
    print("sub-topics:", sum(1 for q in questions if q["topics"]), "/", chemcount, "chem questions tagged,",
          sum(1 for q in questions if len(q["topics"]) > 1), "multi-tagged")

# ---------- Prat's own exercises: worksheet-generator/chapters/*.py, read AT BUILD TIME ----------
# That folder stays the source of truth -- nothing is copied into question-bank.md. Each file defines
# CHAPTER = {id, title, sections:[(title, [(ง่าย|กลาง|ยาก, question_text, box_mm, solution_html), ...])]}.
# EX_MAP puts a worksheet chapter under a bank chapter (unknown id -> skipped with a warning); sub-topics come from
# concepts/exercise-topics.json. They join `questions` as exam "ex" with Prat's worked solution as the solution --
# flagged ⚠ (solFlag + solPending, "not yet verified") while the file's leading # comment block contains "PENDING";
# delete that line once the answers are checked and the next build shows them as verified.
# present / chemcount above were counted before this, so the landing tiles and hero stay exams-only.
# No worksheet folder -> no exercises, the feature is simply absent.
EX_DIR = os.path.join(os.path.dirname(ROOT), "worksheet-generator", "chapters")
EX_MAP = {"mol": "05", "กรดเบส": "11"}
EX_DIFF = {"ง่าย": "easy", "กลาง": "medium", "ยาก": "hard"}
EX_TOP = os.path.join(ROOT, "concepts", "exercise-topics.json")
_EX_ANS = re.compile(r"(?:<br>\s*)?<b>ตอบ\s*(.+?)</b>\s*$", re.S)   # a trailing "ตอบ ..." line -> the answer box
exercises = []
if os.path.isdir(EX_DIR):
    extop = json.load(open(EX_TOP, encoding="utf-8")) if os.path.isfile(EX_TOP) else {}
    for fn in sorted(os.listdir(EX_DIR)):
        if not fn.endswith(".py"): continue
        ns, src = {}, open(os.path.join(EX_DIR, fn), encoding="utf-8").read()   # own namespace: the file only builds a dict
        exec(compile(src, fn, "exec"), ns)
        pending = "PENDING" in re.match(r"(?:[ \t]*#.*\n)*", src).group()   # header comment says answers aren't verified
        C = ns.get("CHAPTER") or {}
        ck = EX_MAP.get(C.get("id"))
        if not ck:
            print("WARNING: exercise chapter", ascii(C.get("id")), "from", ascii(fn), "has no EX_MAP entry - skipped"); continue
        ids, n = {t["id"] for t in subtopics.get(ck, [])}, 0
        for sec, items in C.get("sections", []):
            for diff, qtext, _box, sol in items:
                n += 1
                eid = "E-%s-%02d" % (C["id"], n)
                ts = [t for t in dict.fromkeys(extop.get(eid, [])) if t in ids]
                if not ts: print("WARNING: exercise", ascii(eid), "has no valid sub-topic")
                m = _EX_ANS.search(sol)
                exercises.append({
                    "id": eid, "ch": ck, "chName": CHAPTERS[ck], "subject": "", "bio": "", "app": "",
                    "groupKey": "ch-" + ck, "groupLabel": f"บทที่ {int(ck)} · {CHAPTERS[ck]}",
                    "exam": "ex", "year": "", "ver": "", "diff": EX_DIFF.get(diff, ""), "type": "open",
                    "bodyHtml": "<p>%s</p>" % _html.escape(qtext, quote=False),   # question is plain text, solution is HTML
                    "snippet": _html.escape(qtext[:90], quote=False),
                    "answer": "", "source": f"แบบฝึกหัด {C.get('title', '')} · {sec} · ข้อ {n}",
                    "note": "", "figure": "", "search": " ".join((qtext, sec, "แบบฝึกหัด", C.get("title", ""))).lower(),
                    "solHtml": sol[:m.start()] if m else sol, "solAnswer": m.group(1).strip() if m else "",
                    "solFlag": pending, "solPending": pending, "solChecked": not pending, "topics": ts,
                })
    questions += exercises
    questions.sort(key=lambda q: (*_sortkey(q)[:2], q["exam"] == "ex", q["id"]))   # "E-" < "Q-": keep exams first per chapter
    if exercises: examcount["ex"] = len(exercises)
    print("exercises:", len(exercises), "| unverified (PENDING):", sum(e["solPending"] for e in exercises), {k: sum(1 for e in exercises if e["ch"] == k) for k in sorted({e["ch"] for e in exercises})})

data = {
 "questions": questions, "chapters": CHAPTERS, "solcount": solcount,
 "bioChapters": BIO_CHAPTERS, "appTopics": APP_TOPICS,
 "exams": {k:{"label":v[0],"color":v[1]} for k,v in EXAMS.items()},
 "years": sorted({q["year"] for q in questions if q["year"]}),
 "types": sorted({q["type"] for q in questions if q["type"]}),
 "counts": present, "examcount": examcount,
 "chemcount": chemcount, "biocount": biocount, "appcount": appcount,
 "biocounts": biocounts, "appcounts": appcounts,
 "formulas": FORMULAS, "subtopics": subtopics,
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
:root{--sh:#141414;--paper:#efe9dc;--card:#fffdf7;--ink:#141414;--red:#e4412b;--blue:#1f3fbf;--yel:#f2b705;--mut:#6b6457;--line:#141414;--acc:#f2b705;--stbg:#fcebb8;--sxbg:#fef7e1;--sxbd:#8a8886;--exg:rgba(20,20,20,.055)}
/* registered as colors so a subject / night-mode swap can TRANSITION the tokens themselves: every
   var(--x) user fades together, without touching any element's own transition list */
@property --paper{syntax:"<color>";inherits:true;initial-value:#efe9dc}
@property --card{syntax:"<color>";inherits:true;initial-value:#fffdf7}
@property --ink{syntax:"<color>";inherits:true;initial-value:#141414}
@property --red{syntax:"<color>";inherits:true;initial-value:#e4412b}
@property --blue{syntax:"<color>";inherits:true;initial-value:#1f3fbf}
@property --yel{syntax:"<color>";inherits:true;initial-value:#f2b705}
@property --mut{syntax:"<color>";inherits:true;initial-value:#6b6457}
@property --sh{syntax:"<color>";inherits:true;initial-value:#141414}
@property --acc{syntax:"<color>";inherits:true;initial-value:#f2b705}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;font-family:"Anuphan","Sarabun","Segoe UI",Tahoma,sans-serif;background:var(--paper);color:var(--ink);font-size:16px;
  transition:--paper .5s,--card .5s,--ink .5s,--red .5s,--blue .5s,--yel .5s,--mut .5s,--sh .5s,--acc .5s}
@media(prefers-reduced-motion:reduce){body{transition:none}}
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
/* --cols is the column count packBoard reads: the computed grid-template-columns also lists the implicit tracks
   explicitly placed tiles create, so after a 6-col layout it kept reporting 6 on a 4- or 2-col screen (no repack) */
.board{--cols:6;display:grid;grid-template-columns:repeat(var(--cols),1fr);grid-auto-rows:150px;grid-auto-flow:row;gap:6px;background:var(--ink);border:6px solid var(--ink)}
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
.c-red{background:var(--red);color:#fff}.c-yel{background:var(--yel)}.c-blue{background:var(--blue);color:#fff}.c-ink{background:var(--ink);color:var(--paper)}.c-card{background:var(--card)}.c-acc{background:var(--acc);color:#141414}
.hero{grid-column:span 2;grid-row:span 2;background:var(--card);cursor:default;padding:0;touch-action:pan-y;user-select:none;-webkit-user-select:none;outline-offset:-5px}
.hero:focus-visible{outline:3px solid var(--red)}
/* subject selector: a 2-panel track slid by translateX; the drag follows the finger, release snaps */
.htrack{position:relative;height:100%}
.hpanel{position:absolute;inset:0;transition:transform .45s cubic-bezier(.2,.9,.3,1);display:flex;flex-direction:column;justify-content:flex-end;gap:4px;padding:14px 16px}
.hero b{font-size:4.6rem;font-weight:800;line-height:.9;color:var(--red);display:flex;align-items:center;gap:.14em}
.hero b .sic{width:.8em;height:.8em;color:var(--ink)}   /* subject icon beside the count: ink body + accent in var(--red) */
.hero span{font-size:1.5rem;font-weight:800;line-height:1.15}
.hero small{font-size:.8rem;color:var(--mut);margin-top:6px;line-height:1.5}
.hnav{position:absolute;top:10px;left:16px;right:12px;display:flex;gap:4px;z-index:2}
.hnav button{border:2px solid var(--ink);background:var(--card);color:var(--ink);font:800 .82rem "Anuphan",sans-serif;height:32px;padding:0 10px;cursor:pointer}
.hnav .harr{width:34px;padding:0;font-size:1.05rem}.hnav .hsp{margin-left:auto}
.hnav .hdot.on{background:var(--ink);color:var(--paper)}
.hnav .hdot{display:inline-flex;align-items:center;gap:5px}.hnav .hdot .sic{width:18px;height:18px}
.sic{flex:none;display:block}
@media(prefers-reduced-motion:reduce){.hpanel{transition:none}}
.tile.deco{cursor:default}
.d0{background:radial-gradient(circle at 100% 100%,var(--blue) 0 58%,transparent 59%),var(--paper)}
.d1{background:repeating-linear-gradient(45deg,var(--yel) 0 18px,var(--ink) 18px 36px)}
.d2{background:radial-gradient(circle at 50% 50%,var(--red) 0 32%,transparent 33%),var(--card)}
.d3{background:linear-gradient(var(--yel),var(--yel)) center/40% 40% no-repeat,var(--ink)}
.d4{background:var(--card)}.d4:after{content:"";position:absolute;inset:24%;background:var(--blue);clip-path:polygon(50% 0,100% 100%,0 100%)}
.sec-t{grid-column:1/-1;background:var(--ink);color:var(--paper);font-weight:800;letter-spacing:.2em;font-size:.72rem;padding:6px 14px;display:flex;align-items:center;animation:none}
.board .sec-t{grid-row:span 1;height:auto}
.lfoot{margin-top:14px;font-size:.8rem;color:var(--mut)}
@media(max-width:900px){.board{--cols:4}}
@media(max-width:560px){.board{--cols:2;grid-auto-rows:130px}.tile.w2,.hero{grid-column:span 2}.lhead h1{font-size:1.8rem}.tile.big .no{font-size:3.2rem}}

/* circle reveal between landing and app */
#app{display:none}
#app.show{display:block}
/* the poster deck's tilted backing cards poke a few px past a phone's edge: clip them at the screen edge (clip, not
   hidden: no scroll box). Only in poster view, and on a full-width wrapper BELOW the header -- never on an ancestor
   of anything sticky: iPad Safari shakes a sticky element inside a one-axis overflow clip while it scrolls
   (WebKit bug 247130: the clip layer's "infinite" rect loses float precision, worse the longer the page) */
#appbody.clipx{overflow-x:clip}
#app.opening{clip-path:circle(0 at var(--x,50%) var(--y,50%));animation:reveal .65s cubic-bezier(.7,0,.2,1) forwards}
@keyframes reveal{to{clip-path:circle(150% at var(--x,50%) var(--y,50%))}}
body.inapp #landing{display:none}

/* ================= APP HEADER ================= */
header{position:sticky;top:0;z-index:20;background:var(--ink);color:var(--paper)}
.bar1{display:flex;align-items:stretch;flex-wrap:wrap;max-width:1180px;margin:0 auto}
.home{border:0;background:var(--red);color:#fff;font-weight:800;padding:0 16px;font-size:.9rem;display:flex;align-items:center;gap:6px}
.home:hover{background:color-mix(in srgb,var(--red) 86%,#000)}
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
/* sub-topic (chem only): tinted with the palette accent so it reads apart from the dashed chapter badge; a tap
   filters to it (a plain <span> label in present mode). white-space:normal: a long name drops to its own line
   first and only breaks inside when even that line is too narrow */
.b-st{background:var(--stbg);color:var(--ink);font-family:inherit;white-space:normal;text-align:left}
button.b-st{cursor:pointer}button.b-st:hover{background:var(--acc);color:#141414}
.row-h .b-st{display:block;flex:0 1 auto;min-width:0;max-width:30%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}   /* one line in a list row */
/* extra sub-topics (a question that also needs another skill): same badge, paler, so the main one leads */
.b-st.b-sx{background:var(--sxbg);border-color:var(--sxbd);font-weight:600}
.b-more{background:var(--card);color:var(--ink);border-style:dotted;font-family:"JetBrains Mono";cursor:pointer;flex:0 0 auto}
.row-h .b-st.b-sx,.row-h.allst .b-more{display:none}   /* list row: main + "+N"; the chip unfolds the rest onto a wrapped line */
.row-h.allst{flex-wrap:wrap}.row-h.allst .b-st.b-sx{display:block}.row-h.allst .b-st{max-width:100%}
@media(max-width:480px){.row-h:has(.b-more){gap:6px}.row-h .b-more{padding:2px 5px}}   /* phone: the chip's room comes out of the gaps, not the main badge */
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
.sheet .mtop{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:16px;padding-right:104px}
.sheet .mtop .badge{white-space:normal}   /* a long chapter name wraps instead of running under ✎ ✕ on a phone */
.sheet .body{font-size:1.38rem;line-height:1.85}
/* save-as-image: an off-screen copy of the sheet (badges + question + choices), fixed width so every PNG matches */
.shotwrap{position:fixed;left:0;top:0;box-sizing:border-box;opacity:0;z-index:-1;pointer-events:none;width:1100px;padding:28px 46px 46px 28px;background:var(--paper)}
.shotsd{position:absolute}
.sheet.shot{box-shadow:none;max-height:none;overflow:visible;animation:none!important;max-width:none;width:100%;padding:34px 40px 30px 54px}
.sheet.shot .body{font-size:1.38rem}.sheet.shot .body img{max-width:100%;height:auto}.sheet.shot .mtop{padding-right:0}
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
/* poster-pen: two canvases over the sheet's content (highlighter under pen); inert until write mode (✎ beside ✕, or P)
   is on. The controls (✕ ✎, ◀ ▶ row, ดูวิธีทำ) sit above them so they stay clickable while writing. The tool bar
   floats in the modal's bottom padding, which is always reserved, so showing/hiding it never moves the question.
   While writing nothing in the modal is selectable: iPad double-tap otherwise grabs the nearest text (it took ✎). */
.modal{flex-direction:column;padding-bottom:84px}
.mink{position:relative}
.mink canvas{position:absolute;left:0;top:0;z-index:2;pointer-events:none}
#inkhl,#bhl{mix-blend-mode:multiply}body.dark #inkhl,body.dark #bhl{mix-blend-mode:screen}
#modal.inking #inkpen,#modal.inking #bpen{pointer-events:auto;touch-action:pan-x pan-y;cursor:crosshair}
#modal.inking,#modal .x,.inkbar{-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}
#modal button{touch-action:manipulation}
.sheet .x{z-index:3}.mctrl,#modal .solbtn{position:relative;z-index:3}
.sheet .inkw{right:66px;background:var(--card);color:var(--ink);font-size:1.3rem;transition:background .15s,color .15s}
.sheet .inkw.on{background:var(--yel);color:#141414}
.inkbar{position:absolute;left:50%;bottom:18px;display:flex;gap:3px;background:var(--card);border:3px solid var(--ink);box-shadow:5px 5px 0 var(--sh);padding:4px;
  opacity:0;visibility:hidden;pointer-events:none;transform:translate(-50%,14px);transition:opacity .2s,transform .2s,visibility 0s .2s}
.inkbar.show{opacity:1;visibility:visible;pointer-events:auto;transform:translate(-50%,0);transition:opacity .2s,transform .2s}
.inkbar button{width:32px;height:32px;padding:0;border:2px solid var(--ink);background:var(--card);color:var(--ink);font-size:1rem;display:grid;place-items:center}
.inkbar button.sel{background:var(--yel);color:#141414}
.inkbar .dot{width:18px;height:18px;border-radius:50%;border:2px solid var(--ink)}
/* split-scratch (▦ in the ink bar): question | draggable bar | grid-paper board; stacked in portrait.
   --sq is the question's size in px, set by JS from a remembered ratio and clamped to the current screen. */
.mdiv,.mboard{display:none}
#modal.split{flex-direction:row;align-items:stretch;justify-content:flex-start;background:var(--paper)}
#modal.split .sheet{flex:0 0 var(--sq,38%);min-width:0;min-height:0;max-width:none;max-height:none;padding:24px 22px 20px 34px;box-shadow:6px 6px 0 var(--red)}
#modal.split .sheet.lv-medium{box-shadow:6px 6px 0 var(--yel)}#modal.split .sheet.lv-easy{box-shadow:6px 6px 0 var(--blue)}
#modal.split .sheet .body{font-size:1.2rem}
#modal.split .mdiv{display:grid;place-items:center;flex:none;width:28px;touch-action:none;cursor:col-resize;-webkit-user-select:none;user-select:none}
.mdiv:after{content:"";width:8px;height:72px;background:var(--ink)}
#modal.split .mboard{display:block;position:relative;flex:1 1 0;min-width:0;min-height:0;overflow:hidden;border:3px solid var(--ink);box-shadow:6px 6px 0 var(--sh);
  background:linear-gradient(var(--gr) 1px,transparent 1px) 0 0/28px 28px,linear-gradient(90deg,var(--gr) 1px,transparent 1px) 0 0/28px 28px,var(--card)}
.mboard{--gr:color-mix(in srgb,var(--ink) 10%,transparent)}
.mboard canvas{position:absolute;left:0;top:0;pointer-events:none}
@media (orientation:portrait){#modal.split{flex-direction:column}
  #modal.split .mdiv{width:auto;height:28px;cursor:row-resize}#modal.split .mdiv:after{width:72px;height:8px}}
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
.pdhov{font:600 .8rem "JetBrains Mono",monospace;color:var(--mut);flex:1 1 0;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}   /* never re-wraps the header: a tap's mouseover would shift the table under the finger before its click lands */
.pdmwt{margin-left:auto;border:3px solid var(--ink);background:var(--card);font:800 .85rem "Anuphan",sans-serif;padding:6px 12px;cursor:pointer;box-shadow:3px 3px 0 var(--sh)}
.pdmwt.on{background:var(--blue);color:#fff}
.pdmwt:active{transform:translate(3px,3px);box-shadow:none}
#pd.nomw .pdcalc,#pd.nomw .pdbrk,#pd.nomw .pdq{display:none}
.pdx{background:var(--ink);color:var(--paper);border:0;width:36px;height:36px;font-weight:800;cursor:pointer}
.pdw{container-type:inline-size;overflow-x:auto}
.pdg{--u:calc(max(100cqi,600px)/18);display:grid;grid-template-columns:repeat(18,minmax(0,1fr));gap:3px;min-width:600px}
.pde{aspect-ratio:1/1;cursor:pointer;user-select:none;-webkit-user-select:none;min-width:0;position:relative;line-height:1;perspective:calc(var(--u)*9);transition:transform .15s,box-shadow .15s}
/* a tile is a slot holding two real faces: .pf (the element) and .pb (the memorize-mode back); both carry the category colour via --kb */
.pf,.pb{position:absolute;inset:0;border:2px solid var(--kbd,var(--ink));background:var(--kb);overflow:hidden}
.pf{display:flex;flex-direction:column;align-items:center;justify-content:space-between;padding:3px 3px 4px}
.pb{display:none}
.pde i{align-self:flex-start;font-style:normal;font-weight:500;opacity:.75;font-size:calc(var(--u)*.16)}
.pde b{font-weight:800;font-size:calc(var(--u)*.33);margin-top:-6%}
.pde s{text-decoration:none;font-family:"JetBrains Mono",monospace;font-size:calc(var(--u)*.15);opacity:.85}
.pde:hover{transform:translate(-2px,-2px);box-shadow:3px 3px 0 var(--sh);z-index:2}
.pde.inq::after{content:"";position:absolute;inset:0;z-index:2;border:3px solid var(--red);animation:pdpulse 1.2s infinite}
@keyframes pdpulse{50%{inset:3px;opacity:.3}}
.pde.inf .pf{outline:3px solid var(--blue);outline-offset:-3px}
.pde.pdflash .pf{animation:pdfl .35s}
@keyframes pdfl{0%{background:var(--ink);color:var(--yel)}}
.k-alk{--kb:var(--red);color:#fff}.k-ae{--kb:#f28c28}.k-tm{--kb:var(--card)}.k-pt{--kb:#d9d2c1}.k-md{--kb:#9fb0e8}.k-nm{--kb:var(--yel)}.k-hal{--kb:var(--blue);color:#fff}.k-ng{--kb:var(--ink);color:var(--paper)}.k-ln{--kb:#f3c3b8}.k-an{--kb:#e39c8c}
.pdph{display:flex;align-items:center;justify-content:center;font:600 calc(var(--u)*.17) "JetBrains Mono",monospace;opacity:.55;aspect-ratio:1/1}
.pdinfo{grid-row:1/4;grid-column:3/13;display:flex;gap:16px;align-items:flex-start;padding:0 6px;overflow:auto}
.pdbig{flex:none;position:relative;width:calc(var(--u)*2.9);height:calc(var(--u)*2.75);border:4px solid var(--ink);background:var(--card);box-shadow:6px 6px 0 var(--sh);display:flex;flex-direction:column;align-items:center;justify-content:space-between;font-weight:800;font-size:calc(var(--u)*1.05);padding:4px 10px 6px;line-height:1}
.pdbig i{align-self:flex-start;font:800 calc(var(--u)*.44) "JetBrains Mono",monospace;font-style:normal;line-height:1}
.pdbig u{font:700 calc(var(--u)*.22) "Anuphan",sans-serif;text-decoration:none;margin-top:-4px}
.pdbig s{font:800 calc(var(--u)*.36) "JetBrains Mono",monospace;text-decoration:none;line-height:1}
.pdbig.nil{color:var(--mut)}
.pdbig.pdrev{animation:pdbin .38s cubic-bezier(.2,.7,.2,1)}
@keyframes pdbin{0%{transform:perspective(600px) rotateY(-90deg);opacity:.3}}
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
/* ท่องตารางธาตุ: #pdg.mem shows the backs; a tile turns face-down (.dn) or back up (.up). Each face turns on its own rotateY
   transition with its backface hidden, so exactly one face shows at every angle: no swap at the edge-on midpoint. Only
   transform/opacity/scale animate (compositor-only), and the deck turns in an eased diagonal ripple (--d per tile). */
.pdmem.on{background:var(--red);color:#fff}
#pdmwt{margin-left:0}
.pdrst{position:relative}.pdrst::after{content:"";position:absolute;inset:-5px -2px}   /* hit area >= 44px without a taller button */
.pde{touch-action:manipulation}
.pde:focus-visible{outline:3px solid var(--ink);outline-offset:2px;z-index:3}
.mem .pf,.mem .pb{backface-visibility:hidden;-webkit-backface-visibility:hidden;transition:transform .48s cubic-bezier(.2,.7,.2,1) var(--d,0ms)}
/* the back recedes into the drawer: its own paper colour, a faint ink edge, Z at low contrast, so an opened tile's category colour pops */
.mem .pb{display:flex;align-items:center;justify-content:center;transform:rotateY(-180deg);background:var(--paper);border:1px solid rgba(var(--pbi),.3);color:rgba(var(--pbi),.45);font:800 calc(var(--u)*.3) "JetBrains Mono",monospace;font-style:normal}
.pdg{--pbi:20,20,20}body.dark .pdg{--pbi:232,226,212}
.mem .dn .pf{transform:rotateY(180deg)}
.mem .dn .pb{transform:none}
.mem .pde::before{content:"";position:absolute;inset:0;background:var(--sh);translate:2px 2px;opacity:0;pointer-events:none}
.mem .pde.dn,.mem .pde.up{animation:pdld .48s ease-in-out var(--d,0ms)}.mem .pde.up{animation-name:pdlu}
.mem .pde.dn::before,.mem .pde.up::before{animation:pdsd .48s ease-in-out var(--d,0ms)}.mem .pde.up::before{animation-name:pdsu}
@keyframes pdld{45%{scale:1.06}}@keyframes pdlu{45%{scale:1.06}}   /* two names so each turn restarts the lift */
@keyframes pdsd{45%{opacity:.45}}@keyframes pdsu{45%{opacity:.45}}
.pdg.still *,.pdg.still *::before{transition:none!important;animation:none!important}
@media (prefers-reduced-motion:reduce){#pd,#pdscrim{transition:none}.pde.inq::after,.mem .pde,.mem .pde::before,.pdbig.pdrev{animation:none!important}
  .mem .pf,.mem .pb{transition-duration:1ms!important;transition-delay:0s!important}}

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
  #vs{width:min(1500px,96vw)}
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
#stabs{position:fixed;left:0;top:50%;transform:translateY(-50%);z-index:45;display:flex;flex-direction:column;align-items:flex-start;gap:14px}
#stabs>button{position:static!important;min-height:104px;text-align:center}
#vstab{position:fixed;left:0;top:calc(28% + 384px);z-index:45;writing-mode:vertical-rl;background:var(--ink);color:#fff;border:3px solid var(--ink);border-left:0;padding:14px 8px;font:800 .9rem "Anuphan",sans-serif;box-shadow:4px 4px 0 var(--sh);cursor:pointer;display:block;transition:transform .2s}
#vstab:hover{transform:translateX(4px)}
#vs{position:fixed;left:0;top:0;bottom:0;z-index:73;width:min(1040px,97vw);background:var(--paper);border-right:4px solid var(--ink);box-shadow:10px 0 0 var(--red);transform:translateX(calc(-100% - 20px));visibility:hidden;transition:transform .6s cubic-bezier(.34,1.35,.64,1),visibility 0s .6s;padding:14px 18px 18px;display:flex;flex-direction:column}
body.vsopen #vs{transform:none;visibility:visible;transition:transform .6s cubic-bezier(.34,1.35,.64,1),visibility 0s}
body.vsopen #pdscrim{opacity:1;pointer-events:auto}
#vsf{flex:1;width:100%;border:0;background:var(--paper);min-height:0}
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
.tile.recent{cursor:default;gap:8px}
.board.hasrec{grid-template-rows:auto}   /* row 1 = the full-width recent strip, sized to its content */
.recent .rtop{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.recent .rk{font-weight:800;font-size:.9rem;margin-right:4px}
.recent .rtx{font-size:1.02rem;line-height:1.6;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.recent .rgo{align-self:flex-start;border:3px solid var(--ink);background:var(--red);color:#fff;font:800 .95rem "Anuphan",sans-serif;padding:6px 16px;cursor:pointer;box-shadow:3px 3px 0 var(--sh)}
.recent .rgo:active{transform:translate(3px,3px);box-shadow:none}
.recent .rl{display:flex;flex-wrap:wrap;gap:5px}
.recent .rl button{border:2px solid var(--ink);background:var(--card);color:var(--ink);font:700 .74rem "JetBrains Mono",monospace;padding:3px 8px;cursor:pointer;box-shadow:2px 2px 0 var(--sh)}
.recent .rl button:hover{background:var(--ink);color:var(--paper)}
.btn.on{background:var(--ink);color:var(--paper)}

/* ---------- landing: chapter stats slide (chem chapter tile: .tface = the normal tile, .tback = its stats) ----------
   Slid left or right (or ←/→ on the focused tile) it is re-packed 2 columns wide and as many rows as its stats need, and turns over. */
.tile.st{padding:0;touch-action:pan-y;-webkit-user-select:none;user-select:none}
.tile.st.c-red{--c:var(--red)}.tile.st.c-yel{--c:var(--yel)}.tile.st.c-blue,.tile.st.c-card,.tile.st.c-ink{--c:var(--blue)}
.tface{position:absolute;inset:0;border:0;background:none;color:inherit;font:inherit;text-align:left;padding:14px 16px;display:flex;flex-direction:column;gap:4px;cursor:pointer}
.tile.st:not(.open):hover{transform:scale(.965)}
.tback{display:none;position:absolute;left:0;right:0;top:0;min-height:100%;flex-direction:column}
.tile.st.open{cursor:default;z-index:2}
.tile.st.open .tback{display:flex}
.tile.st.open .tface{visibility:hidden}
.sth{display:flex;align-items:center;gap:10px;padding:8px 10px 8px 14px}
.sth .sn{font-size:2.3rem;font-weight:800;line-height:.9}
.sth .snm{flex:1;min-width:0;font-weight:800;font-size:.98rem;line-height:1.2}
.sth .snm small{display:block;font-weight:600;font-size:.76rem;opacity:.8}
.tbx{flex:none;width:34px;height:34px;border:2px solid currentColor;background:transparent;color:inherit;font-weight:800;font-size:1rem}
.tbx:hover{background:var(--ink);color:var(--paper)}
.sbody{flex:1;background:var(--card);color:var(--ink);border-top:3px solid #141414;padding:9px 12px 12px;display:flex;flex-direction:column;gap:7px}
body.dark .sbody{border-top-color:#050506}
.scap{font-size:.7rem;font-weight:800;letter-spacing:.08em;color:var(--mut)}
.pchips{display:flex;flex-wrap:wrap;gap:4px}
.pchip{border:2px solid var(--ink);background:var(--card);color:var(--ink);font:700 .76rem "Anuphan",sans-serif;padding:2px 8px;cursor:pointer}
.pchip.on{background:var(--ink);color:var(--paper)}
.pchip.on:before{content:"✓ "}
body.dark .pchip.on{background:var(--yel);color:#141414;border-color:var(--yel)}
.sbars{display:flex;flex-direction:column;gap:3px}
.sbar{position:relative;display:flex;align-items:center;gap:8px;height:23px;border:0;background:color-mix(in srgb,var(--ink) 7%,transparent);color:var(--ink);padding:0 8px;font:600 .8rem "Anuphan",sans-serif;text-align:left;cursor:pointer;overflow:hidden}
.sbar:before{content:"";position:absolute;left:0;top:0;bottom:0;width:var(--w);background:color-mix(in srgb,var(--c) 40%,var(--card));border-left:4px solid var(--c);transform-origin:left;animation:sgrow .5s cubic-bezier(.2,.9,.3,1) both;animation-delay:calc(var(--k)*28ms)}
.sbar .sl{position:relative;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sbar b{position:relative;font:800 .8rem "JetBrains Mono",monospace}
.sbar:hover:not(:disabled),.sbar:focus-visible{outline:2px solid var(--ink);outline-offset:-2px}
.sbar:disabled{opacity:.38;cursor:default}.sbar:disabled:before{display:none}
@keyframes sgrow{from{transform:scaleX(0)}}
.sdiff{display:flex;height:24px;border:2px solid var(--ink)}
.sdiff i{display:flex;align-items:center;justify-content:center;min-width:26px;overflow:hidden;font:800 .76rem "JetBrains Mono",monospace;font-style:normal}
.sdiff i+i{border-left:2px solid var(--ink)}
.sd-easy{background:var(--blue);color:#fff}.sd-medium{background:var(--yel);color:#141414}.sd-hard{background:var(--red);color:#fff}
.sdw{margin-top:auto;display:flex;flex-direction:column;gap:4px}
.sleg{display:flex;gap:12px;flex-wrap:wrap}
.snone{font-size:.8rem;color:var(--mut);font-weight:600}
body[data-subj=bio] .lfst{display:none}
@media(prefers-reduced-motion:reduce){.sbar:before{animation:none}}

/* ---------- Prat's own exercises (exam "ex"): solid-ink ✎ badge, and in place of the difficulty strip a plain ink
   strip (same --bw width as each view's strip). Question cards keep the plain card background like exams (Prat
   2026-09-25: no grid, no punched holes); only the landing ✎ tile keeps the faint exercise-book grid. Plain var()/rgba
   only -- html2canvas 1.4.1 (save-as-image) can't parse color-mix()/oklch()/color(). */
.b-ex{background:var(--ink);color:var(--paper);border-color:var(--ink);font-weight:800}
.tile.ex{background-image:linear-gradient(var(--exg) 1px,transparent 1px),linear-gradient(90deg,var(--exg) 1px,transparent 1px);background-size:20px 20px}
.poster.ex{--bw:14px}.card.ex{--bw:10px}.sheet.ex{--bw:16px}.row.ex{--bw:10px;position:relative;padding-left:15px}
.poster.ex:after,.card.ex:before,.sheet.ex:before,.row.ex:before{content:"";position:absolute;left:0;top:0;bottom:0;height:auto;width:var(--bw);background:var(--ink)}
.sexb{border:2px solid var(--ink);background:var(--ink);color:var(--paper);font:800 .8rem "Anuphan",sans-serif;padding:5px 10px;text-align:left;cursor:pointer}
.sexb:hover,.sexb:focus-visible{background:var(--yel);color:#141414}

/* ---------- night mode: ink-black surfaces, cream text, black offset shadows ---------- */
body.dark{--paper:#18181b;--card:#232327;--ink:#e8e2d4;--mut:#9c958a;--sh:#050506;--blue:#3b57d6;--red:#e2492f;--yel:#e8ae06;--stbg:#59491e;--sxbg:#363024;--sxbd:#86827e;--exg:rgba(232,226,212,.06);color-scheme:dark}
body.dark .board{background:#050506;border-color:#050506}
body.dark .d1{background:repeating-linear-gradient(45deg,var(--yel) 0 18px,#050506 18px 36px)}
body.dark .d3{background:linear-gradient(var(--yel),var(--yel)) center/40% 40% no-repeat,#050506}
body.dark .c-ink,body.dark .b-id,body.dark .sec-t,body.dark .pane-item.sel,body.dark .seg button.on,body.dark .tmseg button.on,body.dark .tdtabs button.on,body.dark .tmpre button.on,body.dark .cvout div.src,body.dark .iontbl th,body.dark .ftbl th,body.dark .fxchips button.cur,body.dark .pdbrk th,body.dark .pdx,body.dark .x,body.dark .exprow button.pri,body.dark .pdmw{background:#050506;color:#e8e2d4}
body.dark .k-ng{--kb:#050506;--kbd:#e8e2d4;color:#e8e2d4}
body.dark header{background:#050506;color:#e8e2d4}
body.dark #q,body.dark .hbtn{background:#050506;color:#e8e2d4;border-left-color:#3a3a40}
body.dark #q:focus,body.dark .hbtn:hover{background:#1c1c20}
body.dark .hbtn.on{background:var(--yel);color:#141414}
body.dark .lsearch button{background:#050506}
body.dark .c-yel,body.dark .k-nm,body.dark .k-ae,body.dark .k-pt,body.dark .k-md,body.dark .k-ln,body.dark .k-an,body.dark .chap-h.app b,body.dark #exportbtn,body.dark .tmctl .go.pause{color:#141414}
body.dark .k-tm{--kb:#2c2c32}
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

/* ---------- biology palette (colorhunt 063b00-266210-90b800-e1e100): same Bauhaus roles, warm greens ---------- */
body[data-subj=bio]{--paper:#edeedb;--card:#fcfdf2;--mut:#5d634e;--red:#266210;--blue:#063b00;--yel:#e1e100;--acc:#90b800;--stbg:#e0ebb3;--sxbg:#f2f7dc;--sxbd:#888883}
body.dark[data-subj=bio]{--paper:#151a13;--card:#1f261c;--ink:#e4e8d4;--mut:#98a08a;--sh:#040604;--red:#347a1a;--blue:#1a5410;--yel:#d4d400;--acc:#86ab00;--stbg:#3a4915;--sxbg:#283219;--sxbd:#828778;--exg:rgba(228,232,212,.06)}
</style></head><body>
<div class="kin" aria-hidden="true"><i class="k1"></i><i class="k2"></i><i class="k3"></i><i class="k4"></i><i class="k5"></i></div>

<!-- ================= LANDING ================= -->
<section id="landing"><div class="lwrap">
  <div class="lhead"><h1><span class="shapes"><i class="c"></i><i class="s"></i><i class="t"></i></span><span class="tn">คลังข้อสอบเคมี</span></h1>
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
   <span class="title"><span class="shapes"><i class="c"></i><i class="s"></i><i class="t"></i></span><span class="tn">คลังข้อสอบเคมี</span> <small class="tne">Chem Question Bank</small></span>
   <input id="q" placeholder="ค้นหาข้อความ / สูตร / Q-id…  ( / )">
   <button class="hbtn" id="random">🎲 สุ่ม</button>
   <button class="hbtn" id="ftoggle">ตัวกรอง ▾</button>
 </div>
 <div class="bar2"><div class="in">
   <select id="fsubj"></select>
   <select id="fch"></select>
   <select id="ftopic" hidden></select>
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
   <button class="btn" id="bgbtn" title="เปิด/ปิดพื้นหลังเคลื่อนไหว">◐</button>
   <button class="btn" id="darkbtn" title="โหมดกลางคืน">🌙</button>
   <span class="volbox"><button class="sfxbtn" id="sfxbtn">🔊</button><input type="range" class="vol" min="0" max="100" aria-label="ระดับเสียง"></span>
   <span id="count"></span>
 </div></div>
</header>
<div id="appbody"><main id="root"></main></div>
</div>

<div class="modal" id="modal"><div class="sheet">
  <button class="x" id="mx">✕</button>
  <button class="x inkw" id="inkw" title="โหมดเขียน (P)" aria-pressed="false">✎</button>
  <div class="mink" id="mink">
  <div class="mtop" id="mtop"></div>
  <div class="body" id="mbody"></div>
  <div class="note" id="mnote" style="display:none"></div>
  <div class="ans-box" id="mans"></div>
  <div id="msol"></div>
  <canvas id="inkhl"></canvas><canvas id="inkpen"></canvas>
  </div>
  <div class="mctrl">
    <button id="mreveal" class="reveal">เฉลย / หมายเหตุ</button>
    <button id="mprev">◀ ก่อนหน้า</button>
    <button id="mnext">ถัดไป ▶</button>
    <button id="mpt" title="ตารางธาตุ">เปิดตารางธาตุ</button>
    <button id="mshot" title="บันทึกโจทย์ข้อนี้เป็นไฟล์ PNG">💾 บันทึกเป็นรูป</button>
    <span class="mpos" id="mpos"></span>
  </div>
  <div class="foot" id="mfoot" style="margin-top:14px"></div>
</div>
<div class="mdiv" id="mdiv" role="separator" aria-label="ลากเพื่อปรับขนาด"></div>
<div class="mboard" id="mboard"><canvas id="bhl"></canvas><canvas id="bpen"></canvas></div>
<div class="inkbar" id="inkbar">
  <button data-c="0" class="sel" title="ปากกาดำ"><span class="dot" style="background:var(--ink)"></span></button>
  <button data-c="1" title="ปากกาแดง"><span class="dot" style="background:var(--red)"></span></button>
  <button data-c="2" title="ปากกาน้ำเงิน"><span class="dot" style="background:var(--blue)"></span></button>
  <button data-t="hl" title="ไฮไลต์">🖍</button>
  <button data-t="er" title="ยางลบ (ลบทั้งเส้น)">⌫</button>
  <button id="inkundo" title="ย้อนกลับ">↶</button>
  <button id="inkclr" title="ล้างหมึกข้อนี้">🧹</button>
  <button id="inkwipe" title="ล้างหมึกทั้งหมด">🗑</button>
  <button id="inksplit" title="กระดาษทด (แบ่งจอ)" aria-pressed="false">▦</button>
</div></div>


<nav id="stabs"><button id="pdtab" title="ตารางธาตุ + คำนวณ Mw">ตารางธาตุ</button>
<button id="tdtab" title="ค่าคงที่ · แปลงหน่วย · ไอออน · สูตร">เครื่องมือ</button>
<button id="tmtab" title="จับเวลา">จับเวลา</button>
<button id="vstab" title="รูปร่างโมเลกุล 3 มิติ (VSEPR)">โมเลกุล 3D</button></nav>
<aside id="td" aria-label="เครื่องมือ">
  <div class="pdh"><b>🧰 เครื่องมือ</b><span class="pdhov">ค่าคงที่ · แปลงหน่วย · ไอออน · สูตร</span><button class="pdx" id="tdx" title="ปิด (Esc)">✕</button></div>
  <div class="tdtabs" id="tdtabs"><button data-t="fx" id="fxtabb" class="on">สูตร</button><button data-t="k">ค่าคงที่</button><button data-t="cv">แปลงหน่วย</button><button data-t="io">ไอออน</button></div>
  <div class="tdpane on" id="td-fx"></div><div class="tdpane" id="td-k"></div><div class="tdpane" id="td-cv"></div><div class="tdpane" id="td-io"></div>
</aside>
<aside id="vs" aria-label="รูปร่างโมเลกุล">
  <div class="pdh"><b>รูปร่างโมเลกุล 3D</b><span class="pdhov">VSEPR · เพิ่ม/ลดพันธะและอิเล็กตรอนคู่โดดเดี่ยว · ลากหมุนได้</span><button class="pdx" id="vsx" title="ปิด (Esc)">✕</button></div>
  <iframe id="vsf" title="รูปร่างโมเลกุล 3D"></iframe>
</aside>
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
  <div class="pdh"><b>ตารางธาตุ</b><span class="pdq" id="pdq"></span><span class="pdhov" id="pdhov"></span><button class="pdmwt pdmem" id="pdmem" aria-pressed="false" title="คว่ำทุกธาตุ เหลือแค่เลขอะตอม แล้วแตะเพื่อเปิดทีละตัว">🃏 ท่องตารางธาตุ: ปิด</button><button class="pdmwt pdrst" id="pdrst" hidden title="คว่ำทุกธาตุที่เปิดอยู่กลับทั้งหมด">↺ รีเซ็ต</button><button class="pdmwt" id="pdmwt" title="เปิด/ปิดเครื่องคิด Mw">🧮 คิด Mw</button><button class="pdx" id="pdx" title="ปิด (Esc)">✕</button></div>
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
const ST=DATA.subtopics||{};   // chem sub-topics per chapter ("07": [{id,th}]); empty -> stats slide + topic filter off
const ls={get:(k,d)=>{try{const v=localStorage.getItem(k);return v===null?d:v;}catch(e){return d;}},set:(k,v)=>{try{localStorage.setItem(k,v);}catch(e){}},del:k=>{try{localStorage.removeItem(k);}catch(e){}}};
let view = ls.get("cqb_view","poster");
if(!["poster","cards","list","pane"].includes(view)) view="poster";
let filtered = [], pIdx = 0;
const hasSol=q=>!!(q.solHtml||q.solAnswer);
// Prat's own exercises (exam "ex"). The landing's chapter / ทุกบท / สุ่ม tiles open exams only: EXONLY is every
// exam slug but "ex" joined with "+", which the exam filter already reads as "any of these"
const isEx=q=>q.exam==="ex",exCls=q=>isEx(q)?" ex":"";
const EXN=DATA.questions.filter(isEx).length,EXONLY=Object.keys(DATA.examcount||{}).filter(k=>k!=="ex").join("+");
/* worked solutions carry LaTeX ($$\frac{...}$$); KaTeX loads deferred from the CDN, so typeset whatever
   is on screen now and again once it arrives. Without the CDN the raw text simply stays. */
function tex(el){if(!el||!window.renderMathInElement)return;
  try{renderMathInElement(el,{delimiters:[{left:"$$",right:"$$",display:true},{left:"\\(",right:"\\)",display:false}],throwOnError:false,strict:false});}catch(e){}}
window.texReady=()=>{tex($("#root"));tex($("#msol"));};

/* ---------- sound fx: synthesized with Web Audio (no files to host), muteable, remembered ----------
   Each action family has its own voice, so the app reads by ear: paper flicks move between questions,
   wood blocks and pops are toggles, marker taps are the pen, glass + bubbles are chem, plucked strings +
   wood are bio. "Satisfying" rules: a crisp transient over a soft round body, warm low-mids (no square
   waves; the chain lowpasses at 7.5k), fast clean decays, consonant intervals (5ths, 4ths, major 3rds)
   rising for doing and falling for undoing. Every layer is pitch/velocity-varied a few % and many presets
   pick between 2-3 voicings, so repeats never sound robotic. */
const SFX=(()=>{let ctx=null,master=null,verb=null,nbuf=null,on=ls.get("cqb_sfx","1")!=="0",vol=Math.max(0,Math.min(100,parseInt(ls.get("cqb_vol","70"),10)||0));
  const gainFor=v=>Math.pow(v/100,1.6)*1.35;   // perceptual-ish curve: the slider feels even across its range
  /* signal chain: every voice -> master -> soft lowpass -> compressor -> out, plus a send into a small
     generated-impulse room reverb. One shared 2 s noise buffer feeds every noise voice (random offset). */
  function ac(){
    if(!ctx){const A=window.AudioContext||window.webkitAudioContext;if(!A)return null;ctx=new A();
      const comp=ctx.createDynamicsCompressor();comp.threshold.value=-20;comp.knee.value=14;comp.ratio.value=4;comp.attack.value=.003;comp.release.value=.18;
      const lp=ctx.createBiquadFilter();lp.type="lowpass";lp.frequency.value=7500;
      master=ctx.createGain();master.gain.value=gainFor(vol);master.connect(lp);lp.connect(comp);comp.connect(ctx.destination);
      const len=Math.floor(ctx.sampleRate*1.2),ir=ctx.createBuffer(2,len,ctx.sampleRate);
      for(let c=0;c<2;c++){const d=ir.getChannelData(c);for(let i=0;i<len;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/len,3.4);}
      const cv=ctx.createConvolver();cv.buffer=ir;verb=ctx.createGain();verb.gain.value=.9;verb.connect(cv);cv.connect(master);
      nbuf=ctx.createBuffer(1,ctx.sampleRate*2,ctx.sampleRate);const nd=nbuf.getChannelData(0);for(let i=0;i<nd.length;i++)nd[i]=Math.random()*2-1;}
    if(ctx.state==="suspended")ctx.resume();return ctx;}
  const rnd=Math.random,pick=a=>a[Math.floor(rnd()*a.length)],vary=(x,p=.03)=>x*(1+(rnd()*2-1)*p);
  const PENTA=[0,2,4,7,9],note=(root,i)=>{i|=0;return root*Math.pow(2,(PENTA[(i%5+5)%5]+12*Math.floor(i/5))/12);};   // major pentatonic: any mix of steps is consonant
  function route(g,wet){g.connect(master);if(wet){const s=ctx.createGain();s.gain.value=wet;g.connect(s);s.connect(verb);}}
  function env(g,t,v,a,dur){g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(vary(v,.07),t+a);g.gain.exponentialRampToValueAtTime(.0001,t+dur);}
  function tone(f,dur,o={}){const c=ac();if(!c)return;const t=c.currentTime+(o.delay||0),os=c.createOscillator(),g=c.createGain();
    os.type=o.type||"sine";os.frequency.setValueAtTime(f,t);
    if(o.slide)os.frequency.exponentialRampToValueAtTime(Math.max(20,f*o.slide),t+(o.slideT||dur));
    let n=os;if(o.lp){const fl=c.createBiquadFilter();fl.type="lowpass";fl.frequency.value=o.lp;os.connect(fl);n=fl;}
    env(g,t,o.vol||.12,o.attack||.004,dur);n.connect(g);route(g,o.wet);os.start(t);os.stop(t+dur+.05);}
  function noise(dur,o={}){const c=ac();if(!c)return;const t=c.currentTime+(o.delay||0);dur=Math.min(dur,1);
    const src=c.createBufferSource();src.buffer=nbuf;const f=c.createBiquadFilter();f.type=o.type||"bandpass";
    f.frequency.setValueAtTime(o.freq||1800,t);if(o.sweep)f.frequency.exponentialRampToValueAtTime((o.freq||1800)*o.sweep,t+dur);f.Q.value=o.q||.8;
    const g=c.createGain();env(g,t,o.vol||.1,o.attack||.002,dur);src.connect(f);f.connect(g);route(g,o.wet);src.start(t,rnd()*(2-dur-.1));src.stop(t+dur+.05);}
  function bell(f,dur,o={}){const c=ac();if(!c)return;const t=c.currentTime+(o.delay||0),car=c.createOscillator(),mod=c.createOscillator(),mg=c.createGain(),g=c.createGain();
    car.frequency.value=f;mod.frequency.value=f*(o.ratio||3.5);mg.gain.setValueAtTime(f*(o.index||1.6),t);mg.gain.exponentialRampToValueAtTime(1,t+dur);
    mod.connect(mg);mg.connect(car.frequency);env(g,t,o.vol||.08,.003,dur);car.connect(g);route(g,o.wet==null?.5:o.wet);
    car.start(t);mod.start(t);car.stop(t+dur+.05);mod.stop(t+dur+.05);}
  // Karplus-Strong plucked string: a burst of softened noise circulating in a tiny averaging delay line
  function pluck(f,dur,o={}){const c=ac();if(!c)return;const sr=c.sampleRate,n=Math.floor(sr*dur),N=Math.max(2,Math.round(sr/f)),
      b=c.createBuffer(1,n,sr),d=b.getChannelData(0),ring=new Float32Array(N),br=o.bright||.15,damp=o.damp||.996;
    let lp=0,mx=1e-6;for(let i=0;i<N;i++){lp+=br*((rnd()*2-1)-lp);ring[i]=lp;mx=Math.max(mx,Math.abs(lp));}   // lowpassed pluck = warm, not twangy
    for(let i=0;i<N;i++)ring[i]/=mx;   // normalised so every pluck lands at the same level
    for(let i=0,p=0;i<n;i++){const q=p+1===N?0:p+1,y=ring[p];d[i]=y;ring[p]=damp*.5*(y+ring[q]);p=q;}
    const t=c.currentTime+(o.delay||0),src=c.createBufferSource(),g=c.createGain();src.buffer=b;
    const v=vary(o.vol||.3,.07);g.gain.setValueAtTime(v,t);g.gain.setValueAtTime(v,t+dur*.7);g.gain.linearRampToValueAtTime(0,t+dur);
    src.connect(g);route(g,o.wet==null?.15:o.wet);src.start(t);}
  // ---- instruments built from those voices ----
  function mallet(f,o={}){const v=o.vol||.14;tone(f,.42,{vol:v,wet:.25,delay:o.delay,attack:.002});tone(f*3.98,.07,{vol:v*.22,delay:o.delay,attack:.001});noise(.012,{vol:v*.3,freq:3000,q:1,delay:o.delay});}
  function thock(o={}){const v=o.vol||.15,d=o.delay||0;
    tone(vary(o.f||190),.1,{vol:v,slide:.5,slideT:.07,attack:.001,delay:d,lp:1400});
    noise(.016,{vol:v*.55,freq:vary(o.nf||3000,.1),q:1.3,delay:d});}
  function wood(f,o={}){const v=o.vol||.1,d=o.delay||0;   // wood block: short pitched knock + one inharmonic partial + contact click
    tone(f,.08,{vol:v,slide:.93,slideT:.05,attack:.001,delay:d,wet:o.wet});tone(f*2.72,.03,{vol:v*.25,attack:.001,delay:d});
    noise(.008,{vol:v*.35,freq:Math.min(f*3,4200),q:2.5,delay:d});}
  function pop(f,o={}){const T=o.dur||.07;tone(f,T,{vol:o.vol||.1,slide:o.rise||1.8,slideT:T*.8,attack:.002,delay:o.delay,wet:o.wet==null?.12:o.wet});}   // bubble: a sine whose pitch rises as it dies
  function glass(f,o={}){const v=o.vol||.06,d=o.delay||0,T=o.dur||.5;   // struck glass: partials at wine-glass ratios
    tone(f,T,{vol:v,delay:d,attack:.002,wet:.4});tone(f*2.32,T*.5,{vol:v*.3,delay:d,attack:.001,wet:.4});tone(f*4.25,T*.22,{vol:v*.1,delay:d,attack:.001});}
  function paper(dir,o={}){const v=o.vol||.1,t=o.delay||0,fwd=dir>0;
    noise(.07,{freq:vary(fwd?2300:1500,.08),sweep:fwd?1.6:.62,q:1.2,vol:v*.5,attack:.004,delay:t});           // the edge leaving your thumb
    noise(.16,{freq:vary(fwd?700:1900,.08),sweep:fwd?2.6:.4,q:.8,vol:v,attack:.05,delay:t+.02,wet:.12});      // air as the page turns
    thock({f:vary(125),vol:v*.75,nf:1800,delay:t+.15});}                                                     // ...and it lands
  function arp(fs,gap,fn){fs.forEach((f,i)=>fn(f,i*gap,i));}
  const P={
    // ---- generic / feedback ----
    preview:()=>thock({f:150+vol*2.2,vol:.13}),                     // volume slider: the knock climbs with the level
    tick:()=>tone(vary(1700,.03),.02,{vol:.035,type:"triangle",lp:3000,attack:.001}),   // scrubber detent
    bad:()=>{wood(vary(330,.02),{vol:.08});wood(vary(262,.02),{vol:.085,delay:.1});tone(131,.22,{vol:.05,lp:400,delay:.1});},   // "uh-uh": two knocks falling a 3rd
    empty:()=>{pop(vary(520),{vol:.05,rise:.55,dur:.12});pop(vary(390),{vol:.05,rise:.55,dur:.16,delay:.13});tone(98,.3,{vol:.04,lp:300,delay:.13,wet:.2});},   // no results: a deflating double plop
    // ---- navigation ----
    flip:d=>paper(d>0?1:-1),                                          // next / prev question
    view:i=>{const f=note(330,i);wood(vary(f*1.5,.015),{vol:.09});wood(vary(f,.015),{vol:.11,delay:.055});},   // slider moving over: two clacks, pitch = which view
    tab:i=>{noise(.014,{freq:2200,q:1.4,vol:.09});wood(vary(note(587,i),.015),{vol:.12,delay:.008});},       // card tab: paper tick + pitched knock
    tile:()=>{mallet(vary(523,.015));mallet(vary(784,.015),{delay:.065,vol:.12});},
    whoosh:()=>{noise(.62,{freq:260,sweep:9,q:.7,vol:.12,attack:.26,wet:.35});tone(95,.45,{vol:.16,slide:.65,delay:.42,lp:320,attack:.01,wet:.2});},
    home:()=>{const[a,b]=pick([[587,392],[659,440],[523,349]]);noise(.38,{freq:2600,sweep:.18,q:.7,vol:.09,attack:.05,wet:.3});
      mallet(vary(a,.01),{delay:.22,vol:.1});mallet(vary(b,.01),{delay:.3,vol:.1});},   // back out: air falling + a 5th resolving down
    // ---- subject swipe on the landing: chem = glass + bubbles, bio = plucked string + wood + leaves ----
    chem:d=>{const up=d>=0;[0,.05,.1,.16].forEach((t,i)=>pop(vary(up?420+i*120:780-i*120,.08),{vol:.085,delay:t+rnd()*.02,dur:.06}));
      glass(vary(up?1319:1175,.01),{vol:.05,delay:.2});noise(.25,{freq:up?700:2200,sweep:up?3:.33,q:.8,vol:.05,attack:.08,wet:.2});},
    bio:d=>{const[a,b]=d>=0?[392,523]:[523,392];   // water-drop bloop, then a kalimba duet a 4th apart (up = next, down = back); pure sines, no grit
      tone(vary(520,.03),.09,{vol:.033,slide:1.9,slideT:.07,attack:.005,lp:3000,wet:.2});
      [[a,.07],[b,.17]].forEach(([f,t])=>{f=vary(f,.008);tone(f,.7,{vol:.061,attack:.006,delay:t,lp:3000,wet:.3});tone(f*2,.22,{vol:.016,attack:.005,delay:t,lp:3000});});},
    // ---- filters and picking things ----
    filter:i=>{noise(.01,{vol:.05,freq:2400,q:3});noise(.01,{vol:.04,freq:2600,q:3,delay:.03});   // dial detent, then a blip per filter
      tone(vary(note(523,i),.01),.09,{vol:.09,type:"triangle",lp:1800,slide:1.12,slideT:.02,attack:.002,delay:.02,wet:.12});thock({f:vary(180),vol:.06});},
    select:()=>{pop(vary(pick([440,523,587]),.02),{vol:.13,rise:1.5,dur:.06});thock({f:vary(210),vol:.08});},   // soft pop
    unfold:()=>{noise(.09,{freq:900,sweep:2.2,q:.8,vol:.06,attack:.03});pluck(vary(392,.01),.3,{vol:.07,bright:.2});pluck(vary(523,.01),.35,{vol:.065,bright:.2,delay:.05});},
    fold:()=>{noise(.08,{freq:1800,sweep:.45,q:.8,vol:.05,attack:.02});pluck(vary(523,.01),.25,{vol:.07,bright:.2});pluck(vary(392,.01),.3,{vol:.07,bright:.2,delay:.05});},
    key:k=>{const low=k==="bk"||k==="clr";tone(vary(low?250:330,.03),.035,{vol:.09,type:"triangle",lp:1200,attack:.001});thock({f:vary(low?150:185),vol:.1,nf:2600});},
    // ---- toggles: up = a pop rising a 5th, down = a plop falling one ----
    on:()=>{thock({f:vary(210),vol:.1});pop(vary(440,.02),{vol:.07,rise:1.5,dur:.06});pop(vary(660,.02),{vol:.075,rise:1.3,dur:.07,delay:.05});},
    off:()=>{thock({f:vary(170),vol:.09});tone(vary(660,.02),.08,{vol:.06,slide:.68,slideT:.06,lp:1500,attack:.002});tone(vary(440,.02),.09,{vol:.055,slide:.7,lp:1100,delay:.05,attack:.002});},
    // ---- present mode ----
    present:()=>{const c=pick([[392,494,587],[349,440,523],[440,554,659]]);noise(.26,{type:"lowpass",freq:400,sweep:5,q:.6,vol:.07,attack:.12,wet:.3});
      arp(c,.07,(f,t)=>mallet(vary(f,.01),{delay:.05+t,vol:.11}));bell(c[2]*2,.7,{vol:.03,delay:.24,index:1.1});},
    dismiss:()=>{noise(.2,{type:"lowpass",freq:2200,sweep:.25,q:.6,vol:.07,attack:.04,wet:.2});mallet(vary(587,.01),{vol:.08});mallet(vary(392,.01),{vol:.08,delay:.07});},
    dice:()=>{let t=0;const n=5+(rnd()*3|0);   // clatter whose gaps widen as it settles, then the landing
      for(let i=0;i<n;i++){t+=.018+rnd()*.014+i*.004;const f=vary(1500,.35);
        noise(.02,{freq:f,q:7,vol:.14-i*.008,delay:t});tone(vary(f*.5,.1),.035,{vol:.035,type:"triangle",lp:2200,delay:t,attack:.001});}
      thock({f:vary(160),vol:.12,delay:t+.05});},
    // ---- answering ----
    mark:i=>{const f=note(523,i);noise(.05,{freq:2000,sweep:1.5,q:1.1,vol:.045,attack:.01});   // marker circling it, then its note
      thock({f:vary(230),vol:.09,delay:.03});mallet(f,{vol:.1,delay:.035});bell(f*2,.45,{vol:.026,delay:.06,index:1.1,wet:.35});},
    unmark:()=>{thock({f:vary(170),vol:.09});tone(vary(620),.11,{vol:.06,slide:.62,slideT:.09,attack:.002,wet:.12});},
    reveal:()=>{const c=pick([[784,988,1175,1568],[698,880,1047,1397],[784,1047,1175,1568]]);   // rising 4-note resolve on celesta
      noise(.12,{freq:1200,sweep:2,q:.8,vol:.04,attack:.03});arp(c,.06,(f,t,i)=>bell(vary(f,.005),.55+i*.1,{vol:.05,delay:t,ratio:1,index:.9,wet:.45}));
      tone(c[0]/2,.5,{vol:.06,delay:.18,wet:.3});},
    conceal:()=>{bell(vary(1175,.01),.3,{vol:.04,ratio:1,index:.7,wet:.3});bell(vary(784,.01),.35,{vol:.045,ratio:1,index:.7,delay:.06,wet:.3});},
    search:()=>{const f=vary(pick([880,988]),.01);[0,.13,.26].forEach((t,i)=>bell(f,.5,{vol:.12*Math.pow(.45,i),ratio:1,index:.5,delay:t,wet:.4}));   // sonar ping + echoes
      pop(vary(330),{vol:.1,rise:2,dur:.08});},
    // ---- poster-pen ----
    penOn:()=>{noise(.03,{type:"lowpass",freq:1200,q:.7,vol:.08});pop(vary(360),{vol:.11,rise:2,dur:.07,delay:.02});tone(vary(740),.07,{vol:.035,delay:.06,wet:.15});},   // uncap
    penOff:()=>{thock({f:vary(260),vol:.1});noise(.01,{freq:2800,q:3,vol:.05,delay:.028});thock({f:vary(190),vol:.06,delay:.03});},   // cap clicks back on
    tool:t=>{if(t==="hl"){noise(.07,{freq:1300,sweep:1.6,q:.9,vol:.15,attack:.015});thock({f:170,vol:.09});}   // fat felt swipe
      else if(t==="er"){tone(vary(240),.07,{vol:.15,slide:.7,lp:900});noise(.03,{type:"lowpass",freq:700,vol:.08});}   // rubber thup
      else{const k=+t||0;noise(.018,{freq:vary(1900+k*300,.05),q:1.5,vol:.12});thock({f:vary(200+k*30),vol:.11,nf:2200});}},   // marker tap, per colour
    undo:()=>{tone(vary(880),.09,{vol:.07,slide:.55,slideT:.08,type:"triangle",lp:2000,attack:.002});thock({f:180,vol:.06,delay:.085});},   // tape rewind blip
    clear:()=>{noise(.2,{freq:1800,sweep:.5,q:.9,vol:.09,attack:.04,wet:.1});noise(.18,{freq:900,sweep:.6,q:.7,vol:.05,attack:.05,delay:.05});thock({f:140,vol:.08,delay:.2});},   // eraser across paper
    wipe:()=>{noise(.45,{freq:2400,sweep:.2,q:.7,vol:.1,attack:.08,wet:.25});tone(520,.4,{vol:.05,slide:.5,lp:1200,attack:.05,wet:.2});
      thock({f:110,vol:.12,delay:.42});bell(262,.8,{vol:.03,delay:.44,ratio:1,index:.4});},   // clean slate
    splitOn:()=>{noise(.14,{freq:600,sweep:2.5,q:1,vol:.07,attack:.05});wood(vary(660,.015),{vol:.09,delay:.13});wood(vary(990,.015),{vol:.06,delay:.16});},   // panel slides open, latches
    splitOff:()=>{noise(.14,{freq:1500,sweep:.4,q:1,vol:.07,attack:.05});wood(vary(495,.015),{vol:.09,delay:.13});wood(vary(330,.015),{vol:.07,delay:.16});},
    snap:()=>{wood(vary(880,.03),{vol:.07});thock({f:vary(200),vol:.07,delay:.012});},   // divider dropped
    // ---- side drawers: a soft slide + landing, tinted per drawer ----
    drawer:w=>{if(w==="td"){tone(vary(330,.02),.14,{vol:.055,type:"triangle",slide:1.5,slideT:.12,attack:.008,lp:1800,wet:.15});   // tools: a smooth glide in...
        tone(vary(140),.14,{vol:.097,slide:.6,slideT:.09,attack:.004,lp:600,delay:.13});   // ...lands on a felt thock...
        tone(vary(784,.008),.45,{vol:.035,attack:.005,delay:.17,lp:3000,wet:.35});tone(vary(1175,.008),.5,{vol:.031,attack:.005,delay:.25,lp:3000,wet:.35});return;}
      noise(.16,{type:"lowpass",freq:500,sweep:4,q:.7,vol:.08,attack:.07,wet:.15});thock({f:vary(150),vol:.09,delay:.14});
      if(w==="pd")glass(vary(1568,.01),{vol:.04,delay:.15,dur:.4});
      else if(w==="vs"){tone(vary(523),.3,{vol:.05,slide:1.5,slideT:.25,delay:.12,wet:.35});tone(vary(784),.3,{vol:.04,slide:1.5,slideT:.25,delay:.16,wet:.35});}   // swirl for the 3D model
      else if(w==="tm"){wood(1175,{vol:.06,delay:.14});wood(880,{vol:.06,delay:.26});}},   // tick-tock
    undrawer:()=>{noise(.13,{type:"lowpass",freq:1800,sweep:.3,q:.7,vol:.07,attack:.03});thock({f:vary(130),vol:.09,delay:.1});},
    // ---- periodic table: glass blips pitched by atomic number ----
    element:z=>glass(note(523,((z|0)-1)%12),{vol:.07,dur:.25}),
    add:z=>{const f=note(523,((z|0)-1)%12);glass(f,{vol:.06,dur:.25});pop(f*.75,{vol:.06,rise:1.5,dur:.05,delay:.04});},
    remove:()=>{pop(vary(620),{vol:.1,rise:.6,dur:.09});thock({f:vary(160),vol:.07});},
    // ท่องตารางธาตุ: a riffle dealing the deck face-down / one card turned up (tick pitched by period) / the deck gathered and squared
    memOn:()=>{noise(.55,{freq:900,sweep:3,q:.6,vol:.05,attack:.15,wet:.2});let t=.02;
      for(let i=0;i<12;i++){t+=.045-i*.0015;noise(.018,{freq:vary(2600,.15),q:2.2,vol:.07,delay:t,attack:.001});}
      thock({f:vary(170),vol:.08,delay:t+.06});},
    memFlip:p=>{noise(.05,{freq:vary(1400,.1),sweep:2,q:1,vol:.07,attack:.006});thock({f:vary(200),vol:.06,nf:2400,delay:.03});
      tone(vary(note(784,(p|0)-1),.01),.06,{vol:.05,type:"triangle",lp:3500,attack:.001,delay:.04,wet:.15});},
    memUnflip:p=>{noise(.05,{freq:vary(2000,.1),sweep:.5,q:1,vol:.06,attack:.006});thock({f:vary(160),vol:.07,nf:1800,delay:.03});   // turned back down: the flick falls
      tone(vary(note(784,(p|0)-1)*.75,.01),.07,{vol:.04,type:"triangle",lp:2500,slide:.8,slideT:.05,attack:.001,delay:.04,wet:.12});},
    memReset:()=>{noise(.3,{freq:1800,sweep:.5,q:.7,vol:.05,attack:.06,wet:.15});let t=.02;   // the open cards swept back into the deck
      for(let i=0;i<6;i++){t+=.035;noise(.016,{freq:vary(2300,.15),q:2,vol:.06,delay:t,attack:.001});}thock({f:vary(160),vol:.09,delay:t+.06});},
    memOff:()=>{noise(.4,{freq:2400,sweep:.3,q:.6,vol:.05,attack:.1,wet:.15});let t=0;
      for(let i=0;i<9;i++){t+=.03+i*.004;noise(.016,{freq:vary(2000,.15),q:2,vol:.06,delay:t,attack:.001});}
      thock({f:vary(150),vol:.1,delay:t+.07});thock({f:vary(190),vol:.07,delay:t+.15});},
    // ---- timer ----
    start:()=>{wood(vary(784,.01),{vol:.09});wood(vary(1175,.01),{vol:.08,delay:.07});},
    pause:()=>{wood(vary(1175,.01),{vol:.07});wood(vary(784,.01),{vol:.08,delay:.07});},
    reset:()=>{[0,.04,.075,.105].forEach((t,i)=>wood(vary(1400-i*150,.02),{vol:.05,delay:t}));thock({f:150,vol:.08,delay:.14});},   // ratchet back to zero
    ring:()=>[0,.38,.76].forEach(t=>{bell(1319,.6,{vol:.07,delay:t,index:1.2});bell(1047,.8,{vol:.07,delay:t+.14,index:1.2});}),   // kitchen-timer ding-dong x3
    exOpen:()=>{noise(.09,{freq:vary(3400,.08),sweep:1.3,q:1.6,vol:.05,attack:.01});noise(.07,{freq:vary(3000,.08),sweep:.8,q:1.6,vol:.045,attack:.01,delay:.1});
      wood(vary(523,.015),{vol:.08,delay:.2});wood(vary(698,.015),{vol:.07,delay:.27});},   // exercise: pencil scribble, then two soft knocks up a 4th
    saved:()=>{noise(.02,{freq:2000,q:1.2,vol:.1});thock({f:220,vol:.08});noise(.025,{freq:1600,q:1.2,vol:.08,delay:.07});thock({f:180,vol:.07,delay:.07});
      bell(1319,.5,{vol:.035,delay:.16});bell(1976,.6,{vol:.03,delay:.22});},   // shutter, then a 5th
    // ---- chapter stats tile: a card turned over (flick + two wood knocks a 5th apart, up to open, down to close),
    //      paper chips are soft pops, a topic bar is a mallet pitched by its rank ----
    statOpen:()=>{noise(.12,{freq:vary(1100,.08),sweep:2.2,q:.9,vol:.07,attack:.02});wood(vary(523,.015),{vol:.085,delay:.1});
      wood(vary(784,.015),{vol:.07,delay:.16});glass(vary(1568,.01),{vol:.03,delay:.22,dur:.35});},
    statClose:()=>{noise(.11,{freq:vary(1900,.08),sweep:.5,q:.9,vol:.065,attack:.02});wood(vary(784,.015),{vol:.075,delay:.09});wood(vary(523,.015),{vol:.08,delay:.15});},
    chip:on=>{thock({f:vary(on?220:170),vol:.07});on?pop(vary(587,.02),{vol:.075,rise:1.5,dur:.06}):tone(vary(587,.02),.08,{vol:.05,slide:.68,slideT:.06,lp:1500,attack:.002});},
    bar:i=>{mallet(note(392,Math.max(0,7-(i|0))),{vol:.11});noise(.03,{freq:2200,q:1.2,vol:.04});}
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
function toggleSfx(){SFX.set(!SFX.on);syncSfxBtns();SFX.play("on");}
document.querySelectorAll(".sfxbtn").forEach(b=>b.onclick=toggleSfx);
document.querySelectorAll(".vol").forEach(r=>r.addEventListener("input",()=>{
  if(!SFX.on)SFX.set(true);                       // dragging the slider un-mutes
  SFX.setVol(+r.value);syncSfxBtns();SFX.play("preview");}));
syncSfxBtns();

/* ---------- background toggle ---------- */
function setBg(on){document.body.classList.toggle("nobg",!on);ls.set("cqb_bg",on?"1":"0");}
setBg(ls.get("cqb_bg","1")!=="0");
$("#lbg").onclick=$("#bgbtn").onclick=()=>{setBg(document.body.classList.contains("nobg"));SFX.play(document.body.classList.contains("nobg")?"off":"on");};

/* ---------- night mode + teaching (screen-share) mode ---------- */
function setDark(on){document.body.classList.toggle("dark",on);ls.set("cqb_dark",on?"1":"0");
  $("#ldark").textContent=on?"☀":"🌙";$("#darkbtn").textContent=on?"☀":"🌙";}
setDark(ls.get("cqb_dark","0")==="1");
$("#ldark").onclick=$("#darkbtn").onclick=()=>{setDark(!document.body.classList.contains("dark"));SFX.play(document.body.classList.contains("dark")?"on":"off");};

/* ---------- recently viewed questions (landing tile) ---------- */
let RECENT=[];try{RECENT=JSON.parse(ls.get("cqb_recent","[]"))||[];}catch(e){RECENT=[];}
function seen(q){if(!q)return;RECENT=[q.id,...RECENT.filter(x=>x!==q.id)].slice(0,8);ls.set("cqb_recent",JSON.stringify(RECENT));}
// merely displaying a question doesn't count: a single-question view (poster / pane / present) counts it only
// after ~8 s on screen; choosing a choice, opening a solution or jumping to a Q-id counts it at once
let dwellT=0;
function dwell(q){clearTimeout(dwellT);dwellT=q?setTimeout(()=>{if(!document.hidden)seen(q);},8000):0;}

/* ---------- subject (เคมี / ชีววิทยา): drives the landing board AND the whole-app palette ---------- */
const SUBJS=DATA.biocount?["chem","bio"]:["chem"];
let SUBJ=ls.get("cqb_subj","chem");if(!SUBJS.includes(SUBJ))SUBJ="chem";
// palette + every title (landing h1, app bar, tab) follow the subject
function showSubj(){const[th,en]=SUBJ==="bio"?["ชีววิทยา","Biology"]:["เคมี","Chem"];document.body.dataset.subj=SUBJ;
  document.querySelectorAll(".tn").forEach(x=>x.textContent="คลังข้อสอบ"+th);$(".tne").textContent=en+" Question Bank";
  document.title=`คลังข้อสอบ${th} · ${en} Question Bank`;}
showSubj();
function setSubj(s){if(s===SUBJ||!SUBJS.includes(s))return false;SUBJ=s;ls.set("cqb_subj",s);showSubj();return true;}

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
}

/* ---------- badges ---------- */
function examBadge(q){if(isEx(q))return `<span class="badge b-ex">✎ แบบฝึกหัด</span>`;
  const e=DATA.exams[q.exam]||{label:q.exam.toUpperCase(),color:"#64748b"};
  return `<span class="badge b-exam"><i style="background:${e.color}"></i>${e.label} ${q.year}</span>`;}
function diffBadge(q){return q.diff?`<span class="badge b-diff d-${q.diff}">${DIFF_TH[q.diff]||q.diff}</span>`:"";}
function idBadge(q){return `<span class="badge b-id">${q.id}</span>`;}
function typeBadge(q){return q.type?`<span class="badge b-type">${q.type}</span>`:"";}
// chem only (bio/applied never carry topics); ids repeat across chapters, so look them up under the question's own.
// Main sub-topic first, extras (.b-sx) lighter. brief (list rows): extras hide behind a "+N" chip that shows them on tap
function topicBadge(q,label,brief){const L=q.topics.map(id=>(ST[q.ch]||[]).find(x=>x.id===id)).filter(Boolean);if(!L.length)return "";
  return L.map((t,k)=>{const c=`badge b-st${k?" b-sx":""}`;return label?`<span class="${c}">${t.th}</span>`
    :`<button class="${c}" data-ch="${q.ch}" data-st="${t.id}" title="${t.th} · ดูทุกข้อในหัวข้อย่อยนี้">${t.th}</button>`;}).join("")
    +(brief&&L.length>1?`<button class="badge b-more" title="${L.slice(1).map(t=>t.th).join(" · ")}" aria-label="หัวข้อย่อยอีก ${L.length-1}">+${L.length-1}</button>`:"");}
// filters for chapter + sub-topic (a sub-topic badge or a stats bar); the caller resets the rest first
function topicFilters(ch,t){$("#fsubj").value="chem";populateChapters("chem");$("#fch").value=ch;syncFacets(fstate());$("#ftopic").value=t;}
function chBadge(q){
  if(q.subject==="bio") return `<span class="badge b-ch">ชีววิทยา ${q.bio}. ${q.chName}</span>`;
  if(q.subject==="applied") return `<span class="badge b-ch">ประยุกต์ · ${q.chName}</span>`;
  return `<span class="badge b-ch">บท ${parseInt(q.ch)}. ${q.chName}</span>`;}
const NOKEY=/no key/i;
function keyTxt(q){return (q.answer&&!NOKEY.test(q.answer))?q.answer:"";}
function footHtml(q){const k=keyTxt(q);return `📄 ${q.source}${k?` &nbsp;·&nbsp; เฉลยทางการ: ${k}`:""}`;}
function figHtml(q){return q.figure?`<img class="fig" src="${q.figure}" alt="${q.id} figure" loading="lazy">`:"";}
function noteHtml(q){return q.note?`<div class="note">📌 ${q.note}</div>`:"";}
const qnum=q=>parseInt(q.id.slice(q.id.lastIndexOf("-")+1),10);   // Q-0038 -> 38, E-mol-07 -> 7
function chapH(q){const cls=q.subject==="bio"?" bio":q.subject==="applied"?" app":"";
  const n=q.subject==="bio"?(q.bio.split(".")[0]||"?"):q.subject==="applied"?"✦":(q.ch?parseInt(q.ch):"?");
  const nm=q.groupLabel.replace(/^บทที่ \d+ · /,"");
  return `<div class="chap-h${cls}"><b>${n}</b><span>${nm}</span></div>`;}

function solLabel(q){return q.solPending ? "⚠ ดูเฉลย (ยังไม่ได้ตรวจ)" : q.solFlag ? "⚠ ดูวิธีทำ (ไม่ฟันธง)" : isEx(q) ? "ดูเฉลย →" : "ดูวิธีทำ →";}
/* Solution block — ALWAYS collapsed on render (attempt before seeing the working). */
function solHtml(q){
  if(!hasSol(q)) return "";
  const f = q.solFlag ? " flag" : "";
  const label = solLabel(q);
  return `<button class="solbtn${f}" data-sol="1" data-label="${label}">${label}</button>
    <div class="solwrap${f}"><div class="solin"><div class="solbox">
      ${q.solPending?`<div class="soldis">⚠ เฉลยข้อนี้ยังไม่ได้ตรวจยืนยัน — อาจมีจุดผิด คิดตามทีละขั้นแล้วตัดสินเอง</div>`
        :q.solFlag?`<div class="soldis">⚠ ข้อนี้ไม่ฟันธง — โจทย์กำกวมหรือตัวเลือกไม่ตรง อ่านเหตุผลในวิธีทำแล้วตัดสินเอง</div>`:""}
      ${q.solAnswer?`<div class="solans">ตอบ: ${q.solAnswer}</div>`:""}
      <div class="solbody">${q.solHtml}</div>
    </div></div></div>`;
}

/* One predicate for everything. `skip` leaves one filter out, so each dropdown can count what it WOULD
   show with every other filter applied -- that's how the selects stay in sync with each other. */
// sub-topics exist only under one chem chapter; a topic left over from another chapter is dropped here, once
const topicList=f=>(f.subj===""||f.subj==="chem")&&ST[f.ch]?ST[f.ch].map(t=>[t.id,t.th]):[];
function fstate(){const f={t:$("#q").value.trim().toLowerCase(),subj:$("#fsubj").value,ch:$("#fch").value,
  ex:$("#fexam").value,yr:$("#fyear").value,df:$("#fdiff").value,tp:$("#ftype").value,sl:$("#fsol").value},st=$("#ftopic").value;
  f.st=topicList(f).some(t=>t[0]===st)?st:"";return f;}
const subjOf=x=>x.subject==="bio"?"bio":x.subject==="applied"?"applied":"chem";
const chOf=(x,subj)=>subj==="bio"?(x.bio.split(".")[0]||"?"):subj==="applied"?x.app:x.ch;
function qMatch(x,f,skip){
  if(skip!=="subj"&&f.subj&&subjOf(x)!==f.subj) return false;
  if(skip!=="ch"&&f.ch&&chOf(x,f.subj)!==f.ch) return false;
  if(f.st&&!["st","ch","subj"].includes(skip)&&!x.topics.includes(f.st)) return false;   // anywhere in its list; a topic lives under one chapter: it never narrows the chapter/subject lists
  if(skip!=="ex"&&f.ex&&!f.ex.split("+").includes(x.exam)) return false;   // "samanya+alevel" = either
  if(skip!=="yr"&&f.yr&&x.year!==f.yr) return false;
  if(skip!=="df"&&f.df&&x.diff!==f.df) return false;
  if(skip!=="tp"&&f.tp&&x.type!==f.tp) return false;
  if(skip!=="sl"&&f.sl){const hs=hasSol(x),sl=f.sl;
    if(sl==="has"       && !hs) return false;
    if(sl==="none"      &&  hs) return false;
    if(sl==="flag"      && !(hs && x.solFlag)) return false;
  }
  if(f.t && !(x.search.includes(f.t)||x.id.toLowerCase().includes(f.t))) return false;
  return true;}
function chList(subj){
  if(subj==="bio")return Object.entries(DATA.bioChapters).map(([n,name])=>[n,`${n}. ${name}`]);
  if(subj==="applied")return[...Object.entries(DATA.appTopics),...Object.keys(DATA.appcounts).filter(k=>!DATA.appTopics[k]).map(k=>[k,k])];
  return CHS.map(([n,name])=>[n,`${parseInt(n)}. ${name}`]);}
const FACETS=[
  ["#fsubj","subj",f=>[["chem","เคมี"],["bio","ชีววิทยา"],["applied","เคมีประยุกต์"]],x=>subjOf(x),()=>"ทุกวิชา",true],
  ["#fch","ch",f=>chList(f.subj),(x,f)=>chOf(x,f.subj),f=>f.subj==="bio"||f.subj==="applied"?"ทุกหัวข้อ":"ทุกบท"],
  ["#ftopic","st",f=>topicList(f),x=>x.topics,()=>"ทุกหัวข้อย่อย"],   // a list: the question counts under each of its topics
  ["#fexam","ex",f=>{const L=[["samanya+alevel","9 วิชาสามัญ + A-Level"],...(EXN?[[EXONLY,"ข้อสอบทุกสนาม"]]:[]),...Object.keys(DATA.examcount||{}).map(k=>[k,(DATA.exams[k]||{label:k}).label])];
    return f.ex&&!L.some(o=>o[0]===f.ex)?[[f.ex,f.ex.split("+").map(k=>(DATA.exams[k]||{label:k}).label).join(" + ")],...L]:L;},x=>x.exam,()=>"ทุกสนามสอบ"],   // + any paper mix picked on a stats tile
  ["#fyear","yr",f=>DATA.years.map(y=>[y,"ปี "+y]),x=>x.year,()=>"ทุกปี"],
  ["#fdiff","df",f=>["easy","medium","hard"].map(d=>[d,DIFF_TH[d]]),x=>x.diff,()=>"ทุกระดับ"],
  ["#ftype","tp",f=>DATA.types.map(t=>[t,t]),x=>x.type,()=>"ทุกชนิด"]];
const SOLOPTS=[["has","มีวิธีทำ"],["none","ยังไม่มีวิธีทำ"],["flag","⚠ ไม่ฟันธง"]];
// rebuild each select: only values that still have questions under the other filters (the chosen one always stays)
function syncFacets(f){
  const fill=(sel,allLabel,items)=>{const cur=sel.value;sel.innerHTML="";opt(sel,"",allLabel);
    items.forEach(([v,l,c])=>{if(c||v===cur)opt(sel,v,`${l} (${c})`);});sel.value=cur;if(sel.value!==cur)sel.value="";};
  for(const[sel,key,list,keyOf,all,countAll]of FACETS){
    const pool=DATA.questions.filter(x=>qMatch(x,f,key)),cnt={};
    pool.forEach(x=>[].concat(keyOf(x,f)).forEach(k=>cnt[k]=(cnt[k]||0)+1));
    fill($(sel),all(f)+(countAll?` (${pool.length})`:""),list(f).map(([v,l])=>[v,l,v.split("+").reduce((a,k)=>a+(cnt[k]||0),0)]));}
  $("#ftopic").hidden=!topicList(f).length;
  if(SC.have){const pool=DATA.questions.filter(x=>qMatch(x,f,"sl"));
    fill($("#fsol"),"วิธีทำ: ทั้งหมด",SOLOPTS.map(([v,l])=>[v,l,pool.filter(x=>qMatch(x,{...f,sl:v},null)).length]));}}
function apply(keepPos){
  let f=fstate();syncFacets(f);f=fstate();   // a select can fall back to "all" when its value vanished
  const had=filtered.length;filtered=DATA.questions.filter(x=>qMatch(x,f));
  // palette follows the subject on screen: the subject filter, else a result set that's all one subject
  const bioN=filtered.filter(x=>x.subject==="bio").length;
  setSubj(f.subj?(f.subj==="bio"?"bio":"chem"):!filtered.length?SUBJ:bioN===filtered.length?"bio":bioN?SUBJ:"chem");
  if(!keepPos) pIdx=0;
  $("#count").textContent=`${filtered.length} / ${DATA.questions.length} ข้อ`;
  render();if(had&&!filtered.length)SFX.play("empty");   // only on the step INTO no results, not every keystroke there
  const id=$("#q").value.trim().toUpperCase();if(/^Q-\d{4}$/.test(id))seen(filtered.find(x=>x.id===id));
}

function render(){
  const R=$("#root");dwell(null);$("#appbody").classList.toggle("clipx",view==="poster");
  if(!filtered.length){R.innerHTML='<div class="empty">ไม่พบข้อสอบที่ตรงกับเงื่อนไข</div>';return;}
  if(view==="poster") renderPoster(R);
  else if(view==="cards") renderCards(R);
  else if(view==="list") renderList(R);
  else renderPane(R);
  tex(R);
}
/* ---- POSTER (one question at a time, deck) ---- */
function posterHtml(q,i,anim){return `<article class="poster lv-${q.diff}${exCls(q)} ${anim||""}" data-i="${i}">
   <div class="pnum${qnum(q)>999?" l4":""}">${qnum(q)}</div>
   <div class="phead">${q.groupLabel}</div>
   <div class="pmeta">${idBadge(q)}${topicBadge(q)}${examBadge(q)}${diffBadge(q)}${typeBadge(q)}</div>
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
  const q=filtered[pIdx];if(!q)return;dwell(q);
  $("#deck").innerHTML=posterHtml(q,pIdx,anim);tex($("#deck"));
  $("#ppos").textContent=`${pIdx+1} / ${filtered.length}`;
  $("#pscrub").value=pIdx+1;
}
let pBusy=false;
function pstep(d){
  if(view!=="poster"||!filtered.length||pBusy) return;
  const p=$("#deck .poster");pBusy=true;
  if(p) p.classList.add(d>0?"outL":"outR");
  SFX.play("flip",d);
  setTimeout(()=>{pIdx=(pIdx+d+filtered.length)%filtered.length;fillPoster(d>0?"inR":"inL");pBusy=false;},180);
}
/* ---- CARDS ---- */
function cardHtml(q,idx){return `<div class="card lv-${q.diff}${exCls(q)}${idx<12?" anim":""}" data-i="${idx}" style="--i:${idx}">
   <span class="cnum">${qnum(q)}</span>
   <div class="card-top">${idBadge(q)}${chBadge(q)}${topicBadge(q)}${examBadge(q)}${diffBadge(q)}${typeBadge(q)}
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
    html+=`<div class="row${exCls(q)}" data-i="${i}">
      <div class="row-h"><span class="chev">▸</span><span class="row-id">${q.id}</span>
        <span class="diff-txt de-${q.diff}">${DIFF_TH[q.diff]||""}</span>
        <span class="row-snip">${q.snippet||""}</span>${topicBadge(q,false,true)}${examBadge(q)}</div>
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
  $("#detail").innerHTML=posterHtml(filtered[i],i,"enter");dwell(filtered[i]);tex($("#detail"));
}

/* ---- present modal ---- */
let mIdx=0;
function openModal(i){mIdx=i;fillModal();$("#modal").classList.add("show");INK.open();SFX.play(isEx(filtered[i])?"exOpen":"present");}
function closeModal(){if(!$("#modal").classList.contains("show"))return;$("#modal").classList.remove("show");INK.close();SFX.play("dismiss");
  dwell(view==="poster"&&document.body.classList.contains("inapp")?filtered[pIdx]:null);}
function fillModal(){
  const q=filtered[mIdx];dwell(q);
  $("#mtop").innerHTML=`${idBadge(q)}${chBadge(q)}${topicBadge(q,true)}${examBadge(q)}${diffBadge(q)}`;
  $("#mbody").innerHTML=q.bodyHtml+figHtml(q).replace(' loading="lazy"','');
  $("#mfoot").innerHTML=footHtml(q);
  const nb=$("#mnote");if(q.note){nb.style.display="block";nb.innerHTML="📌 "+q.note;}else nb.style.display="none";
  const ans=$("#mans");ans.classList.remove("show");
  ans.innerHTML=keyTxt(q)?`<b>เฉลยทางการ:</b> ${keyTxt(q)}`:q.solAnswer?`<b>ตอบ:</b> ${q.solAnswer}`:isEx(q)?`เฉลยอยู่ในวิธีทำด้านล่าง ↓`:`ข้อนี้ไม่มีเฉลยทางการ และยังไม่มีวิธีทำ`;
  $("#msol").innerHTML=solHtml(q);tex($("#msol"));
  $("#mpos").textContent=`${mIdx+1} / ${filtered.length}`;
  const sh=$("#modal .sheet");sh.classList.remove("lv-easy","lv-medium","lv-hard");if(q.diff)sh.classList.add("lv-"+q.diff);sh.classList.toggle("ex",isEx(q));sh.style.animation="none";void sh.offsetWidth;sh.style.animation="";
  if(window.prepShot)prepShot(150);
  INK.refresh();
  // fetch the neighbours' figures now so ◀ / ▶ show them (and can save them) without waiting
  [1,-1].forEach(d=>{const n=filtered[(mIdx+d+filtered.length)%filtered.length];if(n&&n.figure)(new Image()).src=n.figure;});
}
function step(d){mIdx=(mIdx+d+filtered.length)%filtered.length;fillModal();SFX.play("flip",d);}

/* ---- poster-pen: ink over the present sheet, and over the split-mode scratch board ----
   Question ink is stored normalised to #mbody (the question itself, not the viewport or the growing sheet), so a
   rotated iPad / resized window / opened solution keeps it on the same words. Board ink is stored in CSS px from the
   board's top-left: scratch paper is a fixed page seen through a window, so dragging the divider or rotating shows
   more or less of it but never stretches the handwriting or slides it off the 28px grid. One store per local day
   in localStorage: {d:"Y-M-D", q:{"Q-0751":[{t:"p"|"h", c:0-2, p:[x,y,x,y,...]}]}, b:{same, board}}; another day's
   store is wiped. */
const INK=(()=>{
  const K="cqb_ink",modal=$("#modal"),body=$("#mbody"),bar=$("#inkbar"),hist={};
  let S=null,on=false,split=false,tool="pen",col=0,cur=null,box=null,raf=0;
  const shown=()=>modal.classList.contains("show");
  const today=()=>{const d=new Date();return d.getFullYear()+"-"+(d.getMonth()+1)+"-"+d.getDate();};
  function load(){const t=today();if(S&&S.d===t)return;
    try{S=JSON.parse(ls.get(K,"null"));}catch(e){S=null;}
    if(!S||S.d!==t||!S.q||typeof S.q!=="object"){S={d:t,q:{},b:{}};ls.del(K);}
    if(!S.b||typeof S.b!=="object")S.b={};}
  const save=()=>ls.set(K,JSON.stringify(S));
  const qid=()=>{const q=filtered[mIdx];return q?q.id:"";};
  // the two surfaces share tools, store and one undo history per question; k = the surface's key in the store,
  // R rounds a stored coordinate (4 decimals of a fraction on the question, 0.1px on the board)
  const SF=[["q","#mink","#inkhl","#inkpen",1e4],["b","#mboard","#bhl","#bpen",10]].map(([k,w,h,p,r])=>
    ({k,wrap:$(w),cvH:$(h),cvP:$(p),xH:$(h).getContext("2d"),xP:$(p).getContext("2d"),R:v=>Math.round(v*r)/r,ox:0,oy:0,bw:1,bh:1,dirty:0}));
  const [SQ,SB]=SF;
  const list=s=>S[s.k][qid()]||[];
  function put(k,a){const id=qid();if(!id)return;if(a.length)S[k][id]=a;else delete S[k][id];}
  // one undo step = the previous stroke list of every surface the change touched
  function commit(after,before){const h=hist[qid()]=hist[qid()]||[];h.push(before);if(h.length>60)h.shift();
    for(const k in after)put(k,after[k]);save();frame(3);}
  // layout offsets, not getBoundingClientRect: the sheet's entry animation scales and rotates it
  function size(s){if(!shown())return;const w=s.wrap.clientWidth,h=s.wrap.clientHeight,d=window.devicePixelRatio||1;
    if(s===SQ){s.ox=body.offsetLeft;s.oy=body.offsetTop;s.bw=body.offsetWidth||1;s.bh=body.offsetHeight||1;}
    [s.cvH,s.cvP].forEach(c=>{c.style.width=w+"px";c.style.height=h+"px";c.width=Math.round(w*d);c.height=Math.round(h*d);c.getContext("2d").setTransform(d,0,0,d,0,0);});
    draw(s,3);}
  const sizeAll=()=>SF.forEach(size);
  // smoothed "ball pen": quadratic curves through the midpoints, straight into the last point
  function path(s,x,p){const n=p.length,X=i=>s.ox+p[i]*s.bw,Y=i=>s.oy+p[i+1]*s.bh;x.beginPath();x.moveTo(X(0),Y(0));
    if(n<6){x.lineTo(X(n-2)+.01,Y(n-2));return;}
    for(let i=2;i<n-2;i+=2)x.quadraticCurveTo(X(i),Y(i),(X(i)+X(i+2))/2,(Y(i)+Y(i+2))/2);
    x.lineTo(X(n-2),Y(n-2));}
  // colours are read at draw time, so the chem/bio palette and dark mode recolour existing ink.
  // The live stroke is drawn with its tail running to the pen tip; pointerup stores that same tip, so nothing jumps.
  function draw(s,m){const st=getComputedStyle(s.cvP),C=["--ink","--red","--blue","--yel"].map(v=>st.getPropertyValue(v).trim()),
      a=cur&&cur.s===s&&cur.p?list(s).concat([{t:cur.t,c:cur.c,p:cur.p.concat(tail(cur))}]):list(s),xH=s.xH,xP=s.xP;
    if(m&1){xH.clearRect(0,0,s.cvH.width,s.cvH.height);xH.save();xH.globalAlpha=.38;
      xH.globalCompositeOperation=document.body.classList.contains("dark")?"screen":"multiply";
      xH.strokeStyle=C[3];xH.lineWidth=22;xH.lineCap="butt";xH.lineJoin="round";
      a.forEach(t=>{if(t.t==="h"){path(s,xH,t.p);xH.stroke();}});xH.restore();}
    if(m&2){xP.clearRect(0,0,s.cvP.width,s.cvP.height);xP.lineWidth=3.2;xP.lineCap=xP.lineJoin="round";
      a.forEach(t=>{if(t.t==="p"){xP.strokeStyle=C[t.c]||C[0];path(s,xP,t.p);xP.stroke();}});}}
  function frame(m,s){(s?[s]:SF).forEach(x=>x.dirty|=m);
    if(!raf)raf=requestAnimationFrame(()=>{raf=0;SF.forEach(x=>{const d=x.dirty;x.dirty=0;if(d)draw(x,d);});});}
  // every pointer sample (coalesced: the pencil's full rate), in px relative to the surface's origin
  function pts(e){const ev=e.getCoalescedEvents&&e.getCoalescedEvents(),s=cur.s;
    return(ev&&ev.length?ev:[e]).map(v=>[v.clientX-box.left-s.ox,v.clientY-box.top-s.oy]);}
  // stabiliser: each sample pulls the pen point part-way toward it, more when the hand moves fast, so tremor and
  // pixel steps are ironed out without slow lag; points closer than 1.5px to the last kept one are dropped
  function add(P){const f=cur.f;P.forEach(([x,y])=>{cur.tip=[x,y];
      if(!f.length){f.push(x,y);keep(x,y);return;}
      const dx=x-f[0],dy=y-f[1],a=Math.min(1,.3+Math.hypot(dx,dy)/16);f[0]+=dx*a;f[1]+=dy*a;
      if(Math.hypot(f[0]-cur.k[0],f[1]-cur.k[1])>=1.5)keep(f[0],f[1]);});
    frame(cur.t==="h"?1:2,cur.s);}
  function keep(x,y){const s=cur.s;cur.k=[x,y];cur.p.push(s.R(x/s.bw),s.R(y/s.bh));}
  // the unsmoothed pen tip closes the stroke, so it ends exactly where the pen lifted
  function tail(c){const p=c.p,n=p.length,s=c.s,x=s.R(c.tip[0]/s.bw),y=s.R(c.tip[1]/s.bh);return p[n-2]===x&&p[n-1]===y?[]:[x,y];}
  // eraser: drops every whole stroke passing within reach (distance to each segment, in px)
  function near(s,p,X,Y,r){let ax=p[0]*s.bw,ay=p[1]*s.bh;if(Math.hypot(X-ax,Y-ay)<r)return true;
    for(let i=2;i<p.length;i+=2){const bx=p[i]*s.bw,by=p[i+1]*s.bh,dx=bx-ax,dy=by-ay,L=dx*dx+dy*dy,
        t=L?Math.max(0,Math.min(1,((X-ax)*dx+(Y-ay)*dy)/L)):0;
      if(Math.hypot(X-ax-t*dx,Y-ay-t*dy)<r)return true;ax=bx;ay=by;}return false;}
  function erase(P){const s=cur.s,a=list(s),k=a.filter(t=>!P.some(([x,y])=>near(s,t.p,x,y,t.t==="h"?24:14)));
    if(k.length!==a.length){put(s.k,k);cur.chg=1;frame(3,s);}}
  function finish(){const c=cur,s=c.s,k=s.k;cur=null;
    if(!c.p){if(c.chg)commit({[k]:list(s)},{[k]:c.before});return;}   // a whole erase gesture = one undo step
    c.p.push(...tail(c));
    commit({[k]:list(s).concat([{t:c.t,c:c.c,p:c.p}])},{[k]:list(s)});}
  const end=e=>{if(!cur||e.pointerId!==cur.id)return;if(e.type==="pointerup"&&cur.p)add(pts(e));finish();};
  SF.forEach(s=>{const cv=s.cvP;
    cv.addEventListener("pointerdown",e=>{if(!on||!e.isPrimary||e.pointerType==="touch")return;e.preventDefault();   // finger scrolls; Pencil + mouse write
      if(cur)finish();   // a stroke whose pointerup never arrived must not block the next one
      const sel=getSelection();if(sel&&sel.rangeCount)sel.removeAllRanges();
      try{cv.setPointerCapture(e.pointerId);}catch(_){}box=cv.getBoundingClientRect();
      if(tool==="er"){cur={s,id:e.pointerId,before:list(s)};erase(pts(e));return;}
      cur={s,id:e.pointerId,t:tool==="hl"?"h":"p",c:col,p:[],f:[],k:null,tip:null};add(pts(e));});
    cv.addEventListener("pointermove",e=>{if(cur&&e.pointerId===cur.id){const P=pts(e);cur.p?add(P):erase(P);}});
    ["pointerup","pointercancel","lostpointercapture"].forEach(ev=>cv.addEventListener(ev,end));
    // iPad: a quick second tap is a double-tap to Safari (select text / zoom / callout), and cancelling the pointer
    // events doesn't stop that; cancelling the touch does. Mouse/desktop: no double-click select or context menu.
    // finger touches are left alone so they scroll; only the Pencil's (touchType "stylus") are cancelled
    const pen=e=>!e.changedTouches||[...e.changedTouches].some(t=>t.touchType==="stylus");
    ["touchstart","touchmove","dblclick","selectstart","contextmenu","gesturestart"].forEach(ev=>
      cv.addEventListener(ev,e=>{if(on&&(!ev.startsWith("touch")||pen(e)))e.preventDefault();},{passive:false}));});
  function setOn(v){on=v;modal.classList.toggle("inking",v);bar.classList.toggle("show",v);
    const b=$("#inkw");b.classList.toggle("on",v);b.setAttribute("aria-pressed",v);}
  // split is a view, not a tool: it stays on when write mode goes off (the board just stops taking ink)
  function setSplit(v){split=v;modal.classList.toggle("split",v);lay();
    const b=$("#inksplit");b.classList.toggle("sel",v);b.setAttribute("aria-pressed",v);}
  function mark(){bar.querySelectorAll("[data-c]").forEach(b=>b.classList.toggle("sel",tool==="pen"&&+b.dataset.c===col));
    bar.querySelectorAll("[data-t]").forEach(b=>b.classList.toggle("sel",tool===b.dataset.t));}
  $("#inkw").addEventListener("click",e=>{e.currentTarget.blur();if(!cur){setOn(!on);SFX.play(on?"penOn":"penOff");}});
  bar.addEventListener("click",e=>{const b=e.target.closest("button");if(!b||cur)return;b.blur();
    if(b.dataset.c||b.dataset.t){tool=b.dataset.t||"pen";if(b.dataset.c)col=+b.dataset.c;mark();SFX.play("tool",b.dataset.t||col);}
    else if(b.id==="inksplit"){setSplit(!split);SFX.play(split?"splitOn":"splitOff");return;}
    else if(b.id==="inkundo"){const h=hist[qid()];if(!h||!h.length)return;const p=h.pop();for(const k in p)put(k,p[k]);save();frame(3);SFX.play("undo");}
    // 🧹 clears what you can see: the question, plus the board while it's on screen (one undo step)
    else if(b.id==="inkclr"){const a={q:[]},p={q:list(SQ)};if(split){a.b=[];p.b=list(SB);}
      if(!p.q.length&&!(p.b&&p.b.length))return;commit(a,p);SFX.play("clear");}
    else if(b.id==="inkwipe"){if(!confirm("ล้างหมึกทั้งหมด? (ทุกข้อ)"))return;S={d:today(),q:{},b:{}};Object.keys(hist).forEach(k=>delete hist[k]);ls.del(K);frame(3);SFX.play("wipe");}});
  // divider: the question's share of the space beside the 28px bar, remembered per orientation
  const DK="cqb_split",div=$("#mdiv");let SR={},drag=null;
  try{SR=JSON.parse(ls.get(DK,"{}"))||{};}catch(e){}
  function span(){const r=modal.getBoundingClientRect(),cs=getComputedStyle(modal),P=matchMedia("(orientation:portrait)").matches,
      pt=parseFloat(cs.paddingTop),pl=parseFloat(cs.paddingLeft);
    return P?{P,a:r.top+pt,n:modal.clientHeight-pt-parseFloat(cs.paddingBottom)-28}:{P,a:r.left+pl,n:modal.clientWidth-pl-parseFloat(cs.paddingRight)-28};}
  // px = wanted question size (default: the remembered ratio); clamped so neither side gets unusably small
  function lay(px){if(!split||!shown())return 0;const z=span(),lo=z.P?150:240,hi=z.n-(z.P?200:280);
    if(px==null)px=(+SR[z.P?"p":"l"]||(z.P?.36:.38))*z.n;
    px=Math.round(hi<lo?z.n/2:Math.max(lo,Math.min(hi,px)));modal.style.setProperty("--sq",px+"px");return px;}
  div.addEventListener("pointerdown",e=>{if(!split)return;e.preventDefault();drag=e.pointerId;try{div.setPointerCapture(e.pointerId);}catch(_){}});
  div.addEventListener("pointermove",e=>{if(e.pointerId!==drag)return;const z=span();
    SR[z.P?"p":"l"]=+(lay((z.P?e.clientY:e.clientX)-z.a-14)/z.n).toFixed(4);});
  ["pointerup","pointercancel","lostpointercapture"].forEach(ev=>div.addEventListener(ev,e=>{if(e.pointerId!==drag)return;drag=null;ls.set(DK,JSON.stringify(SR));SFX.play("snap");}));
  new MutationObserver(()=>{if(shown())frame(3);}).observe(document.body,{attributes:true,attributeFilter:["class","data-subj"]});
  if(window.ResizeObserver){const ro=new ResizeObserver(sizeAll);[SQ.wrap,body,SB.wrap].forEach(el=>ro.observe(el));}
  addEventListener("resize",()=>{lay();sizeAll();});
  return{open(){load();setOn(false);sizeAll();},close(){cur=null;setOn(false);setSplit(false);},
         refresh(){if(!shown())return;cur=null;load();sizeAll();},toggle(){setOn(!on);SFX.play(on?"penOn":"penOff");}};
})();

/* ---- view switch ---- */
$("#layout").querySelectorAll("button").forEach(b=>{
  b.classList.toggle("on",b.dataset.v===view);
  b.onclick=()=>{view=b.dataset.v;ls.set("cqb_view",view);SFX.play("view",[...b.parentElement.children].indexOf(b));
    $("#layout").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x.dataset.v===view));render();};
});
["input","change"].forEach(ev=>{$("#q").addEventListener(ev,()=>apply());
  ["#fch","#ftopic","#fexam","#fyear","#fdiff","#ftype","#fsol"].forEach(s=>$(s).addEventListener(ev,()=>apply()));});
$("#fsubj").addEventListener("change",()=>{populateChapters($("#fsubj").value);apply();});
["#fsubj","#fch","#fexam","#fyear","#fdiff","#ftype","#fsol","#ftopic"].forEach((s,i)=>$(s).addEventListener("change",()=>SFX.play("filter",i)));
$("#random").onclick=()=>{if(!filtered.length)return;SFX.play("dice");const i=Math.floor(Math.random()*filtered.length);setTimeout(()=>openModal(i),380);};
$("#ftoggle").onclick=()=>{SFX.play($("#hdr").classList.toggle("fopen")?"unfold":"fold");};

/* the question a click landed in: the modal's, else the nearest [data-i] (poster / card / row) */
const qAt=el=>el.closest("#modal")?filtered[mIdx]:(el=el.closest("[data-i]"))&&filtered[+el.dataset.i];
/* ---- solution toggle (delegated: every view + the modal) ---- */
function solToggle(e){
  const b=e.target.closest(".solbtn");
  if(!b) return false;
  e.stopPropagation();
  const w=b.nextElementSibling;
  if(w && w.classList.contains("solwrap")){
    const open=w.classList.toggle("show");
    SFX.play(open?"reveal":"conceal");if(open)seen(qAt(b));
    b.textContent = open ? "ซ่อนวิธีทำ ↑" : (b.dataset.label || "ดูวิธีทำ →");
  }
  return true;
}
// one mark per question: marking a line clears any other mark in that question; tapping the marked one clears it
function markChoice(e){const li=e.target.closest(".body li");if(!li)return false;
  const on=!li.classList.contains("mk");
  li.closest(".body").querySelectorAll("li.mk").forEach(x=>x.classList.remove("mk"));
  if(on){li.classList.add("mk");seen(qAt(li));}SFX.play(on?"mark":"unmark",[...li.parentElement.children].indexOf(li));return true;}
$("#root").addEventListener("click",e=>{
  if(solToggle(e)) return;
  if(e.target.closest("#pprev")){pstep(-1);return;}
  if(e.target.closest("#pnext")){pstep(1);return;}
  const p=e.target.closest(".present-btn");if(p){openModal(+p.dataset.i);return;}
  const tb=e.target.closest("button.b-st");if(tb){SFX.play("bar",0);resetFilters();topicFilters(tb.dataset.ch,tb.dataset.st);apply();window.scrollTo(0,0);return;}
  const bm=e.target.closest(".b-more");if(bm){bm.closest(".row-h").classList.add("allst");SFX.play("select");return;}   // list row: show the extra sub-topics
  const item=e.target.closest(".pane-item");if(item){SFX.play("select");paneShow(+item.dataset.i);return;}
  const rh=e.target.closest(".row-h");if(rh){SFX.play(rh.parentElement.classList.toggle("open")?"unfold":"fold");return;}
  markChoice(e);
});
$("#root").addEventListener("input",e=>{
  if(e.target.id==="pscrub"){pIdx=(+e.target.value)-1;fillPoster("");SFX.play("tick");return;}
});
$("#msol").addEventListener("click",solToggle);
$("#mbody").addEventListener("click",e=>{if(markChoice(e)&&window.prepShot)prepShot(250);});

$("#mx").onclick=closeModal;
$("#modal").onclick=e=>{if(e.target.id==="modal")closeModal();};
$("#mreveal").onclick=()=>{const open=$("#mans").classList.toggle("show");SFX.play(open?"reveal":"conceal");if(open)seen(filtered[mIdx]);};
$("#mprev").onclick=()=>step(-1);$("#mnext").onclick=()=>step(1);

/* ---- keyboard ---- */
document.addEventListener("keydown",e=>{
  if(e.target.classList&&e.target.classList.contains("vol"))return;   // arrows on the volume slider adjust volume only
  const typing=/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)&&e.target.type!=="range";
  if(PD.isOpen()){if(e.key==="Escape")PD.close();return;}   // drawer open: keys stay inside it
  if(TD.isOpen()){if(e.key==="Escape")TD.close();return;}
  if(VS.isOpen()){if(e.key==="Escape")VS.close();return;}
  if(TM.isOpen()&&!typing){if(e.key==="Escape"){TM.close();return;}if(e.key===" "){e.preventDefault();TM.toggle();return;}}
  if($("#modal").classList.contains("show")){
    if(e.key==="Escape")closeModal();
    if(e.key==="ArrowLeft")step(-1);if(e.key==="ArrowRight")step(1);
    if((e.key==="p"||e.key==="P")&&!e.ctrlKey&&!e.metaKey&&!e.altKey)INK.toggle();
    return;
  }
  if(typing){if(e.key==="Escape")e.target.blur();return;}
  if(!document.body.classList.contains("inapp")){if(e.key==="/"){e.preventDefault();$("#lq").focus();}else if(e.key==="m"||e.key==="M")toggleSfx();
    else if(e.key==="Escape")statSet($("#board .tile.st.open"),false);return;}
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
      h+=`<div class="pde k-${e.cat}" data-z="${e.z}" data-w="${r+c-2}" style="grid-row:${r};grid-column:${c}"><div class="pf"><i>${e.z}</i><b>${e.s}</b><s>${fm(e)}</s></div><em class="pb">${e.z}</em></div>`;});
    h+=`<div class="pdph" style="grid-row:6;grid-column:3">57–71</div><div class="pdph" style="grid-row:7;grid-column:3">89–103</div><div style="grid-row:8;grid-column:1;height:10px"></div>`;
    h+=`<div class="pdinfo"><div class="pdbig" id="pdbig"></div><div class="pdbrk" id="pdbrk"></div></div>`;
    G.innerHTML=h;
    $("#pdkeys").innerHTML=["(",")","[","]","·"].map(k=>`<button class="kp" data-k="${k}">${k}</button>`).join("")+`<span class="sep"></span>`+[..."1234567890"].map(k=>`<button data-k="${k}">${k}</button>`).join("")+`<span class="sep"></span><button class="kx" data-k="bk" title="ลบตัวสุดท้าย">⌫</button><button class="kx" data-k="clr">ล้าง</button><span class="tip">คลิกซ้าย = เพิ่มธาตุ · คลิกขวา = ลดทีละ 1</span>`;
    big(BY[1]);update();built=true;}
  // big tile: an element, or (e null) the memorize-mode neutral card that gives nothing away; fx = the flip-in reveal
  let shown=0;
  const big=(e,fx)=>{const b=$("#pdbig");b.classList.toggle("nil",!e);shown=e?e.z:0;
    if(e){last=e;b.innerHTML=`<i>${e.z}</i>${e.s}<u>${e.n}</u><s>${fm(e)}</s>`;}else b.innerHTML=`<i>&nbsp;</i>?<u>แตะธาตุเพื่อเปิด</u><s>&nbsp;</s>`;
    if(fx){b.classList.remove("pdrev");void b.offsetWidth;b.classList.add("pdrev");}};
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
  function open(){if(TD.isOpen())TD.close();if(!built)build();else if(memOn)setMem(false,1);refreshQ();document.body.classList.add("pdopen");SFX.play("drawer","pd");}
  function close(){if(!isOpen())return;document.body.classList.remove("pdopen");SFX.play("undrawer");}
  // Mw on: a tap adds the element to the formula. Mw off: a tap only shows it in the big tile.
  let mwOn=ls.get("cqb_mw2","0")==="1";   // off by default; new key so the old saved "on" does not stick
  function setMw(on){mwOn=on;ls.set("cqb_mw2",on?"1":"0");$("#pd").classList.toggle("nomw",!on);
    $("#pdmwt").classList.toggle("on",on);$("#pdmwt").textContent=on?"🧮 คิด Mw: เปิด":"🧮 คิด Mw: ปิด";}
  setMw(mwOn);
  $("#pdmwt").onclick=()=>{setMw(!mwOn);SFX.play(mwOn?"on":"off");};
  // ท่องตารางธาตุ: on = every tile face-down (only Z shows) in an eased diagonal ripple; each tap turns ONE tile over, open <-> closed,
  // and the big tile shows what was just opened (neutral "?" at the start / when the shown one is closed). Taps never touch Mw here.
  // Off = everything face-up. Always starts off: never saved, and reopening the drawer snaps it back off without animating.
  let memOn=false,memT=0;
  const ripple=t=>Math.round(420*(1-Math.cos(Math.PI*t.dataset.w/24)));   // 0..840 ms, eased; 24 = the far end of the f-row
  function setMem(on,quiet){memOn=on;const b=$("#pdmem");b.classList.toggle("on",on);b.setAttribute("aria-pressed",on);b.textContent=on?"🃏 ท่องตารางธาตุ: เปิด":"🃏 ท่องตารางธาตุ: ปิด";
    $("#pdrst").hidden=!on;clearTimeout(memT);
    if(quiet)G.classList.add("still");
    if(on){G.classList.add("mem");void G.offsetWidth;}   // backs exist before the turn starts, so the first flip transitions too
    G.querySelectorAll(".pde").forEach(t=>{t.style.setProperty("--d",ripple(t)+"ms");
      if(on){t.classList.remove("up","pdflash");t.classList.add("dn");t.tabIndex=0;}
      else{t.removeAttribute("tabindex");if(t.classList.contains("dn")){t.classList.remove("dn");if(!quiet)t.classList.add("up");}}});
    if(!on){if(quiet)G.classList.remove("mem");else memT=setTimeout(()=>G.classList.remove("mem"),1500);}   // drop the backs once the wave is over
    if(quiet){void G.offsetWidth;G.classList.remove("still");}
    big(on?null:last,!quiet);}
  $("#pdmem").onclick=()=>{setMem(!memOn);SFX.play(memOn?"memOn":"memOff");};
  $("#pdrst").onclick=()=>{const up=[...G.querySelectorAll(".pde:not(.dn)")],d0=Math.min(...up.map(ripple));   // only open tiles turn; the wave starts at the first of them
    up.forEach(t=>{t.style.setProperty("--d",ripple(t)-d0+"ms");t.classList.remove("up");t.classList.add("dn");});big(null,1);SFX.play("memReset");};
  G.addEventListener("animationend",e=>{if(e.animationName==="pdlu")e.target.classList.remove("up");});
  G.addEventListener("click",e=>{const t=e.target.closest(".pde");if(!t)return;const el=BY[t.dataset.z];
    if(memOn){if(Date.now()-(t._ft||0)<350)return;t._ft=Date.now();t.style.setProperty("--d","0ms");   // a fast double-tap is one turn, not open-then-shut
      if(t.classList.contains("dn")){t.classList.replace("dn","up");big(el,1);SFX.play("memFlip",el.p);}
      else{t.classList.remove("up");t.classList.add("dn");if(shown===el.z)big(null,1);SFX.play("memUnflip",el.p);}
      return;}
    if(mwOn)addSym(el.s);SFX.play(mwOn?"add":"element",el.z);big(el);flash(el.z);});
  G.addEventListener("keydown",e=>{const t=e.target.closest(".pde");if(t&&(e.key==="Enter"||e.key===" ")){e.preventDefault();t.click();}});
  G.addEventListener("contextmenu",e=>{const t=e.target.closest(".pde");if(!t||!mwOn||memOn)return;e.preventDefault();const el=BY[t.dataset.z];big(el);
    if(decSym(el.s)){flash(el.z);SFX.play("remove");}else SFX.play("bad");});
  G.addEventListener("mouseover",e=>{const t=e.target.closest(".pde");if(t){const el=BY[t.dataset.z];$("#pdhov").textContent=t.classList.contains("dn")?`Z ${el.z} · ?`:`${el.s} · ${el.n} · Z ${el.z} · ${fm(el)}`;}});
  inp.addEventListener("input",update);
  $("#pdkeys").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;const k=b.dataset.k;SFX.play("key",k);
    if(k=="bk")put(inp.value.slice(0,-1));else if(k=="clr")put("");else put(inp.value+k);});
  $("#pdq").addEventListener("click",e=>{const b=e.target.closest("button");if(b){put(b.dataset.f);SFX.play("select");}});
  $("#pdtab").onclick=open;$("#pdx").onclick=close;$("#pdscrim").onclick=close;
  return{open,close,isOpen,parseF,curQ,load(v){open();if(!mwOn)setMw(true);put(v);}};
})();
$("#mpt").onclick=()=>PD.open();
/* 💾 save the question on screen as a PNG: badges + question + choices only: no 📌 note, solution or controls.
   html2canvas loads from the CDN on first use; on touch devices the share sheet offers "Save Image". */
let h2cP=null;
function loadH2C(){return h2cP||(h2cP=new Promise((res,rej)=>{const sc=document.createElement("script");
  sc.src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js";
  sc.onload=()=>res(window.html2canvas);sc.onerror=()=>{h2cP=null;rej(Object.assign(new Error("cdn"),{cdn:1}));};document.head.appendChild(sc);}));}
function shotKey(){const q=filtered[mIdx];if(!q)return"";
  return q.id+"|"+document.body.className+"|"+$("#mtop").innerHTML+"|"+$("#mbody").innerHTML;}
const imgsReady=root=>Promise.all([...root.querySelectorAll("img")].map(im=>im.complete?0:new Promise(r=>{im.addEventListener("load",r,{once:true});im.addEventListener("error",r,{once:true});})));
async function renderShot(){const q=filtered[mIdx];const h2c=await loadH2C();
  // let the figure on screen finish downloading first; cloning earlier starts a second parallel download of the same file
  await imgsReady($("#mbody"));
  const wrap=document.createElement("div");wrap.className="shotwrap";
  const sh=document.createElement("div");sh.className=$("#modal .sheet").className+" shot";
  ["#mtop","#mbody"].forEach(sel=>sh.appendChild($(sel).cloneNode(true)));
  sh.querySelectorAll("[id]").forEach(e=>e.removeAttribute("id"));sh.querySelectorAll("img").forEach(im=>im.loading="eager");
  const sd=document.createElement("div");sd.className="shotsd";wrap.appendChild(sd);
  wrap.appendChild(sh);document.body.appendChild(wrap);
  try{
    // html2canvas can't draw box-shadow, so the difficulty-coloured offset block is a real div behind the sheet
    sd.style.cssText=`left:${sh.offsetLeft+12}px;top:${sh.offsetTop+12}px;width:${sh.offsetWidth}px;height:${sh.offsetHeight}px;background:${q.diff==="easy"?"var(--blue)":q.diff==="medium"?"var(--yel)":"var(--red)"}`;
    if(document.fonts&&document.fonts.ready)await document.fonts.ready;
    // any figure in the question goes into the PNG too: wait until every image has loaded
    await imgsReady(sh);
    const cv=await h2c(wrap,{scale:2,backgroundColor:getComputedStyle(wrap).backgroundColor,logging:false,   // same-origin figures: no useCORS, so the copy on screen is reused, not downloaded again
      
      // copy only the capture box, not the whole page (list view is ~45k elements)
      ignoreElements:el=>document.body.contains(el)&&el!==document.body&&!wrap.contains(el)&&!el.contains(wrap),
      onclone:doc=>{const c=doc.querySelector(".shotwrap");if(c)c.style.opacity="1";}});
    // a scanned figure makes a huge PNG that is slow to encode on iPad; those go out as a high-quality JPG
    const jpg=!!sh.querySelector("img");
    const blob=await new Promise(r=>cv.toBlob(r,jpg?"image/jpeg":"image/png",jpg?.92:undefined));if(!blob)throw new Error("blob");return blob;
  }finally{wrap.remove();}}
/* the PNG is made in the background while you look at the question, so the button only hands it over */
let shot={key:"",blob:null,job:null},shotT=0;
function prepShot(delay){clearTimeout(shotT);shotT=setTimeout(()=>{
  if(!$("#modal").classList.contains("show"))return;const k=shotKey();
  if(shot.key===k&&(shot.blob||shot.job))return;
  const job=renderShot();shot={key:k,blob:null,job};
  job.then(b=>{if(shot.job===job)shot.blob=b;},()=>{if(shot.job===job)shot={key:"",blob:null,job:null};});},delay);}
function deliverShot(blob,name){const file=new File([blob],name,{type:blob.type});
  const dl=()=>{const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();
    setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},1500);};
  if(matchMedia("(pointer:coarse)").matches&&navigator.canShare&&navigator.canShare({files:[file]}))
    return navigator.share({files:[file]}).catch(e=>{if(e&&e.name!=="AbortError")dl();});
  dl();}
async function saveShot(){const q=filtered[mIdx],b=$("#mshot");if(!q||b.disabled)return;
  const lbl="💾 บันทึกเป็นรูป",k=shotKey();const nm=b=>`${q.id}.${b.type==="image/jpeg"?"jpg":"png"}`;
  if(shot.key===k&&shot.blob){deliverShot(shot.blob,nm(shot.blob));SFX.play("saved");b.textContent="✅ บันทึกแล้ว";setTimeout(()=>{b.textContent=lbl;},1200);return;}
  b.disabled=true;b.textContent="กำลังสร้างรูป…";
  try{if(!(shot.key===k&&shot.job)){const job=renderShot();shot={key:k,blob:null,job};}
    const blob=await shot.job;shot.blob=blob;deliverShot(blob,nm(blob));
    SFX.play("saved");b.textContent="✅ บันทึกแล้ว";setTimeout(()=>{b.textContent=lbl;},1200);
  }catch(e){shot={key:"",blob:null,job:null};b.textContent=lbl;console.error(e);alert(e&&e.cdn?"บันทึกรูปไม่ได้ — ต้องต่ออินเทอร์เน็ตครั้งแรกเพื่อโหลดตัวสร้างรูป":"บันทึกรูปไม่ได้ — สร้างรูปข้อนี้ไม่สำเร็จ ลองอีกครั้ง");}
  finally{b.disabled=false;}}
$("#mshot").onclick=saveShot;
// fetch the image maker quietly once the site has settled, so the first save doesn't wait on the CDN
setTimeout(()=>{(window.requestIdleCallback||setTimeout)(()=>loadH2C().catch(()=>{}));},4000);


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
    $("#cvcat").onclick=e=>{const b=e.target.closest("button");if(!b)return;cat=b.dataset.c;unit=Object.keys(CV[cat].u)[0];SFX.play("select");cvRender();};
    $("#cvx").addEventListener("input",cvCalc);$("#cvu").onchange=()=>{unit=$("#cvu").value;SFX.play("select");cvCalc();};
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
    $("#fxchips").onclick=e=>{const b=e.target.closest("button");if(!b)return;SFX.play("select");
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
    document.body.classList.add("tdopen");fxFit();SFX.play("drawer","td");}
  function close(){if(!isOpen())return;document.body.classList.remove("tdopen");SFX.play("undrawer");}
  $("#tdtabs").onclick=e=>{const b=e.target.closest("button");if(!b)return;SFX.play("tab",[...b.parentElement.children].indexOf(b));
    $("#tdtabs").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x===b));
    document.querySelectorAll(".tdpane").forEach(p=>p.classList.toggle("on",p.id==="td-"+b.dataset.t));fxFit();};
  $("#tdtab").onclick=open;$("#tdx").onclick=close;
  $("#pdscrim").onclick=()=>{PD.close();close();TM.close();};
  return{open,close,isOpen};
})();

/* ================= VSEPR 3D (left drawer, vsepr.html in an iframe, loaded on first open) ================= */
const VS=(()=>{
  const isOpen=()=>document.body.classList.contains("vsopen");
  function open(){if(PD.isOpen())PD.close();if(TD.isOpen())TD.close();
    const f=$("#vsf");if(!f.src)f.src="vsepr.html?embed=1";
    document.body.classList.add("vsopen");SFX.play("drawer","vs");}
  function close(){if(!isOpen())return;document.body.classList.remove("vsopen");SFX.play("undrawer");}
  $("#vstab").onclick=()=>isOpen()?close():open();$("#vsx").onclick=close;
  $("#pdscrim").addEventListener("click",close);
  // Esc pressed inside the 3D view closes the drawer too
  $("#vsf").addEventListener("load",()=>{try{$("#vsf").contentWindow.addEventListener("keydown",e=>{if(e.key==="Escape")close();});}catch(_){}});
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
    SFX.play("ring");draw();}
  function start(){if(mode==="down"&&left<=0)left=total;rang=false;$("#tmface").classList.remove("done");$("#tmmini").classList.remove("done");
    running=true;t0=Date.now();clearInterval(iv);iv=setInterval(draw,200);SFX.play("start");draw();}
  function pause(){const el=(Date.now()-t0)/1000;if(mode==="down")left=Math.max(0,left-el);else up+=el;running=false;clearInterval(iv);SFX.play("pause");draw();}
  function reset(){running=false;clearInterval(iv);left=total;up=0;$("#tmface").classList.remove("done");$("#tmmini").classList.remove("done");SFX.play("reset");draw();}
  function setMode(m){if(running)pause();mode=m;document.getElementById("tm").classList.toggle("tm-up",m==="up");
    $("#tmseg").querySelectorAll("button").forEach(b=>b.classList.toggle("on",b.dataset.m===m));SFX.play("tab",m==="up"?1:0);draw();}
  function setTotal(sec){if(running)return;total=Math.max(10,Math.min(5*3600,sec));left=total;$("#tmface").classList.remove("done");SFX.play("key");draw();}
  const isOpen=()=>document.body.classList.contains("tmopen");
  function open(){document.body.classList.add("tmopen");SFX.play("drawer","tm");}
  function close(){if(!isOpen())return;document.body.classList.remove("tmopen");SFX.play("undrawer");}
  $("#tmgo").onclick=()=>running?pause():start();$("#tmreset").onclick=reset;
  $("#tmseg").onclick=e=>{const b=e.target.closest("button");if(b&&b.dataset.m!==mode)setMode(b.dataset.m);};
  $("#tmpre").onclick=e=>{const b=e.target.closest("button");if(b)setTotal(+b.dataset.m*60);};
  document.querySelector(".tmadj").onclick=e=>{const b=e.target.closest("button");if(b)setTotal(total+ +b.dataset.a);};
  $("#tmtab").onclick=()=>isOpen()?close():open();$("#tmx").onclick=close;
  // corner widget: a bigger always-visible clock, switched from the panel, remembered
  function setMini(on){$("#tmmini").classList.toggle("show",on);$("#tmfull").classList.toggle("on",on);
    $("#tmfull").textContent=on?"✓ นาฬิกามุมจอ (กดเพื่อซ่อน)":"⧉ แสดงนาฬิกามุมจอ";ls.set("cqb_tmmini",on?"1":"0");}
  $("#tmfull").onclick=()=>{setMini(!$("#tmmini").classList.contains("show"));SFX.play($("#tmmini").classList.contains("show")?"on":"off");};
  $("#tmmx").onclick=()=>{setMini(false);SFX.play("off");};
  $("#tmmgo").onclick=()=>running?pause():start();$("#tmmreset").onclick=reset;$("#tmmd").onclick=()=>isOpen()?close():open();
  setMini(ls.get("cqb_tmmini","0")==="1");
  draw();
  return{open,close,isOpen,toggle:()=>running?pause():start()};
})();

/* ================= LANDING (grid board) ================= */
const PAL=["c-red","c-yel","c-blue","c-card","c-ink","c-card","c-yel","c-red","c-card","c-blue"];
function cov(qs){const n=qs.length;return n?Math.round(qs.filter(hasSol).length/n*100):0;}
function tileSize(n,max){const r=n/max;return r>=.8?"w2 h2 big":r>=.5?"w2":"";}
/* subject icons: flat inline SVG, ink parts = currentColor, accent = var(--red), so they follow palette + dark mode
   (var() must go in style="", SVG presentation attributes don't resolve it) */
const ICON={
 chem:`<svg class="sic" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M8 2h8v2h-1.5v5.2l5.9 10.3A1.7 1.7 0 0 1 18.9 22H5.1a1.7 1.7 0 0 1-1.5-2.5l5.9-10.3V4H8z"/><path style="fill:var(--red)" d="M6.7 15.4h10.6l2 3.6a.7.7 0 0 1-.6 1H5.3a.7.7 0 0 1-.6-1z"/></svg>`,
 bio:`<svg class="sic" viewBox="0 0 24 24" aria-hidden="true"><g fill="none" stroke-width="2.6" stroke-linecap="round"><path stroke="currentColor" d="M7 2c0 5 10 5 10 10s-10 5-10 10"/><path style="stroke:var(--red)" d="M17 2c0 5-10 5-10 10s10 5 10 10"/><path stroke="currentColor" stroke-width="1.8" d="M8.6 4.2h6.8M8.6 12h6.8M8.6 19.8h6.8"/></g></svg>`};
const BPAL=["c-red","c-acc","c-blue","c-yel","c-card","c-acc","c-ink"];
/* plain text of a question for the recent preview: DOMParser is inert (never fetches the <img>s), and the
   cut is by characters -- Thai has no spaces to cut at -- stepping past combining vowel/tone marks so a
   base consonant never loses its mark */
function plainClip(html,n){const s=new DOMParser().parseFromString(html,"text/html").body.textContent.replace(/\s+/g," ").trim();
  if(s.length<=n)return s;let e=n;while(e<s.length&&/[\u0E31\u0E34-\u0E3A\u0E47-\u0E4E]/.test(s[e]))e++;return s.slice(0,e).trimEnd()+"…";}
function recentHtml(){
  const rq=RECENT.map(id=>DATA.questions.find(x=>x.id===id)).filter(Boolean);if(!rq.length)return"";
  const q=rq[0];
  return `<div class="tile c-card recent full" style="--i:0"><div class="rtop"><span class="rk">🕘 เพิ่งดู</span>${idBadge(q)}${chBadge(q)}${topicBadge(q)}${examBadge(q)}${diffBadge(q)}</div>
    <div class="rtx">${plainClip(q.bodyHtml,160).replace(/&/g,"&amp;").replace(/</g,"&lt;")}</div>
    <button class="rgo" data-go="qid" data-q="${q.id}">ทำต่อ →</button>
    ${rq.length>1?`<div class="rl">${rq.slice(1,6).map(q=>`<button data-go="qid" data-q="${q.id}" title="${(q.snippet||"").replace(/<[^>]+>/g,"").replace(/"/g,"&quot;").slice(0,90)}">${isEx(q)?"✎"+qnum(q):q.id.slice(2)} · ${q.subject==="bio"?"ชีวะ":q.subject==="applied"?"ประยุกต์":"บท "+parseInt(q.ch)}</button>`).join("")}</div>`:""}</div>`;}
function heroHtml(){
  const bio=DATA.questions.filter(q=>q.subject==="bio"),si=SUBJS.indexOf(SUBJ);
  const bex=[...new Set(bio.map(q=>(DATA.exams[q.exam]||{label:q.exam}).label))].join(" · ");
  const yrs=bio.map(q=>q.year).filter(Boolean).sort(),yr=yrs.length?` ปี ${yrs[0]}${yrs[0]!==yrs[yrs.length-1]?"–"+yrs[yrs.length-1]:""}`:"";
  const nav=SUBJS.length<2?"":`<div class="hnav"><button class="hdot${si===0?" on":""}" data-s="0">${ICON.chem}เคมี</button><button class="hdot${si===1?" on":""}" data-s="1">${ICON.bio}ชีววิทยา</button>
    <button class="harr hsp" data-d="-1" title="วิชาก่อนหน้า (←)">‹</button><button class="harr" data-d="1" title="วิชาถัดไป (→)">›</button></div>`;
  return `<div class="tile hero" tabindex="0" aria-label="เลือกวิชา · ปัดหรือกด ← →">${nav}<div class="htrack">
    <div class="hpanel"><b>${DATA.chemcount}${ICON.chem}</b><span>ข้อสอบเคมี<br>แยกตามบท</span><small>สอวน. · PAT2 · A-Level · 9 วิชาสามัญ<br>เลือกบทด้านข้าง หรือกด ทุกบท</small></div>
    ${SUBJS.length>1?`<div class="hpanel"><b>${DATA.biocount}${ICON.bio}</b><span>ข้อสอบชีววิทยา<br>แยกตามหัวข้อ</span><small>${bex}${yr}<br>เลือกหัวข้อด้านข้าง หรือกด ทุกหัวข้อ</small></div>`:""}</div></div>`;}
/* every tile that depends on the chosen subject (rebuilt on a switch; hero + recent stay put) */
function subjTiles(){
  const bio=SUBJ==="bio",pool=DATA.questions.filter(q=>subjOf(q)===SUBJ&&!isEx(q)),name=bio?"ชีววิทยา":"เคมี";   // tiles count exams only
  const groups=bio?Object.entries(DATA.bioChapters).map(([k,n])=>[k,n,DATA.biocounts[k]||0]):CHS.map(([k,n])=>[k,n,DATA.counts[k]||0]);
  const max=Math.max(...groups.map(g=>g[2])),P=bio?BPAL:PAL;let i=2;
  let h=`<button class="tile c-ink" data-go="all" style="--i:${i++}"><span class="no">∀</span><span class="nm">${bio?"ทุกหัวข้อ":"ทุกบท"}</span><span class="ct">${pool.length} ข้อ · ${name}</span></button>`;
  h+=`<button class="tile c-yel" data-go="random" style="--i:${i++}"><span class="no">🎲</span><span class="nm">สุ่ม 1 ข้อ</span><span class="ct">จาก${name}ทั้งหมด</span></button>`;
  if(!bio&&EXN)h+=`<button class="tile c-card ex" data-go="ex" style="--i:${i++}"><span class="no">✎</span><span class="nm">แบบฝึกหัด</span><span class="ct">${EXN} ข้อ · มีเฉลยทุกข้อ</span></button>`;
  groups.forEach(([k,gname,c],j)=>{if(!c)return;
    const cv=cov(pool.filter(q=>chOf(q,SUBJ)===k)),cls=`tile ${P[j%P.length]} ${tileSize(c,max)}`,n=parseInt(k),ii=i++;
    const face=`<span class="no">${n}</span><span class="nm">${gname}</span>
      <span class="ct">${c} ข้อ${cv?` · วิธีทำ ${cv}%`:""}</span><span class="cov"><i style="width:${cv}%"></i></span>`;
    // chem chapters with sub-topics: a wrapper (no nested buttons) holding the tile face and the stats face
    h+=!bio&&ST[k]?`<div class="${cls} st" data-ch="${k}" style="--i:${ii}"><button class="tface" data-go="ch" data-ch="${k}" aria-keyshortcuts="ArrowLeft ArrowRight">${face}</button>
      <div class="tback" role="region" aria-label="สถิติบท ${n}"></div></div>`
      :`<button class="${cls}" data-go="ch" data-ch="${k}" style="--i:${ii}">${face}</button>`;
  });
  if(!bio&&DATA.appcount){const qs=DATA.questions.filter(q=>q.subject==="applied"),cv=cov(qs);
    h+=`<button class="tile c-red" data-go="applied" style="--i:${i++}"><span class="no">✦</span><span class="nm">เคมีประยุกต์</span><span class="ct">${DATA.appcount} ข้อ</span><span class="cov"><i style="width:${cv}%"></i></span></button>`;}
  const fl=pool.filter(q=>hasSol(q)&&q.solFlag).length;
  if(fl) h+=`<button class="tile c-card" data-go="flag" style="--i:${i++}"><span class="no">⚠</span><span class="nm">วิธีทำไม่ฟันธง</span><span class="ct">${fl} ข้อ</span></button>`;
  return h;}
function buildBoard(){
  const rec=recentHtml();
  $("#board").classList.toggle("hasrec",!!rec);
  $("#board").innerHTML=rec+heroHtml()+subjTiles();packBoard();
  const si=SUBJS.indexOf(SUBJ);heroPlace($("#board .htrack"),si,(si+1)%SUBJS.length,1,0,false);
}
/* endless hero carousel: each panel carries its own offset -- the current one at 0 (+ drag px), the one
   we're heading to right beside it on that side, the rest hidden -- so the ring wraps for any N subjects
   (index mod N) and a wrap still slides the way you swiped instead of rewinding across the track */
function heroPlace(tr,cur,nb,side,px,anim){
  [...tr.children].forEach((p,k)=>{p.style.transition=anim?"":"none";
    p.style.transform=`translateX(calc(${k===cur?0:k===nb?side*100:0}% + ${px}px))`;
    p.style.visibility=k===cur||k===nb?"":"hidden";});}
/* switch subject from the landing: slide the hero, swap palette, rebuild only the subject tiles.
   d = travel direction (+1 = next comes in from the right); px = where a drag left the panels */
function goSubj(ti,d,px=0){
  const B=$("#board"),hero=B.querySelector(".hero"),tr=hero.querySelector(".htrack"),N=SUBJS.length,si=SUBJS.indexOf(SUBJ);
  ti=(ti%N+N)%N;d=d||(ti>si?1:-1);
  if(ti===si){heroPlace(tr,si,(si+d+N)%N,d,0,true);return;}   // same subject / short drag: snap back
  heroPlace(tr,si,ti,d,px,false);void tr.offsetWidth;          // line the target up on the side we're heading to...
  heroPlace(tr,ti,si,-d,0,true);setSubj(SUBJS[ti]);            // ...then slide both
  hero.querySelectorAll(".hdot").forEach((b,k)=>b.classList.toggle("on",k===ti));
  SFX.play(SUBJ,d);   // "chem" / "bio": each subject has its own timbre
  [...B.children].forEach(el=>{if(!el.matches(".hero,.recent"))el.remove();});
  B.insertAdjacentHTML("beforeend",subjTiles());packBoard();
}
/* swipe: only a drag that is clearly horizontal (>10px, more x than y) is taken over; a vertical one is
   left alone (touch-action:pan-y lets the browser scroll it), so page scrolling on phones is untouched */
let hdrag=null;
$("#board").addEventListener("pointerdown",e=>{const h=e.target.closest(".hero");
  if(!h||SUBJS.length<2||e.button>0||e.target.closest("button"))return;
  hdrag={x:e.clientX,y:e.clientY,id:e.pointerId,dx:0,on:false,h,tr:h.querySelector(".htrack")};});
$("#board").addEventListener("pointermove",e=>{const d=hdrag;if(!d||e.pointerId!==d.id)return;
  const dx=e.clientX-d.x,dy=e.clientY-d.y,si=SUBJS.indexOf(SUBJ);
  if(!d.on){if(Math.abs(dx)<10&&Math.abs(dy)<10)return;if(Math.abs(dy)>=Math.abs(dx)){hdrag=null;return;}
    d.on=true;try{d.h.setPointerCapture(e.pointerId);}catch(_){}}
  d.dx=dx;d.side=dx<0?1:-1;   // dragging left pulls the next subject in from the right, and vice versa
  heroPlace(d.tr,si,(si+d.side+SUBJS.length)%SUBJS.length,d.side,dx,false);});
function hdragEnd(e){const d=hdrag;if(!d||e.pointerId!==d.id)return;hdrag=null;if(!d.on)return;
  const si=SUBJS.indexOf(SUBJ),go=e.type==="pointerup"&&Math.abs(d.dx)>Math.max(40,d.h.offsetWidth*.18);
  goSubj(go?si+d.side:si,d.side,d.dx);}
$("#board").addEventListener("pointerup",hdragEnd);
$("#board").addEventListener("pointercancel",hdragEnd);
$("#board").addEventListener("keydown",e=>{if(!e.target.closest(".hero")||SUBJS.length<2)return;
  if(e.key==="ArrowLeft"||e.key==="ArrowRight"){e.preventDefault();const k=e.key==="ArrowRight"?1:-1;goSubj(SUBJS.indexOf(SUBJ)+k,k);}});
/* Place tiles in order (same rule as CSS sparse auto-placement) at explicit cells, then fill
   every cell left empty -- a wide tile that doesn't fit at a row end leaves one -- with a filler. */
let boardCols=0;
const boardN=()=>parseInt(getComputedStyle($("#board")).getPropertyValue("--cols"))||6;
function packBoard(){
  const B=$("#board");B.querySelectorAll(".tile.deco").forEach(x=>x.remove());
  const cols=boardN();boardCols=cols;
  const occ=[],used=(r,c)=>occ[r]&&occ[r][c];
  const fits=(r,c,w,h)=>{if(c+w>cols)return false;for(let y=r;y<r+h;y++)for(let x=c;x<c+w;x++)if(used(y,x))return false;return true;};
  let r=0,c=0;
  [...B.children].forEach(el=>{const cl=el.classList,op=cl.contains("open"),big=cl.contains("hero")||cl.contains("big")||op;
    const w=cl.contains("full")?cols:Math.min(cols,big||cl.contains("w2")?2:1),h=op?(+el.dataset.rows||2):big||cl.contains("h2")?2:1;   // an open stats tile: as many rows as its stats need
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
  const n=boardN(),o=$("#board .tile.st.open");
  if(n!==boardCols||(o&&statRows(o)!=o.dataset.rows))repack();});

/* ---- chapter stats: slide a chem chapter tile left or right (or ←/→ on it) -> it re-packs 2 columns wide and turns
   over to its sub-topic bars + difficulty split; slide either way / ←→ / ✕ / Esc turns it back. One open at a time; the paper
   chips are one global choice, remembered. A bar opens the app on that chapter + sub-topic + those papers. ---- */
// the 5th chip (แบบฝึกหัด) only decides whether a bar also opens the exercises: bars + difficulty always count exam papers (PX)
const EXPAPERS=[["posn","สอวน."],["pat2","PAT2"],["alevel","A-Level"],["samanya","9 วิชาสามัญ"]],PAPERS=EXPAPERS.concat(EXN?[["ex","✎ แบบฝึกหัด"]]:[]);
let PSEL=[];try{PSEL=JSON.parse(ls.get("cqb_papers","[]"));}catch(e){}
PSEL=PAPERS.map(p=>p[0]).filter(k=>Array.isArray(PSEL)&&PSEL.includes(k));if(!PSEL.some(k=>k!=="ex"))PSEL=PAPERS.map(p=>p[0]);
const PX=()=>PSEL.filter(k=>k!=="ex");
const EXC={};DATA.questions.forEach(q=>{if(isEx(q))EXC[q.ch]=(EXC[q.ch]||0)+1;});   // exercises per chapter
const examSel=()=>PSEL.length===PAPERS.length?"":PSEL.join("+");   // every paper on = no exam filter at all
const RM=matchMedia("(prefers-reduced-motion:reduce)");
function statBody(ch){
  const px=PX(),qs=DATA.questions.filter(q=>subjOf(q)==="chem"&&q.ch===ch&&px.includes(q.exam)),cnt={},df={easy:0,medium:0,hard:0};
  qs.forEach(q=>{q.topics.forEach(t=>cnt[t]=(cnt[t]||0)+1);if(q.diff in df)df[q.diff]++;});   // bars count every tag (can sum > qs.length); header + difficulty stay distinct
  const tops=ST[ch].map(t=>[t.id,t.th,cnt[t.id]||0]).sort((a,b)=>b[2]-a[2]),max=Math.max(1,tops[0][2]),n=parseInt(ch);
  return `<div class="sth"><span class="sn">${n}</span><span class="snm">${DATA.chapters[ch]}<small>${qs.length} ข้อ${px.length<EXPAPERS.length?" · "+px.map(k=>PAPERS.find(p=>p[0]===k)[1]).join(" + "):""}</small></span>
    <button class="tbx" title="กลับ (Esc)" aria-label="ปิดสถิติบท ${n}">✕</button></div>
  <div class="sbody"><div class="pchips" role="group" aria-label="สนามสอบ">${PAPERS.map(([k,l])=>{const on=PSEL.includes(k);
      return `<button class="pchip${on?" on":""}" data-p="${k}" aria-pressed="${on}">${l}</button>`;}).join("")}</div>
    <div class="scap">หัวข้อย่อย · แตะเพื่อดูข้อ</div>
    <div class="sbars">${tops.map(([id,th,c],k)=>`<button class="sbar" data-go="topic" data-ch="${ch}" data-t="${id}" data-k="${k}" style="--w:${c/max*100}%;--k:${k}"${c?"":" disabled"} title="${th} · ${c} ข้อ"><span class="sl">${th}</span><b>${c}</b></button>`).join("")}</div>
    <div class="sdw"><div class="scap">ความยาก</div>${qs.length?`<div class="sdiff">${["easy","medium","hard"].filter(d=>df[d]).map(d=>`<i class="sd-${d}" style="flex:${df[d]}" title="${DIFF_TH[d]} ${df[d]} ข้อ">${df[d]}</i>`).join("")}</div>
      <div class="sleg">${["easy","medium","hard"].map(d=>`<span class="diff-txt de-${d}">${DIFF_TH[d]}</span>`).join("")}</div>`:`<div class="snone">ไม่มีข้อจากสนามที่เลือกในบทนี้</div>`}</div>
    ${EXC[ch]?`<button class="sexb" data-go="exch" data-ch="${ch}">✎ +${EXC[ch]} แบบฝึกหัด</button>`:""}</div>`;}
// rows the open tile needs at its current width: the stats face's natural height over one grid row (+ gap)
function statRows(t){const b=t.querySelector(".tback"),cs=getComputedStyle($("#board")),rh=parseFloat(cs.gridAutoRows)||150,g=parseFloat(cs.rowGap)||6;
  b.style.minHeight="0";const h=b.offsetHeight;b.style.minHeight="";return Math.max(2,Math.ceil((h+g)/(rh+g)));}
function repack(){packBoard();const o=$("#board .tile.st.open");if(o){const r=statRows(o);if(r!=o.dataset.rows){o.dataset.rows=r;packBoard();}}}
let stBusy=false;
/* open/close with a card turn: the face being left folds edge-on (phase 1), then the board re-packs and every
   tile FLIP-slides from where it was; the turned tile unfolds from its old spot + size. WAAPI, because the
   tiles' tileIn fill would override an inline transform. tx = where a drag left the tile; dir = which way it
   turns (-1 left, 1 right; default: open turns left, close turns right). */
function statSet(t,open,tx=0,dir=open?-1:1){
  if(!t||stBusy||t.classList.contains("open")===open)return;
  const B=$("#board"),prev=open?B.querySelector(".tile.st.open"):null,turn=[t,prev].filter(Boolean);stBusy=true;
  SFX.play(open?"statOpen":"statClose");
  const go=()=>{
    const kids=[...B.children].filter(el=>!el.classList.contains("deco")),F=new Map(kids.map(el=>[el,el.getBoundingClientRect()]));
    if(prev)prev.classList.remove("open");
    t.classList.toggle("open",open);
    if(open)t.querySelector(".tback").innerHTML=statBody(t.dataset.ch);
    repack();B.querySelectorAll(".tile.deco").forEach(d=>d.style.animationDelay=".12s");
    if(!RM.matches)kids.forEach(el=>{const a=F.get(el),b=el.getBoundingClientRect(),E={duration:440,easing:"cubic-bezier(.2,.9,.3,1)"};
      if(turn.includes(el)){const dx=a.left+a.width/2-b.left-b.width/2,dy=a.top+a.height/2-b.top-b.height/2;
        el.animate([{transform:`perspective(1200px) translate(${dx}px,${dy}px) scale(${a.width/b.width},${a.height/b.height}) rotateY(${el===t?-dir*90:-90}deg)`},
          {transform:"perspective(1200px)"}],E);}
      else if(Math.abs(a.left-b.left)+Math.abs(a.top-b.top)>.5)el.animate([{transform:`translate(${a.left-b.left}px,${a.top-b.top}px)`},{transform:"none"}],E);});
    const f=t.querySelector(open?".tbx":".tface");if(open||t.contains(document.activeElement)||document.activeElement===document.body)f.focus({preventScroll:true});
    setTimeout(()=>{stBusy=false;if(open){const r=t.getBoundingClientRect();if(r.bottom>innerHeight||r.top<0)t.scrollIntoView({block:"nearest",behavior:RM.matches?"auto":"smooth"});}},RM.matches?0:460);};
  if(RM.matches)return go();
  // phase 1: fold what's showing edge-on the way it was slid (then phase 2 unfolds it from the other edge)
  const fold=turn.map(el=>el.animate([{transform:`perspective(1200px) translateX(${el===t?tx:0}px)`},
      {transform:`perspective(1200px) translateX(${el===t?tx:0}px) rotateY(${el===t?dir*90:90}deg)`}],{duration:150,easing:"ease-in",fill:"forwards"}));
  Promise.all(fold.map(a=>a.finished)).then(()=>{go();fold.forEach(a=>a.cancel());},()=>{stBusy=false;});   // phase 2 is already running when the fold lets go
}
function chipToggle(b){const k=b.dataset.p,on=PSEL.includes(k),t=b.closest(".tile");
  if(on&&k!=="ex"&&PX().length===1){SFX.play("bad");return;}   // never zero exam papers: the last one stays on
  PSEL=PAPERS.map(p=>p[0]).filter(x=>x===k?!on:PSEL.includes(x));ls.set("cqb_papers",JSON.stringify(PSEL));SFX.play("chip",!on);
  t.querySelector(".tback").innerHTML=statBody(t.dataset.ch);t.querySelector(`.pchip[data-p="${k}"]`).focus({preventScroll:true});}
// slide: a clearly horizontal drag (>10px, more x than y) is taken over, a vertical one scrolls the page as usual
// (touch-action:pan-y); released 30px+ either way it turns the tile that way. The click a mouse drag ends with is eaten.
let sdrag=null,sEat=0;
$("#board").addEventListener("pointerdown",e=>{const t=e.target.closest(".tile.st");if(!t||e.button>0||stBusy)return;
  sdrag={x:e.clientX,y:e.clientY,id:e.pointerId,t,on:false,dx:0};});
$("#board").addEventListener("pointermove",e=>{const d=sdrag;if(!d||e.pointerId!==d.id)return;const dx=e.clientX-d.x,dy=e.clientY-d.y;
  if(!d.on){if(Math.abs(dx)<10&&Math.abs(dy)<10)return;if(Math.abs(dy)>=Math.abs(dx)){sdrag=null;return;}
    d.on=true;try{d.t.setPointerCapture(e.pointerId);}catch(_){}}
  d.dx=dx;d.t.style.translate=`${Math.round(dx*.35)}px 0`;});
function sdragEnd(e){const d=sdrag;if(!d||e.pointerId!==d.id)return;sdrag=null;if(!d.on)return;sEat=Date.now()+350;
  const open=d.t.classList.contains("open"),tx=parseFloat(d.t.style.translate)||0;d.t.style.translate="";
  if(e.type==="pointerup"&&Math.abs(d.dx)>=30)statSet(d.t,!open,tx,Math.sign(d.dx));
  else if(tx)d.t.animate([{translate:`${tx}px 0`},{translate:"0 0"}],{duration:220,easing:"cubic-bezier(.2,.9,.3,1)"});}
$("#board").addEventListener("pointerup",sdragEnd);
$("#board").addEventListener("pointercancel",sdragEnd);
$("#board").addEventListener("click",e=>{if(Date.now()<sEat){e.stopPropagation();e.preventDefault();}},true);
// keyboard: ←/→ on a focused tile face turns it that way; inside an open stats tile they turn it back
$("#board").addEventListener("keydown",e=>{const t=e.target.closest(".tile.st");if(!t||(e.key!=="ArrowLeft"&&e.key!=="ArrowRight"))return;
  const open=t.classList.contains("open");if(!open&&!e.target.classList.contains("tface"))return;
  e.preventDefault();statSet(t,!open,0,e.key==="ArrowLeft"?-1:1);});
if(Object.keys(ST).length)$(".lfoot").insertAdjacentHTML("beforeend",`<span class="lfst"> · ปัดบล็อกบทไปซ้ายหรือขวา (หรือกด ← → ที่บล็อก) เพื่อดูสถิติหัวข้อย่อย</span>`);
/* ---- search straight from the board: text / formula / Q-id ("38" or "q38" -> Q-0038) ---- */
function lsNorm(v){v=v.trim();const m=v.match(/^(?:q-?)?0*(\d{1,4})$/i);
  if(m){const id="Q-"+m[1].padStart(4,"0");if(DATA.questions.some(x=>x.id===id))return id;}return v;}
function lsCount(v){const t=v.trim().toLowerCase();if(!t)return -1;return DATA.questions.filter(x=>x.search.includes(t)||x.id.toLowerCase().includes(t)).length;}
function lsGo(){
  const v=lsNorm($("#lq").value),n=lsCount(v),box=$("#lsearch");if(n<0)return;
  if(!n){SFX.play("empty");box.classList.remove("shake");void box.offsetWidth;box.classList.add("shake");return;}
  const r=box.getBoundingClientRect();SFX.play("search");setTimeout(()=>SFX.play("whoosh"),70);
  enterApp(r.left+r.width/2,r.top+r.height/2,()=>{resetFilters();$("#q").value=v;apply();});
  $("#lq").value="";$("#lct").textContent="";$("#lq").blur();}
$("#lq").addEventListener("input",()=>{const v=lsNorm($("#lq").value),n=lsCount(v);$("#lct").textContent=n<0?"":v!==$("#lq").value.trim()?v:`${n} ข้อ`;});
$("#lq").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();lsGo();}});
$("#lgo").onclick=lsGo;
// ...then re-list every option: syncFacets drops options that had 0 hits under the LAST filter, so
// without this a tile could set #fsubj="bio" on a select that no longer has a "bio" option
function resetFilters(){$("#q").value="";$("#fsubj").value="";populateChapters("");["#ftopic","#fexam","#fyear","#fdiff","#ftype","#fsol"].forEach(s=>$(s).value="");syncFacets(fstate());}
function enterApp(x,y,fn){
  const app=$("#app");app.style.setProperty("--x",x+"px");app.style.setProperty("--y",y+"px");
  fn();document.body.classList.add("inapp");app.classList.add("show","opening");window.scrollTo(0,0);
  setTimeout(()=>app.classList.remove("opening"),700);
}
$("#board").addEventListener("click",e=>{
  const hb=e.target.closest(".hnav button");
  if(hb){const k=+hb.dataset.d||0;goSubj(hb.dataset.s!=null?+hb.dataset.s:SUBJS.indexOf(SUBJ)+k,k);return;}
  const sb=e.target.closest(".tbx");if(sb){statSet(sb.closest(".tile"),false);return;}
  const pc=e.target.closest(".pchip");if(pc){chipToggle(pc);return;}
  const tb=e.target.closest("button.b-st");if(tb){const r=tb.getBoundingClientRect();SFX.play("bar",0);setTimeout(()=>SFX.play("whoosh"),70);   // sub-topic badge on the recent block
    enterApp(r.left+r.width/2,r.top+r.height/2,()=>{resetFilters();topicFilters(tb.dataset.ch,tb.dataset.st);apply();});return;}
  const t=e.target.closest("[data-go]");if(!t||t.disabled)return;
  const r=t.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2,g=t.dataset.go;
  SFX.play(g==="topic"?"bar":g==="ex"||g==="exch"?"exOpen":"tile",+t.dataset.k);setTimeout(()=>SFX.play("whoosh"),70);
  enterApp(x,y,()=>{
    resetFilters();
    if(g==="qid"){$("#q").value=t.dataset.q;}
    else{const s=g==="applied"?"applied":SUBJ;$("#fsubj").value=s;populateChapters(s);   // every other tile is scoped to the subject
      if(EXN&&s==="chem"&&g!=="topic"){const ex=g==="ex"||g==="exch"?"ex":EXONLY;opt($("#fexam"),ex,ex);$("#fexam").value=ex;}   // ✎ tiles: exercises only; the rest: exams only
      if(g==="ch"||g==="exch")$("#fch").value=t.dataset.ch;
      else if(g==="flag")$("#fsol").value=g;
      else if(g==="topic"){$("#fch").value=t.dataset.ch;const ex=examSel();   // a stats bar: chapter + sub-topic + the chosen papers
        if(ex){opt($("#fexam"),ex,ex);$("#fexam").value=ex;}
        syncFacets(fstate());$("#ftopic").value=t.dataset.t;}}
    apply();
    if(g==="random"&&filtered.length){setTimeout(()=>SFX.play("dice"),250);setTimeout(()=>openModal(Math.floor(Math.random()*filtered.length)),650);}
  });
});
$("#home").onclick=()=>{SFX.play("home");dwell(null);document.body.classList.remove("inapp");$("#app").classList.remove("show");window.scrollTo(0,0);buildBoard();};
buildBoard();
</script></body></html>"""

open(OUT,"w",encoding="utf-8").write(HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False)))
print("wrote", OUT, "-", len(questions), "questions -", len(examcount), "exam type(s)")
