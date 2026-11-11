# La matrice dei gol con le quote contro l'1X2 con le quote (AGENTS.md, La matrice con le quote e il pareggio).
#
#   python3 strumenti/rating-quote.py --scarica      # una volta: i file di football-data in batch/fd
#   python3 strumenti/quote-coerenza.py              # l'esplorazione: 11 leghe, 2023/24-2025/26 (tre minuti)
#   python3 strumenti/quote-coerenza.py --terzo      # anche il kappa e il rho della partita (altri cinque minuti)
#   python3 strumenti/quote-coerenza.py --prova      # il test registrato, una volta sola
#   python3 strumenti/quote-coerenza.py --rese       # le rese dei gol nel tabellone con le quote, con la matrice nuova
#
# Nessuna chiamata alla PitchAPI e nessun CSV del Comparatore: solo i file di football-data.
#
# Con le quote dell'1X2 e dell'Over 2.5 lo Scanner mostra l'1X2 di QUOTE_COMB e, per Goal, Over 1.5 e 3.5, risultati
# esatti, multigol e handicap, la matrice allineata (b57, b62): un Dixon-Coles col rho del motore e i due lambda scelti
# perche' dia l'Over 2.5 con le quote e il log(p1/p2) dell'1X2 con le quote. Il PAREGGIO con le quote non e' un vincolo:
# la matrice ha il suo, e quindi anche il suo 1 e il suo 2 (l'handicap -0.5 non e' l'1 a schermo).
# Qui si misura di quanto, e si confrontano con la matrice di oggi i modi SENZA PARAMETRI di farle rispettare anche il
# pareggio con le quote:
#   R, raking: le tre regioni (1, X, 2) e le due fasce (Over, Under 2.5) riscalate a turno fino ai quattro numeri;
#   K, kappa della partita: P * exp(-k*(x-y)^2) riallineata, col k che da' il pareggio con le quote;
#   H, rho della partita: il rho che da' il pareggio con le quote, coi lambda riallineati;
# e un kappa uguale per tutte (la regola del 7 ottobre 2026, non passata), da solo o seguito dal raking.
# Il candidato registrato e' KR: la matrice riallineata con kappa 0.02, poi il raking.
#
# Quello che lo Scanner ha e qui manca e' l'1X2 del motore dentro QUOTE_COMB e QUOTE_OU. Al suo posto sta il mercato
# stesso (i pesi del motore sommati a quelli del mercato): dato il mercato il motore pesa poco (b54, b57).
# Il rho e' quello del motore rifatto dai punteggi di football-data: estimateRho sulle stagioni s-2, s-1 e s prima del
# giorno, con le medie gol piatte di computeLeagueParams.
import os, sys, io, csv, math, collections, importlib.util
import numpy as np
QUI = os.path.dirname(os.path.abspath(__file__))
def _mod(n, f):
    s = importlib.util.spec_from_file_location(n, os.path.join(QUI, f)); m = importlib.util.module_from_spec(s)
    a = sys.argv; sys.argv = ['x']; s.loader.exec_module(m); sys.argv = a; return m
qh = _mod('qh', 'quote-handicap.py'); qm, qg, qb = qh.qm, qh.qg, qh.qb
rq = _mod('rq', 'rating-quote.py')
I, J = qg.I, qg.J; D2 = (I - J) ** 2

UNDICI = ['E0', 'I1', 'SP1', 'D1', 'F1', 'E1', 'N1', 'P1', 'B1', 'D2', 'SC0']
ESPLORA = [(UNDICI, ['2324', '2425', '2526'])]
KAPPA = 0.02            # il candidato: scelto fuori lega sul risultato esatto, 11 fold su 11 (scritto prima del test)
KAPPA_OTT = 0.03        # quello della regola del 7 ottobre 2026 (scelto sulla differenza reti), per riferimento
GRIGLIA = [0.01, 0.02, 0.03, 0.045, 0.06]
DICIOTTO = UNDICI + ['E2', 'E3', 'T1', 'G1', 'I2', 'SP2', 'F2']
# i dati del test: mai aperti per questa domanda (AGENTS.md, La matrice con le quote e il pareggio: la regola)
PROVA = [(DICIOTTO, ['1920', '2021', '2122', '2223']), (['G1', 'I2', 'SP2', 'F2'], ['2324', '2425', '2526'])]
# gia' aperti per il kappa (il test del 7 ottobre): solo descrittivi
GIA_VISTI = [(['E2', 'E3', 'T1'], ['2324', '2425', '2526']), (DICIOTTO, ['2627'])]

