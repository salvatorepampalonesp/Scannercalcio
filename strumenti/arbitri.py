# Gli arbitri e i gialli (AGENTS.md, Da fare, Cartellini).
#
#   python3 strumenti/arbitri.py [--scarica] [--footiqo batch/footiqo] [batch48 batch/2627]
#
# --scarica prende da footiqo.com, parte gratuita, per i cinque campionati, due tabelle in piu' oltre alle
# quote di quote-goal.py: la panoramica (arbitro e punteggio di ogni partita, dal 2015/16) e corner e
# cartellini. Una pagina e quattro richieste per lega, con una pausa, come fa la pagina col menu «All».
# Condizioni d'uso: uso personale, niente ridistribuzione; i file restano in batch/footiqo/, fuori da git.
import os, sys, re, json, html, math, time, subprocess, collections, importlib.util, datetime as dt
import numpy as np
QUI = os.path.dirname(os.path.abspath(__file__))
_s = importlib.util.spec_from_file_location('quote_goal', os.path.join(QUI, 'quote-goal.py'))
qgo = importlib.util.module_from_spec(_s); _s.loader.exec_module(qgo)
qm, qg, LEGHE = qgo.qm, qgo.qg, qgo.LEGHE
SEZIONI = {'arbitri': 'referee', 'cartellini': 'HYCFT'}

def tabelle(s):
    # (id, colonne) di ogni tabella della pagina, nell'ordine: per ogni sezione prima la stagione in corso, poi le passate
    out = []
    for tid in dict.fromkeys(re.findall(r'data-wpdatatable_id="(\d+)"', s)):
        seg = s[s.find('data-wpdatatable_id="%s"' % tid):][:60000].split('</thead>')[0]
        out.append((tid, [html.unescape(re.sub(r'<[^>]+>', '', h)).strip() for h in re.findall(r'<th[^>]*>(.*?)</th>', seg, re.S)]))
    return out

def scarica(cartella, sezioni=SEZIONI):
    os.makedirs(cartella, exist_ok=True)
    for slug in LEGHE:
        s = qgo.curl(f'https://footiqo.com/database/leagues/{slug}/'); time.sleep(3)
        tab = tabelle(s)
        for nome, colonna in sezioni.items():
            scelte = [(tid, teste) for tid, teste in tab if colonna in teste][:2]
            assert len(scelte) == 2, (slug, nome, scelte)
            for (tid, teste), quando in zip(scelte, ('corrente', 'passate')):
                nonce = re.search(r'id="wdtNonceFrontendServerSide_%s" name="[^"]+" value="([^"]+)"' % tid, s).group(1)
                dati = ['draw=1', 'start=0', 'length=-1', 'search[value]=', 'search[regex]=false', 'order[0][column]=1', 'order[0][dir]=asc', 'wdtNonce=' + nonce]
                for k, h in enumerate(teste):
                    dati += [f'columns[{k}][data]={k}', f'columns[{k}][name]={h}', f'columns[{k}][searchable]=true', f'columns[{k}][orderable]=true',
                             f'columns[{k}][search][value]=', f'columns[{k}][search][regex]=false']
                r = json.loads(qgo.curl('-X', 'POST', '-H', 'X-Requested-With: XMLHttpRequest', '-H', 'Referer: https://footiqo.com/', '--data', '&'.join(dati),
                                        f'https://footiqo.com/wp-admin/admin-ajax.php?action=get_wdtable&table_id={tid}'))
                json.dump({'heads': teste, 'data': r['data']}, open(os.path.join(cartella, f'{slug}_{nome}_{quando}.json'), 'w'))
                print(f'  {slug} {nome} {quando} (tabella {tid}): {len(r["data"])} righe'); time.sleep(4)


