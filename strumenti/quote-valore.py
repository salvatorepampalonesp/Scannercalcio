# Battere il bookmaker (AGENTS.md, Battere il bookmaker: la regola della ricerca).
#
#   python3 strumenti/quote-valore.py batch48 batch4 [--quote batch/quote]
#
# Tre domande, scelte sull'esplorazione (2023/24 e 2024/25) e confermate sul 2025/26:
# 1) il motore anticipa la mossa del mercato dalle quote di qualche giorno prima alla chiusura?
# 2) il prezzo migliore fra i bookmaker batte il consenso, senza motore?
# 3) in quali sottoinsiemi il motore, dato il mercato di chiusura, pesa piu' di zero?
# CLV = p_chiusura_equa x prezzo - 1: il guadagno atteso della giocata se la chiusura e' giusta.
import os, sys, io, csv, math, collections, importlib.util
import numpy as np
_s = importlib.util.spec_from_file_location('qg', os.path.join(os.path.dirname(__file__), 'quote-gol.py'))
qg = importlib.util.module_from_spec(_s); _s.loader.exec_module(qg); qb = qg.qb
ESPLORA, CONFERMA = {'2023/2024', '2024/2025'}, {'2025/2026'}

def quote(r, pre, suff):
    q = [qb.num(r.get(pre + x)) for x in suff]
    return q if all(q) and all(x > 1 for x in q) else None

def eque(q): inv = [1 / x for x in q]; s = sum(inv); return [x / s for x in inv]

def archivio(f):
    righe, dentro = [], False
    for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if r and r[0].startswith('=== ARCHIVIO'): dentro = True; continue
        if dentro and r and r[0].startswith('ARCHIVIO #'): righe.append(r)
    return righe

def contesto(Q, cartelle):
    """giornata (partite di campionato gia' giocate dalla squadra che ne ha meno, piu' uno) e neopromossa (assente dalla stagione prima)."""
    file = {os.path.basename(f): f for d in cartelle for f in qb.glob.glob(os.path.join(d, '*.csv'))}
    out = {}
    for nome in {q['file'] for q in Q}:
        A = archivio(file[nome]); stag = nome.rsplit('_', 1)[1][:9].replace('-', '/')
        prima = f'{int(stag[:4]) - 1}/{stag[:4]}'
        squadre_prima = {x for r in A if r[2] == prima for x in (r[6], r[8])}
        ore = collections.defaultdict(list)
        for r in A:
            if r[2] == stag and r[4] == 'finished':
                for x in (r[6], r[8]): ore[x].append(r[3])
        for q in Q:
            if q['file'] != nome: continue
            g = min(sum(t < q['ora'] for t in ore[q['H']]), sum(t < q['ora'] for t in ore[q['A']])) + 1
            out[q['id']] = dict(stag=stag, giornata=g, neo=bool(squadre_prima) and (q['H'] not in squadre_prima or q['A'] not in squadre_prima))
    return out

def media(x):
    x = np.asarray(x, float); n = len(x)
    if n < 2: return (float(x.mean()) if n else float('nan')), float('nan'), n
    return float(x.mean()), float(x.mean() / (x.std(ddof=1) / math.sqrt(n))), n

def pendenza(x, y):
    x, y = np.asarray(x), np.asarray(y); X = np.column_stack([np.ones(len(x)), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b
    V = np.linalg.inv(X.T @ X) @ (X.T * e ** 2) @ X @ np.linalg.inv(X.T @ X) * len(x) / (len(x) - 2)
    return b[1], b[1] / math.sqrt(V[1, 1]), len(x)

def logistica(X, y, it=50):
    X = np.column_stack([np.ones(len(y)), X]); b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); H = X.T @ (X * (p * (1 - p))[:, None]); b += np.linalg.solve(H, X.T @ (y - p))
    p = 1 / (1 + np.exp(-X @ b)); se = np.sqrt(np.diag(np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]))))
    return b, b / se

