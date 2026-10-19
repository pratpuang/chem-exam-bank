"""--student mode helpers for build_viewer.py: turn the finished viewer HTML into ONE offline file.
Third-party assets (KaTeX, three.js, html2canvas, Google fonts) are fetched once into tools/vendor/ (gitignored)
and then embedded as data URIs / inline scripts, so the result opens from file:// with no network."""
import base64, os, re, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VEN = os.path.join(HERE, "vendor")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/"
GFONTS = ("https://fonts.googleapis.com/css2?family=Anuphan:wght@400;500;600;700;800&family=Sarabun:wght@400;600;700"
          "&family=JetBrains+Mono:wght@500;700&display=swap")
KEEP_SUBSETS = ("thai", "latin")   # latin-ext / vietnamese would only add weight; glyphs outside fall back to system fonts

def _get(url, name=None):
    p = os.path.join(VEN, name or os.path.basename(url.split("?")[0]))
    if not os.path.isfile(p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
            open(p, "wb").write(r.read())
    return open(p, "rb").read()

def _b64(b, mime): return "data:%s;base64,%s" % (mime, base64.b64encode(b).decode())
def js_safe(s): return s.replace("</script", "<\/script").replace("<!--", "<\!--")

def katex_css():
    css = _get(KATEX + "katex.min.css", "katex.css").decode()
    # keep woff2 only (every browser that runs this page reads it), embed it
    def font(m):
        return "url(%s)" % _b64(_get(KATEX + "fonts/" + m.group(1) + ".woff2", "katex-fonts/" + m.group(1) + ".woff2"), "font/woff2")
    css = re.sub(r"url\(fonts/([^)]+?)\.woff2\)\s*format\(\"woff2\"\)\s*,\s*url\(fonts/[^)]+?\.woff\)\s*format\(\"woff\"\)\s*,\s*url\(fonts/[^)]+?\.ttf\)\s*format\(\"truetype\"\)",
                 lambda m: font(m) + ' format("woff2")', css)
    assert "fonts/" not in css, "katex css still has relative font urls"
    return css

def google_css(url=GFONTS, name="gfonts.css"):
    css = _get(url, name).decode()
    out = []
    for sub, block in re.findall(r"/\* ([\w-]+) \*/\s*(@font-face\s*\{.*?\})", css, re.S):
        if sub not in KEEP_SUBSETS: continue
        u = re.search(r"url\((https://[^)]+)\)", block).group(1)
        out.append(block.replace(u, _b64(_get(u, "gfonts/" + re.sub(r"\W", "_", u[-60:])), "font/woff2")))
    assert out and "https://" not in "".join(out)
    return "\n".join(out)

def inline_images(text, root):
    """every images/<file> reference -> data URI (cached per file)"""
    seen = {}
    def sub(m):
        f = m.group(0)
        if f not in seen:
            ext = f.rsplit(".", 1)[1].lower()
            mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "svg": "image/svg+xml", "webp": "image/webp"}[ext]
            seen[f] = _b64(open(os.path.join(root, f), "rb").read(), mime)
        return seen[f]
    return re.sub(r"images/[A-Za-z0-9_\-.]+\.(?:png|jpe?g|gif|svg|webp)", sub, text), len(seen)

# ---------- the viewer HTML -> student edition ----------
def _cut(s, a, b, keep_b=True):
    i = s.index(a); j = s.index(b, i)
    return s[:i] + (s[j:] if keep_b else s[j + len(b):])

def _sub1(s, old, new):
    assert s.count(old) == 1, ("expected exactly one", old[:60], s.count(old))
    return s.replace(old, new)

