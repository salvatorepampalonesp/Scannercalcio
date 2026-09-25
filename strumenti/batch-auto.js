// BATCH AUTOMATICO: il Comparatore vero, guidato senza schermo, sulla PitchAPI vera.
//
// Apre comparatore.html da un server locale, col scanner.html del repository accanto (quindi
// la copia conforme si certifica riga per riga come a mano), sceglie leghe e stagioni e lancia
// lo sweep del Comparatore. Le chiamate alla PitchAPI le fa Node, mai la pagina: la chiave la
// aggiunge il proxy dell'ambiente (credenziale API sul sito della PitchAPI, header X-API-KEY),
// oppure, fuori da un ambiente cloud, la variabile PITCHAPI_KEY. Ogni CSV si salva appena la sua stagione finisce, e una
// stagione che ha gia' il suo file nella cartella si salta: rilanciare riprende da dove era.
//
//   node strumenti/batch-auto.js --leghe "Serie A,Eredivisie" --stagioni 2024/2025,2025/2026
//   node strumenti/batch-auto.js --leghe l_0ALvwF --out /percorso/cartella
//   node strumenti/batch-auto.js --finto ...      la lega finta del banco al posto della PitchAPI
//
// --leghe: id di leghe.json o nomi; se un nome e' ambiguo, PAESE:Nome (GER:Bundesliga).
// --stagioni: di default 2023/2024, 2024/2025 e 2025/2026 (le stagioni con due alle spalle).
// --out: di default batch/ nella radice del repository (fuori da git).
// AGENTS.md, Il batch automatico.
'use strict';
const { spawnSync } = require('child_process');
if (process.env.HTTPS_PROXY && !process.env.NODE_USE_ENV_PROXY && !process.argv.includes('--finto')) {
  const r = spawnSync(process.execPath, ['--no-warnings', __filename, ...process.argv.slice(2)],
                      { stdio: 'inherit', env: { ...process.env, NODE_USE_ENV_PROXY: '1' } });
  process.exit(r.status == null ? 1 : r.status);
}
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const PITCH = 'https://pitchapi-proxy.salvatorepampalone-sp.workers.dev';
const arg = (nome, def) => { const i = process.argv.indexOf('--' + nome); return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : def; };
const FINTO = process.argv.includes('--finto');
const OUT = path.resolve(arg('out', path.join(ROOT, 'batch')));
const STAGIONI = arg('stagioni', '2023/2024,2024/2025,2025/2026').split(',').map(s => s.trim()).filter(Boolean);
const KEY = process.env.PITCHAPI_KEY || '';
const CORS = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*' };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ora = () => new Date().toISOString().slice(11, 19);

function esci(msg) { console.error(msg); process.exit(1); }

// le leghe richieste, risolte su leghe.json
const LEGHE = JSON.parse(fs.readFileSync(path.join(ROOT, 'leghe.json'), 'utf8')).data.leagues;
function risolvi(x) {
  const [cc, nome] = x.includes(':') ? x.split(':') : [null, x];
  const trov = LEGHE.filter(l => l.id === x || (l.name.toLowerCase() === nome.toLowerCase() && (!cc || l.country_code === cc)));
  if (trov.length === 1) return trov[0];
  if (!trov.length) esci(`Lega "${x}" non trovata in leghe.json.`);
  esci(`Lega "${x}" ambigua: ${trov.map(l => l.country_code + ':' + l.name).join(', ')}. Scrivi PAESE:Nome.`);
}
const richieste = arg('leghe', '').split(',').map(s => s.trim()).filter(Boolean);
if (!richieste.length) esci('Indica le leghe: --leghe "Serie A,Premier League" (id o nomi di leghe.json).');
const nomeFile = (l, s) => `Backtest_V97_${l.country_code}_${l.name.replace(/[\s/]+/g, '_')}_${s.replace(/\//g, '-')}.csv`;
const lavori = [];
for (const l of richieste.map(risolvi)) for (const s of STAGIONI) {
  if (!l.seasons.includes(s)) { console.log(`   ${l.country_code} ${l.name} ${s}: la stagione non e' in leghe.json, salto.`); continue; }
  if (fs.existsSync(path.join(OUT, nomeFile(l, s)))) { console.log(`   ${l.country_code} ${l.name} ${s}: il file c'e' gia', salto.`); continue; }
  lavori.push({ l, s });
}
if (!lavori.length) { console.log('Niente da fare: tutte le stagioni richieste hanno gia\' il loro file.'); process.exit(0); }

