# Il rating sugli xG (AGENTS.md, Il rating sugli xG: la regola).
#
#   python3 strumenti/rating-xg.py --allena batch48 batch4 batch/2627
#   python3 strumenti/rating-xg.py --prova batch/nuove batch/livello
#
# Dai CSV del Comparatore rifa' per ogni lega, in ordine di data, un rating lineare delle squadre sugli xG
# delle partite (margine di xG previsto = R_casa - R_trasf + H; dopo ogni giornata R_casa += K*e,
# R_trasf -= K*e, H += KH*e, con e = margine vero - previsto). Una squadra che entra in una stagione parte
# dalla media dei rating delle squadre uscite. La prima stagione di ogni lega e' solo rodaggio.
# Poi combina il log-odds 1 contro 2 del motore (lgTarget) col margine previsto:
# lg' = a*lgTarget + b*margine + c. --allena stima a, b, c; --prova applica quelli di COEF e fa il test.
# Esito: non passa. Esplorazione -5.53 per mille (z -3.95); test su dieci leghe -2.00 per mille (z -1.19), 5 su 10.
import csv, io, os, re, sys, glob, math, collections
import numpy as np

K, KH, H0 = 0.05, 0.01, 0.3
COEF = (0.31000, 1.03668, -0.03559)   # --allena batch48 batch4 batch/2627: dodici leghe, 6.315 partite senza pari

def num(s):
    if s is None: return None
    s = str(s).strip().replace('%', '').replace(',', '.')
    if s in ('', 'N/D', '--', '-'): return None
    try: return float(s.split()[0])
    except ValueError: return None

def leggi(f):
    righe = collections.defaultdict(list)
    for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if not r or not r[0]: continue
        if r[0].startswith('=== ARCHIVIO'): break
        righe[r[0]].append(r)
    g = lambda k, i=0: righe[k][i] if k in righe and len(righe[k]) > i else None
    ids, out = g('ID PARTITA'), []
    k = re.match(r'Backtest_V97_(.+)_(\d{4}(?:-\d{4})?)\.csv', os.path.basename(f))
    for c in range(1, len(ids), 4):
        if not ids[c]: continue
        v = lambda k, j=0, i=0: (g(k, i)[c + j] if g(k, i) and len(g(k, i)) > c + j else None)
        try: hg, ag = [int(x) for x in v('SCORE').split('-')]
        except (AttributeError, ValueError): continue
        out.append({'id': ids[c], 'L': k.group(1), 'S': k.group(2), 'ora': v('DATA ISO (UTC)'), 'H': v('SQUADRA CASA'), 'A': v('SQUADRA TRASFERTA'),
                    'hg': hg, 'ag': ag, 'out': 0 if hg > ag else (1 if hg == ag else 2),
                    'conf': (v('COPIA CONFORME DELLO SCANNER') or '').startswith('SI'), 'p': [num(v(x)) for x in ('1', 'X', '2')],
                    'lgT': num(v('Elo: log-odds bersaglio [completo → 1X2]')), 'lgM': num(v('Elo: log-odds modello [completo → 1X2]')),
                    'elod': num(v('ELO Diff (H-A)')), 'hfa': num(v('HFA Lega')), 'xg': [num(v('xG', 2, 0)), num(v('xG', 2, 1))]})
    return out

def carica(dirs):
    M = {}
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, '*.csv'))):
            for m in leggi(f): M[m['id']] = m
    L = collections.defaultdict(list)
    for m in M.values(): L[m['L']].append(m)
    for k in L: L[k].sort(key=lambda m: m['ora'])
    return L

def rating(ms):
    # margine di xG previsto per ogni partita, con i soli dati dei giorni prima; None nella prima stagione
    R, H, out, cur = {}, H0, {}, None
    stag = sorted({m['S'] for m in ms})
    squadre = {s: {t for m in ms if m['S'] == s for t in (m['H'], m['A'])} for s in stag}
    giorni = collections.OrderedDict()
    for m in ms: giorni.setdefault(m['ora'][:10], []).append(m)
    for g in giorni.values():
        s = g[0]['S']
        if s != cur:
            if cur is not None:
                usc = [R[t] for t in squadre[cur] - squadre[s] if t in R]
                liv = float(np.mean(usc)) if usc else 0.0
                for t in squadre[s] - squadre[cur]: R[t] = liv
            cur = s
        for m in g:
            out[m['id']] = None if s == stag[0] else R.get(m['H'], 0.0) - R.get(m['A'], 0.0) + H
        for m in g:
            if None in m['xg']: continue
            rh, ra = R.get(m['H'], 0.0), R.get(m['A'], 0.0)
            e = (m['xg'][0] - m['xg'][1]) - (rh - ra + H)
            R[m['H']], R[m['A']] = rh + K * e, ra - K * e; H += KH * e
    return out

def righe(L):
    X = []
    for lega, ms in sorted(L.items()):
        r = rating(ms)
        for m in ms:
            if m['conf'] and m['lgT'] is not None and r[m['id']] is not None and None not in m['p']:
                m['dr'] = r[m['id']]; X.append(m)
    return X

def fit(F, y, it=60):
    F = np.column_stack([F, np.ones(len(y))]); b = np.zeros(F.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-F @ b)); W = p * (1 - p)
        b += np.linalg.solve((F * W[:, None]).T @ F + 1e-9 * np.eye(len(b)), F.T @ (y - p))
    return b

