# Le quote per gli altri mercati (AGENTS.md, Le quote per gli altri mercati: la regola).
#
#   python3 strumenti/quote-gol.py batch48 batch4 [--quote batch/quote]
#
# Stesse partite e stesso aggancio di strumenti/quote-bookmaker.py. Rifa' i tre test registrati:
# l'Over 2.5 motore + mercato (undici leghe coi file principali), il Goal dalla matrice allineata
# all'Over e all'1X2 con le quote, il Goal dalla matrice del motore inclinata con le sole quote
# dell'1X2 (dodici leghe); poi i descrittivi e i coefficienti su tutte le partite (QUOTE_OU).
import os, sys, math, json, importlib.util, warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
warnings.filterwarnings('ignore')
_s = importlib.util.spec_from_file_location('qb', os.path.join(os.path.dirname(__file__), 'quote-bookmaker.py'))
qb = importlib.util.module_from_spec(_s); _s.loader.exec_module(qb)

G = np.arange(11)
LF = np.array([math.lgamma(k + 1) for k in G])

def matrici(lh, la, rho):
    lh, la, rho = [np.asarray(x, float)[:, None] for x in (lh, la, rho)]
    ph = np.exp(-lh + G * np.log(lh) - LF); pa = np.exp(-la + G * np.log(la) - LF)
    P = ph[:, :, None] * pa[:, None, :]
    P[:, 0, 0] *= np.maximum(0, 1 - lh[:, 0] * la[:, 0] * rho[:, 0]); P[:, 0, 1] *= np.maximum(0, 1 + lh[:, 0] * rho[:, 0])
    P[:, 1, 0] *= np.maximum(0, 1 + la[:, 0] * rho[:, 0]); P[:, 1, 1] *= np.maximum(0, 1 - rho[:, 0])
    return P / P.sum((1, 2), keepdims=True)

I, J = np.meshgrid(G, G, indexing='ij')
def mercati(P):
    s = lambda k: (P * k).sum((1, 2))
    return {'p1': s(I > J), 'p2': s(I < J), 'gg': s((I > 0) & (J > 0)), 'o15': s(I + J > 1.5), 'o25': s(I + J > 2.5), 'o35': s(I + J > 3.5)}

def dividi(T, lg12, rho, it=50):
    lo, hi = np.full(len(T), 0.01), np.full(len(T), 0.99)
    for _ in range(it):
        s = (lo + hi) / 2; m = mercati(matrici(T * s, T * (1 - s), rho))
        su = np.log(m['p1'] / m['p2']) < lg12; lo = np.where(su, s, lo); hi = np.where(su, hi, s)
    return (lo + hi) / 2

def allinea(pov, lg12, rho, it=45):
    lo, hi = np.full(len(pov), 0.2), np.full(len(pov), 9.0)
    for _ in range(it):
        T = (lo + hi) / 2; s = dividi(T, lg12, rho, 30); m = mercati(matrici(T * s, T * (1 - s), rho))
        su = m['o25'] < pov; lo = np.where(su, T, lo); hi = np.where(su, hi, T)
    T = (lo + hi) / 2; s = dividi(T, lg12, rho); return T * s, T * (1 - s)

def ou(r, pre):
    for k in pre:
        a, b = qb.num(r.get(k + '>2.5')), qb.num(r.get(k + '<2.5'))
        if a and b and a > 1 and b > 1: return [a, b], k
    return None, None

def logit(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))
def ll(p, y): p = np.clip(p, 1e-9, 1 - 1e-9); return -(y * np.log(p) + (1 - y) * np.log(1 - p))

def stima2(X, y):
    mu, sd = X.mean(0), X.std(0)
    m = LogisticRegression(C=1.0, max_iter=2000).fit((X - mu) / sd, y)
    w = m.coef_[0] / sd; return np.r_[m.intercept_[0] - (m.coef_[0] * mu / sd).sum(), w]

def lolo2(X, y, lg):
    p = np.zeros(len(y))
    for l in sorted(set(lg)):
        te = lg == l; c = stima2(X[~te], y[~te]); p[te] = 1 / (1 + np.exp(-(c[0] + X[te] @ c[1:])))
    return p

