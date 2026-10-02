# Le debolezze delle quote (AGENTS.md, Le debolezze delle quote: la regola).
#
#   python3 strumenti/quote-debolezze.py batch48 batch4 --prova batch/nuove
#
# Cerca dove le quote di chiusura sbagliano in un verso che i nostri dati sanno vedere: per ogni candidato,
# una logistica  esito ~ logit(mercato) + candidato (standardizzato). Primo giro: dodici candidati sulle
# dodici leghe, esplorazione 2023/24 e 2024/25 (passa all'esame con |z| >= 3), conferma 2025/26 (z >= 2 nello
# stesso verso) solo per chi passa. Secondo giro, scritto dopo il primo: fortuna ultime 10 e rating sugli xG
# sul 2025/26 delle dodici leghe e su League One, League Two e Super Lig (--prova): passa con |z| >= 2 nel
# verso atteso e lo stesso verso in 3 blocchi su 4. Esito: nessuno dei due passa. Solo descrittivo.
import os, io, sys, csv, glob, math, collections, importlib.util
import numpy as np
DIR = os.path.dirname(os.path.abspath(__file__))
def _mod(nome, f):
    s = importlib.util.spec_from_file_location(nome, os.path.join(DIR, f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
rx = _mod('rx', 'rating-xg.py'); qg = _mod('qg', 'quote-gol.py'); qb = qg.qb; qm = _mod('qm', 'quote-matrice.py')

def feature(dirs):
    # per ogni partita, coi soli giorni prima: rating sugli xG, fortuna (diff gol meno diff xG), punti, xG, neopromosse
    F = {}
    for lega, ms in rx.carica(dirs).items():
        rat = rx.rating(ms)
        stag = sorted({m['S'] for m in ms}); sq = {s: {t for m in ms if m['S'] == s for t in (m['H'], m['A'])} for s in stag}
        hist, giorni = collections.defaultdict(list), collections.OrderedDict()
        for m in ms: giorni.setdefault(m['ora'][:10], []).append(m)
        for g in giorni.values():
            for m in g:
                i = stag.index(m['S']); prev = sq[stag[i - 1]] if i > 0 else None
                ult = lambda t, n: hist[t][-n:] if len(hist[t]) >= n else None
                f = {'rat': rat.get(m['id']), 'neo': None if prev is None else (m['H'] not in prev) - (m['A'] not in prev)}
                for n in (5, 10):
                    hH, hA = ult(m['H'], n), ult(m['A'], n)
                    ok = bool(hH and hA) and all(None not in x[2:4] for x in hH + hA)
                    lk = lambda h: np.mean([(x[0] - x[1]) - (x[2] - x[3]) for x in h])
                    f[f'fort{n}'] = lk(hH) - lk(hA) if ok else None
                    if n == 5: f['forma5'] = sum(x[4] for x in hH) - sum(x[4] for x in hA) if hH and hA else None
                    if n == 10:
                        mean = lambda h, fn: np.mean([fn(x) for x in h])
                        f['xgd10'] = mean(hH, lambda x: x[2] - x[3]) - mean(hA, lambda x: x[2] - x[3]) if ok else None
                        f['fortgol10'] = mean(hH, lambda x: x[0] + x[1] - x[2] - x[3]) + mean(hA, lambda x: x[0] + x[1] - x[2] - x[3]) if ok else None
                        f['xgtot10'] = mean(hH, lambda x: x[2] + x[3]) + mean(hA, lambda x: x[2] + x[3]) if ok else None
                F[m['id']] = f
            for m in g:
                xh, xa = m['xg']; ph = 3 if m['hg'] > m['ag'] else (1 if m['hg'] == m['ag'] else 0); pa = {3: 0, 1: 1, 0: 3}[ph]
                hist[m['H']].append((m['hg'], m['ag'], xh, xa, ph)); hist[m['A']].append((m['ag'], m['hg'], xa, xh, pa))
    return F

def stanchezza(dirs, F):
    K = ('Stanchezza casa: giorni di riposo', 'Stanchezza trasf.: giorni di riposo',
         'Stanchezza casa: giorni dalla coppa europea', 'Stanchezza trasf.: giorni dalla coppa europea')
    for f in [f for d in dirs for f in sorted(glob.glob(os.path.join(d, '*.csv')))]:
        righe = collections.defaultdict(list)
        for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
            if not r or not r[0]: continue
            if r[0].startswith('=== ARCHIVIO'): break
            righe[r[0]].append(r)
        ids = righe['ID PARTITA'][0]
        for c in range(1, len(ids), 4):
            if not ids[c] or ids[c] not in F: continue
            rh, ra, eh, ea = [rx.num(righe[k][0][c]) if k in righe and len(righe[k][0]) > c else None for k in K]
            eu = lambda x: 1 if x is not None and x <= 4 else 0
            F[ids[c]]['riposo'] = None if rh is None or ra is None else min(rh, 7) - min(ra, 7)
            F[ids[c]]['europa'] = eu(eh) - eu(ea)

def logistic(X, y, it=60):
    X = np.column_stack([np.ones(len(y)), X]); b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); H = X.T @ (X * (p * (1 - p))[:, None]); d = np.linalg.solve(H, X.T @ (y - p)); b += d
        if np.abs(d).max() < 1e-10: break
    return b, np.sqrt(np.diag(np.linalg.inv(H)))

def righe(Q, F, blocco):
    out = []
    for q in Q:
        f = F.get(q['id'])
        if f is None: continue
        pm = np.array([1 / x for x in q['qc']]); pm /= pm.sum()
        ou = qg.ou(q['riga'], ['AvgC', 'PC', 'B365C'])[0]
        po = (1 / ou[0]) / (1 / ou[0] + 1 / ou[1]) if ou else None
        out.append(dict({k: None for k in ('riposo', 'europa')}, **f, lega=q['lega'], blocco=blocco(q), out=q['out'], tot=q['hg'] + q['ag'],
                        m12=math.log(pm[0] / pm[2]), mX=math.log(pm[1] / (1 - pm[1])), mO=None if po is None else math.log(po / (1 - po)),
                        lam=q['lam'][0] + q['lam'][1] if None not in q['lam'] else None, absrat=None if f['rat'] is None else abs(f['rat'])))
    return out

CAND = [('a', 'margine del rating sugli xG', 'rat', '12'), ('b', 'fortuna ultime 5', 'fort5', '12'), ('c', 'fortuna ultime 10', 'fort10', '12'),
        ('d', 'punti ultime 5', 'forma5', '12'), ('e', 'riposo', 'riposo', '12'), ('f', 'coppa europea nei 4 giorni prima', 'europa', '12'),
        ('g', 'neopromossa', 'neo', '12'), ('h', 'diff xG ultime 10', 'xgd10', '12'),
        ('i', '|margine del rating sugli xG|', 'absrat', 'X'), ('j', 'lambda totale del motore', 'lam', 'X'),
        ('k', 'fortuna gol ultime 10', 'fortgol10', 'O'), ('l', 'xG totali ultime 10', 'xgtot10', 'O')]

def dati(R, feat, tipo):
    if tipo == '12': R = [r for r in R if r['out'] != 1 and r[feat] is not None]; y = [r['out'] == 0 for r in R]; mk = [r['m12'] for r in R]
    elif tipo == 'X': R = [r for r in R if r[feat] is not None]; y = [r['out'] == 1 for r in R]; mk = [r['mX'] for r in R]
    else: R = [r for r in R if r[feat] is not None and r['mO'] is not None]; y = [r['tot'] > 2.5 for r in R]; mk = [r['mO'] for r in R]
    return R, np.array(y, float), np.array(mk), np.array([r[feat] for r in R], float)

def main():
    args = sys.argv[1:]; prova = []
    if '--prova' in args: i = args.index('--prova'); prova = args[i + 1:]; args = args[:i]
    F = feature(args); stanchezza(args, F)
    M = list({m['id']: m for d in args for f in sorted(glob.glob(os.path.join(d, '*.csv'))) for m in qb.leggi_csv(f)}.values())
    R = righe(qb.aggancia(M, qb.quote_fd('batch/quote')), F, lambda q: '12 leghe 2025/26' if '2025-2026' in q['file'] else 'esplorazione')
    ESP, CON = [r for r in R if r['blocco'] == 'esplorazione'], [r for r in R if r['blocco'] != 'esplorazione']
    print(f'partite con le quote: esplorazione {len(ESP)}, conferma {len(CON)}\n\n=== primo giro, esplorazione 2023/24 + 2024/25 ===')
    passati, std = [], {}
    for c, nome, feat, tipo in CAND:
        Re, y, mk, x = dati(ESP, feat, tipo); mu, sd = x.mean(), x.std(); std[feat] = (mu, sd)
        b, se = logistic(np.column_stack([mk, (x - mu) / sd]), y); z = b[2] / se[2]
        per = collections.Counter()
        for l in sorted({r['lega'] for r in Re}):
            k = np.array([r['lega'] == l for r in Re])
            if k.sum() > 50 and np.std(x[k]) > 0: per[np.sign(logistic(np.column_stack([mk[k], (x[k] - mu) / sd]), y[k])[0][2]) == np.sign(b[2])] += 1
        print(f'  {c} {nome:34s} [{tipo:2s}] {len(y):5d} partite · {b[2]:+.3f} (z {z:+.2f}) · stesso verso in {per[True]}/{sum(per.values())} leghe' + ('  -> ESAME' if abs(z) >= 3 else ''))
        if abs(z) >= 3: passati.append((c, nome, feat, tipo, b[2]))
    print('\n=== primo giro, conferma 2025/26 (solo chi passa) ===')
    if not passati: print('  nessun candidato passa l esplorazione')
    for c, nome, feat, tipo, segno in passati:
        _, y, mk, x = dati(CON, feat, tipo); mu, sd = std[feat]; b, se = logistic(np.column_stack([mk, (x - mu) / sd]), y)
        print(f'  {c} {nome}: {b[2]:+.3f} (z {b[2] / se[2]:+.2f}) -> ' + ('CONFERMATO' if np.sign(b[2]) == np.sign(segno) and abs(b[2] / se[2]) >= 2 else 'non confermato'))
    if not prova: return
    _, QN = qm.carica(prova, 'batch/quote')
    TEST = [r for r in CON + righe(QN, feature(prova), lambda q: q['lega']) if r['out'] != 1]
    E = [r for r in ESP if r['out'] != 1]
    print(f'\n=== secondo giro: {len(TEST)} partite senza pari mai usate per questa domanda ===')
    for c, nome, feat, verso in (('c', 'fortuna ultime 10', 'fort10', -1), ('a', 'margine del rating sugli xG', 'rat', +1)):
        Ee = [r for r in E if r[feat] is not None]; mu, sd = std[feat]
        Xe = np.column_stack([[r['m12'] for r in Ee], (np.array([r[feat] for r in Ee]) - mu) / sd]); ye = np.array([r['out'] == 0 for r in Ee], float)
        be, _ = logistic(Xe, ye); bm, _ = logistic(Xe[:, :1], ye)
        T = [r for r in TEST if r[feat] is not None]
        X = np.column_stack([[r['m12'] for r in T], (np.array([r[feat] for r in T]) - mu) / sd]); y = np.array([r['out'] == 0 for r in T], float)
        b, se = logistic(X, y); z = b[2] / se[2]
        blocchi = {}
        for k in sorted({r['blocco'] for r in T}):
            s = np.array([r['blocco'] == k for r in T]); bk, sk = logistic(X[s], y[s]); blocchi[k] = (bk[2], bk[2] / sk[2], int(s.sum()))
        nv = sum(np.sign(v[0]) == verso for v in blocchi.values())
        print(f'{c} {nome}: esplorazione {be[2]:+.3f} · test {len(y)} partite, {b[2]:+.3f} (z {z:+.2f}), verso atteso in {nv}/{len(blocchi)} blocchi -> '
              + ('PASSA' if np.sign(b[2]) == verso and abs(z) >= 2 and nv >= 3 else 'NON PASSA'))
        for k, (bk, zk, n) in blocchi.items(): print(f'   {k:18s} {n:5d}  {bk:+.3f} (z {zk:+.2f})')
        p1 = 1 / (1 + np.exp(-(be[0] + be[1] * X[:, 0] + be[2] * X[:, 1]))); p0 = 1 / (1 + np.exp(-(bm[0] + bm[1] * X[:, 0])))
        d = -(y * np.log(p1) + (1 - y) * np.log(1 - p1)) + (y * np.log(p0) + (1 - y) * np.log(1 - p0))
        print(f'   logloss sul test coi coefficienti dell esplorazione, contro il mercato ricalibrato: {1000 * d.mean():+.2f} per mille (z {d.mean() / d.std(ddof=1) * math.sqrt(len(d)):+.2f})')
    T = [r for r in E + TEST if r['fort10'] is not None]; x = np.array([r['fort10'] for r in T]); sd = x.std()
    b, se = logistic(np.column_stack([[r['m12'] for r in T], x / sd]), np.array([r['out'] == 0 for r in T], float))
    q90 = np.percentile(np.abs(x), 90)
    print(f'\ndescrittivo, tutti i dati: fortuna ultime 10 {b[2]:+.3f} per sd (z {b[2] / se[2]:+.2f}, sd {sd:.2f} gol a partita); '
          f'oltre {q90:.2f} (il 10% piu estremo) circa {100 * abs(b[2]) * q90 / sd / 4:.1f} punti di probabilita a una partita 50-50')

if __name__ == '__main__':
    main()
