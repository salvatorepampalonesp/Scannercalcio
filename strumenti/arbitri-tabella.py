# La tabella degli arbitri dello Scanner (arbitri.json), dalla PitchAPI (AGENTS.md, Gli arbitri e i gialli: la regola).
#
#   python3 strumenti/arbitri-tabella.py            # scarica le partite nuove e riscrive arbitri.json
#   python3 strumenti/arbitri-tabella.py --prova    # dice cosa cambierebbe, senza scrivere niente
#
# Per Serie A e LaLiga, ogni stagione di leghe.json: l'archivio di lega (/leagues/{id}/matches, una chiamata per
# stagione), e per ogni partita conclusa l'arbitro (/matches/{id}) e i gialli (/matches/{id}/stats, come li legge il
# motore: periodo All, yellow_cards di casa piu' trasferta, 0 se la chiave manca). Ogni risposta si tiene in
# batch/arbitri/, fuori da git: rilanciare chiede solo le partite nuove (circa 20 chiamate a settimana per le due
# leghe; la prima volta circa 8.000). I dati di Footiqo non entrano qui: non si ridistribuiscono.
#
# I nomi: la PitchAPI a volte accorcia quello dello stesso arbitro («Jose Munuera» e «José Luis Munuera Montero»,
# «Alberto Arena» e «Alberto Ruben Arena»). Dentro una lega, un nome le cui parole stanno tutte, in ordine, in un nome
# piu' lungo si unisce a quello; se i nomi lunghi sono piu' d'uno, a quello con piu' partite.
#
# arbitri.json: per lega i nomi e le partite, [giorno, indice dell'arbitro o null, gialli], in ordine di giorno. Lo
# Scanner ne rifa' il rapporto dell'arbitro come profili() di strumenti/arbitri.py, con le sole partite prima del giorno.
import os, sys, json, unicodedata, collections, datetime, importlib.util
from concurrent.futures import ThreadPoolExecutor

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(RADICE, 'batch', 'arbitri')
FILE = os.path.join(RADICE, 'arbitri.json')
LEGHE = {'l_0ALvwF': 'Serie A', 'l_0ErfuF': 'LaLiga'}
_s = importlib.util.spec_from_file_location('tiri', os.path.join(RADICE, 'strumenti', 'tiri.py'))
tiri = importlib.util.module_from_spec(_s); _s.loader.exec_module(tiri)

def norm(n):
    n = unicodedata.normalize('NFKD', n or '').encode('ascii', 'ignore').decode().lower()
    return ' '.join(n.split())

def stagioni(lid):
    L = json.load(open(os.path.join(RADICE, 'leghe.json'), encoding='utf-8'))
    L = L.get('data', L); L = L.get('leagues', L) if isinstance(L, dict) else L
    for l in L:
        if l['id'] == lid: return [s if isinstance(s, str) else s.get('name') for s in l.get('seasons', [])]
    return []

def archivio(lid):
    out = []
    for s in stagioni(lid):
        c, d = tiri.chiama(f'/leagues/{lid}/matches?season={s.replace("/", "%2F")}&status=all')
        if c != 200: raise SystemExit(f'archivio di {LEGHE[lid]} {s}: risposta {c}')
        ms = d.get('matches') if isinstance(d, dict) else d
        out += [dict(id=m['id'], giorno=str(m.get('date') or m.get('time_utc'))[:10], ora=m.get('time_utc') or '')
                for m in (ms or []) if m.get('status') == 'finished' and m.get('score_home') is not None]
    return out

def gialli(st):
    per = [p for p in ((st or {}).get('periods') or []) if p.get('period') == 'All']
    if not per: return None
    v = {'home': None, 'away': None}
    for g in per[0].get('groups') or []:
        for it in g.get('items') or []:
            if it.get('key') == 'yellow_cards' or str(it.get('title', '')).lower() == 'yellow cards':
                for k in v:
                    try: v[k] = float(str(it.get(k)).replace(',', '.').split(' ')[0])
                    except (TypeError, ValueError): v[k] = None
                break
        else: continue
        break
    return int(sum(x or 0 for x in v.values()))

