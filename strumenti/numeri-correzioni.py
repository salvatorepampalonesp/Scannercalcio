# Le correzioni delle card di Numeri che non reggono (AGENTS.md, Le card di Numeri: la regola).
#
#   python3 strumenti/numeri-correzioni.py                    # l'esplorazione: batch/numeri e i CSV delle cinque leghe
#   python3 strumenti/numeri-correzioni.py --prova <cartelle> # il test: batch con --scritture mai aperti per Numeri
#          [--csv <cartelle>]                                 # e, per il KNN 1X2, i CSV delle leghe mai guardate per il KNN
#
# Ogni candidato e' fissato in REGOLA. Per ogni partita (o squadra, o gol) si confronta la perdita del candidato con
# quella del numero che lo schermo mostra oggi, appaiata. Un candidato passa se la perdita scende con z <= -2
# sull'insieme e scende in piu' di meta' delle leghe con almeno 50 osservazioni (le eccezioni sono scritte accanto).
import os, sys, io, re, csv, glob, math, json, collections
import numpy as np

REGOLA = {
    # quota dei gol per fascia di 15 minuti: i gol delle 1.743 partite dell'esplorazione (4.682 gol)
    'FORMA_TEMPI': [0.1209, 0.1275, 0.1848, 0.1625, 0.157, 0.2473],
    # rosso: Gamma-Poisson sui rossi di ogni squadra nelle ultime 30, verso un tasso comune
    'ROSSO_TASSO': 0.0931, 'ROSSO_ALFA': 60,
    # corner totali: binomiale negativa, lambda ristretto verso una costante
    'CORNER_C0': 9.5947, 'CORNER_BETA': 0.6431, 'CORNER_K': 57.2,
    # restringimenti James-Stein (peso tau2 / (tau2 + s2/n), dall'esplorazione)
    'CECCHINO_M0': 0.1371, 'CECCHINO_W': 0.270,
    'INATTIVA_M0': 24.77, 'INATTIVA_W': 0.541,
    'EFFICIENZA_W': 0.035,
    # recuperi e tempo di recupero: mio + concesso dall'avversario, ristretto
    'CP_S': 0.279, 'REC_S': 0.808,
    # progressione: media lunga + r (ultime n - media lunga)
    'PROG_R5': 0.166, 'PROG_R3': 0.141,
    # stile del funnel: baricentro previsto, casa meno trasferta, in metri
    'STILE_SOGLIA': 1.5,
    # capocannoniere: 1 - exp(-c lambda (gol + 1) / (gol della squadra + 8))
    'CAPO_C': 0.723,
    # KNN: Goal e Over 2.5 ricalibrati (a + b logit), 1X2 multinomiale sui log(p1/pX), log(p2/pX)
    'KNN_GG': (0.2003, 0.1868), 'KNN_OV': (0.2100, 0.3381),
    'KNN_1X2_W': [[0.5555, -0.3767], [-0.1038, -0.1605], [-0.4518, 0.5373]], 'KNN_1X2_B': [-0.1965, -0.1348, 0.3314],
}
# i file senza una stagione alle spalle restano fuori da ogni misura (AGENTS.md, Le leghe mai viste)
FUORI = ('GRE_Super_League_1_2025-2026', 'KSA_Saudi_Pro_League_2023-2024')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
os.chdir(ROOT)
ARGS = sys.argv[1:]
PROVA = '--prova' in ARGS
def _cartelle(flag, default):
    if flag not in ARGS: return default
    i = ARGS.index(flag) + 1; out = []
    while i < len(ARGS) and not ARGS[i].startswith('--'): out.append(ARGS[i]); i += 1
    return out
SCRITTURE = _cartelle('--prova', ['batch/numeri'])
CSVK = _cartelle('--csv', [])

