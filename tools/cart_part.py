# -*- coding: utf-8 -*-
import os
"""🛒 cart -> A4 แบบฝึกหัด (Prat's spec 2026-11-11; v2 redesign same day: drug-webapp ribbon, mouse drag, ribbon tap removes).
Drag / swipe a question SIDEWAYS (mouse or finger; Pencil never) -> it goes into a per-device cart (localStorage) and a red
ribbon bookmark slides out of the card's top edge (forked from drug-webapp v2's dock pin). Tap the ribbon -> it slides back
up and the question leaves the cart. Keyboard: C toggles the open / current question. Present mode: the bookmark button.
Right-edge tab -> the cart drawer: title, easy->hard, shuffle, drag ⋮⋮ to reorder, drag an item sideways out, workspace size,
print -> one-column A4 sheet (header name/date/score-with-count, paper + chapter chips, page numbers, NO answers, QR),
link for a student (#sheet=...), save as named set, mark as given to a student (warns on re-add), clear.
Main site only: apply(HTML) is called for index.html, never for the student builds."""

CSS = r"""
/* ===== 🛒 cart (tools/cart_part.py) ===== */
/* the ribbon: forked from drug-webapp v2 .pin (2026-09-27). Nothing shows on a question that isn't carted; carted, a red
   ribbon slides down out of the card's top edge and hangs there, swaying to rest. The button clips it at the card's edge. */
.cpin{position:absolute;z-index:4;top:-3px;right:16px;width:44px;height:56px;padding:0;border:0;background:none;overflow:hidden;opacity:0;pointer-events:none;cursor:pointer}
.cpin .rb{position:absolute;left:10px;top:0;width:24px;height:48px;transform:translateY(-105%);transform-origin:50% 0;filter:drop-shadow(2px 2px 0 rgba(0,0,0,.28))}
.cpin .rb i{display:block;width:100%;height:100%;background:linear-gradient(90deg,rgba(0,0,0,.14),transparent 30%,transparent 70%,rgba(0,0,0,.14)),var(--red);clip-path:polygon(0 0,100% 0,100% 100%,50% 78%,0 100%)}
body.dark .cpin .rb{filter:drop-shadow(2px 2px 0 rgba(0,0,0,.6))}
.cpin.done{opacity:1;pointer-events:auto}.cpin.done .rb{transform:none}
.cpin:focus-visible{opacity:1;pointer-events:auto;outline:3px solid var(--yel);outline-offset:-3px}
.cpin:not(.done):focus-visible .rb{transform:none;opacity:.35}
.cpin.pop .rb{animation:cribIn .6s cubic-bezier(.3,.7,.4,1) .12s both}
.cpin.unpop .rb{animation:cribOut .3s cubic-bezier(.5,0,.9,.5) both}
@keyframes cribIn{0%{transform:translateY(-105%)}55%{transform:translateY(7%)}70%{transform:translateY(-3%) rotate(4deg)}84%{transform:translateY(1%) rotate(-2.5deg)}100%{transform:none}}
@keyframes cribOut{0%{transform:none}25%{transform:translateY(5%)}100%{transform:translateY(-105%)}}
/* the ribbon takes the corner: the ghost number steps aside (card: fades, poster: slides left) so the two never stack */
.card>.cnum{transition:opacity .25s}.card.incart>.cnum{opacity:0}
.poster>.pnum{transition:transform .35s cubic-bezier(.3,1.2,.5,1)}.poster.incart>.pnum{transform:translateX(-52px)}
.poster>.cpin{right:22px;height:70px}.poster>.cpin .rb{left:8px;width:28px;height:60px}
.row{position:relative}
.row>.cpin{height:38px;right:8px;width:36px}.row>.cpin .rb{left:9px;width:18px;height:31px}
.row.incart .row-h{padding-right:50px}
/* the drag: the question follows the pointer sideways, past the line it arms (dashed yellow), release = into the cart */
.poster,.card,.row{touch-action:pan-y pinch-zoom}
.cdrag{position:relative;z-index:5;transition:none!important;will-change:transform}
.carmed{outline:3px dashed var(--yel);outline-offset:4px}
html.cdragging,html.cdragging *{user-select:none!important;-webkit-user-select:none!important;cursor:grabbing!important}
/* the right-edge tab: the left tool tabs (#pdtab ...) mirrored */
#carttab{position:fixed;right:0;top:calc(50% - 58px);z-index:45;writing-mode:vertical-rl;background:var(--yel);color:#141414;border:3px solid var(--ink);border-right:0;padding:14px 8px;font:800 .9rem "Anuphan",sans-serif;box-shadow:-4px 4px 0 var(--sh);display:none;align-items:center;gap:9px;cursor:pointer;transition:transform .2s}
#carttab b{font:800 .82rem "JetBrains Mono",monospace;writing-mode:horizontal-tb;background:#141414;color:#f2b705;min-width:24px;text-align:center;padding:3px 4px}
#carttab:hover{transform:translateX(-4px)}
body.hascart #carttab{display:flex}
body.cartopen #carttab,body.sheetview #carttab{visibility:hidden}
#carttab.bump{animation:cbump .45s cubic-bezier(.3,1.6,.5,1)}
@keyframes cbump{40%{transform:translateX(-10px) scale(1.08)}}
@media(max-width:560px){#carttab{padding:12px 5px;font-size:.84rem}}
/* toast */
.ctoast{position:fixed;left:50%;bottom:calc(22px + env(safe-area-inset-bottom,0px));transform:translateX(-50%) translateY(16px);z-index:95;display:flex;align-items:center;gap:12px;
  background:#141414;color:#efe9dc;border:3px solid #141414;border-left:10px solid var(--yel);box-shadow:5px 5px 0 var(--yel);padding:10px 14px;font:700 .88rem "Anuphan",sans-serif;
  opacity:0;pointer-events:none;transition:opacity .2s,transform .25s cubic-bezier(.3,1.4,.5,1);max-width:min(92vw,520px)}
body.dark .ctoast{border-color:#e8e2d4;border-left-color:var(--yel)}
body.cartopen .ctoast{left:auto;right:21px;bottom:calc(96px + env(safe-area-inset-bottom,0px));transform:translateY(16px);max-width:min(438px,calc(100vw - 42px))}
body.cartopen .ctoast.show{transform:none}
.ctoast.show{opacity:1;transform:translateX(-50%);pointer-events:auto}
.ctoast.warn{border-left-color:var(--red);box-shadow:5px 5px 0 var(--red)}
body.dark .ctoast.warn{border-left-color:var(--red)}
.ctoast button{font:800 .8rem "Anuphan",sans-serif;background:var(--yel);color:#141414;border:2px solid #efe9dc;padding:4px 10px;cursor:pointer;white-space:nowrap}
/* the drawer: the site's own drawer (#pd) mirrored to the right edge */
.cartwrap{position:fixed;inset:0;z-index:72;background:rgba(20,20,20,.35);opacity:0;visibility:hidden;transition:opacity .35s,visibility 0s .35s}
body.cartopen .cartwrap{opacity:1;visibility:visible;transition:opacity .35s}
.cartpanel{position:absolute;right:0;top:0;bottom:0;width:min(480px,100vw);background:var(--paper);color:var(--ink);border-left:4px solid var(--ink);box-shadow:-10px 0 0 var(--sh);
  display:flex;flex-direction:column;font-family:"Anuphan",sans-serif;transform:translateX(calc(100% + 20px));transition:transform .5s cubic-bezier(.34,1.25,.64,1)}
body.cartopen .cartpanel{transform:none}
.cartpanel button{font-family:inherit;color:var(--ink);cursor:pointer}
.cphead{flex:none;display:flex;align-items:center;gap:10px;padding:14px 16px 12px 18px;border-bottom:3px solid var(--ink)}
.cphead .cprb{flex:none;width:16px;height:30px;margin-top:-14px;align-self:flex-start;background:var(--red);clip-path:polygon(0 0,100% 0,100% 100%,50% 78%,0 100%)}
.cphead h3{margin:0;font-size:1.3rem;font-weight:800;line-height:1.2}
.cphead .n{font:800 .78rem "JetBrains Mono","Anuphan",monospace;background:var(--yel);color:#141414;border:2px solid var(--ink);padding:1px 8px;white-space:nowrap}
.cphead .cpx{margin-left:auto;flex:none;width:42px;height:42px;border:3px solid var(--ink);background:var(--ink);color:var(--paper);font-size:1.1rem;font-weight:800;display:grid;place-items:center}
.cphead .cpx:hover{background:var(--red);color:#fff}
.cpscroll{flex:1;overflow-y:auto;padding:16px 22px 22px 18px;display:flex;flex-direction:column;gap:18px;overscroll-behavior:contain}
.cpsec{display:flex;flex-direction:column;gap:9px}
.cplab{font:800 .68rem "JetBrains Mono","Anuphan",monospace;letter-spacing:.06em;color:var(--mut);margin:0}
/* the title: the filter bar's labelled box (.fsel) */
.cpfield{display:flex;flex-direction:column;border:2px solid var(--ink);background:var(--card);cursor:text}
.cpfield>span{font:600 .62rem "JetBrains Mono","Anuphan",monospace;letter-spacing:.04em;color:var(--mut);padding:5px 11px 0}
.cpfield:focus-within{outline:3px solid var(--yel);outline-offset:1px}
.cptitle{width:100%;font:800 1.12rem "Anuphan",sans-serif;color:var(--ink);background:none;border:0;padding:0 11px 7px;outline:0;border-radius:0;min-width:0}
.cptitle::placeholder{color:var(--mut);opacity:.7}
.cpopt{display:flex;align-items:center;justify-content:space-between;gap:8px 10px;flex-wrap:wrap}
.cartpanel .seg button{min-height:34px;padding:5px 12px}
.cartpanel .seg button.on{color:var(--paper)}
.cplh{display:flex;align-items:center;gap:6px;border-bottom:3px solid var(--ink);padding-bottom:7px}
.cplh .cplab{margin-right:auto;font:800 .92rem "Anuphan",sans-serif;color:var(--ink);letter-spacing:0}
.cpmini{font-size:.76rem;font-weight:800;border:2px solid var(--ink);background:var(--card);padding:4px 9px;white-space:nowrap}
.cpmini:hover{background:var(--yel);color:#141414}
.cpmini.quiet{border-color:transparent;background:none;color:var(--mut);text-decoration:underline dotted;padding:4px 4px}
.cpmini.quiet:hover{background:none;color:var(--red)}
.cplist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:9px}
.cpi{position:relative;display:grid;grid-template-columns:44px minmax(0,1fr) 40px;background:var(--card);border:2px solid var(--ink);box-shadow:3px 3px 0 var(--sh);touch-action:pan-y}
.cpi.lift{z-index:3;box-shadow:7px 7px 0 var(--sh);transition:none}
.cph{grid-column:1;grid-row:1/3;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;background:var(--red);color:#fff;border-right:2px solid var(--ink);cursor:grab;touch-action:none;user-select:none;-webkit-user-select:none}
.cpi.d-easy .cph{background:var(--blue)}.cpi.d-medium .cph{background:var(--yel);color:#141414}
.cph:active{cursor:grabbing}
.cpno{font:800 1.02rem "JetBrains Mono",monospace;line-height:1.1}
.cph i{font:800 .72rem "JetBrains Mono",monospace;font-style:normal;letter-spacing:1px;opacity:.65;line-height:1}
.cpmeta{grid-column:2;grid-row:1;display:flex;flex-wrap:wrap;align-items:center;gap:5px;padding:8px 0 0 11px}
.cpmeta .badge{font-size:.62rem;padding:1px 6px}
.cpi .ps-paper{background:var(--yel);color:#141414}
.cps{grid-column:2;grid-row:2;font-size:.82rem;line-height:1.5;color:var(--ink);opacity:.85;margin:4px 0 9px 11px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;align-self:start}
.cpg{font:800 .64rem "Anuphan",sans-serif;color:#fff;background:var(--red);padding:2px 6px}
.cpdel{grid-column:3;grid-row:1/3;border:0;background:none;color:var(--mut)!important;font-size:.95rem;font-weight:800;display:grid;place-items:center}
.cpdel:hover{background:var(--red);color:#fff!important}
.cpempty{display:flex;flex-direction:column;align-items:center;gap:8px;text-align:center;padding:0 14px 28px;border:3px dashed var(--mut);color:var(--mut);font-size:.9rem;line-height:1.7}
.cpempty b{color:var(--ink);font-size:1rem}
.cpempty .rbdemo{width:20px;height:36px;margin-bottom:6px;background:var(--red);clip-path:polygon(0 0,100% 0,100% 100%,50% 78%,0 100%)}
.cpkeep{border:2px solid var(--ink);background:var(--card);padding:11px 12px 12px;display:flex;flex-direction:column;gap:9px}
.cpkeep.nudge{border-color:var(--red);box-shadow:5px 5px 0 var(--red)}
.cpkeep.nudge>.cplab{color:var(--red)}
.cpkeep .row2{display:flex;gap:7px;flex-wrap:wrap}
.cpkeep input{flex:1 1 130px;min-width:0;font:700 .88rem "Anuphan",sans-serif;border:2px solid var(--ink);background:var(--paper);color:var(--ink);padding:7px 10px;border-radius:0}
.cpkeep input:focus{outline:3px solid var(--yel);outline-offset:1px}
.cpbtn{font-size:.8rem;font-weight:800;border:2px solid var(--ink);background:var(--card);padding:7px 11px;box-shadow:3px 3px 0 var(--sh);white-space:nowrap;transition:transform .08s,box-shadow .08s}
.cpbtn:hover{background:var(--yel);color:#141414}
.cpbtn:active{transform:translate(2px,2px);box-shadow:1px 1px 0 var(--sh)}
.cpsets{display:flex;flex-direction:column}
.cpsets:empty{display:none}
.cpsets .cplab{padding-top:9px;border-top:2px dashed var(--mut)}
.cpset{display:flex;align-items:center;gap:6px;padding:7px 0 0;font-size:.86rem}
.cpset span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.cpset small{color:var(--mut)}
.cpfoot{flex:none;display:flex;gap:12px;padding:14px 22px calc(16px + env(safe-area-inset-bottom,0px)) 18px;border-top:3px solid var(--ink);background:var(--paper)}
.cpprint,.cplink{font-weight:800;border:3px solid var(--ink);box-shadow:4px 4px 0 var(--sh);padding:11px 12px;transition:transform .08s,box-shadow .08s;min-height:50px}
.cpprint{flex:1.5;font-size:1.02rem;background:var(--yel);color:#141414!important}
.cplink{flex:1;font-size:.88rem;background:var(--card)}
.cplink:hover{background:var(--ink);color:var(--paper)}
.cpfoot button:active{transform:translate(3px,3px);box-shadow:1px 1px 0 var(--sh)}
.cartpanel button:disabled{opacity:.4;cursor:not-allowed;box-shadow:none;pointer-events:none}
@media(max-width:560px){
  .cphead{padding:10px 12px 9px 14px}.cphead h3{font-size:1.15rem}
  .cpscroll{padding:14px 18px 20px 14px;gap:16px}
  .cpkeep input{flex-basis:100%}.cpkeep .row2 .cpbtn{flex:1}
  .cpfoot{padding-left:14px;padding-right:18px;gap:10px}
  .cpprint,.cplink{padding:10px 6px}
}
/* present mode: a bookmark in the tools */
#mcart svg path{fill:none;transition:fill .2s}
#mcart.on svg path{fill:var(--red);stroke:var(--red)}
@media(prefers-reduced-motion:reduce){.cartpanel,.cartwrap,.ctoast,.poster>.pnum{transition:none}#carttab.bump{animation:none}}
/* the sheet itself (print, and the student link on screen) */
.psheet{display:none}
body.sheetview{overflow:hidden}
body.sheetview .psheet{display:block;position:fixed;inset:0;z-index:90;overflow-y:auto;background:#efe9dc;padding:0 0 40px}
.psbar{position:sticky;top:0;z-index:2;background:#141414;color:#efe9dc;display:flex;gap:10px;align-items:center;padding:10px 14px;border-bottom:5px solid #f2b705;font:700 .9rem "Anuphan",sans-serif}
.psbar button{margin-left:auto;font:800 .9rem "Anuphan",sans-serif;background:#f2b705;border:2px solid #efe9dc;padding:7px 14px;cursor:pointer}
.pspage{max-width:820px;margin:16px auto;padding:0 12px}
.psheet{color:#141414;font-family:"Anuphan","IBM Plex Sans Thai",system-ui,sans-serif}
.ps-hd{position:static;display:grid;grid-template-columns:1fr auto auto;gap:14px;align-items:stretch;border:3px solid #141414;box-shadow:6px 6px 0 #141414;padding:12px 14px;margin:0 6px 16px 0;background:#fffdf7;border-top:9px solid #e4412b}
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

.ps-hd.hasqr{grid-template-columns:1fr auto auto auto}
.ps-qr{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;width:24mm}
.ps-qr svg{width:20mm;height:20mm;display:block}
.ps-qr small{font:700 .55rem "Anuphan",sans-serif;color:#6b6457;white-space:nowrap}
.ps-qr:not(:has(svg)){display:none}
.ps-done{display:none}
@media screen{
/* ---- the student link, on screen ---- */
body.sheetview .psheet{background:#efe9dc}
body.sheetview .psbar{gap:12px;padding:10px 14px calc(10px) 16px}
.psbt{display:flex;flex-direction:column;min-width:0;flex:1;line-height:1.25}
.psbt small{font:800 .62rem "JetBrains Mono","Anuphan",monospace;letter-spacing:.1em;color:#f2b705}
.psbt b{font-size:1rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.psprog{font:800 .78rem "JetBrains Mono","Anuphan",monospace;background:#f2b705;color:#141414;padding:4px 9px;white-space:nowrap}
body.sheetview .psbar button{margin-left:0;background:none;color:#efe9dc;border:2px solid #efe9dc;padding:6px 12px;font-size:.82rem}
body.sheetview .ps-f,body.sheetview .ps-sc{display:none}
body.sheetview .ps-hd{grid-template-columns:1fr;margin-top:6px}
body.sheetview .ps-hd h1{font-size:1.7rem;line-height:1.25}
body.sheetview .ps-hd:after{content:"แตะตัวเลือกเพื่อเลือกคำตอบ แล้วกดคัดลอกคำตอบส่งครูท้ายหน้า";font:600 .8rem "Anuphan",sans-serif;color:#6b6457;margin-top:6px}
body.sheetview .psheet .ps-opts>li{padding:9px 12px;margin:6px 0;border:2px solid #d8cfbb;background:#fff;cursor:pointer;transition:background .15s,border-color .15s}
body.sheetview .psheet .ps-opts>li:hover{border-color:#141414}
body.sheetview .psheet .ps-opts>li.mk{background:#141414!important;color:#efe9dc;border-color:#141414}
body.sheetview .psheet .ps-opts>li.mk *{color:#efe9dc}
body.sheetview .ps-c.answered .ps-n{-webkit-text-stroke-color:#2f8f4e}
body.sheetview .ps-done{display:block;background:#fffdf7;border:3px solid #141414;box-shadow:5px 5px 0 #141414;padding:14px;margin:6px 6px 0 0}
.ps-dl{margin:0 0 8px;font-weight:800}
.ps-dr{display:flex;gap:8px;flex-wrap:wrap}
.ps-dr input{flex:1 1 160px;min-width:0;font:700 1rem "Anuphan",sans-serif;border:2px solid #141414;background:#efe9dc;padding:9px 10px;color:#141414}
.ps-dr button{font:800 .95rem "Anuphan",sans-serif;background:#f2b705;color:#141414;border:3px solid #141414;box-shadow:4px 4px 0 #141414;padding:9px 16px;cursor:pointer}
@media(max-width:600px){
  body.sheetview .pspage{padding:0 10px;margin-top:12px}
  body.sheetview .ps-hd{padding:12px;margin-right:4px;box-shadow:4px 4px 0 #141414}
  body.sheetview .ps-c{padding:12px 12px 12px 20px;margin-right:4px;box-shadow:4px 4px 0 #141414}
  body.sheetview .ps-n{font-size:2.2rem;right:8px}
  body.sheetview .ps-top{padding-right:36px}
  body.sheetview .psheet .body{font-size:.95rem}
  .psprog{font-size:.7rem;padding:3px 7px}
}
}
@page{size:A4;margin:12mm 11mm;@top-center{content:""}@bottom-center{content:"หน้า " counter(page) " / " counter(pages);font:700 9pt "Anuphan",sans-serif;color:#6b6457}}
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
<button id="carttab" aria-label="เปิดตะกร้าแบบฝึกหัด">ตะกร้า<b id="cartn">0</b></button>
<div class="ctoast" id="ctoast" role="status"><span id="ctmsg"></span><button id="ctact" hidden></button></div>
<div class="cartwrap" id="cartwrap"><aside class="cartpanel" role="dialog" aria-label="ตะกร้าแบบฝึกหัด">
  <div class="cphead"><i class="cprb"></i><h3>ตะกร้าแบบฝึกหัด</h3><span class="n" id="cphn">0 ข้อ</span><button class="cpx" id="cpx" aria-label="ปิด">✕</button></div>
  <div class="cpscroll">
    <div class="cpsec">
      <label class="cpfield"><span>หัวข้อชีต</span><input class="cptitle" id="cptitle" autocomplete="off"></label>
      <div class="cpopt"><p class="cplab">ที่ทดใต้แต่ละข้อ</p><span class="seg" id="cpws"><button data-v="0">ไม่มี</button><button data-v="22">น้อย</button><button data-v="38">กลาง</button><button data-v="60">มาก</button></span></div>
    </div>
    <div class="cpsec">
      <div class="cplh"><p class="cplab">โจทย์ในชีต</p><button class="cpmini" id="cpsort" title="เรียงจากง่ายไปยาก">ง่าย → ยาก</button><button class="cpmini" id="cpshuf" title="สลับลำดับแบบสุ่ม">สุ่มลำดับ</button><button class="cpmini quiet" id="cpclear">ล้าง</button></div>
      <ol class="cplist" id="cplist"></ol>
    </div>
    <div class="cpkeep" id="cpkeep"><p class="cplab" id="cpkl">เก็บตะกร้านี้</p>
      <div class="row2"><input id="cpname" placeholder="ชื่อชุด หรือ ชื่อนักเรียน" list="cpnames" autocomplete="off"><datalist id="cpnames"></datalist>
        <button class="cpbtn" id="cpsave" title="เก็บเป็นชุดไว้เปิดใช้ทีหลัง">บันทึกชุด</button><button class="cpbtn" id="cpgive" title="จำว่าให้ข้อพวกนี้กับนักเรียนคนนี้แล้ว">ให้นักเรียนแล้ว</button></div>
      <div class="cpsets" id="cpsets"></div>
    </div>
  </div>
  <div class="cpfoot"><button class="cpprint" id="cpprint">พิมพ์ / PDF</button><button class="cplink" id="cplink">ลิงก์ให้นักเรียน</button></div>
</aside></div>
<div class="psheet" id="psheet"></div>
"""