// la PitchAPI: vera (Node, con la chiave) o quella finta del banco
const conta = { chiamate: 0, assenti: 0, errori: 0, riprovate: 0 };
let finta = null;
if (FINTO) finta = require('./banco-parita.js');
async function pitch(url) {
  conta.chiamate++;
  if (FINTO) {
    const b = finta.api(url);
    return b ? { status: 200, body: JSON.stringify(b) } : { status: 404, body: '{"error":"not found"}' };
  }
  for (let t = 0; ; t++) {
    try {
      const r = await fetch(url, { headers: KEY ? { 'X-API-KEY': KEY } : {}, signal: AbortSignal.timeout(45000) });
      if ((r.status === 429 || r.status >= 500) && t < 3) { conta.riprovate++; await sleep(3000 * 2 ** t); continue; }
      if (r.status === 404) conta.assenti++; else if (!r.ok) conta.errori++;
      return { status: r.status, body: await r.text() };
    } catch (e) {
      if (t < 3) { conta.riprovate++; await sleep(3000 * 2 ** t); continue; }
      conta.errori++;
      return { status: 599, body: JSON.stringify({ error: String(e.cause ? (e.cause.code || e.cause.message) : e.message) }) };
    }
  }
}

function serve() {
  return new Promise(res => {
    const srv = http.createServer((q, s) => {
      const f = path.join(ROOT, decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'index.html');
      if (!f.startsWith(ROOT)) { s.writeHead(403); return s.end(); }
      fs.readFile(f, (e, b) => {
        if (e) { s.writeHead(404); return s.end(); }
        s.writeHead(200, { 'content-type': f.endsWith('.json') ? 'application/json' : 'text/html; charset=utf-8', 'cache-control': 'no-store' });
        s.end(b);
      });
    });
    srv.listen(0, '127.0.0.1', () => res(srv));
  });
}

