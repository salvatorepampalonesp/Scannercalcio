# La card «Primo gol» dello Scanner contro il reale (AGENTS.md, La card del primo gol). Solo misura.
#
#   python3 strumenti/primo-gol.py --scarica batch48 batch4 batch/2627   scarica i gol delle partite (una chiamata per partita)
#   python3 strumenti/primo-gol.py batch48 batch4 batch/2627             la misura (l'esplorazione)
#   python3 strumenti/primo-gol.py --scarica <cartelle del test>         e poi senza --scarica: il test della regola
#   ... --partita m_4bVd52                                               i due numeri di una partita, da confrontare con lo Scanner
#
# La card dice due numeri: il gol prima del 30' e l'Over 0.5 del primo tempo. Lo Scanner li fa cosi':
# P = 1 - exp(-lambda * quota), con lambda la somma dei lambda di ruolo (col livello dei gol del b63) e quota
# la parte dei gol che cade nei primi 30 o 45 minuti, contata sui minuti dei gol delle ultime 30 partite di
# lega delle due squadre (fatti e subiti, 500 giorni, sei fasce da 15'; sotto i 31 gol la quota e' uniforme).
# Qui si rifa' uguale dall'archivio in fondo al CSV e dai gol di /matches/{id}/events, e si confronta col
# minuto vero del primo gol. Partite bersaglio: quelle dei CSV dal --dal (di default il 2025/26 e dopo).
# I gol si tengono in batch/eventi/ (fuori da git): una partita giocata non cambia.
import os, sys, json, glob, math, ssl, time, datetime as dt, collections, urllib.request, urllib.error, importlib.util, io, contextlib
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from sklearn.metrics import roc_auc_score
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
s = importlib.util.spec_from_file_location('qb', 'strumenti/quote-bookmaker.py'); qb = importlib.util.module_from_spec(s); s.loader.exec_module(qb)

PITCH = 'https://pitchapi-proxy.salvatorepampalone-sp.workers.dev'
CART = 'batch/eventi'
RIGA_F = "Ambito: livello dei gol (fattore gia' nei lambda di ruolo)"
GOALS_LEVEL, LIMITE, FINESTRA = 1.051, 30, 500
QUOTA_FISSA = (0.268, 0.446)  # la quota media dei gol nei primi 30 e 45 minuti sull'esplorazione: il candidato della regola
# senza una stagione alle spalle: fuori da ogni misura (AGENTS.md, Le leghe mai viste)
ESCLUSI = {'Backtest_V97_GRE_Super_League_1_2025-2026.csv', 'Backtest_V97_KSA_Saudi_Pro_League_2023-2024.csv'}
a = sys.argv[1:]
SCARICA = '--scarica' in a
DAL = a[a.index('--dal') + 1] if '--dal' in a else '2025-07-01'
PARTITA = a[a.index('--partita') + 1] if '--partita' in a else None
cartelle = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--dal', '--partita'))]

def archivio(f):
    out = {}
    for r in io.open(f, encoding='utf-8-sig'):
        if r.startswith('ARCHIVIO #'):
            c = r.rstrip('\n').split(';')
            out[c[1]] = dict(id=c[1], st=c[2], ora=c[3], giorno=c[3][:10], stato=c[4], h=c[5], a=c[7],
                             gh=int(c[9]) if c[9] else None, ga=int(c[10]) if c[10] else None)
    return out

def ha_fattore(f):
    return any(r.startswith(RIGA_F) for r in io.open(f, encoding='utf-8-sig'))

def leggi(cartelle):
    F = [f for d in cartelle for f in sorted(glob.glob(os.path.join(d, '*.csv'))) if os.path.basename(f) not in ESCLUSI]
    T, A = {}, {}
    for f in F:
        ar = archivio(f); lega = os.path.basename(f)[len('Backtest_V97_'):].rsplit('_', 1)[0]
        A.setdefault(lega, {}).update(ar)
        fatt = 1.0 if ha_fattore(f) else GOALS_LEVEL
        with contextlib.redirect_stdout(io.StringIO()): M = qb.leggi_csv(f)
        for m in M:
            if m['data'] >= DAL and m['id'] in ar and None not in m['lam']:
                T[m['id']] = dict(m, lega=lega, lt=sum(m['lam']) * fatt, ora=ar[m['id']]['ora'], hid=ar[m['id']]['h'], aid=ar[m['id']]['a'])
    return T, A