JS = r"""
/* ===== 🛒 cart -> A4 แบบฝึกหัด (tools/cart_part.py) ===== */
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
  const rm=()=>typeof RM!=="undefined"&&RM.matches;
  const snd=k=>{try{SFX.play(k);}catch(_){}};
  let tt=0;function toast(m,o){o=o||{};const t=$("#ctoast"),a=$("#ctact");$("#ctmsg").textContent=m;t.classList.toggle("warn",!!o.warn);
    a.hidden=!o.act;if(o.act){a.textContent=o.act;a.onclick=()=>{t.classList.remove("show");o.fn();};}
    t.classList.add("show");clearTimeout(tt);tt=setTimeout(()=>t.classList.remove("show"),o.act?4200:2400);}
  function bump(){const t=$("#carttab");t.classList.remove("bump");void t.offsetWidth;t.classList.add("bump");}
  function add(id){if(!BY.has(id))return false;if(has(id)){toast("ข้อนี้อยู่ในตะกร้าแล้ว — แตะริบบิ้นแดงเพื่อเอาออก");return false;}
    cart.ids.push(id);save();bump();const g=givenTo(id);
    toast(g.length?`ใส่ตะกร้าแล้ว · เคยให้ ${g.join(", ")} ไปแล้ว`:`ใส่ตะกร้าแล้ว · ${cart.ids.length} ข้อ`,{warn:g.length>0});return true;}
  function remove(id,undo){const at=cart.ids.indexOf(id);if(at<0)return;cart.ids.splice(at,1);save();snd("chip");
    if(undo)toast("เอาออกจากตะกร้าแล้ว",{act:"ย้อนกลับ",fn:()=>{if(!has(id)){cart.ids.splice(Math.min(at,cart.ids.length),0,id);save();}}});}
  const toggle=id=>has(id)?remove(id,true):add(id);
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
    return `<div class="psbar"><div class="psbt"><small>แบบฝึกหัด</small><b>${esc(t)}</b></div><span class="psprog" id="psprog">ตอบแล้ว 0/${n}</span><button id="psprint" aria-label="พิมพ์">พิมพ์</button></div><div class="pspage">
      <div class="ps-hd${link?" hasqr":""}"><div><div class="ps-k">แบบฝึกหัด</div><h1>${esc(t)}</h1></div>
      <div class="ps-f"><div>ชื่อ <span></span></div><div>วันที่ <span></span></div></div>
      <div class="ps-sc"><div>คะแนน · ${n} ข้อ</div><b>&nbsp;&nbsp;&nbsp;/ ${n}</b></div>${link?`<div class="ps-qr" id="psqr"><small>สแกนทำออนไลน์</small></div>`:""}</div>
      ${cards}<div class="ps-done"><p class="ps-dl">ทำครบแล้ว? ส่งคำตอบให้ครู</p><div class="ps-dr"><input id="psname" placeholder="ชื่อของเรา" autocomplete="name"><button id="pscopy">คัดลอกคำตอบ</button></div></div></div>`;}
  function linkFor(ids,t){return location.origin+location.pathname+"#sheet="+ids.map(encodeURIComponent).join(",")+"&t="+encodeURIComponent(t);}
  let qrLib=null;function qr(){return qrLib||(qrLib=new Promise(res=>{if(window.qrcode)return res(window.qrcode);const s=document.createElement("script");
    s.src="https://cdn.jsdelivr.net/npm/qrcode-generator@1.4.4/qrcode.min.js";s.onload=()=>res(window.qrcode||null);s.onerror=()=>res(null);document.head.appendChild(s);setTimeout(()=>res(window.qrcode||null),4000);}));}
  async function fill(ids,t,w,withLink){const ps=$("#psheet"),link=withLink?linkFor(ids,t):"";ps.innerHTML=sheetHtml(ids,t,w,link);tex(ps);
    if(link){const Q=await qr();const ft=$("#psqr");if(Q&&ft){try{const c=Q(0,"M");c.addData(link);c.make();ft.insertAdjacentHTML("afterbegin",c.createSvgTag({cellSize:2,margin:0,scalable:true}));}catch(_){}}}
    await Promise.all([...ps.querySelectorAll("img")].map(i=>i.complete?0:new Promise(r=>{i.onload=i.onerror=r;setTimeout(r,5000);})));
    const p=$("#psprint");if(p)p.onclick=()=>doPrint(false);
    if(!withLink)student(ids,t);}
  /* the student link: tap a choice to pick it (one per question, kept on this phone), progress in the bar, copy the answers */
  function student(ids,t){const ps=$("#psheet"),KEY="cqb_sheet:"+ids.join(","),pick=J(KEY,{}),cards=[...ps.querySelectorAll(".ps-c")];
    const opts=c=>{const L=c.querySelectorAll(".body ul,.body ol");return L.length?[...L[L.length-1].children].filter(x=>x.tagName==="LI"):[];};
    cards.forEach(c=>{const L=c.querySelectorAll(".body ul,.body ol");if(L.length)L[L.length-1].classList.add("ps-opts");});
    const lab=li=>{const m=li.textContent.trim().match(/^\(?([ก-ฮ1-9A-Za-z])[.)]/);return m?m[1]:li.textContent.trim().slice(0,12);};
    const paint=()=>{let done=0;cards.forEach((c,i)=>{const L=opts(c),k=pick[ids[i]];L.forEach((li,j)=>li.classList.toggle("mk",j===k));
        const a=k!=null&&L[k];c.classList.toggle("answered",!!a);if(a)done++;});$("#psprog").textContent=`ตอบแล้ว ${done}/${ids.length}`;};
    ps.addEventListener("click",e=>{const li=e.target.closest(".ps-opts>li");if(!li)return;const c=li.closest(".ps-c"),i=cards.indexOf(c),j=opts(c).indexOf(li);
      pick[ids[i]]=pick[ids[i]]===j?undefined:j;W(KEY,pick);paint();});
    const nm=$("#psname");nm.value=ls.get("cqb_sheet_name","");nm.oninput=()=>ls.set("cqb_sheet_name",nm.value);
    $("#pscopy").onclick=async()=>{const lines=cards.map((c,i)=>{const L=opts(c),k=pick[ids[i]];return `${i+1}) ${k!=null&&L[k]?lab(L[k]):"-"}`;});
      const txt=`${t}${nm.value.trim()?" · "+nm.value.trim():""}\n`+lines.join("\n");
      try{await navigator.clipboard.writeText(txt);toast("คัดลอกคำตอบแล้ว — วางในแชทส่งครูได้เลย");}catch(_){prompt("คัดลอกคำตอบนี้",txt);}};
    paint();}
  let printed=false;
  function doPrint(nudge){document.body.classList.add("printing");printed=nudge;
    if(document.fonts&&document.fonts.ready)document.fonts.ready.then(()=>window.print());else window.print();}
  addEventListener("afterprint",()=>{document.body.classList.remove("printing");
    if(printed){printed=false;const k=$("#cpkeep");k.classList.add("nudge");$("#cpkl").textContent="พิมพ์แล้ว — เก็บตะกร้านี้ไว้ยังไง?";}});

  /* ---- ribbons: same pin state machine as drug-webapp (only a CHANGE animates) ---- */
  function pinSet(b,on){const was=b.dataset.st,now=on?"1":"0";b.dataset.st=now;b.setAttribute("aria-pressed",on?"true":"false");
    b.title=on?"อยู่ในตะกร้า · แตะริบบิ้นเพื่อเอาออก":"ใส่ตะกร้า (C)";const c=b.parentElement;if(c)c.classList.toggle("incart",on);
    if(was===undefined||was===now||rm()){b.classList.toggle("done",on);b.classList.remove("pop","unpop");return 0;}
    clearTimeout(b._pt);
    if(on){b.classList.remove("unpop");b.classList.add("done","pop");b._pt=setTimeout(()=>b.classList.remove("pop"),800);return 1;}
    b.classList.remove("pop");b.classList.add("unpop");b._pt=setTimeout(()=>b.classList.remove("unpop","done"),320);return 0;}
  function mark(){let ins=0;document.querySelectorAll("#root .cpin").forEach(b=>{ins+=pinSet(b,has(b.dataset.id));});
    const m=$("#mcart"),q=typeof mIdx!=="undefined"&&filtered[mIdx];if(m&&q){const on=has(q.id);m.classList.toggle("on",on);m.setAttribute("aria-pressed",on);m.title=on?"เอาออกจากตะกร้า (C)":"ใส่ตะกร้า (C)";}
    if(ins)snd("ribbon");}
  /* ---- the drawer ---- */
  function names(){const s=new Set([...J(KS,[]).map(x=>x.n),...Object.keys(given())]);$("#cpnames").innerHTML=[...s].map(n=>`<option value="${esc(n)}">`).join("");}
  function list(){const L=$("#cplist");
    if(!cart.ids.length){L.innerHTML=`<li class="cpempty"><span class="rbdemo"></span><b>ตะกร้ายังว่าง</b>ลากโจทย์ไปด้านข้าง (เมาส์หรือนิ้ว) หรือกด C<br>ข้อที่อยู่ในตะกร้าจะมีริบบิ้นแดงห้อยอยู่</li>`;return;}
    L.innerHTML=cart.ids.map((id,i)=>{const q=BY.get(id),g=givenTo(id);return `<li class="cpi d-${q.diff}" data-id="${esc(id)}"><span class="cph" title="ลากเพื่อเรียงลำดับ"><span class="cpno">${i+1}</span><i>⋮⋮</i></span>
      <div class="cpmeta"><span class="badge b-id">${esc(id)}</span><span class="badge ps-paper">${esc(paperTxt(q))}</span>${g.length?`<span class="cpg">ให้ ${esc(g.join(", "))} แล้ว</span>`:""}</div>
      <button class="cpdel" title="เอาออก" aria-label="เอาออก">✕</button><span class="cps">${q.snippet||""}</span></li>`;}).join("");}
  function sets(){const S=J(KS,[]);$("#cpsets").innerHTML=S.length?`<p class="cplab">ชุดที่บันทึกไว้</p>`+S.map((s,i)=>`<div class="cpset"><span><b>${esc(s.n)}</b> <small>· ${s.ids.length} ข้อ</small></span>
      <button class="cpmini" data-open="${i}">เปิด</button><button class="cpmini quiet" data-del="${i}">ลบ</button></div>`).join(""):"";}
  function wsBtns(){$("#cpws").querySelectorAll("button").forEach(b=>b.classList.toggle("on",+b.dataset.v===ws));}
  function panel(){const n=cart.ids.length;$("#cptitle").value=cart.t||"";$("#cptitle").placeholder=n?autoTitle():"ตั้งชื่อชีต";$("#cphn").textContent=n+" ข้อ";
    list();sets();names();wsBtns();["#cpprint","#cplink","#cpsort","#cpshuf","#cpsave","#cpgive","#cpclear"].forEach(s=>$(s).disabled=!n);}
  const isOpen=()=>document.body.classList.contains("cartopen");
  function open(){panel();$("#cpkeep").classList.remove("nudge");$("#cpkl").textContent="เก็บตะกร้านี้";document.body.classList.add("cartopen");try{SL.lock("cart");}catch(_){}snd("drawer");}
  function close(){if(!isOpen())return;document.body.classList.remove("cartopen");try{SL.unlock("cart");}catch(_){}}
  function sync(){const n=cart.ids.length;$("#cartn").textContent=n;document.body.classList.toggle("hascart",n>0||J(KS,[]).length>0);mark();if(isOpen())panel();}
  /* ---- drag a question sideways: mouse or finger (never the Pencil). Forked from drug-webapp dkGesture: one drag at a
     time, ended by pointerup/cancel/lostpointercapture, blur, or the element leaving the DOM. ---- */
  let D=null,EAT=0;const BTN="button,a,input,textarea,select,label,canvas,.v3d,.cph,.badge,.mink";
  function abort(){const d=D;D=null;document.documentElement.classList.remove("cdragging");if(!d)return;
    try{if(d.el.hasPointerCapture&&d.el.hasPointerCapture(d.id))d.el.releasePointerCapture(d.id);}catch(_){}d.el.classList.remove("cdrag","carmed");d.el.style.transform="";d.el.style.opacity="";}
  function gesture(root,o){root.addEventListener("pointerdown",e=>{if(D||e.button>0||!e.isPrimary||e.pointerType==="pen")return;
      const el=e.target.closest(o.sel);if(!el||!root.contains(el)||e.target.closest(BTN))return;
      for(let x=e.target;x&&x!==el;x=x.parentElement)if(x.scrollWidth>x.clientWidth+1&&/auto|scroll/.test(getComputedStyle(x).overflowX))return;
      D={o,id:e.pointerId,x:e.clientX,y:e.clientY,el,on:false,dx:0};},true);
    root.addEventListener("touchmove",e=>{if(D&&D.on&&e.cancelable)e.preventDefault();},{passive:false});}
  document.addEventListener("pointermove",e=>{const s=D;if(!s||e.pointerId!==s.id)return;if(!s.el.isConnected){abort();return;}
    const dx=e.clientX-s.x,dy=e.clientY-s.y;
    if(!s.on){if(Math.abs(dx)<8&&Math.abs(dy)<8)return;if(Math.abs(dy)>=Math.abs(dx)*.8){D=null;return;}
      s.on=true;try{s.el.setPointerCapture(e.pointerId);}catch(_){}document.documentElement.classList.add("cdragging");s.el.classList.add("cdrag");
      const sel=getSelection&&getSelection();if(sel&&!sel.isCollapsed)sel.removeAllRanges();}
    s.dx=dx;const p=Math.min(1,Math.abs(dx)/s.o.th),armed=Math.abs(dx)>=s.o.th;
    s.el.style.transform=`translateX(${dx}px) rotate(${dx/45}deg)`;s.el.style.opacity=String(1-p*.35);
    if(armed!==s.el.classList.contains("carmed")){s.el.classList.toggle("carmed",armed);if(armed)snd("tick");}
    if(e.cancelable)e.preventDefault();},{capture:true,passive:false});
  function end(e){const s=D;if(!s||e.pointerId!==s.id)return;if(!s.el.isConnected){abort();return;}
    if(e.type==="lostpointercapture"){if(e.target===s.el||e.target===document)abort();return;}
    D=null;document.documentElement.classList.remove("cdragging");s.el.classList.remove("cdrag","carmed");if(!s.on)return;EAT=Date.now()+350;
    const from=s.el.style.transform,op=s.el.style.opacity;
    if(e.type==="pointerup"&&Math.abs(s.dx)>=s.o.th&&s.o.go(s.el,s.dx)!==false)return;
    s.el.style.transform="";s.el.style.opacity="";
    if(!rm()&&from)s.el.animate([{transform:from,opacity:op||1},{transform:"none",opacity:1}],{duration:360,easing:"cubic-bezier(.3,1.45,.5,1)"});}
  function settle(el){el.style.transform="";el.style.opacity="";if(!rm())el.animate([{opacity:0,transform:"scale(.97)"},{opacity:1,transform:"none"}],{duration:260,easing:"ease-out"});}
  function boot(){
    document.body.insertAdjacentHTML("beforeend",`__MARKUP__`);
    document.addEventListener("pointerup",end,true);document.addEventListener("pointercancel",end,true);document.addEventListener("lostpointercapture",end,true);
    document.addEventListener("pointerdown",e=>{if(D&&e.pointerId!==D.id)abort();},true);
    addEventListener("blur",abort);document.addEventListener("visibilitychange",()=>{if(document.hidden)abort();});
    document.addEventListener("click",e=>{if(Date.now()<EAT){e.stopPropagation();e.preventDefault();}},true);
    document.addEventListener("dragstart",e=>{if(e.target.closest&&e.target.closest("#root .poster,#root .card,#root .row,#cplist"))e.preventDefault();});
    gesture($("#root"),{sel:".poster,.card,.row",th:110,go:el=>{const b=el.querySelector(":scope>.cpin");if(!b||!add(b.dataset.id))return false;settle(el);}});
    gesture($("#cplist"),{sel:".cpi",th:90,go:(el,dx)=>{el.style.transition="transform .2s,opacity .2s";el.style.transform=`translateX(${dx>0?120:-120}%)`;el.style.opacity="0";
      setTimeout(()=>remove(el.dataset.id,true),180);}});
    document.addEventListener("click",e=>{const b=e.target.closest(".cpin");if(!b)return;e.stopPropagation();e.preventDefault();toggle(b.dataset.id);},true);
    $("#mcart").onclick=()=>{const q=filtered[mIdx];if(q)toggle(q.id);};
    $("#carttab").onclick=open;$("#cpx").onclick=close;$("#cartwrap").addEventListener("click",e=>{if(e.target.id==="cartwrap")close();});
    addEventListener("keydown",e=>{if(e.key==="Escape"&&isOpen()){e.stopPropagation();close();}},true);
    $("#cptitle").oninput=e=>{cart.t=e.target.value;W(K,cart);};
    $("#cpsort").onclick=()=>{const o={easy:0,medium:1,hard:2};cart.ids.sort((a,b)=>(o[BY.get(a).diff]??1)-(o[BY.get(b).diff]??1));save();snd("chip");};
    $("#cpshuf").onclick=()=>{const a=cart.ids;for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}save();snd("chip");};
    $("#cpws").onclick=e=>{const b=e.target.closest("button");if(!b)return;ws=+b.dataset.v;ls.set(KW,String(ws));wsBtns();snd("chip");};
    $("#cplist").addEventListener("click",e=>{const d=e.target.closest(".cpdel");if(!d)return;const li=d.closest(".cpi");li.style.transition="transform .2s,opacity .2s";li.style.transform="translateX(110%)";li.style.opacity="0";setTimeout(()=>remove(li.dataset.id,true),180);});
    /* drag ⋮⋮ to reorder */
    $("#cplist").addEventListener("pointerdown",e=>{const h=e.target.closest(".cph");if(!h)return;e.preventDefault();const li=h.closest(".cpi"),L=$("#cplist");
      li.classList.add("lift");try{h.setPointerCapture(e.pointerId);}catch(_){}let y0=e.clientY;
      const mv=ev=>{li.style.transform=`translateY(${ev.clientY-y0}px)`;const r=li.getBoundingClientRect(),mid=r.top+r.height/2;
        const p=li.previousElementSibling,n=li.nextElementSibling;
        if(p&&mid<p.getBoundingClientRect().top+p.offsetHeight/2){L.insertBefore(li,p);y0-=p.offsetHeight+9;li.style.transform=`translateY(${ev.clientY-y0}px)`;}
        else if(n&&mid>n.getBoundingClientRect().top+n.offsetHeight/2){L.insertBefore(n,li);y0+=n.offsetHeight+9;li.style.transform=`translateY(${ev.clientY-y0}px)`;}};
      const up=()=>{h.removeEventListener("pointermove",mv);h.removeEventListener("pointerup",up);h.removeEventListener("pointercancel",up);
        li.classList.remove("lift");li.style.transform="";cart.ids=[...L.querySelectorAll(".cpi")].map(x=>x.dataset.id);save();};
      h.addEventListener("pointermove",mv);h.addEventListener("pointerup",up);h.addEventListener("pointercancel",up);});
    $("#cpprint").onclick=async()=>{if(!cart.ids.length)return;await fill(cart.ids,title(),ws,true);doPrint(true);};
    $("#cplink").onclick=async()=>{if(!cart.ids.length)return;const u=linkFor(cart.ids,title());
      try{if(navigator.share&&matchMedia("(pointer:coarse)").matches){await navigator.share({title:title(),url:u});return;}}catch(_){return;}
      try{await navigator.clipboard.writeText(u);toast("คัดลอกลิงก์แล้ว — ส่งให้นักเรียนได้เลย");}catch(_){prompt("คัดลอกลิงก์นี้",u);}};
    const nm=()=>{const n=$("#cpname").value.trim();if(!n){toast("ใส่ชื่อก่อน",{warn:true});$("#cpname").focus();}return n;};
    $("#cpsave").onclick=()=>{const n=nm();if(!n||!cart.ids.length)return;const S=J(KS,[]).filter(x=>x.n!==n);S.unshift({n,t:title(),ids:[...cart.ids],w:ws,d:Date.now()});W(KS,S);sync();toast(`บันทึกชุด “${n}” แล้ว`);};
    $("#cpgive").onclick=()=>{const n=nm();if(!n||!cart.ids.length)return;const g=given();g[n]=[...new Set([...(g[n]||[]),...cart.ids])];W(KG,g);list();names();toast(`บันทึกว่าให้ ${n} แล้ว · ${cart.ids.length} ข้อ`);};
    $("#cpclear").onclick=()=>{if(!cart.ids.length)return;const old={t:cart.t,ids:[...cart.ids]};cart={t:"",ids:[]};save();close();
      toast(`ล้างตะกร้าแล้ว (${old.ids.length} ข้อ)`,{act:"ย้อนกลับ",fn:()=>{cart=old;save();}});};
    $("#cpsets").onclick=e=>{const S=J(KS,[]),o=e.target.dataset.open,d=e.target.dataset.del;
      if(o!=null){const s=S[+o];if(!s)return;cart={t:s.t||"",ids:s.ids.filter(id=>BY.has(id))};if(s.w!=null){ws=s.w;ls.set(KW,String(ws));}save();$("#cpname").value=s.n;toast(`เปิดชุด “${s.n}” แล้ว`);}
      if(d!=null){const s=S[+d];if(!s||!confirm(`ลบชุด “${s.n}”?`))return;S.splice(+d,1);W(KS,S);sync();}};
    addEventListener("keydown",e=>{if((e.key!=="c"&&e.key!=="C")||e.metaKey||e.ctrlKey||e.altKey||e.target.closest("input,textarea,select,[contenteditable]")||isOpen())return;
      let q=null;if($("#modal").classList.contains("show"))q=filtered[mIdx];
      else if(view==="poster"&&document.body.classList.contains("inapp"))q=filtered[pIdx];
      else{const h=document.querySelector("#root .card:hover,#root .row:hover,#root .poster:hover");const b=h&&h.querySelector(":scope>.cpin");if(b)q=BY.get(b.dataset.id);}
      if(q){e.preventDefault();toggle(q.id);}});
    new MutationObserver(mark).observe($("#root"),{childList:true,subtree:true});
    new MutationObserver(mark).observe($("#mtop"),{childList:true});
    /* a student's link: #sheet=Q-0113,Q-0192&t=... -> the sheet on screen, no answers */
    const m=location.hash.match(/^#sheet=([^&]*)(?:&t=(.*))?$/);
    if(m){const ids=m[1].split(",").map(decodeURIComponent).filter(id=>BY.has(id));
      if(ids.length){document.body.classList.add("sheetview");fill(ids,m[2]?decodeURIComponent(m[2]):"แบบฝึกหัด",0,false);}}
    sync();}
  return {boot,add,remove,has,toggle};
})();
CART.boot();
"""

