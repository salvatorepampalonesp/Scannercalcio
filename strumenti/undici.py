# La qualita' dell'undici dai voti dei giocatori (AGENTS.md, Il rating dalle quote passate, «La qualita'
# dell'undici»).
#
#   python3 strumenti/undici.py --scarica "ITA:Serie A=2024/2025,2025/2026,2026/2027" ...   # in batch/giocatori
#   python3 strumenti/undici.py "ITA:Serie A=2024/2025,2025/2026,2026/2027" ...             # la misura
#
# Lo scarico chiede alla PitchAPI l'archivio della lega e, per ogni partita conclusa, /lineups e /players (due
# chiamate a partita, fino a TETTO, di default 8000). La misura: il voto di un giocatore e' la media dei suoi
# voti (rating_title di /players) nelle sue ultime 30 partite di lega, pesata coi minuti e ristretta verso la
# media della lega con KSHR = 3 partite intere. La qualita' dell'undici e' la media dei voti degli 11 titolari;
# quella abituale e' la media, coi voti di oggi, degli undici delle ultime 5 partite della squadra. d = (oggi
# meno abituale) della casa, meno lo stesso della trasferta. Le quote vengono da football-data (batch/fd,
# strumenti/rating-quote.py --scarica): il residuo del mercato e' log(p1/p2) di chiusura meno il rating dalle
# quote passate, o meno le quote di prima della partita. Si confronta anche l'indice per presenze del b43.
import json, os, sys, math, time, collections, threading, importlib.util, urllib.request, urllib.error, concurrent.futures as cf
import datetime as dt
import numpy as np

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(RADICE, 'batch', 'giocatori')
PITCH = 'https://pitchapi-proxy.salvatorepampalone-sp.workers.dev'
KSHR, NABIT, TETTO = 3.0, 5, int(os.environ.get('TETTO', '8000'))
_sp = importlib.util.spec_from_file_location('rq', os.path.join(RADICE, 'strumenti', 'rating-quote.py'))
rq = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(rq)
CAT = json.load(open(os.path.join(RADICE, 'leghe.json')))['data']['leagues']
FDCOD = {'l_0ALvwF': 'I1', 'l_4WFCIZ': 'E0', 'l_0ErfuF': 'SP1', 'l_1Isor4': 'D1', 'l_3FJFUl': 'F1'}

def lega(spec):
    paese, nome = spec.split(':', 1)
    return [l for l in CAT if l['country_code'] == paese and l['name'] == nome][0]['id']

def argomenti(a):
    out = []
    for x in a:
        if x.startswith('--'): continue
        spec, ss = x.split('='); out.append((lega(spec), ss.split(',')))
    return out

def jl(nome):
    try: return json.load(open(os.path.join(DIR, nome)))
    except (OSError, ValueError): return None

_lock = threading.Lock(); _conto = {'chiamate': 0, 'falliti': 0}

def chiama(path):
    for t in range(6):
        with _lock:
            if _conto['chiamate'] >= TETTO: raise SystemExit('tetto di chiamate raggiunto')
            _conto['chiamate'] += 1
        try:
            with urllib.request.urlopen(urllib.request.Request(PITCH + path, headers={'User-Agent': 'Mozilla/5.0'}), timeout=40) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404: return {'_404': True}
            time.sleep((5 if e.code == 429 else 2) * (t + 1))
        except Exception:
            time.sleep(2 * (t + 1))
    with _lock: _conto['falliti'] += 1
    return None

def salva(nome, d):
    f = os.path.join(DIR, nome); json.dump(d, open(f + '.tmp', 'w')); os.replace(f + '.tmp', f)

def scarica(leghe):
    os.makedirs(DIR, exist_ok=True); lavori = []
    for lid, ss in leghe:
        for s in ss:
            nf = f'arch_{lid}_{s.replace("/", "-")}.json'
            if not jl(nf):
                d = chiama(f'/leagues/{lid}/matches?season={s}&status=all')
                if d: salva(nf, d)
            for m in jl(nf)['data']['matches']:
                if m['status'] != 'finished': continue
                for ep in ('lineups', 'players'):
                    if not os.path.exists(os.path.join(DIR, f'{ep}_{m["id"]}.json')): lavori.append((m['id'], ep))
    print(len(lavori), 'chiamate da fare', flush=True)
    def uno(x):
        d = chiama(f'/matches/{x[0]}/{x[1]}')
        if d is not None: salva(f'{x[1]}_{x[0]}.json', d)
    with cf.ThreadPoolExecutor(4) as ex: list(ex.map(uno, lavori))
    print('fine', _conto, flush=True)

def voti(mid):
    d = jl(f'players_{mid}.json'); out = {}
    for p in (d or {}).get('data') or []:
        st = {s['key']: s['stat'].get('value') for g in p['stats'] for s in g['stats'].values()}
        out[p['player']['id']] = (st.get('rating_title'), st.get('minutes_played') or 0)
    return out

def titolari(mid):
    d = (jl(f'lineups_{mid}.json') or {}).get('data')
    try: return {'H': [s['player_id'] for s in d['home']['starters']], 'A': [s['player_id'] for s in d['away']['starters']]}
    except (KeyError, TypeError): return None

