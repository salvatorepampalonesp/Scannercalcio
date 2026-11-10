# Il rating dalle quote passate insieme al maestro (AGENTS.md, Il rating dalle quote passate: la regola).
#
#   python3 strumenti/quote-passate.py --scarica           # i file di football-data dell'esplorazione in batch/fd-nov
#   python3 strumenti/quote-passate.py                     # l'esplorazione: la combinazione stimata sul mercato
#   python3 strumenti/quote-passate.py --scarica-prova     # i file delle leghe del test (dopo aver registrato la regola)
#   python3 strumenti/quote-passate.py --prova batch/b94/livello   # il test registrato, coi numeri di REGOLA
#
# Nessuna chiamata alla PitchAPI. Il rating e' quello di strumenti/rating-quote.py (K 0.35, KH 0.01, REG 0.85, H0 0.35),
# fatto come lo farebbe lo Scanner: per una partita della stagione s, dalle quote di chiusura delle stagioni s-2, s-1 e s
# (le tre del database), e solo se le due squadre hanno almeno 6 partite con le quote in quella finestra. Il candidato:
#   lg' = a + b * log(p1/p2) del maestro + c * rating,  pX quello del maestro,  1 e 2 si dividono il resto secondo sigma(lg').
# a, b, c si stimano sul mercato (log p1/p2 di chiusura, margine tolto in proporzione), come il maestro.
import os, io, sys, csv, glob, math, collections, datetime as dt, urllib.request, importlib.util
import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__)); RADICE = os.path.dirname(QUI)
def _mod(nome, f):
    s = importlib.util.spec_from_file_location(nome, os.path.join(QUI, f)); m = importlib.util.module_from_spec(s)
    argv = sys.argv; sys.argv = ['x']; s.loader.exec_module(m); sys.argv = argv; return m
rq = _mod('rq', 'rating-quote.py'); qb = _mod('qb', 'quote-bookmaker.py')

NOV = os.path.join(RADICE, 'batch', 'fd-nov')
FINESTRA, MIN_Q = 2, 6
# la regola, fissata sull'esplorazione del 10 novembre 2026 prima di aprire le leghe del test: a, b sul maestro, c sul rating
REGOLA = (-0.0147, 0.3599, 0.6533)

# file del batch -> codice di football-data (file principali per stagione, file 'new' con tutte le stagioni)
PRINC = {'ITA_Serie_A': 'I1', 'ENG_Premier_League': 'E0', 'ESP_LaLiga': 'SP1', 'GER_Bundesliga': 'D1', 'FRA_Ligue_1': 'F1',
         'ENG_Championship': 'E1', 'NED_Eredivisie': 'N1', 'POR_Liga_Portugal': 'P1', 'BEL_First_Division_A': 'B1',
         'GER_2._Bundesliga': 'D2', 'SCO_Premiership': 'SC0', 'ENG_League_One': 'E2', 'ENG_League_Two': 'E3', 'TUR_Super_Lig': 'T1'}
NUOVI = {'SUI_Super_League': 'SWZ', 'ROU_Liga_I': 'ROU', 'CHN_Super_League': 'CHN', 'FIN_Veikkausliiga': 'FIN', 'IRL_Premier_Division': 'IRL',
         'AUT_Bundesliga': 'AUT', 'DEN_Superligaen': 'DNK', 'MEX_Liga_MX': 'MEX', 'NOR_Eliteserien': 'NOR', 'SWE_Allsvenskan': 'SWE',
         'USA_MLS': 'USA', 'JPN_J._League': 'JPN', 'ARG_Liga_Profesional': 'ARG', 'BRA_Serie_A': 'BRA'}
ESPLORA_NUOVI = ['SWZ', 'ROU', 'CHN', 'FIN', 'IRL']
PROVA_NUOVI = ['AUT', 'DNK', 'MEX', 'NOR', 'SWE', 'USA', 'JPN', 'ARG', 'BRA']
# il 2026/27 delle leghe del maestro dopo il taglio del suo allenamento (vedi Il ristudio del batch del b94)
TUTTO_2627 = ('GER_Bundesliga', 'ENG_League_One', 'ENG_League_Two', 'TUR_Super_Lig')
TAGLIO = '2026-10-03'

