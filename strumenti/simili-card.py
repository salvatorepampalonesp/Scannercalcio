# La card «contro squadre simili» dello Scanner rifatta da batch/stile (AGENTS.md, Il confronto contro squadre simili,
# «Le 30 partite invece della stessa sede, e altre metriche»).
#
#   python3 strumenti/simili-card.py "ITA:Serie A=2024/2025,2025/2026,2026/2027" ...   # dopo simili.py --scarica
#
# Copia di getSimilarMatches: per ogni squadra le ultime 30 partite di lega entro 500 giorni (solo le partite con
# tutte e 30), il campione (la stessa sede come lo Scanner, oppure tutte e 30), la distanza pesata dall'avversario di
# oggi con la deviazione standard del campione, la copertura almeno 0.6, il nucleo largo quanto la distanza mediana
# (almeno 0.35), l'emivita di 106 giorni. Il bersaglio e' quello dello Scanner: la media dei valori dell'avversario di
# oggi nelle sue ultime 30, ristretta verso la sua sede con k = 5. «Sede corretta»: i punti di ogni partita spostati
# dalla media della lega in quella sede alla media nella sede di oggi. Il numero confrontato e' quello della card, i
# punti a partita contro le simili, casa meno trasferta; accanto i punti a partita semplici dello stesso campione.
# Le varianti cambiano cosa descrive l'avversario di allora:
#   motore              i numeri di quella partita, come lo Scanner (tocchi in area, ingressi nell'ultimo terzo e
#                       recuperi entro 5" sono quelli della squadra stessa: KNN_DIMS li legge da own)
#   3 corrette          le stesse 11, coi tre numeri presi dall'avversario
#   profilo             il profilo dell'avversario prima di quella partita (simili.profili): serve la sua storia
#   forza, stile        lo stesso profilo, solo npxg e npxga, o le 12 di stile
#   rating, Elo         il rating dalle quote passate o l'Elo dell'avversario prima di quella partita
#   corrette + Elo      la card del b90 (similiCard): le 11 corrette e l'Elo dell'avversario prima di quella partita
import sys, os, math, collections, datetime as dt, importlib.util, warnings
import numpy as np
warnings.filterwarnings('ignore')
RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_sp = importlib.util.spec_from_file_location('simili', os.path.join(RADICE, 'strumenti', 'simili.py'))
S = importlib.util.module_from_spec(_sp); _argv = sys.argv; sys.argv = ['x']; _sp.loader.exec_module(S); sys.argv = _argv
rq = S.rq
_leggi, _fdc = rq.leggi, {}
def _leggi_una_volta(dv):
    if dv not in _fdc: _fdc[dv] = _leggi(dv)
    return _fdc[dv]
rq.leggi = _leggi_una_volta   # carica() e questo file devono vedere gli stessi oggetti di football-data

def rating_prima(fd):
    # rating dalle quote passate (rq.rating_quote) ed Elo (rq.elo) di casa e trasferta prima di ogni partita
    R, H, cur = {}, rq.H0, None; st = rq.squadre_per_stagione(fd)
    for d, day in rq.per_giorno(fd).items():
        s = day[0]['stag']
        if s != cur:
            if cur is not None:
                usc = [R[t] for t in st[cur] if t not in st[s] and t in R]
                lev = sum(usc) / len(usc) if usc else (min(R.values()) if R else 0.0)
                for t in st[s]: R.setdefault(t, lev)
                mu = np.mean([R[t] for t in st[s]])
                for t in st[s]: R[t] = mu + rq.REG * (R[t] - mu)
            cur = s
        for m in day:
            for t in (m['H'], m['A']): R.setdefault(t, 0.0)
            m['RH'], m['RA'] = R[m['H']], R[m['A']]
        for m in day:
            if not m['pc']: continue
            e = rq.lo(m['pc']) - (m['RH'] - m['RA'] + H)
            R[m['H']] += rq.K * e; R[m['A']] -= rq.K * e; H += rq.KH * e
    E, n, cur, hw, aw = {}, collections.Counter(), None, 0, 0
    for d, day in rq.per_giorno(fd).items():
        s = day[0]['stag']
        if s != cur and cur is not None:
            usc = [E[t] for t in st[cur] if t not in st[s] and t in E]; lev = sum(usc) / len(usc) if usc else 1500
            for t in st[s]: E.setdefault(t, lev)
        cur = s; hfa = min(100, max(30, 400 * math.log10(max(hw, 1) / max(aw, 1)))) if hw + aw >= 50 else 65
        for m in day:
            for t in (m['H'], m['A']): E.setdefault(t, 1500)
            m['EH'], m['EA'] = E[m['H']], E[m['A']]
        for m in day:
            if m['hg'] is None: continue
            dr = E[m['H']] - E[m['A']] + hfa; ex = 1 / (1 + 10 ** (-dr / 400)); sc = 1 if m['hg'] > m['ag'] else (0.5 if m['hg'] == m['ag'] else 0)
            gd = abs(m['hg'] - m['ag']); mult = 1 if gd <= 1 else (1.5 if gd == 2 else (11 + gd) / 8)
            for t, sg in ((m['H'], 1), (m['A'], -1)): E[t] += sg * (30 if n[t] < 15 else 20) * mult * (sc - ex); n[t] += 1
            if m['hg'] > m['ag']: hw += 1
            elif m['hg'] < m['ag']: aw += 1

