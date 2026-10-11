# Le card della scheda Numeri dello Scanner contro il reale (AGENTS.md, Le card di Numeri). Solo misura.
#
#   node strumenti/batch-auto.js --scritture --leghe "..." --stagioni 2025/2026 --out batch/numeri
#   python3 strumenti/numeri.py batch/numeri
#
# Il batch con --scritture registra, per il primo giro di ogni partita (quello dello Scanner), ogni numero che il
# motore scrive a schermo (scritture.jsonl), e i valori che il motore estrae da ogni partita dello storico
# (dettagli.jsonl, chiave partita|squadra). Il reale di una partita per una squadra e' quello che il motore stesso
# estrae da quella partita quando entra nello storico delle partite dopo: stesse fonti, stesse regole. Le partite
# che non entrano in nessuno storico dopo (l'ultima di ogni squadra) restano senza i reali avanzati.
#
# Per ogni numero: previsto contro reale (livello), quanto segue il reale partita per partita (correlazione e
# pendenza dentro la lega, AUC per le probabilita'), e quanto fa meglio di un numero uguale per tutte le partite
# della lega (la media o la frequenza del campione, che e' un riferimento un po' favorito).
import os, sys, re, io, json, glob, math, collections, contextlib, importlib.util
import numpy as np
from sklearn.metrics import roc_auc_score
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
s = importlib.util.spec_from_file_location('qb', 'strumenti/quote-bookmaker.py'); qb = importlib.util.module_from_spec(s); s.loader.exec_module(qb)

CARTELLE = [a for a in sys.argv[1:] if not a.startswith('--')] or ['batch/numeri']

# ---------- lettura ----------
def archivio(f):
    out = {}
    for r in io.open(f, encoding='utf-8-sig'):
        if r.startswith('ARCHIVIO #'):
            c = r.rstrip('\n').split(';')
            out[(c[3][:10], c[5], c[7])] = dict(id=c[1], h=c[5], a=c[7], gh=int(c[9]) if c[9] else None, ga=int(c[10]) if c[10] else None)
    return out

PART, DET = {}, {}
for d in CARTELLE:
    for f in sorted(glob.glob(os.path.join(d, '*.csv'))):
        lega = os.path.basename(f)[len('Backtest_V97_'):].rsplit('_', 1)[0]
        ar = archivio(f)
        with contextlib.redirect_stdout(io.StringIO()): M = {m['id']: m for m in qb.leggi_csv(f)}
        for (giorno, h, a), x in ar.items():
            if x['id'] in M: PART[(giorno, h, a)] = dict(x, lega=lega, csv=M[x['id']])
    for r in io.open(os.path.join(d, 'dettagli.jsonl')):
        j = json.loads(r); DET[j['k']] = j['d']
GIRI = []
for d in CARTELLE:
    for r in io.open(os.path.join(d, 'scritture.jsonl')):
        j = json.loads(r)
        p = PART.get((j['data'], j['casa'], j['trasf']))
        if j['rec'] and p and p['gh'] is not None:
            W = {x[1]: x[2] for x in j['rec']}
            GIRI.append(dict(p, W=W, dh=DET.get(p['id'] + '|' + p['h']), da=DET.get(p['id'] + '|' + p['a'])))
print(f"partite in copia conforme col giro registrato: {len(GIRI)} in {len(set(g['lega'] for g in GIRI))} leghe; "
      f"col reale estratto dal motore per tutte e due le squadre: {sum(1 for g in GIRI if g['dh'] and g['da'])}")

# ---------- lettura dei numeri a schermo ----------
TAG = re.compile(r'<[^>]+>')
NUM = re.compile(r'[-+]?\d+(?:\.\d+)?')
def testo(h): return TAG.sub(' ', h or '').replace('&middot;', ' ').replace('&nbsp;', ' ')
def numeri(h): return [float(x) for x in NUM.findall(testo(h))]
def n0(h):
    t = testo(h).strip()
    if not t or t.startswith('N/D') or t.startswith('--') or t.startswith('N/A'): return None
    v = numeri(t); return v[0] if v else None
def pc(h): v = n0(h); return None if v is None else v / 100
def vnan(v): return np.nan if v is None else v   # lo zero e' un valore: «0.0%» a schermo conta
def celle(h):
    righe = re.findall(r'<tr[^>]*>(.*?)</tr>', h or '', re.S)
    return [[testo(c).strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)] for r in righe]

# ---------- misure ----------
LEGHE = sorted(set(g['lega'] for g in GIRI))
def _z(d): d = np.asarray(d, float); return d.mean() / d.std(ddof=1) * math.sqrt(len(d)) if len(d) > 2 and d.std() > 0 else float('nan')
def auc_lega(p, y, lg):
    au = []
    for l in set(lg):
        k = lg == l
        if 0 < y[k].sum() < k.sum() and k.sum() >= 30: au.append((roc_auc_score(y[k], p[k]), k.sum()))
    return sum(a * n for a, n in au) / sum(n for _, n in au) if au else float('nan')