def costruisci(lid, ss):
    ms = sorted([dict(m, _stag=s) for s in ss for m in jl(f'arch_{lid}_{s.replace("/", "-")}.json')['data']['matches']
                 if m['status'] == 'finished' and m.get('score_home') is not None], key=lambda m: m['time_utc'])
    fd = rq.leggi(FDCOD[lid]); rq.rating_quote(fd)
    storia, undici, tutti, righe = collections.defaultdict(list), collections.defaultdict(list), [], []
    for m in ms:
        L, V = titolari(m['id']), voti(m['id'])
        mu = np.mean(tutti[-3000:]) if len(tutti) > 200 else 6.8
        def q(p):
            h = storia[p][-30:]
            return (sum(r * mi / 90 for r, mi in h) + KSHR * mu) / (sum(mi / 90 for _, mi in h) + KSHR)
        f = {}
        if L and len(L['H']) == 11 and len(L['A']) == 11:
            for lato, team in (('H', m['home_team']['id']), ('A', m['away_team']['id'])):
                prev = undici[team][-NABIT:]
                if len(prev) >= 3:
                    f[lato] = np.mean([q(p) for p in L[lato]]) - np.mean([np.mean([q(p) for p in xi]) for xi in prev])
                    p10 = undici[team][-10:]; sh = collections.Counter(x for xi in p10 for x in xi)
                    reg = {x: c / len(p10) for x, c in sh.items() if c / len(p10) >= 0.5}
                    f[lato + 'p'] = sum(v for x, v in reg.items() if x not in L[lato]) / max(sum(reg.values()), 1e-9)
                undici[team].append(L[lato])
        if 'H' in f and 'A' in f:
            x = rq.aggancia({'data': m['date'], 'hg': m['score_home'], 'ag': m['score_away'], 'H': m['home_team']['name'], 'A': m['away_team']['name']}, fd)
            if x and x['pc'] and x['pe'] and min(x['nq']) >= 6:
                righe.append({'stag': m['_stag'], 'hg': m['score_home'], 'ag': m['score_away'], 'd': f['H'] - f['A'], 'p': f['Hp'] - f['Ap'],
                              'yq': x['yq'], 'yc': rq.lo(x['pc']), 'yp': rq.lo(x['pe'])})
        for p, (r, mi) in V.items():
            if r is not None and mi >= 10: storia[p].append((r, mi)); tutti.append(r)
    return righe

def ols(y, X):
    X = np.c_[X, np.ones(len(y))]; b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    se = np.sqrt(np.diag(e.var() * len(y) / (len(y) - X.shape[1]) * np.linalg.inv(X.T @ X)))
    return b, se, 1 - e.var() / y.var()

def misura(leghe):
    from sklearn.linear_model import LogisticRegression
    R = [r for lid, ss in leghe for r in costruisci(lid, ss)]
    d, pr = np.array([r['d'] for r in R]), np.array([r['p'] for r in R])
    yq, yc, yp = (np.array([r[k] for r in R]) for k in ('yq', 'yc', 'yp'))
    print(f'{len(R)} partite con formazioni, voti e quote; deviazione standard di d {d.std():.3f}')
    for nome, y in (('chiusura meno quote passate', yc - yq), ('chiusura meno quote di prima', yc - yp)):
        b, se, r2 = ols(y, d[:, None]); print(f'  {nome}: coefficiente di d {b[0]:+.3f} (z {b[0]/se[0]:+.2f}), R2 {r2:.3f}')
    b, se, r2 = ols(yc - yq, pr[:, None]); print(f'  chiusura meno quote passate, presenze (b43): {b[0]:+.3f} (z {b[0]/se[0]:+.2f}), R2 {r2:.3f}')
    b, se, r2 = ols(yc - yq, np.c_[d, pr]); print(f'  le due insieme: {b[0]:+.3f} (z {b[0]/se[0]:+.2f}) e {b[1]:+.3f} (z {b[1]/se[1]:+.2f}), R2 {r2:.3f}')
    # sui risultati: 1X2 da (y, |y|) stimato sulle altre stagioni, con y' = y + c*d e c preso dal mercato
    yv = np.array([0 if r['hg'] > r['ag'] else (1 if r['hg'] == r['ag'] else 2) for r in R]); st = np.array([r['stag'] for r in R])
    def prob(y):
        P = np.zeros((len(yv), 3)); X = np.c_[y, np.abs(y)]
        for s in sorted(set(st)): P[st == s] = LogisticRegression(C=1e4, max_iter=3000).fit(X[st != s], yv[st != s]).predict_proba(X[st == s])
        return P
    for nome, base in (('quote passate', yq), ('quote di prima', yp)):
        c = ols(yc - base, d[:, None])[0][0]; P0, P1 = prob(base), prob(base + c * d)
        dl = np.log(P0[np.arange(len(yv)), yv]) - np.log(P1[np.arange(len(yv)), yv]); dh = (P1.argmax(1) == yv).astype(float) - (P0.argmax(1) == yv)
        print(f'  risultati, {nome} + {c:.2f}*d: logloss {1000*dl.mean():+.2f} per mille (z {dl.mean()/(dl.std()/math.sqrt(len(dl))):+.2f}), '
              f'prese {100*(P0.argmax(1) == yv).mean():.2f} -> {100*(P1.argmax(1) == yv).mean():.2f} ({100*dh.mean():+.2f}, z {dh.mean()/(dh.std()/math.sqrt(len(dh))):+.2f})')

if __name__ == '__main__':
    a = sys.argv[1:]
    (scarica if '--scarica' in a else misura)(argomenti(a))
