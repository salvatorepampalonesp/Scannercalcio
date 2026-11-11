# La coerenza del verdetto: il pareggio col rating dalle quote passate, e la matrice dei gol contro l'1X2 a schermo
# (AGENTS.md, Da fare, «Il verdetto e la matrice dei gol non descrivono la stessa partita»).
#
#   python3 strumenti/coerenza.py <cartelle o file di CSV del Comparatore, dal b77>
#
# Solo esplorazione. Nessuna chiamata e nessun file di quote: tutto dai CSV. I due candidati non hanno parametri.
#
# 1. IL PAREGGIO (CSV dal b96, partite col rating attivo). Lo Scanner corregge log(p1/p2) del maestro col rating e tiene
#    FERMO il pareggio del maestro. Ma nessun modello dei gol tiene fermo il pareggio quando cambia lo squilibrio.
#    Candidato: tenere fermo il parametro di Davidson, nu = pX * 2cosh(lg/2) / (1 - pX) dal maestro, e ricavare
#    pX' = nu / (2cosh(lg'/2) + nu). Sui casi tipo coincide entro 0.1 punti col pareggio della matrice Dixon-Coles a
#    totale fisso (node strumenti/formule.js, punto 5). Metro: logloss 1X2 contro il verdetto di oggi.
# 2. LA MATRICE (CSV dal b77, maestro attivo). Risultati esatti, handicap e multigol escono dalla matrice dei lambda del
#    maestro, l'1X2 a schermo no (softmax del maestro, e dal b96 il rating): l'handicap -0.5 non e' l'1 del verdetto.
#    Due candidati: A, la matrice riallineata (stessi Over 2.5 e rho, lambda divisi per dare il log(p1/p2) del verdetto,
#    come matriceAllineata dello Scanner); B, la matrice del maestro riscalata (raking) finche' 1, X, 2 sono quelli del
#    verdetto e l'Over 2.5 resta il suo. Metro: i tre di strumenti/quote-matrice.py (risultati esatti, multigol,
#    differenza reti) e il Goal, contro la matrice di oggi.
#
# Per ogni confronto: differenza appaiata, z per partita e z con l'errore fra leghe (qb.zeta_leghe), in quante leghe
# migliora. Sulle 14 leghe dell'allenamento del maestro le sue probabilita' sono in campione (AGENTS.md, Il maestro
# mercato: la regola): i candidati non hanno parametri, ma il numero che conta e' quello delle altre leghe.
# Prima la prova di coincidenza: la matrice rifatta dai lambda del CSV deve ridare Over 1.5, Over 3.5 e Goal del CSV,
# e il verdetto rifatto da maestro e rating deve ridare 1, X, 2 del CSV.
import os, re, io, sys, glob, math, importlib.util
import numpy as np
QUI = os.path.dirname(os.path.abspath(__file__))
_s = importlib.util.spec_from_file_location('qm', os.path.join(QUI, 'quote-matrice.py'))
qm = importlib.util.module_from_spec(_s); _a = sys.argv; sys.argv = ['x']; _s.loader.exec_module(qm); sys.argv = _a
qg, qb = qm.qg, qm.qb
ALLENAMENTO = {'Serie A', 'Premier League', 'LaLiga', 'Bundesliga', 'Ligue 1', 'Championship', 'Eredivisie', 'Liga Portugal',
               '2. Bundesliga', 'First Division A', 'Premiership', 'League One', 'League Two', 'Super Lig'}

def regola():
    s = io.open(os.path.join(QUI, '..', 'scanner.html'), encoding='utf-8').read()
    m = re.search(r'const QUOTE_PASSATE_REG = \{ a: ([-\d.]+), b: ([-\d.]+), c: ([-\d.]+),', s)
    return [float(x) for x in m.groups()]

def etichetta(f):
    b = os.path.basename(f)[:-4].replace('Backtest_V97_', ''); return b.rsplit('_', 1)[0] if '_' in b else b

def carica(percorsi):
    M = []
    for p in percorsi:
        for f in ([p] if os.path.isfile(p) else sorted(glob.glob(os.path.join(p, '*.csv')))):
            for m in qb.leggi_csv(f):
                if m['lamM'][0] is None or None in m['lam'] or m['rho'] is None or None in m['p']: continue   # senza maestro
                m['gruppo'] = etichetta(f); M.append(m)
    return M

def zeta(d): d = np.asarray(d, float); return d.mean() / d.std(ddof=1) * math.sqrt(len(d)) if len(d) > 1 and d.std() else 0.0

