# Il rating di pressione: la curva /momentum della PitchAPI, corretta per l'avversario come l'Elo, sopra il maestro mercato.
#
#   python3 strumenti/pressione.py                     # esplorazione fuori lega sulle leghe del maestro
#   python3 strumenti/pressione.py --allena            # stima il maestro con la pressione e scrive pressione_regola.json
#   python3 strumenti/pressione.py --prova <cartelle>  # il test registrato (vedi AGENTS.md, Il rating di pressione: la regola)
#
# Servono i file di batch/tiri (strumenti/tiri.py --scarica): di ogni partita dell'archivio di lega la media della curva di
# pressione (positiva = casa). Il rating: pressione media ~ R_casa - R_trasf + H; dopo ogni partita R_casa += K*e,
# R_trasf -= K*e, H += KH*e, con e = pressione meno la prevista. Il valore di una partita e' R_casa - R_trasf prima di
# lei; manca (e il maestro usa la mediana) se una delle due squadre ha meno di MIN_PARTITE partite con la pressione.
import os, sys, json, glob, math, collections, importlib.util
import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__)); RADICE = os.path.dirname(QUI)
def _mod(nome, f):
    s = importlib.util.spec_from_file_location(nome, os.path.join(QUI, f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
ma = _mod('maestro', 'maestro.py')
FILE_REGOLA = os.path.join(QUI, 'pressione_regola.json')
K, KH, H0, MIN_PARTITE = 0.15, 0.03, 3.5, 6
TIRI = os.path.join(RADICE, 'batch', 'tiri')

_cache = {}
def pressione(mid):
    if mid not in _cache:
        v = None; f = os.path.join(TIRI, mid + '.json')
        if os.path.exists(f):
            try:
                mo = [q[1] for q in (json.load(open(f)).get('mo') or []) if q and q[1] is not None]
                if mo: v = float(np.mean(mo))
            except ValueError: v = None
        _cache[mid] = v
    return _cache[mid]

def archivio(f):
    A = []
    for l in open(f, encoding='utf-8'):
        if not l.startswith('ARCHIVIO #'): continue
        p = l.rstrip('\n').split(';')
        if p[4] != 'finished' or p[9] == '': continue
        A.append((p[3], p[1], p[5], p[7]))
    A.sort(); return A

def ids_file(f):
    for l in open(f, encoding='utf-8'):
        if l.startswith('ID PARTITA;'): return [x for x in l.rstrip('\n').split(';')[1:] if x]
    return []

def rating(A, k=K, kh=KH, h0=H0, minimo=MIN_PARTITE):
    # A in ordine di orario; per ogni partita il valore prima di lei (una squadra non gioca due volte nello stesso giorno)
    R = collections.defaultdict(float); N = collections.Counter(); H = h0; prima = {}
    for ora, mid, h, a in A:
        prima[mid] = (R[h] - R[a]) if N[h] >= minimo and N[a] >= minimo else None
        x = pressione(mid)
        if x is None: continue
        e = x - (R[h] - R[a] + H); R[h] += k * e; R[a] -= k * e; H += kh * e; N[h] += 1; N[a] += 1
    return prima

def valori(cartelle, **kw):
    out = {}
    for c in cartelle:
        for f in sorted(glob.glob(os.path.join(RADICE, c, '*.csv'))):
            pr = rating(archivio(f), **kw)
            for mid in ids_file(f):
                if mid in pr: out[mid] = pr[mid]
    return out

def _ridge(Xa, Ya, Xb):
    mu, sd = Xa.mean(0), Xa.std(0); sd[sd < 1e-9] = 1
    Z = np.c_[np.ones(len(Xa)), (Xa - mu) / sd]; Rg = ma.ALFA * np.eye(Z.shape[1]); Rg[0, 0] = 0
    return np.c_[np.ones(len(Xb)), (Xb - mu) / sd] @ np.linalg.solve(Z.T @ Z + Rg, Z.T @ Ya)

def _ll1x2(T, y3):
    P = ma.soft(T[:, 0], T[:, 1]); return -np.log(P[np.arange(len(P)), y3])

def esplora():
    Q, MM, nomi, X, med, Y = ma._dati()
    lg = np.array([q['lega'] for q in Q]); hg = np.array([m['hg'] for m in MM]); ag = np.array([m['ag'] for m in MM])
    y3 = np.where(hg > ag, 0, np.where(hg == ag, 1, 2)); rho = X[:, nomi.index('rho')]
    P0 = np.zeros_like(Y)
    for l in sorted(set(lg)): t = lg == l; P0[t] = _ridge(X[~t], Y[~t], X[t])
    G0 = ma.perdite_gol(ma.qg.matrici(np.exp(P0[:, 2]), np.exp(P0[:, 3]), rho), hg, ag); L0 = _ll1x2(P0, y3)
    print(f'{len(Q)} partite di {len(set(lg))} leghe; il maestro fuori lega contro il maestro con la pressione')
    for k in (0.05, 0.10, 0.15, 0.20, 0.30):
        V = valori(ma.ALLENA, k=k, kh=k / 5)
        x = np.array([V.get(m['id']) for m in MM], dtype=float); cop = (~np.isnan(x)).mean()
        x = np.where(np.isnan(x), np.nanmedian(x), x); X2 = np.c_[X, x]; P1 = np.zeros_like(Y)
        for l in sorted(set(lg)): t = lg == l; P1[t] = _ridge(X2[~t], Y[~t], X2[t])
        G1 = ma.perdite_gol(ma.qg.matrici(np.exp(P1[:, 2]), np.exp(P1[:, 3]), rho), hg, ag)
        d = _ll1x2(P1, y3) - L0; de = G1['esatto'] - G0['esatto']; dg = G1['Over 2.5'] + G1['Goal'] - G0['Over 2.5'] - G0['Goal']
        m1 = sum(d[lg == l].mean() < 0 for l in set(lg)); m2 = sum(de[lg == l].mean() < 0 for l in set(lg))
        print(f'  K {k:.2f} (copertura {100 * cop:.0f}%): 1X2 {1000 * d.mean():+.2f} per mille (z {ma.zeta(d):+.2f}, {m1}/{len(set(lg))})'
              f' · esatto {1000 * de.mean():+.2f} (z {ma.zeta(de):+.2f}, {m2}) · Over 2.5 + Goal {1000 * dg.mean():+.2f} (z {ma.zeta(dg):+.2f})')

def allena():
    Q, MM, nomi, X, med, Y = ma._dati(); V = valori(ma.ALLENA)
    x = np.array([V.get(m['id']) for m in MM], dtype=float)
    for m in MM: m['v']['pres'] = V.get(m['id'])
    nomi2 = nomi + ['pres']; X2, med2 = ma.matrice(MM, nomi2)
    reg = ma._stima(X2, med2, Y, nomi2); reg.update(partite=len(Q), leghe=sorted(set(q['lega'] for q in Q)), copertura=round(float((~np.isnan(x)).mean()), 4),
                                                    pressione=dict(K=K, KH=KH, H0=H0, minimo=MIN_PARTITE))
    json.dump(reg, open(FILE_REGOLA, 'w'), indent=1)
    print(f'{len(Q)} partite, pressione su {100 * reg["copertura"]:.1f}%; scritto', FILE_REGOLA)

def prova(dirs):
    reg0 = json.load(open(ma.FILE_REGOLA)); reg1 = json.load(open(FILE_REGOLA))
    M = ma.carica(dirs); V = valori(dirs)
    for m in M: m['v']['pres'] = V.get(m['id'])
    lg = np.array([m['lega'] for m in M]); hg = np.array([m['hg'] for m in M]); ag = np.array([m['ag'] for m in M])
    y3 = np.where(hg > ag, 0, np.where(hg == ag, 1, 2)); idx = np.arange(len(M))
    # dove il rating manca resta il maestro di oggi: la differenza li' e' zero
    cop = np.array([m['v']['pres'] is not None for m in M])
    T0 = ma.applica(M, reg0); T1 = np.where(cop[:, None], ma.applica(M, reg1), T0)
    P0 = ma.soft(T0[:, 0], T0[:, 1]); P1 = ma.soft(T1[:, 0], T1[:, 1])
    d = -np.log(P1[idx, y3]) + np.log(P0[idx, y3]); dp = (P1.argmax(1) == y3).astype(float) - (P0.argmax(1) == y3)
    leghe = sorted(set(lg)); grandi = [l for l in leghe if (cop & (lg == l)).sum() >= 100]
    print(f'{len(M)} partite di {len(leghe)} leghe; rating di pressione su {100 * cop.mean():.1f}%, {len(grandi)} leghe con almeno 100 partite col rating')
    meglio = sum(d[lg == l].mean() < 0 for l in grandi)
    print(f'\n=== 1X2: maestro con la pressione contro il maestro ===\n  logloss {1000 * d.mean():+.2f} per mille (z {ma.zeta(d):+.2f}), meglio in {meglio} leghe su {len(grandi)}'
          f' · prese {100 * (P0.argmax(1) == y3).mean():.2f} -> {100 * (P1.argmax(1) == y3).mean():.2f} ({100 * dp.mean():+.2f}, z {ma.zeta(dp):+.2f})')
    passa1 = ma.zeta(d) <= -2 and meglio > len(grandi) / 2 and ma.zeta(dp) >= -2
    print(f'  ESITO 1X2: {"PASSA" if passa1 else "NON PASSA"}')
    rho = np.array([m['v']['rho'] for m in M]); ok = (hg <= 10) & (ag <= 10)
    E = ma.perdite_gol(ma.qg.matrici(np.exp(T0[:, 2]), np.exp(T0[:, 3]), rho), hg, ag)
    D = ma.perdite_gol(ma.qg.matrici(np.exp(T1[:, 2]), np.exp(T1[:, 3]), rho), hg, ag)
    print('\n=== gol: matrice del maestro con la pressione contro quella del maestro ===')
    for k in E:
        dd = (D[k] - E[k])[ok]; mg = sum(dd[lg[ok] == l].mean() < 0 for l in grandi)
        print(f'  {k:16s} {1000 * dd.mean():+.2f} per mille (z {ma.zeta(dd):+.2f}), meglio in {mg} leghe su {len(grandi)}')
    de = (D['esatto'] - E['esatto'])[ok]; dg = ((D['Over 2.5'] + D['Goal']) - (E['Over 2.5'] + E['Goal']))[ok]
    passa2 = ma.zeta(de) <= -2 and sum(de[lg[ok] == l].mean() < 0 for l in grandi) > len(grandi) / 2 and dg.mean() <= 0
    print(f'  guardia Over 2.5 + Goal: {1000 * dg.mean():+.2f} per mille (z {ma.zeta(dg):+.2f})')
    print(f'  ESITO GOL: {"PASSA" if passa2 else "NON PASSA"}')
    print('\n=== per lega (descrittivo) ===')
    for l in leghe:
        k = lg == l; kk = k & ok
        print(f'  {l:34s} {k.sum():5d}  pressione {100 * cop[k].mean():5.1f}%  1X2 {1000 * d[k].mean():+7.2f}  esatto {1000 * (D["esatto"] - E["esatto"])[kk].mean():+7.2f}')
    print(f'\n  solo le partite col rating: 1X2 {1000 * d[cop].mean():+.2f} (z {ma.zeta(d[cop]):+.2f}), {cop.sum()} partite')
    return passa1, passa2

if __name__ == '__main__':
    os.chdir(RADICE)
    if '--allena' in sys.argv: allena()
    elif '--prova' in sys.argv: prova([a for a in sys.argv[1:] if not a.startswith('--')])
    else: esplora()
