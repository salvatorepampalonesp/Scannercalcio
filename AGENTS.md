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

**Build corrente: `0905-b16`.** Scanner e Comparatore devono coincidere, e sul
Comparatore il badge sotto la dropzone deve uscire **verde** dopo aver trascinato
lo Scanner. Il branch di lavoro è `claude/scanner-stat-optimization-sgs62u`;
`main` è indietro (fermo al merge della PR #1, cioè al `0905-b2`), quindi
**scaricare i file dal branch, non da `main`**.

### Dove siamo

L'**1X2 funziona** (48–49% di pick azzeccati contro il 39–42% del «gioca sempre in
casa», e la fascia ≥60% rende il 71–78%). I **mercati gol** erano il muro: il
lambda del Dixon-Coles sull'Over 2.5 fa 0.554 / 0.495 / 0.501 per lega, cioè quasi
il caso fuori dalla LaLiga. Il `b12` li porta a 0.572 / 0.514 / 0.521 usando i
tiri in porta previsti come seconda stima del lambda — vedi *I gol*.

La sorpresa dell'ultimo giro è che i **mercati sui numeri discriminano meglio dei
gol**: cartellini ~0.57 di AUC, tiri in porta ~0.56, corner ~0.53. Sono anche i
meno guardati.

**Tre strade chiuse da misure, non da opinioni** (i numeri in *Cosa è già stato
provato*): prevedere meglio le stats avanzate — siamo al tetto; usare le stats per
calibrare la forza dell'avversario — si fa già, e non resta niente oltre;
sistemare il KNN — la premessa è vera ma ridondante, il Dixon-Coles estrae la
stessa informazione meglio.

### La cronologia

| build | cosa |
|---|---|
| `b2` | shrinkage per metrica al posto dello 0.35 fisso; correzione residuale sull'1X2 |
| `b3` | correzione residuale **spenta** (`RESID_ALPHA = 0`): non reggeva fuori campione |
| — | via i commenti dal JS (26% del codice); verifica per confronto di AST |
| `b4` | 34 metriche nuove da `/advanced` (zero chiamate in più), tipi `volume`/`additivo`, Comparatore che usa le previsioni del motore |
| `b5` | `STAT_SHRINK_TABLE` rifatta su 1133 partite, tre leghe |
| `b6` | revisione UI: testo nero su nero, card diagnostica di troppo, `skellamPMF` morta |
| `b7` | via il confronto col book, i resti del KNN nell'ensemble, tre metriche a segnale zero |
| `b8` | narrative che confrontano le due squadre, KNN delle formazioni leggibile, `xg_sp_ag` |
| `b9` | `sum_sot` sui lambda gol; salto data dell'Elo reso continuo |
| `b10` | mercati sui numeri: shrinkage tarato, dispersione ristretta, più linee; Progressione Storica rifatta |
| `b11` | il backtest boccia metà del `b9` e del `b10`: `_base` usata come media di lega |
| `b12` | tre leghe: i gol confermati; la sovradispersione dei mercati veniva dalla **baseline**, non da `k` |
| `b13` | l'Elo entra nell'1X2 inclinando i lambda: batteva il modello e non era usato |
| `b14` | **cinque leghe**: Bundesliga e Ligue 1 confermano l'Elo fuori campione, il peso sale a 0.75 |
| `b15` | le differenze fra leghe erano rumore; la pendenza dei mercati va misurata **dentro** la lega |
| `b16` | **lo squilibrio della partita prevede i cartellini**: AUC 0.562 → 0.593, a costo zero |

Le tre build finali hanno una storia sola e va letta in *La baseline di coppia*:
tre tentativi svuotati dallo stesso malinteso.

### Il salto data dell'Elo (`b9`, e non è più stato toccato)

Era una funzione a gradini, `min(0.9, 0.3*ceil(giorni/365))`: 61 giorni e 11 mesi
ricevevano la stessa regressione del 30%, e a 1.01 anni si saltava al 60%. Ora è
continua, `0.9*(1 - exp(-(giorni - soglia)/110))` con soglia a 45 giorni, quindi
parte da zero alla soglia senza scalino: il salto massimo in un giorno passa da
**0.300 a 0.008**. La costante 110 è scelta perché a **90 giorni** (una pausa
estiva) la curva dia **0.302**, cioè riproduca il valore che la vecchia funzione
usava nell'unico regime che si presenta davvero.

Misurato sul panel: nelle tre leghe 2025/26 l'intervallo massimo fra due partite
della stessa squadra **dentro la stagione è 28.8 giorni**, e nessuno supera i 30.
Quindi **la correzione non scatta mai in stagione** — la soglia a 45 ha 16 giorni
di margine — e i regimi che contano sono la pausa estiva (75–105 giorni) e
l'assenza dalla lega. Attenzione: `buildGlobalElo` filtra per `_chosenLeagueId`,
quindi una neopromossa non ha un Elo vecchio da regredire, parte da 1500.

Nei backtest di una sola stagione questa modifica è **invisibile per costruzione**:
se un giro non mostra differenze sull'Elo, è il comportamento atteso.

### La prossima cosa da fare, in ordine di rapporto valore/rischio

1. **Continuare sui cartellini.** Il `b16` ha preso il primo pezzo (lo squilibrio,
   AUC 0.562 → 0.593). Restano: l'**arbitro** — `/v1/matches/{id}` lo espone e il
   nome è già in `globalLeagueMatchesCache`, ma i cartellini delle sue partite
   passate no, quindi servirebbero ~15 chiamate in più per profilarlo; la
   **posizione in classifica** (calcolabile a costo zero dai punteggi già in
   cache); e lo stesso effetto squilibrio sui **tiri in porta**, oggi a 2.8 sigma
   con una lega discorde.
2. **Capire la Premier sui tiri in porta**: pendenza 0.10–0.20 contro 0.77 in
   LaLiga e 0.35 in Serie A. O ha qualcosa di diverso, o è rumore.
3. ~~Capire perché il Dixon-Coles è cieco sull'Over in Premier e Serie A~~ —
   **domanda mal posta**, le cinque leghe sono indistinguibili (p = 0.19). Vedi
   *Il modello non fallisce in una lega più che in un'altra*. La domanda giusta
   resta quella di sempre: il lambda correla **+0.087** col totale dei gol, e
   nessuna feature provata lo alza. È il muro dell'Over/Under, punto.
4. **Verificare la pendenza dell'Elo** (`penH`/`penA`, ±8% sui lambda): non è mai
   stata misurata, e ora che il livello entra dall'inclinazione potrebbe essere
   ridondante. Serve esportarla nel CSV.
5. **`GOALS_SOT_W` e `ELO_1X2_W` alla sesta lega.** Il backtest dice 0.50, ma 0.75 e 1.00 sono
   migliori di un margine non distinguibile (±0.030 di errore standard). Il CSV
   ricostruisce tutti i pesi senza rilanciare il motore: basta un'altra lega.
6. **L'endpoint `/shots`.** Il candidato più serio per la forma della
   distribuzione dei gol, con la ragione spiegata in *Il muro dell'Over/Under*.
   Costa una chiamata in più per partita.
7. **Un ancoraggio di lega per i falli**, che oggi non ce l'hanno (il rapporto coi
   gol varia del 28% fra leghe, quindi `MARKET_PER_GOAL.fouls = null`).
8. **La tab «racconto»**: mostrare uno scenario invece di una distribuzione. Idea
   arrivata da fuori, già misurata e in parte bocciata — vedi *Lo scenario
   singolo*. La parte che sopravvive è la card dei risultati esatti.
9. **Ricontrollare `avg_def_x`**: pendenza 0.06, la previsione è quasi scorrelata
   dal reale. O è un problema di forma del modello, o la metrica va tolta.
10. **Togliere `vaep_def`, `pv_def`, `sca_def`** dalle feature: correlazione
   previsto/reale a zero su 1133 partite. Il fix additivo che le ha rese
   calcolabili era giusto, ma quello che si vede è rumore.

Già fatte e da non riaprire: togliere il KNN dall'ensemble (`b7`), `sum_sot`
nell'Over/Under (`b9`, riformulato nel `b12`), tarare i `k` di mercato (`b12`).

