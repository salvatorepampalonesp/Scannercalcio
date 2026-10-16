# Chi fa piu' corner (AGENTS.md, Chi fa piu' corner: la regola).
#
#   python3 strumenti/corner-differenza.py                 # l'esplorazione sulle 24 leghe, e i numeri della regola
#   python3 strumenti/corner-differenza.py --prova <cartelle>   # il test registrato, coi numeri di REGOLA
#   python3 strumenti/corner-differenza.py --rese          # le rese per fascia dei mercati nuovi nel tabellone (24 leghe fuori lega, b74 con REGOLA)
#   python3 strumenti/corner-differenza.py --schermo <cartelle>  # dal b84: i corner che lo Scanner ha stampato, rifatti dal CSV con REGOLA
#
# Il totale dei corner di una partita quasi non si prevede (b76), chi ne fa di piu' si'. Il modello divide il totale
# fra le due squadre:
#   totale T ~ binomiale negativa, media c + b*(corner previsti casa + trasferta), dispersione kT
#   corner di casa | T ~ beta-binomiale(T, s, phi),  s = sigmoide(a + b1*log(previsti casa / previsti trasf) + b2*diff Elo/100)
# Dalla distribuzione della differenza D = casa - trasferta escono il corner 1X2 e ogni linea dell'handicap.
# La beta-binomiale tiene la correlazione negativa fra i corner delle due squadre (residui -0.21): con due binomiali
# negative indipendenti la differenza verrebbe troppo stretta.
import os, io, re, sys, csv, glob, math, collections
import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln, betaln, expit

QUI = os.path.dirname(os.path.abspath(__file__)); RADICE = os.path.dirname(QUI)
ESPLORA = ['batch48', 'batch4', 'batch/2627', 'batch/nuove', 'batch/livello']
FUORI = ('Saudi_Pro_League_2023-2024', 'Super_League_1_2025-2026')   # senza una stagione alle spalle
MINIMO = 0.5     # corner previsti sotto questo valore (0 quando la squadra non ha dati) contano MINIMO

# fissati sull'esplorazione (le 24 leghe, 23.278 partite), prima di aprire i dati del test
REGOLA = dict(c=5.3693, b=0.4597, kT=63.97, a=0.112, b1=0.5231, b2=0.1781, phi=13.843,
              costante=[0.541, 0.0936, 0.3655],            # casa piu' corner / pari / trasferta: la frequenza delle 24 leghe
              handicap={'-1.5': 0.4445, '1.5': 0.7216})    # casa -1.5 e +1.5: le frequenze delle 24 leghe

def num(s):
    s = (s or '').strip().replace('%', '').replace(',', '.')
    try: v = float(s.split()[0])
    except Exception: return None
    return v if math.isfinite(v) else None

def leggi(f):
    righe = collections.defaultdict(list)
    for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if not r or not r[0]: continue
        if r[0].startswith('=== ARCHIVIO'): break
        righe[r[0]].append(r)
    g = lambda k, i=0: righe[k][i] if k in righe and len(righe[k]) > i else None
    ids = g('ID PARTITA'); out = []
    k = re.match(r'Backtest_V97_(.+)_(\d{4}(?:-\d{4})?)\.csv', os.path.basename(f))
    for c in range(1, len(ids), 4):
        if not ids[c]: continue
        v = lambda k, j=0, i=0: (g(k, i)[c + j] if g(k, i) and len(g(k, i)) > c + j else None)
        if not (v('COPIA CONFORME DELLO SCANNER') or '').startswith('SI'): continue
        x = dict(id=ids[c], lega=k.group(1), stag=k.group(2), ph=num(v('Corner', 0, 0)), pa=num(v('Corner', 0, 1)),
                 rh=num(v('Corner', 2, 0)), ra=num(v('Corner', 2, 1)), elod=num(v('ELO Diff (H-A)')))
        if None in x.values(): continue
        out.append(x)
    return out

