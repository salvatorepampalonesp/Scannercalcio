# Le quote del Goal (AGENTS.md, Le quote del Goal: la regola).
#
#   python3 strumenti/quote-goal.py [batch48 batch/2627] [--footiqo batch/footiqo] [--scarica]
#
# Footiqo (parte gratuita) ha le quote di chiusura di 1xBet di 1X2, Over/Under 0.5-4.5 e Goal/NoGoal per i
# cinque campionati. Qui si agganciano alle partite dei CSV (con le quote di football-data, come
# quote-matrice.py) per data e nomi, si controlla l'aggancio sulle quote dell'1X2 e dell'Over 2.5 (senza
# risultati), e si fanno i tre test della regola: il Goal con la sua quota contro la matrice allineata
# dello Scanner, l'Over 1.5 e 3.5 con le loro quote, la matrice a tre vincoli (rho sul Goal).
# --scarica prende le tabelle da footiqo.com: due pagine e due richieste per lega, con una pausa, come fa
# la pagina col menu «All». Condizioni d'uso: uso personale, niente ridistribuzione. I file restano in
# batch/footiqo/, fuori da git.
#
# Esito: nessuno dei tre passa. Il Goal con la sua quota contro la matrice allineata -1.69 per mille
# (z = -1.73, 3 leghe su 5), Over 1.5 +0.11, Over 3.5 +0.90: la matrice allineata ordina il Goal meglio
# della sua quota, che ne correggerebbe solo il livello. Il terzo test non si fa se il primo non passa.
import os, sys, re, json, html, math, time, subprocess, collections, importlib.util, datetime as dt, warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
warnings.filterwarnings('ignore')
QUI = os.path.dirname(os.path.abspath(__file__))
_s = importlib.util.spec_from_file_location('qm', os.path.join(QUI, 'quote-matrice.py'))
qm = importlib.util.module_from_spec(_s); _s.loader.exec_module(qm); qg = qm.qg

LEGHE = {'italy-serie-a': 'Serie A', 'england-premier-league': 'Premier League', 'spain-laliga': 'LaLiga',
         'germany-bundesliga': 'Bundesliga', 'france-ligue-1': 'Ligue 1'}
COL = ['id', 'matchDate', 'Country', 'League', 'Season', 'homeTeam', 'awayTeam', 'H', 'D', 'A', 'O05', 'U05', 'O15', 'U15',
       'O25', 'U25', 'O35', 'U35', 'O45', 'U45', 'BTTSY', 'BTTSN']

def curl(*a):
    return subprocess.run(['curl', '-s', '--max-time', '120', *a], capture_output=True, text=True).stdout

def scarica(cartella):
    os.makedirs(cartella, exist_ok=True)
    for slug in LEGHE:
        s = curl(f'https://footiqo.com/database/leagues/{slug}/'); time.sleep(3)
        i = s.find('Historical Odds: 1X2')
        ids = list(dict.fromkeys(re.findall(r'data-wpdatatable_id="(\d+)"', s[i:])))[:2]
        for tid, nome in zip(ids, ('corrente', 'passate')):
            nonce = re.search(r'id="wdtNonceFrontendServerSide_%s" name="[^"]+" value="([^"]+)"' % tid, s).group(1)
            seg = s[s.find('data-wpdatatable_id="%s"' % tid):][:60000].split('</thead>')[0]
            teste = [html.unescape(re.sub(r'<[^>]+>', '', h)).strip() for h in re.findall(r'<th[^>]*>(.*?)</th>', seg, re.S)]
            assert teste == COL, teste
            dati = ['draw=1', 'start=0', 'length=-1', 'search[value]=', 'search[regex]=false', 'order[0][column]=1', 'order[0][dir]=asc', 'wdtNonce=' + nonce]
            for k, h in enumerate(teste):
                dati += [f'columns[{k}][data]={k}', f'columns[{k}][name]={h}', f'columns[{k}][searchable]=true', f'columns[{k}][orderable]=true',
                         f'columns[{k}][search][value]=', f'columns[{k}][search][regex]=false']
            r = json.loads(curl('-X', 'POST', '-H', 'X-Requested-With: XMLHttpRequest', '-H', 'Referer: https://footiqo.com/', '--data', '&'.join(dati),
                                f'https://footiqo.com/wp-admin/admin-ajax.php?action=get_wdtable&table_id={tid}'))
            json.dump({'heads': teste, 'data': r['data']}, open(os.path.join(cartella, f'{slug}_{nome}.json'), 'w'))
            print(f'  {slug} {nome}: {len(r["data"])} righe'); time.sleep(4)

