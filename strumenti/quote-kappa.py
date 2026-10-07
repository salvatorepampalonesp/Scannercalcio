# La differenza reti della matrice allineata, stretta (AGENTS.md, L'handicap della matrice allineata: la regola).
#
#   python3 strumenti/quote-kappa.py                                   # l'esplorazione, sulle 11 leghe (batch48 batch4)
#   python3 strumenti/quote-kappa.py --prova batch/nuove batch/2627    # il test registrato, una volta sola
#
# La matrice allineata del b57 (Dixon-Coles col rho del motore, lambda scelti perche' dia il log(p1/p2) di QUOTE_COMB e
# l'Over 2.5 di QUOTE_OU) moltiplicata per exp(-KAPPA*(x-y)^2), rinormalizzata e riallineata agli stessi due bersagli:
# 1X2 e Over 2.5 restano quelli, cambia solo come si distribuisce la differenza reti. L'handicap si misura alla linea del
# mercato come in quote-handicap.py (mezze puntate, il nulla escluso). Solo misura: lo Scanner non cambia.
import os, sys, math, collections, importlib.util
import numpy as np
QUI = os.path.dirname(os.path.abspath(__file__)); os.chdir(os.path.join(QUI, '..'))
s = importlib.util.spec_from_file_location('qh', os.path.join(QUI, 'quote-handicap.py')); qh = importlib.util.module_from_spec(s); s.loader.exec_module(qh)
qm, qg = qh.qm, qh.qg

KAPPA = 0.03            # scelto fuori lega sulla differenza reti, 11 fold su 11 (scritto prima del test)
GRIGLIA = [0.0, 0.01, 0.02, 0.03, 0.045, 0.06, 0.08, 0.10]

G = np.arange(11); I, J = np.meshgrid(G, G, indexing='ij'); D2 = (I - J) ** 2
def mat_k(lh, la, rho, k):
    P = qg.matrici(lh, la, rho) * np.exp(-k * D2); return P / P.sum((1, 2), keepdims=True)
def dividi(T, lg12, rho, k, it=30):
    lo, hi = np.full(len(T), 0.01), np.full(len(T), 0.99)
    for _ in range(it):
        s_ = (lo + hi) / 2; m = qg.mercati(mat_k(T * s_, T * (1 - s_), rho, k))
        su = np.log(m['p1'] / m['p2']) < lg12; lo = np.where(su, s_, lo); hi = np.where(su, hi, s_)
    return (lo + hi) / 2
def allinea(pov, lg12, rho, k, it=40):
    lo, hi = np.full(len(pov), 0.2), np.full(len(pov), 9.0)
    for _ in range(it):
        T = (lo + hi) / 2; s_ = dividi(T, lg12, rho, k, 25); m = qg.mercati(mat_k(T * s_, T * (1 - s_), rho, k))
        su = m['o25'] < pov; lo = np.where(su, T, lo); hi = np.where(su, hi, T)
    T = (lo + hi) / 2; s_ = dividi(T, lg12, rho, k, 40); return mat_k(T * s_, T * (1 - s_), rho, k)

def prepara(dirs):
    W, b, OU = qm.costanti(); M, Q = qm.carica(dirs, 'batch/quote'); C = qm.calcola(Q, W, b, OU)
    rho = np.array([q['rho'] for q in C['Q']]); lg12 = np.log(C['PC'][:, 0] / C['PC'][:, 2])
    rows = []
    for i, q in enumerate(C['Q']):
        a = qh.ah_quote(q['riga'])
        if not a: continue
        h, oh, oa, _ = a
        if abs(round(h * 4) - h * 4) > 1e-6: continue
        d = q['hg'] - q['ag']; e = [qh.esito(d, hh) for hh in qh.sotto(h)]; w = sum(x > 0 for x in e); l = sum(x < 0 for x in e)
        if w + l == 0: continue
        rows.append(dict(i=i, h=h, pm=(1 / oh) / (1 / oh + 1 / oa), y=w / (w + l), wt=w + l))
    return C, rho, lg12, rows

