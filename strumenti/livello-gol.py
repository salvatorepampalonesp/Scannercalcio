# Il livello dei gol (AGENTS.md, Il livello dei gol: la regola).
#
#   python3 strumenti/livello-gol.py batch/livello [--fattore 1.051] [--allena batch48 batch4 batch/nuove]
#
# Rifa' dai CSV del Comparatore la matrice dei gol del motore (lambda di ruolo e rho) con e senza il
# fattore sui due lambda, e applica la regola: la somma delle logloss di Over 2.5 e Goal, col fattore
# contro senza, migliora con z <= -2 sull'insieme e in almeno due terzi delle leghe con 100 partite o
# piu'. Con --allena stampa anche gol/lambda sulle partite di stima (il fattore della regola). Dal b63
# i lambda del CSV hanno gia' il fattore (riga «Ambito: livello dei gol»): lo strumento lo toglie.
# Esito: passa (b63), -3.80 per mille su 6.472 partite di nove leghe mai aperte, z -2.99, 6 su 9.
import os, sys, glob, math, collections, importlib.util
import numpy as np
QUI = os.path.dirname(os.path.abspath(__file__))
_s = importlib.util.spec_from_file_location('qm', os.path.join(QUI, 'quote-matrice.py'))
qm = importlib.util.module_from_spec(_s); _s.loader.exec_module(qm); qg, qb = qm.qg, qm.qb

RIGA_F = "Ambito: livello dei gol (fattore gia' nei lambda di ruolo)"

def fattori(f):
    # dal b63 i lambda di ruolo del CSV hanno gia' dentro GOALS_LEVEL: qui si tolgono, per misurare
    # sempre il motore senza fattore contro il motore col fattore
    ids = fx = None
    for r in qb.csv.reader(qb.io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if r and r[0] == 'ID PARTITA': ids = r
        elif r and r[0] == RIGA_F: fx = r
        elif r and r[0].startswith('=== ARCHIVIO'): break
    if not ids or not fx: return {}
    return {ids[c]: qb.num(fx[c]) for c in range(1, len(ids), 4) if ids[c] and c < len(fx) and qb.num(fx[c])}

def carica(dirs):
    M = []
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, '*.csv'))):
            FX = fattori(f)
            for m in qb.leggi_csv(f):
                m['fx'] = FX.get(m['id'], 1.0)
                if m['lam'][0] and m['lam'][1]: m['lam'] = [x / m['fx'] for x in m['lam']]
                M.append(m)
    M = list({m['id']: m for m in M}.values())
    return [m for m in M if m['lam'][0] and m['lam'][1] and m['rho'] is not None]

def misura(M, F):
    lh = np.array([m['lam'][0] for m in M]); la = np.array([m['lam'][1] for m in M]); rho = np.array([m['rho'] for m in M])
    hg = np.array([m['hg'] for m in M]); ag = np.array([m['ag'] for m in M]); lega = np.array([m['lega'] for m in M])
    E, C = qg.matrici(lh, la, rho), qg.matrici(F * lh, F * la, rho); E0, C0 = qg.mercati(E), qg.mercati(C)
    fx = np.array([m['fx'] for m in M]); X0 = qg.mercati(qg.matrici(fx * lh, fx * la, rho))   # la matrice com'era nel CSV
    dev = max(abs(100 * X0[k] - np.array([m['gol'][c] for m in M])).max() for k, c in (('o25', 'Over 2.5'), ('gg', 'GG (da matrice)')))
    Y = {'o15': hg + ag > 1, 'o25': hg + ag > 2, 'o35': hg + ag > 3, 'gg': (hg > 0) & (ag > 0)}
    Y = {k: v.astype(float) for k, v in Y.items()}
    return dict(E0=E0, C0=C0, E=E, C=C, Y=Y, hg=hg, ag=ag, lega=lega, dev=dev, lam=lh + la)

def main():
    a = sys.argv[1:]; F = 1.051
    if '--fattore' in a: i = a.index('--fattore'); F = float(a[i + 1]); del a[i:i + 2]
    allena = []
    if '--allena' in a: i = a.index('--allena'); allena = a[i + 1:]; a = a[:i]
    if allena:
        A = carica(allena); g = sum(m['hg'] + m['ag'] for m in A); l = sum(m['lam'][0] + m['lam'][1] for m in A)
        print(f'--allena: {len(A)} partite, gol/lambda {g / l:.4f}')
    M = carica(a); R = misura(M, F); lega = R['lega']
    print(f'\n=== IL TEST: {len(M)} partite, fattore {F} · prova di coincidenza della matrice del motore: scarto massimo {R["dev"]:.3f} punti ===')
    d = (qg.ll(R['C0']['o25'], R['Y']['o25']) + qg.ll(R['C0']['gg'], R['Y']['gg'])) - (qg.ll(R['E0']['o25'], R['Y']['o25']) + qg.ll(R['E0']['gg'], R['Y']['gg']))
    z = d.mean() / d.std(ddof=1) * math.sqrt(len(d))
    per = {l: (d[lega == l].mean(), (lega == l).sum()) for l in sorted(set(lega))}
    grandi = {l: v for l, v in per.items() if v[1] >= 100}; meglio = sum(v[0] < 0 for v in grandi.values())
    for l, (v, n) in per.items():
        s = lega == l; g = (R['hg'][s] + R['ag'][s]).sum() / R['lam'][s].sum()
        print(f'  {l:18s} {n:5d}  Over+Goal {1000 * v:+7.2f}‰  gol/lambda {g:.3f}  Over prev-reale {100 * (R["E0"]["o25"][s].mean() - R["Y"]["o25"][s].mean()):+5.1f} -> {100 * (R["C0"]["o25"][s].mean() - R["Y"]["o25"][s].mean()):+5.1f}'
              f'  Goal {100 * (R["E0"]["gg"][s].mean() - R["Y"]["gg"][s].mean()):+5.1f} -> {100 * (R["C0"]["gg"][s].mean() - R["Y"]["gg"][s].mean()):+5.1f}')
    soglia = math.ceil(2 * len(grandi) / 3)
    print(f'insieme: {1000 * d.mean():+.2f}‰ (z {z:+.2f}) · meglio in {meglio}/{len(grandi)} leghe con 100+ partite (servono {soglia})')
    print('ESITO:', 'PASSA' if z <= -2 and meglio >= soglia else 'NON PASSA')
    print('\n=== descrittivi ===')
    for k, nome in (('o25', 'Over 2.5'), ('gg', 'Goal'), ('o15', 'Over 1.5'), ('o35', 'Over 3.5')):
        qm.confronto(nome, qg.ll(R['E0'][k], R['Y'][k]), qg.ll(R['C0'][k], R['Y'][k]), lega)
    L0, L1 = qm.perdite(R['E'], R['hg'], R['ag']), qm.perdite(R['C'], R['hg'], R['ag'])
    for k in L0: qm.confronto(k, L0[k], L1[k], lega)
    g = (R['hg'] + R['ag']).sum() / R['lam'].sum()
    print(f'gol/lambda {g:.4f} · Over previsto {100 * R["E0"]["o25"].mean():.1f} -> {100 * R["C0"]["o25"].mean():.1f}, reale {100 * R["Y"]["o25"].mean():.1f}'
          f' · Goal {100 * R["E0"]["gg"].mean():.1f} -> {100 * R["C0"]["gg"].mean():.1f}, reale {100 * R["Y"]["gg"].mean():.1f}')

if __name__ == '__main__':
    main()