def uno(mid):
    f = os.path.join(CACHE, mid + '.json')
    if os.path.exists(f): return 'gia'
    c1, m = tiri.chiama(f'/matches/{mid}')
    c2, st = tiri.chiama(f'/matches/{mid}/stats')
    if c1 is None or c2 is None: return 'fallita'
    m = m or {}
    json.dump(dict(arb=(m.get('referee') or '').strip() or None, gialli=gialli(st) if c2 == 200 else None),
              open(f, 'w'), separators=(',', ':'))
    return 'scaricata'

def tabella(lid, A):
    righe = []
    for m in sorted(A, key=lambda m: (m['giorno'], m['ora'], m['id'])):
        f = os.path.join(CACHE, m['id'] + '.json')
        if not os.path.exists(f): continue
        c = json.load(open(f))
        if c['gialli'] is None: continue
        righe.append((m['giorno'], c['arb'], c['gialli']))
    conto = collections.Counter(norm(a) for _, a, _ in righe if a)
    forma = collections.defaultdict(collections.Counter)
    for _, a, _ in righe:
        if a: forma[norm(a)][a] += 1
    def dentro(a, b):
        a, b = a.split(), iter(b.split())
        return all(t in b for t in a)
    unisci = {}
    for n in conto:
        lunghi = [x for x in conto if len(x.split()) > len(n.split()) and dentro(n, x)]
        if lunghi: unisci[n] = max(lunghi, key=lambda x: (conto[x], x))
    chiave = lambda a: unisci.get(norm(a), norm(a))
    nomi = sorted({chiave(a) for _, a, _ in righe if a})
    idx = {n: i for i, n in enumerate(nomi)}
    vis = [forma[n].most_common(1)[0][0] for n in nomi]
    partite = [[g, idx[chiave(a)] if a else None, y] for g, a, y in righe]
    return dict(nome=LEGHE[lid], arbitri=vis, partite=partite), len(unisci)

def main():
    prova = '--prova' in sys.argv
    os.makedirs(CACHE, exist_ok=True)
    out = dict(fonte='PitchAPI: /leagues/{id}/matches, /matches/{id} (arbitro), /matches/{id}/stats (gialli)',
               aggiornato=datetime.date.today().isoformat(), leghe={})
    vecchio = json.load(open(FILE, encoding='utf-8')) if os.path.exists(FILE) else {'leghe': {}}
    for lid in LEGHE:
        A = archivio(lid)
        mancano = [m['id'] for m in A if not os.path.exists(os.path.join(CACHE, m['id'] + '.json'))]
        print(f'{LEGHE[lid]}: {len(A)} partite concluse, da scaricare {len(mancano)}', flush=True)
        if mancano and not prova:
            with ThreadPoolExecutor(6) as ex: esiti = collections.Counter(ex.map(uno, mancano))
            print('  ', dict(esiti), flush=True)
        T, n_uniti = tabella(lid, A)
        P = T['partite']; v = vecchio['leghe'].get(lid, {}).get('partite', [])
        print(f'  in tabella {len(P)} partite (dal {P[0][0] if P else "-"} al {P[-1][0] if P else "-"}), senza arbitro '
              f'{sum(p[1] is None for p in P)}, arbitri {len(T["arbitri"])}, nomi accorciati uniti {n_uniti}; nel file di prima {len(v)}')
        out['leghe'][lid] = T
    print(f'chiamate {tiri._FATTE[0]}')
    if prova: print('--prova: arbitri.json non riscritto'); return
    with open(FILE, 'w', encoding='utf-8') as f:
        f.write('{"fonte":' + json.dumps(out['fonte'], ensure_ascii=False) + ',"aggiornato":"' + out['aggiornato'] + '","leghe":{\n')
        for k, (lid, T) in enumerate(out['leghe'].items()):
            f.write(json.dumps(lid) + ':{"nome":' + json.dumps(T['nome'], ensure_ascii=False) + ',"arbitri":'
                    + json.dumps(T['arbitri'], ensure_ascii=False) + ',\n"partite":[\n'
                    + ',\n'.join(json.dumps(p, separators=(',', ':')) for p in T['partite']) + ']}' + (',' if k < len(LEGHE) - 1 else '') + '\n')
        f.write('}}\n')
    print(f'scritto {FILE} ({os.path.getsize(FILE) // 1024} KB)')

if __name__ == '__main__': main()
