# Il maestro mercato (AGENTS.md, Il maestro mercato: la regola).
#
#   python3 strumenti/maestro.py --allena            # stima REGOLA sulle leghe con le quote (scrive i numeri a schermo)
#   python3 strumenti/maestro.py --prova <cartelle>  # il test registrato, coi numeri di maestro_regola.json
#
# L'idea: il mercato e' un bersaglio molto meno rumoroso del risultato. Si stima, con una regressione ridge, come le
# quantita' del mercato (log p1/pX e log p2/pX dell'1X2 di chiusura tolto il margine in proporzione; i lambda di casa
# e di trasferta della matrice allineata a 1X2 e Over 2.5, b57) dipendono da quello che il motore sa prima della
# partita (65 variabili del CSV). Poi lo si usa senza quote: 1X2 = softmax(T1, 0, T2); gol = Dixon-Coles coi due
# lambda previsti e il rho del motore. Le variabili mancanti prendono la mediana dell'allenamento.
import os, io, re, sys, csv, glob, json, math, collections, contextlib, importlib.util
import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__)); RADICE = os.path.dirname(QUI)
def _mod(nome, f):
    s = importlib.util.spec_from_file_location(nome, os.path.join(QUI, f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
qg = _mod('qg', 'quote-gol.py')
FILE_REGOLA = os.path.join(QUI, 'maestro_regola.json')
ALLENA = ['batch48', 'batch4', 'batch/2627', 'batch/nuove']
FATT = 1.051         # il livello dei gol del b63, da mettere sui lambda di ruolo dei CSV che non lo hanno
ALFA = 10.0          # ridge, sulle variabili standardizzate
FUORI = ('Saudi_Pro_League_2023-2024', 'Super_League_1_2025-2026')   # senza una stagione alle spalle

VIETATE = ('SCORE', 'GOL TOTALI', 'GG REALE', 'PICK', 'COPIA', 'DATA', 'MATCH', 'SQUADRA', 'Nome ', 'ID ', 'METRICA', 'LEGA', 'STAGIONE', 'Tabellone')
def _num(s):
    s = (s or '').strip().replace('%', '').replace(',', '.')
    if s in ('', 'N/D', '--', '-', 'SI', 'NO', 'si', 'no'): return None
    try: v = float(s.split()[0])
    except ValueError: return None
    return v if math.isfinite(v) else None

def leggi(f):
    # per ogni partita in copia conforme: le righe numeriche nella colonna Previsto (solo quello che si sa prima), e il punteggio
    righe = collections.defaultdict(list)
    for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if not r or not r[0]: continue
        if r[0].startswith('=== ARCHIVIO'): break
        righe[r[0]].append(r)
    ids = righe['ID PARTITA'][0]; out = []
    lega = os.path.basename(f).split('_', 2)[2].rsplit('_', 1)[0]
    for c in range(1, len(ids), 4):
        if not ids[c] or not (righe['COPIA CONFORME DELLO SCANNER'][0][c] or '').startswith('SI'): continue
        try: hg, ag = [int(v) for v in righe['SCORE'][0][c].split('-')]
        except Exception: continue
        x = {}
        for k, rr in righe.items():
            if k.startswith('---') or k.startswith('===') or any(k.startswith(v) for v in VIETATE) or len(rr) > 2: continue
            for i, r in enumerate(rr):
                if len(r) > c:
                    v = _num(r[c])
                    if v is not None: x[f'{k}#{i}'] = v
        out.append(dict(id=ids[c], lega=lega, hg=hg, ag=ag, x=x))
    return out

def ha_fattore(f):
    for l in open(f, encoding='utf-8'):
        if l.startswith('Ambito: livello dei gol'): return True
        if l.startswith('=== ARCHIVIO'): return False
    return False

STAT = ['NPxG', 'xG', 'xGOT', 'SoT', 'Corner', 'Possesso %', 'Tocchi Area', 'Big Chances', 'Gol', 'xG Palle Inattive', 'Falli', 'Gialli',
        'Field Tilt %', 'PPDA', 'Ingressi Trequarti', 'Altezza Difensiva', 'Big Ch. Sprecate', 'Tiri Totali']

def variabili(x, fatt):
    g = lambda k, d=None: x.get(k, d)
    try:
        # dal b77 la riga di ruolo e' il lambda del maestro: il motore prima del maestro sta nelle righe Maestro
        mot = x.get('Maestro: lambda casa del motore (ruolo)#0') is not None
        lh = g('Maestro: lambda casa del motore (ruolo)#0') if mot else g('Ambito: lambda casa (ruolo)#0') * fatt
        la = g('Maestro: lambda trasf. del motore (ruolo)#0') if mot else g('Ambito: lambda trasf. (ruolo)#0') * fatt
        ch, ca = g('Ambito: lambda casa (completo)#0'), g('Ambito: lambda trasf. (completo)#0')
        v = {'lgElo': g('Elo: log-odds Elo [completo → 1X2]#0'), 'lgMod': g('Elo: log-odds modello [completo → 1X2]#0'),
             'elod': g('ELO Diff (H-A)#0') / 100, 'hfa': g('HFA Lega#0') / 100,
             'eloH': (g('ELO Casa#0') - 1500) / 100, 'eloA': (g('ELO Trasferta#0') - 1500) / 100,
             'llh': math.log(lh), 'lla': math.log(la), 'lch': math.log(ch), 'lca': math.log(ca), 'rho': g('Unita: rho stimato#0'),
             'lsot': math.log(max(g('Tiri: lambda dai tiri#0', 2.5), 0.3)), 'rigH': g('Unita: rigori casa#0', 0), 'rigA': g('Unita: rigori trasferta#0', 0),
             'attH': g('Unita: attacco casa#0', 1), 'difA': g('Unita: difesa trasferta#0', 1), 'attA': g('Unita: attacco trasferta#0', 1), 'difH': g('Unita: difesa casa#0', 1),
             'mgH': g('Unita: media gol casa#0', 1.5), 'mgA': g('Unita: media gol trasf.#0', 1.2),
             'penH': g('Elo: pendenza casa sul lambda (penH, cap 8%)#0', 0), 'penA': g('Elo: pendenza trasferta sul lambda (penA, cap 8%)#0', 0),
             'nRH': g('Scope: partite di ruolo casa#0', 15), 'nRA': g('Scope: partite di ruolo trasf.#0', 15),
             'serH': min(g('Elo: partite nella serie casa#0', 100), 120) / 100, 'serA': min(g('Elo: partite nella serie trasferta#0', 100), 120) / 100}
        for k in STAT:
            h, a = x.get(k + '#0'), x.get(k + '#1')
            v['d_' + k] = (h - a) if h is not None and a is not None else 0.0
            v['s_' + k] = (h + a) if h is not None and a is not None else None
        m = qg.mercati(qg.matrici([lh], [la], [v['rho']]))
        v['ov25'] = float(qg.logit(m['o25'])[0]); v['gg'] = float(qg.logit(m['gg'])[0]); v['lg12r'] = math.log(m['p1'][0] / m['p2'][0])
        p = [g('Maestro: 1 del motore#0'), g('Maestro: X del motore#0'), g('Maestro: 2 del motore#0')]
        if None in p: p = [g('1#0'), g('X#0'), g('2#0')]
        v['l1x'] = math.log(p[0] / p[1]); v['l2x'] = math.log(p[2] / p[1])
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    if any(v[k] is None for k in ('lgElo', 'lgMod', 'rho')): return None
    return v

def carica(dirs):
    P = {}
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(RADICE, d, '*.csv'))):
            if any(s in f for s in FUORI): continue
            fa = 1.0 if ha_fattore(f) else FATT
            for m in leggi(f):
                m['fatt'] = fa; m['v'] = variabili(m['x'], fa); P[m['id']] = m
    return [m for m in P.values() if m['v'] is not None]