def carica(dirs):
    P = {}
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(RADICE, d, '*.csv'))):
            if any(s in f for s in FUORI): continue
            for m in leggi(f): P[m['id']] = m
    M = list(P.values())
    A = {k: np.array([m[k] for m in M], float) for k in ('ph', 'pa', 'rh', 'ra', 'elod')}
    A['ph'] = np.maximum(A['ph'], MINIMO); A['pa'] = np.maximum(A['pa'], MINIMO)
    A['lega'] = np.array([m['lega'] for m in M]); A['stag'] = np.array([m['stag'] for m in M]); A['id'] = np.array([m['id'] for m in M])
    return A

def _parti(th, A, i):
    c, b, lkT, a, b1, b2, lphi = th
    mu = np.maximum(c + b * (A['ph'][i] + A['pa'][i]), 2.0)
    s = expit(a + b1 * np.log(A['ph'][i] / A['pa'][i]) + b2 * A['elod'][i] / 100)
    return mu, math.exp(lkT), s, math.exp(lphi)

def _nll(th, A, i):
    mu, k, s, phi = _parti(th, A, i); t = (A['rh'][i] + A['ra'][i]).astype(int); h = A['rh'][i].astype(int)
    lT = gammaln(t + k) - gammaln(k) - gammaln(t + 1) + k * np.log(k / (k + mu)) + t * np.log(mu / (k + mu))
    al, be = s * phi, (1 - s) * phi
    lH = gammaln(t + 1) - gammaln(h + 1) - gammaln(t - h + 1) + betaln(h + al, t - h + be) - betaln(al, be)
    return -(lT + lH).sum()

def stima(A, i):
    th = minimize(_nll, [4.0, 0.6, 3.0, 0.1, 0.8, 0.1, 3.0], args=(A, i), method='L-BFGS-B').x
    c, b, lkT, a, b1, b2, lphi = th
    return dict(c=round(c, 4), b=round(b, 4), kT=round(math.exp(lkT), 2), a=round(a, 4), b1=round(b1, 4), b2=round(b2, 4), phi=round(math.exp(lphi), 3))

def _th(r): return [r['c'], r['b'], math.log(r['kT']), r['a'], r['b1'], r['b2'], math.log(r['phi'])]

TT = np.arange(41); V = np.arange(-40, 41)
def differenza(r, A, i):
    # la distribuzione di D = casa - trasferta, da -40 a +40
    mu, k, s, phi = _parti(_th(r), A, i)
    PT = np.exp(gammaln(TT + k) - gammaln(k) - gammaln(TT + 1) + k * np.log(k / (k + mu[:, None])) + TT * np.log(mu[:, None] / (k + mu[:, None])))
    PT /= PT.sum(1, keepdims=True)
    D = np.zeros((len(mu), 81)); al, be = s * phi, (1 - s) * phi
    for t in range(41):
        h = np.arange(t + 1)
        pb = np.exp(gammaln(t + 1) - gammaln(h + 1) - gammaln(t - h + 1)
                    + betaln(h[None, :] + al[:, None], t - h[None, :] + be[:, None]) - betaln(al, be)[:, None])
        D[:, 2 * h - t + 40] += PT[:, t:t + 1] * pb
    return D

def zeta(d): d = np.asarray(d, float); return d.mean() / d.std(ddof=1) * math.sqrt(len(d))
def tre(D): return np.c_[(D * (V > 0)).sum(1), (D * (V == 0)).sum(1), (D * (V < 0)).sum(1)]
LINEE = (-2.5, -1.5, -0.5, 0.5, 1.5, 2.5)

