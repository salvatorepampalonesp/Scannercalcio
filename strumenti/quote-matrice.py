# I mercati della matrice con le quote (AGENTS.md, I mercati della matrice con le quote: la regola).
#
#   python3 strumenti/quote-matrice.py --allena batch48 batch4 --prova batch/nuove batch/2627 [--quote batch/quote]
#
# Con le quote dell'1X2 e dell'Over 2.5 lo Scanner allinea la matrice dei gol al mercato (b57). Qui si
# rifanno, partita per partita, la matrice del motore (lambda di ruolo e rho del CSV) e quella allineata,
# con i coefficienti dello Scanner letti da scanner.html (QUOTE_COMB, QUOTE_OU: non si ristimano), e si
# misurano risultati esatti, multigol, handicap asiatico e il Goal ricalibrato. La ricalibrazione del Goal
# si stima sulle partite di --allena; il test e' sulle partite di --prova. Senza --prova stampa solo la
# stima e i descrittivi di --allena.
import os, sys, re, io, csv, math, glob, collections, importlib.util, urllib.request, warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
warnings.filterwarnings('ignore')
QUI = os.path.dirname(os.path.abspath(__file__))
_s = importlib.util.spec_from_file_location('qg', os.path.join(QUI, 'quote-gol.py'))
qg = importlib.util.module_from_spec(_s); _s.loader.exec_module(qg); qb = qg.qb

COD = dict(qb.COD) | {'E2': 'League One', 'E3': 'League Two', 'T1': 'Super Lig'}
LEGA_COD = {v: k for k, v in COD.items()}

def costanti():
    s = io.open(os.path.join(QUI, '..', 'scanner.html'), encoding='utf-8').read()
    m = re.search(r'const QUOTE_COMB = \{\s*W: (\[\[.*?\]\]),\s*b: (\[.*?\]) \};', s, re.S)
    W, b = np.array(eval(m.group(1))), np.array(eval(m.group(2)))
    m = re.search(r'const QUOTE_OU = \{ b: ([-\d.]+), motore: ([-\d.]+), mercato: ([-\d.]+) \};', s)
    m2 = re.search(r'const GOAL_QUOTE_CAL = \{ a: ([-\d.]+), b: ([-\d.]+) \};', s)
    return W, b, [float(x) for x in m.groups()], ([float(x) for x in m2.groups()] if m2 else None)

def stagione(f):
    a = os.path.basename(f).rsplit('_', 1)[1][:9]
    return a[2:4] + a[7:9]

def carica(dirs, cq):
    M = []
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, '*.csv'))):
            for m in qb.leggi_csv(f): m['fds'] = stagione(f); M.append(m)
    M = list({m['id']: m for m in M}.values())
    righe = []
    for cod, fds in sorted({(LEGA_COD[m['lega']], m['fds']) for m in M if m['lega'] in LEGA_COD}):
        nome = os.path.join(cq, f'{cod}_{fds}.csv')
        if not os.path.exists(nome):
            os.makedirs(cq, exist_ok=True)
            with urllib.request.urlopen(f'https://www.football-data.co.uk/mmz4281/{fds}/{cod}.csv', timeout=60) as r: open(nome, 'wb').write(r.read())
        for r in csv.DictReader(io.open(nome, encoding='utf-8-sig', errors='replace')):
            if not r.get('HomeTeam') or not r.get('FTHG'): continue
            qc, fc = qb.prendi(r, ['AvgC', 'PSC', 'B365C']); qp, _ = qb.prendi(r, ['Avg', 'PS', 'B365'])
            righe.append(dict(lega=COD[cod], data=qb.data(r['Date']), H=r['HomeTeam'], A=r['AwayTeam'], hg=int(r['FTHG']), ag=int(r['FTAG']), qc=qc, fc=fc, qp=qp, riga=r))
    return M, qb.aggancia(M, righe)

def blocco(m):
    return 'il 2026/27' if m['fds'] == '2627' else m['lega']

