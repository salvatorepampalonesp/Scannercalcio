# La bolletta del Toto-Amici: quanto prendono le giocate del gioco dell'utente coi colleghi
# (AGENTS.md, La bolletta del Toto-Amici). Solo descrittivo.
#
#   python3 strumenti/bolletta.py                 quote di chiusura (batch/fd) e Scanner (batch/2627b89, batch/disaccordo)
#   python3 strumenti/bolletta.py --scanner DIR   altre cartelle di CSV del Comparatore (dal b77, col maestro)
#   python3 strumenti/bolletta.py --toto FILE     le bollette vere del gioco (il JSON di /api/snapshot del sito, fuori da git):
#                                                 il margine delle quote in bolletta, per tipo, contro la chiusura di football-data
#
# Il regolamento: dieci giocate per giornata, 1 combo (1X2 + Over/Under 2.5 o 1X2 + Goal/NoGoal, 6 punti), 2 doppie chance
# (1 punto), 3 variabili (Over/Under 2.5, Goal/NoGoal, pari/dispari, 2 punti), 4 fisse (1, X, 2: 4 punti). Con la quota
# del singolo evento a 3,50 o piu' i punti raddoppiano.
#
# Le probabilita' di ogni giocata escono da una matrice dei gol (Dixon-Coles 11x11): con le quote quella allineata
# all'1X2 e all'Over 2.5 del mercato (come lo Scanner dal b57), senza quelle del maestro (b77). Una combo e' la
# probabilita' del segno, quella mostrata, per la probabilita' del bonus dato quel segno nella matrice: cosi' le due
# combo di un segno sommano al segno.
import os, sys, io, csv, glob, math, importlib.util, collections
import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__)); RADICE = os.path.dirname(QUI)
def _mod(nome, f):
    s = importlib.util.spec_from_file_location(nome, os.path.join(QUI, f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
qg = _mod('qg', 'quote-gol.py'); mae = _mod('mae', 'maestro.py'); rq = _mod('rq', 'rating-quote.py')

G = qg.G; I, J = qg.I, qg.J
SEGNI = ['1', 'X', '2']; BONUS = ['Over', 'Under', 'Goal', 'NoGoal']
PUNTI = {'combo': 6, 'doppia': 1, 'variabile': 2, 'fissa': 4}
QUANTE = {'combo': 1, 'doppia': 2, 'variabile': 3, 'fissa': 4}
# margine del bookmaker per stimare la quota dove non c'e' (doppie, combo, Goal, pari e dispari non sono nei file di
# football-data): misurato con --toto sulle 1.120 giocate delle prime sette giornate del 2026/27; pari e dispari non misurati
MARGINE = {'fissa': 0.065, 'doppia': 0.065, 'combo': 0.125, 'Over': 0.06, 'Under': 0.06, 'Goal': 0.095, 'NoGoal': 0.095, 'Pari': 0.08, 'Dispari': 0.08}
RHO = -0.05     # con le sole quote: il rho tipico delle leghe (lo Scanner usa quello stimato della lega)

def maschere():
    tot = I + J
    seg = [(I > J), (I == J), (I < J)]
    bon = {'Over': tot > 2.5, 'Under': tot < 2.5, 'Goal': (I > 0) & (J > 0), 'NoGoal': (I == 0) | (J == 0),
           'Pari': tot % 2 == 0, 'Dispari': tot % 2 == 1}
    return seg, bon
SEG, BON = maschere()

def giocate(P, S):
    # P: matrici (N,11,11); S: 1X2 mostrato (N,3). Torna {nome: (tipo, probabilita' (N,))}
    s = lambda m: (P * m).sum((1, 2))
    pm = np.stack([s(m) for m in SEG], 1)
    out = {}
    for k, n in enumerate(SEGNI): out[n] = ('fissa', S[:, k])
    out['1X'] = ('doppia', S[:, 0] + S[:, 1]); out['X2'] = ('doppia', S[:, 1] + S[:, 2]); out['12'] = ('doppia', S[:, 0] + S[:, 2])
    for b in ('Over', 'Under', 'Goal', 'NoGoal', 'Pari', 'Dispari'): out[b] = ('variabile', s(BON[b]))
    for k, n in enumerate(SEGNI):
        for b in BONUS:
            out[n + '+' + b] = ('combo', S[:, k] * s(SEG[k] & BON[b]) / np.maximum(pm[:, k], 1e-9))
    return out

def esiti(hg, ag):
    hg, ag = np.asarray(hg), np.asarray(ag); tot = hg + ag
    seg = [hg > ag, hg == ag, hg < ag]
    bon = {'Over': tot > 2.5, 'Under': tot < 2.5, 'Goal': (hg > 0) & (ag > 0), 'NoGoal': (hg == 0) | (ag == 0), 'Pari': tot % 2 == 0, 'Dispari': tot % 2 == 1}
    out = {n: seg[k] for k, n in enumerate(SEGNI)}
    out['1X'] = seg[0] | seg[1]; out['X2'] = seg[1] | seg[2]; out['12'] = seg[0] | seg[2]
    out.update(bon)
    for k, n in enumerate(SEGNI):
        for b in BONUS: out[n + '+' + b] = seg[k] & bon[b]
    return {k: v.astype(float) for k, v in out.items()}

def calibrazione(p, y, bins=(0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0001)):
    # errore medio di calibrazione pesato (punti) e la pendenza della ricalibrazione logistica
    b = np.digitize(p, bins) - 1; ece = 0.0; fasce = []
    for k in range(len(bins) - 1):
        w = b == k
        if w.sum() < 30: continue
        ece += w.sum() * abs(p[w].mean() - y[w].mean()); fasce.append((bins[k], int(w.sum()), 100 * p[w].mean(), 100 * y[w].mean()))
    lp = np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1))
    try:
        from sklearn.linear_model import LogisticRegression
        m = LogisticRegression(C=1e6).fit(lp[:, None], y); pend = float(m.coef_[0, 0])
    except Exception: pend = float('nan')
    return 100 * ece / len(p), pend, fasce