def matrice(M, nomi, mediane=None):
    X = np.array([[np.nan if m['v'].get(k) is None else m['v'][k] for k in nomi] for m in M], float)
    if mediane is None: mediane = np.nanmedian(X, 0)
    return np.where(np.isnan(X), mediane, X), mediane

def soft(a, b):
    Z = np.c_[a, np.zeros(len(a)), b]; Z -= Z.max(1, keepdims=True); E = np.exp(Z); return E / E.sum(1, keepdims=True)

def zeta(d): d = np.asarray(d, float); return d.mean() / d.std(ddof=1) * math.sqrt(len(d))

def _dati():
    qm = _mod('qm', 'quote-matrice.py')
    os.chdir(RADICE)
    with contextlib.redirect_stdout(io.StringIO()): _, Q = qm.carica(ALLENA, 'batch/quote')
    M = {m['id']: m for m in carica(ALLENA)}
    Q = [q for q in Q if q['id'] in M and qg.ou(q['riga'], ['AvgC', 'PC', 'B365C'])[0]]
    MM = [M[q['id']] for q in Q]
    nomi = sorted(MM[0]['v'])
    nomi = [k for k in nomi if not (k.startswith('s_') and np.mean([m['v'][k] is not None for m in MM]) < 0.5)]
    X, med = matrice(MM, nomi)
    tiene = X.std(0) > 1e-9; nomi = [k for k, t in zip(nomi, tiene) if t]; X, med = X[:, tiene], med[tiene]
    OU = np.array([qg.ou(q['riga'], ['AvgC', 'PC', 'B365C'])[0] for q in Q])
    PM = np.array([[1 / v for v in q['qc']] for q in Q]); PM /= PM.sum(1, keepdims=True)
    pov = (1 / OU[:, 0]) / (1 / OU[:, 0] + 1 / OU[:, 1]); rho = X[:, nomi.index('rho')]
    mh, ma = qg.allinea(pov, np.log(PM[:, 0] / PM[:, 2]), rho)
    Y = np.c_[np.log(PM[:, 0] / PM[:, 1]), np.log(PM[:, 2] / PM[:, 1]), np.log(mh), np.log(ma)]
    return Q, MM, nomi, X, med, Y

