# Quando lo Scanner e le quote non sono d'accordo, chi ha ragione, per fascia di disaccordo
# (AGENTS.md, Il motore contro il mercato, «Quando lo Scanner e le quote non sono d'accordo»).
#
#   python3 strumenti/disaccordo.py <cartelle dei CSV> [--quote batch/quote-disaccordo]
#
# Aggancia le partite in copia conforme dei CSV del Comparatore alle quote di chiusura di football-data (file della
# stagione 2026/27 dei cinque campionati, file new/ delle altre leghe; scaricati nella cartella --quote se mancano, mai in
# batch/quote) per data e nomi, col punteggio come prova. Lo Scanner e' l'1X2 delle righe 1, X, 2 (dal b77 il maestro);
# il motore prima del maestro sta nelle righe Maestro:. Il mercato e' la chiusura media col margine tolto in proporzione.
# Stampa: chi vince per fascia della differenza Scanner meno mercato sul favorito del mercato; le partite coi favoriti
# diversi; ogni esito a cui lo Scanner da' piu' del mercato, e il favorito e lo sfavorito del mercato per fascia, con la resa
# alla quota di chiusura; il peso dello Scanner dato il mercato su 1 contro 2. Solo descrittivo.
import os, re, sys, io, csv, glob, math, collections, importlib.util, urllib.request, datetime as dt
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
s = importlib.util.spec_from_file_location('qb', 'strumenti/quote-bookmaker.py'); qb = importlib.util.module_from_spec(s); s.loader.exec_module(qb)
args = sys.argv[1:]; FD = 'batch/quote-disaccordo'
if '--quote' in args: i = args.index('--quote'); FD = args[i + 1]; del args[i:i + 2]
CINQUE = {'ITA': 'I1', 'ENG': 'E0', 'ESP': 'SP1', 'GER': 'D1', 'FRA': 'F1'}
NEW = {'SWE': 'SWE', 'NOR': 'NOR', 'JPN': 'JPN', 'USA': 'USA', 'ARG': 'ARG', 'BRA': 'BRA', 'AUT': 'AUT', 'DEN': 'DNK', 'MEX': 'MEX',
       'SUI': 'SWZ', 'CHN': 'CHN', 'FIN': 'FIN', 'IRL': 'IRL', 'ROU': 'ROU', 'POL': 'POL'}
os.makedirs(FD, exist_ok=True)
def scarica(nome, url):
    f = os.path.join(FD, nome)
    if not os.path.exists(f) or os.path.getsize(f) == 0:
        with urllib.request.urlopen(url, timeout=60) as r: open(f, 'wb').write(r.read())
    return f

def motore(f):
    righe = {}
    for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if r and r[0].startswith('=== ARCHIVIO'): break
        if r and r[0] and r[0] not in righe: righe[r[0]] = r
    ids, out = righe['ID PARTITA'], {}
    for c in range(1, len(ids), 4):
        pm = [qb.num(righe[f'Maestro: {k} del motore'][c]) if f'Maestro: {k} del motore' in righe else None for k in ('1', 'X', '2')]
        out[ids[c]] = pm if None not in pm else None
    return out

M, PM = [], {}
for cart in args:
    for f in sorted(glob.glob(os.path.join(cart, 'Backtest_V97_*.csv'))):
        paese = re.match(r'Backtest_V97_([A-Z]{3})_', os.path.basename(f)).group(1)
        if paese not in CINQUE and paese not in NEW: print(f'{os.path.basename(f)}: football-data non ha questa lega, salto'); continue
        for m in qb.leggi_csv(f): m['lega'] = paese; M.append(m)
        PM.update(motore(f))
righe = []
for paese in sorted({m['lega'] for m in M}):
    if paese in CINQUE:
        f = scarica(f'{CINQUE[paese]}_2627.csv', f'https://www.football-data.co.uk/mmz4281/2627/{CINQUE[paese]}.csv'); kH, kA, kh, ka = 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'
    else:
        f = scarica(f'{NEW[paese]}.csv', f'https://www.football-data.co.uk/new/{NEW[paese]}.csv'); kH, kA, kh, ka = 'Home', 'Away', 'HG', 'AG'
    for r in csv.DictReader(io.open(f, encoding='utf-8-sig', errors='replace')):
        if not r.get(kH) or not (r.get(kh) or '').strip().isdigit(): continue
        qc, fc = qb.prendi(r, ['AvgC', 'PSC', 'B365C'])
        righe.append(dict(lega=paese, data=qb.data(r['Date']), H=r[kH], A=r[kA], hg=int(r[kh]), ag=int(r[ka]), qc=qc, fc=fc))

per_data = collections.defaultdict(list)
for r in righe: per_data[(r['lega'], r['data'])].append(r)
vicine = lambda lg, d: sum((per_data.get((lg, d + dt.timedelta(days=k)), []) for k in (-1, 0, 1)), [])
cooc = collections.defaultdict(collections.Counter)
for m in M:
    for r in vicine(m['lega'], dt.date.fromisoformat(m['data'])):
        w = 1 if (r['hg'], r['ag']) == (m['hg'], m['ag']) else 0.01
        cooc[(m['lega'], m['H'])][r['H']] += w; cooc[(m['lega'], m['A'])][r['A']] += w
