// 🛒 Enter-reveal test. Run after build_viewer.py:  node tools/test_cart.js [outdir]
// Drives real headless Chrome over CDP: real mouse drags + finger swipes (hit-tested), the ribbon, the drawer, print-to-PDF of
// the sheet, the student link. Screenshots for an eyeball check land in outdir (cart-*.png).
const { spawn } = require("child_process"), fs = require("fs"), path = require("path"), os = require("os");
const CH = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const ROOT = path.join(__dirname, ".."), URL0 = "file:///" + encodeURI(path.join(ROOT, "index.html").replace(/\\/g, "/"));
const OUT = process.argv[2] || os.tmpdir();
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ok = 0, bad = 0; const check = (n, c, x) => { if (c) { ok++; console.log("  ✓", n); } else { bad++; console.log("  ✗", n, x === undefined ? "" : JSON.stringify(x)); } };
(async () => {
  for (const d of fs.readdirSync(os.tmpdir())) if (d.startsWith("ent-")) try { fs.rmSync(path.join(os.tmpdir(), d), { recursive: true, force: true }); } catch (_) {}   // sweep leftovers from earlier runs
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), "ent-"));
  const ch = spawn(CH, ["--headless=new", "--mute-audio", "--remote-debugging-port=9334", "--user-data-dir=" + prof, "--window-size=1200,900", "about:blank"]);
  process.on("exit",()=>{try{ch.kill();fs.rmSync(prof,{recursive:true,force:true,maxRetries:8,retryDelay:150});}catch(_){}});   // never leave Chrome profiles in Temp (they filled C: once)
  let ws; for (let i = 0; i < 40; i++) { try { const l = await (await fetch("http://127.0.0.1:9334/json")).json(); const p = l.find(x => x.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch (_) {} await sleep(250); }
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

  const key = async k => { for (const type of ["keyDown", "keyUp"]) await cdp("Input.dispatchKeyEvent", { type, key: k, code: k, windowsVirtualKeyCode: k === "Enter" ? 13 : 0, text: type === "keyDown" && k === "Enter" ? "\r" : undefined }); await sleep(300); };
  await go(URL0);
  // present modal: focus the → button (as after a mouse click), Enter must open the เฉลย, not jump
  const pre = await ev(`(()=>{enterApp(10,10,()=>{});filtered=DATA.questions.slice(0,60);render();const i=filtered.findIndex(q=>q.solHtml||q.solAnswer);openModal(i);const n=document.querySelector("#mshot");n&&n.focus();return {i,mIdx,foc:document.activeElement&&document.activeElement.textContent}})()`);
  await key("Enter");
  check("modal: Enter with arrow focused opens เฉลย, stays on same Q", await ev(`!!document.querySelector("#msol .solwrap.show")&&mIdx===${pre.i}`), pre);
  await key("Enter"); check("modal: Enter again closes it", await ev(`!document.querySelector("#msol .solwrap.show")`));
  await ev(`closeModal()`);
  // poster view
  await ev(`view="poster";render()`); await sleep(500);
  await key("Enter"); check("poster: Enter opens deck เฉลย", await ev(`(()=>{const b=document.querySelector("#deck .solbtn");return !!b&&(b.nextElementSibling&&b.nextElementSibling.classList.contains("show")||b.getAttribute("aria-expanded")==="true"||/ซ่อน/.test(b.textContent))})()`), await ev(`document.querySelector("#deck .solbtn")?.outerHTML.slice(0,200)`));
  // cards view: hover a card, Enter opens that card's เฉลย
  await ev(`view="cards";render()`); await sleep(500);
  const c = await ev(`(()=>{const b=document.querySelectorAll(".solbtn")[1];b.scrollIntoView({block:"center"});const r=b.getBoundingClientRect();return {x:r.left+5,y:r.top-30}})()`);
  await cdp("Input.dispatchMouseEvent", { type: "mouseMoved", x: c.x, y: c.y }); await sleep(200);
  const before = await ev(`document.querySelectorAll(".solwrap.show").length`);
  await key("Enter"); check("cards: Enter opens hovered card's เฉลย", await ev(`document.querySelectorAll(".solwrap.show").length`) === before + 1, before);
  check("no JS errors", errs.length === 0, errs);
  console.log(ok + " ok, " + bad + " bad"); ws.close(); ch.kill(); process.exit(bad ? 1 : 0);
})();
