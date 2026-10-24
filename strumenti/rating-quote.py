# Il rating dalle quote passate (AGENTS.md, Il rating dalle quote passate).
#
#   python3 strumenti/rating-quote.py --scarica          # i file di football-data in batch/fd (180 file, fuori da git)
#   python3 strumenti/rating-quote.py                    # l'esplorazione sulle 18 leghe
#   python3 strumenti/rating-quote.py --griglia          # K e regressione d'estate
#   python3 strumenti/rating-quote.py --maestro batch/2627b89   # contro il maestro, sulle partite dei CSV
#
# Nessuna chiamata alla PitchAPI. Per ogni lega, in ordine di data, un rating delle squadre dalle quote di
# chiusura delle partite gia' giocate: log(p1/p2) del mercato = R_casa - R_trasf + H. Dopo ogni giornata,
# con e = log(p1/p2) di chiusura - previsto, R_casa += K*e, R_trasf -= K*e, H += KH*e. A ogni stagione nuova
# i rating si stringono verso la media (REG) e chi entra parte dalla media delle squadre uscite. Le partite
# dello stesso giorno usano i rating di prima del giorno. L'Elo e' quello dei risultati, fatto come quello
# del motore (K 30 e 20, scarto di gol, scala 1.25, HFA dalle vittorie) ma non identico: e' un riferimento.
# Le probabilita' 1X2 escono da una logistica multinomiale su (y, |y|), stimata fuori lega.
import csv, io, os, sys, math, collections, datetime as dt, urllib.request
import numpy as np

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = os.path.join(RADICE, 'batch', 'fd')
STAG = ['1718', '1819', '1920', '2021', '2122', '2223', '2324', '2425', '2526', '2627']
DIVS = ['E0', 'I1', 'SP1', 'D1', 'F1', 'E1', 'N1', 'P1', 'B1', 'D2', 'SC0', 'E2', 'E3', 'T1', 'G1', 'I2', 'SP2', 'F2']
CINQUE = {'E0', 'I1', 'SP1', 'D1', 'F1'}
K, KH, REG, H0 = 0.35, 0.01, 0.85, 0.35

def num(s):
    try:
        v = float(s)
        return v if v > 1.0 else None
    except (TypeError, ValueError):
        return None

def data(s):
    for f in ('%d/%m/%Y', '%d/%m/%y'):
        try: return dt.datetime.strptime(s.strip(), f).date()
        except ValueError: pass
    return None

def tre(r, pref):
    for p in pref:
        q = [num(r.get(p + k)) for k in 'HDA']
        if all(q): return q
    return None

def probs(q):
    inv = [1 / x for x in q]; s = sum(inv)
    return [x / s for x in inv]

def lo(p): return math.log(p[0] / p[2])

def out_of(m): return 0 if m['hg'] > m['ag'] else (1 if m['hg'] == m['ag'] else 2)

def scarica():
    os.makedirs(FD, exist_ok=True)
    for c in DIVS:
        for s in STAG:
            f = os.path.join(FD, f'{c}_{s}.csv')
            if os.path.exists(f) and os.path.getsize(f) > 0: continue
            r = urllib.request.urlopen(urllib.request.Request(f'https://football-data.co.uk/mmz4281/{s}/{c}.csv', headers={'User-Agent': 'Mozilla/5.0'}), timeout=60)
            open(f, 'wb').write(r.read())
    print('file in', FD)

def leggi(div):
    out = []
    for i, s in enumerate(STAG):
        f = os.path.join(FD, f'{div}_{s}.csv')
        if not os.path.exists(f): continue
        for r in csv.DictReader(io.open(f, encoding='utf-8-sig', errors='replace')):
            d = data(r.get('Date', ''))
            if not d or not r.get('HomeTeam'): continue
            try: hg, ag = int(r['FTHG']), int(r['FTAG'])
            except (KeyError, ValueError): hg = ag = None
            c = tre(r, ['AvgC', 'PSC', 'B365C'])
            e = tre(r, ['Avg', 'BbAv', 'PS', 'B365'])
            ou = next(([num(r.get(p + '>2.5')), num(r.get(p + '<2.5'))] for p in ('AvgC', 'PC', 'B365C') if num(r.get(p + '>2.5')) and num(r.get(p + '<2.5'))), None)
            out.append({'div': div, 'stag': i, 'd': d, 'H': r['HomeTeam'].strip(), 'A': r['AwayTeam'].strip(), 'hg': hg, 'ag': ag,
                        'pc': probs(c) if c else None, 'pe': probs(e) if e else None, 'ov': (1 / ou[0]) / (1 / ou[0] + 1 / ou[1]) if ou else None})
    out.sort(key=lambda m: m['d'])
    return out

