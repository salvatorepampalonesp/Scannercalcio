# L'handicap asiatico del mercato contro le nostre matrici (AGENTS.md, Da fare: l'handicap della matrice allineata).
#
#   python3 strumenti/quote-handicap.py batch48 batch4
#
# Quote di chiusura dell'handicap asiatico di football-data (AHCh, AvgCAHH/AvgCAHA), margine tolto in proporzione,
# contro la matrice del motore (lambda di ruolo e rho del CSV) e quella allineata a 1X2 + Over 2.5 come nello
# Scanner. Per ogni linea la probabilita' e' somma(vinte)/(somma(vinte)+somma(perse)) sulle due mezze puntate, e
# il reale pesa le mezze puntate decise (1 o 2): cosi' la quota equa del mercato e la previsione misurano la
# stessa cosa anche sulle linee intere e a quarti. Solo descrittivo.
import os, sys, math, collections, importlib.util
import numpy as np
from sklearn.linear_model import LogisticRegression
import warnings; warnings.filterwarnings('ignore')
QUI = os.path.dirname(os.path.abspath(__file__)); os.chdir(os.path.join(QUI, '..'))
def mod(n, f):
    s = importlib.util.spec_from_file_location(n, f); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
qm = mod('qm', os.path.join(QUI, 'quote-matrice.py')); qg = qm.qg; qb = qm.qb

def num(x):
    try: return float(str(x).replace(',', '.'))
    except Exception: return None

def ah_quote(r):
    h = num(r.get('AHCh'))
    for k in ('AvgC', 'PC', 'B365C'):
        a, b = num(r.get(k + 'AHH')), num(r.get(k + 'AHA'))
        if h is not None and a and b and a > 1 and b > 1: return h, a, b, k
    return None

def sotto(h):
    # una linea asiatica in mezze puntate: -0.25 -> (0, -0.5); -0.5 -> (-0.5, -0.5)
    f = round(h * 4) / 4
    if abs(f * 2 - round(f * 2)) < 1e-9: return (f, f)
    return (f - 0.25, f + 0.25)

def esito(d, h):
    # d = gol casa - gol trasferta; per la casa con handicap h: +1 vince, 0 nulla, -1 perde
    x = d + h
    return 1 if x > 1e-9 else (0 if abs(x) < 1e-9 else -1)

def p_imp(GD, h):
    # GD: (n, 21) probabilita' della differenza reti -10..+10. p = sum W / (sum W + sum L) sulle due mezze puntate
    W = np.zeros(len(GD)); L = np.zeros(len(GD))
    for hh in sotto(h):
        for i, d in enumerate(range(-10, 11)):
            e = esito(d, hh)
            if e > 0: W += GD[:, i]
            elif e < 0: L += GD[:, i]
    return W / (W + L)

def gd_dist(P):
    n = P.shape[0]; GD = np.zeros((n, 21))
    for x in range(11):
        for y in range(11): GD[:, x - y + 10] += P[:, x, y]
    return GD