def bin_(nome, p, y, lg, piu=''):
    p, y, lg = np.asarray(p, float), np.asarray(y, float), np.asarray(lg)
    k = ~np.isnan(p) & ~np.isnan(y); p, y, lg = np.clip(p[k], 1e-4, 1 - 1e-4), y[k], lg[k]
    if len(p) < 30: return print(f'   {nome:44s} troppo poche partite ({len(p)})')
    fr = np.array([y[lg == l].mean() for l in lg])
    ll = -(y * np.log(p) + (1 - y) * np.log(1 - p)); llf = -(y * np.log(np.clip(fr, 1e-4, 1)) + (1 - y) * np.log(np.clip(1 - fr, 1e-4, 1)))
    pend = pendenza_logit(np.log(p / (1 - p)), y)
    print(f'   {nome:44s} {len(p):5d}  previsto {100*p.mean():5.1f}  reale {100*y.mean():5.1f}  AUC {auc_lega(p, y, lg):.3f}  '
          f'pendenza {pend:4.2f}  contro la frequenza della lega {1000*(ll-llf).mean():+6.1f}‰ (z {_z(ll-llf):+5.1f}){piu}')
    return dict(n=len(p), prev=p.mean(), reale=y.mean(), auc=auc_lega(p, y, lg), d=(ll - llf).mean(), z=_z(ll - llf), pend=pend)
def pendenza_logit(lo, y):
    b = np.zeros(2)
    for _ in range(30):
        q = 1 / (1 + np.exp(-(b[0] + b[1] * lo))); W = q * (1 - q) + 1e-9
        H = np.array([[W.sum(), (W * lo).sum()], [(W * lo).sum(), (W * lo * lo).sum()]]); g = np.array([(y - q).sum(), ((y - q) * lo).sum()])
        b = b + np.linalg.solve(H + 1e-9 * np.eye(2), g)
    return b[1]
def cont(nome, x, y, lg, unita='', livello=True):
    x, y, lg = np.asarray(x, float), np.asarray(y, float), np.asarray(lg)
    k = ~np.isnan(x) & ~np.isnan(y); x, y, lg = x[k], y[k], lg[k]
    if len(x) < 30: return print(f'   {nome:44s} troppo poche partite ({len(x)})')
    xm = np.array([x[lg == l].mean() for l in lg]); ym = np.array([y[lg == l].mean() for l in lg])
    xd, yd = x - xm, y - ym
    r = (xd * yd).sum() / math.sqrt((xd * xd).sum() * (yd * yd).sum()) if (xd * xd).sum() > 0 else float('nan')
    sl = (xd * yd).sum() / (xd * xd).sum() if (xd * xd).sum() > 0 else float('nan')
    sk = 1 - ((y - x) ** 2).mean() / ((y - ym) ** 2).mean()
    if not livello:
        print(f'   {nome:44s} {len(x):5d}  correlazione col reale {r:+.3f}  pendenza {sl:+.3f}  (unita\' diverse: niente livello)')
        return dict(n=len(x), r=r, pend=sl)
    print(f'   {nome:44s} {len(x):5d}  previsto {x.mean():7.2f}{unita}  reale {y.mean():7.2f}{unita}  correlazione {r:+.3f}  '
          f'pendenza {sl:+.2f}  errore contro la media della lega {100*sk:+5.1f}%')
    return dict(n=len(x), prev=x.mean(), reale=y.mean(), r=r, pend=sl, skill=sk)
def multi(nome, P, Y, lg):
    P, Y, lg = np.asarray(P, float), np.asarray(Y, int), np.asarray(lg)
    k = ~np.isnan(P).any(1); P, Y, lg = P[k], Y[k], lg[k]
    P = np.clip(P, 1e-4, 1); P = P / P.sum(1, keepdims=True)
    F = np.array([np.bincount(Y[lg == l], minlength=P.shape[1]) / (lg == l).sum() for l in lg])
    ll = -np.log(P[np.arange(len(Y)), Y]); llf = -np.log(np.clip(F[np.arange(len(Y)), Y], 1e-4, 1))
    print(f'   {nome:44s} {len(Y):5d}  logloss {ll.mean():.4f}  contro le frequenze della lega {1000*(ll-llf).mean():+6.1f}‰ (z {_z(ll-llf):+5.1f})  '
          f'la classe piu\' probabile esce il {100*(P.argmax(1)==Y).mean():.1f}%')
    return dict(n=len(Y), ll=ll.mean(), d=(ll - llf).mean(), z=_z(ll - llf))
def fasce(nome, p, y, bordi):
    p, y = np.asarray(p, float), np.asarray(y, float); k = ~np.isnan(p) & ~np.isnan(y); p, y = p[k], y[k]
    s = []
    for a, b in zip(bordi[:-1], bordi[1:]):
        kk = (p >= a) & (p < b)
        if kk.sum() >= 30: s.append(f'{int(100*a)}-{int(100*b) if b <= 1 else 100}: {100*p[kk].mean():.1f} -> {100*y[kk].mean():.1f} ({kk.sum()})')
    print(f'      {nome}, per fascia (previsto -> reale): ' + ' · '.join(s))

def lati(fn):
    """Per i numeri di squadra: le righe di casa e di trasferta insieme."""
    out = []
    for g in GIRI:
        for lato in ('h', 'a'):
            v = fn(g, lato)
            if v is not None: out.append((g['lega'],) + tuple(v))
    return out
def col(rows, i): return np.array([r[i] for r in rows], float)
LG = np.array([g['lega'] for g in GIRI])
D = lambda g, l: g['d' + l]
def det(g, l, k):
    d = D(g, l); v = d.get(k) if d else None
    return float(v) if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)) else None
GH = np.array([g['gh'] for g in GIRI]); GA = np.array([g['ga'] for g in GIRI]); TOT = GH + GA
ESITO = np.where(GH > GA, 0, np.where(GH == GA, 1, 2))
SUF = {'h': 'h', 'a': 'a'}

