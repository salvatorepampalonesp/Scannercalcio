# Il rating dalle quote passate insieme al maestro (AGENTS.md, Il rating dalle quote passate: la regola).
#
#   python3 strumenti/quote-passate.py --scarica           # i file di football-data dell'esplorazione in batch/fd-nov
#   python3 strumenti/quote-passate.py                     # l'esplorazione: la combinazione stimata sul mercato
#   python3 strumenti/quote-passate.py --scarica-prova     # i file delle leghe del test (dopo aver registrato la regola)
#   python3 strumenti/quote-passate.py --prova batch/b94/livello   # il test registrato, coi numeri di REGOLA
#   python3 strumenti/quote-passate.py --rimisura          # b96: le tabelle senza quote sulle probabilita' col rating
#   python3 strumenti/quote-passate.py --schermo <cartelle>   # b96: lo Scanner calcola il rating come lo strumento?
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
                p = np.array(m['pMa'] or m['p'], float); p /= p.sum()   # il maestro, anche sui CSV dal b96
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

# --- la rimisura del b96: le tabelle senza quote sulle probabilita' col rating dalle quote passate --------------------
# Dai CSV del batch del b94 (batch/b94) e dai file di football-data (batch/fd, batch/fd-nov), nessuna chiamata. Il maestro
# e' rifatto fuori lega sulle 14 leghe del suo allenamento (le partite fino al taglio del 3 ottobre 2026, come nel b77),
# con le registrate altrove; il rating e il candidato sono quelli di REGOLA. Si stampano maestro e candidato sulle stesse
# partite: PICK_RESA (soglie, cinque, fuori), SORPRESA_TAB, EDGE_BANDS dell'1X2 e QUOTE_RESA.
B94 = 'batch/b94'
CINQUE5 = ('ITA_Serie_A', 'ENG_Premier_League', 'ESP_LaLiga', 'GER_Bundesliga', 'FRA_Ligue_1')
STAG_ESTESE = {'2023/24': '2023-2024', '2024/25': '2024-2025', '2025/26': '2025-2026', '2026/27': '2026-2027'}

def _stagioni(txt):
    # '2023/24-2025/26' -> {'2023-2024', '2024-2025', '2025-2026'}; '2023-2025' -> {'2023', '2024', '2025'}; '2026' -> {'2026'}
    a, _, b = txt.partition('-') if '/' in txt else (txt.split('-')[0], '-', txt.split('-')[-1])
    if '/' in a:
        y0, y1 = int(a[:4]), int((b or a)[:4]); return {f'{y}-{y + 1}' for y in range(y0, y1 + 1)}
    return {str(y) for y in range(int(a), int(b or a) + 1)}

def _pick_resa():
    # le voci di PICK_RESA (cinque e fuori) lette da scanner.html: id -> [nome, partite, tutte, >=55, quota, stagioni, n55]
    import json as _j, re as _re
    src = io.open(os.path.join(RADICE, 'scanner.html'), encoding='utf-8').read()
    blocco = src[src.index('const PICK_RESA'):src.index('const _seResa')]
    out = {}
    for parte in ('cinque', 'fuori'):
        b = blocco[blocco.index(parte + ':'):]
        b = b[:b.index('}') + 1]
        for lid, corpo in _re.findall(r"(l_\w+): \[(.*?)\]", b):
            v = __import__('ast').literal_eval('[' + corpo + ']')
            out[lid] = (parte, v)
    return out

def _etichette():
    import json as _j
    L = _j.load(open(os.path.join(RADICE, 'leghe.json')))['data']['leagues']
    return {l['id']: l['country_code'] + '_' + l['name'].replace(' ', '_') for l in L}

