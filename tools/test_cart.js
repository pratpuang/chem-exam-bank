// 🛒 cart test (tools/cart_part.py). Run after build_viewer.py:  node tools/test_cart.js [outdir]
// Drives real headless Chrome over CDP: real mouse/touch input (hit-tested), the cart panel, print-to-PDF of the sheet, the student link.
const { spawn } = require("child_process"), fs = require("fs"), path = require("path"), os = require("os");
const CH = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const ROOT = path.join(__dirname, ".."), URL0 = "file:///" + path.join(ROOT, "index.html").replace(/\\/g, "/");
const OUT = process.argv[2] || os.tmpdir();
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ok = 0, bad = 0; const check = (n, c, x) => { if (c) { ok++; console.log("  ✓", n); } else { bad++; console.log("  ✗", n, x === undefined ? "" : JSON.stringify(x)); } };
(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), "cart-"));
  const ch = spawn(CH, ["--headless=new", "--mute-audio", "--remote-debugging-port=9333", "--user-data-dir=" + prof, "--window-size=1100,1400", "about:blank"]);
  let ws; for (let i = 0; i < 40; i++) { try { const l = await (await fetch("http://127.0.0.1:9333/json")).json(); const p = l.find(x => x.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch (_) {} await sleep(250); }
  await new Promise(r => ws.onopen = r); let id = 0; const pend = {};
  ws.onmessage = m => { const d = JSON.parse(m.data); if (d.id && pend[d.id]) { pend[d.id](d); delete pend[d.id]; } };
  const cdp = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async e => { const r = await cdp("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true }); if (r.result.exceptionDetails) console.log("JS ERR", r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text); return r.result.result?.value; };
  const errs = []; await cdp("Runtime.enable"); ws.addEventListener("message", m => { const d = JSON.parse(m.data); if (d.method === "Runtime.exceptionThrown") errs.push(d.params.exceptionDetails.exception?.description?.slice(0, 200)); });
  await cdp("Page.enable");
  const go = async u => { await cdp("Page.navigate", { url: u }); await sleep(600); if (u === "about:blank") return;
    for (let i = 0; i < 60; i++) { if (await ev(`typeof CART!=="undefined"&&document.readyState==="complete"`)) break; await sleep(500); } await sleep(1200); };
  // real tap/click at an element's centre, after proving it is the top element there
  const center = async sel => ev(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});if(!e)return null;e.scrollIntoView({block:"center"});const r=e.getBoundingClientRect();const x=r.left+r.width/2,y=r.top+Math.min(r.height/2,120);const t=document.elementFromPoint(x,y);return {x,y,hit:!!t&&(t===e||e.contains(t))};})()`);
  const click = async sel => { const c = await center(sel); if (!c || !c.hit) return c; for (const type of ["mousePressed", "mouseReleased"]) await cdp("Input.dispatchMouseEvent", { type, x: c.x, y: c.y, button: "left", clickCount: 1 }); await sleep(300); return c; };
  const swipe = async (sel, dx) => { const c = await center(sel); if (!c || !c.hit) return c; const pts = (x) => [{ x, y: c.y }];
    await cdp("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: pts(c.x) });
    for (let k = 1; k <= 8; k++) { await cdp("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: pts(c.x + dx * k / 8) }); await sleep(16); }
    await cdp("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); await sleep(450); return c; };
  const n = () => ev(`JSON.parse(localStorage.getItem("cqb_cart")||'{"ids":[]}').ids`);

  console.log("1 · add from the question list");
  await go(URL0); console.log("  page:", await ev(`location.href+" "+typeof $`)); await ev(`localStorage.clear();localStorage.setItem("cqb_sfx","0")`); await go("about:blank"); await go(URL0 + "#ch=07"); await sleep(2500); console.log("  in app:", await ev(`document.body.classList.contains("inapp")+" view="+view+" n="+filtered.length`));
  await ev(`document.querySelectorAll("*").forEach(e=>{e.style.transition="none";e.style.animation="none"})`);
  check("🛒 buttons on the questions", (await ev(`document.querySelectorAll(".cartadd").length`)) > 0);
  check("FAB hidden while empty", await ev(`$("#cartfab").hidden`));
  const c1 = await click(".cartadd"); check("tap 🛒 hit-tests", c1 && c1.hit, c1);
  let ids = await n(); check("tap adds 1", ids.length === 1, ids);
  check("FAB shows 1", await ev(`!$("#cartfab").hidden&&$("#cartn").textContent==="1"`));
  check("question marked incart", await ev(`!!document.querySelector(".incart")`));
  // switch to cards view for a finger swipe on a 2nd question
  await ev(`document.querySelector('#layout [data-v="cards"]').click()`); await sleep(600);
  await ev(`document.querySelectorAll("*").forEach(e=>{e.style.transition="none";e.style.animation="none"})`);
  await ev(`window.scrollTo(0,0)`); const target = await ev(`(()=>{const c=[...document.querySelectorAll(".card")].find(c=>!c.classList.contains("incart"));c.id="swipeme";return c.dataset.i})()`);
  await cdp("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  const s1 = await swipe("#swipeme .body", 180); check("finger swipe hit-tests", s1 && s1.hit, s1);
  ids = await n(); check("sideways swipe adds (2)", ids.length === 2, ids);
  await swipe("#swipeme .body", -180); ids = await n(); check("swiping a carted Q again doesn't duplicate", ids.length === 2, ids);
  check("toast says already in cart", (await ev(`$("#ctoast").textContent`)).includes("อยู่ในตะกร้าแล้ว"));
  await swipe("#swipeme .body", 30); ids = await n(); check("short drag does nothing", ids.length === 2, ids);
  await cdp("Emulation.setTouchEmulationEnabled", { enabled: false });

  console.log("2 · cart panel");
  await click("#cartfab"); check("panel opens", await ev(`$("#cartwrap").classList.contains("show")`));
  check("panel lists 2", (await ev(`document.querySelectorAll(".cpi").length`)) === 2);
  await ev(`(()=>{const L=JSON.parse(localStorage.getItem("cqb_cart"));})()`);
  await click("#cpsort"); const ord = await ev(`JSON.parse(localStorage.getItem("cqb_cart")).ids.map(id=>DATA.questions.find(q=>q.id===id).diff)`);
  const rank = { easy: 0, medium: 1, hard: 2 }; check("sort easy→hard", ord.every((d, i) => !i || rank[ord[i - 1]] <= rank[d]), ord);
  await click('#cpws [data-v="38"]');
  await ev(`(()=>{const i=$("#cptitle");i.value="ทดสอบตะกร้า";i.dispatchEvent(new Event("input"))})()`);

  console.log("3 · print sheet");
  await ev(`window.print=()=>{window.__printed=(window.__printed||0)+1}`);
  await click("#cpprint"); await sleep(1500);
  check("print called", (await ev(`window.__printed`)) === 1);
  const sh = await ev(`({cards:document.querySelectorAll("#psheet .ps-c").length,ok:document.querySelectorAll("#psheet .okopt").length,h1:$("#psheet h1").textContent,sc:$("#psheet .ps-sc").textContent,chips:document.querySelectorAll("#psheet .ps-paper").length+document.querySelectorAll("#psheet .ps-ch").length,ws:document.querySelectorAll("#psheet .ps-w").length,printing:document.body.classList.contains("printing")})`);
  check("sheet has 2 questions", sh.cards === 2, sh); check("no answer marks in the sheet", sh.ok === 0, sh);
  check("title used", sh.h1 === "ทดสอบตะกร้า", sh); check("score box carries the count", sh.sc.includes("2 ข้อ"), sh);
  check("paper + chapter chips", sh.chips === 4, sh); check("workspace boxes", sh.ws === 2, sh);
  await cdp("Emulation.setEmulatedMedia", { media: "print" });
  const pdf = await cdp("Page.printToPDF", { preferCSSPageSize: true, printBackground: true, displayHeaderFooter: false });
  const pdfPath = path.join(OUT, "cart-test-print.pdf"); fs.writeFileSync(pdfPath, Buffer.from(pdf.result.data, "base64")); console.log("  → " + pdfPath);
  await cdp("Emulation.setEmulatedMedia", { media: "" });
  await ev(`dispatchEvent(new Event("afterprint"))`);
  check("after print: keep-it nudge", await ev(`$("#cpkeep").classList.contains("nudge")`));

  console.log("4 · keep: set + given + remove");
  await ev(`(()=>{const i=$("#cpname");i.value="ไคด้า";})()`); await click("#cpsave"); await click("#cpgive");
  check("set saved", (await ev(`JSON.parse(localStorage.getItem("cqb_sets")||"[]").length`)) === 1);
  check("given recorded", (await ev(`(JSON.parse(localStorage.getItem("cqb_given")||"{}")["ไคด้า"]||[]).length`)) === 2);
  check("list shows ให้ ไคด้า แล้ว", (await ev(`document.querySelectorAll(".cpg").length`)) === 2);
  await cdp("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  await swipe(".cpi .cps", 160); await sleep(300); ids = await n(); check("swipe an item out of the cart", ids.length === 1, ids);
  await cdp("Emulation.setTouchEmulationEnabled", { enabled: false });
  const gone = ids.length === 1 ? (await ev(`JSON.parse(localStorage.getItem("cqb_given"))["ไคด้า"].find(x=>!JSON.parse(localStorage.getItem("cqb_cart")).ids.includes(x))`)) : null;
  await click("#cpx"); check("panel closes", !(await ev(`$("#cartwrap").classList.contains("show")`)));
  if (gone) { await ev(`window.__e=document.querySelector('.cartadd[data-id="${gone}"]')`); const has = await ev(`!!window.__e`);
    if (has) { await click(`.cartadd[data-id="${gone}"]`); check("re-adding a given Q warns", (await ev(`$("#ctoast").textContent`)).includes("ไคด้า")); } }
  await click("#cartfab"); await click('#cpsets [data-open="0"]'); check("open saved set restores 2", (await n()).length === 2);

  console.log("5 · student link");
  const link = await ev(`location.origin+location.pathname+"#sheet="+JSON.parse(localStorage.getItem("cqb_cart")).ids.map(encodeURIComponent).join(",")+"&t="+encodeURIComponent("ชุดนักเรียน")`);
  await go("about:blank"); await go(link.replace("file:///", "file:///")); await sleep(1500);
  const sv = await ev(`({on:document.body.classList.contains("sheetview"),cards:document.querySelectorAll("#psheet .ps-c").length,t:$("#psheet h1")?.textContent,fab:$("#cartfab").hidden,top:(()=>{const r=$("#psheet .ps-c").getBoundingClientRect();const t=document.elementFromPoint(r.left+20,r.top+20);return !!t.closest("#psheet")})(),ws:document.querySelectorAll("#psheet .ps-w").length})`);
  check("link opens the sheet on screen", sv.on && sv.cards === 2 && sv.t === "ชุดนักเรียน", sv);
  check("sheet is on top + no workspace on screen + no FAB", sv.top && sv.ws === 0 && sv.fab, sv);
  check("no JS errors", errs.length === 0, errs);
  console.log(`\n${ok} passed, ${bad} failed`); ws.close(); ch.kill(); process.exit(bad ? 1 : 0);
})();