# ===================================================================================================
print('\n=== 1. Confidence e modelli ===')
for pre, nome in (('mdl-dc', 'Dixon-Coles di ruolo'), ('mdl-dco', 'Dixon-Coles generale'), ('mdl-mk', 'Markov di ruolo'),
                  ('mdl-mko', 'Markov generale'), ('mdl-knn', 'KNN'), ('mdl-ol', 'Ordered Logit'), ('mdl-ens', 'Ensemble (il verdetto)')):
    P = np.array([[pc(g['W'].get(f'{pre}-{s}')) if pc(g['W'].get(f'{pre}-{s}')) is not None else np.nan for s in ('1', 'x', '2')] for g in GIRI])
    multi(f'1X2 {nome}', P, ESITO, LG)
print('  generale contro ruolo (la colonna con la spunta e\' quella che il motore usa):')
EV = {'1': ESITO == 0, 'x': ESITO == 1, '2': ESITO == 2, '1x': ESITO != 2, 'x2': ESITO != 0, '12': ESITO != 1,
      'gg': (GH > 0) & (GA > 0), 'ov': TOT > 2}
for k, nome in (('1', '1'), ('x', 'X'), ('2', '2'), ('1x', '1X'), ('x2', 'X2'), ('12', '12'), ('gg', 'Goal'), ('ov', 'Over 2.5')):
    for amb in ('over', 'role'):
        bin_(f'{nome} {"generale" if amb == "over" else "ruolo"}', [vnan(pc(g['W'].get(f'p{k}-{amb}' if k not in ('gg', 'ov') else f'{k}-{amb}'))) for g in GIRI], EV[k], LG)
print('  doppie chance, Goal e Over del Dixon-Coles e del KNN:')
for pre, nome in (('mdl-dc', 'DC'), ('mdl-knn', 'KNN')):
    for k, ev in (('1x', '1x'), ('x2', 'x2'), ('12', '12'), ('gg', 'gg'), ('ng', None), ('ov', 'ov'), ('un', None)):
        y = EV[ev] if ev else (~EV['gg'] if k == 'ng' else ~EV['ov'])
        bin_(f'{nome} {k.upper()}', [vnan(pc(g['W'].get(f'{pre}-{k}'))) for g in GIRI], y, LG)
print('  le confidence (il numero a schermo, da 0 a 100, contro quante volte esce):')
for k, ev in (('p1', '1'), ('px', 'x'), ('p2', '2'), ('1x', '1x'), ('x2', 'x2'), ('12', '12'), ('gg', 'gg'), ('ov', 'ov')):
    p = np.array([(vnan(n0(g['W'].get('conf-' + k)))) / 100 for g in GIRI]); r = bin_(f'confidence {k.upper()}', p, EV[ev], LG)
for k, y in (('ng', ~EV['gg']), ('un', ~EV['ov'])):
    p = np.array([(vnan(n0(g['W'].get('conf-' + k)))) / 100 for g in GIRI]); bin_(f'confidence {k.upper()}', p, y, LG)
pick = np.array([np.argmax([pc(g['W'].get(f'mdl-ens-{s}')) or 0 for s in ('1', 'x', '2')]) for g in GIRI])
cg = np.array([(vnan(n0(g['W'].get('master-conf')))) / 100 for g in GIRI])
r = bin_('confidence globale (il pick)', cg, (pick == ESITO).astype(float), LG); fasce('confidence globale', cg, (pick == ESITO), [0, .4, .45, .5, .55, .6, .65, .7, 1.01])
SOGLIE = json.loads(re.search(r'soglie: (\[\[.*?\]\]),', io.open('scanner.html', encoding='utf-8').read()).group(1))
pp = np.array([max(pc(g['W'].get(f'mdl-ens-{s}')) or 0 for s in ('1', 'x', '2')) for g in GIRI]); ok = pick == ESITO
print('  le soglie del pick (la card «Quante volte esce il pick», PICK_RESA; queste partite sono fra quelle su cui e\' misurata):')
for so, resa, quota, _ in sorted(SOGLIE):
    k = pp >= so / 100
    if k.sum(): print(f'   pick al {so}% o piu\': {k.sum():4d} partite ({100*k.mean():.0f}% del calendario, la card dice {quota}%), esce il {100*ok[k].mean():.1f}% '
                      f'(±{200*math.sqrt(ok[k].mean()*(1-ok[k].mean())/k.sum()):.1f}; la card dice {resa}%)')

# ===================================================================================================
print('\n=== 2. Qualita\' del tiro, cinismo e palle inattive (medie delle ultime 30, contro la partita) ===')
def xgot_card(g, l): v = numeri(g['W'].get('l-xgot-' + l, '')); return v if len(v) >= 2 and 'xG/Tiro' not in g['W'].get('l-xgot-' + l, '') else None
R = lati(lambda g, l: (xgot_card(g, l)[0], det(g, l, 'npxg')) if xgot_card(g, l) and det(g, l, 'npxg') is not None else None)
cont('NPxG medio (30 partite)', col(R, 1), col(R, 2), col(R, 0).astype(str) if False else np.array([r[0] for r in R]))
R = lati(lambda g, l: (xgot_card(g, l)[1], det(g, l, 'xgot')) if xgot_card(g, l) and det(g, l, 'xgot') is not None else None)
cont('xGOT medio', col(R, 1), col(R, 2), np.array([r[0] for r in R]))
R = lati(lambda g, l: (xgot_card(g, l)[1] - xgot_card(g, l)[0], det(g, l, 'xgot') - det(g, l, 'npxg'))
         if xgot_card(g, l) and det(g, l, 'xgot') is not None and det(g, l, 'npxg') is not None else None)
cont('xGOT meno NPxG (il «cecchino»)', col(R, 1), col(R, 2), np.array([r[0] for r in R]))
def set_real(g, l):
    sp, x = det(g, l, 'xg_sp'), det(g, l, 'npxg')
    return 100 * sp / x if sp is not None and x and x > 0.05 else None
