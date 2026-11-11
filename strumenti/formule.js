// Le formule del motore contro la loro definizione (AGENTS.md, Gli audit, «Le formule contro la loro definizione»).
//
//   node strumenti/formule.js            gli invarianti (esce con 1 se uno non torna) e i conti del controllo del b97
//   node strumenti/formule.js --breve    solo gli invarianti
//
// Nessuna rete e nessun browser: legge le funzioni pure da scanner.html (matrice Dixon-Coles, binomiale negativa,
// handicap, Markov, inclinazione dell'Elo, matrice allineata, corner, quote, giocate) e le fa girare qui.
// Prima parte, gli invarianti: somme a 1, identita' fra mercati, vincoli raggiunti dalle bisezioni. Da rifare quando si
// tocca una di quelle funzioni. Seconda parte, i conti su casi tipo che reggono le voci del controllo: non sono misure
// su partite vere, dicono quanto pesa ogni punto.
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(process.env.ROOT || path.join(__dirname, '..'), 'scanner.html'), 'utf8');
const js = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');
const fetta = (da, a, incl) => { const i = js.indexOf(da), j = js.indexOf(a, i + 1); if (i < 0 || j < 0) throw new Error('fetta non trovata: ' + da); return js.slice(i, incl ? js.indexOf('\n', j) : j); };
const codice = [fetta('function _mean(arr)', 'const PITCH_BASE'), fetta('const ADV_SPEC = [', 'const ADV_KEYS = ', true),
  fetta('const QUOTE_COMB = {', 'const _gqQ'), fetta('const STAT_SHRINK_DEFAULT', 'async function avviaScanner()')].join('\n;\n');
const M = new Function('window', 'document', 'globalLeagueMatchesCache', codice + `
  return { _stddev, negBinPMF, negBinCDF, negBinK, poisson, calcDCMatrix, probsFromMatrix, multigoal, asianHandicapMat, markovFlow,
           eloTiltLambdas, matriceAllineata, combinaQuote, combinaOU, giocateProb, cornerDiff };`)({}, undefined, []);
const { negBinPMF, negBinCDF, negBinK, calcDCMatrix: dc, probsFromMatrix: pr, multigoal, asianHandicapMat: ah, markovFlow, eloTiltLambdas,
        matriceAllineata, combinaQuote, combinaOU, giocateProb, cornerDiff } = M;
const pc = (x, d = 1) => (100 * x).toFixed(d), lg = x => Math.log(x / (1 - x));
let rotti = 0, fatti = 0;
const vero = (cond, nome, dett) => { fatti++; if (!cond) { rotti++; console.log('  NON TORNA  ' + nome + (dett ? ' (' + dett + ')' : '')); } };
const vicino = (a, b, tol, nome) => vero(Math.abs(a - b) <= tol, nome, `${a} contro ${b}`);
const CASI = [[1.5, 1.2, -0.03], [1.35, 1.35, 0], [2.4, 0.7, -0.10], [0.6, 0.5, -0.15], [3.2, 2.1, 0.05], [1.1, 1.0, -0.25]];

