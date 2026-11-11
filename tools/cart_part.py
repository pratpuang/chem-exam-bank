# -*- coding: utf-8 -*-
"""🛒 swipe-to-cart -> A4 แบบฝึกหัด (Prat's spec, 2026-11-11; sample: Matcha/matcha-output/swipe-cart-sample/).
Swipe a question sideways (touch) or tap 🛒 / press C -> it goes into a per-device cart (localStorage).
Cart panel: title, easy->hard sort, shuffle, drag reorder (⋮⋮), swipe an item out to remove, workspace size,
print -> one-column A4 sheet (header name/date/score-with-count, paper + chapter chips, page numbers, NO answers),
link for a student (#sheet=...), save as named set, mark as given to a student (warns on re-swipe), clear.
Main site only: apply(HTML) is called for index.html, never for the student builds."""

CSS = r"""
/* ===== 🛒 cart ===== */
.cartadd{margin-left:auto;border:2px solid var(--ink);background:var(--card);color:var(--ink);padding:4px 10px;font:700 .8rem inherit;box-shadow:3px 3px 0 var(--sh);cursor:pointer;white-space:nowrap}
.cartadd~.present-btn{margin-left:0}
.cartadd.on{background:var(--yel);color:#141414}
.poster,.card,.row{touch-action:pan-y pinch-zoom}
.cartarm{outline:3px dashed var(--yel);outline-offset:3px}
.incart{position:relative}
.card.incart:after,.poster.incart:after{content:"🛒";position:absolute;left:-12px;top:-12px;width:30px;height:30px;display:grid;place-items:center;background:var(--yel);border:2px solid #141414;border-radius:50%;font-size:15px;z-index:3;pointer-events:none}
.row.incart .row-id:before{content:"🛒 "}
.cartfab{position:fixed;right:18px;bottom:calc(18px + env(safe-area-inset-bottom,0px));z-index:60;border:3px solid #141414;background:var(--yel);color:#141414;font:800 1rem "Anuphan",sans-serif;padding:10px 16px;box-shadow:5px 5px 0 #141414;cursor:pointer;display:flex;gap:8px;align-items:center}
.cartfab[hidden]{display:none}
.cartfab.bump{animation:cbump .35s}
@keyframes cbump{40%{transform:scale(1.18)}}
.cfly{position:fixed;z-index:70;pointer-events:none;font-size:22px;transition:transform .55s cubic-bezier(.5,-0.3,.6,1),opacity .55s}
.ctoast{position:fixed;left:50%;bottom:calc(84px + env(safe-area-inset-bottom,0px));transform:translateX(-50%) translateY(20px);z-index:80;background:#141414;color:#efe9dc;padding:9px 16px;font:700 .85rem "Anuphan",sans-serif;opacity:0;pointer-events:none;transition:.25s;border:2px solid #efe9dc;max-width:88vw;text-align:center}
.ctoast.show{opacity:1;transform:translateX(-50%)}
.cartwrap{position:fixed;inset:0;z-index:65;background:rgba(20,20,20,.35);display:none}
.cartwrap.show{display:block}
.cartpanel{position:absolute;right:0;top:0;bottom:0;width:min(460px,100vw);background:var(--paper);color:var(--ink);border-left:4px solid var(--ink);display:flex;flex-direction:column;gap:10px;padding:14px 14px calc(14px + env(safe-area-inset-bottom,0px));overflow-y:auto;font-family:"Anuphan",sans-serif;animation:cpin .22s ease-out}
@keyframes cpin{from{transform:translateX(40px);opacity:0}}
.cphead{display:flex;align-items:center;gap:8px;font-size:1.1rem}
.cphead .x{margin-left:auto}
.cartpanel button{font-family:inherit;font-weight:700;border:2px solid var(--ink);background:var(--card);color:var(--ink);padding:6px 10px;cursor:pointer;box-shadow:2px 2px 0 var(--sh)}
.cartpanel button.on{background:var(--ink);color:var(--paper)}
.cartpanel input{font:inherit;border:2px solid var(--ink);background:var(--card);color:var(--ink);padding:7px 9px;min-width:0}
.cpt{display:flex;gap:8px;align-items:center;font-weight:700}.cpt input{flex:1}
.cprow{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.cpws{display:inline-flex;align-items:center;gap:4px;margin-left:auto;font-size:.8rem;font-weight:700}
.cpws button{padding:4px 8px;font-size:.78rem}
.cplist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}
.cpi{display:flex;align-items:center;gap:7px;background:var(--card);border:2px solid var(--ink);padding:6px 6px 6px 0;touch-action:pan-y;transition:transform .2s,opacity .2s}
.cpi.drag{opacity:.85;box-shadow:4px 4px 0 var(--sh);z-index:2;position:relative;transition:none}
.cpi.gone{transform:translateX(110%);opacity:0}
.cph{cursor:grab;touch-action:none;padding:6px 6px 6px 8px;color:var(--mut);font-weight:800;user-select:none}
.cpi .badge{font-size:.66rem}
.cpdot{width:9px;height:9px;flex:none}.cpdot.d-easy{background:var(--blue);border-radius:50%}.cpdot.d-medium{background:var(--yel)}.cpdot.d-hard{background:var(--red);clip-path:polygon(50% 0,100% 100%,0 100%)}
.cps{flex:1;min-width:0;font-size:.8rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cpg{font-size:.68rem;color:var(--red);font-weight:700;white-space:nowrap}
.cpdel{padding:2px 8px!important;box-shadow:none!important}
.cpempty{color:var(--mut);text-align:center;padding:24px 8px;font-size:.9rem;border:2px dashed var(--mut)}
.cpgo{display:flex;gap:8px}.cpgo button{flex:1;padding:11px 10px}
.cpprint{background:var(--yel)!important;color:#141414!important}
.cpkeep{display:flex;flex-wrap:wrap;gap:6px;border:2px solid var(--ink);padding:9px;background:var(--card)}
.cpkeep input{flex:1 1 100%}
.cpkeep .lb{flex:1 1 100%;font-size:.8rem;font-weight:800}
.cpkeep.nudge{border-color:var(--red);box-shadow:4px 4px 0 var(--red)}
.cpsets h4{margin:4px 0 6px;font-size:.85rem}
.cpset{display:flex;gap:6px;align-items:center;font-size:.82rem;padding:4px 0;border-bottom:1px dashed var(--mut)}
.cpset span{flex:1}
.cpset button{padding:2px 8px;font-size:.75rem}
/* the sheet itself (print, and the student link on screen) */
.psheet{display:none}
body.sheetview{overflow:hidden}
body.sheetview .psheet{display:block;position:fixed;inset:0;z-index:90;overflow-y:auto;background:#efe9dc;padding:0 0 40px}
.psbar{position:sticky;top:0;z-index:2;background:#141414;color:#efe9dc;display:flex;gap:10px;align-items:center;padding:10px 14px;border-bottom:5px solid #f2b705;font:700 .9rem "Anuphan",sans-serif}
.psbar button{margin-left:auto;font:800 .9rem "Anuphan",sans-serif;background:#f2b705;border:2px solid #efe9dc;padding:7px 14px;cursor:pointer}
.pspage{max-width:820px;margin:16px auto;padding:0 12px}
.psheet{color:#141414;font-family:"Anuphan","IBM Plex Sans Thai",system-ui,sans-serif}
.ps-hd{display:grid;grid-template-columns:1fr auto auto;gap:14px;align-items:stretch;border:3px solid #141414;box-shadow:6px 6px 0 #141414;padding:12px 14px;margin:0 6px 16px 0;background:#fffdf7;border-top:9px solid #e4412b}
.ps-k{font:800 .68rem "JetBrains Mono","Anuphan",monospace;letter-spacing:.08em;color:#e4412b}
.ps-hd h1{margin:2px 0 0;font-size:1.45rem;font-weight:800;color:#141414}
.ps-f div,.ps-sc,.ps-sc b{color:#141414}
.ps-f{display:flex;flex-direction:column;justify-content:center;gap:10px;min-width:62mm}
.ps-f div{font-weight:700;font-size:.82rem;display:flex;gap:6px;align-items:flex-end}.ps-f span{flex:1;border-bottom:2px dotted #141414;height:1.1em}
.ps-sc{border:3px solid #141414;padding:6px 10px;text-align:center;font-weight:800;font-size:.72rem;min-width:28mm;display:flex;flex-direction:column;justify-content:center;background:#fff}
.ps-sc b{font-size:1.25rem;margin-top:4px}
.ps-c{position:relative;background:#fffdf7;border:3px solid #141414;box-shadow:5px 5px 0 #141414;padding:12px 14px 12px 24px;margin:0 6px 14px 0;overflow:hidden;break-inside:avoid;page-break-inside:avoid}
.ps-c:before{content:"";position:absolute;left:0;top:0;bottom:0;width:8px;background:#e4412b}
.ps-c.lv-easy:before{background:#1f3fbf}.ps-c.lv-medium:before{background:#f2b705}
.ps-n{position:absolute;right:10px;top:-6px;font-size:2.8rem;font-weight:800;color:transparent;-webkit-text-stroke:2px #e1d8c4;line-height:1}
.ps-top{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:7px;padding-right:50px}
.psheet .badge{border-color:#141414;background:#fffdf7;color:#141414;font-size:.62rem}
.psheet .b-id{background:#141414;color:#fff}
.ps-paper{background:#f2b705!important}
.ps-ch{border-style:dashed!important}
.psheet .body{font-size:.9rem;line-height:1.55;color:#141414}
.psheet .body *{color:inherit}
.psheet .body ul,.psheet .body ol{margin:.3em 0}
.psheet .body li{padding:2px 10px;margin:1px 0;border:0;background:none!important;cursor:default}
.psheet .body p{margin:.3em 0}
.psheet img.fig{display:block;max-width:100%;max-height:75mm;margin:6px auto;background:#fff}
.ps-w{margin-top:8px;border:2px solid #141414;background-color:#fffefb;background-image:linear-gradient(rgba(20,20,20,.10) 1px,transparent 1px),linear-gradient(90deg,rgba(20,20,20,.10) 1px,transparent 1px);background-size:6mm 6mm}
.ps-ft{display:flex;gap:12px;align-items:center;margin-top:8px;padding-top:10px;border-top:3px solid #141414;font-size:.74rem;break-inside:avoid}
.ps-ft svg{width:20mm;height:20mm;flex:none}
.ps-ft span{color:#6b6457}
@page{size:A4;margin:12mm 11mm;@bottom-center{content:"หน้า " counter(page) " / " counter(pages);font:700 9pt "Anuphan",sans-serif;color:#6b6457}}
@media print{
  body.printing{background:#fff!important;overflow:visible!important;position:static!important;top:auto!important;left:auto!important;right:auto!important;width:auto!important;height:auto!important}
  body.printing>*:not(#psheet){display:none!important}
  body.printing #psheet{display:block!important;position:static!important;overflow:visible!important;background:#fff!important;padding:0!important}
  body.printing .psbar{display:none!important}
  body.printing .pspage{max-width:none;margin:0;padding:0}
  .psheet *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
"""