def descrivi(A, D, costante, titolo):
    d = (A['rh'] - A['ra']).astype(int); y = np.where(d > 0, 0, np.where(d == 0, 1, 2)); idx = np.arange(len(y)); P = tre(D)
    print(f'\n=== {titolo} ===')
    print(f'  previsto casa / pari / trasferta {100 * P[:, 0].mean():.1f} / {100 * P[:, 1].mean():.1f} / {100 * P[:, 2].mean():.1f}'
          f'  reale {100 * (y == 0).mean():.1f} / {100 * (y == 1).mean():.1f} / {100 * (y == 2).mean():.1f}')
    pp = P[:, 0] / (P[:, 0] + P[:, 2])
    for a, b in ((0, .4), (.4, .5), (.5, .6), (.6, .7), (.7, 1.01)):
        k = (pp >= a) & (pp < b) & (y != 1)
        if k.sum() > 50: print(f'    casa sopra trasferta {int(100 * a)}-{min(100, int(100 * b))}%: {k.sum()} partite, previsto {100 * pp[k].mean():.1f}, esce {100 * (y[k] == 0).mean():.1f}')
    # contro la frequenza della lega presa sulle stesse partite (col senno di poi: solo descrittivo)
    fr = np.zeros_like(P)
    for l in set(A['lega']):
        k = A['lega'] == l; fr[k] = [(y[k] == j).mean() for j in range(3)]
    dd = -np.log(P[idx, y]) + np.log(fr[idx, y])
    print(f'  contro la frequenza della lega sulle stesse partite (col senno di poi): {1000 * dd.mean():+.1f} per mille (z {zeta(dd):+.1f})')
    for h in LINEE:
        p = (D * (V + h > 0)).sum(1); yy = d + h > 0
        print(f'    handicap casa {h:+.1f}: previsto {100 * p.mean():.1f}%, esce {100 * yy.mean():.1f}%')

# i mercati del tabellone (b84): chiave, nome, condizione su D = casa - trasferta, base di lega fissa
MERCATI = [('cdH', 'Corner: piu\' la casa', lambda v: v > 0, REGOLA['costante'][0]),
           ('cdA', 'Corner: piu\' la trasferta', lambda v: v < 0, REGOLA['costante'][2]),
           ('chH', 'Corner: casa -1.5', lambda v: v >= 2, REGOLA['handicap']['-1.5']),
           ('chA', 'Corner: trasferta -1.5', lambda v: v <= -2, round(1 - REGOLA['handicap']['1.5'], 4)),
           ('chH+', 'Corner: casa +1.5', lambda v: v >= -1, REGOLA['handicap']['1.5']),
           ('chA+', 'Corner: trasferta +1.5', lambda v: v <= 1, round(1 - REGOLA['handicap']['-1.5'], 4))]
FASCE = ((20, 'FORTE'), (10, 'GIOCABILE'), (5, 'MARGINALE'))

def _tabellone(dirs):
    # dal CSV, la proposta in cima di ogni partita come la stampava lo Scanner: scarto, se e' uscita, e il suo mercato
    T = {}
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(RADICE, d, '*.csv'))):
            if any(s in f for s in FUORI): continue
            righe = collections.defaultdict(list)
            for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
                if not r or not r[0]: continue
                if r[0].startswith('=== ARCHIVIO'): break
                righe[r[0]].append(r)
            ids = righe['ID PARTITA'][0]; cc = righe['COPIA CONFORME DELLO SCANNER'][0]
            tab = [righe['Tabellone #%d' % i][0] for i in range(1, 40) if righe.get('Tabellone #%d' % i)]
            for c in range(1, len(ids), 4):
                if not ids[c] or not cc[c].startswith('SI'): continue
                V = []
                for r in tab:
                    if len(r) <= c + 3 or not r[c]: continue
                    m = re.match(r'scarto ([+-]?[\d,]+)', r[c + 3] or '')
                    V.append(dict(nome=re.sub(r' [\d,]+%?$', '', r[c]).strip(), hit=r[c + 2], e=num(m.group(1)) if m else None))
                T[ids[c]] = (os.path.basename(f), V)
    return T

