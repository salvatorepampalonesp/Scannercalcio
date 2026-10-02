# Il Dixon-Coles contro i risultati dei CSV (AGENTS.md, Il Dixon-Coles contro i risultati reali).
#
#   python3 strumenti/dc-residui.py batch48 batch4 batch/2627 batch/nuove batch/livello
#   python3 strumenti/dc-residui.py --prova <cartelle con le partite nuove> --dal 2026-10-03
#
# Senza --prova: la pagella del Dixon-Coles di ruolo (livello, correlazione coi gol e tetto di Poisson, mercati
# della matrice, risultato esatto), i residui dei gol contro le statistiche previste del CSV, quanto varrebbero
# fuori lega (stimato su tutte le leghe meno una, misurato su quella), e i coefficienti della regola stimati su
# tutte le cartelle. Con --prova: il test registrato, coi coefficienti di REGOLA, sulle partite giocate dal
# giorno --dal in poi (si guarda una volta sola). Solo misura: il motore non cambia.
import os, io, sys, csv, glob, math, datetime, collections, importlib.util
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
DIR = os.path.dirname(os.path.abspath(__file__))
s = importlib.util.spec_from_file_location('qg', os.path.join(DIR, 'quote-gol.py')); qg = importlib.util.module_from_spec(s); s.loader.exec_module(qg); qb = qg.qb

# Scritti il 2 ottobre 2026, prima di qualunque partita del test: stimati su tutte le 23.278 partite delle 24 leghe.
# A = Elo e modello con pesi liberi; B = A + tocchi in area previsti (casa meno trasferta, standardizzati).
REGOLA = dict(A=(+0.01024, +0.47035, +0.65971), B=(+0.08218, +0.43716, +0.49462, +0.21680), m=+5.0773, sd=7.6366,
              dal='2026-10-03', minimo=4000)
ELO, MOD, TGT = 'Elo: log-odds Elo [completo → 1X2]', 'Elo: log-odds modello [completo → 1X2]', 'Elo: log-odds bersaglio [completo → 1X2]'
SQ = ['Gol', 'NPxG', 'xG', 'xGOT', 'xG Palle Inattive', 'SoT', 'Corner', 'Falli', 'Gialli', 'Big Chances', 'Big Ch. Sprecate', 'Possesso %', 'Tocchi Area']
UNI = [MOD, 'Ambito: lambda casa (ruolo)', 'Ambito: lambda trasf. (ruolo)', 'Ambito: lambda casa (completo)', 'Ambito: lambda trasf. (completo)',
       'Unita: rho stimato', 'DCover 1', 'DCover X', 'DCover 2', 'Over 2.5', '1', 'X', '2', ELO, TGT, 'ELO Diff (H-A)']

def leggi(f):
    righe = collections.defaultdict(list)
    for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if not r or not r[0]: continue
        if r[0].startswith('=== ARCHIVIO'): break
        righe[r[0]].append(r)
    ids = righe['ID PARTITA'][0]; out = []
    stag = os.path.basename(f).rsplit('_', 1)[1][:9]
    for c in range(1, len(ids), 4):
        if not ids[c] or not (righe['COPIA CONFORME DELLO SCANNER'][0][c] or '').startswith('SI'): continue
        try: hg, ag = [int(x) for x in righe['SCORE'][0][c].split('-')]
        except Exception: continue
        u = {k: qb.num(righe[k][0][c]) if k in righe and len(righe[k][0]) > c else None for k in UNI}
        if None in [u[k] for k in UNI[:15]]: continue
        sq = {}
        for k in SQ:
            r = righe.get(k, [])
            if len(r) >= 2: sq[k] = (qb.num(r[0][c]), qb.num(r[1][c]))
        d = righe['DATA'][0][c]
        try: data = datetime.datetime.strptime(d, '%d/%m/%Y').date().isoformat()
        except Exception: data = None
        out.append(dict(id=ids[c], lega=os.path.basename(f).split('_', 2)[2].rsplit('_', 1)[0], stag=stag, data=data, hg=hg, ag=ag, u=u, sq=sq))
    return out

def carica(dirs, dal=None):
    M = {m['id']: m for d in dirs for f in sorted(glob.glob(os.path.join(d, '*.csv'))) for m in leggi(f)}
    M = list(M.values())
    if dal: M = [m for m in M if m['data'] and m['data'] >= dal]
    return M