**Il campione di riferimento** per qualunque nuova taratura è ora: Serie A +
Premier + LaLiga + **Bundesliga + Ligue 1** 2025/26, **1743 partite**, esportate
dal Comparatore `0905-b14` o successivo. Meno di due leghe non basta — è l'errore
che ha prodotto quattro falsi positivi di fila — e **le AUC dei mercati gol non si
leggono mai aggregate fra leghe**.

Bundesliga e Ligue 1 sono le uniche due su cui **non è mai stata tarata nessuna
costante**: finché resta così, sono il miglior banco di prova che abbiamo. Se le
usi per tarare qualcosa, scrivilo qui, perché da quel momento non lo sono più.

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

### Sistemato (b6 → b8)

- **Testo nero su nero in quattro riquadri** (qualità del tiro, fase di non
  possesso, funnel, punti attesi): era `color:#1c1c1e` su `background:var(--panel2)`,
  un residuo di quando l'app era a tema chiaro. Passati a `var(--txt)`. Stessa
  origine per i bordi pastello (`#ffe0b2`, `#ffcdd2`, `#e0f2f1`, `#e1bee7`),
  portati su `var(--line)`.
- **Card «Diagnostica predittore» rimossa**: era nata per capire perché
  `predictStat` collassava sulla baseline, problema risolto. `window.__PRED_DEBUG`
  resta esposto perché lo consuma la sezione diagnostica del CSV.
- **Confronto col book rimosso** (`b7`): markup, `calcValue` e la chiamata.
- **Resti dell'ensemble rimossi** (`b7`): `tvDist`, `wKnn`, `knnRel`, `nEffMin` e
  `sampleFactor` erano calcolati a ogni partita e nessuno li leggeva più.
  `probsKnn` invece **resta**: alimenta la card a schermo e il CSV.
- **`vaep_def`, `pv_def`, `sca_def` fuori da `ADV_SPEC`** (`b7`): correlazione
  previsto/reale misurata a zero su 1133 partite.
- **Le narrative parlano di entrambe le squadre** (`b8`): letalità e fase di non
  possesso nominavano solo la squadra di casa. Ora ogni riga è un confronto —
  chi tira meglio di quanto crea, chi spreca di più, chi tiene i reparti più
  stretti — e le palle inattive incrociano quanto una produce con quanto l'altra
  **concede** (`xg_sp_ag`, estratto da `b8`).
- **KNN a schermo leggibile** (`b8`): sei vicini invece di quattro, numerati,
  con la somiglianza in percentuale (il peso del kernel) e ogni statistica
  affiancata dallo scarto rispetto all'avversario di oggi, in verde sotto l'8%.
  Erano **già ordinati** per distanza crescente: mancava solo mostrarlo.
- **Residui del tema chiaro normalizzati** (`b6`–`b8`): `#1c1c1e`, `#eee`,
  `#ddd`, `#f8bbd0`, `#ffe0b2`, `#ffcdd2`, `#e0f2f1`, `#e1bee7` sostituiti dai
  token del tema.

### Coda: leggibilità e presentazione

