# Il tabellone con le quote (AGENTS.md, Il tabellone con le quote: la regola).
#
#   python3 strumenti/quote-tabellone.py batch48 batch4 [--quote batch/quote]
#
# Legge la sezione TABELLONE dei CSV (le proposte come le stampa lo Scanner, con base di lega e
# reale), rifa' il tabellone con le probabilita' con le quote (1X2 e doppie chance dal b54,
# Over/Under e Goal dal b57 dove c'e' l'Over, numeri del motore; tutto fuori lega) e confronta
# il guadagno della prima proposta di ogni partita col tabellone del motore. Stampa anche le
# rese per fascia e famiglia con le quote, nella forma di EDGE_BANDS_QUOTE (scanner.html).
import os, sys, math, json, collections, importlib.util
import numpy as np
_s = importlib.util.spec_from_file_location('qg', os.path.join(os.path.dirname(__file__), 'quote-gol.py'))
qg = importlib.util.module_from_spec(_s); _s.loader.exec_module(qg); qb = qg.qb

CINQUE = qb.CINQUE
FAM = {k: 'gol' for k in ('pOv', 'pUn', 'pGG', 'pNG')} | {k: 'numeri' for k in ('cor9.5', 'sot8.5', 'yel3.5')}
ORDINE = ['p1', 'pX', 'p2', 'p1X', 'pX2', 'p12', 'pOv', 'pUn', 'pGG', 'pNG', 'cor9.5', 'sot8.5', 'yel3.5']
FASCE = [(20, 'FORTE'), (10, 'GIOCABILE'), (5, 'MARGINALE')]

def ordina(voci):
    return sorted(voci, key=lambda v: (-(v['e'] if v['e'] is not None else -1e9), ORDINE.index(v['key'])))