# ---------- la lettura e le misure di numeri.py (fino alla prima sezione di misure) ----------
_src = io.open('strumenti/numeri.py', encoding='utf-8').read()
_cut = _src.index("# ===================================================================================================\nprint('\\n=== 1.")
_argv = sys.argv; sys.argv = [_argv[0]] + SCRITTURE
__file__ = os.path.abspath('strumenti/numeri.py')
exec(compile(_src[:_cut], 'numeri.py', 'exec'), globals())
sys.argv = _argv

GIORNO = {x['id']: k[0] for k, x in PART.items()}
STORIA = collections.defaultdict(list)
for k, d in DET.items():
    mid, tid = k.split('|')
    if d.get('dateStrUtc'): STORIA[tid].append((d['dateStrUtc'][:10], mid, d))
for t in STORIA: STORIA[t].sort(key=lambda x: x[0])
def storia(tid, giorno, n=30): return [x[2] for x in STORIA[tid] if x[0] < giorno][-n:]
def nv(x, k): v = x.get(k) if x else None; return float(v) if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)) else None
def media(s, k):
    v = [nv(x, k) for x in s if nv(x, k) is not None]; return np.mean(v) if v else None
PT = lambda a, b: 3 if a > b else (1 if a == b else 0)
def lla(p, y): p = min(max(p, 1e-4), 1 - 1e-4); return -(y * math.log(p) + (1 - y) * math.log(1 - p))

ESITI = []
def esito(nome, d, lg, unita='‰', scala=1000, regola='standard'):
    """d: differenze appaiate (candidato meno oggi) di una perdita; negativo = il candidato fa meglio."""
    d, lg = np.asarray(d, float), np.asarray(lg)
    k = ~np.isnan(d); d, lg = d[k], lg[k]
    if len(d) < 30: print(f'  {nome}: troppo poche osservazioni ({len(d)})'); return
    leghe = [l for l in sorted(set(lg)) if (lg == l).sum() >= 50]
    meglio = [l for l in leghe if d[lg == l].mean() < 0]
    z = _z(d); passa = z <= -2 and len(meglio) > len(leghe) / 2
    print(f'  {nome:58s} {len(d):6d}  {scala*d.mean():+8.2f}{unita} (z {z:+6.2f})  meglio in {len(meglio)} leghe su {len(leghe)}'
          + (f'   -> {"PASSA" if passa else "non passa"}' if PROVA and regola == 'standard' else ''))
    ESITI.append((nome, len(d), scala * d.mean(), z, len(meglio), len(leghe), passa if regola == 'standard' else None))
    for l in leghe: PERLEGA[nome].append((l, (lg == l).sum(), scala * d[lg == l].mean()))
PERLEGA = collections.defaultdict(list)

print(f'\nfase: {"TEST su " + ", ".join(SCRITTURE) if PROVA else "esplorazione su " + ", ".join(SCRITTURE)}')

# ===================================================================================================
print('\n=== Quando segnano: la fascia dei gol, forma fissa contro i minuti delle due squadre ===')
def fb(m): return 0 if m <= 15 else 1 if m <= 30 else 2 if m <= 45 else 3 if m <= 60 else 4 if m <= 75 else 5
Q0 = np.array(REGOLA['FORMA_TEMPI']); d, lg = [], []
for g in GIRI:
    c = celle(g['W'].get('timing-body', ''))
    if len(c) < 6: continue
    T = np.array([[float(x) for x in r[1:5]] for r in c[:6]])
    for l, prof in (('h', T[:, 0] + T[:, 3]), ('a', T[:, 2] + T[:, 1])):
        dd = D(g, l)
        if not dd: continue
        q = (prof + 1) / (prof + 1).sum()
        for m in dd.get('goal_timings_scored') or []:
            b = fb(m); d.append(-math.log(Q0[b]) + math.log(q[b])); lg.append(g['lega'])
esito('fascia del gol (logloss)', d, lg)