- **Tabellone scommesse**: propone solo 1X / X2 / 12, mai gli altri mercati. È il
  sintomo del problema noto (l'1X2 discrimina, i gol molto meno), non un difetto
  della card. Da rivedere ora che i mercati sui numeri discriminano **meglio dei
  gol**: cartellini e tiri in porta meriterebbero di comparirci.
- **Doppie chance e gol con confidence**: tabella confusa e, sui gol, poggia su
  probabilità che discriminano poco.
- ~~**Progressione storica**~~ — **fatto nel `0905-b10`**: le quattro metriche
  mostrate erano proprio quelle su cui la forma recente non dice nulla.
  Sostituite con sei in cui lo scostamento recente si è dimostrato persistente,
  e aggiunta la spiegazione in card. Vedi *I mercati sui numeri*.
- **Mega-prompt**: da rifare quando le statistiche giuste saranno decise —
  più dati, percentuali ed ensemble, meno prosa.

### Coda: da controllare nel modello

- ~~**Handicap asiatico**~~ — **verificato**: le linee a quarti si spezzano
  correttamente, `pHome + pRefund + pAway` fa 1 su tutte le linee da −1.5 a +1.5,
  la copertura è monotona nell'handicap e AH −0.5 coincide con `p1`, AH +0.5 con
  `p1 + pX`. Attenzione a un'asserzione sbagliata facile da rifare: **AH −0.75 sta
  fra −1 e −0.5**, non fra −0.5 e +0.5.
- ~~**Multigol**~~ — **verificato**: `0-1 + 2-3 + 4+` fa 1, le fasce più larghe
  contengono quelle strette, `0-20` copre tutto per totali, casa e trasferta.
- ~~**Alta varianza e disciplina**~~ — **fatto nel `0905-b10`–`b12`**: era già
  relazionale (usava il concesso dall'avversario) ma senza shrinkage, e come
  probabilità valeva meno di sparare la media. Vedi *I mercati sui numeri*.
- ~~**Elo, salto data**~~ — **fatto nel `0905-b9`**, vedi *Stato del lavoro*. E nel
  `b13` l'Elo è finalmente **collegato all'1X2**: era il predittore migliore del
  motore e non veniva usato. Vedi *L'Elo nell'1X2*.
- **Markov** — `markovFlow` con rate dipendenti dal punteggio. Verificato solo
  negli invarianti (`p1+pX+p2` fa 1, simmetrico scambiando i lambda, scarto
  massimo dal Dixon-Coles 0.035); **mai** verificato contro il backtest come
  modello a sé.
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
mercati sui gol: 1X2, doppia chance, GG, Over/Under multilinea, multigol,
risultati esatti, handicap asiatico. Nessuno di questi è calcolato per conto
proprio, ed è il motivo per cui una correzione ai lambda li migliora o li rompe
tutti insieme.

L'unica cosa **fuori** dalla matrice è `calcAdv`, che produce i mercati sui
numeri (corner, tiri in porta, cartellini, falli) con un proprio lambda e una
binomiale negativa: sono conteggi diversi dai gol e non escono dallo stesso
processo. Vedi *I mercati sui numeri*.

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

Subito prima di costruire la matrice, il totale dei lambda viene mediato con una
**seconda stima ricavata dai tiri in porta previsti** (`goalsSotCorrection`), e la
scala risultante moltiplica entrambi i lambda così il rapporto casa/trasferta non
cambia. È l'unica correzione esterna attiva sui gol: vedi *I gol*.

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

- **`_base` non è una media di lega, è una media della coppia.** Usarla come
  denominatore di qualcosa che le correla (0.84 sui tiri in porta) cancella il
  segnale; usarla come moltiplicatore fa entrare due volte l'effetto coppia e
  gonfia le previsioni. Ha svuotato due modifiche di fila. Vedi *La baseline di
  coppia*.
- **Una previsione fatta da media + scarto va scomposta prima di ritararla.** Sui
  mercati statistici la dispersione di troppo veniva dalla baseline (sd 0.81) e
  non dal termine attacco/difesa (sd 0.11), ma la pendenza da sola non lo diceva:
  abbassare `k` è stato un giro a vuoto. Guardare le sd delle componenti prima.
- **Prima di spiegare una differenza fra leghe, misurare se esiste.** Con una
  stagione a lega l'errore standard di una correlazione è ~0.053: due leghe
  possono distare 0.15 per puro caso. Prendere il minimo di cinque stime rumorose
  e cercarne la causa è confronto multiplo, e il calcio offre un aneddoto
  plausibile per qualunque ipotesi. Ci sono cascato io nel `b14`. Vedi *Il modello
  non fallisce in una lega più che in un'altra*.
- **Le etichette di riga del CSV devono essere uniche.** Tre sezioni diverse
  usavano `applicata`, due `peso w` e due `ha toccato il cap`: un parser che
  cerca per etichetta prende la prima e legge la sezione sbagliata **senza
  accorgersene**. Corretto nel `b14` con un prefisso (`Tiri:`, `Elo:`). Le uniche
  ripetizioni legittime sono le metriche nelle sezioni CASA e TRASFERTA, che vanno
  in coppia per costruzione.
- **Non leggere mai l'AUC dei mercati gol aggregata fra leghe.** Con base rate
  diversi (Premier 55.1% di Over 2.5, Serie A 45.7%) l'aggregato dava 0.531 dove
  dentro ogni lega era 0.495 e 0.500, cioè caso puro. Sempre per lega.

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
| Stimare attacco/difesa su **tutta la lega** invece che su 15 partite a squadra | **non serve** | AUC 0.681 contro 0.680 del modello attuale; mescolato 0.688 contro lo 0.690 che l'Elo dà già. Sul totale gol è perfino peggio. Vedi *L'Elo nell'1X2* |
| Individuare le partite che finiranno pari | **non regge** | `pX` ha AUC **0.487** (SE ±0.020) su 1133 partite: nessuna capacità di distinguere. Anche `-\|p1−p2\|` e `-max(p1,p2)` stanno a 0.495–0.498. La calibrazione è giusta in media (27.6% detto contro 25.9% reale) ma piatta a fasce. Vedi *Lo scenario singolo* |

**L'unica cosa che ha superato la verifica incrociata su tre leghe:**

| idea | esito | numeri |
|---|---|---|
| `sum_sot` (tiri in porta previsti, somma delle due squadre) sull'Over 2.5 | **regge** | AUC 0.581 / 0.531 / 0.546 sulle tre leghe nel panel, e **0.579 / 0.534 / 0.537 confermate in produzione** sul backtest `b11`. Batte il lambda del Dixon-Coles in tutti e tre gli holdout |

Tre cose da notare. La prima: `sum_sot` **da solo** batte il lambda del
Dixon-Coles **e** la combinazione dei due — la stessa cosa che si rivede
nell'A/B sul peso, dove l'AUC cresce fino a `w = 1.00`. La probabilità Over della
matrice non aggiunge quasi niente sopra i tiri in porta previsti.
La seconda: `sot` non è una metrica «avanzata», viene da `/stats` ed era
disponibile da sempre. La terza: è l'unica idea sopravvissuta su una decina
provate, ed è servita **una riformulazione completa** (da moltiplicatore a media
di lambda) perché il segnale arrivasse davvero al motore — vedi *La baseline di
coppia*.

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

### Il muro dell'Over/Under, e dove siamo adesso

Il lambda del Dixon-Coles da solo ha AUC **0.554 / 0.495 / 0.501** (LaLiga /
Premier / Serie A): fuori dalla LaLiga la probabilità Over della matrice non
distingue una partita dall'altra. Il totale di gol lo azzecca in media (le linee
0.5, 1.5, 3.5, 4.5 sono calibrate entro 2–4 punti), quindi il problema non è mai
stato il **livello** dei lambda ma la **capacità di ordinare le partite**.

Il `b12` scavalca in parte il muro con i tiri in porta previsti (0.572 / 0.514 /
0.521, vedi *I gol*), ma il margine resta piccolo e nessuna delle altre feature
provate è sopravvissuta alla verifica incrociata.

L'ipotesi ancora non testata è che manchi la *forma* della distribuzione: dieci
tiri da 0.10 xG e due da 0.50 danno lo stesso lambda ma distribuzioni di gol
diverse. Servirebbe l'endpoint `/v1/matches/{id}/shots`, che dà ogni tiro con
`expected_goals`, `is_on_target`, `is_inside_box`, `situation` e coordinate. Costa
una chiamata in più per partita storica (da 4 a 5, +25% sul batch) ed è il
candidato più serio rimasto. Nota che `sum_sot` funziona già come *proxy* grezzo
della stessa informazione: i tiri in porta sono la coda buona della distribuzione
dei tiri, ed è probabilmente per questo che è l'unica cosa che ha retto.

## I gol: la seconda stima del lambda dai tiri in porta

`sum_sot` (la somma dei tiri in porta previsti delle due squadre) è l'unica
feature sopravvissuta a tre leghe. Da sola fa **AUC 0.579 / 0.534 / 0.537**
sull'Over 2.5 dove il lambda del Dixon-Coles fa **0.554 / 0.495 / 0.501**, cioè
quasi il caso fuori dalla LaLiga.

Entra nel motore **non come moltiplicatore ma come seconda stima del lambda**:

```js
lam_sot = sum_sot / SOT_PER_GOAL          // SOT_PER_GOAL = 3.25
lam_mix = (1 - w) * lam_DC + w * lam_sot  // GOALS_SOT_W = 0.50
scala   = lam_mix / lam_DC                // cap ±20% (GOALS_SOT_CAP)
```

La scala moltiplica **entrambi** i lambda, quindi il rapporto casa/trasferta della
matrice non cambia e tutti i mercati che escono dal Dixon-Coles si muovono
insieme.

**Perché non un moltiplicatore.** Un fattore limitato lascia il *rango* dominato
da `lam_DC`, che sull'Over 2.5 vale 0.495/0.500 cioè niente: per smuoverlo
servirebbe `alpha 5` e cap ±90%, e il Brier passerebbe da 0.2537 a **0.3151**.
Una media pesata sposta il rango **tenendo il livello**.

Misure su 1133 partite, AUC Over 2.5 per lega:

| w | LaLiga | Premier | Serie A | Brier |
|---|---|---|---|---|
| 0.00 | 0.554 | 0.495 | 0.501 | 0.2518 |
| **0.50** | **0.572** | **0.514** | **0.521** | **0.2490** |
| 0.75 | 0.576 | 0.524 | 0.529 | 0.2486 |
| 1.00 | 0.580 | 0.532 | 0.532 | 0.2487 |

Migliora **ogni** linea Over (0.5, 1.5, 2.5, 3.5, 4.5) su AUC e Brier insieme, e
il livello resta calibrato a ogni `w` (0.5: 92 vs 93 · 1.5: 72 vs 76 · 2.5: 47 vs
50 · 3.5: 26 vs 25 · 4.5: 12 vs 12).

**Perché `w = 0.50` e non 1.00.** L'errore standard dell'AUC per lega è ±0.030,
quindi il passo da 0.50 a 0.75 (+0.007 in media) non è distinguibile da zero. In
più l'unica linea con un massimo interno è l'Over 3.5 (0.543 a w 0.50–0.75 contro
0.538 a w 1.00).

**Le due leghe nuove hanno confermato lo 0.50** (`b14`, 1734 partite, cinque
leghe). Il Brier ha il minimo a w 0.50 (0.2469 contro 0.2486 a w 0), e il test
appaiato sul logloss dà **+2.18 sigma** per w 0 → 0.50.

Guardando l'AUC per lega sembrava che la correzione servisse solo dove il modello
è debole (Premier e Serie A) e fosse inutile o dannosa in Bundesliga e Ligue 1.
**Era una lettura sbagliata**, e la correzione di quella lettura è documentata in
*Il modello non fallisce in una lega più che in un'altra*: il test di omogeneità
sui guadagni per lega dà **Q = 3.93 su 4 gradi di libertà, p = 0.42**. Le leghe
non rispondono diversamente; il guadagno comune è +0.0037 di logloss e lo scarto
fra leghe è compatibile col caso.

`window.GOALS_SOT_W` è esposto e il CSV ricostruisce w = 0 / 0.25 / 0.5 / 0.75 /
1.0 senza rilanciare il motore.

`SOT_PER_GOAL = 3.25` è misurato (LaLiga 3.19, Premier 3.04, Serie A 3.33) e tocca
solo il **livello**, mai il rango. Il cap ±20% ha morso sullo **0.18%** delle
partite: è un paracadute inerte, come dev'essere.

## L'Elo nell'1X2: il pezzo migliore del motore non era collegato

Trovato rispondendo alla domanda «correggiamo l'Elo?». La risposta è che l'Elo non
andava corretto: **andava usato**.

### Cosa succedeva

`buildGlobalElo` è strutturalmente sano: HFA stimato dalle vittorie reali della
lega, K adattivo (30 sotto le 15 partite, poi 20), moltiplicatore per scarto di
gol, cronologico, a somma zero, con la regressione per inattività sistemata nel
`b9`. Ma del suo risultato il modello usava **solo la pendenza**:

```js
trendH = media(ultimi 5 Elo) − media(dal 5° al 15°)
penH   = clamp(trendH / 1200, ±0.08)
lamH  *= (1 + penH)
```

Il **livello** del rating — cioè tutto il punto di un Elo — non entrava da nessuna
parte. E il livello è la parte che sa qualcosa:

| | AUC sulla vittoria casa | LaLiga | Premier | Serie A |
|---|---|---|---|---|
| differenza Elo | **0.689** | 0.697 | 0.671 | 0.702 |
| `p1` dell'ensemble | 0.662 | 0.688 | 0.625 | 0.663 |

L'Elo **batte il modello in tutte e tre le leghe**, e correla meglio con la
differenza reti (+0.405 contro +0.367).

### Perché vince, e perché non è magia

L'Elo pesca dalla **stessa** storia del modello, ma la comprime meglio: propaga i
risultati di *tutta* la lega in modo transitivo (chi batte chi, e chi ha battuto
chi), mentre le forze attacco/difesa del Dixon-Coles si stimano sulle ~15 partite
di ciascuna delle due squadre e basta. Non è informazione nuova, è **più dati
sullo stesso segnale**.

Sembrava seguirne che la strada lunga fosse **stimare attacco e difesa su tutta
la lega** invece che su 15 partite a testa, e che l'Elo fosse solo la scorciatoia.
**Provato, e non è così.** Un modello di Poisson attacco/difesa a punto fisso,
stimato in walk-forward su *tutte* le partite passate della lega con lo stesso
decadimento a 106 giorni (i punteggi sono già in `globalLeagueMatchesCache`,
costo zero chiamate):

| predittore | AUC vittoria casa | Bun | LaL | Lig | Pre | Ser |
|---|---|---|---|---|---|---|
| `p1` del modello (15 partite/squadra) | 0.680 | 0.722 | 0.688 | 0.680 | 0.642 | 0.670 |
| differenza Elo | **0.689** | 0.747 | 0.684 | 0.656 | 0.675 | 0.688 |
| attacco/difesa su tutta la lega | 0.681 | 0.759 | 0.665 | 0.645 | 0.658 | 0.672 |

Mescolato col modello arriva a **0.688** al suo meglio (w 0.50), contro lo
**0.690** che l'inclinazione dall'Elo dà già. Sul **totale dei gol** va perfino
peggio del modello attuale: corr +0.114 contro +0.153, AUC 0.551 contro 0.555.

**Conclusione: la stima delle forze non è il collo di bottiglia.** Con più dati
sullo stesso segnale non si va oltre; quello che l'Elo aggiunge, lo aggiunge tutto
lui. Non riaprire questa strada senza un'idea diversa da «più partite».

### Come è collegato

Non sovrascrivendo l'1X2 — quello romperebbe il principio della matrice unica —
ma **inclinando il rapporto fra i lambda tenendo fisso il totale**:

```
lgModel  = logit( p1 / (p1 + p2) )         dalla matrice attuale
lgElo    = (Elo_casa − Elo_trasferta + HFA) / 173.72
lgTarget = (1 − w) · lgModel + w · lgElo    w = ELO_1X2_W = 0.50
```

poi `eloTiltLambdas` cerca per bisezione l'inclinazione `t` tale che
`lamH·e^t`, `lamA·e^−t` (riscalati perché la somma resti identica) producano
esattamente `lgTarget`. Ventiquattro iterazioni su una matrice 7×7: costo
trascurabile.

Il 173.72 è `400/ln(10)`, la conversione esatta da punti Elo a log-odds: **non è
una costante tarata**, è la definizione della scala Elo.

**Cosa si muove e cosa no.** Il totale dei lambda è identico al bit, quindi
Over/Under non si sposta di un punto. Si spostano 1X2, doppia chance, handicap
asiatico, risultati esatti — e il **GG**, che dipende dallo squilibrio e non solo
dal totale: su un esempio con Elo +250 va da 55.9% a 51.8%. È corretto che si
muova, una partita più squilibrata ha meno GG.

### Le misure

Tenendo `pX` del modello (che è calibrata) e ribilanciando solo 1 contro 2:

Misure su **1743 partite e cinque leghe** (`b13`), di cui **Bundesliga e Ligue 1
mai usate per tarare nulla**:

| w | pick giusti | Brier 1X2 | logloss | Bun | LaL | Lig | Pre | Ser |
|---|---|---|---|---|---|---|---|---|
| 0.00 | 50.8% | 0.6108 | 1.0198 | 52.1% | 52.8% | 52.1% | 48.9% | 48.4% |
| 0.50 | 51.5% | 0.6034 | 1.0094 | 53.8% | 51.2% | 52.5% | 48.1% | 52.6% |
| **0.75** | **51.7%** | **0.6018** | **1.0073** | **55.4%** | 51.2% | 51.5% | **49.7%** | 51.6% |
| 1.00 | 51.5% | 0.6015 | 1.0072 | 53.8% | 52.0% | 51.8% | 48.4% | 52.1% |

**Sulle sole due leghe nuove** (610 partite): pick 52.1% → **53.4%**, Brier
0.6012 → **0.5944**, logloss 1.0065 → **0.9965**, con l'ottimo di nuovo a 0.75 su
tutte e tre le metriche.

Test appaiato sul logloss, che è quello che conta:

| confronto | tutte | solo leghe nuove |
|---|---|---|
| w 0.00 → 0.50 | **+5.02 sigma** | +2.55 sigma |
| w 0.50 → 0.75 | +2.09 sigma | +0.91 sigma |
| w 0.75 → 1.00 | +0.14 sigma | −0.21 sigma |

Quindi: **che l'Elo serva è fuori discussione** (5 sigma, replicato su leghe
mai viste). Che 0.75 batta 0.50 è più tenue — 2 sigma aggregate, meno di 1 fuori
campione — ma è l'argmin ovunque, l'ottimo è **interno** (1.00 è peggio) e nessuna
metrica preferisce 0.50. Alzato a **0.75** nel `b14`.