def tocchi(M):
    # tocchi in area previsti, casa meno trasferta; None se il CSV non li ha (o li ha a zero tutti e due)
    out = []
    for m in M:
        h, a = m['sq'].get('Tocchi Area', (None, None))
        out.append(h - a if h is not None and a is not None and (h != 0 or a != 0) else None)
    return out

def z_di(d): return d.mean() / d.std(ddof=1) * math.sqrt(len(d))
lp = lambda p, y: -(y * np.log(p) + (1 - y) * np.log(1 - p))
sig = lambda x: 1 / (1 + np.exp(-x))

def prese(M, lg12):
    # 1X2 intero: pX del motore, il resto diviso secondo sigma(lg12); contro il pick del motore
    F = np.array([[m['u']['1'], m['u']['X'], m['u']['2']] for m in M]) / 100; F = F / F.sum(1, keepdims=True)
    y = np.array([0 if m['hg'] > m['ag'] else (1 if m['hg'] == m['ag'] else 2) for m in M])
    q = sig(lg12); N2 = np.column_stack([(1 - F[:, 1]) * q, F[:, 1], (1 - F[:, 1]) * (1 - q)])
    h0, h1 = (F.argmax(1) == y).astype(float), (N2.argmax(1) == y).astype(float); d = h1 - h0
    return 100 * h0.mean(), 100 * h1.mean(), 100 * d.mean(), 100 * d.std(ddof=1) / math.sqrt(len(d))