MARKUP = r"""
<button class="cartfab" id="cartfab" hidden title="ตะกร้าแบบฝึกหัด">🛒 <b id="cartn">0</b></button>
<div class="ctoast" id="ctoast" role="status"></div>
<div class="cartwrap" id="cartwrap"><div class="cartpanel" role="dialog" aria-label="ตะกร้าแบบฝึกหัด">
  <div class="cphead"><b>🛒 ตะกร้าแบบฝึกหัด</b><button class="x" id="cpx" aria-label="ปิด">✕</button></div>
  <label class="cpt">หัวข้อ <input id="cptitle" autocomplete="off"></label>
  <div class="cprow"><button id="cpsort">ง่าย → ยาก</button><button id="cpshuf">สุ่ม</button>
    <span class="cpws" id="cpws">ที่ทด <button data-v="0">ไม่มี</button><button data-v="22">เล็ก</button><button data-v="38">กลาง</button><button data-v="60">ใหญ่</button></span></div>
  <ol class="cplist" id="cplist"></ol>
  <div class="cpgo"><button class="cpprint" id="cpprint">🖨 พิมพ์ / PDF</button><button id="cplink">🔗 ลิงก์ให้นักเรียน</button></div>
  <div class="cpkeep" id="cpkeep"><span class="lb" id="cpkl">เก็บตะกร้านี้</span>
    <input id="cpname" placeholder="ชื่อชุด หรือ ชื่อนักเรียน" list="cpnames" autocomplete="off"><datalist id="cpnames"></datalist>
    <button id="cpsave">💾 บันทึกเป็นชุด</button><button id="cpgive">👤 ให้นักเรียนคนนี้</button><button id="cpclear">🗑 ล้างตะกร้า</button></div>
  <div class="cpsets" id="cpsets"></div>
</div></div>
<div class="psheet" id="psheet"></div>
"""

