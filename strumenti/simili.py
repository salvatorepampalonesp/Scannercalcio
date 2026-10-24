# Il confronto contro squadre simili, con piu' dati (AGENTS.md, Il confronto contro squadre simili).
#
#   python3 strumenti/simili.py --scarica "ITA:Serie A=2024/2025,2025/2026,2026/2027" ...   # in batch/stile
#   python3 strumenti/simili.py "ITA:Serie A=2024/2025,2025/2026,2026/2027" ...             # la misura
#
# Lo scarico chiede alla PitchAPI l'archivio della lega e, per ogni partita conclusa, /stats e /advanced (due
# chiamate a partita, fino a TETTO). Le quote vengono da football-data (batch/fd, strumenti/rating-quote.py
# --scarica): i punti attesi di ogni partita sono quelli delle probabilita' di chiusura, e il residuo e' punti veri
# meno punti attesi. Lo stile di una squadra prima di una partita e' la media, con emivita di 106 giorni, delle
# sue partite di lega precedenti (anche di altre stagioni, anche dell'altra sede).
# Quattro misure: il KNN dello Scanner su tutta la storia (punti e residui contro le squadre simili all'avversario);
# la risposta di ogni squadra allo stile dell'avversario (ridge sulle sue partite precedenti); gli incastri di stile
# per tutte le squadre (ridge fuori lega); pareggi e gol fra squadre simili. Esito, 6.445 partite di 11 campionati: il
# numero della card misura la forza (correlazione +0.344 coi punti), ma dato il mercato non aggiunge niente (z -0.5), e
# un rendimento particolare contro un tipo di avversario non si ripete (z +1.2, 5 leghe su 11).
import json, os, sys, math, collections, importlib.util, concurrent.futures as cf
import datetime as dt
import numpy as np

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _modulo(nome, file):
    sp = importlib.util.spec_from_file_location(nome, os.path.join(RADICE, 'strumenti', file)); m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m); return m
un = _modulo('undici', 'undici.py'); rq = un.rq
un.DIR = DIR = os.path.join(RADICE, 'batch', 'stile')
FDCOD = {'l_0ALvwF': 'I1', 'l_4WFCIZ': 'E0', 'l_0ErfuF': 'SP1', 'l_1Isor4': 'D1', 'l_3FJFUl': 'F1', 'l_4DWyTT': 'E1',
         'l_4H43wr': 'N1', 'l_4QexZg': 'P1', 'l_3hvsne': 'D2', 'l_2L6d1F': 'B1', 'l_1LMdEO': 'SC0'}

def scarica(leghe):
    os.makedirs(DIR, exist_ok=True); lavori = []
    for lid, ss in leghe:
        for s in ss:
            nf = f'arch_{lid}_{s.replace("/", "-")}.json'
            if not un.jl(nf):
                d = un.chiama(f'/leagues/{lid}/matches?season={s}&status=all')
                if d: un.salva(nf, d)
            for m in un.jl(nf)['data']['matches']:
                if m['status'] != 'finished': continue
                for ep, nome in (('stats', 'stats'), ('advanced', 'adv')):
                    if not os.path.exists(os.path.join(DIR, f'{nome}_{m["id"]}.json')): lavori.append((m['id'], ep, nome))
    print(len(lavori), 'chiamate da fare', flush=True)
    def uno(x):
        d = un.chiama(f'/matches/{x[0]}/{x[1]}')
        if d is not None: un.salva(f'{x[2]}_{x[0]}.json', d)
    with cf.ThreadPoolExecutor(4) as ex:
        for i, _ in enumerate(ex.map(uno, lavori)):
            if i % 1000 == 0: print(i, un._conto, flush=True)
    print('fine', un._conto, flush=True)

if __name__ == '__main__' and '--scarica' in sys.argv:
    scarica(un.argomenti(sys.argv[1:])); sys.exit()

def n0(v):
    try: return float(str(v).split()[0].replace('%', ''))
    except (TypeError, ValueError, IndexError): return None

STATS = {'npxg': 'expected_goals_non_penalty', 'sot': 'ShotsOnTarget', 'tch_box': 'touches_opp_box', 'poss': 'BallPossesion',
         'big_ch': 'big_chance', 'corners': 'corners', 'long_balls': 'long_balls_accurate', 'fouls': 'fouls', 'aerials': 'aerials_won'}
