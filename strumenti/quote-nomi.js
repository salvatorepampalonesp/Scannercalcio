// Prova dell'aggancio delle quote automatiche (AGENTS.md, Le quote automatiche): per ogni partita
// conclusa di una lega e stagione, la riga vera di football-data si trova per data (entro un giorno)
// e punteggio, coi nomi per co-occorrenza, senza guardare la somiglianza dei nomi; poi la cerca
// trovaPartitaQuote dello scanner.html del repository, e si conta giuste / sbagliate / non trovate.
//
//   node strumenti/quote-nomi.js --leghe l_0jy5yE,l_0S1uaf --stagione 2025/2026
//
// Una chiamata alla PitchAPI per lega (la credenziale come per strumenti/batch-auto.js) e un file
// di football-data. Una lega a calendario solare vuole la stagione "2025".
const { spawnSync } = require('child_process');
if (process.env.HTTPS_PROXY && !process.env.NODE_USE_ENV_PROXY) {
  const r = spawnSync(process.execPath, ['--no-warnings', __filename, ...process.argv.slice(2)],
                      { stdio: 'inherit', env: { ...process.env, NODE_USE_ENV_PROXY: '1' } });
  process.exit(r.status == null ? 1 : r.status);
}
const fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..');
const PITCH = 'https://pitchapi-proxy.salvatorepampalone-sp.workers.dev', KEY = process.env.PITCHAPI_KEY || '';
const arg = n => { const i = process.argv.indexOf('--' + n); return i > 0 ? process.argv[i + 1] : null; };

const html = fs.readFileSync(path.join(ROOT, 'scanner.html'), 'utf8');
const js = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');
const F = new Function(js.slice(js.indexOf('const QUOTE_FD'), js.indexOf('const _QUOTE_FILE'))
  + '; return { trovaPartitaQuote, _csvQuote, _dataQuote, _simNomi, QUOTE_FD, QUOTE_PAESE };')();

(async () => {
  const leghe = (arg('leghe') || '').split(',').filter(Boolean), stag = arg('stagione') || '2025/2026';
  if (!leghe.length) { console.log('uso: node strumenti/quote-nomi.js --leghe <id,id,...> [--stagione 2025/2026]'); process.exit(2); }
  const tot = { giuste: 0, sbagliate: 0, nonTrovate: 0, senzaVerita: 0 };
  for (const lId of leghe) {
    const cod = F.QUOTE_FD[lId];
    if (!cod) { console.log(lId, 'non e\' in QUOTE_FD'); continue; }
    const r = await fetch(`${PITCH}/leagues/${lId}/matches?season=${encodeURIComponent(stag)}`, { headers: KEY ? { 'X-API-KEY': KEY } : {} });
    if (!r.ok) { console.log(lId, 'PitchAPI ha risposto', r.status); continue; }
    const P = ((await r.json()).data || {}).matches.filter(m => m.status === 'finished' && m.score_home != null);
    const y = +stag.slice(0, 4), file = F.QUOTE_PAESE[cod] ? `new/${cod}.csv` : `mmz4281/${String(y % 100).padStart(2, '0')}${String((y + 1) % 100).padStart(2, '0')}/${cod}.csv`;
    const R = F._csvQuote(await (await fetch('https://www.football-data.co.uk/' + file)).text())
      .filter(x => F.QUOTE_PAESE[cod] ? (x.Country || '').trim() === F.QUOTE_PAESE[cod] : true);
    const gol = x => [+(x.FTHG ?? x.HG), +(x.FTAG ?? x.AG)], nh = x => x.HomeTeam || x.Home, na = x => x.AwayTeam || x.Away;
    const giorno = m => Date.parse(m.time_utc.slice(0, 10) + 'T00:00:00Z');
    const vicine = t => R.filter(x => { const d = F._dataQuote(x.Date); return d != null && Math.abs(d - t) <= 86400000; });
    const co = new Map(), conta = (k, v) => { const c = co.get(k) || new Map(); c.set(v, (c.get(v) || 0) + 1); co.set(k, c); };
    for (const m of P) for (const x of vicine(giorno(m))) {
      const [h, a] = gol(x); if (h === m.score_home && a === m.score_away) { conta(m.home_team.name, nh(x)); conta(m.away_team.name, na(x)); } }
    const nome = new Map([...co].map(([k, c]) => [k, [...c].sort((p, q) => q[1] - p[1])[0][0]]));
    const e = { giuste: 0, sbagliate: 0, nonTrovate: 0, senzaVerita: 0 }, deboli = new Set();
    for (const m of P) {
      const v = vicine(giorno(m)).filter(x => nh(x) === nome.get(m.home_team.name) && na(x) === nome.get(m.away_team.name)
        && gol(x)[0] === m.score_home && gol(x)[1] === m.score_away);
      if (v.length !== 1) { e.senzaVerita++; continue; }
      const T = F.trovaPartitaQuote(R, cod, m.time_utc.slice(0, 10), m.home_team.name, m.away_team.name);
      if (!T.riga) { e.nonTrovate++; for (const [p, f] of [[m.home_team.name, nh(v[0])], [m.away_team.name, na(v[0])]])
        if (F._simNomi(p, f) < 0.5) deboli.add(`${p} -> ${f} (${F._simNomi(p, f).toFixed(2)})`); }
      else if (T.riga.r === v[0]) e.giuste++;
      else { e.sbagliate++; console.log(`   SBAGLIATA ${m.time_utc.slice(0, 10)} ${m.home_team.name} - ${m.away_team.name} -> ${T.riga.h} - ${T.riga.a}`); }
    }
    console.log(`${lId} ${cod}: ${JSON.stringify(e)}` + (deboli.size ? ' · nomi che non si somigliano: ' + [...deboli].join('; ') : ''));
    for (const k in tot) tot[k] += e[k];
  }
  console.log('TOTALE', JSON.stringify(tot));
  process.exit(tot.sbagliate ? 1 : 0);
})();
