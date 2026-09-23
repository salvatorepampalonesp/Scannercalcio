// BANCO DI PROVA DELLA COPIA CONFORME: il Comparatore stampa quello che stampa lo Scanner?
//
// Una lega finta (10 squadre, tre stagioni, generata in modo deterministico dall'id della
// partita) servita al posto di PitchAPI. Lo Scanner si guida come lo usa l'utente, il
// Comparatore gira in tutte le sue modalita', e si confrontano OGNI scrittura a schermo del
// motore (safeTxt/safeHtml) e ogni riga del CSV che riporta un numero dello Scanner.
// Tre modalita' sono controlli di potenza: il certificato DEVE dire NO.
//
//   node strumenti/banco-parita.js                      tutte le modalita', ~3 minuti
//   MODES=singola,batch node strumenti/banco-parita.js  solo alcune
//   MOBILE=1 ...                                        pagine a 390px, e si misura lo scorrimento laterale
//   VECCHIO=/percorso/scanner-vecchio.html MODES=vecchio ...   il Comparatore con un motore diverso dal pubblicato
//   PENDENTI=1 ...                                      due partite prima della data risultano non concluse
//
// Esce con 0 se tutto e' come deve essere. Il dettaglio va in $OUT/parita-report.json
// (di default la cartella temporanea). AGENTS.md, Il Comparatore stampa come lo Scanner.
'use strict';
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = process.env.ROOT || path.resolve(__dirname, '..');
const OUT = process.env.OUT || os.tmpdir();
const PITCH = 'https://pitchapi-proxy.salvatorepampalone-sp.workers.dev';
const LEAGUE = 'l_0ALvwF';           // Serie A in leghe.json: serve all'interfaccia dello Scanner
const COUNTRY = 'ITA';
const SEASONS = ['2023/2024', '2024/2025', '2025/2026'];
const MODES = (process.env.MODES || ('singola,giorno,intervallo,batch,sweep,ab,sconfina' + (process.env.VECCHIO ? ',vecchio' : ''))).split(',');
const CONTROLLI = { ab: ['ELO_SCALE', 'storico'], vecchio: ['motore caricato diverso'] };
const ROUND_TARGET = +(process.env.ROUND || 11);

// ---------- lega sintetica, deterministica sull'id ----------
function hash(str) { let h = 2166136261 >>> 0; for (const c of str) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619) >>> 0; } return h || 1; }
function rng(seed) { let s = hash(seed); return () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; }; }
function pois(lam, r) { const L = Math.exp(-lam); let k = 0, p = 1; do { k++; p *= r(); } while (p > L && k < 30); return k - 1; }
const NAMES = ['Aquile', 'Bisonti', 'Cervi', 'Delfini', 'Falchi', 'Grifoni', 'Lupi', 'Orsi', 'Pantere', 'Tori', 'Volpi'];
const teamsOf = si => si < 2 ? [0,1,2,3,4,5,6,7,8,9] : [0,1,2,3,4,5,6,7,8,10];   // la 10 e' neopromossa
const team = i => ({ id: 't_' + i, name: NAMES[i] });
const str = i => { const r = rng('forza' + i); return { att: 0.7 + 0.6 * r(), def: 0.7 + 0.6 * r(), cards: 0.8 + 0.5 * r(), cor: 0.8 + 0.4 * r() }; };

const MATCHES = {}; const BY_SEASON = {};
SEASONS.forEach((s, si) => {
  const ts = teamsOf(si), n = ts.length, rounds = [];
  const arr = ts.slice();
  for (let r = 0; r < n - 1; r++) {
    const pr = [];
    for (let k = 0; k < n / 2; k++) { const a = arr[k], b = arr[n - 1 - k]; pr.push(r % 2 ? [b, a] : [a, b]); }
    rounds.push(pr);
    arr.splice(1, 0, arr.pop());
  }
  const all = rounds.concat(rounds.map(pr => pr.map(([a, b]) => [b, a])));
  const y = 2023 + si; const t0 = Date.UTC(y, 7, 19);
  const slots = [[0, '14:00:00'], [0, '17:00:00'], [0, '19:45:00'], [1, '11:30:00'], [1, '18:45:00']];
  BY_SEASON[s] = [];
  all.forEach((pr, ri) => pr.forEach(([h, a], k) => {
    const id = `m${si}r${ri}k${k}`;
    const day = new Date(t0 + (ri * 14 + slots[k][0]) * 86400000).toISOString().slice(0, 10);
    const r = rng(id + 'score'), H = str(h), A = str(a);
    const lamH = 1.45 * H.att / A.def, lamA = 1.15 * A.att / H.def;
    const m = { id, home_team: team(h), away_team: team(a), status: 'finished',
                time_utc: `${day}T${slots[k][1]}Z`, score_home: pois(lamH, r), score_away: pois(lamA, r),
                _lam: [lamH, lamA], _si: si, _ri: ri };
    MATCHES[id] = m; BY_SEASON[s].push(m);
  }));
});