def main():
    dirs = sys.argv[1:] or ['batch48', 'batch4']
    W, b, OU = qm.costanti()
    M, Q = qm.carica(dirs, 'batch/quote'); C = qm.calcola(Q, W, b, OU)
    rows = []
    for i, q in enumerate(C['Q']):
        a = ah_quote(q['riga'])
        if not a: continue
        h, oh, oa, k = a
        if abs(round(h * 4) - h * 4) > 1e-6: continue
        d = q['hg'] - q['ag']; s = [esito(d, hh) for hh in sotto(h)]
        w = sum(x > 0 for x in s); l = sum(x < 0 for x in s)
        if w + l == 0: continue
        rows.append(dict(i=i, h=h, pm=(1 / oh) / (1 / oh + 1 / oa), y=w / (w + l), wt=w + l, lega=q['lega'], fonte=k,
                         tipo='mezza' if abs(h * 2 - round(h * 2)) < 1e-9 and abs(h - round(h)) > 1e-9 else ('intera' if abs(h - round(h)) < 1e-9 else 'quarto')))
    idx = np.array([r['i'] for r in rows]); h = np.array([r['h'] for r in rows])
    GDe, GDa = gd_dist(C['E'][idx]), gd_dist(C['A'][idx])
    pe = np.array([p_imp(GDe[j:j + 1], h[j])[0] for j in range(len(rows))])
    pa = np.array([p_imp(GDa[j:j + 1], h[j])[0] for j in range(len(rows))])
    pm = np.array([r['pm'] for r in rows]); y = np.array([r['y'] for r in rows]); lg = np.array([r['lega'] for r in rows])
    tipo = np.array([r['tipo'] for r in rows]); wt = np.array([r['wt'] for r in rows], float)
    print(f'partite con le quote dell 1X2, dell Over e dell handicap: {len(rows)} · fonti {collections.Counter(r["fonte"] for r in rows)}')
    print('tipi di linea', collections.Counter(tipo), '· linee piu frequenti', collections.Counter(h).most_common(8))
    print(f'media prevista (casa copre): motore {pe.mean():.4f}, allineata {pa.mean():.4f}, mercato {pm.mean():.4f}; realizzato {np.average(y, weights=wt):.4f}')
    L = lambda p: wt * qg.ll(p, y) / wt.mean()
    def conf(nome, a, bb):
        d = bb - a; z = d.mean() / d.std(ddof=1) * math.sqrt(len(d))
        per = {x: d[lg == x].mean() for x in sorted(set(lg))}
        print(f'  {nome:55s} {1000 * d.mean():+7.2f}‰  z {z:+6.2f}  meglio in {sum(v < 0 for v in per.values())}/{len(per)} leghe')
        return d
    print('\n--- logloss della copertura dell handicap (linea del mercato) ---')
    conf('motore -> allineata (1X2 + Over)', L(pe), L(pa))
    conf('allineata -> mercato dell handicap (in proporzione)', L(pa), L(pm))
    # fuori lega: mercato ricalibrato, e combinazione con l'allineata
    def fl(cols):
        X = np.column_stack(cols); out = np.zeros(len(y))
        for x in set(lg):
            tr, te = lg != x, lg == x
            m = LogisticRegression(penalty=None, max_iter=1000).fit(np.vstack([X[tr], X[tr]]), np.r_[np.ones(tr.sum()), np.zeros(tr.sum())], sample_weight=np.r_[wt[tr] * y[tr], wt[tr] * (1 - y[tr])])
            out[te] = m.predict_proba(X[te])[:, 1]
        return out
    pmr = fl([qg.logit(pm)]); par = fl([qg.logit(pa)]); pcomb = fl([qg.logit(pm), qg.logit(pa)])
    conf('allineata ricalibrata -> mercato ricalibrato', L(par), L(pmr))
    conf('mercato ricalibrato -> mercato + allineata', L(pmr), L(pcomb))
    for t in ('mezza', 'intera', 'quarto'):
        k = tipo == t
        if k.sum() < 200: continue
        d = (L(pm) - L(pa))[k]; z = d.mean() / d.std(ddof=1) * math.sqrt(k.sum())
        print(f'  per tipo di linea, {t:7s} {k.sum():5d} partite: allineata -> mercato {1000 * d.mean():+.2f}‰ (z {z:+.2f}); previsto allineata {pa[k].mean():.3f}, mercato {pm[k].mean():.3f}, realizzato {np.average(y[k], weights=wt[k]):.3f}')
    # dove sbaglia l'allineata: per linea
    print('\n--- per linea (casa): partite, allineata, mercato, realizzato ---')
    for v, n in sorted(collections.Counter(h).items()):
        if n < 150: continue
        k = h == v
        print(f'  {v:+5.2f}  {n:5d}  motore {np.average(pe[k], weights=wt[k]):.3f}  {np.average(pa[k], weights=wt[k]):.3f}  {np.average(pm[k], weights=wt[k]):.3f}  {np.average(y[k], weights=wt[k]):.3f}')
    X = np.column_stack([np.ones(len(y)), qg.logit(pm), qg.logit(pa)])
    m = LogisticRegression(penalty=None, max_iter=1000).fit(np.vstack([X[:, 1:], X[:, 1:]]), np.r_[np.ones(len(y)), np.zeros(len(y))], sample_weight=np.r_[wt * y, wt * (1 - y)])
    print(f'\npesi su tutte le partite: mercato {m.coef_[0][0]:+.3f}, allineata {m.coef_[0][1]:+.3f}, intercetta {m.intercept_[0]:+.3f}')

main()
