# Markov e Dixon-Coles contro l'Elo e i risultati reali (AGENTS.md, Markov, Dixon-Coles ed Elo).
#
#   python3 strumenti/markov-dc.py batch48 batch4 batch/2627 batch/nuove batch/livello
#
# Rifà dai lambda completi del CSV (dopo l'Elo, e prima dell'Elo con la divisione data dal log-odds del modello)
# il Dixon-Coles e il Markov del motore, con la prova di coincidenza, e li confronta coi risultati: logloss,
# prese, AUC e pendenza 1 contro 2, il pareggio per fascia; poi Elo, DC e Markov insieme fuori lega (stimato su
# tutte le leghe meno una, misurato su quella) e il peso del Markov nell'ensemble. Solo descrittivo.
import os, io, sys, csv, glob, math, collections, importlib.util
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
DIR = os.path.dirname(os.path.abspath(__file__))
s = importlib.util.spec_from_file_location('qg', os.path.join(DIR, 'quote-gol.py')); qg = importlib.util.module_from_spec(s); s.loader.exec_module(qg); qb = qg.qb
DIRS = sys.argv[1:] or ['batch48', 'batch4', 'batch/2627', 'batch/nuove', 'batch/livello']
KEYS = ['DCover 1', 'DCover X', 'DCover 2', 'MKover 1', 'MKover X', 'MKover 2', '1', 'X', '2', 'Ambito: lambda casa (completo)',
        'Ambito: lambda trasf. (completo)', 'Unita: rho stimato', 'Elo: log-odds modello [completo → 1X2]', 'Elo: log-odds Elo [completo → 1X2]',
        'Elo: log-odds bersaglio [completo → 1X2]', 'COPIA CONFORME DELLO SCANNER', 'SCORE', 'LEGA']
def leggi(f):
    righe = collections.defaultdict(list)
    for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if not r or not r[0]: continue
        if r[0].startswith('=== ARCHIVIO'): break
        righe[r[0]].append(r)
    ids = righe['ID PARTITA'][0]; out = []
    for c in range(1, len(ids), 4):
        if not ids[c]: continue
        v = {k: (righe[k][0][c] if k in righe and len(righe[k][0]) > c else None) for k in KEYS}
        if not (v['COPIA CONFORME DELLO SCANNER'] or '').startswith('SI'): continue
        try: hg, ag = [int(x) for x in v['SCORE'].split('-')]
        except Exception: continue
        n = {k: qb.num(v[k]) for k in KEYS[:-3]}
        if None in n.values(): continue
        out.append(dict(id=ids[c], lega=os.path.basename(f).split('_', 2)[2].rsplit('_', 1)[0], out=0 if hg > ag else (1 if hg == ag else 2), n=n))
    return out
M = list({m['id']: m for d in DIRS for f in sorted(glob.glob(os.path.join(d, '*.csv'))) for m in leggi(f)}.values())
N = len(M); g = lambda k: np.array([m['n'][k] for m in M])
y = np.array([m['out'] for m in M]); lg = np.array([m['lega'] for m in M])
DC = np.column_stack([g('DCover 1'), g('DCover X'), g('DCover 2')]) / 100; MK = np.column_stack([g('MKover 1'), g('MKover X'), g('MKover 2')]) / 100
FIN = np.column_stack([g('1'), g('X'), g('2')]) / 100
LH, LA, RHO = g('Ambito: lambda casa (completo)'), g('Ambito: lambda trasf. (completo)'), g('Unita: rho stimato')
LGM, LGE, LGT = g('Elo: log-odds modello [completo → 1X2]'), g('Elo: log-odds Elo [completo → 1X2]'), g('Elo: log-odds bersaglio [completo → 1X2]')
print(f'{N} partite di {len(set(lg))} leghe')
def markov(lH, lA):
    # markovFlow del motore: 90 minuti, rate per minuto, piu' gol dopo il 75', chi e' avanti rallenta e chi e' dietro accelera
    FAT_FROM, FAT = 75, 1.30; norm = (FAT_FROM + (90 - FAT_FROM) * FAT) / 90
    rH0, rA0 = lH / 90 / norm, lA / 90 / norm
    d = np.zeros((len(lH), 11)); d[:, 5] = 1
    mH = np.array([1.12] * 5 + [1.0] + [0.94] * 5); mA = np.array([0.94] * 5 + [1.0] + [1.12] * 5)
    for t in range(90):
        f = FAT if t >= FAT_FROM else 1.0
        crH = rH0[:, None] * f * mH[None, :]; crA = rA0[:, None] * f * mA[None, :]; cp0 = np.maximum(0, 1 - crH - crA)
        nd = d * cp0
        up = d * crH; nd[:, 1:] += up[:, :-1]; nd[:, 10] += up[:, 10]
        dn = d * crA; nd[:, :-1] += dn[:, 1:]; nd[:, 0] += dn[:, 0]
        d = nd
    return np.column_stack([d[:, 6:].sum(1), d[:, 5], d[:, :5].sum(1)])