ADV = {'field_tilt': ('territory', 'field_tilt'), 'ppda': ('defending', 'ppda'), 'avg_def_x': ('defending', 'avg_defensive_action_x'),
       'avg_x': ('territory', 'avg_action_x'), 'f3_entries': ('territory', 'final_third_entries'), 'box_entries': ('territory', 'box_entries'),
       'high_to': ('defending', 'high_turnovers'), 'cp_regains': ('defending', 'counterpress_regains_5s'), 'rec_time': ('defending', 'ball_recovery_time'),
       'seq_time': ('tempo', 'sequence_time'), 'pps': ('tempo', 'passes_per_sequence'), 'direct_speed': ('tempo', 'direct_speed'),
       'direct_att': ('tempo', 'direct_attacks'), 'buildup_att': ('tempo', 'buildup_attacks'), 'crosses': ('passing', 'crosses'),
       'prog_passes': ('passing', 'progressive_passes'), 'xt': ('possession_value', 'xt_total')}
CHIAVI = list(STATS) + list(ADV)
# le 11 dimensioni del KNN dello Scanner (KNN_DIMS): chiave del profilo dell'avversario e peso
KNN = [('npxg', 1.5), ('npxga', 1.5), ('field_tilt', 1.2), ('avg_def_x', 1.2), ('poss', 1.0), ('ppda', 1.0), ('tch_box', 1.1),
       ('f3_entries', 0.9), ('cp_regains', 0.7), ('seq_time', 0.6), ('avg_x', 0.8)]
VARIANTI = [('knn', KNN, 1.0, False), ('stile', [(k, w) for k, w in KNN if k not in ('npxg', 'npxga')], 1.0, False),
            ('stretto', KNN, 0.5, False), ('ruolo', KNN, 1.0, True)]
DESCR = {'knn': "le 11 dimensioni del KNN dello Scanner", 'stile': "le 9 di stile, senza npxg e npxga",
         'stretto': "le 11 del KNN, nucleo largo la meta' (piu' selettivo)", 'ruolo': "le 11 del KNN, solo le partite nella stessa sede (come lo Scanner)"}
STILE = ['poss', 'field_tilt', 'ppda', 'avg_def_x', 'direct_speed', 'seq_time', 'long_balls', 'crosses', 'high_to', 'cp_regains', 'aerials', 'tch_box']

def valori(mid, home_id):
    s, a = un.jl(f'stats_{mid}.json'), un.jl(f'adv_{mid}.json')
    out = {'H': {}, 'A': {}}
    try:
        per = [p for p in s['data']['periods'] if p['period'] == 'All'][0]
        it = {i['key']: i for g in per['groups'] for i in g['items']}
        for k, key in STATS.items():
            if key in it: out['H'][k], out['A'][k] = n0(it[key]['home']), n0(it[key]['away'])
    except (TypeError, KeyError, IndexError): pass
    try:
        for t in a['data']['teams']:
            lato = 'H' if t['team']['id'] == home_id else 'A'
            for k, (g, f) in ADV.items(): out[lato][k] = (t.get(g) or {}).get(f)
    except (TypeError, KeyError): pass
    return out

_CAL = []
def calibra():
    # la chiusura col margine tolto in proporzione sottovaluta i favoriti: i punti attesi vengono da una logistica su
    # (log(p1/p2), |log(p1/p2)|) stimata sulle 18 leghe di football-data dal 2019/20 al 2023/24, fuori dal campione
    if not _CAL:
        from sklearn.linear_model import LogisticRegression
        X, y = [], []
        for dv in rq.DIVS:
            for m in rq.leggi(dv):
                if 2 <= m['stag'] <= 6 and m['pc'] and m['hg'] is not None:
                    v = rq.lo(m['pc']); X.append([v, abs(v)]); y.append(rq.out_of(m))
        _CAL.append(LogisticRegression(C=100, max_iter=3000).fit(np.array(X), np.array(y)))
    return _CAL[0]

def carica(lid, ss):
    ms = sorted([dict(m, _stag=s) for s in ss for m in un.jl(f'arch_{lid}_{s.replace("/", "-")}.json')['data']['matches']
                 if m['status'] == 'finished' and m.get('score_home') is not None], key=lambda m: m['time_utc'])
    fd = rq.leggi(FDCOD[lid]); rq.rating_quote(fd); rq.elo(fd)
    for m in ms:
        m['_v'] = valori(m['id'], m['home_team']['id'])
        x = rq.aggancia({'data': m['date'], 'hg': m['score_home'], 'ag': m['score_away'], 'H': m['home_team']['name'], 'A': m['away_team']['name']}, fd)
        m['_fd'] = x if (x and x['pc']) else None
        m['_lid'] = lid
    return ms