const PEND = new Set(process.env.PENDENTI ? ['m2r10k0', 'm2r10k1'] : []);
const pub = m => PEND.has(m.id) ? ({ id: m.id, home_team: { ...m.home_team }, away_team: { ...m.away_team }, status: 'scheduled',
                    time_utc: m.time_utc, score_home: null, score_away: null })
  : ({ id: m.id, home_team: { ...m.home_team }, away_team: { ...m.away_team }, status: m.status,
                    time_utc: m.time_utc, score_home: m.score_home, score_away: m.score_away });
const r2 = v => Math.round(v * 100) / 100;

function statsOf(m) {
  const r = rng(m.id + 'stats'); const [lH, lA] = m._lam; const H = str(+m.home_team.id.slice(2)), A = str(+m.away_team.id.slice(2));
  const side = (lam, st, gf) => {
    const xg = r2(Math.max(0.05, lam * (0.75 + 0.5 * r()))); const pen = r() < 0.2 ? 0.76 : 0;
    const shots = Math.round(xg * 9 + 3 + 4 * r()); const sot = Math.max(gf, Math.round(shots * (0.28 + 0.15 * r())));
    return { xg, npxg: r2(Math.max(0.03, xg - pen)), xgot: r2(xg * (0.8 + 0.5 * r())), shots, sot,
             cor: pois(4.7 * st.cor, r), yel: pois(1.9 * st.cards, r), fouls: pois(11.5, r),
             bc: pois(xg * 2.2, r), bcm: 0, box: Math.round(18 + 14 * xg + 6 * r()), xgsp: r2(xg * (0.15 + 0.2 * r())) };
  };
  const h = side(lH, H, m.score_home), a = side(lA, A, m.score_away);
  h.bcm = Math.max(0, h.bc - m.score_home); a.bcm = Math.max(0, a.bc - m.score_away);
  const possH = Math.round(50 + 20 * (H.att - A.att) + 6 * (r() - 0.5));
  const it = (key, title, hv, av) => ({ key, title, home: String(hv), away: String(av) });
  return { data: { periods: [{ period: 'All', groups: [
    { name: 'Expected', items: [it('expected_goals', 'Expected goals', h.xg, a.xg), it('npxg', 'Non-penalty xG', h.npxg, a.npxg),
                                it('expected_goals_on_target', 'xG on target', h.xgot, a.xgot), it('expected_goals_set_play', 'xG set play', h.xgsp, a.xgsp)] },
    { name: 'Shots', items: [it('totalshots', 'Total shots', h.shots, a.shots), it('ShotsOnTarget', 'Shots on target', h.sot, a.sot),
                             it('bigchances', 'Big chances', h.bc, a.bc), it('bigchancesmissed', 'Big chances missed', h.bcm, a.bcm)] },
    { name: 'General', items: [it('BallPossesion', 'Ball possession', possH + '%', (100 - possH) + '%'), it('corners', 'Corner kicks', h.cor, a.cor),
                               it('yellow_cards', 'Yellow cards', h.yel, a.yel), it('fouls', 'Fouls', h.fouls, a.fouls),
                               it('touches_in_opp_box', 'Touches in opposition box', h.box, a.box)] }
  ] }] } };
}