# ===================================================================================================
print('\n=== Corner, tiri e cartellini ===')
d, lg = [], []
for g in GIRI:
    if not (D(g, 'h') and D(g, 'a')): continue
    a, b = nv(D(g, 'h'), 'red_cards'), nv(D(g, 'a'), 'red_cards'); p0 = pc(g['W'].get('red-tot-role'))
    if a is None or b is None or p0 is None: continue
    gd = GIORNO[g['id']]; mu = 0
    for t in (g['h'], g['a']):
        r = [nv(x, 'red_cards') for x in storia(t, gd) if nv(x, 'red_cards') is not None]
        mu += (sum(r) + REGOLA['ROSSO_ALFA'] * REGOLA['ROSSO_TASSO']) / (len(r) + REGOLA['ROSSO_ALFA'])
    y = float(a + b > 0); d.append(lla(1 - math.exp(-mu), y) - lla(p0, y)); lg.append(g['lega'])
esito('almeno un rosso (logloss)', d, lg)
from scipy.stats import nbinom
d, lg = [], []
for g in GIRI:
    if not (D(g, 'h') and D(g, 'a')): continue
    a, b = nv(D(g, 'h'), 'cor'), nv(D(g, 'a'), 'cor')
    if a is None or b is None: continue
    gd = GIORNO[g['id']]; sH, sA = storia(g['h'], gd), storia(g['a'], gd)
    v = [media(sH, 'cor'), media(sH, 'cor_ag'), media(sA, 'cor'), media(sA, 'cor_ag')]
    if None in v: continue
    lam = min(max(REGOLA['CORNER_C0'] + REGOLA['CORNER_BETA'] * (sum(v) / 2 - REGOLA['CORNER_C0']), 1), 30); k = REGOLA['CORNER_K']
    linee = {}; merc = None
    for r in celle(g['W'].get('mkt-lines', ''))[1:]:
        if len(r) == 5: merc = r[0]; r = r[2:]
        elif len(r) != 3: continue
        if merc == 'Corner': linee[float(r[0])] = pc(r[1])
    if not all(linee.get(L) is not None for L in (8.5, 9.5, 10.5)): continue
    s = 0
    for L in (8.5, 9.5, 10.5):
        y = float(a + b > L); s += lla(1 - nbinom.cdf(math.floor(L), k, k / (k + lam)), y) - lla(linee[L], y)
    d.append(s); lg.append(g['lega'])
esito('corner Over 8.5, 9.5 e 10.5 (somma delle logloss)', d, lg)

# ===================================================================================================
print('\n=== Qualita\' del tiro: cecchino e palle inattive (errore quadratico sulla partita) ===')
def xgot_card(g, l):
    h = g['W'].get('l-xgot-' + l, ''); v = numeri(h); return v if len(v) >= 2 and 'xG/Tiro' not in h else None
d, lg = [], []
for g in GIRI:
    for l in 'ha':
        c, dd = xgot_card(g, l), D(g, l)
        y = (nv(dd, 'xgot') - nv(dd, 'npxg')) if nv(dd, 'xgot') is not None and nv(dd, 'npxg') is not None else None
        if not c or y is None: continue
        oggi = c[1] - c[0]; cand = REGOLA['CECCHINO_M0'] + REGOLA['CECCHINO_W'] * (oggi - REGOLA['CECCHINO_M0'])
        d.append((y - cand) ** 2 - (y - oggi) ** 2); lg.append(g['lega'])
esito('xGOT meno NPxG (il «cecchino»)', d, lg, unita='', scala=1)
d, lg = [], []
for g in GIRI:
    gd = GIORNO[g['id']]
    for l, me in (('h', g['h']), ('a', g['a'])):
        dd = D(g, l); oggi = n0(g['W'].get('l-set-' + l))
        if oggi is None or nv(dd, 'xg_sp') is None or not nv(dd, 'npxg') or nv(dd, 'npxg') <= 0.05: continue
        s = [(nv(x, 'xg_sp'), nv(x, 'npxg')) for x in storia(me, gd) if nv(x, 'xg_sp') is not None and nv(x, 'npxg') is not None]
        den = sum(q for _, q in s)
        if len(s) < 5 or den <= 0: continue
        cand = REGOLA['INATTIVA_M0'] + REGOLA['INATTIVA_W'] * (100 * sum(p for p, _ in s) / den - REGOLA['INATTIVA_M0'])
        y = 100 * nv(dd, 'xg_sp') / nv(dd, 'npxg'); d.append((y - cand) ** 2 - (y - oggi) ** 2); lg.append(g['lega'])