mappa = {k: c.most_common(1)[0][0] for k, c in cooc.items()}
Q, diversi, mancanti = [], 0, 0
for m in M:
    c = [r for r in vicine(m['lega'], dt.date.fromisoformat(m['data'])) if r['H'] == mappa.get((m['lega'], m['H'])) and r['A'] == mappa.get((m['lega'], m['A']))]
    if len(c) != 1 or not c[0]['qc']: mancanti += 1; continue
    if (c[0]['hg'], c[0]['ag']) != (m['hg'], m['ag']): diversi += 1; continue
    Q.append(dict(m, qc=c[0]['qc'], fc=c[0]['fc']))
n = len(Q)
print(f'partite in copia conforme {len(M)}: agganciate col punteggio uguale {n}, punteggio diverso {diversi}, non trovate {mancanti}')
print('per lega:', dict(collections.Counter(q['lega'] for q in Q)), '· chiusura da', dict(collections.Counter(q['fc'] for q in Q)))
y = np.array([q['out'] for q in Q])
P = np.array([q['p'] for q in Q], float); P /= P.sum(1, keepdims=True)
O = np.array([q['qc'] for q in Q], float); Mk = 1 / O; marg = Mk.sum(1) - 1; Mk /= Mk.sum(1, keepdims=True)
pe = [PM.get(q['id']) for q in Q]; okE = np.array([x is not None for x in pe])
E = np.array([x if x is not None else [1/3] * 3 for x in pe], float); E /= E.sum(1, keepdims=True)
idx = np.arange(n); Y = np.zeros((n, 3)); Y[idx, y] = 1
pc = lambda x: f'{100 * x:.1f}'
se2 = lambda v: 200 * math.sqrt(max(v.mean() * (1 - v.mean()), 1e-9) / len(v)) if len(v) else float('nan')
ll = lambda X: -np.log(np.clip(X[idx, y], 1e-12, 1))
print(f'\nmargine medio {100 * marg.mean():.2f}% · logloss 1X2 Scanner {ll(P).mean():.4f}, mercato {ll(Mk).mean():.4f} '
      f'(Scanner meno mercato {1000 * (ll(P) - ll(Mk)).mean():+.2f}‰ ±{2000 * (ll(P) - ll(Mk)).std() / math.sqrt(n):.2f})')
print(f'prese: Scanner {pc((P.argmax(1) == y).mean())}%, favorito del mercato {pc((Mk.argmax(1) == y).mean())}%')

fav = np.where(Mk[:, 0] >= Mk[:, 2], 0, 2); dog = 2 - fav
d = 100 * (P[idx, fav] - Mk[idx, fav])
print(f'\n1. Per fascia della differenza Scanner meno mercato sul favorito del mercato (in punti; mediana |d| {np.median(np.abs(d)):.1f}).')
print('   negativa: lo Scanner crede meno del mercato al favorito, cioe\' vede piu\' sorpresa')
print(f'   {"fascia":>12} {"partite":>7} | {"vince il favorito: mercato / Scanner / esce ±2se":>48} | {"pareggio: mercato / esce":>24} | {"vince lo sfavorito: mercato / Scanner / esce":>44}')
for a, b in ((-99, -8), (-8, -4), (-4, -1.5), (-1.5, 1.5), (1.5, 4), (4, 8), (8, 99)):
    k = (d >= a) & (d < b)
    if not k.any(): continue
    vf = (y[k] == fav[k]).astype(float); vd = (y[k] == dog[k]).astype(float); vx = (y[k] == 1).astype(float)
    nome = f'{a:+g}…{b:+g}'.replace('-99…', 'sotto ').replace('…+99', ' e oltre')
    print(f'   {nome:>12} {k.sum():>7} | {pc(Mk[k][np.arange(k.sum()), fav[k]].mean()):>17} / {pc(P[k][np.arange(k.sum()), fav[k]].mean())} / {pc(vf.mean())} ±{se2(vf):.1f}'
          f' | {pc(Mk[k, 1].mean()):>14} / {pc(vx.mean())} ±{se2(vx):.1f} | {pc(Mk[k][np.arange(k.sum()), dog[k]].mean()):>17} / {pc(P[k][np.arange(k.sum()), dog[k]].mean())} / {pc(vd.mean())} ±{se2(vd):.1f}')

pk = P.argmax(1); dv = pk != Mk.argmax(1)
print(f'\n2. Favoriti diversi: {dv.sum()} partite su {n} ({pc(dv.mean())}%).')
if dv.any():
    v1 = (y[dv] == pk[dv]).astype(float); v2 = (y[dv] == Mk[dv].argmax(1)).astype(float); vx = (y[dv] == 1).astype(float)
    print(f'   vince il pick dello Scanner {pc(v1.mean())}% ±{se2(v1):.1f} (lo Scanner diceva {pc(P[dv][np.arange(dv.sum()), pk[dv]].mean())}, il mercato {pc(Mk[dv][np.arange(dv.sum()), pk[dv]].mean())})'
          f' · vince il favorito del mercato {pc(v2.mean())}% ±{se2(v2):.1f} (il mercato diceva {pc(Mk[dv].max(1).mean())}, lo Scanner {pc(P[dv][np.arange(dv.sum()), Mk[dv].argmax(1)].mean())})'
          f' · pareggio {pc(vx.mean())}% (mercato {pc(Mk[dv, 1].mean())})')