def confronto(nome, a, b, g, ok=None):
    ok = np.isfinite(a) & np.isfinite(b) if ok is None else ok
    d = (b - a)[ok]; gg = g[ok]
    if not len(d): print(f'   {nome}: nessuna partita'); return
    per = {x: d[gg == x].mean() for x in sorted(set(gg.tolist()))}
    zl = qb.zeta_leghe(d, gg); zl = 'n/d' if zl != zl else f'{zl:+.2f}'
    print(f'   {nome}: {1000 * d.mean():+.2f} per mille (z {zeta(d):+.2f}, fra leghe {zl}), {len(d)} partite, meglio in {sum(v < 0 for v in per.values())} leghe su {len(per)}')

def davidson(pm, lg):
    # pm: 1, X, 2 del maestro; lg: il log(p1/p2) corretto. nu fisso: il pareggio segue lo squilibrio
    lg0 = np.log(pm[:, 0] / pm[:, 2]); nu = pm[:, 1] * 2 * np.cosh(lg0 / 2) / (1 - pm[:, 1])
    pX = nu / (2 * np.cosh(lg / 2) + nu); p1 = (1 - pX) / (1 + np.exp(-lg)); return np.c_[p1, pX, 1 - pX - p1]

def fermo(pm, lg):
    pX = pm[:, 1]; p1 = (1 - pX) / (1 + np.exp(-lg)); return np.c_[p1, pX, 1 - pX - p1]

def raking(P, p, ov, giri=60):
    # P: matrici (n, 11, 11); p: 1, X, 2 da dare; ov: Over 2.5 da tenere. Riscala le tre regioni e le due fasce a turno
    R = [(qg.I > qg.J), (qg.I == qg.J), (qg.I < qg.J)]; O = qg.I + qg.J > 2.5; Q = P.copy()
    for _ in range(giri):
        for k, r in enumerate(R):
            s = (Q * r).sum((1, 2)); Q = np.where(r, Q * (p[:, k] / s)[:, None, None], Q)
        s = (Q * O).sum((1, 2)); Q = np.where(O, Q * (ov / s)[:, None, None], Q * ((1 - ov) / (1 - s))[:, None, None])
    return Q

def pareggio(M, g):
    a, b, c = regola()
    Q = [m for m in M if m['qp'] == 'si' and m['pMa'] and m['yq'] is not None]
    print(f'\n1. IL PAREGGIO COL RATING: {len(Q)} partite col rating attivo su {len(M)}')
    if len(Q) < 2: print('   servono CSV dal b96 con le quote passate attive'); return True
    gq = np.array([m['gruppo'] for m in Q]); y = np.array([m['out'] for m in Q]); i = np.arange(len(Q))
    pm = np.array([m['pMa'] for m in Q], float); pm /= pm.sum(1, keepdims=True); pv = np.array([m['p'] for m in Q], float)
    lg = a + b * np.log(pm[:, 0] / pm[:, 2]) + c * np.array([m['yq'] for m in Q]); F = fermo(pm, lg); D = davidson(pm, lg)
    sc = np.abs(F - pv).max(); ok = sc <= 0.0025
    print(f'   prova di coincidenza: il verdetto rifatto da maestro e rating sta entro {100 * sc:.2f} punti da 1, X, 2 del CSV' + ('' if ok else ' -> NON COINCIDE'))
    L = lambda P: -np.log(np.clip(P[i, y], 1e-12, 1))
    confronto('logloss 1X2, Davidson contro pareggio fermo', L(F), L(D), gq)
    hF = (F.argmax(1) == y).astype(float); hD = (D.argmax(1) == y).astype(float); dh = hD - hF
    print(f'   prese {100 * hF.mean():.2f} -> {100 * hD.mean():.2f}% ({100 * dh.mean():+.2f} ±{200 * dh.std(ddof=1) / math.sqrt(len(dh)):.2f}), pick cambiato in {int((F.argmax(1) != D.argmax(1)).sum())} partite')
    sp = np.abs(lg) - np.abs(np.log(pm[:, 0] / pm[:, 2])); x = (y == 1).astype(float)
    print('   il pareggio per spostamento dello squilibrio (|lg corretto| - |lg del maestro|): partite, fermo, Davidson, uscito')
    for nome, k in (('piu\' equilibrata (sotto -0.10)', sp < -0.10), ('quasi uguale', np.abs(sp) <= 0.10), ('piu\' sbilanciata (sopra +0.10)', sp > 0.10)):
        if k.sum(): print(f'     {nome:32s} {int(k.sum()):6d}  {100 * F[k, 1].mean():5.1f}  {100 * D[k, 1].mean():5.1f}  {100 * x[k].mean():5.1f} ±{200 * x[k].std() / math.sqrt(k.sum()):.1f}')
    print(f'   spostamento: deviazione {sp.std():.3f}; il pareggio cambia in media di {100 * np.abs(D[:, 1] - F[:, 1]).mean():.2f} punti, al massimo {100 * np.abs(D[:, 1] - F[:, 1]).max():.2f}')
    return ok