R = lati(lambda g, l: (n0(g['W'].get('l-set-' + l)), set_real(g, l)) if n0(g['W'].get('l-set-' + l)) is not None and set_real(g, l) is not None else None)
cont('quota dei pericoli da palla inattiva', col(R, 1), col(R, 2), np.array([r[0] for r in R]), '%')
def bc_card(g, l): v = numeri(g['W'].get('l-bc-' + l, '')); return v if len(v) >= 2 else None
R = lati(lambda g, l: (bc_card(g, l)[0], det(g, l, 'bc')) if bc_card(g, l) and det(g, l, 'bc') is not None else None)
cont('Big Chances create', col(R, 1), col(R, 2), np.array([r[0] for r in R]))
R = lati(lambda g, l: (bc_card(g, l)[1], det(g, l, 'bcm')) if bc_card(g, l) and det(g, l, 'bcm') is not None else None)
cont('Big Chances sprecate', col(R, 1), col(R, 2), np.array([r[0] for r in R]))
for nome, fc, fr in (('NPxG', lambda g, l: (xgot_card(g, l) or [None])[0], lambda g, l: det(g, l, 'npxg')),
                     ('xGOT', lambda g, l: (xgot_card(g, l) or [None, None])[1], lambda g, l: det(g, l, 'xgot')),
                     ('Big Chances', lambda g, l: (bc_card(g, l) or [None])[0], lambda g, l: det(g, l, 'bc'))):
    R2 = [(g['lega'], fc(g, 'h') - fc(g, 'a'), fr(g, 'h') - fr(g, 'a')) for g in GIRI
          if None not in (fc(g, 'h'), fc(g, 'a'), fr(g, 'h'), fr(g, 'a'))]
    cont(f'{nome}, casa meno trasferta', col(R2, 1), col(R2, 2), np.array([r[0] for r in R2]))
print('  le frasi della card (quando segnalano una squadra, nella partita succede?):')
def frase(nome, righe):
    if not righe: return print(f'   {nome}: mai')
    ok = np.array(righe, float); print(f'   {nome}: {len(ok)} partite, la squadra segnalata davanti nella partita il {100*ok.mean():.1f}% (±{200*math.sqrt(ok.mean()*(1-ok.mean())/len(ok)):.1f})')
cec, spr, pin = [], [], []
for g in GIRI:
    a, b = xgot_card(g, 'h'), xgot_card(g, 'a')
    if a and b and abs((a[1] - a[0]) - (b[1] - b[0])) > 0.15 and a[1] > 0 and b[1] > 0:
        rh = [det(g, 'h', 'xgot'), det(g, 'h', 'npxg')]; ra = [det(g, 'a', 'xgot'), det(g, 'a', 'npxg')]
        if None not in rh + ra and (rh[0] - rh[1]) != (ra[0] - ra[1]):
            cec.append(((a[1] - a[0]) > (b[1] - b[0])) == ((rh[0] - rh[1]) > (ra[0] - ra[1])))
    a, b = bc_card(g, 'h'), bc_card(g, 'a')
    if a and b and (a[1] > 1.2 or b[1] > 1.2) and a[1] != b[1]:
        x, y = det(g, 'h', 'bcm'), det(g, 'a', 'bcm')
        if x is not None and y is not None and x != y: spr.append((a[1] > b[1]) == (x > y))
    a, b = n0(g['W'].get('l-set-h')), n0(g['W'].get('l-set-a'))
    if a is not None and b is not None and a != b:
        x, y = set_real(g, 'h'), set_real(g, 'a')
        if x is not None and y is not None and x != y: pin.append((a > b) == (x > y))
frase('«Cecchini» (chi tira meglio di quanto crea)', cec); frase('«Spreco» (chi butta piu\' Big Chances)', spr); frase('«Palle inattive» (chi ne dipende di piu\')', pin)

# ===================================================================================================
print('\n=== 3. Non possesso e gegenpressing ===')
def reale_len(g, l):
    x, d = det(g, l, 'avg_x'), det(g, l, 'avg_def_x'); return x - d if x and d else None
def reale_choke(g, l):
    c, r = det(g, l, 'cp_regains'), det(g, l, 'rec_time'); return c * 1.5 / r if c is not None and r else None
for idp, nome, fr in (('np-defx-', 'altezza difensiva (m)', lambda g, l: det(g, l, 'avg_def_x')), ('np-len-', 'lunghezza della squadra (m)', reale_len),
                      ('np-cp-', 'recuperi entro 5" dalla perdita', lambda g, l: det(g, l, 'cp_regains')), ('np-choke-', 'Choke Index', reale_choke)):
    R = lati(lambda g, l: (n0(g['W'].get(idp + l)), fr(g, l)) if n0(g['W'].get(idp + l)) is not None and fr(g, l) is not None else None)
    cont(nome, col(R, 1), col(R, 2), np.array([r[0] for r in R]))
    R2 = [(g['lega'], n0(g['W'].get(idp + 'h')) - n0(g['W'].get(idp + 'a')), fr(g, 'h') - fr(g, 'a')) for g in GIRI
          if n0(g['W'].get(idp + 'h')) is not None and n0(g['W'].get(idp + 'a')) is not None and fr(g, 'h') is not None and fr(g, 'a') is not None]
    cont('   ... casa meno trasferta', col(R2, 1), col(R2, 2), np.array([r[0] for r in R2]))