def esplora(dirs):
    M = carica(dirs); N = len(M); u = lambda k: np.array([m['u'][k] for m in M], float)
    hg, ag = np.array([m['hg'] for m in M]), np.array([m['ag'] for m in M]); tot = hg + ag
    gr = np.array([m['lega'] + m['stag'] for m in M]); lg = np.array([m['lega'] for m in M])
    LHr, LAr, RHO = u('Ambito: lambda casa (ruolo)'), u('Ambito: lambda trasf. (ruolo)'), u('Unita: rho stimato')
    m0 = qg.mercati(qg.matrici(LHr, LAr, RHO))
    print(f'{N} partite di {len(set(lg))} leghe · prova di coincidenza: Over 2.5 dalla matrice entro {100 * np.abs(m0["o25"] - u("Over 2.5") / 100).max():.3f} punti')
    # i CSV fino al b62 hanno i lambda di ruolo senza il livello dei gol del b63: si mette, per misurare il motore di oggi
    F = 1.051; LH, LA = LHr * F, LAr * F; P = qg.matrici(LH, LA, RHO); mk = qg.mercati(P); LT = LH + LA
    LHc, LAc = u('Ambito: lambda casa (completo)'), u('Ambito: lambda trasf. (completo)')
    def demean(x):
        x = x.astype(float).copy()
        for gg in set(gr): k = gr == gg; x[k] -= x[k].mean()
        return x
    corr = lambda x, y: np.corrcoef(demean(x), demean(y))[0, 1]
    def auc_dentro(p, yy):
        a, w = [], []
        for l in set(lg):
            k = lg == l
            if 0 < yy[k].mean() < 1: a.append(roc_auc_score(yy[k], p[k])); w.append(k.sum())
        return np.average(a, weights=w)
    print('\n=== 1. i gol: lambda di ruolo (col livello del b63) contro i gol veri, dentro la lega-stagione ===')
    print(f'  livello: casa {LH.mean():.3f} contro {hg.mean():.3f} · trasferta {LA.mean():.3f} contro {ag.mean():.3f} · totale {LT.mean():.3f} contro {tot.mean():.3f}')
    print(f'  correlazione: casa {corr(LH, hg):.3f} · trasferta {corr(LA, ag):.3f} · totale {corr(LT, tot):.3f} · differenza reti (lambda completi) {corr(LHc - LAc, hg - ag):.3f}')
    for nome, lam in (('casa', LH), ('trasferta', LA), ('totale', LT)):
        vl = np.mean([lam[gr == gg].var() for gg in set(gr)])
        print(f'  tetto di Poisson, {nome}: sqrt(var/(var+media)) = {math.sqrt(vl / (vl + lam.mean())):.3f} (varianza del lambda dentro la lega {vl:.3f})')
    print('\n=== 2. i mercati della matrice di ruolo contro il reale ===')
    for nome, p, yy in (('Over 1.5', mk['o15'], tot > 1.5), ('Over 2.5', mk['o25'], tot > 2.5), ('Over 3.5', mk['o35'], tot > 3.5), ('Goal', mk['gg'], (hg > 0) & (ag > 0))):
        yy = yy.astype(int); fasce = []
        for a, b in ((0, .4), (.4, .5), (.5, .6), (.6, 1.01)):
            k = (p >= a) & (p < b)
            if k.sum() > 50: fasce.append(f'{int(100*a)}-{min(100, int(100*b))}: {k.sum()} {100*p[k].mean():.1f}->{100*yy[k].mean():.1f}')
        print(f'  {nome:8s} previsto {100*p.mean():.1f}% reale {100*yy.mean():.1f}% · AUC dentro la lega {auc_dentro(p, yy):.3f} · ' + ' · '.join(fasce))
    flat = P.reshape(N, -1); best = flat.argmax(1); bi, bj = best // 11, best % 11
    hit = (bi == np.minimum(hg, 10)) & (bj == np.minimum(ag, 10))
    print(f'  risultato esatto: il piu probabile esce il {100*hit.mean():.1f}% (previsto {100*flat.max(1).mean():.1f}%) · '
          'il piu probabile e\' ' + ', '.join(f'{a}-{b} {100*c/N:.0f}%' for (a, b), c in collections.Counter(zip(bi, bj)).most_common(4)))
    fr = collections.Counter(zip(np.minimum(hg, 4), np.minimum(ag, 4)))
    print('  punteggi, previsto -> reale: ' + ' · '.join(f'{a}-{b} {100*P[:, a, b].mean():.1f}->{100*fr[(a, b)]/N:.1f}' for a, b in ((0,0),(1,0),(0,1),(1,1),(2,1),(1,2),(2,0),(0,2),(2,2),(3,1))))
    print(f'  pareggi dalla matrice di ruolo {100*(1 - mk["p1"] - mk["p2"]).mean():.1f}% contro {100*(hg == ag).mean():.1f}% reali')
    print('\n=== 3. dove sbaglia: residui dei gol contro le previsioni pre-partita del CSV (correlazione dentro la lega-stagione) ===')
    rt = tot - LT; rd = (hg - ag) - (LHc - LAc); prima = np.array([m['stag'] < '2025' for m in M])
    cand = {}
    for k in SQ:
        h = np.array([m['sq'].get(k, (None, None))[0] for m in M], dtype=object); a = np.array([m['sq'].get(k, (None, None))[1] for m in M], dtype=object)
        ok = np.array([x is not None and y is not None and (x != 0 or y != 0) for x, y in zip(h, a)])
        if ok.mean() < 0.8: continue
        h, a = np.where(ok, h, np.nan).astype(float), np.where(ok, a, np.nan).astype(float)
        cand[f'{k} somma'] = (h + a, ok); cand[f'{k} casa meno trasf.'] = (h - a, ok)
    cand['Elo diff'] = (u('ELO Diff (H-A)'), np.isfinite(u('ELO Diff (H-A)')))
    def tabella(nome, r):
        res = []
        for kk, (x, ok) in cand.items():
            z = []
            for sel in (ok, ok & prima, ok & ~prima):
                xd, yd = x[sel].copy(), r[sel].copy(); g2 = gr[sel]
                for gg in set(g2): q = g2 == gg; xd[q] -= xd[q].mean(); yd[q] -= yd[q].mean()
                c = np.corrcoef(xd, yd)[0, 1]; z.append((c, c * math.sqrt(sel.sum())))
            res.append((kk, *z))
        res.sort(key=lambda t: -abs(t[1][1]))
        print(f'  residuo {nome}:')
        for kk, a, b, c in res[:6]:
            print(f'    {kk:28s} r {a[0]:+.3f} (z {a[1]:+.1f}) · 2023/24-24/25 {b[0]:+.3f} · dal 2025/26 {c[0]:+.3f}')
    tabella('del totale gol (gol veri meno lambda di ruolo)', rt)
    tabella('della differenza reti (coi lambda completi, quelli dell 1X2)', rd)
    print('\n=== 4. quanto varrebbero, fuori lega (stimato su tutte le leghe meno una, misurato su quella) ===')
    xd, yd = demean(LT), demean(tot)
    print(f'  gol totali sul lambda totale, dentro la lega-stagione: pendenza {np.polyfit(xd, yd, 1)[0]:.3f} (sotto 1 = lambda troppo largo)')
    # il centro e' la media della lega-stagione col senno di poi: solo descrittivo
    mu = np.array([LT[gr == g_].mean() for g_ in gr]); yo = (tot > 2.5).astype(float); yg = ((hg > 0) & (ag > 0)).astype(float)
    def perdita(c):
        T2 = mu + c * (LT - mu); s_ = LH / LT; mm = qg.mercati(qg.matrici(T2 * s_, T2 * (1 - s_), RHO))
        return qg.ll(mm['o25'], yo) + qg.ll(mm['gg'], yg)
    C = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]; tab = {c: perdita(c) for c in C}; oos = np.zeros(N); scelte = []
    for l in sorted(set(lg)):
        te = lg == l; cb = min(C, key=lambda c: tab[c][~te].mean()); scelte.append(cb); oos[te] = tab[cb][te]
    d = oos - tab[1.0]; per = {l: d[lg == l].mean() for l in set(lg)}
    print('  Over 2.5 + Goal restringendo il totale verso la media della lega-stagione: ' + ' · '.join(f'{c} {tab[c].mean():.5f}' for c in C))
    print(f'  scelto fuori lega {collections.Counter(scelte).most_common()}: {1000*d.mean():+.2f} per mille (z {z_di(d):+.2f}), meglio in {sum(v < 0 for v in per.values())}/{len(per)} leghe')
    nd = hg != ag; y12 = (hg > ag)[nd].astype(int); L12 = lg[nd]
    def lolo(Fm):
        p = np.zeros(len(y12))
        for l in sorted(set(L12)):
            te = L12 == l; p[te] = LogisticRegression(C=1e6, max_iter=2000).fit(Fm[~te], y12[~te]).predict_proba(Fm[te])[:, 1]
        return p
    def riga(nome, p, rif):
        d = lp(p, y12) - lp(rif, y12); per = {l: d[L12 == l].mean() for l in set(L12)}
        print(f'  {nome:62s} {1000*d.mean():+.2f} per mille (z {z_di(d):+.2f}), meglio in {sum(v < 0 for v in per.values())}/{len(per)} leghe')
    DCc = np.log(u('DCover 1') / u('DCover 2'))[nd]; p0 = lolo(DCc[:, None])
    for kk in ('Tocchi Area casa meno trasf.', 'Corner casa meno trasf.', 'Possesso % casa meno trasf.'):
        x, ok = cand[kk]; xs = np.where(ok[nd], (x[nd] - np.nanmean(x[nd])) / np.nanstd(x[nd]), 0.0)
        riga(f'1 contro 2, {kk} sopra il DC di oggi (ricalibrato)', lolo(np.column_stack([DCc, xs])), p0)
    # la regola: A = Elo e modello a pesi liberi, B = A + tocchi in area; contro il motore di oggi, sigma(lgTarget)
    tc = tocchi(M); okt = np.array([t is not None for t in tc])
    dt = np.array([t if t is not None else np.nan for t in tc], float)[nd]
    mt, st = np.nanmean(dt), np.nanstd(dt); tz = np.where(np.isfinite(dt), (dt - mt) / st, 0.0)
    E, Mo, T = u(ELO)[nd], u(MOD)[nd], u(TGT)[nd]; mot = sig(T)
    pA, pB = lolo(np.column_stack([E, Mo])), lolo(np.column_stack([E, Mo, tz]))
    print(f'  tocchi in area previsti presenti su {100*okt.mean():.1f}% delle partite (dove mancano, al centro)')
    riga('A: Elo e modello a pesi liberi, contro il motore di oggi', pA, mot)
    riga('B: A + tocchi in area, contro il motore di oggi', pB, mot)
    riga('B contro A (quello che aggiungono i tocchi)', pB, pA)
    # prese del 1X2 intero, fuori lega: B stimato sulle partite senza pari delle altre leghe, pX del motore
    dta = np.array([t if t is not None else np.nan for t in tc], float); tza = np.where(np.isfinite(dta), (dta - mt) / st, 0.0)
    Xa = np.column_stack([u(ELO), u(MOD), tza]); lgB = np.zeros(N)
    for l in sorted(set(lg)):
        te = lg == l; tr = ~te & (hg != ag)
        lgB[te] = LogisticRegression(C=1e6, max_iter=2000).fit(Xa[tr], (hg > ag)[tr].astype(int)).decision_function(Xa[te])
    h0, h1, dh, se = prese(M, lgB)
    print(f'  prese del 1X2 intero, B fuori lega: motore {h0:.2f}% · B {h1:.2f}% · differenza {dh:+.2f} (errore {se:.2f})')
    fA = LogisticRegression(C=1e6, max_iter=2000).fit(np.column_stack([E, Mo]), y12)
    fB = LogisticRegression(C=1e6, max_iter=2000).fit(np.column_stack([E, Mo, tz]), y12)
    print('\n=== 5. i coefficienti della regola, su tutte le partite (vanno scritti in REGOLA prima del test) ===')
    print(f'  A: intercetta {fA.intercept_[0]:+.5f} · Elo {fA.coef_[0][0]:+.5f} · modello {fA.coef_[0][1]:+.5f}')
    print(f'  B: intercetta {fB.intercept_[0]:+.5f} · Elo {fB.coef_[0][0]:+.5f} · modello {fB.coef_[0][1]:+.5f} · tocchi {fB.coef_[0][2]:+.5f}'
          f' (tocchi in area casa meno trasferta: media {mt:+.4f}, deviazione standard {st:.4f})')
    print('  REGOLA in uso: A ' + ' '.join(f'{v:+.5f}' for v in REGOLA['A']) + ' · B ' + ' '.join(f'{v:+.5f}' for v in REGOLA['B']) + f' · m {REGOLA["m"]:+.4f} sd {REGOLA["sd"]:.4f}')

