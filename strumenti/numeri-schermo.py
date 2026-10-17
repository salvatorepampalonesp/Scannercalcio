# Lo schermo dello Scanner contro le formule delle correzioni di Numeri (AGENTS.md, Le card di Numeri: la regola).
#
#   node strumenti/batch-auto.js --finto --scritture --leghe "ITA:Serie A" --stagioni 2025/2026 --out <cartella>
#   python3 strumenti/numeri-schermo.py <cartella>
#
# Per ogni partita rifa' dai valori che il motore estrae dallo storico (dettagli.jsonl) i numeri che la regola ha
# provato, e li confronta con quelli scritti a schermo (scritture.jsonl). Lo storico e' quello del motore: le ultime 30
# partite di lega nei 500 giorni prima del giorno della partita. Ogni riga deve stare entro l'arrotondamento dello
# schermo; esce con 1 se una non ci sta. Serve dopo ogni modifica del motore che tocca le card di Numeri.
import io, os, sys, math, re, datetime as dt
import numpy as np

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'numeri-correzioni.py')
_src = io.open(SRC, encoding='utf-8').read()
_argv = sys.argv; sys.argv = [SRC, '--prova'] + [a for a in _argv[1:] if not a.startswith('--')]
__file__ = SRC
exec(compile(_src[:_src.index('ESITI = []')], SRC, 'exec'), globals())
sys.argv = _argv
R = REGOLA

def storia(tid, giorno, n=30):
    lim = (dt.date.fromisoformat(giorno) - dt.timedelta(days=500)).isoformat()
    return [x[2] for x in STORIA[tid] if lim <= x[0] < giorno][-n:]

RIGHE = []
def rep(nome, schermo, formula, tol):
    a, b = np.asarray(schermo, float), np.asarray(formula, float)
    e = np.abs(a - b); fuori = int((e > tol).sum())
    RIGHE.append(fuori)
    print(f'  {nome:42s} {len(e):5d}   scarto massimo {e.max() if len(e) else float("nan"):.4f}   oltre {tol}: {fuori}'
          + ('' if len(e) else '   NESSUN CONFRONTO'))
    if not len(e): RIGHE.append(1)

V = {k: ([], []) for k in ('rosso', 'corner', 'inattiva', 'recuperi', 'choke', 'cecchino', 'efficienza', 'ult3', 'ult5',
                           'capo', 'tempi', 'modulo')}
def add(k, s, f): V[k][0].append(s); V[k][1].append(f)
PROG = ['prog_carries', 'switches', 'tackles', 'carries_box', 'f3_entries', 'aerials']

