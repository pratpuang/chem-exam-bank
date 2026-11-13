// 🛒 teaching-models test (models.html + โมเดล drawer): node tools/test_models.js [outdir]. Run after build_viewer.py:  node tools/test_cart.js [outdir]
// Drives real headless Chrome over CDP: real mouse drags + finger swipes (hit-tested), the ribbon, the drawer, print-to-PDF of
// the sheet, the student link. Screenshots for an eyeball check land in outdir (cart-*.png).
const { spawn } = require("child_process"), fs = require("fs"), path = require("path"), os = require("os");
const CH = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const ROOT = path.join(__dirname, ".."), URL0 = "file:///" + encodeURI(path.join(ROOT, "index.html").replace(/\\/g, "/"));
const OUT = process.argv[2] || os.tmpdir();
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ok = 0, bad = 0; const check = (n, c, x) => { if (c) { ok++; console.log("  ✓", n); } else { bad++; console.log("  ✗", n, x === undefined ? "" : JSON.stringify(x)); } };
(async () => {
  for (const d of fs.readdirSync(os.tmpdir())) if (d.startsWith("mod-")) try { fs.rmSync(path.join(os.tmpdir(), d), { recursive: true, force: true }); } catch (_) {}   // sweep leftovers from earlier runs
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), "mod-"));
  const ch = spawn(CH, ["--headless=new", "--mute-audio", "--remote-debugging-port=9340", "--user-data-dir=" + prof, "--window-size=1400,950", "about:blank"]);
  process.on("exit",()=>{try{ch.kill();fs.rmSync(prof,{recursive:true,force:true,maxRetries:8,retryDelay:150});}catch(_){}});   // never leave Chrome profiles in Temp (they filled C: once)
  let ws; for (let i = 0; i < 40; i++) { try { const l = await (await fetch("http://127.0.0.1:9340/json")).json(); const p = l.find(x => x.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch (_) {} await sleep(250); }
  await new Promise(r => ws.onopen = r); let id = 0; const pend = {};
  ws.onmessage = m => { const d = JSON.parse(m.data); if (d.id && pend[d.id]) { pend[d.id](d); delete pend[d.id]; } };
  const cdp = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async e => { const r = await cdp("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true }); if (r.result.exceptionDetails) console.log("JS ERR", r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text); return r.result.result?.value; };
  const errs = []; await cdp("Runtime.enable"); ws.addEventListener("message", m => { const d = JSON.parse(m.data); if (d.method === "Runtime.exceptionThrown") errs.push(d.params.exceptionDetails.exception?.description?.slice(0, 200)); });
  await cdp("Page.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1400, height: 950, deviceScaleFactor: 1, mobile: false });
  const go = async u => { await cdp("Page.navigate", { url: u }); await sleep(600); if (u === "about:blank") return;
    for (let i = 0; i < 60; i++) { if (await ev(`typeof openModal==="function"&&document.readyState==="complete"`)) break; await sleep(500); } await sleep(1200); };
  const shot = async (name, clip) => { const r = await cdp("Page.captureScreenshot", clip ? { format: "png", clip: { ...clip, scale: 1 } } : { format: "png" }); fs.writeFileSync(path.join(OUT, name), Buffer.from(r.result.data, "base64")); };
  // real input at an element's point, after proving it is the top element there


  const MURL = URL0.replace("index.html", "models.html");
  await cdp("Page.navigate", { url: MURL }); for (let i = 0; i < 40 && !(await ev(`!!window.__gas`)); i++) await sleep(250); await sleep(300);
  const g = e => ev(`(()=>{const G=window.__gas,S=G.S;return ${e}})()`);
  check("starts at 40 dots, P ~ 0.99 atm", await g(`G.ps.length===40&&Math.abs(S.P-0.985)<0.01`), await g(`[G.ps.length,S.P]`));
  const set = async (k, v) => { await ev(`(()=>{const i=document.querySelector('.sl[data-k="${k}"] input');i.value=${v};i.dispatchEvent(new Event("input"))})()`); };
  const lock = async k => { await ev(`document.querySelector('#glocks button[data-v="${k}"]').click()`); await sleep(100); };
  // hold T: hammer the piston down and up; speeds must stay matched to T (thermostat) and no dot may leave the box
  await lock("T");
  for (const v of [1.2, 9, 1, 8, 1.5, 6]) { await set("V", v); await sleep(250); }
  await sleep(1500);
  const rms = await g(`Math.sqrt(G.ps.reduce((a,p)=>a+p.vx*p.vx+p.vy*p.vy,0)/G.ps.length)/G.vrms(S.T)`);
  check("piston pumping doesn't heat the dots (rms speed within 15% of T's)", Math.abs(rms - 1) < .15, rms);
  check("every dot inside the chamber", await g(`G.ps.every(p=>p.x>=G.geo.CX0&&p.x<=G.geo.CX1&&p.y<=G.geo.CB&&p.y>=G.geo.yOf(S.vDisp)-1)`));
  check("Boyle: P*V = nRT", await g(`Math.abs(S.P*S.V-S.n*0.0821*S.T)<1e-6`));
  check("hold T: T slider disabled, V free", await ev(`document.querySelector('.sl[data-k="T"] input').disabled&&!document.querySelector('.sl[data-k="V"] input').disabled`));
  // hold V: T up -> P up, V unchanged
  await lock("V"); const v0 = await g(`S.V`), p0 = await g(`S.P`);
  await set("T", 600); await sleep(200);
  check("hold V: T 300 -> 600 doubles P", Math.abs(await g(`S.P`) / p0 - 2) < .02, [p0, await g(`S.P`)]);
  check("hold V: V unchanged, V slider disabled", await g(`S.V`) === v0 && await ev(`document.querySelector('.sl[data-k="V"] input').disabled`));
  // hold P: heat -> V grows; push past the top stop -> P has to change and the stop warning shows
  await set("T", 300); await lock("P"); const pH = await g(`S.Pheld`);
  await set("T", 450); await sleep(200);
  check("hold P: P stays, V = nRT/P", await g(`Math.abs(S.P-S.Pheld)<1e-9&&Math.abs(S.V-S.n*0.0821*S.T/S.Pheld)<1e-6`));
  await set("n", 0.5); await sleep(300);
  check("hold P: past the stop -> V capped, P rises, warning shown", await g(`S.V===10&&S.P>S.Pheld&&S.stop`) && await ev(`document.querySelector("#geq").textContent.includes("ชนจุดหยุด")`));
  check("n 0.50 -> 100 dots", await g(`G.ps.length`) === 100);
  await set("n", 0.1); await sleep(300);
  check("n 0.10 -> 20 dots (gas let out)", await g(`G.ps.length`) === 20);
  await ev(`document.querySelector("#greset").click()`); await sleep(1200);
  // Ea: heating puts more of the dots past the line
  check("Ea line starts OFF", await ev(`document.querySelector("#gea").textContent.includes("ปิด")`));
  await ev(`document.querySelector("#gea").click()`);
  await lock("V"); await set("T", 300); await sleep(3500); const e1 = await g(`G.eap`);
  await set("T", 650); await sleep(3500); const e2 = await g(`G.eap`);
  check("Ea: hotter gas -> bigger share past Ea", e2 > e1 + 10, [e1, e2]);
  await set("T", 300); await lock("T"); await sleep(1500);
  await shot("models.png");
  await ev(`document.querySelector('#mtabs button[data-i="0"]').click()`); await sleep(1500);
  check("บท 4 tab shows the VSEPR 3D model inside the panel", await ev(`!!document.querySelector("iframe.vsf")&&document.querySelector("iframe.vsf").src.includes("vsepr.html?embed=1")`));
  // บท 9 rate: box reacts faster when hot; one-collision view passes / bounces by energy
  await cdp("Page.navigate", { url: MURL + "?ch=09" }); for (let i = 0; i < 40 && !(await ev(`!!window.__rate`)); i++) await sleep(250);
  check("?ch=09 opens the rate model", await ev(`document.querySelector("#mtabs button.on").textContent.includes("บท 9")`));
  await ev(`__rate.setT(250)`); await sleep(3000); const cold = await ev(`__rate.evs.length`);
  await ev(`__rate.setT(700)`); await sleep(3000); const hot = await ev(`__rate.evs.length`);
  check("hotter box -> more reactions per 3 s", hot > cold, [cold, hot]);
  await sleep(1500); await shot("rate-box.png");
  await ev(`document.querySelector('#rsw button[data-v="one"]').click()`); await sleep(500);
  await ev(`__one.fire(0.95)`); await sleep(4500);
  check("strong shot: over the hump, AB forms", await ev(`__one.st==="done"&&__one.s===1`), await ev(`[__one.st,__one.s]`));
  await shot("rate-one.png");
  await ev(`__one.reset()`); await sleep(300); await ev(`__one.fire(0.35)`); await sleep(5000);
  check("weak shot: turns back, no reaction", await ev(`__one.st==="done"&&__one.s===0`), await ev(`[__one.st,__one.s]`));
  // the drawer inside the bank
  await go(URL0);
  await ev(`document.querySelector("#motab").click()`); await sleep(1200);
  check("old โมเลกุล 3D tab is gone (merged)", await ev(`!document.querySelector("#vstab")&&!document.querySelector("#vs")`));
  check("โมเดล tab opens the drawer with models.html", await ev(`document.body.classList.contains("moopen")&&document.querySelector("#mof").src.includes("models.html?embed=1&ch=")`));
  await shot("models-drawer.png");
  check("no JS errors", errs.length === 0, errs);
  console.log(ok + " ok, " + bad + " bad"); ws.close(); ch.kill(); process.exit(bad ? 1 : 0);
})();
