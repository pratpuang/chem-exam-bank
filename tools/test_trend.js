// 🛒 periodic trend-mode test: node tools/test_trend.js [outdir]. Run after build_viewer.py:  node tools/test_cart.js [outdir]
// Drives real headless Chrome over CDP: real mouse drags + finger swipes (hit-tested), the ribbon, the drawer, print-to-PDF of
// the sheet, the student link. Screenshots for an eyeball check land in outdir (cart-*.png).
const { spawn } = require("child_process"), fs = require("fs"), path = require("path"), os = require("os");
const CH = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const ROOT = path.join(__dirname, ".."), URL0 = "file:///" + encodeURI(path.join(ROOT, "index.html").replace(/\\/g, "/"));
const OUT = process.argv[2] || os.tmpdir();
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ok = 0, bad = 0; const check = (n, c, x) => { if (c) { ok++; console.log("  ✓", n); } else { bad++; console.log("  ✗", n, x === undefined ? "" : JSON.stringify(x)); } };
(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), "trd-"));
  const ch = spawn(CH, ["--headless=new", "--mute-audio", "--remote-debugging-port=9335", "--user-data-dir=" + prof, "--window-size=1500,1000", "about:blank"]);
  let ws; for (let i = 0; i < 40; i++) { try { const l = await (await fetch("http://127.0.0.1:9335/json")).json(); const p = l.find(x => x.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch (_) {} await sleep(250); }
  await new Promise(r => ws.onopen = r); let id = 0; const pend = {};
  ws.onmessage = m => { const d = JSON.parse(m.data); if (d.id && pend[d.id]) { pend[d.id](d); delete pend[d.id]; } };
  const cdp = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async e => { const r = await cdp("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true }); if (r.result.exceptionDetails) console.log("JS ERR", r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text); return r.result.result?.value; };
  const errs = []; await cdp("Runtime.enable"); ws.addEventListener("message", m => { const d = JSON.parse(m.data); if (d.method === "Runtime.exceptionThrown") errs.push(d.params.exceptionDetails.exception?.description?.slice(0, 200)); });
  await cdp("Page.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1500, height: 1000, deviceScaleFactor: 1, mobile: false });
  const go = async u => { await cdp("Page.navigate", { url: u }); await sleep(600); if (u === "about:blank") return;
    for (let i = 0; i < 60; i++) { if (await ev(`typeof openModal==="function"&&document.readyState==="complete"`)) break; await sleep(500); } await sleep(1200); };
  const shot = async (name, clip) => { const r = await cdp("Page.captureScreenshot", clip ? { format: "png", clip: { ...clip, scale: 1 } } : { format: "png" }); fs.writeFileSync(path.join(OUT, name), Buffer.from(r.result.data, "base64")); };
  // real input at an element's point, after proving it is the top element there


  await go(URL0);
  await ev(`PD.open()`); await sleep(900);
  const btn = async k => { await ev(`document.querySelector('#pdtr button[data-t="${k}"]').click()`); await sleep(1800); };
  check("trend row has off + 6 trends", await ev(`document.querySelectorAll("#pdtr button").length`) === 7);
  await btn(1);
  check("IE: tiles heat-coloured", await ev(`getComputedStyle(document.querySelector('.pde[data-z="9"] .pf')).backgroundColor`) !== await ev(`getComputedStyle(document.querySelector('.pde[data-z="3"] .pf')).backgroundColor`));
  check("IE: F tile shows 1681", await ev(`document.querySelector('.pde[data-z="9"] .pf s').textContent`) === "1681");
  check("IE: exception tags on B,O,Al,S", await ev(`[...document.querySelectorAll(".pde.tex")].map(t=>t.dataset.z).join()`) === "5,8,13,16");
  check("IE: both arrows shown", await ev(`document.querySelectorAll(".tra.show").length`) === 2);
  check("IE: graph drawn with 86 points", await ev(`document.querySelectorAll("#pdgph circle").length`) === 86);
  check("IE: drawer widened", await ev(`document.querySelector("#pd").classList.contains("trw")`));
  // hover a tile -> big tile shows value
  const c = await ev(`(()=>{const r=document.querySelector('.pde[data-z="11"]').getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()`);
  await cdp("Input.dispatchMouseEvent", { type: "mouseMoved", x: c.x, y: c.y }); await sleep(300);
  check("hover Na: big tile shows 496 kJ/mol", await ev(`document.querySelector("#pdbig .bf s").textContent`) === "496 kJ/mol");
  await shot("trend-ie.png");
  await ev(`document.querySelector("#pdgph").scrollIntoView({block:"center"})`); await sleep(300); await shot("trend-graph.png"); await ev(`document.querySelector("#pd").scrollTop=0`);
  await btn(0);
  check("size: spheres sized (Cs > H)", await ev(`parseFloat(document.querySelector('.pde[data-z="55"]').style.getPropertyValue("--sz"))>parseFloat(document.querySelector('.pde[data-z="1"]').style.getPropertyValue("--sz"))`));
  await shot("trend-size.png");
  await btn(3); await shot("trend-ea.png");
  // memorize mode turns trend off; mass labels come back
  await ev(`document.querySelector("#pdmem").click()`); await sleep(1500);
  check("ท่อง on -> trend off", await ev(`!document.querySelector("#pdg").classList.contains("trend")&&!document.querySelector("#pd").classList.contains("trw")`));
  await ev(`document.querySelector("#pdmem").click()`); await sleep(1500);
  check("trend off: Na shows mass again", await ev(`document.querySelector('.pde[data-z="11"] .pf s').textContent`) === "22.99");
  await btn(2); await btn(-1);
  check("off button clears", await ev(`!document.querySelector("#pdgph").classList.contains("show")&&!document.querySelector(".tra.show")`));
  check("no JS errors", errs.length === 0, errs);
  console.log(ok + " ok, " + bad + " bad"); ws.close(); ch.kill(); process.exit(bad ? 1 : 0);
})();
