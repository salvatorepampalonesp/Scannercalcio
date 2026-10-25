# Il maestro sbaglia di piu' quando i dati sono pochi? Calibrazione dell'1X2 per copertura dei dati
# (AGENTS.md, Cosa e' gia' stato provato, «Mostrare l'incertezza della stima»).
#
#   python3 strumenti/copertura.py <cartelle dei CSV>
#
# Sulle partite in copia conforme dei CSV del Comparatore: logloss 1X2, pick previsto contro uscito e pendenza 1 contro 2
# (logistica dell'esito sulle partite senza pari su log(p1/p2)), per le partite di ruolo della squadra che ne ha meno,
# per le partite nella serie dell'Elo della squadra che ne ha meno, e per l'origine delle metriche avanzate.
# L'1X2 e' quello delle righe 1, X, 2: dal b77 il maestro. Solo descrittivo.
import csv, io, glob, sys, math
import numpy as np
def num(s):
    try: return float(str(s).strip().replace('%','').replace(',','.'))
    except: return None
M = []
for cart in sys.argv[1:]:
    for f in sorted(glob.glob(cart + '/Backtest_V97_*.csv')):
        R = {}
        for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
            if r and r[0].startswith('=== ARCHIVIO'): break
            if r and r[0] and r[0] not in R: R[r[0]] = r
        ids = R['ID PARTITA']
        for c in range(1, len(ids), 4):
            if not ids[c] or not (R['COPIA CONFORME DELLO SCANNER'][c] or '').startswith('SI'): continue
            hg, ag = [int(x) for x in R['SCORE'][c].split('-')]
            g = lambda k: num(R[k][c]) if k in R and len(R[k]) > c else None
            p = [g(k) / 100 for k in ('1', 'X', '2')]
            M.append(dict(p=p, out=0 if hg > ag else (1 if hg == ag else 2), ruolo=min(g('Scope: partite di ruolo casa'), g('Scope: partite di ruolo trasf.')),
                          serie=min(g('Elo: partite nella serie casa'), g('Elo: partite nella serie trasferta')), orig=R['Origine metriche avanzate'][c], f=f))
def logit_fit(x, y):
    X = np.column_stack([np.ones_like(x), x]); b = np.zeros(2)
    for _ in range(30):
        q = 1 / (1 + np.exp(-X @ b)); W = q * (1 - q); H = X.T @ (X * W[:, None]); b += np.linalg.solve(H, X.T @ (y - q))
    return b, np.sqrt(np.diag(np.linalg.inv(H)))
def riga(nome, S):
    if len(S) < 30: print(f'{nome:<46} {len(S):>5}  troppo poche'); return
    ll = np.mean([-math.log(max(m['p'][m['out']], 1e-9)) for m in S])
    pk = [max(range(3), key=lambda k: m['p'][k]) for m in S]
    pp = np.mean([m['p'][k] for m, k in zip(S, pk)]); hit = np.mean([m['out'] == k for m, k in zip(S, pk)])
    se = math.sqrt(hit * (1 - hit) / len(S))
    nd = [m for m in S if m['out'] != 1]
    x = np.array([math.log(m['p'][0] / m['p'][2]) for m in nd]); y = np.array([1.0 if m['out'] == 0 else 0.0 for m in nd])
    b, e = logit_fit(x, y)
    print(f'{nome:<46} {len(S):>5}  logloss {ll:.4f}  pick previsto {pp*100:5.1f} esce {hit*100:5.1f} ±{2*se*100:4.1f}  pendenza 1c2 {b[1]:.2f} ±{2*e[1]:.2f}')
print(f'partite: {len(M)}')
riga('tutte', M)
riga('partite di ruolo: minimo < 6', [m for m in M if m['ruolo'] < 6])
riga('partite di ruolo: minimo 6-11', [m for m in M if 6 <= m['ruolo'] < 12])
riga('partite di ruolo: minimo 12 o piu', [m for m in M if m['ruolo'] >= 12])
riga('serie Elo: minimo < 15 (squadra nuova)', [m for m in M if m['serie'] < 15])
riga('serie Elo: minimo 15 o piu', [m for m in M if m['serie'] >= 15])
riga('metriche avanzate: riserva', [m for m in M if m['orig'] != 'motore'])
riga('metriche avanzate: dal motore', [m for m in M if m['orig'] == 'motore'])
bassa = lambda m: m['ruolo'] < 6 or m['serie'] < 15 or m['orig'] != 'motore'
riga('copertura bassa (una delle tre)', [m for m in M if bassa(m)])
riga('copertura piena', [m for m in M if not bassa(m)])
