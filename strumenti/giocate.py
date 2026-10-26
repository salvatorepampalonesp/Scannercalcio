# Tutte le giocate: quanto prendono le probabilita' di 1X2, doppie chance, Over/Under 2.5, Goal/NoGoal e delle 12 combo
# segno + gol, e il margine con cui lo Scanner stima la quota dove il bookmaker non c'e' (AGENTS.md, Tutte le giocate).
# Solo descrittivo.
#
#   python3 strumenti/giocate.py                 quote di chiusura (batch/fd) e Scanner (batch/2627b89, batch/disaccordo)
#   python3 strumenti/giocate.py --scanner DIR   altre cartelle di CSV del Comparatore (dal b77, col maestro)
#   python3 strumenti/giocate.py --quote FILE    quote vere di doppie, gol e combo della Serie A 2026/27 (il JSON dato
#                                                dall'utente, fuori da git): il margine per gruppo contro la chiusura
#
# Le probabilita' escono da una matrice dei gol (Dixon-Coles 11x11): con le quote quella allineata all'1X2 e all'Over 2.5
# del mercato (come lo Scanner dal b57), senza quelle del maestro (b77). Una combo e' la probabilita' del segno, quella
# mostrata, per la probabilita' del gol dato quel segno nella matrice: cosi' le due combo di un tipo sommano al segno.
import os, sys, io, csv, glob, math, importlib.util, collections
import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__)); RADICE = os.path.dirname(QUI)
def _mod(nome, f):
    s = importlib.util.spec_from_file_location(nome, os.path.join(QUI, f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
qg = _mod('qg', 'quote-gol.py'); mae = _mod('mae', 'maestro.py'); rq = _mod('rq', 'rating-quote.py')

G = qg.G; I, J = qg.I, qg.J
SEGNI = ['1', 'X', '2']; BONUS = ['Over', 'Under', 'Goal', 'NoGoal']
GRUPPI = ('1x2', 'doppia', 'ou', 'gg', 'combo')
# margine del bookmaker per stimare la quota dove non c'e' (doppie, combo e Goal non sono nei file di football-data):
# misurato con --quote su 1.120 quote vere delle prime sette giornate di Serie A 2026/27. Uguale a GIOCATE.margine dello Scanner
MARGINE = {'1x2': 0.065, 'doppia': 0.065, 'ou': 0.06, 'gg': 0.095, 'combo': 0.125}
RHO = -0.05     # con le sole quote: il rho tipico delle leghe (lo Scanner usa quello stimato della lega)

def maschere():
    tot = I + J
    seg = [(I > J), (I == J), (I < J)]
    bon = {'Over': tot > 2.5, 'Under': tot < 2.5, 'Goal': (I > 0) & (J > 0), 'NoGoal': (I == 0) | (J == 0)}
    return seg, bon
SEG, BON = maschere()

def giocate(P, S):
    # P: matrici (N,11,11); S: 1X2 mostrato (N,3). Torna {nome: (tipo, probabilita' (N,))}
    s = lambda m: (P * m).sum((1, 2))
    pm = np.stack([s(m) for m in SEG], 1)
    out = {}
    for k, n in enumerate(SEGNI): out[n] = ('1x2', S[:, k])
    out['1X'] = ('doppia', S[:, 0] + S[:, 1]); out['X2'] = ('doppia', S[:, 1] + S[:, 2]); out['12'] = ('doppia', S[:, 0] + S[:, 2])
    for b in ('Over', 'Under'): out[b] = ('ou', s(BON[b]))
    for b in ('Goal', 'NoGoal'): out[b] = ('gg', s(BON[b]))
    for k, n in enumerate(SEGNI):
        for b in BONUS:
            out[n + '+' + b] = ('combo', S[:, k] * s(SEG[k] & BON[b]) / np.maximum(pm[:, k], 1e-9))
    return out

def esiti(hg, ag):
    hg, ag = np.asarray(hg), np.asarray(ag); tot = hg + ag
    seg = [hg > ag, hg == ag, hg < ag]
    bon = {'Over': tot > 2.5, 'Under': tot < 2.5, 'Goal': (hg > 0) & (ag > 0), 'NoGoal': (hg == 0) | (ag == 0)}
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
    print(f'   {"giocata":14s} {"gruppo":10s} {"detta":>7s} {"uscita":>7s} {"errore":>7s} {"pendenza":>9s}')
    for k, (tipo, p) in G_.items():
        y = E[k]; ece, pend, _ = calibrazione(p, y)
        print(f'   {k:14s} {tipo:10s} {100 * p.mean():6.1f}% {100 * y.mean():6.1f}% {ece:7.2f} {pend:9.2f}')

def migliori(nome, G_, E, Q=None):
    # per ogni partita la giocata piu' probabile di ogni gruppo: detta contro uscita, e dove c'e' la quota di chiusura
    # quanto rende giocarla sempre
    print(f'\n{nome}: la giocata piu\' probabile di ogni gruppo, in ogni partita')
    for g in GRUPPI:
        ks = [k for k, (t, _) in G_.items() if t == g]
        M = np.stack([G_[k][1] for k in ks], 1); Y = np.stack([E[k] for k in ks], 1)
        i = M.argmax(1); r = np.arange(len(i)); p, y = M[r, i], Y[r, i]
        cnt = collections.Counter(ks[j] for j in i).most_common(4)
        rende = ''
        if Q is not None and all(k in Q for k in ks):
            qq = np.stack([Q[k] for k in ks], 1)[r, i]; x = y * qq - 1
            rende = f', alla chiusura {100 * x.mean():+.1f}% (+/-{200 * x.std() / math.sqrt(len(x)):.1f})'
        print(f'   {g:7s} detta {100 * p.mean():5.1f}%, uscita {100 * y.mean():5.1f}% (+/-{200 * y.std() / math.sqrt(len(y)):.1f}){rende}  le piu\' scelte: '
              + ', '.join(f'{k} {100 * c / len(i):.0f}%' for k, c in cnt))

def quota_stimata(g, p):
    return 1 / (np.clip(p, 1e-6, 1) * (1 + MARGINE[g]))

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

# ---------- le quote vere (--quote) ----------
SERIE_A = {'AC Milan': 'Milan', 'AC Monza': 'Monza', 'ACF Fiorentina': 'Fiorentina', 'AS Roma': 'Roma', 'Atalanta BC': 'Atalanta',
           'Bologna FC 1909': 'Bologna', 'Cagliari Calcio': 'Cagliari', 'Como 1907': 'Como', 'FC Internazionale Milano': 'Inter',
           'Frosinone Calcio': 'Frosinone', 'Genoa CFC': 'Genoa', 'Juventus FC': 'Juventus', 'Parma Calcio 1913': 'Parma', 'SS Lazio': 'Lazio',
           'SSC Napoli': 'Napoli', 'Torino FC': 'Torino', 'US Lecce': 'Lecce', 'US Sassuolo Calcio': 'Sassuolo', 'Udinese Calcio': 'Udinese',
           'Venezia FC': 'Venezia', 'Hellas Verona FC': 'Verona', 'Empoli FC': 'Empoli', 'Cremonese': 'Cremonese', 'Pisa SC': 'Pisa'}
SIGLA = {'1': '1', 'X': 'X', '2': '2', '1X': '1X', 'X2': 'X2', '12': '12', 'OVER_2.5': 'Over', 'UNDER_2.5': 'Under', 'GOAL': 'Goal',
         'NOGOAL': 'NoGoal'}

def quote_vere(snap):
    # ogni quota vera del file: la probabilita' equa dalla chiusura (matrice allineata), il margine per gruppo, e la quota
    # che lo Scanner stimerebbe col margine di MARGINE contro quella vera. Del file si leggono solo partita, giocata e quota
    import json
    d = json.load(io.open(snap, encoding='utf-8'))
    fd = {}
    for r in csv.DictReader(io.open(os.path.join(rq.FD, 'I1_2627.csv'), encoding='utf-8-sig', errors='replace')):
        q = rq.tre(r, ['AvgC', 'PSC', 'B365C']); ou = [rq.num(r.get('AvgC>2.5')), rq.num(r.get('AvgC<2.5'))]
        if q and all(ou): fd[(r['HomeTeam'].strip(), r['AwayTeam'].strip())] = dict(q=q, ou=ou, hg=int(r['FTHG']), ag=int(r['FTAG']))
    par = {}
    for p in d['partite']:
        h, a = p['nome'].split(' - '); k = (SERIE_A.get(h), SERIE_A.get(a))
        if k in fd: par[p['id']] = fd[k]
    ids = list(par); idx = {i: n for n, i in enumerate(ids)}
    G_, quote, mar, maro = con_quote([par[i] for i in ids])
    R, visti = [], set()
    for sc in d['schedine']:
        for r in sc['righe']:
            if r['partita_id'] not in idx: continue
            pr = r['pronostico']; b = pr.split('+')[1] if '+' in pr else pr
            if b not in SIGLA: continue
            k = (pr.split('+')[0] + '+' + SIGLA[b]) if '+' in pr else SIGLA[pr]
            n = idx[r['partita_id']]; g = G_[k][0]
            R.append(dict(g=g, k=k, q=r['quota'], p=float(G_[k][1][n]), cl=float(quote[k][n]) if k in quote else None))
    print(f'Quote vere: {len(R)} su {len(ids)} partite con la chiusura di football-data (su {len(d["partite"])}). '
          f'Margine della chiusura: 1X2 {100 * mar.mean():.1f}%, Over/Under {100 * maro.mean():.1f}%.')
    print('\nIl margine, 1/(quota x probabilita\' equa) - 1 (la probabilita\' equa dalla matrice allineata alla chiusura):')
    for g in GRUPPI:
        L = [r for r in R if r['g'] == g]
        if not L: continue
        m = np.array([1 / (r['q'] * r['p']) - 1 for r in L])
        print(f'   {g:7s} {len(L):5d} quote: {100 * m.mean():5.1f}% (+/-{200 * m.std() / math.sqrt(len(m)):.1f}), mediana {100 * np.median(m):.1f}%')
    print('\nLa quota vera contro la media di chiusura, dove c\'e\':')
    for g in ('1x2', 'doppia', 'ou'):
        x = np.array([r['q'] / r['cl'] for r in R if r['g'] == g and r['cl']])
        if len(x): print(f'   {g:7s} {len(x):5d}: {x.mean():.3f} (fra {np.percentile(x, 10):.3f} e {np.percentile(x, 90):.3f})')
    print('\nLa quota stimata (col margine di MARGINE) contro quella vera:')
    for g in GRUPPI:
        L = [r for r in R if r['g'] == g]
        if not L: continue
        qs = np.array([float(quota_stimata(g, r['p'])) for r in L]); qb = np.array([r['q'] for r in L])
        print(f'   {g:7s} stimata / vera {np.mean(qs / qb):.3f} (fra {np.percentile(qs / qb, 10):.2f} e {np.percentile(qs / qb, 90):.2f})')

def main():
    a = sys.argv[1:]
    if '--quote' in a: quote_vere(a[a.index('--quote') + 1]); return
    cart = [a[i + 1] for i, x in enumerate(a) if x == '--scanner'] or [os.path.join(RADICE, 'batch', d) for d in ('2627b89', 'disaccordo')]
    M = leggi_fd()
    G_, quote, mar, maro = con_quote(M)
    E = esiti([m['hg'] for m in M], [m['ag'] for m in M])
    print(f'Quote di chiusura (football-data, 18 leghe, 2017/18-2026/27): {len(M)} partite con 1X2 e Over/Under 2.5.'
          f' Margine medio 1X2 {100 * mar.mean():.1f}%, Over/Under {100 * maro.mean():.1f}%.')
    tabella('Con le quote (matrice allineata)', G_, E)
    migliori('Con le quote', G_, E, quote)
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