def main():
    args = sys.argv[1:]; cartelle = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] != '--quote')]
    M, Q = qg.carica(args); C = qg.con_quote(Q); K = contesto(Q, cartelle)
    stag = np.array([K[q['id']]['stag'] for q in Q]); esp, con = np.isin(stag, list(ESPLORA)), np.isin(stag, list(CONFERMA))
    print(f'partite: esplorazione {esp.sum()}, conferma {con.sum()}')
    P0 = C['P0']; E0 = C['E0']
    righe = []
    for i, q in enumerate(Q):
        r = q['riga']
        righe.append(dict(i=i, lega=q['lega'], out=q['out'], ov=int(q['hg'] + q['ag'] > 2), pm=list(P0[i]), pmo=float(E0['o25'][i]),
            E=quote(r, 'Avg', 'HDA'), Emax=quote(r, 'Max', 'HDA'), Cq=quote(r, 'AvgC', 'HDA'), Cmax=quote(r, 'MaxC', 'HDA'), BFE=quote(r, 'BFE', 'HDA'),
            Eo=quote(r, 'Avg', ['>2.5', '<2.5']), Eomax=quote(r, 'Max', ['>2.5', '<2.5']), Co=quote(r, 'AvgC', ['>2.5', '<2.5']),
            Comax=quote(r, 'MaxC', ['>2.5', '<2.5']), esp=bool(esp[i]), con=bool(con[i])))
    ok1 = [x for x in righe if x['E'] and x['Cq']]; oko = [x for x in righe if x['Eo'] and x['Co']]
    print(f'con le quote di prima e di chiusura: 1X2 {len(ok1)}, Over/Under {len(oko)}')

    print('\n=== DOMANDA 1a: il mercato va dove dice il motore? (pendenza della mossa sulla distanza motore - quote di prima) ===')
    for nome, R, f in (('1 contro 2', ok1, lambda x: (math.log(eque(x['Cq'])[0] / eque(x['Cq'])[2]) - math.log(eque(x['E'])[0] / eque(x['E'])[2]),
                                                           math.log(x['pm'][0] / x['pm'][2]) - math.log(eque(x['E'])[0] / eque(x['E'])[2]))),
                       ('Over 2.5', oko, lambda x: (qg.logit(eque(x['Co'])[0]) - qg.logit(eque(x['Eo'])[0]), qg.logit(x['pmo']) - qg.logit(eque(x['Eo'])[0])))):
        for et, sel in (('esplorazione', 'esp'), ('CONFERMA', 'con')):
            v = [f(x) for x in R if x[sel]]; b, z, n = pendenza([a[1] for a in v], [a[0] for a in v])
            print(f'  {nome}, {et}: pendenza {b:+.4f} (z {z:+.2f}, {n} partite)' + ('' if sel == 'esp' else f'  -> {"PASSA" if b > 0 and z >= 2 else "NON PASSA"}'))

    def giocate_1b(x, t, prezzo):
        out = []
        if x['E'] and x['Cq'] and x[prezzo[0]]:
            pe, pc = eque(x['E']), eque(x['Cq']); d = [100 * (x['pm'][j] - pe[j]) for j in range(3)]; j = int(np.argmax(d))
            if d[j] >= t: pz = x[prezzo[0]][j]; out.append(dict(clv=pc[j] * pz - 1, roi=(pz - 1) if x['out'] == j else -1, mk='1X2'))
        if x['Eo'] and x['Co'] and x[prezzo[1]]:
            pe, pc = eque(x['Eo']), eque(x['Co']); d = 100 * (x['pmo'] - pe[0])
            for j, s in ((0, d), (1, -d)):
                if s >= t: pz = x[prezzo[1]][j]; out.append(dict(clv=pc[j] * pz - 1, roi=(pz - 1) if (x['ov'] == 1) == (j == 0) else -1, mk='OU'))
        return out
    print('\n=== DOMANDA 1b: giocare dove il motore supera le quote di prima di almeno t punti ===')
    for nome, prezzo in (('alle quote medie di prima (Avg)', ('E', 'Eo')), ('al prezzo migliore di prima (Max)', ('Emax', 'Eomax'))):
        tab = {}
        for t in (3, 5, 8, 12):
            G = [g for x in righe if x['esp'] for g in giocate_1b(x, t, prezzo)]; tab[t] = media([g['clv'] for g in G])
            print(f'  {nome}, esplorazione t={t}: {len(G)} giocate, CLV {100 * tab[t][0]:+.2f}% (z {tab[t][1]:+.2f}), ROI {100 * np.mean([g["roi"] for g in G]):+.2f}%')
        t = max(tab, key=lambda k: tab[k][0]); G = [g for x in righe if x['con'] for g in giocate_1b(x, t, prezzo)]
        c, z, n = media([g['clv'] for g in G]); r_ = media([g['roi'] for g in G])
        print(f'  {nome}, CONFERMA con t={t}: {n} giocate, CLV {100 * c:+.2f}% (z {z:+.2f}), ROI {100 * r_[0]:+.2f}% (z {r_[1]:+.2f})  -> {"PASSA" if c > 0 and z >= 2 else "NON PASSA"}'
              + '  [1X2: CLV {:+.2f}%, {} · Over/Under: CLV {:+.2f}%, {}]'.format(*[v for mk in ('1X2', 'OU') for v in (100 * np.mean([g['clv'] for g in G if g['mk'] == mk] or [np.nan]), sum(g['mk'] == mk for g in G))]))

    print('\n=== DOMANDA 2: il prezzo migliore contro il consenso, senza motore ===')
    def giocate_2(x, m, quando):
        out = []
        for cons, mx, chiusa, oc in ((('E', 'Emax', 'Cq') if quando == 'prima' else ('Cq', 'Cmax', None)) + (x['out'],),
                                     (('Eo', 'Eomax', 'Co') if quando == 'prima' else ('Co', 'Comax', None)) + (0 if x['ov'] else 1,)):
            if not (x[cons] and x[mx] and (chiusa is None or x[chiusa])): continue
            pe = eque(x[cons])
            for j, pz in enumerate(x[mx]):
                if pe[j] * pz - 1 >= m / 100:
                    out.append(dict(clv=(eque(x[chiusa])[j] * pz - 1) if chiusa else None, roi=(pz - 1) if oc == j else -1))
        return out
    for quando, metro in (('prima', 'clv'), ('chiusura', 'roi')):
        tab = {}
        for m in (0, 2, 4, 6):
            G = [g for x in righe if x['esp'] for g in giocate_2(x, m, quando)]; tab[m] = media([g[metro] for g in G])
            extra = f', CLV {100 * np.mean([g["clv"] for g in G]):+.2f}%' if quando == 'prima' and G else ''
            print(f'  {quando}, esplorazione m={m}%: {len(G)} giocate, ROI {100 * np.mean([g["roi"] for g in G]) if G else float("nan"):+.2f}%{extra}')
        m = max(tab, key=lambda k: tab[k][0] if not math.isnan(tab[k][0]) else -9); G = [g for x in righe if x['con'] for g in giocate_2(x, m, quando)]
        c, z, n = media([g[metro] for g in G]); r_ = media([g['roi'] for g in G])
        print(f'  {quando}, CONFERMA con m={m}%: {n} giocate, {metro.upper()} {100 * c:+.2f}% (z {z:+.2f})' + (f', ROI {100 * r_[0]:+.2f}% (z {r_[1]:+.2f})' if metro == 'clv' else '')
              + f'  -> {"PASSA" if c > 0 and z >= 2 else "NON PASSA"}')
        if quando == 'prima':
            # trovato dopo il test: la chiusura in proporzione sopravvaluta gli sfavoriti; lo stesso CLV con la chiusura ricalibrata fuori lega
            lg = np.array([x['lega'] for x in righe]); y1 = np.array([x['out'] for x in righe]); yo = np.array([x['ov'] for x in righe], float)
            k1 = np.array([bool(x['Cq']) for x in righe]); ko = np.array([bool(x['Co']) for x in righe])
            PC = np.array([eque(x['Cq']) if x['Cq'] else [1 / 3] * 3 for x in righe]); lr = np.column_stack([np.log(PC[:, 0] / PC[:, 1]), np.log(PC[:, 2] / PC[:, 1])])
            PR = np.array(PC)
            for l in sorted(set(lg)):
                te, tr = (lg == l) & k1, (lg != l) & k1; W, b = qg.stima1(lr[tr], y1[tr]); Z = lr[te] @ W.T + b; Z -= Z.max(1, keepdims=True); Ee = np.exp(Z); PR[te] = Ee / Ee.sum(1, keepdims=True)
            pco = np.array([eque(x['Co'])[0] if x['Co'] else .5 for x in righe]); pro = np.array(pco); pro[ko] = qg.lolo2(qg.logit(pco[ko])[:, None], yo[ko], lg[ko])
            clv = []
            for x in righe:
                if not x['con']: continue
                if x['E'] and x['Emax'] and x['Cq']:
                    pe = eque(x['E']); clv += [PR[x['i']][j] * x['Emax'][j] - 1 for j in range(3) if pe[j] * x['Emax'][j] - 1 >= m / 100]
                if x['Eo'] and x['Eomax'] and x['Co']:
                    pe = eque(x['Eo']); pr = [pro[x['i']], 1 - pro[x['i']]]; clv += [pr[j] * x['Eomax'][j] - 1 for j in range(2) if pe[j] * x['Eomax'][j] - 1 >= m / 100]
            c2, z2, n2 = media(clv)
            print(f'  (trovato dopo) stesse giocate, CLV sulla chiusura ricalibrata fuori lega: {100 * c2:+.2f}% (z {z2:+.2f}, {n2})')
    uguali = [abs(x['Emax'][j] - x['BFE'][j]) < 1e-9 for x in righe if x['Emax'] and x['BFE'] for j in range(3)]
    print(f'  il prezzo migliore di prima coincide con l exchange (BFE) nel {100 * np.mean(uguali):.0f}% dei casi')

    print('\n=== DOMANDA 3: dove il motore, dato il mercato di chiusura, pesa piu di zero (1 contro 2, senza pareggi) ===')
    R = [x for x in righe if x['Cq'] and x['out'] != 1]
    def feat(x):
        q = Q[x['i']]; k = K[q['id']]; pc = eque(x['Cq']); fav = max(pc)
        dist = 100 * abs(x['pm'][0] / (x['pm'][0] + x['pm'][2]) - pc[0] / (pc[0] + pc[2]))
        return {'lega: ' + x['lega']: True,
                'giornata: 1-5': k['giornata'] <= 5, 'giornata: 6-19': 6 <= k['giornata'] <= 19, 'giornata: 20+': k['giornata'] >= 20,
                'neopromossa in campo': k['neo'], 'nessuna neopromossa': not k['neo'],
                'favorita sotto 45%': fav < .45, 'favorita 45-60%': .45 <= fav <= .60, 'favorita oltre 60%': fav > .60,
                'motore-mercato sotto 5 punti': dist < 5, 'motore-mercato 5-10 punti': 5 <= dist <= 10, 'motore-mercato oltre 10 punti': dist > 10,
                'motore ed Elo d accordo': (q['lgModel'] or 0) * (q['lgElo'] or 0) > 0, 'motore ed Elo in disaccordo': (q['lgModel'] or 0) * (q['lgElo'] or 0) <= 0,
                'advanced presente': q['origine'] == 'motore', 'advanced assente': q['origine'] != 'motore'}
    F = [feat(x) for x in R]; nomi = sorted({k for f in F for k in f})
    X = lambda S: np.array([[math.log(eque(x['Cq'])[0] / eque(x['Cq'])[2]), math.log(x['pm'][0] / x['pm'][2])] for x in S])
    y = lambda S: np.array([1.0 if x['out'] == 0 else 0.0 for x in S])
    candidati = []
    for nm in nomi:
        S = [x for x, f in zip(R, F) if f.get(nm) and x['esp']]
        if len(S) < 100: continue
        b, z = logistica(X(S), y(S)); flag = b[2] > 0 and z[2] >= 3
        print(f'  {nm:32s} esplorazione {len(S):5d}: peso del motore {b[2]:+.3f} (z {z[2]:+.2f}), del mercato {b[1]:+.3f}' + ('   <- all esame' if flag else ''))
        if flag: candidati.append(nm)
    b, z = logistica(X([x for x in R if x['esp']]), y([x for x in R if x['esp']]))
    print(f'  {"tutte":32s} esplorazione: peso del motore {b[2]:+.3f} (z {z[2]:+.2f})')
    if not candidati: print('  ESITO: nessun sottoinsieme arriva a z >= 3 sull esplorazione: da nessuna parte, con questi dati.')
    for nm in candidati:
        S = [x for x, f in zip(R, F) if f.get(nm) and x['con']]; b, z = logistica(X(S), y(S))
        pc = [eque(x['Cq']) for x in S]; lato = [0 if x['pm'][0] / (x['pm'][0] + x['pm'][2]) > p[0] / (p[0] + p[2]) else 2 for x, p in zip(S, pc)]
        roi = [(x['Cq'][j] - 1) if x['out'] == j else -1 for x, j in zip(S, lato)]; roim = [(x['Cmax'][j] - 1) if x['out'] == j else -1 for x, j in zip(S, lato) if x['Cmax']]
        print(f'  CONFERMA {nm}: {len(S)} partite, peso del motore {b[2]:+.3f} (z {z[2]:+.2f}) -> {"CONFERMATO" if b[2] > 0 and z[2] >= 2 else "NON CONFERMATO"};'
              f' lato del motore alla chiusura ROI {100 * np.mean(roi):+.1f}% (media), {100 * np.mean(roim):+.1f}% (migliore)')

if __name__ == '__main__':
    main()