// ---------------------------------------------------------------- gli invarianti
for (const [mu, k] of [[9.6, 57.2], [4.1, 12], [8.4, Infinity], [0.19, 3]]) {
  let s = 0; for (let x = 0; x <= 120; x++) s += negBinPMF(x, mu, k);
  vicino(s, 1, 1e-6, `binomiale negativa (${mu}, ${k}): somma`);
  let m = 0; for (let x = 0; x <= 120; x++) m += x * negBinPMF(x, mu, k);
  vicino(m, mu, 1e-5, `binomiale negativa (${mu}, ${k}): media`);
  vicino(1 - negBinCDF(9, mu, k) + negBinCDF(9, mu, k), 1, 1e-12, 'Over e Under di una linea');
}
for (const [lh, la, rho] of CASI) {
  const mat = dc(lh, la, rho), P = pr(mat), nome = `matrice (${lh}, ${la}, ${rho})`;
  let s = 0, mh = 0, ma = 0, neg = 0;
  mat.forEach((r, i) => r.forEach((p, j) => { s += p; mh += i * p; ma += j * p; if (p < 0) neg++; }));
  vicino(s, 1, 1e-12, nome + ': somma'); vero(!neg, nome + ': nessuna cella negativa');
  // rho non sposta i gol attesi; la matrice e' tagliata a 10 gol, e a lambda 3.2 il taglio ne toglie 0.004
  vicino(mh, lh, 6e-3, nome + ': gol attesi di casa'); vicino(ma, la, 6e-3, nome + ': gol attesi di trasferta');
  vicino(P.p1 + P.pX + P.p2, 1, 1e-12, nome + ': 1X2');
  // le quattro celle corrette da rho stanno tutte sotto 2.5 e la loro somma non cambia: Over 2.5 e 3.5 non dipendono da rho
  vicino(P.pOv, pr(dc(lh, la, 0)).pOv, 1e-9, nome + ': Over 2.5 non dipende da rho');
  vicino(pr(mat, 3.5).pOv, pr(dc(lh, la, 0), 3.5).pOv, 1e-9, nome + ': Over 3.5 non dipende da rho');
  let prima = -1;
  for (const h of [-1.5, -1, -0.75, -0.5, 0.5, 1, 1.5]) { const a = ah(mat, h);
    vicino(a.pHome + a.pRefund + a.pAway, 1, 1e-12, nome + ': handicap ' + h + ' somma');
    vero(a.pHome + a.pRefund >= prima - 1e-12, nome + ': handicap monotono a ' + h); prima = a.pHome + a.pRefund; }
  vicino(ah(mat, -0.5).pHome, P.p1, 1e-12, nome + ': handicap -0.5 = 1'); vicino(ah(mat, 0.5).pHome, P.p1 + P.pX, 1e-12, nome + ': handicap +0.5 = 1X');
  const q = ah(mat, -0.75).pHome; vero(q <= ah(mat, -0.5).pHome + 1e-12 && q >= ah(mat, -1).pHome - 1e-12, nome + ': handicap -0.75 fra -1 e -0.5');
  vicino(multigoal(mat, 0, 1) + multigoal(mat, 2, 3) + multigoal(mat, 4, 20), 1, 1e-12, nome + ': multigol 0-1, 2-3, 4+');
  vicino(multigoal(mat, 0, 0, 'h') + multigoal(mat, 1, 10, 'h'), 1, 1e-12, nome + ': multigol casa');
  const mk = markovFlow(lh, la); vicino(mk.p1 + mk.pX + mk.p2, 1, 1e-9, nome + ': Markov 1X2');
}
{ // l'inclinazione dell'Elo: totale identico, bersaglio raggiunto
  for (const [lh, la, d] of [[1.5, 1.2, 180], [1.2, 1.4, -90], [1.9, 0.9, 40], [1.3, 1.3, 0]]) {
    const E = eloTiltLambdas(lh, la, d, 55, -0.03), P = pr(dc(E.lamH, E.lamA, -0.03));
    vero(E.applied, `inclinazione (${lh}, ${la}, ${d}): applicata`);
    vicino(E.lamH + E.lamA, lh + la, 1e-12, `inclinazione (${lh}, ${la}, ${d}): totale dei lambda`);
    if (!E.capped) vicino(Math.log(P.p1 / P.p2), E.lgTarget, 1e-5, `inclinazione (${lh}, ${la}, ${d}): bersaglio`);
  } }
{ // la matrice allineata: Over e log(p1/p2) chiesti
  for (const [ov, l12, rho] of [[0.54, 0.4, -0.03], [0.38, -0.9, -0.10], [0.66, 1.6, 0]]) {
    const P = pr(matriceAllineata(ov, l12, rho));
    vicino(P.pOv, ov, 1e-6, `matrice allineata (${ov}, ${l12}): Over`); vicino(Math.log(P.p1 / P.p2), l12, 1e-6, `matrice allineata (${ov}, ${l12}): log(p1/p2)`);
  } }
{ // chi fa piu' corner
  for (const [h, a, e] of [[5.4, 4.3, 120], [4.0, 6.2, -260], [0.2, 5, 0]]) {
    const C = cornerDiff(h, a, e), nome = `corner (${h}, ${a}, ${e})`;
    vicino(C.pH + C.pX + C.pA, 1, 1e-6, nome + ': somma'); vicino(C.hc['-0.5'], C.pH, 1e-12, nome + ': casa -0.5 = piu\' corner casa');
    vicino(C.hc['0.5'], 1 - C.pA, 1e-6, nome + ': casa +0.5 = non piu\' corner trasferta');
    const v = ['-2.5', '-1.5', '-0.5', '0.5', '1.5', '2.5'].map(k => C.hc[k]); vero(v.every((x, i) => !i || x >= v[i - 1]), nome + ': handicap monotono');
  } }
{ // le quote e le giocate
  const R = combinaQuote([0.46, 0.27, 0.27], [2.10, 3.40, 3.60]);
  vicino(R.comb.reduce((a, b) => a + b, 0), 1, 1e-12, 'quote 1X2: somma'); vicino(R.mercato.reduce((a, b) => a + b, 0), 1, 1e-12, 'mercato senza margine: somma');
  const O = combinaOU(0.52, [1.90, 1.95]); vero(O.comb > 0 && O.comb < 1, 'Over con le quote fra 0 e 1');
  for (const [S, q, qo] of [[[0.46, 0.27, 0.27], null, null], [R.comb, [2.10, 3.40, 3.60], [1.90, 1.95]]]) {
    const mat = dc(1.5, 1.2, -0.03), G = giocateProb(S, mat, q, qo, qo ? O.comb : null), p = k => G.voci.find(v => v.k === k).p;
    vero(G.voci.length === 22, 'giocate: 22');
    ['1', 'X', '2'].forEach((s, i) => { vicino(p(s + '+Over') + p(s + '+Under'), S[i], 1e-12, `giocate: ${s} + Over e ${s} + Under fanno il segno`);
      vicino(p(s + '+Goal') + p(s + '+NoGoal'), S[i], 1e-12, `giocate: ${s} + Goal e ${s} + NoGoal fanno il segno`); });
    vicino(p('Over') + p('Under'), 1, 1e-12, 'giocate: Over e Under'); vicino(p('Goal') + p('NoGoal'), 1, 1e-12, 'giocate: Goal e NoGoal');
    vicino(p('1X') + p('2'), 1, 1e-12, 'giocate: 1X e 2');
  } }