def _stima(X, med, Y, nomi):
    mu, sd = X.mean(0), X.std(0); Z = np.c_[np.ones(len(Y)), (X - mu) / sd]
    Rg = ALFA * np.eye(Z.shape[1]); Rg[0, 0] = 0
    B = np.linalg.solve(Z.T @ Z + Rg, Z.T @ Y)
    return dict(nomi=nomi, media=[round(float(v), 6) for v in mu], sd=[round(float(v), 6) for v in sd], mediana=[round(float(v), 6) for v in med],
                B=[[round(float(v), 6) for v in r] for r in B], alfa=ALFA)

def allena():
    Q, MM, nomi, X, med, Y = _dati()
    print(f'{len(Q)} partite di {len(set(q["lega"] for q in Q))} leghe, {len(nomi)} variabili')
    reg = _stima(X, med, Y, nomi); reg.update(partite=len(Q), leghe=sorted(set(q['lega'] for q in Q)))
    json.dump(reg, open(FILE_REGOLA, 'w'), indent=1)
    print('scritto', FILE_REGOLA)

def predizioni(dirs):
    # per ogni partita delle cartelle: 1X2 e lambda del maestro. Sulle leghe dell'allenamento coi numeri stimati senza
    # quella lega (fuori lega), sulle altre con quelli registrati: per rimisurare quello che ne dipende senza barare.
    reg = json.load(open(FILE_REGOLA)); M = carica(dirs)
    Q, MM, nomi, X, med, Y = _dati(); lgq = np.array([q['lega'] for q in Q])
    fold = {l: _stima(X[lgq != l], med, Y[lgq != l], nomi) for l in sorted(set(lgq))}
    out = {}
    for l in sorted(set(m['lega'] for m in M)):
        G = [m for m in M if m['lega'] == l]; T = applica(G, fold.get(l, reg))
        for m, t in zip(G, T):
            P = soft(t[:1], t[1:2])[0]; out[m['id']] = dict(p=P, lam=(math.exp(t[2]), math.exp(t[3])), fuori=l in fold)
    return out

def applica(M, reg):
    X, _ = matrice(M, reg['nomi'], np.array(reg['mediana']))
    Z = np.c_[np.ones(len(X)), (X - np.array(reg['media'])) / np.array(reg['sd'])]
    return Z @ np.array(reg['B'])

I, J = np.meshgrid(np.arange(11), np.arange(11), indexing='ij')
def perdite_gol(P, hg, ag):
    idx = np.arange(len(P)); o = {}; tot = hg + ag
    o['esatto'] = -np.log(np.clip(P[idx, np.minimum(hg, 10), np.minimum(ag, 10)], 1e-12, 1))
    for L in (1.5, 2.5, 3.5):
        p = (P * (I + J > L)).sum((1, 2)); y = tot > L; o[f'Over {L}'] = -np.log(np.clip(np.where(y, p, 1 - p), 1e-12, 1))
    p = (P * ((I > 0) & (J > 0))).sum((1, 2)); y = (hg > 0) & (ag > 0); o['Goal'] = -np.log(np.clip(np.where(y, p, 1 - p), 1e-12, 1))
    dd = np.clip(I - J, -3, 3); pd = np.stack([(P * (dd == k)).sum((1, 2)) for k in range(-3, 4)], 1)
    o['differenza reti'] = -np.log(np.clip(pd[idx, np.clip(hg - ag, -3, 3) + 3], 1e-12, 1))
    return o