# KNN_DIMS dello Scanner: chiave, peso, da dove la legge (oN, oNa: npxg e npxga dell'avversario; own: la squadra stessa)
KNN = [('npxg', 1.5, 'oN'), ('npxga', 1.5, 'oNa'), ('field_tilt', 1.2, 'o'), ('avg_def_x', 1.2, 'o'), ('poss', 1.0, 'o'),
       ('ppda', 1.0, 'o'), ('tch_box', 1.1, 'own'), ('f3_entries', 0.9, 'own'), ('cp_regains', 0.7, 'own'), ('seq_time', 0.6, 'o'), ('avg_x', 0.8, 'o')]
STILE = [(k, 1.0, 'o') for k in S.STILE]
FORZA = [('npxg', 1.0, 'oN'), ('npxga', 1.0, 'oNa')]
VAR = [('motore, stessa sede (oggi)', KNN, 'motore', 'sede', False), ('motore, 30', KNN, 'motore', 'tutte', False),
       ('motore, 30 sede corretta', KNN, 'motore', 'tutte', True), ('3 corrette, stessa sede', KNN, 'corrette', 'sede', False),
       ('3 corrette, 30 sede corretta', KNN, 'corrette', 'tutte', True), ('profilo, 30 sede corretta', KNN, 'profilo', 'tutte', True),
       ('forza, 30 sede corretta', FORZA, 'profilo', 'tutte', True), ('stile, 30 sede corretta', STILE, 'profilo', 'tutte', True),
       ('rating dalle quote, 30 sede corretta', [('rat', 1.0, 'o')], 'rating', 'tutte', True),
       ('Elo, stessa sede', [('elo', 1.0, 'o')], 'elo', 'sede', False), ('Elo, 30 sede corretta', [('elo', 1.0, 'o')], 'elo', 'tutte', True)]
KNN3 = [(k, w, 'o' if m == 'own' else m) for k, w, m in KNN]
VAR += [(f'corrette + Elo {w:g}{" (b90)" if w == 1.5 else ""}', KNN3 + [('elo', w, 'elo')], 'mix', 'tutte', True) for w in (1.5, 3.0, 6.0, 12.0)]

def valore(x, k, modo, prof):
    own, opp = x[1], x[2]
    if modo == 'elo': return x[9]
    if prof == 'profilo': return (x[5] or {}).get(k)
    if prof == 'rating': return x[8]
    if prof == 'elo': return x[9]
    if k == 'npxg': return opp.get('npxg')
    if k == 'npxga': return own.get('npxg')
    return own.get(k) if (modo == 'own' and prof == 'motore') else opp.get(k)

def bersaglio(hist_o, d, sede_o, dims):
    # come target in getSimilarMatches: _shrunkMean dei valori dell'avversario di oggi, sede e ultime 30, k = 5
    h = [x for x in hist_o if x[0] < d and (d - x[0]).days <= 500][-30:]; t = {}
    for k, _, modo in dims:
        if modo == 'elo': continue
        val = (lambda x: x[2].get('npxg')) if k == 'npxga' else (lambda x: x[1].get(k))
        ro = [val(x) for x in h if x[7] == sede_o and val(x) is not None]; ov = [val(x) for x in h if val(x) is not None]
        if ov: mo = float(np.mean(ov)); t[k] = (len(ro) * np.mean(ro) + 5 * mo) / (len(ro) + 5) if ro else mo
    return t