C'era anche una verifica temporale sul `b13` a tre leghe (taratura sulla prima
metà di stagione, verifica sui 567 match della seconda): pick 48.3% → 48.9%,
Brier 0.6194 → 0.6107, logloss 1.0317 → 1.0202.

`window.ELO_1X2_W` è esposto e il CSV ricostruisce w = 0 / 0.25 / 0.5 / 0.75 / 1.0
dai soli log-odds, senza rilanciare il motore.

**In produzione** l'inclinazione si applica al 100% delle partite, ha mediana
−0.001, 5°–95° percentile −0.103 / +0.109 e massimo assoluto **0.215** contro un
cap a 0.60: il paracadute non ha mai morso.

### Cosa resta da capire

- **La pendenza (`penH`/`penA`) è ancora lì e non è mai stata verificata.** Ora
  che il livello entra dalla porta principale, il ±8% sulla pendenza potrebbe
  essere ridondante o peggio. Va misurato: serve esportarla nel CSV, oggi non c'è.
- **L'HFA stimato varia molto fra leghe**: LaLiga 78, Premier 49, Serie A 47. È
  plausibile, ma non è mai stato verificato contro il vantaggio campo reale.

## Lo squilibrio e i cartellini: il guadagno più grande, e gratis

Il risultato migliore di tutta la serie `b9`–`b16`, trovato cercando cosa manca al
mercato che discrimina meglio.

**Le partite squilibrate hanno meno cartellini di quanti il modello ne preveda.**
Correlazione fra `|differenza Elo|` e il residuo dei gialli: **−0.138** su 1743
partite, con lo **stesso segno in tutte e cinque le leghe**.

| | coefficiente | SE | sigma |
|---|---|---|---|
| Bundesliga | −0.00294 | 0.00137 | −2.2 |
| LaLiga | −0.00306 | 0.00132 | −2.3 |
| Ligue 1 | −0.00405 | 0.00144 | −2.8 |
| Premier | −0.00313 | 0.00140 | −2.2 |
| Serie A | −0.00429 | 0.00115 | −3.7 |
| **comune** | **−0.00354** | | **−5.8** |

Test di omogeneità: **Q = 0.97 su 4 gradi di libertà, p = 0.914**. È lo stesso
effetto ovunque, e questa volta il test lo conferma invece di smentirlo.