def rese():
    A1 = carica(ESPLORA); A2 = carica(['batch/lontane', 'batch/anno2026', 'batch/europa2526'])
    n1 = len(A1['lega']); D1 = np.zeros((n1, 81))
    for l in sorted(set(A1['lega'])):
        te = np.where(A1['lega'] == l)[0]; D1[te] = differenza(stima(A1, np.where(A1['lega'] != l)[0]), A1, te)
    D2 = differenza(REGOLA, A2, np.arange(len(A2['lega'])))
    print(f'24 leghe {n1} partite (fuori lega), b74 {len(A2["lega"])} partite (REGOLA)')
    righe = []    # (campione, mercato, scarto, uscita, frequenza alla cieca della stagione)
    for cam, A, D in (('24', A1, D1), ('b74', A2, D2)):
        d = (A['rh'] - A['ra']).astype(int); gr = collections.defaultdict(list)
        for i, (l, s_) in enumerate(zip(A['lega'], A['stag'])): gr[(l, s_)].append(i)
        for key, nome, cond, base in MERCATI:
            p = (D * cond(V)[None, :]).sum(1); y = cond(d).astype(float); cieca = np.zeros(len(y))
            for ii in gr.values(): cieca[ii] = y[ii].mean()
            for i in range(len(y)): righe.append((cam, key, 100 * (p[i] - base), y[i], cieca[i]))
    R = np.array([(r[2], r[3], r[4]) for r in righe]); cam = np.array([r[0] for r in righe]); key = np.array([r[1] for r in righe])
    def fascia(k):
        e = R[k, 0]; g = 100 * (R[k, 1] - R[k, 2]); out = []
        for i, (sg, nm) in enumerate(FASCE):
            hi = FASCE[i - 1][0] if i else 1e9; m = (e >= sg) & (e < hi)
            out.append((nm, m.sum(), g[m].mean() if m.sum() else float('nan'), 2 * g[m].std(ddof=1) / math.sqrt(m.sum()) if m.sum() > 1 else float('nan')))
        return out
    for titolo, k in (('tutti i mercati, 24 leghe + b74', np.ones(len(R), bool)), ('24 leghe', cam == '24'), ('b74', cam == 'b74'),
                      ('le quattro proposte (senza +1.5), 24 + b74', ~np.isin(key, ['chH+', 'chA+']))):
        print(f'\n=== {titolo} ===')
        for nm, nn, g, se in fascia(k): print(f'  {nm:10s} {nn:6d} proposte  rende {g:+.1f} (+/-{se:.1f})')
    print('\n=== per mercato, 24 + b74 ===')
    for k_, nome, _, base in MERCATI:
        k = key == k_; e = R[k, 0]
        print(f'  {nome:26s} base {100 * base:.1f}  scarto>=5 su {100 * (e >= 5).mean():.1f}% delle partite, >=10 {100 * (e >= 10).mean():.1f}%, >=20 {100 * (e >= 20).mean():.1f}%'
              + ''.join(f' · {nm} {g:+.1f} ({nn})' for nm, nn, g, se in fascia(k)))
    # la proposta in cima al tabellone, con e senza i mercati nuovi (descrittivo: i tabelloni dei CSV sono dei motori di allora)
    T = _tabellone(ESPLORA + ['batch/lontane', 'batch/anno2026', 'batch/europa2526'])
    freq = collections.defaultdict(list)
    for fn, Vv in T.values():
        for v in Vv:
            if v['hit'] in ('SI', 'NO'): freq[(fn, v['nome'])].append(v['hit'] == 'SI')
    freq = {k_: sum(v) / len(v) for k_, v in freq.items()}
    # per ogni partita, la proposta nuova con lo scarto piu' alto (le +1.5 escluse: vedi sotto) e cosa rende
    best = {}
    for (cm, k_, e, y, c), mid in zip(righe, [x for cm_, A in (('24', A1), ('b74', A2)) for _ in MERCATI for x in A['id']]):
        if k_ in ('chH+', 'chA+') or e < 5: continue
        if mid not in best or e > best[mid][0]: best[mid] = (e, 100 * (y - c))
    for titolo, ids in (('24 leghe', set(A1['id'])), ('b74', set(A2['id']))):
        g0, g1, cambia = [], [], 0
        for mid in ids:
            if mid not in T: continue
            fn, Vv = T[mid]
            if not Vv or Vv[0]['hit'] not in ('SI', 'NO') or Vv[0]['e'] is None: continue
            v = Vv[0]; a0 = 100 * ((v['hit'] == 'SI') - freq[(fn, v['nome'])]); g0.append(a0)
            if mid in best and best[mid][0] > v['e']: g1.append(best[mid][1]); cambia += 1
            else: g1.append(a0)
        g0, g1 = np.array(g0), np.array(g1); dd = g1 - g0
        print(f'  prima proposta, {titolo}: {len(g0)} partite, {g0.mean():+.2f} -> {g1.mean():+.2f} ({dd.mean():+.2f} +/-{2 * dd.std(ddof=1) / math.sqrt(len(dd)):.2f}), in cima un corner in {cambia} partite')