PIN = '<button class="cpin" data-id="${q.id}" aria-pressed="false" title="ใส่ตะกร้า (C)"><span class="rb"><i></i></span></button>'
BOOKMARK = ('<button class="x" id="mcart" title="ใส่ตะกร้า (C)" aria-label="ตะกร้า" aria-pressed="false"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" '
            'stroke="currentColor" stroke-width="2.6" stroke-linejoin="round" aria-hidden="true"><path d="M6 3h12v18l-6-4.5L6 21z"/></svg></button>')
# drug-webapp v2 SFX.ribbon, verbatim: a soft cloth swish down, a light tick as it lands, a small wood knock as it settles
RIBBON_SFX = ('    ribbon:()=>{noise(.3,{type:"lowpass",freq:2400,sweep:.35,q:.6,vol:.07,attack:.08,delay:.1,wet:.15});'
              'tone(vary(1500,.03),.02,{vol:.03,type:"triangle",attack:.001,delay:.43});wood(vary(659,.015),{vol:.05,delay:.55});},\n')


def apply(html):
    """Wire the cart into the main index.html template (never the student builds)."""
    def rep(old, new):
        nonlocal html
        assert html.count(old) == 1, ("cart_part anchor not unique/missing", old[:70])
        html = html.replace(old, new)
    rep("</style></head><body>", CSS + "</style></head><body>")
    rep('<article class="poster lv-${q.diff}${exCls(q)} ${anim||""}" data-i="${i}">',
        '<article class="poster lv-${q.diff}${exCls(q)} ${anim||""}" data-i="${i}">' + PIN)
    rep('<span class="cnum">${qnum(q)}</span>', PIN + '<span class="cnum">${qnum(q)}</span>')
    rep('<div class="row${exCls(q)}" data-i="${i}">', '<div class="row${exCls(q)}" data-i="${i}">' + PIN)
    rep('<button class="x shotx" id="mshot"', BOOKMARK + '<button class="x shotx" id="mshot"')
    rep("    chip:on=>", RIBBON_SFX + "    chip:on=>")
    qr = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrcode-generator-1.4.4.min.js"), encoding="utf-8").read()
    rep("</script></body></html>", JS.replace("__MARKUP__", MARKUP) + "</script><script>/* qrcode-generator 1.4.4 (MIT, Kazuhiko Arase), vendored so the sheet's QR never waits on a CDN */" + chr(10) + qr + chr(10) + "</script></body></html>")
    return html