comp, riag = [], []
for g in GIRI:
    a, b = n0(g['W'].get('np-len-h')), n0(g['W'].get('np-len-a'))
    if a and b and abs(a - b) >= 4:
        x, y = reale_len(g, 'h'), reale_len(g, 'a')
        if x and y and x != y: comp.append((a < b) == (x < y))
    a, b = n0(g['W'].get('np-choke-h')), n0(g['W'].get('np-choke-a'))
    if a and b and abs(a - b) >= 0.3:
        x, y = reale_choke(g, 'h'), reale_choke(g, 'a')
        if x is not None and y is not None and x != y: riag.append((a > b) == (x > y))
frase('«Compattezza» (scarto di 4m o piu\': la piu\' corta resta piu\' corta)', comp); frase('«Riaggressione» (scarto di 0.3 o piu\')', riag)

# ===================================================================================================
print('\n=== 4. Funnel offensivo ===')
def reale_pen(g, l):
    f, t = det(g, l, 'f3_entries'), det(g, l, 'tch_box'); return 100 * t / f if f and t is not None else None
for idp, nome, fr in (('tr-x-', 'baricentro (m)', lambda g, l: det(g, l, 'avg_x')), ('tr-f3-', 'ingressi nell\'ultimo terzo', lambda g, l: det(g, l, 'f3_entries')),
                      ('tr-box-', 'tocchi in area', lambda g, l: det(g, l, 'tch_box')), ('tr-pen-', 'penetrazione (tocchi in area / ingressi)', reale_pen)):
    R = lati(lambda g, l: (n0(g['W'].get(idp + l)), fr(g, l)) if n0(g['W'].get(idp + l)) is not None and fr(g, l) is not None else None)
    cont(nome, col(R, 1), col(R, 2), np.array([r[0] for r in R]))
    R2 = [(g['lega'], n0(g['W'].get(idp + 'h')) - n0(g['W'].get(idp + 'a')), fr(g, 'h') - fr(g, 'a')) for g in GIRI
          if n0(g['W'].get(idp + 'h')) is not None and n0(g['W'].get(idp + 'a')) is not None and fr(g, 'h') is not None and fr(g, 'a') is not None]
    cont('   ... casa meno trasferta', col(R2, 1), col(R2, 2), np.array([r[0] for r in R2]))
st = collections.defaultdict(list)
for g in GIRI:
    x, y = det(g, 'h', 'avg_x'), det(g, 'a', 'avg_x')
    if x and y: st[g['W'].get('tr-style', '?')].append((x, y))
for k, v in sorted(st.items(), key=lambda kv: -len(kv[1])):
    v = np.array(v); print(f'   stile «{k}»: {len(v)} partite, baricentro reale casa {v[:,0].mean():.1f}m, trasferta {v[:,1].mean():.1f}m')

# ===================================================================================================
print('\n=== 5. Punti attesi dagli xG ===')
PTS = lambda gf, ga: 3 if gf > ga else (1 if gf == ga else 0)
def punti(g, l): return PTS(g['gh'], g['ga']) if l == 'h' else PTS(g['ga'], g['gh'])
def ep_master(g, l):
    p = [pc(g['W'].get(f'mdl-ens-{s}')) for s in ('1', 'x', '2')]
    if None in p: return None
    return 3 * p[0] + p[1] if l == 'h' else 3 * p[2] + p[1]
for idp, nome in (('pyt-act-', 'punti a partita, veri (30 partite)'), ('pyt-exp-', 'punti a partita attesi dagli xG')):
    R = lati(lambda g, l: (n0(g['W'].get(idp + l)), punti(g, l)) if n0(g['W'].get(idp + l)) is not None else None)
    cont(nome, col(R, 1), col(R, 2), np.array([r[0] for r in R]))
R = lati(lambda g, l: (ep_master(g, l), punti(g, l)) if ep_master(g, l) is not None else None)
cont('(riferimento: punti attesi dal verdetto 1X2)', col(R, 1), col(R, 2), np.array([r[0] for r in R]))
lab = collections.defaultdict(list)
for g in GIRI:
    for l in ('h', 'a'):
        t = g['W'].get('pyt-diag-' + l, ''); e = ep_master(g, l)
        if e is None or not t or t.startswith('Dati'): continue
        k = re.sub(r'^[^A-Za-z]+', '', t.split(' (')[0]); lab[k].append(punti(g, l) - e)
print('  il giudizio della card, contro i punti veri meno quelli attesi dal verdetto 1X2:')
for k, v in sorted(lab.items(), key=lambda kv: -len(kv[1])):
    v = np.array(v); print(f'   «{k}»: {len(v)} squadre, punti veri meno attesi {v.mean():+.3f} (±{2*v.std()/math.sqrt(len(v)):.3f})')
print('  i marcatori (il primo dei tre segna nella partita?):')
seg, att, n_ = [], [], 0
for g in GIRI:
    for l in ('h', 'a'):
        t = testo(g['W'].get('ts-' + l, '')); m = re.match(r'\s*(.+?) \((\d+) gol\)', t); d = D(g, l)
        if not m or not d: continue
        nome, k = m.group(1).strip(), int(m.group(2)); nn = n0(g['W'].get('pyt-diag-' + l, '').split(' su ')[-1]) or 30
        seg.append(nome in (d.get('scorers') or [])); att.append(1 - math.exp(-k / nn))
seg, att = np.array(seg, float), np.array(att)
if len(seg): print(f'   {len(seg)} squadre: il capocannoniere delle ultime 30 segna nel {100*seg.mean():.1f}% delle partite, '
                   f'contro il {100*att.mean():.1f}% che danno i suoi gol a partita (Poisson)')

