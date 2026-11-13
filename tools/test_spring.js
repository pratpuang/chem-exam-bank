// 🛒 spring-motion test (SP module): node tools/test_spring.js. Run after build_viewer.py:  node tools/test_cart.js [outdir]
// Drives real headless Chrome over CDP: real mouse drags + finger swipes (hit-tested), the ribbon, the drawer, print-to-PDF of
// the sheet, the student link. Screenshots for an eyeball check land in outdir (cart-*.png).
const { spawn } = require("child_process"), fs = require("fs"), path = require("path"), os = require("os");
const CH = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const ROOT = path.join(__dirname, ".."), URL0 = "file:///" + encodeURI(path.join(ROOT, "index.html").replace(/\\/g, "/"));
const OUT = process.argv[2] || os.tmpdir();
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ok = 0, bad = 0; const check = (n, c, x) => { if (c) { ok++; console.log("  ✓", n); } else { bad++; console.log("  ✗", n, x === undefined ? "" : JSON.stringify(x)); } };
(async () => {
  for (const d of fs.readdirSync(os.tmpdir())) if (d.startsWith("spr-")) try { fs.rmSync(path.join(os.tmpdir(), d), { recursive: true, force: true }); } catch (_) {}   // sweep leftovers from earlier runs
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), "spr-"));
  const ch = spawn(CH, ["--headless=new", "--mute-audio", "--remote-debugging-port=9338", "--user-data-dir=" + prof, "--window-size=1200,900", "about:blank"]);
  process.on("exit",()=>{try{ch.kill();fs.rmSync(prof,{recursive:true,force:true,maxRetries:8,retryDelay:150});}catch(_){}});   // never leave Chrome profiles in Temp (they filled C: once)
  let ws; for (let i = 0; i < 40; i++) { try { const l = await (await fetch("http://127.0.0.1:9338/json")).json(); const p = l.find(x => x.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch (_) {} await sleep(250); }
  await new Promise(r => ws.onopen = r); let id = 0; const pend = {};
  ws.onmessage = m => { const d = JSON.parse(m.data); if (d.id && pend[d.id]) { pend[d.id](d); delete pend[d.id]; } };
  const cdp = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async e => { const r = await cdp("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true }); if (r.result.exceptionDetails) console.log("JS ERR", r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text); return r.result.result?.value; };
  const errs = []; await cdp("Runtime.enable"); ws.addEventListener("message", m => { const d = JSON.parse(m.data); if (d.method === "Runtime.exceptionThrown") errs.push(d.params.exceptionDetails.exception?.description?.slice(0, 200)); });
  await cdp("Page.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1200, height: 900, deviceScaleFactor: 1, mobile: false });
  const go = async u => { await cdp("Page.navigate", { url: u }); await sleep(600); if (u === "about:blank") return;
    for (let i = 0; i < 60; i++) { if (await ev(`typeof openModal==="function"&&document.readyState==="complete"`)) break; await sleep(500); } await sleep(1200); };
  const shot = async (name, clip) => { const r = await cdp("Page.captureScreenshot", clip ? { format: "png", clip: { ...clip, scale: 1 } } : { format: "png" }); fs.writeFileSync(path.join(OUT, name), Buffer.from(r.result.data, "base64")); };
  // real input at an element's point, after proving it is the top element there


  const anims = sel => ev(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});return e?e.getAnimations().length:-1})()`);
  await go(URL0);
  await ev(`enterApp(10,10,()=>{});filtered=DATA.questions.filter(q=>/<li/.test(q.bodyHtml)&&(q.solHtml||q.solAnswer)).slice(0,40);view="poster";pIdx=0;render()`); await sleep(1500);
  check("SP on, html.spr set", await ev(`SP.on()&&document.documentElement.classList.contains("spr")`));
  // poster next: anticipation exit, then the new card + its parts spring in
  const id0 = await ev(`document.querySelector("#deck .poster").dataset.i`);
  await ev(`pstep(1)`); await sleep(120);
  check("poster exit is a WAAPI animation (anticipation)", await anims("#deck .poster") > 0);
  await sleep(150);
  check("new poster springs in", await anims("#deck .poster") > 0 && await ev(`document.querySelector("#deck .poster").dataset.i`) !== id0);
  check("its parts spring in too (overlapping)", await ev(`[...SP.parts(document.querySelector("#deck .poster"))].filter(e=>e.getAnimations().length).length`) >= 3);
  await sleep(1600);
  check("poster settles at rest (opacity 1, no transform)", await ev(`(()=>{const c=getComputedStyle(document.querySelector("#deck .poster"));return c.opacity==="1"&&(c.transform==="none")})()`));
  // mark a choice
  await ev(`document.querySelector("#deck .body li").click()`); await sleep(60);
  check("marked choice pops", await anims("#deck .body li.mk") > 0);
  // reveal
  await ev(`document.querySelector("#deck .solbtn").click()`); await sleep(80);
  check("solution springs open", await anims("#deck .solwrap.show") > 0);
  await sleep(1500);
  check("solution settles visible", await ev(`getComputedStyle(document.querySelector("#deck .solwrap.show")).opacity==="1"`));
  // generic button press
  await ev(`document.querySelector("#pnext").dispatchEvent(new MouseEvent("click",{bubbles:true}))`); await sleep(40);
  check("button press pops", await anims("#pnext") > 0);
  await sleep(1200);
  // modal
  await ev(`openModal(2)`); await sleep(200);
  check("modal parts stagger in", await ev(`[...SP.parts(document.querySelector("#modal .sheet"))].filter(e=>e.getAnimations().length).length`) >= 2);
  await sleep(1200); await ev(`step(1)`); await sleep(300);
  check("modal step springs the sheet", await anims("#modal .sheet") > 0);
  await sleep(1500);
  check("modal sheet settles", await ev(`getComputedStyle(document.querySelector("#modal .sheet")).opacity==="1"`));
  await ev(`closeModal()`); await sleep(500);
  // cards view stagger
  await ev(`view="cards";render()`); await sleep(100);
  check("cards stagger in", await ev(`[...document.querySelectorAll(".card.anim")].filter(e=>e.getAnimations().length).length`) >= 5);
  // periodic tile hop
  await ev(`PD.open()`); await sleep(900);
  await ev(`document.querySelector('.pde[data-z="6"]').click()`); await sleep(50);
  check("periodic tile hops", await anims('.pde[data-z="6"]') > 0);
  await ev(`PD.close()`); await sleep(600);
  // reduced motion: nothing animates
  await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] }); await sleep(200);
  await ev(`view="poster";render()`); await sleep(100);
  check("reduced motion: SP off, poster not springing", await ev(`!SP.on()`) && await ev(`document.querySelector("#deck .poster").getAnimations().filter(a=>a instanceof CSSAnimation===false).length`) === 0);
  check("no JS errors", errs.length === 0, errs);
  console.log(ok + " ok, " + bad + " bad"); ws.close(); ch.kill(); process.exit(bad ? 1 : 0);
})();
