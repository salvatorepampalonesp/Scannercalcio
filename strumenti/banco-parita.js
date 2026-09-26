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
//   SALVA_CSV=<cartella> ...                            salva l'ultimo CSV di ogni modalita'
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

// coppe europee finte: le squadre 0 e 1 giocano 3 giorni prima e 4 dopo ogni giornata, la 2 solo dopo
const UEFA = { l_0bfbkO: {}, l_38d9HA: {}, l_2WZ2tt: {} };
SEASONS.forEach((s, si) => {
  const t0 = Date.UTC(2023 + si, 7, 19); UEFA.l_0bfbkO[s] = [];
  for (let ri = 0; ri < 18; ri++) for (const [t, off] of [[0, -3], [1, -3], [0, 4], [1, 4], [2, 4]]) {
    const day = new Date(t0 + (ri * 14 + off) * 86400000).toISOString().slice(0, 10), r = rng(`u${si}r${ri}t${t}${off}`);
    UEFA.l_0bfbkO[s].push({ id: `u${si}r${ri}t${t}${off < 0 ? 'a' : 'b'}`, home_team: team(t), away_team: { id: 't_9' + t, name: 'Estero ' + t },
      status: 'finished', time_utc: `${day}T20:00:00Z`, score_home: pois(1.3, r), score_away: pois(1.1, r) });
  }
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
  const add = (tid, n) => { const rs = rng(m.id + 'marcatori' + tid), xi = xiOf(m, tid).xi;
    for (let i = 0; i < n; i++) { const pid = xi[6 + Math.floor(rs() * 5)];
      ev.push({ event_type: 'goal', team_id: tid, minute: 1 + Math.floor(r() * 94),
                is_own_goal: false, player: { id: pid, name: 'Giocatore ' + tid.slice(2) + '-' + Math.floor(r() * 6) } }); } };
  add(m.home_team.id, m.score_home); add(m.away_team.id, m.score_away);
  if (r() < 0.12) ev.push({ event_type: 'redcard', team_id: r() < 0.5 ? m.home_team.id : m.away_team.id, minute: 60 });
  for (const tid of [m.home_team.id, m.away_team.id]) { const ry = rng(m.id + 'gialli' + tid), xi = xiOf(m, tid).xi;
    for (let i = pois(1.9, ry); i > 0; i--) ev.push({ event_type: 'YellowCard', team_id: tid, minute: 30, player: { id: xi[Math.floor(ry() * 11)], name: 'G' } }); }
  return { data: { events: ev } };
}
const FORM = ['4-3-3', '4-2-3-1', '3-5-2', '4-4-2', '3-4-3'];
// rosa di 18 per squadra: 11 titolari abituali, ognuno riposa col 15%; la squadra 3 cambia
// allenatore a meta' del girone d'andata dell'ultima stagione (AGENTS.md, Formazioni e assenze)
function xiOf(m, tid) {
  const r = rng(m.id + 'xi' + tid); const sq = [...Array(18).keys()].map(k => 'p_' + tid.slice(2) + '_' + k);
  const xi = []; let b = 11;
  for (let k = 0; k < 11; k++) xi.push(r() < 0.15 && b < 18 ? sq[b++] : sq[k]);
  return { xi, subs: sq.filter(p => !xi.includes(p)).slice(0, 7), cap: xi.includes(sq[0]) ? sq[0] : xi[1] };
}
const coachOf = (m, tid) => 'Allenatore ' + tid.slice(2) + (tid === 't_3' && m._si === 2 && m._ri >= 6 ? ' bis' : '');
function sideOf(m, tid, fi) {
  const { xi, subs, cap } = xiOf(m, tid);
  return { formation: FORM[fi], confirmed: true, coach: { name: coachOf(m, tid) },
    starters: xi.map((p, i) => ({ player_id: p, name: 'G ' + p, shirt_number: String(i + 1), position_id: i, is_captain: p === cap, pitch_x: 0.5, pitch_y: 0.5 })),
    subs: subs.map(p => ({ player_id: p, name: 'G ' + p, shirt_number: '', position_id: 2, is_captain: false, pitch_x: 0, pitch_y: 0 })) };
}
// statistiche per giocatore come /players: gol e assist omessi quando valgono 0, il portiere
// (k = 0) senza il gruppo duels, come fa l'API; le chiavi sono quelle attese dal motore
function playersOf(m) {
  const out = [], it = (key, value, total) => ({ key, stat: total == null ? { type: 'integer', value } : { type: 'fractionWithPercentage', value, total } });
  for (const tid of [m.home_team.id, m.away_team.id]) {
    const { xi, subs } = xiOf(m, tid), r = rng(m.id + 'pl' + tid);
    xi.concat(subs.slice(0, 3)).forEach((pid, i) => {
      const mins = i < 11 ? (r() < 0.8 ? 90 : 60 + Math.floor(r() * 30)) : 10 + Math.floor(r() * 25), k = +pid.split('_').pop(), q = mins / 90;
      const shots = pois((k >= 6 && k <= 10 ? 2.2 : 0.4) * q, r), sot = Math.min(shots, pois(shots * 0.4, r)), gol = Math.min(sot, pois(sot * 0.3, r));
      const top = { 'Minutes played': it('minutes_played', mins), 'Total shots': it('total_shots', shots), 'Shot accuracy': it('shot_accuracy', sot, shots) };
      if (gol) top.Goals = it('goals', gol); const ast = pois(0.1 * q, r); if (ast) top.Assists = it('assists', ast);
      const stats = [{ key: 'top_stats', stats: top }];
      if (k !== 0) stats.push({ key: 'duels', stats: { 'Fouls committed': it('fouls', pois(1.1 * q, r)), 'Was fouled': it('was_fouled', pois((k >= 6 ? 1.8 : 0.9) * q, r)) } },
                             { key: 'defense', stats: { 'Tackles won': it('tackles_won', pois(1.3 * q, r)) } });
      out.push({ player: { id: pid, name: 'Giocatore ' + pid.slice(2), position_id: k }, team_id: tid, stats });
    });
  }
  return { data: out };
}
const lineupsOf = m => ({ data: { home: sideOf(m, m.home_team.id, hash(m.home_team.id) % 5), away: sideOf(m, m.away_team.id, hash(m.away_team.id + 'a') % 5) } });

let API_CALLS = 0;
function api(url) {
  API_CALLS++;
  const u = new URL(url); const p = u.pathname;
  let mm = p.match(/^\/leagues\/([^/]+)\/matches$/);
  if (mm) {
    const s = u.searchParams.get('season');
    if (mm[1] === LEAGUE && BY_SEASON[s]) return { data: { matches: BY_SEASON[s].map(pub) } };
    if (UEFA[mm[1]]) return { data: { matches: (UEFA[mm[1]][s] || []).map(m => ({ ...m })) } };
    return { data: { matches: [] } };
  }
  mm = p.match(/^\/date\/(\d{4}-\d{2}-\d{2})$/);
  if (mm) return { data: { date: mm[1], matches: Object.values(MATCHES).filter(m => m.time_utc.slice(0, 10) === mm[1]).map(pub) } };
  mm = p.match(/^\/matches\/([^/]+)\/(stats|lineups|advanced|events|players)$/);
  if (mm && MATCHES[mm[1]]) {
    const m = MATCHES[mm[1]];
    if (mm[2] === 'stats') return statsOf(m);
    if (mm[2] === 'lineups') return lineupsOf(m);
    if (mm[2] === 'players') return playersOf(m);
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
  confMk: JSON.parse(JSON.stringify(window.__CONF_MK || null)), lineup: JSON.parse(JSON.stringify(window.__LINEUP_DEBUG || null)),
  fatigue: JSON.parse(JSON.stringify(window.__FATIGUE_DEBUG || null)),
  trend: JSON.parse(JSON.stringify(window.__ELO_TREND || null)) }))()`;

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
      const snap = eval(SNAP), pr = (document.getElementById('ai-prompt') || {}).value || '';
      snap.prompt = { n: pr.length, rotto: pr ? ((pr.match(/.{0,40}(NaN|undefined|\[object|Infinity)/) || [null])[0]) : 'vuoto' };
      return snap;
    }, { h: m.home_team.id, a: m.away_team.id, d: m.time_utc.slice(0, 10), limit, SNAP });
    out[m.id] = snap;
  }
  // le statistiche dei giocatori (bottone, fuori dal giro del motore): tabelle piene, niente NaN
  const giocatori = await page.evaluate(async () => {
    if (typeof caricaGiocatori !== 'function') return null;
    await caricaGiocatori(); const sel = document.getElementById('sel-mercato-giocatori'); const per = [];
    for (let i = 0; i < sel.options.length; i++) { sel.value = String(i); renderGiocatori();
      const h = document.getElementById('giocatori-box').innerHTML;
      per.push({ m: sel.options[i].text, righe: (h.match(/<tr>/g) || []).length, rotto: /NaN|undefined|Infinity/.test(h) }); }
    const D = window.__PLAYER_DATA; sel.value = '1'; renderGiocatori();
    return { dati: [D.H.nDati, D.A.nDati], partite: [D.H.nPartite, D.A.nPartite], per };
  });
  // le quote (b54, fuori dal giro del motore): card e prompt senza NaN ne' segnaposto, l'avviso
  // quando il mercato contraddice il motore (controllo di potenza), e la card piena per i 390px
  const quote = await page.evaluate(() => {
    if (typeof aggiornaQuote !== 'function') return null;
    const set = (a, b, c) => { [['quota-1', a], ['quota-x', b], ['quota-2', c]].forEach(([id, v]) => document.getElementById(id).value = v); aggiornaQuote(); };
    const casi = [], leggi = (nome, valide) => { const h = document.getElementById('quote-box').innerHTML, p = document.getElementById('ai-prompt').value;
      casi.push({ nome, valide, righe: (h.match(/<tr>/g) || []).length, conQuote: /CON LE QUOTE DEL MERCATO/.test(p), sintesi: /pick da citare/.test(p),
                  avviso: /Segui il pick con le quote/.test(h), segnaposto: /@@QUOTE/.test(p), rotto: /NaN|undefined|Infinity/.test(h + p) }); };
    const P = window.__QUOTE_CTX.p, contro = P[0] >= P[2] ? ['9', '5', '1.30'] : ['1.30', '5', '9'];
    set('', '', ''); leggi('vuote', false);
    set('2,10', '3.40', '3.60'); leggi('normali, con la virgola', true);
    set(...contro); leggi('il mercato contraddice il motore', true);
    set('2.1', '', '3.6'); leggi('incomplete', false);
    set('1.20', '6.50', '13'); leggi('favorita netta', true);
    return casi;
  });
  const log = page.__log.slice();
  const scroll = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  // una tabella di confronto non deve scorrere nemmeno dentro il suo riquadro: la pagina puo'
  // stare a 0 px mentre la tabella esce di lato (il tabellone, fino al b49, di 53 px a 390px)
  const compatte = await page.evaluate(() => [...document.querySelectorAll('table.table-compact')]
    .map(t => { const w = t.closest('.tbl-scroll') || t.parentElement, c = t.closest('[id]');
                return { id: c ? c.id : '?', eccesso: t.scrollWidth - w.clientWidth }; })
    .filter(x => x.eccesso > 1));
  if (quote) quote.push(await page.evaluate(() => { nuovaPartita();
    const vuoti = ['quota-1', 'quota-x', 'quota-2'].every(id => document.getElementById(id).value === '');
    return { nome: 'cambia partita', svuotate: vuoti && window.__QUOTE_CTX === null && document.getElementById('quote-box').innerHTML === '--' }; }));
  await page.context().close();
  return { runs: out, log, scroll, compatte, giocatori, quote };
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
  // l'archivio in fondo al CSV (b47) deve bastare a rifare l'Elo del motore identico:
  // lo si rilegge dal TESTO esportato e si fa girare buildGlobalElo del motore su quello
  const archivio = (mode === 'batch' || mode === 'sweep') ? await page.evaluate(() => {
    const txt = (window.__CSVS || []).slice(-1)[0] || '';
    const L = txt.replace(/^\uFEFF/, '').split(/\r?\n/).map(l => l.split(';'));
    const head = L.find(c => /^ARCHIVIO \S+ \S+$/.test(c[0]));
    if (!head) return { righe: 0, database: cmpAllMatches.length, partite: 0, diversi: -1, esempi: ['sezione ARCHIVIO assente'] };
    const lega = head[0].split(' ')[1];
    const arch = L.filter(c => /^ARCHIVIO #\d+$/.test(c[0])).map(c => ({ id: c[1], _season: c[2], time_utc: c[3], status: c[4],
      home_team: { id: c[5], name: c[6] }, away_team: { id: c[7], name: c[8] },
      score_home: c[9] === '' ? null : Number(c[9]), score_away: c[10] === '' ? null : Number(c[10]), league_id: lega }));
    const riga = n => L.find(c => c[0] === n) || [];
    const ids = riga('ID PARTITA'), t = riga('DATA ISO (UTC)'), hid = riga('ID SQUADRA CASA'), aid = riga('ID SQUADRA TRASFERTA');
    const eh = riga('ELO Casa'), ea = riga('ELO Trasferta'), hf = riga('HFA Lega');
    const salva = window.__ENGINE_CACHE;
    const giro = A => { window.__ENGINE_CACHE = A; let n = 0; const d = [];
      for (let i = 1; i < ids.length; i += 4) {
        if (!ids[i]) continue;
        const E = buildGlobalElo(new Date(t[i]).getTime());
        const v = [E.table[hid[i]] ?? 1500, E.table[aid[i]] ?? 1500, E._hfa].map(x => String(Math.round(x)));
        n++;
        if (v[0] !== eh[i] || v[1] !== ea[i] || v[2] !== hf[i]) d.push(`${ids[i]}: ${v.join('/')} contro ${eh[i]}/${ea[i]}/${hf[i]}`);
      }
      return { n, d }; };
    let G, P;
    try {
      G = giro(arch);
      // controllo di potenza: senza la prima partita conclusa dell'archivio l'Elo non deve piu' coincidere
      const i0 = arch.findIndex(m => m.status === 'finished');
      P = giro(arch.filter((m, i) => i !== i0));
    } finally { window.__ENGINE_CACHE = salva; }
    return { righe: arch.length, database: cmpAllMatches.length, partite: G.n, diversi: G.d.length, esempi: G.d.slice(0, 3), potenza: P.d.length };
  }) : null;
  const res = await page.evaluate(() => ({ runs: window.__RUNS, csvs: window.__CSVS, dl: window.__DL || [],
    saved: (cmpSavedMatches || []).map(m => ({ id: m.ids && m.ids.matchId, conf: m.conf, R: { m1: m.R.m1, confidence: m.R.confidence } })),
    consoleTxt: (document.getElementById('console') || {}).innerText || '',
    scroll: document.documentElement.scrollWidth - window.innerWidth }));
  res.log = page.__log.slice(); res.sec = Math.round((Date.now() - t0) / 1000); res.archivio = archivio;
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
  // la pendenza dell'Elo (b47): il trend che sposta i lambda del modello
  if (!S.trend) out.push({ what: 'pendenza Elo', scanner: '(__ELO_TREND assente)', csv: '-', ok: false });
  else for (const [k, lbl, tol] of [['trendH', 'Elo: pendenza casa (media ultime 5 meno 6-15, punti)', 0.0051],
                                    ['trendA', 'Elo: pendenza trasferta (media ultime 5 meno 6-15, punti)', 0.0051],
                                    ['penH', 'Elo: pendenza casa sul lambda (penH, cap 8%)', 0.00005],
                                    ['penA', 'Elo: pendenza trasferta sul lambda (penA, cap 8%)', 0.00005],
                                    ['nH', 'Elo: partite nella serie casa', 0], ['nA', 'Elo: partite nella serie trasferta', 0],
                                    ['ingresso', 'Elo: ingresso delle neopromosse (livello della stagione)', 0.0051]])
    cmp('Elo ' + k, S.trend[k], cell(lbl, 0), tol);
  cmp('Over 2.5 (multi-linea)', R['mdl-dc-ov'], cell('Over 2.5', 0, '--- OVER/UNDER MULTI-LINEA (prob DC vs reale) ---'));
  cmp('GG (da matrice)', R['mdl-dc-gg'], cell('GG (da matrice)', 0));
  { const cc = cell('COPIA CONFORME DELLO SCANNER', 0); out.push({ what: 'certificato di copia conforme', scanner: 'SI', csv: cc == null ? '(assente)' : cc, ok: cc === 'SI' }); }
  // le formazioni: il CSV deve riportare gli indici che lo Scanner ha calcolato
  const LU = "--- FORMAZIONI (misura: non entrano nelle probabilita') ---", L = S.lineup;
  const sn = v => v == null ? 'N/D' : (v ? 'SI' : 'no');
  const eqs = (what, sv, cv) => out.push({ what, scanner: sv, csv: cv == null ? '(assente)' : cv, ok: sv === cv });
  if (!L) out.push({ what: 'formazioni', scanner: '(__LINEUP_DEBUG assente)', csv: '-', ok: false });
  else for (const [k, nome] of [['H', 'casa'], ['A', 'trasf.']]) {
    const F = L[k] || {}, c = lbl => cell('Formazioni ' + nome + ': ' + lbl, 0, LU);
    eqs('formazione ' + nome + ': disponibile', sn(F.disponibile), c('disponibile'));
    eqs('formazione ' + nome + ': confermata', sn(F.confermata), c('confermata'));
    cmp('formazione ' + nome + ': formazioni nello storico', F.nStorico, c('formazioni nello storico'));
    cmp('formazione ' + nome + ': titolari abituali assenti', F.abitualiAssenti, c('titolari abituali assenti'));
    cmp('formazione ' + nome + ': peso degli assenti', F.pesoAssenti, c('peso degli assenti'), 0.00005);
    cmp('formazione ' + nome + ': gol degli assenti', F.golAssenti, c('gol degli assenti'), 0.00005);
    cmp('formazione ' + nome + ': cambi dall ultima', F.cambi, c('cambi dall ultima'));
    eqs('formazione ' + nome + ': capitano assente', sn(F.capitanoAssente), c('capitano assente'));
    eqs('formazione ' + nome + ': allenatore nuovo', sn(F.allenatoreNuovo), c('allenatore nuovo'));
    cmp('formazione ' + nome + ': partite con l allenatore', F.partiteAllenatore, c('partite con l allenatore'));
  }
  const ST = "--- STANCHEZZA (misura: non entra nelle probabilita') ---", T = S.fatigue;
  if (!T) out.push({ what: 'stanchezza', scanner: '(__FATIGUE_DEBUG assente)', csv: '-', ok: false });
  else {
    eqs('stanchezza: stagione delle coppe', T.stagione, cell('Stanchezza: stagione delle coppe', 0, ST));
    cmp('stanchezza: partite europee in archivio', T.partiteCoppe, cell('Stanchezza: partite europee in archivio', 0, ST));
    for (const [k, nome] of [['H', 'casa'], ['A', 'trasf.']]) {
      const F = T[k] || {}, c = lbl => cell('Stanchezza ' + nome + ': ' + lbl, 0, ST), nd = v => v == null ? 'N/D' : String(v);
      eqs('stanchezza ' + nome + ': giorni di riposo', nd(F.riposo), c('giorni di riposo'));
      eqs('stanchezza ' + nome + ': giorni di riposo dalla lega', nd(F.riposoLega), c('giorni di riposo dalla lega'));
      eqs('stanchezza ' + nome + ': partite in 14 giorni', nd(F.partite14), c('partite in 14 giorni'));
      eqs('stanchezza ' + nome + ': giorni dalla coppa europea', nd(F.coppaPrima), c('giorni dalla coppa europea'));
      eqs('stanchezza ' + nome + ': giorni alla coppa europea', nd(F.coppaDopo), c('giorni alla coppa europea'));
      eqs('stanchezza ' + nome + ': in Europa', sn(F.inEuropa), c('in Europa'));
    }
  }
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

module.exports = { api, PITCH, LEAGUE, COUNTRY, SEASONS };

if (require.main === module) (async () => {
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
            + (process.env.MOBILE ? ` · scorrimento laterale ${scanner.scroll}px · tabelle compatte che escono di lato: `
                                    + (scanner.compatte.length ? JSON.stringify(scanner.compatte) : 'nessuna') : ''));
  console.log('   sottotitolo:', recMap(scanner.runs[day[0].id].rec)['ui-subtitle']);
  // il mega-prompt non passa da safeTxt/safeHtml: si controlla a parte che non sia vuoto o rotto
  const P = day.map(m => scanner.runs[m.id].prompt), pRotti = P.filter(x => x.rotto);
  console.log(`   mega-prompt: ${Math.min(...P.map(x => x.n))}-${Math.max(...P.map(x => x.n))} caratteri`
    + (pRotti.length ? ' · ROTTO: ' + JSON.stringify(pRotti.map(x => x.rotto)) : ' · niente NaN, undefined o vuoti'));
  const G = scanner.giocatori;
  const gRotti = G ? G.per.filter(x => x.rotto || x.righe < 2) : null;
  console.log('   giocatori: ' + (G ? `statistiche per ${G.dati[0]}/${G.partite[0]} e ${G.dati[1]}/${G.partite[1]} partite, ${G.per.length} mercati, righe per mercato ${Math.min(...G.per.map(x => x.righe))}-${Math.max(...G.per.map(x => x.righe))}`
    + (gRotti.length ? ' · ROTTI: ' + gRotti.map(x => x.m).join(', ') : ' · nessun NaN') : 'bottone assente'));
  const Q = scanner.quote;
  const qRotte = Q ? Q.filter(x => x.nome === 'cambia partita' ? !x.svuotate
    : x.rotto || x.segnaposto || (x.valide ? (x.righe !== 4 || !x.conQuote || !x.sintesi) : (x.righe !== 0 || x.conQuote || x.sintesi))
      || (x.nome === 'il mercato contraddice il motore' && !x.avviso)) : null;
  console.log('   quote: ' + (Q ? `${Q.length} casi` + (qRotte.length ? ' · ROTTI: ' + JSON.stringify(qRotte)
    : ' · card e prompt senza NaN ne\' segnaposto, avviso quando il mercato contraddice il motore, campi svuotati al cambio partita') : 'campo assente'));
  // le formazioni devono avere valori veri, non tutti nulli: altrimenti il confronto non prova niente
  for (const m of day) { const L = scanner.runs[m.id].lineup, f = F => F ? `assenti ${F.abitualiAssenti} (peso ${F.pesoAssenti == null ? '-' : F.pesoAssenti.toFixed(2)}, gol ${F.golAssenti == null ? '-' : F.golAssenti.toFixed(2)}), cambi ${F.cambi}, allenatore ${F.allenatoreNuovo ? 'nuovo' : F.partiteAllenatore + '+'}` : '-';
    console.log(`   formazioni ${m.id}: casa ${f(L && L.H)} | trasf. ${f(L && L.A)}`);
    const T = scanner.runs[m.id].fatigue, g = F => F ? `riposo ${F.riposo} (lega ${F.riposoLega}), ${F.partite14} in 14 gg, coppa ${F.coppaPrima == null ? '-' : F.coppaPrima + ' fa'} / ${F.coppaDopo == null ? '-' : 'fra ' + F.coppaDopo}` : '-';
    console.log(`   stanchezza ${m.id}: casa ${g(T && T.H)} | trasf. ${g(T && T.A)}`); }
  let fail = (sLog.length || (process.env.MOBILE && (scanner.scroll > 0 || scanner.compatte.length)) || !G || gRotti.length || pRotti.length || !Q || qRotte.length) ? 1 : 0;

  const results = {};
  await Promise.all(MODES.map(async mode => { results[mode] = await runComparatore(browser, base, mode, date); }));

  const report = { date, matches: day.map(m => `${m.id} ${m.home_team.name}-${m.away_team.name}`), modes: {} };
  for (const mode of MODES) {
    const R = results[mode]; const mr = { sec: R.sec, csvs: R.csvs.length, dl: R.dl, log: R.log.slice(0, 12), perMatch: {} };
    const csvTxt = R.csvs[R.csvs.length - 1] || '';
    if (process.env.SALVA_CSV && csvTxt) fs.writeFileSync(path.join(process.env.SALVA_CSV, 'banco-' + mode + '.csv'), csvTxt);
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
        && (mode !== 'sconfina' || /le salto/.test(logTxt))
        && (!R.archivio || (R.archivio.righe > 0 && R.archivio.righe === R.archivio.database
                            && R.archivio.partite === cc.tot && R.archivio.diversi === 0 && R.archivio.potenza > 0));
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
    if (R.archivio) { const A = R.archivio; mr.archivio = A;
      console.log(`   archivio in fondo al CSV: ${A.righe} partite su ${A.database} del database · Elo rifatto dall'archivio su ${A.partite} partite: ${A.diversi} diverse${A.esempi.length ? ' ' + JSON.stringify(A.esempi) : ''} · senza una partita: ${A.potenza} diverse (potenza)`); }
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