# ===================================================================================================
print('\n=== 6. Progressione storica (le medie brevi contro la partita) ===')
PROG = [('Conduzioni prog.', 'prog_carries'), ('Cambi di gioco', 'switches'), ('Contrasti', 'tackles'), ('Conduzioni in area', 'carries_box'),
        ('Ingressi ultimo terzo', 'f3_entries'), ('Duelli aerei', 'aerials')]
FIN = ['ultime 3', 'ultime 5', 'ultime 10', 'ultime 15', 'tutte']
for i, (lab_, k) in enumerate(PROG):
    rr = {f: [] for f in FIN}
    for g in GIRI:
        for l in ('h', 'a'):
            c = celle(g['W'].get('table-prog-' + l, ''))
            if len(c) <= i + 1: continue
            v = c[i + 1][1:6]; y = det(g, l, k)
            if y is None: continue
            for f, x in zip(FIN, v):
                try: rr[f].append((g['lega'], float(x), y))
                except ValueError: pass
    print(f'  {lab_}:')
    for f in FIN: cont(f, col(rr[f], 1), col(rr[f], 2), np.array([r[0] for r in rr[f]]))

# ===================================================================================================
print('\n=== 7. Quando segnano (i gol della partita, per fascia di 15 minuti) ===')
BK = ['1-15', '16-30', '31-45', '46-60', '61-75', '76-90+']
def fascia(m): return 0 if m <= 15 else 1 if m <= 30 else 2 if m <= 45 else 3 if m <= 60 else 4 if m <= 75 else 5
lsq, lle, lun, ngol = [], [], [], 0
gl = collections.defaultdict(lambda: np.zeros(6))
for g in GIRI:
    for l in ('h', 'a'):
        d = D(g, l)
        if d:
            for m in d.get('goal_timings_scored') or []: gl[g['lega']][fascia(m)] += 1
for g in GIRI:
    c = celle(g['W'].get('timing-body', ''))
    if len(c) < 6: continue
    T = np.array([[float(x) for x in r[1:5]] for r in c[:6]])  # casa fatti, casa subiti, trasf fatti, trasf subiti
    for l, prof in (('h', T[:, 0] + T[:, 3]), ('a', T[:, 2] + T[:, 1])):
        d = D(g, l)
        if not d: continue
        q = (prof + 1) / (prof + 1).sum(); ql = gl[g['lega']] / gl[g['lega']].sum()
        for m in d.get('goal_timings_scored') or []:
            b = fascia(m); lsq.append(math.log(q[b])); lle.append(math.log(ql[b])); lun.append(math.log(1 / 6)); ngol += 1
if ngol:
    d1, d2 = np.array(lsq) - np.array(lle), np.array(lsq) - np.array(lun)
    print(f'   {ngol} gol: la fascia del gol con i minuti delle due squadre (chi segna e chi subisce) contro quella della lega '
          f'{1000*d1.mean():+.1f}‰ (z {_z(d1):+.1f}), contro una fascia uguale per tutte {1000*d2.mean():+.1f}‰ (z {_z(d2):+.1f})')
    tl = sum(gl.values()); print('   quota dei gol per fascia nel campione: ' + ' · '.join(f'{b} {100*x/tl.sum():.1f}%' for b, x in zip(BK, tl)))

# ===================================================================================================
print('\n=== 8. Primo gol ===')
y30, yht = [], []
for g in GIRI:
    if not (D(g, 'h') and D(g, 'a')): y30.append(np.nan); yht.append(np.nan); continue
    mm = (D(g, 'h').get('goal_timings_scored') or []) + (D(g, 'a').get('goal_timings_scored') or [])
    if len(mm) != g['gh'] + g['ga']: y30.append(np.nan); yht.append(np.nan); continue
    y30.append(float(any(m <= 30 for m in mm))); yht.append(float(any(m <= 45 for m in mm)))
for idp, nome, y in (('surv-30', 'gol prima del 30\'', y30), ('surv-45', 'Over 0.5 nel primo tempo', yht)):
    p = [vnan(pc(g['W'].get(idp))) for g in GIRI]; bin_(nome, p, y, LG); fasce(nome, p, y, [0, .4, .5, .6, .7, .8, .9, 1.01])

# ===================================================================================================
print('\n=== 9. Risultati esatti, handicap e multigol ===')
pe, ye, cov, cpr = [], [], [], []
for g in GIRI:
    h = g['W'].get('exact-scores', '')
    sc = re.findall(r'(\d+) - (\d+)</div><div[^>]*>([\d.]+)%', h)
    if not sc: continue
    s = 0
    for a, b, p in sc: pe.append(float(p) / 100); ye.append(float(int(a) == g['gh'] and int(b) == g['ga'])); s += float(p) / 100
    cov.append(any(int(a) == g['gh'] and int(b) == g['ga'] for a, b, _ in sc)); cpr.append(s)
pe, ye = np.array(pe), np.array(ye)
print(f'   i sei risultati mostrati: insieme danno il {100*np.mean(cpr):.1f}%, esce uno di loro il {100*np.mean(cov):.1f}% delle partite ({len(cov)})')
for i in range(6):
    sel = slice(i, None, 6); print(f'      il {i+1}° risultato: previsto {100*pe[sel].mean():.1f}%, esce il {100*ye[sel].mean():.1f}%')