def main():
    M, Q = qg.carica(sys.argv[1:]); C = qg.con_quote(Q)
    cieca = collections.defaultdict(list)
    for m in M:
        for v in m['tab']:
            if v['hit'] is not None: cieca[(m['file'], v['key'])].append(v['hit'])
    cieca = {k: sum(v) / len(v) for k, v in cieca.items()}
    # prova di coincidenza: l'ordine del CSV e' quello per scarto, e 1/X/2 del tabellone sono quelli del CSV
    fuori_ordine = sum(any((a['p'] - a['b']) < (b['p'] - b['b']) - 0.0011 for a, b in zip(m['tab'], m['tab'][1:]) if a['b'] is not None and b['b'] is not None) for m in Q)
    diversi = sum(abs({v['key']: v['p'] for v in m['tab']}.get('p1', -1) - m['p'][0]) > 0.0005 for m in Q)
    reali = sum(any(v['key'] == 'p1' and v['hit'] is not None and v['hit'] != (m['out'] == 0) for v in m['tab']) for m in Q)
    print(f'prova di coincidenza: {len(Q)} partite, tabellone fuori ordine {fuori_ordine}, "1" diverso dal CSV {diversi}, reale del "1" diverso dal punteggio {reali}')
    k_ou = np.cumsum(C['k']) - 1
    righe = []
    for i, m in enumerate(Q):
        P = C['PC'][i]; q = {'p1': P[0], 'pX': P[1], 'p2': P[2], 'p1X': P[0] + P[1], 'pX2': P[1] + P[2], 'p12': P[0] + P[2]}
        if C['k'][i]:
            j = k_ou[i]; po, gg = C['pc'][j], C['A']['gg'][j]; q |= {'pOv': po, 'pUn': 1 - po, 'pGG': gg, 'pNG': 1 - gg}
        mot = [dict(v, e=None if v['b'] is None else 100 * (v['p'] - v['b']), quote=False) for v in m['tab']]
        con = ordina([dict(v, p=q.get(v['key'], v['p']), e=None if v['b'] is None else 100 * (q.get(v['key'], v['p']) - v['b']), quote=v['key'] in q) for v in m['tab']])
        g = lambda v, f=m['file']: None if v['hit'] is None else 100 * (v['hit'] - cieca[(f, v['key'])])
        righe.append(dict(m=m, i=i, mot=mot, con=con, gm=g(mot[0]) if mot else None, gc=g(con[0]) if con else None, g=g))
    def confronto(nome, R):
        R = [r for r in R if r['gm'] is not None and r['gc'] is not None]
        d = np.array([r['gc'] - r['gm'] for r in R]); per = {}
        for l in sorted({r['m']['lega'] for r in R}):
            x = np.array([r['gc'] - r['gm'] for r in R if r['m']['lega'] == l])
            per[l] = (x.mean(), x.mean() / (x.std(ddof=1) / math.sqrt(len(x))) if x.std() > 0 else 0.0, len(x),
                      np.mean([r['gm'] for r in R if r['m']['lega'] == l]), np.mean([r['gc'] for r in R if r['m']['lega'] == l]),
                      sum(r['mot'][0]['key'] != r['con'][0]['key'] for r in R if r['m']['lega'] == l))
        z = d.mean() / (d.std(ddof=1) / math.sqrt(len(d)))
        print(f'{nome}: {len(R)} partite, prima proposta motore {np.mean([r["gm"] for r in R]):+.2f} -> con le quote {np.mean([r["gc"] for r in R]):+.2f}'
              f' ({d.mean():+.2f} ±{2 * d.std(ddof=1) / math.sqrt(len(d)):.2f}, z {z:+.2f}) · prima proposta cambiata in {sum(r["mot"][0]["key"] != r["con"][0]["key"] for r in R)}')
        for l, (dm, zl, n, a, b, c) in per.items(): print(f'  {l:17s} {n:5d}  {a:+.1f} -> {b:+.1f}  {dm:+.2f} (z {zl:+.2f})  cambiata {c}')
        return z, sum(v[0] > 0 for v in per.values()), min(v[1] for v in per.values()), len(per)
    sette = [r for r in righe if r['m']['lega'] not in CINQUE]; cinque = [r for r in righe if r['m']['lega'] in CINQUE]
    print('\n=== IL TEST: le sette leghe ===')
    z, meglio, zmin, n = confronto('tabellone con le quote contro motore', sette)
    print('ESITO:', 'PASSA' if z >= 2 and meglio >= 5 and zmin >= -1 else 'NON PASSA',
          f'(z {z:+.2f} >= +2; meglio in {meglio}/{n} >= 5; lega peggiore z {zmin:+.2f} >= -1)')
    print('\n=== descrittivo: le cinque leghe ===')
    confronto('tabellone con le quote contro motore', cinque)

    def fasce(R, chi, solo=None):
        acc = collections.defaultdict(list)
        for r in R:
            for v in r[chi]:
                if v['e'] is None or (solo is not None and v['quote'] != solo): continue
                for s, nome in FASCE:
                    if v['e'] >= s:
                        gv = r['g'](v)
                        if gv is not None: acc[(nome, FAM.get(v['key'], '1x2'))].append(gv)
                        break
        return {k: (np.mean(v), 2 * np.std(v, ddof=1) / math.sqrt(len(v)), len(v)) for k, v in acc.items() if len(v) > 1}
    print('\n=== rese per fascia e famiglia (tutte le leghe), motore | con le quote (solo proposte con le quote) ===')
    FM, FQ = fasce(righe, 'mot'), fasce(righe, 'con', True)
    for fam in ('1x2', 'gol', 'numeri'):
        print(f'  {fam}: ' + ' · '.join(f'{nome} ' + ' | '.join('--' if F.get((nome, fam)) is None else f'{F[(nome, fam)][0]:+.1f} ±{F[(nome, fam)][1]:.1f} ({F[(nome, fam)][2]})' for F in (FM, FQ)) for _, nome in FASCE))
    for gruppo, R in (('sette', sette), ('cinque', cinque)):
        F = fasce(R, 'con', True)
        print(f'  con le quote, {gruppo}: ' + ' · '.join(f'{fam} ' + ' / '.join('--' if F.get((nome, fam)) is None else f'{F[(nome, fam)][0]:+.1f}' for _, nome in FASCE) for fam in ('1x2', 'gol')))
    for chi, nome in (('mot', 'motore'), ('con', 'con le quote')):
        fg = np.mean([any(v['e'] is not None and v['e'] >= 10 for v in r[chi]) for r in righe])
        top = collections.Counter(r[chi][0]['key'] for r in righe if r[chi])
        print(f'  {nome}: almeno una FORTE o GIOCABILE nel {100 * fg:.0f}% delle partite; in cima ' + ', '.join(f'{k} {100 * c / len(righe):.0f}%' for k, c in top.most_common(7)))

    print('\n=== resa alla quota di chiusura delle proposte FORTE e GIOCABILE con una quota ===')
    for chi, nome in (('mot', 'motore'), ('con', 'con le quote')):
        for soglia, et in ((20, 'FORTE'), (10, 'GIOCABILE e FORTE')):
            r_ = []
            for r in righe:
                m, i = r['m'], r['i']
                for v in r[chi]:
                    if v['e'] is None or v['e'] < soglia or v['hit'] is None: continue
                    if v['key'] in ('p1', 'pX', 'p2'): qq = m['qc'][('p1', 'pX', 'p2').index(v['key'])]
                    elif v['key'] in ('pOv', 'pUn') and C['OUc'][i][0]: qq = C['OUc'][i][0][0 if v['key'] == 'pOv' else 1]
                    else: continue
                    r_.append(v['hit'] * qq - 1)
            print(f'  {nome}, {et}: {len(r_)} giocate, {100 * np.mean(r_):+.1f}% della posta' if r_ else f'  {nome}, {et}: nessuna')

    FQ = fasce(righe, 'con', True)
    print('\nEDGE_BANDS_QUOTE (tutte le leghe, proposte con le quote): ' + json.dumps(
        {fam: [[round(float(FQ[(nome, fam)][0]), 1), round(float(FQ[(nome, fam)][1]), 1), int(FQ[(nome, fam)][2])] if (nome, fam) in FQ else None for _, nome in FASCE] for fam in ('1x2', 'gol')}))

if __name__ == '__main__':
    main()
