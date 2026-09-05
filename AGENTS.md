# AGENTS.md — Scanner Calcio V9.7

Istruzioni per chi (agente o persona) mette mano a questo repository.

## Cos'è

Modello analitico per il calcio, servito come pagine statiche. Nessun build,
nessun package manager, nessun test runner: si aprono i file nel browser e
basta. Tutto il codice sta dentro un unico `<script>` inline per file.

| file | ruolo |
|---|---|
| `index.html` | menu, due link |
| `scanner.html` | **il motore**. Analizza una partita: Dixon-Coles + Ordered Logit + Markov, mercati, statistiche previste |
| `comparatore.html` | **backtest**. Carica `scanner.html` come testo, lo inietta in memoria e ne guida il motore su centinaia di partite, poi esporta un CSV previsto-vs-reale |
| `leghe.json` | catalogo leghe/stagioni (id PitchAPI) |

Dati da PitchAPI via proxy Cloudflare: `PITCH_BASE` in `scanner.html`.
Endpoint usati per partita: `/stats`, `/lineups`, `/advanced`, `/events`,
tutti attraverso `fetchMatchRaw` (che li mette in `RAW_CACHE`).

## Stato del lavoro, e da dove ripartire

Sezione di consegna: dice a che punto siamo, così una sessione nuova non
ricomincia da capo. Aggiornala quando cambia qualcosa di sostanziale.

**Build corrente: `0905-b5`.** Scanner e Comparatore devono coincidere, e sul
Comparatore il badge sotto la dropzone deve uscire **verde** dopo aver trascinato
lo Scanner. Il branch di lavoro è `claude/scanner-stat-optimization-sgs62u`;
`main` è indietro (fermo al merge della PR #1, cioè al `0905-b2`), quindi
**scaricare i file dal branch, non da `main`**.

**Cosa è stato fatto, in ordine:**

1. `0905-b2` — shrinkage per metrica al posto dello 0.35 fisso; correzione
   residuale sull'1X2 con le metriche di creazione.
2. `0905-b3` — correzione residuale **spenta** (`RESID_ALPHA = 0`): non reggeva
   fuori campione. `k` ritarati su 76 partite.
3. Ripulitura — via i commenti dal JS (26% del codice), la spiegazione è passata
   in questo file. Verifica per confronto di AST: stesso identico programma.
4. `0905-b4` — 34 metriche nuove da `/advanced` (zero chiamate in più), otto
   metriche orfane cablate, tipi `volume` / `additivo`, unificazione col
   Comparatore che ora usa le previsioni del motore invece di rifarle.
5. `0905-b5` — `STAT_SHRINK_TABLE` rifatta su **1133 partite, tre leghe**.

**Dove siamo bloccati:** i mercati gol. L'1X2 funziona (48–49% contro il 39–42%
del «gioca sempre in casa», e la fascia ≥60% rende il 71–78%), ma l'Over/Under
2.5 della matrice non discrimina fuori dalla LaLiga. Tutte le idee provate per
correggerlo con le statistiche avanzate sono cadute alla verifica incrociata —
la tabella in *Cosa è già stato provato* le elenca una per una.

**Tre strade chiuse da misure, non da opinioni** (i numeri sono in *Cosa è già
stato provato*): prevedere meglio le stats avanzate — siamo al tetto; usare le
stats per calibrare la forza dell'avversario — si fa già, e non resta niente
oltre; sistemare il KNN — la sua premessa è vera ma ridondante, il Dixon-Coles
estrae la stessa informazione meglio.

**La prossima cosa da fare, in ordine di rapporto valore/rischio:**

0. **Togliere il KNN.** Non entra nell'ensemble dal `0905-b2`, costa `getSimilarMatches`
   su tutto lo storico a ogni partita, ed è misurato come strutturalmente ridondante.
   Attenzione: `knnRel` e `wKnn` sono ancora letti altrove (narrativi, fallback della
   confidence), e `probsKnn` finisce nel CSV e nel mega-prompt. Vanno ripuliti insieme.
1. **`sum_sot` nell'Over/Under.** È l'unica feature che ha superato le tre leghe.
   Va integrata correggendo il **totale dei lambda** e tenendo il rapporto
   casa/trasferta della matrice, così migliorano insieme tutti i mercati gol e
   resta valido il principio «una matrice governa tutto». Esporre la forza su
   `window` per l'A/B e mettere la diagnostica nel CSV, come è stato fatto per la
   correzione residuale: è quella che ha permesso di scoprire in dieci minuti che
   non funzionava.
2. **L'endpoint `/shots`.** Il candidato più serio per il muro dell'Over, con la
   ragione spiegata in *Il muro dell'Over/Under*. Costa una chiamata in più per
   partita.
3. **Ricontrollare `avg_def_x`**: pendenza 0.06, la previsione è quasi scorrelata
   dal reale. O è un problema di forma del modello, o la metrica va tolta.
4. **Togliere `vaep_def`, `pv_def`, `sca_def`** dalle feature: correlazione
   previsto/reale a zero misurata su 1133 partite. Il fix additivo che le ha rese
   calcolabili era giusto, ma quello che si vede è rumore.

**Il campione di riferimento** per qualunque nuova taratura è: Serie A + Premier
+ LaLiga 2025/26, 1133 partite, esportate dal Comparatore `0905-b4` o successivo.
Meno di due leghe non basta — è l'errore che ha prodotto quattro falsi positivi
di fila.

## Revisione della UI: cosa è stato verificato e cosa resta

Giro di revisione fatto dall'utente davanti allo Scanner. Diviso in quello che è
già stato guardato nel codice e quello che è ancora un sospetto.

### Verificato, e la risposta è questa

- **«Skellam Distribution» non esisteva.** `skellamPMF` era definita e **mai
  chiamata**: codice morto, ma il titolo della card la annunciava. Rimossa nel
  `0905-b6` insieme al titolo, che ora dice quello che la card fa davvero.