def per_giorno(ms):
    g = collections.OrderedDict()
    for m in ms: g.setdefault(m['d'], []).append(m)
    return g

def squadre_per_stagione(ms):
    t = collections.defaultdict(set)
    for m in ms: t[m['stag']].update([m['H'], m['A']])
    return t

def rating_quote(ms, K=K, KH=KH, REG=REG):
    R, H, gioc, cur = {}, H0, collections.Counter(), None
    st = squadre_per_stagione(ms)
    for d, day in per_giorno(ms).items():
        s = day[0]['stag']
        if s != cur:
            if cur is not None:
                usc = [R[t] for t in st[cur] if t not in st[s] and t in R]
                lev = sum(usc) / len(usc) if usc else (min(R.values()) if R else 0.0)
                for t in st[s]: R.setdefault(t, lev)
                mu = np.mean([R[t] for t in st[s]])
                for t in st[s]: R[t] = mu + REG * (R[t] - mu)
            cur = s
        for m in day:
            for t in (m['H'], m['A']): R.setdefault(t, 0.0)
            m['yq'] = R[m['H']] - R[m['A']] + H
            m['nq'] = (gioc[m['H']], gioc[m['A']])
        for m in day:
            if not m['pc']: continue
            e = lo(m['pc']) - m['yq']
            R[m['H']] += K * e; R[m['A']] -= K * e; H += KH * e
            gioc[m['H']] += 1; gioc[m['A']] += 1
    return ms

def elo(ms, K1=30, K2=20, SC=1.25):
    R, n, cur, hw, aw = {}, collections.Counter(), None, 0, 0
    st = squadre_per_stagione(ms)
    for d, day in per_giorno(ms).items():
        s = day[0]['stag']
        if s != cur and cur is not None:
            usc = [R[t] for t in st[cur] if t not in st[s] and t in R]
            lev = sum(usc) / len(usc) if usc else 1500
            for t in st[s]: R.setdefault(t, lev)
        cur = s
        hfa = min(100, max(30, 400 * math.log10(max(hw, 1) / max(aw, 1)))) if hw + aw >= 50 else 65
        for m in day:
            for t in (m['H'], m['A']): R.setdefault(t, 1500)
            m['ye'] = (SC * (R[m['H']] - R[m['A']]) + hfa) / 173.72
        for m in day:
            if m['hg'] is None: continue
            dr = R[m['H']] - R[m['A']] + hfa
            ex = 1 / (1 + 10 ** (-dr / 400)); sc = 1 if m['hg'] > m['ag'] else (0.5 if m['hg'] == m['ag'] else 0)
            gd = abs(m['hg'] - m['ag']); mult = 1 if gd <= 1 else (1.5 if gd == 2 else (11 + gd) / 8)
            for t, sg in ((m['H'], 1), (m['A'], -1)):
                R[t] += sg * (K1 if n[t] < 15 else K2) * mult * (sc - ex); n[t] += 1
            if m['hg'] > m['ag']: hw += 1
            elif m['hg'] < m['ag']: aw += 1
    return ms

def tutte(**kw):
    out = []
    for dv in DIVS:
        ms = leggi(dv)
        if not ms: continue
        rating_quote(ms, **kw); elo(ms)
        gio = collections.Counter()
        for m in ms:
            gio[(m['stag'], m['H'])] += 1; gio[(m['stag'], m['A'])] += 1
            m['g'] = min(gio[(m['stag'], m['H'])], gio[(m['stag'], m['A'])])
            m['yc'] = lo(m['pc']) if m['pc'] else None
            m['yp'] = lo(m['pe']) if m['pe'] else None
        out += ms
    return out

def misurabili(ms):
    # dal 2019/20 (due stagioni di rodaggio), col punteggio e le due quote, sei partite di quote per squadra
    return [m for m in ms if m['stag'] >= 2 and m['hg'] is not None and m['pc'] and m['pe'] and min(m['nq']) >= 6]

def fuori_lega(ok, chiavi):
    from sklearn.linear_model import LogisticRegression
    yv = np.array([out_of(m) for m in ok]); divs = sorted(set(m['div'] for m in ok)); P = {}
    for nome, f in chiavi:
        x = np.array([m[f] for m in ok]); X = np.c_[x, np.abs(x)]; Q = np.zeros((len(ok), 3))
        for dv in divs:
            tr = np.array([m['div'] != dv for m in ok])
            Q[~tr] = LogisticRegression(C=100, max_iter=3000).fit(X[tr], yv[tr]).predict_proba(X[~tr])
        P[nome] = Q
    return yv, divs, P

