# Le quote dei bookmaker contro il motore (AGENTS.md, Le quote dei bookmaker: la regola).
#
#   python3 strumenti/quote-bookmaker.py batch48 batch4 [--quote batch/quote]
#
# Legge i CSV del Comparatore delle cartelle date (probabilita' 1X2, squadre, data, punteggio),
# scarica da football-data.co.uk le quote delle dodici leghe se mancano nella cartella --quote,
# le aggancia per data (entro un giorno) e nomi delle squadre (per co-occorrenza sulle date),
# verifica il punteggio, e rifa' il test registrato: combinazione motore + mercato stimata su
# undici leghe e misurata sulla dodicesima. Stampa anche i coefficienti su tutte le partite
# nella forma di QUOTE_COMB (scanner.html), le soglie e il peso del motore dato il mercato.
# Serve scikit-learn (pip install scikit-learn).
import csv, io, os, sys, glob, math, json, collections, datetime as dt, urllib.request, warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
warnings.filterwarnings('ignore')

COD = {'I1': 'Serie A', 'E0': 'Premier League', 'SP1': 'LaLiga', 'D1': 'Bundesliga', 'F1': 'Ligue 1', 'E1': 'Championship',
       'N1': 'Eredivisie', 'P1': 'Liga Portugal', 'B1': 'First Division A', 'D2': '2. Bundesliga', 'SC0': 'Premiership'}
STAG = {'2324': '2023/2024', '2425': '2024/2025', '2526': '2025/2026'}
CINQUE = {'Serie A', 'Premier League', 'LaLiga', 'Bundesliga', 'Ligue 1'}

def num(s):
    try: return float(str(s).strip().replace('%', '').replace(',', '.'))
    except (TypeError, ValueError): return None

def leggi_csv(f):
    righe = collections.defaultdict(list)
    for r in csv.reader(io.open(f, encoding='utf-8-sig'), delimiter=';'):
        if not r or not r[0]: continue
        if r[0].startswith('=== ARCHIVIO'): break
        righe[r[0]].append(r)
    g = lambda k: righe[k][0] if k in righe else None
    ids, out = g('ID PARTITA'), []
    for c in range(1, len(ids), 4):
        if not ids[c]: continue
        v = lambda k: g(k)[c] if g(k) and len(g(k)) > c else None
        if not (v('COPIA CONFORME DELLO SCANNER') or '').startswith('SI'): continue
        hg, ag = [int(x) for x in v('SCORE').split('-')]
        out.append({'id': ids[c], 'lega': v('LEGA'), 'data': v('DATA ISO (UTC)')[:10], 'H': v('SQUADRA CASA'), 'A': v('SQUADRA TRASFERTA'),
                    'hg': hg, 'ag': ag, 'out': 0 if hg > ag else (1 if hg == ag else 2), 'p': [num(v(k)) / 100 for k in ('1', 'X', '2')]})
    return out

def scarica(cartella):
    os.makedirs(cartella, exist_ok=True)
    nomi = [(f'{c}_{s}.csv', f'https://www.football-data.co.uk/mmz4281/{s}/{c}.csv') for c in COD for s in STAG] + [('SWZ.csv', 'https://www.football-data.co.uk/new/SWZ.csv')]
    for nome, url in nomi:
        f = os.path.join(cartella, nome)
        if not os.path.exists(f):
            with urllib.request.urlopen(url, timeout=60) as r: open(f, 'wb').write(r.read())

def data(s):
    for fmt in ('%d/%m/%Y', '%d/%m/%y'):
        try: return dt.datetime.strptime(s, fmt).date()
        except ValueError: pass

def prendi(r, pre):
    for k in pre:
        q = [num(r.get(k + e)) for e in 'HDA']
        if all(q) and all(x > 1 for x in q): return q, k
    return None, None