print('\n3. Ogni esito (1, X o 2) a cui lo Scanner da\' piu\' del mercato, giocato alla quota media di chiusura (una giocata per partita: l\'esito con lo scarto piu\' grande).')
g = 100 * (P - Mk); best = g.argmax(1); gb = g[idx, best]
print(f'   {"scarto":>10} {"giocate":>7} | {"Scanner / mercato / esce ±2se":>30} | {"resa ±2se":>14} | quota media')
for a, b in ((0, 3), (3, 5), (5, 8), (8, 12), (12, 99)):
    k = (gb >= a) & (gb < b)
    if not k.any(): continue
    vk = (y[k] == best[k]).astype(float); r = vk * O[k][np.arange(k.sum()), best[k]] - 1
    print(f'   {f"+{a}…+{b}".replace("…+99", " e oltre"):>10} {k.sum():>7} | {pc(P[k][np.arange(k.sum()), best[k]].mean()):>14} / {pc(Mk[k][np.arange(k.sum()), best[k]].mean())} / {pc(vk.mean())} ±{se2(vk):.1f}'
          f' | {100 * r.mean():+6.1f}% ±{200 * r.std() / math.sqrt(k.sum()):.1f} | {O[k][np.arange(k.sum()), best[k]].mean():.2f}')
r = (y == Mk.argmax(1)) * O[idx, Mk.argmax(1)] - 1
print(f'   per confronto, sempre il favorito del mercato: {100 * r.mean():+.1f}% ±{200 * r.std() / math.sqrt(n):.1f}')
print('\n   Il favorito e lo sfavorito del mercato giocati alla chiusura, per fascia della tabella 1:')
for a, b in ((-99, -8), (-8, -4), (-4, -1.5), (-1.5, 1.5), (1.5, 4), (4, 8), (8, 99)):
    k = (d >= a) & (d < b)
    if not k.any(): continue
    rf = (y[k] == fav[k]) * O[k][np.arange(k.sum()), fav[k]] - 1; rd = (y[k] == dog[k]) * O[k][np.arange(k.sum()), dog[k]] - 1
    nome = f'{a:+g}…{b:+g}'.replace('-99…', 'sotto ').replace('…+99', ' e oltre')
    print(f'   {nome:>12} {k.sum():>7} | favorito {100 * rf.mean():+6.1f}% ±{200 * rf.std() / math.sqrt(k.sum()):.1f} (quota {O[k][np.arange(k.sum()), fav[k]].mean():.2f})'
          f' | sfavorito {100 * rd.mean():+6.1f}% ±{200 * rd.std() / math.sqrt(k.sum()):.1f} (quota {O[k][np.arange(k.sum()), dog[k]].mean():.2f})')

nd = y != 1
def peso(X):
    lq = np.log(Mk[nd, 0] / Mk[nd, 2]); lx = np.log(X[nd, 0] / X[nd, 2]) - lq; t = (y[nd] == 0).astype(float)
    A = np.c_[np.ones(nd.sum()), lq, lx]; b = np.zeros(3)
    for _ in range(50):
        p = 1 / (1 + np.exp(-A @ b)); W = p * (1 - p); H = A.T @ (A * W[:, None]) + 1e-9 * np.eye(3); b += np.linalg.solve(H, A.T @ (t - p))
    return b, np.sqrt(np.diag(np.linalg.inv(H)))
b, e = peso(P)
print(f'\n4. 1 contro 2 sulle {nd.sum()} partite senza pari: logit = a + b·log(p1/p2) del mercato + c·(Scanner meno mercato)')
print(f'   Scanner: a {b[0]:+.3f}, b {b[1]:.3f} ±{e[1]:.3f}, c {b[2]:+.3f} ±{e[2]:.3f} (z {b[2] / e[2]:+.2f})')
if okE.all():
    b, e = peso(E); print(f'   motore prima del maestro: c {b[2]:+.3f} ±{e[2]:.3f} (z {b[2] / e[2]:+.2f})')
for lg in sorted({q['lega'] for q in Q}):
    k = np.array([q['lega'] == lg for q in Q]); kd = dv & k
    print(f'   {lg}: {k.sum()} partite, favoriti diversi {kd.sum()}, pick dello Scanner {pc((y[kd] == pk[kd]).mean()) if kd.any() else "--"}% contro favorito del mercato {pc((y[kd] == Mk[kd].argmax(1)).mean()) if kd.any() else "--"}%'
          f' · logloss Scanner meno mercato {1000 * (ll(P)[k] - ll(Mk)[k]).mean():+.1f}‰')