- **«Dà sempre 1-1» è corretto, non è un bug.** Con λ fra 1.0 e 2.0 per parte il
  risultato modale *è* 1-1, al 12–15%. Smette di esserlo solo sopra λH 2.2
  (2-0) o 2.4 (2-1), che quasi non capitano. Il problema non è il calcolo, è che
  **mostrare la moda non informa**: l'informazione sta nella distribuzione.
- **L'«Analisi di Sopravvivenza» non è un'analisi di sopravvivenza.** È
  `P(gol entro il minuto X) = 1 − exp(−λ_totale × quota_di_tempo)`, cioè il
  tempo al primo evento di un processo di Poisson, dove la quota viene dalla
  distribuzione empirica dei minuti dei gol in sei fasce da 15'. Con meno di 30
  gol nel campione la forma diventa uniforme. È legittimo ma il nome promette
  molto più di quanto faccia.
- **L'Elo è strutturalmente sano.** HFA stimato dalle vittorie reali
  (`400·log10(wr_casa/wr_trasferta)`, limitato fra 30 e 100), K adattivo (30
  sotto le 15 partite, poi 20), moltiplicatore per scarto di gol, cronologico e
  a somma zero. Il **salto data** regredisce verso 1500 quando passano più di 60
  giorni, con forza `min(0.9, 0.3 × ceil(anni_di_pausa))`. Funziona, ma è una
  funzione a gradini: una pausa di 61 giorni e una di 11 mesi ricevono la stessa
  regressione del 30%, e a 1.01 anni si salta di colpo al 60%. Da smussare.

### Sistemato nel `0905-b6`

- **Testo nero su nero in quattro riquadri** (qualità del tiro, fase di non
  possesso, funnel, punti attesi): era `color:#1c1c1e` su `background:var(--panel2)`,
  un residuo di quando l'app era a tema chiaro. Passati a `var(--txt)`. Stessa
  origine per i bordi pastello (`#ffe0b2`, `#ffcdd2`, `#e0f2f1`, `#e1bee7`),
  portati su `var(--line)`.
- **Card «Diagnostica predittore» rimossa**: era nata per capire perché
  `predictStat` collassava sulla baseline, problema risolto. `window.__PRED_DEBUG`
  resta esposto perché lo consuma la sezione diagnostica del CSV.

### Coda: leggibilità e presentazione