def calcola(Q, W, b, OU):
    P0 = np.array([q['p'] for q in Q]); P0 /= P0.sum(1, keepdims=True)
    PM = np.array([[1 / x for x in q['qc']] for q in Q]); PM /= PM.sum(1, keepdims=True)
    lr = lambda P: np.column_stack([np.log(P[:, 0] / P[:, 1]), np.log(P[:, 2] / P[:, 1])])
    Z = np.column_stack([lr(P0), lr(PM)]) @ W.T + b; Z -= Z.max(1, keepdims=True); PC = np.exp(Z); PC /= PC.sum(1, keepdims=True)
    OUc = [qg.ou(q['riga'], ['AvgC', 'PC', 'B365C'])[0] for q in Q]
    k = np.array([o is not None for o in OUc])
    Q = [q for q, kk in zip(Q, k) if kk]; P0, PM, PC = P0[k], PM[k], PC[k]
    pm = np.array([(1 / o[0]) / (1 / o[0] + 1 / o[1]) for o in OUc if o is not None])
    lamH = np.array([q['lam'][0] for q in Q]); lamA = np.array([q['lam'][1] for q in Q]); rho = np.array([q['rho'] for q in Q])
    E = qg.matrici(lamH, lamA, rho); E0 = qg.mercati(E)
    pc = 1 / (1 + np.exp(-(OU[0] + OU[1] * qg.logit(E0['o25']) + OU[2] * qg.logit(pm))))
    aH, aA = qg.allinea(pc, np.log(PC[:, 0] / PC[:, 2]), rho); A = qg.matrici(aH, aA, rho)
    hg = np.array([q['hg'] for q in Q]); ag = np.array([q['ag'] for q in Q])
    dev = max(abs(100 * E0[kk] - np.array([q['gol'][c] for q in Q])).max() for kk, c in (('o15', 'Over 1.5'), ('o25', 'Over 2.5'), ('o35', 'Over 3.5'), ('gg', 'GG (da matrice)')))
    return dict(Q=Q, P0=P0, PM=PM, PC=PC, pm=pm, pc=pc, E=E, A=A, E0=E0, A0=qg.mercati(A), hg=hg, ag=ag, dev=dev,
                bl=np.array([blocco(q) for q in Q]), lega=np.array([q['lega'] for q in Q]))

G = np.arange(11)
def perdite(P, hg, ag):
    n = len(hg); ok = (hg <= 10) & (ag <= 10); i = np.arange(n)
    es = np.full(n, np.nan); es[ok] = -np.log(np.clip(P[i[ok], hg[ok], ag[ok]], 1e-12, 1))
    tot = np.zeros((n, 7)); ph = np.zeros((n, 4)); pa = np.zeros((n, 4)); dr = np.zeros((n, 7))
    for x in G:
        for y in G:
            c = P[:, x, y]; tot[:, min(x + y, 6)] += c; ph[:, min(x, 3)] += c; pa[:, min(y, 3)] += c; dr[:, min(max(x - y, -3), 3) + 3] += c
    L = lambda M, j: -np.log(np.clip(M[i, j], 1e-12, 1))
    mg = L(tot, np.minimum(hg + ag, 6)) + L(ph, np.minimum(hg, 3)) + L(pa, np.minimum(ag, 3))
    ah = L(dr, np.clip(hg - ag, -3, 3) + 3)
    return {'esatti': es, 'multigol': mg, 'handicap': ah}

def confronto(nome, a, b, bl, ok=None):
    ok = np.isfinite(a) & np.isfinite(b) if ok is None else ok
    d = (b - a)[ok]; B = bl[ok]; z = d.mean() / d.std(ddof=1) * math.sqrt(len(d))
    per = {x: d[B == x].mean() for x in sorted(set(B))}; meglio = sum(v < 0 for v in per.values())
    print(f'  {nome}: {a[ok].mean():.5f} -> {b[ok].mean():.5f} ({d.mean():+.5f}, z {z:+.2f}, {len(d)} partite) · meglio in {meglio}/{len(per)} blocchi')
    print('    ' + ' · '.join(f'{x} {v:+.5f} ({(B == x).sum()})' for x, v in per.items()))
    return z, meglio, len(per)

def stima_goal(C):
    yg = ((C['hg'] > 0) & (C['ag'] > 0)).astype(float)
    m = LogisticRegression(penalty=None, max_iter=1000).fit(qg.logit(C['A0']['gg'])[:, None], yg)
    return float(m.intercept_[0]), float(m.coef_[0][0])

def goal_cal(p, ab): return 1 / (1 + np.exp(-(ab[0] + ab[1] * qg.logit(p))))

