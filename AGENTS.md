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
- **Build corrente: `0905-b42`.** `window.__SCANNER_BUILD` (Scanner), `_bComp`
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
- **Il Comparatore deve stampare quello che stampa lo Scanner.** Ogni riga del CSV dice se
  lo fa (`COPIA CONFORME DELLO SCANNER`), e `strumenti/banco-parita.js` lo verifica in tutte
  le modalita'. Chi tocca il motore o il Comparatore lo rifa' prima di committare. Vedi
  *Il Comparatore stampa come lo Scanner*.
- **Ogni costante del motore** è stimata dai dati (campione scritto nel *Registro delle
  costanti*), oppure è un a priori dichiarato che si spegne quando i dati bastano, oppure
  è un paracadute di cui è misurato che non morde. Altrimenti è un parametro nascosto.
  Vedi *Le costanti messe a mano*.
- La storia dei perché: messaggi di commit, `git log -S <costante>`, e il codice
  pre-ripulitura (commento in testa a `scanner.html` al commit `cd51a69`).

## Da fare

Dentro ogni gruppo, in ordine di rapporto valore/rischio. Quando chiudi una voce,
spostala in *Cosa è già stato provato* con i numeri, e aggiorna *Stato attuale*.

### 0. Il campione di riferimento in copia conforme — fatto (`b41`)

