# L'avviso di sorpresa (AGENTS.md, L'avviso di sorpresa).
#
#   python3 strumenti/sorpresa.py batch48 batch4 batch/2627 batch/nuove batch/livello
#
# Dai CSV del Comparatore (1X2 del motore, identico dal b48) conta, per fascia di probabilita' dello
# sfavorito (il meno probabile fra 1 e 2) e per accordo fra modello ed Elo sul favorito (segno di
# lgModel e lgElo del ramo completo), quante volte hanno vinto sfavorito, pareggio e favorito, e stampa
# SORPRESA_TAB nella forma di scanner.html. Poi il residuo dello sfavorito (vinte meno previste) col
# disaccordo, sulle dodici leghe dell'esplorazione e sulle altre separate.
import os, sys, math, importlib.util
import numpy as np
_s = importlib.util.spec_from_file_location('rx', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rating-xg.py'))
rx = importlib.util.module_from_spec(_s); _s.loader.exec_module(rx)
FASCE = [0, 15, 20, 25, 30, 35]
VECCHIE = {'ITA_Serie_A', 'ENG_Premier_League', 'ESP_LaLiga', 'GER_Bundesliga', 'FRA_Ligue_1', 'ENG_Championship', 'NED_Eredivisie',
           'POR_Liga_Portugal', 'GER_2._Bundesliga', 'BEL_First_Division_A', 'SCO_Premiership', 'SUI_Super_League'}

def main(dirs):
    X = [m for ms in rx.carica(dirs).values() for m in ms if m['conf'] and None not in m['p'] and m['lgM'] is not None and m['lgE'] is not None]
    P = np.array([m['p'] for m in X]); P /= P.sum(1, keepdims=True); o = np.array([m['out'] for m in X])
    fav = np.where(P[:, 0] >= P[:, 2], 0, 2); und = 2 - fav; pU = P[np.arange(len(X)), und]
    dis = np.array([(m['lgM'] > 0) != (m['lgE'] > 0) for m in X]); vec = np.array([m['L'] in VECCHIE for m in X])
    leghe = len({m['L'] for m in X})
    print(f'{len(X)} partite di {leghe} leghe; modello ed Elo in disaccordo sul favorito nel {100 * dis.mean():.1f}%')
    cella = lambda s: [int(s.sum())] + [round(float(100 * v), 1) for v in ((o[s] == und[s]).mean(), (o[s] == 1).mean(), (o[s] == fav[s]).mean())] if s.any() else None
    righe = []
    for i, lo in enumerate(FASCE):
        hi = FASCE[i + 1] if i + 1 < len(FASCE) else 101
        b = (pU * 100 >= lo) & (pU * 100 < hi)
        t, a, d = cella(b), cella(b & ~dis), cella(b & dis)
        print(f'  sfavorito {lo:2d}-{hi:3d}%: tutte {t}  accordo {a}  disaccordo {d}   (previsto {100 * pU[b].mean():.1f})')
        js = lambda c: 'null' if c is None else '[' + ', '.join(str(x) for x in c) + ']'
        righe.append(f'  {{ da: {lo}, tutte: {js(t)}, accordo: {js(a)}, disaccordo: {js(d)} }}')
    r = (o == und).astype(float) - pU
    for nome, s in (('tutte', np.ones(len(X), bool)), ('le dodici leghe dell esplorazione', vec), ('le altre', ~vec)):
        for f, fn in ((dis, 'disaccordo'), (~dis, 'accordo')):
            q = s & f; print(f'  residuo dello sfavorito, {nome}, {fn}: {100 * r[q].mean():+.2f} (2se {200 * r[q].std() / math.sqrt(q.sum()):.2f}, {q.sum()} partite)')
    print('\nconst SORPRESA_TAB = { partite: %d, leghe: %d, fasce: [\n%s ] };' % (len(X), leghe, ',\n'.join(righe)))

if __name__ == '__main__':
    main(sys.argv[1:])