def num(x):
    try: v = float(x); return v if v > 1 else None
    except Exception: return None

def footiqo(cartella):
    out = []
    for slug, lg in LEGHE.items():
        for nome in ('passate', 'corrente'):
            for r in json.load(open(os.path.join(cartella, f'{slug}_{nome}.json')))['data']:
                r = dict(zip(COL, r)); g, m, a = r['matchDate'][:8].split('-')
                out.append(dict(lega=lg, data=dt.date(2000 + int(a), int(m), int(g)), H=r['homeTeam'], A=r['awayTeam'], q={k: num(r[k]) for k in COL[7:]}, fid=r['id']))
    return out

# Per data (entro un giorno) e nomi; la co-occorrenza dei nomi conta le partite vicine con l'1X2 simile
# (log(p1/p2) entro 0.4), non il punteggio, che Footiqo non ha in questa tabella.
def aggancia(Q, F):
    per = collections.defaultdict(list)
    for f in F: per[(f['lega'], f['data'])].append(f)
    vic = lambda lg, d: sum((per.get((lg, d + dt.timedelta(days=k)), []) for k in (-1, 0, 1)), [])
    cooc = collections.defaultdict(collections.Counter)
    for q in Q:
        x = math.log(q['qc'][2] / q['qc'][0])
        for f in vic(q['lega'], dt.date.fromisoformat(q['data'])):
            if not (f['q']['H'] and f['q']['A']): continue
            w = 1 if abs(math.log(f['q']['A'] / f['q']['H']) - x) < 0.4 else 0.01
            cooc[(q['lega'], q['H'])][f['H']] += w; cooc[(q['lega'], q['A'])][f['A']] += w
    mappa = {k: c.most_common(1)[0][0] for k, c in cooc.items()}
    out = []
    for q in Q:
        c = [f for f in vic(q['lega'], dt.date.fromisoformat(q['data'])) if f['H'] == mappa.get((q['lega'], q['H'])) and f['A'] == mappa.get((q['lega'], q['A']))]
        out.append(c[0] if len(c) == 1 else None)
    return out

def coppia(a, b, k):
    p = np.array([(1 / x[a]) / (1 / x[a] + 1 / x[b]) if x[a] and x[b] else np.nan for x in k]); return p

def confronto(nome, base, cand, y, lega, ok):
    d = qg.ll(cand[ok], y[ok]) - qg.ll(base[ok], y[ok]); lg = lega[ok]
    z = d.mean() / d.std(ddof=1) * math.sqrt(len(d))
    per = {l: d[lg == l].mean() for l in sorted(set(lg))}
    meglio = sum(v < 0 for v in per.values())
    print(f'  {nome:62s} {1000 * d.mean():+7.2f}‰  z {z:+6.2f}  meglio in {meglio}/{len(per)}  ({len(d)} partite)')
    print('     per lega: ' + ' · '.join(f'{l} {1000 * v:+.2f}‰' for l, v in per.items()))
    return z, meglio, len(per)