def leggi(divs):
    M = []
    for div in divs:
        for si, s in enumerate(rq.STAG):
            f = os.path.join(rq.FD, f'{div}_{s}.csv')
            if not os.path.exists(f): continue
            for r in csv.DictReader(io.open(f, encoding='utf-8-sig', errors='replace')):
                d = rq.data(r.get('Date') or '')
                try: hg, ag = int(r['FTHG']), int(r['FTAG'])
                except (KeyError, ValueError, TypeError): continue
                if not d: continue
                ou = next(([rq.num(r.get(p + '>2.5')), rq.num(r.get(p + '<2.5'))] for p in ('AvgC', 'PC', 'B365C')
                           if rq.num(r.get(p + '>2.5')) and rq.num(r.get(p + '<2.5'))), None)
                M.append(dict(div=div, stag=si, d=d.toordinal(), hg=hg, ag=ag, q=rq.tre(r, ['AvgC', 'PSC', 'B365C']), ou=ou, ah=qh.ah_quote(r)))
    return M

def rho_motore(M, B):
    # per ogni partita di B il rho e le medie gol che il motore avrebbe stimato: archivio = la lega nelle stagioni
    # s-2, s-1, s, partite prima del giorno (come _isPast: il giorno della partita escluso)
    RG = []; x = -0.25
    while x <= 0.1001: RG.append(x); x += 0.005
    RG = np.array(RG); per = collections.defaultdict(list)
    for m in M: per[m['div']].append(m)
    memo = {}
    for div, L in per.items():
        d = np.array([m['d'] for m in L]); st = np.array([m['stag'] for m in L]); hg = np.array([m['hg'] for m in L]); ag = np.array([m['ag'] for m in L])
        for s, day in sorted({(m['stag'], m['d']) for m in B if m['div'] == div}):
            k = (st >= s - 2) & (st <= s) & (d < day); n = int(k.sum())
            aH, aA = (hg[k].mean(), ag[k].mean()) if n >= 30 else (1.50, 1.20)
            if n < 100: memo[div, s, day] = (-0.11, aH, aA, n); continue
            obs = np.array([((hg[k] == a) & (ag[k] == b)).mean() for a, b in ((0, 0), (1, 0), (0, 1), (1, 1))])
            P = qg.matrici(np.full(len(RG), aH), np.full(len(RG), aA), RG)
            err = ((np.stack([P[:, 0, 0], P[:, 1, 0], P[:, 0, 1], P[:, 1, 1]], 1) - obs) ** 2).sum(1)
            memo[div, s, day] = (float(RG[int(err.argmin())]), aH, aA, n)
    return np.array([memo[m['div'], m['stag'], m['d']][0] for m in B]), memo

def mat(lh, la, rho, kap=None):
    P = qg.matrici(lh, la, rho)
    if kap is None: return P
    P = P * np.exp(-np.asarray(kap, float)[:, None, None] * D2); return P / P.sum((1, 2), keepdims=True)

def dividi(T, lg12, rho, kap, it):
    lo, hi = np.full(len(T), 0.01), np.full(len(T), 0.99)
    for _ in range(it):
        s = (lo + hi) / 2; P = mat(T * s, T * (1 - s), rho, kap)
        su = np.log((P * (I > J)).sum((1, 2)) / (P * (I < J)).sum((1, 2))) < lg12; lo = np.where(su, s, lo); hi = np.where(su, hi, s)
    return (lo + hi) / 2