def misure(C, rows, A):
    hg, ag = C['hg'], C['ag']; n = len(hg); ii = np.arange(n); ok = (hg <= 10) & (ag <= 10)
    idx = np.array([r['i'] for r in rows]); h = np.array([r['h'] for r in rows]); y = np.array([r['y'] for r in rows]); wt = np.array([r['wt'] for r in rows], float)
    GD = qh.gd_dist(A[idx]); p = np.array([qh.p_imp(GD[j:j + 1], h[j])[0] for j in range(len(rows))])
    cl = lambda classi, yy: -np.log(np.stack([(A * c).sum((1, 2)) for c in classi], 1)[ii, yy])
    es = np.full(n, np.nan); es[ok] = -np.log(np.clip(A[ii[ok], hg[ok], ag[ok]], 1e-12, 1))
    mg = cl([np.minimum(I + J, 6) == c for c in range(7)], np.minimum(hg + ag, 6)) + cl([np.minimum(I, 3) == c for c in range(4)], np.minimum(hg, 3)) \
        + cl([np.minimum(J, 3) == c for c in range(4)], np.minimum(ag, 3))
    gg = ((hg > 0) & (ag > 0)).astype(float); pgg = (A * ((I > 0) & (J > 0))).sum((1, 2))
    return dict(hand=wt * qg.ll(p, y) / wt.mean(), p_hand=p, dr=cl([np.clip(I - J, -3, 3) + 3 == c for c in range(7)], np.clip(hg - ag, -3, 3) + 3),
                esatto=es, multigol=mg, goal=qg.ll(pgg, gg), pgg=pgg, o15=(A * (I + J > 1.5)).sum((1, 2)), o35=(A * (I + J > 3.5)).sum((1, 2)),
                pari=(A * (I == J)).sum((1, 2)))

def confronto(nome, a, b, grp):
    k = ~np.isnan(a) & ~np.isnan(b); d = (b - a)[k]; g = grp[k]; z = d.mean() / d.std(ddof=1) * math.sqrt(len(d))
    per = {x: d[g == x].mean() for x in sorted(set(g))}
    print(f'  {nome:44s} {1000 * d.mean():+7.2f}‰  z {z:+6.2f}  meglio in {sum(v < 0 for v in per.values())}/{len(per)} · '
          + ' · '.join(f'{x} {1000 * v:+.2f}' for x, v in per.items()))
    return d.mean(), z, sum(v < 0 for v in per.values()), len(per)

def per_linea(rows, pa, pk, grp=None):
    h = np.array([r['h'] for r in rows]); y = np.array([r['y'] for r in rows]); wt = np.array([r['wt'] for r in rows], float); pm = np.array([r['pm'] for r in rows])
    print('  linea (casa)  partite  allineata  corretta  mercato  realizzato')
    for v, n in sorted(collections.Counter(h).items()):
        if n < 100: continue
        k = h == v
        print(f'  {v:+5.2f}      {n:5d}     {np.average(pa[k], weights=wt[k]):.3f}     {np.average(pk[k], weights=wt[k]):.3f}    {np.average(pm[k], weights=wt[k]):.3f}    {np.average(y[k], weights=wt[k]):.3f}')

def esplora(dirs):
    C, rho, lg12, rows = prepara(dirs); lg = C['lega']; lgr = lg[[r['i'] for r in rows]]
    print(f'{len(C["Q"])} partite con le quote di 1X2 e Over, {len(rows)} anche con quelle dell handicap')
    MS = {k: misure(C, rows, allinea(C['pc'], lg12, rho, k)) for k in GRIGLIA}
    print('in campione, contro kappa 0 (per mille): ' + ' · '.join(f'{k}: handicap {1000 * (MS[k]["hand"] - MS[0]["hand"]).mean():+.2f}, differenza reti {1000 * (MS[k]["dr"] - MS[0]["dr"]).mean():+.2f}' for k in GRIGLIA[1:]))
    scelto = {l: min(GRIGLIA, key=lambda k: MS[k]['dr'][lg != l].mean()) for l in sorted(set(lg))}
    print(f'kappa scelto fuori lega sulla differenza reti: {collections.Counter(scelto.values())}')
    pick = lambda key, grp: np.concatenate([[MS[scelto[x]][key][j]] for j, x in enumerate(grp)])
    print('fuori lega, corretta contro allineata:')
    confronto('handicap (linea del mercato)', MS[0]['hand'], pick('hand', lgr), lgr)
    for key, nome in (('dr', 'differenza reti'), ('esatto', 'risultato esatto'), ('multigol', 'multigol'), ('goal', 'Goal')):
        confronto(nome, MS[0][key], pick(key, lg), lg)
    per_linea(rows, MS[0]['p_hand'], pick('p_hand', lgr))

