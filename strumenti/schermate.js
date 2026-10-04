// SCHERMATE DELLO SCANNER: la pagina della cartella di lavoro, come la vede il telefono.
//
// Apre scanner.html da un server locale, fa un'analisi intera come l'utente (database della
// lega, poi la partita) e salva una schermata per ogni passo e ogni scheda: setup, anello,
// Partita, Tabellone, Squadre (formazioni, giocatori, ruolo e generale), Numeri, Prompt, Dati,
// foglio Altro. Poi misura lo scorrimento laterale in ogni scheda con tutte le details aperte.
//
//   node strumenti/schermate.js                                   lega finta del banco, nessuna chiamata
//   node strumenti/schermate.js --vera "Juventus|Atalanta|2026-09-20"     PitchAPI vera, Serie A
//   node strumenti/schermate.js --vera "Lausanne|Lugano|2026-09-20" --lega "Super League"
//
// --vera "Casa|Trasferta|AAAA-MM-GG": i nomi come nel menu dello Scanner. La chiave la aggiunge il
//   proxy dell'ambiente (vedi AGENTS.md, Il batch automatico); un'analisi costa 200-300 chiamate.
// --lega: id o nome di leghe.json, PAESE:Nome se ambiguo (di default Serie A).
// --stagione: di default quella che contiene la data.
// --out: di default <cartella temporanea>/schermate. --nome: prefisso dei file (finta o vera).
// --larghezza: di default 390. --ridotto: movimento ridotto (i numeri finali, senza animazioni).
// Esce con 1 se ci sono errori nella pagina, l'anello non si chiude o una scheda scorre di lato.
'use strict';
const { spawnSync } = require('child_process');
const VERA_ARG = process.argv.includes('--vera');
if (VERA_ARG && process.env.HTTPS_PROXY && !process.env.NODE_USE_ENV_PROXY) {
  const r = spawnSync(process.execPath, ['--no-warnings', __filename, ...process.argv.slice(2)],
                      { stdio: 'inherit', env: { ...process.env, NODE_USE_ENV_PROXY: '1' } });
  process.exit(r.status == null ? 1 : r.status);
}
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = process.env.ROOT || path.resolve(__dirname, '..');
const PITCH = 'https://pitchapi-proxy.salvatorepampalone-sp.workers.dev';
const arg = (nome, def) => { const i = process.argv.indexOf('--' + nome); return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : def; };
const VERA = VERA_ARG ? arg('vera', '') : '';
const OUT = path.resolve(arg('out', path.join(os.tmpdir(), 'schermate')));
const NOME = arg('nome', VERA ? 'vera' : 'finta');
const W = +arg('larghezza', 390);
const RIDOTTO = process.argv.includes('--ridotto');
const KEY = process.env.PITCHAPI_KEY || '';
const sleep = ms => new Promise(r => setTimeout(r, ms));
function esci(msg) { console.error(msg); process.exit(1); }
fs.mkdirSync(OUT, { recursive: true });

const LEGHE = JSON.parse(fs.readFileSync(path.join(ROOT, 'leghe.json'), 'utf8')).data.leagues;
function risolvi(x) {
  const [cc, nome] = x.includes(':') ? x.split(':') : [null, x];
  const trov = LEGHE.filter(l => l.id === x || (l.name.toLowerCase() === nome.toLowerCase() && (!cc || l.country_code === cc)));
  if (trov.length === 1) return trov[0];
  if (!trov.length) esci(`Lega "${x}" non trovata in leghe.json.`);
  esci(`Lega "${x}" ambigua: ${trov.map(l => l.country_code + ':' + l.name).join(', ')}. Scrivi PAESE:Nome.`);
}

let partita = null, lega = null, stagione = null, finta = null;
if (VERA) {
  const [casa, trasf, giorno] = VERA.split('|').map(s => (s || '').trim());
  if (!casa || !trasf || !/^\d{4}-\d{2}-\d{2}$/.test(giorno || '')) esci('--vera vuole "Casa|Trasferta|AAAA-MM-GG".');
  partita = { casa, trasf, giorno };
  lega = risolvi(arg('lega', 'l_0ALvwF'));
  const y = +giorno.slice(0, 4), m = +giorno.slice(5, 7);
  stagione = arg('stagione', [m >= 7 ? `${y}/${y + 1}` : `${y - 1}/${y}`, String(y)].find(s => lega.seasons.includes(s)));
  if (!stagione || !lega.seasons.includes(stagione)) esci(`Stagione non trovata per ${lega.name} il ${giorno}: indica --stagione.`);
} else {
  finta = require('./banco-parita.js');
  lega = { id: finta.LEAGUE, country_code: finta.COUNTRY, name: 'lega finta' };
  stagione = '2025/2026';
}