def quote_fd(cartella):
    righe = []
    for cod, lg in COD.items():
        for s, stag in STAG.items():
            for r in csv.DictReader(io.open(os.path.join(cartella, f'{cod}_{s}.csv'), encoding='utf-8-sig', errors='replace')):
                if not r.get('HomeTeam') or not r.get('FTHG'): continue
                qc, fc = prendi(r, ['AvgC', 'PSC', 'B365C']); qp, _ = prendi(r, ['Avg', 'PS', 'B365'])
                righe.append(dict(lega=lg, data=data(r['Date']), H=r['HomeTeam'], A=r['AwayTeam'], hg=int(r['FTHG']), ag=int(r['FTAG']), qc=qc, fc=fc, qp=qp))
    for r in csv.DictReader(io.open(os.path.join(cartella, 'SWZ.csv'), encoding='utf-8-sig')):
        if r['Season'] not in STAG.values() or not r.get('HG'): continue
        qc, fc = prendi(r, ['AvgC', 'PSC', 'B365C'])
        righe.append(dict(lega='Super League', data=data(r['Date']), H=r['Home'], A=r['Away'], hg=int(r['HG']), ag=int(r['AG']), qc=qc, fc=fc, qp=None))
    return righe

def aggancia(M, righe):
    per_data = collections.defaultdict(list)
    for r in righe: per_data[(r['lega'], r['data'])].append(r)
    vicine = lambda lg, d: sum((per_data.get((lg, d + dt.timedelta(days=k)), []) for k in (-1, 0, 1)), [])
    cooc = collections.defaultdict(collections.Counter)
    for m in M:
        for r in vicine(m['lega'], dt.date.fromisoformat(m['data'])):
            cooc[(m['lega'], m['H'])][r['H']] += 1; cooc[(m['lega'], m['A'])][r['A']] += 1
    mappa = {k: c.most_common(1)[0][0] for k, c in cooc.items()}
    out, diversi, mancanti = [], 0, 0
    for m in M:
        c = [r for r in vicine(m['lega'], dt.date.fromisoformat(m['data'])) if r['H'] == mappa.get((m['lega'], m['H'])) and r['A'] == mappa.get((m['lega'], m['A']))]
        if len(c) != 1 or not c[0]['qc']: mancanti += 1; continue
        if (c[0]['hg'], c[0]['ag']) != (m['hg'], m['ag']): diversi += 1; continue
        out.append(dict(m, qc=c[0]['qc'], fc=c[0]['fc'], qp=c[0]['qp']))
    print(f'partite dei CSV {len(M)}: agganciate col punteggio uguale {len(out)}, punteggio diverso {diversi}, non trovate {mancanti}'
          f' · coincidenza {100 * len(out) / max(1, len(out) + diversi):.2f}% · quote di chiusura da {dict(collections.Counter(o["fc"] for o in out))}')
    return out