def leggi_footiqo(cartella):
    # una riga per partita: data, squadre, arbitro, gialli e corner (le due tabelle hanno lo stesso id)
    out = {}
    for slug, lg in LEGHE.items():
        for quando in ('passate', 'corrente'):
            A = json.load(open(os.path.join(cartella, f'{slug}_arbitri_{quando}.json')))
            C = json.load(open(os.path.join(cartella, f'{slug}_cartellini_{quando}.json')))
            cart = {r[0]: dict(zip(C['heads'], r)) for r in C['data']}
            for r in A['data']:
                r = dict(zip(A['heads'], r)); c = cart.get(r['id'])
                g, m, a = r['matchDate'][:8].split('-')
                n = lambda x: int(x) if x not in (None, '') and str(x).lstrip('-').isdigit() else None
                y = (n(c['HYCFT']) + n(c['AYCFT'])) if c and n(c['HYCFT']) is not None and n(c['AYCFT']) is not None else None
                k = (n(c['HCFT']) + n(c['ACFT'])) if c and n(c['HCFT']) is not None and n(c['ACFT']) is not None else None
                arb = (r.get('referee') or '').strip()
                out[r['id']] = dict(fid=r['id'], lega=lg, data=dt.date(2000 + int(a), int(m), int(g)), stag=r['Season'], H=r['homeTeam'], A=r['awayTeam'],
                                    arb=arb if arb and arb.lower() not in ('none', 'null', '-', 'n/a') else None, gialli=y, corner=k)
    return out

def profili(F, K=10, NMAX=80, chiave='gialli', scarta_zero=True):
    # per ogni partita, il rapporto dell'arbitro sulle sue partite PRIMA del giorno: (somma reali + K*e) / (somma attesi + K*e),
    # dove l'atteso di ogni partita e' la media della lega nei 365 giorni prima (anche lei solo dal passato)
    per_lega = collections.defaultdict(list)
    for f in F.values():
        # Footiqo scrive 0 dove il dato manca (in Ligue 1 una partita su sette ha 0 gialli e il CSV 3-6): si scarta
        if f[chiave] is not None and not (scarta_zero and f[chiave] == 0): per_lega[f['lega']].append(f)
    R = {}
    for lg, L in per_lega.items():
        L.sort(key=lambda f: f['data'])
        date = np.array([f['data'].toordinal() for f in L]); val = np.array([f[chiave] for f in L], float); cum = np.r_[0, np.cumsum(val)]
        e = np.full(len(L), np.nan)
        for i, d in enumerate(date):
            a, b = np.searchsorted(date, d - 365, 'left'), np.searchsorted(date, d, 'left')
            if b - a >= 50: e[i] = (cum[b] - cum[a]) / (b - a)
        storia = collections.defaultdict(list)
        for i, f in enumerate(L):
            ei = e[i]
            if f['arb'] and not np.isnan(ei):
                h = [x for x in storia[f['arb']] if x[0] < date[i]][-NMAX:]
                n = len(h); sy = sum(x[1] for x in h); se = sum(x[2] for x in h)
                R[f['fid']] = dict(r=(sy + K * ei) / (se + K * ei), n=n, e=ei)
            if f['arb'] and not np.isnan(ei): storia[f['arb']].append((date[i], val[i], ei))
    return R

def num(x):
    try: return float(str(x).replace(',', '.').replace('%', ''))
    except Exception: return None

