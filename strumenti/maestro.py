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
        lh, la = g('Ambito: lambda casa (ruolo)#0') * fatt, g('Ambito: lambda trasf. (ruolo)#0') * fatt
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
        p = [g('1#0'), g('X#0'), g('2#0')]; v['l1x'] = math.log(p[0] / p[1]); v['l2x'] = math.log(p[2] / p[1])
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

def allena():
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
    mu, sd = X.mean(0), X.std(0); Z = np.c_[np.ones(len(Y)), (X - mu) / sd]
    Rg = ALFA * np.eye(Z.shape[1]); Rg[0, 0] = 0
    B = np.linalg.solve(Z.T @ Z + Rg, Z.T @ Y)
    print(f'{len(Q)} partite di {len(set(q["lega"] for q in Q))} leghe, {len(nomi)} variabili')
    reg = dict(nomi=nomi, media=[round(float(v), 6) for v in mu], sd=[round(float(v), 6) for v in sd], mediana=[round(float(v), 6) for v in med],
               B=[[round(float(v), 6) for v in r] for r in B], alfa=ALFA, partite=len(Q), leghe=sorted(set(q['lega'] for q in Q)))
    json.dump(reg, open(FILE_REGOLA, 'w'), indent=1)
    print('scritto', FILE_REGOLA)

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
    P0 = np.array([[m['x']['1#0'], m['x']['X#0'], m['x']['2#0']] for m in M]); P0 /= P0.sum(1, keepdims=True)
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

if __name__ == '__main__':
    if '--allena' in sys.argv: allena()
    elif '--prova' in sys.argv: prova([a for a in sys.argv[1:] if not a.startswith('--')])