def punti(g, s): return 3 if g > s else (1 if g == s else 0)

def profili(ms, HL=106.0):
    # per ogni partita e lato, il profilo della squadra prima della partita: media decaduta di quello che ha fatto (k)
    # e di quello che ha concesso (k + 'a'), dalle partite precedenti; e il residuo di ogni partita sul mercato
    storia = collections.defaultdict(list)   # squadra -> [(data, valori propri, valori concessi, residuo, avversario, profilo avversario)]
    xi = math.log(2) / HL
    for m in ms:
        d = dt.date.fromisoformat(m['date'])
        for lato, t in (('H', m['home_team']['id']), ('A', m['away_team']['id'])):
            h = storia[t]
            if len(h) < 6: m['_p' + lato] = None; continue
            w = np.array([math.exp(-xi * (d - x[0]).days) for x in h]); p = {}
            for k in CHIAVI:
                for suf, j in (('', 1), ('a', 2)):
                    v = [(wi, x[j].get(k)) for wi, x in zip(w, h) if x[j].get(k) is not None]
                    if len(v) >= 4: p[k + suf] = sum(a * b for a, b in v) / sum(a for a, _ in v)
            p['n'] = len(h); m['_p' + lato] = p
        if m['_fd']:
            v = rq.lo(m['_fd']['pc']); pc = calibra().predict_proba([[v, abs(v)]])[0]; eH, eA = 3 * pc[0] + pc[1], 3 * pc[2] + pc[1]
            rH, rA = punti(m['score_home'], m['score_away']) - eH, punti(m['score_away'], m['score_home']) - eA
        else: rH = rA = None
        m['_r'] = (rH, rA)
        for lato, t, o, ol, r in (('H', m['home_team']['id'], m['away_team']['id'], 'A', rH), ('A', m['away_team']['id'], m['home_team']['id'], 'H', rA)):
            storia[t].append((d, m['_v'][lato], m['_v'][ol], r, o, m.get('_p' + ol), punti(*((m['score_home'], m['score_away']) if lato == 'H' else (m['score_away'], m['score_home']))), lato))
    return storia

def simili_di(storia_t, d, target, sd, dims, HL=106.0, hmul=1.0, sede=None):
    # media dei residui (e dei punti) di una squadra contro gli avversari simili a target, col nucleo dello Scanner
    xi = math.log(2) / HL; rows = []
    for x in storia_t:
        if x[0] >= d: break
        po = x[5]
        if po is None or x[3] is None or (sede and x[7] != sede): continue
        num = den = 0.0
        for k, wk in dims:
            if po.get(k) is None or target.get(k) is None or not sd.get(k): continue
            num += wk * ((po[k] - target[k]) / sd[k]) ** 2; den += wk
        if den == 0: continue
        rows.append((math.sqrt(num / den), x[3], x[6], math.exp(-xi * (d - x[0]).days)))
    if len(rows) < 8: return None
    h = hmul * max(0.35, float(np.median([r[0] for r in rows])))
    w = np.array([math.exp(-0.5 * (r[0] / h) ** 2) * r[3] for r in rows]); t = np.array([r[3] for r in rows])
    res = np.array([r[1] for r in rows]); pts = np.array([r[2] for r in rows])
    return {'sim_r': (w * res).sum() / w.sum(), 'tutte_r': (t * res).sum() / t.sum(), 'sim_p': (w * pts).sum() / w.sum(),
            'tutte_p': (t * pts).sum() / t.sum(), 'neff': w.sum() ** 2 / (w ** 2).sum(), 'n': len(rows)}

def misura(leghe):
    tutte, sdl = [], {}
    for lid, ss in leghe:
        ms = carica(lid, ss); st = profili(ms)
        P = [m['_p' + l] for m in ms for l in 'HA' if m.get('_p' + l)]
        sd = {k: float(np.std([p[k] for p in P if p.get(k) is not None])) for k in [k for k, _ in KNN] + STILE + [s + 'a' for s in STILE]
              if sum(1 for p in P if p.get(k) is not None) > 30}
        for m in ms:
            if not (m['_fd'] and m.get('_pH') and m.get('_pA')): continue
            pA, pH = dict(m['_pA']), dict(m['_pH'])
            pA['npxga'], pH['npxga'] = pA.get('npxga'), pH.get('npxga')
            d = dt.date.fromisoformat(m['date'])
            for nome, dims, hm, sede in VARIANTI:
                m['_s' + nome] = (simili_di(st[m['home_team']['id']], d, pA, sd, dims, hmul=hm, sede=sede and 'H'),
                                  simili_di(st[m['away_team']['id']], d, pH, sd, dims, hmul=hm, sede=sede and 'A'))
            m['_sd'] = sd
            tutte.append(m)
    return tutte