def sig(x): return 1 / (1 + np.exp(-x))
def zeta(d): return d.mean() / d.std(ddof=1) * math.sqrt(len(d))

def allena(dirs):
    X = [m for m in righe(carica(dirs)) if m['out'] != 1]
    y = np.array([m['out'] == 0 for m in X], float); F = np.array([[m['lgT'], m['dr']] for m in X])
    b = fit(F, y); print(f'--allena: {len(X)} partite senza pari di {len({m["L"] for m in X})} leghe')
    print(f'COEF = ({b[0]:.5f}, {b[1]:.5f}, {b[2]:.5f})   # lg\' = a*lgTarget + b*margine xG + c')
    Ls = np.array([m['L'] for m in X]); p = np.zeros(len(y))
    for l in sorted(set(Ls)):
        te = Ls == l; bb = fit(F[~te], y[~te]); p[te] = sig(F[te] @ bb[:2] + bb[2])
    ll = lambda q: -(y * np.log(q) + (1 - y) * np.log(1 - q)); d = ll(p) - ll(sig(F[:, 0]))
    print(f'fuori lega: logloss 1 contro 2 {1000 * d.mean():+.2f} per mille (z {zeta(d):+.2f}), meglio in {sum(d[Ls == l].mean() < 0 for l in set(Ls))}/{len(set(Ls))}')

def prova(dirs, coef):
    a, b, c = coef
    X = righe(carica(dirs)); Ls = np.array([m['L'] for m in X]); o = np.array([m['out'] for m in X])
    lgT = np.array([m['lgT'] for m in X]); dr = np.array([m['dr'] for m in X]); P = np.array([m['p'] for m in X]) / 100
    q = sig(a * lgT + b * dr + c); nd = o != 1; y = (o == 0).astype(float)
    ll = lambda p: -(y * np.log(p) + (1 - y) * np.log(1 - p))
    d = (ll(q) - ll(sig(lgT)))[nd]; Ln = Ls[nd]; leghe = sorted(set(Ls))
    per = {l: (d[Ln == l].mean(), (Ln == l).sum()) for l in leghe}; meglio = sum(v[0] < 0 for v in per.values())
    N = np.column_stack([(1 - P[:, 1]) * q, P[:, 1], (1 - P[:, 1]) * (1 - q)]); N /= N.sum(1, keepdims=True)
    h0 = (P.argmax(1) == o).astype(float); h1 = (N.argmax(1) == o).astype(float); dh = h1 - h0; se = dh.std(ddof=1) / math.sqrt(len(dh))
    print(f'\n=== IL TEST: {len(X)} partite ({nd.sum()} senza pari) di {len(leghe)} leghe, COEF {coef} ===')
    for l in leghe:
        s = Ls == l
        print(f'  {l:22s} {per[l][1]:5d} senza pari  logloss 1 contro 2 {1000 * per[l][0]:+7.2f} per mille   prese {100 * h0[s].mean():5.1f} -> {100 * h1[s].mean():5.1f} ({s.sum()} partite)')
    soglia = math.ceil(2 * len(leghe) / 3)
    print(f'insieme: {1000 * d.mean():+.2f} per mille (z {zeta(d):+.2f}), meglio in {meglio}/{len(leghe)} (servono {soglia}); '
          f'prese {100 * h0.mean():.2f} -> {100 * h1.mean():.2f} ({100 * dh.mean():+.2f}, 2se {200 * se:.2f}), pick cambiato {int((P.argmax(1) != N.argmax(1)).sum())}')
    passa = zeta(d) <= -2 and meglio >= soglia and dh.mean() >= -2 * se
    print('ESITO:', 'PASSA' if passa else 'NON PASSA')
    print('\n=== descrittivi ===')
    lp = lambda A: -np.log(A[np.arange(len(o)), o]); d3 = lp(N) - lp(P)
    print(f'logloss 1X2 {1000 * d3.mean():+.2f} per mille (z {zeta(d3):+.2f})')
    for fr in (0.1, 0.2, 0.3, 0.5):
        r0, r1 = [], []
        for l in leghe:
            s = np.where(Ls == l)[0]; n = int(round(fr * len(s)))
            r0 += list(h0[s[np.argsort(-P[s].max(1))][:n]]); r1 += list(h1[s[np.argsort(-N[s].max(1))][:n]])
        print(f'  il {int(100 * fr)}% piu\' sicuro del calendario: motore {100 * np.mean(r0):.1f}%, col rating {100 * np.mean(r1):.1f}%')
    fav0 = np.where(P[:, 0] >= P[:, 2], 0, 2); fav1 = np.where(N[:, 0] >= N[:, 2], 0, 2)
    for nome, fav, Q in (('motore', fav0, P), ('col rating', fav1, N)):
        sf = np.where(fav == 0, 2, 0); ps = Q[np.arange(len(o)), sf]
        for t in (0.25, 0.30, 0.35):
            s = ps >= t
            if not s.any(): continue
            print(f'  sorpresa ({nome}): sfavorito al {int(100 * t)}% o piu\' in {100 * s.mean():.1f}% delle partite, vince il {100 * (o[s] == sf[s]).mean():.1f}% (previsto {100 * ps[s].mean():.1f})')

if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '--allena': allena(a[1:])
    elif a and a[0] == '--prova':
        if COEF is None: sys.exit('COEF non scritti: prima --allena')
        prova(a[1:], COEF)
    else: sys.exit(__doc__ or 'uso: --allena <cartelle> | --prova <cartelle>')