def matrice(M, g):
    print(f'\n2. LA MATRICE DEI GOL CONTRO IL VERDETTO: {len(M)} partite col maestro')
    lh = np.array([m['lam'][0] for m in M]); la = np.array([m['lam'][1] for m in M]); rho = np.array([m['rho'] for m in M])
    hg = np.array([m['hg'] for m in M]); ag = np.array([m['ag'] for m in M])
    p = np.array([m['p'] for m in M], float); p /= p.sum(1, keepdims=True)
    P0 = qg.matrici(lh, la, rho); m0 = qg.mercati(P0)
    sc = max(np.abs(100 * m0[k] - np.array([m['gol'][n] if m['gol'][n] is not None else np.nan for m in M])).max()
             for k, n in (('o15', 'Over 1.5'), ('o35', 'Over 3.5'), ('gg', 'GG (da matrice)')))
    ok = sc <= 0.08
    print(f'   prova di coincidenza: Over 1.5, Over 3.5 e Goal rifatti dai lambda stanno entro {sc:.3f} punti dal CSV' + ('' if ok else ' -> NON COINCIDE'))
    x0 = 1 - m0['p1'] - m0['p2']
    print(f'   oggi, verdetto contro matrice: 1 {100 * p[:, 0].mean():.1f} / {100 * m0["p1"].mean():.1f}, X {100 * p[:, 1].mean():.1f} / {100 * x0.mean():.1f}, 2 {100 * p[:, 2].mean():.1f} / {100 * m0["p2"].mean():.1f};'
          f' in media distano {100 * np.abs(p[:, 0] - m0["p1"]).mean():.1f} punti sull\'1 e {100 * np.abs(p[:, 1] - x0).mean():.1f} sul pareggio (un decimo delle partite oltre {100 * np.quantile(np.abs(p[:, 0] - m0["p1"]), 0.9):.1f})')
    ah, aa = qg.allinea(m0['o25'], np.log(p[:, 0] / p[:, 2]), rho); PA = qg.matrici(ah, aa, rho); PB = raking(P0, p, m0['o25'])
    mB = qg.mercati(PB); print(f'   raking: 1 e Over 2.5 raggiunti entro {100 * max(np.abs(mB["p1"] - p[:, 0]).max(), np.abs(mB["o25"] - m0["o25"]).max()):.4f} punti')
    L0, LA, LB = qm.perdite(P0, hg, ag), qm.perdite(PA, hg, ag), qm.perdite(PB, hg, ag)
    gg = ((hg > 0) & (ag > 0)).astype(float)
    for d, P in ((L0, P0), (LA, PA), (LB, PB)): d['goal'] = qg.ll(qg.mercati(P)['gg'], gg)
    gruppi = [('tutte', np.ones(len(M), bool))]
    al = np.array([m['lega'] in ALLENAMENTO for m in M])
    if al.any() and (~al).any(): gruppi += [('leghe mai viste dal maestro', ~al), ("leghe dell'allenamento (in campione)", al)]
    for nome, k in gruppi:
        print(f'   --- {nome}: {int(k.sum())} partite')
        for cand, Lc in (('A, riallineata', LA), ('B, raking', LB)):
            for metro, tit in (('handicap', 'differenza reti'), ('esatti', 'risultato esatto'), ('multigol', 'multigol'), ('goal', 'Goal')):
                confronto(f'{cand}: {tit}', L0[metro][k], Lc[metro][k], g[k])
        confronto('B contro A: differenza reti', LA['handicap'][k], LB['handicap'][k], g[k])
    gB = qg.mercati(PB)['gg']; gA = qg.mercati(PA)['gg']
    print(f'   Goal previsto: oggi {100 * m0["gg"].mean():.1f}, A {100 * gA.mean():.1f}, B {100 * gB.mean():.1f}, uscito {100 * gg.mean():.1f};'
          f' pareggi: oggi {100 * x0.mean():.1f}, A {100 * (1 - qg.mercati(PA)["p1"] - qg.mercati(PA)["p2"]).mean():.1f}, B {100 * p[:, 1].mean():.1f}, usciti {100 * (hg == ag).mean():.1f}')
    return ok

if __name__ == '__main__':
    arg = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not arg: sys.exit('uso: python3 strumenti/coerenza.py <cartelle o file di CSV dal b77>')
    M = carica(arg)
    if len(M) < 2: sys.exit('nessuna partita col maestro acceso nei CSV dati: servono CSV dal b77')
    g = np.array([m['gruppo'] for m in M])
    print(f'{len(M)} partite in copia conforme col maestro acceso, {len(set(g.tolist()))} leghe')
    ok1 = pareggio(M, g); ok2 = matrice(M, g)
    sys.exit(0 if ok1 and ok2 else 1)