def allinea(pov, lg12, rho, kap=None, it=(28, 24)):
    # come matriceAllineata dello Scanner (bisezione annidata), col rho e il kappa della partita
    lo, hi = np.full(len(pov), 0.2), np.full(len(pov), 9.0)
    for _ in range(it[0]):
        T = (lo + hi) / 2; s = dividi(T, lg12, rho, kap, it[1]); P = mat(T * s, T * (1 - s), rho, kap)
        su = (P * (I + J > 2.5)).sum((1, 2)) < pov; lo = np.where(su, T, lo); hi = np.where(su, hi, T)
    T = (lo + hi) / 2; s = dividi(T, lg12, rho, kap, it[1] + 8); return mat(T * s, T * (1 - s), rho, kap)

def pari(P): return (P * (I == J)).sum((1, 2))

def terzo(pov, lg12, pX, rho, quale, giri=15):
    # il terzo parametro della partita (kappa o rho) che da' alla matrice riallineata il pareggio pX
    n = len(pov)
    lo, hi = (np.full(n, -0.10), np.full(n, 0.60)) if quale == 'kappa' else (np.full(n, -0.95), np.full(n, 0.40))
    for _ in range(giri):
        t = (lo + hi) / 2; A = allinea(pov, lg12, rho if quale == 'kappa' else t, t if quale == 'kappa' else None, it=(22, 20))
        su = (pari(A) < pX) if quale == 'kappa' else (pari(A) > pX)        # il pareggio sale con kappa, scende con rho
        lo = np.where(su, t, lo); hi = np.where(su, hi, t)
    t = (lo + hi) / 2; return allinea(pov, lg12, rho if quale == 'kappa' else t, t if quale == 'kappa' else None), t

def raking(P, p, ov, giri=60):
    R = [(I > J), (I == J), (I < J)]; O = I + J > 2.5; Q = P.copy()
    for _ in range(giri):
        for k, r in enumerate(R):
            s = (Q * r).sum((1, 2)); Q = np.where(r, Q * (p[:, k] / s)[:, None, None], Q)
        s = (Q * O).sum((1, 2)); Q = np.where(O, Q * (ov / s)[:, None, None], Q * ((1 - ov) / (1 - s))[:, None, None])
    return Q

def bersagli(B):
    # l'1X2 e l'Over 2.5 con le quote come li fa lo Scanner, col mercato al posto del motore
    W, b, OU = qm.costanti()
    Q = np.array([m['q'] for m in B], float); S = (1 / Q) / (1 / Q).sum(1, keepdims=True)
    f1, f2 = np.log(S[:, 0] / S[:, 1]), np.log(S[:, 2] / S[:, 1]); Wm = W[:, :2] + W[:, 2:]
    z = b + f1[:, None] * Wm[:, 0] + f2[:, None] * Wm[:, 1]; z -= z.max(1, keepdims=True); P = np.exp(z); P /= P.sum(1, keepdims=True)
    O = np.array([m['ou'] for m in B], float); pm = (1 / O[:, 0]) / (1 / O).sum(1)
    pov = 1 / (1 + np.exp(-(OU[0] + (OU[1] + OU[2]) * qg.logit(pm))))
    return S, P, pm, pov