def prova(dirs, dal):
    M = carica(dirs, dal); R = REGOLA
    nd = np.array([m['hg'] != m['ag'] for m in M]); Mn = [m for m, k in zip(M, nd) if k]
    print(f'{len(M)} partite giocate dal {dal} in copia conforme, {len(Mn)} senza pari, {len({m["lega"] for m in M})} leghe; il test si guarda quando le senza pari sono almeno {R["minimo"]}')
    if not Mn: return
    y12 = np.array([1 if m['hg'] > m['ag'] else 0 for m in Mn]); L12 = np.array([m['lega'] for m in Mn])
    E, Mo, T = (np.array([m['u'][k] for m in Mn]) for k in (ELO, MOD, TGT))
    dt = np.array([t if t is not None else np.nan for t in tocchi(Mn)], float); tz = np.where(np.isfinite(dt), (dt - R['m']) / R['sd'], 0.0)
    lA = R['A'][0] + R['A'][1] * E + R['A'][2] * Mo; lB = R['B'][0] + R['B'][1] * E + R['B'][2] * Mo + R['B'][3] * tz
    print(f'  tocchi in area previsti presenti su {100*np.isfinite(dt).mean():.1f}% delle partite senza pari')
    dB, dA, dBA = lp(sig(lB), y12) - lp(sig(T), y12), lp(sig(lA), y12) - lp(sig(T), y12), lp(sig(lB), y12) - lp(sig(lA), y12)
    per = {l: dB[L12 == l].mean() for l in set(L12) if (L12 == l).sum() >= 50}
    meglio = sum(v < 0 for v in per.values())
    # prese sul 1X2 intero: lg12 di B su tutte le partite (anche i pari), pX del motore
    Et, Mt = (np.array([m['u'][k] for m in M]) for k in (ELO, MOD))
    dtt = np.array([t if t is not None else np.nan for t in tocchi(M)], float); tzt = np.where(np.isfinite(dtt), (dtt - R['m']) / R['sd'], 0.0)
    h0, h1, dh, se = prese(M, R['B'][0] + R['B'][1] * Et + R['B'][2] * Mt + R['B'][3] * tzt)
    print(f'  B contro il motore: {1000*dB.mean():+.2f} per mille (z {z_di(dB):+.2f}) · meglio in {meglio} leghe su {len(per)} con almeno 50 partite senza pari')
    print(f'  B contro A: {1000*dBA.mean():+.2f} per mille (z {z_di(dBA):+.2f}) · A contro il motore {1000*dA.mean():+.2f} (z {z_di(dA):+.2f})')
    print(f'  prese del 1X2: motore {h0:.2f}% · B {h1:.2f}% · differenza {dh:+.2f} (errore {se:.2f})')
    passa = z_di(dB) <= -2 and dBA.mean() < 0 and meglio > len(per) / 2 and dh >= -2 * se
    pronto = len(Mn) >= R['minimo']
    print(f'  esito: {"PASSA" if passa else "NON PASSA"}' + ('' if pronto else f' (ma il campione non e\' ancora quello della regola: {len(Mn)} su {R["minimo"]})'))

if __name__ == '__main__':
    a = sys.argv[1:]
    if '--prova' in a:
        dal = REGOLA['dal']
        if '--dal' in a: i = a.index('--dal'); dal = a[i + 1]; del a[i:i + 2]
        a.remove('--prova'); prova(a, dal)
    else:
        esplora(a or ['batch48', 'batch4', 'batch/2627', 'batch/nuove', 'batch/livello'])
