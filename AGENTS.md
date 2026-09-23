# AGENTS.md — Scanner Calcio V9.7

Istruzioni per chi (agente o persona) mette mano a questo repository. È la memoria del
progetto: ogni voce è una domanda già chiusa, con i numeri che la chiudono.

**È memoria, non verità corrente.** Un audit del `b23` ha trovato quattro punti in cui
questo file descriveva un motore diverso da quello che gira. Prima di fondare una misura
su una frase di qui, verificala nel sorgente.

**La versione lunga.** Fino al `b38` questo file conteneva anche il racconto completo di
ogni misura (tabelle per fold, stagione e lega, i ragionamenti sbagliati e come sono stati
corretti). È stato asciugato tenendo le conclusioni e i numeri che le reggono; il testo
integrale è in `git show 6ad0415:AGENTS.md`. Se una voce qui sotto non basta, è lì.

**Rimandi dal codice.** I commenti di `scanner.html` e `comparatore.html` citano sezioni di
questo file per titolo (`vedi AGENTS.md, La baseline di coppia`). I titoli citati sono
conservati: cercali qui così come sono scritti nel codice.

## Cos'è

Modello analitico per il calcio servito come pagine statiche. Nessun build, nessun package
manager, nessun test runner: si aprono i file nel browser. Tutto il codice sta in un unico
`<script>` inline per file.

| file | ruolo |
|---|---|
| `index.html` | menu, due link |
| `scanner.html` | **il motore**: analizza una partita (Dixon-Coles + Markov inclinati dall'Elo), mercati, statistiche previste, tabellone |
| `comparatore.html` | **il backtest**: carica `scanner.html` come testo, lo inietta in memoria, lo fa girare su centinaia di partite ed esporta un CSV previsto-vs-reale |
| `leghe.json` | catalogo leghe/stagioni (id PitchAPI) |

Dati da PitchAPI via proxy Cloudflare (`PITCH_BASE` in `scanner.html`). Endpoint per
partita: `/stats`, `/lineups`, `/advanced`, `/events`, tutti attraverso `fetchMatchRaw`,
che li mette in `RAW_CACHE`.

## Regole di lavoro

- **Git.** Branch `claude/*`, mai push diretto su `main`. Commit in italiano, con i numeri
  della misura che giustifica il cambiamento quando c'è. Il «N commit behind» di GitHub
  conta i merge commit delle PR: se `git rev-list --left-right --count origin/main...<branch>`
  dà `N 0`, il branch non ha niente che `main` non abbia.
- **Build corrente: `0905-b38`.** `window.__SCANNER_BUILD` (Scanner), `_bComp`
  (Comparatore) e i due badge `#build-ver` si alzano **insieme, a ogni modifica del
  motore**; se divergono il Comparatore mostra un avviso arancione. Il badge è l'unico modo
  per sapere cosa il browser sta mostrando: non c'è nessuna difesa contro la cache.
- **Stile.** Il JS non ha commenti: la spiegazione va qui, nella sezione che le compete.
  Restano solo marcatori brevi dove una modifica in buona fede rompe tutto in silenzio
  (righe agganciate dal Comparatore, le due convenzioni di `k`, scelte deliberate che
  sembrano errori come `ENS_SCOPE_W` solo sull'1X2 o `GOALS_UNIT_FIX` a 0). Si commenta il
  **controintuitivo**, mai il complicato. Commenti CSS e marcatori `<!-- STEP n -->`
  restano.
- Testi UI in italiano, senza accenti nelle stringhe JS di servizio (il file gira dentro
  `new Function`). Nessuna dipendenza esterna, nessun CDN. File grossi: edit puntuali,
  non riscritture.
- **Il telefono in verticale è il caso principale.** A 390px
  `document.body.scrollWidth − larghezza schermo` deve fare 0. Le tabelle stanno in
  `.tbl-scroll` (lo fa `wrapTables()`); una tabella di **confronto** usa `table-compact` e
  non deve scorrere; i figli di griglia vogliono `min-width:0`.
- **Le manopole per chi fa backtest vanno nel pannello del Comparatore**, non in console:
  il Comparatore si usa anche da telefono.
- **Ogni costante del motore** è stimata dai dati (campione scritto nel *Registro delle
  costanti*), oppure è un a priori dichiarato che si spegne quando i dati bastano, oppure
  è un paracadute di cui è misurato che non morde. Altrimenti è un parametro nascosto.
  Vedi *Le costanti messe a mano*.
- La storia dei perché: messaggi di commit, `git log -S <costante>`, e il codice
  pre-ripulitura (commento in testa a `scanner.html` al commit `cd51a69`).

## Da fare

Dentro ogni gruppo, in ordine di rapporto valore/rischio. Quando chiudi una voce,
spostala in *Cosa è già stato provato* con i numeri, e aggiorna *Stato attuale*.

### 1. Backtest che decidono senza rilanciare il motore

Il CSV esporta già i pezzi da cui si ricompone ogni valore: basta un export recente.

- [ ] **`LEAGUE_HALFLIFE_DAYS`** (oggi 0 = media piatta). È l'ultima ipotesi rimasta sul
  *livello* dei mercati gol: il lambda è inversamente proporzionale alla base di lega, e la
  base è una media piatta su tre stagioni (Premier: 3.041 contro 2.754 veri, −5% sul
  lambda). Il CSV esporta `Unita: media gol casa (piatta)` e `(emivita 106)` fianco a
  fianco. Vedi *I mercati gol: due muri*.
- [ ] **La regola dell'HFA: pavimento o shrinkage.** `ELO_HFA_MODE` da `'clamp'` a
  `'shrink'` (prior 65, `k` 200). Il pavimento 30 morde sul 27.6% delle righe di backtest
  (archivi corti, mai in produzione), ed è lì che si concentra il guadagno sospetto di
  `SHRINK_K`. Sezione CSV `A/B REGOLA DELL HFA`. **Da decidere prima di riaprire lo
  shrinkage.**
- [ ] **Rifare il backtest su tutte e cinque le leghe col motore attuale.** Dopo il `b18`
  è stata rifatta solo la Serie A: Premier, LaLiga, Bundesliga e Ligue 1 hanno misure prese
  con la lega congelata a 1.50/1.20, e la Bundesliga (3.25 gol reali) è dove il bug mordeva
  di più. Primo controllo: `Unita: partite di lega usate` alto, mai 0.

### 2. Aspettano una sesta lega (o le stagioni vecchie di Premier e LaLiga)

Quasi tutto oggi è misurato sulla sola Serie A.

- [ ] **Riconfermare la tabella del `b38`** (`CONF_1X2_TABLE`, `EDGE_BANDS`, soglie del
  pick). La struttura regge in cinque stagioni (lo scarto ordina, la probabilità grezza no);
  i valori delle bande sono di una lega sola.
- [ ] **`ELO_SCALE` e `ELO_1X2_W` rispazzati insieme.** LaLiga da sola dice `S = 1.00`, la
  Serie A 1.60, il pool 1.25. Non alzare `S` per compensare la timidezza del modello: vedi
  *La scala dell'Elo*.
- [ ] **`SHRINK_LAM_K` fra 5 e 8.** Chiude parte del livello dei gol, ma `z = −1.82` e il
  segno si ribalta nel 2022/23. Punta nello stesso verso di `LEAGUE_HALFLIFE_DAYS`.
- [ ] **`GOALS_SOT_W`**: 0.50 in uso, 0.75 e 1.00 indistinguibili (±0.030 di SE).
- [ ] **Lo squilibrio sui tiri in porta**, come per i cartellini: 2.8 sigma, una lega su
  cinque discorde.

### 3. Da misurare, dopo averlo esportato nel CSV

- [ ] **La pendenza dell'Elo** (`penH`/`penA`, ±8% sui lambda): mai misurata, e ora che il
  livello dell'Elo entra dall'inclinazione potrebbe essere ridondante.
- [ ] **Le cinque metriche che nessun backtest ha visto**: `cross`, `thru`, `aer`,
  `seq_time`, `xg_shot`. Il motore le prevede e le mostra, il CSV non le esporta.
- [ ] **`aerials`**: rifare il `k` (0.54, tarato sulla quantità di partita pre-`b19`) e la
  riga `t = +2.4` della Progressione Storica; togliere il doppione `aer`, che legge gli
  stessi due campi.
- [ ] **Le sette metriche col `k` di default 0.50**: `gf`, `direct_speed`, `seq_time`,
  `avg_x`, `cp_regains`, `rec_time`, `xg_sp`. Mai misurate.
- [ ] **`avg_def_x`**: pendenza 0.06, la previsione è scorrelata dal reale. Capire (forse
  la forma attacco × difesa non va bene per una coordinata) o togliere.
- [ ] **`vaep` e `pv`**: rapporto previsto/reale 0.87/0.88 senza spiegazione. Sono le due
  metriche `additivo` non coordinate.

### 4. Lavori nuovi (costano chiamate o sviluppo)

- [ ] **Una media NPxG di lega.** È la radice del disallineamento di unità (attacco e
  difesa sono NPxG divisi per la media *gol*). Finché manca, `SHRINK_K` e `SHRINK_LAM_K`
  fanno due mestieri e nessuna delle due è libera, e `GOALS_UNIT_FIX` resta spenta. Serve
  aggregare `/advanced` su tutta la lega, non sulle due squadre.
- [ ] **Cartellini**: posizione in classifica (costo zero, i punteggi sono già in cache) e
  arbitro (`/v1/matches/{id}` lo espone, profilarlo costa ~15 chiamate).
- [ ] **L'endpoint `/shots`** (`/v1/matches/{id}/shots`, ogni tiro con xG, porta, area,
  situazione, coordinate): la forma della distribuzione dei tiri è il candidato più serio
  per l'*ordinamento* dei mercati gol. Una chiamata in più per partita (+25% sul batch).
- [ ] **Ancoraggio di lega per i falli.** Oggi `MARKET_PER_GOAL.fouls = null`: il rapporto
  coi gol varia del 28% fra leghe.
- [ ] **La card dei risultati esatti come scarto**: mostrare quali punteggi sono più
  probabili *in questa partita che nella partita tipo della lega*. Un 3-1 a 1.8× la sua
  frequenza dice qualcosa, un 1-1 al 12% no. È la parte sopravvissuta dell'idea dello
  «scenario singolo».
- [ ] **Probabili formazioni** (`/lineups` in versione prevista): da valutare.
- [ ] **I parametri interni di Markov**: verificati solo gli invarianti.

### 5. UI e pulizie

- [ ] **Doppie chance e gol con confidence**: la tabella è confusa, e sui gol poggia su
  probabilità che discriminano poco.
- [ ] **La card «Sopravvivenza (Goal Timing)»** è `1 − exp(−λ_totale × quota_di_tempo)`, con
  la quota presa dalla distribuzione dei minuti dei gol in sei fasce da 15' (uniforme sotto i
  30 gol). È corretta, ma il nome promette un'analisi di sopravvivenza che non fa.
- [ ] **`RESID_GAMMA` da 0.678 a 0.360**, o rimisurarlo. Non sposta probabilità
  (`RESID_ALPHA = 0`), ma la sezione CSV *A/B CORREZIONE RESIDUALE* è calcolata con la
  scala che il `b5` ha dichiarato sbagliata.
- [ ] `cmpDcPredict` (il predittore di riserva del Comparatore) tratta `vaep_def`/`pv_def`
  con la forma moltiplicativa: sulle righe `riserva-*` quei due numeri non valgono.
- [ ] Facoltativo: una difesa contro la cache del browser (`no-store` o query string).

### Mai verificato

Non sono bug noti, sono buchi di copertura: se contengono un errore, nessun controllo fatto
finora lo vedrebbe.

- Che ogni numero a schermo sia quello calcolato dal motore (si è verificata solo la
  presenza degli id).
- I casi numerici estremi: lambda molto alti o bassi, squadre con pochissime partite, leghe
  con meno di 30 partite in archivio.
- Il comportamento quando `/advanced` c'è solo su parte delle partite di una squadra.

## Stato attuale (`b38`)

**1X2.** Pick azzeccato ~52% contro ~40–43% del «gioca sempre in casa», fermo da venti
build. Il valore sta nella **fascia alta**, che la card mostra con la tabella misurata
(1882 partite di Serie A, motore post-`b30`):

| soglia sul pick | partite | quota del calendario | azzecca | ±2se |
|---|---|---|---|---|
| ≥50% | 823 | 44% | 62.0% | 3.4 |
| ≥55% | 559 | 30% | 65.3% | 4.0 |
| ≥60% | 339 | 18% | 71.1% | 4.9 |
| ≥65% | 179 | 10% | 74.3% | 6.5 |
| ≥70% | 81 | 4% | 79.0% | 9.0 |