console.log(`Invarianti: ${fatti - rotti} su ${fatti} tornano` + (rotti ? `, ${rotti} NO` : ''));
if (process.argv.includes('--breve')) process.exit(rotti ? 1 : 0);

// ---------------------------------------------------------------- i conti del controllo (casi tipo, non partite vere)
console.log('\n1. Markov: i gol attesi della catena contro i lambda in ingresso, e il pareggio contro il Dixon-Coles');
function catena(lH, lA) {       // la stessa catena di markovFlow, tenendo anche i gol attesi
  const DA = 75, F = 1.30, norm = (DA + (90 - DA) * F) / 90, rH = lH / 90 / norm, rA = lA / 90 / norm;
  let dist = new Array(11).fill(0), eH = 0, eA = 0; dist[5] = 1;
  for (let t = 0; t < 90; t++) { const f = t >= DA ? F : 1, nd = new Array(11).fill(0);
    for (let s = -5; s <= 5; s++) { const p = dist[s + 5]; if (p <= 0) continue;
      const mH = s > 0 ? 0.94 : s < 0 ? 1.12 : 1, mA = s > 0 ? 1.12 : s < 0 ? 0.94 : 1, cH = rH * f * mH, cA = rA * f * mA;
      eH += p * cH; eA += p * cA; nd[s + 5] += p * (1 - cH - cA); nd[Math.min(10, s + 6)] += p * cH; nd[Math.max(0, s + 4)] += p * cA; }
    dist = nd; }
  return eH + eA;
}
for (const [lH, lA] of [[1.5, 1.2], [1.35, 1.35], [2.0, 0.9], [2.4, 0.7]]) { const K = markovFlow(lH, lA), D = pr(dc(lH, lA, -0.03));
  console.log(`   lambda ${lH}/${lA}: gol della catena ${(100 * (catena(lH, lA) / (lH + lA) - 1)).toFixed(1)}% | pareggio Markov ${pc(K.pX)} contro Dixon-Coles ${pc(D.pX)} | log(p1/p2) ${Math.log(K.p1 / K.p2).toFixed(3)} contro ${Math.log(D.p1 / D.p2).toFixed(3)}`); }

console.log('\n2. Elo: il log-odds 1 contro 2 diviso il log-odds del punteggio atteso (pareggio = mezzo), rho -0.03');
for (const [T, s] of [[2.7, 0.52], [2.7, 0.60], [2.7, 0.70], [2.7, 0.80], [2.3, 0.60], [3.2, 0.60]]) { const P = pr(dc(T * s, T * (1 - s), -0.03)), E = P.p1 + P.pX / 2, q = P.p1 / (P.p1 + P.p2);
  console.log(`   ${T} gol, ${pc(s, 0)}% alla casa: pareggio ${pc(P.pX)}, scarto Elo equivalente ${(173.7178 * lg(E)).toFixed(0)}, rapporto ${(lg(q) / lg(E)).toFixed(3)}`); }