esito('quota dei pericoli da palla inattiva', d, lg, unita=' punti²', scala=1)

# ===================================================================================================
print('\n=== Z-score ed efficienza: gol meno xG della partita ===')
d, lg = [], []
for g in GIRI:
    for l in 'ha':
        ef, xg, dd = n0(g['W'].get(f'e-ef-{l}o')), n0(g['W'].get(f'e-xg-{l}o')), D(g, l)
        if ef is None or xg is None or nv(dd, 'xg') is None: continue
        y = (g['gh'] if l == 'h' else g['ga']) - nv(dd, 'xg'); oggi = (ef - 1) * xg; cand = REGOLA['EFFICIENZA_W'] * oggi
        d.append((y - cand) ** 2 - (y - oggi) ** 2); lg.append(g['lega'])
esito('efficienza (gol / xG) come previsione di gol meno xG', d, lg, unita='', scala=1)

# ===================================================================================================
print('\n=== Non possesso: recuperi e Choke Index fra le due squadre (errore quadratico della differenza) ===')
def adj(sH, sA, k, s):
    mH, mA, cH, cA = media(sH, k), media(sA, k), media(sH, 'opp_' + k), media(sA, 'opp_' + k)
    if None in (mH, mA, cH, cA): return None
    mu = (mH + mA + cH + cA) / 4
    return mu + s * (mH + cA - 2 * mu), mu + s * (mA + cH - 2 * mu)
dcp, dch, lg1, lg2 = [], [], [], []
for g in GIRI:
    if not (D(g, 'h') and D(g, 'a')): continue
    gd = GIORNO[g['id']]; sH, sA = storia(g['h'], gd), storia(g['a'], gd)
    cp = adj(sH, sA, 'cp_regains', REGOLA['CP_S']); rc = adj(sH, sA, 'rec_time', REGOLA['REC_S'])
    yH, yA = nv(D(g, 'h'), 'cp_regains'), nv(D(g, 'a'), 'cp_regains'); rH, rA = nv(D(g, 'h'), 'rec_time'), nv(D(g, 'a'), 'rec_time')
    oH, oA = n0(g['W'].get('np-cp-h')), n0(g['W'].get('np-cp-a'))
    if cp and None not in (yH, yA, oH, oA):
        y = yH - yA; dcp.append((y - (cp[0] - cp[1])) ** 2 - (y - (oH - oA)) ** 2); lg1.append(g['lega'])
    kH, kA = n0(g['W'].get('np-choke-h')), n0(g['W'].get('np-choke-a'))
    if cp and rc and None not in (yH, yA, rH, rA, kH, kA) and rH and rA and kH and kA and rc[0] > 0 and rc[1] > 0:
        y = 1.5 * yH / rH - 1.5 * yA / rA; cand = 1.5 * cp[0] / rc[0] - 1.5 * cp[1] / rc[1]
        dch.append((y - cand) ** 2 - (y - (kH - kA)) ** 2); lg2.append(g['lega'])
esito('recuperi entro 5", casa meno trasferta', dcp, lg1, unita='', scala=1)
esito('Choke Index, casa meno trasferta', dch, lg2, unita='', scala=1)

# ===================================================================================================
print('\n=== Punti contro il modulo avversario: i punti a partita su tutte (errore quadratico) ===')
d, lg = [], []
for g in GIRI:
    for l in 'ha':
        c = celle('<tr>' + g['W'].get(f'row-form-{l}o', '') + '</tr>'); tutte = n0(g['W'].get('pyt-act-' + l))
        if not c or len(c[0]) < 6 or c[0][5] in ('N/D', '') or tutte is None: continue
        y = PT(g['gh'], g['ga']) if l == 'h' else PT(g['ga'], g['gh'])
        d.append((y - tutte) ** 2 - (y - float(c[0][5])) ** 2); lg.append(g['lega'])