function advOf(m) {
  if (m._si === 0) return null;   // come l'API vera: niente /advanced sulle stagioni vecchie
  const r = rng(m.id + 'adv'); const [lH, lA] = m._lam;
  const one = (tid, lam, opLam, st) => {
    const q = lam / 1.3, v = (base, sp) => r2(base * q * (0.8 + sp * r()));
    return { team: { id: tid },
      defending: { ppda: r2(8 + 8 * r() / q), avg_defensive_action_x: r2(35 + 10 * r()), counterpress_regains_5s: Math.round(3 + 6 * r()),
                   ball_recovery_time: r2(10 + 8 * r()), tackles: Math.round(14 + 8 * r()), interceptions: Math.round(8 + 6 * r()),
                   blocks: Math.round(3 + 4 * r()), clearances: Math.round(12 + 14 * r() / q), duels_won: Math.round(40 + 20 * r()),
                   aerials: 30 + Math.round(10 * r()), aerials_won: Math.round(10 + 8 * r()), challenges: Math.round(10 + 6 * r()),
                   opponent_passes: Math.round(250 + 150 * r()), defensive_actions: Math.round(25 + 15 * r()) },
      territory: { field_tilt: r2(35 + 30 * q * r()), avg_action_x: r2(45 + 10 * r()), final_third_entries: Math.round(30 + 25 * q * r()),
                   touches_in_opp_box: Math.round(15 + 20 * q * r()) },
      tempo: { direct_speed: r2(1 + 1.5 * r()), sequence_time: r2(8 + 6 * r()) },
      creation: { gca: v(2, 1), sca: v(20, 0.6), xag: v(1.1, 0.8), chances_created: v(9, 0.7), second_assists: v(0.6, 1), xg_per_shot: r2(0.08 + 0.06 * r()),
                  sca_breakdown: { pass_live: v(14, 0.6), pass_dead: v(3, 0.8), take_on: v(1.5, 1), shot: v(1, 1), foul_drawn: v(1, 1), defensive: v(0.5, 1) } },
      passing: { passes: Math.round(350 + 250 * r()), key_passes: v(9, 0.6), switches: Math.round(3 + 6 * r()), progressive_pass_distance: Math.round(1500 + 1200 * r()),
                 assists: v(0.9, 1), progressive_passes: v(35, 0.5), passes_into_box: v(10, 0.6), crosses: Math.round(10 + 12 * r()), through_balls: Math.round(1 + 4 * r()) },
      carrying: { carries: Math.round(300 + 200 * r()), carry_distance: Math.round(4000 + 2500 * r()), carries_into_final_third: v(15, 0.6), take_ons: v(16, 0.6),
                  progressive_carry_distance: Math.round(1500 + 1000 * r()), take_ons_won: v(8, 0.6), miscontrols: Math.round(8 + 8 * r()),
                  dispossessed: Math.round(5 + 6 * r()), carries_into_box: v(6, 0.7), progressive_carries: v(22, 0.6) },
      possession_value: { xt_total: v(1.4, 0.7), vaep_total: r2(0.2 + (q - 1) + 0.6 * (r() - 0.5)), vaep_offensive: v(1.5, 0.6),
                          vaep_defensive: r2(-0.4 - 0.5 * r()), pv_total: r2(0.1 + (q - 1) + 0.5 * (r() - 0.5)), pv_offensive: v(1.2, 0.6), pv_defensive: r2(-0.3 - 0.4 * r()) } };
  };
  const H = str(+m.home_team.id.slice(2)), A = str(+m.away_team.id.slice(2));
  return { data: { teams: [one(m.home_team.id, lH, lA, H), one(m.away_team.id, lA, lH, A)] } };
}

function eventsOf(m) {
  const r = rng(m.id + 'ev'); const ev = [];
  const add = (tid, n) => { for (let i = 0; i < n; i++) ev.push({ event_type: 'goal', team_id: tid, minute: 1 + Math.floor(r() * 94),
                            is_own_goal: false, player: { name: 'Giocatore ' + tid.slice(2) + '-' + Math.floor(r() * 6) } }); };
  add(m.home_team.id, m.score_home); add(m.away_team.id, m.score_away);
  if (r() < 0.12) ev.push({ event_type: 'redcard', team_id: r() < 0.5 ? m.home_team.id : m.away_team.id, minute: 60 });
  return { data: { events: ev } };
}
const FORM = ['4-3-3', '4-2-3-1', '3-5-2', '4-4-2', '3-4-3'];
const lineupsOf = m => ({ data: { home: { formation: FORM[hash(m.home_team.id) % 5] }, away: { formation: FORM[hash(m.away_team.id + 'a') % 5] } } });

let API_CALLS = 0;
function api(url) {
  API_CALLS++;
  const u = new URL(url); const p = u.pathname;
  let mm = p.match(/^\/leagues\/([^/]+)\/matches$/);
  if (mm) {
    const s = u.searchParams.get('season');
    if (mm[1] === LEAGUE && BY_SEASON[s]) return { data: { matches: BY_SEASON[s].map(pub) } };
    return { data: { matches: [] } };
  }
  mm = p.match(/^\/matches\/([^/]+)\/(stats|lineups|advanced|events)$/);
  if (mm && MATCHES[mm[1]]) {
    const m = MATCHES[mm[1]];
    if (mm[2] === 'stats') return statsOf(m);
    if (mm[2] === 'lineups') return lineupsOf(m);
    if (mm[2] === 'events') return eventsOf(m);
    if (mm[2] === 'advanced') return advOf(m);
  }
  return null;
}

// ---------- server statico e strumentazione ----------
function serve() {
  return new Promise(res => {
    const srv = http.createServer((q, s) => {
      const f = path.join(ROOT, decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'index.html');
      fs.readFile(f, (e, b) => { if (e) { s.writeHead(404); return s.end(); }
        s.writeHead(200, { 'content-type': f.endsWith('.json') ? 'application/json' : 'text/html; charset=utf-8', 'cache-control': 'no-store' }); s.end(b); });
    });
    srv.listen(0, '127.0.0.1', () => res(srv));
  });
}

