# Il maestro coi bersagli tolti alla Shin (AGENTS.md, Il maestro coi bersagli di Shin: la regola).
#
#   python3 strumenti/maestro-shin.py                  # l'esplorazione sulle 14 leghe del maestro, fuori lega
#   python3 strumenti/maestro-shin.py --allena         # scrive maestro_regola_shin.json (stimato su tutte le 14 leghe)
#   python3 strumenti/maestro-shin.py --prova <cartelle>   # il test registrato: maestro_regola_shin.json contro maestro_regola.json
#
# Il maestro (b77) impara dal mercato l'1X2 di chiusura col margine tolto in proporzione: 1/q normalizzato. Cosi' il
# favorito risulta meno probabile di quanto e' (b54: il mercato in proporzione va allargato di 1.34), e il maestro
# eredita la timidezza. Il metodo di Shin toglie il margine supponendo che il bookmaker si difenda da chi sa di piu'
# (una quota z di scommettitori informati): carica piu' margine sugli sfavoriti. Per ogni partita z si trova per
# bisezione perche' le tre probabilita' sommino a 1.
import os, io, sys, json, math, contextlib, importlib.util
import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
def _mod(nome, f):
    s = importlib.util.spec_from_file_location(nome, os.path.join(QUI, f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
ma = _mod('ma', 'maestro.py'); qg = ma.qg
FILE_SHIN = os.path.join(QUI, 'maestro_regola_shin.json')
VARIANTE = None   # fissata dall'esplorazione: 'A' solo i bersagli dell'1X2, 'B' anche i lambda della matrice allineata

def shin(IP):
    # IP: le probabilita' implicite 1/q (n x 3). Le probabilita' di Shin, che sommano a 1.
    S = IP.sum(1)[:, None]
    f = lambda z: (np.sqrt(z ** 2 + 4 * (1 - z) * IP ** 2 / S) - z) / (2 * (1 - z))
    lo, hi = np.zeros((len(IP), 1)), np.full((len(IP), 1), 0.4)
    for _ in range(60):
        z = (lo + hi) / 2; s = f(z).sum(1, keepdims=True); lo = np.where(s > 1, z, lo); hi = np.where(s > 1, hi, z)
    P = f((lo + hi) / 2); return P / P.sum(1, keepdims=True)

def bersagli(Q, X, nomi, Y, variante):
    IP = np.array([[1 / v for v in q['qc']] for q in Q]); P = shin(IP); Yv = Y.copy()
    Yv[:, 0] = np.log(P[:, 0] / P[:, 1]); Yv[:, 1] = np.log(P[:, 2] / P[:, 1])
    if variante == 'B':
        OU = np.array([qg.ou(q['riga'], ['AvgC', 'PC', 'B365C'])[0] for q in Q])
        pov = (1 / OU[:, 0]) / (1 / OU[:, 0] + 1 / OU[:, 1]); rho = X[:, nomi.index('rho')]
        mh, ma_ = qg.allinea(pov, np.log(P[:, 0] / P[:, 2]), rho); Yv[:, 2] = np.log(mh); Yv[:, 3] = np.log(ma_)
    return Yv

def _dati():
    with contextlib.redirect_stdout(io.StringIO()): return ma._dati()

def _prevedi(reg, X):
    Z = np.c_[np.ones(len(X)), (X - np.array(reg['media'])) / np.array(reg['sd'])]; return Z @ np.array(reg['B'])

def esplora():
    Q, MM, nomi, X, med, Y = _dati(); lg = np.array([q['lega'] for q in Q]); leghe = sorted(set(lg))
    y = np.array([q['out'] for q in Q]); hg = np.array([q['hg'] for q in Q]); ag = np.array([q['ag'] for q in Q]); idx = np.arange(len(y))
    rho = X[:, nomi.index('rho')]; ok = (hg <= 10) & (ag <= 10)
    print(f'{len(Q)} partite di {len(leghe)} leghe')
    T = {}
    for nome, Yv in (('proporzione', Y), ('A', bersagli(Q, X, nomi, Y, 'A')), ('B', bersagli(Q, X, nomi, Y, 'B'))):
        T[nome] = np.zeros((len(y), 4))
        for l in leghe:
            te = lg == l; T[nome][te] = _prevedi(ma._stima(X[~te], med, Yv[~te], nomi), X[te])
    P0 = ma.soft(T['proporzione'][:, 0], T['proporzione'][:, 1]); G0 = ma.perdite_gol(qg.matrici(np.exp(T['proporzione'][:, 2]), np.exp(T['proporzione'][:, 3]), rho), hg, ag)
    for nome in ('A', 'B'):
        P1 = ma.soft(T[nome][:, 0], T[nome][:, 1]); d = -np.log(P1[idx, y]) + np.log(P0[idx, y])
        dp = (P1.argmax(1) == y).astype(float) - (P0.argmax(1) == y)
        print(f'\n=== variante {nome}, fuori lega, contro il maestro in proporzione ===')
        print(f'  1X2 {1000 * d.mean():+.2f} per mille (z {ma.zeta(d):+.2f}), meglio in {sum(d[lg == l].mean() < 0 for l in leghe)} leghe su {len(leghe)}'
              f' · prese {100 * dp.mean():+.2f} (z {ma.zeta(dp) if dp.std() > 0 else 0:+.2f})')
        G1 = ma.perdite_gol(qg.matrici(np.exp(T[nome][:, 2]), np.exp(T[nome][:, 3]), rho), hg, ag)
        for k in G0:
            dd = (G1[k] - G0[k])[ok]
            if dd.std() > 0: print(f'  {k:16s} {1000 * dd.mean():+.2f} per mille (z {ma.zeta(dd):+.2f})')
            else: print(f'  {k:16s} identico')
        for nm, P in (('proporzione', P0), (nome, P1)):
            nd = y != 1; x = np.log(P[nd, 0] / P[nd, 2]); yy = (y[nd] == 0).astype(float)
            b = 1.0
            for _ in range(30):
                p = 1 / (1 + np.exp(-b * x)); b += ((yy - p) * x).sum() / (p * (1 - p) * x * x).sum()
            pk = P.max(1); k = pk > 0.65
            print(f'    {nm:11s} pendenza 1 contro 2 {b:.3f} · pick sopra il 65%: {k.sum()} partite, previsto {100 * pk[k].mean():.1f}, esce {100 * (P.argmax(1) == y)[k].mean():.1f}'
                  f' · sfavorito previsto {100 * np.minimum(P[:, 0], P[:, 2]).mean():.2f}, vince {100 * np.where(P[:, 0] >= P[:, 2], y == 2, y == 0).mean():.2f}')

def allena():
    Q, MM, nomi, X, med, Y = _dati()
    reg = ma._stima(X, med, bersagli(Q, X, nomi, Y, VARIANTE), nomi)
    reg.update(partite=len(Q), leghe=sorted(set(q['lega'] for q in Q)), margine='shin', variante=VARIANTE)
    json.dump(reg, open(FILE_SHIN, 'w'), indent=1); print('scritto', FILE_SHIN)

def prova(dirs):
    r0 = json.load(open(ma.FILE_REGOLA)); r1 = json.load(open(FILE_SHIN))
    M = ma.carica(dirs); lg = np.array([m['lega'] for m in M]); hg = np.array([m['hg'] for m in M]); ag = np.array([m['ag'] for m in M])
    y = np.where(hg > ag, 0, np.where(hg == ag, 1, 2)); idx = np.arange(len(M)); ok = (hg <= 10) & (ag <= 10)
    T0, T1 = ma.applica(M, r0), ma.applica(M, r1)
    P0, P1 = ma.soft(T0[:, 0], T0[:, 1]), ma.soft(T1[:, 0], T1[:, 1])
    d = -np.log(P1[idx, y]) + np.log(P0[idx, y]); dp = (P1.argmax(1) == y).astype(float) - (P0.argmax(1) == y)
    leghe = sorted(set(lg)); grandi = [l for l in leghe if (lg == l).sum() >= 100]; meglio = sum(d[lg == l].mean() < 0 for l in grandi)
    print(f'{len(M)} partite di {len(leghe)} leghe ({len(grandi)} con almeno 100 partite)')
    print(f'\n=== il test: 1X2 del maestro di Shin contro quello del b77 ===\n  {1000 * d.mean():+.2f} per mille (z {ma.zeta(d):+.2f}), meglio in {meglio} leghe su {len(grandi)}'
          f' · prese {100 * (P0.argmax(1) == y).mean():.2f} -> {100 * (P1.argmax(1) == y).mean():.2f} (z {ma.zeta(dp) if dp.std() > 0 else 0:+.2f})')
    rho = np.array([m['v']['rho'] for m in M])
    G0 = ma.perdite_gol(qg.matrici(np.exp(T0[:, 2]), np.exp(T0[:, 3]), rho), hg, ag); G1 = ma.perdite_gol(qg.matrici(np.exp(T1[:, 2]), np.exp(T1[:, 3]), rho), hg, ag)
    de = (G1['esatto'] - G0['esatto'])[ok]
    print(f'  guardia, risultato esatto: {1000 * de.mean():+.2f} per mille' + (f' (z {ma.zeta(de):+.2f})' if de.std() > 0 else ''))
    passa = ma.zeta(d) <= -2 and meglio > len(grandi) / 2 and (dp.std() == 0 or ma.zeta(dp) >= -2) and de.mean() <= 0
    print(f'  ESITO: {"PASSA" if passa else "NON PASSA"}')
    print('\n=== descrittivi ===')
    for l in leghe:
        k = lg == l; print(f'  {l:34s} {k.sum():5d}  1X2 {1000 * d[k].mean():+7.2f}')
    for k_ in G0:
        dd = (G1[k_] - G0[k_])[ok]
        if dd.std() > 0: print(f'  {k_:16s} {1000 * dd.mean():+.2f} per mille (z {ma.zeta(dd):+.2f})')
    for nm, P in (('b77', P0), ('Shin', P1)):
        pk = P.max(1)
        print(f'  {nm}: pick {100 * (P.argmax(1) == y).mean():.2f}% con probabilita\' media {100 * pk.mean():.1f}%'
              f' · sfavorito previsto {100 * np.minimum(P[:, 0], P[:, 2]).mean():.2f}, vince {100 * np.where(P[:, 0] >= P[:, 2], y == 2, y == 0).mean():.2f}')
        for a, b in ((0, .45), (.45, .55), (.55, .65), (.65, 1.01)):
            k = (pk >= a) & (pk < b)
            if k.sum() > 50: print(f'    pick {int(100 * a)}-{min(100, int(100 * b))}%: {k.sum()} partite, previsto {100 * pk[k].mean():.1f}, esce {100 * (P.argmax(1) == y)[k].mean():.1f}')
    return passa

if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '--allena': allena()
    elif a and a[0] == '--prova': prova(a[1:])
    else: esplora()