JS = r"""
/* ===== 🛒 swipe-to-cart -> A4 แบบฝึกหัด (tools/cart_part.py) ===== */
const CART=(()=>{
  const K="cqb_cart",KS="cqb_sets",KG="cqb_given",KW="cqb_cart_ws";
  const J=(k,d)=>{try{const v=JSON.parse(ls.get(k,"null"));return v==null?d:v;}catch(_){return d;}};
  const W=(k,v)=>ls.set(k,JSON.stringify(v));
  const BY=new Map(DATA.questions.map(q=>[q.id,q]));
  let cart=J(K,{t:"",ids:[]});cart.ids=(cart.ids||[]).filter(id=>BY.has(id));
  let ws=parseInt(ls.get(KW,"38"),10);if(isNaN(ws))ws=38;
  const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const has=id=>cart.ids.includes(id);
  const save=()=>{W(K,cart);sync();};
  const given=()=>J(KG,{});
  const givenTo=id=>{const g=given();return Object.keys(g).filter(n=>(g[n]||[]).includes(id));};
  let tt=0;function toast(m){const t=$("#ctoast");t.textContent=m;t.classList.add("show");clearTimeout(tt);tt=setTimeout(()=>t.classList.remove("show"),2200);}
  const snd=on=>{try{SFX.play("chip",on);}catch(_){}};
  function fly(el){const f=$("#cartfab");if(!el||!f)return;const a=el.getBoundingClientRect(),b=f.getBoundingClientRect(),d=document.createElement("div");
    d.className="cfly";d.textContent="🛒";d.style.left=(a.left+a.width/2-11)+"px";d.style.top=(a.top+Math.min(a.height/2,160)-11)+"px";document.body.appendChild(d);
    requestAnimationFrame(()=>{d.style.transform=`translate(${b.left+b.width/2-(a.left+a.width/2)}px,${b.top+b.height/2-(a.top+Math.min(a.height/2,160))}px) scale(.6)`;d.style.opacity=".2";});
    setTimeout(()=>{d.remove();f.classList.remove("bump");void f.offsetWidth;f.classList.add("bump");},560);}
  function add(id,el){if(!BY.has(id))return;
    if(has(id)){toast("ข้อนี้อยู่ในตะกร้าแล้ว");return;}
    cart.ids.push(id);save();snd(true);fly(el);
    const g=givenTo(id);toast(g.length?`ใส่ตะกร้าแล้ว · ⚠ เคยให้ ${g.join(", ")} แล้ว`:`ใส่ตะกร้าแล้ว (${cart.ids.length} ข้อ)`);}
  function remove(id){cart.ids=cart.ids.filter(x=>x!==id);save();snd(false);}
  /* chips + labels */
  const paperTxt=q=>isEx(q)?"แบบฝึกหัด":((DATA.exams[q.exam]||{label:q.exam.toUpperCase()}).label+" "+(q.year||"")).trim();
  const chTxt=q=>q.subject==="bio"?`ชีววิทยา ${q.bio}. ${q.chName}`:q.subject==="applied"?`ประยุกต์ · ${q.chName}`:`บท ${parseInt(q.ch)} ${q.chName}`;
  function autoTitle(){const qs=cart.ids.map(id=>BY.get(id));const s=new Set(qs.map(q=>q.chName));return s.size===1?[...s][0]:"แบบฝึกหัดรวม";}
  const title=()=>(cart.t||"").trim()||autoTitle();
  /* ---- the sheet ---- */
  function sheetHtml(ids,t,w,link){const qs=ids.map(id=>BY.get(id)).filter(Boolean),n=qs.length;
    const cards=qs.map((q,i)=>`<div class="ps-c lv-${q.diff||"medium"}"><div class="ps-n">${i+1}</div>
      <div class="ps-top">${idBadge(q)}<span class="badge ps-paper">${esc(paperTxt(q))}</span><span class="badge ps-ch">${esc(chTxt(q))}</span>${diffBadge(q)}</div>
      <div class="body">${q.bodyHtml.replace(/\bokopt\b/g,"")}${q.figure?`<img class="fig" src="${q.figure}" alt="">`:""}</div>
      ${w>0?`<div class="ps-w" style="height:${w}mm"></div>`:""}</div>`).join("");
    return `<div class="psbar">แบบฝึกหัด · ${n} ข้อ<button id="psprint">🖨 พิมพ์</button></div><div class="pspage">
      <header class="ps-hd"><div><div class="ps-k">แบบฝึกหัด</div><h1>${esc(t)}</h1></div>
      <div class="ps-f"><div>ชื่อ <span></span></div><div>วันที่ <span></span></div></div>
      <div class="ps-sc"><div>คะแนน · ${n} ข้อ</div><b>&nbsp;&nbsp;&nbsp;/ ${n}</b></div></header>
      ${cards}${link?`<div class="ps-ft" id="psft"><div><b>สแกนเพื่อทำออนไลน์บนมือถือ</b><br><span>chem-exam-bank.vercel.app · ${n} ข้อ</span></div></div>`:""}</div>`;}
  function linkFor(ids,t){return location.origin+location.pathname+"#sheet="+ids.map(encodeURIComponent).join(",")+"&t="+encodeURIComponent(t);}
  let qrLib=null;function qr(){return qrLib||(qrLib=new Promise(res=>{if(window.qrcode)return res(window.qrcode);const s=document.createElement("script");
    s.src="https://cdn.jsdelivr.net/npm/qrcode-generator@1.4.4/qrcode.min.js";s.onload=()=>res(window.qrcode||null);s.onerror=()=>res(null);document.head.appendChild(s);setTimeout(()=>res(window.qrcode||null),4000);}));}
  async function fill(ids,t,w,withLink){const ps=$("#psheet"),link=withLink?linkFor(ids,t):"";ps.innerHTML=sheetHtml(ids,t,w,link);tex(ps);
    if(link){const Q=await qr();const ft=$("#psft");if(Q&&ft){try{const c=Q(0,"M");c.addData(link);c.make();ft.insertAdjacentHTML("afterbegin",c.createSvgTag({cellSize:2,margin:0,scalable:true}));}catch(_){}}}
    await Promise.all([...ps.querySelectorAll("img")].map(i=>i.complete?0:new Promise(r=>{i.onload=i.onerror=r;setTimeout(r,5000);})));
    const p=$("#psprint");if(p)p.onclick=()=>doPrint(false);}
  let printed=false;
  function doPrint(nudge){document.body.classList.add("printing");printed=nudge;
    if(document.fonts&&document.fonts.ready)document.fonts.ready.then(()=>window.print());else window.print();}
  addEventListener("afterprint",()=>{document.body.classList.remove("printing");
    if(printed){printed=false;const k=$("#cpkeep");k.classList.add("nudge");$("#cpkl").textContent="พิมพ์แล้ว — เก็บตะกร้านี้ไว้ยังไง?";}});
  /* ---- panel ---- */
  function names(){const s=new Set([...J(KS,[]).map(x=>x.n),...Object.keys(given())]);$("#cpnames").innerHTML=[...s].map(n=>`<option value="${esc(n)}">`).join("");}
  function list(){const L=$("#cplist");
    if(!cart.ids.length){L.innerHTML=`<li class="cpempty">ยังว่าง — ปัดโจทย์ไปด้านข้าง หรือกด 🛒 ที่โจทย์</li>`;return;}
    L.innerHTML=cart.ids.map(id=>{const q=BY.get(id),g=givenTo(id);return `<li class="cpi" data-id="${esc(id)}"><span class="cph" title="ลากเพื่อเรียง">⋮⋮</span>
      <span class="badge b-id">${esc(id)}</span><i class="cpdot d-${q.diff}"></i><span class="cps">${q.snippet||""}</span>
      ${g.length?`<span class="cpg">ให้ ${esc(g.join(", "))} แล้ว</span>`:""}<button class="cpdel" title="เอาออก" aria-label="เอาออก">✕</button></li>`;}).join("");}
  function sets(){const S=J(KS,[]);$("#cpsets").innerHTML=S.length?`<h4>ชุดที่บันทึกไว้</h4>`+S.map((s,i)=>`<div class="cpset"><span><b>${esc(s.n)}</b> · ${s.ids.length} ข้อ</span>
      <button data-open="${i}">เปิด</button><button data-del="${i}">ลบ</button></div>`).join(""):"";}
  function wsBtns(){$("#cpws").querySelectorAll("button").forEach(b=>b.classList.toggle("on",+b.dataset.v===ws));}
  function panel(){$("#cptitle").value=cart.t||"";$("#cptitle").placeholder=autoTitle();list();sets();names();wsBtns();}
  function open(){panel();$("#cpkeep").classList.remove("nudge");$("#cpkl").textContent="เก็บตะกร้านี้";$("#cartwrap").classList.add("show");try{SL.lock("cart");}catch(_){}}
  function close(){$("#cartwrap").classList.remove("show");try{SL.unlock("cart");}catch(_){}}
  /* ---- marks on the questions ---- */
  function mark(){document.querySelectorAll(".cartadd").forEach(b=>{const on=has(b.dataset.id);b.classList.toggle("on",on);const tx=on?"🛒 ✓":"🛒";if(b.textContent!==tx)b.textContent=tx;
      const c=b.closest(".poster,.card,.row");if(c)c.classList.toggle("incart",on);});
    const m=$("#mcart");if(m&&typeof mIdx!=="undefined"&&filtered[mIdx]){m.classList.toggle("on",has(filtered[mIdx].id));}}
  function sync(){const n=cart.ids.length;$("#cartn").textContent=n;$("#cartfab").hidden=!n||document.body.classList.contains("sheetview");mark();
    if($("#cartwrap").classList.contains("show"))panel();}
  /* ---- swipe a question sideways (one finger; Pencil never) ---- */
  function swiper(root,sel,onGo,TH){let s=null;
    root.addEventListener("touchstart",e=>{s=null;if(e.touches.length!==1)return;const t=e.touches[0];if(t.touchType==="stylus")return;
      const c=e.target.closest(sel);if(!c||e.target.closest("button,a,input,select,textarea,.v3d,canvas,.cph"))return;
      for(let el=e.target;el&&el!==c;el=el.parentElement)if(el.scrollWidth>el.clientWidth+1&&/auto|scroll/.test(getComputedStyle(el).overflowX))return;
      s={c,x:t.clientX,y:t.clientY,on:false};},{passive:true});
    root.addEventListener("touchmove",e=>{if(!s)return;if(e.touches.length!==1){s=null;return;}const t=e.touches[0],dx=t.clientX-s.x,dy=t.clientY-s.y;
      if(!s.on){if(Math.abs(dy)>12&&Math.abs(dy)>Math.abs(dx)){s=null;return;}if(Math.abs(dx)>12&&Math.abs(dx)>Math.abs(dy)*1.3){s.on=true;s.c.style.transition="none";}else return;}
      if(e.cancelable)e.preventDefault();s.dx=dx;s.c.style.transform=`translateX(${dx*.6}px) rotate(${dx*.01}deg)`;s.c.classList.toggle("cartarm",Math.abs(dx)>=TH);},{passive:false});
    const end=()=>{if(!s||!s.on){s=null;return;}const c=s.c,go=Math.abs(s.dx||0)>=TH,dx=s.dx||0;s=null;c.classList.remove("cartarm");
      c.style.transition="transform .25s ease-out";c.style.transform="";setTimeout(()=>{c.style.transition="";},260);if(go)onGo(c,dx);};
    root.addEventListener("touchend",end);root.addEventListener("touchcancel",end);}
  function boot(){
    document.body.insertAdjacentHTML("beforeend",`__MARKUP__`);
    swiper($("#root"),".poster,.card,.row",c=>{const b=c.querySelector(".cartadd");if(b)add(b.dataset.id,c);},90);
    swiper($("#cplist"),".cpi",(c,dx)=>{c.style.transform=`translateX(${dx>0?110:-110}%)`;c.classList.add("gone");setTimeout(()=>{remove(c.dataset.id);toast("เอาออกจากตะกร้าแล้ว");},200);},80);
    document.addEventListener("click",e=>{const b=e.target.closest(".cartadd");if(!b)return;e.stopPropagation();
      if(has(b.dataset.id)){toast("ข้อนี้อยู่ในตะกร้าแล้ว — เอาออกได้ในตะกร้า 🛒");return;}add(b.dataset.id,b.closest(".poster,.card,.row")||b);},true);
    $("#mcart").onclick=()=>{const q=filtered[mIdx];if(q)add(q.id,$("#modal .sheet"));};
    $("#cartfab").onclick=open;$("#cpx").onclick=close;$("#cartwrap").addEventListener("click",e=>{if(e.target.id==="cartwrap")close();});
    $("#cptitle").oninput=e=>{cart.t=e.target.value;W(K,cart);};
    $("#cpsort").onclick=()=>{const o={easy:0,medium:1,hard:2};cart.ids.sort((a,b)=>(o[BY.get(a).diff]??1)-(o[BY.get(b).diff]??1));save();toast("เรียงง่าย → ยากแล้ว");};
    $("#cpshuf").onclick=()=>{const a=cart.ids;for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}save();toast("สุ่มลำดับแล้ว");};
    $("#cpws").onclick=e=>{const b=e.target.closest("button");if(!b)return;ws=+b.dataset.v;ls.set(KW,String(ws));wsBtns();};
    $("#cplist").addEventListener("click",e=>{const d=e.target.closest(".cpdel");if(!d)return;const li=d.closest(".cpi");li.classList.add("gone");setTimeout(()=>remove(li.dataset.id),200);});
    /* drag ⋮⋮ to reorder */
    $("#cplist").addEventListener("pointerdown",e=>{const h=e.target.closest(".cph");if(!h)return;e.preventDefault();const li=h.closest(".cpi"),L=$("#cplist");
      li.classList.add("drag");try{h.setPointerCapture(e.pointerId);}catch(_){}let y0=e.clientY;
      const mv=ev=>{li.style.transform=`translateY(${ev.clientY-y0}px)`;const r=li.getBoundingClientRect(),mid=r.top+r.height/2;
        const p=li.previousElementSibling,n=li.nextElementSibling;
        if(p&&mid<p.getBoundingClientRect().top+p.offsetHeight/2){L.insertBefore(li,p);y0-=p.offsetHeight+6;li.style.transform=`translateY(${ev.clientY-y0}px)`;}
        else if(n&&mid>n.getBoundingClientRect().top+n.offsetHeight/2){L.insertBefore(n,li);y0+=n.offsetHeight+6;li.style.transform=`translateY(${ev.clientY-y0}px)`;}};
      const up=()=>{h.removeEventListener("pointermove",mv);h.removeEventListener("pointerup",up);h.removeEventListener("pointercancel",up);
        li.classList.remove("drag");li.style.transform="";cart.ids=[...L.querySelectorAll(".cpi")].map(x=>x.dataset.id);save();};
      h.addEventListener("pointermove",mv);h.addEventListener("pointerup",up);h.addEventListener("pointercancel",up);});
    $("#cpprint").onclick=async()=>{if(!cart.ids.length){toast("ตะกร้ายังว่าง");return;}await fill(cart.ids,title(),ws,true);doPrint(true);};
    $("#cplink").onclick=async()=>{if(!cart.ids.length){toast("ตะกร้ายังว่าง");return;}const u=linkFor(cart.ids,title());
      try{if(navigator.share&&matchMedia("(pointer:coarse)").matches){await navigator.share({title:title(),url:u});return;}}catch(_){return;}
      try{await navigator.clipboard.writeText(u);toast("คัดลอกลิงก์แล้ว — ส่งให้นักเรียนได้เลย");}catch(_){prompt("คัดลอกลิงก์นี้",u);}};
    const nm=()=>{const n=$("#cpname").value.trim();if(!n){toast("ใส่ชื่อก่อน");$("#cpname").focus();}return n;};
    $("#cpsave").onclick=()=>{const n=nm();if(!n||!cart.ids.length)return;const S=J(KS,[]).filter(x=>x.n!==n);S.unshift({n,t:title(),ids:[...cart.ids],w:ws,d:Date.now()});W(KS,S);sets();names();toast(`บันทึกชุด “${n}” แล้ว`);};
    $("#cpgive").onclick=()=>{const n=nm();if(!n||!cart.ids.length)return;const g=given();g[n]=[...new Set([...(g[n]||[]),...cart.ids])];W(KG,g);list();names();toast(`บันทึกว่าให้ ${n} แล้ว ${cart.ids.length} ข้อ`);};
    $("#cpclear").onclick=()=>{if(!cart.ids.length)return;if(!confirm(`ล้างตะกร้า ${cart.ids.length} ข้อ?`))return;cart={t:"",ids:[]};save();close();toast("ล้างตะกร้าแล้ว");};
    $("#cpsets").onclick=e=>{const S=J(KS,[]),o=e.target.dataset.open,d=e.target.dataset.del;
      if(o!=null){const s=S[+o];if(!s)return;cart={t:s.t||"",ids:s.ids.filter(id=>BY.has(id))};if(s.w!=null){ws=s.w;ls.set(KW,String(ws));}save();$("#cpname").value=s.n;toast(`เปิดชุด “${s.n}” แล้ว`);}
      if(d!=null){const s=S[+d];if(!s||!confirm(`ลบชุด “${s.n}”?`))return;S.splice(+d,1);W(KS,S);sets();names();}};
    addEventListener("keydown",e=>{if((e.key!=="c"&&e.key!=="C")||e.metaKey||e.ctrlKey||e.altKey||e.target.closest("input,textarea,select,[contenteditable]"))return;
      let q=null;if($("#modal").classList.contains("show"))q=filtered[mIdx];else if(view==="poster"&&document.body.classList.contains("inapp"))q=filtered[pIdx];
      if(q){e.preventDefault();add(q.id,$("#modal").classList.contains("show")?$("#modal .sheet"):$("#deck .poster"));}});
    new MutationObserver(mark).observe($("#root"),{childList:true,subtree:true});
    new MutationObserver(mark).observe($("#mtop"),{childList:true});
    /* a student's link: #sheet=Q-0113,Q-0192&t=... -> the sheet on screen, no answers */
    const m=location.hash.match(/^#sheet=([^&]*)(?:&t=(.*))?$/);
    if(m){const ids=m[1].split(",").map(decodeURIComponent).filter(id=>BY.has(id));
      if(ids.length){document.body.classList.add("sheetview");fill(ids,m[2]?decodeURIComponent(m[2]):"แบบฝึกหัด",0,false);}}
    sync();}
  return {boot,add,has};
})();
CART.boot();
"""


def apply(html):
    """Wire the cart into the main index.html template (never the student builds)."""
    def rep(old, new):
        nonlocal html
        assert html.count(old) == 1, ("cart_part anchor not unique/missing", old[:60])
        html = html.replace(old, new)
    rep("</style></head><body>", CSS + "</style></head><body>")
    rep("function footHtml(q){return `📄 ${q.source}`;}",
        "function footHtml(q){return `📄 ${q.source}<button class=\"cartadd\" data-id=\"${q.id}\" title=\"ใส่ตะกร้า (C)\">🛒</button>`;}")
    rep('<button class="x shotx" id="mshot"',
        '<button class="x" id="mcart" title="ใส่ตะกร้า (C)" aria-label="ใส่ตะกร้า">🛒</button><button class="x shotx" id="mshot"')
    rep("</script></body></html>", JS.replace("__MARKUP__", MARKUP.replace("`", "\\`")) + "</script></body></html>")
    return html