def leggi_csv(f):
    import csv, io as _io
    righe = {}
    for r in csv.reader(_io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if not r or not r[0]: continue
        if r[0].startswith('=== ARCHIVIO'): break
        righe.setdefault(r[0], r)
    ids, out = righe['ID PARTITA'], {}
    for c in range(1, len(ids), 4):
        if not ids[c] or not (righe['COPIA CONFORME DELLO SCANNER'][c] or '').startswith('SI'): continue
        v = lambda k, d=0: righe[k][c + d] if k in righe and len(righe[k]) > c + d else None
        kk = lambda k: float('inf') if (v(k) or '').strip() in ('--', '') else num(v(k))
        out[ids[c]] = dict(lam_y=num(v('Gialli tot (atteso)')), y=num(v('Gialli tot (atteso)', 2)), k_y=kk('Dispersione gialli (k)'),
                           p35=num(v('Gialli Over 3.5')), lam_c=num(v('Corner tot (atteso)')), c=num(v('Corner tot (atteso)', 2)), k_c=kk('Dispersione corner (k)'))
    return out

def nb_logpmf(y, m, k):
    y, m, k = np.asarray(y, float), np.asarray(m, float), np.asarray(k, float)
    lp = y * np.log(m) - m - np.array([math.lgamma(v + 1) for v in y])
    fin = np.isfinite(k); kf = np.where(fin, k, 1.0)
    lg = np.array([math.lgamma(a + b) - math.lgamma(b) for a, b in zip(y, kf)])
    nb = lg - np.array([math.lgamma(v + 1) for v in y]) + kf * np.log(kf / (kf + m)) + y * np.log(m / (kf + m))
    return np.where(fin, nb, lp)

def nb_over(soglia, m, k):
    return 1 - sum(np.exp(nb_logpmf(np.full(len(m), j), m, k)) for j in range(int(soglia) + 1))

def misura(nome, lam, kd, y, f, lega, soglia):
    b_grid = np.round(np.arange(-1.0, 2.51, 0.01), 2)
    ll = lambda b, s: nb_logpmf(y[s], lam[s] * np.exp(b * f[s]), kd[s])
    leghe = sorted(set(lega)); d_cnt, d_ov, bs = np.zeros(len(y)), np.zeros(len(y)), {}
    yy = (y > soglia).astype(float)
    for l in leghe:
        tr, te = lega != l, lega == l
        b = b_grid[np.argmax([ll(bb, tr).sum() for bb in b_grid])]; bs[l] = b
        d_cnt[te] = -(ll(b, te) - ll(0, te))
        p0 = nb_over(soglia, lam[te], kd[te]); p1 = nb_over(soglia, lam[te] * np.exp(b * f[te]), kd[te])
        d_ov[te] = qg.ll(p1, yy[te]) - qg.ll(p0, yy[te])
    z = lambda d: d.mean() / d.std(ddof=1) * math.sqrt(len(d))
    meglio = lambda d: sum(d[lega == l].mean() < 0 for l in leghe)
    print(f'  {nome}: b fuori lega {" / ".join(f"{bs[l]:+.2f}" for l in leghe)} ({" / ".join(leghe)})')
    print(f'     log-verosimiglianza del conteggio {1000 * d_cnt.mean():+.2f}‰ (z {z(d_cnt):+.2f}, meglio in {meglio(d_cnt)}/{len(leghe)})'
          f' · logloss Over {soglia}.5 {1000 * d_ov.mean():+.2f}‰ (z {z(d_ov):+.2f}, meglio in {meglio(d_ov)}/{len(leghe)})')
    print('     per lega, Over: ' + ' · '.join(f'{l} {1000 * d_ov[lega == l].mean():+.2f}‰' for l in leghe))
    X = lam * f; e = y - lam; bb = (X * e).sum() / (X * X).sum(); res = e - bb * X
    se = math.sqrt((res ** 2).sum() / (len(y) - 1) / (X * X).sum())
    print(f'     su tutte (in campione): b {bb:+.3f} ±{se:.3f} (z {bb / se:+.2f})')
    return d_cnt, d_ov

def main():
    a = sys.argv[1:]; cart = 'batch/footiqo'
    if '--footiqo' in a: i = a.index('--footiqo'); cart = a[i + 1]; del a[i:i + 2]
    if '--scarica' in a: a.remove('--scarica'); scarica(cart)
    STAGIONI = {'2324', '2425'}
    dirs = a or ['batch48', 'batch/2627']
    F = leggi_footiqo(cart)
    print(f'Footiqo: {len(F)} partite dei cinque campionati, con l arbitro {sum(f["arb"] is not None for f in F.values())}, con i gialli {sum(f["gialli"] is not None for f in F.values())}')
    M, Q = qm.carica(dirs, 'batch/quote')
    Q = [q for q in Q if q['lega'] in LEGHE.values() and q['fds'] in STAGIONI]
    A = qgo.aggancia(Q, qgo.footiqo(cart))
    csvv = {}
    for d in dirs:
        for fn in sorted(os.listdir(d)):
            if fn.endswith('.csv'): csvv.update(leggi_csv(os.path.join(d, fn)))
    righe = []
    for q, x in zip(Q, A):
        if x is None or x['fid'] not in F or q['id'] not in csvv: continue
        righe.append(dict(q=q, f=F[x['fid']], c=csvv[q['id']]))
    print(f'esplorazione (2023/24 e 2024/25): {len(Q)} partite coi file di football-data, agganciate a Footiqo {len(righe)}')
    # prove di coincidenza
    ok_y = [r for r in righe if r['f']['gialli'] is not None and r['c']['y'] is not None]
    ok_c = [r for r in righe if r['f']['corner'] is not None and r['c']['c'] is not None]
    print(f'coincidenza: gialli di Footiqo uguali a quelli del CSV {sum(r["f"]["gialli"] == r["c"]["y"] for r in ok_y)}/{len(ok_y)}'
          f' (scarto medio {np.mean([r["f"]["gialli"] - r["c"]["y"] for r in ok_y]):+.3f}) · corner {sum(r["f"]["corner"] == r["c"]["c"] for r in ok_c)}/{len(ok_c)}')
    lam = np.array([r['c']['lam_y'] for r in righe]); kd = np.array([r['c']['k_y'] for r in righe])
    pc = np.array([r['c']['p35'] for r in righe]) / 100
    print(f'  Over 3.5 dei gialli rifatto da atteso e dispersione: scarto massimo dal CSV {100 * np.nanmax(abs(nb_over(3, lam, kd) - pc)):.3f} punti')
    for K in (10, 5, 20, 40):
        R = profili(F, K=K)
        S = [r for r in righe if r['f']['fid'] in R and r['c']['y'] is not None]
        if K == 10:
            nn = np.array([R[r['f']['fid']]['n'] for r in S])
            print(f'\narbitro col profilo: {len(S)}/{len(righe)} · partite precedenti dell arbitro: mediana {int(np.median(nn))}, sotto 10 {np.mean(nn < 10) * 100:.1f}%,'
                  f' arbitri diversi {len({r["f"]["arb"] for r in S})}')
            rr = np.array([R[r['f']['fid']]['r'] for r in S]); print(f'rapporto dell arbitro (K = 10): 10° / 50° / 90° percentile {np.percentile(rr, 10):.3f} / {np.median(rr):.3f} / {np.percentile(rr, 90):.3f}')
        f = np.log(np.array([R[r['f']['fid']]['r'] for r in S]))
        lg = np.array([r['q']['lega'] for r in S]); y = np.array([r['c']['y'] for r in S]); l_ = np.array([r['c']['lam_y'] for r in S]); k_ = np.array([r['c']['k_y'] for r in S])
        print(f'\n=== GIALLI, K = {K} ===')
        misura('gialli', l_, k_, y, f, lg, 3)
        if K == 10:
            print('  per quinto del rapporto dell arbitro: partite, gialli veri, attesi dal motore, veri/attesi')
            qs = np.quantile(f, [0, .2, .4, .6, .8, 1])
            for j in range(5):
                s = (f >= qs[j]) & (f <= qs[j + 1]) if j == 4 else (f >= qs[j]) & (f < qs[j + 1])
                print(f'    {j + 1}° (rapporto {np.exp(f[s]).mean():.3f}) {s.sum():5d}  {y[s].mean():.2f}  {l_[s].mean():.2f}  {y[s].mean() / l_[s].mean():.3f}')
            Sc = [r for r in S if r['c']['c'] is not None and r['c']['lam_c']]
            fc = np.log(np.array([R[r['f']['fid']]['r'] for r in Sc]))
            print('\n=== CONTROLLO: i corner, con lo stesso profilo dei gialli (non deve muovere niente) ===')
            misura('corner', np.array([r['c']['lam_c'] for r in Sc]), np.array([r['c']['k_c'] for r in Sc]), np.array([r['c']['c'] for r in Sc]), fc,
                   np.array([r['q']['lega'] for r in Sc]), 9)

if __name__ == '__main__':
    if '--solo-scarica' in sys.argv: scarica('batch/footiqo', {'cartellini': 'HYCFT'})
    else: main()