**La selezione vale più dell'accuratezza.** Prima di aggiungere una feature, chiedersi se
il segnale non sia già nell'output, solo mal etichettato.

**Tabellone.** Ordina per **scarto dal base rate della lega**. Sulla proposta migliore di
ogni partita rende +16.7 punti sopra il giocarla alla cieca (walk-forward +18.8), contro
+11.7 del vecchio ordinamento per probabilità. Vedi *Il tabellone ordinava per la colonna
sbagliata*.

**Calibrazione 1X2.** Probabilità ancora un po' timide: pendenza 1.199 (1 contro 2) e 1.125
(tre esiti) sul prodotto finito. La timidezza sta nel modello (`lgModel` 1.443, `z = +4.81`),
non nell'Elo (1.092). Nessuna manopola disponibile la chiude senza costare sui gol.

**Mercati gol.** Due muri distinti. *Ordinamento*: AUC dell'Over 2.5 fra 0.51 e 0.60 a
seconda del campione, e l'unica feature che l'ha spostato è `sum_sot`. *Livello*: l'Over
2.5 previsto sta ~2.6 punti sotto il reale; resta un'ipotesi (`LEAGUE_HALFLIFE_DAYS`) più la
radice (la media NPxG di lega).

**Mercati sui numeri.** Discriminano meglio dei gol: cartellini ~0.59 di AUC, tiri in porta
~0.56, corner ~0.53. Dal `b38` sono nel tabellone.

**Pareggio.** Non si prevede: `pX` ha AUC 0.487. È calibrato in media e piatto a fasce, e
trascina con sé il `12`.

**Campioni su cui si è misurato:**

| campione | partite | note |
|---|---|---|
| Serie A 2021/22 → 2025/26 | 1882 | motore post-`b30`; `/advanced` assente sulle tre stagioni più vecchie |
| Serie A + Premier + LaLiga 2025/26 | 1133 | post-`b18`, con `/advanced` |
| le tre sopra + Bundesliga + Ligue 1 2025/26 | 1743 | export `b14`, **pre-`b18`**: lega congelata a 1.50/1.20 |

Bundesliga e Ligue 1 non sono mai state usate per tarare niente: sono il banco di prova più
pulito. Se le usi per tarare, scrivilo qui. Meno di due leghe non bastano a spedire una
costante: è l'errore che ha prodotto quattro falsi positivi di fila.

### Le otto cose che più facilmente fanno perdere una giornata

1. `_base` **non** è una media di lega: è una media della **coppia**, e correla 0.84 col
   numeratore. → *La baseline di coppia*.
2. L'**AUC dei mercati gol non si legge mai aggregata** fra leghe: i base rate diversi la
   gonfiano (Over 2.5: Serie A 45.8%, Premier 55.0%).
3. Il CSV scrive le probabilità a **una cifra decimale**: ±0.05 punti su ogni Brier, e i
   confronti con una soglia sbagliano al confine.
4. Il lambda è **inversamente proporzionale** alla media gol di lega. Prima di dedurre una
   direzione, scrivi la formula.
5. In `predictStat` **`k` alto = MENO shrinkage**; in `SHRINK_K` e `SHRINK_LAM_K` è
   l'opposto. → *Convenzioni del motore*.
6. Lo scope `role` è un **sottoinsieme** di `overall`: con `limit = 15` sono 8 partite, non
   15. → *Il campione di ruolo è un sottoinsieme*.
7. `SHRINK_LAM_K` **non tocca l'1X2**: sta solo sui lambda di ruolo, e `ENS_SCOPE_W = 1`
   manda l'1X2 su quelli completi. Chi la ritara per l'1X2 sposta i **mercati gol**.
8. Una probabilità alta **non è una proposta**: `12` al 73% è il base rate della lega.
   Conta lo **scarto dal base rate**.

## Come funziona il motore

**La catena.** `aggregaTeam` scarica lo storico di una squadra (`history-limit`, default
15, dentro una finestra di 500 giorni) e per ogni partita estrae quanto la squadra ha
**prodotto** e **concesso**. `calcFeatures` trasforma ogni serie in
`{avg_3, avg_5, avg_10, avg_15, avg_tot, decay, std, nValid}`; `decay` (emivita 106 giorni,
`_timeDecayDates`) è il valore usato quasi ovunque. Dai lambda esce **una sola matrice
Dixon-Coles**, e da quella tutti i mercati gol: 1X2, doppie chance, GG, Over/Under,
multigol, risultati esatti, handicap asiatico. Una correzione ai lambda li muove tutti
insieme. Fuori dalla matrice c'è solo `calcAdv` (corner, tiri in porta, cartellini, falli),
con lambda propri e binomiale negativa.

**Due scope.** `overall` sono le ultime N partite; `role` sono quelle **fra queste** giocate
nel proprio ruolo (in casa per chi gioca in casa). I lambda di ruolo normalizzano sulla
media della propria sede (`LG.avgH`/`LG.avgA`): **non va aggiunto nessun moltiplicatore di
vantaggio campo**, ci sarebbe due volte.

**I lambda.** `lambda = media_sede × forza_attacco × debolezza_difesa`, dove attacco e
difesa sono NPxG divisi per la media **gol** di lega, più la componente rigori
`xG − NPxG`, più la pendenza dell'Elo (±8%, mai verificata). `rho` lo stima `estimateRho`
dalle frequenze reali di 0-0/1-0/0-1/1-1 della lega. Poi, in ordine:

1. **Shrinkage**, forma `n/(n+k)`: `SHRINK_K = 4` porta attacco e difesa verso la media di
   lega; `SHRINK_LAM_K = 3` porta i lambda **di ruolo** verso la media di lega quando le
   partite di ruolo sono poche.
2. **La seconda stima dai tiri in porta** (`goalsSotCorrection`): vedi *I gol*.
3. **L'inclinazione dall'Elo** (`eloTiltLambdas`): vedi *L'Elo nell'1X2*. Cambia il rapporto
   fra i lambda tenendo il totale identico al bit.

**L'ensemble 1X2:**

```
RUOLO    = 0.70·probsRole + 0.30·mk_ro        lambda casa/trasferta
COMPLETO = 0.70·probsOver + 0.30·mk_ov        lambda su tutte le partite
core     = (1 − ENS_SCOPE_W)·RUOLO + ENS_SCOPE_W·COMPLETO      ENS_SCOPE_W = 1
finale   = (1 − ENS_W.ol)·core + ENS_W.ol·probsOL               ENS_W.ol = 0
```

**Asimmetria deliberata**: `ENS_SCOPE_W = 1` vale **solo per l'1X2**. GG, Over/Under,
multigol, risultati esatti e handicap escono dalla matrice **di ruolo** (`dcMat = dcRole`),
perché sui gol il completo peggiora la calibrazione ovunque. Non «sistemarlo».

- **Ordered Logit**: `y* = OL_BETA·(olH − olA)` tagliato da due soglie, con
  `ol = 0.7·NPxG + 0.3·NPxGA avversario` di ruolo. Calcolato e mostrato ma **peso 0**: va
  tenuto giusto lo stesso, perché è a schermo e nel prompt.
- **KNN**: calcolato e mostrato come riferimento tattico, **non entra nell'ensemble**. Non
  descriverlo come se ci fosse.
- **Markov** (`markovFlow`, rate dipendenti dal punteggio): da solo fa logloss 1.0091,
  leggermente meglio del Dixon-Coles (1.0098). Verificati solo gli invarianti.

**Tre quarti dell'1X2 non passano dal modello.** Con `ELO_1X2_W = 0.75` si ha
`lgTarget = 0.25·lgModel + 0.75·lgElo`: qualunque correzione lato Dixon-Coles arriva
all'1X2 divisa per quattro.

### La confidence

È la probabilità del pick **ricalibrata sull'hit reale**, non l'accordo fra i modelli
(l'accordo correlava −0.007 con l'azzeccare).

- **1X2**: `CONF_1X2_TABLE`, tabella empirica per fascia (`b38`, 1882 partite). Con
  `window.CONF_1X2_MODE = 'retta'` si torna alla vecchia `6.26 + 0.880·p`, che sottostimava
  fino a 8 punti dove si decide (a 62 mostrava 61, il vero era 67.5).
- **Mercati binari**: retta `−5.06 + 1.091·p`, rimisurata nel `b38` su 22.584 proposte:
  sbaglia al massimo di 2.4 punti. Non si tocca.

### Il tabellone

`renderVerdetti` trasforma ogni coppia partita-mercato in una proposta e la ordina per
**scarto** = probabilità − base rate. Il base rate lo calcola
`leagueBaseRates(leagueId, targetTimeMs)` sull'archivio della lega stessa, con lo stesso
`_isPast` del motore e a costo zero chiamate (minimo 200 partite). Per corner, tiri e
gialli il base rate è il riferimento ancorato ai gol di lega (`MARKET_PER_GOAL ×
(avgH+avgA)`) passato per la stessa binomiale negativa. Fasce (`EDGE_BANDS`): ≥20 FORTE,
≥10 GIOCABILE, ≥5 MARGINALE. Ogni riga dice su quanti casi è misurato il suo hit.

### Le statistiche previste: `predictStat`

`media × sh(mio/media) × sh(concesso_avversario/media)`, con `sh(r) = 1 + k·(r − 1)` e `k`
da `STAT_SHRINK_TABLE` (default 0.50). La media è `_base`, cioè **della coppia**, non della
lega. Se manca il concesso o la media, torna la media semplice (le leghe minori spesso non
hanno `/advanced`).

`STAT_SHRINK_TABLE`, rifatta nel `b5` su 1133 partite di tre leghe col metodo della
pendenza (`k_nuovo = k × pendenza` di `reale ~ previsto`), 51 voci:

| famiglia | metriche e `k` |
|---|---|
| gol e tiri | `npxg` 0.54 · `xg` 0.50 · `sot` 0.50 · `xgot` 0.46 · `cor` 0.40 |
| possesso e territorio | `poss` 0.76 · `tch_box` 0.61 · `field_tilt` 0.41 · `ppda` 0.35 · `f3_entries` 0.29 · `avg_def_x` 0.10 |
| creazione | `sca` 0.34 · `sca_live` 0.41 · `gca` 0.31 · `xag` 0.24 · `chances_created` 0.39 · `key_passes` 0.39 |
| breakdown SCA | `sca_dead` 0.18 · `sca_takeon` 0.16 · `sca_foul` 0.11 · `sca_shot` 0.10 |
| passaggi | `passes` 0.54 · `prog_passes` 0.47 · `passes_box` 0.44 · `prog_pass_dist` 0.36 · `switches` 0.28 · `assists` 0.16 · `second_assists` 0.17 |
| conduzioni | `carries` 0.49 · `prog_carry_dist` 0.50 · `carry_dist` 0.48 · `prog_carries` 0.48 · `carries_f3` 0.38 · `take_ons` 0.37 · `carries_box` 0.55 |
| difesa | `aerials` 0.54 · `ppda_num` 0.53 · `ppda_den` 0.29 · `clearances` 0.30 · `tackles` 0.23 · `interceptions` 0.23 · `duels_won` 0.22 · `blocks` 0.20 · `challenges` 0.14 · `yel` 0.23 · `fouls` 0.48 |
| possession value | `xt` 0.40 · `vaep_off` 0.23 · `pv_off` 0.21 · `vaep` 0.18 · `pv` 0.15 |

Leghe discordi (spread delle pendenze > 0.35, valore tenuto prudente): `fouls`, `vaep_off`,
`pv_off`, `assists`. Il Comparatore ha una seconda tabella, `CMP_DC_SHRINK_TABLE`, usata
solo come riserva per motori pre-`b4`: non copiare valori dall'una all'altra.

**Il tetto.** Su 2266 osservazioni squadra-partita, 26 metriche su 47 sono già al 90% o più
del tetto teorico `sqrt(ICC)` di qualunque modello pre-partita (`npxg`: tetto 0.369,
correlazione attuale 0.393). Prevedere meglio le stats non è dove sta il valore.

### Aggiungere una metrica: `ADV_SPEC`

Una riga `[chiave, getter, tipo]`, per esempio `['tackles', m => m.defending?.tackles,
'volume']`. Ne discendono da sole estrazione (prodotta da `myAdv`, concessa da `oppAdv`),
serie, lista `OPT`, `calcFeatures`, `STAT_PAIRS`, la mappa `pair` di `_base` e `STAT_TYPE`.

Poi, a mano:
- aggiungerla anche in `CMP_NEW_SPEC` e in `NEWK` dell'export del Comparatore, **con lo
  stesso campo**, altrimenti è prevista ma mai verificata (controllo E);
- verificare che `Object.keys(STAT_PAIRS)` la contenga: senza un «concesso» il suo `k` non
  viene mai usato, in silenzio (era il caso di `f3_entries`);
- verificare che il reale di casa e quello di trasferta non siano identici: se lo sono è una
  quantità della partita, non di squadra (controllo D).

