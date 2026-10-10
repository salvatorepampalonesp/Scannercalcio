// Il catalogo delle leghe (AGENTS.md, Il catalogo delle leghe): scarica /leagues dalla PitchAPI e
// riscrive leghe.json e le due copie di riserva dentro le pagine (LEAGUES_CATALOG nello Scanner,
// CMP_LEAGUES_FALLBACK nel Comparatore), poi dice cosa e' cambiato.
//
//   node strumenti/catalogo.js            scarica, confronta e riscrive
//   node strumenti/catalogo.js --prova    dice solo cosa cambierebbe, e se le tre copie sono uguali
//
// Una chiamata. La chiave come per strumenti/batch-auto.js: la aggiunge il proxy dell'ambiente,
// oppure la variabile PITCHAPI_KEY. Non toglie mai una lega o una stagione: se l'API non ne elenca
// piu' una che il file ha, si ferma e lo dice (i batch e i CSV si appoggiano a quelle).
// Dopo una riscrittura scanner.html cambia: build nuova e banco di parita' (skill nuova-build).
const { spawnSync } = require('child_process');
if (process.env.HTTPS_PROXY && !process.env.NODE_USE_ENV_PROXY) {
  const r = spawnSync(process.execPath, ['--no-warnings', __filename, ...process.argv.slice(2)],
                      { stdio: 'inherit', env: { ...process.env, NODE_USE_ENV_PROXY: '1' } });
  process.exit(r.status == null ? 1 : r.status);
}
const fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..');
const PITCH = 'https://pitchapi-proxy.salvatorepampalone-sp.workers.dev', KEY = process.env.PITCHAPI_KEY || '';
const PROVA = process.argv.includes('--prova');
const COPIE = [['scanner.html', /(LEAGUES_CATALOG = )\[\{.*?\}\](;)/], ['comparatore.html', /(const CMP_LEAGUES_FALLBACK = )\[\{.*?\}\](;\n)/]];
const corta = L => JSON.stringify(L.map(l => ({ id: l.id, name: l.name, country_code: l.country_code, seasons: l.seasons })));
const nome = l => `${l.country_code} ${l.name}`;

(async () => {
  const r = await fetch(PITCH + '/leagues', { headers: KEY ? { 'X-API-KEY': KEY } : {} });
  if (!r.ok) { console.log('la PitchAPI ha risposto', r.status, '(manca la chiave?)'); process.exit(1); }
  const testo = await r.text(), vive = (JSON.parse(testo).data || {}).leagues;
  if (!Array.isArray(vive) || !vive.length) { console.log('risposta senza leghe'); process.exit(1); }
  const file = JSON.parse(fs.readFileSync(path.join(ROOT, 'leghe.json'), 'utf8')).data.leagues;
  const V = new Map(vive.map(l => [l.id, l]));

  let tolte = 0, cambi = 0;
  for (const l of file) {
    const v = V.get(l.id);
    if (!v) { console.log('TOLTA dall\'API:', nome(l), l.id); tolte++; continue; }
    const via = l.seasons.filter(s => !v.seasons.includes(s)), nuove = v.seasons.filter(s => !l.seasons.includes(s));
    if (via.length) { console.log('stagioni TOLTE dall\'API:', nome(l), via.join(', ')); tolte++; }
    if (nuove.length) { console.log('stagioni nuove:', nome(l), nuove.join(', ')); cambi++; }
    if (v.name !== l.name || v.country_code !== l.country_code) { console.log('nome o paese cambiato:', nome(l), '->', nome(v)); cambi++; }
  }
  const ids = new Set(file.map(l => l.id));
  for (const v of vive) if (!ids.has(v.id)) { console.log('lega nuova:', nome(v), v.id, v.seasons.join(', ')); cambi++; }

  const sf = corta(file);
  for (const [f, re] of COPIE) {
    const m = re.exec(fs.readFileSync(path.join(ROOT, f), 'utf8'));
    console.log(`copia in ${f}:`, !m ? 'NON TROVATA' : corta(JSON.parse(m[0].slice(m[1].length, -m[2].length))) === sf ? 'uguale a leghe.json' : 'DIVERSA da leghe.json');
  }
  console.log(`leghe: ${file.length} nel file, ${vive.length} nell'API; ${cambi} cambiamenti`);
  if (tolte) { console.log('l\'API non elenca piu\' qualcosa che il file ha: non riscrivo niente, guarda a mano.'); process.exit(1); }
  if (PROVA || !cambi) process.exit(0);

  fs.writeFileSync(path.join(ROOT, 'leghe.json'), testo.endsWith('\n') ? testo : testo + '\n');
  const fb = corta(vive);
  for (const [f, re] of COPIE) {
    const p = path.join(ROOT, f), s = fs.readFileSync(p, 'utf8');
    if (!re.test(s)) { console.log('copia di riserva non trovata in', f); process.exit(1); }
    fs.writeFileSync(p, s.replace(re, (_, a, b) => a + fb + b));
  }
  console.log('riscritti leghe.json, scanner.html e comparatore.html: ora build nuova e banco di parita\'.');
})();