def rimisura():
    import json as _j, contextlib
    mm = _mod('mm', 'maestro.py'); qm = _mod('qm', 'quote-matrice.py'); qg = mm.qg
    os.chdir(RADICE)
    cart = sorted(d for d in glob.glob(os.path.join(B94, '*')) if os.path.isdir(d))
    ALL = [os.path.join(B94, c) for c in ('cinque', 'sette', 'inglesi-turchia')]
    # 1. il maestro fuori lega: la ridge rifatta senza ogni lega dell'allenamento (14 leghe coi file principali)
    with contextlib.redirect_stdout(io.StringIO()): _, Q = qm.carica(ALL, 'batch/fd')
    def allena(q):
        lab, st = chiave(q['file']); return st != '2026-2027' or (lab not in TUTTO_2627 and q['data'] < TAGLIO)
    MV = {m['id']: m for m in mm.carica(ALL)}
    Q = [q for q in Q if q['id'] in MV and allena(q) and qg.ou(q['riga'], ['AvgC', 'PC', 'B365C'])[0]]
    MM = [MV[q['id']] for q in Q]
    reg = _j.load(open(mm.FILE_REGOLA)); nomi = reg['nomi']
    X, med = mm.matrice(MM, nomi)
    OU = np.array([qg.ou(q['riga'], ['AvgC', 'PC', 'B365C'])[0] for q in Q])
    PM = np.array([[1 / v for v in q['qc']] for q in Q]); PM /= PM.sum(1, keepdims=True)
    pov = (1 / OU[:, 0]) / (1 / OU[:, 0] + 1 / OU[:, 1]); rho = X[:, nomi.index('rho')]
    mh, ma_ = qg.allinea(pov, np.log(PM[:, 0] / PM[:, 2]), rho)
    Y = np.c_[np.log(PM[:, 0] / PM[:, 1]), np.log(PM[:, 2] / PM[:, 1]), np.log(mh), np.log(ma_)]
    lgq = np.array([q['lega'] for q in Q])
    print(f'allenamento del maestro rifatto dal b94: {len(Q)} partite di {len(set(lgq))} leghe (b77: 16.071 di 14)')
    fold = {l: mm._stima(X[lgq != l], med, Y[lgq != l], nomi) for l in sorted(set(lgq))}
    # 2. tutte le partite del b94, col maestro (fuori lega dove serve) e col rating
    tutte, cache, conta = [], {}, collections.Counter()
    for c in cart:
        for f in sorted(glob.glob(os.path.join(c, '*.csv'))):
            if any(s_ in f for s_ in mm.FUORI): continue
            lab, st = chiave(f)
            V = {m['id']: m for m in mm.leggi(f)}
            for m in V.values(): m['v'] = mm.variabili(m['x'], 1.0)
            G = [m for m in qb.leggi_csv(f) if m['id'] in V and V[m['id']]['v'] is not None]
            if not G: continue
            leg = G[0]['lega']; r_ = fold.get(leg) if lab in PRINC and PRINC[lab] in qm.COD else None
            T = mm.applica([V[m['id']] for m in G], r_ or reg); P = mm.soft(T[:, 0], T[:, 1])
            div = PRINC.get(lab) or NUOVI.get(lab)
            if div and div not in cache:
                cache[div] = rating_finestre(leggi_principale(div) if div in PRINC.values() else leggi_nuovo(div))
            for m, p, t in zip(G, P, T):
                m.update(lab=lab, st=st, cart=os.path.basename(c), file=f, pma=p, lam=(math.exp(t[2]), math.exp(t[3])), fuori=r_ is not None,
                         div=div, yq=None, pc=None)
                if div:
                    x = rq.aggancia(m, cache[div])
                    if x:
                        m['pc'] = np.array(x['pc']) if x['pc'] else None
                        if 'nq' in x and min(x['nq']) >= MIN_Q: m['yq'] = x['yq']
                a, b, cc = REGOLA
                if m['yq'] is not None:
                    lg = a + b * math.log(p[0] / p[2]) + cc * m['yq']; pX = p[1]; p1 = (1 - pX) / (1 + math.exp(-lg))
                    m['pqp'] = np.array([p1, pX, 1 - pX - p1]); conta['col rating'] += 1
                else:
                    m['pqp'] = p; conta['senza rating'] += 1
                tutte.append(m)
    print(f'{len(tutte)} partite del b94: ' + ', '.join(f'{k} {v}' for k, v in conta.items()))
    def stats(G, k):
        P = np.array([m[k] for m in G]); y = np.array([m['out'] for m in G]); pk = P.max(1); hit = P.argmax(1) == y
        return P, y, pk, hit
    C5 = [m for m in tutte if m['lab'] in CINQUE5 and m['st'] != '2026-2027']
    # PICK_RESA, soglie sulle cinque leghe
    print(f'\n=== PICK_RESA, cinque leghe 2023/24-2025/26: {len(C5)} partite, col rating {sum(m["yq"] is not None for m in C5)} ===')
    for k, nome in (('pma', 'maestro'), ('pqp', 'candidato')):
        P, y, pk, hit = stats(C5, k); sog = []
        for t in (70, 65, 60, 55, 50):
            s_ = pk >= t / 100; q = 100 * s_.mean(); sog.append([t, round(100 * hit[s_].mean(), 1), round(q), round(100 / q, 1)])
        print(f'  {nome:10s} tutte {100 * hit.mean():.1f}, casa {100 * (y == 0).mean():.1f}, soglie ' + _j.dumps(sog)
              + '  ±2se ' + ' / '.join(f'{200 * math.sqrt(hit[pk >= t / 100].mean() * (1 - hit[pk >= t / 100].mean()) / (pk >= t / 100).sum()):.1f}' for t in (70, 65, 60, 55, 50)))
    for k, nome in (('pma', 'maestro'), ('pqp', 'candidato')):
        print(f'  {nome:10s} >=65% per lega: ' + ', '.join(f'{lab[4:]} {100 * h[pk >= 0.65].mean():.1f}' for lab in CINQUE5
              for P_, y_, pk, h in [stats([m for m in C5 if m['lab'] == lab], k)]))
    # PICK_RESA lega per lega, sulle stesse stagioni della tabella
    PR, ET = _pick_resa(), _etichette()
    print('\n=== PICK_RESA lega per lega (solo le leghe con le quote passate cambiano): [partite, tutte, >=55, quota, n55] ===')
    nuove = {}
    for lid, (parte, v) in PR.items():
        lab = ET.get(lid); sts = _stagioni(v[5])
        G = [m for m in tutte if m['lab'] == lab and m['st'] in sts]
        if not G: print(f'  {v[0]:30s} nessuna partita ({lab}, {sorted(sts)})'); continue
        riga = {}
        for k in ('pma', 'pqp'):
            P, y, pk, hit = stats(G, k); s_ = pk >= 0.55
            riga[k] = [len(G), round(100 * hit.mean(), 1), round(100 * hit[s_].mean(), 1) if s_.any() else None, round(100 * s_.mean()), int(s_.sum())]
        nr = sum(m['yq'] is not None for m in G)
        tab = [v[1], v[2], v[3], v[4], v[6]]
        print(f'  {parte:6s} {v[0]:30s} tabella {tab}  maestro {riga["pma"]}  candidato {riga["pqp"]}  col rating {nr}/{len(G)}')
        nuove[lid] = (parte, v, riga['pqp'], nr)
    print('\n  le righe nuove (dove entra il rating):')
    for lid, (parte, v, r, nr) in nuove.items():
        if nr: print(f"           {lid}: ['{v[0]}', {r[0]}, {r[1]}, {r[2]}, {r[3]}, '{v[5]}', {r[4]}],  ({parte})")
    # SORPRESA_TAB, sulle 24 leghe del b64 (fino al taglio per il 2026/27)
    VENTIQ = set(CINQUE5) | {'ENG_Championship', 'NED_Eredivisie', 'POR_Liga_Portugal', 'GER_2._Bundesliga', 'BEL_First_Division_A', 'SCO_Premiership',
                             'SUI_Super_League', 'ENG_League_One', 'ENG_League_Two', 'TUR_Super_Lig'}
    DIECI = {'ITA_Serie_A', 'ENG_Premier_League', 'ESP_LaLiga', 'FRA_Ligue_1', 'ENG_Championship', 'NED_Eredivisie', 'POR_Liga_Portugal',
             'BEL_First_Division_A', 'GER_2._Bundesliga', 'SCO_Premiership'}
    S = [m for m in tutte if m['lgModel'] is not None and m['lgElo'] is not None and (
         (m['lab'] in VENTIQ and (m['st'] != '2026-2027' or (m['lab'] in DIECI and m['data'] < TAGLIO))) or m['cart'] == 'livello')]
    print(f'\n=== SORPRESA_TAB: {len(S)} partite di {len({m["lab"] for m in S})} leghe (b77: 23.278 di 24), col rating {sum(m["yq"] is not None for m in S)} ===')
    for k, nome in (('pma', 'maestro'), ('pqp', 'candidato')):
        P, y, pk, hit = stats(S, k); fav = np.where(P[:, 0] >= P[:, 2], 0, 2); und = 2 - fav; pU = P[np.arange(len(S)), und]
        dis = np.array([(m['lgModel'] > 0) != (m['lgElo'] > 0) for m in S])
        cella = lambda s_: [int(s_.sum())] + [round(float(100 * v), 1) for v in ((y[s_] == und[s_]).mean(), (y[s_] == 1).mean(), (y[s_] == fav[s_]).mean())] if s_.any() else None
        js = lambda c: 'null' if c is None else '[' + ', '.join(str(x) for x in c) + ']'
        FAS = [0, 15, 20, 25, 30, 35]; righe = []
        for i, lo_ in enumerate(FAS):
            hi = FAS[i + 1] if i + 1 < len(FAS) else 101; b_ = (pU * 100 >= lo_) & (pU * 100 < hi)
            righe.append(f'  {{ da: {lo_}, tutte: {js(cella(b_))}, accordo: {js(cella(b_ & ~dis))}, disaccordo: {js(cella(b_ & dis))} }}')
        r_ = (y == und).astype(float) - pU
        print(f'  {nome}: residuo dello sfavorito col disaccordo {100 * r_[dis].mean():+.2f} (2se {200 * r_[dis].std() / math.sqrt(dis.sum()):.2f}),'
              f' con l\'accordo {100 * r_[~dis].mean():+.2f} (2se {200 * r_[~dis].std() / math.sqrt((~dis).sum()):.2f})')
        print('const SORPRESA_TAB = { partite: %d, leghe: %d, fasce: [\n%s ] };' % (len(S), len({m['lab'] for m in S}), ',\n'.join(righe)))
    # EDGE_BANDS dell'1X2, cinque leghe: il tabellone del CSV con le probabilita' 1X2 e gol rifatte
    FAM = {k: 'gol' for k in ('pOv', 'pUn', 'pGG', 'pNG')} | {k: 'numeri' for k in ('cor9.5', 'sot8.5', 'yel3.5')} | {k: 'corner' for k in ('cdH', 'cdA', 'chH', 'chA')}
    ORD = ['p1', 'pX', 'p2', 'p1X', 'pX2', 'p12', 'pOv', 'pUn', 'pGG', 'pNG', 'cor9.5', 'sot8.5', 'yel3.5', 'cdH', 'cdA', 'chH', 'chA']
    cieca = collections.defaultdict(list)
    for m in C5:
        for v in m['tab']:
            if v['hit'] is not None: cieca[(m['file'], v['key'])].append(v['hit'])
    cieca = {k: sum(v) / len(v) for k, v in cieca.items()}
    acc = {'pma': collections.defaultdict(list), 'pqp': collections.defaultdict(list)}; prima = {'pma': [], 'pqp': []}
    for m in C5:
        mk = qg.mercati(qg.matrici([m['lam'][0]], [m['lam'][1]], [m['rho']]))
        for chi in ('pma', 'pqp'):
            P_ = m[chi]
            q = {'p1': P_[0], 'pX': P_[1], 'p2': P_[2], 'p1X': P_[0] + P_[1], 'pX2': P_[1] + P_[2], 'p12': P_[0] + P_[2],
                 'pOv': mk['o25'][0], 'pUn': 1 - mk['o25'][0], 'pGG': mk['gg'][0], 'pNG': 1 - mk['gg'][0]}
            voci = [dict(v, p=q.get(v['key'], v['p'])) for v in m['tab']]
            for v in voci: v['e'] = None if v['b'] is None else 100 * (v['p'] - v['b'])
            voci = sorted(voci, key=lambda v: (-(v['e'] if v['e'] is not None else -1e9), ORD.index(v['key'])))
            g = lambda v: None if v['hit'] is None else 100 * (v['hit'] - cieca[(m['file'], v['key'])])
            if voci and g(voci[0]) is not None: prima[chi].append(g(voci[0]))
            for v in voci:
                if v['e'] is None: continue
                for s_, nome in ((20, 'FORTE'), (10, 'GIOCABILE'), (5, 'MARGINALE')):
                    if v['e'] >= s_:
                        if g(v) is not None: acc[chi][(nome, FAM.get(v['key'], '1x2'))].append(g(v))
                        break
    print(f'\n=== EDGE_BANDS, cinque leghe: prima proposta maestro {np.mean(prima["pma"]):+.2f}, candidato {np.mean(prima["pqp"]):+.2f} ===')
    for chi in ('pma', 'pqp'):
        EB = {}
        for fam in ('1x2', 'gol'):
            EB[fam] = [[round(float(np.mean(acc[chi][(n_, fam)])), 1), round(float(2 * np.std(acc[chi][(n_, fam)], ddof=1) / math.sqrt(len(acc[chi][(n_, fam)]))), 1), len(acc[chi][(n_, fam)])]
                       if len(acc[chi].get((n_, fam), [])) > 1 else None for n_ in ('FORTE', 'GIOCABILE', 'MARGINALE')]
        print(f'  {chi}: ' + _j.dumps(EB))
    # QUOTE_RESA: le 12 leghe con la chiusura, 2023/24-2025/26
    DODICI = set(CINQUE5) | {'ENG_Championship', 'NED_Eredivisie', 'POR_Liga_Portugal', 'GER_2._Bundesliga', 'BEL_First_Division_A', 'SCO_Premiership', 'SUI_Super_League'}
    D = [m for m in tutte if m['lab'] in DODICI and m['st'] != '2026-2027' and m['pc'] is not None]
    print(f'\n=== QUOTE_RESA: {len(D)} partite di {len({m["lab"] for m in D})} leghe con la chiusura (b54: 11.902) ===')
    y = np.array([m['out'] for m in D]); pc = np.array([m['pc'] for m in D]); hm = pc.argmax(1) == y
    print(f'  mercato: pick {100 * hm.mean():.1f}%')
    for k, nome in (('pma', 'maestro'), ('pqp', 'candidato')):
        P = np.array([m[k] for m in D]); h = P.argmax(1) == y; dis = P.argmax(1) != pc.argmax(1)
        print(f'  {nome:10s} pick senza quote {100 * h.mean():.1f}%; disaccordo col mercato {dis.sum()} partite ({100 * dis.mean():.1f}%), lì {nome} {100 * h[dis].mean():.1f}%, mercato {100 * hm[dis].mean():.1f}%')