def _get(url, f):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60) as r: open(f, 'wb').write(r.read())

def scarica(nuovi, principali=True):
    os.makedirs(NOV, exist_ok=True)
    if principali:
        for c in sorted(set(PRINC.values())): _get(f'https://football-data.co.uk/mmz4281/2627/{c}.csv', os.path.join(NOV, f'{c}_2627.csv'))
    for c in nuovi: _get(f'https://football-data.co.uk/new/{c}.csv', os.path.join(NOV, f'{c}.csv'))
    print('file in', NOV)

def _riga(div, stag, d, H, A, hg, ag, r):
    c = rq.tre(r, ['AvgC', 'PSC', 'B365C'])
    return {'div': div, 'stag': stag, 'd': d, 'H': H.strip(), 'A': A.strip(), 'hg': hg, 'ag': ag, 'pc': rq.probs(c) if c else None}

def leggi_principale(div):
    out = []
    for i, s in enumerate(rq.STAG):
        f = os.path.join(NOV if s == '2627' else rq.FD, f'{div}_{s}.csv')
        if not os.path.exists(f): continue
        for r in csv.DictReader(io.open(f, encoding='utf-8-sig', errors='replace')):
            d = rq.data(r.get('Date', ''))
            if not d or not r.get('HomeTeam'): continue
            try: hg, ag = int(r['FTHG']), int(r['FTAG'])
            except (KeyError, ValueError): hg = ag = None
            out.append(_riga(div, i, d, r['HomeTeam'], r['AwayTeam'], hg, ag, r))
    out.sort(key=lambda m: m['d']); return out

def leggi_nuovo(code):
    rr = []
    for r in csv.DictReader(io.open(os.path.join(NOV, f'{code}.csv'), encoding='utf-8-sig', errors='replace')):
        d = rq.data(r.get('Date', ''))
        if not d or not r.get('Home'): continue
        try: hg, ag = int(r['HG']), int(r['AG'])
        except (KeyError, ValueError): hg = ag = None
        rr.append((d, r.get('Season', '').strip(), r))
    rr.sort(key=lambda t: t[0]); ordine = []
    for _, s, _ in rr:
        if s not in ordine: ordine.append(s)
    out = []
    for d, s, r in rr:
        try: hg, ag = int(r['HG']), int(r['AG'])
        except (KeyError, ValueError): hg = ag = None
        out.append(_riga(code, ordine.index(s), d, r['Home'], r['Away'], hg, ag, r))
    return out

def rating_finestre(ms):
    # per ogni stagione s, il rating dalle stagioni s-2..s; si tiene quello delle partite di s
    for s in sorted(set(m['stag'] for m in ms)):
        idx = [i for i, m in enumerate(ms) if s - FINESTRA <= m['stag'] <= s]
        cp = [dict(ms[i]) for i in idx]; rq.rating_quote(cp)
        for i, c in zip(idx, cp):
            if ms[i]['stag'] == s: ms[i]['yq'], ms[i]['nq'] = c['yq'], c['nq']
    return ms

def chiave(f):
    b = os.path.basename(f)[:-4].replace('Backtest_V97_', ''); lab, st = b.rsplit('_', 1); return lab, st

def partite(cartelle, codici_nuovi):
    # le partite in copia conforme dei CSV, agganciate alla loro riga di football-data (data, punteggio e nomi)
    cache, out, conta = {}, [], collections.Counter()
    for c in cartelle:
        for f in sorted(glob.glob(os.path.join(RADICE, c, '*.csv'))):
            lab, st = chiave(f)
            if lab in NUOVI and NUOVI[lab] in codici_nuovi: div, nuovo = NUOVI[lab], True
            elif lab in PRINC and codici_nuovi is ESPLORA_NUOVI and st == '2026-2027': div, nuovo = PRINC[lab], False
            else: continue
            if div not in cache: cache[div] = rating_finestre(leggi_nuovo(div) if nuovo else leggi_principale(div))
            for m in qb.leggi_csv(f):
                if not nuovo and lab not in TUTTO_2627 and m['data'] < TAGLIO: continue
                conta[(div, 'partite')] += 1
                x = rq.aggancia(m, cache[div])
                if not x or not x['pc']: conta[(div, 'senza quote')] += 1; continue
                if 'nq' not in x or min(x['nq']) < MIN_Q: conta[(div, 'senza rating')] += 1; continue
                p = np.array(m['p'], float); p /= p.sum()
                out.append(dict(div=div, lab=lab, st=st, data=m['data'], out=m['out'], pm=p, lgM=math.log(p[0] / p[2]),
                                yq=x['yq'], yc=rq.lo(x['pc']), pc=np.array(x['pc'])))
    return out, conta