def prova(dirs):
    reg = json.load(open(FILE_REGOLA))
    M = carica(dirs); lg = np.array([m['lega'] for m in M]); hg = np.array([m['hg'] for m in M]); ag = np.array([m['ag'] for m in M])
    y3 = np.where(hg > ag, 0, np.where(hg == ag, 1, 2)); idx = np.arange(len(M))
    T = applica(M, reg)
    P0 = soft(np.array([m['v']['l1x'] for m in M]), np.array([m['v']['l2x'] for m in M]))   # il motore prima del maestro
    P1 = soft(T[:, 0], T[:, 1])
    ll0, ll1 = -np.log(P0[idx, y3]), -np.log(P1[idx, y3]); d = ll1 - ll0
    leghe = sorted(set(lg)); grandi = [l for l in leghe if (lg == l).sum() >= 100]
    print(f'{len(M)} partite di {len(leghe)} leghe ({len(grandi)} con almeno 100 partite)')
    dp = (P1.argmax(1) == y3).astype(float) - (P0.argmax(1) == y3)
    meglio = sum(d[lg == l].mean() < 0 for l in grandi)
    print(f'\n=== 1X2: maestro contro motore ===\n  logloss {1000 * d.mean():+.2f} per mille (z {zeta(d):+.2f}), meglio in {meglio} leghe su {len(grandi)}'
          f' · prese {100 * (P0.argmax(1) == y3).mean():.2f} -> {100 * (P1.argmax(1) == y3).mean():.2f} ({100 * dp.mean():+.2f}, z {zeta(dp):+.2f})')
    passa1 = zeta(d) <= -2 and meglio > len(grandi) / 2 and zeta(dp) >= -2
    print(f'  ESITO 1X2: {"PASSA" if passa1 else "NON PASSA"}')
    rho = np.array([m['v']['rho'] for m in M]); LH = np.exp([m['v']['llh'] for m in M]); LA = np.exp([m['v']['lla'] for m in M])
    E = perdite_gol(qg.matrici(LH, LA, rho), hg, ag); D = perdite_gol(qg.matrici(np.exp(T[:, 2]), np.exp(T[:, 3]), rho), hg, ag)
    ok = (hg <= 10) & (ag <= 10)
    print('\n=== gol: matrice coi lambda del maestro contro la matrice di ruolo del motore ===')
    for k in E:
        dd = (D[k] - E[k])[ok]; mg = sum(dd[lg[ok] == l].mean() < 0 for l in grandi)
        print(f'  {k:16s} {1000 * dd.mean():+.2f} per mille (z {zeta(dd):+.2f}), meglio in {mg} leghe su {len(grandi)}')
    de = (D['esatto'] - E['esatto'])[ok]; dg = ((D['Over 2.5'] + D['Goal']) - (E['Over 2.5'] + E['Goal']))[ok]
    passa2 = zeta(de) <= -2 and sum(de[lg[ok] == l].mean() < 0 for l in grandi) > len(grandi) / 2 and dg.mean() <= 0
    print(f'  guardia Over 2.5 + Goal: {1000 * dg.mean():+.2f} per mille (z {zeta(dg):+.2f})')
    print(f'  ESITO GOL: {"PASSA" if passa2 else "NON PASSA"}')
    print('\n=== per lega (descrittivo) ===')
    for l in leghe:
        k = lg == l; kk = k & ok
        print(f'  {l:34s} {k.sum():5d}  1X2 {1000 * d[k].mean():+7.2f}  esatto {1000 * (D["esatto"] - E["esatto"])[kk].mean():+7.2f}'
              f'  Over 2.5 {1000 * (D["Over 2.5"] - E["Over 2.5"])[kk].mean():+6.2f}  Goal {1000 * (D["Goal"] - E["Goal"])[kk].mean():+6.2f}')
    print('\n=== descrittivi ===')
    for nome, P in (('motore', P0), ('maestro', P1)):
        pk = P.max(1); print(f'  {nome}: pick {100 * (P.argmax(1) == y3).mean():.2f}% con probabilita\' media {100 * pk.mean():.1f}% · pareggio previsto {100 * P[:, 1].mean():.1f}% (reale {100 * (y3 == 1).mean():.1f}%)')
        for a, b in ((0, .45), (.45, .55), (.55, .65), (.65, 1.01)):
            k = (pk >= a) & (pk < b)
            if k.sum() > 50: print(f'    pick {int(100 * a)}-{min(100, int(100 * b))}%: {k.sum()} partite, previsto {100 * pk[k].mean():.1f}, esce {100 * (P.argmax(1) == y3)[k].mean():.1f}')
    tot = hg + ag
    for nome, A, B in (('Over 2.5', I + J > 2.5, tot > 2.5), ('Goal', (I > 0) & (J > 0), (hg > 0) & (ag > 0))):
        pe = (qg.matrici(LH, LA, rho) * A).sum((1, 2)); pm = (qg.matrici(np.exp(T[:, 2]), np.exp(T[:, 3]), rho) * A).sum((1, 2))
        print(f'  {nome}: previsto motore {100 * pe.mean():.1f}%, maestro {100 * pm.mean():.1f}%, reale {100 * B.mean():.1f}%')
    return passa1, passa2