esito('punti della partita', d, lg, unita='', scala=1)

# ===================================================================================================
print('\n=== Progressione storica: ultime 5 e 3 ristrette, contro la media lunga (errore quadratico, in sd della metrica) ===')
PROG = [('prog_carries', 0), ('switches', 1), ('tackles', 2), ('carries_box', 3), ('f3_entries', 4), ('aerials', 5)]
for nn, col_, r in ((5, 2, REGOLA['PROG_R5']), (3, 1, REGOLA['PROG_R3'])):
    d, d2, lg = [], [], []
    for k, i in PROG:
        rows = []
        for g in GIRI:
            for l in 'ha':
                c = celle(g['W'].get('table-prog-' + l, '')); y = nv(D(g, l), k)
                if len(c) <= i + 1 or y is None: continue
                try: u, tutte = float(c[i + 1][col_]), float(c[i + 1][5])
                except (ValueError, IndexError): continue
                rows.append((g['lega'], u, tutte, y))
        if not rows: continue
        sd = np.std([r_[3] for r_ in rows])
        for lga, u, tutte, y in rows:
            cand = tutte + r * (u - tutte)
            d.append(((y - cand) ** 2 - (y - tutte) ** 2) / sd ** 2); d2.append(((y - cand) ** 2 - (y - u) ** 2) / sd ** 2); lg.append(lga)
    esito(f'ultime {nn} ristrette contro la media lunga', d, lg, unita=' %', scala=100)
    esito(f'   (ultime {nn} ristrette contro le ultime {nn} di oggi)', d2, lg, unita=' %', scala=100, regola='descrittivo')

# ===================================================================================================
print('\n=== Stile del funnel: il baricentro previsto separa le partite? ===')
gr = collections.defaultdict(list)
for g in GIRI:
    bh, ba = n0(g['W'].get('tr-x-h')), n0(g['W'].get('tr-x-a')); rh, ra = nv(D(g, 'h'), 'avg_x'), nv(D(g, 'a'), 'avg_x')
    if None in (bh, ba, rh, ra): continue
    s = REGOLA['STILE_SOGLIA']; k = 'casa' if bh - ba >= s else ('trasferta' if bh - ba <= -s else 'equilibrio')
    gr[k].append(rh - ra)
tot_ = sum(len(v) for v in gr.values())
for k in ('casa', 'equilibrio', 'trasferta'):
    v = np.array(gr[k]); print(f'  «{k}»: {len(v)} partite ({100*len(v)/tot_:.0f}%), baricentro reale casa meno trasferta {v.mean():+.2f} m (±{2*v.std()/math.sqrt(len(v)):.2f})')
z1 = (np.mean(gr['casa']) - np.mean(gr['equilibrio'])) / math.sqrt(np.var(gr['casa']) / len(gr['casa']) + np.var(gr['equilibrio']) / len(gr['equilibrio']))
z2 = (np.mean(gr['equilibrio']) - np.mean(gr['trasferta'])) / math.sqrt(np.var(gr['equilibrio']) / len(gr['equilibrio']) + np.var(gr['trasferta']) / len(gr['trasferta']))
ok_ = min(len(v) for v in gr.values()) >= 0.2 * tot_ and z1 >= 2 and z2 >= 2
print(f'  scarti fra gruppi vicini: z {z1:+.1f} e {z2:+.1f}' + (f'   -> {"PASSA" if ok_ else "non passa"}' if PROVA else ''))
ESITI.append(('stile del funnel', tot_, None, min(z1, z2), None, None, ok_))

