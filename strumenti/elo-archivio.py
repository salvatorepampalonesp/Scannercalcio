# L'ELO DEL MOTORE, RIFATTO DALL'ARCHIVIO IN FONDO AL CSV DEL COMPARATORE (dal b47).
#
# Replica buildGlobalElo e calcTrend di scanner.html con le manopole libere, per provare
# fuori dal motore curve dello stacco, ingressi delle neopromosse, K e scale. Prima di ogni
# uso, la prova di coincidenza: con le manopole di default deve ridare Elo, HFA e pendenza
# che il CSV riporta, partita per partita.
#
#   python3 strumenti/elo-archivio.py Backtest_V97_....csv     prova di coincidenza
#
# Se il motore cambia buildGlobalElo, questa copia va cambiata con lui (AGENTS.md, Due copie
# della stessa costante divergono, sempre): la prova di coincidenza lo dice.
import csv, io, math, sys, datetime as dt

DEFAULT = dict(soglia=45, tau=360, asintoto=0.9, bersaglio=1500, ingresso=1500,
               k_basso=30, k_alto=20, k_soglia=15)


def leggi(path):
    righe = list(csv.reader(io.open(path, encoding='utf-8-sig'), delimiter=';'))
    archivio, partite = [], {}
    for r in righe:
        if not r or not r[0]:
            continue
        if r[0].startswith('ARCHIVIO #'):
            archivio.append(dict(id=r[1], stagione=r[2], t=r[3], stato=r[4], h=r[5], hn=r[6], a=r[7], an=r[8],
                                 gh=None if r[9] == '' else int(r[9]), ga=None if r[10] == '' else int(r[10])))
        elif not r[0].startswith('=== ARCHIVIO') and not r[0].startswith('ARCHIVIO '):
            partite.setdefault(r[0], r)
    return archivio, partite


def _ms(t):
    return dt.datetime.strptime(t[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=dt.timezone.utc).timestamp() * 1000


def elo(archivio, orario_bersaglio, P=DEFAULT):
    giorno, tms = orario_bersaglio[:10], _ms(orario_bersaglio)
    passate = [m for m in archivio if m['stato'] == 'finished' and m['t'] and m['h'] and m['a']
               and m['t'][:10] < giorno and _ms(m['t']) < tms]
    visti, vc, vf, n = set(), 0, 0, 0
    for m in passate:
        if m['id'] in visti:
            continue
        visti.add(m['id'])
        gh, ga = m['gh'] or 0, m['ga'] or 0
        vc += gh > ga
        vf += gh < ga
        n += 1
    hfa = 65
    if n >= 50 and vc > 0 and vf > 0:
        hfa = max(30, min(100, round(400 * math.log10(vc / vf))))
    tab, serie, ultima, giocate, visti = {}, {}, {}, {}, set()
    for m in sorted(passate, key=lambda m: _ms(m['t'])):
        if m['id'] in visti:
            continue
        visti.add(m['id'])
        h, a, t = m['h'], m['a'], _ms(m['t'])
        for x in (h, a):
            if x not in tab:
                tab[x], serie[x], giocate[x] = P['ingresso'], [], 0
        for x in (h, a):
            if x in ultima:
                g = (t - ultima[x]) / 86400000
                if g > P['soglia']:
                    s = P['asintoto'] * (1 - math.exp(-(g - P['soglia']) / P['tau']))
                    tab[x] = (1 - s) * tab[x] + s * P['bersaglio']
        gh, ga = m['gh'] or 0, m['ga'] or 0
        esito = 1 if gh > ga else (0 if gh < ga else 0.5)
        d = abs(gh - ga)
        mov = 1.0 if d <= 1 else (1.5 if d == 2 else (11 + d) / 8)
        atteso = 1 / (1 + 10 ** ((tab[a] - (tab[h] + hfa)) / 400))
        K = sum(P['k_basso'] if giocate[x] < P['k_soglia'] else P['k_alto'] for x in (h, a)) / 2
        delta = K * mov * (esito - atteso)
        tab[h] += delta
        tab[a] -= delta
        giocate[h] += 1
        giocate[a] += 1
        ultima[h] = ultima[a] = t
        serie[h].insert(0, round(tab[h]))
        serie[a].insert(0, round(tab[a]))
    return tab, serie, hfa


def pendenza(s):
    if len(s) < 10:
        return 0
    return sum(s[:5]) / 5 - sum(s[5:15]) / len(s[5:15])


def coincidenza(path):
    archivio, P = leggi(path)
    col = lambda nome: P.get(nome, [])
    ids, t, hid, aid = col('ID PARTITA'), col('DATA ISO (UTC)'), col('ID SQUADRA CASA'), col('ID SQUADRA TRASFERTA')
    eh, ea, hf = col('ELO Casa'), col('ELO Trasferta'), col('HFA Lega')
    trH = col('Elo: pendenza casa (media ultime 5 meno 6-15, punti)')
    trA = col('Elo: pendenza trasferta (media ultime 5 meno 6-15, punti)')
    n = diversi = diversa_pend = 0
    for i in range(1, len(ids), 4):
        if not ids[i]:
            continue
        tab, serie, hfa = elo(archivio, t[i])
        n += 1
        v = (str(round(tab.get(hid[i], 1500))), str(round(tab.get(aid[i], 1500))), str(hfa))
        diversi += v != (eh[i], ea[i], hf[i])
        for sq, tr in ((hid[i], trH[i] if trH else ''), (aid[i], trA[i] if trA else '')):
            if tr and tr != 'N/D':
                diversa_pend += abs(pendenza(serie.get(sq, [])) - float(tr.replace(',', '.'))) > 0.0051
    return dict(archivio=len(archivio), partite=n, elo_diversi=diversi, pendenza_diversa=diversa_pend)


if __name__ == '__main__':
    for f in sys.argv[1:]:
        r = coincidenza(f)
        esito = 'COINCIDE' if r['archivio'] and r['partite'] and not r['elo_diversi'] and not r['pendenza_diversa'] else 'NON COINCIDE'
        print(f"{f}: archivio {r['archivio']} partite · {r['partite']} partite nel file · "
              f"Elo/HFA diversi {r['elo_diversi']} · pendenza diversa {r['pendenza_diversa']} · {esito}")
