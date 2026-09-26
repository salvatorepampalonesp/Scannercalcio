// Strada /quote/ del worker Cloudflare (pitchapi-proxy): passa allo Scanner i file delle quote
// di football-data.co.uk, che il browser non puo' leggere da solo (non mandano l'intestazione
// CORS). Legge solo i file dell'elenco, niente chiave, niente dati dell'utente.
// Come si aggiunge al worker: vedi AGENTS.md, Le quote automatiche.

const QUOTE_FILE_OK = /^(fixtures\.csv|new_league_fixtures\.csv|mmz4281\/\d{4}\/[A-Z0-9]{1,4}\.csv|new\/[A-Z]{3}\.csv)$/;

async function gestisciQuote(request) {
  const url = new URL(request.url);
  if (!url.pathname.startsWith('/quote/')) return null;
  const cors = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Max-Age': '86400',
  };
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
  if (request.method !== 'GET') return new Response('metodo non ammesso', { status: 405, headers: cors });
  const file = url.pathname.slice('/quote/'.length);
  if (!QUOTE_FILE_OK.test(file)) return new Response('file non ammesso', { status: 404, headers: cors });
  const storico = !file.endsWith('fixtures.csv');
  let r;
  try {
    r = await fetch('https://www.football-data.co.uk/' + file, {
      headers: { 'User-Agent': 'Mozilla/5.0 (pitchapi-proxy quote)' },
      cf: { cacheTtl: storico ? 21600 : 1800, cacheEverything: true },
    });
  } catch (e) {
    return new Response('football-data non raggiungibile', { status: 502, headers: cors });
  }
  if (!r.ok) return new Response('football-data ha risposto ' + r.status, { status: r.status === 404 ? 404 : 502, headers: cors });
  return new Response(await r.text(), {
    status: 200,
    headers: { ...cors, 'Content-Type': 'text/csv; charset=utf-8', 'Cache-Control': 'public, max-age=' + (storico ? 3600 : 900) },
  });
}

if (typeof module !== 'undefined') module.exports = { gestisciQuote, QUOTE_FILE_OK };