def rimisura():
    # le tabelle senza quote che dipendono dall'1X2 e dai mercati gol, sulle probabilita' del maestro
    os.chdir(RADICE); qb = qg.qb
    TUTTE = ALLENA + ['batch/livello', 'batch/lontane', 'batch/anno2026', 'batch/europa2526']
    PR = predizioni(TUTTE); R_ = {}
    for d in TUTTE:
        for f in sorted(glob.glob(os.path.join(RADICE, d, '*.csv'))):
            if any(s_ in f for s_ in FUORI): continue
            b = os.path.basename(f)[:-4].split('_', 2)[2]; lab, st = b.rsplit('_', 1)
            for m in qb.leggi_csv(f):
                if m['id'] in PR: m.update(cart=d, lab=lab, st=st, file=f); R_[m['id']] = m
    M = list(R_.values()); print(f'{len(M)} partite')
    def stats(G):
        P = np.array([PR[m['id']]['p'] for m in G]); y = np.array([m['out'] for m in G]); pk = P.max(1); hit = P.argmax(1) == y
        return P, y, pk, hit
    # 1. PICK_RESA
    CINQUE5 = ('ITA_Serie_A', 'ENG_Premier_League', 'ESP_LaLiga', 'GER_Bundesliga', 'FRA_Ligue_1')
    C5 = [m for m in M if m['cart'] == 'batch48' and m['lab'] in CINQUE5]; P, y, pk, hit = stats(C5)
    P0 = np.array([m['p'] for m in C5], float); P0 /= P0.sum(1, keepdims=True); h0 = P0.argmax(1) == y
    print(f'\n=== PICK_RESA, cinque leghe: {len(C5)} partite, pick {100 * hit.mean():.1f}% (motore {100 * h0.mean():.1f}), sempre in casa {100 * (y == 0).mean():.1f}%')
    sog = []
    for t in (70, 65, 60, 55, 50):
        k = pk >= t / 100; q = 100 * k.mean(); sog.append([t, round(100 * hit[k].mean(), 1), round(q), round(100 / q, 1)])
        se = 200 * math.sqrt(hit[k].mean() * (1 - hit[k].mean()) / k.sum())
        k0 = P0.max(1) >= t / 100
        print(f'  >= {t}: {k.sum()} partite, {100 * hit[k].mean():.1f}% ±{se:.1f} su {q:.0f}% del calendario (motore {100 * h0[k0].mean():.1f}% su {100 * k0.mean():.0f}%)')
    print('  soglie: ' + json.dumps(sog))
    def per_lega(G):
        P, y, pk, hit = stats(G); k = pk >= 0.55; sts = sorted({m['st'] for m in G})
        return [len(G), round(100 * hit.mean(), 1), round(100 * hit[k].mean(), 1) if k.any() else None, round(100 * k.mean()), sts, int(k.sum())]
    print('\n=== per lega: partite, pick su tutte, pick sopra il 55%, quota del calendario, stagioni, partite sopra il 55% ===')
    for lab in sorted({m['lab'] for m in M}):
        G = [m for m in M if m['lab'] == lab and m['cart'] != 'batch/2627']
        if not G: continue
        print(f'  {lab:34s} ' + json.dumps(per_lega(G)) + ('  (fuori lega)' if PR[G[0]['id']]['fuori'] else ''))
    # 2. SORPRESA_TAB, sulle 24 leghe del b64
    S = [m for m in M if m['cart'] in ('batch48', 'batch4', 'batch/2627', 'batch/nuove', 'batch/livello') and m['lgModel'] is not None and m['lgElo'] is not None]
    P, y, pk, hit = stats(S); fav = np.where(P[:, 0] >= P[:, 2], 0, 2); und = 2 - fav; pU = P[np.arange(len(S)), und]
    dis = np.array([(m['lgModel'] > 0) != (m['lgElo'] > 0) for m in S])
    cella = lambda s_: [int(s_.sum())] + [round(float(100 * v), 1) for v in ((y[s_] == und[s_]).mean(), (y[s_] == 1).mean(), (y[s_] == fav[s_]).mean())] if s_.any() else None
    js = lambda c: 'null' if c is None else '[' + ', '.join(str(x) for x in c) + ']'
    FAS = [0, 15, 20, 25, 30, 35]; righe = []
    print(f'\n=== SORPRESA_TAB: {len(S)} partite di {len({m["lab"] for m in S})} leghe ===')
    for i, lo in enumerate(FAS):
        hi = FAS[i + 1] if i + 1 < len(FAS) else 101; b_ = (pU * 100 >= lo) & (pU * 100 < hi)
        print(f'  sfavorito {lo}-{hi}%: tutte {cella(b_)} accordo {cella(b_ & ~dis)} disaccordo {cella(b_ & dis)} (previsto {100 * pU[b_].mean():.1f})')
        righe.append(f'  {{ da: {lo}, tutte: {js(cella(b_))}, accordo: {js(cella(b_ & ~dis))}, disaccordo: {js(cella(b_ & dis))} }}')
    r_ = (y == und).astype(float) - pU
    for f_, fn in ((dis, 'disaccordo'), (~dis, 'accordo')):
        print(f'  residuo dello sfavorito, {fn}: {100 * r_[f_].mean():+.2f} (2se {200 * r_[f_].std() / math.sqrt(f_.sum()):.2f}, {f_.sum()} partite)')
    print('const SORPRESA_TAB = { partite: %d, leghe: %d, fasce: [\n%s ] };' % (len(S), len({m['lab'] for m in S}), ',\n'.join(righe)))
    # 3. il tabellone senza quote (EDGE_BANDS 1X2 e gol) e 4. la retta dei binari, sulle cinque leghe
    FAM = {k: 'gol' for k in ('pOv', 'pUn', 'pGG', 'pNG')} | {k: 'numeri' for k in ('cor9.5', 'sot8.5', 'yel3.5')}
    ORD = ['p1', 'pX', 'p2', 'p1X', 'pX2', 'p12', 'pOv', 'pUn', 'pGG', 'pNG', 'cor9.5', 'sot8.5', 'yel3.5']
    cieca = collections.defaultdict(list)
    for m in C5:
        for v in m['tab']:
            if v['hit'] is not None: cieca[(m['file'], v['key'])].append(v['hit'])
    cieca = {k: sum(v) / len(v) for k, v in cieca.items()}
    acc = {'mot': collections.defaultdict(list), 'ma': collections.defaultdict(list)}; prima = {'mot': [], 'ma': []}; bin_ = []
    for m in C5:
        pr = PR[m['id']]; P_ = pr['p']; mat = qg.matrici([pr['lam'][0]], [pr['lam'][1]], [m['rho']]); mk = qg.mercati(mat)
        q = {'p1': P_[0], 'pX': P_[1], 'p2': P_[2], 'p1X': P_[0] + P_[1], 'pX2': P_[1] + P_[2], 'p12': P_[0] + P_[2],
             'pOv': mk['o25'][0], 'pUn': 1 - mk['o25'][0], 'pGG': mk['gg'][0], 'pNG': 1 - mk['gg'][0]}
        for chi, voci in (('mot', [dict(v) for v in m['tab']]), ('ma', [dict(v, p=q.get(v['key'], v['p'])) for v in m['tab']])):
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
        for k_ in ('p1X', 'pX2', 'p12', 'pOv', 'pUn', 'pGG', 'pNG'):
            hv = next((v['hit'] for v in m['tab'] if v['key'] == k_), None)
            if hv is not None: bin_.append((q[k_], hv))
    print(f'\n=== tabellone senza quote, cinque leghe: prima proposta motore {np.mean(prima["mot"]):+.2f}, maestro {np.mean(prima["ma"]):+.2f} ===')
    EB = {}
    for fam in ('1x2', 'gol', 'numeri'):
        for chi in ('mot', 'ma'):
            F = acc[chi]
            print(f'  {fam} {chi}: ' + ' · '.join(f'{nome} ' + ('--' if not F.get((nome, fam)) else f'{np.mean(F[(nome, fam)]):+.1f} ±{2 * np.std(F[(nome, fam)], ddof=1) / math.sqrt(len(F[(nome, fam)])):.1f} ({len(F[(nome, fam)])})') for nome in ('FORTE', 'GIOCABILE', 'MARGINALE')))
        EB[fam] = [[round(float(np.mean(acc['ma'][(n_, fam)])), 1), round(float(2 * np.std(acc['ma'][(n_, fam)], ddof=1) / math.sqrt(len(acc['ma'][(n_, fam)]))), 1), len(acc['ma'][(n_, fam)])] if len(acc['ma'].get((n_, fam), [])) > 1 else None for n_ in ('FORTE', 'GIOCABILE', 'MARGINALE')]
    print('  EDGE_BANDS col maestro: ' + json.dumps(EB))
    B_ = np.array(bin_); pp, hh = 100 * B_[:, 0], 100 * B_[:, 1]
    print(f'\n=== retta dei binari (-5.06 + 1.091 p), {len(B_)} probabilita\' ===')
    for a_ in range(30, 100, 10):
        k = (pp >= a_) & (pp < a_ + 10)
        if k.sum() > 100: print(f'  {a_}-{a_ + 10}: {k.sum()} previsto {pp[k].mean():.1f} retta {-5.06 + 1.091 * pp[k].mean():.1f} esce {hh[k].mean():.1f}')
    A_ = np.c_[np.ones(len(pp)), pp]; co = np.linalg.lstsq(A_, hh, rcond=None)[0]; print(f'  retta stimata: {co[0]:+.2f} + {co[1]:.3f} p')