def perdite(A, B, hg, ag):
    L = qm.perdite(A, hg, ag); m = qg.mercati(A); i = np.arange(len(hg))
    L['goal'] = qg.ll(m['gg'], ((hg > 0) & (ag > 0)).astype(float)); L['o15'] = qg.ll(m['o15'], (hg + ag > 1.5).astype(float)); L['o35'] = qg.ll(m['o35'], (hg + ag > 3.5).astype(float))
    p3 = np.stack([m['p1'], 1 - m['p1'] - m['p2'], m['p2']], 1); y = np.where(hg > ag, 0, np.where(hg == ag, 1, 2)); L['1x2'] = -np.log(np.clip(p3[i, y], 1e-12, 1))
    # l'handicap alla linea del mercato, come quote-handicap.py: mezze puntate decise, il nulla escluso
    hd = np.full(len(hg), np.nan); GD = qh.gd_dist(A); wt = np.zeros(len(hg))
    for j, mm in enumerate(B):
        a = mm['ah']
        if not a or abs(round(a[0] * 4) - a[0] * 4) > 1e-6: continue
        e = [qh.esito(int(hg[j] - ag[j]), hh) for hh in qh.sotto(a[0])]; w = sum(x > 0 for x in e); l = sum(x < 0 for x in e)
        if w + l == 0: continue
        p = qh.p_imp(GD[j:j + 1], a[0])[0]; hd[j] = (w + l) * qg.ll(np.array([p]), np.array([w / (w + l)]))[0]; wt[j] = w + l
    L['linea'] = hd / wt[wt > 0].mean() if (wt > 0).any() else hd
    return L

def zeta(d): return d.mean() / d.std(ddof=1) * math.sqrt(len(d)) if len(d) > 1 and d.std() > 0 else 0.0

METRI = [('esatti', 'risultato esatto'), ('multigol', 'multigol'), ('handicap', 'differenza reti'), ('linea', "handicap alla linea del mercato"),
         ('goal', 'Goal'), ('o15', 'Over 1.5'), ('o35', 'Over 3.5'), ('1x2', '1X2 della matrice')]

def confronto(nome, a, b, g):
    k = np.isfinite(a) & np.isfinite(b); d = (b - a)[k]; gg = g[k]; per = {x: d[gg == x].mean() for x in sorted(set(gg.tolist()))}
    zl = qb.zeta_leghe(d, gg)
    print(f'   {nome:32s} {1000 * d.mean():+7.2f} per mille  z {zeta(d):+6.2f}  fra leghe {zl:+6.2f}  meglio in {sum(v < 0 for v in per.values()):2d} su {len(per)}  ({len(d)} partite)')
    return d.mean(), zeta(d), zl, sum(v < 0 for v in per.values()), len(per)

def descrivi(nome, A, hg, ag):
    m = qg.mercati(A); px = pari(A); c = lambda f: 100 * (A * f).sum((1, 2)).mean()
    return (f'   {nome:22s} pari {100 * px.mean():5.2f}  0-0 {c((I == 0) & (J == 0)):5.2f}  1-1 {c((I == 1) & (J == 1)):5.2f}  2-2 {c((I == 2) & (J == 2)):5.2f}  '
            f'scarto 1 {c(np.abs(I - J) == 1):5.2f}  scarto 2 {c(np.abs(I - J) == 2):5.2f}  3+ {c(np.abs(I - J) >= 3):5.2f}  Goal {100 * m["gg"].mean():5.2f}  '
            f'Over 1.5 {100 * m["o15"].mean():5.2f}  3.5 {100 * m["o35"].mean():5.2f}')

def carica(blocchi):
    divs = sorted({d for D, _ in blocchi for d in D}); M = leggi(divs)
    dentro = {(d, rq.STAG.index(s)) for D, S_ in blocchi for d in D for s in S_}
    B = [m for m in M if (m['div'], m['stag']) in dentro and m['q'] and m['ou']]
    senza = sum(1 for m in M if (m['div'], m['stag']) in dentro) - len(B)
    X = dict(M=M, B=B, senza=senza, hg=np.array([m['hg'] for m in B]), ag=np.array([m['ag'] for m in B]), g=np.array([m['div'] for m in B]),
             st=np.array([rq.STAG[m['stag']] for m in B]))
    X['rho'], X['memo'] = rho_motore(M, B); X['S'], X['P'], X['pm'], X['pov'] = bersagli(B); X['lg12'] = np.log(X['P'][:, 0] / X['P'][:, 2])
    return X

def kr(X, k=KAPPA):
    return raking(allinea(X['pov'], X['lg12'], X['rho'], np.full(len(X['B']), k)), X['P'], X['pov'])

