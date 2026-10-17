# Le rese della famiglia dei numeri nel tabellone coi corner del b76, senza un batch nuovo (AGENTS.md, Da fare, punto 5).
#
#   python3 strumenti/rese-numeri.py                      # batch/numeri, batch/numeri-prova1, batch/numeri-prova2 (motore b75)
#   python3 strumenti/rese-numeri.py <cartelle>           # altre cartelle fatte con --scritture
#   python3 strumenti/rese-numeri.py --verifica <cartella> # su un batch dal b76: il corner del CSV e' quello ricostruito?
#
# I batch con --scritture portano lo storico che il motore estrae (dettagli.jsonl). Da li' si rifa' il corner del b76:
# lambda = C0 + beta (media della coppia - C0) sulle ultime 30 di tutte (entro 500 giorni), k fissa a 57.2; la base del
# tabellone e' 1 - BN(9; Rif. lega corner, 57.2). Tiri in porta e gialli sono quelli del CSV: il motore non li ha cambiati
# dal b42, e l'arbitro (b85) il Comparatore non ce l'ha. La resa e' quella di EDGE_BANDS: il reale meno la frequenza del
# mercato nella stagione del file, per fascia di scarto (>= 20 / 10 / 5).
import os, sys, io, csv, glob, math, collections, datetime
import numpy as np
from scipy.stats import nbinom

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
os.chdir(ROOT)
VERIFICA = '--verifica' in sys.argv
CARTELLE = [a for a in sys.argv[1:] if not a.startswith('--')] or ['batch/numeri', 'batch/numeri-prova1', 'batch/numeri-prova2']
C0, BETA, K = 9.5947, 0.6431, 57.2          # NUMERI_REG dello Scanner (CORNER_C0, CORNER_BETA, CORNER_K)
CINQUE = {'ITA_Serie_A', 'ENG_Premier_League', 'ESP_LaLiga', 'GER_Bundesliga', 'FRA_Ligue_1'}

# ---------- la lettura di numeri.py (fino alla prima sezione di misure) ----------
_src = io.open('strumenti/numeri.py', encoding='utf-8').read()
_cut = _src.index("# ===================================================================================================\nprint('\\n=== 1.")
_argv = sys.argv; sys.argv = [_argv[0]] + CARTELLE
__file__ = os.path.abspath('strumenti/numeri.py')
exec(compile(_src[:_cut], 'numeri.py', 'exec'), globals())
sys.argv = _argv

STORIA = collections.defaultdict(list)
for k, d in DET.items():
    mid, tid = k.split('|')
    if d.get('dateStrUtc'): STORIA[tid].append((d['dateStrUtc'][:10], mid, d))
for t in STORIA: STORIA[t].sort(key=lambda x: x[0])
_o = lambda s: datetime.date.fromisoformat(s).toordinal()
def storia(tid, giorno, n=30): return [x[2] for x in STORIA[tid] if x[0] < giorno and _o(giorno) - _o(x[0]) < 500][-n:]
def nv(x, k):
    v = x.get(k) if x else None
    return float(v) if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)) else None
def media(s, k):   # come _mean dello Scanner: 0 senza valori
    v = [nv(x, k) for x in s if nv(x, k) is not None]; return float(np.mean(v)) if v else 0.0
def over(L, lam, k): return 1 - nbinom.cdf(math.floor(L), k, k / (k + lam))

def riferimenti(f):
    R = {}
    for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if not r or not r[0]: continue
        if r[0].startswith('=== ARCHIVIO'): break
        if r[0] in ('ID PARTITA', 'Rif. lega corner') and r[0] not in R: R[r[0]] = r
    ids, rif = R['ID PARTITA'], R.get('Rif. lega corner', [])
    return {ids[c]: qb.num(rif[c]) if len(rif) > c else None for c in range(1, len(ids), 4) if ids[c]}
RIF = {}
for d in CARTELLE:
    for f in glob.glob(os.path.join(d, '*.csv')): RIF.update(riferimenti(f))