def scarica(ids):
    os.makedirs(CART, exist_ok=True)
    ctx = ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt') if os.path.exists('/root/.ccr/ca-bundle.crt') else None
    chiave = os.environ.get('PITCHAPI_KEY')
    def uno(mid):
        f = os.path.join(CART, mid + '.json')
        if os.path.exists(f): return 'gia'
        h = {'User-Agent': 'Mozilla/5.0'}
        if chiave: h['X-API-KEY'] = chiave
        for prova in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request(f'{PITCH}/matches/{mid}/events', headers=h), context=ctx, timeout=30) as r:
                    d = json.load(r).get('data') or {}
                evs = d.get('events') if isinstance(d, dict) else d
                gol = [dict(m=e.get('minute'), add=e.get('minute_added'), per=e.get('period'), t=e.get('team_id'), og=bool(e.get('is_own_goal')))
                       for e in (evs or []) if str(e.get('event_type', '')).lower() == 'goal']
                json.dump(dict(ok=evs is not None, gol=gol), open(f, 'w')); return 'ok'
            except urllib.error.HTTPError as e:
                if e.code == 404: json.dump(dict(ok=False, gol=[]), open(f, 'w')); return '404'
                time.sleep(2 ** prova)
            except Exception:
                time.sleep(2 ** prova)
        return 'fallita'
    conto = collections.Counter()
    with ThreadPoolExecutor(8) as ex:
        for i, r in enumerate(ex.map(uno, ids)):
            conto[r] += 1
            if (i + 1) % 500 == 0: print(f'  {i + 1}/{len(ids)}', dict(conto), flush=True)
    print('scaricate:', dict(conto))

_G = {}
def gol(mid):
    if mid not in _G:
        f = os.path.join(CART, mid + '.json')
        _G[mid] = json.load(open(f)) if os.path.exists(f) else None
    return _G[mid]

def esito(mid):
    g = gol(mid)
    if not g or not g['ok']: return None
    pt = [e for e in g['gol'] if e['per'] == 'FirstHalf']
    return int(any(e['m'] is not None and e['m'] <= 30 for e in pt)), int(bool(pt))