def previsto(X, C):
    hg, ag = X['hg'], X['ag']; c = lambda f: 100 * f.mean()
    print(f'   {"uscito":24s} pari {c(hg == ag):5.2f}  0-0 {c((hg == 0) & (ag == 0)):5.2f}  1-1 {c((hg == 1) & (ag == 1)):5.2f}  2-2 {c((hg == 2) & (ag == 2)):5.2f}  '
          f'scarto 1 {c(np.abs(hg - ag) == 1):5.2f}  scarto 2 {c(np.abs(hg - ag) == 2):5.2f}  3+ {c(np.abs(hg - ag) >= 3):5.2f}  Goal {c((hg > 0) & (ag > 0)):5.2f}  '
          f'Over 1.5 {c(hg + ag > 1.5):5.2f}  3.5 {c(hg + ag > 3.5):5.2f}')
    for n, A in C: print(descrivi(n, A, hg, ag))

def linee(X, C):
    B, hg, ag = X['B'], X['hg'], X['ag']
    riga = [(m['ah'][0], j) for j, m in enumerate(B) if m['ah'] and abs(round(m['ah'][0] * 4) - m['ah'][0] * 4) < 1e-6]
    GD = {n: qh.gd_dist(A) for n, A in C}
    print('   linea   partite   mercato  ' + '  '.join(f'{n[:16]:>16s}' for n in GD) + '   uscito')
    for v, cnt in sorted(collections.Counter(h for h, _ in riga).items()):
        if cnt < 250: continue
        jj = []; w = []; yy = []; pmk = []
        for h, j in riga:
            if h != v: continue
            e = [qh.esito(int(hg[j] - ag[j]), hh) for hh in qh.sotto(v)]; a_ = sum(x > 0 for x in e); l_ = sum(x < 0 for x in e)
            if a_ + l_ == 0: continue
            jj.append(j); w.append(a_ + l_); yy.append(a_ / (a_ + l_)); pmk.append((1 / B[j]['ah'][1]) / (1 / B[j]['ah'][1] + 1 / B[j]['ah'][2]))
        w = np.array(w, float)
        print(f'   {v:+5.2f}   {len(jj):6d}   {100 * np.average(pmk, weights=w):6.2f}  ' + '  '.join(f'{100 * np.average(qh.p_imp(GD[n][jj], v), weights=w):16.2f}' for n in GD) + f'   {100 * np.average(yy, weights=w):6.2f}')

def distanza(X, A0):
    B, hg, ag, g, S, P, pov = X['B'], X['hg'], X['ag'], X['g'], X['S'], X['P'], X['pov']
    m0 = qg.mercati(A0); x0 = pari(A0); y = np.where(hg > ag, 0, np.where(hg == ag, 1, 2)); i = np.arange(len(B))
    print(f'   pareggio: mercato {100 * S[:, 1].mean():.2f}, con le quote {100 * P[:, 1].mean():.2f}, matrice allineata {100 * x0.mean():.2f}, uscito {100 * (y == 1).mean():.2f}')
    print(f'   1: con le quote {100 * P[:, 0].mean():.2f}, matrice {100 * m0["p1"].mean():.2f}, uscito {100 * (y == 0).mean():.2f};  2: {100 * P[:, 2].mean():.2f}, {100 * m0["p2"].mean():.2f}, {100 * (y == 2).mean():.2f}')
    dx = P[:, 1] - x0; d1 = np.abs(P[:, 0] - m0['p1'])
    print(f'   il pareggio con le quote meno quello della matrice: media {100 * dx.mean():+.2f} punti, positivo nel {100 * (dx > 0).mean():.0f}% delle partite, un decimo oltre {100 * np.quantile(dx, 0.9):.1f};'
          f' sull\'1 in media {100 * d1.mean():.2f} punti')
    for nome, k in (('favorita sotto il 45%', P.max(1) < 0.45), ('45-60%', (P.max(1) >= 0.45) & (P.max(1) < 0.60)), ('60% o piu\'', P.max(1) >= 0.60)):
        print(f'     {nome:22s} {int(k.sum()):6d} partite: pareggio con le quote {100 * P[k, 1].mean():5.2f}, matrice {100 * x0[k].mean():5.2f}, uscito {100 * (y[k] == 1).mean():5.2f} ±{200 * (y[k] == 1).std() / math.sqrt(k.sum()):.2f}')
    l3 = lambda p: -np.log(np.clip(p[i, y], 1e-12, 1)); pm3 = np.stack([m0['p1'], x0, m0['p2']], 1)
    confronto('1X2 con le quote contro matrice', l3(pm3), l3(P), g)

