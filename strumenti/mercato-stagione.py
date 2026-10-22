# Lo Scanner contro il bookmaker su una stagione in corso, e quanto del mercato il maestro ricostruisce dalle statistiche
# (AGENTS.md, Il motore contro il mercato, «Il 2026/27, e quanto del mercato sta nelle statistiche»).
#
#   python3 strumenti/mercato-stagione.py batch/2627b85 [--quote batch/quote-2627b85] [--r2]
#
# Aggancia le partite in copia conforme dei CSV alle quote di chiusura di football-data della stagione 2026/27
# (scaricate nella cartella --quote se mancano; non tocca batch/quote, che tiene i file dei test registrati) e
# confronta il pick dello Scanner (le righe 1, X, 2: il maestro), il motore prima del maestro e il favorito del
# mercato: prese, logloss, soglie, partite in disaccordo, per lega e per giornata. Con --r2 misura, fuori lega sulle
# 14 leghe dell'allenamento del maestro, quanta parte dell'1X2 e dei lambda del mercato il maestro ricostruisce.
import os, sys, io, csv, glob, math, collections, contextlib, importlib.util, urllib.request, datetime as dt
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
s = importlib.util.spec_from_file_location('qb', 'strumenti/quote-bookmaker.py'); qb = importlib.util.module_from_spec(s); s.loader.exec_module(qb)
args = sys.argv[1:]; FD = 'batch/quote-2627b85'; R2 = '--r2' in args
if R2: args.remove('--r2')
if '--quote' in args: i = args.index('--quote'); FD = args[i + 1]; del args[i:i + 2]
CART = args[0]
os.makedirs(FD, exist_ok=True)
for cod in ('I1', 'E0', 'SP1', 'D1', 'F1'):
    f = os.path.join(FD, f'{cod}_2627.csv')
    if not os.path.exists(f):
        with urllib.request.urlopen(f'https://www.football-data.co.uk/mmz4281/2627/{cod}.csv', timeout=60) as r: open(f, 'wb').write(r.read())
# 1X2 del motore prima del maestro e giornata
def extra(f):
    righe = collections.defaultdict(list); arch = []; dentro = False; stag = None
    for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if r and r[0].startswith('=== ARCHIVIO'): dentro = True; stag = r[0].split('database ')[1].split(',')[0]; continue
        if dentro:
            if r and r[0].startswith('ARCHIVIO #'): arch.append(r)
            continue
        if r and r[0]: righe[r[0]].append(r)
    g = lambda k: righe[k][0] if k in righe else None
    ids = g('ID PARTITA'); out = {}
    sel = sorted([r for r in arch if r[2] == stag and r[4] == 'finished'], key=lambda r: (r[3], int(r[0].split('#')[1])))
    cnt, G = collections.Counter(), {}
    for r in sel: cnt[r[5]] += 1; cnt[r[7]] += 1; G[r[1]] = max(cnt[r[5]], cnt[r[7]])
    for c in range(1, len(ids), 4):
        if not ids[c]: continue
        v = lambda k: g(k)[c] if g(k) and len(g(k)) > c else None
        pm = [qb.num(v(f'Maestro: {k} del motore')) for k in ('1', 'X', '2')]
        out[ids[c]] = dict(pm=pm if None not in pm else None, g=G.get(ids[c]))
    return out
M, E = [], {}
for f in sorted(glob.glob(os.path.join(CART, '*.csv'))):
    M += qb.leggi_csv(f); E.update(extra(f))
righe = []
for cod, lg in qb.COD.items():
    p = os.path.join(FD, f'{cod}_2627.csv')
    if not os.path.exists(p): continue
    for r in csv.DictReader(io.open(p, encoding='utf-8-sig', errors='replace')):
        if not r.get('HomeTeam') or not r.get('FTHG'): continue
        qc, fc = qb.prendi(r, ['AvgC', 'PSC', 'B365C'])
        righe.append(dict(lega=lg, data=qb.data(r['Date']), H=r['HomeTeam'], A=r['AwayTeam'], hg=int(r['FTHG']), ag=int(r['FTAG']), qc=qc, fc=fc, qp=None, riga=r))
def aggancia(M, righe):
    per_data = collections.defaultdict(list)
    for r in righe: per_data[(r['lega'], r['data'])].append(r)
    vicine = lambda lg, d: sum((per_data.get((lg, d + dt.timedelta(days=k)), []) for k in (-1, 0, 1)), [])
    cooc = collections.defaultdict(collections.Counter)
    for m in M:
        for r in vicine(m['lega'], dt.date.fromisoformat(m['data'])):
            w = 1 if (r['hg'], r['ag']) == (m['hg'], m['ag']) else 0.01
            cooc[(m['lega'], m['H'])][r['H']] += w; cooc[(m['lega'], m['A'])][r['A']] += w
    mappa = {k: c.most_common(1)[0][0] for k, c in cooc.items()}
    out, diversi, mancanti = [], 0, 0
    for m in M:
        c = [r for r in vicine(m['lega'], dt.date.fromisoformat(m['data'])) if r['H'] == mappa.get((m['lega'], m['H'])) and r['A'] == mappa.get((m['lega'], m['A']))]
        if len(c) != 1 or not c[0]['qc']: mancanti += 1; continue
        if (c[0]['hg'], c[0]['ag']) != (m['hg'], m['ag']): diversi += 1; continue
        out.append(dict(m, qc=c[0]['qc'], fc=c[0]['fc'], riga=c[0]['riga']))
    print(f'partite {len(M)}: agganciate {len(out)}, punteggio diverso {diversi}, non trovate {mancanti}')
    return out