- **Tabellone scommesse**: propone solo 1X / X2 / 12, mai gli altri mercati. È il
  sintomo del problema noto (l'1X2 discrimina, i gol no), non un difetto della
  card.
- **Confronto con le quote del book**: non viene usato, si può togliere insieme a
  `calcValue` e alla sezione Kelly.
- **Le note narrative** (letalità, gegenpressing, funnel) dicono cose vere su una
  squadra ma **mai in relazione all'altra**: «è corta» senza dire corta rispetto
  a chi. Vanno riscritte come confronto, non come descrizione.
- **Doppie chance e gol con confidence**: tabella confusa e, sui gol, poggia su
  probabilità che sappiamo non discriminare.
- **Progressione storica**: ha senso ma va spiegata, e va deciso quali statistiche
  mostrarci (ora sono scelte storicamente, non per utilità misurata).
- **KNN a schermo**: mostrare le avversarie simili **ordinate dalla più alla meno
  simile**, con le statistiche che determinano la somiglianza. Nota: è il KNN
  *delle formazioni* che interessa all'utente, non quello che era nell'ensemble —
  che invece va tolto (vedi punto 0 della coda principale).
- **Palle inattive**: si mostra quanto una squadra produce, non quanto **subisce**.
  Il dato concesso c'è già (`xg_sp` ha la sua controparte).
- **Mega-prompt**: da rifare quando le statistiche giuste saranno decise —
  più dati, percentuali ed ensemble, meno prosa.

### Coda: da controllare nel modello

Nessuno di questi è ancora stato verificato. Sono sospetti dell'utente, non
difetti accertati.

- **Handicap asiatico** — le linee a quarti si spezzano in due mezze puntate,
  da verificare che la somma torni.
- **Multigol** — `multigoal()` somma celle della matrice, da controllare estremi
  e sovrapposizioni fra le fasce.
- **Alta varianza e disciplina** — da controllare, e da mettere in relazione con
  l'avversario invece che come numeri assoluti.
- **Markov** — `markovFlow` con rate dipendenti dal punteggio, mai verificato
  contro il backtest se non come colonna dell'ensemble.
- **Elo** — la funzione a gradini del salto data (vedi sopra).
- **Probabili formazioni**: PitchAPI espone `/lineups` anche in versione prevista.
  Da valutare dopo il resto.

## Come funziona il motore

I file non hanno commenti (vedi *Stile*): quello che spiegava il codice sta qui.

**La catena, in ordine.** `aggregaTeam` scarica lo storico di una squadra (fino
a 30 partite, `/stats` + `/lineups` + `/advanced` + `/events` per ognuna, tutte
via `fetchMatchRaw` e `RAW_CACHE`) e ne estrae per ogni partita quanto la
squadra ha **prodotto** e quanto ha **concesso**. `calcFeatures` trasforma ogni
serie in `{avg_3, avg_5, avg_10, avg_15, avg_tot, decay, std, nValid}`, dove
`decay` è la media pesata con emivita 106 giorni ed è il valore che il motore
usa quasi ovunque. Da lì si costruiscono i lambda, da un solo lambda-paio esce
**una sola matrice Dixon-Coles**, e da quella matrice discendono *tutti* i
mercati: 1X2, doppia chance, GG, Over/Under multilinea, multigol, risultati
esatti, handicap asiatico. Non ci sono mercati calcolati per conto proprio.

**Due scope.** `overall` sono le ultime N partite di qualunque tipo, `role`
sono le ultime N **in casa** per la squadra di casa e **in trasferta** per
l'ospite. Sono insiemi indipendenti, non uno sottoinsieme dell'altro. I lambda
di ruolo normalizzano ogni statistica sul baseline della propria sede
(`LG.avgH` o `LG.avgA`), ed è per questo che **non va aggiunto nessun
moltiplicatore di vantaggio campo sopra**: ci sarebbe due volte.

**I lambda.** `lambda = baseline_sede × forza_attacco × debolezza_difesa`
(struttura moltiplicativa, non media aritmetica fra attacco proprio e difesa
avversaria), più la componente rigori recuperata come `xG − NPxG` (gli NPxG
escludono i rigori, i gol no), più una correzione di forma dall'Elo limitata a
±8%. `rho` di Dixon-Coles è stimato dalle frequenze reali di 0-0/1-0/0-1/1-1
della lega, non fisso.

**I due shrinkage dei lambda**, entrambi su `window` così il Comparatore può
fare A/B prima di iniettare il motore:

| costante | formula | default | effetto |
|---|---|---|---|
| `SHRINK_K` | `peso = n/(n+k)` | 4 | forze attacco/difesa verso la media di lega. k=4 → con 15 match crede al 79%; k=10 → 60%; k=28 → 35% |
| `SHRINK_LAM_K` | `peso = n/(n+k)` | 3 | lambda di ruolo verso la media di lega quando le partite di ruolo sono poche |

Attenzione: qui **k alto = più shrinkage**, l'opposto della convenzione di
`predictStat` (vedi *Convenzioni del motore*).

**L'ensemble 1X2** è `Dixon-Coles 60% + Ordered Logit 30% + Markov 10%`.

- L'**Ordered Logit** ha preso il posto del KNN. Su 2639 partite, stesse
  partite per entrambi, il KNN faceva 46.3% e l'OL 50.2% — ma il problema vero
  era la calibrazione: quando il KNN diceva "70%" succedeva il 63%, quando
  diceva "50-60%" succedeva il 42%, scarti fino a −18 punti. Causa: media di
  pochi vicini, stime estreme e instabili (dava prob >70% in 1007 partite su
  6824, il DC solo in 55). L'OL modella l'esito come variabile **ordinale**
  (2 < X < 1) su una scala latente `y* = beta × (forza_casa − forza_trasferta)`
  tagliata da due soglie, e ha scarti di calibrazione entro ±3.6 punti su tutte
  le fasce. `OL_BETA = 1.950`, `OL_T1 = −0.850`, `OL_T2 = 0.350`, stimati per
  massima verosimiglianza su 1903 partite (split temporale 70/30) e validati su
  816 mai viste. La forza è `0.7 × attacco + 0.3 × difesa_avversaria`:
  l'additivo batte il moltiplicativo, e l'attacco pesa più della difesa
  avversaria (correlazione 0.26 contro 0.17).
- Il peso dell'OL è **fisso a 0.30**, non dipende più dal numero di vicini: non
  usa vicini. Tenuto sotto il vecchio picco 0.45 del KNN perché l'OL mangia gli
  stessi ingredienti del DC (xG attacco/difesa) ed è quindi parzialmente
  ridondante — un peso alto duplicherebbe il DC.
- Il **KNN resta calcolato e mostrato** come riferimento tattico e alimenta
  `knnRel`/`wKnn` usati altrove, ma **non entra nell'ensemble**. Se scrivi
  testi o prompt, non descriverlo come se ci fosse.

**La confidence non è l'accordo fra i modelli.** La vecchia formula misurava
`1 − tvDist` fra DC, KNN e Markov: verificato sui backtest, la correlazione fra
accordo e azzeccare è **−0.007**, cioè zero. Due modelli che concordano non
azzeccano più spesso di due che discordano; il numero era alto (spesso 90+) e
non significava niente. Ora la confidence è la **probabilità del pick,
ricalibrata sull'hit reale** con due rette stimate su 6824 partite
(Europa + MLS + Turchia):

```
1X2             hit_reale ≈ 6.26 + 0.880 × prob
mercati binari  hit_reale ≈ −5.06 + 1.091 × prob
```

Riscontro: pick ≥60% → 64.7% di hit reale su 821 partite, ≥65% → 69.5% su 387.
"Confidence 64" vuol dire davvero "64% di probabilità di indovinare".
`tvDist` e `sampleFactor` restano calcolati perché servono ai narrativi, ma
**non entrano più nella confidence**.

**Le statistiche previste** passano da `predictStat`, modello moltiplicativo
`media_lega × (quanto produco / lega) × (quanto concede lui / lega)` con
smorzamento per metrica sui due rapporti. Prima erano la media decayed della
squadra e basta — "l'Inter di solito fa 37 tocchi in area" restava 37 sia
contro il Genoa sia contro il Napoli — e il difetto era misurabile: il residuo
reale-meno-previsto correlava con la forza dell'avversario fino a −0.47 sul
Field Tilt e −0.37 sui passaggi progressivi. Se manca il dato del concesso o la
baseline di lega, `predictStat` torna da solo alla media semplice: le leghe
fuori dalle top europee spesso non hanno `/advanced`.

**Taratura di `STAT_SHRINK_TABLE` (0905-b5)** — rifatta da zero su **1133 partite,
tre leghe intere** (Serie A, Premier, LaLiga, stagione 2025/26), col metodo della
pendenza: si regredisce `reale ~ previsto`, e siccome la deviazione dalla baseline
è lineare in `k` al primo ordine, `k_nuovo = k_attuale × pendenza`. Ogni metrica è
verificata **lega per lega**: quelle dove le tre pendenze divergono di più di 0.35
sono marcate qui sotto e tenute prudenti.

Il quadro è netto: quasi tutto era **sopra-disperso**, cioè `k` troppo alto. Le
tarature precedenti venivano da 40–76 partite di un mese solo e sbagliavano di
molto su diverse metriche (`gca` era a 0.75, la pendenza dice 0.31).

| famiglia | metriche e `k` |
|---|---|
| gol e tiri | `npxg` 0.54 · `xg` 0.50 · `sot` 0.50 · `xgot` 0.46 · `cor` 0.40 |
| possesso e territorio | `poss` 0.76 · `tch_box` 0.61 · `field_tilt` 0.41 · `ppda` 0.35 · `f3_entries` 0.29 · `avg_def_x` 0.10 |
| creazione | `sca` 0.34 · `sca_live` 0.41 · `gca` 0.31 · `xag` 0.24 · `chances_created` 0.39 · `key_passes` 0.39 |
| breakdown SCA | `sca_dead` 0.18 · `sca_takeon` 0.16 · `sca_foul` 0.11 · `sca_shot` 0.10 · `sca_def` 0.10 |
| passaggi | `passes` 0.54 · `prog_passes` 0.47 · `passes_box` 0.44 · `prog_pass_dist` 0.36 · `switches` 0.28 · `assists` 0.16 · `second_assists` 0.17 |
| conduzioni | `carries` 0.49 · `prog_carry_dist` 0.50 · `carry_dist` 0.48 · `prog_carries` 0.48 · `carries_f3` 0.38 · `take_ons` 0.37 · `carries_box` 0.55 |
| difesa | `aerials` 0.54 · `ppda_num` 0.53 · `ppda_den` 0.29 · `clearances` 0.30 · `tackles` 0.23 · `interceptions` 0.23 · `duels_won` 0.22 · `blocks` 0.20 · `challenges` 0.14 · `yel` 0.23 · `fouls` 0.48 |
| possession value | `xt` 0.40 · `vaep_off` 0.23 · `pv_off` 0.21 · `vaep` 0.18 · `pv` 0.15 · `vaep_def` 0.10 · `pv_def` 0.10 |
| default | 0.50 |

Leghe discordi (pendenze con spread > 0.35, valore tenuto prudente): `fouls`,
`vaep_off`, `pv_off`, `assists`, `sca_def`.

**`avg_def_x` ha pendenza 0.06**, cioè la previsione non ha praticamente
relazione col valore reale. È a `k` 0.10 e non va usata come feature finché non
si capisce perché: è una coordinata media, e forse il modello attacco × difesa
non è la forma giusta per prevederla.

Il Comparatore ha una **seconda** tabella (`CMP_DC_SHRINK_TABLE`) usata solo come
fallback per i motori precedenti al 0905-b4: dal b4 le previsioni arrivano dal
motore. Non copiare valori dall'una all'altra: scope e baseline sono diversi.

### Aggiungere una metrica: `ADV_SPEC`

Dal `0905-b4` le metriche di `/advanced` non si cablano più a mano. `ADV_SPEC`,
appena sopra `aggregaTeam`, è una tabella `[chiave, getter, tipo]` e da lì
discendono **da sole**: estrazione (prodotta *e* concessa), inizializzazione
delle serie, lista `OPT`, `calcFeatures`, `STAT_PAIRS`, la mappa `pair` della
baseline di lega e `STAT_TYPE`. Aggiungere una metrica è **una riga**.

```js
['tackles', m => m.defending?.tackles, 'volume'],
```

Il getter viene applicato due volte allo stesso payload, a `myAdv` e a `oppAdv`:
`tackles` è quanto ne facciamo noi, `tackles_ag` quanto ne fa chi ci affronta.
È il secondo fattore del modello moltiplicativo, e costa zero chiamate perché
`/advanced` contiene già entrambe le squadre.

Il Comparatore ha la tabella speculare `CMP_NEW_SPEC`, **stesse chiavi, stesso
ordine**, che serve a estrarre i valori reali per il CSV. Se aggiungi una riga
in `ADV_SPEC`, aggiungila anche lì (e in `NEWK` dell'export), altrimenti la
metrica viene prevista ma mai verificata.

Otto metriche erano raccolte da sempre ma non passavano da `calcFeatures`
(`ppda`, `field_tilt`, `direct_speed`, `seq_time`, `avg_x`, `avg_def_x`,
`cp_regains`, `rec_time`): `predictStat` tornava `null` e finivano sulla media
semplice. Ora sono in `ORPHAN_PAIRS`, che le aggancia ai rispettivi `opp_*`.

### I tipi di metrica: `volume` e `additivo`

`STAT_TYPE` decide la forma del modello, e la distinzione **non è cosmetica**.

- **`volume`** (default) — conteggi e somme non negative. Forma moltiplicativa
  `lg × sh(mio/lg) × sh(concesso/lg)`.
- **`additivo`** — forma `lg + k·((mio − lg) + (concesso − lg))`, per due casi:
  - **valori che attraversano lo zero.** `vaep_defensive` e `pv_defensive` sono
    **negativi per definizione** (misurano il rischio di subire). Il rapporto
    `mio/lg` fra due negativi ha segno invertito e il prodotto è privo di senso;
    peggio, i guardiani storici `decay > 0` e `v > 0` li scartavano in silenzio
    e `predictStat` tornava `null`. `vaep`, `pv`, `vaep_def`, `pv_def` sono
    additive, e i guardiani per queste sono su `isFinite`, non sul segno.
  - **coordinate**, non volumi. `avg_x` e `avg_def_x` sono metri sul campo: un
    prodotto di rapporti su una coordinata non ha dimensioni sensate.

Nel campo normale le due forme danno quasi lo stesso numero (baseline 40, mio
42, concesso 38: 39.98 contro 40.00). Divergono agli estremi, dove la
moltiplicativa esplode: mio 70 e concesso 10 danno 34.4 contro 40.0. Per le
metriche a segno variabile la moltiplicativa non è "meno precisa", è **rotta**.

Le metriche a rapporto (`ppda`) restano `volume` per compatibilità, ma dal
`0905-b4` ci sono anche `ppda_num` e `ppda_den` sciolti: prevedere i due
conteggi e fare il rapporto dopo è più stabile che prevedere il rapporto.

## Politica sui valori mancanti

È una decisione di progetto, non un dettaglio: la v9.4 forzava tutto a 0, la
v9.5 lasciava tutto `null`, ed erano sbagliate entrambe perché i due casi non
sono lo stesso problema.

- **Conteggi** (Big Chances, cross, filtranti, tocchi in area, recuperi): molte
  API omettono la chiave quando il valore è zero. Se la risposta è arrivata ma
  la chiave manca → **0** (`zeroIf(..., statsOk)`).
- **Rapporti, percentuali, distanze, xG** (possesso, PPDA, field tilt,
  baricentro, xG): uno 0 è fisicamente impossibile. Se manca, il dato non c'è e
  la partita **esce da quella media**, non conta come prestazione nulla
  (`keepNull`).
- Se `/advanced` fallisce, **niente** viene zero-fillato: quella partita
  semplicemente non porta metriche avanzate.
- I metrici opzionali si inseriscono **sempre**, anche come `null` (lista
  `OPT`): saltarli disallineava gli indici dalle date e il decay accoppiava il
  valore alla partita sbagliata.
- La tabella "Copertura Dati API" mostra in quante partite ogni metrica è
  stata davvero restituita: serve a distinguere a colpo d'occhio una metrica
  assente (0%) da una con zeri legittimi. `N/D` si mostra solo a copertura
  zero — uno zero reale resta zero.

## Trappole già corrette: non rifarle

Errori trovati e sistemati nelle versioni precedenti. Sono facili da
reintrodurre modificando in buona fede.

1. **Vantaggio campo contato due volte** nel modello di ruolo (dati di sola
   casa *più* un moltiplicatore 1.10). Vedi *Come funziona il motore*.
2. **Elo calcolato a ritroso**: il trend usciva col segno invertito e
   penalizzava le squadre in crescita. Ora è cronologico, di lega, a somma
   zero, con vantaggio campo esplicito.
3. **Array delle metriche avanzate compattati saltando i null**: indici non più
   allineati a match e date.
4. **`out.n` uguale alla lunghezza della lista richiesta** invece che ai match
   con dati: i cicli leggevano `undefined` in coda.
5. **`avg_3/5/10` che pescavano match più vecchi** per riempire i buchi. I
   valori mancanti si saltano, non si sostituiscono.
6. **Campione di ruolo come sottoinsieme** degli ultimi N complessivi: con 15
   restavano ~7 gare. Ora i due insiemi sono indipendenti.
7. **Profilo tattico dell'avversario per il KNN preso dal generale** invece che
   dal suo ruolo.
8. **1X2 in Poisson puro senza rho** mentre i risultati esatti usavano
   Dixon-Coles con lambda diversi: due blocchi incoerenti fra loro. Ora una
   matrice sola.
9. **Taglio temporale a `T23:59`**: la partita target, giocata di pomeriggio,
   rientrava nel proprio storico e fra i vicini KNN. Ora `T00:00`.
10. **`RAW_CACHE` che memorizzava anche le risposte vuote**: un buco di rete
    diventava "questa partita non ha dati" per sempre. Il Comparatore patcha la
    riga; nello Scanner puro il rischio resta.

Il dettaglio completo delle 23 correzioni v9.4 → v9.6 sta nel commento in testa
a `scanner.html` al commit `cd51a69`, prima della ripulitura.

## Cosa è già stato provato, e come è andata

Questa è la sezione da leggere **prima** di proporre un miglioramento: quasi tutte
le idee ovvie sono già state misurate, e la maggior parte non ha funzionato. Ogni
riga qui sotto costa già un backtest.

| idea | esito | dove si vede |
|---|---|---|
| Correggere l'1X2 con GCA / conduzioni in area / passaggi progressivi | **smentita** | il residuo correla +0.336 su aprile (dove era tarata) e −0.174 su marzo: il segno si ribalta. Con GAMMA misurato bene la correlazione è +0.015 su 716 partite |
| `min(npxg)` per il GG | **non regge** | 0.584 in Serie A ma 0.494 in LaLiga. Il campione «a due leghe» che sembrava confermarlo conteneva la Serie A stessa: non era una replica |
| `interceptions` invertita sui gol | **non regge** | usciva quattro volte in Serie A, ma il segno si ribalta sulle altre due leghe |
| Breakdown SCA (`sca_takeon`, `sca_shot`) sui gol | **non regge** | 0.588 in LaLiga, 0.484 in Premier |
| SCA totale con segno negativo sui gol | **non regge** | 0.584 / 0.467 / 0.505 |
| Altezza difensiva (`sum_defx`) sull'Over | **debole** | 0.9 sigma, e la metrica ha pendenza 0.06: la previsione è quasi scorrelata dal reale |
| Ritoccare i pesi dell'ensemble (DC/OL/Markov) | **non serve** | la griglia in-sample preferisce Markov, ma fuori campione è pari e patta: una lega meglio, una peggio, differenze da 0.0007 di Brier |
| Ricalibrare le rette della confidence | **non serve** | rifittate su 756 partite danno 16.88 + 0.686·p contro 6.26 + 0.880·p: ai punti che contano (50–60%) coincidono entro un punto |
| Affilare le probabilità (temperatura) | **non serve** | il Brier peggiora oltre T≈1.1 su 716 partite |

**L'unica cosa che ha superato la verifica incrociata su tre leghe:**

| idea | esito | numeri |
|---|---|---|
| `sum_sot` (tiri in porta previsti, somma delle due squadre) sull'Over 2.5 | **regge** | AUC 0.581 / 0.531 / 0.546 sulle tre leghe, pooled 0.556 (3.3 sigma). Batte `dc_over` in **tutti e tre** gli holdout: +0.021, +0.028, +0.036. Spread fra quintile alto e basso: +21.3 / +9.3 / +10.7 punti |

Da notare due cose. La prima: `sum_sot` **da solo** batte `dc_over` **e** la
combinazione dei due (0.581 contro 0.577), cioè la probabilità Over della matrice
non aggiunge niente sopra i tiri in porta previsti. La seconda: `sot` non è una
metrica «avanzata», viene da `/stats` ed era disponibile da sempre.

### Il tetto: le previsioni delle stats sono al massimo, o quasi

Misurato su un panel di **2266 osservazioni squadra-partita** (1133 partite, tre
leghe, 60 squadre) costruito dai CSV del backtest. Per ogni metrica si calcola
l'**ICC** — quanta della sua varianza sta *fra* le squadre invece che da partita
a partita — e il tetto teorico di qualunque modello pre-partita è `sqrt(ICC)`.

Il risultato chiude la questione: **26 metriche su 47 sono al 90% o più del loro
tetto**, e diverse lo superano (il tetto ICC ignora l'effetto avversario, che il
modello invece usa). Il punto è che i tetti sono **bassi**, perché nel calcio la
varianza è quasi tutta dentro la squadra:

| metrica | ICC | tetto | correlazione attuale |
|---|---|---|---|
| `npxg` | 0.136 | 0.369 | **0.393** |
| `sot` | 0.124 | 0.351 | **0.367** |
| `poss` | 0.287 | 0.535 | **0.655** |
| `sca` | 0.145 | 0.381 | 0.373 |
| `passes` | 0.380 | 0.616 | 0.555 |

L'86% della varianza di `npxg` è rumore partita-a-partita: nessun modello
pre-partita lo può prevedere, e siamo già oltre il tetto naive. **Lavorare per
prevedere meglio le stats non è dove sta il valore.**

Il margine residuo, dove c'è, sta su metriche il cui tetto è comunque basso:
`avg_def_x` (26% del tetto, ma vedi la nota nella taratura), `assists` e
`second_assists` (47%), `sca_takeon` (49%), `sca_foul` (51%), `pv_off` (58%),
`vaep_off` (63%), `gca` (71%, tetto 0.30), `xag` (74%, tetto 0.35).

### Usare le stats per calibrare la forza dell'avversario: si fa già

Idea ragionevole e già implementata: il termine "concesso" di `predictStat` **è**
la calibrazione della forza dell'avversario. La domanda vera è se resta qualcosa
oltre a quella.

Misurato: si stima `reale ~ media squadra + concesso avversario` in leave-one-out,
e si guarda se il residuo correla con lo **stile** dell'avversario (possesso,
PPDA, field tilt, altezza difensiva, passaggi, conduzioni). Risultato: le
correlazioni stanno fra 0.02 e 0.09, appena sopra la soglia dei 2 sigma — ma
soprattutto **hanno tutte lo stesso segno su tutte le metriche**. Sette variabili
di stile che dicono la stessa cosa non sono stile: sono forza residua.

Aggiungere un indice composito di forza dell'avversario al modello dà **+0.001**
di correlazione. Zero. La strada è chiusa.

### Il KNN non è rotto, è ridondante

Testata la sua premessa direttamente: per prevedere una metrica di una squadra,
la media pesata sulla **somiglianza di stile fra l'avversario di allora e quello
di adesso** batte la media semplice?

| metrica | media semplice | pesata per somiglianza | modello attuale |
|---|---|---|---|
| `poss` | 0.506 | 0.656 | **0.714** |
| `field_tilt` | 0.435 | 0.569 | **0.612** |
| `prog_passes` | 0.401 | 0.500 | **0.534** |
| `sca` | 0.343 | 0.406 | **0.446** |
| `npxg` | 0.340 | 0.362 | **0.382** |

La premessa è **vera**: pesare per somiglianza batte ignorare l'avversario, su
tutte e dieci le metriche provate. Ma il modello attuale (media × concesso) batte
la versione a somiglianza su **tutte e dieci**, e la media dei due non aiuta.

Cioè il KNN estrae in modo rumoroso un'informazione che il Dixon-Coles estrae già
in modo pulito. Non c'è una versione "sistemata" del KNN che possa fare meglio:
il difetto è strutturale, non di implementazione. **Toglierlo, non aggiustarlo.**

Attenzione a un tranello trovato durante questa misura: se il profilo di stile
dell'avversario si calcola includendo la partita in esame, `poss` e `field_tilt`
risultano gonfiati, perché nella stessa partita le due squadre sono complementari
(la somma fa ~100). Il profilo va calcolato **escludendo la partita**, entrambe
le righe.

### Il muro dell'Over/Under

`dc_over` ha AUC **0.503 in Serie A, 0.494 in Premier, 0.556 in LaLiga**. Fuori
dalla LaLiga la probabilità Over della matrice non distingue una partita
dall'altra. Il totale di gol lo azzecca in media (le linee 0.5, 1.5, 3.5, 4.5
sono calibrate entro 2 punti), quindi il problema non è il livello dei lambda ma
la **capacità di ordinare le partite**.