(async () => {
  if (!FINTO) {
    const l0 = lavori[0];
    const prova = await pitch(`${PITCH}/leagues/${l0.l.id}/matches?season=${encodeURIComponent(l0.s)}`);
    conta.chiamate = 0; conta.assenti = 0; conta.errori = 0; conta.riprovate = 0;
    const dove = 'serve la credenziale API dell\'ambiente sul sito pitchapi-proxy.salvatorepampalone-sp.workers.dev, header X-API-KEY senza prefisso';
    if (prova.status === 599) esci(`La PitchAPI non si raggiunge (${prova.body}): ${dove}.`);
    if (prova.status === 401 || prova.status === 403) esci(`La PitchAPI rifiuta la richiesta (HTTP ${prova.status}): la chiave manca o e' sbagliata; ${dove}.`);
    if (prova.status !== 200) esci(`La PitchAPI risponde HTTP ${prova.status} alla prova: ${prova.body.slice(0, 200)}`);
  }
  fs.mkdirSync(OUT, { recursive: true });
  const logFile = fs.createWriteStream(path.join(OUT, 'batch.log'), { flags: 'a' });
  const scrivi = (riga, aSchermo) => { logFile.write(`[${ora()}] ${riga}\n`); if (aSchermo) console.log(`[${ora()}] ${riga}`); };
  scrivi(`=== batch ${FINTO ? 'FINTO ' : ''}di ${lavori.length} stagioni: ${lavori.map(j => `${j.l.country_code} ${j.l.name} ${j.s}`).join(' · ')}`, true);

  const srv = await serve(); const base = 'http://127.0.0.1:' + srv.address().port;
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const ctx = await browser.newContext({ timezoneId: 'Europe/Rome', viewport: { width: 1280, height: 900 } });
  const salvati = [];
  await ctx.exposeBinding('__salvaCSV', (src, nome, testo) => {
    fs.writeFileSync(path.join(OUT, nome), testo);
    salvati.push(nome);
    const cc = (testo.match(/Copia conforme dello Scanner;([^;\r\n]*)/) || [])[1] || '?';
    const ar = (testo.match(/=== ARCHIVIO DI LEGA[^\r\n]*?(\d+) partite ===/) || [])[1] || 'assente';
    scrivi(`SALVATO ${nome} · copia conforme ${cc} · archivio ${ar} partite · chiamate API finora ${conta.chiamate}`, true);
  });
  await ctx.addInitScript(() => {
    const blobs = new Map(); const _c = URL.createObjectURL.bind(URL);
    URL.createObjectURL = b => { const u = _c(b); blobs.set(u, b); return u; };
    HTMLAnchorElement.prototype.click = function () {
      const b = blobs.get(this.href);
      if (b && this.download) b.text().then(t => window.__salvaCSV(this.download, t));
    };
  });
  await ctx.route(PITCH + '/**', async route => {
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers: CORS });
    const r = await pitch(route.request().url());
    return route.fulfill({ status: r.status, headers: { ...CORS, 'content-type': 'application/json' }, body: r.body });
  });
  const page = await ctx.newPage();
  page.setDefaultTimeout(0);
  page.on('dialog', d => d.accept());
  page.on('pageerror', e => scrivi('ERRORE NELLA PAGINA ' + e.message, true));

  await page.goto(base + '/comparatore.html');
  await page.evaluate(() => { document.getElementById('cmp-api-key').value = 'chiave-in-node'; });
  await page.evaluate(() => loadEngineFromServer());
  await page.waitForFunction(() => typeof engineReady !== 'undefined' && engineReady === true);
  const motore = await page.evaluate(() => ({ build: window.__SCANNER_BUILD, comp: window.__CMP_BUILD, storico: window.__ENGINE_LIMIT }));
  scrivi(`motore ${motore.build}, Comparatore ${motore.comp}, storico ${motore.storico} partite`, true);
  if (motore.build !== motore.comp) scrivi('ATTENZIONE: le build di motore e Comparatore non coincidono.', true);

  // il log del Comparatore finisce nel file, e a schermo le righe che contano
  let letti = 0;
  const leggiLog = async () => {
    const h = await page.evaluate(() => { const c = document.getElementById('console'); return c ? c.innerHTML : ''; }).catch(() => '');
    if (h.length < letti) letti = 0;
    const nuovo = h.slice(letti); letti = h.length;
    for (const r of nuovo.split('<br>').map(x => x.replace(/<[^>]*>/g, '').trim()).filter(Boolean))
      scrivi(r, /===|❌|Stagione fallita|NON|Copia conforme|le salto|popup/.test(r));
  };
  let ultimoStato = '';
  const timerLog = setInterval(leggiLog, 15000);
  const timer = setInterval(async () => {
    const st = await page.evaluate(() => { const b = document.getElementById('cmp-sweep-progress'); return b ? b.innerText : ''; }).catch(() => '');
    const riga = st.split('\n').find(x => /partita \d+\/\d+/.test(x)) || '';
    if (riga && riga !== ultimoStato) { ultimoStato = riga; scrivi(`${riga.replace(/^⏳\s*/, '')} · API ${conta.chiamate} chiamate, ${conta.assenti} senza dati (404), ${conta.errori} errori`, true); }
  }, 60000);

  const idLeghe = [...new Set(lavori.map(j => j.l.id))];
  await page.evaluate(({ idLeghe, lavori }) => {
    try { localStorage.removeItem(CMP_SWEEP_KEY); } catch (e) {}
    cmpLeagues = cmpLeagues.filter(l => idLeghe.includes(l.id))
      .map(l => ({ ...l, seasons: lavori.filter(j => j.id === l.id).map(j => j.s) }));
    document.getElementById('cmp-sweep-cups').checked = true;
  }, { idLeghe, lavori: lavori.map(j => ({ id: j.l.id, s: j.s })) });
  const t0 = Date.now();
  await page.evaluate(() => cmpSweepStart(false));
  clearInterval(timer); clearInterval(timerLog);
  await leggiLog();
  await sleep(1500);

  const mancano = lavori.filter(j => !fs.existsSync(path.join(OUT, nomeFile(j.l, j.s))));
  scrivi(`=== fine in ${((Date.now() - t0) / 60000).toFixed(1)} minuti: ${salvati.length} file salvati, API ${conta.chiamate} chiamate `
       + `(${conta.assenti} senza dati, ${conta.errori} fallite, ${conta.riprovate} riprovate)${mancano.length ? ' · SENZA FILE: ' + mancano.map(j => `${j.l.name} ${j.s}`).join(', ') : ''}`, true);
  await browser.close(); srv.close(); logFile.end();
  process.exit(mancano.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