// registra OGNI scrittura a schermo del motore, nei due file allo stesso modo
const REC_TXT = "const safeTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };";
const REC_HTML = "const safeHtml = (id, val) => { const el = document.getElementById(id); if (el) el.innerHTML = val; };";
function instrument(src) {
  if (!src.includes(REC_TXT) || !src.includes(REC_HTML)) throw new Error('safeTxt/safeHtml hanno cambiato forma: aggiorna il banco');
  return src.replace(REC_TXT, "const safeTxt = (id, val) => { try { (window.__REC_CUR = window.__REC_CUR || []).push(['t', id, String(val)]); } catch (e) {} const el = document.getElementById(id); if (el) el.textContent = val; };")
            .replace(REC_HTML, "const safeHtml = (id, val) => { try { (window.__REC_CUR = window.__REC_CUR || []).push(['h', id, String(val)]); } catch (e) {} const el = document.getElementById(id); if (el) el.innerHTML = val; };");
}

async function newPage(browser, base) {
  const ctx = await browser.newContext({ acceptDownloads: false, timezoneId: 'Europe/Rome',
                                         viewport: process.env.MOBILE ? { width: 390, height: 844 } : { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  page.setDefaultTimeout(0);
  page.__log = [];
  page.on('dialog', d => { page.__log.push('DIALOG ' + d.type() + ': ' + d.message().slice(0, 160)); d.type() === 'prompt' ? d.accept('') : d.accept(); });
  page.on('pageerror', e => page.__log.push('PAGEERROR ' + e.message));
  page.on('console', m => { if (m.type() === 'error') page.__log.push('CONSOLE ' + m.text().slice(0, 200)); });
  await page.route(PITCH + '/**', async route => {
    const body = api(route.request().url());
    if (!body) return route.fulfill({ status: 404, contentType: 'application/json', body: '{"error":"not found"}' });
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.route(base + '/scanner.html*', async route => {
    const src = fs.readFileSync(path.join(ROOT, 'scanner.html'), 'utf8');
    return route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: instrument(src) });
  });
  await page.addInitScript(() => {
    window.__CSVS = [];
    const _c = URL.createObjectURL.bind(URL);
    URL.createObjectURL = (b) => { try { if (b && b.text) b.text().then(t => window.__CSVS.push(t)); } catch (e) {} return _c(b); };
    HTMLAnchorElement.prototype.click = function () { (window.__DL = window.__DL || []).push(this.download || this.href); };
  });
  return page;
}

// Lo stato del motore dopo un giro: le scritture a schermo e quello che il motore espone
const SNAP = `(() => ({ rec: window.__REC_CUR || [], verd: JSON.parse(JSON.stringify(window.__VERDETTI || null)),
  verdTxt: window.__VERDETTI_TXT || null, master: JSON.parse(JSON.stringify(window.__MASTER || null)),
  confMk: JSON.parse(JSON.stringify(window.__CONF_MK || null)) }))()`;

async function runScanner(browser, base, matches, limit) {
  const page = await newPage(browser, base);
  await page.goto(base + '/scanner.html');
  await page.waitForFunction(() => document.getElementById('sel-country').options.length > 2);
  await page.evaluate(({ COUNTRY, LEAGUE }) => {
    const s = (id, v) => { const el = document.getElementById(id); el.value = v; if (el.value !== v) throw new Error('select ' + id + ' ' + v); };
    s('sel-country', COUNTRY); updateLeagues(); s('sel-league', LEAGUE); updateSeasons(); s('sel-season', '2025/2026');
    document.getElementById('api-key').value = 'finta';
  }, { COUNTRY, LEAGUE });
  await page.evaluate(() => caricaSquadreLega());
  const out = {};
  for (const m of matches) {
    const snap = await page.evaluate(async ({ h, a, d, limit, SNAP }) => {
      if (typeof nuovaPartita === 'function') nuovaPartita();
      document.getElementById('sel-home').value = h; document.getElementById('sel-away').value = a;
      document.getElementById('target-date').value = d;
      if (limit != null) document.getElementById('history-limit').value = String(limit);
      window.__REC_CUR = [];
      await avviaScanner();
      return eval(SNAP);
    }, { h: m.home_team.id, a: m.away_team.id, d: m.time_utc.slice(0, 10), limit, SNAP });
    out[m.id] = snap;
  }
  const log = page.__log.slice();
  const scroll = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  await page.context().close();
  return { runs: out, log, scroll };
}

async function comparatorePage(browser, base, engineText) {
  const page = await newPage(browser, base);
  await page.goto(base + '/comparatore.html');
  await page.evaluate(() => { document.getElementById('cmp-api-key').value = 'finta'; });
  if (engineText) await page.evaluate(t => loadEngineFromText(t, 'copia salvata in localStorage'), engineText);
  else await page.evaluate(() => loadEngineFromServer());
  await page.waitForFunction(() => typeof engineReady !== 'undefined' && engineReady === true);
  // ogni giro del motore dentro il Comparatore: chiave = data|casa|trasferta, e il k del giro
  await page.evaluate((SNAP) => {
    window.__RUNS = [];
    const orig = window.avviaScanner;
    window.avviaScanner = async function () {
      window.__REC_CUR = [];
      const key = [document.getElementById('target-date').value, document.getElementById('sel-home').value,
                   document.getElementById('sel-away').value].join('|');
      const k = window.SHRINK_K, lim = document.getElementById('history-limit').value;
      const r = await orig.apply(this, arguments);
      const s = eval(SNAP); s.key = key; s.k = k; s.limit = lim; window.__RUNS.push(s);
      return r;
    };
  }, SNAP);
  await page.evaluate(({ COUNTRY, LEAGUE }) => {
    const s = (id, v) => { const el = document.getElementById(id); el.value = v; if (el.value !== v) throw new Error('select ' + id + ' ' + v); };
    s('cmp-country', COUNTRY); cmpUpdateLeagues(); s('cmp-league', LEAGUE); cmpUpdateSeasons(); s('cmp-season', '2025/2026');
  }, { COUNTRY, LEAGUE });
  return page;
}

async function runComparatore(browser, base, mode, date) {
  // 'vecchio': il motore caricato e' una copia vecchia (il Comparatore la ripristina da localStorage)
  const old = (mode === 'vecchio') ? instrument(fs.readFileSync(process.env.VECCHIO, 'utf8')) : null;
  const page = await comparatorePage(browser, base, old);
  if (old) await page.waitForTimeout(800);   // la verifica contro il server e' asincrona
  const t0 = Date.now();
  if (mode === 'singola' || mode === 'giorno' || mode === 'intervallo' || mode === 'vecchio') {
    await page.evaluate(d => { document.getElementById('cmp-target-date').value = d; }, date);
    await page.evaluate(() => cmpCaricaDatabase());
    if (mode === 'singola' || mode === 'vecchio') {
      await page.evaluate(async () => {
        const ids = cmpMatchesOfTheDay.map(m => m.id);
        for (const id of ids) { document.getElementById('cmp-partita').value = id; await cmpEsegui(); cmpSalva(); }
        cmpExportCSV();
      });
    } else if (mode === 'giorno') {
      await page.evaluate(async () => { await cmpEseguiTutte(); cmpExportCSV(); });
    } else {
      await page.evaluate(async d => { document.getElementById('cmp-range-start').value = d; document.getElementById('cmp-range-end').value = d;
                                      await cmpEseguiIntervallo(); cmpExportCSV(); }, date);
    }
  } else if (mode === 'ab') {
    // controllo di potenza: un A/B dichiarato NON deve risultare copia conforme
    await page.evaluate(d => { document.getElementById('cmp-target-date').value = d; }, date);
    // uno storico diverso da quello dello Scanner, qualunque esso sia
    await page.evaluate(() => { document.getElementById('cmp-elo-scale').value = '1.00'; cmpApplyEloScale(true);
                                document.getElementById('cmp-history-limit').value = (window.__ENGINE_LIMIT === 15) ? '30' : '15'; });
    await page.evaluate(() => cmpCaricaDatabase());
    await page.evaluate(async () => { await cmpEseguiTutte(); cmpExportCSV(); });
  } else if (mode === 'sconfina') {
    // un intervallo che parte nella stagione precedente: quelle partite vanno saltate
    await page.evaluate(d => { document.getElementById('cmp-target-date').value = d; }, date);
    await page.evaluate(() => cmpCaricaDatabase());
    await page.evaluate(async d => { document.getElementById('cmp-range-start').value = '2025-03-01';
                                    document.getElementById('cmp-range-end').value = d; await cmpEseguiIntervallo(); cmpExportCSV(); }, date);
  } else if (mode === 'batch') {
    await page.evaluate(async () => {
      cmpRenderBatchSeasons();
      document.querySelectorAll('#cmp-batch-seasons input[type=checkbox]').forEach(c => { c.checked = (c.value === '2025/2026'); });
      await cmpAvviaBatchStagioni();
    });
  } else if (mode === 'sweep') {
    await page.evaluate(async (LEAGUE) => {
      cmpLeagues = cmpLeagues.filter(l => l.id === LEAGUE).map(l => ({ ...l, seasons: ['2025/2026'] }));
      try { localStorage.removeItem(CMP_SWEEP_KEY); } catch (e) {}
      await cmpSweepStart(false);
    }, LEAGUE);
  }
  await page.waitForTimeout(300);
  const res = await page.evaluate(() => ({ runs: window.__RUNS, csvs: window.__CSVS, dl: window.__DL || [],
    saved: (cmpSavedMatches || []).map(m => ({ id: m.ids && m.ids.matchId, conf: m.conf, R: { m1: m.R.m1, confidence: m.R.confidence } })),
    consoleTxt: (document.getElementById('console') || {}).innerText || '',
    scroll: document.documentElement.scrollWidth - window.innerWidth }));
  res.log = page.__log.slice(); res.sec = Math.round((Date.now() - t0) / 1000);
  await page.context().close();
  return res;
}

// ---------- confronto ----------
function parseCSV(txt) {
  const lines = txt.replace(/^﻿/, '').split(/\r?\n/);
  let header = null; const sec = {}; let cur = '_';
  for (const ln of lines) {
    const c = ln.split(';');
    if (c[0] === 'MATCH') header = c;
    if (/^--- .* ---$/.test(c[0])) { cur = c[0]; sec[cur] = sec[cur] || {}; continue; }
    (sec[cur] = sec[cur] || {});
    if (c[0] && !(c[0] in sec[cur])) sec[cur][c[0]] = c;
    if (c[0] && !(c[0] in (sec._all = sec._all || {}))) sec._all[c[0]] = c;
  }
  return { header, sec };
}
const numOf = s => { if (s == null) return null; const m = String(s).replace(/<[^>]*>/g, '').replace(',', '.').match(/-?\d+(\.\d+)?/); return m ? +m[0] : null; };
const recMap = rec => { const o = {}; for (const [, id, v] of rec) o[id] = v; return o; };

function diffRecs(a, b) {
  // stessa sequenza di scritture: id per id, ultima scrittura
  const A = recMap(a), B = recMap(b); const ids = new Set([...Object.keys(A), ...Object.keys(B)]); const d = [];
  for (const id of ids) if (A[id] !== B[id]) d.push({ id, scanner: (A[id] || '(assente)').slice(0, 140), comparatore: (B[id] || '(assente)').slice(0, 140) });
  return { n: ids.size, diff: d };
}

// righe del CSV che dichiarano di riportare un numero dello Scanner
function csvChecks(S, csv, col) {
  const R = recMap(S.rec); const out = []; const all = csv.sec._all;
  const cell = (lbl, k, secName) => { const row = secName ? (csv.sec[secName] || {})[lbl] : all[lbl]; return row ? row[1 + 4 * col + k] : undefined; };
  const cmp = (what, sv, cv, tol) => { const a = numOf(sv), b = numOf(cv);
    const ok = a != null && b != null && Math.abs(a - b) <= (tol || 0) + 1e-9;
    out.push({ what, scanner: sv == null ? '(assente)' : String(sv).replace(/<[^>]*>/g, ''), csv: cv == null ? '(assente)' : cv, ok }); };
  const M1 = '--- MERCATI 1X2 (Ensemble V9.7) ---', MOD = '--- 1X2 PER MODELLO (DC / KNN / OL / Markov, ruolo e completo) ---';
  cmp('1 (ensemble)', R['master-1'], cell('1', 0, M1)); cmp('X (ensemble)', R['master-x'], cell('X', 0, M1)); cmp('2 (ensemble)', R['master-2'], cell('2', 0, M1));
  cmp('confidence 1', R['conf-p1'], cell('1', 1, M1)); cmp('confidence X', R['conf-px'], cell('X', 1, M1)); cmp('confidence 2', R['conf-p2'], cell('2', 1, M1));
  cmp('confidence globale', R['master-conf'], cell('Confidence Globale', 0, MOD));
  for (const [sid, lbl] of [['dc', 'DC'], ['knn', 'KNN'], ['ol', 'OL'], ['mk', 'Markov'], ['dco', 'DCover'], ['mko', 'MKover']])
    for (const [s, l] of [['1', '1'], ['x', 'X'], ['2', '2']]) cmp(`${lbl} ${l}`, R[`mdl-${sid}-${s}`], cell(`${lbl} ${l}`, 0, MOD));
  cmp('Goal', R['mdl-dc-gg'], cell('Goal', 0, M1)); cmp('NoGoal', R['mdl-dc-ng'], cell('NoGoal', 0, M1));
  cmp('Over 2.5', R['mdl-dc-ov'], cell('Over 2.5', 0, M1)); cmp('Under 2.5', R['mdl-dc-un'], cell('Under 2.5', 0, M1));
  for (const [id, lbl] of [['conf-1x', '1X'], ['conf-x2', 'X2'], ['conf-12', '12'], ['conf-gg', 'Goal'], ['conf-ng', 'NoGoal'], ['conf-ov', 'Over 2.5'], ['conf-un', 'Under 2.5']])
    cmp('confidence ' + lbl, R[id], cell(lbl, 1, M1));
  cmp('corner attesi', R['cor-tot-role'], cell('Corner tot (atteso)', 0), 0.051);
  cmp('tiri in porta attesi', R['sot-tot-role'], cell('Tiri porta tot (atteso)', 0), 0.051);
  cmp('gialli attesi', R['yel-tot-role'], cell('Gialli tot (atteso)', 0), 0.051);
  // linee dei mercati sui numeri: tabella mkt-lines
  const ml = (R['mkt-lines'] || '').split('</tr>').map(r => (r.match(/<td[^>]*>([^<]*)<\/td>/g) || []).map(x => x.replace(/<[^>]*>/g, '')));
  let iCor = 0, iSot = 0, iYel = 0, curN = null;
  for (const cells of ml) {
    if (!cells.length) continue;
    let c = cells.slice();
    if (c.length === 5) { curN = c[0]; c = c.slice(2); }
    if (c.length !== 3) continue;
    const nome = curN === 'Corner' ? 'Corner' : curN === 'Tiri in porta' ? 'Tiri porta' : 'Gialli';
    const i = nome === 'Corner' ? ++iCor : nome === 'Tiri porta' ? ++iSot : ++iYel;
    const cv = cell(`${nome} Over #${i}`, 0); cmp(`${nome} Over ${c[0]}`, c[1], cv ? cv.split(' ').pop() : cv);
  }
  // handicap asiatico e multigol
  const ah = (R['table-ah'] || '').split('</tr>').slice(1).map(r => (r.match(/<td[^>]*>([^<]*)<\/td>/g) || []).map(x => x.replace(/<[^>]*>/g, '')));
  for (const c of ah) if (c.length === 4) cmp('AH ' + c[0], c[1], cell('AH ' + (Number(c[0]) > 0 ? '+' : '') + Number(c[0]), 0));
  const mg = [...(R['mg-tot'] || '').matchAll(/>([0-9]-[0-9]) Gol<\/span><span[^>]*>([^<]*)</g)];
  for (const [, k, v] of mg) cmp('MG ' + k, v, cell('MG ' + k, 0));
  cmp('Elo casa', R['elo-h-ov'], cell('ELO Casa', 0)); cmp('Elo trasferta', R['elo-a-ov'], cell('ELO Trasferta', 0));
  cmp('Over 2.5 (multi-linea)', R['mdl-dc-ov'], cell('Over 2.5', 0, '--- OVER/UNDER MULTI-LINEA (prob DC vs reale) ---'));
  cmp('GG (da matrice)', R['mdl-dc-gg'], cell('GG (da matrice)', 0));
  { const cc = cell('COPIA CONFORME DELLO SCANNER', 0); out.push({ what: 'certificato di copia conforme', scanner: 'SI', csv: cc == null ? '(assente)' : cc, ok: cc === 'SI' }); }
  // il tabellone: la sezione deve esistere e riportare le stesse proposte nello stesso ordine
  const tab = csv.sec['--- TABELLONE (come lo stampa lo Scanner) ---'];
  if (!tab) out.push({ what: 'tabellone', scanner: (S.verd || []).length + ' proposte', csv: '(sezione assente)', ok: false });
  else (S.verd || []).forEach((v, i) => {
    const row = tab['Tabellone #' + (i + 1)]; const cv = row ? row[1 + 4 * col] : undefined;
    const sv = `${v.nome} ${(v.p * 100).toFixed(1).replace('.', ',')}%`;
    out.push({ what: 'tabellone #' + (i + 1), scanner: sv + ' ' + v.verdetto, csv: cv == null ? '(assente)' : cv + ' ' + (row ? row[4 + 4 * col] : ''),
               ok: cv === sv && row && String(row[4 + 4 * col]).includes(v.verdetto) });
  });
  return out;
}

(async () => {
  const srv = await serve(); const base = 'http://127.0.0.1:' + srv.address().port;
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const cur = BY_SEASON['2025/2026'].filter(m => m._ri === ROUND_TARGET);
  const date = cur[0].time_utc.slice(0, 10);
  const day = cur.filter(m => m.time_utc.startsWith(date));
  console.log(`Lega finta: ${Object.keys(MATCHES).length} partite. Giornata ${ROUND_TARGET} del 2025/26, data ${date}, ${day.length} partite.`);

  const t0 = Date.now();
  const scanner = await runScanner(browser, base, day, null);
  const sLog = scanner.log.filter(l => !/CONSOLE/.test(l));
  console.log(`Scanner: ${day.length} partite in ${Math.round((Date.now() - t0) / 1000)}s · log ${sLog.slice(0, 5).join(' | ') || 'pulito'}`
            + (process.env.MOBILE ? ` · scorrimento laterale ${scanner.scroll}px` : ''));
  console.log('   sottotitolo:', recMap(scanner.runs[day[0].id].rec)['ui-subtitle']);
  let fail = (sLog.length || (process.env.MOBILE && scanner.scroll > 0)) ? 1 : 0;

  const results = {};
  await Promise.all(MODES.map(async mode => { results[mode] = await runComparatore(browser, base, mode, date); }));

  const report = { date, matches: day.map(m => `${m.id} ${m.home_team.name}-${m.away_team.name}`), modes: {} };
  for (const mode of MODES) {
    const R = results[mode]; const mr = { sec: R.sec, csvs: R.csvs.length, dl: R.dl, log: R.log.slice(0, 12), perMatch: {} };
    const csvTxt = R.csvs[R.csvs.length - 1] || '';
    const csv = csvTxt ? parseCSV(csvTxt) : null;
    const colonne = row => (row || []).filter((x, i) => i > 0 && (i - 1) % 4 === 0);
    if (csv) {
      const cnt = {}; colonne(csv.sec._all['STAGIONE']).forEach(x => cnt[x] = (cnt[x] || 0) + 1); mr.stagioniNelCSV = cnt;
      const cc = colonne(csv.sec._all['COPIA CONFORME DELLO SCANNER']);
      mr.copiaConforme = { si: cc.filter(x => x === 'SI').length, tot: cc.length, no: [...new Set(cc.filter(x => x !== 'SI'))].slice(0, 3) };
    }
    for (const m of day) {
      const key = [date, m.home_team.id, m.away_team.id].join('|');
      const first = R.runs.find(r => r.key === key);
      const S = scanner.runs[m.id];
      const pm = {};
      if (!first) pm.engine = 'nessun giro del motore per questa partita';
      else {
        pm.kPrimoGiro = first.k; pm.limit = first.limit;
        const d = diffRecs(S.rec, first.rec);
        pm.scrittureMotore = d.n; pm.scrittureDiverse = d.diff.length; pm.esempi = d.diff.slice(0, 6);
      }
      if (csv && csv.header) {
        const col = ((csv.sec._all['ID PARTITA'] || []).indexOf(m.id) - 1) / 4;
        if (col >= 0 && Number.isInteger(col)) {
          const ch = csvChecks(S, csv, col); const bad = ch.filter(x => !x.ok);
          pm.csvControlli = ch.length; pm.csvDiversi = bad.length; pm.csvEsempi = bad.slice(0, 12);
        } else pm.csv = 'partita assente dal CSV';
      } else pm.csv = 'nessun CSV';
      mr.perMatch[m.id] = pm;
    }
    // il verdetto: nelle modalita' vere tutto identico e certificato; nei controlli di
    // potenza il certificato deve dire NO, col motivo giusto
    const pms = Object.values(mr.perMatch), cc = mr.copiaConforme || { si: 0, tot: 0, no: [] };
    const logTxt = R.consoleTxt || '';
    if (CONTROLLI[mode]) {
      mr.ok = cc.tot > 0 && cc.si === 0 && CONTROLLI[mode].every(w => cc.no.some(x => x.includes(w)));
    } else {
      mr.ok = pms.every(p => !p.engine && !p.csv && p.scrittureDiverse === 0 && p.csvDiversi === 0)
        && cc.tot > 0 && cc.si === cc.tot
        && Object.keys(mr.stagioniNelCSV || {}).every(k => k === '2025/2026')
        && (!process.env.MOBILE || R.scroll <= 0)
        && (mode !== 'sconfina' || /le salto/.test(logTxt));
    }
    if (!mr.ok) fail++;
    report.modes[mode] = mr;

    const eng = pms.map(p => p.scrittureDiverse), cs = pms.map(p => p.csvDiversi);
    console.log(`\n[${mode}] ${mr.ok ? 'OK' : 'FALLITO'}${CONTROLLI[mode] ? ' (controllo di potenza: il certificato deve dire NO)' : ''} · ${mr.sec}s`
      + ` · storico ${[...new Set(pms.map(p => p.limit))].join(',')} · k del primo giro ${[...new Set(pms.map(p => p.kPrimoGiro))].join(',')}`
      + (process.env.MOBILE ? ` · scorrimento laterale ${R.scroll}px` : ''));
    console.log(`   CSV: stagioni ${JSON.stringify(mr.stagioniNelCSV)} · copia conforme ${cc.si}/${cc.tot}${cc.no.length ? ' ' + JSON.stringify(cc.no) : ''}`);
    console.log(`   scritture a schermo del motore diverse dallo Scanner: ${eng.join(' / ')} su ${pms[0] && pms[0].scrittureMotore}`);
    console.log(`   righe del CSV diverse dallo Scanner: ${cs.join(' / ')} su ${pms[0] && pms[0].csvControlli}`);
    const ex = pms.find(p => p.esempi && p.esempi.length); if (ex) console.log('   es. motore:', JSON.stringify(ex.esempi.slice(0, 3)));
    const ec = pms.find(p => p.csvEsempi && p.csvEsempi.length); if (ec) console.log('   es. CSV:', JSON.stringify(ec.csvEsempi.slice(0, 6)));
    const note = pms.find(p => p.engine || p.csv); if (note) console.log('   nota:', note.engine || note.csv);
    const avv = logTxt.split('\n').filter(l => /le salto|NON stampera|NON e' lo scanner/i.test(l)).slice(0, 2);
    if (avv.length) console.log('   log del Comparatore:', avv.map(x => x.trim().slice(0, 200)).join(' || '));
  }
  report.apiCalls = API_CALLS;
  fs.writeFileSync(path.join(OUT, 'parita-report.json'), JSON.stringify(report, null, 1));
  console.log(`\nChiamate API servite: ${API_CALLS}. Esito: ${fail ? fail + ' verifiche fallite' : 'COPIA CONFORME in tutte le modalita\', controlli di potenza compresi'}`);
  console.log(`Dettaglio: ${path.join(OUT, 'parita-report.json')}`);
  await browser.close(); srv.close();
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