# ===================================================================================================
print('\n=== Punti attesi: la fortuna delle ultime 30 si ripete? (controllo: deve stare entro ±2se da zero) ===')
from scipy.stats import poisson
def xpts(xg, xga):
    M = np.outer(poisson.pmf(np.arange(10), max(xg, .01)), poisson.pmf(np.arange(10), max(xga, .01))); w = np.tril(M, -1).sum(); dr = np.trace(M)
    return 3 * w + dr, 9 * w + dr - (3 * w + dr) ** 2
fl = []
for g in GIRI:
    gd = GIORNO[g['id']]; ep = [pc(g['W'].get(f'mdl-ens-{s}')) for s in ('1', 'x', '2')]
    if None in ep: continue
    for l, me in (('h', g['h']), ('a', g['a'])):
        s = storia(me, gd); e = [xpts(nv(x, 'xg'), nv(x, 'xga')) for x in s if nv(x, 'xg') is not None and nv(x, 'xga') is not None]
        if len(e) < 10: continue
        z = (np.mean([PT(x['gf'], x['ga']) for x in s]) - np.mean([q for q, _ in e])) / (math.sqrt(sum(v for _, v in e)) / len(e))
        res = (PT(g['gh'], g['ga']) if l == 'h' else PT(g['ga'], g['gh'])) - (3 * ep[0] + ep[1] if l == 'h' else 3 * ep[2] + ep[1])
        if abs(z) >= 2: fl.append(res * (1 if z > 0 else -1))
fl = np.array(fl)
ok_ = abs(fl.mean()) <= 2 * fl.std() / math.sqrt(len(fl))
print(f'  squadre con la fortuna oltre 2 deviazioni: {len(fl)}; punti della partita oltre il verdetto, nel verso della fortuna: {fl.mean():+.3f} (±{2*fl.std()/math.sqrt(len(fl)):.3f})'
      + (f'   -> {"non si ripete (conferma)" if ok_ else "si ripete"}' if PROVA else ''))
ESITI.append(('la fortuna non si ripete', len(fl), fl.mean(), None, None, None, ok_))

# ===================================================================================================
print('\n=== Il capocannoniere segna? (logloss contro la frequenza fissa dell\'esplorazione, 18.8%) ===')
d, lg, pp, yy = [], [], [], []
for g in GIRI:
    gd = GIORNO[g['id']]
    for l, me in (('h', g['h']), ('a', g['a'])):
        m = re.match(r'\s*(.+?) \((\d+) gol\)', testo(g['W'].get('ts-' + l, ''))); dd = D(g, l)
        lam = (g['csv'].get('lam') or [None, None])[0 if l == 'h' else 1]
        if not m or not dd or not lam: continue
        G = sum(x['gf'] for x in storia(me, gd))
        if not G: continue
        p = 1 - math.exp(-REGOLA['CAPO_C'] * lam * (int(m.group(2)) + 1) / (G + 8)); y = float(m.group(1).strip() in (dd.get('scorers') or []))
        d.append(lla(p, y) - lla(0.188, y)); lg.append(g['lega']); pp.append(p); yy.append(y)
esito('probabilita\' che il capocannoniere segni', d, lg)
if pp: print(f'      previsto {100*np.mean(pp):.1f}%, esce il {100*np.mean(yy):.1f}%; AUC {auc_lega(np.array(pp), np.array(yy), np.array(lg)):.3f}')

# ===================================================================================================
print('\n=== KNN: Goal e Over 2.5 ricalibrati (logloss) ===')
for k, ev, (a, b) in (('gg', (GH > 0) & (GA > 0), REGOLA['KNN_GG']), ('ov', TOT > 2, REGOLA['KNN_OV'])):
    d, lg = [], []
    for g, y in zip(GIRI, ev):
        p = pc(g['W'].get(f'mdl-knn-{k}'))
        if p is None: continue
        p = min(max(p, 1e-3), 1 - 1e-3); q = 1 / (1 + math.exp(-(a + b * math.log(p / (1 - p)))))
        d.append(lla(q, float(y)) - lla(p, float(y))); lg.append(g['lega'])
    esito(f'KNN {"Goal" if k == "gg" else "Over 2.5"}', d, lg)

