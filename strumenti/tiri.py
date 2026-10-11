# I tiri uno per uno e la curva di pressione delle partite di lega dei batch (PitchAPI /shots, /momentum, /events).
#
#   python3 strumenti/tiri.py --scarica [cartelle]     # una chiamata per partita e per endpoint, in batch/tiri e batch/eventi
#
# Le partite sono quelle concluse dell'ARCHIVIO DI LEGA in fondo ai CSV delle cartelle (di default tutte quelle dei
# batch). Ogni partita e' un file JSON compatto in batch/tiri, fuori da git; i gol degli eventi vanno in batch/eventi,
# nella forma di strumenti/primo-gol.py. Una partita gia' scaricata si salta: rilanciare riprende.
import os, sys, json, glob, ssl, time, threading, collections, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PITCH = 'https://pitchapi-proxy.salvatorepampalone-sp.workers.dev'
TIRI = os.path.join(RADICE, 'batch', 'tiri')
EVENTI = os.path.join(RADICE, 'batch', 'eventi')
CARTELLE = ['batch48', 'batch4', 'batch/2627', 'batch/nuove', 'batch/livello', 'batch/lontane', 'batch/anno2026',
            'batch/europa2526', 'batch/numeri', 'batch/numeri-prova1', 'batch/numeri-prova2']

def archivio(cartelle):
    A = {}
    for c in cartelle:
        for f in sorted(glob.glob(os.path.join(RADICE, c, '*.csv'))):
            for l in open(f, encoding='utf-8'):
                if not l.startswith('ARCHIVIO #'): continue
                p = l.rstrip('\n').split(';')
                if p[4] != 'finished' or p[9] == '': continue
                A[p[1]] = dict(id=p[1], stagione=p[2], ora=p[3], h=p[5], a=p[7], gh=int(p[9]), ga=int(p[10]))
    return A

_CTX = ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt') if os.path.exists('/root/.ccr/ca-bundle.crt') else None
_CHIAVE = os.environ.get('PITCHAPI_KEY')

# la PitchAPI respinge (429, Retry-After 1) oltre circa 10 chiamate al secondo: un solo ritmo per tutti i fili
RITMO = 8.0
_LOCK, _PROSSIMA = threading.Lock(), [0.0]
def _turno(ritardo=0.0):
    with _LOCK:
        t = max(time.time(), _PROSSIMA[0]) + ritardo; _PROSSIMA[0] = t + 1.0 / RITMO
    time.sleep(max(0.0, t - time.time()))

def chiama(path):
    h = {'User-Agent': 'Mozilla/5.0'}
    if _CHIAVE: h['X-API-KEY'] = _CHIAVE
    for prova in range(8):
        _turno()
        try:
            with urllib.request.urlopen(urllib.request.Request(PITCH + path, headers=h), context=_CTX, timeout=30) as r:
                return 200, json.load(r).get('data')
        except urllib.error.HTTPError as e:
            if e.code == 404: return 404, None
            ra = e.headers.get('Retry-After') if e.headers else None
            _turno(float(ra) if ra and ra.replace('.', '').isdigit() else 2 ** min(prova, 4))
        except Exception:
            time.sleep(2 ** prova)
    return None, None

def _tiro(s, per):
    g = lambda k: s.get(k)
    return dict(t=g('team_id'), m=g('minute'), ma=g('minute_added') or 0, p=1 if per == 'FirstHalf' else 2 if per == 'SecondHalf' else 0,
                xg=g('expected_goals'), xgot=g('expected_goals_on_target'), sit=g('situation'), st=g('shot_type'),
                box=g('is_inside_box'), ev=g('event_type'), og=bool(g('is_own_goal')), x=g('x'), y=g('y'),
                on=g('is_on_target'), bl=bool(g('is_blocked')), pl=(g('player') or {}).get('id'), k=(g('keeper') or {}).get('id'))

def uno(mid):
    f = os.path.join(TIRI, mid + '.json'); fe = os.path.join(EVENTI, mid + '.json'); esito = []
    if os.path.exists(f):
        try: json.load(open(f))
        except ValueError: os.remove(f)
    if os.path.exists(fe):
        try: json.load(open(fe))
        except ValueError: os.remove(fe)
    if not os.path.exists(f):
        c1, s = chiama(f'/matches/{mid}/shots'); c2, mo = chiama(f'/matches/{mid}/momentum')
        if c1 is None or c2 is None: return 'fallita'
        tiri = [_tiro(x, p.get('period')) for p in ((s or {}).get('periods') or []) for x in (p.get('shots') or [])]
        punti = [[q.get('minute'), q.get('value')] for q in ((mo or {}).get('points') or [])]
        json.dump(dict(ok=c1 == 200, tiri=tiri, mo=punti), open(f, 'w'), separators=(',', ':')); esito.append('tiri')
    if not os.path.exists(fe):
        c, d = chiama(f'/matches/{mid}/events')
        if c is None: return 'fallita'
        evs = (d or {}).get('events') if isinstance(d, dict) else d
        gol = [dict(m=e.get('minute'), add=e.get('minute_added'), per=e.get('period'), t=e.get('team_id'), og=bool(e.get('is_own_goal')))
               for e in (evs or []) if str(e.get('event_type', '')).lower() == 'goal']
        json.dump(dict(ok=evs is not None, gol=gol), open(fe, 'w')); esito.append('eventi')
    return '+'.join(esito) or 'gia'

def scarica(ids, fili=10):
    os.makedirs(TIRI, exist_ok=True); os.makedirs(EVENTI, exist_ok=True)
    conto = collections.Counter(); t0 = time.time()
    with ThreadPoolExecutor(fili) as ex:
        for i, r in enumerate(ex.map(uno, ids)):
            conto[r] += 1
            if (i + 1) % 1000 == 0: print(f'  {i + 1}/{len(ids)} in {time.time() - t0:.0f}s', dict(conto), flush=True)
    print('scaricate:', dict(conto), flush=True)

if __name__ == '__main__' and '--scarica' in sys.argv:
    cart = [a for a in sys.argv[1:] if not a.startswith('--')] or CARTELLE
    # in ordine di cartella: le prime (le leghe dove si esplora) arrivano per prime
    ids, visti = [], set()
    for c in cart:
        for mid in sorted(archivio([c])):
            if mid not in visti: visti.add(mid); ids.append(mid)
    print(f'{len(ids)} partite concluse negli archivi di {len(cart)} cartelle', flush=True)
    scarica(ids)