def tabella(nome, G_, E, filtro=None):
    print(f'\n{nome}: per ogni giocata la probabilita\' media detta, quante volte e\' uscita, l\'errore di calibrazione (punti)')
    print(f'   {"giocata":14s} {"tipo":10s} {"detta":>7s} {"uscita":>7s} {"errore":>7s} {"pendenza":>9s}')
    for k, (tipo, p) in G_.items():
        y = E[k]; ece, pend, _ = calibrazione(p, y)
        print(f'   {k:14s} {tipo:10s} {100 * p.mean():6.1f}% {100 * y.mean():6.1f}% {ece:7.2f} {pend:9.2f}')

def migliori(nome, G_, E, Q=None):
    # per ogni partita la giocata piu' probabile di ogni tipo: detta contro uscita, e i punti attesi contro i punti fatti
    print(f'\n{nome}: la giocata piu\' probabile di ogni tipo, in ogni partita')
    for tipo in ('fissa', 'doppia', 'variabile', 'combo'):
        ks = [k for k, (t, _) in G_.items() if t == tipo]
        M = np.stack([G_[k][1] for k in ks], 1); Y = np.stack([E[k] for k in ks], 1)
        i = M.argmax(1); r = np.arange(len(i)); p, y = M[r, i], Y[r, i]
        cnt = collections.Counter(ks[j] for j in i).most_common(4)
        print(f'   {tipo:10s} detta {100 * p.mean():5.1f}%, uscita {100 * y.mean():5.1f}% (+/-{200 * y.std() / math.sqrt(len(y)):.1f})  le piu\' scelte: '
              + ', '.join(f'{k} {100 * c / len(i):.0f}%' for k, c in cnt))

def quota_stimata(k, tipo, p):
    return 1 / (np.clip(p, 1e-6, 1) * (1 + MARGINE[k if k in MARGINE else tipo]))

def valori(G_, quote=None):
    # i punti attesi di ogni giocata: probabilita' per punti, raddoppiati se la quota (vera o stimata) e' almeno 3,50
    V = {}
    for k, (tipo, p) in G_.items():
        q = quote[k] if quote is not None and k in quote else quota_stimata(k, tipo, p)
        V[k] = (tipo, p, q, p * PUNTI[tipo] * np.where(q >= 3.5, 2, 1))
    return V