def descrittivi(C, ab):
    y1 = np.array([0 if h > a else (1 if h == a else 2) for h, a in zip(C['hg'], C['ag'])])
    for nome, P in (('motore', C['P0']), ('mercato', C['PM']), ('con le quote', C['PC'])):
        print(f'  1X2, prese del pick {nome}: {100 * (P.argmax(1) == y1).mean():.2f}%  logloss {-np.log(P[np.arange(len(y1)), y1]).mean():.5f}')
    yo = (C['hg'] + C['ag'] > 2).astype(float); yg = ((C['hg'] > 0) & (C['ag'] > 0)).astype(float)
    confronto('Over 2.5, motore -> con le quote', qg.ll(C['E0']['o25'], yo), qg.ll(C['pc'], yo), C['bl'])
    for c, lin in (('o15', 1.5), ('o35', 3.5)):
        yy = (C['hg'] + C['ag'] > lin).astype(float)
        confronto(f'Over {lin}, motore -> matrice allineata', qg.ll(C['E0'][c], yy), qg.ll(C['A0'][c], yy), C['bl'])
    confronto('Goal, motore -> matrice allineata', qg.ll(C['E0']['gg'], yg), qg.ll(C['A0']['gg'], yg), C['bl'])
    g2 = goal_cal(C['A0']['gg'], ab)
    print(f'  Goal medio: motore {100 * C["E0"]["gg"].mean():.1f}, allineata {100 * C["A0"]["gg"].mean():.1f}, ricalibrata {100 * g2.mean():.1f}, reale {100 * yg.mean():.1f}')
    for lo, hi in ((0, .4), (.4, .5), (.5, .6), (.6, 1.01)):
        s = (C['A0']['gg'] >= lo) & (C['A0']['gg'] < hi)
        if s.sum(): print(f'    fascia {int(100 * lo)}-{min(100, int(100 * hi))}: {s.sum():5d} partite, allineata {100 * C["A0"]["gg"][s].mean():.1f}, ricalibrata {100 * g2[s].mean():.1f}, esce {100 * yg[s].mean():.1f}')

def main():
    a = sys.argv[1:]; cq = 'batch/quote'
    if '--quote' in a: i = a.index('--quote'); cq = a[i + 1]; del a[i:i + 2]
    i = a.index('--allena'); j = a.index('--prova') if '--prova' in a else len(a)
    allena, prova = a[i + 1:j], a[j + 1:]
    W, b, OU, cal = costanti()
    print(f'dallo Scanner: QUOTE_COMB W {W.tolist()} b {b.tolist()} · QUOTE_OU {OU} · ricalibrazione del Goal {cal}')
    M, Q = carica(allena, cq); C = calcola(Q, W, b, OU)
    print(f'--allena: {len(C["Q"])} partite con le quote dell\'Over · prova di coincidenza della matrice del motore: scarto massimo {C["dev"]:.3f} punti')
    ab = stima_goal(C)
    print(f'ricalibrazione del Goal stimata su --allena: a {ab[0]:+.5f}, b {ab[1]:.5f}')
    ab = cal or ab
    C['bl'] = C['lega']
    print('\n=== --allena, descrittivo (per lega) ===')
    L0, L1 = perdite(C['E'], C['hg'], C['ag']), perdite(C['A'], C['hg'], C['ag'])
    for k in L0: confronto(f'{k}, motore -> allineata', L0[k], L1[k], C['bl'])
    descrittivi(C, ab)
    if not prova: return
    M, Q = carica(prova, cq); C = calcola(Q, W, b, OU)
    print(f'\n=== IL TEST: --prova, {len(C["Q"])} partite con le quote dell\'Over · coincidenza della matrice del motore {C["dev"]:.3f} punti ===')
    print('blocchi:', dict(collections.Counter(C['bl'])))
    L0, L1 = perdite(C['E'], C['hg'], C['ag']), perdite(C['A'], C['hg'], C['ag']); esiti = {}
    for k in L0: esiti[k] = confronto(f'{k}, motore -> allineata', L0[k], L1[k], C['bl'])
    yg = ((C['hg'] > 0) & (C['ag'] > 0)).astype(float)
    esiti['goal'] = confronto('Goal, allineata -> ricalibrata', qg.ll(C['A0']['gg'], yg), qg.ll(goal_cal(C['A0']['gg'], ab), yg), C['bl'])
    for k, (z, meglio, n) in esiti.items():
        print(f'ESITO {k}: {"PASSA" if z <= -2 and meglio >= 3 else "NON PASSA"} (z {z:+.2f} <= -2; meglio in {meglio}/{n} >= 3)')
    print('\n=== --prova, descrittivo ===')
    descrittivi(C, ab)

if __name__ == '__main__':
    main()
