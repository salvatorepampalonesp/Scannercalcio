# Quanto reggono le statistiche avanzate previste (AGENTS.md, Il mega-prompt, sezione 5). Solo descrittivo.
#
#   python3 strumenti/stat-previste.py                       le cartelle dei batch (batch48 batch4 batch/2627 batch/nuove batch/livello)
#   python3 strumenti/stat-previste.py <cartelle>
#
# Dai CSV del Comparatore, sulle sole partite in copia conforme con le metriche avanzate del motore
# (Origine metriche avanzate = motore), per ogni statistica: il livello (media prevista / media reale),
# la pendenza e la correlazione di reale ~ previsto per squadra, e le stesse sulla differenza casa meno
# trasferta, che e' quello che il prompt chiede all'LLM di leggere («chi crea di piu'»). Tutto dentro il
# file (lega-stagione): le medie di ogni file sono tolte prima. I gruppi del prompt sono per correlazione
# della differenza: reggono bene da 0.37, a meta' da 0.22, sotto non usarle.
import os, sys, glob, collections
import numpy as np
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DIRS = sys.argv[1:] or ['batch48', 'batch4', 'batch/2627', 'batch/nuove', 'batch/livello']
NOMI = {'passes': 'passes', 'carries': 'carries', 'Passaggi progressivi': 'prog_passes', 'Conduzioni progressive': 'prog_carries',
        'Passaggi in area': 'passes_box', 'Conduzioni in area': 'carries_box', 'carries_f3': 'carries_f3', 'SCA (shot-creating)': 'sca',
        'xT totale': 'xt', 'key_passes': 'key_passes', 'chances_created': 'chances_created', 'PPDA': 'ppda',
        'xAG (expected assists)': 'xag', 'GCA (goal-creating)': 'gca', 'take_ons': 'take_ons', 'clearances': 'clearances',
        'aerials': 'aerials', 'tackles': 'tackles', 'interceptions': 'interceptions', 'duels_won': 'duels_won', 'blocks': 'blocks',
        'vaep': 'vaep', 'pv': 'pv', 'assists': 'assists', 'second_assists': 'second_assists',
        'sca_shot': 'sca_shot', 'sca_foul': 'sca_foul', 'sca_takeon': 'sca_takeon',
        'NPxG': 'npxg', 'Tocchi Area': 'tch_box', 'Possesso %': 'poss'}

def num(x):
    try: return float(x.strip().replace('+', '').replace(',', '.'))
    except ValueError: return None

def leggi(dirs):
    per_squadra, per_partita, visti = collections.defaultdict(list), collections.defaultdict(dict), set()
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, '*.csv'))):
            L = [l.rstrip('\n').split(';') for l in open(f, encoding='utf-8', errors='replace')]
            ids = next((l for l in L if l[0] == 'ID PARTITA'), None)
            orig = next((l for l in L if l[0].startswith('Origine metriche avanzate')), None)
            conf = next((l for l in L if l[0] == 'COPIA CONFORME DELLO SCANNER'), None)
            if not ids or not orig or not conf: continue
            n = (len(ids) - 1) // 4
            ok = [orig[1 + 4 * j].strip() == 'motore' and conf[1 + 4 * j].strip().startswith('SI') and ids[1 + 4 * j] not in visti for j in range(n)]
            visti.update(ids[1 + 4 * j] for j in range(n))
            lato = None
            for l in L:
                if l[0].startswith('---'):
                    lato = ('H' if 'CASA' in l[0] else 'A' if 'TRASFERTA' in l[0] else None) if ('METRICHE' in l[0] or 'SQUADRA' in l[0]) else None
                    continue
                if lato and l[0] in NOMI:
                    k = NOMI[l[0]]
                    for j in range(n):
                        p, r = (num(l[1 + 4 * j]), num(l[3 + 4 * j])) if ok[j] else (None, None)
                        if p is None or r is None: continue
                        per_squadra[k].append((f, p, r)); per_partita[(k, ids[1 + 4 * j])][lato] = (p, r); per_partita[(k, ids[1 + 4 * j])]['f'] = f
    return per_squadra, per_partita, sum(1 for _ in visti)

def retta(ff, p, r):
    p, r = p.copy(), r.copy()
    for g in set(ff):
        m = ff == g; p[m] -= p[m].mean(); r[m] -= r[m].mean()
    sl = (p * r).sum() / (p * p).sum(); se = np.sqrt(((r - sl * p) ** 2).sum() / (len(p) - 2) / (p * p).sum())
    return sl, 2 * se, np.corrcoef(p, r)[0, 1]

def main():
    S, P, n = leggi(DIRS)
    print(f'partite lette: {n} (si usano solo quelle in copia conforme con le metriche avanzate del motore)')
    print(f'{"metrica":16s} {"squadre":>7s} {"livello":>7s} {"pendenza":>13s} {"corr":>6s} | {"partite":>7s} {"pendenza diff.":>14s} {"corr diff.":>10s}  gruppo')
    for k in dict.fromkeys(NOMI.values()):
        v = S.get(k)
        if not v or len(v) < 200: continue
        ff = np.array([x[0] for x in v]); p = np.array([x[1] for x in v]); r = np.array([x[2] for x in v])
        sl, se, c = retta(ff, p, r)
        X = [(x['f'], x['H'][0] - x['A'][0], x['H'][1] - x['A'][1]) for kk, x in P.items() if kk[0] == k and 'H' in x and 'A' in x]
        fd = np.array([x[0] for x in X]); sld, sed, cd = retta(fd, np.array([x[1] for x in X]), np.array([x[2] for x in X]))
        gruppo = 'reggono bene' if cd >= 0.37 else ('a meta' if cd >= 0.22 else 'non usarle')
        print(f'{k:16s} {len(p):7d} {p.mean() / r.mean():7.2f} {sl:7.2f} ±{se:4.2f} {c:6.3f} | {len(X):7d} {sld:8.2f} ±{sed:4.2f} {cd:10.3f}  {gruppo}')

if __name__ == '__main__':
    main()