RIGHE_SCHERMO = (("Corner: piu' la casa", lambda D: (D * (V > 0)).sum(1)), ('Corner: stesso numero', lambda D: (D * (V == 0)).sum(1)),
                 ("Corner: piu' la trasferta", lambda D: (D * (V < 0)).sum(1)), ('Corner: casa -1.5', lambda D: (D * (V >= 2)).sum(1)),
                 ('Corner: casa +1.5', lambda D: (D * (V >= -1)).sum(1)))

def schermo(dirs, reg=REGOLA, tol=0.15):
    # le probabilita' del CSV sono quelle che lo Scanner ha stampato (copia conforme): si rifanno dai corner previsti
    # e dalla differenza di Elo del CSV coi numeri della regola. Il CSV ha 2 decimali sui corner e 1 sulle probabilita'.
    peggio, n = 0.0, 0
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(RADICE, d, '*.csv'))):
            righe = collections.defaultdict(list)
            for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
                if not r or not r[0]: continue
                if r[0].startswith('=== ARCHIVIO'): break
                righe[r[0]].append(r)
            if RIGHE_SCHERMO[0][0] not in righe: print(f'  {os.path.basename(f)}: senza le righe del b84'); continue
            ids = righe['ID PARTITA'][0]; cc = righe['COPIA CONFORME DELLO SCANNER'][0]; X = []
            for c in range(1, len(ids), 4):
                if not ids[c] or not cc[c].startswith('SI'): continue
                ph, pa, e = num(righe['Corner'][0][c]), num(righe['Corner'][1][c]), num(righe['ELO Diff (H-A)'][0][c])
                st = [num(righe[k][0][c]) for k, _ in RIGHE_SCHERMO]
                if None in (ph, pa, e) or None in st: continue
                X.append((max(ph, MINIMO), max(pa, MINIMO), e, st))
            if not X: continue
            A = {'ph': np.array([x[0] for x in X]), 'pa': np.array([x[1] for x in X]), 'elod': np.array([x[2] for x in X])}
            D = differenza(reg, A, np.arange(len(X))); S = np.array([x[3] for x in X])
            R_ = np.c_[tuple(100 * fn(D) for _, fn in RIGHE_SCHERMO)]; dd = np.abs(R_ - S).max()
            peggio = max(peggio, dd); n += len(X)
            print(f'  {os.path.basename(f)}: {len(X)} partite, scarto massimo {dd:.3f} punti')
    print(f'{n} partite, scarto massimo {peggio:.3f} punti (tolleranza {tol}): {"COINCIDE" if n and peggio <= tol else "NON COINCIDE"}')
    return n > 0 and peggio <= tol