Oggi `ADV_SPEC` ha 31 voci e `CMP_NEW_SPEC` 34: le tre in più (`vaep_def`, `pv_def`,
`sca_def`) sono uscite dal motore nel `b7` ma il CSV ne esporta ancora il reale. Otto
metriche senza un concesso diretto sono agganciate in `ORPHAN_PAIRS`.

**Tipi (`STAT_TYPE`).** `volume` (default) = forma moltiplicativa, per conteggi. `additivo` =
`lg + k·((mio − lg) + (concesso − lg))`, per i valori che attraversano lo zero (`vaep`, `pv`:
il rapporto fra due negativi inverte il segno) e per le coordinate (`avg_x`, `avg_def_x`).
Per le additive i guardiani sono su `isFinite`, non sul segno. `ppda` resta `volume`, con
`ppda_num` e `ppda_den` sciolti accanto.

### I mercati sui numeri: `calcAdv`

```
riferimento = MARKET_PER_GOAL[m] × (LG.avgH + LG.avgA)                   costante dentro la lega
lambda      = riferimento
            + MARKET_BASE_SHRINK[m] × (2·lg − riferimento)                livello della coppia
            + (grezzo − 2·lg)                                             attacco vs difesa, k = MARKET_SHRINK_K
```

`grezzo` è la somma dei due `predictStat`, `lg` la media dei due `_base`. Lo scope è `role` se
**entrambe** le squadre hanno almeno 3 partite nel ruolo, altrimenti `overall`. Sui gialli
si aggiunge lo squilibrio (vedi *Lo squilibrio e i cartellini*). La dispersione (`negBinK`)
restringe l'eccesso osservato verso Poisson col peso `ex²/(ex²+2/n)`, senza pavimenti, e
torna `Infinity` sui campioni non sovradispersi: i tiri in porta non lo sono (var/media
8.36/8.38), i corner poco (`k` di lega 56).

Quanto aspettarsi: anche conoscendo il lambda esatto di ogni partita l'AUC sui corner non
supererebbe ~0.68, e due stime costruite su metà della storia ciascuna correlano appena +0.26.
Il segnale c'è, ma è piccolo.

### Scanner in uso

- `nuovaPartita()` rimette la card di setup senza svuotare `globalLeagueMatchesCache` né
  `RAW_CACHE`: la prima partita costa 239 chiamate, una con una squadra già vista 108, una
  con tutte e due già viste 0. Ricaricare la pagina butta tutto.
- Il database di lega va in `localStorage` (chiave lega+stagione, scadenza 24 ore).
  `RAW_CACHE` no: sono decine di MB.
- **Progressione Storica**: le medie brevi non prevedono mai meglio della lunga (47 metriche
  su 47). Uno scostamento recente **persiste** solo sui volumi strutturali (`prog_carries`
  t=+3.5, `switches` +2.9, `prog_carry_dist` +2.7, `tackles` +2.7, `ppda_den` +2.5,
  `carries_box` +2.4, `f3_entries` +2.2, `carry_dist` +2.0) e si **inverte** sulla creazione
  (`sca` −2.2, `sca_live` −2.1, `sca_shot` −2.0). La card mostra sei delle persistenti.

### L'ambito di ogni box

Ogni card dice su quale campione poggia (`GENERALE`, `RUOLO · casa/trasferta`, o entrambi),
con la legenda in cima alla sezione *PERCHÉ*. Quasi tutte le card *PERCHÉ* usano
`_mean(team.overall.vals.*)`: media semplice, non decaduta, non di ruolo. Il box di
confronto ruolo/generale mostra la numerosità di ciascuno e diventa rosso sotto le 6 partite
di ruolo. La spunta ✓ sulla colonna usata dall'1X2 è calcolata da `ENS_SCOPE_W`, non scritta a
mano. Regola: **due numeri affiancati da un `vs` devono venire dallo stesso campione.**

### Il mega-prompt

Porta il tabellone e i verdetti misurati e dice all'LLM di non ridiscuterli: il suo compito è
spiegare perché le statistiche di questa partita portano lì. Tutti i numeri escono dalle
stesse variabili dello schermo (un controllo verifica che `ensemble 1+X` coincida col
tabellone). Sezione *COSA NON FARE*: niente risultati esatti, niente
«certo/sicuro/esplosione/goleada», non mescolare ruolo e generale nella stessa frase. Quando
Elo e modello distano 10+ punti, card e prompt dicono che il verdetto lo decide l'Elo; quando
il clamp dell'HFA ha morso, dicono che è un limite, non una misura. Le narrative riportano lo
scarto misurato e si fermano lì.

## Politica sui valori mancanti

- **Conteggi** (big chances, cross, filtranti, tocchi in area, recuperi): molte API omettono
  la chiave quando vale zero. Se la risposta è arrivata ma la chiave manca → **0**
  (`zeroIf(..., statsOk)`), ma **solo dopo** aver provato tutte le fonti di riserva.
- **Rapporti, percentuali, distanze, xG**: uno 0 è impossibile. Se manca, la partita **esce
  da quella media** (`keepNull`).
- Se `/advanced` fallisce, niente viene zero-fillato: quella partita non porta metriche
  avanzate.
- I metrici opzionali si inseriscono **sempre**, anche come `null` (lista `OPT`): saltarli
  disallinea gli indici dalle date.
- La tabella «Copertura Dati API» distingue una metrica assente (0%) da una con zeri
  legittimi. `N/D` solo a copertura zero.

## Convenzioni del motore

**Le manopole di smorzamento hanno tre forme.** Leggi la formula, non il nome:

| costante | formula | verso |
|---|---|---|
| `STAT_SHRINK_TABLE`, `MARKET_SHRINK_K`, `CMP_DC_SHRINK_TABLE` | `1 + k(r−1)` | **k alto = meno** shrinkage |
| `SHRINK_K`, `SHRINK_LAM_K`, `ELO_HFA_K` | `n/(n+k)` | **k alto = più** shrinkage |
| `MARKET_BASE_SHRINK` | `ref + c(x−ref)` | **c alto = meno** restringimento (`c = 1` non fa niente) |
| `GOALS_SOT_W`, `ELO_1X2_W` | `(1−w)·a + w·b` | **w alto = più** peso al secondo termine |