def matrice_tre(pc, lg12, gg, rho0, it=24):
    # rho del Dixon-Coles scelto perche' la matrice allineata a 1X2 e Over 2.5 dia il Goal gg
    lo, hi = np.full(len(pc), -1.0), np.full(len(pc), 1.0)
    aH, aA = qg.allinea(pc, lg12, rho0)
    for _ in range(it):
        b0 = np.maximum(-1 / aH, -1 / aA); b1 = np.minimum(1 / (aH * aA), 1.0)
        lo, hi = np.maximum(lo, b0), np.minimum(hi, b1); r = (lo + hi) / 2
        aH, aA = qg.allinea(pc, lg12, r); g = qg.mercati(qg.matrici(aH, aA, r))['gg']
        su = g > gg; lo = np.where(su, r, lo); hi = np.where(su, hi, r)
    r = (lo + hi) / 2; aH, aA = qg.allinea(pc, lg12, r); P = qg.matrici(aH, aA, r)
    return P, r, np.abs(qg.mercati(P)['gg'] - gg)

def main():
    a = sys.argv[1:]; cart = 'batch/footiqo'
    if '--footiqo' in a: i = a.index('--footiqo'); cart = a[i + 1]; del a[i:i + 2]
    if '--scarica' in a: a.remove('--scarica'); scarica(cart)
    dirs = a or ['batch48', 'batch/2627']
    W, b, OU = qm.costanti()
    M, Q = qm.carica(dirs, 'batch/quote')
    Q = [q for q in Q if q['lega'] in LEGHE.values()]
    C = qm.calcola(Q, W, b, OU); Q = C['Q']
    F = footiqo(cart); A = aggancia(Q, F)
    print(f'partite dei cinque campionati con 1X2 e Over di football-data: {len(Q)} · agganciate a Footiqo {sum(x is not None for x in A)}'
          f' · matrice del motore entro {C["dev"]:.3f} punti dal CSV')
    k = np.array([x is not None for x in A]); A = [x for x in A if x is not None]
    sel = lambda v: v[k]
    lega = sel(C['lega']); hg, ag = sel(C['hg']), sel(C['ag']); A0 = {kk: sel(v) for kk, v in C['A0'].items()}
    q1 = [x['q'] for x in A]; Qk = [q for q, kk in zip(Q, k) if kk]
    x12 = np.log(np.array([q['qc'][2] / q['qc'][0] for q in Qk])); y12 = np.log(np.array([x['A'] / x['H'] for x in q1]))
    print(f'coincidenza senza risultati: log(p1/p2) 1xBet contro football-data r {np.corrcoef(x12, y12)[0, 1]:.4f}, scarto mediano {np.median(abs(x12 - y12)):.3f}')
    marg = lambda a_, b_: 100 * np.nanmean([1 / x[a_] + 1 / x[b_] - 1 if x[a_] and x[b_] else np.nan for x in q1])
    print(f'margine medio di 1xBet: Goal/NoGoal {marg("BTTSY", "BTTSN"):.2f}% · Over/Under 1.5 {marg("O15", "U15"):.2f}% · 2.5 {marg("O25", "U25"):.2f}% · 3.5 {marg("O35", "U35"):.2f}%')
    tot = hg + ag
    Y = {'gg': ((hg > 0) & (ag > 0)).astype(float), 'o15': (tot > 1).astype(float), 'o35': (tot > 3).astype(float)}
    PM = {'gg': coppia('BTTSY', 'BTTSN', q1), 'o15': coppia('O15', 'U15', q1), 'o35': coppia('O35', 'U35', q1)}
    esiti, comb = {}, {}
    print('\n=== I TEST (fuori lega: stimato su quattro leghe, misurato sulla quinta) ===')
    for kk, nome in (('gg', 'primo test, il Goal'), ('o15', 'secondo test, Over 1.5'), ('o35', 'secondo test, Over 3.5')):
        ok = ~np.isnan(PM[kk]); y = Y[kk]
        X = np.column_stack([qg.logit(PM[kk]), qg.logit(A0[kk])])
        p = np.full(len(y), np.nan); p[ok] = qg.lolo2(X[ok], y[ok], lega[ok]); comb[kk] = p
        z, m, n = confronto(f'{nome}: allineata -> con la sua quota', A0[kk], p, y, lega, ok)
        esiti[kk] = z <= -2 and m >= 4
        print(f'  -> {"PASSA" if esiti[kk] else "NON PASSA"}')
    if esiti['gg']:
        print('\n=== TERZO TEST: la matrice a tre vincoli ===')
        ok = ~np.isnan(comb['gg'])
        PC, pc = C['PC'][k][ok], C['pc'][k][ok]; lg12 = np.log(PC[:, 0] / PC[:, 2])
        rho0 = np.array([q['rho'] for q in Qk])[ok]
        t0 = time.time(); P3, r3, err = matrice_tre(pc, lg12, comb['gg'][ok], rho0)
        print(f'  {ok.sum()} partite in {time.time() - t0:.0f} s · rho {np.percentile(r3, 5):+.3f} … {np.percentile(r3, 95):+.3f} (motore {np.mean(rho0):+.3f})'
              f' · Goal non raggiunto (scarto > 0.001) {int((err > 1e-3).sum())}')
        m3 = qg.mercati(P3); mA = {kk: v[ok] for kk, v in A0.items()}
        print(f'  controllo: Over 2.5 a tre vincoli contro allineata, scarto massimo {abs(m3["o25"] - mA["o25"]).max():.2e};'
              f' log(p1/p2) {abs(np.log(m3["p1"] / m3["p2"]) - lg12).max():.2e}')
        L3, LA = qm.perdite(P3, hg[ok], ag[ok]), qm.perdite(C['A'][k][ok], hg[ok], ag[ok])
        for kk in ('esatti', 'multigol', 'handicap'):
            d = L3[kk] - LA[kk]; v = ~np.isnan(d); lg = lega[ok][v]; d = d[v]
            z = d.mean() / d.std(ddof=1) * math.sqrt(len(d)); per = {l: d[lg == l].mean() for l in sorted(set(lg))}
            print(f'  {kk:9s} {1000 * d.mean():+7.2f}‰  z {z:+6.2f}  meglio in {sum(x < 0 for x in per.values())}/{len(per)} · '
                  + ' · '.join(f'{l} {1000 * x:+.2f}' for l, x in per.items()) + ('  -> PASSA' if z <= -2 and sum(x < 0 for x in per.values()) >= 4 else '  -> NON PASSA'))
    descrittivi(C, k, Qk, q1, lega, hg, ag, A0, PM, comb, Y, W, b, OU)