def esplora():
    A = carica(ESPLORA); n = len(A['lega']); tutte = np.arange(n)
    print(f'{n} partite di {len(set(A["lega"]))} leghe')
    r = stima(A, tutte); print('\nREGOLA (stimata su tutte):', r)
    d = (A['rh'] - A['ra']).astype(int); y = np.where(d > 0, 0, np.where(d == 0, 1, 2))
    cst = [round(float((y == j).mean()), 4) for j in range(3)]; print('  costante (frequenza delle 24 leghe):', cst)
    print('  handicap (frequenze delle 24 leghe):', {str(h): round(float((d + h > 0).mean()), 4) for h in (-1.5, 1.5)})
    D = np.zeros((n, 81)); leghe = sorted(set(A['lega']))
    for l in leghe:
        te = np.where(A['lega'] == l)[0]; D[te] = differenza(stima(A, np.where(A['lega'] != l)[0]), A, te)
    P = tre(D); idx = np.arange(n); dl = -np.log(P[idx, y]) + np.log(np.array(cst)[y])
    print(f'\n=== fuori lega, corner 1X2 contro la costante ===\n  {1000 * dl.mean():+.1f} per mille (z {zeta(dl):+.1f}),'
          f' meglio in {sum(dl[A["lega"] == l].mean() < 0 for l in leghe)} leghe su {len(leghe)}')
    meta = np.array([int(s[:4]) <= 2024 for s in A['stag']])
    print(f'  2023/24-2024/25 {1000 * dl[meta].mean():+.1f} (z {zeta(dl[meta]):+.1f}), dal 2025 {1000 * dl[~meta].mean():+.1f} (z {zeta(dl[~meta]):+.1f})')
    for h in (-1.5, 1.5):
        p = (D * (V + h > 0)).sum(1); yy = d + h > 0
        fh = float((d + h > 0).mean()); dh = -np.log(np.where(yy, p, 1 - p)) + np.log(np.where(yy, fh, 1 - fh))
        print(f'  handicap casa {h:+.1f} contro la sua frequenza: {1000 * dh.mean():+.1f} per mille (z {zeta(dh):+.1f})')
    for l in leghe:
        k = A['lega'] == l; print(f'    {l:34s} {k.sum():5d}  {1000 * dl[k].mean():+7.1f}')
    descrivi(A, D, cst, 'fuori lega, descrittivi')

def prova(dirs):
    A = carica(dirs); n = len(A['lega']); idx = np.arange(n)
    d = (A['rh'] - A['ra']).astype(int); y = np.where(d > 0, 0, np.where(d == 0, 1, 2))
    D = differenza(REGOLA, A, idx); P = tre(D); cst = np.array(REGOLA['costante'])
    dl = -np.log(P[idx, y]) + np.log(cst[y]); leghe = sorted(set(A['lega'])); grandi = [l for l in leghe if (A['lega'] == l).sum() >= 100]
    meglio = sum(dl[A['lega'] == l].mean() < 0 for l in grandi)
    print(f'{n} partite di {len(leghe)} leghe ({len(grandi)} con almeno 100 partite)')
    print(f'\n=== il test: corner 1X2 contro la costante ===\n  {1000 * dl.mean():+.1f} per mille (z {zeta(dl):+.2f}), meglio in {meglio} leghe su {len(grandi)}')
    dh = np.zeros(n)
    for h in (-1.5, 1.5):
        p = (D * (V + h > 0)).sum(1); yy = d + h > 0; f = REGOLA['handicap'][str(h)]
        dh += -np.log(np.where(yy, p, 1 - p)) + np.log(np.where(yy, f, 1 - f))
    print(f'  guardia, handicap -1.5 e +1.5 contro le loro frequenze: {1000 * dh.mean():+.1f} per mille (z {zeta(dh):+.2f})')
    passa = zeta(dl) <= -2 and meglio > len(grandi) / 2 and zeta(dh) <= -2
    print(f'  ESITO: {"PASSA" if passa else "NON PASSA"}')
    for l in leghe:
        k = A['lega'] == l; print(f'    {l:34s} {k.sum():5d}  {1000 * dl[k].mean():+7.1f}')
    descrivi(A, D, cst, 'descrittivi')
    return passa

if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '--prova': prova(a[1:])
    elif a and a[0] == '--rese': rese()
    elif a and a[0] == '--schermo':
        ok = schermo(a[1:])
        print('\ncontrollo di potenza, b1 spostato di 0.05:'); pot = schermo(a[1:], dict(REGOLA, b1=REGOLA['b1'] + 0.05))
        sys.exit(0 if ok and not pot else 1)
    else: esplora()