righe, scarti, senza = [], [], 0   # righe: (file, lega, mercato, p, base, reale)
for g in GIRI:
    m = g['csv']; tab = {t['key']: t for t in m['tab']}
    for key in ('sot8.5', 'yel3.5'):
        t = tab.get(key)
        if t and t['b'] is not None and t['hit'] is not None: righe.append((m['file'], g['lega'], key, t['p'], t['b'], t['hit']))
    t = tab.get('cor9.5')
    if not t or t['hit'] is None: continue
    if t['b'] is not None: righe.append((m['file'], g['lega'], 'cor9.5 CSV', t['p'], t['b'], t['hit']))
    sH, sA = storia(g['h'], m['data']), storia(g['a'], m['data'])
    v = [media(sH, 'cor'), media(sH, 'cor_ag'), media(sA, 'cor'), media(sA, 'cor_ag')]
    ref = RIF.get(m['id'])
    if not all(x > 0 for x in v) or not ref: senza += 1; continue
    lam = min(30, max(1, C0 + BETA * (sum(v) / 2 - C0))); p, b = over(9.5, lam, K), over(9.5, ref, K)
    righe.append((m['file'], g['lega'], 'cor9.5 b76', p, b, t['hit']))
    if t['b'] is not None: scarti.append((abs(p - t['p']) * 100, abs(b - t['b']) * 100))

print(f'corner del b76 ricostruiti su {len(GIRI) - senza} partite su {len(GIRI)}')
if scarti:
    dp, db = max(s[0] for s in scarti), max(s[1] for s in scarti)
    print(f'corner del CSV contro ricostruiti: probabilita\' entro {dp:.3f} punti, base entro {db:.3f}'
          + ('' if VERIFICA else ' (su un CSV fino al b75 e\' il cambiamento del b76, non un errore)'))
if VERIFICA:
    ok = bool(scarti) and dp <= 0.06 and db <= 0.11
    print('COINCIDE' if ok else 'NON COINCIDE: il corner del CSV non e\' quello ricostruito'); sys.exit(0 if ok else 1)

FREQ = collections.defaultdict(dict)
for g in GIRI:
    for t in g['csv']['tab']:
        if t['hit'] is not None: FREQ[(g['csv']['file'], t['key'])][g['csv']['id']] = t['hit']
FREQ = {k: np.mean(list(v.values())) for k, v in FREQ.items()}

def tabella(sel, titolo):
    print(f'\n=== {titolo} ===')
    print(f"{'':12s} {'FORTE (>= 20)':>23s} {'GIOCABILE (>= 10)':>23s} {'MARGINALE (>= 5)':>23s}   scarto medio, quota sopra +5")
    G = collections.defaultdict(list)
    for f, lg, key, p, b, h in sel: G[key].append(((p - b) * 100, h - FREQ[(f, key.split(' ')[0])]))
    def riga(nome, L):
        s = f'{nome:12s}'
        for lo, hi in ((20, 1e9), (10, 20), (5, 10)):
            x = np.array([r for e, r in L if lo <= e < hi])
            s += (f'  {100 * x.mean():+6.1f} ±{200 * x.std(ddof=1) / math.sqrt(len(x)):4.1f} ({len(x):5d})' if len(x) > 1
                  else f"{'-':>23s}")
        e = np.array([e for e, _ in L]); print(s + f'   {e.mean():+5.1f}, {100 * (e >= 5).mean():4.1f}%')
    for key in ('cor9.5 CSV', 'cor9.5 b76', 'sot8.5', 'yel3.5'):
        if G[key]: riga(key, G[key])
    riga('numeri CSV', G['cor9.5 CSV'] + G['sot8.5'] + G['yel3.5'])
    riga('numeri b76', G['cor9.5 b76'] + G['sot8.5'] + G['yel3.5'])

tabella([r for r in righe if r[1] in CINQUE], 'cinque campionati')
tabella([r for r in righe if r[1] not in CINQUE], 'le altre leghe')
print('\nEDGE_BANDS dei numeri (b49, cinque campionati 2023/24-2025/26): +7.2 ±8.0 (133) / +10.2 ±2.9 (1058) / +8.2 ±2.4 (1628)')