def regr(y, x):
    x = np.asarray(x, float); y = np.asarray(y, float); X = np.c_[x, np.ones(len(x))]
    b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    se = math.sqrt(e.var() * len(y) / (len(y) - 2) / ((x - x.mean()) ** 2).sum())
    return b[0], b[0] / se, float(np.corrcoef(x, y)[0, 1])

def rapporto_squadra(tutte):
    print(f'{len(tutte)} partite con le quote di chiusura e i profili delle due squadre')
    for nome, *_ in VARIANTI:
        R = [m for m in tutte if m['_s' + nome][0] and m['_s' + nome][1]]
        y = [m['_r'][0] - m['_r'][1] for m in R]
        H = [m['_s' + nome][0] for m in R]; A = [m['_s' + nome][1] for m in R]
        print(f'\n[{nome}: dimensioni {DESCR[nome]}] {len(R)} partite; '
              f'partite precedenti per squadra in mediana {int(np.median([h["n"] for h in H]))}, simili efficaci {np.median([h["neff"] for h in H]):.1f}')
        y2 = [punti(m['score_home'], m['score_away']) - punti(m['score_away'], m['score_home']) for m in R]
        cand = {
            'punti contro i simili (come lo Scanner), sui punti': ([h['sim_p'] - a['sim_p'] for h, a in zip(H, A)], y2),
            'punti contro i simili, sul residuo del mercato': ([h['sim_p'] - a['sim_p'] for h, a in zip(H, A)], y),
            'residuo contro i simili': ([h['sim_r'] - a['sim_r'] for h, a in zip(H, A)], y),
            'residuo contro i simili meno il residuo su tutte': ([(h['sim_r'] - h['tutte_r']) - (a['sim_r'] - a['tutte_r']) for h, a in zip(H, A)], y),
            'residuo su tutte (forma contro il mercato)': ([h['tutte_r'] - a['tutte_r'] for h, a in zip(H, A)], y),
        }
        ym = [rq.lo(m['_fd']['pc']) - m['_fd']['yq'] for m in R]
        # il numero della card dice piu' dei punti a partita su tutte? regressione dei punti su tutti e due
        X2 = np.c_[[h['sim_p'] - a['sim_p'] for h, a in zip(H, A)], [h['tutte_p'] - a['tutte_p'] for h, a in zip(H, A)], np.ones(len(R))]
        b2, *_ = np.linalg.lstsq(X2, np.array(y2, float), rcond=None); e2 = np.array(y2) - X2 @ b2
        se2 = np.sqrt(np.diag(e2.var() * len(R) / (len(R) - 3) * np.linalg.inv(X2.T @ X2)))
        print(f'  punti sui punti contro i simili e su tutte, insieme: simili {b2[0]:+.3f} (z {b2[0]/se2[0]:+.2f}), tutte {b2[1]:+.3f} (z {b2[1]/se2[1]:+.2f})')
        cand['il mercato lo sa? residuo contro i simili meno tutte, su chiusura meno quote passate'] = (cand['residuo contro i simili meno il residuo su tutte'][0], ym)
        cand['il mercato lo sa? punti contro i simili, su chiusura meno quote passate'] = (cand['punti contro i simili, sul residuo del mercato'][0], ym)
        for k, (x, yy) in cand.items():
            b, z, c = regr(yy, x)
            leghe = collections.defaultdict(list)
            for m, xi, yi in zip(R, x, yy): leghe[m['_lid']].append((xi, yi))
            pos = sum(1 for v in leghe.values() if len(v) > 50 and regr([q[1] for q in v], [q[0] for q in v])[0] > 0)
            print(f'  {k:52s}\n      coef {b:+.3f} (z {z:+5.2f}), correlazione {c:+.3f}, positivo in {pos}/{len(leghe)} leghe')

