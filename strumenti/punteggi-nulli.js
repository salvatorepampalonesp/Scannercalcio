// Una partita conclusa SENZA punteggio vale come una partita che non c'e' (dal b97; AGENTS.md, Politica sui valori
// mancanti). Fino al b96 l'Elo e lo storico di squadra la contavano 0-0.
//
//   node strumenti/punteggi-nulli.js                              il motore della cartella di lavoro
//   node strumenti/punteggi-nulli.js <scanner.html di prima>      anche il controllo di potenza col motore di prima
//
// Lega finta del banco, nessuna chiamata. Tre giri dello Scanner sulla stessa partita: l'archivio com'e'; con una
// partita dello storico della casa senza punteggio (stato finished, score null); con quella partita tolta. Il secondo
// deve dare gli stessi numeri del terzo (1X2, Elo, HFA, storico, media di lega, lambda, tabellone) e numeri diversi dal
// primo. Col motore di prima, se lo si passa, il secondo NON deve dare i numeri del terzo. Esce con 1 se non torna.
// Riposo e stanchezza restano fuori dal confronto: una partita giocata senza punteggio conta come giocata.
const http = require('http'), fs = require('fs'), path = require('path'), { chromium } = require('playwright');
const ROOT = process.env.ROOT || path.join(__dirname, '..'), finta = require('./banco-parita.js');
const PRIMA = process.argv[2] || process.env.VECCHIO || null, PAGINE = { nuovo: path.join(ROOT, 'scanner.html'), prima: PRIMA };
(async () => {
  const srv = http.createServer((q, s) => {
    const u = decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, ''), m = /^(nuovo|prima)\/scanner\.html$/.exec(u);
    const f = m ? PAGINE[m[1]] : path.join(ROOT, u.replace(/^(nuovo|prima)\//, ''));
    fs.readFile(f, (e, b) => { if (e) { s.writeHead(404); return s.end(); } s.writeHead(200, { 'content-type': f.endsWith('.json') ? 'application/json' : 'text/html; charset=utf-8', 'cache-control': 'no-store' }); s.end(b); });
  });
  await new Promise(r => srv.listen(0, '127.0.0.1', r));
  const base = 'http://127.0.0.1:' + srv.address().port, browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  async function giro(motore, modo, bersaglio) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' }), page = await ctx.newPage(), err = [];
    page.on('dialog', d => { err.push('DIALOG ' + d.message()); d.accept(); }); page.on('pageerror', e => err.push('PAGEERROR ' + e.message));
    await page.route(finta.PITCH + '/**', route => {
      let body = finta.api(route.request().url());
      if (!body) return route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
      if (typeof body === 'string') return route.fulfill({ status: 200, contentType: 'text/csv', headers: { 'access-control-allow-origin': '*' }, body });
      if (bersaglio && modo !== 'intero' && body.data && Array.isArray(body.data.matches))
        body = { data: { ...body.data, matches: body.data.matches.filter(m => !(modo === 'tolta' && m.id === bersaglio.guasta))
          .map(m => (modo === 'nulla' && m.id === bersaglio.guasta) ? { ...m, score_home: null, score_away: null } : m) } };
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    });
    await page.goto(base + '/' + motore + '/scanner.html');
    await page.waitForFunction(() => document.getElementById('sel-country').options.length > 2);
    await page.evaluate(({ cc, id }) => { const v = (x, y) => { document.getElementById(x).value = y; };
      v('sel-country', cc); updateLeagues(); v('sel-league', id); updateSeasons(); v('sel-season', '2025/2026'); v('api-key', 'finta'); }, { cc: finta.COUNTRY, id: finta.LEAGUE });
    await page.evaluate(() => caricaSquadreLega());
    const scelta = await page.evaluate(b => {
      const L = globalLeagueMatchesCache.filter(x => x._season === '2025/2026' && x.status === 'finished' && x.score_home != null).sort((a, c) => a.time_utc < c.time_utc ? -1 : 1);
      const x = b ? L.find(m => m.id === b.id) : L[Math.floor(L.length * 0.7)];
      const prima = L.filter(m => m.time_utc.slice(0, 10) < x.time_utc.slice(0, 10) && (m.home_team.id === x.home_team.id || m.away_team.id === x.home_team.id));
      const g = prima[prima.length - 3];           // la terzultima della casa prima del bersaglio: sta nello storico e nell'Elo
      ['sel-home', 'sel-away'].forEach((id, i) => { document.getElementById(id).value = i ? x.away_team.id : x.home_team.id; });
      document.getElementById('target-date').value = x.time_utc.slice(0, 10);
      return { id: x.id, nome: x.home_team.name + ' - ' + x.away_team.name + ' del ' + x.time_utc.slice(0, 10), guasta: g.id,
               guastaNome: g.home_team.name + ' - ' + g.away_team.name + ' ' + g.score_home + '-' + g.score_away + ' del ' + g.time_utc.slice(0, 10),
               nulle: globalLeagueMatchesCache.filter(m => m.status === 'finished' && m.score_home == null).length, tot: globalLeagueMatchesCache.length };
    }, bersaglio);
    await page.evaluate(() => avviaScanner());
    await page.waitForFunction(() => window.__ESITO && window.__QUOTE_CTX, null, { timeout: 120000 });
    const out = await page.evaluate(() => { const E = window.__ELO_DEBUG_OVER, S = window.__SCOPE_DEBUG, U = window.__UNIT_DEBUG, r = x => +x.toFixed(6);
      return { p: window.__ESITO.p.map(r), motore: window.__QUOTE_CTX.pm.map(r), eloDiff: E.eloDiff, hfa: E.hfa, lgElo: r(E.lgElo), lgModel: r(E.lgModel), nHo: S.nHo, nHr: S.nHr, nAo: S.nAo,
               lgN: U.lgN, lgH: r(U.lgH), rho: U.rho, lam: window.__QUOTE_CTX.lam.map(r), tab: (window.__VERDETTI || []).map(v => v.key + ' ' + (v.edge == null ? '' : v.edge.toFixed(2))).join(' | ') }; });
    await ctx.close();
    return { scelta, out, err };
  }
  const A = await giro('nuovo', 'intero', null), B = A.scelta, R = { nuovo: {}, prima: {} }; let errori = 0;
  console.log('bersaglio: ' + B.nome + ' | partita senza punteggio: ' + B.guastaNome);
  for (const mot of PRIMA ? ['nuovo', 'prima'] : ['nuovo']) for (const modo of ['intero', 'nulla', 'tolta']) {
    const g = (mot === 'nuovo' && modo === 'intero') ? A : await giro(mot, modo, B); R[mot][modo] = g.out; errori += g.err.length;
    console.log(`${(mot === 'nuovo' ? 'motore' : 'di prima').padEnd(8)} ${modo.padEnd(6)} archivio ${g.scelta.tot} (senza punteggio ${g.scelta.nulle}) | 1X2 ${g.out.p.map(x => (100 * x).toFixed(2)).join(' ')} | Elo ${g.out.eloDiff} HFA ${g.out.hfa}`
      + ` | storico casa ${g.out.nHo} (ruolo ${g.out.nHr}) | lega ${g.out.lgN} | lambda ${g.out.lam.map(x => x.toFixed(3)).join(' ')}` + (g.err.length ? ' | ERRORI ' + g.err.join('; ') : ''));
  }
  const ug = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const ok1 = ug(R.nuovo.nulla, R.nuovo.tolta), ok2 = !ug(R.nuovo.nulla, R.nuovo.intero);
  console.log(`motore: senza punteggio come tolta ${ok1 ? 'SI' : 'NO'}; diversa dall'archivio intero ${ok2 ? 'SI' : 'NO'}`);
  let ok3 = true, ok4 = true;
  if (PRIMA) { ok3 = !ug(R.prima.nulla, R.prima.tolta); ok4 = ug(R.nuovo.intero, R.prima.intero) && ug(R.nuovo.tolta, R.prima.tolta);
    console.log(`motore di prima: senza punteggio come tolta ${ok3 ? 'NO (la contava 0-0: il controllo ha potere)' : 'SI'}; sugli archivi senza guasti i due motori ${ok4 ? 'coincidono' : 'NON coincidono'}`); }
  await browser.close(); srv.close();
  process.exit(ok1 && ok2 && ok3 && ok4 && !errori ? 0 : 1);
})();
