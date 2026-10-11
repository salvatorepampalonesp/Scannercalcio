# Cosa aggiunge il motore al mercato, mercato per mercato (AGENTS.md, Il motore contro il mercato). Solo descrittivo.
#
#   python3 strumenti/motore-mercato.py [--footiqo batch/footiqo]
#
# Su ogni mercato che ha una quota, lo stesso metro:
# - chi sta piu' vicino al vero, motore o mercato (logloss, e il lato piu' probabile: quante volte esce);
# - cosa aggiunge il motore dato il mercato: il mercato ricalibrato contro motore + mercato, stimati fuori lega;
# - quando non sono d'accordo sul lato, chi ha ragione;
# - quanto rende alla quota di chiusura giocare sempre il lato del mercato (la favorita), sempre quello del motore,
#   o il lato del motore solo dove il mercato dice il contrario.
# Il motore e' quello di oggi: matrice di ruolo coi lambda del CSV, col livello dei gol del b63 se il file non lo ha.
# I campioni:
# - le undici leghe coi file principali di football-data, 2023/24-2025/26 (batch48, batch4): 1X2, Over/Under 2.5,
#   handicap asiatico, quote di chiusura AvgC;
# - League One, League Two e Super Lig 2023/24-2025/26 e il 2026/27 di dieci leghe (batch/nuove, batch/2627): gli stessi;
# - i cinque campionati con le quote di chiusura di 1xBet da Footiqo (batch48, batch/2627): Goal, Over 0.5, 1.5, 3.5, 4.5.
import os, sys, re, io, glob, math, collections, importlib.util, warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
warnings.filterwarnings('ignore')
QUI = os.path.dirname(os.path.abspath(__file__)); os.chdir(os.path.join(QUI, '..'))
def mod(n, f):
    s = importlib.util.spec_from_file_location(n, os.path.join(QUI, f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
qm = mod('qm', 'quote-matrice.py'); qg = qm.qg; qb = qm.qb
qh = mod('qh', 'quote-handicap.py'); qgo = mod('qgo', 'quote-goal.py')

RIGA_F = "Ambito: livello dei gol (fattore gia' nei lambda di ruolo)"
LIVELLO = float(re.search(r"window\.GOALS_LEVEL\s*=.*?:\s*([\d.]+);", io.open('scanner.html', encoding='utf-8').read()).group(1))
_HA_F = {}
def ha_fattore(path):
    if path not in _HA_F: _HA_F[path] = RIGA_F in io.open(path, encoding='utf-8-sig').read()
    return _HA_F[path]

def carica(dirs):
    W, b, OU = qm.costanti()
    M, Q = qm.carica(dirs, 'batch/quote')
    # prova di coincidenza sulla matrice del CSV, poi il livello dei gol di oggi
    E0 = qg.mercati(qg.matrici([q['lam'][0] for q in Q], [q['lam'][1] for q in Q], [q['rho'] for q in Q]))
    dev = np.nanmax(abs(100 * E0['o25'] - np.array([q['gol']['Over 2.5'] for q in Q])))
    nf, dove = 0, {os.path.basename(f): f for d in dirs for f in glob.glob(os.path.join(d, '*.csv'))}
    for q in Q:
        if not ha_fattore(dove[q['file']]): q['lam'] = [x * LIVELLO for x in q['lam']]; nf += 1
    print(f'  matrice del motore rifatta dal CSV entro {dev:.3f} punti; livello dei gol {LIVELLO} aggiunto su {nf} partite su {len(Q)}')
    return qm.calcola(Q, W, b, OU)

def zeta(d): d = np.asarray(d, float); return d.mean() / d.std(ddof=1) * math.sqrt(len(d))

def fuori_lega(X, y, lg, w=None):
    w = np.ones(len(y)) if w is None else w; out = np.zeros(len(y))
    for l in set(lg):
        tr, te = lg != l, lg == l
        m = LogisticRegression(penalty=None, max_iter=2000).fit(np.vstack([X[tr], X[tr]]), np.r_[np.ones(tr.sum()), np.zeros(tr.sum())],
                                                                    sample_weight=np.r_[w[tr] * y[tr], w[tr] * (1 - y[tr])])
        out[te] = m.predict_proba(X[te])[:, 1]
    return out

def peso(X, y, w=None):
    # coefficienti su tutte le partite con l'errore standard (informazione di Fisher)
    w = np.ones(len(y)) if w is None else w
    m = LogisticRegression(penalty=None, max_iter=2000).fit(np.vstack([X, X]), np.r_[np.ones(len(y)), np.zeros(len(y))], sample_weight=np.r_[w * y, w * (1 - y)])
    Z = np.column_stack([np.ones(len(y)), X]); p = 1 / (1 + np.exp(-(Z @ np.r_[m.intercept_, m.coef_[0]])))
    H = (Z * (w * p * (1 - p))[:, None]).T @ Z; se = np.sqrt(np.diag(np.linalg.inv(H)))
    return m.coef_[0], se[1:]

def riga(nome, n, ll_m, ll_e, agg, z_agg, meglio, hit_e, hit_m, dis, hd_e, hd_m, roi_m, roi_e, roi_d, peso_e):
    print(f'\n  {nome} ({n} partite)')
    print(f'    logloss: motore {ll_e:.4f}, mercato {ll_m:.4f}  ·  il motore aggiunge al mercato {1000 * agg:+.2f}‰ (z {z_agg:+.2f}, meglio in {meglio})'
          f'  ·  peso del motore dato il mercato {peso_e[0]:+.3f} ±{peso_e[1]:.3f}')
    print(f'    lato piu probabile: esce col motore {100 * hit_e:.1f}%, col mercato {100 * hit_m:.1f}%  ·  in disaccordo nel {100 * dis:.1f}%:'
          f' li ha ragione il motore {100 * hd_e:.1f}%, il mercato {100 * hd_m:.1f}%')
    print(f'    alla chiusura: favorita del mercato sempre {roi_m}, lato del motore sempre {roi_e}, lato del motore dove il mercato dice il contrario {roi_d}')

def roi_txt(r):
    r = np.asarray(r, float)
    return f'{100 * r.mean():+.1f}% ±{200 * r.std(ddof=1) / math.sqrt(len(r)):.1f} ({len(r)})' if len(r) > 1 else 'n/d'

def binario(nome, pe, pm, y, lg, qs, qn, w=None):
    """pe, pm: probabilita' del si' (motore, mercato senza margine); qs, qn: quote di chiusura del si' e del no."""
    k = np.isfinite(pe) & np.isfinite(pm) & np.isfinite(qs) & np.isfinite(qn)
    pe, pm, y, lg, qs, qn = pe[k], pm[k], y[k], lg[k], qs[k], qn[k]
    w = np.ones(len(y)) if w is None else w[k]
    L = lambda p: w * qg.ll(p, y) / w.mean()
    pmr = fuori_lega(qg.logit(pm)[:, None], y, lg, w); pc = fuori_lega(np.column_stack([qg.logit(pm), qg.logit(pe)]), y, lg, w)
    d = L(pc) - L(pmr); per = {l: d[lg == l].mean() for l in sorted(set(lg))}
    c, se = peso(np.column_stack([qg.logit(pm), qg.logit(pe)]), y, w)
    se_, sm = pe > 0.5, pm > 0.5
    hit = lambda s: np.average(np.where(s, y, 1 - y), weights=w)
    dis = se_ != sm
    pay = lambda s: np.where(s, np.where(y > 0.5, qs - 1, -1), np.where(y < 0.5, qn - 1, -1))
    riga(nome, len(y), L(pm).mean(), L(pe).mean(), d.mean(), zeta(d), f'{sum(v < 0 for v in per.values())}/{len(per)}', hit(se_), hit(sm), dis.mean(),
         np.average(np.where(se_, y, 1 - y)[dis], weights=w[dis]) if dis.any() else np.nan,
         np.average(np.where(sm, y, 1 - y)[dis], weights=w[dis]) if dis.any() else np.nan,
         roi_txt(pay(sm)), roi_txt(pay(se_)), roi_txt(pay(se_)[dis]), (c[1], se[1]))

def unoxdue(nome, C, sel=None):
    k = np.ones(len(C['Q']), bool) if sel is None else sel
    P0, PM = C['P0'][k], C['PM'][k]; Q = [q for q, kk in zip(C['Q'], k) if kk]
    out = np.array([q['out'] for q in Q]); lg = C['lega'][k]; qc = np.array([q['qc'] for q in Q])
    lr = lambda P: np.column_stack([np.log(P[:, 0] / P[:, 1]), np.log(P[:, 2] / P[:, 1])])
    ll3 = lambda P: -np.log(np.clip(P[np.arange(len(out)), out], 1e-9, 1))
    def fl(X):
        P = np.zeros((len(out), 3))
        for l in set(lg):
            tr, te = lg != l, lg == l
            m = LogisticRegression(penalty=None, max_iter=3000).fit(X[tr], out[tr]); P[te] = m.predict_proba(X[te])
        return P
    pmr, pc = fl(lr(PM)), fl(np.column_stack([lr(PM), lr(P0)]))
    d = ll3(pc) - ll3(pmr); per = {l: d[lg == l].mean() for l in sorted(set(lg))}
    nx = out != 1; y12 = (out[nx] == 0).astype(float)
    c, se = peso(np.column_stack([np.log(PM[nx, 0] / PM[nx, 2]), np.log(P0[nx, 0] / P0[nx, 2])]), y12)
    pe_, pm_ = P0.argmax(1), PM.argmax(1); dis = pe_ != pm_
    pay = lambda s: np.where(s == out, qc[np.arange(len(out)), s] - 1, -1.0)
    riga(nome, len(out), ll3(PM).mean(), ll3(P0).mean(), d.mean(), zeta(d), f'{sum(v < 0 for v in per.values())}/{len(per)}',
         (pe_ == out).mean(), (pm_ == out).mean(), dis.mean(), (pe_ == out)[dis].mean(), (pm_ == out)[dis].mean(),
         roi_txt(pay(pm_)), roi_txt(pay(pe_)), roi_txt(pay(pe_)[dis]), (c[1], se[1]))
    # la selezione: il 10 / 20 / 30% piu' sicuro per ognuno, ordinando dentro la lega
    fr = []
    for f in (0.1, 0.2, 0.3):
        e = m_ = 0; n = 0
        for l in set(lg):
            i = np.where(lg == l)[0]; t = max(1, int(round(f * len(i))))
            ie = i[np.argsort(-P0[i].max(1))[:t]]; im = i[np.argsort(-PM[i].max(1))[:t]]
            e += (pe_[ie] == out[ie]).sum(); m_ += (pm_[im] == out[im]).sum(); n += t
        fr.append(f'{int(100 * f)}%: motore {100 * e / n:.1f}, mercato {100 * m_ / n:.1f}')
    print('    selezione, il pick piu sicuro: ' + ' · '.join(fr))

def handicap(nome, C):
    rows = []
    for i, q in enumerate(C['Q']):
        a = qh.ah_quote(q['riga'])
        if not a: continue
        h, oh, oa, _ = a
        if abs(round(h * 4) - h * 4) > 1e-6: continue
        d = q['hg'] - q['ag']; s = [qh.esito(d, hh) for hh in qh.sotto(h)]
        wv, lv = sum(x > 0 for x in s), sum(x < 0 for x in s)
        if wv + lv == 0: continue
        # resa per una puntata da 1 divisa sulle due mezze linee, casa e trasferta
        rc = sum(((oh - 1) if x > 0 else (-1 if x < 0 else 0)) / 2 for x in s)
        ra = sum(((oa - 1) if x < 0 else (-1 if x > 0 else 0)) / 2 for x in s)
        rows.append((i, h, (1 / oh) / (1 / oh + 1 / oa), wv / (wv + lv), wv + lv, q['lega'], rc, ra))
    idx = np.array([r[0] for r in rows]); h = np.array([r[1] for r in rows])
    GD = qh.gd_dist(C['E'][idx]); pe = np.array([qh.p_imp(GD[j:j + 1], h[j])[0] for j in range(len(rows))])
    pm = np.array([r[2] for r in rows]); y = np.array([r[3] for r in rows]); wt = np.array([r[4] for r in rows], float)
    lg = np.array([r[5] for r in rows]); rc = np.array([r[6] for r in rows]); ra = np.array([r[7] for r in rows])
    L = lambda p: wt * qg.ll(p, y) / wt.mean()
    pmr = fuori_lega(qg.logit(pm)[:, None], y, lg, wt); pc = fuori_lega(np.column_stack([qg.logit(pm), qg.logit(pe)]), y, lg, wt)
    d = L(pc) - L(pmr); per = {l: d[lg == l].mean() for l in sorted(set(lg))}
    c, se = peso(np.column_stack([qg.logit(pm), qg.logit(pe)]), y, wt)
    se_, sm = pe > 0.5, pm > 0.5; dis = se_ != sm
    hit = lambda s, k: np.average(np.where(s, y, 1 - y)[k], weights=wt[k])
    pay = lambda s: np.where(s, rc, ra)
    tutte = np.ones(len(y), bool)
    riga(nome, len(y), L(pm).mean(), L(pe).mean(), d.mean(), zeta(d), f'{sum(v < 0 for v in per.values())}/{len(per)}',
         hit(se_, tutte), hit(sm, tutte), dis.mean(), hit(se_, dis), hit(sm, dis),
         roi_txt(pay(sm)), roi_txt(pay(se_)), roi_txt(pay(se_)[dis]), (c[1], se[1]))

def campione(nome, dirs):
    print(f'\n===== {nome} =====')
    C = carica(dirs); Q = C['Q']
    unoxdue('1X2', C)
    ou = np.array([qg.ou(q['riga'], ['AvgC', 'PC', 'B365C'])[0] for q in Q], float)
    y = ((C['hg'] + C['ag']) > 2.5).astype(float)
    binario('Over/Under 2.5', C['E0']['o25'], C['pm'], y, C['lega'], ou[:, 0], ou[:, 1])
    handicap('Handicap asiatico, alla linea del mercato', C)
    return C

def footiqo(cart):
    print('\n===== i cinque campionati, quote di chiusura di 1xBet (Footiqo) =====')
    C = carica(['batch48', 'batch/2627'])
    k5 = np.array([q['lega'] in qgo.LEGHE.values() for q in C['Q']])
    Q = [q for q, kk in zip(C['Q'], k5) if kk]
    A = qgo.aggancia(Q, qgo.footiqo(cart)); ok = np.array([a is not None for a in A])
    print(f'  partite dei cinque campionati {len(Q)}, agganciate a Footiqo {ok.sum()}')
    sel = np.where(k5)[0][ok]; q1 = [a['q'] for a in A if a is not None]
    hg, ag, lg = C['hg'][sel], C['ag'][sel], C['lega'][sel]; tot = hg + ag
    E0 = {kk: v[sel] for kk, v in C['E0'].items()}
    Pe = C['E'][sel]; o05 = 1 - Pe[:, 0, 0]; o45 = 1 - sum(Pe[:, x, yy] for x in range(5) for yy in range(5 - x))
    for nome, pe, si, no, y in (('Goal/NoGoal', E0['gg'], 'BTTSY', 'BTTSN', (hg > 0) & (ag > 0)),
                                ('Over/Under 0.5', o05, 'O05', 'U05', tot > 0), ('Over/Under 1.5', E0['o15'], 'O15', 'U15', tot > 1),
                                ('Over/Under 2.5', E0['o25'], 'O25', 'U25', tot > 2), ('Over/Under 3.5', E0['o35'], 'O35', 'U35', tot > 3),
                                ('Over/Under 4.5', o45, 'O45', 'U45', tot > 4)):
        qs = np.array([x[si] or np.nan for x in q1], float); qn = np.array([x[no] or np.nan for x in q1], float)
        binario(nome, pe, (1 / qs) / (1 / qs + 1 / qn), y.astype(float), lg, qs, qn)

def main():
    a = sys.argv[1:]; cart = 'batch/footiqo'
    if '--footiqo' in a: cart = a[a.index('--footiqo') + 1]
    campione('le undici leghe coi file principali, 2023/24-2025/26, quote di chiusura medie', ['batch48', 'batch4'])
    campione('League One, League Two, Super Lig e il 2026/27, quote di chiusura medie', ['batch/nuove', 'batch/2627'])
    footiqo(cart)

if __name__ == '__main__':
    main()