def rapporto_stile(tutte):
    # incastri di stile per tutte le squadre: z dello stile della casa per z dello stile della trasferta (144 prodotti) e
    # gli stili da soli (24), ridge stimata fuori lega. Bersagli: il residuo dei punti sul mercato, e il residuo del mercato
    # sul rating dalle quote passate (cosa il mercato sa della partita oltre la forza delle squadre)
    R = [m for m in tutte if m['_fd'].get('yq') is not None and min(m['_fd']['nq']) >= 6]
    per = collections.defaultdict(list)
    for m in R:
        for l in 'HA': per[m['_lid']].append(m['_p' + l])
    mu = {lid: {k: np.mean([p[k] for p in P if p.get(k) is not None]) for k in STILE} for lid, P in per.items()}
    sd = {lid: {k: np.std([p[k] for p in P if p.get(k) is not None]) or 1 for k in STILE} for lid, P in per.items()}
    def z(m, l): return np.array([((m['_p' + l].get(k, mu[m['_lid']][k]) or mu[m['_lid']][k]) - mu[m['_lid']][k]) / sd[m['_lid']][k] for k in STILE])
    ZH = np.array([z(m, 'H') for m in R]); ZA = np.array([z(m, 'A') for m in R])
    INT = np.einsum('ni,nj->nij', ZH, ZA).reshape(len(R), -1)
    y_r = np.array([m['_r'][0] - m['_r'][1] for m in R])
    y_m = np.array([rq.lo(m['_fd']['pc']) - m['_fd']['yq'] for m in R])
    lid = np.array([m['_lid'] for m in R])
    print(f'\n[incastri di stile] {len(R)} partite di {len(set(lid))} leghe; 12 stili: {", ".join(STILE)}')
    for nome_y, y in (('residuo dei punti sul mercato', y_r), ('residuo del mercato sul rating dalle quote passate', y_m)):
        for nome_x, X in (('stili da soli (24)', np.c_[ZH, ZA]), ('incastri (144)', INT), ('tutti e due (168)', np.c_[ZH, ZA, INT])):
            riga = []
            for lam in (10, 100, 1000, 10000):
                pr = np.zeros(len(y))
                for L in set(lid):
                    tr = lid != L; Xt = X[tr]; m0 = Xt.mean(0); yt = y[tr]
                    b = np.linalg.solve((Xt - m0).T @ (Xt - m0) + lam * np.eye(X.shape[1]), (Xt - m0).T @ (yt - yt.mean()))
                    pr[~tr] = yt.mean() + (X[~tr] - m0) @ b
                r2 = 1 - ((y - pr) ** 2).mean() / ((y - y.mean()) ** 2).mean(); c = np.corrcoef(pr, y)[0, 1]
                riga.append(f'lam {lam}: R2 {r2:+.4f}, corr {c:+.3f} (z {c * math.sqrt(len(y)):+.1f})')
            print(f'  {nome_y}, {nome_x}: ' + ' | '.join(riga))

def rapporto_risposta(tutte, LAM=(3, 10, 30, 100)):
    # la risposta di ogni squadra allo stile dell'avversario: per ogni partita, una ridge del residuo della squadra
    # (punti meno punti attesi) sullo stile dell'avversario (12 z) nelle sue partite precedenti; la previsione per la
    # partita di oggi, casa meno trasferta, contro il residuo di oggi
    per = collections.defaultdict(list)
    for m in tutte:
        for l in 'HA': per[m['_lid']].append(m['_p' + l])
    mu = {lid: {k: np.mean([p[k] for p in P if p.get(k) is not None]) for k in STILE} for lid, P in per.items()}
    sd = {lid: {k: np.std([p[k] for p in P if p.get(k) is not None]) or 1 for k in STILE} for lid, P in per.items()}
    def z(p, lid): return np.array([((p.get(k) if p.get(k) is not None else mu[lid][k]) - mu[lid][k]) / sd[lid][k] for k in STILE])
    print('\n[la risposta di ogni squadra allo stile dell\'avversario]')
    for lam in LAM:
        storia = collections.defaultdict(list); pr, yy, nn = [], [], []
        for m in sorted(tutte, key=lambda m: m['time_utc']):
            zA, zH = z(m['_pA'], m['_lid']), z(m['_pH'], m['_lid'])
            f = []
            for t, zo in ((m['home_team']['id'], zA), (m['away_team']['id'], zH)):
                h = storia[t]
                if len(h) < 15: f.append(None); continue
                X = np.array([x[0] for x in h]); y = np.array([x[1] for x in h]); X0 = X - X.mean(0)
                b = np.linalg.solve(X0.T @ X0 + lam * np.eye(len(STILE)), X0.T @ (y - y.mean()))
                f.append((zo - X.mean(0)) @ b)
            if None not in f:
                pr.append(f[0] - f[1]); yy.append(m['_r'][0] - m['_r'][1]); nn.append(min(len(storia[m['home_team']['id']]), len(storia[m['away_team']['id']])))
            storia[m['home_team']['id']].append((zA, m['_r'][0])); storia[m['away_team']['id']].append((zH, m['_r'][1]))
        b, zz, c = regr(yy, pr)
        print(f'  lam {lam:4d}: {len(yy)} partite (storia in mediana {int(np.median(nn))}), coefficiente {b:+.3f} (z {zz:+.2f}), correlazione {c:+.3f}, '
              f'deviazione standard della previsione {np.std(pr):.3f} punti')