def schermo(cartelle):
    # lo Scanner calcola il maestro come lo strumento? Dai CSV di un batch (anche finto): le variabili del CSV, i numeri
    # di maestro_regola.json, contro l'1X2 e i lambda stampati. Esce con 1 se uno sta fuori dall'arrotondamento del CSV.
    reg = json.load(open(FILE_REGOLA)); M = []
    for c in cartelle:
        for f in sorted(glob.glob(os.path.join(c, '*.csv'))):
            for m in leggi(f):
                if 'Maestro: 1 del motore#0' not in m['x']: continue
                m['v'] = variabili(m['x'], 1.0)
                if m['v'] is not None: M.append(m)
    if not M: print('nessuna partita col maestro nei CSV'); sys.exit(1)
    T = applica(M, reg); P = soft(T[:, 0], T[:, 1])
    C = np.array([[m['x']['1#0'], m['x']['X#0'], m['x']['2#0']] for m in M]) / 100
    L = np.array([[m['x']['Ambito: lambda casa (ruolo)#0'], m['x']['Ambito: lambda trasf. (ruolo)#0']] for m in M])
    e1, e2 = 100 * np.abs(P - C).max(), np.abs(np.exp(T[:, 2:]) - L).max()
    print(f'{len(M)} partite col maestro: 1X2 entro {e1:.3f} punti, lambda entro {e2:.4f}')
    ok = e1 <= 0.3 and e2 <= 0.01
    print('tutto entro l arrotondamento del CSV' if ok else 'DIVERSI'); sys.exit(0 if ok else 1)

if __name__ == '__main__':
    if '--allena' in sys.argv: allena()
    elif '--rimisura' in sys.argv: rimisura()
    elif '--schermo' in sys.argv: schermo([a for a in sys.argv[1:] if not a.startswith('--')])
    elif '--prova' in sys.argv: prova([a for a in sys.argv[1:] if not a.startswith('--')])