def bolletta(vm):
    # vm: per partita {tipo: (punti attesi, giocata)}. Programmazione dinamica sulle quantita' rimaste: 1/2/3/4
    tipi = list(QUANTE); n = len(vm)
    memo = {}
    def f(i, rest):
        if i == n: return (0.0, ()) if all(r == 0 for r in rest) else (-1e9, ())
        key = (i, rest)
        if key in memo: return memo[key]
        best = (-1e9, ())
        for j, t in enumerate(tipi):
            if rest[j] == 0: continue
            r2 = list(rest); r2[j] -= 1; v, sc = f(i + 1, tuple(r2))
            v += vm[i][t][0]
            if v > best[0]: best = (v, ((t, vm[i][t][1]),) + sc)
        memo[key] = best; return best
    return f(0, tuple(QUANTE[t] for t in tipi))

# ---------- le quote di chiusura ----------
def leggi_fd():
    M = []
    for div in rq.DIVS:
        for s in rq.STAG:
            f = os.path.join(rq.FD, f'{div}_{s}.csv')
            if not os.path.exists(f): continue
            for r in csv.DictReader(io.open(f, encoding='utf-8-sig', errors='replace')):
                d = rq.data(r.get('Date', ''))
                try: hg, ag = int(r['FTHG']), int(r['FTAG'])
                except (KeyError, ValueError): continue
                q = rq.tre(r, ['AvgC', 'PSC', 'B365C'])
                ou = next(([rq.num(r.get(p + '>2.5')), rq.num(r.get(p + '<2.5'))] for p in ('AvgC', 'PC', 'B365C') if rq.num(r.get(p + '>2.5')) and rq.num(r.get(p + '<2.5'))), None)
                if not d or not q or not ou: continue
                M.append(dict(div=div, stag=s, d=d, H=r['HomeTeam'].strip(), A=r['AwayTeam'].strip(), hg=hg, ag=ag, q=q, ou=ou))
    M.sort(key=lambda m: (m['div'], m['d']))
    return M

def con_quote(M):
    Q = np.array([m['q'] for m in M], float); OU = np.array([m['ou'] for m in M], float)
    S = (1 / Q) / (1 / Q).sum(1, keepdims=True); pov = (1 / OU[:, 0]) / (1 / OU).sum(1)
    lh, la = qg.allinea(pov, np.log(S[:, 0] / S[:, 2]), np.full(len(M), RHO))
    P = qg.matrici(lh, la, np.full(len(M), RHO))
    G_ = giocate(P, S)
    quote = {'1': Q[:, 0], 'X': Q[:, 1], '2': Q[:, 2], 'Over': OU[:, 0], 'Under': OU[:, 1],
             '1X': 1 / (1 / Q[:, 0] + 1 / Q[:, 1]), 'X2': 1 / (1 / Q[:, 1] + 1 / Q[:, 2]), '12': 1 / (1 / Q[:, 0] + 1 / Q[:, 2])}
    return G_, quote, (1 / Q).sum(1) - 1, (1 / OU).sum(1) - 1

def giornate(M, div='I1'):
    # le giornate della Serie A dai file: in ordine di data, una giornata finisce quando una squadra gioca di nuovo
    out, cur, sq = [], [], set()
    for i, m in enumerate(M):
        if m['div'] != div: continue
        if m['H'] in sq or m['A'] in sq or (cur and (m['d'] - M[cur[-1]]['d']).days > 5):
            if len(cur) == 10: out.append(cur)
            cur, sq = [], set()
        cur.append(i); sq |= {m['H'], m['A']}
    if len(cur) == 10: out.append(cur)
    return out