Q = aggancia(M, righe)
y = np.array([q['out'] for q in Q]); n = len(Q); idx = np.arange(n)
P = np.array([q['p'] for q in Q]); P /= P.sum(1, keepdims=True)
PM = np.array([[1 / x for x in q['qc']] for q in Q]); PM /= PM.sum(1, keepdims=True)
pe = [E[q['id']]['pm'] for q in Q]; ok = np.array([x is not None for x in pe])
PE = np.array([x if x is not None else [1/3]*3 for x in pe], float); PE /= PE.sum(1, keepdims=True)
G = np.array([E[q['id']]['g'] or 0 for q in Q])
def riga(nome, X, k=slice(None)):
    X, yy = X[k], y[k]; pk = X.argmax(1); hit = pk == yy
    ll = -np.log(X[np.arange(len(yy)), yy]); br = ((X - np.eye(3)[yy]) ** 2).sum(1)
    print(f'  {nome:22s} pick {100*hit.mean():5.1f}% (prob. media del pick {100*X.max(1).mean():4.1f})  logloss {ll.mean():.4f}  Brier {br.mean():.4f}  pick X {int((pk==1).sum())}')
    return ll
print(f'\n{n} partite agganciate alle quote di chiusura')
for nome, k in (('tutte', slice(None)), ('giornate 1-5', G <= 5), ('dalla 6a', G > 5)):
    print(f'\n== {nome} ({int(np.ones(n)[k].sum())} partite) ==')
    a = riga('maestro (lo Scanner)', P, k); b = riga('mercato, chiusura', PM, k)
    if ok[k].all() if isinstance(k, np.ndarray) else ok.all(): riga('motore prima del maestro', PE, k)
    d = a - b; print(f'  maestro meno mercato: {1000*d.mean():+.1f} per mille (±{2000*d.std()/math.sqrt(len(d)):.1f})')
# disaccordo sul favorito
fa = np.where(P[:, 0] >= P[:, 2], 0, 2); fm = np.where(PM[:, 0] >= PM[:, 2], 0, 2); dis = fa != fm
print(f'\nfavorito diverso fra maestro e mercato: {dis.sum()} partite; vince il favorito del maestro {int((y[dis]==fa[dis]).sum())}, quello del mercato {int((y[dis]==fm[dis]).sum())}, pari {int((y[dis]==1).sum())}')
# quanto sono "sbagliate": esito con probabilita' sotto il 25%
for nome, X in (('maestro', P), ('mercato', PM)):
    pr = X[idx, y]
    print(f'{nome}: esito uscito con probabilita\' sotto il 25%: {100*(pr<.25).mean():.1f}% delle partite; sotto il 20%: {100*(pr<.20).mean():.1f}%; probabilita\' media dell\'esito uscito {100*pr.mean():.1f}%')
print(f'\npareggi reali {100*(y==1).mean():.1f}% (maestro {100*P[:,1].mean():.1f}, mercato {100*PM[:,1].mean():.1f}); casa {100*(y==0).mean():.1f}% (maestro {100*P[:,0].mean():.1f}, mercato {100*PM[:,0].mean():.1f})')
# per lega
print()
for l in sorted(set(q['lega'] for q in Q)):
    k = np.array([q['lega'] == l for q in Q])
    print(f'  {l:15s} {k.sum():3d}  pick maestro {100*(P[k].argmax(1)==y[k]).mean():5.1f}  mercato {100*(PM[k].argmax(1)==y[k]).mean():5.1f}  logloss {(-np.log(P[k][np.arange(k.sum()),y[k]])).mean():.3f} / {(-np.log(PM[k][np.arange(k.sum()),y[k]])).mean():.3f}')
print('\nsoglie sul pick (quante partite, quante prese):')
for t in (.45, .50, .55, .60, .65):
    for nome, X in (('maestro', P), ('mercato', PM)):
        k = X.max(1) >= t
        if k.sum(): print(f'  {nome} >= {int(100*t)}%: {k.sum():3d} partite, previsto {100*X[k].max(1).mean():4.1f}, prese {100*(X[k].argmax(1)==y[k]).mean():5.1f}%', end='')
    print()