def dcp(lH, lA, rho):
    P = qg.matrici(lH, lA, rho); I, J = qg.I, qg.J
    return np.column_stack([(P * (I > J)).sum((1, 2)), (P * (I == J)).sum((1, 2)), (P * (I < J)).sum((1, 2))])
# prova di coincidenza: dai lambda completi (dopo l'Elo) il DC e il Markov del CSV
DCr, MKr = dcp(LH, LA, RHO), markov(LH, LA)
print(f'prova di coincidenza: DC entro {100 * np.abs(DCr - DC).max():.2f} punti, Markov entro {100 * np.abs(MKr - MK).max():.2f}')
# prima dell'Elo: stesso totale, divisione dal log-odds del modello
T = LH + LA; sp = qg.dividi(T, LGM, RHO, 60); LH0, LA0 = T * sp, T * (1 - sp)
DC0, MK0 = dcp(LH0, LA0, RHO), markov(LH0, LA0)
print(f'prima dell Elo: il log(p1/p2) del DC rifatto sta entro {np.abs(np.log(DC0[:, 0] / DC0[:, 2]) - LGM).max():.4f} da quello del CSV')
nd = y != 1; y12 = (y[nd] == 0).astype(int)
def lg12(P): return np.log(P[:, 0] / P[:, 2])
def rep(nome, P):
    P = P / P.sum(1, keepdims=True); ll = -np.log(P[np.arange(N), y]); x = lg12(P)[nd]
    sl = LogisticRegression(C=1e6).fit(x[:, None], y12).coef_[0][0]
    print(f'  {nome:28s} logloss 1X2 {ll.mean():.4f} · prese {100 * (P.argmax(1) == y).mean():.2f}% · 1 contro 2: AUC {roc_auc_score(y12, x):.3f}, pendenza {sl:.3f}'
          f' · pareggio: previsto {100 * P[:, 1].mean():.1f}% (reale {100 * (y == 1).mean():.1f}), AUC {roc_auc_score((y == 1).astype(int), P[:, 1]):.3f}')
    return ll
print('\n=== i modelli contro i risultati ===')
L = {}
L['dc0'] = rep('Dixon-Coles senza Elo', DC0); L['mk0'] = rep('Markov senza Elo', MK0)
L['dc'] = rep('Dixon-Coles con Elo', DC); L['mk'] = rep('Markov con Elo', MK); L['fin'] = rep('finale (0.70 DC + 0.30 Markov)', FIN)
xe = LGE[nd]; print(f'  Elo da solo (solo 1 contro 2)   AUC {roc_auc_score(y12, xe):.3f}, pendenza {LogisticRegression(C=1e6).fit(xe[:, None], y12).coef_[0][0]:.3f}')
print('\n=== quanto vanno d accordo con l Elo (log p1/p2) ===')
for nome, x in (('DC senza Elo', lg12(DC0)), ('Markov senza Elo', lg12(MK0)), ('DC con Elo', lg12(DC)), ('Markov con Elo', lg12(MK))):
    print(f'  {nome:18s} correlazione con l Elo {np.corrcoef(x, LGE)[0, 1]:.3f} · con il DC senza Elo {np.corrcoef(x, lg12(DC0))[0, 1]:.4f}')