print('  handicap asiatico (la casa copre; sulle linee intere si conta il rimborso a parte):')
AH = collections.defaultdict(list)
for g in GIRI:
    d = g['gh'] - g['ga']
    for r in celle(g['W'].get('table-ah', ''))[1:]:
        if len(r) < 4: continue
        L = float(r[0].replace('+', '')); p1 = pc(r[1]); pr = pc(r[2]) if r[2] not in ('-', '') else 0.0
        x = d + L
        win = 1.0 if x > 0.25 else (0.5 if abs(x - 0.25) < 1e-9 else 0.0)
        if abs(L * 4 % 2 - 1) < 1e-9:  # linee a quarti: vince intero, mezzo, perde
            win = 1.0 if x > 0.25 else (0.5 if x == 0.25 else 0.0)
            push = 0.0
        else:
            push = 1.0 if x == 0 else 0.0
            win = 1.0 if x > 0 else 0.0
        AH[L].append((g['lega'], p1, win, pr, push))
for L in sorted(AH):
    v = AH[L]; p = col(v, 1); y = col(v, 2)
    lab_ = f'AH {L:+.2f}'.rstrip('0').rstrip('.') + ' casa copre'
    if abs(L * 4 % 2 - 1) < 1e-9: print(f'   {lab_:44s} {len(p):5d}  previsto {100*p.mean():5.1f}  reale {100*y.mean():5.1f} (linea a quarti: copertura attesa, mezzo punto se finisce a meta\')')
    else:
        bin_(lab_, p, y, np.array([r[0] for r in v]))
        if L == int(L): print(f'      rimborso: previsto {100*col(v,3).mean():.1f}%, reale {100*col(v,4).mean():.1f}%')
for idm, nome, gv in (('mg-tot', 'multigol totali', TOT), ('mg-h', 'multigol casa', GH), ('mg-a', 'multigol trasferta', GA)):
    MG = collections.defaultdict(list)
    for g, n in zip(GIRI, gv):
        for a, b, p in re.findall(r'>(\d+)-(\d+) Gol</span><span[^>]*>([\d.]+)%', g['W'].get(idm, '')):
            MG[(int(a), int(b))].append((g['lega'], float(p) / 100, float(int(a) <= n <= int(b))))
    for (a, b), v in sorted(MG.items()): bin_(f'{nome} {a}-{b}', col(v, 1), col(v, 2), np.array([r[0] for r in v]))

# ===================================================================================================
print('\n=== 10. Corner, tiri e cartellini ===')
def tot(g, k):
    a, b = det(g, 'h', k), det(g, 'a', k); return a + b if a is not None and b is not None else None
for idp, nome, k in (('cor-tot', 'corner totali', 'cor'), ('sot-tot', 'tiri in porta totali', 'sot'), ('fls-tot', 'falli totali', 'fouls'), ('yel-tot', 'gialli totali', 'yel')):
    for amb in ('over', 'role'):
        R = [(g['lega'], n0(g['W'].get(f'{idp}-{amb}')), tot(g, k)) for g in GIRI if n0(g['W'].get(f'{idp}-{amb}')) is not None and tot(g, k) is not None]
        cont(f'{nome} ({"generale" if amb == "over" else "ruolo"})', col(R, 1), col(R, 2), np.array([r[0] for r in R]))
for amb in ('over', 'role'):
    p = [vnan(pc(g['W'].get(f'red-tot-{amb}'))) for g in GIRI]
    y = [float(tot(g, 'red_cards') > 0) if tot(g, 'red_cards') is not None else np.nan for g in GIRI]
    bin_(f'almeno un rosso ({"generale" if amb == "over" else "ruolo"})', p, y, LG)
ML = collections.defaultdict(list)
for g in GIRI:
    merc = None
    for r in celle(g['W'].get('mkt-lines', ''))[1:]:
        if len(r) == 5: merc = r[0]; r = r[2:]
        elif len(r) != 3: continue
        k = {'Corner': 'cor', 'Tiri in porta': 'sot', 'Gialli': 'yel'}.get(merc)
        if not k or tot(g, k) is None: continue
        L = float(r[0]); ML[(merc, L)].append((g['lega'], pc(r[1]), float(tot(g, k) > L)))
for (m, L), v in sorted(ML.items()): bin_(f'{m} Over {L}', col(v, 1), col(v, 2), np.array([r[0] for r in v]))

# ===================================================================================================
print('\n=== 11. Z-score ed efficienza ===')
for amb, nome in (('ov', 'generale'), ('ro', 'ruolo')):
    R = lati(lambda g, l: (n0(g['W'].get(f'z-xg-{l}-{amb}')), det(g, l, 'npxg')) if n0(g['W'].get(f'z-xg-{l}-{amb}')) is not None and det(g, l, 'npxg') is not None else None)
    cont(f'z-score {nome} contro l\'NPxG della partita', col(R, 1), col(R, 2), np.array([r[0] for r in R]), livello=False)
    R = lati(lambda g, l: (n0(g['W'].get(f'z-xg-{l}-{amb}')), float(g['gh'] if l == 'h' else g['ga'])) if n0(g['W'].get(f'z-xg-{l}-{amb}')) is not None else None)
    cont(f'z-score {nome} contro i gol della partita', col(R, 1), col(R, 2), np.array([r[0] for r in R]), livello=False)
    bd = collections.defaultdict(list)
    for g in GIRI:
        for l in ('h', 'a'):
            b = g['W'].get(f'z-b-{l}-{amb}'); x = det(g, l, 'npxg')
            if b and x is not None: bd[b].append((x, g['gh'] if l == 'h' else g['ga']))
    print(f'   etichette ({nome}): ' + ' · '.join(f'«{k}» {len(v)}: NPxG {np.mean([a for a,_ in v]):.2f}, gol {np.mean([b for _,b in v]):.2f}' for k, v in sorted(bd.items())))