def r2(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    A = np.c_[a, np.ones(len(b))]; c, *_ = np.linalg.lstsq(A, b, rcond=None); e = b - A @ c
    return 1 - e.var() / b.var(), c

def esplora():
    ok = misurabili(tutte())
    CH = [('elo', 'ye'), ('quote passate', 'yq'), ('quote di prima', 'yp'), ('chiusura', 'yc')]
    yv, divs, P = fuori_lega(ok, CH)
    H = {k: (v.argmax(1) == yv) for k, v in P.items()}
    L = {k: -np.log(v[np.arange(len(yv)), yv]) for k, v in P.items()}
    print(f'{len(ok)} partite di {len(divs)} leghe, dal 2019/20; probabilita\' stimate fuori lega')
    for k in P:
        dl = L[k] - L['elo']; dh = H[k].astype(float) - H['elo']
        zl = dl.mean() / (dl.std() / math.sqrt(len(dl))) if dl.std() else 0
        zh = dh.mean() / (dh.std() / math.sqrt(len(dh))) if dh.std() else 0
        meglio = sum(1 for dv in divs if np.mean([dl[i] for i, m in enumerate(ok) if m['div'] == dv]) < 0)
        print(f'  {k:15s} prese {100*H[k].mean():5.2f}%  logloss {L[k].mean():.4f}  contro l\'Elo {1000*dl.mean():+7.2f} per mille (z {zl:+6.2f}), prese {100*dh.mean():+5.2f} (z {zh:+5.2f}), leghe meglio {meglio}/{len(divs)}')
    print('R2 sul log(p1/p2) di chiusura:')
    for nome, sel in (('tutte', ok), ('cinque', [m for m in ok if m['div'] in CINQUE])):
        print(f'  {nome:7s} ' + '  '.join(f'{k} {r2([m[f] for m in sel], [m["yc"] for m in sel])[0]:.3f}' for k, f in CH[:3]))
    print('prese per lega: elo / quote passate / quote di prima / chiusura')
    for dv in divs:
        i = np.array([m['div'] == dv for m in ok]); print(f'  {dv:4s} {i.sum():5d}  ' + '  '.join(f'{100*H[k][i].mean():5.1f}' for k in P))
    print('per giornata della stagione (la meno avanti delle due squadre)')
    for a, b in ((1, 5), (6, 10), (11, 19), (20, 99)):
        i = np.array([a <= m['g'] <= b for m in ok]); print(f'  {a:2d}-{b:2d} {i.sum():5d}  ' + '  '.join(f'{100*H[k][i].mean():5.1f}' for k in P))
    print('selezione: prese nel 10 / 20 / 30 / 50% piu\' sicuro, dentro ogni lega e stagione')
    gruppi = collections.defaultdict(list)
    for j, m in enumerate(ok): gruppi[(m['div'], m['stag'])].append(j)
    for k in P:
        v = []
        for q in (0.1, 0.2, 0.3, 0.5):
            hits = []
            for idx in gruppi.values():
                idx = np.array(idx); o = idx[np.argsort(-P[k][idx].max(1))[:max(1, int(len(idx) * q))]]; hits += list(H[k][o])
            v.append(100 * np.mean(hits))
        print(f'  {k:15s} ' + ' / '.join(f'{x:.1f}' for x in v))

def griglia():
    for k in (0.06, 0.12, 0.2, 0.3, 0.35, 0.4, 0.5, 0.6):
        for rg in (0.7, 0.85, 1.0):
            ok = misurabili(tutte(K=k, REG=rg))
            yv, divs, P = fuori_lega(ok, [('elo', 'ye'), ('q', 'yq')])
            dl = -np.log(P['q'][np.arange(len(yv)), yv]) + np.log(P['elo'][np.arange(len(yv)), yv])
            print(f'K {k:.2f} REG {rg:.2f}: prese {100*(P["q"].argmax(1) == yv).mean():.2f}%, contro l\'Elo {1000*dl.mean():+.2f} per mille, '
                  f'R2 sulla chiusura {r2([m["yq"] for m in ok], [m["yc"] for m in ok])[0]:.4f}')

LEGA_FD = {'Serie A': 'I1', 'Premier League': 'E0', 'LaLiga': 'SP1', 'Bundesliga': 'D1', 'Ligue 1': 'F1', 'Championship': 'E1',
           'Eredivisie': 'N1', 'Liga Portugal': 'P1', 'First Division A': 'B1', '2. Bundesliga': 'D2', 'Premiership': 'SC0',
           'League One': 'E2', 'League Two': 'E3', 'Super Lig': 'T1', 'Serie B': 'I2', 'LaLiga2': 'SP2', 'Ligue 2': 'F2'}

def simile(a, b):
    import difflib, unicodedata
    def n(s):
        s = ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')
        for w in (' fc', 'fc ', ' afc', 'ac ', ' calcio', '1. ', ' cf', 'cf ', 'ssc ', 'as ', 'us '): s = s.replace(w, ' ')
        return ' '.join(s.split())
    a, b = n(a), n(b)
    return 1.0 if (a in b or b in a) else difflib.SequenceMatcher(None, a, b).ratio()

def aggancia(m, fd):
    # per data (entro un giorno) e punteggio, poi il nome: somiglianza delle due squadre almeno 1, staccata di 0.3
    d = dt.date.fromisoformat(m['data'])
    c = [x for x in fd if x['hg'] == m['hg'] and x['ag'] == m['ag'] and abs((x['d'] - d).days) <= 1]
    sc = sorted(((simile(m['H'], x['H']) + simile(m['A'], x['A']), i) for i, x in enumerate(c)), reverse=True)
    if not sc or sc[0][0] < 1.0 or (len(sc) > 1 and sc[0][0] - sc[1][0] < 0.3): return None
    return c[sc[0][1]]

def contro_maestro(cartelle):
    import glob, importlib.util
    from sklearn.linear_model import LogisticRegression
    sp = importlib.util.spec_from_file_location('qb', os.path.join(RADICE, 'strumenti', 'quote-bookmaker.py'))
    qb = importlib.util.module_from_spec(sp); argv = sys.argv; sys.argv = ['x']; sp.loader.exec_module(qb); sys.argv = argv
    cache, righe = {}, []
    for c in cartelle:
        for f in sorted(glob.glob(os.path.join(c, '*.csv'))):
            for m in qb.leggi_csv(f):
                dv = LEGA_FD.get(m['lega'])
                if not dv: continue
                if dv not in cache:
                    ms = leggi(dv); rating_quote(ms); elo(ms); cache[dv] = ms
                x = aggancia(m, cache[dv])
                if x and x['pc'] and x['pe']: righe.append((m, x))
    print(len(righe), 'partite agganciate (data, punteggio e nomi)')
    pm = np.array([m['p'] for m, _ in righe]); yv = np.array([m['out'] for m, _ in righe])
    ym = np.log(pm[:, 0] / pm[:, 2]); yq = np.array([x['yq'] for _, x in righe]); yc = np.array([lo(x['pc']) for _, x in righe])
    yp = np.array([lo(x['pe']) for _, x in righe]); ye = np.array([x['ye'] for _, x in righe])
    for nome, a in (('maestro', ym), ('quote passate', yq), ('elo', ye), ('quote di prima', yp)):
        print(f'  R2 sulla chiusura, {nome:15s} {r2(a, yc)[0]:.3f}')
    A = np.c_[ym, yq, np.ones(len(yc))]; c, *_ = np.linalg.lstsq(A, yc, rcond=None); e = yc - A @ c
    print(f'  R2 sulla chiusura, maestro e quote passate {1 - e.var() / yc.var():.3f} (pesi {c[0]:.3f} e {c[1]:.3f})')
    # le quote passate calibrate sulle stagioni prima del 2026/27 delle leghe di football-data
    tr = [x for ms in cache.values() for x in misurabili(ms) if x['stag'] < len(STAG) - 1]
    cal = LogisticRegression(C=100, max_iter=3000).fit(np.array([[x['yq'], abs(x['yq'])] for x in tr]), np.array([out_of(x) for x in tr]))
    Pq = cal.predict_proba(np.c_[yq, np.abs(yq)])
    def media(w):
        l = (1 - w) * ym + w * yq; pX = pm[:, 1]; p1 = (1 - pX) / (1 + np.exp(-l)); return np.c_[p1, pX, 1 - pX - p1]
    l0 = -np.log(pm[np.arange(len(yv)), yv]); h0 = (pm.argmax(1) == yv)
    for nome, P in (('maestro', pm), ('quote passate', Pq), ('maestro e quote 50/50', media(0.5)),
                    ('quote di prima', np.array([x['pe'] for _, x in righe])), ('chiusura', np.array([x['pc'] for _, x in righe]))):
        h = (P.argmax(1) == yv); dl = -np.log(np.clip(P[np.arange(len(yv)), yv], 1e-9, 1)) - l0
        z = dl.mean() / (dl.std() / math.sqrt(len(dl))) if dl.std() else 0
        print(f'  {nome:24s} prese {100*h.mean():5.2f}%  contro il maestro {1000*dl.mean():+6.2f} per mille (z {z:+.2f}), prese {100*(h.astype(float)-h0).mean():+5.2f}')

if __name__ == '__main__':
    a = sys.argv[1:]
    if '--scarica' in a: scarica()
    elif '--griglia' in a: griglia()
    elif '--maestro' in a: contro_maestro(a[a.index('--maestro') + 1:])
    else: esplora()