HELP_CSS = """
#help{position:fixed;inset:0;z-index:2000;display:none;align-items:center;justify-content:center;padding:18px;background:rgba(20,20,20,.72)}
#help.on{display:flex}
#help .hsheet{background:var(--card);color:var(--ink);border:3px solid var(--ink);box-shadow:8px 8px 0 var(--sh);max-width:560px;width:100%;max-height:88vh;overflow:auto;position:relative}
#help h2{margin:0;padding:14px 52px 12px 18px;background:var(--yel);color:#141414;border-bottom:3px solid var(--ink);font:800 1.15rem "Anuphan",sans-serif}
#help .hx{position:absolute;top:8px;right:8px;width:34px;height:34px;border:3px solid var(--ink);background:var(--card);color:var(--ink);font-weight:800}
#help ul{margin:0;padding:14px 18px 6px 36px;line-height:1.65;font-size:.95rem}
#help li{margin:0 0 7px}
#help li b{background:var(--stbg);padding:0 4px}
#help .hwarn{margin:8px 18px 18px;padding:10px 12px;border:3px solid var(--ink);background:var(--sxbg);font-size:.9rem;line-height:1.6}
.hbtn.hq,.lbtn.hq{font-weight:800}
#hint{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:1500;display:none;align-items:center;gap:10px;max-width:calc(100vw - 24px);
  background:var(--yel);color:#141414;border:3px solid var(--ink);box-shadow:4px 4px 0 var(--sh);padding:8px 8px 8px 14px;font:700 .88rem/1.4 "Anuphan",sans-serif}
#hint.on{display:flex}
#hint button{border:2px solid var(--ink);background:var(--card);color:var(--ink);font-weight:800;width:28px;height:28px;flex:none}
"""
HELP_HTML = """<div id="hint" role="status">ครั้งแรกใช่ไหม? กดปุ่ม ⓘ ที่แถบด้านบน ดูวิธีใช้ได้นะ<button id="hintx" title="ปิด" aria-label="ปิด">✕</button></div>
<div id="help" role="dialog" aria-modal="true" aria-label="วิธีใช้"><div class="hsheet">
<button class="hx" id="helpx" title="ปิด (Esc)">✕</button><h2>ⓘ วิธีใช้</h2>
<ul>
<li><b>เลือกบท</b> แตะบล็อกบทที่อยากฝึกในหน้าแรก หรือพิมพ์ค้นหา (สูตร / คำ / รหัสข้อ) ที่ช่องค้นหา</li>
<li><b>กรอง</b> กด “ตัวกรอง ▾” ที่แถบบน แล้วเลือก บท · สนามสอบ · ปี · ความยาก (ง่าย/กลาง/ยาก) · ชนิดข้อ · มี/ไม่มีเฉลย ได้พร้อมกัน</li>
<li><b>🎲 สุ่ม</b> สุ่มโจทย์ข้อหนึ่งจากสิ่งที่กรองอยู่</li>
<li><b>ทำโจทย์</b> แตะข้อไหนก็ได้เพื่อเปิดเต็มจอ ปัดซ้าย/ขวา (หรือกดปุ่ม ← →) เพื่อเปลี่ยนข้อ</li>
<li><b>เฉลย</b> กดปุ่ม “เฉลย” ใต้โจทย์เพื่อดูคำตอบและวิธีทำ (ลองทำเองก่อนนะ)</li>
<li><b>โหมดเขียน ✎</b> ปุ่มดินสอมุมขวาบนของโจทย์ ใช้เขียนทดบนโจทย์ได้ มีปากกา 3 สี ไฮไลต์ ยางลบ ย้อนกลับ และปุ่ม ▦ แบ่งจอเป็นกระดาษทด</li>
<li><b>โหมดแสดงเต็มจอ</b> ปุ่ม “⤢ ขยายเต็มจอ” ที่ท้ายแต่ละข้อ ใช้อ่านโจทย์ใหญ่ ๆ</li>
<li><b>ตารางธาตุ</b> แท็บ “ตารางธาตุ” ทางซ้ายของจอ เปิดตารางธาตุและช่องคำนวณมวลโมเลกุล (พิมพ์สูตรได้) ข้าง ๆ ก็มี เครื่องมือ (ค่าคงที่ · แปลงหน่วย · สูตร) จับเวลา และโมเลกุล 3 มิติ</li>
<li><b>🌙</b> โหมดกลางคืน · <b>🔊</b> เสียงเอฟเฟกต์ปรับหรือปิดได้</li>
</ul>
<div class="hwarn">⚠️ เฉลยและวิธีทำเขียนโดย AI อาจมีผิดพลาดได้ เฉลยบางข้อยังไม่ได้ตรวจ ถ้าข้อไหนแปลกๆ ถามพี่ได้</div>
</div></div>"""
HELP_JS = """
(()=>{const h=document.getElementById("hint"),K="cqb_student_hint";let seen=false;
  try{seen=!!localStorage.getItem(K);}catch(_){}
  window.hintOff=()=>{h.classList.remove("on");try{localStorage.setItem(K,"1");}catch(_){}};
  document.getElementById("hintx").addEventListener("click",hintOff);
  if(!seen)h.classList.add("on");})();
(()=>{const h=document.getElementById("help"),open=()=>{h.classList.add("on");hintOff();},close=()=>h.classList.remove("on");
  for(const id of ["helpbtn","lhelp"])document.getElementById(id).addEventListener("click",open);
  document.getElementById("helpx").addEventListener("click",close);
  h.addEventListener("click",e=>{if(e.target===h)close();});
  addEventListener("keydown",e=>{if(e.key==="Escape"&&h.classList.contains("on")){close();e.stopPropagation();}},true);})();
"""