def candidato(P, a, b, c):
    lg = a + b * np.array([r['lgM'] for r in P]) + c * np.array([r['yq'] for r in P])
    pm = np.array([r['pm'] for r in P]); pX = pm[:, 1]; p1 = (1 - pX) / (1 + np.exp(-lg))
    return np.c_[p1, pX, 1 - pX - p1]

def ols(P):
    A = np.c_[np.ones(len(P)), [r['lgM'] for r in P], [r['yq'] for r in P]]; y = np.array([r['yc'] for r in P])
    c, *_ = np.linalg.lstsq(A, y, rcond=None); e = y - A @ c; return c, 1 - e.var() / y.var()

def zeta(d): d = np.asarray(d, float); return d.mean() / d.std(ddof=1) * math.sqrt(len(d)) if d.std() else 0.0

def confronto(P, Q, nome):
    yv = np.array([r['out'] for r in P]); pm = np.array([r['pm'] for r in P]); n = np.arange(len(yv))
    l0 = -np.log(pm[n, yv]); l1 = -np.log(np.clip(Q[n, yv], 1e-12, 1)); dl = l1 - l0
    h0 = (pm.argmax(1) == yv).astype(float); h1 = (Q.argmax(1) == yv).astype(float); dh = h1 - h0
    se = dh.std(ddof=1) / math.sqrt(len(dh))
    divs = sorted(set(r['div'] for r in P)); meglio = [dv for dv in divs if dl[[r['div'] == dv for r in P]].mean() < 0]
    print(f'  {nome}: {len(P)} partite, contro il maestro {1000 * dl.mean():+.2f} per mille (z {zeta(dl):+.2f}), meglio in {len(meglio)} su {len(divs)}; '
          f'prese {100 * h0.mean():.2f} -> {100 * h1.mean():.2f}% ({100 * dh.mean():+.2f} ±{200 * se:.2f})')
    return dl, dh, divs

def per_lega(P, Q, dl):
    yv = np.array([r['out'] for r in P]); pm = np.array([r['pm'] for r in P])
    for dv in sorted(set(r['div'] for r in P)):
        i = np.array([r['div'] == dv for r in P])
        print(f'    {dv:4s} {i.sum():5d}  {1000 * dl[i].mean():+7.2f} per mille (z {zeta(dl[i]):+.2f})  prese maestro {100 * (pm[i].argmax(1) == yv[i]).mean():5.1f}%'
              f'  candidato {100 * (Q[i].argmax(1) == yv[i]).mean():5.1f}%')

