# Dove la PitchAPI ha la curva di pressione (/momentum): una prova di poche chiamate per lega e stagione.
#
#   python3 strumenti/momentum-copertura.py [--campione 6] [--tetto 3000]
#
# Per ogni lega di leghe.json e ognuna delle sue stagioni: l'archivio (una chiamata) e la curva di N partite concluse
# prese a intervalli regolari nella stagione (N chiamate; una partita gia' scaricata in batch/tiri non costa niente).
# Dice quante hanno la curva. Scrive batch/momentum-copertura.json, fuori da git.
import os, sys, json, importlib.util
from concurrent.futures import ThreadPoolExecutor

QUI = os.path.dirname(os.path.abspath(__file__)); RADICE = os.path.dirname(QUI)
_s = importlib.util.spec_from_file_location('tiri', os.path.join(QUI, 'tiri.py')); tiri = importlib.util.module_from_spec(_s); _s.loader.exec_module(tiri)

def curva(mid):
    f = os.path.join(tiri.TIRI, mid + '.json')
    if os.path.exists(f):
        try: return bool(json.load(open(f)).get('mo')), False
        except ValueError: pass
    c, d = tiri.chiama(f'/matches/{mid}/momentum')
    if c is None: return None, True
    return bool(((d or {}).get('points')) if isinstance(d, dict) else False), True

def main():
    n = int(sys.argv[sys.argv.index('--campione') + 1]) if '--campione' in sys.argv else 6
    if '--tetto' in sys.argv: tiri.TETTO = int(sys.argv[sys.argv.index('--tetto') + 1])
    L = json.load(open(os.path.join(RADICE, 'leghe.json')))
    L = L['data']['leagues'] if isinstance(L, dict) else L
    out = []
    for lg in sorted(L, key=lambda x: (x['country_code'], x['name'])):
        for s in lg['seasons']:
            c, d = tiri.chiama(f"/leagues/{lg['id']}/matches?season={s}&status=all")
            M = sorted([m for m in ((d or {}).get('matches') or []) if m.get('status') == 'finished'], key=lambda m: (m.get('time_utc') or '', m['id']))
            scelte = [M[round(i * (len(M) - 1) / (n - 1))]['id'] for i in range(n)] if len(M) >= n else [m['id'] for m in M]
            scelte = list(dict.fromkeys(scelte))
            with ThreadPoolExecutor(6) as ex: R = list(ex.map(curva, scelte))
            si = sum(1 for r, _ in R if r); fall = sum(1 for r, _ in R if r is None)
            riga = dict(id=lg['id'], paese=lg['country_code'], lega=lg['name'], stagione=s, concluse=len(M), provate=len(scelte), con_curva=si, fallite=fall)
            out.append(riga)
            print(f"{lg['country_code']:4s} {lg['name'][:28]:28s} {s:10s} concluse {len(M):4d}  curva {si}/{len(scelte)}" + (f'  fallite {fall}' if fall else ''), flush=True)
    json.dump(out, open(os.path.join(RADICE, 'batch', 'momentum-copertura.json'), 'w'), indent=1)
    print('chiamate', tiri._FATTE[0])

if __name__ == '__main__':
    main()