def strategie(M, G_, quote, E):
    V = valori(G_, quote); ks = list(V)
    def per_partita(i):
        d = {}
        for t in QUANTE:
            cand = [(V[k][3][i], k) for k in ks if V[k][0] == t]; d[t] = max(cand)
        return d
    tot = collections.defaultdict(list); scelte = collections.Counter()
    for g in giornate(M):
        vm = [per_partita(i) for i in g]
        att, sc = bolletta(vm)
        fatti = sum(PUNTI[t] * (2 if V[k][2][i] >= 3.5 else 1) * E[k][i] for (t, k), i in zip(sc, g))
        tot['ottima: attesi'].append(att); tot['ottima: fatti'].append(fatti)
        for (t, k), i in zip(sc, g): scelte[(t, k, bool(V[k][2][i] >= 3.5))] += 1
        # a occhio: i 4 favoriti piu' netti fisse, il quinto combo col bonus piu' probabile, poi 2 doppie e 3 variabili
        fav = sorted(g, key=lambda i: -max(G_[s][1][i] for s in SEGNI))
        pts = 0.0; attn = 0.0
        for r, i in enumerate(fav):
            t = 'fissa' if r < 4 else 'combo' if r == 4 else 'doppia' if r < 7 else 'variabile'
            cand = [k for k in ks if V[k][0] == t]
            k = max(cand, key=lambda k: V[k][1][i])        # la piu' probabile del tipo, senza guardare il raddoppio
            m = PUNTI[t] * (2 if V[k][2][i] >= 3.5 else 1)
            pts += m * E[k][i]; attn += m * V[k][1][i]
        tot['a occhio: attesi'].append(attn); tot['a occhio: fatti'].append(pts)
    n = len(tot['ottima: fatti'])
    print(f'\nLa bolletta su {n} giornate di Serie A (quote di chiusura), punti a giornata:')
    for k in ('ottima: attesi', 'ottima: fatti', 'a occhio: attesi', 'a occhio: fatti'):
        a = np.array(tot[k]); print(f'   {k:18s} {a.mean():5.1f} (+/-{2 * a.std() / math.sqrt(len(a)):.1f})')
    d = np.array(tot['ottima: fatti']) - np.array(tot['a occhio: fatti'])
    print(f'   ottima meno a occhio: {d.mean():+.2f} punti a giornata (+/-{2 * d.std() / math.sqrt(len(d)):.2f})')
    print('   le giocate della bolletta ottima (tipo, giocata, raddoppio), le piu\' frequenti:')
    for (t, k, x), c in scelte.most_common(14): print(f'      {t:10s} {k:12s} {"x2" if x else "  "} {100 * c / n:5.1f} volte su 100 giornate')

# ---------- le bollette vere ----------
SERIE_A = {'AC Milan': 'Milan', 'AC Monza': 'Monza', 'ACF Fiorentina': 'Fiorentina', 'AS Roma': 'Roma', 'Atalanta BC': 'Atalanta',
           'Bologna FC 1909': 'Bologna', 'Cagliari Calcio': 'Cagliari', 'Como 1907': 'Como', 'FC Internazionale Milano': 'Inter',
           'Frosinone Calcio': 'Frosinone', 'Genoa CFC': 'Genoa', 'Juventus FC': 'Juventus', 'Parma Calcio 1913': 'Parma', 'SS Lazio': 'Lazio',
           'SSC Napoli': 'Napoli', 'Torino FC': 'Torino', 'US Lecce': 'Lecce', 'US Sassuolo Calcio': 'Sassuolo', 'Udinese Calcio': 'Udinese',
           'Venezia FC': 'Venezia', 'Hellas Verona FC': 'Verona', 'Empoli FC': 'Empoli', 'Cremonese': 'Cremonese', 'Pisa SC': 'Pisa'}
TIPO = {'fisse': 'fissa', 'doppie_chance': 'doppia', 'variabili': 'variabile', 'combo': 'combo'}
SIGLA = {'1': '1', 'X': 'X', '2': '2', '1X': '1X', 'X2': 'X2', '12': '12', 'OVER_2.5': 'Over', 'UNDER_2.5': 'Under', 'GOAL': 'Goal',
         'NOGOAL': 'NoGoal', 'PARI': 'Pari', 'DISPARI': 'Dispari'}

