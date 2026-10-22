# Il rischio sorpresa del motore giornata per giornata (AGENTS.md, L'avviso di sorpresa, «Sul 2026/27»).
#
#   python3 strumenti/sorpresa-giornate.py batch/2627b85
#
# Dai CSV del Comparatore rifa' il livello che lo Scanner stampa (rischioSorpresa con SORPRESA_TAB letta da
# scanner.html: 1X2 del verdetto e log-odds di modello ed Elo del ramo completo), conta la giornata di ogni partita
# dall'archivio in fondo al file (la k-esima partita della stagione, la piu' alta delle due squadre) e dice, per le
# giornate 1-5 e per quelle dopo, quante partite ALTO / medio / basso e quante volte ha vinto lo sfavorito.
import os, sys, io, csv, glob, re, math, collections, importlib.util, json
import numpy as np
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
_s = importlib.util.spec_from_file_location('rx', os.path.join(ROOT, 'strumenti', 'rating-xg.py'))
rx = importlib.util.module_from_spec(_s); _s.loader.exec_module(rx)

src = io.open(os.path.join(ROOT, 'scanner.html'), encoding='utf-8').read()
blk = re.search(r'const SORPRESA_TAB = \{.*?fasce: \[(.*?)\] \};', src, re.S).group(1)
FASCE = []
for m in re.finditer(r'\{ da: (\d+), tutte: (\[[^\]]*\]|null), accordo: (\[[^\]]*\]|null), disaccordo: (\[[^\]]*\]|null) \}', blk):
    FASCE.append({'da': int(m.group(1)), 'tutte': json.loads(m.group(2)), 'accordo': json.loads(m.group(3)), 'disaccordo': json.loads(m.group(4))})

def rischio(p1, pX, p2, lgM, lgE):
    pU = min(p1, p2) / (p1 + pX + p2)
    i = next(j for j in range(len(FASCE)) if j == len(FASCE) - 1 or 100 * pU < FASCE[j + 1]['da'])
    f = FASCE[i]
    dis = None if lgM is None or lgE is None else ((lgM > 0) != (lgE > 0))
    k = 'tutte' if dis is None else ('disaccordo' if dis else 'accordo')
    c = f[k] if f[k] and f[k][0] >= 150 else f['tutte']
    liv = 'alto' if c[1] >= 33 else ('medio' if c[1] >= 25 else 'basso')
    return liv, pU, dis, c

def giornate(f):
    # k-esima partita di lega della stagione del database per ogni squadra, dall'archivio in fondo al CSV
    righe, dentro, stag = [], False, None
    for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if r and r[0].startswith('=== ARCHIVIO'):
            dentro = True; stag = re.search(r'database (\S+),', r[0]).group(1); continue
        if dentro and r and r[0].startswith('ARCHIVIO #'): righe.append(r)
    sel = sorted([r for r in righe if r[2] == stag and r[4] == 'finished'], key=lambda r: (r[3], int(r[0].split('#')[1])))
    cnt, G = collections.Counter(), {}
    for r in sel:
        cnt[r[5]] += 1; cnt[r[7]] += 1
        G[r[1]] = max(cnt[r[5]], cnt[r[7]])
    return G

X = []
for d in sys.argv[1:]:
    for f in sorted(glob.glob(os.path.join(d, '*.csv'))):
        G = giornate(f)
        for m in rx.leggi(f):
            if not m['conf'] or None in m['p']: continue
            liv, pU, dis, c = rischio(*m['p'], m['lgM'], m['lgE'])
            fav = 0 if m['p'][0] >= m['p'][2] else 2
            X.append(dict(L=m['L'], id=m['id'], g=G.get(m['id']), liv=liv, pU=pU, dis=dis, und=2 - fav, out=m['out'],
                          H=m['H'], A=m['A'], ora=m['ora'], p=m['p'], score=f"{m['hg']}-{m['ag']}"))
print(f'{len(X)} partite in copia conforme; giornata nota per {sum(x["g"] is not None for x in X)}')

def riga(nome, S):
    if not S: print(f'  {nome:28s}  -'); return
    u = np.array([x['out'] == x['und'] for x in S]); pr = np.array([x['pU'] for x in S]); dr = np.array([x['out'] == 1 for x in S])
    se = 200 * math.sqrt(max(u.mean() * (1 - u.mean()), 1e-9) / len(S))
    print(f'  {nome:28s} {len(S):4d} partite   vince lo sfavorito {100 * u.mean():5.1f}% (previsto {100 * pr.mean():4.1f}, ±{se:4.1f})   pareggi {100 * dr.mean():4.1f}%')

for titolo, sel in (('giornate 1-5', lambda x: x['g'] is not None and x['g'] <= 5), ('dalla giornata 6', lambda x: x['g'] is not None and x['g'] > 5), ('tutte', lambda x: True)):
    S = [x for x in X if sel(x)]
    print(f'\n=== {titolo}: {len(S)} partite ===')
    for liv in ('alto', 'medio', 'basso'): riga(liv, [x for x in S if x['liv'] == liv])
    riga('disaccordo modello/Elo', [x for x in S if x['dis']])
    riga('sfavorito al 35% o piu', [x for x in S if x['pU'] >= 0.35])
    riga('sfavorito 30-35%', [x for x in S if 0.30 <= x['pU'] < 0.35])
    per = collections.Counter(x['L'] for x in S); alt = collections.Counter(x['L'] for x in S if x['liv'] == 'alto')
    print('  per lega (ALTO / partite):', ', '.join(f'{l} {alt[l]}/{per[l]}' for l in sorted(per)))

print('\n=== le partite ALTO ===')
for x in sorted([x for x in X if x['liv'] == 'alto'], key=lambda x: x['ora']):
    sf = x['A'] if x['und'] == 2 else x['H']
    esito = 'SORPRESA' if x['out'] == x['und'] else ('pari' if x['out'] == 1 else 'favorito')
    print(f"  {x['ora'][:10]} g{x['g']}  {x['L']:20s} {x['H']} - {x['A']} {x['score']:5s}  1X2 {x['p'][0]:.1f}/{x['p'][1]:.1f}/{x['p'][2]:.1f}  sfavorito {sf} {100 * x['pU']:.1f}%  {esito}")
print('\nper giornata (ALTO / partite):', ', '.join(f'g{g} {sum(1 for x in X if x["g"] == g and x["liv"] == "alto")}/{sum(1 for x in X if x["g"] == g)}'
                                                for g in sorted({x['g'] for x in X if x['g']})))
