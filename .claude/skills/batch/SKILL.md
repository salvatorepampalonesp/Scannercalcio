---
name: batch
description: Fa i backtest sulla PitchAPI vera col batch automatico del Comparatore (strumenti/batch-auto.js), per una o più leghe e stagioni. Lo segue, controlla ogni CSV (copia conforme, ID unici, Elo rifatto dall'archivio) e manda i file all'utente appena sono pronti. Da usare quando servono CSV nuovi per una misura, un test registrato o una tabella da rifare.
---

# Batch automatico

AGENTS.md, *Il batch automatico* e *Leggere un CSV del Comparatore*.

## 1. Prima di lanciare

- **Se è un test**, la regola deve essere già scritta e committata (skill `regola-registrata`).
  Le leghe del test non si aprono prima.
- **Leghe e stagioni** da `leghe.json`: id o nome, `PAESE:Nome` se il nome è ambiguo
  (`GER:Bundesliga`). Le stagioni vanno prese con due stagioni alle spalle in `leghe.json`, come
  le vede lo Scanner. Di default sono 2023/2024–2025/2026; le leghe a anno solare usano `2023,2024,2025`.
  Se una stagione che l'API ha già non è in `leghe.json`, il catalogo è vecchio:
  `node strumenti/catalogo.js --prova` lo dice (vedi in AGENTS.md *Il catalogo delle leghe*).
- **Il motore** è quello della cartella di lavoro: su un branch che cambia `scanner.html`, il
  batch misura il branch.
- **La chiave** è una credenziale API dell'ambiente: tipo Bearer, sito
  `pitchapi-proxy.salvatorepampalone-sp.workers.dev`, header `X-API-KEY` senza prefisso. Non è
  una variabile d'ambiente. Non chiedere mai all'utente di scriverla in chat. Lo script prova una
  chiamata prima di aprire il browser e dice cosa manca. Se manca, leggi la documentazione
  dell'ambiente sui segreti e passa all'utente i passi giusti.

## 2. Il lancio

```bash
node strumenti/batch-auto.js --leghe "League One,League Two,TUR:Super Lig" \
  --stagioni 2023/2024,2024/2025,2025/2026 --out batch/<nome>
```

- Lancialo in background: una stagione dura da 10 minuti a qualche ora. Per avere un'idea, 9
  stagioni (4.327 partite) hanno chiesto un'ora e 25.705 chiamate.
- Il log completo è in `batch/<nome>/batch.log`. A schermo restano le righe che contano e, ogni
  minuto, la partita a cui è arrivato.
- Rilanciare riprende da dove era: una stagione che ha già il suo file si salta.
- I 404 si contano a parte («senza dati»): sono le `/advanced` delle stagioni che non le hanno.
  Quelle righe escono `riserva-k-motore`, e va bene così.
- `--finto` usa la lega finta del banco al posto della PitchAPI. Serve a provare uno strumento
  nuovo senza chiamate.

## 3. Ogni file, appena salvato

```bash
python3 strumenti/elo-archivio.py batch/<nome>/<file>.csv     # deve dire COINCIDE
python3 strumenti/controlla-csv.py batch/<nome>                # deve uscire con 0
```

`controlla-csv.py` controlla:

- la copia conforme (`N partite su N`);
- che gli `ID PARTITA` siano unici, dentro il file e fra i file passati;
- che la stagione di ogni partita sia quella del database;
- che `lgN` sia sopra 0.

Dice anche, come avvisi, su quante righe ha morso il clamp dell'HFA e quante sono di riserva. Per
controllare i doppioni anche contro i batch vecchi, passa insieme tutte le cartelle che userai.

**Manda il file all'utente subito** (`SendUserFile`). Il batch vive nel computer della sessione:
se la sessione resta ferma, il computer si spegne e `batch/` sparisce.

## 4. Alla fine

- All'utente: quante partite, quante in copia conforme, quante chiamate e quante fallite, quanto
  tempo.
- In AGENTS.md la tabella *Campioni su cui si è misurato* prende una riga, che dice per quale
  domanda quelle leghe sono state aperte. Da lì in poi non sono più vergini per quella domanda.