# ===================================================================================================
print('\n=== KNN 1X2 ricalibrato (logloss, dai CSV) ===')
def leggi_knn(f):
    righe = collections.defaultdict(list)
    for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if not r or not r[0]: continue
        if r[0].startswith('=== ARCHIVIO'): break
        righe[r[0]].append(r)
    gg = lambda k: righe[k][0] if k in righe else None
    ids, out = gg('ID PARTITA'), []
    for c in range(1, len(ids), 4):
        if not ids[c]: continue
        v = lambda k: gg(k)[c] if gg(k) and len(gg(k)) > c else None
        if not (v('COPIA CONFORME DELLO SCANNER') or '').startswith('SI'): continue
        try: P = [float(v(f'KNN {s}').replace('%', '').replace(',', '.')) / 100 for s in ('1', 'X', '2')]
        except (AttributeError, ValueError): continue
        hg, ag = [int(x) for x in v('SCORE').split('-')]
        out.append((v('LEGA'), np.array(P), 0 if hg > ag else (1 if hg == ag else 2)))
    return out
CINQUE = ('ITA_Serie_A', 'ENG_Premier_League', 'ESP_LaLiga', 'GER_Bundesliga', 'FRA_Ligue_1')
def feat(P): P = np.clip(P, 1e-3, 1); return np.column_stack([np.log(P[:, 0] / P[:, 1]), np.log(P[:, 2] / P[:, 1])])
if not PROVA:
    from sklearn.linear_model import LogisticRegression
    K = [r for f in sorted(glob.glob('batch48/*.csv')) if any(c in f for c in CINQUE) for r in leggi_knn(f)]
    P = np.array([r[1] for r in K]); Y = np.array([r[2] for r in K]); L = np.array([r[0] for r in K])
    M = LogisticRegression(C=1e6, max_iter=5000).fit(feat(P), Y)
    print(f'  coefficienti sulle cinque leghe 2023/24-2025/26 ({len(K)} partite): W {np.round(M.coef_, 4).tolist()} b {np.round(M.intercept_, 4).tolist()}')
    d = np.zeros(len(Y))
    for l in sorted(set(L)):
        tr, te = L != l, L == l
        Mi = LogisticRegression(C=1e6, max_iter=5000).fit(feat(P[tr]), Y[tr]); Q = Mi.predict_proba(feat(P[te]))
        Pn = P[te] / P[te].sum(1, keepdims=True); d[te] = -np.log(Q[np.arange(te.sum()), Y[te]]) + np.log(np.clip(Pn[np.arange(te.sum()), Y[te]], 1e-4, 1))
    esito('KNN 1X2 (fuori lega, sulle cinque leghe 2023/24-2025/26)', d, L)
elif CSVK and REGOLA['KNN_1X2_W']:
    W, B = np.array(REGOLA['KNN_1X2_W']), np.array(REGOLA['KNN_1X2_B'])
    K = [r for c in CSVK for f in sorted(glob.glob(os.path.join(c, '*.csv'))) if not (c.rstrip('/').endswith('batch48') and any(x in f for x in CINQUE)) and not any(x in f for x in FUORI) for r in leggi_knn(f)]
    P = np.array([r[1] for r in K]); Y = np.array([r[2] for r in K]); L = np.array([r[0] for r in K])
    Z = feat(P) @ W.T + B; Q = np.exp(Z - Z.max(1, keepdims=True)); Q /= Q.sum(1, keepdims=True)
    Pn = P / P.sum(1, keepdims=True)
    d = -np.log(Q[np.arange(len(Y)), Y]) + np.log(np.clip(Pn[np.arange(len(Y)), Y], 1e-4, 1))
    esito('KNN 1X2', d, L)

# ===================================================================================================
if PROVA:
    print('\n=== Riepilogo ===')
    for nome, n, dm, z, m, nl, ok_ in ESITI:
        if ok_ is None: continue
        print(f'  {"PASSA    " if ok_ else "non passa"}  {nome}')