def confronto(nome, pa, pb, y, lg, k=None):
    k = np.ones(len(y), bool) if k is None else k
    d = ll(pb, y)[k] - ll(pa, y)[k]; L = lg[k]
    z = d.mean() / d.std(ddof=1) * math.sqrt(len(d)); per = {l: d[L == l].mean() for l in sorted(set(L))}
    meglio = sum(v < 0 for v in per.values())
    print(f'{nome}: logloss {ll(pa, y)[k].mean():.5f} -> {ll(pb, y)[k].mean():.5f} ({d.mean():+.5f}, z {z:+.2f}) · meglio in {meglio}/{len(per)} leghe')
    return z, meglio, per

def auc(p, y):
    o = np.argsort(p); r = np.empty(len(p)); r[o] = np.arange(1, len(p) + 1)
    n1 = y.sum(); return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))

def carica(args):
    cq = 'batch/quote'
    if '--quote' in args: i = args.index('--quote'); cq = args[i + 1]; del args[i:i + 2]
    M = [m for d in args for f in sorted(qb.glob.glob(os.path.join(d, '*.csv'))) for m in qb.leggi_csv(f)]
    M = list({m['id']: m for m in M}.values())
    qb.scarica(cq); return M, qb.aggancia(M, qb.quote_fd(cq))

def con_quote(Q):
    lg = np.array([q['lega'] for q in Q]); hg = np.array([q['hg'] for q in Q]); ag = np.array([q['ag'] for q in Q])
    y1 = np.array([q['out'] for q in Q])
    P0 = np.array([q['p'] for q in Q]); P0 /= P0.sum(1, keepdims=True)
    PM = np.array([[1 / x for x in q['qc']] for q in Q]); PM /= PM.sum(1, keepdims=True)
    lr = lambda P: np.column_stack([np.log(P[:, 0] / P[:, 1]), np.log(P[:, 2] / P[:, 1])])
    X1 = np.column_stack([lr(P0), lr(PM)]); PC = np.zeros((len(Q), 3))
    for l in sorted(set(lg)):
        te = lg == l; W, b = stima1(X1[~te], y1[~te]); Z = X1[te] @ W.T + b; Z -= Z.max(1, keepdims=True); E = np.exp(Z); PC[te] = E / E.sum(1, keepdims=True)
    lamH = np.array([q['lam'][0] for q in Q]); lamA = np.array([q['lam'][1] for q in Q]); rho = np.array([q['rho'] for q in Q])
    E0 = mercati(matrici(lamH, lamA, rho))
    yo = (hg + ag > 2).astype(float)
    OUc = [ou(q['riga'], ['AvgC', 'PC', 'B365C']) for q in Q]
    k = np.array([o[0] is not None for o in OUc])
    pm = np.array([(1 / o[0][0]) / (1 / o[0][0] + 1 / o[0][1]) for o in OUc if o[0]]); pe = E0['o25'][k]
    X = np.column_stack([logit(pe), logit(pm)]); pc = lolo2(X, yo[k], lg[k])
    aH, aA = allinea(pc, np.log(PC[k, 0] / PC[k, 2]), rho[k]); A = mercati(matrici(aH, aA, rho[k]))
    return dict(lg=lg, hg=hg, ag=ag, y1=y1, P0=P0, PM=PM, PC=PC, E0=E0, rho=rho, lamH=lamH, lamA=lamA, OUc=OUc, k=k, pm=pm, pe=pe, X=X, pc=pc, aH=aH, aA=aA, A=A)