def schermo(cartelle):
    # lo Scanner calcola il rating come lo strumento? Dai CSV di un batch del b96: per ogni partita il rating di football-data
    # rifatto qui (aggancio per data, punteggio e nomi; batch/fd e batch/fd-nov) contro la riga del CSV, e l'1X2 del CSV contro
    # la formula della regola sul maestro del CSV. Esce con 1 se qualcosa sta fuori dall'arrotondamento del CSV.
    a, b, c = REGOLA; cache, n, dy, dp, att, diversi = {}, 0, 0.0, 0.0, collections.Counter(), []
    for cart in cartelle:
        for f in sorted(glob.glob(os.path.join(cart, '*.csv'))):
            lab, st = chiave(f); div = PRINC.get(lab) or NUOVI.get(lab)
            for m in qb.leggi_csv(f):
                if m['qp'] is None: continue
                att[m['qp']] += 1
                if m['qp'] != 'si' or not div: continue
                if div not in cache: cache[div] = rating_finestre(leggi_principale(div) if div in PRINC.values() else leggi_nuovo(div))
                x = rq.aggancia(m, cache[div])
                if not x and len(m['qpNomi']) == 2:
                    # gli alias dello Scanner (QUOTE_ALIAS) lo strumento non li ha: la riga coi nomi che lo Scanner ha agganciato
                    d = dt.date.fromisoformat(m['data'])
                    cc = [r for r in cache[div] if (r['H'], r['A']) == tuple(m['qpNomi']) and abs((r['d'] - d).days) <= 1]
                    x = cc[0] if len(cc) == 1 and (cc[0]['hg'], cc[0]['ag']) == (m['hg'], m['ag']) else None
                    if x: att['coi nomi dello Scanner'] += 1
                if not x or 'nq' not in x: att['non agganciata qui'] += 1; continue
                n += 1; e = abs(x['yq'] - m['yq']); dy = max(dy, e)
                lg = a + b * math.log(m['pMa'][0] / m['pMa'][2]) + c * m['yq']; pX = m['pMa'][1]; p1 = (1 - pX) / (1 + math.exp(-lg))
                ep = 100 * max(abs(p1 - m['p'][0]), abs(1 - pX - p1 - m['p'][2]), abs(pX - m['p'][1])); dp = max(dp, ep)
                if e > 0.0002 or ep > 0.15: diversi.append((m['id'], m['data'], m['H'], m['A'], round(x['yq'], 4), m['yq'], round(ep, 2)))
    print(f'righe Quote passate: {dict(att)}; rifatte qui {n}: rating entro {dy:.5f}, 1X2 entro {dp:.3f} punti')
    for d in diversi[:8]: print('   DIVERSA', d)
    ok = n > 0 and not diversi
    print('tutto entro l arrotondamento del CSV' if ok else 'DIVERSI'); sys.exit(0 if ok else 1)

if __name__ == '__main__':
    a = sys.argv[1:]
    if '--scarica' in a: scarica(ESPLORA_NUOVI)
    elif '--scarica-prova' in a: scarica(PROVA_NUOVI, principali=False)
    elif '--prova' in a: prova([x for x in a if not x.startswith('--')])
    elif '--rimisura' in a: rimisura()
    elif '--schermo' in a: schermo([x for x in a if not x.startswith('--')])
    else: esplora()