L'ipotesi ancora non testata è che manchi la *forma* della distribuzione: dieci
tiri da 0.10 xG e due da 0.50 danno lo stesso lambda ma distribuzioni di gol
diverse. Servirebbe l'endpoint `/v1/matches/{id}/shots`, che dà ogni tiro con
`expected_goals`, `is_on_target`, `is_inside_box`, `situation` e coordinate. Costa
una chiamata in più per partita storica (da 4 a 5, +25% sul batch) ed è il
candidato più serio rimasto.

## Il contratto Scanner ↔ Comparatore

**Questa è la parte che si rompe in silenzio.** Il Comparatore non importa lo
Scanner: ne legge il testo, lo modifica con delle regex e lo esegue con
`new Function`. Quindi dipende dalla **forma testuale** di alcune righe.

1. **La cache condivisa** deve restare dichiarata esattamente così:
   `let globalLeagueMatchesCache = [];`
   Se cambi `let`, il nome o la posizione, il batch smette di popolare le
   partite e "non fa più nulla". C'è già un avviso nel file, sopra la riga.

2. **I nomi delle funzioni-motore** sono chiamati per nome dal Comparatore
   (`exposeNames` in `loadEngineFromText`): `apiCall`, `avviaScanner`,
   `aggregaTeam`, `extractSafeStat`, `buildGlobalElo`, `calcDCMatrix`,
   `markovFlow`, `probsFromMatrix`, `estimateRho`, `calculateRho`,
   `getSimilarMatches`, `computeLeagueParams`, `multigoal`,
   `asianHandicapMat`, `negBinCDF`, `negBinK`, `poisson`, `expectedPoints`,
   `loadLegheJson`, `fetchMatchRaw`, `predictStat`, `leagueStatBaseline`.
   Il **contenuto** è libero, i **nomi** no.