def main():
    M, Q = carica(sys.argv[1:]); C = con_quote(Q)
    lg, hg, ag, y1, PC, E0, rho, lamH, lamA, OUc, k, pm, pe, X, pc = [C[x] for x in 'lg hg ag y1 PC E0 rho lamH lamA OUc k pm pe X pc'.split()]
    dev = max(abs(100 * E0[kk] - np.array([q['gol'][c] for q in Q])).max() for kk, c in (('o15', 'Over 1.5'), ('o25', 'Over 2.5'), ('o35', 'Over 3.5'), ('gg', 'GG (da matrice)')))
    print(f'prova di coincidenza della matrice del motore: scarto massimo {dev:.3f} punti su {len(Q)} partite')
    yo = (hg + ag > 2).astype(float); yg = ((hg > 0) & (ag > 0)).astype(float)
    OUp = [ou(q['riga'], ['Avg', 'P', 'B365']) for q in Q]
    print(f'partite con le quote dell Over di chiusura: {k.sum()} su {len(Q)} ({dict(qb.collections.Counter(o[1] for o in OUc if o[0]))})'
          f' · leghe {len(set(lg[k]))}: fuori {sorted(set(lg) - set(lg[k]))}')
    L = lg[k]; Yo = yo[k]; Yg = yg[k]

    print('\n=== PRIMO TEST: Over 2.5, combinazione contro motore ===')
    z, meglio, per = confronto('combinazione contro motore', pe, pc, Yo, L)
    print('ESITO:', 'PASSA' if z <= -2 and meglio >= 8 else 'NON PASSA', '(z <= -2 e almeno 8 leghe su 11)')
    for l, v in per.items(): print(f'  {l:17s} {(L == l).sum():5d} {v:+.5f}')
    print('descrittivi:'); confronto('  mercato contro motore', pe, pm, Yo, L); confronto('  combinazione contro mercato', pm, pc, Yo, L)
    confronto('  combinazione contro mercato ricalibrato', lolo2(logit(pm)[:, None], Yo, L), pc, Yo, L)
    c = stima2(X, Yo); print(f'  pesi su tutte (logit grezzi): intercetta {c[0]:+.4f}, motore {c[1]:+.4f}, mercato {c[2]:+.4f}')
    print('  prese Over/Under: motore {:.1f} · mercato {:.1f} · combinazione {:.1f}'.format(*[100 * ((p > .5) == Yo).mean() for p in (pe, pm, pc)]))
    print('  Over previsto / reale: motore {:.1f} · mercato {:.1f} · combinazione {:.1f} · reale {:.1f}'.format(*[100 * p.mean() for p in (pe, pm, pc, Yo)]))
    print('  AUC dell Over per lega, motore / mercato / combinazione:')
    for l in sorted(set(L)):
        s = L == l; print(f'    {l:17s} ' + ' / '.join(f'{auc(p[s], Yo[s]):.3f}' for p in (pe, pm, pc)))
    qo = np.array([o[0] for o in OUc if o[0]])
    gioca = lambda sc, q: np.where(sc, np.where(Yo == 1, q[:, 0] - 1, -1), np.where(Yo == 0, q[:, 1] - 1, -1))
    print(f'  resa giocando sempre la scelta alla chiusura: motore {100 * gioca(pe > .5, qo).mean():+.1f}% · mercato {100 * gioca(pm > .5, qo).mean():+.1f}%'
          f' · combinazione {100 * gioca(pc > .5, qo).mean():+.1f}% · margine medio {100 * (1 / qo[:, 0] + 1 / qo[:, 1] - 1).mean():.1f}%')
    for t in (3, 5, 8):
        so, su = pe - pm >= t / 100, pm - pe >= t / 100
        r = np.r_[np.where(Yo[so] == 1, qo[so, 0] - 1, -1), np.where(Yo[su] == 0, qo[su, 1] - 1, -1)]
        print(f'  dove il motore si discosta dal mercato di {t}+ punti, giocando il suo lato: {len(r)} giocate, {100 * r.mean():+.1f}%'
              f' (Over {so.sum()}: escono {100 * Yo[so].mean():.1f}% contro {100 * pm[so].mean():.1f}% del mercato; Under {su.sum()})')
    kp = np.array([o[0] is not None for o in OUp])[k]
    if kp.sum():
        pp = np.array([(1 / o[0][0]) / (1 / o[0][0] + 1 / o[0][1]) if o[0] else np.nan for o in OUp])[k]
        Xp = np.column_stack([logit(pe), logit(np.where(kp, pp, .5))])
        pcp = np.zeros(len(Yo))
        for l in sorted(set(L)):
            te = L == l; cc = stima2(X[~te], Yo[~te]); pcp[te] = 1 / (1 + np.exp(-(cc[0] + Xp[te] @ cc[1:])))
        confronto(f'  quote di prima della partita ({kp.sum()} partite), coi coefficienti della chiusura, contro motore', pe, pcp, Yo, L, kp)

    print('\n=== SECONDO TEST: Goal dalla matrice allineata ===')
    lg12 = np.log(PC[k, 0] / PC[k, 2]); aH, aA, A = C['aH'], C['aA'], C['A']
    r1, r2 = abs(A['o25'] - pc).max(), abs(np.log(A['p1'] / A['p2']) - lg12).max()
    print(f'allineamento: scarto massimo sull Over {r1:.2e}, su log(p1/p2) {r2:.2e}')
    z, meglio, per = confronto('Goal, matrice allineata contro motore', E0['gg'][k], A['gg'], Yg, L)
    print('ESITO:', 'PASSA' if z <= -2 and meglio >= 8 else 'NON PASSA', '(z <= -2 e almeno 8 leghe su 11)')
    for l, v in per.items(): print(f'  {l:17s} {v:+.5f}')
    for nome, key, yy in (('Over 1.5', 'o15', (hg + ag > 1)), ('Over 3.5', 'o35', (hg + ag > 3))):
        z2, _, _ = confronto(f'{nome}, matrice allineata contro motore', E0[key][k], A[key], yy[k].astype(float), L)
        print(f'  {nome}:', 'ENTRA' if z2 <= -2 else 'NON ENTRA', '(z <= -2)')
    print('descrittivi:')
    print('  Goal previsto / reale: motore {:.1f} · allineata {:.1f} · reale {:.1f}; AUC motore {:.3f} · allineata {:.3f}'.format(
        100 * E0['gg'][k].mean(), 100 * A['gg'].mean(), 100 * Yg.mean(), auc(E0['gg'][k], Yg), auc(A['gg'], Yg)))
    print('  Goal per fascia (allineata): ' + ' · '.join(f'{a}-{b} {s.sum()}: {100 * A["gg"][s].mean():.1f} -> {100 * Yg[s].mean():.1f}'
          for a, b in ((0, 40), (40, 50), (50, 60), (60, 101)) for s in [(100 * A['gg'] >= a) & (100 * A['gg'] < b)]))
    Pm0, Pma = matrici(lamH[k], lamA[k], rho[k]), matrici(aH, aA, rho[k]); ix = np.arange(k.sum()); h, a = np.minimum(hg[k], 10), np.minimum(ag[k], 10)
    d = -np.log(Pma[ix, h, a]) + np.log(Pm0[ix, h, a]); print(f'  risultato esatto: logloss {-np.log(Pm0[ix, h, a]).mean():.4f} -> {-np.log(Pma[ix, h, a]).mean():.4f} (z {d.mean() / d.std(ddof=1) * math.sqrt(len(d)):+.2f})')

    print('\n=== TERZO TEST: Goal con le sole quote dell 1X2 (matrice del motore inclinata) ===')
    T0 = lamH + lamA; s = dividi(T0, np.log(PC[:, 0] / PC[:, 2]), rho); B = mercati(matrici(T0 * s, T0 * (1 - s), rho))
    print(f'totale identico: scarto sull Over {abs(B["o25"] - E0["o25"]).max():.2e}')
    z, meglio, per = confronto('Goal, matrice inclinata contro motore', E0['gg'], B['gg'], yg, lg)
    print('ESITO:', 'PASSA' if z <= -2 and meglio >= 8 else 'NON PASSA', '(z <= -2 e almeno 8 leghe su 12)')
    for l, v in per.items(): print(f'  {l:17s} {v:+.5f}')

    print('\n=== doppie chance con le quote (calibrazione per fascia) ===')
    for nome, p, yy in (('1X', PC[:, 0] + PC[:, 1], y1 != 2), ('X2', PC[:, 1] + PC[:, 2], y1 != 0), ('12', PC[:, 0] + PC[:, 2], y1 != 1)):
        print(f'  {nome}: ' + ' · '.join(f'{a}-{b} {s.sum()}: {100 * p[s].mean():.1f} -> {100 * yy[s].mean():.1f}'
              for a, b in ((0, 60), (60, 70), (70, 80), (80, 101)) for s in [(100 * p >= a) & (100 * p < b)] if s.sum()))
    c = stima2(X, Yo)
    print('\nQUOTE_OU (su tutte le partite con le quote dell Over): ' + json.dumps([round(float(x), 5) for x in c]))

def stima1(X, y):
    mu, sd = X.mean(0), X.std(0)
    m = LogisticRegression(C=1.0, max_iter=2000).fit((X - mu) / sd, y)
    return m.coef_ / sd, m.intercept_ - (m.coef_ * mu / sd).sum(1)

if __name__ == '__main__':
    main()
