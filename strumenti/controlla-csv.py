#!/usr/bin/env python3
# CONTROLLI DEI CSV DEL COMPARATORE, prima di qualunque analisi (AGENTS.md, Leggere un CSV del
# Comparatore): copia conforme, ID PARTITA unici dentro e fra i file, stagione della partita
# uguale a quella del database, lgN > 0, metriche avanzate dal motore o di riserva, clamp
# dell'HFA, archivio di lega in fondo. Non guarda nessun risultato.
#
#   python3 strumenti/controlla-csv.py batch48 batch4            cartelle o file, anche insieme
#
# Esce con 1 se una partita non e' in copia conforme, un ID si ripete, una stagione non
# coincide o lgN e' 0. L'Elo rifatto dall'archivio lo controlla strumenti/elo-archivio.py.
import collections
import glob
import os
import sys


def leggi(f):
    righe, archivio = {}, False
    with open(f, encoding='utf-8-sig', errors='replace') as h:
        for line in h:
            if line.startswith('=== ARCHIVIO'):
                archivio = True
                break
            p = line.rstrip('\r\n').split(';')
            righe.setdefault(p[0], p)
    return righe, archivio


def valori(righe, etichetta):
    p = righe.get(etichetta)
    return [v.strip() for v in p[1::4]] if p else []


def main(argomenti):
    file = []
    for a in argomenti:
        file += sorted(glob.glob(os.path.join(a, '*.csv'))) if os.path.isdir(a) else [a]
    if not file:
        sys.exit('Indica cartelle o file CSV del Comparatore.')
    visti, male, tot = {}, 0, collections.Counter()
    for f in file:
        righe, archivio = leggi(f)
        ids = [x for x in valori(righe, 'ID PARTITA') if x]
        n = len(ids)
        cc = valori(righe, 'COPIA CONFORME DELLO SCANNER')[:n]
        no = sum(1 for v in cc if not v.upper().startswith('SI'))
        testa = (righe.get('Copia conforme dello Scanner') or ['', 'assente'])[1]
        dentro = n - len(set(ids))
        fra = sorted({i for i in ids if i in visti and visti[i] != f})
        for i in ids:
            visti.setdefault(i, f)
        st, db = valori(righe, 'STAGIONE')[:n], valori(righe, 'STAGIONE DEL DATABASE')[:n]
        stag = sum(1 for a, b in zip(st, db) if a != b)
        lg = valori(righe, 'Unita: partite di lega usate')[:n]
        lg0 = sum(1 for v in lg if not v.replace('.', '').isdigit() or float(v) <= 0)
        orig = collections.Counter(valori(righe, 'Origine metriche avanzate')[:n])
        clamp = sum(1 for v in valori(righe, 'HFA: il clamp ha morso?')[:n] if v.upper().startswith('SI'))
        guasti = []
        if no: guasti.append(f'{no} non in copia conforme')
        if dentro: guasti.append(f'{dentro} ID ripetuti nel file')
        if fra: guasti.append(f'{len(fra)} ID gia\' in un altro file ({os.path.basename(visti[fra[0]])})')
        if stag: guasti.append(f'{stag} con la stagione diversa da quella del database')
        if lg0: guasti.append(f'{lg0} con lgN 0')
        if len(lg) < n: guasti.append('riga lgN assente')
        avvisi = []
        if not archivio: avvisi.append('senza archivio di lega (file prima del b47)')
        if clamp: avvisi.append(f'clamp dell\'HFA su {clamp}')
        ris = sum(v for k, v in orig.items() if k.startswith('riserva'))
        if ris: avvisi.append(f'riserva su {ris}')
        male += bool(guasti)
        tot['file'] += 1
        tot['partite'] += n
        tot['conformi'] += n - no
        stato = 'NO  ' if guasti else 'ok  '
        print(f'{stato}{os.path.basename(f)}: {n} partite, intestazione «{testa}»'
              + (', ' + ', '.join(guasti) if guasti else '') + (' · ' + ', '.join(avvisi) if avvisi else ''))
    print(f'\n{tot["file"]} file, {tot["partite"]} partite, {tot["conformi"]} in copia conforme, {len(visti)} ID diversi; '
          + (f'{male} file da guardare' if male else 'niente da segnalare'))
    sys.exit(1 if male else 0)


if __name__ == '__main__':
    main(sys.argv[1:])