print(f'  pX: correlazione fra DC e Markov {np.corrcoef(DC[:, 1], MK[:, 1])[0, 1]:.3f}; Markov meno DC in media {100 * (MK[:, 1] - DC[:, 1]).mean():+.2f} punti')
# combinazioni 1 contro 2 fuori lega
L12 = lg[nd]
def lolo(F):
    p = np.zeros(len(y12))
    for l in sorted(set(L12)):
        te = L12 == l; p[te] = LogisticRegression(C=1e6, max_iter=2000).fit(F[~te], y12[~te]).predict_proba(F[te])[:, 1]
    return p
lp = lambda p: -(y12 * np.log(p) + (1 - y12) * np.log(1 - p))
print('\n=== 1 contro 2 fuori lega: Elo, DC e Markov (senza Elo) insieme ===')
base = lp(1 / (1 + np.exp(-LGT[nd])))
cands = {'Elo da solo (ricalibrato)': [LGE], 'DC da solo': [lg12(DC0)], 'Markov da solo': [lg12(MK0)], 'Elo + DC (pesi liberi)': [LGE, lg12(DC0)],
         'Elo + Markov (pesi liberi)': [LGE, lg12(MK0)], 'Elo + DC + Markov': [LGE, lg12(DC0), lg12(MK0)]}
for nome, cols in cands.items():
    d = lp(lolo(np.column_stack([c[nd] for c in cols]))) - base; per = {l: d[L12 == l].mean() for l in set(L12)}
    print(f'  {nome:28s} contro il motore di oggi {1000 * d.mean():+.2f} per mille (z {d.mean() / d.std(ddof=1) * math.sqrt(len(d)):+.2f}), meglio in {sum(v < 0 for v in per.values())}/{len(per)} leghe')
F3 = np.column_stack([LGE[nd], lg12(DC0)[nd], lg12(MK0)[nd]]); m = LogisticRegression(C=1e6, max_iter=2000).fit(F3, y12)
print(f'  pesi su tutte (Elo, DC, Markov): {m.coef_[0][0]:+.3f} {m.coef_[0][1]:+.3f} {m.coef_[0][2]:+.3f}')
# il peso del Markov nell'1X2 finale (dopo l'Elo, come nell'ensemble), fuori lega
print('\n=== il peso del Markov nell ensemble (1X2 intero, dopo l Elo) ===')
W = np.round(np.arange(0, 1.01, 0.1), 2)
llw = {w: -np.log(((1 - w) * DC + w * MK)[np.arange(N), y] / ((1 - w) * DC + w * MK).sum(1)) for w in W}
scelte = []
oos = np.zeros(N)
for l in sorted(set(lg)):
    te = lg == l; wb = min(W, key=lambda w: llw[w][~te].mean()); scelte.append(wb); oos[te] = llw[wb][te]
d = oos - llw[0.3]; print('  logloss per peso del Markov: ' + ' · '.join(f'{w:.1f} {llw[w].mean():.5f}' for w in W))
print(f'  scelto fuori lega: {collections.Counter(scelte).most_common()}; contro 0.30 {1000 * d.mean():+.3f} per mille (z {d.mean() / d.std(ddof=1) * math.sqrt(N):+.2f})')
d0 = llw[1.0] - llw[0.3]; d1 = llw[0.0] - llw[0.3]
print(f'  solo Markov contro 0.30: {1000 * d0.mean():+.3f} per mille (z {d0.mean() / d0.std(ddof=1) * math.sqrt(N):+.2f}); solo DC: {1000 * d1.mean():+.3f} (z {d1.mean() / d1.std(ddof=1) * math.sqrt(N):+.2f})')
# il pareggio: calibrazione per fascia
print('\n=== il pareggio per fascia (previsto -> reale) ===')
for nome, p in (('DC', DC[:, 1]), ('Markov', MK[:, 1]), ('finale', FIN[:, 1] / FIN.sum(1))):
    out = []
    for a, b in ((0, .22), (.22, .26), (.26, .30), (.30, 1)):
        k = (p >= a) & (p < b)
        if k.sum(): out.append(f'{int(100*a)}-{int(100*b)}%: {k.sum()} {100 * p[k].mean():.1f}->{100 * (y[k] == 1).mean():.1f}')
    print(f'  {nome:7s} ' + ' · '.join(out))
