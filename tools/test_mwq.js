// Parser test for the present-card Mw strip. Run after build_viewer.py:  node tools/test_mwq.js [--sweep]
// Pulls the real MWCORE (atomic-mass table + parseF) and MWQ (formula finder) blocks out of index.html, so it tests what ships.
// --sweep: run the finder over every question in the bank and list the most frequent detections, to eyeball for garbage.
const fs = require("fs"), path = require("path");
const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const between = (a, b) => { const i = html.indexOf(a), j = html.indexOf(b); if (i < 0 || j < 0) throw new Error("marker missing " + a); return html.slice(i + a.length, j); };
global.document = { createElement: () => ({ set innerHTML(h) { this.value = h.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&"); } }) };
const core = between("/*MWCORE*/", "/*ENDMWCORE*/"), mwq = between("/*MWQ*/", "/*ENDMWQ*/");
const { parseF, SYM, MWQ } = new Function(core + "\n" + mwq.replace("const MWQ=", "var MWQ=") + "\nreturn{parseF,SYM,MWQ};")();
const found = h => MWQ.find(h, parseF).map(r => r.f);
const mw = f => Object.entries(parseF(f)).reduce((a, [k, n]) => a + SYM[k].m * n, 0);

// [input html, expected formulas (in order)]  -- inputs are modelled on real bank / worksheet strings
const T = [
  ["<p>ละลาย CuSO₄·5H₂O 5.0 g ในน้ำ</p>", ["CuSO4·5H2O"]],
  ["<p>K<sub>2</sub>Cr<sub>2</sub>O<sub>7</sub> 0.1 mol</p>", ["K2Cr2O7"]],
  ["<p>H₂C₂O₄ ทำปฏิกิริยากับ KMnO₄</p>", ["H2C2O4", "KMnO4"]],
  ["<p>Fe₃O₄ และ Fe₂O₃</p>", ["Fe3O4", "Fe2O3"]],
  ["<p>Ca(OH)₂ 0.2 mol</p>", ["Ca(OH)2"]],
  ["<p>Ca(OH)2(aq) + 2HCl(aq)</p>", ["Ca(OH)2", "HCl"]],
  ["<p>5Fe²⁺ + MnO<sub>4</sub><sup>-</sup> + 8H<sup>+</sup></p>", ["Fe", "MnO4"]],
  ["<p>Fe<sup>3+</sup>(aq) + 3e<sup>-</sup></p>", ["Fe"]],
  ["<p>Mg2+ และ Cr3+ และ SO42-</p>", ["Mg", "Cr", "SO4"]],
  ["<p>NH4+ กับ MnO4- กับ [Cu(NH3)4]2+</p>", ["NH4", "MnO4", "Cu(NH3)4"].map(x => x === "Cu(NH3)4" ? "[Cu(NH3)4]" : x)],
  ["<p>(NH4)2HPO4 และ Al2(SO4)3</p>", ["(NH4)2HPO4", "Al2(SO4)3"]],
  ["<p>Zn(s) + CuSO4(aq) → ZnSO4(aq) + Cu(s)</p>", ["Zn", "CuSO4", "ZnSO4", "Cu"]],
  ["<li>ก) CO₂ ข) SO₂ ค) NO₂</li><li>ง) H₂O</li>", ["CO2", "SO2", "NO2", "H2O"]],
  ["<p>CH₃COOH 0.1 M</p>", ["CH3COOH"]],
  ["<p>แก๊ส O2(g) และ N₂ กับ Cl2</p>", ["O2", "N2", "Cl2"]],
  ["<p>CuSO4.5H2O</p>", ["CuSO4.5H2O"]],
  ["<p>2H2O + 3CO2</p>", ["H2O", "CO2"]],
  ["<p>Na, K, Ar</p>", ["Na", "Ar"]],           // K alone = one-letter -> skipped (precision)
  // ---- negatives: must produce NOTHING ----
  ["<p>ข้อใดถูก A. B. C. D.</p>", []],
  ["<p>V = 25 cm³ ความเข้มข้น 0.1 M pH = 3 mol/L</p>", []],
  ["<p>Ka ของกรด = 1.8×10⁻⁵ และ Kb, Kw, K1, K2</p>", []],
  ["<p>โลหะ X ทำปฏิกิริยากับ Y ได้ XO และ YZ3 ,A, B, M</p>", []],
  ["<p>M1V1 = M2V2 , C1V1 = C2V2, P1V1 = P2V2, PV = nRT</p>", []],
  ["<p>ΔHf และ ΔH2 ของปฏิกิริยา kJ/mol</p>", []],
  ["<p>SN1 SN2 E2 UV IR NMR DNA RNA ATP HIV PVC CFC IUPAC GHS STP</p>", []],
  ["<p>In the lab, As shown, At 25 °C, He said No, Be careful, 100 Pa, Co</p>", []],
  ["<p>[Ne]3s² [Ar]3d⁵4s¹ [He]2s² และ IE1, IE2</p>", []],
  ["<p>HA + H2O ⇌ H3O+ + A- , BOH, MOH, HB</p>", ["H2O", "H3O"]],
  ["<p>PH2 = 0.5 atm, PSO2, PCH4 และ n_A, nB, mL, kJ</p>", []],
  ["<p>ปริมาตร Prat Latte Cryptozona ข้อ 3 Q-0042</p>", []],
];

let fail = 0;
for (const [h, want] of T) {
  const got = found(h), ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) { fail++; console.log("FAIL", JSON.stringify(h), "\n  want", JSON.stringify(want), "\n  got ", JSON.stringify(got)); }
}
// Mw spot checks against hand values (g/mol, 1 dp)
const M = { "CuSO4": 159.6, "K2Cr2O7": 294.2, "CuSO4·5H2O": 249.7, "Ca(OH)2": 74.1, "Fe3O4": 231.5, "H2C2O4": 90.0, "NaCl": 58.4, "Fe": 55.8 };
for (const [f, v] of Object.entries(M)) { const g = +mw(f).toFixed(1); if (g !== v) { fail++; console.log("FAIL Mw", f, "want", v, "got", g); } }
console.log(`${T.length} parser cases + ${Object.keys(M).length} Mw checks: ${fail ? fail + " FAILED" : "all pass"}`);

if (process.argv.includes("--sweep")) {
  const line = html.split("\n").find(l => l.startsWith("const DATA = "));
  const data = JSON.parse(line.slice(13).replace(/;\s*$/, "")), cnt = {}; let withHit = 0;
  for (const q of data.questions) { const r = found(q.bodyHtml || ""); if (r.length) withHit++; r.forEach(f => cnt[f] = (cnt[f] || 0) + 1); }
  console.log(`questions with >=1 formula: ${withHit}/${data.questions.length}; distinct ${Object.keys(cnt).length}`);
  console.log(Object.entries(cnt).sort((a, b) => b[1] - a[1]).map(([f, n]) => f + ":" + n).join(" "));
}
process.exit(fail ? 1 : 0);