def descrittivi(C, k, Qk, q1, lega, hg, ag, A0, PM, comb, Y, W, b, OU):
    print('\n=== DESCRITTIVI ===')
    y = Y['gg']; ok = ~np.isnan(PM['gg'])
    confronto('Goal: allineata -> mercato in proporzione', A0['gg'], PM['gg'], y, lega, ok)
    ar = np.full(len(y), np.nan); ar[ok] = qg.lolo2(qg.logit(A0['gg'][ok])[:, None], y[ok], lega[ok])
    mr = np.full(len(y), np.nan); mr[ok] = qg.lolo2(qg.logit(PM['gg'][ok])[:, None], y[ok], lega[ok])
    confronto('Goal: allineata ricalibrata -> combinazione', ar, comb['gg'], y, lega, ok)
    confronto('Goal: mercato ricalibrato -> combinazione', mr, comb['gg'], y, lega, ok)
    c = qg.stima2(np.column_stack([qg.logit(PM['gg'][ok]), qg.logit(A0['gg'][ok])]), y[ok])
    print(f'  coefficienti su tutte e cinque (QUOTE_GG se passa): intercetta {c[0]:+.5f} · mercato {c[1]:+.5f} · allineata {c[2]:+.5f}')
    for kk in ('gg', 'o15', 'o35'):
        okk = ~np.isnan(comb[kk])
        print(f'  {kk}: previsto allineata {100 * A0[kk][okk].mean():.1f}% · mercato {100 * PM[kk][okk].mean():.1f}% · combinazione {100 * comb[kk][okk].mean():.1f}% · reale {100 * Y[kk][okk].mean():.1f}%')
    print('  Goal per fascia (allineata / mercato / combinazione -> esce):')
    for lo_, hi_ in ((0, .4), (.4, .5), (.5, .6), (.6, 1)):
        for nome, p in (('allineata', A0['gg']), ('mercato', PM['gg']), ('combinazione', comb['gg'])):
            s = ok & (p >= lo_) & (p < hi_)
            if s.sum(): print(f'    {int(100 * lo_):2d}-{int(100 * hi_):3d} {nome:12s} {s.sum():5d} partite, prevista {100 * p[s].mean():.1f}, esce {100 * y[s].mean():.1f}')
    print('  AUC del Goal per lega (allineata / mercato / combinazione):')
    for l in sorted(set(lega)):
        s = ok & (lega == l)
        print(f'    {l:15s} {roc_auc_score(y[s], A0["gg"][s]):.3f} / {roc_auc_score(y[s], PM["gg"][s]):.3f} / {roc_auc_score(y[s], comb["gg"][s]):.3f}')
    tot = hg + ag
    for kk, a_, b_, soglia in (('o05', 'O05', 'U05', 0), ('o45', 'O45', 'U45', 4)):
        pm = coppia(a_, b_, q1); s = ~np.isnan(pm); yy = (tot > soglia).astype(float)
        P = C['A'][k]; pa = P[:, :, :].reshape(len(P), -1)[:, (qg.I + qg.J > soglia + .5).ravel()].sum(1)
        d = qg.ll(pm[s], yy[s]) - qg.ll(pa[s], yy[s]); print(f'  Over {soglia}.5: allineata -> mercato {1000 * d.mean():+.2f}‰ (z {d.mean() / d.std(ddof=1) * math.sqrt(s.sum()):+.2f}); previsto {100 * pa[s].mean():.1f} / {100 * pm[s].mean():.1f}, reale {100 * yy[s].mean():.1f}')
    # la matrice allineata alle quote di 1xBet invece che a quelle di football-data
    Qx = [dict(q, qc=[x['H'], x['D'], x['A']], riga={'AvgC>2.5': str(x['O25']), 'AvgC<2.5': str(x['U25'])}) for q, x in zip(Qk, q1) if x['H'] and x['D'] and x['A'] and x['O25'] and x['U25']]
    kx = np.array([bool(x['H'] and x['D'] and x['A'] and x['O25'] and x['U25']) for x in q1])
    Cx = qm.calcola(Qx, W, b, OU); gx = Cx['A0']['gg']; s = ok & kx
    d = qg.ll(gx[ok[kx]], y[s]) - qg.ll(A0['gg'][s], y[s])
    print(f'  Goal dalla matrice allineata alle quote di 1xBet invece che a football-data: {1000 * d.mean():+.2f}‰ (z {d.mean() / d.std(ddof=1) * math.sqrt(len(d)):+.2f}), previsto {100 * gx[ok[kx]].mean():.1f}%')
    dd = qg.ll(comb['gg'][s], y[s]) - qg.ll(gx[ok[kx]], y[s])
    print(f'  ... e la combinazione col mercato del Goal contro quella: {1000 * dd.mean():+.2f}‰ (z {dd.mean() / dd.std(ddof=1) * math.sqrt(len(dd)):+.2f})')
    # i soldi, alla chiusura di 1xBet
    qy = np.array([x['BTTSY'] or np.nan for x in q1]); qn = np.array([x['BTTSN'] or np.nan for x in q1])
    def roi(gioca_si, mask):
        r = np.where(gioca_si, np.where(y == 1, qy - 1, -1.0), np.where(y == 0, qn - 1, -1.0))[mask]
        return 100 * r.mean(), 100 * r.std(ddof=1) / math.sqrt(len(r)), len(r)
    m, se, n = roi(comb['gg'] >= .5, ok); print(f'  il lato piu probabile (combinazione) sempre, alla chiusura di 1xBet: {m:+.1f}% ±{2 * se:.1f} su {n}')
    for t in (3, 5):
        diff = A0['gg'] - PM['gg']; mk = ok & (abs(diff) >= t / 100)
        m, se, n = roi(diff > 0, mk); print(f'  dove la matrice allineata si discosta dal mercato di {t}+ punti, il suo lato: {m:+.1f}% ±{2 * se:.1f} su {n}')

if __name__ == '__main__':
    main()
