---
name: regola-registrata
description: Il metodo del progetto per provare un'idea sul motore senza ingannarsi. Prima si controlla cosa è già stato provato, poi si esplora sulle leghe già guardate. La regola si scrive in AGENTS.md prima di aprire dati nuovi, il test si fa una volta sola e l'esito si scrive com'è. Da usare quando l'utente chiede di indovinare più partite, migliorare un mercato, cambiare una costante, aggiungere una feature o misurare un'idea sui CSV.
---

# Regola registrata

Il progetto ha avuto quattro falsi positivi di fila prima di lavorare così (AGENTS.md, *Disciplina
di calibrazione*). Un'idea entra nel motore solo se passa un test scritto prima di vedere i dati
che lo decidono.

## 1. È già stato provato?

Cerca in AGENTS.md prima di proporre: *Cosa è già stato provato*, *Le cose che hanno retto*,
*Da fare*, *Registro delle costanti*.

```bash
grep -n -i "<parola chiave>" AGENTS.md | head -30
```

Quasi tutte le idee ovvie sono già misurate (forma, riposo, formazioni, pesi dell'Elo, rating sugli
xG, Davidson, Poisson bivariata, temperatura, stacking, quote...). Se c'è, riporta il numero e dì
cosa ci sarebbe di nuovo, se c'è qualcosa.

## 2. L'esplorazione

- **I dati**: i CSV dei batch, nelle cartelle `batch48`, `batch4`, `batch/2627`, `batch/nuove` e
  `batch/livello` (fuori da git, nel computer della sessione). Se non ci sono, chiedili all'utente
  o rifalli con la skill `batch`. Prima `python3 strumenti/controlla-csv.py <cartelle>`.
- **La prova di coincidenza, per prima**: ricalcola un valore che il CSV contiene già e verifica
  che torni. Per esempio l'Over 2.5 dai lambda di ruolo e da `rho` (entro 0.075 punti), o l'Elo
  con `python3 strumenti/elo-archivio.py <csv>`. Non verifica il motore: verifica la tua
  trascrizione.
- **Fuori lega**: si stima su N−1 leghe e si misura sulla N-esima, a turno. La differenza si
  calcola appaiata partita per partita, e `z` è la media divisa per l'errore standard. Si dice in
  quante leghe migliora.
- **Le trappole note**:
  - L'AUC dei mercati gol non si aggrega mai fra leghe.
  - Il CSV ha una cifra decimale.
  - `_base` è della coppia, non della lega.
  - Il lambda è inversamente proporzionale alla media gol di lega.
  - Un miglioramento monotono senza ottimo interno di solito affila e basta.
  - Un candidato sul bordo della griglia non si spedisce.
  - Un effetto che c'è in una metà sola non è un effetto.
- **Strumenti già fatti**, da riusare: in `strumenti/` ci sono `dc-residui.py`, `markov-dc.py`,
  `livello-gol.py`, `rating-xg.py`, `sorpresa.py`, `sorpresa-quote.py` e i `quote-*.py`.

## 3. La regola, scritta prima

Una sezione in AGENTS.md («*Titolo*: la regola»), **committata e pushata prima di aprire i dati
del test**: il commit è la prova della data. Deve dire:

- **perché**: i numeri dell'esplorazione;
- **il candidato con tutto fissato**: la formula e i coefficienti con le loro cifre. Nessun
  parametro si stima sui dati del test;
- **i dati del test**: leghe o stagioni mai aperte per questa domanda. La tabella *Campioni su cui
  si è misurato* dice cosa è già stato guardato e per cosa. In alternativa le partite future, con
  una data (`--dal`);
- **il metro**: logloss 1 contro 2, Over + Goal, Brier o prima proposta del tabellone, sempre
  appaiato;
- **quando passa**, fissato adesso. Di solito: `z ≤ −2` sull'insieme; meglio in almeno metà o due
  terzi delle leghe; nessuna lega con `z > +1`; le prese del pick che non calano oltre −2 errori
  standard;
- **se passa**: cosa entra nel motore e cosa va rimisurato (`PICK_RESA`, `EDGE_BANDS`,
  `SORPRESA_TAB`, la confidence...). **Se non passa**: tutto resta com'è, e la sezione dice
  perché;
- **i descrittivi**: si riportano comunque, ma non decidono.

## 4. Il test

Una volta sola. Il batch si fa con la skill `batch` e si controlla con `controlla-csv.py`; prima
di ricostruire, la prova di coincidenza. La regola non si ritocca dopo aver visto, nemmeno «per
poco»: vedi in AGENTS.md *Il «4 su 5»* e le prese «non in calo» delle neopromosse.

## 5. L'esito, com'è

- «**Esito: passa**» o «**non passa**», con la tabella per lega, `z` e il numero di leghe.
- Quello che si trova dopo si scrive come «trovato dopo»: non conta come prova.
- Aggiorna *Cosa è già stato provato* (o *Le cose che hanno retto*), *Da fare* e *Stato attuale*,
  e il *Registro delle costanti* col campione, `z` e i fold.
- Se l'idea entra nel motore:
  - una manopola su `window`, nella forma che `cmpEngineDefaults` sa leggere (contratto, punto 9),
    col valore nuovo come default e quello vecchio che torna a prima;
  - il CSV esporta i pezzi da cui la si ricostruisce;
  - poi la skill `nuova-build`.
- All'utente: passa o non passa, il numero che decide e cosa cambia per lui. Senza girarci
  intorno quando non passa.