- **Lo scope `role` contiene già il vantaggio campo.** Ogni modello che usa numeri di ruolo:
  misurare la **media** della variabile. Se non è centrata su zero, una costante simmetrica
  che la accompagna non può essere giusta (l'Ordered Logit aveva media +0.196 e soglie
  centrate a −0.250: +6.8 punti di bias sull'`1`).
- **Il time decay** (emivita 106) è replicato nel Comparatore in `cmpTimeDecayWeighted`: se
  lo cambi da una parte, cambialo dall'altra.
- **Niente leakage.** Ogni filtro temporale passa da `_isPast(timeUtc, targetTimeMs,
  targetDay)`: confronto sulla **data in forma di stringa** in AND col timestamp, taglio a
  `T00:00:00Z` del giorno della partita, giorno bersaglio escluso per intero. La usano
  `aggregaTeam`, i due cicli di `buildGlobalElo`, `computeLeagueParams`, `estimateRho`,
  `leagueBaseRates` e il Comparatore (via `exposeNames`). Qualunque aggregazione nuova passa
  da lì.
- **Le finestre sono asimmetriche, apposta.** `aggregaTeam` guarda indietro 500 giorni;
  Elo, media gol di lega e `rho` usano tutte e tre le stagioni caricate, senza limite
  inferiore e (per la lega) senza decadimento.
- **Chi consuma una stima con una calibrazione propria passa un `k` esplicito.** L'Ordered
  Logit e `applyResidualCorrection` chiamano `predictStat(..., STAT_SHRINK_LEGACY)` (0.35):
  ritarare `STAT_SHRINK_TABLE` non deve spostare in silenzio l'1X2.
- **La correzione residuale è spenta ma misura sempre.** `applyResidualCorrection` espone
  `sig`, `edge`, `resid` e le probabilità pre-correzione anche con `RESID_ALPHA = 0`: tenere
  separati i due percorsi (misura sempre, applica solo se alpha > 0).
- **La provenienza delle costanti sta qui**, nel *Registro delle costanti*, insieme alla
  **forma della variabile** su cui la stima è stata fatta. Se ne cambi una, aggiorna la riga;
  se ne aggiungi una, scrivila prima di committare.

## Il contratto Scanner ↔ Comparatore

**È la parte che si rompe in silenzio.** Il Comparatore non importa lo Scanner: ne legge il
testo, lo modifica con delle regex e lo esegue con `new Function`. Dipende quindi dalla
**forma testuale** di alcune righe.

1. **La cache condivisa** resta dichiarata esattamente `let globalLeagueMatchesCache = [];`.
   Cambiando `let`, nome o posizione, il batch smette di popolare le partite.
2. **I nomi delle funzioni-motore** sono chiamati per nome (`exposeNames` in
   `loadEngineFromText`), ventidue: `apiCall`, `avviaScanner`, `aggregaTeam`,
   `extractSafeStat`, `buildGlobalElo`, `calcDCMatrix`, `markovFlow`, `probsFromMatrix`,
   `estimateRho`, `calculateRho`, `getSimilarMatches`, `computeLeagueParams`, `multigoal`,
   `asianHandicapMat`, `negBinCDF`, `negBinK`, `poisson`, `expectedPoints`, `loadLegheJson`,
   `fetchMatchRaw`, `predictStat`, `_isPast`. Il contenuto è libero, i nomi no.
3. **L'hook** si aggancia alla riga della confidence,
   `/(const\s+confidence\s*=\s*Math\.round\([^;]*;)/`. Non riscriverla e non citarla
   testualmente altrove nel file. Tutto ciò che l'hook legge va prodotto **prima**:
   `__PRED_STATS`, `__PRED_DEBUG`, `__RESID_DEBUG`, `__GOALS_DEBUG`, `__ELO_DEBUG`,
   `__ELO_DEBUG_OVER`, `__UNIT_DEBUG`, `__ENS_DEBUG`, `__SCOPE_DEBUG`, `m1/mX/m2`, `probsRole`,
   `probsOver`, `probsOL`, `mk_ro`, `mk_ov`, `dcMat`, `lamH_mix/lamA_mix`,
   `lamH_over/lamA_over`. Una variabile dichiarata dopo finisce a `null` senza errori (una
   colonna di `N/D` nel CSV). Aggancio di riserva: le tre righe `const m1 = …; const mX = …;
   const m2 = …;`; se il log dice «Hook iniettato dopo l'ensemble (fallback)», qualcosa nel
   motore è cambiato.
4. **`RAW_CACHE[id] = res;`** viene riscritta per non memorizzare le risposte vuote. Se
   cambi quella riga la patch smette di applicarsi, e il log lo dice appena.
5. **Le tabelle di estrazione sono in due copie**: `ADV_SPEC` (Scanner) e `CMP_NEW_SPEC` /
   `CMP_ADV_KEYS` (Comparatore) devono leggere lo stesso campo per la stessa chiave.
   Controllo E dopo ogni getter toccato.
6. **La build** coincide nei due file (vedi *Regole di lavoro*).

**Come gira un batch.** `cmpRunMatch` mette la lega nel DOM del motore (creando l'`<option>`
se manca e verificando che abbia attecchito), ricopia `history-limit`, e chiama
`avviaScanner()` **tre volte**, una per ogni valore di `CMP_K_LIST = [4, 2, 1]`, per la
sezione *A/B SHRINKAGE*. Il CSV e le colonne principali sono il **primo** giro, quindi
`CMP_K_LIST[0]` deve restare uguale al `SHRINK_K` del motore. I `window.__*_DEBUG` restano
quelli dell'**ultimo** giro: per qualunque confronto si legge il debug dentro l'oggetto
risultato (`R.eloDebugOver`, `R.scopeDebug`, …). Se `__UNIT_DEBUG.lgN` è 0 dopo il primo
giro, `cmpRunMatch` si ferma: la lega non è arrivata al motore.

**Le manopole che possono far divergere Comparatore e Scanner**, tutte dichiarate nel log
all'iniezione con un verdetto (verde ai default, arancione nominando la manopola). I default
si leggono **dal sorgente iniettato**, non da `window`, perché le righe del motore
preservano un valore già impostato.

| manopola | default | chi la sposta |
|---|---|---|
| `SHRINK_K` | 4 | `CMP_K_LIST[0]`, se qualcuno riordina la lista |
| `SHRINK_LAM_K` | 3 | letta dal sorgente (fino al `b34` era cablata a mano) |
| `ELO_SCALE` | 1.25 | il campo nel pannello |
| `ROLE_SCOPE_INDEPENDENT` | 0 | la casella nel pannello |
| `history-limit` | 15 | `cmp-history-limit`: la più facile da spostare senza pensarci |

Le prime due, se divergono, sono errori; le ultime tre sono scelte legittime per gli A/B, e
l'unica difesa è dichiararle.

## Il Comparatore stampa come lo Scanner

Misurato passando dal vero `cmpRunMatch` (`b33`): lo Scanner con `caricaSquadreLega()` +
`avviaScanner()`, il Comparatore con `loadEngineFromText()` + `cmpRunMatch()`, stesso
campionato sintetico. **16 campi su 16 identici**, i lambda fino all'ultima cifra in virgola
mobile. Da rifare quando si tocca il percorso di iniezione.

**Il leakage è chiuso, e il controllo ha potere.** Il risultato di una partita entra nel
motore da **due strade**: il payload (`/stats`, `/advanced` → `aggregaTeam`) e il punteggio
(`score_home`/`score_away` → lega, `rho`, Elo, cartellini). Drogando la partita bersaglio o
un'altra dello stesso giorno, su ciascuna strada, la previsione resta **identica al bit**;
drogando una partita del giorno prima **cambia** (0.5276 → 0.5846 sul payload, → 0.5354 sul
punteggio). Rifatto anche con tutti gli orari appiattiti a `T00:00:00Z`: stesso esito.

### L'orario non è affidabile

`new Date("2025-04-30T00:00:00")`, **senza** la `Z`, è ora locale: in un browser a
Europe/Rome cade due ore prima del taglio, e la partita da prevedere entrava nel proprio
storico (l'`1` da 0.528 a 0.557). Dal `b24` il taglio confronta la **data come stringa**
(`slice(0,10)`, immune a fuso e formato) in AND col timestamp. Il Comparatore segnala al
caricamento quante partite hanno `time_utc` senza fuso: il taglio regge lo stesso, ma ogni
altro conto che usi l'orario di quelle righe è sospetto.

**Arretrare il taglio a `x-1` non serve.** Le due squadre in campo non possono aver giocato
il giorno prima, quindi il loro storico non ci guadagna niente; si butterebbero in media 2.18
partite di lega per previsione (fino a 8). E per Serie A, Premier e LaLiga la data UTC non
può scivolare (primo calcio d'inizio 10:30Z, ultimo 19:00Z). Diventerebbe utile solo se
l'API cominciasse a restituire la data *locale* di una lega a ovest di Greenwich.

## Registro delle costanti

| costante | valore | tipo | da dove viene |
|---|---|---|---|
| `ENS_W` dc / mk / ol | 0.70 / 0.30 / 0.00 | stimata `b20` | griglia leave-one-league-out su 1743 partite, OL a 0 in 4 fold su 5. Vale −0.0013 di logloss, `z = −2.03`: pulizia più che guadagno |
| `ENS_SCOPE_W` | 1 | stimata `b21` | 1133 partite, logloss 1.0113 → 1.0071, monotono in 3 leghe su 3, `z = −3.96`, fuori campione 1.0 in 3 fold su 3. Solo 1X2 |
| `ELO_1X2_W` | 0.75 | stimata `b14`, riconfermata `b35` | 5 leghe, 1743 partite: w 0 → 0.50 a +5.02σ, ottimo a 0.75. `b35` (Serie A 1882, ramo giusto): ottimo interno piatto fra 0.50 e 0.75, estremi peggiori a 2σ |
| `ELO_SCALE` | 1.25 | stimata `b30`, confermata `b35` | pendenza di calibrazione dell'Elo 1.235 (`z = 3.13`); fuori campione 1.20–1.35 in 7 fold su 7; `b35`: 1.25 batte 1.00 a `z = 3.92`. Applicata alla sola differenza di rating, non all'HFA |
| `ELO_GAP_THRESHOLD` / `TAU` / `ASY` | 45 / 360 / 0.9 | `τ` scelto dove smette di costare (`b30`) | la logloss cala in modo monotono fino a τ infinito; da 360 in su il guadagno residuo è 0.0005. Non misurato sulla pausa estiva (33 partite) |
| K dell'Elo | 30 sotto le 15 partite, poi 20 | a mano, verificato `b30` | alzare K porta la pendenza a 1 ma peggiora la logloss oltre 40/28: si tara la conversione, non il rating |
| clamp dell'HFA | [30, 100], con ≥50 partite | **paracadute che morde** | 27.6% delle righe di backtest (archivio < 600 partite), 0% con ≥900 (produzione). Alternativa esposta: `ELO_HFA_MODE = 'shrink'`, `ELO_HFA_PRIOR` 65, `ELO_HFA_K` 200 |
| `ELO_TILT_MAX` | 0.60 | paracadute misurato | inclinazione massima osservata 0.215 |
| `SHRINK_K` | 4 | misurata `b35`–`b37` | 12 e 28 peggiori a 5σ; sotto 4 migliora l'1X2 (−0.0016, `z = −3.03`) ma i gol pagano +0.0056 |
| `SHRINK_LAM_K` | 3 | a mano, misurata `b37` | ottimo del Brier Over fra 5 e 8, ma `z = −1.82` e segno ribaltato nel 2022/23 |
| `GOALS_SOT_W` | 0.50 | stimata `b12`, confermata `b14` | AUC Over 2.5 da 0.554/0.495/0.501 a 0.572/0.514/0.521; cinque leghe +2.18σ |
| `SOT_PER_GOAL` | 3.25 | misurata | LaLiga 3.19, Premier 3.04, Serie A 3.33. Tocca solo il livello |
| `GOALS_SOT_CAP` | 0.20 | paracadute misurato | morde nello 0.18% |
| `OL_BETA` / `T1` / `T2` | 2.056 / −0.475 / +0.671 | stimata `b20` | massima verosimiglianza su 1743 partite, leave-one-league-out, sulla variabile di **ruolo** (media +0.196). Peso 0 |
| `CARDS_ELO_B` / cap | −0.0035 / ±30% | stimata `b16` | 1743 partite, 5 leghe, −5.8σ, omogeneo (p = 0.914), ottimo interno del Brier |
| `MARKET_SHRINK_K` | cor 0.07 · sot 0.30 · yel 0.10 · fouls 0.15 | stimata `b12` | Brier su 1133 partite, tre leghe |
| `MARKET_BASE_SHRINK` | cor 0.50 · sot 0.55 · yel 0.75 · fouls 1.00 | stimata `b12`, `sot` ritoccata `b15` | affidabilità della baseline di coppia; `sot` 0.75 → 0.55 al minimo del Brier |
| `MARKET_PER_GOAL` | cor 3.61 · sot 3.20 · yel 1.48 · fouls null | misurata | variazione fra leghe: corner 1.1%, tiri 8.7%, gialli 14.7%, falli 28% (quindi null) |
| `STAT_SHRINK_TABLE` | 51 voci, default 0.50 | stimata `b5` | vedi *Le statistiche previste* |
| `STAT_SHRINK_LEGACY` | 0.35 | storica | il `k` a cui valgono OL e correzione residuale |
| `CONF_1X2_TABLE` | 8 fasce | stimata `b38` | resa del pick per fascia, 1882 partite di Serie A post-`b30` |
| retta dei mercati binari | −5.06 + 1.091·p | stimata, riconfermata `b38` | 22.584 proposte, errore massimo 2.4 punti |
| `EDGE_BANDS` | ≥20 / ≥10 / ≥5 | stimata `b38` | 28.230 proposte: +24.6 / +14.8 / +6.3 punti, monotono, segno concorde in 5 stagioni su 5 |
| minimo di `leagueBaseRates` | 200 partite | paracadute misurato `b38` | guadagno piatto fra 50 e 500; in produzione arrivano 900+ partite |
| emivita | 106 giorni | a mano | uguale nei due file |
| a priori di lega | avgH 1.50 / avgA 1.20 sotto 30 partite; `rho` −0.11 sotto 100 | a priori | si spengono da soli; `lgN` dice se sono attivi |
| `RESID_ALPHA` | 0 | spenta per misura `b3`/`b5` | residuo contro errore dell'ensemble: +0.015 su 716 partite |
| `RESID_GAMMA` | 0.678 | **sbagliata** | il `b5` ha misurato 0.360: vedi *Da fare* |
| `GOALS_UNIT_FIX` | 0 | spenta per misura `b22` | vedi *Il disallineamento di unita nel lambda* |
| `LEAGUE_HALFLIFE_DAYS` | 0 | non stimata, dichiarata | un backtest decide: vedi *Da fare* |
| `ROLE_SCOPE_INDEPENDENT` | 0 | misurata `b26` | A/B appaiato, 1133 partite: 0.0002 di logloss |
| `CMP_K_LIST` (Comparatore) | [4, 2, 1] | strumento `b36` | il primo valore deve restare il `SHRINK_K` del motore |

## Le costanti messe a mano

In statistica le costanti fissate a priori sono legittime solo di tre tipi. Classificala
prima di scriverla nel codice.

- **Tipo 1, il numero è la procedura.** `n/(n+k)` è empirical Bayes (James-Stein), e il `k`
  va stimato dai dati. L'emivita è una media mobile esponenziale. La regressione dell'Elo
  dopo l'inattività è un'approssimazione grezza di Glicko. La binomiale negativa è testo da
  manuale.
- **Tipo 2, l'a priori con la data di scadenza.** `avgH 1.50 / avgA 1.20` sotto le 30
  partite, `rho −0.11` sotto le 100: si spengono appena i dati bastano. Devono però essere
  **osservabili** (vedi *La lega che non arrivava mai*).
- **Tipo 3, il paracadute, legittimo finché è inerte.** Un cap non è un parametro finché non
  morde; quando morde **diventa** il modello, in silenzio. Va misurato quanto morde e
  mostrato il grezzo accanto al valore usato (controllo P). Il clamp sull'HFA è l'unico che
  morde davvero.

**Fuori classifica**, trovati nel motore e tolti: `Math.max(2, ...)` in `negBinK`; la media
geometrica in `calcAdv`, cioè shrinkage zero deciso non scrivendolo (pendenza 0.47); e
`_base` chiamata «baseline di lega» quando è di coppia. Il valore più pericoloso non è quello
scritto male, è quello **non scritto**, o scritto con il nome sbagliato.

**Una stima invecchia quando cambia ciò che sta a monte.** `OL_BETA` e soglie erano stimate
bene ed erano sbagliate, perché la loro variabile era passata allo scope `role`. Accanto al
campione va scritta la forma della variabile.

**La forma canonica** per aggiungere un grado di libertà al motore:

1. La costante è esposta su `window` con un default che **riproduce esattamente il
   comportamento precedente**.
2. Il CSV esporta **tutte le quantità che servono a ricostruirla** (non il risultato con la
   costante accesa, ma i pezzi da cui si ricompone ogni suo valore).
3. **Un solo backtest** spazza tutto l'intervallo, offline.
4. Si sceglie **fuori campione** (leave-one-league-out), non sul minimo in-sample.
5. Il valore scelto va nel *Registro delle costanti* con campione, `z` e fold.

`ENS_SCOPE_W`, `GOALS_SOT_W` ed `ELO_1X2_W` sono stati decisi così. `ROLE_SCOPE_INDEPENDENT`
rompe il punto 2 (cambia quali partite si scaricano) e ha richiesto due giri appaiati.

## Trappole: non rifarle

Tutte già successe. Accanto a ogni «corretto» c'è dove guardare per riverificarlo: una voce
di questo elenco è stata a lungo falsa proprio perché nessuno sapeva dove controllarla.

**Nel modello**

- **Il vantaggio campo contato due volte**: dati di sola casa più un moltiplicatore 1.10
  (v9.4), poi di nuovo nell'Ordered Logit (`b20`). Vedi *Convenzioni del motore*.
- **Elo calcolato a ritroso**: il trend usciva col segno invertito. Ora è cronologico, di
  lega, a somma zero (controllo M: media esatta 1500).
- **1X2 in Poisson senza `rho`** mentre i risultati esatti usavano Dixon-Coles: ora una
  matrice sola.
- **Una correzione espressa come rapporto non si trasporta su un'altra baseline.**
  `goalsSotCorrection` torna una scala contro il totale che le passi: il `b19` applicava la
  scala del ruolo anche ai lambda completi. Ora ogni blocco ha la sua (`_GC`, `_GCo`).
- **`_base` è di coppia.** Vedi *La baseline di coppia*.
- **Una previsione fatta da media + scarto va scomposta prima di ritararla**: guardare la sd
  delle componenti, non solo la pendenza.
- **Una diagnosi giusta non rende giusta la cura.** `GOALS_UNIT_FIX`, `ELO_SCALE` a 1.60,
  `SHRINK_K` sotto 4: tre volte si è aggiustato un numero prendendo il prestito dal conto di
  un altro. Prima di accendere una correzione, misurare quanto sposta e contro cosa divide.
- **Un componente con peso 0 va tenuto giusto**: l'Ordered Logit a schermo, la diagnostica
  della correzione residuale nel CSV.
- **Prima di misurare un grado di libertà, scrivere per quale strada arriva al numero che si
  guarda.** `SHRINK_LAM_K` e `ROLE_SCOPE_INDEPENDENT` sono stati sospettati sull'1X2 senza
  avere un percorso fin lì; `grep` lo dice in un secondo.
- **Due costanti dichiarate insieme non invecchiano insieme**: delle due rette della
  confidence ne era sbagliata una sola.
- **Il lambda è inversamente proporzionale alla base di lega**: una base troppo alta lo
  abbassa. Scrivi la formula prima di dedurre un segno.
- **Una probabilità alta non è un'informazione, lo scarto dal base rate sì**, e il base rate
  va preso dalla lega, non dal campione su cui l'hai misurato.

**Nei dati**

- **Array delle metriche compattati saltando i `null`**, `out.n` uguale alla lista richiesta
  invece che ai match con dati, `avg_3/5/10` che pescavano match più vecchi per riempire i
  buchi: tutti corretti, tutti facili da reintrodurre.
- **Non normalizzare un valore prima di aver provato tutte le sue fonti.** Vedi *I fallback
  che non scattavano mai*.
- **Una metrica condivisa fra le due squadre non è di squadra.** Vedi *Le metriche che non
  erano di squadra*.
- **Punteggi nulli contati come 0-0** in `computeLeagueParams` ed `estimateRho` (`?? 0`): ora
  quelle partite si saltano.
- **`RAW_CACHE` che memorizzava anche le risposte vuote**: un buco di rete diventava «nessun
  dato» per sempre. Il Comparatore patcha la riga; nello Scanner il rischio resta.
- **Un taglio temporale dedotto da un orario è forte quanto il formato dell'orario.** Vedi
  *L'orario non è affidabile*.
- **Un valore di ripiego plausibile è più pericoloso di un errore**: 1.50/1.20 per sedici
  build, l'HFA a +100 per tre. Un fallback deve dire su quante osservazioni è prodotto.

**Fra i due file**

- **Due copie della stessa costante divergono, sempre.** `CMP_DC_SHRINK_TABLE` rimasta ai
  valori pre-`b5`, `_calibConf1X2` scritta due volte, `SHRINK_LAM_K = 3` cablata in
  `cmpRunMatch`. Il Comparatore legge dal motore e tiene la propria copia solo come rete,
  dicendolo nel log.
- **Una correzione applicata in un file va applicata in tutti e due.** `aerials` corretto in
  `ADV_SPEC` e non in `CMP_NEW_SPEC`: per tre build il CSV ha confrontato una quantità di
  squadra (14.5) con una di partita (28.4).
- **Quando una costante sceglie un ramo, ogni strumento di misura a valle va riletto quel
  giorno stesso.** Vedi *Il peso dell'Elo si misurava sul ramo sbagliato*.
- **Una costante tarata sul predittore del Comparatore non vale per lo Scanner.**
  `RESID_GAMMA` era 0.56 sul predittore del Comparatore (scope `overall`) e 0.678 su quello
  dello Scanner (scope `role`, baseline `_base`): un bias costante verso la trasferta. Se tari
  su un predittore, verifica sulla diagnostica dell'altro.

**Etichette e DOM**

- **Assegnare un valore a una `<select>` senza l'`<option>` non fa niente**, senza errori
  (`sel-league`, `b18`). Se si passa configurazione via DOM, verificare che abbia attecchito.
- **Un'etichetta va presa dai dati che descrive, non dallo stato del momento.** Tre volte: la
  lega presa dalla dropdown (vedi *L'etichetta di lega letta dal DOM*), il suffisso
  `_ruoloIndip` del file preso dall'interruttore all'export, il marcatore della scala nel
  titolo di riga. Gli export si accumulano: un'etichetta che descrive righe va calcolata
  **dalle righe**.
- **Le etichette di riga del CSV devono essere uniche**, e vanno lette come sono scritte: un
  parser che cerca `Unita: media gol trasferta` non trova `Unita: media gol trasf.` e legge
  `null` senza avvisi.

**Nel metodo**

- **Non leggere mai l'AUC dei mercati gol aggregata fra leghe** (l'aggregato dava 0.531 dove
  dentro le leghe era 0.495 e 0.500).
- **Prima di spiegare una differenza fra leghe o stagioni, misurare se esiste.** Con ~350
  partite l'errore standard di una correlazione è ~0.053 e quello di una pendenza ~0.19. Test
  di omogeneità, poi la spiegazione. Vedi *Il modello non fallisce in una lega più che in
  un'altra*.
- **Un test che verifica un'assenza porta con sé il caso in cui la presenza si vede**
  (controllo di potenza).
- **«Verificato» vale solo per i dati con cui hai verificato.** Quando un test genera i propri
  dati, elencare i formati che l'API potrebbe restituire e passarli tutti.
- **Un banco sintetico risponde alle domande di struttura** («esiste un percorso?»), **non a
  quelle di direzione** («in che verso si muove?»).
- **Minimizzare il solo errore di calibrazione porta a shrinkage estremi**: una previsione
  piatta è perfettamente calibrata e vale zero. L'arbitro è il Brier, con la pendenza come
  controllo.
- **Il profilo di stile di un avversario va calcolato escludendo la partita in esame**:
  `poss` e `field_tilt` delle due squadre sono complementari.

## Disciplina di calibrazione

Prima di cambiare una costante:

1. **Misura sul CSV del backtest**, non a occhio.
2. **Guarda la pendenza di `reale ~ previsto`, non solo la MAE**: >1 sotto-disperso, <1
   sopra-disperso.
3. **Smorza la stima verso il valore vecchio in proporzione al suo errore standard.**
4. **Verifica su due metà del periodo** (o su due leghe). Un effetto che c'è solo in una metà
   non è un effetto. Il segno deve reggere ovunque: è la regola che ha evitato quattro falsi
   positivi.
5. **Diffida di un miglioramento monotono senza ottimo interno**: di solito stai solo
   affilando.
6. **Controlla la collinearità prima di aggiungere una feature «residuale»**: il segnale utile
   sta nelle metriche che il motore non usa già per i lambda.
7. **Guarda bias e AUC insieme, per lega**: il Brier mescola livello e ordinamento.

I suggerimenti presi da fuori vanno verificati sul CSV prima di essere incollati: più di una
volta erano tarati sulla convenzione sbagliata di `k`.

## Cosa è già stato provato

Da leggere **prima** di proporre un miglioramento: quasi tutte le idee ovvie sono già state
misurate.

| idea | esito | numeri |
|---|---|---|
| Correzione residuale dell'1X2 (GCA, conduzioni in area, passaggi progressivi) | **no** | il segno si ribalta fra aprile (+0.336) e marzo (−0.174); con `RESID_GAMMA` misurato bene +0.015 su 716 partite |
| `min(npxg)` per il GG | **no** | 0.584 in Serie A, 0.494 in LaLiga |
| `interceptions` invertita sui gol | **no** | il segno si ribalta sulle altre due leghe |
| Breakdown SCA, o SCA totale col segno meno, sui gol | **no** | 0.588 LaLiga / 0.484 Premier; 0.584 / 0.467 / 0.505 |
| Altezza difensiva (`sum_defx`) sull'Over | **debole** | 0.9σ, e la metrica ha pendenza 0.06 |
| Ritoccare i pesi dell'ensemble | **quasi niente** | −0.0013, `z = −2.03`, una lega discorde. Adottato per pulizia |
| Correggere le soglie dell'Ordered Logit | **sul modello sì, sull'ensemble no** | bias sull'`1` da +6.8 a −0.1, ma l'ensemble si muove di 0.0001: l'OL mangia lo stesso NPxG del Dixon-Coles |
| `rho` come causa del bias dell'Over | **falsificata** | spegnerlo sposta l'Over 2.5 di +0.0 punti; `rho` vale fra −0.001 e −0.043 |
| Distribuzione dei gol a coda più grassa | **falsificata, di segno sbagliato** | il totale gol è sottodisperso: var/media 0.849 / 0.895 / 0.975 |
| La forma della distribuzione come causa del livello | **no** | col lambda riscalato ai gol veri il residuo non è distinguibile da zero (z = 1.3 e 0.85) |
| `GOALS_UNIT_FIX` | **diagnosi giusta, cura sbagliata** | vedi *Il disallineamento di unita nel lambda* |
| Affilare le probabilità (temperatura) | **no** | il Brier peggiora oltre T ≈ 1.1 |
| Attacco/difesa stimati su tutta la lega invece che su 15 partite | **no** | AUC 0.681 contro 0.680; mescolato 0.688 contro lo 0.690 che l'Elo dà già |
| Rendere il campione di ruolo indipendente | **no** | vedi *Il campione di ruolo è un sottoinsieme* |
| Abbassare `SHRINK_K` sotto 4 | **no** | vedi *Le due costanti dello shrinkage* |
| Alzare `SHRINK_LAM_K` | **non ancora** | candidato per la sesta lega |
| `SHRINK_K` giù e `SHRINK_LAM_K` su per compensare | **non torna** | l'escursione utile di `SHRINK_LAM_K` (0.9 punti di Over) non paga gli 1.5 che `SHRINK_K` a 1 toglie |
| Alzare `ELO_SCALE` oltre 1.25 | **no** | la logloss migliora fino a 1.60, ma a 1.25 l'Elo è già calibrato (1.092): si sovra-scalerebbe il termine giusto per compensare quello sbagliato |
| Alzare il K dell'Elo | **no** | vedi *Registro delle costanti* |
| Applicare la regressione dell'Elo fra l'ultima partita e la data da prevedere | **no** | peggiora: 0.5743 → 0.5745, sulle partite post-stacco 0.5068 → 0.5124 |
| Prevedere quali partite finiscono pari | **no** | `pX` ha AUC 0.487 (±0.020); anche `−|p1−p2|` e `−max(p1,p2)` stanno a 0.495–0.498 |
| Soglia sul pareggio «alla Champions» (X se nessuno supera il 43%) | **no** | corregge il conteggio dei pareggi ma sceglie le partite a caso (22.8% contro 25.9% alla cieca). La colonna ▲▼ di quella classifica è un artefatto del calendario |
| Prevedere meglio le stats | **al tetto** | 26 metriche su 47 al 90% del tetto `sqrt(ICC)` |
| Calibrare le stats sullo stile dell'avversario | **si fa già** | il «concesso» di `predictStat` lo fa; un indice composito aggiunge +0.001 |
| Sistemare il KNN | **ridondante** | pesare per somiglianza batte la media semplice, ma media × concesso batte la somiglianza su 10 metriche su 10. Toglierlo, non aggiustarlo |
| Medie brevi (ultime 3, ultime 5) | **mai meglio della lunga** | 47 metriche su 47 |
| Abbassare i `k` dei mercati sui numeri | **cura sbagliata** | la dispersione veniva dalla baseline di coppia (sd 8:1 sullo scarto); vedi *La baseline di coppia* |
| Squilibrio della partita su corner e tiri | **corner no, tiri forse** | corner: segni ribaltati; tiri 2.8σ con una lega discorde |
| Ricalibrare la confidence a retta | **sostituita da una tabella** | vedi *La confidence* |
| Arretrare il taglio temporale a `x-1` | **no** | vedi *L'orario non è affidabile* |
| Ordinare il tabellone per probabilità grezza | **no** | guadagno piatto (+1.4 … +7.1) contro monotono per scarto |

**Le cose che hanno retto**, in ordine di quanto valgono:

| idea | numeri |
|---|---|
| **L'Elo che inclina i lambda dell'1X2** (`b13`–`b14`) | +5σ, replicato su due leghe mai usate per tarare |
| **Il tabellone per scarto dal base rate** (`b38`) | +16.7 punti sulla proposta migliore, walk-forward +18.8, monotono in 5 stagioni |
| **La scala dell'Elo 1.25** (`b30`) | logloss 1-contro-2 0.5836 → 0.5743, `z = −3.54`, 6 fold su 7 |
| **`ENS_SCOPE_W = 1`** (`b21`) | −0.0042 di logloss, `z = −3.96`, 3 leghe su 3 |
| **Lo squilibrio sui cartellini** (`b16`) | AUC 0.562 → 0.593, stesso segno in 5 leghe |
| **`sum_sot` sull'Over 2.5** (`b9`–`b12`) | l'unica feature sopravvissuta a tre leghe |

## La baseline di coppia

`_base[k]` è la media di tutti i valori visti nelle partite di quella squadra, prodotti e
concessi insieme: contiene un **effetto coppia**, non solo il livello della lega
(`corr(sum_sot previsto, baseline) = +0.841`). Per `predictStat` va benissimo; usata come
media di lega ha svuotato tre modifiche di fila:

1. **`b9`, un rapporto contro se stesso.** `sum_sot / (2 × lg)` cancellava la variazione fra
   partite: AUC Premier 0.534 → 0.469.
2. **`b10`, previsioni troppo larghe.** Se `pred ≈ lg × (…)` e `lg` varia con la coppia,
   l'effetto coppia entra due volte: pendenze 0.60 / 0.30 / 0.64 sui mercati sui numeri.
3. **`b11`, abbassare `k`.** Inutile: la sd di `2·lg` stava 8:1 (corner), 11:1 (tiri), 3:1
   (gialli) su quella dello scarto che `k` governa.

La causa: `_base` è una media di ~30 partite e metà della sua varianza è rumore di stima (la
pendenza gira attorno a 0.5, che è la sua affidabilità). La cura: restringere **la
baseline** verso un riferimento davvero di lega (i gol di `computeLeagueParams`), che è
`MARKET_BASE_SHRINK` per i numeri e la media di lambda per i gol.

**Regola**: prima di usare una quantità come «media di lega», chiedersi su quali partite è
calcolata. Le uniche quantità davvero di lega sono quelle costruite su
`globalLeagueMatchesCache`: `LG` e l'Elo.

## La lega che non arrivava mai

Fino al `b17` il Comparatore passava la lega al motore con `setV('sel-league', lId)` su una
`<select>` **senza `<option>`**: no-op silenzioso, `lId === ''`. Quindi
`computeLeagueParams` ripiegava su avgH 1.50 / avgA 1.20 ed `estimateRho` su −0.11, **in ogni
lega e in ogni partita di backtest**. L'Elo invece funzionava, perché la sua guardia
(`if (_chosenLeagueId && ...)`) si spegneva sul vuoto: è per questo che era l'unica cosa che
batteva il modello. Lo Scanner in produzione non aveva il problema.

Ogni backtest fino al `b17` ha misurato un motore con 2.70 gol e `rho −0.11` fissi. Da
rivedere, in ordine: `SOT_PER_GOAL` e `MARKET_PER_GOAL` (ancorati a `LG.avgH + LG.avgA`),
`MARKET_SHRINK_K`, `MARKET_BASE_SHRINK`, `GOALS_SOT_W`, `CARDS_ELO_B`. Meno esposti
`ELO_1X2_W` e `STAT_SHRINK_TABLE`. Solo la Serie A è stata rifatta (vedi *Da fare*).

Ora `setV` crea l'`<option>`, verifica che il valore abbia attecchito e ferma il batch; il
CSV esporta `Unita: partite di lega usate` (`LG.n`) e `Unita: rho stimato`; `cmpRunMatch`
si ferma se `lgN = 0`.

## Il disallineamento di unita nel lambda

```
attH = shrink(npxg_casa / LG.avgH)       NPxG diviso la media GOL
defA = shrink(npxga_trasf / LG.avgH)
lamH = LG.avgH · attH · defA · (1 + pen) + pxH
```

Gli NPxG escludono i rigori e stanno sotto i gol: tutti e otto i moltiplicatori
attacco/difesa stanno **sotto 1** in tutte le leghe misurate (prodotti fra 0.76 e 0.91). Ma
la contrazione verso la media di lega ne restituisce +12.3%, e il lambda finale esce a
−2.5% / −5.0% / +0.3% dai gol veri: il difetto è **già compensato a valle**.

**`GOALS_UNIT_FIX` resta 0.** La correzione del `b17` divide per `_baseN`, la baseline NPxG
**di coppia**, che correla 0.77–0.87 col lambda (la trappola della baseline di coppia), e il
livello sfonderebbe a 2.87–3.65 gol contro 2.43–2.75 veri. Il codice resta come
documentazione eseguibile di un difetto noto. **Non accenderla senza aver prima sostituito
`_baseN` con una media NPxG di lega.**

La conseguenza che conta oggi: lo shrinkage fa **due mestieri** (regolarizza le stime e
compensa il disallineamento), quindi `SHRINK_K` e `SHRINK_LAM_K` non sono manopole libere.

## I mercati gol: due muri

**L'ordinamento.** Il lambda del Dixon-Coles correla **+0.087** col totale dei gol, uguale in
tutte le leghe (omogeneità Q = 6.14 su 4 gdl, p = 0.19). L'AUC dell'Over 2.5 sta fra 0.51 e
0.60. Nessuna feature provata lo sposta tranne `sum_sot`. Il candidato serio rimasto è la
forma della distribuzione dei tiri (`/shots`): dieci tiri da 0.10 e due da 0.50 danno lo
stesso lambda ma distribuzioni diverse.

**Il livello.** Tre ipotesi falsificate (`rho`, sovradispersione, forma della distribuzione:
vedi *Cosa è già stato provato*). Riscalando il lambda ai gol veri della lega il bias
dell'Over si chiude del tutto in LaLiga e il resto non è distinguibile da zero. Resta
**la base di lega**: `computeLeagueParams` è una media **piatta** su tutte le stagioni
caricate, l'unica stima del motore che non decade, e il lambda le è inversamente
proporzionale.

| lega | base usata | gol reali 25/26 | lambda contro reale |
|---|---|---|---|
| LaLiga | 2.637 | 2.698 | −2.5% |
| Premier | 3.041 | 2.754 | −5.0% |
| Serie A | 2.548 | 2.426 | +0.3% |

Da qui `LEAGUE_HALFLIFE_DAYS` (vedi *Da fare*).

**I sei mercati, sull'ensemble del `b22`** (1133 partite, tre leghe):

| mercato | base | detto | bias | AUC | AUC LaLiga / Premier / Serie A |
|---|---|---|---|---|---|
| `1` (= `X2`) | 43.4% | 41.9% | −1.6 | **0.694** | 0.699 / 0.675 / 0.702 |
| `2` (= `1X`) | 30.6% | 31.3% | +0.7 | **0.694** | 0.669 / 0.675 / 0.725 |
| `X` (= `12`) | 25.9% | 26.8% | +0.9 | 0.531 | 0.591 / 0.488 / 0.523 |
| `Goal` | 52.6% | 50.1% | −2.5 | 0.551 | 0.514 / 0.535 / 0.553 |
| `Over 2.5` | 50.3% | 47.0% | −3.4 | 0.549 | 0.573 / 0.513 / 0.522 |

Le doppie chance sono complementi degli esiti singoli: stessa AUC, stesso Brier, nessuna
informazione in più.

## I gol

`sum_sot` (somma dei tiri in porta previsti delle due squadre) entra come **seconda stima del
lambda**, non come moltiplicatore:

```js
lam_sot = sum_sot / SOT_PER_GOAL          // 3.25
lam_mix = (1 - w) * lam_DC + w * lam_sot  // w = GOALS_SOT_W = 0.50
scala   = lam_mix / lam_DC                // cap ±20%, applicata a entrambi i lambda
```

Un moltiplicatore lasciava il rango dominato da `lam_DC`; per smuoverlo sarebbero serviti
`alpha 5` e cap ±90%, con il Brier da 0.2537 a 0.3151. La media pesata sposta il rango
tenendo il livello, e migliora ogni linea Over (0.5 … 4.5) su AUC e Brier insieme. Il CSV
ricostruisce w = 0 / 0.25 / 0.5 / 0.75 / 1.0 senza rilanciare il motore.

## L'Elo nell'1X2

Fino al `b13` il motore usava dell'Elo **solo la pendenza** (`penH`, ±8%), non il livello. Ma
la differenza Elo batteva il modello in tutte e tre le leghe del primo panel (AUC sulla
vittoria casa 0.689 contro 0.662). Non è informazione nuova: è la stessa storia compressa
meglio, perché l'Elo propaga i risultati di tutta la lega in modo transitivo.

`buildGlobalElo`: cronologico, a somma zero, K 30 sotto le 15 partite e poi 20,
moltiplicatore per scarto di gol, e **di lega** (filtra `_chosenLeagueId`: una neopromossa
parte da 1500). Usa tutte e tre le stagioni caricate.

Si collega **inclinando il rapporto fra i lambda a totale fisso**:

```
lgModel  = logit(p1 / (p1 + p2))                              dalla matrice
lgElo    = (ELO_SCALE·(Elo_casa − Elo_trasferta) + HFA) / 173.72
lgTarget = (1 − w)·lgModel + w·lgElo                          w = ELO_1X2_W = 0.75
```

`eloTiltLambdas` cerca per bisezione `t` tale che `lamH·e^t`, `lamA·e^−t` (riscalati a somma
costante) producano `lgTarget`. Il totale dei lambda è identico al bit (controllo N), quindi
Over/Under non si muove; si muovono 1X2, doppie chance, handicap, risultati esatti e GG.
`pX` resta quella del modello. Il CSV ricostruisce w e `ELO_SCALE` senza rilanciare il
motore: `lgModel` si calcola prima dell'inclinazione e non dipende da nessuno dei due.

L'HFA viene da `400·log10(wr_casa/wr_fuori)` sulle partite di lega ed è già un log-odds, per
questo `ELO_SCALE` non lo tocca. Quando il clamp morde, card, prompt e CSV lo dicono
(`HFA grezzo (prima del clamp 30-100)`, `HFA: il clamp ha morso?`): il pavimento 30
corrisponde a un rapporto vittorie di 1.1885, dentro l'intervallo plausibile della Serie A
moderna, e può ribaltare il segno (un grezzo di −98 usciva +30).

### Il peso dell'Elo si misurava sul ramo sbagliato

Fino al `b31` il CSV registrava il tilt di **ruolo** (`__ELO_DEBUG`), mentre dal `b21` l'1X2
esce dai lambda **completi** (`__ELO_DEBUG_OVER`). Le due ricostruzioni di `w` vanno in
direzioni opposte (a `w = 0`: 42.9% dal ruolo, 64.5% dal completo). Ogni ritaratura di `w`
fatta con un CSV fra il `b21` e il `b30` è da buttare. Ora il Comparatore registra tutti e
due i rami, etichettati `[ruolo → mercati gol]` e `[completo → 1X2]`, e ricostruisce `w` e
`ELO_SCALE` da quello giusto. Controllo O.

## La scala dell'Elo, e la curva dello stacco

**La scala.** La conversione `400/ln(10) = 173.72` è la definizione della scala Elo, ma il
nostro rating è una stima online con `K` limitato e sotto-disperde: la pendenza di
calibrazione è **1.235** (`z = 3.13`), e non cala con l'età del rating (1.250 a zero giorni,
1.243 a sei mesi). Si tara la conversione, non il rating: `ELO_SCALE = 1.25`.

Il `b35` l'ha confermata sui dati veri e ha localizzato il resto della timidezza. Sulla
sezione A/B del peso, `w = 0` è il solo modello e `w = 1` il solo Elo:

| `w` | pendenza | σ da 1 |
|---|---|---|
| 0 (solo Dixon-Coles + Markov) | 1.443 | +4.81 |
| 0.75 (in uso) | 1.209 | +2.72 |
| 1 (solo Elo, scala 1.25) | 1.092 | +1.30 |

**L'Elo è calibrato, il modello è timido.** Alzare `ELO_SCALE` a 1.60 calibrerebbe la
miscela sovra-scalando il termine giusto: quando il modello sarà calibrato, `S` andrà
rimisurata e l'ottimo scenderà.

### Lo stacco

La regressione verso 1500 dopo l'inattività è `ELO_GAP_ASY·(1 − e^{−(giorni − 45)/τ})`,
con τ = 360:

| stacco | regressione |
|---|---|
| in stagione (massimo 28.8 giorni osservati) | 0% |
| pausa estiva, 83 giorni | 9.0% |
| 8 mesi | 37.6% |
| 2 anni | 79.7% |

Con τ = 110 (fino al `b29`) la pausa estiva valeva 26.3%, e siccome il motore mangia tre
stagioni le due pause si componevano a −45.7%: lavava via quasi metà dello scarto da 1500
prima che la stagione cominciasse. Il regime «otto mesi» nei dati non esiste: si passa dalla
pausa estiva (75–105 giorni) ai ritorni dalla B (455+).

La regressione si applica **alla partita successiva**, dentro il ciclo cronologico, non fra
l'ultima partita e la data da prevedere: chiudere l'asimmetria peggiora (vedi *Cosa è già
stato provato*). La card mostra le pause già scontate (`gapLog`) separate dall'ultimo tratto:
una frase negativa su una card deve dire a cosa si riferisce il «no».

## Ruolo o completo

Con 15 partite lo scope `role` ne lascia ~8, e in cambio compra la differenza casa/trasferta
della singola squadra, che vale meno del rumore che aggiunge: il vantaggio casa vero sta già
in `LG.avgH`/`LG.avgA`. Backtest `b20` su 1133 partite:

| `ENS_SCOPE_W` | logloss | pick |
|---|---|---|
| 0 (solo ruolo) | 1.0113 | 50.9% |
| 0.5 | 1.0090 | 51.1% |
| **1 (solo completo)** | **1.0071** | **51.4%** |

Monotono in tutte e tre le leghe, `z = −3.96`, scelta fuori campione 1.0 in 3 fold su 3.
**Ma solo per l'1X2**: sui mercati gol il completo ordina meglio in due leghe su tre e
peggiora la calibrazione ovunque, quindi `dcMat` resta `dcRole`.

## Il campione di ruolo è un sottoinsieme

```js
let overallMatches = past.slice(0, limit);
let roleMatches = overallMatches.filter(m => (m.home_team.id === teamId) === isHomeTeamUI);
```

`role` è quello che c'è **dentro** le ultime `limit` partite: con `limit = 15` restano 8
partite, e in produzione `nHr ≈ limit/2` (alzare `history-limit` alza il ruolo a metà
velocità). Questo file ha sostenuto il contrario per parecchie build, anche nell'elenco delle
trappole «già corrette». Ogni costante tarata finora (`SHRINK_LAM_K`, le tre `MARKET_*`) è
tarata su ~8 partite di ruolo: **non «correggere» la riga senza un backtest.**

### L'A/B del campione di ruolo: la risposta è no

`ROLE_SCOPE_INDEPENDENT = 1` rende il ruolo le ultime `limit` partite giocate nel ruolo.
A/B appaiato su 1133 partite di tre leghe con `/advanced` pieno: campione di ruolo da 15 a 26,
logloss **+0.0002** (`z = +1.85`), pick 51.5% in entrambi, segni discordi sui mercati gol.
**Resta 0.** Era prevedibile: con `ENS_SCOPE_W = 1` il ruolo entra nell'1X2 solo di
straforo, dalla scala dei tiri in porta.

Nel Comparatore c'è una casella che la accende (ricordata in `localStorage`). Gli export si
accumulano, quindi un file può contenere tutti e due i regimi: la stessa partita due volte non
è un doppione ma le due metà dell'A/B (riga `Scope: ruolo indipendente`). Il nome del file lo
dice dal contenuto: `_ruoloIndip`, `_AB` se misto, niente se tutto di default.

## Le due costanti dello shrinkage

**`SHRINK_LAM_K` sull'1X2 vale zero.** Da 0.5 a 40 (80×) l'1X2 non si muove di un millesimo:
la costante tocca solo i lambda di ruolo, e l'1X2 esce da quelli completi. È invece la
manopola di livello dei **mercati gol** (su un campionato sintetico, Over 2.5 da 43.6% a
10.5% sulla stessa escursione).
Il `b37` l'ha spazzata sulla ricostruzione esatta del CSV (1127 partite di Serie A):

| `SHRINK_LAM_K` | bias Over | Brier Over | logloss Over+GG contro 3 |
|---|---|---|---|
| 1 | −3.2 | 0.24500 | +0.00211 |
| **3** | −2.6 | 0.24469 | in uso |
| 5 | −2.2 | 0.24459 | −0.00110 (`z = −1.82`) |
| 8 | −1.7 | 0.24459 | −0.00196 (`z = −1.56`) |

Ottimo interno fra 5 e 8, ma sotto soglia e col segno ribaltato nel 2022/23. **Resta 3.**

**`SHRINK_K` l'1X2 lo tocca, ma non basta e costa.** `lgModel` scala come `w = n/(n+k)`, e a
`k = 0` (shrinkage spento) la pendenza resterebbe 1.273, ancora a 3σ. Sotto 4 l'1X2 migliora,
ma i gol pagano di più:

| `k` | 1X2 | Over 2.5 | GG | somma |
|---|---|---|---|---|
| 2 | −0.00097 | +0.00118 | +0.00180 | **+0.00201** |
| 1 | −0.00163 | +0.00240 | +0.00321 | **+0.00399** |

E sulle 567 righe dove il pavimento dell'HFA non morde il guadagno sull'1X2 scende a
`z = −1.35`. **Resta 4.** Abbassare `k` abbassa il livello dei gol perché toglie la
compensazione del disallineamento di unità: le due manopole tirano sulla stessa carenza in
versi opposti, e la radice è la media NPxG di lega.

**L'ensemble non comprime, espande**: log-odds dell'ensemble = 1.0076 × `lgTarget`.

## Lo squilibrio e i cartellini

Le partite squilibrate hanno meno cartellini di quanti il modello ne preveda: correlazione
fra `|ΔElo|` e il residuo dei gialli −0.138 su 1743 partite, stesso segno in tutte e cinque
le leghe (coefficiente comune −0.00354, −5.8σ, omogeneità p = 0.914). Gialli reali dal
quintile più equilibrato al più squilibrato: 4.33 → 3.21.

```js
lYel = lYel_grezzo + CARDS_ELO_B * (|Elo_casa − Elo_trasferta| − scarto_medio_di_lega)
```

Lo scarto medio di lega è calcolato al volo su `ELO.table`. Il Brier migliora in tutte e
cinque le leghe con ottimo interno su −0.0035; AUC Over 3.5 / 4.5 / 5.5 da 0.562 / 0.567 /
0.580 a 0.593 / 0.590 / 0.599. Costo zero chiamate.

## Il modello non fallisce in una lega più che in un'altra

L'errore del `b14`: guardare cinque numeri, prendere i due più bassi e chiedersi perché quelle
leghe sono rotte. La correlazione lambda-gol va da −0.004 (Premier) a +0.168 (Bundesliga), ma
con ~350 partite l'errore standard è 0.053 e il test di omogeneità dà p = 0.19: le leghe sono
indistinguibili. Stesso esito sulle pendenze dei mercati sui numeri (p = 0.54 / 0.12 / 0.16)
e sulle stagioni di `lgModel` (p = 0.071). Prima si misura se la differenza esiste, poi la si
spiega; per accorgersi che una lega è davvero diversa servono più stagioni, non più leghe.

Vale anche per le pendenze dei mercati sui numeri: vanno calcolate **dentro** la lega
(aggregate risultano gonfiate dalla variazione fra leghe: 0.88 contro 0.63 sui corner).

## Il tabellone ordinava per la colonna sbagliata

Il tabellone ordinava per **probabilità grezza** con soglie fisse, cioè premiava l'aritmetica
delle doppie chance. Su 1882 partite di Serie A:

| mercato | soglia vecchia | la supera | guadagno sopra il giocarlo sempre |
|---|---|---|---|
| `12` | 70% | **90% delle partite** | **+0.5** |
| `1X` | 65% | 59% | +13.9 |
| `X2` | 60% | 50% | +14.7 |
| `1` | 55% | 21% | +25.3 |
| `Over 2.5` | 55% | 8% | +14.1 |
| `2` | 60% | **5%** | **+37.8** |

Il mercato proposto di più valeva meno di tutti. Su 28.230 proposte il guadagno per fascia di
**scarto** cresce monotono (+2.3 / +6.3 / +14.1 / +16.0 / +24.6 / +36.8) e regge in tutte e
cinque le stagioni; per fascia di **probabilità** è piatto (+1.4 … +7.1). I mercati sui numeri
hanno più scarto da offrire di `12`, `GG` e `Over 2.5` insieme (scarto ≥ +10: tiri 15%, gialli
14%, corner 13%) ed erano gli unici assenti. `X` non ha mai uno scarto ≥ +10.

Sulla proposta migliore di ogni partita: prima in cima finiva sempre una doppia chance
(guadagno +11.7), ora `1` 26%, `2` 16%, `X2` 15%, gialli 13%, Under 10%, tiri 8% (**+16.7**,
walk-forward **+18.8**). La resa grezza scende e il guadagno sale: è il punto.

Il motore non si è mosso (39 campi su 39 identici al `b36`): è cambiato solo quale numero va
in cima e come è etichettato. Resta da riconfermare su una seconda lega (vedi *Da fare*).

## Gli audit

Controlli fatti sul codice contro se stesso (`b19`, `b22`) e sul documento contro il codice
(`b23`). Oltre a quelli qui sotto hanno trovato puliti: `ADV_SPEC` contro lo schema, nessuno
scambio casa/trasferta su 43 metriche, nessuna fuga dal futuro nei cicli, le 1743 verità di
riferimento ricalcolate dal punteggio, gli invarianti dei mercati. I controlli sono in *Come
validare una modifica*.

### I fallback che non scattavano mai

`aggregaTeam` faceva `drib = zeroIf(drib, anyOk)` e **poi** `if (drib === null && d) drib =
…`: dopo `zeroIf` il test non è mai vero. Sette fallback su dieci su `/stats` erano codice
morto, e le medie venivano diluite con degli zeri (previsto/reale 0.63 su dribbling, controlli
sbagliati, palle perse). Ora `zeroIf` gira dopo i fallback. Controllo A.

### La doppia verita sullo shrinkage

`CMP_DC_SHRINK_TABLE` nel Comparatore aveva 10 valori su 10 diversi da `STAT_SHRINK_TABLE`
(erano pre-`b5`). Vive in `cmpDcPredict`, il percorso di riserva che si accende solo se l'hook
non espone `__PRED_STATS`. Ora usa la tabella del motore quando c'è, si annuncia nel log, e il
CSV esporta `Origine metriche avanzate` (`motore` / `riserva-k-motore` / `riserva-k-locali`).

### Le metriche che non erano di squadra

`defending.aerials` è il numero di duelli aerei **della partita**: identico fra casa e
trasferta nel 100% dei casi, e `predictStat` lo contava due volte. Corretto in
`defending.aerials_won` nel `b19`, nel Comparatore solo nel `b22`. Il suo `k` e la sua riga
nella Progressione Storica vanno ancora rifatti (vedi *Da fare*). Controllo D.

### L'etichetta di lega letta dal DOM

`cmpBuildResult` scriveva la lega leggendo il testo **attualmente selezionato** in
`#cmp-league`, che `cmpUpdateLeagues()` svuota a ogni cambio di paese: nei tre export del
06/09 il 59–88% delle righe aveva la lega sbagliata. Ora il nome si risolve dall'id della
partita (`cmpLeagueName(match.league_id)`), la dropdown è solo l'ultima rete, e l'export
dichiara la composizione del file nel log. I 25 CSV precedenti sono stati verificati puliti.
Controllo H.

### Il documento contro il codice

Il `b23` ha trovato quattro punti in cui questo file descriveva un motore diverso: il più
grosso era il campione di ruolo (vedi *Il campione di ruolo è un sottoinsieme*). Ha tolto
anche otto variabili riempite dal payload e mai usate e una funzione mai chiamata.
**`lamH_mix` e `lamA_mix` sembrano morte al linter e non lo sono**: le legge l'hook iniettato.
Prima di cancellare qualcosa segnalato come inutilizzato, cercarlo nell'hook e negli `onclick`
dei due `.html`. Controlli J e K.

## Leggere un CSV del Comparatore

Prima di analizzare, sempre, in quest'ordine:

- **I-bis. `ID PARTITA` unici**, dentro il file e fra i file. `cmpSavedMatches` si accumula:
  export consecutivi si contengono (conteggi multipli di una giornata, 378, 756, 1134… sono il
  segnale) e la stessa partita può comparire due volte. Se le due righe hanno regimi diversi
  (`Scope: ruolo indipendente`) è un A/B da separare, altrimenti un doppione. Deduplica
  sempre.
- **H. La colonna `LEGA`**: ricostruisci la lega dai nomi delle squadre e confrontala.
- **I. `Origine metriche avanzate`**: se dice `riserva-*`, le sezioni *NUOVE METRICHE* e
  *METRICHE 0905-b4* sono da saltare, il resto del file resta valido. Sulle stagioni di Serie
  A 2021/22–2023/24 PitchAPI non serve `/advanced`: `riserva-*` sul 100% delle righe, e il
  motore gira con l'xG al posto degli NPxG.
- **Q. `lgN > 0`** su tutte le righe.
- **P. Il clamp dell'HFA**: su quante righe ha morso (`HFA: il clamp ha morso?`).
- **Il verdetto di parità** nel log dell'iniezione: manopole ai default o A/B dichiarato.

Poi: ogni partita occupa **4 colonne** (Previsto, Confidence, Reale, Esito); le sezioni CASA e
TRASFERTA ripetono le stesse etichette (la seconda occorrenza è la trasferta); le
probabilità hanno una cifra decimale. Per ricostruire qualcosa fuori dal motore, fare **per
prima** la prova di coincidenza: ricalcolare un valore che il CSV già contiene e verificare
che coincida entro la quantizzazione (0.0005). Non verifica il motore, verifica la tua
trascrizione.

## Leggere il log del Comparatore

Quattro messaggi che sembrano bug e non lo sono:

- **`⚠️ data fuori dallo storico caricato (…)`** e **`Nessuna partita per <data>`**: la data
  non è coperta dall'archivio scaricato (le stagioni le sceglie la dropdown, e l'API non ha
  ancora la stagione in corso). «Si gioca il *g±n*» vuol dire turno di sosta.
- **`Il V9.7 non ha esposto _V97_probs`**: `avviaScanner` è uscito prima della riga
  dell'hook. Quasi sempre è il guardrail «Storico insufficiente» su una **neopromossa** nelle
  prime giornate.
- **`⚠️ RISERVA: le metriche avanzate NON vengono dal motore ma da cmpDcPredict`**, seguito
  da **`Estratti da 0/0 match storici`**: `R.predStats` era vuoto e nemmeno la riserva ha
  trovato partite. Nei backtest riusciti la riga è `→ Metriche avanzate: previste dal motore`.
- **«Hook iniettato dopo l'ensemble (fallback)»**: la riga della confidence ha cambiato forma
  e la confidence esce `null`. Questo invece è da guardare.

## Come validare una modifica

Non c'è una suite. Il minimo prima di committare:

```bash
# 1. sintassi: estrai il JS inline e passalo a node
python3 - <<'PY'
import io,re,os
for f in ('scanner.html','comparatore.html'):
    s=io.open(f,encoding='utf-8').read()
    js='\n;\n'.join(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', s, re.S))
    io.open('/tmp/'+f.replace('.html','.js'),'w',encoding='utf-8').write(js)
PY
node --check /tmp/scanner.js && node --check /tmp/comparatore.js

# 2. i cinque agganci testuali del Comparatore fanno ancora presa sul motore?
node -e '
const js=require("fs").readFileSync("/tmp/scanner.js","utf8");
const t=[["cache lega",  /(^|\n)\s*(?:let|var|const)\s+globalLeagueMatchesCache\s*=\s*\[\]\s*;?/],
         ["RAW_CACHE decl", /(^|\n)\s*(?:let|var|const)\s+RAW_CACHE\s*=\s*\{\}\s*;?/],
         ["RAW_CACHE save", /RAW_CACHE\[id\]\s*=\s*res;/],
         ["punto hook 1",   /(const\s+confidence\s*=\s*Math\.round\([^;]*;)/],
         ["punto hook 2",   /(const\s+m1\s*=[^;]*;\s*const\s+mX\s*=[^;]*;\s*const\s+m2\s*=[^;]*;)/]];
for(const [n,re] of t) console.log((re.test(js)?"OK  ":"KO  ")+n);
' # e le build: window.__SCANNER_BUILD deve coincidere con _bComp del Comparatore

# 3. le pagine si aprono senza errori in console
python3 -m http.server 8204 &
# poi Playwright (Chromium è preinstallato in /opt/pw-browsers/chromium):
# apri le tre pagine e raccogli pageerror + console error: zero errori e zero richieste
# fallite (leghe.json sta nel repository). A 390px, zero scroll laterale. Ogni id scritto
# da safeTxt/safeHtml deve esistere nel DOM.
```

**I controlli con nome**, da rifare quando si tocca la parte che riguardano. Ognuno ha
trovato un bug vero.

| | controllo | quando |
|---|---|---|
| A | nessuna variabile passata da `zeroIf`/`keepNull` è poi testata con `=== null` | si tocca l'estrazione |
| B | `media(previsto)/media(reale)` vicino a 1 per ogni metrica del CSV | dopo un backtest |
| C | il previsto di casa correla col reale di casa più che con quello di trasferta | dopo un backtest |
| D | il reale di casa e quello di trasferta non sono mai identici (metrica di squadra) | metrica nuova |
| E | `ADV_SPEC` contro `CMP_NEW_SPEC`/`CMP_ADV_KEYS`, campo per campo (confronta il percorso principale: fermarsi al primo `??` dà falsi positivi) | si tocca un getter |
| F | ogni `m.R.<chiave>` letta dal Comparatore è esposta da `_V97_probs` | si tocca l'hook o il CSV |
| G | le etichette in prima colonna del CSV (`mdl`, `uRows`, `scRows`, `statList`, `rowMkt`) sono uniche | sezione CSV nuova |
| J | le costanti scritte in questo file esistono nel motore con quel valore | si tocca una costante |
| K | `eslint` con `no-unused-vars` e `no-undef` sul JS estratto (attenzione a `onclick` e all'hook) | pulizie |
| L | leakage col controllo di potenza (ricetta sotto) | si tocca un filtro temporale o una fonte di dati |
| M | la curva dello stacco dà 0% / 9.0% / 37.6% / 79.7% a 30 / 83 / 240 / 826 giorni, e la tabella Elo ha media esatta 1500 | si tocca l'Elo |
| N | da `__ELO_DEBUG_OVER`, `lamH0 + lamA0` identico al bit a `lamH + lamA` | si tocca l'inclinazione |
| O | gli strumenti del Comparatore leggono il ramo che il motore usa (`__ELO_DEBUG.lgModel` contro `__ELO_DEBUG_OVER.lgModel`) | si tocca una costante che sceglie un ramo |
| P | ogni clamp espone il grezzo e quante volte ha morso (HFA, `ELO_TILT_MAX`, `GOALS_SOT_CAP`) | clamp nuovo o toccato |
| Q | `__UNIT_DEBUG.lgN > 0` a ogni partita | nuovo percorso che chiama `avviaScanner()` |
| R | il debug si legge dall'oggetto risultato, non da `window` (che è dell'ultimo `k` di `CMP_K_LIST`) | confronti Comparatore/Scanner |

**Il giro completo senza rete.** Il motore gira per intero su dati finti, in Chromium, senza
PitchAPI:

1. Aprire **`comparatore.html`** (ha gli id DOM ombra che il motore si aspetta), leggere
   `scanner.html` via `fetch`, applicare **le stesse regex del Comparatore** e iniettare con
   `new Function`.
2. Popolare `window.globalLeagueMatchesCache` con un campionato sintetico. Funziona solo dopo
   la patch della cache: la variabile è dichiarata `let` e da fuori non arriva al motore.
3. Non sostituire `fetchMatchRaw` da fuori (dentro `new Function` le funzioni sono
   riassegnabili solo da dentro): precaricare
   `window.__RAW_CACHE[id] = [stats, lineups, advanced, events]` per ogni partita.
4. `setV` su `sel-league`/`sel-home`/`sel-away`, `avviaScanner()`, poi guardare `_V97_probs`,
   i `__*_DEBUG` e ogni nodo con `id` in cerca di `NaN`/`undefined`.

**Il controllo L, leakage.** Sul giro senza rete: una partita bersaglio, un'altra lo stesso
giorno, una il giorno prima. Drogare la bersaglio **una strada per volta** (prima il payload
in `RAW_CACHE`, poi il punteggio sull'oggetto partita) e verificare che l'oggetto risultato
resti identico bit per bit. Poi drogare quella del giorno prima e verificare che **cambi**
(controllo di potenza). Poi rifare tutto con `time_utc` senza `Z` in un browser a
Europe/Rome (`newContext({ timezoneId: 'Europe/Rome' })`).

**Due build a confronto.** Per una modifica che non deve spostare numeri, far girare vecchia e
nuova build sul giro senza rete, stesso seme e stessa partita, e diffare gli oggetti che
escono (`m1/mX/m2`, i quattro lambda, `probsOL`, `advRole`, i `__*_DEBUG`). È così che si può
dire «39 campi su 39 identici» invece di «compila». Per un refactoring puro (rinomine,
riformattazioni) basta il confronto di AST:

```bash
node -e '
const fs=require("fs"), acorn=require("/opt/node22/lib/node_modules/eslint/node_modules/acorn");
const get=p=>/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/.exec(fs.readFileSync(p,"utf8"))[1];
const norm=j=>JSON.stringify(acorn.parse(j,{ecmaVersion:2022}),
  (k,v)=>(k==="start"||k==="end"||k==="loc")?undefined:v);
console.log(norm(get("prima.html"))===norm(get("dopo.html")));
'
```

Quando si tocca il testo del JS si usa un parser, non un regex: `//` compare negli URL, `/*`
nelle stringhe, e i regex letterali del Comparatore verrebbero massacrati.

**Oltre al minimo**, quando si tocca il motore:

- simulare `aggregaTeam` con un payload `/advanced` finto e verificare che ogni coppia di
  `STAT_PAIRS` abbia la sua feature e che `predictStat` non torni `null` (ha trovato il bug
  delle metriche a segno negativo);
- controllare gli invarianti dei mercati: la matrice somma a 1; l'handicap asiatico somma a 1
  su ogni linea ed è monotono (AH −0.5 = `p1`, AH +0.5 = `p1 + pX`; **AH −0.75 sta fra −1 e
  −0.5**); le fasce multigol disgiunte sommano a 1; le probabilità Over decrescono con la
  linea; `negBinK` restituisce `Infinity` sui campioni non sovradispersi. Quando un invariante
  fallisce, sospetta prima del test;
- riprodurre la matrice fuori dal motore (`calcDCMatrix` + `probsFromMatrix` in una ventina di
  righe di Python, alimentate coi lambda del CSV) per provare varianti offline, dopo la prova
  di coincidenza;
- dopo aver aggiunto una metrica ad `aggregaTeam`, controllare le liste che la devono
  contenere: dichiarazione, `myAdv`/`oppAdv`, `matchDetails`, `out.vals`, `OPT`,
  `out.features`, la mappa `pair` di `_base`, `STAT_PAIRS`. Una chiave in `OPT` senza array in
  `vals` fa esplodere `push` alla prima partita.

Le funzioni pure si testano in node estraendo la fetta da `const STAT_SHRINK_DEFAULT` a
`async function avviaScanner()`, con `globalThis.window = globalThis` in testa.

Il giro completo su una partita vera richiede rete verso PitchAPI: se non c'è, **dillo**
invece di dichiarare verificato quello che non lo è.

## Cronologia delle build

| build | cosa |
|---|---|
| `b2`–`b3` | shrinkage per metrica al posto dello 0.35 fisso; correzione residuale accesa, poi spenta perché non reggeva fuori campione |
| — | via i commenti dal JS (26% del codice), verifica per confronto di AST |
| `b4` | 34 metriche nuove da `/advanced` a zero chiamate in più, tipi `volume`/`additivo`, il Comparatore usa le previsioni del motore |
| `b5` | `STAT_SHRINK_TABLE` rifatta su 1133 partite, tre leghe |
| `b6`–`b8` | revisione UI: testo nero su nero, card morte, via il confronto col book e i resti del KNN, narrative che confrontano le due squadre |
| `b9` | `sum_sot` sui lambda gol; salto data dell'Elo reso continuo |
| `b10`–`b12` | mercati sui numeri; il backtest boccia metà del `b9`–`b10` per la baseline di coppia, poi la cura giusta |
| `b13`–`b14` | l'Elo entra nell'1X2 inclinando i lambda; cinque leghe, peso 0.75 |
| `b15` | le differenze fra leghe erano rumore; pendenze dentro la lega |
| `b16` | lo squilibrio prevede i cartellini: AUC 0.562 → 0.593 |
| `b17` | trovato il disallineamento di unità nel lambda; correzione pronta ma spenta |
| `b18` | la lega non arrivava mai al motore nei backtest |
| `b19` | audit: sette fallback morti, due tabelle divergenti, una metrica non di squadra |
| `b20` | l'Ordered Logit contava la casa due volte: soglie ristimate, peso 0; ensemble a due blocchi |
| `b21` | il completo batte il ruolo sull'1X2 (`ENS_SCOPE_W = 1`); l'etichetta di lega del CSV veniva dalla dropdown |
| `b22` | `rho` e sovradispersione scagionati; il muro dei gol è nel livello; `aerials` corretto anche nel Comparatore |
| `b23` | audit del documento contro il sorgente; il ruolo è un sottoinsieme; via il codice morto |
| `b24` | il taglio temporale non si fida più dell'orario (`_isPast`) |
| `b25`–`b26` | l'A/B del campione di ruolo diventa una casella, e risponde no |
| `b27`–`b28` | la UI dice quale ambito usa; il mega-prompt porta i verdetti misurati; telefono in verticale |
| `b29` | cambiare partita non costa più un ricaricamento |
| `b30` | la scala dell'Elo (1.25) e la curva dello stacco (τ 360) |
| `b31` | il peso dell'Elo si misurava sul ramo sbagliato |
| `b32` | il clamp sull'HFA mordeva in silenzio: ora si vede |
| `b33`–`b34` | parità Comparatore↔Scanner rimisurata sul percorso vero; via l'ultima copia cablata |
| `b35` | backtest su cinque stagioni: la timidezza è nel modello, non nell'Elo |
| `b36`–`b37` | le due costanti dello shrinkage misurate: nessuna si muove |
| `b38` | tabellone per scarto dal base rate, confidence 1X2 dalla tabella misurata |