def rapporto_pari_gol(tutte):
    # squadre simili fra loro: pareggi e gol rispetto al mercato. Il pareggio atteso e' quello della chiusura ricalibrata,
    # l'Over 2.5 quello della chiusura col margine tolto in proporzione (sull'Over il margine e' quasi simmetrico)
    per = collections.defaultdict(list)
    for m in tutte:
        for l in 'HA': per[m['_lid']].append(m['_p' + l])
    mu = {lid: {k: np.mean([p[k] for p in P if p.get(k) is not None]) for k in STILE} for lid, P in per.items()}
    sd = {lid: {k: np.std([p[k] for p in P if p.get(k) is not None]) or 1 for k in STILE} for lid, P in per.items()}
    def z(p, lid): return np.array([((p.get(k) if p.get(k) is not None else mu[lid][k]) - mu[lid][k]) / sd[lid][k] for k in STILE])
    R = [m for m in tutte if m['_fd'].get('ov') is not None]
    dist = np.array([np.sqrt(((z(m['_pH'], m['_lid']) - z(m['_pA'], m['_lid'])) ** 2).mean()) for m in R])
    somma = {k: np.array([(z(m['_pH'], m['_lid']) + z(m['_pA'], m['_lid']))[i] / 2 for m in R]) for i, k in enumerate(STILE)}
    pX = np.array([calibra().predict_proba([[rq.lo(m['_fd']['pc']), abs(rq.lo(m['_fd']['pc']))]])[0][1] for m in R])
    rx = np.array([m['score_home'] == m['score_away'] for m in R], float) - pX
    ro = np.array([m['score_home'] + m['score_away'] > 2.5 for m in R], float) - np.array([m['_fd']['ov'] for m in R])
    print(f'\n[squadre simili fra loro: pareggi e gol contro il mercato] {len(R)} partite; pareggi {100*(rx + pX).mean():.1f}% contro {100*pX.mean():.1f}% della chiusura, '
          f'Over 2.5 {100*(ro + np.array([m["_fd"]["ov"] for m in R])).mean():.1f}% contro {100*np.mean([m["_fd"]["ov"] for m in R]):.1f}%')
    q = np.quantile(dist, [0.2, 0.8])
    for nome, sel in (('stili piu\' simili (20%)', dist <= q[0]), ('in mezzo', (dist > q[0]) & (dist < q[1])), ('stili piu\' diversi (20%)', dist >= q[1])):
        n = sel.sum(); print(f'  {nome:26s} {n:5d} partite: pareggi meno chiusura {100*rx[sel].mean():+5.2f} (±{200*rx[sel].std()/math.sqrt(n):.2f}), '
                            f'Over 2.5 meno chiusura {100*ro[sel].mean():+5.2f} (±{200*ro[sel].std()/math.sqrt(n):.2f})')
    b, zz, c = regr(rx, dist); print(f'  pareggi sulla distanza di stile: coef {b:+.4f} (z {zz:+.2f})')
    b, zz, c = regr(ro, dist); print(f'  Over 2.5 sulla distanza di stile: coef {b:+.4f} (z {zz:+.2f})')
    for k in STILE:
        b1, z1, _ = regr(ro, somma[k]); b2, z2, _ = regr(rx, somma[k])
        print(f'  media dello stile {k:12s} delle due: Over {100*b1:+5.2f} punti per sd (z {z1:+5.2f}), pareggi {100*b2:+5.2f} (z {z2:+5.2f})')

if __name__ == '__main__':
    T = misura(un.argomenti(sys.argv[1:]))
    rapporto_squadra(T); rapporto_stile(T); rapporto_risposta(T); rapporto_pari_gol(T)