Gialli reali per quintile di squilibrio (Q1 = partite più equilibrate):

| | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|
| tutte | 4.33 | 3.93 | 3.72 | 3.81 | 3.21 |

Fra una partita equilibrata (scarto Elo 20) e una squilibrata (300) c'è quasi **un
cartellino intero** di differenza, su una base di 3.8.

### Come è implementato

```js
lYel = lYel_grezzo + CARDS_ELO_B * (|Elo_casa − Elo_trasferta| − scarto_medio_di_lega)
```

`CARDS_ELO_B = −0.0035`, e lo **scarto medio di lega** è calcolato al volo come
media di `|r_i − r_j|` su tutte le coppie di squadre in `ELO.table`: si
auto-calibra, non è una costante. Cap al ±30% di lambda, che non morde mai nei
dati (lo scarto Elo arriva a ~400, l'aggiustamento a ~1 cartellino su 3.8).

### Le misure

| coefficiente | pendenza dentro lega | Brier | Bun | LaL | Lig | Pre | Ser |
|---|---|---|---|---|---|---|---|
| 0 (com'era) | 0.68 | 0.20245 | 0.1991 | 0.2270 | 0.1895 | 0.2047 | 0.1889 |
| −0.0020 | 0.80 | 0.20032 | | | | | |
| **−0.0035** | **0.75** | **0.19968** | **0.1974** | **0.2237** | **0.1869** | **0.2035** | **0.1839** |
| −0.0050 | 0.65 | 0.19983 | | | | | |

Ottimo **interno** esattamente sul coefficiente stimato, e il Brier migliora in
**tutte e cinque le leghe**. L'AUC media delle cinque leghe:

| linea | prima | dopo |
|---|---|---|
| Over 3.5 | 0.562 | **0.593** |
| Over 4.5 | 0.567 | **0.590** |
| Over 5.5 | 0.580 | **0.599** |

Trenta punti base di AUC: più di qualunque altra cosa ottenuta in questa serie, e
non costa una chiamata in più perché l'Elo è già calcolato.

### Perché solo i cartellini

Lo stesso test sugli altri mercati:

| mercato | corr col residuo | sigma | segni per lega |
|---|---|---|---|
| gialli | −0.138 | −5.8 | **tutti negativi** |
| tiri in porta | +0.067 | +2.8 | 4 su 5 positivi |
| corner | +0.041 | +1.7 | 3 su 5 positivi |

Sui **corner** i segni si ribaltano: scartato. Sui **tiri in porta** l'effetto è a
2.8 sigma con 4 leghe su 5 concordi — **candidato, non applicato**: la regola è che
il segno regga ovunque, ed è la regola che ha evitato quattro falsi positivi.
Riprovarlo alla sesta lega.

## Il modello non fallisce in una lega più che in un'altra

Sezione nata da un errore mio, scritto in questo file e corretto un'ora dopo.
Vale la pena tenerla perché l'errore è di quelli che si rifanno.

**La domanda sbagliata era:** «perché il Dixon-Coles non discrimina l'Over in
Premier e Serie A (AUC 0.493 e 0.501) mentre in Bundesliga, Ligue 1 e LaLiga fa
0.538–0.556?»

**La risposta è che non è vero.** Correlazione fra lambda previsto e gol reali,
una stagione per lega:

| lega | n | corr | z di Fisher | SE |
|---|---|---|---|---|
| Bundesliga | 305 | +0.168 | +0.169 | 0.058 |
| LaLiga | 377 | +0.134 | +0.135 | 0.052 |
| Serie A | 378 | +0.083 | +0.083 | 0.052 |
| Ligue 1 | 305 | +0.065 | +0.065 | 0.058 |
| Premier | 378 | **−0.004** | −0.004 | 0.052 |

Test di omogeneità: **Q = 6.14 su 4 gradi di libertà, p = 0.19**. Le cinque leghe
sono **statisticamente indistinguibili**. La correlazione comune è **+0.087**, e
se fosse 0.087 ovunque, con ~350 partite a lega ci si aspetterebbe di vedere
valori sparsi fra −0.021 e +0.193 solo per caso: esattamente l'intervallo
osservato.

Stessa storia sul guadagno della correzione dai tiri: Q = 3.93 su 4, **p = 0.42**.

**Quindi la verità è meno interessante e più utile:** il lambda del Dixon-Coles
correla **+0.087 col totale dei gol, ovunque**. Non c'è una lega rotta da
riparare, c'è un modello che sull'Over è debole dappertutto. La forma della
relazione lo conferma — gol medi per quintile di lambda, tutte le leghe: nessuna
è monotona, e gli scarti fra quintili sono dell'ordine dell'errore standard di un
quintile (~0.20 gol su ~65 partite).

### L'errore, e come non rifarlo

Ho guardato cinque numeri, ho preso i due più bassi e ho chiesto «perché questi
due sono rotti». È **il confronto multiplo**: prendendo il minimo di cinque stime
rumorose si trova sempre qualcosa da spiegare, e la spiegazione sarà sempre
plausibile perché il calcio offre un aneddoto per ogni ipotesi (la Premier è più
imprevedibile, la Serie A è più tattica, e così via).

**Regola:** prima di spiegare una differenza fra leghe, misurare se la differenza
esiste. Un test di omogeneità su cinque correlazioni costa dieci righe di codice.
Con una stagione a lega (~350 partite) l'errore standard di una correlazione è
**1/√n ≈ 0.053**: due leghe possono distare 0.15 senza che voglia dire niente.

Questo vale anche al contrario: la stessa aritmetica dice che per **accorgersi**
davvero che una lega è diversa servono più stagioni, non più leghe.

## I mercati sui numeri: corner, tiri in porta, cartellini

**Sono i mercati che discriminano meglio.** AUC media delle leghe: cartellini
**~0.57**, tiri in porta ~0.56, corner ~0.53 — contro lo 0.53 dell'Over 2.5. Ci si
è arrivati in tre giri (`b10` → `b12`), due dei quali hanno curato la cosa
sbagliata: la storia è in *La baseline di coppia*, ed è la parte più utile da
leggere prima di toccarli.

### Come sono calcolati adesso

`calcAdv` produce un lambda per mercato in tre pezzi:

```
riferimento = MARKET_PER_GOAL[m] × (LG.avgH + LG.avgA)   // costante DENTRO la lega
lambda      = riferimento
            + MARKET_BASE_SHRINK[m] × (2·lg − riferimento)   // livello della coppia
            + (grezzo − 2·lg)                                // attacco vs difesa
```

dove `grezzo = predictStat(H,A,m,scope,k) + predictStat(A,H,m,scope,k)` e `lg` è
la media dei due `_base[m]`. Lo `scope` è `role` se **entrambe** le squadre hanno
almeno 3 partite nel ruolo, altrimenti `overall` per tutte e due.

Le tre costanti, e da dove viene ciascuna:

| | `MARKET_SHRINK_K` | `MARKET_BASE_SHRINK` | `MARKET_PER_GOAL` |
|---|---|---|---|
| corner | 0.07 | 0.50 | 3.61 |
| tiri in porta | 0.30 | 0.55 | 3.20 |
| gialli | 0.10 | 0.75 | 1.48 |
| falli | 0.15 | 1.00 | `null` |

- **`MARKET_SHRINK_K`** governa il termine attacco-vs-difesa. Cercato sul backtest
  a tre leghe: sui **corner** il Brier migliora monotonamente scendendo, cioè quel
  termine è rumore e va quasi spento; sui **tiri** c'è un ottimo interno fra 0.25 e
  0.40; sui **gialli** attorno a 0.09.
- **`MARKET_BASE_SHRINK`** è l'affidabilità della baseline di coppia (vedi sotto).
  Più alto su tiri e gialli **non per prudenza sul modello ma per prudenza
  sull'ancoraggio**: l'esposizione all'errore del riferimento vale `(1−c)`.
- **`MARKET_PER_GOAL`** ancora il riferimento ai gol di lega, che
  `computeLeagueParams` calcola su **tutte** le partite: è l'unica quantità
  davvero di lega che il motore abbia (corner e tiri non stanno nella lista
  partite, solo nei dettagli scaricati per le due squadre). Stabilità del rapporto
  fra le tre leghe: corner **1.1%**, tiri 8.7%, gialli 14.7%, **falli 28%** — per
  i falli non c'è ancoraggio utilizzabile, quindi `null` e la correzione si spegne
  da sola (`c = 1.00` fa lo stesso).

Effetto della cura, misurato su 1133 partite:

| | pendenza prima → dopo | Brier prima → dopo |
|---|---|---|
| corner | 0.55 → **0.96** | 0.2281 → **0.2251** |
| tiri in porta | 0.49 → 0.63 | 0.2275 → **0.2261** |
| gialli | 0.66 → 0.88 | 0.2077 → **0.2066** |

Sui corner migliora in tutte e tre le leghe; su tiri e gialli in due su tre, con
la terza ferma.

**Confermato su cinque leghe** (`b14`–`b15`, 1743 partite, Bundesliga e Ligue 1
mai usate per tarare): il livello è ottimo, bias aggregato **+0.8% sui corner,
−0.6% sui tiri, +0.7% sui gialli**.

Sulle pendenze però c'è un tranello che mi è costato una misura sbagliata.

**La pendenza va calcolata DENTRO la lega, non aggregata.** Il modello prevede una
partita in una lega; la calibrazione che l'utente vede è quella. Aggregando cinque
leghe con medie diverse, la variazione *fra* leghe gonfia la pendenza:

| | pendenza aggregata | **dentro la lega** | SE | sigma da 1 |
|---|---|---|---|---|
| corner | 0.88 | **0.63** | 0.20 | −1.8 |
| tiri in porta | 0.84 | **0.62** | 0.13 | −3.0 |
| gialli | 0.82 | **0.68** | 0.13 | −2.5 |

Quindi le previsioni sono ancora **più larghe del vero di circa un terzo**, non
quasi calibrate come sembrava. Ma il Brier è **piatto** in `c` fra 0.40 e 0.75 su
tutti e tre i mercati (differenze sotto 0.0004), quindi abbassare `c` non paga
sulle probabilità: paga sul **numero mostrato**, che è quello che l'utente legge
prima delle percentuali.

Per questo nel `b15` è stato mosso **solo il valore per cui il Brier lo chiedeva
insieme alla pendenza**: `sot` da 0.75 a **0.55** (Brier 0.22426 → 0.22392, il suo
minimo, pendenza 0.62 → 0.83). Corner e gialli restano dove sono, perché lì il
minimo del Brier coincide già col valore attuale e abbassare `c` lo peggiora.

Le pendenze per singola lega **non vanno interpretate**: Ligue 1 fa −0.14 sui
corner e Bundesliga 0.05 sui gialli, ma con errori standard di 0.64 e 0.40. Il
test di omogeneità dà p = 0.54, 0.12 e 0.16 sui tre mercati: **nessuna lega è
diversa dalle altre.**

### La dispersione: `negBinK`

`negBinK` finiva con `Math.max(2, ...)`. Un `k = 2` su una media di 9.5 corner
significa varianza 54 dove quella vera è 11. In pratica il pavimento non mordeva
quasi mai (su 4000 campioni da 30 partite il minimo osservato era 4.9), ma era una
toppa senza giustificazione. Ora la dispersione viene **ristretta verso Poisson**
col peso empirico-bayesiano `ex²/(ex²+2/n)`, dove `ex` è l'eccesso osservato e
`2/n` la sua varianza di campionamento: un eccesso piccolo rispetto al proprio
rumore viene assorbito, uno grande sopravvive, e nessun pavimento serve più.

Dispersione vera dei totali di partita:

| | media | varianza | `k` di lega |
|---|---|---|---|
| corner | 9.49 | 11.10 | 56 |
| tiri in porta | 8.38 | 8.36 | **nessuna sovradispersione** |

I tiri in porta **non sono sovradispersi**: la binomiale negativa lì può solo
peggiorare. Il campione da 30 partite la invocava a sproposito nel 38% dei casi
sui corner e nel 62% sui tiri, saltando fra due distribuzioni diverse per puro
rumore di campionamento.

### Quanto ci si può aspettare

Due misure indipendenti dicono di non farsi illusioni.

**Il tetto.** Se si conoscesse *esattamente* il lambda di ogni partita, l'AUC
massima sui corner sarebbe **circa 0.68**, con la probabilità di Over 9.5 che
spazia dal 27% al 68% fra il 10° e il 90° percentile: più margine che sui gol.
Il tetto assume però che il totale sia Poisson attorno al suo lambda; sui tiri in
porta la stessa formula dà tetto zero, smentita dal fatto che il modello fa 0.56.
La spiegazione è che i tiri sono **sotto**-dispersi rispetto a Poisson. Leggere il
tetto come indicativo.

**Metà della storia contro l'altra metà.** Costruendo due stime indipendenti dalla
stessa storia (partite pari e dispari), la correlazione fra le due è **+0.26 sui
corner**, e negativa in Serie A. Corretta per attenuazione, la correlazione col
reale che si avrebbe con storia infinita è circa **0.25**: reale, ma piccola.

### Un tranello da non ripetere

Minimizzare l'**errore di calibrazione** da solo porta a shrinkage estremi, perché
una previsione *piatta* ha calibrazione perfetta e valore zero. L'arbitro giusto è
il **Brier** — che penalizza sia la miscalibrazione sia l'appiattirsi — con la
**pendenza** a fare da controllo.

### Cosa resta aperto

- **La Premier sui tiri in porta** ha pendenza 0.10–0.20 contro 0.77 di LaLiga e
  0.35 della Serie A. O ha qualcosa di diverso, o è rumore: serve un'altra
  stagione.
- **I cartellini sono il mercato migliore e nessuno li ha guardati davvero.**
  Arbitro, derby, posizione in classifica sono tutte cose che PitchAPI potrebbe
  dare e che il modello oggi ignora.
- **I falli** restano senza ancoraggio di lega.

## La Progressione Storica: quali metriche ha senso mostrare

Le medie brevi (ultime 3, ultime 5) prevedono la partita successiva meglio della
media lunga? Misurato su tutte e 47 le metriche: **no, mai**. Per ognuna la media
lunga vince, con uno svantaggio del breve fra 0.02 e 0.09 di correlazione. La
colonna «Ult 3» era il peggior previsore della tabella ed era la prima che
l'occhio andava a leggere.

Ma «la forma non esiste» sarebbe la conclusione sbagliata. Con la regressione
`reale = a + b1 × media_lunga + b2 × (media_ultime5 − media_lunga)`, il
coefficiente `b2` dice se uno scostamento recente **persiste**. Mediana su 47
metriche: **+0.014** contro +0.73 della media lunga, cioè niente. Ma **12 metriche
su 47 hanno |t| > 2** dove il caso ne darebbe 2.4, e i segni non sono casuali:

- **persistono**: `prog_carries` t=+3.5, `switches` +2.9, `prog_carry_dist` +2.7,
  `tackles` +2.7, `ppda_den` +2.5, `carries_box` +2.4, `aerials` +2.4,
  `f3_entries` +2.2, `carry_dist` +2.0. Sono tutti **volumi strutturali**: quello
  che si sposta quando cambia il modulo, e resta spostato.
- **si invertono**: `sca` t=−2.2, `sca_live` −2.1, `sca_shot` −2.0. Sono metriche
  di **creazione**: una fiammata rientra.

Le quattro metriche che la card mostrava — NPxG fatti, NPxG subiti, Field Tilt,
PPDA — hanno `b2` di −0.01, +0.01, −0.06 e +0.06, con |t| sotto 1: esattamente le
quattro su cui la forma recente non dice nulla. Sostituite con sei delle nove
persistenti, e la card ora spiega il criterio.

## La baseline di coppia: l'errore che ha svuotato tre tentativi

La cosa più utile in questo documento. Tre modifiche di fila sono uscite vuote per
la stessa ragione, e nessuna delle tre era sbagliata *in sé*.

**`_base[k]` non è la media di lega.** È la media di *tutti i valori visti nelle
partite di quella squadra*, prodotti e concessi insieme. Su ~30 partite è
un'ottima stima del livello di quella squadra e dei suoi avversari — cioè contiene
un **effetto coppia**, non solo il livello della lega. Misurato:
`corr(sum_sot previsto, baseline usata) = +0.841`.

Per `predictStat` va benissimo: il rapporto `mine/lg` significa «quanto sopra il
proprio ambiente», ed è esattamente quello che serve. Ma usarla come se fosse una
media di lega l'ha rotta tre volte.

### 1. Un rapporto contro se stesso (`b9`)

La correzione gol faceva `ratio = sum_sot / (2 × lg)`. Dividere per una quantità
che correla 0.84 col numeratore cancella la variazione fra partite, cioè il
segnale:

| | AUC Over 2.5 (Premier / Serie A) |
|---|---|
| `sum_sot` grezzo | 0.534 / 0.537 |
| `sum_sot / baseline di coppia` | **0.469 / 0.542** |
| `sum_sot / media della lega` | 0.534 / 0.537 |

Il rapporto usciva quasi costante (5°–95° percentile 0.936–1.061 contro
0.846–1.165 con un riferimento sano) e la correzione spostava l'AUC di
**+0.0018 con errore standard ±0.021**. Zero.

### 2. Previsioni troppo larghe (`b10`)

Se `pred ≈ lg × (1 + k(...))` e `lg` varia con la coppia, la variazione della
coppia entra **due volte**. Pendenze in produzione contro lo 0.85 atteso dalla
simulazione: corner **0.60**, tiri in porta **0.30**, gialli **0.64**.

### 3. Abbassare `k`, che era la cura sbagliata (`b11`)

Vista la sovradispersione, i `k` sono stati moltiplicati per la pendenza. Non è
servito: corner da 0.60 a **0.55**, gialli da 0.64 a **0.66**. La scomposizione
`previsione = 2·lg + scarto` dice perché:

| | sd di `2·lg` | sd dello scarto | rapporto |
|---|---|---|---|
| corner | 0.812 | 0.105 | **8:1** |
| tiri in porta | 0.748 | 0.066 | **11:1** |
| gialli | 0.503 | 0.162 | **3:1** |

**Quasi tutta la dispersione veniva dalla baseline**, non dal termine che `k`
governa. Toccare `k` non poteva funzionare, e la pendenza da sola non lo diceva:
serviva guardare le **sd delle componenti**.

### La causa vera, e la cura

La baseline è sovradispersa perché è **una media di ~30 partite**, quindi porta il
proprio errore di campionamento. La teoria lo prevede quasi esattamente:

| | sd di una partita | SE della media su 30 | affidabilità attesa | pendenza misurata |
|---|---|---|---|---|
| corner | 3.32 | 0.605 | 0.44 | 0.55 |
| tiri in porta | 2.89 | 0.527 | 0.50 | 0.46 |
| gialli | 1.99 | 0.364 | 0.48 | 0.67 |

Circa **metà della varianza di `_base` è rumore di stima**, ed è per questo che la
pendenza gira attorno a 0.5: è la definizione di affidabilità.

La cura è restringere **la baseline**, non lo scarto, verso un riferimento che sia
davvero costante dentro la lega — e l'unico che il motore possiede sono i gol di
lega di `computeLeagueParams`. La formula e le costanti sono in *I mercati sui
numeri*; per i gol la stessa idea prende la forma della media pesata fra due
lambda, in *I gol*.

### La regola che ne esce

Prima di usare una quantità come «media di lega», chiedersi **su quante e quali
partite è calcolata**. Se viene dallo storico delle due squadre in campo, non è di
lega: è della coppia, correla con tutto il resto della previsione, e porta un
errore di campionamento che va restretto. Le uniche quantità davvero di lega che
il motore ha sono quelle costruite su `globalLeagueMatchesCache`, cioè `LG` e
l'Elo — tutto il resto passa dai dettagli scaricati per le due squadre.

## Lo scenario singolo: cosa si può prendere e cosa no

Idea vista su un post che pubblica una classifica di Champions «giocando ogni
partita una volta sola» invece di simulare: vince il favorito col suo risultato
più probabile, **X quando nessuna delle due supera il 43% di vincere**. Poi una
colonna ▲▼ dice di quanti posti il club finisce sopra o sotto il suo rango per
punti attesi.

**Attenzione a non leggerlo male:** il 43% non è una probabilità di pareggio
corretta al rialzo, è una **soglia sulla probabilità di vittoria**. La probabilità
di pareggio resta quella del modello, ~26%.

### Il problema che risolve è nostro

Sui 1133 match: **il pareggio è l'esito più probabile in 0 partite su 1133**. Una
regola «prendi il più probabile» produce una classifica con **zero** pareggi
quando in realtà sono il 25.9%. È la stessa cosa del «dà sempre 1-1»: la moda di
una distribuzione è un pessimo riassunto della distribuzione.

La cura è legittima e ha un nome: si sceglie la soglia perché il **conteggio**
degli esiti previsti corrisponda a quello atteso, invece di prendere l'argmax che
distrugge la distribuzione marginale. Sui nostri campionati la soglia equivalente
è **0.396**, vicina al loro 0.43 — la differenza torna, la fase campionato di
Champions ha più partite squilibrate.

### Ma quali partite finiscono pari è una monetina

| regola | precisione |
|---|---|
| `max(p1,p2) < soglia` (la loro) | 22.8% |
| `pX > soglia` | 23.3% |
| `\|p1−p2\| < soglia` | 22.9% |
| **294 prese a caso** | **25.9%** |

`pX` ha **AUC 0.487** nel prevedere i pareggi (SE ±0.020): zero capacità di
distinguere. E la calibrazione è piatta — fasce da 23.6% a 30.4% di pareggio
previsto danno 22.6 / 32.3 / 24.8 / 27.9 / **22.3**% di pareggi reali, senza
andamento. «Metterli sulle partite più equilibrate» assume che l'equilibrio
predica il pareggio, e non lo fa.

**Non riaprire questa parte** senza una feature nuova: il pareggio è il buco nero
del modello e non è colpa della soglia.

### La colonna ▲▼ è un artefatto

La regola dà 3 punti a **ogni** favorito marginale. Il 46% delle partite ha il
favorito fra il 39.6% e il 50%: lì assegna 3 punti dove il valore atteso è
**1.62**, cioè gonfia di 1.38 punti a partita. Su una stagione la correlazione fra
forza della squadra e scarto regola-vs-attesi è **+0.955** (Arsenal +36.8, Real
Oviedo −27.3).

Il gonfiaggio è quasi monotono nella forza, quindi la **classifica** si conserva
molto più dei punti: spostamento medio 0.7–1.7 posti. Il ▲▼ resta piccolo, ma
quel poco nasce da come il calendario di una squadra si posiziona rispetto alla
soglia — chi ha molte partite appena sopra prende tutto, chi le ha appena sotto
pareggia tutto. È una proprietà del **sorteggio**, non del club. Se ne facciamo
una versione nostra, quella colonna non ci va.

### Cosa vale la pena provare

**La versione classifica costa un batch intero.** Servono le probabilità di ogni
partita rimanente, cioè far girare il motore su tutto il calendario: è il
Comparatore, non lo Scanner. Ha senso solo come funzione del Comparatore, e solo
se qualcuno la vuole.

**La versione per partita è gratis ed è dove sta l'idea buona.** La card dei
risultati esatti mostra già la distribuzione (sei punteggi con la loro
probabilità), quindi tecnicamente fa la cosa giusta: il fastidio è che 1-1 è
sempre in cima, ed è **corretto** che lo sia. Il modo di renderla informativa non
è cambiare il criterio, è mostrare lo **scarto dal riferimento** invece del
livello: quali punteggi sono più probabili *in questa partita che in una partita
tipo di questa lega*. Un 3-1 all'1.8× della sua frequenza abituale dice qualcosa;
un 1-1 al 12% no, perché lo dice sempre. Stessa logica che ha risolto i mercati
sui numeri: il livello è ovvio, l'informazione sta nello scarto.

## Le costanti messe a mano: quali sono legittime e quali rompono i conti

Domanda posta dall'utente, e vale la pena rispondere per esteso perche' e' il
rischio principale di un modello scritto a mano. La risposta breve: **si', in
statistica si usano costanti fissate a priori, ma solo di tre tipi**, e ognuna va
classificata prima di scriverla nel codice. Quello che non rientra in nessuno dei
tre e' un grado di liberta' non stimato, cioe' una convinzione dell'autore
travestita da numero.

**Tipo 1 — il numero E' la procedura statistica.** Non e' arbitrario: e' un
metodo con un nome.
- `n/(n+k)` in `SHRINK_K` e `SHRINK_LAM_K` e' la media a posteriori di un
  modello normale-normale: **empirical Bayes**, lo stesso oggetto dello
  stimatore di James-Stein. Il `k` e' il rapporto fra varianza entro squadra e
  varianza fra squadre, e infatti va **stimato dai dati** (ed e' quello che
  `STAT_SHRINK_TABLE` e `MARKET_SHRINK_K` fanno).
- Il decadimento temporale con emivita 106 giorni e' una **media mobile
  esponenziale**, equivalente a un modello di stato con un rapporto
  segnale/rumore fissato. L'emivita e' un parametro, non un capriccio.
- La regressione dell'Elo verso 1500 dopo l'inattivita' e' l'approssimazione
  grezza di quello che **Glicko** fa in modo formale gonfiando la deviazione del
  rating col passare del tempo.
- La binomiale negativa per conteggi sovradispersi e' testo da manuale.

**Tipo 2 — la costante e' un a priori, e va difesa PRIMA di vedere i dati.**
`computeLeagueParams` ritorna `avgH 1.50 / avgA 1.20` finche' non ha 30 partite;
`estimateRho` ritorna -0.11 sotto le 100. Sono a priori ragionevoli su un
campione insufficiente, e si spengono da soli appena i dati bastano. Legittimi
proprio perche' **hanno una data di scadenza**. Nota il pattern giusto:
`calculateRho` e' una funzione disegnata a mano, ma in produzione gira
`estimateRho`, che il rho lo **stima** con una ricerca a griglia sulle quattro
celle basse. La versione a mano e' solo la rete.

**Tipo 3 — il paracadute, legittimo finché è inerte.** Il cap ±20% su
`goalsSotCorrection` è di questo tipo. Un cap non è un parametro del modello
finché non morde; quando morde, **diventa** il modello, e in silenzio. Ed è
misurabile: su 1133 partite morde nello **0.18% dei casi**. Nella formulazione
precedente, a moltiplicatore, lo stesso cap mordeva nello 0.61% ad `alpha 0.50`,
nell'11.8% ad `alpha 1.00` e nel **42.3% ad `alpha 2.00`** — ed è esattamente
perché ad alpha 2.00 quasi metà delle partite riceveva il cap invece del modello
che la calibrazione si rompeva. Regola operativa: **un guardrail va misurato, non
solo scritto**; se morde più di qualche punto percentuale, non è un guardrail, è
il modello.

**Fuori classifica — questi rompono davvero i conti.** Tre esempi, tutti trovati
cercando la risposta a questa domanda:
- `Math.max(2, ...)` in `negBinK`. Nessuna giustificazione: `k = 2` su media 9.5
  significa varianza 54 contro le 11 vere. Nei fatti non mordeva quasi mai, ma
  era li' per impedire un'esplosione invece di curarne la causa. Sostituito con
  il restringimento della dispersione verso Poisson, che e' la procedura giusta
  e non ha bisogno di pavimenti.
- La media geometrica `sqrt(miei x concessi)` in `calcAdv`, cioe' **shrinkage
  zero** deciso implicitamente non scrivendolo. Questo mordeva eccome:
  pendenza 0.47, sedici punti di errore sulla prima fascia. Il valore più
  pericoloso non è quello scritto male, è quello **non scritto**.
- **`_base` chiamata «baseline di lega» quando è una baseline di coppia.** Non è
  nemmeno una costante: è un nome sbagliato, e ha svuotato tre modifiche di fila
  prima che qualcuno guardasse cosa contenesse davvero. Vedi *La baseline di
  coppia*. Il rischio non è solo nei numeri messi a mano, è anche nei **nomi** che
  li descrivono male.

**La regola.** Per ogni costante nel motore deve valere una di queste tre:
1. **e' stimata dai dati** e c'e' scritto su quale campione;
2. **e' un a priori dichiarato** che si spegne quando i dati bastano;
3. **e' un paracadute di cui e' stato misurato che non morde.**

Se non vale nessuna delle tre, o la si stima, o si mostra che il risultato non
cambia facendola variare del ±50%. Il rischio non e' che la matematica smetta di
funzionare — continua a girare benissimo — ma che ogni costante non stimata sia
un parametro nascosto, e che i parametri nascosti **interagiscano** senza che
nessuno se ne accorga.

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

**Le costanti calibrate portano la loro provenienza qui dentro, non nel codice.**
I file non hanno commenti (vedi *Stile*), quindi `OL_BETA/OL_T1/OL_T2`, le rette
della confidence, `RESID_GAMMA`, `STAT_SHRINK_TABLE`, le tre tabelle `MARKET_*`,
`SOT_PER_GOAL` e `GOALS_SOT_W` devono dire **in AGENTS.md** su quante partite sono
state stimate e con che metodo. Se ne cambi una, aggiorna la sezione che la
descrive; se ne aggiungi una, scrivila da qualche parte prima di committare.

**Le manopole di smorzamento hanno tre forme diverse.** Leggi la formula, non il
nome:

| costante | formula | verso |
|---|---|---|
| `STAT_SHRINK_TABLE`, `MARKET_SHRINK_K` | `1 + k(r−1)` | **k alto = meno** shrinkage |
| `SHRINK_K`, `SHRINK_LAM_K` | `n/(n+k)` | **k alto = più** shrinkage |
| `MARKET_BASE_SHRINK` | `ref + c(x−ref)` | **c alto = meno** restringimento (`c = 1` non fa niente) |
| `GOALS_SOT_W` | `(1−w)·a + w·b` | **w alto = più** peso ai tiri in porta |

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
# apri http://127.0.0.1:8204/scanner.html e raccogli pageerror + console error.
# L'unico 404 atteso è leghe.json, che non sta nel repository.
# Controlla anche che ogni id scritto da safeTxt/safeHtml esista nel DOM: una
# card riscritta lascia facilmente scritture verso id che non ci sono più.
```

**Oltre al minimo**, quando tocchi il motore vale la pena di:

- **simulare `aggregaTeam`** con un payload `/advanced` finto (venti partite, due
  squadre) e verificare che ogni coppia di `STAT_PAIRS` abbia la sua feature e che
  `predictStat` non torni `null` dove non deve. È il test che ha trovato il bug
  delle metriche a segno negativo (`vaep_defensive`), invisibile a occhio.
- **controllare gli invarianti dei mercati**: la matrice somma a 1, l'handicap
  asiatico somma a 1 su ogni linea ed è monotono, le fasce multigol disgiunte
  sommano a 1, le probabilità Over decrescono al salire della linea. Due
  asserzioni «ovvie» qui si sono rivelate sbagliate — l'AH −0.75 sta fra −1 e
  −0.5, non fra −0.5 e +0.5, e `negBinK` **deve** restituire `Infinity` sui
  campioni non sovradispersi — quindi quando un invariante fallisce, sospetta
  prima del test.
- **testare le funzioni nuove in isolamento** sostituendo `predictStat` con uno
  stub (le dichiarazioni di funzione dentro `new Function` sono riassegnabili):
  serve a verificare cap, spegnimento a peso zero e comportamento coi dati
  mancanti senza dipendere dai dati veri.

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

Le uniche eccezioni sono una trentina di marcatori brevi, nei punti dove una
modifica in buona fede rompe tutto **in silenzio**: le righe che il Comparatore
aggancia per testo, le due convenzioni opposte di `k`, `RESID_ALPHA` a zero, la
provenienza di `OL_BETA` e delle rette della confidence, il `k` fisso
dell'Ordered Logit, il fatto che il riferimento dei mercati deve restare costante
dentro la lega, e che la correzione dai tiri è una media di lambda e non un
moltiplicatore. Rimandano tutti qui. Se ne aggiungi uno, che sia perché *senza*
quella riga qualcuno romperebbe qualcosa, non perché il codice è complicato.

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
