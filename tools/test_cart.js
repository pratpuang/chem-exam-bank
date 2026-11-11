// 🛒 cart test (tools/cart_part.py). Run after build_viewer.py:  node tools/test_cart.js [outdir]
// Drives real headless Chrome over CDP: real mouse drags + finger swipes (hit-tested), the ribbon, the drawer, print-to-PDF of
// the sheet, the student link. Screenshots for an eyeball check land in outdir (cart-*.png).
const { spawn } = require("child_process"), fs = require("fs"), path = require("path"), os = require("os");
const CH = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const ROOT = path.join(__dirname, ".."), URL0 = "file:///" + encodeURI(path.join(ROOT, "index.html").replace(/\\/g, "/"));
const OUT = process.argv[2] || os.tmpdir();
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ok = 0, bad = 0; const check = (n, c, x) => { if (c) { ok++; console.log("  ✓", n); } else { bad++; console.log("  ✗", n, x === undefined ? "" : JSON.stringify(x)); } };
(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), "cart-"));
  const ch = spawn(CH, ["--headless=new", "--mute-audio", "--remote-debugging-port=9333", "--user-data-dir=" + prof, "--window-size=1200,900", "about:blank"]);
  let ws; for (let i = 0; i < 40; i++) { try { const l = await (await fetch("http://127.0.0.1:9333/json")).json(); const p = l.find(x => x.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch (_) {} await sleep(250); }
  await new Promise(r => ws.onopen = r); let id = 0; const pend = {};
  ws.onmessage = m => { const d = JSON.parse(m.data); if (d.id && pend[d.id]) { pend[d.id](d); delete pend[d.id]; } };
  const cdp = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async e => { const r = await cdp("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true }); if (r.result.exceptionDetails) console.log("JS ERR", r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text); return r.result.result?.value; };
  const errs = []; await cdp("Runtime.enable"); ws.addEventListener("message", m => { const d = JSON.parse(m.data); if (d.method === "Runtime.exceptionThrown") errs.push(d.params.exceptionDetails.exception?.description?.slice(0, 200)); });
  await cdp("Page.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1200, height: 900, deviceScaleFactor: 1, mobile: false });
  const go = async u => { await cdp("Page.navigate", { url: u }); await sleep(600); if (u === "about:blank") return;
    for (let i = 0; i < 60; i++) { if (await ev(`typeof CART!=="undefined"&&document.readyState==="complete"`)) break; await sleep(500); } await sleep(1200); };
  const shot = async (name, clip) => { const r = await cdp("Page.captureScreenshot", clip ? { format: "png", clip: { ...clip, scale: 1 } } : { format: "png" }); fs.writeFileSync(path.join(OUT, name), Buffer.from(r.result.data, "base64")); };
  // real input at an element's point, after proving it is the top element there
  const center = async (sel, fy) => ev(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});if(!e)return null;e.scrollIntoView({block:"center"});const r=e.getBoundingClientRect();const x=r.left+r.width*.5,y=r.top+${fy == null ? "Math.min(r.height/2,120)" : "r.height*" + fy};const t=document.elementFromPoint(x,y);return {x,y,hit:!!t&&(t===e||e.contains(t)),top:t&&String(t.className||t.tagName)};})()`);
  const click = async sel => { const c = await center(sel); if (!c || !c.hit) return c; for (const type of ["mousePressed", "mouseReleased"]) await cdp("Input.dispatchMouseEvent", { type, x: c.x, y: c.y, button: "left", clickCount: 1 }); await sleep(350); return c; };
  const mdrag = async (sel, dx, fy) => { const c = await center(sel, fy); if (!c || !c.hit) return c;
    await cdp("Input.dispatchMouseEvent", { type: "mousePressed", x: c.x, y: c.y, button: "left", buttons: 1, clickCount: 1 });
    for (let k = 1; k <= 10; k++) { await cdp("Input.dispatchMouseEvent", { type: "mouseMoved", x: c.x + dx * k / 10, y: c.y + k * .4, button: "left", buttons: 1 }); await sleep(16); }
    await cdp("Input.dispatchMouseEvent", { type: "mouseReleased", x: c.x + dx, y: c.y + 4, button: "left", buttons: 0, clickCount: 1 }); await sleep(900); return c; };
  const swipe = async (sel, dx) => { const c = await center(sel); if (!c || !c.hit) return c; const pts = x => [{ x, y: c.y }];
    await cdp("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: pts(c.x) });
    for (let k = 1; k <= 8; k++) { await cdp("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: pts(c.x + dx * k / 8) }); await sleep(16); }
    await cdp("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); await sleep(900); return c; };
  const n = () => ev(`JSON.parse(localStorage.getItem("cqb_cart")||'{"ids":[]}').ids`);

  console.log("1 · mouse drag on the question list");
  await go(URL0); await ev(`localStorage.clear();localStorage.setItem("cqb_sfx","0")`); await go("about:blank"); await go(URL0 + "#ch=07");
  await ev(`document.querySelector('#layout [data-v="cards"]').click()`); await sleep(800); await ev(`scrollTo(0,0)`);
  check("ribbons in the DOM, none showing", await ev(`document.querySelectorAll("#root .cpin").length>0&&!document.querySelector("#root .cpin.done")`));
  check("no tab while empty", await ev(`getComputedStyle($("#carttab")).display==="none"`));
  await ev(`[...document.querySelectorAll("#root .card")].slice(0,3).forEach((c,i)=>c.id="c"+i)`);
  const d1 = await mdrag("#c0 .body", 170); check("mouse drag hit-tests the card", d1 && d1.hit, d1);
  let ids = await n(); check("mouse drag sideways adds", ids.length === 1, ids);
  check("ribbon down on that card", await ev(`!!document.querySelector("#c0>.cpin.done")`));
  check("tab shows 1", await ev(`getComputedStyle($("#carttab")).display!=="none"&&$("#cartn").textContent==="1"`));
  check("no text left selected", await ev(`getSelection().isCollapsed`));
  await mdrag("#c1 .body", 60); check("short drag springs back, adds nothing", (await n()).length === 1);
  await mdrag("#c1 .body", -170); check("drag left adds too", (await n()).length === 2);
  await sleep(700); await ev(`document.querySelector("#c0").scrollIntoView({block:"start"});scrollBy(0,-250)`); await sleep(300);
  await shot("cart-1-cards.png");

  console.log("2 · ribbon tap removes, undo puts it back");
  const rb = await center("#c1>.cpin.done", .4); check("ribbon is tappable (top element)", rb && rb.hit, rb);
  await click("#c1>.cpin.done"); check("tap ribbon removes", (await n()).length === 1);
  check("undo offered", await ev(`!$("#ctact").hidden&&$("#ctoast").classList.contains("show")`));
  await shot("cart-2-toast.png", { x: 300, y: 760, width: 600, height: 140 });
  await click("#ctact"); check("undo restores", (await n()).length === 2);

  console.log("3 · finger swipe + keyboard");
  await cdp("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  await swipe("#c2 .body", 170); check("finger swipe adds", (await n()).length === 3);
  await cdp("Emulation.setTouchEmulationEnabled", { enabled: false });
  await ev(`document.querySelector('#layout [data-v="poster"]').click()`); await sleep(800);
  const pid = await ev(`filtered[pIdx].id`); const had = (await n()).includes(pid);
  await cdp("Input.dispatchKeyEvent", { type: "keyDown", key: "c", text: "c" }); await cdp("Input.dispatchKeyEvent", { type: "keyUp", key: "c" }); await sleep(500);
  check("C toggles the poster question", (await n()).includes(pid) !== had);
  if (!had) { await sleep(700); await ev(`scrollTo(0,0)`); await shot("cart-3-poster.png"); }
  await ev(`document.querySelector('#layout [data-v="list"]').click()`); await sleep(800);
  check("list rows carry the ribbon", await ev(`!!document.querySelector("#root .row.incart>.cpin.done")`));
  await ev(`document.querySelector("#root .row.incart").scrollIntoView({block:"center"})`); await sleep(500);
  await shot("cart-4-list.png");

  console.log("4 · drawer");
  await ev(`scrollTo(0,0)`); await shot("cart-5-tab.png", { x: 1000, y: 300, width: 200, height: 300 });
  await click("#carttab"); await sleep(600); check("drawer opens", await ev(`document.body.classList.contains("cartopen")`));
  check("drawer lists all", (await ev(`document.querySelectorAll(".cpi").length`)) === (await n()).length);
  await click("#cpsort"); const ord = await ev(`JSON.parse(localStorage.getItem("cqb_cart")).ids.map(id=>DATA.questions.find(q=>q.id===id).diff)`);
  const rank = { easy: 0, medium: 1, hard: 2 }; check("sort easy→hard", ord.every((d, i) => !i || rank[ord[i - 1]] <= rank[d]), ord);
  await click('#cpws [data-v="38"]');
  await ev(`(()=>{const i=$("#cptitle");i.value="ทดสอบตะกร้า";i.dispatchEvent(new Event("input"))})()`);
  await shot("cart-6-drawer.png");
  const before = (await n()).length; await mdrag(".cpi:last-child .cps", 160, .5); await sleep(400);
  check("mouse-drag an item out of the drawer", (await n()).length === before - 1, await n());
  await click("#ctact"); await sleep(300); check("…and undo", (await n()).length === before);

  console.log("5 · print sheet");
  await ev(`window.print=()=>{window.__printed=(window.__printed||0)+1}`);
  await click("#cpprint"); for (let i = 0; i < 20 && !(await ev(`window.__printed`)); i++) await sleep(500);
  check("print called", (await ev(`window.__printed`)) === 1, await ev(`window.__printed`));
  const sh = await ev(`({cards:document.querySelectorAll("#psheet .ps-c").length,ok:document.querySelectorAll("#psheet .okopt").length,h1:$("#psheet h1").textContent,sc:$("#psheet .ps-sc").textContent,ws:document.querySelectorAll("#psheet .ps-w").length})`);
  check("sheet = cart, no answer marks", sh.cards === before && sh.ok === 0, sh); check("title + count", sh.h1 === "ทดสอบตะกร้า" && sh.sc.includes(before + " ข้อ"), sh);
  await cdp("Emulation.setEmulatedMedia", { media: "print" });
  const pdf = await cdp("Page.printToPDF", { preferCSSPageSize: true, printBackground: true, displayHeaderFooter: false });
  fs.writeFileSync(path.join(OUT, "cart-test-print.pdf"), Buffer.from(pdf.result.data, "base64"));
  await cdp("Emulation.setEmulatedMedia", { media: "" }); await ev(`dispatchEvent(new Event("afterprint"))`);
  check("after print: keep-it nudge", await ev(`$("#cpkeep").classList.contains("nudge")`));

  console.log("6 · keep");
  await ev(`$("#cpname").value="ไคด้า"`); await click("#cpsave"); await click("#cpgive");
  check("set saved + given recorded", (await ev(`JSON.parse(localStorage.getItem("cqb_sets")).length===1&&JSON.parse(localStorage.getItem("cqb_given"))["ไคด้า"].length`)) === before);
  await shot("cart-7-drawer-kept.png");
  await click("#cpx"); await sleep(500); check("drawer closes", !(await ev(`document.body.classList.contains("cartopen")`)));
  await ev(`document.querySelector('#layout [data-v="cards"]').click()`); await sleep(800);
  await ev(`(()=>{const g=JSON.parse(localStorage.getItem("cqb_given"))["ไคด้า"][0];window.__g=g;const c=document.querySelector('#root .cpin[data-id="'+g+'"]').parentElement;c.id="cg";})()`);
  await click("#cg>.cpin.done"); await mdrag("#cg .body", 170);
  check("re-adding a given Q warns", (await ev(`$("#ctmsg").textContent`)).includes("ไคด้า") && await ev(`$("#ctoast").classList.contains("warn")`));

  console.log("7 · present mode bookmark");
  await click("#cg .present-btn"); await sleep(900);
  check("bookmark on (carted)", await ev(`$("#mcart").classList.contains("on")`));
  await click("#mcart"); check("bookmark removes", !(await n()).includes(await ev(`window.__g`)));
  await ev(`$("#mx").click()`); await sleep(500);

  console.log("8 · student link");
  const link = await ev(`location.origin+location.pathname+"#sheet="+JSON.parse(localStorage.getItem("cqb_cart")).ids.map(encodeURIComponent).join(",")+"&t="+encodeURIComponent("ชุดนักเรียน")`);
  await go("about:blank"); await go(link);
  const sv = await ev(`({on:document.body.classList.contains("sheetview"),cards:document.querySelectorAll("#psheet .ps-c").length,t:$("#psheet h1")?.textContent,tab:getComputedStyle($("#carttab")).visibility,top:(()=>{const r=$("#psheet .ps-c").getBoundingClientRect();const t=document.elementFromPoint(r.left+20,r.top+20);return !!t.closest("#psheet")})()})`);
  check("link opens the sheet on top, no tab", sv.on && sv.cards > 0 && sv.t === "ชุดนักเรียน" && sv.top && sv.tab === "hidden", sv);

  console.log("9 · looks: long cart, dark, iPad, phone, empty (eyeball the cart-9*.png)");
  const vp = async (w, h, mobile) => { await cdp("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: !!mobile }); await sleep(400); };
  const fits = () => ev(`(()=>{const p=document.querySelector(".cartpanel"),r=p.getBoundingClientRect(),s=document.querySelector(".cpscroll"),f=document.querySelector(".cpfoot").getBoundingClientRect();
    const bad=[...p.querySelectorAll("button,input,.cpi,.seg")].filter(e=>{const b=e.getBoundingClientRect();return b.width&&(b.left<r.left-1||b.right>innerWidth+1);}).length;
    return {left:r.left>=-1,nohs:s.scrollWidth<=s.clientWidth+1,foot:f.bottom<=innerHeight+1&&f.height>40,bad};})()`);
  const fitOk = f => f.left && f.nohs && f.foot && f.bad === 0;
  await go("about:blank"); await go(URL0 + "#ch=07");
  await ev(`(()=>{const ids=DATA.questions.filter(q=>q.ch==="07").slice(0,10).map(q=>q.id);localStorage.setItem("cqb_cart",JSON.stringify({t:"",ids}));
    localStorage.setItem("cqb_given",JSON.stringify({"ไคด้า":ids.slice(1,3)}));localStorage.setItem("cqb_sets",JSON.stringify([{n:"ชุดปริมาณสาร ม.4",t:"",ids:ids.slice(0,6)},{n:"ไคด้า",t:"",ids:ids.slice(0,3)}]));})()`);
  await go("about:blank"); await go(URL0 + "#ch=07");
  await ev(`document.querySelector('#layout [data-v="cards"]').click()`); await sleep(800);
  check("ribbon owns the corner: the card's ghost number steps aside", await ev(`getComputedStyle(document.querySelector("#root .card.incart>.cnum")).opacity==="0"`));
  await click("#carttab"); await sleep(700);
  check("desktop: 10 items, drawer fits", (await ev(`document.querySelectorAll(".cpi").length`)) === 10 && fitOk(await fits()), await fits());
  await shot("cart-9a-long.png", { x: 620, y: 0, width: 580, height: 900 });
  await ev(`document.body.classList.add("dark")`); await sleep(300); await shot("cart-9b-dark.png", { x: 620, y: 0, width: 580, height: 900 });
  await click("#cpx"); await sleep(600); await ev(`scrollTo(0,0)`); await sleep(200); await shot("cart-9c-dark-cards.png", { x: 600, y: 200, width: 600, height: 420 });
  await ev(`document.body.classList.remove("dark")`);
  await vp(820, 1180, true); await ev(`document.querySelector('#layout [data-v="poster"]').click()`); await sleep(900); await ev(`scrollTo(0,0)`);
  const tabr = await ev(`(()=>{const r=$("#carttab").getBoundingClientRect();return {right:Math.round(innerWidth-r.right),w:r.width,h:r.height}})()`);
  check("iPad: tab sits on the right edge", tabr.right <= 1 && tabr.w >= 36, tabr);
  await shot("cart-9d-ipad-poster.png", { x: 0, y: 0, width: 820, height: 760 });
  await vp(390, 844, true); await ev(`document.querySelector('#layout [data-v="cards"]').click()`); await sleep(900);
  await ev(`document.querySelector("#root .card.incart").scrollIntoView({block:"start"});scrollBy(0,-160)`); await sleep(400); await shot("cart-9e-phone-cards.png");
  await ev(`document.querySelector('#layout [data-v="list"]').click()`); await sleep(800);
  await ev(`document.querySelector("#root .row.incart").scrollIntoView({block:"start"});scrollBy(0,-160)`); await sleep(400); await shot("cart-9f-phone-list.png", { x: 0, y: 100, width: 390, height: 330 });
  await ev(`$("#carttab").click()`); await sleep(800);
  check("phone: drawer fits 390px, footer on screen", fitOk(await fits()), await fits());
  await shot("cart-9g-phone-drawer.png");
  await ev(`document.querySelector(".cpscroll").scrollTop=1e5`); await sleep(300); await shot("cart-9h-phone-drawer-end.png");
  await ev(`$("#cpclear").click()`); await sleep(500);
  check("clear empties + closes, undo offered", (await n()).length === 0 && !(await ev(`document.body.classList.contains("cartopen")`)) && await ev(`!$("#ctact").hidden`));
  await ev(`$("#ctact").click()`); await sleep(400); check("undo brings all 10 back", (await n()).length === 10);
  await ev(`$("#carttab").click()`); await sleep(700);
  await ev(`(async()=>{for(const b of [...document.querySelectorAll(".cpdel")]){b.click();}})()`); await sleep(900);
  check("emptied in the drawer: empty state shows, actions disabled", await ev(`!!document.querySelector(".cpempty")&&$("#cpprint").disabled&&$("#cpsort").disabled`));
  await shot("cart-9i-phone-empty.png");
  await ev(`$("#cpx").click()`); await sleep(500);
  check("empty cart but saved sets exist: the tab stays so the sets are reachable", await ev(`getComputedStyle($("#carttab")).display!=="none"&&$("#cartn").textContent==="0"`));
  await vp(1200, 900, false);
  check("no JS errors", errs.length === 0, errs);
  console.log(`\n${ok} passed, ${bad} failed`); ws.close(); ch.kill(); process.exit(bad ? 1 : 0);
})();