def esplora():
    P, conta = partite(['batch/b94/sette', 'batch/b94/europa2526', 'batch/b94/anno2026', 'batch/b94/cinque', 'batch/b94/inglesi-turchia'], ESPLORA_NUOVI)
    divs = sorted(set(r['div'] for r in P))
    tot = sum(v for (d, k), v in conta.items() if k == 'partite')
    print(f'{len(P)} partite col rating su {tot} ({", ".join(f"{k} {v}" for k, v in sorted(collections.Counter(k for (d, k) in conta.elements() if k != "partite").items()))})')
    yc = np.array([r['yc'] for r in P])
    for nome, a in (('maestro', [r['lgM'] for r in P]), ('quote passate', [r['yq'] for r in P])):
        print(f'  R2 sulla chiusura, {nome:13s} {rq.r2(a, yc)[0]:.3f}')
    c, r2 = ols(P)
    print(f'  R2 sulla chiusura, tutti e due {r2:.3f}: a {c[0]:+.4f}, b {c[1]:.4f}, c {c[2]:.4f}')
    print('per lega (fuori lega: a, b, c stimati senza quella lega)')
    Qf = np.zeros((len(P), 3))
    for dv in divs:
        i = np.array([r['div'] == dv for r in P]); cf, _ = ols([r for r in P if r['div'] != dv])
        Qf[i] = candidato([r for r in P if r['div'] == dv], *cf)
        print(f'    {dv:4s} {i.sum():5d}  senza: a {cf[0]:+.4f}, b {cf[1]:.4f}, c {cf[2]:.4f}')
    print('sui risultati (solo descrittivo):')
    dl, dh, _ = confronto(P, Qf, 'a, b, c fuori lega')
    per_lega(P, Qf, dl)
    confronto(P, candidato(P, *c), 'a, b, c su tutte')
    confronto(P, candidato(P, 0.0, 0.5, 0.5), 'media 50/50 dei log-odds')
    gr = [('2026/27 delle leghe del maestro', lambda r: r['div'] in set(PRINC.values())), ('leghe mai viste dal maestro', lambda r: r['div'] in ESPLORA_NUOVI)]
    for nome, f in gr:
        S = [r for r in P if f(r)]
        if S: confronto(S, Qf[[f(r) for r in P]], nome)
    # calibrazione per fascia del pick
    Q = Qf; yv = np.array([r['out'] for r in P]); pm = np.array([r['pm'] for r in P])
    print('pick per fascia, detto e uscito: maestro | candidato fuori lega')
    for lo_, hi in ((0, .45), (.45, .55), (.55, .65), (.65, 1.01)):
        a1 = (pm.max(1) >= lo_) & (pm.max(1) < hi); a2 = (Q.max(1) >= lo_) & (Q.max(1) < hi)
        print(f'    {100*lo_:3.0f}-{min(100*hi,100):3.0f}%  {a1.sum():5d} {100*pm.max(1)[a1].mean():5.1f} {100*(pm.argmax(1)==yv)[a1].mean():5.1f}  |  '
              f'{a2.sum():5d} {100*Q.max(1)[a2].mean():5.1f} {100*(Q.argmax(1)==yv)[a2].mean():5.1f}')

def prova(cartelle):
    if not REGOLA: sys.exit('REGOLA non fissata')
    P, conta = partite(cartelle, PROVA_NUOVI)
    tot = sum(v for (d, k), v in conta.items() if k == 'partite')
    print(f'{len(P)} partite col rating su {tot} ({", ".join(f"{k} {v}" for k, v in sorted(collections.Counter(k for (d, k) in conta.elements() if k != "partite").items()))})')
    Q = candidato(P, *REGOLA)
    dl, dh, divs = confronto(P, Q, 'il test')
    per_lega(P, Q, dl)
    n100 = [dv for dv in divs if sum(r['div'] == dv for r in P) >= 100]
    meglio = [dv for dv in n100 if dl[[r['div'] == dv for r in P]].mean() < 0]
    se = dh.std(ddof=1) / math.sqrt(len(dh))
    ok = zeta(dl) <= -2 and len(meglio) > len(n100) / 2 and dh.mean() >= -2 * se
    print(f'z {zeta(dl):+.2f}; meglio in {len(meglio)} leghe su {len(n100)} con almeno 100 partite; prese {100 * dh.mean():+.2f} (soglia {-200 * se:.2f})')
    print('ESITO:', 'PASSA' if ok else 'NON PASSA')
    # descrittivi
    yc = np.array([r['yc'] for r in P])
    print('descrittivi:')
    for nome, a in (('maestro', [r['lgM'] for r in P]), ('quote passate', [r['yq'] for r in P]), ('candidato', np.log(Q[:, 0] / Q[:, 2]))):
        print(f'  R2 sulla chiusura, {nome:13s} {rq.r2(a, yc)[0]:.3f}')
    confronto(P, np.array([r['pc'] for r in P]), 'la chiusura stessa')
    c, r2 = ols(P); print(f'  a, b, c stimati sul test (solo descrittivo): {c[0]:+.4f}, {c[1]:.4f}, {c[2]:.4f}, R2 {r2:.3f}')

if __name__ == '__main__':
    a = sys.argv[1:]
    if '--scarica' in a: scarica(ESPLORA_NUOVI)
    elif '--scarica-prova' in a: scarica(PROVA_NUOVI, principali=False)
    elif '--prova' in a: prova([x for x in a if not x.startswith('--')])
    else: esplora()