def prova(dirs):
    C, rho, lg12, rows = prepara(dirs)
    bl = C['bl']; blr = bl[[r['i'] for r in rows]]
    print(f'TEST, kappa {KAPPA} fisso: {len(C["Q"])} partite con le quote di 1X2 e Over (prova della matrice del motore entro {C["dev"]:.3f} punti), '
          f'{len(rows)} anche con quelle dell handicap · blocchi ' + ', '.join(f'{x} {v}' for x, v in sorted(collections.Counter(blr).items())))
    A0 = misure(C, rows, allinea(C['pc'], lg12, rho, 0.0)); AK = misure(C, rows, allinea(C['pc'], lg12, rho, KAPPA))
    print('\n=== IL TEST: logloss della copertura dell handicap alla linea del mercato, corretta contro allineata ===')
    d, z, meglio, nb = confronto('handicap', A0['hand'], AK['hand'], blr)
    print('  guardie (non devono peggiorare sull insieme):')
    de, ze, _, _ = confronto('risultato esatto', A0['esatto'], AK['esatto'], bl)
    dm, zm, _, _ = confronto('multigol', A0['multigol'], AK['multigol'], bl)
    ok = z <= -2 and meglio >= 3 and de <= 0 and dm <= 0
    print(f'  -> z <= -2: {"si" if z <= -2 else "no"} · meglio in almeno 3 blocchi su 4: {"si" if meglio >= 3 else "no"} ({meglio}/{nb})'
          f' · risultato esatto non peggiore: {"si" if de <= 0 else "no"} · multigol non peggiore: {"si" if dm <= 0 else "no"} · {"PASSA" if ok else "NON PASSA"}')
    print('\n=== DESCRITTIVI ===')
    confronto('differenza reti', A0['dr'], AK['dr'], bl); confronto('Goal', A0['goal'], AK['goal'], bl)
    hg, ag = C['hg'], C['ag']; gg = ((hg > 0) & (ag > 0)).astype(float)
    pm_ = np.array([r['pm'] for r in rows]); y_ = np.array([r['y'] for r in rows]); wt_ = np.array([r['wt'] for r in rows], float)
    confronto('handicap: corretta contro il mercato dell handicap', AK['hand'], wt_ * qg.ll(pm_, y_) / wt_.mean(), blr)
    print(f'  Goal previsto: allineata {100 * A0["pgg"].mean():.1f}, corretta {100 * AK["pgg"].mean():.1f}, reale {100 * gg.mean():.1f} · '
          f'pareggi {100 * A0["pari"].mean():.1f} / {100 * AK["pari"].mean():.1f} / {100 * (hg == ag).mean():.1f} · '
          f'Over 1.5 {100 * A0["o15"].mean():.1f} / {100 * AK["o15"].mean():.1f} / {100 * (hg + ag > 1.5).mean():.1f} · '
          f'Over 3.5 {100 * A0["o35"].mean():.1f} / {100 * AK["o35"].mean():.1f} / {100 * (hg + ag > 3.5).mean():.1f}')
    for a, b_ in ((0, .4), (.4, .5), (.5, .6), (.6, 1)):
        k = (A0['pgg'] >= a) & (A0['pgg'] < b_)
        if k.sum() >= 30: print(f'  Goal, fascia {int(100 * a)}-{int(100 * b_)} dell allineata: {k.sum()} partite, allineata {100 * A0["pgg"][k].mean():.1f}, corretta {100 * AK["pgg"][k].mean():.1f}, esce {100 * gg[k].mean():.1f}')
    per_linea(rows, A0['p_hand'], AK['p_hand'])

if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '--prova': prova(a[1:] or ['batch/nuove', 'batch/2627'])
    else: esplora(a or ['batch48', 'batch4'])