- [x] ~~Un backtest `b40` di Serie A, una stagione per file~~ — **1134 partite,
  2023/24–2025/26, 1134 su 1134 in copia conforme.** Sono tutte le stagioni di Serie A
  rifacibili come le vede lo Scanner (l'API parte dal 2021/22). Tarature riconfermate, il
  clamp dell'HFA non morde mai, e due difetti del motore trovati e corretti. Vedi *Il
  campione di riferimento in copia conforme*.
- [x] ~~Decidere lo storico canonico: 15 o 30~~ — **30, dal `b40`.** E' il batch base
  dell'utente e lo storico su cui sono misurate le tarature `b24`–`b38`. Il Comparatore lo
  legge dallo Scanner (`id="history-limit" value="30"`); la prima partita dello Scanner
  scarica circa il doppio delle partite per squadra.

### 1. Backtest che decidono senza rilanciare il motore

Il CSV esporta già i pezzi da cui si ricompone ogni valore: basta un export recente.

- [ ] **Il candidato Elo, secondo giro, se si vuole.** `ELO_1X2_W` 0.40 con `ELO_SCALE`
  2.00 **non ha passato** il test registrato: LaLiga −0.0042 e Bundesliga −0.0078, ma Ligue 1
  +0.0004, e la regola chiedeva un miglioramento in ciascuna lega. Resta 0.75 / 1.25. Il
  guadagno segue la timidezza del prodotto finito (Ligue 1 ha già pendenza 1.045), quindi un
  secondo giro va fatto su leghe mai viste (Eredivisie, Liga Portugal, Championship…), con la
  stessa coppia e la regola scritta prima. Vedi *Peso e scala dell'Elo insieme: il candidato
  registrato*.
- [ ] **Il riferimento di lega dei mercati sui numeri è sbagliato da lega a lega.** Corner,
  tiri e gialli si ancorano a `MARKET_PER_GOAL × gol di lega`, ma corner e gialli non
  crescono coi gol: per gol i gialli vanno da 1.18 (Bundesliga) a 1.67 (LaLiga), i corner
  da 3.05 a 3.66, contro 1.48 e 3.61. In Ligue 1 la base dei corner è 54.7% contro 46.0%. Il riferimento sbaglia **due volte**: nella base del
  tabellone (Bundesliga corner 69.7% contro 51.4% vero, LaLiga gialli 52.3% contro 62.7%) e
  nella previsione stessa, perché `MARKET_BASE_SHRINK` ci tira dentro la baseline di coppia
  (corner Over 9.5 in Bundesliga previsto 60.5% contro 51.4%). Né un riferimento costante
  per partita né più peso alla coppia lo sistemano in tutte le leghe: serve la frequenza di
  lega vera, cioè un campione di partite di lega con `/stats` (vedi punto 4). Vedi *Le
  altre quattro leghe*. È la voce che vale di più, insieme alla media NPxG di lega.
- [ ] **`LEAGUE_HALFLIFE_DAYS`** (oggi 0 = media piatta). È l'ultima ipotesi rimasta sul
  *livello* dei mercati gol: il lambda è inversamente proporzionale alla base di lega, e la
  base è una media piatta su tre stagioni (Premier: 3.041 contro 2.754 veri, −5% sul
  lambda). Sul campione in copia conforme la base piatta sbaglia i gol reali della stagione
  di 0.083 in media in Serie A, 0.258 in Premier, 0.070 in LaLiga e 0.094 in Ligue 1, quella
  a emivita 106 di 0.028, 0.132, 0.029 e 0.053 (a favore in 9 stagioni su 12). Ma in Bundesliga la base piatta è
  già giusta (3.17–3.20 contro 3.13–3.25) e il lambda manca lo stesso dell'8–12%: la base non
  è tutto il muro (vedi *Una media NPxG di lega*, punto 4). Va ricostruito il verso
  sull'Over, non dedotto: il CSV esporta `Unita: media gol casa
  (piatta)` e `(emivita 106)` fianco a fianco. Vedi *I mercati gol: due muri*.

### 2. Aspettano una sesta lega

Le cinque leghe sono tutte in copia conforme (`b41`, 5230 partite). Quello che resta aperto
qui ha bisogno di dati nuovi, non di rifare questi.

- [x] ~~Lo squilibrio sui tiri in porta~~ — **nel motore dal `b42`** (`SOT_ELO_B = 0.0030`),
  dopo aver passato il test registrato: Bundesliga −0.0046 (`z = −2.21`), Ligue 1 −0.0045
  (`z = −2.26`), le cinque insieme −0.0029 (`z = −3.10`). Vedi *Cosa è già stato provato*.

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
  aggregare `/advanced` su tutta la lega, non sulle due squadre. **Il `b41` le dà un
  numero**: sulle 12 stagioni-lega in copia conforme i gol per NPxG vanno da 1.055 a 1.156,
  e più sono alti più il lambda resta sotto i gol veri (correlazione −0.62; Bundesliga 1.13–
  1.15 e lambda −8/−12%). **Lo stesso campione risolverebbe anche i mercati sui numeri**
  (punto 1): le ultime N partite di lega prima della data, con `/stats` e `/advanced`, danno
  in un colpo la media NPxG di lega e le frequenze vere di corner, tiri e gialli. Costa
  circa N chiamate la prima volta per lega (in cache come il database), e va scelto in modo
  deterministico (ultime N con `_isPast`) perché Scanner e Comparatore restino uguali.
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
- [ ] **Formazioni e assenze** (`/lineups` della partita, se esce prima del calcio d'inizio):
  l'unica fonte rimasta per anticipare le sorprese, perché forma, riposo e fortuna non le
  vedono (vedi *Cosa è già stato provato*). L'undici abituale si ricava a costo zero dai
  `/lineups` dello storico, già scaricati; serve una chiamata per la partita, e solo i
  titolari (le sostituzioni sono dopo il fischio). Da misurare prima: se l'API la dà in
  anticipo, e quanto sposta.
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

## Stato attuale (`b42`)

**1X2.** Pick azzeccato 52.9% (±3.0) contro il 40.2% del «gioca sempre in casa» in Serie
A, 52.8% contro 43.1% in Premier, 54.2% contro 45.8% in LaLiga, 51.8% contro 42.0% in
Bundesliga, 51.9% contro 43.9% in Ligue 1, fermo da venti build. Il valore sta nella **fascia alta**, che la card mostra con la tabella misurata
in copia conforme dello Scanner (1134 partite di Serie A, 2023/24–2025/26, una stagione per
file; vedi *Il campione di riferimento in copia conforme*):

| soglia sul pick | partite | quota del calendario | azzecca | ±2se | `b38` (1882, non conforme) |
|---|---|---|---|---|---|
| ≥50% | 522 | 46% | 61.3% | 4.3 | 62.0% |
| ≥55% | 359 | 32% | 64.9% | 5.0 | 65.3% |
| ≥60% | 221 | 19% | 70.1% | 6.2 | 71.1% |
| ≥65% | 118 | 10% | 73.7% | 8.1 | 74.3% |
| ≥70% | 52 | 5% | 73.1% | 12.3 | 79.0% |

In Premier (1135 partite, stesse regole): ≥50 / 55 / 60 / 65 / 70 azzeccano 62.8 / 66.3 /
68.2 / 72.3 / 80.9%, su 52 / 37 / 25 / 16 / 8% del calendario. In LaLiga (1134) 65.3 / 71.1 /
75.0 / 80.7 / 84.1%, su 47 / 34 / 23 / 15 / 9%. In Bundesliga (912) 62.6 / 69.2 / 73.7 /
77.4 / 81.8%, su 47 / 34 / 22 / 15 / 8%. In Ligue 1 (915) 59.8 / 66.5 / 69.8 / 72.6 / 78.0%,
su 46 / 29 / 19 / 10 / 4%.

**Dove vanno gli errori, e dove sta il margine.** Sulle cinque leghe (5230 partite) il pick
sbaglia il 47.2%: 25.6 punti sono pareggi (il pick non gioca mai `X`, e `pX` non si prevede)
e 21.6 sono vittorie dello sfavorito. Anche indovinando sempre chi vince fra le partite non
pari si arriverebbe al 74.4%. Le sorprese non si anticipano con forma, momento dell'Elo,
riposo o fortuna sotto-xG (vedi *Cosa è già stato provato*): l'unico segnale è il disaccordo
fra modello ed Elo, +0.57 punti di prese. Il margine vero è la selezione: giocando il
100 / 50 / 30 / 20 / 10% del calendario, in ordine di probabilità del pick, si prende il
52.8 / 62.0 / 68.6 / 72.8 / 78.2%.

**La selezione vale più dell'accuratezza.** Prima di aggiungere una feature, chiedersi se
il segnale non sia già nell'output, solo mal etichettato.

**Tabellone.** Ordina per **scarto dal base rate della lega**. Sulla proposta migliore di
ogni partita rende +17.6 punti sopra il giocarla alla cieca come la stampava il `b40`, +18.9
col `b41` (che ridà la base ai mercati sui numeri), contro +11.7 del vecchio ordinamento per
probabilità. Vedi *Il tabellone ordinava per la colonna sbagliata*.

**Calibrazione 1X2.** Probabilità ancora un po' timide: pendenza 1.249 ±0.098 (1 contro 2)
sul prodotto finito in Serie A, 1.120 in Premier, 1.150 in LaLiga e Bundesliga, 1.038 in
Ligue 1. La timidezza sta nel modello (`lgModel` 1.637 / 1.309 / 1.481 / 1.374 / 1.149), non
nell'Elo (1.119 / 1.018 / 1.017 / 1.035 / 0.957). Pesare di più il modello e scalare di più
l'Elo (0.40 / 2.00) la toglie dove c'è, −0.005 di logloss sulle cinque leghe (`z = −4.07`),
ma **non ha passato il test registrato**: in Ligue 1, dove il prodotto è già calibrato, non
migliora (+0.0004). Resta 0.75 / 1.25. Vedi *Peso e scala dell'Elo insieme: il candidato
registrato*.

**Mercati gol.** Due muri distinti. *Ordinamento*: AUC dell'Over 2.5 fra 0.51 e 0.60 a
seconda del campione (0.552 in copia conforme, GG 0.532), e l'unica feature che l'ha spostato
è `sum_sot`. *Livello*: l'Over 2.5 previsto sta 3.4 punti sotto il reale in Serie A (44.2%
contro 47.6%), 5.2 in Premier (53.7% contro 58.9%), 1.0 in LaLiga, **7.1 in Bundesliga**
(55.2% contro 62.3%) e 1.1 in Ligue 1, il GG 3.0 / 5.1 / 5.1 / 4.4 / 0.0. Più una lega segna per NPxG, più il
lambda resta corto: la radice è la media NPxG di lega (vedi *Da fare*, punto 4);
`LEAGUE_HALFLIFE_DAYS` ne copre una parte.

**Mercati sui numeri.** Discriminano meglio dei gol: in copia conforme gialli 0.647 di AUC,
corner 0.574, tiri in porta 0.556 in Serie A, calibrati in media (previsto contro reale
55.2/54.4, 45.6/45.4, 44.1/44.1). In Premier gialli 0.565, tiri 0.578, corner 0.518; in
LaLiga 0.579, 0.605, 0.568; in Bundesliga 0.576, 0.568, 0.540; in Ligue 1 0.577, 0.587,
0.508. **Ma il loro riferimento di lega sbaglia da lega a lega** (vedi *Da fare*): in LaLiga
i gialli sembrano giocabili quasi sempre e non lo sono, in Bundesliga i corner previsti
stanno 9 punti sopra il vero. Dal `b38` sono nel tabellone, dal `b41` anche quando la coppia
non è sovradispersa, dal `b42` i tiri in porta tengono conto dello squilibrio.

**Pareggio.** Non si prevede abbastanza da giocarlo: in copia conforme `pX` ha AUC 0.562
in Serie A (0.561 / 0.580 / 0.542 nelle tre stagioni; 0.487 sul vecchio campione), 0.547 in
Premier, 0.584 in LaLiga, 0.551 in Bundesliga e 0.544 in Ligue 1, ma sta quasi sempre fra 25 e 30% e il suo scarto dal base rate
non passa mai +7.1. Trascina con sé il `12`.

**Campioni su cui si è misurato:**

| campione | partite | note |
|---|---|---|
| **Serie A 2023/24 → 2025/26** | **1134** | **il riferimento**: export `b40`, 1134 su 1134 in copia conforme, una stagione per file, storico 30, `lgN` ≥ 760; `/advanced` assente sul 2023/24 (`riserva-k-motore`) |
| **Premier 2023/24 → 2025/26** | **1135** | **il riferimento**: export `b41`, 1135 su 1135 in copia conforme, una stagione per file, storico 30, `lgN` ≥ 760, `/advanced` su tutte e tre le stagioni |
| **LaLiga 2023/24 → 2025/26** | **1134** | **prima lega di prova del candidato Elo**: export `b41`, 1134 su 1134 in copia conforme, `lgN` ≥ 759; `/advanced` assente sul 2023/24 |
| **Bundesliga 2023/24 → 2025/26** | **912** | **seconda lega di prova**: export `b41`, 912 su 912 in copia conforme, 18 squadre quindi `lgN` ≥ 611; `/advanced` assente sul 2023/24 |
| **Ligue 1 2023/24 → 2025/26** | **915** | **terza lega di prova**: export `b41`, 915 su 915 in copia conforme; da 20 a 18 squadre nel 2023/24, quindi `lgN` 760 / 686 / 612 al minimo; `/advanced` assente sul 2023/24 |
| Serie A 2021/22 → 2025/26 | 1882 | motore post-`b30`; `/advanced` assente sulle tre stagioni più vecchie; storico 30, ma file con tre stagioni ciascuno (non copia conforme). Superato dalla riga sopra |
| Serie A + Premier + LaLiga 2025/26 | 1133 | post-`b18`, con `/advanced` |
| le tre sopra + Bundesliga + Ligue 1 2025/26 | 1743 | export `b14`, **pre-`b18`**: lega congelata a 1.50/1.20 |

LaLiga, Bundesliga e Ligue 1 sono servite nel `b41` a due test scritti prima di guardarle:
uno passato (lo squilibrio sui tiri), uno no (il candidato Elo). Da qui in poi non sono più
leghe vergini: un test nuovo vuole leghe nuove. Meno di due leghe non bastano a spedire una
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
6. Lo scope `role` è un **sottoinsieme** di `overall`: con `limit = 30` (default dal `b40`)
   sono circa 15 partite, non 30. → *Il campione di ruolo è un sottoinsieme*.
7. `SHRINK_LAM_K` **non tocca l'1X2**: sta solo sui lambda di ruolo, e `ENS_SCOPE_W = 1`
   manda l'1X2 su quelli completi. Chi la ritara per l'1X2 sposta i **mercati gol**.
8. Una probabilità alta **non è una proposta**: `12` al 73% è il base rate della lega.
   Conta lo **scarto dal base rate**.

## Come funziona il motore

**La catena.** `aggregaTeam` scarica lo storico di una squadra (`history-limit`, default
30 dal `b40`, dentro una finestra di 500 giorni) e per ogni partita estrae quanto la squadra ha
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

- **1X2**: `CONF_1X2_TABLE`, tabella empirica per fascia (`b38`, 1882 partite),
  riconfermata in copia conforme nel `b41` (8 fasce su 8 dentro 2se). Con
  `window.CONF_1X2_MODE = 'retta'` si torna alla vecchia `6.26 + 0.880·p`, che sottostimava
  fino a 8 punti dove si decide (a 62 mostrava 61, il vero era 67.5).
- **La tabella serve anche gli esiti non scelti** (le confidence di `1`, `X` e `2` a schermo
  e in `__CONF_MK`), ma era misurata sul solo pick, che non scende mai sotto il 33%. Fino al
  `b40` sotto il primo punto (37.6) restava piatta a 36: un `2` all'11% mostrava 36, e ne
  vince il 9%. Dal `b41` la tabella parte da `[0,0]`, cioè sotto 37.6 scende in linea retta
  (0.960·p). Misura: 2381 probabilità sotto 37.6, hit/p = 0.939.
- **Mercati binari**: retta `−5.06 + 1.091·p`, rimisurata nel `b38` su 22.584 proposte
  (errore massimo 2.4 punti) e nel `b41` su 7938 (errore massimo 2.5, fascia 50–60). Non si
  tocca: lo scarto per mercato (Over −4.4, GG −3.8, `12` +3.3) è il livello dei gol e la
  timidezza dell'1X2, non la retta.

### Il tabellone

`renderVerdetti` trasforma ogni coppia partita-mercato in una proposta e la ordina per
**scarto** = probabilità − base rate. Il base rate lo calcola
`leagueBaseRates(leagueId, targetTimeMs)` sull'archivio della lega stessa, con lo stesso
`_isPast` del motore e a costo zero chiamate (minimo 200 partite). Per corner, tiri e
gialli il base rate è il riferimento ancorato ai gol di lega (`MARKET_PER_GOAL ×
(avgH+avgA)`) passato per la stessa binomiale negativa, **anche quando la `k` della coppia è
infinita** (Poisson): fino al `b40` una guardia `isFinite(kk)` lasciava il mercato senza base
e fuori dall'ordinamento sul 73% delle partite per i gialli, 44% per i tiri, 23% per i
corner. Fasce (`EDGE_BANDS`): ≥20 FORTE, ≥10 GIOCABILE, ≥5 MARGINALE. Ogni riga dice su
quanti casi è misurato il suo hit.

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
  `RAW_CACHE`: con storico 15 la prima partita costava 239 chiamate, una con una squadra già
  vista 108, una con tutte e due già viste 0 (a 30 le partite da scaricare per squadra
  raddoppiano). Ricaricare la pagina butta tutto.
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
7. **Quello che lo Scanner stampa dopo l'hook** il Comparatore lo legge su `window` a fine
   giro, dal **primo** giro del ciclo: `window.__CONF_MK` (le confidence di tutti i mercati,
   gia' arrotondate come nei badge) e `window.__VERDETTI` (il tabellone, ogni voce con la sua
   `key`: `p1`, `pX`, `p2`, `p1X`, `pX2`, `p12`, `pOv`, `pUn`, `pGG`, `pNG`, `cor9.5`,
   `sot8.5`, `yel3.5`). Una voce nuova nel tabellone vuole una `key` nuova e il suo caso in
   `cmpTabHit`, altrimenti nel CSV il reale di quella voce e' `N/D`.
8. **Lo storico dello Scanner** si legge dall'attributo `id="history-limit" ... value="30"`
   dell'HTML dello Scanner. Cambiarne la forma lascia il Comparatore senza metro (il log
   dice «storico dello Scanner: NON TROVATO»).
9. **Le manopole** si dichiarano in una delle due forme che `cmpEngineDefaults` sa leggere:
   `window.X = (typeof window.X === 'number'|'string') ? window.X : <default>;` oppure
   `window.X = window.X || <default>;`, con il nome in maiuscolo. Una manopola scritta in
   un'altra forma sfugge al certificato di copia conforme.
10. **`safeTxt` e `safeHtml`** restano scritte come sono: il banco di prova le strumenta per
    testo, e se cambiano forma si ferma dicendolo.

**Come gira un batch.** `cmpRunMatch` mette la lega nel DOM del motore (creando l'`<option>`
se manca e verificando che abbia attecchito), ricopia `history-limit`, e chiama
`avviaScanner()` **tre volte**, una per ogni valore di `CMP_K_LIST = [4, 2, 1]`, per la
sezione *A/B SHRINKAGE*. Il CSV e le colonne principali sono il **primo** giro, quindi
`CMP_K_LIST[0]` deve restare uguale al `SHRINK_K` del motore. `window.__*_DEBUG` e
`globalThis._V97_probs` restano quelli dell'**ultimo** giro: per qualunque confronto si legge
dall'oggetto risultato (`R.eloDebugOver`, `R.scopeDebug`, `R._confMk`, `R._verdetti`, …).
Se `__UNIT_DEBUG.lgN` è 0, `cmpRunMatch` si ferma, a ogni partita.

**Il database e la stagione.** Lo Scanner, per una partita, carica la **sua** stagione e le
due precedenti. Il Comparatore fa lo stesso (`cmpCaricaDatabase`, stagione `s1` in
`cmpLoadedSeason`), e da `b39` elabora **solo** le partite di `s1`, in tutte le modalita':
quelle delle due stagioni precedenti hanno nel suo database una stagione di storico in meno,
e le salta dicendolo nel log.

## Il Comparatore stampa come lo Scanner

**La richiesta, e cosa vuol dire.** Qualunque cosa il Comparatore stampi su una partita
(schermo o CSV, in qualunque modalita') deve essere quello che lo Scanner avrebbe stampato
su quella partita. Dal `b39` e' verificato, non affermato: il Comparatore lo certifica a ogni
partita, e un banco di prova lo misura in tutte le modalita'.

**Il certificato.** `cmpParita(match)`, chiamata in `cmpRunMatch` al momento del giro,
restituisce l'elenco di cio' che rende quel giro diverso dallo Scanner, vuoto se non c'e'
niente. Controlla:

- che il motore caricato sia lo `scanner.html` pubblicato accanto al Comparatore (hash del
  testo; all'apertura il Comparatore ripristina la copia salvata in localStorage, che puo'
  essere vecchia) e che le build coincidano;
- **ogni** manopola del motore contro il suo default letto dal sorgente
  (`cmpEngineDefaults`, 27 manopole dal `b42`), piu' `CMP_K_LIST[0]` contro `SHRINK_K`;
- lo storico per squadra contro quello dello Scanner (`window.__ENGINE_LIMIT`);
- che la partita sia della stagione per cui e' caricato il database.

Il risultato finisce nella riga `COPIA CONFORME DELLO SCANNER` (SI, oppure NO con i motivi)
e in testa al file (`Copia conforme dello Scanner: N partite su M`).

**Cosa stampava di diverso fino al `b38`**, trovato col banco di prova:

| cosa | dove | effetto |
|---|---|---|
| batch per stagioni e sweep con **30** partite di storico, lo Scanner 15 | tutti i CSV di batch | 131-152 scritture a schermo su 188 diverse dallo Scanner, 62-66 righe del CSV su 66 |
| il batch per stagioni elaborava le **tre** stagioni del database | ogni file di stagione | le due stagioni vecchie rifatte con una stagione di storico in meno, e presenti in piu' file |
| confidence di 1/X/2 da una copia della **retta** vecchia; lo Scanner usa `CONF_1X2_TABLE` | schermo e CSV | es. 37/32/37 dove lo Scanner mostrava 36/36/36 |
| confidence di doppie chance, GG e Over/Under non esportate | CSV | sette numeri dello Scanner assenti |
| il **tabellone** non c'era | CSV e schermo | la cosa da cui si gioca andava ricostruita a mano |
| `cmpLgWarned` spegneva la guardia sulla lega dopo il primo errore | batch | le partite successive con `lgN = 0` passavano |
| il log di una partita singola mostrava l'ensemble dell'ultimo giro (k = 1) | log | un numero diverso da quello a schermo |

**Il banco di prova: `strumenti/banco-parita.js`.** Node e Playwright (Chromium e'
preinstallato). Una lega finta di 10 squadre su tre stagioni, generata in modo deterministico
dall'id della partita e servita al posto di PitchAPI, con una neopromossa e senza
`/advanced` sulla stagione piu' vecchia come l'API vera. Lo Scanner si guida come lo usa
l'utente (`caricaSquadreLega` e `avviaScanner` sulle partite di una data), il Comparatore gira
in ogni modalita', e si confrontano **ogni scrittura a schermo del motore** (`safeTxt` e
`safeHtml`, strumentate nei due file allo stesso modo: 188 per partita) e **81 righe del CSV**
che riportano un numero dello Scanner (1X2, confidence di tutti i mercati, i sei modelli,
GG e Over, corner/tiri/gialli e le loro linee, handicap, multigol, Elo, tabellone voce per
voce, certificato). Tre modalita' sono controlli di potenza, e passano solo se il certificato
dice NO col motivo giusto.

Esito al `b42` (storico 30), a 390px:

| modalita' | copia conforme | scritture del motore diverse | righe CSV diverse | scorrimento laterale |
|---|---|---|---|---|
| una partita, tutte del giorno, intervallo | 3/3 | 0 su 188 | 0 su 81 | 0 |
| batch per stagioni, sweep | 89/89, solo la stagione caricata | 0 su 188 | 0 su 81 | 0 |
| intervallo che sconfina nella stagione prima | 57/57, 20 partite saltate con avviso | 0 | 0 | 0 |
| `ab`: scala Elo 1.00 e uno storico diverso da quello dello Scanner (controllo) | 0/3, «ELO_SCALE ... / storico di 15 partite invece delle 30 ...» | 122-153 | 69-76 | 0 |
| `vecchio`: motore `b41` caricato (controllo) | 0/3, «motore caricato diverso ...» | 2-5 | 6-7 | 0 |

Al `b39` lo stesso controllo col motore `b38` aveva dato 0 scritture diverse su 188: il
motore `b39` stampava esattamente quello del `b38`, e le differenze erano tutte nel
Comparatore. Al `b40` il motore cambia davvero (lo storico passa a 30, 131-152 scritture
diverse col `b39`). Al `b41` il controllo col `b40` vede solo le due correzioni: le confidence
degli esiti non scelti (36/36/36 → 34/30/33) e il tabellone, dove sale in cima un mercato sui
numeri. Al `b42` il controllo col `b41` vede solo i tiri in porta: le quattro linee Over, la
loro riga nel tabellone e il certificato.

**Cosa resta fuori, e va saputo:**

- **Il database dello Scanner puo' essere piu' vecchio di quello del Comparatore.** Lo Scanner
  lo tiene in memoria e in localStorage fino a 24 ore: le partite finite dopo il download
  mancano, e un backtest fatto dopo le vedra'. Dal `b39` lo Scanner lo dice nel sottotitolo
  («N partite di lega prima di questa data non risultano concluse nel database»).
- **Una chiamata fallita nello Scanner** lascia quella partita senza dati per tutta la
  sessione (`RAW_CACHE` memorizza anche la risposta vuota); il Comparatore riprova fino a tre
  volte. Se l'API ha avuto un buco mentre si usava lo Scanner, i due non coincidono.
- **Le colonne Esito e la riga `PICK >=55%`** sono regole del file per contare, non verdetti
  dello Scanner; i verdetti sono nella sezione `TABELLONE`. Idem il «Previsto» delle metriche
  che il motore non prevede (tiri totali, big chances, dribbling...): e' una media calcolata
  dal Comparatore.
- Il banco confronta cio' che il motore scrive con `safeTxt`/`safeHtml`. Le poche card
  scritte con `innerHTML` diretto (la card dell'Elo, la nota di lega) e il mega-prompt non
  sono nel confronto.

**Come si rifa'.** `node strumenti/banco-parita.js` (tutte le modalita' e i controlli, circa
tre minuti); `MOBILE=1` misura lo scorrimento laterale a 390px; `VECCHIO=<scanner vecchio>`
aggiunge il controllo sul motore diverso dal pubblicato; `PENDENTI=1` mette due partite non
concluse nel database. Esce con 0 se tutto e' come deve essere.

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

## Il campione di riferimento in copia conforme

Tre export `b40` di Serie A, uno per stagione (2023/24, 2024/25, 2025/26), **1134 partite,
1134 su 1134 in copia conforme**. ID unici dentro e fra i file, `STAGIONE` uguale a
`STAGIONE DEL DATABASE` su ogni riga, `lgN` fra 760 e 1140, storico 30 (ruolo in media 13.9
partite). Il 2023/24 è tutto `riserva-k-motore`: fino a quella stagione PitchAPI non serve
`/advanced`, e il motore gira con l'xG al posto degli NPxG.

**Sono tutte le stagioni di Serie A rifacibili come le vede lo Scanner.** In `leghe.json` la
Serie A parte dal 2021/22: nel suo file il 2021/22 ha zero stagioni alle spalle e il 2022/23
una, mentre lo Scanner in produzione ne carica due. Per avere più partite servono altre
leghe, non stagioni più vecchie. Le analisi si rifanno dai CSV, con la prova di coincidenza
prima di ogni ricostruzione.

| cosa | `b35`–`b38` (1882, tre stagioni per file) | copia conforme | verdetto |
|---|---|---|---|
| clamp dell'HFA | morde sul 27.6% | **0 su 1134** | paracadute inerte |
| soglie del pick ≥50/55/60/65 | 62.0 / 65.3 / 71.1 / 74.3 | 61.3 / 64.9 / 70.1 / 73.7 | riconfermate |
| `CONF_1X2_TABLE` sul pick | — | 8 fasce su 8 dentro 2se (χ² ≈ 6 su 8) | riconfermata |
| retta dei binari | errore massimo 2.4 | errore massimo 2.5 | riconfermata |
| `EDGE_BANDS` 20 / 10 / 5 | +24.6 / +14.8 / +6.3 | +25.6 / +15.6 / +4.8 (`b40`), +25.0 / +14.9 / +5.7 (`b41`) | riconfermate |
| proposta migliore del tabellone | +16.7 | +17.6 (`b40`), +18.9 (`b41`) | regge |
| `SHRINK_K` 4 | 1X2 meglio sotto 4, gol peggio | idem | resta 4 |
| `SHRINK_LAM_K` 3 | ottimo 5–8, `z = −1.82` | monotono fino a 20, miglior `z = −1.99` | resta 3 |
| `ELO_1X2_W` 0.75 | piatto fra 0.50 e 0.75 | piatto fra 0.50 e 0.75 | riconfermato |
| `ELO_SCALE` 1.25 | Elo calibrato (1.092) | Elo calibrato (1.119 ±0.089) | riconfermata |

**Il clamp dell'HFA.** Morde su 0 righe su 1134 (HFA di lega fra 31 e 62). Il 27.6% del `b35`
erano partite con l'archivio corto: le stagioni 2021/22 e 2022/23, e le stagioni vecchie
rifatte dentro i file delle successive. La regola non sposta niente: la sezione `A/B REGOLA
DELL HFA` dà pavimento = grezzo sul 100% delle righe, e lo shrinkage −0.00027 di logloss
(`z = −1.25`). Il clamp resta com'è, tipo 3 legittimo.

**La confidence dell'1X2**, pick per fascia di probabilità:

| fascia | pick | p media | tabella | hit reale | ±2se |
|---|---|---|---|---|---|
| < 40 | 210 | 37.4 | 36.1 | 34.8 | 6.6 |
| 40–45 | 207 | 42.4 | 45.5 | 44.0 | 6.9 |
| 45–50 | 195 | 47.3 | 52.4 | 59.5 | 7.0 |
| 50–55 | 163 | 52.4 | 54.9 | 53.4 | 7.8 |
| 55–60 | 138 | 57.2 | 56.4 | 56.5 | 8.4 |
| 60–65 | 103 | 62.5 | 67.6 | 66.0 | 9.3 |
| 65–70 | 66 | 67.0 | 70.4 | 74.2 | 10.8 |
| ≥ 70 | 52 | 74.1 | 79.0 | 73.1 | 12.3 |

Sugli esiti **non** scelti la tabella non era mai stata misurata, e lì sbagliava di 6–27
punti: fasce 0–15 / 15–20 / 20–25 / 25–30 / 30–35, probabilità 11.2 / 17.7 / 22.7 / 27.6 /
31.8, hit 9.0 / 15.7 / 19.4 / 27.9 / 29.5, confidence mostrata 36 su tutte. Corretta nel
`b41` (vedi *La confidence*).

**Il tabellone**, guadagno per fascia di scarto (hit meno la frequenza del mercato nella
stagione), col `b41`:

| fascia | proposte | rende | alla cieca | guadagno | ±2se |
|---|---|---|---|---|---|
| sotto il base | 7438 | 40.7% | 48.4% | −7.8 | 1.1 |
| +0 … +5 | 3501 | 52.8% | 49.7% | +3.1 | 1.6 |
| +5 … +10 | 1810 | 57.8% | 52.1% | +5.7 | 2.3 |
| +10 … +15 | 918 | 65.4% | 52.6% | +12.8 | 3.1 |
| +15 … +20 | 505 | 71.3% | 52.5% | +18.8 | 4.0 |
| +20 … +30 | 474 | 73.8% | 48.8% | +25.0 | 3.9 |
| +30 e oltre | 96 | 77.1% | 39.7% | +37.4 | 8.5 |

Monotono in ognuna delle tre stagioni (+5…10 / +10…20 / ≥ +20: +5.9 / +15.1 / +24.4,
+6.6 / +14.7 / +30.4, +4.4 / +14.9 / +26.5). Contro il base rate di lega, che è contato solo
sulle partite precedenti, i numeri sono gli stessi entro 0.7 punti: il guadagno non viene dal
senno di poi. I valori di `EDGE_BANDS` (+24.6 / +14.8 / +6.3) restano quelli del `b38`: le due
misure coincidono entro l'errore.

La proposta migliore di ogni partita: come la stampava il `b40` rende 64.4% contro 46.7%
alla cieca (**+17.6**, per stagione +21.6 / +17.7 / +13.6); col `b41` 66.3% contro 47.4%
(**+18.9**, +18.5 / +19.7 / +18.5). In cima: `1` 27%, gialli 21%, `2` 19%, `X2` 14%, Under
12%. Le partite con almeno una proposta FORTE o GIOCABILE passano dal 71% all'80%. Sulle 203
partite dove la prima proposta cambia il guadagno è +7.0 punti (`z = 1.44`): da solo non
basterebbe, ma la correzione non è una taratura, è il motore che fa quello che dichiarava.

**I mercati sui numeri hanno meno scarto di quanto scritto nel `b38`.** Scarto ≥ +10: gialli
20% delle partite, tiri 1%, corner 1% (il `b38` diceva 14 / 15 / 13%). I tiri e i corner
previsti hanno una sd di 5.5 punti, i gialli di 10.8: solo i gialli si allontanano dal base
rate abbastanza da essere proposti. Non riprodotto, e non spiegato.

**Lo shrinkage.** `SHRINK_K`, dalla sezione `A/B SHRINKAGE`, contro `k = 4`:

| `k` | 1X2 | Over 2.5 | GG | somma |
|---|---|---|---|---|
| 2 | −0.00069 (`z = −3.30`) | +0.00104 | +0.00120 | **+0.00155** (`z = 1.80`) |
| 1 | −0.00101 (`z = −2.78`) | +0.00185 | +0.00211 | **+0.00295** (`z = 2.06`) |

Il guadagno sull'1X2 c'è anche senza nessuna riga col clamp: il sospetto del `b37` (che
venisse dal pavimento dell'HFA) è falsificato. Ma i gol pagano di più: la somma peggiora
nel 2023/24 e nel 2024/25, e nel 2025/26 è pari. **Resta 4.**

`SHRINK_LAM_K`, ricostruita dal CSV (lambda di ruolo prima della contrazione, pesi, scala dei
tiri, `rho`; la divisione fra casa e trasferta tenuta quella del giro, per il GG è
un'approssimazione). Prova di coincidenza a `K = 3`: Over entro 0.05, GG entro 0.06.

| `SHRINK_LAM_K` | bias Over | Brier Over | logloss Over+GG contro 3 |
|---|---|---|---|
| 1 | −3.8 | 0.24870 | +0.00156 (`z = 2.35`) |
| **3** | −3.4 | 0.24833 | in uso |
| 5 | −3.0 | 0.24814 | −0.00096 (`z = −1.99`) |
| 8 | −2.7 | 0.24799 | −0.00184 (`z = −1.80`) |
| 20 | −1.9 | 0.24790 | −0.00302 (`z = −1.38`) |

Stesso verso in 3 stagioni su 3, ma monotono senza ottimo interno e sotto soglia. **Resta 3**
fino a una seconda lega.

**L'Elo**, 817 partite senza pareggio, logloss 1 contro 2:

| `w` | 0 | 0.25 | 0.50 | **0.75** | 1 |
|---|---|---|---|---|---|
| logloss | 0.5601 | 0.5535 | 0.5502 | **0.5501** | 0.5527 |

| `ELO_SCALE` | 0.75 | 1.00 | 1.10 | **1.25** | 1.40 | 1.60 |
|---|---|---|---|---|---|---|
| logloss | 0.5700 | 0.5576 | 0.5540 | **0.5501** | 0.5476 | 0.5466 |

1.25 batte 1.00 a `z = 3.55`; salire oltre migliora (1.40: `z = −1.91`) solo perché compensa
il modello timido. Pendenze di calibrazione: modello 1.637 ±0.128, Elo 1.119 ±0.089, prodotto
finito 1.249 ±0.098. Per stagione l'Elo sta a 1.238 / 1.205 / 0.977.

### Le altre quattro leghe

Export `b41`, uno per stagione, tutte **in copia conforme su ogni partita**: Premier 1135
(`/advanced` su tutte e tre le stagioni), LaLiga 1134, Bundesliga 912 e Ligue 1 915
(`/advanced` assente sul 2023/24), `lgN` pari a due stagioni intere (≥ 759 a 20 squadre,
≥ 611 a 18; la Ligue 1 è passata da 20 a 18 nel 2023/24), clamp dell'HFA mai. LaLiga,
Bundesliga e Ligue 1 sono le leghe di prova del candidato Elo e dello squilibrio sui tiri,
quindi non sono servite a sceglierli.

| cosa | Serie A | Premier | LaLiga | Bundesliga | Ligue 1 | verdetto |
|---|---|---|---|---|---|---|
| pick / «sempre in casa» | 52.9 / 40.2% | 52.8 / 43.1% | 54.2 / 45.8% | 51.8 / 42.0% | 51.9 / 43.9% | — |
| soglie ≥50/55/60/65/70 | 61.3 / 64.9 / 70.1 / 73.7 / 73.1 | 62.8 / 66.3 / 68.2 / 72.3 / 80.9 | 65.3 / 71.1 / 75.0 / 80.7 / 84.1 | 62.6 / 69.2 / 73.7 / 77.4 / 81.8 | 59.8 / 66.5 / 69.8 / 72.6 / 78.0 | reggono |
| `CONF_1X2_TABLE` sul pick, χ² su 8 | ≈ 6 | 11.2 | 7.7 | 7.1 | 5.2 | regge; le fasce che sbagliano cambiano verso da lega a lega: rumore |
| esiti non scelti sotto 37.6, hit/p | 0.939 | 1.000 | 0.943 | 0.993 | 0.963 | `[0,0]` (0.960) regge |
| retta dei binari, errore massimo | 2.5 | 3.9 | 8.4 (fascia 0–30, 125 casi) | 6.4 (fascia 0–30, 100 casi) | 4.7 | regge; per mercato Over e GG, cioè il livello dei gol |
| `EDGE_BANDS` FORTE / GIOCABILE / MARGINALE | +27.1 / +14.9 / +5.7 | +27.4 / +10.7 / +6.0 | +25.0 / +13.7 / +7.3 | +28.7 / +14.0 / +5.5 | +26.4 / +13.4 / +5.0 | reggono, monotone in tutte e cinque |
| proposta migliore del tabellone | +18.9 | +15.0 | +16.4 | +16.4 | +14.8 | regge |
| `SHRINK_K` 2 contro 4: 1X2 / somma coi gol | −0.00069 / +0.00155 | −0.00079 / +0.00136 | −0.00052 / +0.00025 | −0.00052 / **+0.00321** | +0.00001 / +0.00087 | resta 4, cinque leghe su cinque |
| `SHRINK_LAM_K` 5 contro 3, Over+GG | −0.00096 | −0.00078, ma 2023/24 +0.00131 | +0.00001, peggio da 8 in su | **−0.00153** (`z = −2.69`) | −0.00052 (`z = −1.26`) | resta 3: tre leghe sì, una no, una ribaltata |
| `GOALS_SOT_W` | 0 peggio (`z = 2.03`) | 1 peggio (`z = 2.30`) | ottimo a 0.50 | ottimo fra 0.25 e 0.50 | ottimo a 0.50 | resta 0.50 |
| pendenza modello / Elo / finito | 1.637 / 1.119 / 1.249 | 1.309 / 1.018 / 1.120 | 1.481 / 1.017 / 1.150 | 1.374 / 1.035 / 1.150 | 1.149 / 0.957 / 1.038 | la timidezza è nel modello; in Ligue 1 quasi non c'è |
| AUC `1` / `2` / `X` / Over / GG | 0.719 / 0.752 / 0.562 / 0.552 / 0.532 | 0.712 / 0.721 / 0.547 / 0.572 / 0.544 | 0.736 / 0.715 / 0.584 / 0.598 / 0.554 | 0.722 / 0.717 / 0.551 / 0.555 / 0.557 | 0.685 / 0.696 / 0.544 / 0.541 / 0.483 | — |
| AUC gialli / tiri / corner | 0.647 / 0.556 / 0.574 | 0.565 / 0.578 / 0.518 | 0.579 / 0.605 / 0.568 | 0.576 / 0.568 / 0.540 | 0.577 / 0.587 / 0.508 | — |
| Over previsto contro reale | −3.4 | −5.2 (−7.7 / −1.0 / −6.6) | −1.0 (+2.1 / −3.6 / −1.5) | **−7.1** (−6.0 / −5.5 / −9.7) | −1.1 (−1.3 / −0.9 / −1.0) | il muro del livello, diverso per lega |

Livello dei gol stagione per stagione. Premier: base piatta 2.901 / 3.046 / 3.041, a emivita
106 3.103 / 3.088 / 2.821, gol reali 3.280 / 2.937 / 2.754, lambda dell'Over −9.0% / −0.4% /
−5.0% dal reale. LaLiga: base piatta 2.539 / 2.584 / 2.637, emivita 2.613 / 2.618 / 2.652,
reali 2.651 / 2.620 / 2.698, lambda −1.3% / −4.8% / −2.5%. Bundesliga: base piatta 3.170 /
3.198 / 3.185, emivita 3.212 / 3.188 / 3.180, reali 3.230 / 3.135 / 3.246, lambda −8.0% /
−8.3% / −11.9%: qui la base è giusta e il lambda manca lo stesso. Ligue 1: base piatta 2.775
/ 2.795 / 2.838, emivita 2.666 / 2.912 / 2.885, reali 2.695 / 2.984 / 2.826, lambda +1.7% /
−3.3% / −2.6%.

**Il muro del livello segue i gol per NPxG.** Il lambda si costruisce sugli NPxG; una lega
che segna di più per NPxG (rigori, finalizzazione) resta sotto. Sulle 15 stagioni-lega i gol
per NPxG vanno da 1.055 (Serie A 2025/26, Premier 2025/26) a 1.156 (Serie A 2023/24), e il
rapporto lambda/gol scende con loro (correlazione −0.67, pendenza −0.77): Bundesliga 1.13–1.15
e lambda/gol 0.88–0.92, Serie A 2025/26 1.055 e 1.003, Ligue 1 1.08–1.09 e 0.97–1.02. È la
media NPxG di lega che manca.

**Il riferimento dei mercati sui numeri sbaglia da lega a lega.** Il tabellone misura lo
scarto di gialli, tiri e corner contro `MARKET_PER_GOAL × gol di lega` passato per la
binomiale negativa, perché l'archivio di lega ha solo i punteggi; e `calcAdv` ci tira dentro
la baseline di coppia con `MARKET_BASE_SHRINK`. Ma corner e gialli non crescono coi gol:

| lega | gol | gialli: a partita / per gol | corner: a partita / per gol | tiri: a partita / per gol | base contro reale: gialli · tiri · corner |
|---|---|---|---|---|---|
| Serie A | 2.53 | 3.81 / 1.51 | 9.26 / 3.66 | 8.14 / 3.22 | 53.8 / 54.4 · 45.5 / 44.1 · 46.4 / 45.4 |
| Premier | 2.99 | 4.02 / 1.34 | 10.34 / 3.46 | 9.13 / 3.05 | 63.3 / 59.1 · **61.3 / 54.3** · 62.8 / 58.8 |
| LaLiga | 2.66 | 4.43 / **1.67** | 9.51 / 3.58 | 8.46 / 3.18 | **52.3 / 62.7** · 44.4 / 47.4 · 45.5 / 46.5 |
| Bundesliga | 3.20 | 3.78 / **1.18** | 9.76 / **3.05** | 9.47 / 2.96 | **67.9 / 53.3** · **68.1 / 59.2** · **69.7 / 51.4** |
| Ligue 1 | 2.83 | 3.72 / 1.31 | 9.45 / 3.33 | 9.03 / 3.19 | 59.0 / 54.5 · 53.4 / 54.2 · **54.7 / 46.0** |
| costante | | 1.48 | 3.61 | 3.20 | |

Le costanti sono misurate su leghe da 2.5–2.7 gol, e in una lega da 3.2 il riferimento sale
del 20% senza che corner e gialli salgano. Sbaglia due volte:

- **nella base del tabellone.** In LaLiga i gialli hanno scarto ≥ +10 nel 48% delle partite
  e finiscono in cima nel 43%, ma rendono **+3.8** punti sopra il giocarli alla cieca contro
  i +21.4 degli altri mercati allo stesso scarto. In Bundesliga succede il contrario: la base
  è così alta che corner, tiri e gialli non vengono quasi mai proposti. Col comportamento del
  `b40` la proposta migliore di LaLiga faceva +16.5 contro +16.1 (`z = −0.46`): il `b41` non
  ha peggiorato il totale, ma l'etichetta dei gialli promette quello che non rende;
- **nella previsione.** In Bundesliga i corner Over 9.5 previsti sono 60.5% contro 51.4%
  veri, i gialli Over 3.5 57.7% contro 53.3%, i tiri Over 8.5 63.1% contro 59.2%; in Ligue 1
  i corner 50.0% contro 46.0%.

**Le cure da poco non bastano.** Stimato su tre leghe e misurato sulla quarta: un
riferimento costante a partita (9.5–9.9 corner, 3.9–4.1 gialli) aggiusta la Bundesliga
(corner −0.0165 di logloss, `z = −2.33`) e rompe la Premier (+0.0064) e la Serie A
(+0.0028); più peso alla baseline di coppia (`MARKET_BASE_SHRINK` da 0.50 a 0.75 sui corner)
aggiusta la Bundesliga (−0.0123, `z = −3.3`) e peggiora la Premier (+0.0029). Il livello di
corner e gialli cambia davvero da lega a lega, e né i gol né la coppia lo sanno: serve la
frequenza di lega vera (vedi *Da fare*, punto 4).

### Lo squilibrio sui tiri in porta: registrato, passato, nel motore (`b42`)

Come i cartellini (vedi *Lo squilibrio e i cartellini*), ma col segno opposto: le partite
squilibrate hanno **più** tiri in porta di quanti il motore ne preveda, perché la squadra
forte tira di più di quanto la sua media dica. Correlazione fra `|ΔElo|` e il residuo (reale
meno previsto): +0.101 / +0.053 / +0.105 / +0.106 / +0.128 in Serie A / Premier / LaLiga /
Bundesliga / Ligue 1, positiva in 14 stagioni su 15.

Il coefficiente è stato scelto su Serie A, Premier e LaLiga (fuori lega: stimato su due e
misurato sulla terza, −0.0021 / −0.0019 / −0.0023 di logloss dell'Over 8.5, insieme `z =
−1.68`) e scritto qui **prima** di vedere Bundesliga e Ligue 1, con la regola: negativo su
tutte e due, e sulle cinque insieme `z ≤ −2`.

| lega di prova | differenza di logloss (Over 8.5) | `z` | per stagione |
|---|---|---|---|
| Bundesliga | −0.0046 | −2.21 | −0.0076 / +0.0004 / −0.0065 |
| Ligue 1 | −0.0045 | −2.26 | −0.0031 / −0.0055 / −0.0049 |
| le cinque insieme | −0.0029 | **−3.10** | — |

Passa. `lSot = lamOf('sot') + SOT_ELO_B · (|ΔElo| − scarto medio di lega)`, con
`SOT_ELO_B = 0.0030` e lo stesso cap del 30% dei cartellini (non morde: l'aggiustamento
vale ±0.27 tiri per deviazione standard di squilibrio). Stimato su tutte e cinque il
coefficiente sarebbe 0.0034: si spedisce il valore registrato, non quello rifatto a test
finito. Il CSV esporta `Tiri porta prima dello squilibrio`, `Tiri porta: aggiustamento` e
`al cap`. Si muovono i mercati dei tiri e il loro scarto nel tabellone, nient'altro: la
seconda stima dei gol usa i tiri previsti da `predictStat`, non questo lambda.

### Peso e scala dell'Elo insieme: il candidato registrato

**La misura.** Le sezioni `A/B PESO DELL ELO` e `A/B SCALA DELL ELO` si ricostruiscono per
qualunque coppia (`w`, `S`): `lgTarget = (1 − w)·lgModel + w·(S·ΔElo + HFA)/173.72`, e la
probabilità 1 contro 2 è `σ(lgTarget)` (prova di coincidenza a 0.75 / 1.25: entro 0.05).
Finora si era spazzata una manopola alla volta. Insieme, su 1673 partite senza pareggio di
Serie A e Premier (logloss 1 contro 2, ×10⁴, contro la coppia in uso):

| `S` \ `w` | 0.30 | 0.40 | 0.50 | 0.60 | 0.75 |
|---|---|---|---|---|---|
| 1.25 | +8.8 | −2.3 | −8.0 | −8.6 | **0** |
| 1.60 | −30.0 | −43.5 | −47.1 | −41.4 | −16.3 |
| 2.00 | −57.8 | **−62.9** | −51.0 | −23.3 | +44.7 |
| 2.50 | −70.1 | −50.5 | −3.3 | +68.3 | +215.1 |

C'è una cresta, non un punto: meno peso all'Elo e scala più alta. La regressione libera
(`y ~ a·lgModel + b·ΔElo/173.72 + c·HFA/173.72`) dice perché: `a` 0.93, `b` 0.58, `c` 0.28,
contro 0.25 / 0.94 / 0.75 in uso. **Il modello merita molto più peso di un quarto, e l'HFA
dell'Elo molto meno.** Il `b14` aveva fissato 0.75 quando la lega nei backtest era congelata
a 1.50/1.20 (vedi *La lega che non arrivava mai*): il modello era rotto, e l'Elo vinceva
per forza. Il `b35` l'aveva riconfermato spazzando `w` a `S` fisso, cioè lungo la riga 1.25
della tabella, dove l'ottimo è davvero piatto.

**Non è la trappola della scala.** Alzare `S` a `w` fisso sovra-scala un termine già
calibrato (vedi *La scala dell'Elo*). Qui `w·S`, il peso della differenza di rating, scende
da 0.94 a 0.80; sale il peso del modello e scende quello dell'HFA. Una sola temperatura sul
prodotto in uso vale meno della metà (miglior T 1.20: −0.0026, e la Premier non la vuole
oltre 1.15). La pendenza del prodotto finito va da 1.193 a 1.057: la combinazione giusta di
due stime parzialmente indipendenti ha pesi che sommano a più di uno.

**Il candidato: `ELO_1X2_W = 0.40`, `ELO_SCALE = 2.00`.** Scelto dentro la griglia e non sul
bordo (l'ottimo fine scivola verso `w` 0.25, `S` 2.6: è la cresta, e il bordo non si
spedisce). Contro 0.75 / 1.25:

- logloss 1 contro 2 −0.0063 sull'insieme (`z = −3.53`), e negativa in **6 stagioni su 6**: Serie A
  −0.0093 / −0.0114 / −0.0022, Premier −0.0031 / −0.0104 / −0.0017;
- fuori campione sulla griglia grossa: scelto sulla Serie A e misurato sulla Premier −0.0042
  (`z = −2.43`), scelto sulla Premier e misurato sulla Serie A −0.0043 (`z = −2.51`);
- effetti collaterali: l'Over non si muove (l'inclinazione tiene il totale), il GG sì perché
  il ramo di ruolo si inclina con gli stessi `w` e `S`: −0.0001 in Serie A, +0.0017 in
  Premier (`z = 2.33`); l'inclinazione massima stimata resta 0.49 contro il cap di 0.60;
  `pX` non cambia (entro 0.09 punti) e `log(m1/m2)` è 1.007–1.012 volte `lgTarget`, quindi
  tutto l'1X2 si ricostruisce offline.

**La regola, scritta prima di vedere LaLiga, Bundesliga e Ligue 1.** Su ciascuna delle tre,
export `b41` in copia conforme, la logloss 1 contro 2 del candidato contro 0.75 / 1.25 deve
essere negativa; sull'insieme delle tre `z ≤ −2`; nessuna lega con `z > +1`. Se passa si
spedisce nel `b42`, e insieme vanno rifatti sulle probabilità ricostruite delle cinque leghe
`CONF_1X2_TABLE` (le probabilità diventano meno timide, e la tabella le raddrizzava), le
soglie del pick e gli scarti dell'1X2 nel tabellone. Vanno riscritte anche card e prompt che
dicono «quando Elo e modello distano 10+ punti il verdetto lo decide l'Elo». Se non passa,
resta 0.75 / 1.25 e questa sezione dice perché.

**Il test, lega per lega** (logloss 1 contro 2, candidato contro 0.75 / 1.25):

| lega | partite senza pari | differenza | `z` | per stagione | esito |
|---|---|---|---|---|---|
| LaLiga | 840 | −0.0042 | −1.66 | −0.0097 / −0.0072 / +0.0039 | passa |
| Bundesliga | 680 | −0.0078 | −2.59 | −0.0094 / −0.0095 / −0.0046 | passa |
| Ligue 1 | 698 | **+0.0004** | +0.12 | −0.0023 / +0.0034 / −0.0002 | **non negativa: non passa** |
| le tre insieme | 2218 | −0.0039 | −2.37 | 7 stagioni su 9 negative | la soglia d'insieme passerebbe |
| le cinque insieme | 3891 | −0.0049 | −4.07 | — | solo descrittivo |

**Esito: non passa, resta 0.75 / 1.25.** La regola chiedeva un miglioramento in ciascuna
delle tre leghe, e in Ligue 1 non c'è. Non è un peggioramento (`z = +0.12`), ma la regola era
scritta apposta per non spedire un effetto che non regge ovunque, e cambiarla adesso vorrebbe
dire decidere dopo aver visto i dati.

**Perché in Ligue 1 no.** Il guadagno del candidato segue la timidezza del prodotto finito
(pendenza 1 contro 2 con la coppia in uso): Serie A 1.258 e −0.0076, Bundesliga 1.150 e
−0.0078, LaLiga 1.163 e −0.0042, Premier 1.133 e −0.0051, **Ligue 1 1.045 e +0.0004**. Dove
le probabilità sono già calibrate non c'è niente da raddrizzare. È una spiegazione trovata
dopo, quindi non conta come prova.

**Cosa resta.** Se si vuole un secondo giro: la stessa coppia, provata su leghe che non si
sono mai viste (Eredivisie, Liga Portugal, Championship, Süper Lig…), con la regola scritta
prima. In alternativa una soluzione che non ha bisogno di tarare due pesi: una temperatura sul
prodotto stimata sulla lega stessa, con lo stesso archivio che dà `leagueBaseRates`. Tutte e
due costano backtest nuovi.

In Bundesliga, a `S` fisso, anche il vecchio sweep di `w` dice 0.50 meglio di 0.75 (`z =
−1.75`); in Ligue 1 è piatto (0.5945 contro 0.5943). Su LaLiga la griglia, guardata solo
dopo il test, ha la stessa cresta: il minimo sta vicino
al candidato (−0.0042 a 0.40 / 2.00, −0.0045 a 0.30 / 2.50, sulla stessa cresta), e la pendenza del prodotto
finito passa da 1.163 a 1.051.

## Registro delle costanti

| costante | valore | tipo | da dove viene |
|---|---|---|---|
| `ENS_W` dc / mk / ol | 0.70 / 0.30 / 0.00 | stimata `b20` | griglia leave-one-league-out su 1743 partite, OL a 0 in 4 fold su 5. Vale −0.0013 di logloss, `z = −2.03`: pulizia più che guadagno |
| `ENS_SCOPE_W` | 1 | stimata `b21` | 1133 partite, logloss 1.0113 → 1.0071, monotono in 3 leghe su 3, `z = −3.96`, fuori campione 1.0 in 3 fold su 3. Solo 1X2 |
| `ELO_1X2_W` | 0.75 | stimata `b14`, riconfermata `b35` e `b41` a `S` fisso | 5 leghe, 1743 partite: w 0 → 0.50 a +5.02σ, ottimo a 0.75. `b35` (Serie A 1882, ramo giusto): ottimo interno piatto fra 0.50 e 0.75, estremi peggiori a 2σ. `b41` (1134 in copia conforme): idem. Spazzata **insieme a `ELO_SCALE`** su Serie A e Premier la coppia 0.40 / 2.00 vale −0.0063 (`z = −3.53`), 6 stagioni su 6, ma nel test registrato Ligue 1 non migliora (+0.0004): non passa. Vedi *Peso e scala dell'Elo insieme* |
| `ELO_SCALE` | 1.25 | stimata `b30`, confermata `b35` e `b41` a `w` fisso; la coppia con `w` non ha passato il test (`b41`) | pendenza di calibrazione dell'Elo 1.235 (`z = 3.13`); fuori campione 1.20–1.35 in 7 fold su 7; `b35`: 1.25 batte 1.00 a `z = 3.92`; `b41`: a `z = 3.55`, Elo a 1.119 ±0.089. Applicata alla sola differenza di rating, non all'HFA |
| `ELO_GAP_THRESHOLD` / `TAU` / `ASY` | 45 / 360 / 0.9 | `τ` scelto dove smette di costare (`b30`) | la logloss cala in modo monotono fino a τ infinito; da 360 in su il guadagno residuo è 0.0005. Non misurato sulla pausa estiva (33 partite) |
| K dell'Elo | 30 sotto le 15 partite, poi 20 | a mano, verificato `b30` | alzare K porta la pendenza a 1 ma peggiora la logloss oltre 40/28: si tara la conversione, non il rating |
| clamp dell'HFA | [30, 100], con ≥50 partite | paracadute misurato, inerte (`b41`) | 0 righe su 1134 in copia conforme (`lgN` ≥ 760). Il 27.6% del `b35` erano archivi corti (< 600 partite), che lo Scanner in produzione non ha. Alternativa esposta e inutile: `ELO_HFA_MODE = 'shrink'`, `ELO_HFA_PRIOR` 65, `ELO_HFA_K` 200 (−0.00027, `z = −1.25`) |
| `ELO_TILT_MAX` | 0.60 | paracadute misurato | mai toccato; inclinazione massima osservata 0.215 fino al `b35`, 0.49 in copia conforme (`b41`, storico 30), 0.49 stimata anche col candidato |
| `SHRINK_K` | 4 | misurata `b35`–`b37`, riconfermata `b41` | 12 e 28 peggiori a 5σ; sotto 4 migliora l'1X2 (−0.0016, `z = −3.03`) ma i gol pagano +0.0056. `b41`, copia conforme e zero clamp: a 2 l'1X2 −0.00069 (`z = −3.30`), la somma +0.00155; Premier −0.00079 (`z = −3.42`) e +0.00136; LaLiga −0.00052 e +0.00025; Bundesliga −0.00052 e +0.00321 (`z = 3.40`); Ligue 1 +0.00001 e +0.00087 |
| `SHRINK_LAM_K` | 3 | a mano, misurata `b37` e `b41` | `b37`: ottimo del Brier Over fra 5 e 8, `z = −1.82`, segno ribaltato nel 2022/23. `b41`: in Serie A monotono fino a 20, miglior `z = −1.99` a 5, 3 stagioni su 3; in Premier il 2023/24 si ribalta (+0.00131 a 5, +0.0081 a 20); in LaLiga piatta a 5 e peggio da 8 in su; in Bundesliga meglio a 5 (`z = −2.69`, 3 stagioni su 3); in Ligue 1 meglio a 5 (`z = −1.26`). Tre leghe sì, una no, una ribaltata: resta 3 |
| `GOALS_SOT_W` | 0.50 | stimata `b12`, confermata `b14` e `b41` | AUC Over 2.5 da 0.554/0.495/0.501 a 0.572/0.514/0.521; cinque leghe +2.18σ. `b41` in copia conforme: la Serie A punisce 0 (+0.0066, `z = 2.03`), la Premier punisce 1 (+0.0062, `z = 2.30`), LaLiga e Ligue 1 hanno l'ottimo a 0.50, la Bundesliga fra 0.25 e 0.50 |
| `SOT_PER_GOAL` | 3.25 | misurata | LaLiga 3.19, Premier 3.04, Serie A 3.33. Tocca solo il livello |
| `GOALS_SOT_CAP` | 0.20 | paracadute misurato | morde nello 0.18% |
| `OL_BETA` / `T1` / `T2` | 2.056 / −0.475 / +0.671 | stimata `b20` | massima verosimiglianza su 1743 partite, leave-one-league-out, sulla variabile di **ruolo** (media +0.196). Peso 0 |
| `CARDS_ELO_B` / cap | −0.0035 / ±30% | stimata `b16` | 1743 partite, 5 leghe, −5.8σ, omogeneo (p = 0.914), ottimo interno del Brier. In copia conforme (`b41`) il residuo dei gialli dopo la correzione non correla più con lo squilibrio (−0.010 / +0.044 / +0.026 / +0.053) |
| `SOT_ELO_B` / cap | +0.0030 / ±30% (lo stesso dei cartellini) | stimata e registrata `b41`, nel motore `b42` | scelta su Serie A, Premier e LaLiga fuori lega (−0.0021, `z = −1.68`), scritta prima di Bundesliga e Ligue 1: −0.0046 e −0.0045, le cinque insieme `z = −3.10`. Sulle cinque sarebbe 0.0034: si tiene il valore registrato. Il cap non morde |
| `MARKET_SHRINK_K` | cor 0.07 · sot 0.30 · yel 0.10 · fouls 0.15 | stimata `b12` | Brier su 1133 partite, tre leghe |
| `MARKET_BASE_SHRINK` | cor 0.50 · sot 0.55 · yel 0.75 · fouls 1.00 | stimata `b12`, `sot` ritoccata `b15` | affidabilità della baseline di coppia; `sot` 0.75 → 0.55 al minimo del Brier |
| `MARKET_PER_GOAL` | cor 3.61 · sot 3.20 · yel 1.48 · fouls null | misurata | variazione fra leghe: corner 1.1%, tiri 8.7%, gialli 14.7%, falli 28% (quindi null). In copia conforme (`b41`) corner e gialli **non crescono coi gol**: per gol i gialli vanno da 1.18 (Bundesliga) a 1.67 (LaLiga), i corner da 3.05 a 3.66. Il riferimento sbaglia fino a 18 punti la base del tabellone e 9 la previsione (corner in Bundesliga): vedi *Le altre quattro leghe* |
| `STAT_SHRINK_TABLE` | 51 voci, default 0.50 | stimata `b5` | vedi *Le statistiche previste* |
| `STAT_SHRINK_LEGACY` | 0.35 | storica | il `k` a cui valgono OL e correzione residuale |
| `CONF_1X2_TABLE` | `[0,0]` + 8 fasce | stimata `b38`, riconfermata `b41` | resa del pick per fascia, 1882 partite di Serie A post-`b30`; `b41`, 1134 in copia conforme: 8 fasce su 8 dentro 2se; Premier χ² 11.2 su 8, LaLiga 7.7, Bundesliga 7.1, Ligue 1 5.2. Il punto `[0,0]` (`b41`) serve gli esiti non scelti: hit/p 0.939 / 1.000 / 0.943 / 0.993 / 0.963 in Serie A / Premier / LaLiga / Bundesliga / Ligue 1, contro 0.960 della tabella |
| retta dei mercati binari | −5.06 + 1.091·p | stimata, riconfermata `b38` e `b41` | 22.584 proposte, errore massimo 2.4 punti; `b41` 7938 proposte, 2.5 |
| `EDGE_BANDS` | ≥20 / ≥10 / ≥5 | stimata `b38`, riconfermata `b41` | 28.230 proposte: +24.6 / +14.8 / +6.3 punti, monotono, segno concorde in 5 stagioni su 5. `b41` (copia conforme): +25.6 / +15.6 / +4.8 sulle 13.148 proposte con base del `b40`, +25.0 / +14.9 / +5.7 sulle 14.742 del `b41`, monotono in 3 stagioni su 3; Premier (≥20 / 10–20 / 5–10) +27.4 / +10.7 / +6.0, LaLiga +25.0 / +13.7 / +7.3, Bundesliga +28.7 / +14.0 / +5.5, Ligue 1 +26.4 / +13.4 / +5.0 |
| minimo di `leagueBaseRates` | 200 partite | paracadute misurato `b38` | guadagno piatto fra 50 e 500; in produzione arrivano 900+ partite |
| emivita | 106 giorni | a mano | uguale nei due file |
| storico per squadra (`history-limit`) | 30 | scelta dell'utente (`b40`) | il batch base dell'utente e lo storico delle tarature `b24`–`b38`; fino al `b39` lo Scanner stampava a 15. Il Comparatore lo legge dallo Scanner in tutte le modalita' |
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
  mostrato il grezzo accanto al valore usato (controllo P). Il clamp sull'HFA mordeva sul
  27.6% dei vecchi backtest, ma solo su archivi che lo Scanner non ha: in copia conforme 0%.

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
- **Una tabella misurata su un sottoinsieme vale solo lì.** `CONF_1X2_TABLE` era misurata sul
  pick e si applicava a tutti e tre gli esiti: sotto il primo punto restava piatta, e un 11%
  mostrava 36 per tre build. Accanto a una calibrazione va scritto su quali valori è stata
  misurata, e cosa fa fuori da lì.
- **Una guardia contro un valore «strano» può spegnere un mercato.** `isFinite(kk)` scartava
  la `k` infinita, che per `negBinPMF` è Poisson e non un errore: i gialli restavano senza
  base sul 73% delle partite. «BASE DI LEGA ASSENTE» sembrava un caso raro; contare quante
  righe lo dicono costa una riga di Python.

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
- **Lo stesso parametro con due default in due file.** Lo Scanner stampava con 15 partite di
  storico, il batch e lo sweep del Comparatore partivano da 30: per quattordici build ogni
  backtest grande ha misurato un'altra macchina, e il verdetto di parita' all'iniezione
  guardava un campo diverso da quello che il batch usava. Il default si legge da una parte
  sola (lo Scanner) e si controlla al momento del giro, non all'apertura.
- **Un batch che carica tre stagioni ne elabora tre.** L'intervallo di default copriva tutto
  il database, quindi il file di una stagione conteneva anche le due precedenti, rifatte con
  meno storico. Una partita e' confrontabile con lo Scanner solo col database della SUA
  stagione. Il 27.6% di clamp dell'HFA su cui si ragionava da tre build veniva da lì (e dalle
  stagioni troppo vecchie per avere due stagioni alle spalle): in copia conforme è 0%.
- **Dopo un ciclo di giri, `window` e' dell'ultimo giro.** Vale per i `__*_DEBUG`, per
  `_V97_probs`, per `__CONF_MK` e `__VERDETTI`: si legge dall'oggetto risultato.
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
| Abbassare `SHRINK_K` sotto 4 | **no** | vedi *Le due costanti dello shrinkage*; rifatto in copia conforme nel `b41`, stesso esito |
| Il guadagno di `SHRINK_K` sull'1X2 viene dal clamp dell'HFA | **falsificato** (`b41`) | in copia conforme il clamp non morde mai e il guadagno resta (`z = −3.30` a `k = 2`): è vero, ma i gol lo pagano |
| La regola dell'HFA: pavimento o shrinkage | **indifferente** (`b41`) | il pavimento non morde su 0 righe su 1134; shrinkage −0.00027, `z = −1.25` |
| Alzare `SHRINK_LAM_K` | **no** (`b41`) | Serie A e Bundesliga lo vorrebbero (`z = −1.99` e `−2.69` a 5), la Premier 2023/24 ribalta il segno (+0.0081 a 20), LaLiga peggiora da 8 in su. È la manopola del livello dei gol, e il livello manca per una ragione diversa in ogni lega |
| Spostare `GOALS_SOT_W` da 0.50 | **no** (`b41`) | la Serie A punisce 0, la Premier punisce 1, LaLiga e Bundesliga hanno l'ottimo a 0.50 o poco sotto |
| `SHRINK_K` giù e `SHRINK_LAM_K` su per compensare | **non torna** | l'escursione utile di `SHRINK_LAM_K` (0.9 punti di Over) non paga gli 1.5 che `SHRINK_K` a 1 toglie |
| Alzare `ELO_SCALE` oltre 1.25 **a `w` fisso** | **no** | la logloss migliora fino a 1.60, ma a 1.25 l'Elo è già calibrato (1.092): si sovra-scalerebbe il termine giusto per compensare quello sbagliato. Insieme a `w` è un'altra cosa: vedi *Peso e scala dell'Elo insieme* |
| Alzare il K dell'Elo | **no** | vedi *Registro delle costanti* |
| Applicare la regressione dell'Elo fra l'ultima partita e la data da prevedere | **no** | peggiora: 0.5743 → 0.5745, sulle partite post-stacco 0.5068 → 0.5124 |
| Prevedere quali partite finiscono pari | **no** | `pX` ha AUC 0.487 (±0.020); anche `−|p1−p2|` e `−max(p1,p2)` stanno a 0.495–0.498. In copia conforme (`b41`) 0.562, ma lo scarto non supera mai +7.1: non si gioca |
| Soglia sul pareggio «alla Champions» (X se nessuno supera il 43%) | **no** | corregge il conteggio dei pareggi ma sceglie le partite a caso (22.8% contro 25.9% alla cieca). La colonna ▲▼ di quella classifica è un artefatto del calendario |
| Prevedere meglio le stats | **al tetto** | 26 metriche su 47 al 90% del tetto `sqrt(ICC)` |
| Calibrare le stats sullo stile dell'avversario | **si fa già** | il «concesso» di `predictStat` lo fa; un indice composito aggiunge +0.001 |
| Sistemare il KNN | **ridondante** | pesare per somiglianza batte la media semplice, ma media × concesso batte la somiglianza su 10 metriche su 10. Toglierlo, non aggiustarlo |
| Medie brevi (ultime 3, ultime 5) | **mai meglio della lunga** | 47 metriche su 47 |
| Abbassare i `k` dei mercati sui numeri | **cura sbagliata** | la dispersione veniva dalla baseline di coppia (sd 8:1 sullo scarto); vedi *La baseline di coppia* |
| Squilibrio della partita su corner e tiri | **corner no, tiri sì** (`b42`) | tiri: registrato e passato su Bundesliga e Ligue 1, nel motore come `SOT_ELO_B` (vedi *Lo squilibrio sui tiri in porta*); corner fuori lega `z = −0.55`, la Premier peggiora, la Bundesliga +0.002 di correlazione |
| Peso e scala dell'Elo insieme (0.40 / 2.00 al posto di 0.75 / 1.25) | **non passato** (`b41`) | −0.0063 su Serie A e Premier, test registrato: LaLiga −0.0042, Bundesliga −0.0078, Ligue 1 +0.0004. Il guadagno segue la timidezza del prodotto, che in Ligue 1 non c'è. Vedi *Peso e scala dell'Elo insieme* |
| Riferimento dei mercati sui numeri costante a partita invece che ancorato ai gol | **no** (`b41`) | stimato su tre leghe e misurato sulla quarta: corner Bundesliga −0.0165 ma Premier +0.0064 e Serie A +0.0028. Il livello cambia con la lega, non coi gol |
| Più peso alla baseline di coppia nei mercati sui numeri (`MARKET_BASE_SHRINK`) | **no** (`b41`) | corner a 0.75: Bundesliga −0.0123, Premier +0.0029. Stessa ragione |
| Ricalibrare la confidence a retta | **sostituita da una tabella** | vedi *La confidence* |
| Arretrare il taglio temporale a `x-1` | **no** | vedi *L'orario non è affidabile* |
| Ordinare il tabellone per probabilità grezza | **no** | guadagno piatto (+1.4 … +7.1) contro monotono per scarto |
| Anticipare le sorprese con forma (punti nelle ultime 5), momento dell'Elo (ultime 5), giorni di riposo, fortuna (gol − NPxG, ultime 10), NPxG recenti | **no** (`b42`) | 5230 partite, fuori lega (stimato su quattro leghe, misurato sulla quinta), sopra `lgTarget`: logloss 1 contro 2 −0.0000 / −0.0001 / +0.0001 / −0.0012 (`z = −1.40`) / −0.0020 (`z = −1.85`), prese +0.13 / +0.10 / +0.04 / +0.17 / +0.06 punti; tutte insieme +0.31. Il riposo conta solo le partite di lega: le coppe non sono nell'archivio |
| Il disaccordo fra modello ed Elo come segnale di sorpresa | **è il candidato Elo visto da un'altra parte** (`b42`) | fuori lega −0.0037 (`z = −2.47`), prese +0.57 punti, Ligue 1 di nuovo contraria (+0.0020). Nelle 717 partite (14%) in cui modello ed Elo indicano favoriti diversi il pick prende il 37.7% (41.4% col disaccordo in regressione), contro il 55.2% delle altre. A parità di partite giocate la selezione non migliora (top 20%: 72.8 contro 73.2%) |

**Le cose che hanno retto**, in ordine di quanto valgono:

| idea | numeri |
|---|---|
| **L'Elo che inclina i lambda dell'1X2** (`b13`–`b14`) | +5σ, replicato su due leghe mai usate per tarare |
| **Il tabellone per scarto dal base rate** (`b38`) | +16.7 punti sulla proposta migliore, walk-forward +18.8, monotono in 5 stagioni; in copia conforme +17.6 (`b40`) e +18.9 (`b41`), monotono in 3 stagioni su 3 |
| **La scala dell'Elo 1.25** (`b30`) | logloss 1-contro-2 0.5836 → 0.5743, `z = −3.54`, 6 fold su 7 |
| **`ENS_SCOPE_W = 1`** (`b21`) | −0.0042 di logloss, `z = −3.96`, 3 leghe su 3 |
| **Lo squilibrio sui cartellini** (`b16`) | AUC 0.562 → 0.593, stesso segno in 5 leghe |
| **`sum_sot` sull'Over 2.5** (`b9`–`b12`) | l'unica feature sopravvissuta a tre leghe |
| **Lo squilibrio sui tiri in porta** (`b42`) | registrato prima di vedere due leghe e passato su tutte e due; cinque leghe −0.0029 di logloss dell'Over 8.5, `z = −3.10`, positivo in 14 stagioni su 15 |

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

Sul campione in copia conforme (Serie A, `b40`), stagione per stagione:

| stagione | base piatta | base emivita 106 | gol reali | lambda dell'Over contro reale | Over previsto contro reale |
|---|---|---|---|---|---|
| 2023/24 | 2.692 | 2.603 | 2.607 | −6.1% | −5.0 punti |
| 2024/25 | 2.600 | 2.628 | 2.557 | −3.3% | −3.2 |
| 2025/26 | 2.548 | 2.435 | 2.426 | +0.3% | −1.9 |

Il lambda dell'Over è `Ambito: lambda casa/trasf. (ruolo)`, già dopo la scala dei tiri. Più
manca il lambda, più manca l'Over, ma con il lambda giusto (2025/26) mancano ancora 1.9 punti:
il livello del lambda non è tutto. Da qui `LEAGUE_HALFLIFE_DAYS` (vedi *Da fare*).

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

Il `b41` ha spazzato `w` e `S` **insieme**, su Serie A e Premier in copia conforme: l'ottimo
non sta sulla riga `S = 1.25` ma su una cresta con meno peso all'Elo e scala più alta, e il
guadagno regge in 6 stagioni su 6 e fuori lega. È un candidato in test: vedi *Peso e scala
dell'Elo insieme: il candidato registrato*.

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

`role` è quello che c'è **dentro** le ultime `limit` partite: con `limit = 15` restavano 8
partite, col default di oggi (30, dal `b40`) circa 15; in produzione `nHr ≈ limit/2` (alzare
`history-limit` alza il ruolo a metà velocità). Questo file ha sostenuto il contrario per parecchie build, anche nell'elenco delle
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

Nel `b41` tutte e due rifatte in copia conforme, stesso esito: vedi *Il campione di
riferimento in copia conforme*.

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
erano gli unici assenti; il `b38` gli attribuiva molto scarto (≥ +10: tiri 15%, gialli 14%,
corner 13%), ma in copia conforme sono gialli 20%, tiri 1%, corner 1%. `X` non ha mai uno
scarto ≥ +10.

Sulla proposta migliore di ogni partita: prima in cima finiva sempre una doppia chance
(guadagno +11.7), ora `1` 26%, `2` 16%, `X2` 15%, gialli 13%, Under 10%, tiri 8% (**+16.7**,
walk-forward **+18.8**). La resa grezza scende e il guadagno sale: è il punto.

Il motore non si è mosso (39 campi su 39 identici al `b36`): è cambiato solo quale numero va
in cima e come è etichettato. Riconfermato in copia conforme nel `b41` (vedi *Il campione di
riferimento in copia conforme*); resta da riconfermare su una seconda lega.

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

- **Copia conforme.** In testa al file, `Copia conforme dello Scanner: N partite su M`; per
  partita, la riga `COPIA CONFORME DELLO SCANNER`. Una riga a NO non e' un errore (e' un A/B,
  o un giro con un'altra manopola), ma non va mescolata alle altre: il motivo e' scritto li'.
  I file precedenti al `b39` non hanno la riga; quelli del `b39` sono a storico 15, quelli
  dal `b40` a 30 come lo Scanner. I batch precedenti al `b39` sono a 30 ma con tre stagioni
  per file. Nei file del `b40` il tabellone dice «BASE DI LEGA ASSENTE» su gialli, tiri e
  corner quando la loro `Dispersione` è `--`: è il difetto corretto nel `b41`, e la base si
  ricostruisce da `Rif. lega …` con Poisson.
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

La sezione `TABELLONE (come lo stampa lo Scanner)` riporta le proposte nell'ordine dello
Scanner: per ogni `Tabellone #i`, Previsto = mercato e probabilita', Confidence = base rate
di lega, Reale = SI/NO, Esito = scarto e verdetto. La vecchia riga `GIOCABILE (>=55%)` si
chiama ora `PICK >=55% (regola del backtest, non il tabellone)`: era la soglia del file, e
aveva lo stesso nome di un verdetto del tabellone che vuol dire un'altra cosa.

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

# 3. il Comparatore stampa ancora come lo Scanner, in tutte le modalita' (~3 minuti)
node strumenti/banco-parita.js     # deve uscire con 0; MOBILE=1 per i 390px

# 4. le pagine si aprono senza errori in console
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
| S | `strumenti/banco-parita.js`: ogni scrittura a schermo del motore e ogni riga del CSV identiche allo Scanner, in tutte le modalita', e il certificato che dice NO nei controlli di potenza | si tocca il motore o il Comparatore |

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
| `b39` | il Comparatore stampa come lo Scanner in tutte le modalita': storico e stagione come lo Scanner, confidence e tabellone letti dal motore, certificato per partita, banco di prova `strumenti/banco-parita.js`. Motore invariato |
| `b40` | storico per squadra da 15 a 30 nello Scanner, il batch base dell'utente: le tarature `b24`–`b38` sono state misurate a 30. Il Comparatore lo segue da solo |
| `b41` | il campione in copia conforme (Serie A 2023/24–2025/26, 1134 su 1134): tarature `b30`–`b38` riconfermate, il clamp dell'HFA non morde mai (il 27.6% erano archivi corti). Due difetti corretti: i mercati sui numeri senza base quando la coppia non è sovradispersa (gialli sul 73% delle partite; proposta migliore +17.6 → +18.9), e `CONF_1X2_TABLE` piatta a 36 sugli esiti non scelti (ora parte da `[0,0]`) |
| — | le altre quattro leghe in copia conforme (5230 partite in tutto): tarature riconfermate in cinque leghe su cinque; due candidati registrati prima di vedere tre leghe; il riferimento dei mercati sui numeri sbaglia da lega a lega; il muro dei gol segue i gol per NPxG |
| `b42` | lo squilibrio sui tiri in porta (`SOT_ELO_B = 0.0030`), l'unico dei due candidati che ha passato il test. Il peso dell'Elo resta 0.75 / 1.25 |