console.log('   HFA, 1/X/2 di lega 43/26/31: dal rapporto delle vittorie ' + (400 * Math.log10(0.43 / 0.31)).toFixed(1) + ', dal punteggio atteso ' + (400 * Math.log10((0.43 + 0.13) / (0.31 + 0.13))).toFixed(1));

console.log('\n3. KNN: due squadre medie (gol di lega 1.50 in casa, 1.20 in trasferta; NPxG 0.89 dei gol, rigori 0.10)');
{ const base = (/_knnCombine\(knn_H\.avg_xg, knn_A\.avg_xga, LG\.avgH, LG\.avg([HA])\)/.exec(js) || [])[1];
  const aH = 1.50, aA = 1.20, u = 0.89, px = 0.10, c = (att, dif, bA, bD) => bA * (att / bA) * (dif / bD), f = (h, a) => { const P = pr(dc(h, a, -0.03)); return `1X ${pc(P.p1 + P.pX)}, Over ${pc(P.pOv)}`; };
  console.log(`   nel codice la difesa della trasferta e' divisa per LG.avg${base || '?'}` + (base === 'A' ? ' (la media che la trasferta SEGNA, non quella che subisce)' : ''));
  console.log(`   difesa divisa per la media che segna:  ${f(c(u * aH, u * aH, aH, aA) + px, c(u * aA, u * aA, aA, aH) + px)}`);
  console.log(`   difesa divisa per la media che subisce: ${f(c(u * aH, u * aH, aH, aH) + px, c(u * aA, u * aA, aA, aA) + px)}`);
  console.log(`   la lega:                                ${f(aH, aA)}`); }

console.log('\n4. rho: la griglia di estimateRho sulla matrice ai lambda MEDI, quando le squadre sono diverse fra loro');
function caso(seme) { let s = seme; return () => { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; }; }
const gauss = r => Math.sqrt(-2 * Math.log(r() || 1e-12)) * Math.cos(2 * Math.PI * r());
function griglia(f, n, avgH, avgA) { let best = null, be = Infinity;
  for (let rho = -0.25; rho <= 0.1001; rho += 0.005) { const m = dc(avgH, avgA, rho); let e = 0;
    [['0-0', 0, 0], ['1-0', 1, 0], ['0-1', 0, 1], ['1-1', 1, 1]].forEach(([k, i, j]) => { const d = m[i][j] - f[k] / n; e += d * d; });
    if (e < be) { be = e; best = rho; } }
  return best; }
function lega(sd, rhoVero, seme) { const r = caso(seme), n = 20, att = [], dif = [];
  for (let i = 0; i < n; i++) { att.push(Math.exp(sd * gauss(r))); dif.push(Math.exp(sd * gauss(r))); }
  const ma = att.reduce((a, b) => a + b) / n, md = dif.reduce((a, b) => a + b) / n, f = { '0-0': 0, '1-0': 0, '0-1': 0, '1-1': 0 }; let sh = 0, sa = 0, N = 0;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (i !== j) { const m = dc(1.5 * att[i] / ma * dif[j] / md, 1.2 * att[j] / ma * dif[i] / md, rhoVero);
    f['0-0'] += m[0][0]; f['1-0'] += m[1][0]; f['0-1'] += m[0][1]; f['1-1'] += m[1][1]; N++;
    for (let x = 0; x <= 10; x++) for (let y = 0; y <= 10; y++) { sh += x * m[x][y]; sa += y * m[x][y]; } }
  return griglia(f, N, sh / N, sa / N); }
for (const sd of [0, 0.15, 0.25, 0.35]) { const media = rv => { let s = 0; for (let k = 1; k <= 40; k++) s += lega(sd, rv, 1000 + k); return (s / 40).toFixed(3); };
  console.log(`   deviazione di attacco e difesa ${sd}: rho vero 0 -> ${media(0)} | -0.05 -> ${media(-0.05)} | -0.10 -> ${media(-0.10)}`); }
{ const r = caso(7), m = dc(1.5, 1.2, -0.05), cum = [], celle = []; let c = 0;
  for (let x = 0; x <= 10; x++) for (let y = 0; y <= 10; y++) { c += m[x][y]; cum.push(c); celle.push(x + '-' + y); }
  for (const n of [380, 760, 1140]) { const st = [];
    for (let t = 0; t < 300; t++) { const f = { '0-0': 0, '1-0': 0, '0-1': 0, '1-1': 0 };
      for (let i = 0; i < n; i++) { const u = r(); let k = cum.findIndex(v => v >= u); if (k < 0) k = cum.length - 1; if (f[celle[k]] !== undefined) f[celle[k]]++; }
      st.push(griglia(f, n, 1.5, 1.2)); }
    console.log(`   ${n} partite, rho vero -0.05: stima media ${(st.reduce((a, b) => a + b) / st.length).toFixed(3)}, deviazione ${M._stddev(st).toFixed(3)}`); }
  const P = [0, -0.05].map(x => pr(dc(1.5, 1.2, x)));
  console.log(`   rho da 0 a -0.05, a lambda fermi: pareggio ${pc(P[0].pX)} -> ${pc(P[1].pX)}, Goal ${pc(P[0].pGG)} -> ${pc(P[1].pGG)}, Over 2.5 ${pc(P[0].pOv, 3)} -> ${pc(P[1].pOv, 3)}`); }