def toto(snap):
    # ogni giocata di ogni bolletta: la probabilita' equa dalla chiusura (matrice allineata), la quota in bolletta, il margine
    import json
    d = json.load(io.open(snap, encoding='utf-8'))
    fd = {}
    for r in csv.DictReader(io.open(os.path.join(rq.FD, 'I1_2627.csv'), encoding='utf-8-sig', errors='replace')):
        q = rq.tre(r, ['AvgC', 'PSC', 'B365C']); ou = [rq.num(r.get('AvgC>2.5')), rq.num(r.get('AvgC<2.5'))]
        if q and all(ou): fd[(r['HomeTeam'].strip(), r['AwayTeam'].strip())] = dict(q=q, ou=ou, hg=int(r['FTHG']), ag=int(r['FTAG']))
    par = {}
    for p in d['partite']:
        h, a = p['nome'].split(' - '); k = (SERIE_A.get(h), SERIE_A.get(a))
        if k in fd: par[p['id']] = dict(fd[k], g=p['giornata'])
    ids = list(par); idx = {i: n for n, i in enumerate(ids)}
    G_, quote, mar, maro = con_quote([par[i] for i in ids])
    E = esiti([par[i]['hg'] for i in ids], [par[i]['ag'] for i in ids])
    R, diversi = [], 0
    for sc in d['schedine']:
        for r in sc['righe']:
            if r['partita_id'] not in idx: continue
            pr = r['pronostico']; k = (pr.split('+')[0] + '+' + SIGLA[pr.split('+')[1]]) if '+' in pr else SIGLA[pr]
            n = idx[r['partita_id']]; y = float(r['esito'] == 'vinta'); diversi += E[k][n] != y
            R.append(dict(t=TIPO[r['tipologia']], k=k, q=r['quota'], p=float(G_[k][1][n]), y=y, cl=float(quote[k][n]) if k in quote else None,
                          chi=sc['giocatore'], g=par[r['partita_id']]['g'], punti=r['punti']))
    print(f'Bollette: {len(R)} giocate su {len(ids)} partite con la chiusura di football-data (su {len(d["partite"])}); '
          f'esito diverso dal punteggio: {diversi}. Margine della chiusura: 1X2 {100 * mar.mean():.1f}%, Over/Under {100 * maro.mean():.1f}%.')
    print('\nIl margine in bolletta, 1/(quota x probabilita\' equa) - 1 (la probabilita\' equa dalla matrice allineata alla chiusura):')
    for t in ('fissa', 'doppia', 'variabile', 'combo'):
        L = [r for r in R if r['t'] == t]; m = np.array([1 / (r['q'] * r['p']) - 1 for r in L])
        print(f'   {t:10s} {len(L):5d} giocate: {100 * m.mean():5.1f}% (+/-{200 * m.std() / math.sqrt(len(m)):.1f}), mediana {100 * np.median(m):.1f}%')
        for k, c in collections.Counter(r['k'] for r in L).most_common():
            if c < 5: continue
            m2 = np.array([1 / (r['q'] * r['p']) - 1 for r in L if r['k'] == k])
            print(f'      {k:12s} {c:4d}: {100 * m2.mean():5.1f}%, mediana {100 * np.median(m2):.1f}%, quota media {np.mean([r["q"] for r in L if r["k"] == k]):.2f}')
    print('\nLa quota in bolletta contro la media di chiusura, dove c\'e\':')
    for t in ('fissa', 'doppia', 'variabile'):
        x = np.array([r['q'] / r['cl'] for r in R if r['t'] == t and r['cl']])
        if len(x): print(f'   {t:10s} {len(x):5d}: {x.mean():.3f} (fra {np.percentile(x, 10):.3f} e {np.percentile(x, 90):.3f})')
    print('\nLa quota stimata (col margine di MARGINE) contro quella in bolletta, e la soglia di 3,50:')
    for t in ('fissa', 'doppia', 'variabile', 'combo'):
        L = [r for r in R if r['t'] == t]
        qs = np.array([r['cl'] if r['cl'] else float(quota_stimata(r['k'], t, r['p'])) for r in L]); qb = np.array([r['q'] for r in L])
        print(f'   {t:10s} stimata / bolletta {np.mean(qs / qb):.3f} (fra {np.percentile(qs / qb, 10):.2f} e {np.percentile(qs / qb, 90):.2f}), '
              f'soglia giusta {100 * np.mean((qs >= 3.5) == (qb >= 3.5)):.1f}%')
    print('\nQuante ne sono uscite, contro la probabilita\' equa (le giocate delle bollette, sette giornate: molto rumore):')
    for t in ('fissa', 'doppia', 'variabile', 'combo'):
        L = [r for r in R if r['t'] == t]; p = np.mean([r['p'] for r in L]); y = np.array([r['y'] for r in L])
        print(f'   {t:10s} equa {100 * p:5.1f}%, uscite {100 * y.mean():5.1f}%')
    # la bolletta ottima di ogni giornata (quote vere di chiusura per 1X2 e Over/Under, stimate col margine altrove)
    # contro le bollette giocate, coi punti attesi dalla probabilita' equa e la quota in bolletta
    V = valori(G_, quote); per = collections.defaultdict(list)
    for i in ids: per[par[i]['g']].append(idx[i])
    att, fatti = {}, {}
    for g, L in sorted(per.items()):
        vm = [{t: max((V[k][3][n], k) for k in V if V[k][0] == t) for t in QUANTE} for n in L]
        a_, sc = bolletta(vm); att[g] = a_
        fatti[g] = sum(PUNTI[t] * (2 if V[k][2][n] >= 3.5 else 1) * E[k][n] for (t, k), n in zip(sc, L))
    chi = sorted({r['chi'] for r in R}); A = collections.defaultdict(float); F = collections.defaultdict(float)
    for r in R:
        A[(r['chi'], r['g'])] += r['p'] * PUNTI[r['t']] * (2 if r['q'] >= 3.5 else 1); F[(r['chi'], r['g'])] += r['punti']
    gg = sorted(per)
    a = np.array([[A[(c, g)] for g in gg] for c in chi]); f = np.array([[F[(c, g)] for g in gg] for c in chi])
    print(f'\nLa bolletta ottima contro quelle giocate, giornate {gg[0]}-{gg[-1]}, punti a giornata (attesi dalla probabilita\' equa):')
    print(f'   ottima: attesi {np.mean(list(att.values())):.1f}, fatti {np.mean(list(fatti.values())):.1f}')
    print(f'   le {len(chi)} bollette: attesi {a.mean():.1f} (da {a.mean(1).min():.1f} a {a.mean(1).max():.1f}), fatti {f.mean():.1f} (da {f.mean(1).min():.1f} a {f.mean(1).max():.1f})')

