# L'Elo, l'avviso di sorpresa e il tabellone delle partite ALTO contro le quote (AGENTS.md, L'avviso di sorpresa,
# «Contro le quote e nel tabellone»). Solo descrittivo.
#
#   python3 strumenti/sorpresa-quote.py batch48 batch4 --tutte batch/2627 batch/nuove batch/livello
#
# Con le quote di chiusura delle dodici leghe (batch48, batch4): quanto Elo e mercato vanno d'accordo e se l'Elo
# aggiunge qualcosa al mercato; l'avviso di sorpresa (come lo calcola lo Scanner, SORPRESA_TAB letta da
# scanner.html) contro le quote; il tabellone con le quote nelle partite ALTO. Su tutte le leghe dei batch
# (anche --tutte): il tabellone del motore per livello di sorpresa, coi mercati gol rifatti col livello dei gol
# del b63 (i CSV sono di motori precedenti), e la resa delle proposte dalla parte del favorito e dello sfavorito.
# Dal b70 anche la tabella del rischio sorpresa con le quote (SORPRESA_QUOTE_TAB): per fascia dello sfavorito con
# le quote (QUOTE_COMB letta da scanner.html, quote di chiusura), quante volte vincono sfavorito, pareggio e favorito.
import os, re, sys, glob, math, collections, importlib.util
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
DIR = os.path.dirname(os.path.abspath(__file__))
def _mod(nome, f):
    s = importlib.util.spec_from_file_location(nome, os.path.join(DIR, f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
qg = _mod('qg', 'quote-gol.py'); qb = qg.qb
GOALS_LEVEL = 1.051
ORD = ['p1', 'pX', 'p2', 'p1X', 'pX2', 'p12', 'pOv', 'pUn', 'pGG', 'pNG', 'cor9.5', 'sot8.5', 'yel3.5']
sig = lambda x: 1 / (1 + np.exp(-x))
def ms(x): x = np.array(x, float); return (x.mean(), 2 * x.std(ddof=1) / math.sqrt(len(x)), len(x)) if len(x) > 1 else (float('nan'), 0.0, len(x))
fmt = lambda t: f'{t[0]:+5.1f} ±{t[1]:4.1f} ({t[2]})'

def tab_sorpresa():
    s = open(os.path.join(DIR, '..', 'scanner.html'), encoding='utf-8').read()
    blocco = s[s.index('const SORPRESA_TAB'):]; blocco = blocco[:blocco.index('] };')]
    num = lambda t: None if t == 'null' else [float(v) for v in t.strip('[]').split(',')]
    return [(int(m.group(1)), num(m.group(2)), num(m.group(3)), num(m.group(4))) for m in
            re.finditer(r'da: (\d+), tutte: (\[[^\]]*\]|null), accordo: (\[[^\]]*\]|null), disaccordo: (\[[^\]]*\]|null)', blocco)]
TAB = tab_sorpresa()
def livello(m):
    # rischioSorpresa dello Scanner
    p1, pX, p2 = m['p']; pU = min(p1, p2) / (p1 + pX + p2); i = max(j for j, t in enumerate(TAB) if 100 * pU >= t[0])
    dis = (m['lgModel'] > 0) != (m['lgElo'] > 0); c = TAB[i][3] if dis else TAB[i][2]
    if c is None or c[0] < 150: c = TAB[i][1]
    return 'alto' if c[1] >= 33 else ('medio' if c[1] >= 25 else 'basso')

def quote_comb():
    s = open(os.path.join(DIR, '..', 'scanner.html'), encoding='utf-8').read()
    b = s[s.index('const QUOTE_COMB'):]; b = b[:b.index('};')]
    W = [[float(v) for v in r.split(',')] for r in re.findall(r'\[(-?[\d.]+(?:, -?[\d.]+){3})\]', b[:b.index('b:')])]
    B = [float(v) for v in re.search(r'b: \[([^\]]*)\]', b).group(1).split(',')]
    t = s[s.index('const SORPRESA_QUOTE_TAB'):]; t = t[:t.index('] };')]
    T = [[float(v) for v in m.split(',')] for m in re.findall(r'tutte: \[([^\]]*)\]', t)]
    return np.array(W), np.array(B), T

def leggi(dirs):
    M = list({m['id']: m for d in dirs for f in sorted(glob.glob(os.path.join(d, '*.csv'))) for m in qb.leggi_csv(f)}.values())
    return [m for m in M if m['tab'] and None not in m['p'] and m['lgModel'] is not None and m['lgElo'] is not None]

def cieca_di(M):
    c = collections.defaultdict(list)
    for m in M:
        for v in m['tab']:
            if v['hit'] is not None: c[(m['file'], v['key'])].append(v['hit'])
    return {k: sum(v) / len(v) for k, v in c.items()}

def ordina(T):
    for v in T: v['e'] = None if v['b'] is None else 100 * (v['p'] - v['b'])
    return sorted(T, key=lambda v: (-(v['e'] if v['e'] is not None else -1e9), ORD.index(v['key'])))
verd = lambda e: None if e is None else ('FORTE' if e >= 20 else 'GIOCABILE' if e >= 10 else 'MARGINALE' if e >= 5 else None)
def chiavi(m, lato):
    sf = 0 if m['p'][0] < m['p'][2] else 2
    return {'fav': {'p2' if sf == 0 else 'p1', 'pX2' if sf == 0 else 'p1X'}, 'sfav': {'p1' if sf == 0 else 'p2', 'p1X' if sf == 0 else 'pX2', 'pX'},
            'dc_sfav': {'p1X' if sf == 0 else 'pX2'}, 'sfav1': {'p1' if sf == 0 else 'p2'}}[lato]

def elo_e_sorpresa(Q):
    y = np.array([q['out'] for q in Q]); lg = np.array([q['lega'] for q in Q])
    P0 = np.array([q['p'] for q in Q]); P0 /= P0.sum(1, keepdims=True)
    Qc = np.array([q['qc'] for q in Q]); PM = (1 / Qc) / (1 / Qc).sum(1, keepdims=True)
    E = np.array([q['lgElo'] for q in Q]); Mo = np.array([q['lgModel'] for q in Q]); mk = np.log(PM[:, 0] / PM[:, 2]); mo = np.log(P0[:, 0] / P0[:, 2])
    r = lambda a, b: np.corrcoef(a, b)[0, 1]; nd = y != 1; yy = (y[nd] == 0).astype(int); L = lg[nd]
    print(f'=== 1. Elo e quote ({len(Q)} partite) ===')
    print(f'  correlazione col log(p1/p2) del mercato: Elo {r(E, mk):.3f} (R2 {r(E, mk) ** 2:.3f}), modello {r(Mo, mk):.3f}, motore {r(mo, mk):.3f}; '
          f'per lega l Elo da {min(r(E[lg == l], mk[lg == l]) for l in set(lg)):.3f} a {max(r(E[lg == l], mk[lg == l]) for l in set(lg)):.3f}')
    acc = np.sign(E) == np.sign(mk); favM = np.where(mk > 0, y == 0, y == 2)
    print(f'  stesso favorito {100 * acc.mean():.1f}%; in disaccordo ({(~acc).sum()} partite) vince il favorito del mercato il {100 * favM[~acc & nd].mean():.1f}% delle partite senza pari')
    pf = np.where(mk > 0, PM[:, 0], PM[:, 2]); dv = favM - pf
    print(f'  a pari probabilita del mercato il favorito vince sopra il previsto: Elo d accordo {100 * dv[acc].mean():+.2f} ±{200 * dv[acc].std() / math.sqrt(acc.sum()):.2f}, in disaccordo {100 * dv[~acc].mean():+.2f} ±{200 * dv[~acc].std() / math.sqrt((~acc).sum()):.2f}')
    print(f'  AUC 1 contro 2: mercato {roc_auc_score(yy, mk[nd]):.3f}, Elo {roc_auc_score(yy, E[nd]):.3f}')
    def lolo(Fx):
        p = np.zeros(nd.sum())
        for l in sorted(set(L)):
            te = L == l; p[te] = LogisticRegression(C=1e6, max_iter=1000).fit(Fx[~te], yy[~te]).predict_proba(Fx[te])[:, 1]
        return p
    lp = lambda p: -(yy * np.log(p) + (1 - yy) * np.log(1 - p)); F2 = np.column_stack([mk[nd], E[nd]])
    d = lp(lolo(F2)) - lp(lolo(mk[nd][:, None]))
    Xc = np.column_stack([np.ones(len(yy)), F2]); m2 = LogisticRegression(C=1e6).fit(F2, yy); p = m2.predict_proba(F2)[:, 1]
    cov = np.linalg.inv(Xc.T @ (Xc * (p * (1 - p))[:, None]))
    neg = sum(LogisticRegression(C=1e6).fit(F2[L == l], yy[L == l]).coef_[0][1] < 0 for l in sorted(set(L)))
    print(f'  dato il mercato l Elo pesa {m2.coef_[0][1]:+.3f} ±{math.sqrt(cov[2, 2]):.3f}, negativo in {neg} leghe su {len(set(L))}; '
          f'fuori lega mercato + Elo contro mercato ricalibrato {1000 * d.mean():+.2f} per mille (z {d.mean() / d.std(ddof=1) * math.sqrt(len(d)):+.2f})')
    pX = PM[:, 1]; pe1, pe2 = sig(E) * (1 - pX), (1 - sig(E)) * (1 - pX)
    g1, g2 = 100 * (pe1 - PM[:, 0]), 100 * (pe2 - PM[:, 2]); lato = np.where(g1 >= g2, 0, 2); gap = np.maximum(g1, g2)
    quota = np.where(lato == 0, Qc[:, 0], Qc[:, 2])
    print('  giocare 1 o 2 dove l Elo da piu del mercato, quota media di chiusura: ' + ' · '.join(
        f'{t}+ punti {(gap >= t).sum()} giocate {100 * np.where(y == lato, quota - 1, -1)[gap >= t].mean():+.1f}%' for t in (3, 5, 8, 12)))
    print(f'\n=== 2. l avviso di sorpresa contro le quote ===')
    liv = np.array([livello(q) for q in Q]); sf = np.where(P0[:, 0] < P0[:, 2], 0, 2); ps = np.where(sf == 0, P0[:, 0], P0[:, 2])
    X = np.column_stack([np.log(PM[:, 0] / PM[:, 1]), np.log(PM[:, 2] / PM[:, 1])]); PR = np.zeros_like(PM)
    for l in sorted(set(lg)):
        te = lg == l; PR[te] = LogisticRegression(C=1e6, max_iter=2000).fit(X[~te], y[~te]).predict_proba(X[te])
    vs = (y == sf).astype(float); pr = np.where(sf == 0, PR[:, 0], PR[:, 2]); pm = np.where(sf == 0, PM[:, 0], PM[:, 2]); q = np.where(sf == 0, Qc[:, 0], Qc[:, 2])
    for L_ in ('alto', 'medio', 'basso'):
        k = liv == L_; d0, d1 = vs[k] - ps[k], vs[k] - pr[k]; roi = np.where(vs[k] == 1, q[k] - 1, -1)
        print(f'  {L_:5s} {k.sum():5d} ({100 * k.mean():4.1f}%) · lo sfavorito del motore vince {100 * vs[k].mean():.1f}%: motore {100 * ps[k].mean():.1f} ({100 * d0.mean():+.2f} ±{200 * d0.std() / math.sqrt(k.sum()):.2f}), '
              f'mercato ricalibrato {100 * pr[k].mean():.1f} ({100 * d1.mean():+.2f} ±{200 * d1.std() / math.sqrt(k.sum()):.2f}) · pari {100 * (y[k] == 1).mean():.1f}% · '
              f'giocarlo alla chiusura {100 * roi.mean():+.1f}% ±{200 * roi.std() / math.sqrt(k.sum()):.1f} · il mercato ha l altro favorito nel {100 * (np.where(PM[k, 0] < PM[k, 2], 0, 2) != sf[k]).mean():.0f}%')
    pk, pp, hit = P0.argmax(1), P0.max(1), (y == P0.argmax(1))
    for a, b in ((0, .45), (.45, .50)):
        k = (pp >= a) & (pp < b) & (liv == 'alto'); k2 = (pp >= a) & (pp < b) & (liv != 'alto')
        print(f'  pick del motore {int(100 * a)}-{int(100 * b)}%: ALTO {k.sum()} esce {100 * hit[k].mean():.1f} (previsto {100 * pp[k].mean():.1f}) · altre {k2.sum()} esce {100 * hit[k2].mean():.1f} (previsto {100 * pp[k2].mean():.1f})')
    dis = np.sign(Mo) != np.sign(E); sd_ = (np.sign(Mo - E) * dis)[nd]
    d = lp(lolo(np.column_stack([mk[nd], sd_]))) - lp(lolo(mk[nd][:, None])); per = {l: d[L == l].mean() for l in set(L)}
    print(f'  1 contro 2 dato il mercato, col segnale del disaccordo: {1000 * d.mean():+.2f} per mille (z {d.mean() / d.std(ddof=1) * math.sqrt(len(d)):+.2f}), meglio in {sum(v < 0 for v in per.values())}/{len(per)} leghe')

def sorpresa_con_le_quote(Q):
    W, B, Tsc = quote_comb(); FAS = [0, 15, 20, 25, 30]
    y = np.array([q['out'] for q in Q]); P0 = np.array([q['p'] for q in Q], float); lg = np.array([q['lega'] for q in Q])
    Qc = np.array([q['qc'] for q in Q]); PM = (1 / Qc) / (1 / Qc).sum(1, keepdims=True)
    F = np.column_stack([np.log(P0[:, 0] / P0[:, 1]), np.log(P0[:, 2] / P0[:, 1]), np.log(PM[:, 0] / PM[:, 1]), np.log(PM[:, 2] / PM[:, 1])])
    Z = F @ W.T + B; E = np.exp(Z - Z.max(1, keepdims=True)); PC = E / E.sum(1, keepdims=True)
    PF = np.zeros_like(PC); mu, sd = F.mean(0), F.std(0)
    for l in sorted(set(lg)):
        te = lg == l; PF[te] = LogisticRegression(C=1.0, max_iter=3000).fit((F[~te] - mu) / sd, y[~te]).predict_proba((F[te] - mu) / sd)
    dis = np.sign([q['lgModel'] for q in Q]) != np.sign([q['lgElo'] for q in Q])
    def tab(P, k):
        sf = np.where(P[:, 0] < P[:, 2], 0, 2); pu = np.minimum(P[:, 0], P[:, 2]) / P.sum(1); out = []
        for i, a in enumerate(FAS):
            kk = k & (100 * pu >= a) & (100 * pu < (FAS[i + 1] if i + 1 < len(FAS) else 101))
            out.append([int(kk.sum()), round(100 * (y == sf)[kk].mean(), 1), round(100 * (y == 1)[kk].mean(), 1), round(100 * (y == 2 - sf)[kk].mean(), 1), 100 * pu[kk].mean()])
        return out
    tutte = np.ones(len(y), bool); T = tab(PC, tutte)
    print(f'\n=== 5. il rischio sorpresa con le quote ({len(Q)} partite, quote di chiusura) ===')
    for i, a in enumerate(FAS):
        f = lambda r: f'{r[0]:5d} sfavorito {r[1]:5.1f} (previsto {r[4]:5.1f})'
        print(f'  da {a:2d}%: {f(T[i])} pari {T[i][2]:5.1f} favorito {T[i][3]:5.1f} · fuori lega {f(tab(PF, tutte)[i])} · disaccordo {f(tab(PC, dis)[i])} · accordo {f(tab(PC, ~dis)[i])}')
    print('  SORPRESA_QUOTE_TAB di scanner.html ' + ('coincide' if [r[:4] for r in T] == [[int(t[0])] + t[1:] for t in Tsc] else 'NON COINCIDE: ' + str([r[:4] for r in T])))
    liv = np.array([livello(q) for q in Q]); sfM = np.where(P0[:, 0] < P0[:, 2], 0, 2); sfC = np.where(PC[:, 0] < PC[:, 2], 0, 2)
    for L_ in ('alto', 'medio', 'basso'):
        k = liv == L_
        print(f'  riquadro del motore {L_:5s} {k.sum():5d}: con le quote il suo sfavorito e il favorito nel {100 * (sfM != sfC)[k].mean():.1f}%, il pick con le quote nel {100 * (PC.argmax(1) == sfM)[k].mean():.1f}%')

def tabellone_motore(M):
    # mercati gol del tabellone rifatti col livello dei gol del b63 (prova di coincidenza sulla matrice del CSV)
    M = [m for m in M if None not in m['lam'] and m['rho'] is not None]
    LH, LA, RHO = (np.array([m['lam'][0] for m in M]), np.array([m['lam'][1] for m in M]), np.array([m['rho'] for m in M]))
    m0 = qg.mercati(qg.matrici(LH, LA, RHO)); m1 = qg.mercati(qg.matrici(LH * GOALS_LEVEL, LA * GOALS_LEVEL, RHO))
    print(f'\n=== 3. il tabellone del motore per livello di sorpresa ({len(M)} partite) ===\n  prova di coincidenza della matrice: Over 2.5 entro '
          f'{100 * np.abs(m0["o25"] - np.array([m["gol"]["Over 2.5"] for m in M]) / 100).max():.3f} punti')
    for i, m in enumerate(M):
        nuovo = {'pOv': m1['o25'][i], 'pUn': 1 - m1['o25'][i], 'pGG': m1['gg'][i], 'pNG': 1 - m1['gg'][i]}
        m['T'] = ordina([dict(v, p=round(float(nuovo.get(v['key'], v['p'])), 3)) for v in m['tab']]); m['liv'] = livello(m)
    cieca = cieca_di(M); g = lambda m, v: None if v['hit'] is None else 100 * (v['hit'] - cieca[(m['file'], v['key'])])
    lega = lambda m: re.match(r'Backtest_V97_(.+)_\d{4}', m['file']).group(1)
    for L_ in ('alto', 'medio', 'basso'):
        R = [m for m in M if m['liv'] == L_]
        prima = [g(m, m['T'][0]) for m in R if g(m, m['T'][0]) is not None]
        tre = [g(m, v) for m in R for v in [v for v in m['T'] if verd(v['e'])][:3] if g(m, v) is not None]
        fg = np.mean([any(v['e'] is not None and v['e'] >= 10 for v in m['T']) for m in R])
        print(f'  {L_:5s} {len(R):5d} ({100 * len(R) / len(M):.1f}%) · la prima proposta rende {fmt(ms(prima))} · le prime tre con verdetto {fmt(ms(tre))} · almeno una FORTE o GIOCABILE {100 * fg:.0f}%')
        for lato in ('fav', 'sfav'):
            d = [g(m, v) - v['e'] for m in R for v in m['T'] if v['key'] in chiavi(m, lato) and verd(v['e']) and v['hit'] is not None]
            print(f'        1X2 dalla parte del {"favorito" if lato == "fav" else "sfavorito e X"}: rende meno lo scarto promesso {fmt(ms(d))}')
    A = [m for m in M if m['liv'] == 'alto']
    giocab = [(g(m, v), v['e']) for m in A for v in m['T'] if verd(v['e']) == 'GIOCABILE' and v['key'] in ORD[:6] and v['hit'] is not None]
    print(f'  ALTO, 1X2 GIOCABILE: rende {fmt(ms([x[0] for x in giocab]))}, scarto medio {np.mean([x[1] for x in giocab]):.1f}')
    per = collections.defaultdict(list)
    for m in A:
        for v in m['T']:
            if v['key'] in chiavi(m, 'fav') and verd(v['e']) and v['hit'] is not None: per[lega(m)].append(g(m, v) - v['e'])
    print(f'  ALTO, parte del favorito sotto lo scarto promesso in {sum(np.mean(x) < 0 for x in per.values())} leghe su {len(per)}')
    salta = lambda m: [v for v in m['T'] if v['key'] not in chiavi(m, 'fav')]
    d = np.array([g(m, salta(m)[0]) - g(m, m['T'][0]) for m in A if g(m, salta(m)[0]) is not None and g(m, m['T'][0]) is not None])
    perl = collections.defaultdict(list)
    for m in A:
        if g(m, salta(m)[0]) is not None and g(m, m['T'][0]) is not None: perl[lega(m)].append(g(m, salta(m)[0]) - g(m, m['T'][0]))
    print(f'  ALTO, saltando le proposte dalla parte del favorito: prima proposta {d.mean():+.2f} ±{2 * d.std(ddof=1) / math.sqrt(len(d)):.2f}, meglio in {sum(np.mean(x) > 0 for x in perl.values())} leghe su {len(perl)}')
    for lato, nome in (('dc_sfav', 'doppia chance dello sfavorito'), ('sfav1', 'sfavorito secco')):
        tutte, prop, ed, prev, reali = [], [], [], [], []
        for m in A:
            v = next((v for v in m['T'] if v['key'] in chiavi(m, lato)), None)
            if v is None or v['hit'] is None: continue
            tutte.append(g(m, v)); prev.append(100 * v['p']); reali.append(100 * v['hit'])
            if verd(v['e']): prop.append(g(m, v)); ed.append(v['e'])
        print(f'  ALTO, {nome}: esce {np.mean(reali):.1f}% (previsto {np.mean(prev):.1f}), sempre giocata {fmt(ms(tutte))}; proposta in {100 * len(prop) / len(tutte):.0f}%: rende {fmt(ms(prop))}, scarto medio {np.mean(ed):.1f}')

def tabellone_quote(M, Q):
    C = qg.con_quote(Q); k_ou = np.cumsum(C['k']) - 1; cieca = cieca_di(M)
    g = lambda m, v: None if v['hit'] is None else 100 * (v['hit'] - cieca[(m['file'], v['key'])])
    print('\n=== 4. il tabellone con le quote per livello di sorpresa (dodici leghe) ===')
    R = []
    for i, m in enumerate(Q):
        if m['lgModel'] is None or m['lgElo'] is None: continue
        P = C['PC'][i]; q = {'p1': P[0], 'pX': P[1], 'p2': P[2], 'p1X': P[0] + P[1], 'pX2': P[1] + P[2], 'p12': P[0] + P[2]}
        if C['k'][i]: j = k_ou[i]; q |= {'pOv': C['pc'][j], 'pUn': 1 - C['pc'][j], 'pGG': C['A']['gg'][j], 'pNG': 1 - C['A']['gg'][j]}
        R.append((m, ordina([dict(v, p=q.get(v['key'], v['p'])) for v in m['tab']]), ordina([dict(v) for v in m['tab']]), livello(m)))
    for L_ in ('alto', 'medio', 'basso'):
        S = [r for r in R if r[3] == L_]
        pq = [g(m, T[0]) for m, T, _, _ in S if g(m, T[0]) is not None]; pmot = [g(m, T[0]) for m, _, T, _ in S if g(m, T[0]) is not None]
        fq = [g(m, v) - v['e'] for m, T, _, _ in S for v in T if v['key'] in chiavi(m, 'fav') and verd(v['e']) and v['hit'] is not None]
        fm = [g(m, v) - v['e'] for m, _, T, _ in S for v in T if v['key'] in chiavi(m, 'fav') and verd(v['e']) and v['hit'] is not None]
        print(f'  {L_:5s} {len(S):5d} · prima proposta motore {fmt(ms(pmot))} -> con le quote {fmt(ms(pq))} · '
              f'parte del favorito, resa meno scarto: motore {fmt(ms(fm))}, con le quote {fmt(ms(fq))}')

def main():
    args = sys.argv[1:]; tutte = []
    if '--tutte' in args: i = args.index('--tutte'); tutte = args[i + 1:]; args = args[:i]
    M12 = leggi(args); Q = [q for q in qb.aggancia(M12, qb.quote_fd('batch/quote')) if q['lgModel'] is not None and q['lgElo'] is not None]
    elo_e_sorpresa(Q)
    sorpresa_con_le_quote(Q)
    tabellone_motore(leggi(args + tutte))
    tabellone_quote(M12, Q)

if __name__ == '__main__':
    main()