(async () => {
  const srv = http.createServer((q, s) => {
    const f = path.join(ROOT, decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'index.html');
    fs.readFile(f, (e, b) => { if (e) { s.writeHead(404); return s.end(); } s.writeHead(200, { 'content-type': f.endsWith('.json') ? 'application/json' : 'text/html; charset=utf-8' }); s.end(b); });
  });
  await new Promise(r => srv.listen(0, '127.0.0.1', r));
  const base = 'http://127.0.0.1:' + srv.address().port;
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const ctx = await browser.newContext({ viewport: { width: W, height: 844 }, deviceScaleFactor: 2, timezoneId: 'Europe/Rome', reducedMotion: RIDOTTO ? 'reduce' : 'no-preference' });
  const page = await ctx.newPage();
  const errori = [];
  let chiamate = 0;
  page.on('dialog', d => { errori.push('DIALOG ' + d.message()); d.accept(); });
  page.on('pageerror', e => errori.push('PAGEERROR ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errori.push('CONSOLE ' + m.text().slice(0, 200)); });
  await page.route(PITCH + '/**', async route => {
    const u = route.request().url(); chiamate++;
    if (finta) {
      const body = finta.api(u);
      if (!body) return route.fulfill({ status: 404, contentType: 'application/json', body: '{"error":"not found"}' });
      if (typeof body === 'string') return route.fulfill({ status: 200, contentType: 'text/csv', headers: { 'access-control-allow-origin': '*' }, body });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    }
    for (let t = 0; ; t++) {
      try {
        const r = await fetch(u, { headers: KEY ? { 'X-API-KEY': KEY } : {}, signal: AbortSignal.timeout(45000) });
        if ((r.status === 429 || r.status >= 500) && t < 3) { await sleep(2000 * 2 ** t); continue; }
        return route.fulfill({ status: r.status, headers: { 'content-type': r.headers.get('content-type') || 'application/json', 'access-control-allow-origin': '*' }, body: Buffer.from(await r.arrayBuffer()) });
      } catch (e) {
        if (t >= 3) return route.fulfill({ status: 599, body: String(e) });
        await sleep(2000 * 2 ** t);
      }
    }
  });
  const file = [];
  const foto = async (nome, attesa) => {
    await page.waitForTimeout(attesa == null ? (RIDOTTO ? 400 : 1800) : attesa);
    const p = path.join(OUT, `${NOME}-${nome}.png`); await page.screenshot({ path: p }); file.push(p);
  };

  await page.goto(base + '/scanner.html');
  await page.waitForFunction(() => document.getElementById('sel-country').options.length > 2);
  await foto('00-setup');
  await page.evaluate(({ cc, id, s, k }) => {
    const v = (x, y) => { document.getElementById(x).value = y; };
    v('sel-country', cc); updateLeagues(); v('sel-league', id); updateSeasons(); v('sel-season', s); v('api-key', k);
  }, { cc: lega.country_code, id: lega.id, s: stagione, k: VERA ? 'nel-proxy' : 'finta' });
  await page.evaluate(() => caricaSquadreLega());
  const scelta = await page.evaluate(p => {
    const sel = (id, v) => { document.getElementById(id).value = v; };
    if (!p) {
      const L = globalLeagueMatchesCache.filter(x => x._season === '2025/2026' && x.status === 'finished').sort((a, b) => a.time_utc < b.time_utc ? -1 : 1);
      const x = L[Math.floor(L.length * 0.7)];
      sel('sel-home', x.home_team.id); sel('sel-away', x.away_team.id); sel('target-date', x.time_utc.slice(0, 10));
      return x.home_team.name + ' - ' + x.away_team.name + ' del ' + x.time_utc.slice(0, 10);
    }
    const trova = (id, nome) => { const s = document.getElementById(id); const o = [...s.options].find(z => z.text.trim().toLowerCase() === nome.toLowerCase()); if (o) s.value = o.value; return !!o; };
    if (!trova('sel-home', p.casa) || !trova('sel-away', p.trasf)) return null;
    sel('target-date', p.giorno);
    return p.casa + ' - ' + p.trasf + ' del ' + p.giorno;
  }, partita);
  if (!scelta) esci(`Squadre non trovate nel menu di ${lega.name} ${stagione}: scrivi i nomi come li mostra lo Scanner.`);
  console.log(`partita: ${scelta} (${lega.country_code} ${lega.name} ${stagione}), chiamate per il database ${chiamate}`);
  await foto('01-setup-pronto');

  const corsa = page.evaluate(() => analizzaUna());
  await page.waitForTimeout(VERA ? 3000 : 250);
  await page.screenshot({ path: path.join(OUT, `${NOME}-02-anello.png`) }); file.push(path.join(OUT, `${NOME}-02-anello.png`));
  await corsa;
  await page.evaluate(async () => { try { await window.__QUOTE_AUTO; } catch (e) {} });
  await page.waitForFunction(() => document.getElementById('analisi-corso').hidden, null, { timeout: 20000 }).catch(() => errori.push("ANELLO l'analisi in corso non si e' chiusa"));
  if (!(await page.evaluate(() => !!window.__ESITO))) errori.push("ESITO il motore non e' arrivato in fondo (window.__ESITO assente)");
  const quote = await page.evaluate(() => { const q = document.getElementById('quote-auto'); return q ? q.textContent.trim().slice(0, 160) : ''; });
  console.log(`analisi fatta, chiamate ${chiamate}${quote ? ', quote: ' + quote : ''}`);

  await page.evaluate(() => window.scrollTo(0, 0)); await foto('03-partita');
  await page.evaluate(() => window.scrollTo(0, 760)); await foto('04-partita-giu');
  await page.evaluate(() => window.scrollTo(0, 1500)); await foto('05-partita-quote');
  await page.evaluate(() => { schedaVai('tabellone'); window.scrollTo(0, 0); }); await foto('06-tabellone');
  let n = 7;
  for (const k of ['formazioni', 'giocatori', 'ambiti']) {
    await page.evaluate(k => { squadreVai(k); window.scrollTo(0, 0); }, k); await foto(String(n++).padStart(2, '0') + '-squadre-' + k);
  }
  await page.evaluate(() => { schedaVai('numeri'); window.scrollTo(0, 0); }); await foto(String(n++).padStart(2, '0') + '-numeri');
  await page.evaluate(() => { document.querySelectorAll('[data-scheda="numeri"] details.card').forEach((d, i) => { if (i < 3) d.open = true; }); window.scrollTo(0, 0); });
  await foto(String(n++).padStart(2, '0') + '-numeri-aperte');
  for (const k of ['prompt', 'dati']) { await page.evaluate(k => { schedaVai(k); window.scrollTo(0, 0); }, k); await foto(String(n++).padStart(2, '0') + '-' + k); }
  await page.evaluate(() => { schedaVai('partita'); const a = document.querySelector('#nav-sezioni [data-k="altro"]'); if (a) a.click(); });
  await foto(String(n++).padStart(2, '0') + '-altro');

  const scorre = await page.evaluate(() => {
    document.querySelectorAll('.foglio').forEach(f => { f.hidden = true; });
    const r = {}, misura = nome => { document.querySelectorAll('details').forEach(d => { d.open = true; }); r[nome] = document.documentElement.scrollWidth - window.innerWidth; };
    for (const k of ['partita', 'tabellone', 'numeri', 'prompt', 'dati']) { schedaVai(k, false); misura(k); }
    for (const k of ['formazioni', 'giocatori', 'ambiti']) { squadreVai(k); misura('squadre/' + k); }
    schedaVai('partita', false); return r;
  });
  const larghe = Object.entries(scorre).filter(([, v]) => v > 0);
  console.log('scorrimento laterale: ' + Object.entries(scorre).map(([k, v]) => `${k} ${v}`).join(', '));
  console.log(errori.length ? errori.slice(0, 15).join('\n') : 'nessun errore nella pagina');
  console.log(`${file.length} schermate in ${OUT}`);
  await browser.close(); srv.close();
  process.exit(errori.length || larghe.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