def main():
    args = sys.argv[1:]; cq = 'batch/quote'
    if '--quote' in args: i = args.index('--quote'); cq = args[i + 1]; del args[i:i + 2]
    M = [m for d in args for f in sorted(glob.glob(os.path.join(d, '*.csv'))) for m in leggi_csv(f)]
    M = list({m['id']: m for m in M}.values())
    scarica(cq); Q = aggancia(M, quote_fd(cq))
    y = np.array([q['out'] for q in Q]); lg = np.array([q['lega'] for q in Q])
    P0 = np.array([q['p'] for q in Q]); P0 /= P0.sum(1, keepdims=True)
    norm = lambda L: np.array([[1 / x for x in q] for q in L]) / np.array([[sum(1 / x for x in q)] for q in L])
    PM = norm([q['qc'] for q in Q])
    lr = lambda P: np.column_stack([np.log(P[:, 0] / P[:, 1]), np.log(P[:, 2] / P[:, 1])])
    ll = lambda P, k=slice(None): -np.log(P[np.arange(len(y)), y])[k]
    def stima(X, k):
        mu, sd = X[k].mean(0), X[k].std(0)
        m = LogisticRegression(C=1.0, max_iter=2000).fit((X[k] - mu) / sd, y[k])
        W = m.coef_ / sd; b = m.intercept_ - (m.coef_ * mu / sd).sum(1)
        return W, b
    def proba(X, W, b):
        Z = X @ W.T + b; Z -= Z.max(1, keepdims=True); E = np.exp(Z); return E / E.sum(1, keepdims=True)
    def lolo(X):
        P = np.zeros((len(y), 3))
        for l in sorted(set(lg)):
            te = lg == l; W, b = stima(X, ~te); P[te] = proba(X[te], W, b)
        return P
    def confronto(nome, A, B):
        dh = (B.argmax(1) == y).astype(float) - (A.argmax(1) == y); dl = ll(B) - ll(A)
        per = {l: dl[lg == l].mean() for l in sorted(set(lg))}
        z = dh.mean() / dh.std(ddof=1) * math.sqrt(len(y))
        print(f'{nome}: prese {100 * (A.argmax(1) == y).mean():.2f} -> {100 * (B.argmax(1) == y).mean():.2f} ({100 * dh.mean():+.2f}, z {z:+.2f})'
              f' · logloss {dl.mean():+.5f} (z {dl.mean() / dl.std(ddof=1) * math.sqrt(len(y)):+.2f}) · meglio in {sum(v < 0 for v in per.values())}/{len(per)} leghe')
        return z, sum(v < 0 for v in per.values())
    X = np.column_stack([lr(P0), lr(PM)]); PC = lolo(X)
    z, meglio = confronto('IL TEST: combinazione contro motore', P0, PC)
    print('ESITO:', 'PASSA' if z >= 2 and meglio >= 8 else 'NON PASSA', '(z >= +2 sulle prese, logloss meglio in almeno 8 leghe su 12)')
    confronto('mercato contro motore', P0, PM); confronto('combinazione contro mercato', PM, PC)
    confronto('combinazione contro mercato ricalibrato', lolo(lr(PM)), PC)
    print('per lega, prese motore / mercato / combinazione:')
    for l in sorted(set(lg)):
        k = lg == l; print(f'  {l:17s} {k.sum():5d}  ' + ' / '.join(f'{100 * (P.argmax(1) == y)[k].mean():.1f}' for P in (P0, PM, PC)))
    c = 100 * PC.max(1); h = PC.argmax(1) == y; c5 = np.isin(lg, list(CINQUE))
    print(f'soglie con le quote (fuori lega): su tutte {100 * h.mean():.1f} (p media {c.mean():.1f})')
    for s in (70, 65, 60, 55, 50):
        k = c >= s; print(f'  >={s}: {100 * h[k].mean():.1f} ±{200 * math.sqrt(h[k].mean() * (1 - h[k].mean()) / k.sum()):.1f} su {100 * k.mean():.0f}%'
                          f' · cinque {100 * h[k & c5].mean():.1f} · altre {100 * h[k & ~c5].mean():.1f}')
    kk = y != 1; F = np.column_stack([np.log(P0[kk, 0] / P0[kk, 2]), np.log(PM[kk, 0] / PM[kk, 2])])
    m2 = LogisticRegression(C=1e6).fit(F, (y[kk] == 0).astype(int))
    neg = sum(LogisticRegression(C=1e6).fit(F[lg[kk] == l], (y[kk][lg[kk] == l] == 0).astype(int)).coef_[0][0] < 0 for l in sorted(set(lg)))
    print(f'1 contro 2, dato il mercato: peso del motore {m2.coef_[0][0]:+.3f}, del mercato {m2.coef_[0][1]:+.3f}; motore negativo in {neg} leghe su {len(set(lg))}')
    W, b = stima(X, np.ones(len(y), bool))
    print('QUOTE_COMB (su tutte le partite):\n  W: ' + json.dumps([[round(float(x), 5) for x in r] for r in W]) + '\n  b: ' + json.dumps([round(float(x), 5) for x in b]))

if __name__ == '__main__':
    main()