# il favorito netto che perde
for nome, X in (('maestro', P), ('mercato', PM)):
    k = X.max(1) >= .60
    print(f'{nome}: favorito al 60% o piu\' che perde: {int(((X[k].argmax(1)!=y[k])&(y[k]!=1)).sum())} su {k.sum()}, pareggia {int((y[k]==1).sum())}')
print('\nmaestro meno mercato per lega (logloss, per mille, ±2se), e con una neopromossa in campo:')
neo = {'LaLiga': {'Racing Santander', 'Deportivo A Coruña', 'Málaga'}}
ll_a = -np.log(P[idx, y]); ll_b = -np.log(PM[idx, y]); d = ll_a - ll_b
for l in sorted(set(q['lega'] for q in Q)):
    k = np.array([q['lega'] == l for q in Q])
    print(f'  {l:15s} {1000*d[k].mean():+6.1f} ±{2000*d[k].std()/math.sqrt(k.sum()):.1f}')
k = np.array([q['lega'] == 'LaLiga' and (q['H'] in neo['LaLiga'] or q['A'] in neo['LaLiga']) for q in Q]); k2 = np.array([q['lega'] == 'LaLiga' for q in Q]) & ~k
print(f'  LaLiga con neopromossa {k.sum()}: {1000*d[k].mean():+.1f} ±{2000*d[k].std()/math.sqrt(k.sum()):.1f}; senza {k2.sum()}: {1000*d[k2].mean():+.1f} ±{2000*d[k2].std()/math.sqrt(k2.sum()):.1f}')
print('  le 8 partite di LaLiga dove il maestro e il mercato distano di piu\':')
dist = np.abs(P - PM).max(1)
for i in np.argsort(-dist * k2.astype(float) - dist * k.astype(float))[:8]:
    q = Q[i]; print(f"    {q['data']} {q['H']} - {q['A']} {q['hg']}-{q['ag']}  maestro {100*P[i,0]:.0f}/{100*P[i,1]:.0f}/{100*P[i,2]:.0f}  mercato {100*PM[i,0]:.0f}/{100*PM[i,1]:.0f}/{100*PM[i,2]:.0f}")

if R2:
    sys.path.insert(0, os.path.join(ROOT, 'strumenti'))
    s = importlib.util.spec_from_file_location('ma', 'strumenti/maestro.py'); ma = importlib.util.module_from_spec(s); s.loader.exec_module(ma)
    with contextlib.redirect_stdout(io.StringIO()): Q, MM, nomi, X, med, Y = ma._dati()
    lg=np.array([q['lega'] for q in Q]); T=np.zeros_like(Y)
    for l in sorted(set(lg)):
        te=lg==l; reg=ma._stima(X[~te], med, Y[~te], nomi)
        Z=np.c_[np.ones(te.sum()), (X[te]-np.array(reg['media']))/np.array(reg['sd'])]; T[te]=Z@np.array(reg['B'])
    print(f'\n=== quanto del mercato il maestro ricostruisce: {len(Q)} partite di {len(set(lg))} leghe, fuori lega ===')
    for j,n in enumerate(['log p1/pX del mercato','log p2/pX del mercato','log lambda casa','log lambda trasf.']):
        r2=1-((Y[:,j]-T[:,j])**2).sum()/((Y[:,j]-Y[:,j].mean())**2).sum()
        print(f'  {n:24s} R2 {r2:.3f}  sd residuo {np.std(Y[:,j]-T[:,j]):.3f} su sd {np.std(Y[:,j]):.3f}')
    # 1 contro 2 del mercato
    a=Y[:,0]-Y[:,1]; b=T[:,0]-T[:,1]
    print(f'  log p1/p2 del mercato    R2 {1-((a-b)**2).sum()/((a-a.mean())**2).sum():.3f}  correlazione {np.corrcoef(a,b)[0,1]:.3f}')
    # il motore senza maestro: lgTarget-like = log p1/p2 del motore
    pm=np.array([[q['v']['l1x'], q['v']['l2x']] for q in Q]) if 'v' in Q[0] else None
    if pm is not None:
        c=pm[:,0]-pm[:,1]; print(f'  motore senza maestro: correlazione col mercato {np.corrcoef(a,c)[0,1]:.3f}')
    # in punti di probabilita': quanto sta lontano il maestro dal mercato, partita per partita
    def soft(t1,t2):
        E=np.exp(np.c_[t1,np.zeros(len(t1)),t2]); return E/E.sum(1,keepdims=True)
    Pm=soft(Y[:,0],Y[:,1]); Pt=soft(T[:,0],T[:,1])
    d=np.abs(Pm-Pt).max(1)*100
    print(f'  distanza massima fra maestro e mercato sull 1X2: mediana {np.median(d):.1f} punti, 90o percentile {np.percentile(d,90):.1f}, oltre 10 punti {100*(d>10).mean():.1f}% delle partite')