for g in GIRI:
    gd = GIORNO[g['id']]; W = g['W']; sH, sA = storia(g['h'], gd), storia(g['a'], gd)
    # rosso: Gamma-Poisson sulle ultime 30, nelle due colonne
    mu = 0
    for st in (sH, sA):
        r = [nv(x, 'red_cards') for x in st if nv(x, 'red_cards') is not None]
        mu += (sum(r) + R['ROSSO_ALFA'] * R['ROSSO_TASSO']) / (len(r) + R['ROSSO_ALFA'])
    for col in ('red-tot-over', 'red-tot-role'):
        v = n0(W.get(col))
        if v is not None: add('rosso', v, 100 * (1 - math.exp(-mu)))
    # corner attesi
    v4 = [media(sH, 'cor'), media(sH, 'cor_ag'), media(sA, 'cor'), media(sA, 'cor_ag')]
    if None not in v4:
        lam = min(max(R['CORNER_C0'] + R['CORNER_BETA'] * (sum(v4) / 2 - R['CORNER_C0']), 1), 30)
        for col in ('cor-tot-over', 'cor-tot-role'):
            v = numeri(W.get(col, ''))
            if v: add('corner', v[0], lam)
    # recuperi e Choke Index, con quello che concede l'avversario
    def adj(k, s):
        mH, mA, cH, cA = media(sH, k), media(sA, k), media(sH, 'opp_' + k), media(sA, 'opp_' + k)
        if None in (mH, mA, cH, cA): return None
        m = (mH + mA + cH + cA) / 4
        return m + s * (mH + cA - 2 * m), m + s * (mA + cH - 2 * m)
    cp, rc = adj('cp_regains', R['CP_S']), adj('rec_time', R['REC_S'])
    for i, l in enumerate('ha'):
        v = n0(W.get('np-cp-' + l))
        if cp and v is not None: add('recuperi', v, cp[i])
        v = n0(W.get('np-choke-' + l))
        if cp and rc and v is not None and rc[i] > 0: add('choke', v, 1.5 * cp[i] / rc[i])
    for l, st in (('h', sH), ('a', sA)):
        # palla inattiva: rapporto delle somme, ristretto
        v = n0(W.get('l-set-' + l))
        s2 = [(nv(x, 'xg_sp'), nv(x, 'npxg')) for x in st if nv(x, 'xg_sp') is not None and nv(x, 'npxg') is not None]
        den = sum(q for _, q in s2)
        if v is not None and len(s2) >= 5 and den > 0:
            add('inattiva', v, R['INATTIVA_M0'] + R['INATTIVA_W'] * (100 * sum(p for p, _ in s2) / den - R['INATTIVA_M0']))
        # cecchino
        h = W.get('l-xgot-' + l, ''); c = numeri(h); xg_, np_ = media(st, 'xgot'), media(st, 'npxg')
        if len(c) >= 2 and xg_ and np_ is not None and 'xG/Tiro' not in h:
            add('cecchino', c[1] - c[0], R['CECCHINO_M0'] + R['CECCHINO_W'] * (xg_ - np_ - R['CECCHINO_M0']))
        # efficienza
        v = n0(W.get(f'e-ef-{l}o')); gf_, x_ = media(st, 'gf'), media(st, 'xg')
        if v is not None and gf_ is not None and x_: add('efficienza', v, 1 + R['EFFICIENZA_W'] * (gf_ / x_ - 1))
        # progressione: ultime 3 e 5 ristrette verso la media lunga
        rows = celle(W.get('table-prog-' + l, ''))[1:]
        for i, k in enumerate(PROG[:len(rows)]):
            vals = [nv(x, k) for x in st]; tot = [x for x in vals if x is not None]
            if not tot: continue
            T = np.mean(tot)
            for n, col, r in ((3, 1, R['PROG_R3']), (5, 2, R['PROG_R5'])):
                w = [x for x in vals[::-1][:n] if x is not None]
                try:
                    if w: add(f'ult{n}', float(rows[i][col]), T + r * (np.mean(w) - T))
                except ValueError: pass
        # capocannoniere
        m = re.match(r'\s*(.+?) \((\d+) gol\) · segna (\d+)%', testo(W.get('ts-' + l, '')))
        # il capocannoniere usa il lambda di ruolo del motore, non quello del maestro (dal b77 nel CSV e' nelle righe Maestro:)
        lm = g['csv'].get('lamM') or [None, None]; lam = (lm if None not in lm else (g['csv'].get('lam') or [None, None]))[0 if l == 'h' else 1]
        G = sum(x['gf'] for x in st)
        if m and lam and G:
            add('capo', float(m.group(3)), 100 * (1 - math.exp(-R['CAPO_C'] * lam * (int(m.group(2)) + 1) / (G + 8))))
        # modulo: i punti a partita su tutte
        c = celle('<tr>' + W.get(f'row-form-{l}o', '') + '</tr>')
        pts = [PT(x['gf'], x['ga']) for x in st if x.get('gf') is not None and x.get('ga') is not None]
        if c and len(c[0]) >= 6 and c[0][5] not in ('N/D', '') and pts: add('modulo', float(c[0][5]), sum(pts) / len(pts))
    # minuti: «Un gol» per fascia, col lambda totale ricavato dalla quota fissa del primo gol
    s30 = n0(W.get('surv-30')); rows = celle(W.get('timing-body', ''))
    if s30 is not None and len(rows) == 6:
        lt = -math.log(1 - s30 / 100) / 0.268
        for i, r_ in enumerate(rows): add('tempi', float(r_[-1].rstrip('%')), 100 * (1 - math.exp(-lt * R['FORMA_TEMPI'][i])))

print()
rep('rosso, le due colonne (punti %)', *V['rosso'], 0.051)
rep('corner attesi', *V['corner'], 0.051)
rep('palla inattiva (punti %)', *V['inattiva'], 0.051)
rep('recuperi entro 5"', *V['recuperi'], 0.051)
rep('Choke Index', *V['choke'], 0.0051)
rep('cecchino, xGOT meno NPxG', *V['cecchino'], 0.0101)
rep('efficienza', *V['efficienza'], 0.0051)
rep('progressione, ultime 3', *V['ult3'], 0.0051)
rep('progressione, ultime 5', *V['ult5'], 0.0051)
rep('capocannoniere segna (punti %, intero)', *V['capo'], 0.6)
rep('Un gol per fascia (punti %, intero)', *V['tempi'], 0.8)
rep('modulo: punti a partita su tutte', *V['modulo'], 0.0051)
ko = sum(RIGHE)
print(f'\n{"tutto entro l arrotondamento dello schermo" if not ko else "DIVERSI: " + str(ko)}')
sys.exit(1 if ko else 0)