def card(hist, d, sede, target, dims, campione, prof, medie):
    h = [x for x in hist if x[0] < d and (d - x[0]).days <= 500][-30:]
    if len(h) < 30: return None
    if campione == 'sede': h = [x for x in h if x[7] == sede]
    sp = lambda x: 0.0 if medie is None else medie[sede] - medie[x[7]]
    sx = lambda x: 0.0 if medie is None else medie['x' + sede] - medie['x' + x[7]]
    rows = [(x, {k: v for k, _, modo in dims if (v := valore(x, k, modo, prof)) is not None}) for x in h]
    sd = {}
    for k, _, _ in dims:
        a = [v[k] for _, v in rows if k in v]; sd[k] = max(1e-3, float(np.std(a, ddof=1))) if len(a) >= 2 else 1e-3
    R = []
    for x, v in rows:
        ds = ws = 0.0
        for k, w, _ in dims:
            if k in v and target.get(k) is not None: ds += w * ((v[k] - target[k]) / sd[k]) ** 2; ws += w
        if ws: R.append([math.sqrt(ds / ws), ws, x])
    if not R: return None
    wb = max(r[1] for r in R); R = [r + [r[1] / wb] for r in R]
    if sum(1 for r in R if r[3] >= 0.6) >= 4: R = [r for r in R if r[3] >= 0.6]
    sD = sorted(r[0] for r in R); hb = max(0.35, sD[len(sD) // 2]); xi = math.log(2) / 106
    sw = sw2 = spt = sxg = 0.0
    for dist, _, x, cov in R:
        if x[1].get('npxg') is None or x[2].get('npxg') is None: continue
        w = math.exp(-0.5 * (dist / hb) ** 2) * math.exp(-xi * (d - x[0]).days) * cov
        sw += w; sw2 += w * w; spt += w * (x[6] + sp(x)); sxg += w * (x[1]['npxg'] - x[2]['npxg'] + sx(x))
    if sw <= 0: return None
    xg = [x[1]['npxg'] - x[2]['npxg'] + sx(x) for x in h if x[1].get('npxg') is not None and x[2].get('npxg') is not None]
    return {'p': spt / sw, 'neff': sw * sw / sw2, 'ps': float(np.mean([x[6] + sp(x) for x in h])), 'n': len(h), 'x': sxg / sw, 'xs': float(np.mean(xg))}

def raccogli(leghe):
    out = []
    for lid, ss in leghe:
        ms = S.carica(lid, ss); st = S.profili(ms); rating_prima(rq.leggi(S.FDCOD[lid]))
        rat = {}
        for m in ms:
            if m['_fd']: rat[(m['id'], 'H')] = (m['_fd']['RA'], m['_fd']['EA']); rat[(m['id'], 'A')] = (m['_fd']['RH'], m['_fd']['EH'])
        chi = {(t, m['date'], lato): m for m in ms for lato, t in (('H', m['home_team']['id']), ('A', m['away_team']['id']))}
        st = {t: [x + (rat.get((chi[(t, x[0].isoformat(), x[7])]['id'], x[7])) or (None, None)) for x in h] for t, h in st.items()}
        xs = [m['_v']['H']['npxg'] - m['_v']['A']['npxg'] for m in ms if m['_v']['H'].get('npxg') is not None and m['_v']['A'].get('npxg') is not None]
        medie = {'H': np.mean([S.punti(m['score_home'], m['score_away']) for m in ms]), 'A': np.mean([S.punti(m['score_away'], m['score_home']) for m in ms]),
                 'xH': float(np.mean(xs)), 'xA': -float(np.mean(xs))}
        for m in ms:
            if not m['_fd'] or m['_r'][0] is None: continue
            d = dt.date.fromisoformat(m['date']); H, A = m['home_team']['id'], m['away_team']['id']
            r = {'lega': lid, 'hg': m['score_home'], 'ag': m['score_away'], 'res': m['_r'][0] - m['_r'][1], 'ye': m['_fd']['ye']}
            for nome, dims, prof, camp, corr in VAR:
                if prof in ('motore', 'corrette'): tH, tA = bersaglio(st[A], d, 'A', dims), bersaglio(st[H], d, 'H', dims)
                elif prof == 'mix': tH, tA = {**bersaglio(st[A], d, 'A', dims), 'elo': m['_fd']['EA']}, {**bersaglio(st[H], d, 'H', dims), 'elo': m['_fd']['EH']}
                elif prof == 'profilo': tH, tA = m.get('_pA') or {}, m.get('_pH') or {}
                elif prof == 'rating': tH, tA = {'rat': m['_fd']['RA']}, {'rat': m['_fd']['RH']}
                else: tH, tA = {'elo': m['_fd']['EA']}, {'elo': m['_fd']['EH']}
                cH = card(st.get(H, []), d, 'H', tH, dims, camp, prof, medie if corr else None)
                cA = card(st.get(A, []), d, 'A', tA, dims, camp, prof, medie if corr else None)
                if not (cH and cA): break
                r[nome] = (cH, cA)
            else: out.append(r)
    return out

def rapporto(R):
    from sklearn.linear_model import LogisticRegression
    lg = np.array([r['lega'] for r in R]); y = np.array([S.punti(r['hg'], r['ag']) - S.punti(r['ag'], r['hg']) for r in R], float)
    gd = np.array([r['hg'] - r['ag'] for r in R], float); res = np.array([r['res'] for r in R])
    esito = np.array([0 if r['hg'] > r['ag'] else (1 if r['hg'] == r['ag'] else 2) for r in R])
    X = np.array([[r['ye'], abs(r['ye'])] for r in R]); eE = np.zeros(len(R))
    for l in set(lg):   # punti attesi dall'Elo, casa meno trasferta, logistica fuori lega
        P = LogisticRegression(C=100, max_iter=3000).fit(X[lg != l], esito[lg != l]).predict_proba(X[lg == l]); eE[lg == l] = 3 * (P[:, 0] - P[:, 2])
    cor = lambda a, b: float(np.corrcoef(a, b)[0, 1])
    def ols(Y, *Xs):
        A_ = np.c_[tuple(Xs) + (np.ones(len(Y)),)]; b, *_ = np.linalg.lstsq(A_, Y, rcond=None); e = Y - A_ @ b
        return b / np.sqrt(np.diag(e.var() * len(Y) / (len(Y) - A_.shape[1]) * np.linalg.inv(A_.T @ A_)))
    rng = np.random.default_rng(1); B = [rng.integers(0, len(R), len(R)) for _ in range(1000)]
    col = lambda nome, k: np.array([r[nome][0][k] - r[nome][1][k] for r in R])
    base = col(VAR[0][0], 'p'); bs = col(VAR[0][0], 'ps')
    print(f'{len(R)} partite, tutte e due le squadre con 30 partite di lega nei 500 giorni prima; Elo coi punti {cor(eE, y):.3f}')
    print('punti a partita contro le simili (la card), casa meno trasferta: coi punti della partita; contro la card di oggi (bootstrap);')
    print('i punti semplici dello stesso campione; sopra l\'Elo e sopra i punti semplici (z); col residuo del mercato; errore a schermo')
    for nome, *_ in VAR:
        c, ps = col(nome, 'p'), col(nome, 'ps'); dl = cor(c, y) - cor(base, y)
        se = np.std([cor(c[i], y[i]) - cor(base[i], y[i]) for i in B]); sg = np.std([cor(c[i], y[i]) - cor(ps[i], y[i]) for i in B])
        z = ols(y, eE, ps, c)[2]; ne = np.median([r[nome][j]['neff'] for r in R for j in (0, 1)]); n = np.median([r[nome][j]['n'] for r in R for j in (0, 1)])
        meglio = sum(1 for l in set(lg) if cor(c[lg == l], y[lg == l]) > cor(base[lg == l], y[lg == l]))
        print(f'  {nome:38s} {cor(c, y):.3f}  {dl:+.3f} ±{2 * se:.3f} ({meglio:2d} leghe su {len(set(lg))})  semplici {cor(ps, y):.3f} '
              f'(card meno semplici {cor(c, y) - cor(ps, y):+.3f} ±{2 * sg:.3f})  sopra Elo e semplici z {z:+.2f}  mercato {cor(c, res):+.3f}  '
              f'neff {ne:4.1f} su {n:2.0f}, ±{1.3 / math.sqrt(ne):.2f} punti')
    print('\nnpxg meno npxga contro le simili (da cui escono le probabilita\' del KNN): coi gol; sopra l\'Elo e gli xG semplici (z); col residuo del mercato')
    for nome, *_ in VAR:
        g, gs = col(nome, 'x'), col(nome, 'xs')
        print(f'  {nome:38s} gol {cor(g, gd):.3f} (semplici {cor(gs, gd):.3f})  sopra Elo e semplici z {ols(y, eE, gs, g)[2]:+.2f}  mercato {cor(g - gs, res):+.3f}')

if __name__ == '__main__':
    rapporto(raccogli(S.un.argomenti(sys.argv[1:])))