def fascia(mi): return min(5, max(0, (mi - 1) // 15)) if mi is not None else None

def main():
    T, A = leggi(cartelle)
    print(f'partite bersaglio dal {DAL}: {len(T)} in {len(set(t["lega"] for t in T.values()))} leghe')
    # la storia: tutte le partite di lega concluse nei 500 giorni prima della prima partita bersaglio di ogni lega
    serve = set()
    for lega, ar in A.items():
        tl = [t for t in T.values() if t['lega'] == lega]
        if not tl: continue
        da = (dt.date.fromisoformat(min(t['data'] for t in tl)) - dt.timedelta(days=FINESTRA + 1)).isoformat()
        serve |= {m['id'] for m in ar.values() if m['stato'] == 'finished' and m['giorno'] >= da}
    serve |= set(T)
    manca = sorted(m for m in serve if not os.path.exists(os.path.join(CART, m + '.json')))
    print(f'partite che servono: {len(serve)}, da scaricare {len(manca)}')
    if SCARICA: scarica(manca); return
    if manca: print('mancano dei gol: prima --scarica (niente misura su dati a meta\')'); sys.exit(1)
    R = []; scartate = collections.Counter()
    for lega, ar in A.items():
        fin = sorted((m for m in ar.values() if m['stato'] == 'finished'), key=lambda m: m['ora'])
        tl = [t for t in T.values() if t['lega'] == lega]
        quote_lega = []
        for t in tl:
            g = gol(t['id'])
            if not g or not g['ok']: scartate['senza i gol della partita'] += 1; continue
            if len(g['gol']) != t['hg'] + t['ag']: scartate['gol degli eventi diversi dal punteggio'] += 1; continue
            giorno = t['data']; t0 = dt.datetime.fromisoformat(t['ora'].replace('Z', '+00:00')); lim = (t0 - dt.timedelta(days=FINESTRA)).isoformat()[:19]
            b = np.zeros(6)
            for sq in (t['hid'], t['aid']):
                storia = [m for m in fin if (m['h'] == sq or m['a'] == sq) and m['giorno'] < giorno and m['ora'][:19] > lim][-LIMITE:]
                for m in storia:
                    gg = gol(m['id'])
                    for e in (gg['gol'] if gg else []):
                        if e['m'] is not None: b[fascia(e['m'])] += 1
            sh = b / b.sum() if b.sum() > 30 else np.full(6, 1 / 6)
            if t['id'] == PARTITA:
                print(f"{t['H']} - {t['A']} del {giorno}: lambda {t['lt']:.4f}, gol nella storia {b.astype(int).tolist()}, "
                      f"gol prima del 30' {100*(1-math.exp(-t['lt']*sh[:2].sum())):.1f}%, Over 0.5 nel primo tempo {100*(1-math.exp(-t['lt']*sh[:3].sum())):.1f}%")
            # la quota della lega: i gol di tutte le partite di lega nei 365 giorni prima, stessa regola delle fasce
            lg = np.zeros(6); da = (t0 - dt.timedelta(days=365)).isoformat()[:19]
            for m in fin:
                if m['giorno'] < giorno and m['ora'][:19] > da:
                    gg = gol(m['id'])
                    for e in (gg['gol'] if gg else []):
                        if e['m'] is not None: lg[fascia(e['m'])] += 1
            shl = lg / lg.sum() if lg.sum() > 30 else np.full(6, 1 / 6)
            # la frequenza della lega: quante partite di lega nei 365 giorni prima hanno avuto il gol prima del 30' e nel primo tempo
            fr = [esito(m['id']) for m in fin if m['giorno'] < giorno and m['ora'][:19] > da]
            fr = [x for x in fr if x]
            f30 = np.mean([x[0] for x in fr]) if len(fr) >= 50 else None; fht = np.mean([x[1] for x in fr]) if len(fr) >= 50 else None
            pt = [e for e in g['gol'] if e['per'] == 'FirstHalf']
            y30 = int(any(e['m'] is not None and e['m'] <= 30 for e in pt)); yht = int(bool(pt))
            primo = min((e['m'] + (e['add'] or 0) / 100 for e in g['gol'] if e['m'] is not None), default=None)
            if f30 is None: scartate['meno di 50 partite di lega nei 365 giorni prima'] += 1; continue
            R.append(dict(lega=lega, lt=t['lt'], s30=sh[:2].sum(), sht=sh[:3].sum(), l30=shl[:2].sum(), lht=shl[:3].sum(), f30=f30, fht=fht,
                          y30=y30, yht=yht, ng=b.sum(), tot=t['hg'] + t['ag'], primo=primo))
    print('scartate:', dict(scartate) or 'nessuna')
    if not R: return
    lt = np.array([r['lt'] for r in R]); y30 = np.array([r['y30'] for r in R]); yht = np.array([r['yht'] for r in R])
    leghe = np.array([r['lega'] for r in R]); tot = np.array([r['tot'] for r in R])
    P = {k: 1 - np.exp(-lt * np.array([r[k] for r in R])) for k in ('s30', 'sht', 'l30', 'lht')}
    P['u30'] = 1 - np.exp(-lt * 2 / 6); P['uht'] = 1 - np.exp(-lt * 3 / 6)
    P['c30'] = 1 - np.exp(-lt * QUOTA_FISSA[0]); P['cht'] = 1 - np.exp(-lt * QUOTA_FISSA[1])
    ll = lambda p, y: -(y * np.log(np.clip(p, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-9, 1)))
    z = lambda d: d.mean() / d.std(ddof=1) * math.sqrt(len(d))
    print(f'\npartite misurate: {len(R)}; gol nella storia delle due squadre (mediana) {np.median([r["ng"] for r in R]):.0f}, '
          f'sotto i 31 (quota uniforme) {sum(r["ng"] <= 30 for r in R)}')
    for nome, k, kl, ku, y in (('gol prima del 30\'', 's30', 'l30', 'u30', y30), ('Over 0.5 nel primo tempo', 'sht', 'lht', 'uht', yht)):
        p = P[k]
        print(f'\n=== {nome} ===')
        print(f'  previsto {100*p.mean():.1f}%, reale {100*y.mean():.1f}%; quota del tempo usata in media {np.mean([r[k] for r in R]):.3f}, '
              f'della lega {np.mean([r[kl] for r in R]):.3f}')
        print(f'  Brier {((p-y)**2).mean():.4f} (una costante {((y.mean()-y)**2).mean():.4f})')
        for a_, b_ in [(0, .4), (.4, .5), (.5, .6), (.6, .7), (.7, .8), (.8, 1.01)]:
            kk = (p >= a_) & (p < b_)
            if kk.sum() >= 50: print(f'     {int(100*a_):2d}-{min(100, int(100*b_)):3d}%: {kk.sum():5d} partite, previsto {100*p[kk].mean():.1f}, esce {100*y[kk].mean():.1f} ±{200*math.sqrt(y[kk].mean()*(1-y[kk].mean())/kk.sum()):.1f}')
        au = [(roc_auc_score(y[leghe == l], p[leghe == l]), (leghe == l).sum()) for l in sorted(set(leghe)) if 0 < y[leghe == l].sum() < (leghe == l).sum()]
        print(f'  AUC dentro la lega (media pesata) {sum(x*n for x, n in au)/sum(n for _, n in au):.3f}, da {min(x for x, _ in au):.3f} a {max(x for x, _ in au):.3f}')
        P['f' + k[1:]] = np.array([r['f' + k[1:]] for r in R])
        for alt, nm in ((kl, 'la quota della lega (365 giorni prima)'), (ku, 'la quota uniforme (1/6 per fascia)'), ('c' + k[1:], f'una quota fissa per tutte le leghe ({QUOTA_FISSA})'), ('f' + k[1:], 'la frequenza della lega (365 giorni prima), uguale per tutte le partite')):
            d = ll(p, y) - ll(P[alt], y); per = [ (ll(p, y) - ll(P[alt], y))[leghe == l].mean() < 0 for l in sorted(set(leghe))]
            print(f'  la quota delle due squadre contro {nm}: {1000*d.mean():+.2f} per mille (z {z(d):+.2f}), meglio in {sum(per)} leghe su {len(per)}')
        # ricalibrata fuori lega: logit(P) = a + b*logit(previsione dello Scanner), stimata sulle altre leghe
        lo = lambda x: np.log(np.clip(x, 1e-6, 1 - 1e-6) / (1 - np.clip(x, 1e-6, 1 - 1e-6)))
        from sklearn.linear_model import LogisticRegression
        pr = np.zeros(len(y)); bb = []
        for l in sorted(set(leghe)):
            kk = leghe == l
            m_ = LogisticRegression(C=1e6).fit(lo(p[~kk])[:, None], y[~kk]); pr[kk] = m_.predict_proba(lo(p[kk])[:, None])[:, 1]; bb.append(m_.coef_[0][0])
        d = ll(pr, y) - ll(P['f' + k[1:]], y)
        print(f'  ricalibrata fuori lega (pendenza sul logit {min(bb):.2f}-{max(bb):.2f}) contro la frequenza della lega: {1000*d.mean():+.2f} per mille (z {z(d):+.2f})')
        print('  per lega (partite, previsto, reale):')
        for l in sorted(set(leghe), key=lambda l: -(leghe == l).sum()):
            kk = leghe == l
            print(f'     {l[:28]:28s} {kk.sum():5d}  {100*p[kk].mean():5.1f}  {100*y[kk].mean():5.1f}')
    # il motore conta i gol del primo tempo come Poisson del totale (assottigliamento): e' vero?
    q = np.mean([r['lht'] for r in R])
    print(f'\n=== la regola di Poisson: nessun gol nel primo tempo, dato il totale della partita (quota media del primo tempo {q:.3f}) ===')
    for k in range(1, 6):
        kk = tot == k
        if kk.sum(): print(f'   {k} gol: {kk.sum():5d} partite, nessuno nel primo tempo {100*(1-yht[kk].mean()):.1f}% (binomiale {100*(1-q)**k:.1f}%)')
    pr = np.array([r['primo'] for r in R if r['primo'] is not None])
    print(f'\nminuto del primo gol (reale): mediana {np.median(pr):.0f}, prima del 15\' {100*(pr <= 15).mean():.1f}%, '
          f'del 30\' {100*(pr <= 30).mean():.1f}%, nel primo tempo {100*(pr < 46).mean():.1f}%; senza gol {100*(tot == 0).mean():.1f}% delle partite')
    # la regola (AGENTS.md, La card del primo gol: la regola): la quota fissa contro quella delle due squadre, stesso lambda.
    # Per partita la somma delle due logloss (gol prima del 30' e Over 0.5 nel primo tempo), appaiata.
    d30 = ll(P['c30'], y30) - ll(P['s30'], y30); dht = ll(P['cht'], yht) - ll(P['sht'], yht); d = d30 + dht
    grandi = [l for l in sorted(set(leghe)) if (leghe == l).sum() >= 100]
    meglio = [l for l in grandi if d[leghe == l].mean() < 0]
    print(f'\n=== la regola: quota fissa {QUOTA_FISSA} meno quella delle due squadre, somma delle due logloss ===')
    print(f'   insieme {len(d)} partite: {1000*d.mean():+.2f} per mille (z {z(d):+.2f}); '
          f"gol prima del 30' {1000*d30.mean():+.2f} (z {z(d30):+.2f}), primo tempo {1000*dht.mean():+.2f} (z {z(dht):+.2f})")
    print(f'   meglio in {len(meglio)} leghe su {len(grandi)} con almeno 100 partite')
    for l in sorted(set(leghe), key=lambda l: -(leghe == l).sum()):
        kk = leghe == l
        print(f'     {l[:28]:28s} {kk.sum():5d}  {1000*d[kk].mean():+7.2f}  quota della lega nei primi 30 e 45 minuti {np.mean([r["l30"] for r, k in zip(R, kk) if k]):.3f} {np.mean([r["lht"] for r, k in zip(R, kk) if k]):.3f}')
    passa = z(d) <= -2 and len(meglio) > len(grandi) / 2 and d30.mean() <= 0 and dht.mean() <= 0
    print(f"   esito: {'PASSA' if passa else 'NON PASSA'} (z <= -2: {z(d) <= -2}; piu' di meta' delle leghe: {len(meglio) > len(grandi) / 2}; "
          f"nessuno dei due peggio: {d30.mean() <= 0 and dht.mean() <= 0})")

main()