def main():
    a = sys.argv[1:]
    if '--toto' in a: toto(a[a.index('--toto') + 1]); return
    cart = [a[i + 1] for i, x in enumerate(a) if x == '--scanner'] or [os.path.join(RADICE, 'batch', d) for d in ('2627b89', 'disaccordo')]
    M = leggi_fd()
    G_, quote, mar, maro = con_quote(M)
    E = esiti([m['hg'] for m in M], [m['ag'] for m in M])
    print(f'Quote di chiusura (football-data, 18 leghe, 2017/18-2026/27): {len(M)} partite con 1X2 e Over/Under 2.5.'
          f' Margine medio 1X2 {100 * mar.mean():.1f}%, Over/Under {100 * maro.mean():.1f}%.')
    tabella('Con le quote (matrice allineata)', G_, E)
    migliori('Con le quote', G_, E)
    strategie(M, G_, quote, E)
    # lo Scanner: il maestro dei CSV
    S_ = []
    for c in cart:
        for f in sorted(glob.glob(os.path.join(c, '*.csv'))):
            for m in mae.leggi(f):
                x = m['x']
                if 'Maestro: 1 del motore#0' not in x or 'Ambito: lambda casa (ruolo)#0' not in x: continue
                S_.append(m)
    if not S_: print('\nnessun CSV col maestro'); return
    S = np.array([[m['x']['1#0'], m['x']['X#0'], m['x']['2#0']] for m in S_]) / 100; S /= S.sum(1, keepdims=True)
    lh = np.array([m['x']['Ambito: lambda casa (ruolo)#0'] for m in S_]); la = np.array([m['x']['Ambito: lambda trasf. (ruolo)#0'] for m in S_])
    rho = np.array([m['x'].get('Unita: rho stimato#0', RHO) for m in S_])
    G2 = giocate(qg.matrici(lh, la, rho), S); E2 = esiti([m['hg'] for m in S_], [m['ag'] for m in S_])
    print(f'\nLo Scanner senza quote (il maestro, {len(S_)} partite in copia conforme: {", ".join(os.path.basename(c) for c in cart)})')
    tabella('Senza quote (maestro)', G2, E2)
    migliori('Senza quote', G2, E2)

if __name__ == '__main__':
    main()