def intesta(X, titolo, blocchi):
    g = X['g']; v = list(X['memo'].values())
    print(f'{titolo}: {len(X["B"])} partite con le quote di chiusura di 1X2 e Over 2.5, {len(set(g.tolist()))} leghe ({X["senza"]} senza quote, fuori)')
    for D, S_ in blocchi: print(f'   {", ".join(D)}: {", ".join(S_)}')
    print(f'rho del motore rifatto dai punteggi: media {X["rho"].mean():+.3f}, da {X["rho"].min():+.3f} a {X["rho"].max():+.3f}, deviazione {X["rho"].std():.3f}'
          f' (archivio da {min(x[3] for x in v)} a {max(x[3] for x in v)} partite)')

def esplora(blocchi):
    X = carica(blocchi); intesta(X, 'ESPLORAZIONE', blocchi)
    B, hg, ag, g, P, pov, lg12, rho = X['B'], X['hg'], X['ag'], X['g'], X['P'], X['pov'], X['lg12'], X['rho']
    A0 = allinea(pov, lg12, rho); m0 = qg.mercati(A0)
    print(f'prova: la matrice allineata da\' l\'Over 2.5 entro {100 * np.abs(m0["o25"] - pov).max():.4f} punti e il log(p1/p2) entro {np.abs(np.log(m0["p1"] / m0["p2"]) - lg12).max():.5f}')
    print('\n1. QUANTO DISTANO, OGGI, LA MATRICE E L\'1X2 CON LE QUOTE'); distanza(X, A0)
    print('\n2. I CANDIDATI, contro la matrice allineata di oggi (meno e\' meglio)')
    AR = raking(A0, P, pov); mR = qg.mercati(AR)
    print(f'   raking: 1, X, 2 e Over 2.5 raggiunti entro {100 * max(np.abs(mR["p1"] - P[:, 0]).max(), np.abs(pari(AR) - P[:, 1]).max(), np.abs(mR["o25"] - pov).max()):.5f} punti')
    L0 = perdite(A0, B, hg, ag)
    AK = {k: allinea(pov, lg12, rho, np.full(len(B), k)) for k in GRIGLIA}
    AKR = {k: raking(AK[k], P, pov) for k in GRIGLIA}
    LK = {k: perdite(AK[k], B, hg, ag) for k in GRIGLIA}; LKR = {k: perdite(AKR[k], B, hg, ag) for k in GRIGLIA}
    LR = perdite(AR, B, hg, ag)
    print('   in campione, per kappa (per mille contro oggi): risultato esatto / multigol / differenza reti / linea / Goal')
    riga = lambda L: ' / '.join(f'{1000 * np.nanmean(L[m] - L0[m]):+6.2f}' for m in ('esatti', 'multigol', 'handicap', 'linea', 'goal'))
    print(f'     {"solo raking":28s} {riga(LR)}')
    for k in GRIGLIA: print(f'     kappa {k:<5} da solo          {riga(LK[k])}')
    for k in GRIGLIA: print(f'     kappa {k:<5} e poi il raking  {riga(LKR[k])}')
    leghe = sorted(set(g.tolist())); okE = np.isfinite(L0['esatti'])
    def fuori(LL):
        sc = {l: min(GRIGLIA, key=lambda k: LL[k]['esatti'][(g != l) & okE].mean()) for l in leghe}
        return sc, {m: np.array([LL[sc[x]][m][j] for j, x in enumerate(g)]) for m in L0}
    scK, FK = fuori(LK); scKR, FKR = fuori(LKR)
    print(f'   kappa scelto fuori lega sul risultato esatto: da solo {dict(collections.Counter(scK.values()))}, col raking {dict(collections.Counter(scKR.values()))}')
    for n, L in (('R, raking', LR), ('kappa da solo, scelto fuori lega', FK), ('KR, kappa e poi raking, scelto fuori lega', FKR)):
        print(f'  {n}')
        for k, t in METRI: confronto(t, L0[k], L[k], g)
    print('  fra i candidati')
    for k, t in METRI[:5]: confronto(f'KR contro kappa da solo: {t}', FK[k], FKR[k], g)
    for k, t in METRI[:5]: confronto(f'KR contro R: {t}', LR[k], FKR[k], g)
    C = [('matrice di oggi', A0), ('R, raking', AR), (f'kappa {KAPPA} da solo', AK[KAPPA]), (f'KR, kappa {KAPPA} e raking', AKR[KAPPA]),
         (f'kappa {KAPPA_OTT} da solo', AK[KAPPA_OTT]), (f'KR, kappa {KAPPA_OTT} e raking', AKR[KAPPA_OTT])]
    LC = {'R, raking': LR, f'kappa {KAPPA} da solo': LK[KAPPA], f'KR, kappa {KAPPA} e raking': LKR[KAPPA], f'KR, kappa {KAPPA_OTT} e raking': LKR[KAPPA_OTT]}
    if '--terzo' in sys.argv:
        AKp, tk = terzo(pov, lg12, P[:, 1], rho, 'kappa'); AH, th = terzo(pov, lg12, P[:, 1], rho, 'rho')
        print(f'   kappa della partita: media {tk.mean():.3f}, da {np.quantile(tk, .05):.3f} a {np.quantile(tk, .95):.3f} (5-95%)')
        print(f'   rho della partita: media {th.mean():+.3f}, da {np.quantile(th, .05):+.3f} a {np.quantile(th, .95):+.3f} (5-95%)')
        for n, A in (('K, kappa della partita', AKp), ('H, rho della partita', AH)):
            C.append((n, A)); LC[n] = perdite(A, B, hg, ag); print(f'  {n}')
            for k, t in METRI: confronto(t, L0[k], LC[n][k], g)
    print('\n3. PREVISTO E USCITO, in punti'); previsto(X, C)
    print('\n4. PER STAGIONE: risultato esatto / differenza reti / linea, contro la matrice di oggi')
    for n in LC:
        print(f'  {n}: ' + ' · '.join(f'{s_}: ' + ' / '.join(f'{1000 * np.nanmean((LC[n][m] - L0[m])[X["st"] == s_]):+.2f}' for m in ('esatti', 'handicap', 'linea')) for s_ in sorted(set(X['st'].tolist()))))
    print('\n5. LA LINEA DELL\'HANDICAP: copertura della casa, in punti (mezze puntate decise)'); linee(X, C[:4])