console.log('\n5. Il pareggio quando cambia log(p1/p2): fermo, con Davidson a nu fisso, e dalla matrice a totale fisso (2.7 gol)');
{ const trova = l => { let lo = 0.01, hi = 0.99; for (let i = 0; i < 50; i++) { const s = (lo + hi) / 2, P = pr(dc(2.7 * s, 2.7 * (1 - s), -0.03)); if (Math.log(P.p1 / P.p2) < l) lo = s; else hi = s; } return pr(dc(2.7 * lo, 2.7 * (1 - lo), -0.03)); };
  for (const [a, b] of [[0.3, 0.6], [0.5, 0.73], [0.8, 1.3], [1.3, 0.8]]) { const P0 = trova(a), P1 = trova(b), nu = P0.pX * 2 * Math.cosh(a / 2) / (1 - P0.pX);
    console.log(`   da ${a} a ${b}: fermo ${pc(P0.pX)} | Davidson ${pc(nu / (2 * Math.cosh(b / 2) + nu))} | matrice ${pc(P1.pX)}`); } }

console.log('\n6. Le partite efficaci di una media con emivita 106 giorni');
for (const [n, g] of [[30, 300], [30, 420], [15, 300], [15, 420]]) { let s = 0, s2 = 0; for (let i = 0; i < n; i++) { const w = Math.pow(0.5, (g * i / (n - 1)) / 106); s += w; s2 += w * w; }
  console.log(`   ${n} partite su ${g} giorni: ${(s * s / s2).toFixed(1)}`); }
console.log('   attacco x difesa di due squadre medie (NPxG/gol 0.89, SHRINK_K 4): ' + [5, 15, 30].map(n => `${n} partite ${Math.pow((n * 0.89 + 4) / (n + 4), 2).toFixed(3)}`).join(', '));

console.log('\n7. negBinK su campioni di Poisson pura (due squadre messe insieme)');
{ const r = caso(11), pois = lam => { const L = Math.exp(-lam); let k = 0, p = 1; do { k++; p *= r(); } while (p > L); return k - 1; };
  for (const [n, a, b, nome] of [[60, 9.6, 9.6, 'corner 30+30, stessa media'], [60, 8.6, 10.6, 'corner 30+30, medie 8.6 e 10.6'], [30, 4.0, 4.0, 'gialli 15+15, stessa media'], [30, 3.2, 4.8, 'gialli 15+15, medie 3.2 e 4.8']]) {
    let fin = 0, d = 0; const T = 3000, lam = (a + b) / 2, linea = lam > 6 ? 11 : 5;
    for (let t = 0; t < T; t++) { const v = []; for (let i = 0; i < n; i++) v.push(pois(i < n / 2 ? a : b)); const k = negBinK(v); if (isFinite(k)) fin++; d += negBinCDF(linea, lam, Infinity) - negBinCDF(linea, lam, k); }
    console.log(`   ${nome}: dispersione nel ${(100 * fin / T).toFixed(0)}% dei campioni, Over ${linea}.5 spostato in media di ${(100 * d / T).toFixed(2)} punti`); } }

console.log('\n8. La retta dei binari: un esito e il suo contrario');
{ const src = /const _calibConfBin = \(p\) => Math\.max\(0, Math\.min\(100, (-?[\d.]+) \+ ([\d.]+) \* \(p \* 100\)\)\);/.exec(js);
  if (src) { const f = x => Math.max(0, Math.min(100, +src[1] + +src[2] * x)); console.log('   ' + [50, 60, 75, 90].map(p => `${p} e ${100 - p}: ${f(p).toFixed(1)} + ${f(100 - p).toFixed(1)} = ${(f(p) + f(100 - p)).toFixed(1)}`).join(' | ')); }
  else console.log('   la retta non e\' piu\' scritta in quella forma'); }
process.exit(rotti ? 1 : 0);