def student_html(HTML, root, web=False):
    """HTML = the viewer template (still containing __DATA__). Returns the template with every network / teacher-only piece
    removed or inlined; the caller fills __DATA__ and runs inline_images on the result."""
    # --- head: CDN tags -> inline assets
    if web:   # online page: same CDN tags / images/ / vsepr.html as index.html, minus the PWA manifest
        HTML = _sub1(HTML, '<link rel="manifest" href="manifest.webmanifest">', '')
        HTML = _sub1(HTML, '<style>\n', '<style>' + HELP_CSS + '\n')
    else:
        head_old = HTML[HTML.index('<link rel="icon" href="icons/icon.svg"'):HTML.index("<style>")]
        icon = _b64(open(os.path.join(root, "icons", "icon.svg"), "rb").read(), "image/svg+xml")
        head_new = ('<link rel="icon" href="%s" type="image/svg+xml">\n<meta name="theme-color" content="#141414">\n<style>%s\n%s\n%s</style>\n'
                    '<script>%s</script>\n<script>%s</script>\n') % (
            icon, katex_css(), google_css(), HELP_CSS,
            js_safe(_get(KATEX + "katex.min.js", "katex.js").decode()), js_safe(_get(KATEX + "contrib/auto-render.min.js", "auto-render.js").decode()))
        HTML = HTML.replace(head_old, head_new)
    # --- teacher hand-off: CSS, markup, JS (whole blocks, not hidden)
    HTML = _cut(HTML, "/* slide the subject card up -> the teaching page (teach.html).", "/* circle reveal between landing and app */")
    HTML = _cut(HTML, "/* ---------- slide the subject card up -> teaching page", "</script></body>")
    HTML = re.sub(r'<div class="tup">.*?</div>(?=<div class="htrack">)', "", HTML)
    assert 'class="tup"' not in HTML
    if not web:
        # --- VSEPR drawer: vsepr.html inlined as srcdoc (it needs three.js + fonts)
        vs = open(os.path.join(root, "vsepr.html"), encoding="utf-8").read()
        vs = re.sub(r'<link href="https://fonts\.googleapis[^>]*>', lambda m: "<style>%s</style>" % google_css(
            "https://fonts.googleapis.com/css2?family=Anuphan:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700;800&display=swap", "gfonts-vsepr.css"), vs)
        vs = re.sub(r'<script src="https://cdn\.jsdelivr\.net/npm/three@[^"]*"></script>',
                    lambda m: "<script>%s</script>" % js_safe(_get("https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js", "three.js").decode()), vs)
        vs = _sub1(vs, 'QS.get("embed")', '"1"')
        assert "https://" not in re.sub(r"<script>.*?</script>", "", vs, flags=re.S).replace("http://www.w3.org", "")
        import json
        HTML = _sub1(HTML, "const DATA = __DATA__;", "const VSEPR_HTML=%s;\nconst DATA = __DATA__;" % js_safe(json.dumps(vs, ensure_ascii=False)))
        HTML = _sub1(HTML, 'if(!f.src)f.src="vsepr.html?embed=1";', 'if(!f.srcdoc)f.srcdoc=VSEPR_HTML;')
        # --- save-as-picture: html2canvas embedded instead of fetched
        h2c = _b64(_get("https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js", "html2canvas.js"), "text/javascript")
        HTML = _sub1(HTML, 'sc.src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js";', 'sc.src="%s";' % h2c)
    # --- wording for the student
    HTML = HTML.replace("แสดงให้นักเรียน", "ขยายเต็มจอ")
    HTML = HTML.replace("night mode + teaching (screen-share) mode", "night mode + screen-share mode")
    # --- ⓘ help: app bar + landing, panel at the end
    HTML = _sub1(HTML, '<button class="hbtn" id="ftoggle">ตัวกรอง ▾</button>', '<button class="hbtn" id="ftoggle">ตัวกรอง ▾</button>\n   <button class="hbtn hq" id="helpbtn" title="วิธีใช้" aria-label="วิธีใช้">ⓘ</button>')
    HTML = _sub1(HTML, '<button class="lbtn" id="ldark"', '<button class="lbtn hq" id="lhelp" title="วิธีใช้" aria-label="วิธีใช้">ⓘ</button>\n    <button class="lbtn" id="ldark"')
    HTML = _sub1(HTML, '<div id="pdscrim"></div>', HELP_HTML + '<div id="pdscrim"></div>')
    HTML = HTML.replace("</script></body>", HELP_JS + "</script></body>")
    return HTML