def prova():
    X = carica(PROVA); intesta(X, f'TEST, KR con kappa {KAPPA} fisso', PROVA)
    B, hg, ag, g, P, pov, lg12, rho = X['B'], X['hg'], X['ag'], X['g'], X['P'], X['pov'], X['lg12'], X['rho']
    A0 = allinea(pov, lg12, rho); AKs = allinea(pov, lg12, rho, np.full(len(B), KAPPA)); AKR = raking(AKs, P, pov); AR = raking(A0, P, pov)
    mR = qg.mercati(AKR)
    print(f'prova: KR da\' 1, X, 2 e Over 2.5 con le quote entro {100 * max(np.abs(mR["p1"] - P[:, 0]).max(), np.abs(pari(AKR) - P[:, 1]).max(), np.abs(mR["o25"] - pov).max()):.5f} punti')
    L0, LKR, LK, LR = (perdite(A, B, hg, ag) for A in (A0, AKR, AKs, AR))
    print('\n=== IL TEST: logloss del risultato esatto, KR contro la matrice allineata di oggi ===')
    d, z, zl, meglio, nl = confronto('risultato esatto', L0['esatti'], LKR['esatti'], g)
    per = {x: (1000 * np.nanmean((LKR['esatti'] - L0['esatti'])[g == x]), int((g == x).sum())) for x in sorted(set(g.tolist()))}
    print('   per lega: ' + ' · '.join(f'{x} {v:+.2f} ({n})' for x, (v, n) in per.items()))
    print('  guardie')
    G_ = {k: confronto(t, L0[k], LKR[k], g) for k, t in METRI[1:7]}
    ok = [z <= -2, zl <= -2, meglio > nl / 2, G_['handicap'][0] < 0, G_['linea'][0] < 0, all(G_[k][1] < 2 for k in G_)]
    print(f'  -> z per partita <= -2: {"si" if ok[0] else "no"} · z fra leghe <= -2: {"si" if ok[1] else "no"} · meglio in piu\' di meta\' delle leghe: {"si" if ok[2] else "no"} ({meglio}/{nl})'
          f' · differenza reti meglio: {"si" if ok[3] else "no"} · handicap alla linea meglio: {"si" if ok[4] else "no"} · nessun mercato peggio con z >= +2: {"si" if ok[5] else "no"}'
          f' · {"PASSA" if all(ok) else "NON PASSA"}')
    print('\n=== DESCRITTIVI ===')
    print('1. Quanto distano, oggi, la matrice e l\'1X2 con le quote'); distanza(X, A0)
    print('2. Per stagione, KR contro oggi: risultato esatto / differenza reti / linea')
    print('   ' + ' · '.join(f'{s_}: ' + ' / '.join(f'{1000 * np.nanmean((LKR[m] - L0[m])[X["st"] == s_]):+.2f}' for m in ('esatti', 'handicap', 'linea')) + f' ({int((X["st"] == s_).sum())})' for s_ in sorted(set(X['st'].tolist()))))
    print('3. I pezzi del candidato, contro oggi')
    for n, L in ((f'kappa {KAPPA} da solo', LK), ('raking da solo', LR)):
        print(f'  {n}')
        for k, t in METRI[:5]: confronto(t, L0[k], L[k], g)
    print('  KR contro i suoi pezzi')
    for k, t in METRI[:4]: confronto(f'KR contro kappa da solo: {t}', LK[k], LKR[k], g)
    for k, t in METRI[:4]: confronto(f'KR contro raking da solo: {t}', LR[k], LKR[k], g)
    C = [('matrice di oggi', A0), ('raking da solo', AR), (f'kappa {KAPPA} da solo', AKs), (f'KR, kappa {KAPPA} e raking', AKR)]
    print('4. Previsto e uscito, in punti'); previsto(X, C)
    print('5. La linea dell\'handicap: copertura della casa, in punti'); linee(X, C)
    print('\n=== GIA\' APERTI PER IL KAPPA (il test del 7 ottobre 2026): solo descrittivo ===')
    Y = carica(GIA_VISTI); intesta(Y, 'League One, League Two e Super Lig 2023/24-2025/26, e il 2026/27 delle diciotto leghe', GIA_VISTI)
    B0 = allinea(Y['pov'], Y['lg12'], Y['rho']); BK = kr(Y); M0, MK = perdite(B0, Y['B'], Y['hg'], Y['ag']), perdite(BK, Y['B'], Y['hg'], Y['ag'])
    gy = np.where(Y['st'] == '2627', 'il 2026/27', Y['g'])
    for k, t in METRI[:5]: confronto(t, M0[k], MK[k], gy)
    return all(ok)

if __name__ == '__main__':
    if not os.path.isdir(rq.FD): sys.exit('mancano i file di football-data: python3 strumenti/rating-quote.py --scarica')
    if '--prova' in sys.argv: sys.exit(0 if prova() else 1)
    esplora(ESPLORA)