for s_, amb in (('o', 'generale'), ('r', 'ruolo')):
    for k, kk, nome in (('gf', None, 'gol fatti'), ('xg', 'xg', 'xG'), ('ef', None, 'efficienza (gol / xG)')):
        def reale(g, l):
            if k == 'gf': return float(g['gh'] if l == 'h' else g['ga'])
            if k == 'xg': return det(g, l, 'xg')
            x = det(g, l, 'xg'); return (g['gh'] if l == 'h' else g['ga']) - x if x is not None else None
        R = lati(lambda g, l: (n0(g['W'].get(f'e-{k}-{l}{s_}')), reale(g, l)) if n0(g['W'].get(f'e-{k}-{l}{s_}')) is not None and reale(g, l) is not None else None)
        cont(f'{nome} ({amb})' + (' contro gol meno xG' if k == 'ef' else ''), col(R, 1), col(R, 2), np.array([r[0] for r in R]), livello=(k != 'ef'))

# ===================================================================================================
print('\n=== 12. Partite simili (KNN) e moduli ===')
for s_, amb in (('o', 'generale'), ('r', 'ruolo')):
    R = []
    for g in GIRI:
        for l in ('h', 'a'):
            c = celle('<tr>' + g['W'].get(f'row-form-{l}{s_}', '') + '</tr>')
            if c and len(c[0]) >= 6 and c[0][5] not in ('N/D', ''):
                R.append((g['lega'], float(c[0][5]), punti(g, l), float(c[0][4])))
    cont(f'punti a partita contro il modulo avversario ({amb})', col(R, 1), col(R, 2), np.array([r[0] for r in R]))
    if R: print(f'      partite col modulo avversario in media {col(R, 3).mean():.1f}; con almeno 5: '
                f'{(col(R, 3) >= 5).sum()} squadre')
mod = collections.Counter()
for g in GIRI:
    for l, s_ in (('h', 'ho'), ('a', 'ao')):
        c = celle('<tr>' + g['W'].get(f'row-form-{s_}', '') + '</tr>'); d = D(g, l); o = D(g, 'a' if l == 'h' else 'h')
        if not c or len(c[0]) < 3 or not d: continue
        mio = c[0][1].split(' ')[0]; avv = c[0][2]
        if mio not in ('N/D', ''): mod['mio'] += 1; mod['mio_ok'] += (d.get('modulo') or '').split(' ')[0] == mio
        if avv not in ('N/D', '') and o: mod['avv'] += 1; mod['avv_ok'] += (o.get('modulo') or '').split(' ')[0] == avv
if mod['mio']: print(f'   il modulo mostrato (il piu\' usato) e\' quello della partita nel {100*mod["mio_ok"]/mod["mio"]:.1f}% dei casi ({mod["mio"]}); '
                     f'quello dell\'avversario nel {100*mod["avv_ok"]/max(1, mod["avv"]):.1f}%')
R = lati(lambda g, l: (n0(g['W'].get('knn-res-' + l)), punti(g, l)) if n0(g['W'].get('knn-res-' + l)) is not None else None)
cont('punti a partita nelle partite simili (KNN)', col(R, 1), col(R, 2), np.array([r[0] for r in R]))

# ===================================================================================================
print('\n=== 13. Catena di Markov (lo scarto finale) ===')
DIFF = GH - GA; CL = np.select([DIFF >= 2, DIFF == 1, DIFF == 0, DIFF == -1], [0, 1, 2, 3], 4)
for amb, nome in (('ov', 'generale'), ('ro', 'ruolo')):
    P = np.array([[pc(g['W'].get(f'mk-{c}-{amb}')) if pc(g['W'].get(f'mk-{c}-{amb}')) is not None else np.nan for c in ('h2', 'h1', 'x', 'a1', 'a2')] for g in GIRI])
    multi(f'Markov {nome}, cinque esiti', P, CL, LG)
    for i, c in enumerate(('casa di 2+', 'casa di 1', 'pareggio', 'trasferta di 1', 'trasferta di 2+')):
        bin_(f'   {c}', P[:, i], (CL == i).astype(float), LG)

# ===================================================================================================
print('\n=== 14. Elo e trend ===')
de = np.array([(vnan(n0(g['W'].get('elo-h-ov')))) - (vnan(n0(g['W'].get('elo-a-ov')))) for g in GIRI])
k = (ESITO != 1) & ~np.isnan(de)
print(f'   differenza Elo (casa meno trasferta), sulle {k.sum()} partite senza pari: AUC della vittoria casa {auc_lega(de[k], (ESITO[k]==0).astype(float), LG[k]):.3f}')
k12 = ESITO != 1
for kk, nome in (('lgElo', 'l\'Elo da solo'), ('lgModel', 'il modello da solo')):
    lg_ = np.array([g['csv'].get(kk) if g['csv'].get(kk) is not None else np.nan for g in GIRI])
    bin_(f'1 contro 2 secondo {nome} (riquadro «Come entra»)', 1 / (1 + np.exp(-lg_[k12])), (ESITO[k12] == 0).astype(float), LG[k12])
tr = np.array([(vnan(n0(g['W'].get('elo-h-tr')))) - (vnan(n0(g['W'].get('elo-a-tr')))) for g in GIRI])
res = np.array([punti(g, 'h') - (vnan(ep_master(g, 'h'))) for g in GIRI])
cont('trend, casa meno trasferta, contro punti casa meno attesi', tr, res, LG, livello=False)
R = lati(lambda g, l: (n0(g['W'].get(f'elo-{l}-tr')), punti(g, l) - ep_master(g, l)) if n0(g['W'].get(f'elo-{l}-tr')) is not None and ep_master(g, l) is not None else None)
cont('trend di una squadra contro i suoi punti meno attesi', col(R, 1), col(R, 2), np.array([r[0] for r in R]), livello=False)