3. **Il punto di aggancio dell'hook** è la riga della confidence, trovata con
   `/(const\s+confidence\s*=\s*Math\.round\([^;]*;)/`. Non riscriverla e non
   citarla testualmente altrove nel file: la regex prenderebbe la citazione.
   Tutto ciò che l'hook deve leggere (`__PRED_STATS`, `__PRED_DEBUG`,
   `__RESID_DEBUG`, `m1/mX/m2`) va prodotto **prima** di quella riga.

4. **`RAW_CACHE[id] = res;`** viene riscritta dal Comparatore per non
   memorizzare le risposte vuote. Se cambi quella riga, la patch smette di
   applicarsi (silenziosamente: il log dice solo che non l'ha fatta).

5. **La build.** `window.__SCANNER_BUILD` nello Scanner e `_bComp` nel
   Comparatore devono coincidere, e il badge HTML `#build-ver` di entrambi i
   file va aggiornato insieme. Se divergono, il Comparatore mostra un avviso
   arancione. **Alza la build a ogni modifica del motore**: è l'unico modo per
   accorgersi di aver trascinato nella dropzone una copia vecchia.

Dopo ogni modifica al motore, verifica che le regex facciano ancora presa
(vedi *Come validare* più sotto).

## Convenzioni del motore

**Lo shrinkage è al contrario di come sembra.** Ovunque nel codice:

```js
sh(r) = 1 + k * (r - 1)
```

`k = 1` → **nessuno** smorzamento (si crede al rapporto grezzo).
`k = 0` → smorzamento **totale** (la stima collassa sulla media di lega).
Quindi **k alto = meno shrinkage**. Alzare `k` su una metrica rumorosa la
rende più volatile, non meno. Vale per `STAT_SHRINK_TABLE` (Scanner) e
`CMP_DC_SHRINK_TABLE` (Comparatore). Attenzione: `SHRINK_K` e `SHRINK_LAM_K`,
che sono un'altra cosa (shrinkage dei lambda), usano invece la convenzione
`n/(n+k)`, dove **k alto = più shrinkage**. Due convenzioni opposte nello
stesso file: guarda sempre la formula prima di toccare un numero.

**Lo scope `role` contiene già il fattore campo.** `predictStat(..., 'role')`
usa le partite in casa per la squadra di casa e in trasferta per l'ospite.
Aggiungere sopra un moltiplicatore di *home advantage* conta il vantaggio due
volte — è esattamente il bug corretto nella v9.4 sui lambda. Non rifarlo.

**Il time decay** è `_timeDecayDates` con emivita 106 giorni, applicato in
`calcFeatures`. Il Comparatore lo replica in `cmpTimeDecayWeighted`: se cambi
l'emivita da una parte, cambiala dall'altra.

**Niente leakage.** Il taglio temporale è `T00:00` del giorno della partita
(`matchTime` in `avviaScanner`). Qualunque nuova aggregazione deve filtrare
`t < targetMs`, altrimenti il modello vede il risultato che deve prevedere.

**Le costanti calibrate portano la loro provenienza in un commento.**
`OL_BETA/OL_T1/OL_T2`, le rette della confidence, `RESID_GAMMA`, i `k` delle
tabelle: ognuna dice su quante partite è stata stimata e con che metodo. Se
ne cambi una, aggiorna il commento; se ne aggiungi una, scrivilo.

**Chi consuma una stima con una calibrazione propria passa un `k` esplicito.**
L'Ordered Logit e `applyResidualCorrection` chiamano
`predictStat(..., STAT_SHRINK_LEGACY)`: le loro costanti valgono a quel `k`, e
ritarare `STAT_SHRINK_TABLE` non deve spostare in silenzio le probabilità 1X2.

## Disciplina di calibrazione

Questo repository vive di costanti stimate sui dati. Prima di cambiarne una:

1. **Misura sul CSV del backtest**, non a occhio. Il file esportato dal
   Comparatore ha tutto: previsto, reale, la diagnostica del predittore con i
   componenti (prodotto / concesso / baseline / stima) e le sezioni A/B.
2. **Guarda la pendenza, non solo la MAE.** La regressione `reale ~ previsto`
   dice se le stime sono sotto-disperse (pendenza > 1, servono `k` più alti) o
   sopra-disperse (pendenza < 1). La MAE da sola non lo distingue.
3. **Smorza la stima verso il valore vecchio in proporzione al suo errore
   standard.** Su 40–80 osservazioni le pendenze hanno SE dell'ordine di 0.4:
   prendere il punto-stima alla lettera è overfitting.
4. **Verifica su due metà del periodo.** Un effetto che c'è solo in una metà
   non è un effetto.
5. **Diffida di un miglioramento monotono senza ottimo interno.** Di solito
   vuol dire che stai solo affilando le probabilità, non aggiungendo segnale.
6. **Controlla la collinearità prima di aggiungere una feature "residuale".**
   La differenza casa-trasferta di npxg correla 0.99 con l'edge dell'ensemble,
   perché npxg *è* l'ingresso del Dixon-Coles: correggere con quella non è una
   correzione, è un affilamento mascherato. Il segnale utile sta nelle
   metriche che il motore **non** usa per i lambda (GCA, SCA, conduzioni in
   area, passaggi progressivi).

Suggerimenti presi da fuori (altri modelli, altri strumenti) vanno **sempre
verificati sul CSV prima di essere incollati**: più di una volta erano tarati
sulla convenzione sbagliata di `k`, o su metriche che il codice non espone.

### Il caso della correzione residuale (perché `RESID_ALPHA` è a zero)

`applyResidualCorrection` esiste, è cablata nell'ensemble, ma **alpha è 0: non
sposta niente**. Non è un residuo di sviluppo, è il risultato di una misura.

Nel `0905-b2` girava con alpha 0.25, tarata su 40 partite di aprile 2026. Il
backtest successivo (76 partite: le stesse 40 più 36 di marzo mai viste) ha
mostrato che la correlazione fra il residuo e l'errore dell'ensemble è +0.336
in aprile e **−0.174 in marzo**: il segno si ribalta. Sull'insieme è +0.081
con SE 0.11, cioè zero. Nel frattempo il segnale sembrava funzionare benissimo
in aprile, dove era stato tarato.

Due lezioni che valgono oltre questo caso:

- **una costante tarata sulle previsioni del Comparatore non si trasferisce
  allo Scanner.** `RESID_GAMMA` era 0.56 perché stimato sul predittore del
  Comparatore (scope `overall`, ultimi 15 match, baseline a quattro valori);
  in produzione il segnale lo calcola lo Scanner (scope `role`, baseline
  `_base`) e la pendenza vera è 0.678. Risultato: un bias costante verso la
  trasferta su ogni partita. Se tari su un predittore, verifica sulla
  diagnostica dell'altro prima di spedire.
- **la diagnostica va calcolata anche quando la funzione è spenta.** Con
  alpha 0 lo Scanner continua a esporre `sig`, `edge`, `resid` e le
  probabilità pre-correzione: è la sezione *A/B CORREZIONE RESIDUALE* del CSV
  a dire se e quando riaccenderla, e spegnere anche quella significherebbe non
  poterlo più sapere. Se tocchi `applyResidualCorrection`, tieni separati i
  due percorsi (misura sempre, applica solo se alpha > 0).

**Aggiornamento (0905-b5): la questione è chiusa.** I dati sono arrivati — 1133
partite su tre leghe — e la risposta è no: con GAMMA misurato correttamente
(0.360, non lo 0.678 che c'era) la correlazione fra il residuo e l'errore
dell'ensemble è **+0.015 su 716 partite**, cioè zero, e l'A/B non migliora a
nessun alpha. Il guadagno che si vedeva con GAMMA 0.678 era edge residuo
rimasto dentro il residuo per errore di scala: affilamento mascherato, non
informazione nuova. Non riaprirla senza un'idea diversa.

## Come validare una modifica

Non c'è una suite. Questo è il minimo prima di committare:

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

# 2. le regex del Comparatore fanno ancora presa sul motore?
node -e '
const js=require("fs").readFileSync("/tmp/scanner.js","utf8");
console.log("hook confidence:", (js.match(/const\s+confidence\s*=\s*Math\.round\([^;]*;/g)||[]).length, "(deve essere 1)");
console.log("RAW_CACHE:", /RAW_CACHE\[id\]\s*=\s*res;/.test(js));
console.log("cache lite:", /let\s+globalLeagueMatchesCache\s*=\s*\[\]/.test(js));
'

# 3. le pagine si aprono senza errori in console
python3 -m http.server 8199 &
# poi Playwright (Chromium è preinstallato in /opt/pw-browsers/chromium):
# apri http://127.0.0.1:8199/scanner.html e raccogli pageerror + console error.
# L'unico 404 atteso è favicon.ico.
```

Se hai aggiunto una metrica ad `aggregaTeam`, controlla anche la coerenza
delle cinque liste che la devono contenere: dichiarazione, estrazione
(`myAdv` / `oppAdv`), oggetto `matchDetails`, `out.vals`, lista `OPT`,
`out.features`, la mappa `pair` di `_base` e `STAT_PAIRS`. Una chiave in `OPT`
senza array in `vals` fa esplodere `out.vals[kk].push` alla prima partita.

Un test funzionale delle funzioni pure si fa estraendo la fetta di file da
`const STAT_SHRINK_DEFAULT` a `async function avviaScanner()` e importandola in
node con `globalThis.window = globalThis` in testa.

**Per un refactoring che non deve cambiare comportamento** (rinomine,
riformattazioni, rimozione di commenti) la verifica forte è confrontare
l'albero sintattico prima e dopo, non solo che compili. `acorn` è disponibile
dentro eslint:

```bash
node -e '
const fs=require("fs"), acorn=require("/opt/node22/lib/node_modules/eslint/node_modules/acorn");
const get=p=>/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/.exec(fs.readFileSync(p,"utf8"))[1];
const norm=j=>JSON.stringify(acorn.parse(j,{ecmaVersion:2022}),
  (k,v)=>(k==="start"||k==="end"||k==="loc")?undefined:v);
console.log(norm(get("prima.html"))===norm(get("dopo.html")));
'
```

Stesso motivo per cui va usato un parser e non un regex quando si tocca il
testo del JS: `//` compare dentro gli URL, `/*` dentro le stringhe, e i regex
letterali del Comparatore (`/(const\s+confidence...)/`) verrebbero massacrati.

Il giro completo (una partita vera) richiede rete verso PitchAPI: se non ce
l'hai, **dillo** invece di dichiarare verificato quello che non lo è.

## Stile

**Il JS dei due file non ha commenti, e non è un caso.** Erano ~1000 righe su
4400 (26% del codice): la spiegazione sta qui in `AGENTS.md`, il codice resta
leggibile a schermo. Se aggiungi qualcosa che ha bisogno di essere spiegato,
la spiegazione va **in questo file**, nella sezione che le compete, non sopra
la riga.

Le uniche eccezioni sono **dodici marcatori, sedici righe in tutto**, nei punti
dove una modifica in buona fede rompe tutto in silenzio: le tre righe che il Comparatore aggancia
per testo, la convenzione di `k`, `RESID_ALPHA` a zero, la provenienza di
`OL_BETA` e delle rette della confidence, il `k` fisso dell'Ordered Logit, e
tre agganci lato Comparatore. Sono una riga l'una e rimandano qui. Se ne
aggiungi una, che sia perché *senza* quella riga qualcuno romperebbe qualcosa,
non perché il codice è complicato.

I commenti CSS (etichette di sezione, ~1.9 KB in tutto) e i marcatori HTML
`<!-- STEP 1 -->` restano: servono a navigare file da 2000 righe e non pesano.

Il resto:

- Testi UI **in italiano**, senza accenti nelle stringhe JS di servizio (il
  file gira anche incollato dentro `new Function`).
- Nessuna dipendenza esterna, nessun CDN. Tutto inline.
- File singoli e grossi: si modificano con edit puntuali, non riscritture.
- La storia dei perché è nei messaggi di commit e nel codice pre-ripulitura
  (commento in testa a `scanner.html` fino al commit `cd51a69`). `git log -S`
  su una costante trova quando e perché è cambiata.

## Git

Branch di lavoro `claude/*`, mai push diretto su `main`. Commit in italiano,
con i numeri della misura che giustifica il cambiamento quando c'è.
