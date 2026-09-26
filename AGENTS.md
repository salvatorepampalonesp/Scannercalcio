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
che li mette in `RAW_CACHE`. Dal `b43` il motore chiede anche la formazione della partita da
prevedere (`/matches/{id}/lineups`) e, se la partita non è nell'archivio di lega perché non
è ancora giocata, la cerca con `/date/{giorno}?status=all`. Dal `b44` carica anche gli
archivi di Champions, Europa e Conference League della stagione (tre chiamate, in memoria per
la sessione), per contare il riposo vero. Dal `b45` lo Scanner chiede anche `/players` delle
partite dello storico, ma solo quando si preme il bottone della card dei giocatori (una chiamata
per partita, in memoria per la sessione): non fa parte del giro del motore. La documentazione dell'API
(51 pagine, settembre 2026) elenca anche statistiche per giocatore (`/players`,
`/advanced/players`), tiri (`/shots`), `/h2h`, arbitro, heatmap e 42 leghe fra cui coppe e
competizioni UEFA; nessuna quota dei bookmaker.

## Regole di lavoro

- **Git.** Branch `claude/*`, mai push diretto su `main`. Commit in italiano, con i numeri
  della misura che giustifica il cambiamento quando c'è. Il «N commit behind» di GitHub
  conta i merge commit delle PR: se `git rev-list --left-right --count origin/main...<branch>`
  dà `N 0`, il branch non ha niente che `main` non abbia.
- **Build corrente: `0905-b53`.** `window.__SCANNER_BUILD` (Scanner), `_bComp`
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

- [x] ~~**Il batch del `b47`: formazioni, stanchezza, Elo.**~~ — **fatto (`b48`).** Formazioni e
  stanchezza non passano, nemmeno il secondo giro delle formazioni; l'ingresso delle
  neopromosse passa ed è nel motore; il peso e la scala dell'Elo non passano nemmeno al secondo
  giro. Il racconto sotto resta per la storia. Un solo giro di export serve a tre
  decisioni. Le cinque leghe di sempre (stesse stagioni, una per file, in copia conforme: la
  formazione della partita costa una chiamata in più, le coppe europee tre per stagione) e in
  più **Eredivisie, Liga Portugal e Championship**, 2023/24–2025/26, mai guardate. Poi, in
  quest'ordine e con le regole scritte prima di vederle: formazioni e stanchezza (*Formazioni e
  assenze*, *La stanchezza*: **fatto, non passano**; resta il secondo giro delle formazioni sulle
  tre leghe nuove); l'ingresso delle neopromosse nell'Elo (*Le neopromosse*); il peso
  e la scala dell'Elo sull'Elo corretto (*Peso e scala dell'Elo insieme*, «Il 4 su 5»). Le tre
  leghe nuove servono all'Elo: non vanno aperte prima che le regole siano nel repository.
  I file si possono fare anche da qui, con *Il batch automatico*.
- [x] ~~**Il candidato Elo, secondo giro.**~~ — **non passato nemmeno sulle tre leghe nuove**
  (`b48`): sopra l'Elo corretto −0.00135, `z = −0.89`, la Championship peggiora. Resta 0.75 /
  1.25. L'alternativa rimasta è una temperatura sul prodotto stimata sulla lega stessa. Vedi
  *Peso e scala dell'Elo insieme: il candidato registrato*.
- [x] ~~**Riconfermare le tabelle col `b48`.**~~ — **fatto (`b49`)**: batch automatico delle
  cinque leghe, 5230 partite su 5230 in copia conforme, Elo rifatto dall'archivio identico su
  ogni file. `CONF_1X2_TABLE` resta (fuori lega né le probabilità nude né una tabella rifatta la
  battono); le soglie del pick si riscrivono nella card, perché col `b48` le probabilità sono più
  aperte (più calendario sopra ogni soglia, un paio di punti in meno di resa); `EDGE_BANDS` 20 /
  10 / 5 restano monotone in cinque leghe su cinque. Vedi *Le tabelle col `b48`*.
- [x] ~~**Il guadagno di una fascia del tabellone dipende dal mercato.**~~ — **l'ordine resta,
  l'etichetta cambia (`b50`).** Ordinare per guadagno atteso non sceglie proposte migliori (fuori
  lega +0.12 ±0.29 sulla prima proposta, `z = +0.42`, tre leghe su cinque): la regola si ferma al
  primo passo. Dal `b50` ogni riga dice quanto rende il suo tipo di mercato. Vedi *Il tabellone
  per famiglia di mercato: la regola*. Il racconto sotto resta per la storia. L'etichetta dice un numero
  solo per fascia (FORTE +24.6, GIOCABILE +14.8, MARGINALE +6.3), ma col `b48` sulle cinque leghe
  l'1X2 rende +27.5 / +15.5 / +8.0, i mercati gol +1.0 (92 proposte) / +7.2 / +3.5, quelli sui
  numeri +7.2 (133) / +10.2 / +8.2. Un Over 2.5 con scarto +20 è FORTE e rende quanto un
  MARGINALE: lo scarto dei mercati gol vale meno perché la loro probabilità discrimina poco (AUC
  0.55). Il candidato è ordinare e classificare le proposte per **guadagno atteso della famiglia**
  invece che per scarto grezzo; si ricostruisce tutto dalla sezione `TABELLONE` del CSV (mercato,
  probabilità, base, reale), senza rilanciare il motore. **Regola registrata**: vedi *Il
  tabellone per famiglia di mercato: la regola*.
- [x] ~~**La coda alta della selezione contro le neopromosse.**~~ — **non decisa, chiusa
  (`b52`).** Sulle tre leghe nuove il 10% più alto col `b48` prende il 78.2% contro il 78.4% del
  `b47` (−0.3 ±2.0): l'effetto delle cinque leghe (−2.9) non si ripete, ma il test non lo esclude.
  Le 25 partite che entrano in quel 10% (17 contro una neopromossa) vincono il 76.0%, previste al
  74.2%. Sulle otto leghe insieme, solo descrittivo, −1.8 ±1.8. L'ingresso delle neopromosse resta
  quello del `b48`. Il racconto sotto resta per la storia. Col `b48` il 10% del calendario
  col pick più probabile prende il 76.2% contro il 79.1% del `b47` sulle stesse partite (−2.9,
  ±2.4); al 50 / 30 / 20% la differenza è 0.0 / +0.5 / −0.7. Delle 72 partite che entrano in
  quel 10%, 69 sono contro una neopromossa: previste al 70.7%, vinte al 55.1%. Vedi *Le tre leghe
  nuove col `b48`: la regola*, «Esito».
- [x] ~~**La confidence dell'1X2 fuori dai cinque campionati.**~~ — **fatto (`b53`): la
  confidence dell'1X2 è la probabilità.** Sulle quattro leghe mai aperte (2. Bundesliga, First
  Division A, Premiership scozzese, Super League svizzera, 3202 partite) la probabilità nuda ha il
  Brier più basso della tabella in quattro leghe su quattro, −0.00220 sull'insieme (`z = −4.09`).
  Il racconto sotto resta per la storia. Sulle tre leghe nuove
  `CONF_1X2_TABLE` non regge (χ² 32.2 su 8, soglia 15.5): fra il 45 e il 55% mostra 52–55 e i
  pick escono il 46%, sopra il 70% mostra 78 ed escono l'83%. La probabilità nuda del `b48` la
  batte: Brier della confidence del pick +0.00137 con la tabella (`z = +2.68`); sulle cinque
  leghe +0.00043 (`z = +1.01`, il confronto del `b49`, non significativo). La tabella
  raddrizzava la timidezza del `b38`, che il `b48` ha quasi tolto (pendenza 1 contro 2 1.053
  sulle cinque, 1.020 sulle tre). È trovato su una regola che chiedeva solo il χ²: il candidato
  «confidence = probabilità» si prova su quattro leghe mai aperte, circa un'ora col batch
  automatico. **Regola registrata**: vedi *Le tre leghe nuove col `b48`: la regola*, «Il passo
  dopo».
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
  livello dell'Elo entra dall'inclinazione potrebbe essere ridondante. Dal `b47` è nel CSV
  (`Elo: pendenza …`), e si sa che porta dentro i salti della regressione (vedi *Le
  neopromosse*): si misura col batch `b47`.
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
- [ ] **Assenze pesate per valore**, se l'indice per presenze del `b43` mostra il segnale:
  il peso di ogni giocatore da xG+xA o VAEP (`/advanced/players`) invece che dalle presenze.
  Una chiamata in più per ogni partita dello storico.
- [ ] **Le coppe nazionali nel riposo.** Dal `b44` il riposo conta lega e coppe europee
  (vedi *La stanchezza*). Coppa Italia, FA Cup, Pokal, Copa del Rey e Coupe de France non sono
  in `leghe.json`, anche se la documentazione dell'API parla di coppe: va verificato con
  `/v1/leagues` se esistono, e con quali id.
- [ ] **Le chiavi di `/players` sulla API vera.** La card dei giocatori (`b45`) cerca ogni dato
  per chiave e per etichetta, ma le chiavi dei falli e dei contrasti non sono nella
  documentazione e sono state provate solo sul banco. Al primo uso vero, se la card dice
  «il dato … c'è solo su N righe», la chiave è diversa: leggerla dalla risposta e aggiungerla
  a `PLAYER_STATS`. Vedi *Le statistiche dei giocatori*.
- [ ] **Le frequenze dei giocatori contro il reale.** La card mostra quante volte un giocatore
  ha superato una soglia, non una probabilità. Misurarla: esportare nel CSV, per i titolari
  della partita, la frequenza su tutte e sulle ultime 5 e il dato reale, e vedere quanto
  prevede e quanto va ristretta. Poi l'avversario: i falli subiti dipendono da quanti falli fa
  l'altra squadra, che il motore prevede già.
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

## Stato attuale (`b53`)

**1X2.** Col motore `b48` il pick azzecca il 52.7% (±1.4) contro il 43.0% del «gioca sempre in
casa» sulle cinque leghe: 52.7% contro 40.2% in Serie A, 52.7% contro 43.1% in Premier, 53.2%
contro 45.8% in LaLiga, 52.5% contro 42.0% in Bundesliga, 52.3% contro 43.9% in Ligue 1, fermo da
venti build. Il valore sta nella **fascia alta**, che la card mostra con la resa misurata in
copia conforme dello Scanner (dal `b49`: 5230 partite delle cinque leghe, 2023/24–2025/26, una
stagione per file, motore `b48`; vedi *Le tabelle col `b48`*):

| soglia sul pick | partite | quota del calendario | azzecca | ±2se | `b47`, stesse partite |
|---|---|---|---|---|---|
| ≥50% | 2738 | 52% | 61.7% | 1.9 | 62.5% su 48% |
| ≥55% | 1983 | 38% | 66.0% | 2.1 | 67.6% su 33% |
| ≥60% | 1379 | 26% | 69.3% | 2.5 | 71.3% su 22% |
| ≥65% | 854 | 16% | 73.2% | 3.0 | 75.6% su 13% |
| ≥70% | 480 | 9% | 77.1% | 3.8 | 80.6% su 7% |

Per lega, ≥50 / 55 / 60 / 65 / 70: Serie A 61.2 / 64.2 / 67.7 / 70.4 / 71.4% su 50 / 37 / 25 /
13 / 6% del calendario; Premier 61.2 / 65.2 / 66.6 / 69.5 / 77.1% su 59 / 43 / 31 / 21 / 12%;
LaLiga 63.8 / 68.8 / 74.3 / 79.3 / 83.9% su 51 / 38 / 26 / 17 / 11%; Bundesliga 62.8 / 67.9 /
71.1 / 75.8 / 78.9% su 50 / 37 / 25 / 17 / 10%; Ligue 1 59.0 / 63.7 / 67.0 / 70.8 / 66.1% su 51 /
33 / 23 / 13 / 6%. Sopra ogni soglia c'è più calendario e un paio di punti in meno di resa: le
probabilità del `b48` sono più aperte (vedi *Calibrazione 1X2* qui sotto), non peggiori.

**Fuori dai cinque campionati le soglie non valgono** (`b52`: 3495 partite di Eredivisie, Liga
Portugal e Championship col `b48`, in copia conforme). Il pick prende il 50.5% contro il 43.7% del
«sempre in casa»; sopra il 55 / 60 / 65 / 70% il 69.0 / 73.6 / 77.6 / 82.6%, ogni soglia sopra la
card oltre 2se, su 32 / 22 / 16 / 11% del calendario. E le tre leghe sono lontanissime fra loro:
sopra il 55% la Championship prende il 64.8% nel 17% delle partite (su tutte 46.3%, AUC di `1` e
`2` 0.628 / 0.621: è una lega equilibrata), l'Eredivisie il 68.7% nel 47% (su tutte 53.7%), la
Liga Portugal il 72.4% nel 43% (su tutte 55.0%, AUC 0.757 / 0.775). Dal `b52` card e mega-prompt
dicono che le soglie valgono per i cinque campionati, danno quelle misurate per queste tre, e
nelle altre leghe dicono che non sono misurate. Anche `CONF_1X2_TABLE` lì non regge (vedi *Da
fare*). Sulle quattro leghe del `b53` (2. Bundesliga, First Division A, Premiership scozzese,
Super League svizzera, 3202 partite) le soglie invece stanno tutte dentro i 2se (≥55 / 60 / 65 / 70:
66.2 / 69.9 / 73.6 / 78.7%), ma su meno calendario (29 / 19 / 12 / 7%), e anche lì le leghe si
separano: sopra il 55% la 2. Bundesliga ha il 16% delle partite, la Scozia il 41%. Dal `b53`
`PICK_RESA.fuori` ha tutte e sette le leghe.

**La confidence dell'1X2 è la probabilità** (dal `b53`). La tabella misurata nel `b38` alzava le
probabilità timide di allora; col `b48` sono quasi calibrate, e la tabella le alzava troppo. Sulle
quattro leghe mai aperte la probabilità nuda la batte in quattro su quattro (−0.00220 di Brier,
`z = −4.09`). Resta un difetto, fuori dai cinque campionati: fra il 45 e il 55% il pick esce 3–6
punti meno della sua probabilità (sulle quattro leghe 47.4 → 44.5 e 52.4 → 46.1).

**Dove vanno gli errori, e dove sta il margine.** Sulle cinque leghe (5230 partite) il pick
sbaglia il 47.2% (47.3% col `b48`): 25.6 punti sono pareggi (il pick non gioca mai `X`, e `pX` non si prevede)
e 21.6 sono vittorie dello sfavorito. Anche indovinando sempre chi vince fra le partite non
pari si arriverebbe al 74.4%. Le sorprese non si anticipano con forma, momento dell'Elo,
riposo o fortuna sotto-xG (vedi *Cosa è già stato provato*): l'unico segnale è il disaccordo
fra modello ed Elo, +0.57 punti di prese. Il margine vero è la selezione: giocando il
100 / 50 / 30 / 20 / 10% del calendario, in ordine di probabilità del pick, si prende il
52.8 / 62.0 / 68.6 / 72.8 / 78.2%. Col `b48`, ordinando dentro ogni file di stagione, 52.7 / 62.0 /
69.3 / 71.8 / 76.2% contro 52.8 / 62.0 / 68.8 / 72.4 / 79.1% del `b47` sulle stesse partite: il 10%
più alto perde 2.9 punti (±2.4), quasi tutti su partite contro una neopromossa; sulle tre leghe
nuove non si ripete (−0.3 ±2.0), e la voce è chiusa (vedi *Le tre leghe nuove col `b48`: la
regola*).

**Il tetto, sulle dodici leghe** (11.927 partite, probabilità del `b48`). Il pick prende il 51.0%
e la sua probabilità media è il 51.7%: il modello è calibrato, e con queste probabilità il 51% è
quello che ci si deve aspettare. Si perde nelle partite equilibrate: con |p1 − p2| sotto 10 punti
(21% del calendario) il pick prende il 36–38%, sopra 50 punti il 74%. `X` non è mai la più
probabile (pX al massimo 34.2%). Combinare tutto quello che il motore già calcola (le tre
probabilità, `lgModel`, `lgElo`, i sei modelli, lambda, tiri, pendenze, neopromosse, formazioni,
riposo, classifica della stagione), addestrato su undici leghe e misurato sulla dodicesima, non
indovina di più: +0.2 ±0.4 punti (vedi *Cosa è già stato provato*). Per indovinare di più serve
informazione che il motore non ha.

**Formazioni e stanchezza.** Dal `b43` il motore sa chi manca oggi rispetto all'undici
abituale, dal `b44` quanti giorni di riposo ha ogni squadra contando le coppe europee (card
«Formazioni e stanchezza», sezioni CSV `FORMAZIONI` e `STANCHEZZA`). Col batch `b47` le due
regole scritte prima **non sono passate**: l'indice delle formazioni ha il segno giusto in tutte
le leghe ma vale −0.0004 di logloss (`z = −0.72`) e abbassa le prese; la stanchezza peggiora fuori
lega. Restano a schermo come informazione. Il secondo giro delle formazioni, dalla sesta
giornata e su tre leghe mai viste, non passa neppure (+0.00019). Vedi *Formazioni e assenze* e
*La stanchezza*.
Dal `b46` la card dice quando la formazione probabile è solo l'ultimo undici, e con la
confermata mostra chi è cambiato rispetto alla probabile vista prima (vedi *La formazione
probabile*).

**Neopromosse.** Fino al `b47` l'Elo le faceva entrare a 1500 o le tirava verso 1500, cioè
verso la squadra media, e la loro vittoria (1 contro 2) usciva 7.3 punti sopra il vero. Dal
`b48` una squadra che entra nella lega parte dalla media dei rating finali delle squadre uscite
la stagione prima, chi torna dopo più di 180 giorni regredisce verso quel livello, e la
pendenza dell'Elo non legge più i salti della regressione come forma. Sulle cinque leghe il
residuo va a −0.5 ±2.6 punti e la logloss 1 contro 2 migliora di 0.0037 (`z = −2.64`); sulle tre
leghe nuove non peggiora (−0.00076). Le prese non si muovono: il pick contro una neopromossa era
già il pick. Vedi *Le neopromosse*.

**Giocatori.** Dal `b45` una card mostra, per i giocatori della rosa di oggi, quante volte hanno
superato una soglia (falli subiti e commessi, tiri, tiri in porta, gialli, gol, assist,
contrasti) nelle ultime 30 partite di campionato e nelle loro ultime 5 da titolare. Sono
frequenze descrittive, non misurate contro il reale. Vedi *Le statistiche dei giocatori*.

**La selezione vale più dell'accuratezza.** Prima di aggiungere una feature, chiedersi se
il segnale non sia già nell'output, solo mal etichettato.

**Tabellone.** Ordina per **scarto dal base rate della lega**. Sulla proposta migliore di
ogni partita rende +17.6 punti sopra il giocarla alla cieca come la stampava il `b40`, +18.9
col `b41` (che ridà la base ai mercati sui numeri), contro +11.7 del vecchio ordinamento per
probabilità. Col `b48` sulle cinque leghe +16.8 (±1.3; `b47` sulle stesse partite +16.4). Lo
stesso scarto rende molto di più nell'1X2 (FORTE +27.5) che nei mercati gol (+1.0) o sui numeri
(+7.2): dal `b50` l'etichetta di ogni riga dice quanto rende il suo tipo di mercato, mentre
l'ordine resta per scarto, perché ordinare per guadagno atteso non sceglie meglio (vedi *Il
tabellone per famiglia di mercato: la regola*). Vedi *Il tabellone ordinava per la colonna
sbagliata*.

**Calibrazione 1X2.** Col `b48` la timidezza è quasi sparita: pendenza 1 contro 2 del prodotto
finito 1.053 ±0.041 sulle cinque leghe (Serie A 1.151, Premier 1.012, LaLiga 1.064, Bundesliga
1.086, Ligue 1 0.948), contro 1.143 ±0.045 del `b47` sulle stesse partite. Buona parte veniva
dalle neopromosse sopravvalutate: il pick contro di loro rendeva più del previsto in tre fasce su
quattro (+5.8, +5.1 e +10.6 punti sotto il 55%, fra 55 e 65 e sopra il 70%). Prima del `b48`: pendenza 1.249 ±0.098 (1 contro 2)
sul prodotto finito in Serie A, 1.120 in Premier, 1.150 in LaLiga e Bundesliga, 1.038 in
Ligue 1. La timidezza sta nel modello (`lgModel` 1.637 / 1.309 / 1.481 / 1.374 / 1.149), non
nell'Elo (1.119 / 1.018 / 1.017 / 1.035 / 0.957). Pesare di più il modello e scalare di più
l'Elo (0.40 / 2.00) la toglie dove c'è, −0.005 di logloss sulle cinque leghe (`z = −4.07`),
ma **non ha passato il test registrato**: in Ligue 1, dove il prodotto è già calibrato, non
migliora (+0.0004). Il secondo giro, sopra l'Elo corretto del `b48` e su tre leghe mai viste,
non passa neppure (`z = −0.89`): sopra l'Elo corretto non c'è quasi più niente da raddrizzare.
Resta 0.75 / 1.25. Vedi *Peso e scala dell'Elo insieme: il candidato registrato*.

**Mercati gol.** Due muri distinti. *Ordinamento*: AUC dell'Over 2.5 fra 0.51 e 0.60 a
seconda del campione (0.552 in copia conforme, GG 0.532), e l'unica feature che l'ha spostato
è `sum_sot`. *Livello*: l'Over 2.5 previsto sta 3.4 punti sotto il reale in Serie A (44.2%
contro 47.6%), 5.2 in Premier (53.7% contro 58.9%), 1.0 in LaLiga, **7.1 in Bundesliga**
(55.2% contro 62.3%) e 1.1 in Ligue 1, il GG 3.0 / 5.1 / 5.1 / 4.4 / 0.0. Più una lega segna per NPxG, più il
lambda resta corto: la radice è la media NPxG di lega (vedi *Da fare*, punto 4);
`LEAGUE_HALFLIFE_DAYS` ne copre una parte. Sulle tre leghe nuove (`b52`) lo stesso: Over 2.5
previsto sotto il reale di 4.2 punti in Championship, 3.2 in Eredivisie e 5.8 in Liga Portugal,
il GG di 4.8 / 3.7 / 5.3; AUC dell'Over 0.574 / 0.560 / 0.599, del GG 0.559 / 0.533 / 0.538.
Sulle quattro del `b53` l'Over sta sotto di 4.2 (2. Bundesliga), 6.1 (Scozia) e 5.1 (Svizzera), sopra
di 1.5 in Belgio.

**Mercati sui numeri.** Discriminano meglio dei gol: in copia conforme gialli 0.647 di AUC,
corner 0.574, tiri in porta 0.556 in Serie A, calibrati in media (previsto contro reale
55.2/54.4, 45.6/45.4, 44.1/44.1). In Premier gialli 0.565, tiri 0.578, corner 0.518; in
LaLiga 0.579, 0.605, 0.568; in Bundesliga 0.576, 0.568, 0.540; in Ligue 1 0.577, 0.587,
0.508. **Ma il loro riferimento di lega sbaglia da lega a lega** (vedi *Da fare*): in LaLiga
i gialli sembrano giocabili quasi sempre e non lo sono, in Bundesliga i corner previsti
stanno 9 punti sopra il vero. Dal `b38` sono nel tabellone, dal `b41` anche quando la coppia
non è sovradispersa, dal `b42` i tiri in porta tengono conto dello squilibrio. Sulle tre leghe
nuove (`b52`) il riferimento sbaglia di nuovo, in versi diversi: gialli Over 3.5 previsti 44.2%
contro 36.0% veri in Eredivisie (3.42 contro 3.00 a partita) e 65.4% contro 69.6% in Liga
Portugal; corner Over 9.5 61.5% contro 56.7% in Eredivisie e 50.7% contro 55.6% in Championship.
I tiri in porta tengono (40.7 / 40.6, 64.0 / 64.1, 47.1 / 45.1). AUC gialli / tiri / corner:
Championship 0.535 / 0.554 / 0.547, Eredivisie 0.546 / 0.550 / 0.527, Liga Portugal 0.574 /
0.612 / 0.553.

**Pareggio.** Non si prevede abbastanza da giocarlo: in copia conforme `pX` ha AUC 0.562
in Serie A (0.561 / 0.580 / 0.542 nelle tre stagioni; 0.487 sul vecchio campione), 0.547 in
Premier, 0.584 in LaLiga, 0.551 in Bundesliga e 0.544 in Ligue 1 (e 0.537 / 0.570 / 0.624 in Championship, Eredivisie e Liga Portugal), ma sta quasi sempre fra 25 e 30% e il suo scarto dal base rate
non passa mai +7.1. Trascina con sé il `12`.

**Campioni su cui si è misurato:**

| campione | partite | note |
|---|---|---|
| **Le cinque leghe col `b48`** | **5230** | **il riferimento dal `b49`** per soglie, confidence e tabellone: batch automatico `b48`, stesse stagioni e partite delle righe sotto, 5230 su 5230 in copia conforme, Elo rifatto dall'archivio identico su ogni file |
| **Le quattro leghe del `b53`** | **3202** | 2. Bundesliga 908, First Division A 931, Premiership scozzese 683, Super League svizzera 680, 2023/24–2025/26: batch automatico del `b52`, 3202 su 3202 in copia conforme, Elo identico su ogni file; `/advanced` assente sul 2023/24 di Scozia e Svizzera. Aperte solo per il test della confidence nuda; il tabellone non è mai stato guardato |
| **Le tre leghe nuove col `b48`** | **3495** | Championship 1659, Eredivisie 923, Liga Portugal 913, 2023/24–2025/26: batch automatico del `b51` (probabilità del `b48`), 3495 su 3495 in copia conforme, Elo rifatto dall'archivio identico su ogni file; `/advanced` assente sul 2023/24 di Championship e Liga Portugal. La sezione `TABELLONE` non è mai stata guardata |
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
costante: è l'errore che ha prodotto quattro falsi positivi di fila. Eredivisie, Liga Portugal e
Championship sono servite a quattro test (formazioni, neopromosse, peso dell'Elo, coda alta e
soglie): restano vergini solo per il tabellone.

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
  tenuto giusto lo stesso, perché è a schermo (dal `b51` non è più nel mega-prompt).
- **KNN**: calcolato e mostrato come riferimento tattico, **non entra nell'ensemble**. Non
  descriverlo come se ci fosse.
- **Markov** (`markovFlow`, rate dipendenti dal punteggio): da solo fa logloss 1.0091,
  leggermente meglio del Dixon-Coles (1.0098). Verificati solo gli invarianti.

**Tre quarti dell'1X2 non passano dal modello.** Con `ELO_1X2_W = 0.75` si ha
`lgTarget = 0.25·lgModel + 0.75·lgElo`: qualunque correzione lato Dixon-Coles arriva
all'1X2 divisa per quattro.

### La confidence

Una probabilità **misurata sull'hit reale**, non l'accordo fra i modelli (l'accordo correlava
−0.007 con l'azzeccare).

- **1X2, dal `b53`: la probabilità del motore** (`CONF_1X2_MODE = 'nuda'`), per il pick e per
  gli esiti non scelti. Sulle quattro leghe mai aperte batte la tabella in quattro su quattro
  (vedi *Le tre leghe nuove col `b48`: la regola*, «Esito del passo dopo»). Con
  `CONF_1X2_MODE = 'tabella'` si torna alla tabella qui sotto.
- **1X2 fino al `b52`**: `CONF_1X2_TABLE`, tabella empirica per fascia (`b38`, 1882 partite),
  riconfermata in copia conforme nel `b41` (8 fasce su 8 dentro 2se) e col `b48` sulle cinque
  leghe (fuori lega né le probabilità nude né una tabella rifatta la battono). **Fuori da quelle
  cinque non regge** (`b52`, χ² 32.2 su tre leghe nuove, e la probabilità nuda la batte). Con
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
corner. Fasce (`EDGE_BANDS`): ≥20 FORTE, ≥10 GIOCABILE, ≥5 MARGINALE. Dal `b50` ogni fascia
porta il guadagno misurato **per famiglia di mercato** (1X2, gol, numeri: `EDGE_FAMIGLIA` dice
di quale famiglia è ogni chiave), con ±2se e numero di proposte, e ogni riga mostra quello della
sua famiglia.

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

Il testo da copiare in un LLM (card «MEGA-PROMPT»). Serve a due cose, scelte dall'utente nel
`b51`: **decidere cosa giocare** e **capire la partita**. L'LLM spiega, non ricalcola: tutti i
numeri escono dalle stesse variabili dello schermo, e verdetti e rese del tabellone sono dati
come misurati, da non ridiscutere.

**I dati, in quest'ordine** (dal `b51`):

1. **Il verdetto 1X2**: probabilità, quote eque, ruolo contro generale, e il **pick con la sua
   fascia**: la confidence spiegata (quante volte esce un pick con quella probabilità) e dove
   sta nella selezione, dalle soglie misurate di `PICK_RESA` (sopra il 55%: «rientra nel 38% di
   partite più sicure, dove nel complesso il pick esce il 66.0%»; sotto il 45%: non si
   seleziona). Il numero cumulato di una soglia non è la probabilità di quel pick: per quella
   c'è la confidence.
2. **Il tabellone**: le proposte con verdetto per intero, ognuna con quanto rende il suo tipo
   di mercato (`EDGE_BANDS` per famiglia), e quelle senza verdetto in una riga sola. Il prompt
   dice che FORTE/GIOCABILE vuol dire «rende più del giocarlo alla cieca», non «probabile» (un
   `2` al 45% può essere giocabile), e che una doppia chance contiene l'esito singolo.
3. **L'Elo**: rating, vantaggio campo (col clamp detto quando morde), trend, Elo contro modello
   su 1 contro 2 con l'avviso quando distano 10+ punti e decide l'Elo.
4. **I rischi già calcolati**, in JS e non dall'LLM: Elo e modello in disaccordo, meno di 6
   partite di ruolo, pick sotto il 50%, clamp dell'HFA, statistiche avanzate assenti, riposo
   molto diverso.
5. **Le statistiche avanzate previste** con le loro regole di affidabilità (quali reggono,
   quali valgono a metà, quali non usare).
6. **Qualità e cinismo**, con l'avvertenza misurata che la fortuna recente non anticipa il
   risultato.
7. **Stile**, dichiarato descrittivo (medie storiche, non previsioni).
8. **Tempi dei gol e mercati sui numeri.**
9. **Stanchezza** (riposo, partite in 14 giorni, coppe europee), dichiarata contesto: misurato,
   non migliora la previsione (vedi *La stanchezza*).

**Le risposte chieste**: *IN SINTESI* (cinque righe: cosa giocare, quanto rende il suo tipo di
mercato, «niente di giocabile» se non c'è niente, il pick e il rischio principale), *LA PARTITA*
(otto righe), *PERCHÉ LE PROPOSTE* (una frase per proposta con verdetto), *RISCHI*. Le regole
(niente risultati esatti, niente «certo/sicuro/esplosione/goleada», non mescolare ruolo e
generale, N/D detto, stanchezza e fortuna solo contesto) stanno in un blocco che il prompt dice
esplicitamente di non scrivere come sezione.

**Cosa è uscito nel `b51`**, e perché: Ordered Logit e KNN (peso 0 nell'1X2: l'OL poteva dire
`2` al 47% con un verdetto `1`), la correzione residuale spenta, le partite simili del KNN (due
partite), i dettagli delle pause dell'Elo e della scala. Prima il prompt aveva numeri vecchi
(«2963 partite», «pick al 52%, fascia alta al 74%»), la frase rotta «nei mercati dei mercati
gol» del `b50`, *COSA NON FARE* elencata fra le sezioni da scrivere, e chiedeva una frase per
ognuna delle 13 righe del tabellone, anche senza verdetto, con un «FUORI SOGLIA» che il
tabellone non usa. Formazioni e assenze **non** ci sono, per scelta dell'utente.

**Fuori dai cinque campionati** (dal `b52`). Se la lega non è in `PICK_RESA.leghe`, il verdetto
dice che soglie e confidence non valgono lì; per Championship, Eredivisie e Liga Portugal dà quelle
misurate a parte (`PICK_RESA.fuori`), per le altre dice che non sono misurate e l'intervallo visto
nelle leghe misurate. Fra i rischi calcolati c'è «Lega fuori dai cinque campionati» (le rese del
tabellone sono misurate su quelli) o «Lega mai misurata», e la regola sul non promettere di più
cita la resa «nei cinque campionati misurati». Dal `b53` la confidence è spiegata come «la
probabilità del pick, già calibrata dal motore».

**Controllo.** Il banco (dal `b51`) guarda il prompt di ogni partita dello Scanner: non vuoto,
niente `NaN`, `undefined`, `Infinity`; col controllo di potenza (un `NaN` messo apposta) fallisce.
Il contenuto va riletto a mano quando cambia: il banco non sa se una frase è giusta. La lega finta
del banco usa l'id della Serie A, quindi il ramo «fuori dai cinque» il banco non lo passa: al
`b52` è stato verificato a parte, sulla stessa partita, togliendo la lega da `PICK_RESA.leghe`
(e mettendola in `PICK_RESA.fuori`): le due frasi e il rischio compaiono, niente `NaN`, 0 px di
scorrimento.

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
   `__ELO_DEBUG_OVER`, `__ELO_TREND`, `__UNIT_DEBUG`, `__ENS_DEBUG`, `__SCOPE_DEBUG`, `__LINEUP_DEBUG`, `__FATIGUE_DEBUG`, `m1/mX/m2`, `probsRole`,
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
  (`cmpEngineDefaults`, 30 manopole dal `b48`), piu' `CMP_K_LIST[0]` contro `SHRINK_K`;
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
`safeHtml`, strumentate nei due file allo stesso modo: 190 per partita) e **122 righe del CSV**
che riportano un numero dello Scanner (1X2, confidence di tutti i mercati, i sei modelli,
GG e Over, corner/tiri/gialli e le loro linee, handicap, multigol, Elo, tabellone voce per
voce, certificato, dal `b43` gli indici delle formazioni, dal `b44` quelli della stanchezza, dal
`b47` la pendenza dell'Elo, dal `b48` il livello d'ingresso delle neopromosse). Tre modalita' sono controlli di
potenza, e passano solo se il certificato dice NO col motivo giusto. Dal `b43` la lega finta ha
anche le formazioni (rosa di 18, ogni titolare abituale riposa col 15%, la squadra 3 cambia
allenatore a stagione in corso) e i marcatori presi dai titolari; dal `b44` una Champions finta
(le squadre 0 e 1 giocano 3 giorni prima e 4 dopo ogni giornata, la 2 solo dopo); dal `b45`
statistiche per giocatore come `/players` (gol e assist omessi quando valgono zero, il
portiere senza il gruppo dei duelli) e gialli per giocatore negli eventi. Il banco stampa gli
indici di ogni partita: se fossero tutti vuoti il confronto non proverebbe niente. Dopo il giro
dello Scanner preme anche il bottone dei giocatori e passa tutti e 15 i mercati: fallisce se una
tabella è vuota o contiene `NaN`, `undefined` o `Infinity`. Dal `b47`, nel batch e nello sweep,
rilegge l'archivio di lega dal **testo** del CSV esportato, ci fa girare `buildGlobalElo` del
motore e confronta Elo e HFA con le righe del CSV, partita per partita; il controllo di potenza
toglie una partita dall'archivio e deve vedere l'Elo cambiare.

Esito al `b53` (storico 30), a 390px (anche nessuna tabella compatta che esce dal suo riquadro, e il mega-prompt dello Scanner mai vuoto né rotto):

| modalita' | copia conforme | scritture del motore diverse | righe CSV diverse | scorrimento laterale |
|---|---|---|---|---|
| una partita, tutte del giorno, intervallo | 3/3 | 0 su 190 | 0 su 122 | 0 |
| batch per stagioni, sweep | 89/89, solo la stagione caricata; archivio 270 partite su 270, Elo rifatto identico su 89 su 89 (senza una partita: 87 diverse) | 0 su 190 | 0 su 122 | 0 |
| intervallo che sconfina nella stagione prima | 57/57, 20 partite saltate con avviso | 0 | 0 | 0 |
| `ab`: scala Elo 1.00 e uno storico diverso da quello dello Scanner (controllo) | 0/3, «ELO_SCALE ... / storico di 15 partite invece delle 30 ...» | 127-155 | 74-82 | 0 |
| `vecchio`: motore `b52` caricato (controllo) | 0/3, «motore caricato diverso ...» | 4 (le confidence dell'1X2) | 5 (le quattro confidence e il certificato) | 0 |

Al `b39` lo stesso controllo col motore `b38` aveva dato 0 scritture diverse su 188: il
motore `b39` stampava esattamente quello del `b38`, e le differenze erano tutte nel
Comparatore. Al `b40` il motore cambia davvero (lo storico passa a 30, 131-152 scritture
diverse col `b39`). Al `b41` il controllo col `b40` vede solo le due correzioni: le confidence
degli esiti non scelti (36/36/36 → 34/30/33) e il tabellone, dove sale in cima un mercato sui
numeri. Al `b42` il controllo col `b41` vede solo i tiri in porta: le quattro linee Over, la
loro riga nel tabellone e il certificato. Al `b43` il controllo col `b42` vede solo la card
delle formazioni, le venti righe nuove del CSV e il certificato: le probabilità non si muovono.
Al `b44` il controllo col `b43` vede solo la card (ora con la stanchezza), le righe della
stanchezza che cambiano e il certificato. Al `b45` il controllo col `b44` vede solo il
messaggio iniziale della card dei giocatori e il certificato. Al `b46` il controllo col
`b45` vede solo la card delle formazioni (la riga «Rispetto alla probabile») e il certificato.
Al `b47` il controllo col `b46` non vede nessuna scrittura diversa: solo le sei righe della
pendenza (a `N/D`, il `b46` non la espone) e il certificato. Al `b48` il controllo col `b47`
vede 19-76 scritture diverse: la lega finta ha squadre che entrano e escono, quindi cambiano
rating, pendenze e tutto quello che ne discende. Al `b49` il controllo col `b48` non vede
nessuna scrittura diversa e una sola riga del CSV, il certificato: cambia solo il testo fisso
della card delle soglie. Al `b50` il controllo col `b49` vede una scrittura diversa, il
tabellone (le etichette per famiglia), e il certificato. Al `b51` il controllo col `b50` non
vede nessuna scrittura diversa: cambia il mega-prompt, che non passa da `safeHtml`, e la card
delle soglie, che è testo fisso scritto una volta all'apertura. Al `b52` lo stesso col `b51`: cambiano
il mega-prompt fuori dai cinque campionati e il testo fisso delle card della confidence e delle
soglie. Al `b53` il controllo col `b52` vede solo le confidence dell'1X2: quelle di `1`, `X`, `2` e la
globale a schermo (4 scritture), le stesse quattro righe del CSV e il certificato; le probabilità,
le doppie chance e i mercati binari non cambiano.

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
  sono nel confronto; del mega-prompt, dal `b51`, il banco controlla solo che non sia vuoto o
  rotto.

**Come si rifa'.** `node strumenti/banco-parita.js` (tutte le modalita' e i controlli, circa
tre minuti); `MOBILE=1` misura lo scorrimento laterale a 390px; `VECCHIO=<scanner vecchio>`
aggiunge il controllo sul motore diverso dal pubblicato; `PENDENTI=1` mette due partite non
concluse nel database; `SALVA_CSV=<cartella>` salva l'ultimo CSV di ogni modalita' (serve a
provare su dati finti gli strumenti che leggeranno i CSV veri). Esce con 0 se tutto e' come
deve essere.

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

**Il «4 su 5».** Il candidato migliora in quattro leghe su cinque, ma due sono quelle su cui
è stato scelto: le prove sono tre, e fanno due vittorie e un pari. Con la regola delle
formazioni (N−1 su N) sarebbe passato; la regola scritta per lui chiedeva tutte e tre, e
cambiarla dopo aver visto l'esito è l'errore che ha prodotto quattro falsi positivi. Non dice
nemmeno che l'Elo vale di più: il suo peso scende da 0.75 a 0.40, sale la scala della sua
differenza di rating (`w·S` da 0.94 a 0.80) e scende il peso del suo vantaggio campo. Quanto
vale, se è vero, sulle cinque leghe: prese da 52.8 a 53.1% (il pick cambia nel 3–5% delle
partite), selezione da 62.1 / 68.6 / 72.6 / 78.2 a 62.6 / 69.1 / 72.6 / 79.0% giocando metà,
30, 20 e 10% del calendario. È un ritocco della calibrazione, non un salto.

**Il secondo giro, registrato prima del batch `b47`.** Prima si corregge l'ingresso delle
neopromosse (*Le neopromosse*): i pesi dipendono dall'Elo che pesano. Poi, sull'Elo corretto,
si rispazza (`w`, `S`) sulle cinque leghe note e si sceglie fuori lega, dentro la griglia e non
sul bordo. La coppia scelta si prova su Eredivisie, Liga Portugal e Championship (tre
stagioni, mai guardate) con la regola di formazioni e stanchezza: logloss 1 contro 2 migliore
in almeno due leghe su tre, `z ≤ −2` sull'insieme, nessuna lega con `z > +1`, prese del pick
non in calo. Se passa, entra con `CONF_1X2_TABLE`, soglie del pick e scarti dell'1X2 rifatti
sulle probabilità ricostruite. **Il test del `b41` resta non passato**: questo è un test nuovo
su dati nuovi, non una rilettura del primo.

**Fissato prima di aprire le tre leghe (batch `b47`).** Sulle cinque leghe note la griglia dà lo
stesso punto sia con l'Elo in uso sia con B + C: **`w` 0.40, `S` 2.00**, dentro la griglia.
Con l'Elo in uso fuori lega −0.00492 (`z = −4.07`, scelto 0.40 / 2.00 in cinque fold su cinque),
prese 52.79 → 53.06%; sopra B + C −0.00262 (`z = −2.29`), prese 52.72 → 53.15%. La coppia si
prova sopra l'Elo che esce dal secondo passo delle neopromosse (B + C se passa, altrimenti
quello in uso), contro 0.75 / 1.25 sullo stesso Elo. «Prese non in calo» vuol dire, anche qui,
differenza appaiata non sotto −2 errori standard.

**Esito del secondo giro (sopra B + C, che è passato): non passa.** Eredivisie −0.00272 (`z =
−1.00`), Liga Portugal −0.00467 (`z = −1.70`), Championship +0.00125 (`z = +0.52`); insieme
−0.00135, `z = −0.89` contro il −2 richiesto; prese +0.09. Il verso è lo stesso delle cinque
leghe, ma su leghe mai viste l'effetto è la metà e non si distingue dal rumore. **Resta 0.75 /
1.25.** Il motore corretto per intero (B + C con 0.40 / 2.00) contro quello del `b47`, solo
descrittivo: −0.00211, `z = −1.06`.

In Bundesliga, a `S` fisso, anche il vecchio sweep di `w` dice 0.50 meglio di 0.75 (`z =
−1.75`); in Ligue 1 è piatto (0.5945 contro 0.5943). Su LaLiga la griglia, guardata solo
dopo il test, ha la stessa cresta: il minimo sta vicino
al candidato (−0.0042 a 0.40 / 2.00, −0.0045 a 0.30 / 2.50, sulla stessa cresta), e la pendenza del prodotto
finito passa da 1.163 a 1.051.

### Le tabelle col `b48`

Il `b48` sposta l'Elo di tutte le squadre quando una neopromossa entra più in basso, e con lui
tutte le probabilità dell'1X2 (il pick cambia in 202 partite su 5230). `CONF_1X2_TABLE`, le soglie
del pick e le fasce del tabellone erano misurate sul motore di prima: si rifanno col batch
automatico delle cinque leghe, stesse stagioni e stesse partite dei file `b41`/`b47`. **5230
partite su 5230 in copia conforme**, l'Elo rifatto dall'archivio identico su ogni file, 13 file in
71 minuti (più Premier e Serie A 2025/26 già fatti), nessuna chiamata fallita.

**Il `b48` sul motore vero**, contro il `b47` sulle stesse partite:

| lega | logloss 1 contro 2 | logloss 1X2 | prese | pendenza 1 contro 2 |
|---|---|---|---|---|
| Serie A | −0.00363 | −0.00218 | 52.91 → 52.73 | 1.249 → 1.151 |
| Premier | −0.00653 | −0.00394 | 52.78 → 52.69 | 1.120 → 1.012 |
| LaLiga | −0.00252 | −0.00182 | 54.23 → 53.17 | 1.150 → 1.064 |
| Bundesliga | −0.00558 | −0.00389 | 51.75 → 52.52 | 1.150 → 1.086 |
| Ligue 1 | +0.00026 | +0.00050 | 51.91 → 52.35 | 1.038 → 0.948 |
| insieme | −0.00367 (`z = −2.56`) | −0.00231 (`z = −2.08`) | 52.79 → 52.72 (±0.45) | 1.143 → 1.053 |

È quello che la ricostruzione dall'archivio aveva previsto (−0.00375, `z = −2.64`, Ligue 1 la sola
contraria): le misure del test erano quelle del motore.

**`CONF_1X2_TABLE`: resta.** Per fascia sulle cinque leghe (pick, p media, tabella, hit, ±2se):
< 40 756 / 37.8 / 37.0 / 36.4 / 3.5; 40–45 928 / 42.4 / 45.1 / 41.8 / 3.2; 45–50 808 / 47.4 /
51.9 / 50.2 / 3.5; 50–55 755 / 52.4 / 54.8 / 50.2 / 3.6; 55–60 604 / 57.3 / 57.6 / 58.4 / 4.0;
60–65 525 / 62.4 / 66.5 / 63.0 / 4.2; 65–70 374 / 67.3 / 71.0 / 68.2 / 4.8; ≥ 70 480 / 75.8 /
78.0 / 77.1 / 3.8. χ² 16.2 su 8 (`b47` sulle stesse partite 11.6); per lega 7.9 / 18.1 / 8.4 /
5.0 / 9.6, con la Premier fuori nella fascia 65–70 (58.3 contro 71.1). Le probabilità del `b48`
sono quasi calibrate da sole, e la tabella, che le alzava fra 40 e 55, ora le alza un po' troppo.
Ma fuori lega (tabella stimata su quattro leghe, Brier della confidence sulla quinta) nessuna
alternativa la batte: le probabilità nude −0.00043 (`z = −1.01`), una tabella rifatta +0.00007
(`z = +0.18`). Gli esiti non scelti sotto 37.6: hit/p 0.996 su 10.452 probabilità (`b47` 0.968),
contro lo 0.960 della tabella: un 11% mostra 10.6, trascurabile.

**Le soglie del pick: riscritte nella card.** Sopra ogni soglia c'è più calendario e un paio di
punti in meno di resa (tabella in *Stato attuale*). La card mostrava i numeri della Serie A del
`b41` (≥65 → 73.7%, 1 partita su 10); dal `b49` mostra le cinque leghe col `b48` (≥65 → 73.2%, 1
su 6.1). La selezione a pari quota del calendario (ordinando dentro ogni file di stagione) non
cambia fino al 20%: 62.0 / 69.3 / 71.8% contro 62.0 / 68.8 / 72.4% al 50 / 30 / 20% (bootstrap
appaiato 0.0 ±0.9, +0.5 ±1.3, −0.7 ±1.8). Al 10% sì: 76.2 contro 79.1% (−2.9 ±2.4). Le 72 partite
che entrano in quel 10% col `b48` sono per 69 contro una neopromossa, previste al 70.7% e vinte
al 55.1%; le 72 che escono sono per 70 senza neopromosse, previste al 67.1% dal `b47` e vinte al
75.7%. Su tutte le partite col pick contro una neopromossa il `b48` è calibrato per fascia (sotto
55: 46.5 previsto, 44.7 reale; 55–65: 59.9 e 61.0; ≥70: 76.6 e 77.7) tranne 65–70 (67.2 e 58.0,
119 partite, ±9.0), dove il `b47` era sotto in tre fasce su quattro. È un'osservazione trovata
dopo, su quattro quote guardate insieme: si rifà sulle tre leghe nuove prima di toccare niente
(vedi *Da fare*).

**`EDGE_BANDS`: le soglie restano, l'etichetta è da rifare per mercato.** Sulle cinque leghe,
guadagno sopra il giocarlo alla cieca (±2se, proposte):

| fascia | tutti | 1X2 | gol | numeri | `b47`, tutti |
|---|---|---|---|---|---|
| MARGINALE 5–10 | +6.1 ±1.1 (7765) | +8.0 ±1.9 (2680) | +3.5 ±1.7 (3457) | +8.2 ±2.4 (1628) | +6.1 |
| GIOCABILE 10–20 | +12.2 ±1.2 (6512) | +15.5 ±1.6 (3573) | +7.2 ±2.3 (1881) | +10.2 ±2.9 (1058) | +13.4 |
| FORTE ≥ 20 | +25.8 ±1.6 (3116) | +27.5 ±1.6 (2891) | +1.0 ±10.4 (92) | +7.2 ±8.0 (133) | +26.8 |

Monotone in tutte e cinque le leghe (FORTE / GIOCABILE / MARGINALE: Serie A +25.7 / +14.0 / +5.8,
Premier +25.5 / +9.5 / +6.1, LaLiga +25.4 / +12.3 / +7.3, Bundesliga +28.1 / +13.2 / +6.4, Ligue 1
+24.7 / +12.4 / +4.4). La proposta migliore di ogni partita rende +16.8 (±1.3; Serie A +18.8,
Premier +16.2, LaLiga +16.8, Bundesliga +16.9, Ligue 1 +15.0), in cima `1` 26%, `X2` 21%, gialli
16%, `2` 14%, Under 13%, `1X` 7%; almeno una FORTE o GIOCABILE nell'80% delle partite. I numeri
che l'etichetta mostrava (+24.6 / +14.8 / +6.3, Serie A `b38`) nel `b49` sono rimasti: rimpiazzarli
con la media delle cinque leghe (+25.8 / +12.2 / +6.1) avrebbe avvicinato i mercati gol e
allontanato l'1X2, e la media non è giusta per nessuno dei due. Dal `b50` l'etichetta è per
famiglia (vedi *Il tabellone per famiglia di mercato: la regola*).

### Il tabellone per famiglia di mercato: la regola

**Perché.** Col `b48` sulle cinque leghe, a parità di scarto il guadagno dipende dal mercato
(tabella in *Le tabelle col `b48`*): l'1X2 rende quanto lo scarto promette, i mercati gol la metà
o meno, quelli sui numeri in mezzo. Lo scarto dei gol è gonfiato perché le loro probabilità
discriminano poco (AUC 0.55), e quello dell'Under anche perché il livello dei gol è basso (l'Over
previsto sta sotto il reale). Il tabellone ordina e classifica per scarto grezzo: mette in cima
proposte che rendono meno di altre più in basso, e le etichetta con un guadagno che non hanno.

**Il candidato.** Il **guadagno atteso** di ogni proposta, `g = α + β·scarto` in punti, al posto
dello scarto: per ordinare, per le fasce (FORTE ≥ 20, GIOCABILE ≥ 10, MARGINALE ≥ 5, le stesse
soglie, ora sul guadagno atteso) e per l'etichetta, che dice il guadagno atteso di quella
proposta. `α` e `β` si stimano a minimi quadrati di `reale − base di lega` (in punti) su `scarto`,
dentro ogni gruppo. Due forme, e nient'altro:

- **F**, per famiglia: 1X2 (`1`, `X`, `2`, `1X`, `X2`, `12`), gol (Over 2.5, Under 2.5, Goal,
  NoGoal), numeri (corner, tiri in porta, gialli). Sei parametri.
- **M**, per mercato: una coppia (`α`, `β`) per ognuno dei tredici mercati. Ventisei parametri.

**Il metro.** Il guadagno della proposta in cima a ogni partita: reale meno la frequenza di quel
mercato nella stagione del file (il metro di *Il tabellone ordinava per la colonna sbagliata*;
col `b48` oggi +16.8 sulle cinque leghe). La differenza col tabellone di oggi si misura appaiata,
partita per partita. Descrittivi: guadagno delle proposte FORTE e GIOCABILE, quante partite ne
hanno almeno una, guadagno per fascia e famiglia.

**Primo passo, sulle cinque leghe (`b48`), fuori lega.** Parametri stimati su quattro leghe,
misurati sulla quinta. Fra F e M si sceglie quella col guadagno d'insieme più alto, ma M solo se
batte F di almeno un errore standard: a pari merito vince la forma con meno parametri. Il
candidato scelto va al secondo passo se il guadagno della prima proposta migliora rispetto
all'ordine per scarto in almeno quattro leghe su cinque e sull'insieme con `z ≥ +2`. L'idea viene
da queste leghe, quindi questo passo da solo non basta.

**Secondo passo, sulle tre leghe nuove.** Parametri stimati su tutte e cinque le leghe, e scritti
qui **prima** di aprire le tre leghe. Eredivisie, Liga Portugal e Championship 2023/24–2025/26:
dei loro file sono stati guardati copia conforme, Elo e formazioni, mai il tabellone. I file sono
del `b47`, cioè con le probabilità dell'1X2 di prima dell'ingresso delle neopromosse: il batch
`b48` di quelle leghe (vedi *Da fare*, la coda alta della selezione) sarà una seconda conferma.
Passa se il guadagno della prima proposta migliora in almeno due leghe su tre, sull'insieme con
`z ≥ +2`, e nessuna lega peggiora con `z < −1`. Se passa, entra nel motore (una tabella
`EDGE_GAIN` con `α` e `β`), e il CSV esporta il guadagno atteso di ogni proposta.

**Se non passa.** L'ordine resta per scarto. L'etichetta dice comunque, per ogni fascia, il
guadagno misurato **nella famiglia del mercato** (è una misura, non una scelta): un Over 2.5
FORTE mostra quello che rende davvero.

**Esito del primo passo: non passa.** Guadagno della prima proposta sulle cinque leghe `b48`,
fuori lega, contro l'ordine per scarto (oggi +16.8):

| lega | partite | oggi | F | differenza | `z` | prima proposta cambiata |
|---|---|---|---|---|---|---|
| Serie A | 1134 | +18.8 | +19.8 | +1.02 ±0.61 | +1.68 | 103 |
| Premier | 1135 | +16.2 | +16.7 | +0.52 ±0.73 | +0.71 | 180 |
| LaLiga | 1134 | +16.8 | +15.9 | −0.96 ±0.50 | −1.93 | 85 |
| Bundesliga | 912 | +16.9 | +17.4 | +0.46 ±0.76 | +0.60 | 137 |
| Ligue 1 | 915 | +15.0 | +14.5 | −0.47 ±0.65 | −0.73 | 86 |
| insieme | 5230 | +16.8 | +16.9 | +0.12 ±0.29 | +0.42 | 591 |

M fa lo stesso (+0.11 ±0.33, `z = +0.33`, tre leghe su cinque; M contro F −0.01 ±0.26), quindi
vince F per semplicità, e F non arriva né a quattro leghe su cinque né a `z ≥ +2`. Il secondo
passo non si fa: **i tabelloni delle tre leghe nuove restano non guardati**, buoni per un test
futuro. Parametri su tutte e cinque, per chi ci torna: F 1X2 `α` 0.0 `β` 1.041, gol 0.0 / 0.525,
numeri −0.74 / 1.062; in M l'Under ha `α` −3.0 e l'Over +3.0 (il livello basso dei gol), il
Goal +2.4 e il NoGoal −2.4.

**Perché non serve riordinare.** La prima proposta è quasi sempre dell'1X2 in tutti e due gli
ordini (`1`, `X2`, `2`, `1X` fanno il 68% oggi e il 77% col candidato). Dove il candidato toglie
dalla cima un mercato gol (Under in cima dal 13% al 4% delle partite), mette al suo posto un 1X2
con lo scarto più basso, che rende più o meno lo stesso. E la retta per famiglia non basta per i
numeri: le proposte che F manda in FORTE rendono +9.1 contro +23 attesi, perché lo scarto dei
gialli e dei corner dipende dal riferimento di lega sbagliato (vedi *Da fare*), non dalla
partita.

**Cosa è entrato nel motore (`b50`).** Solo l'etichetta: `EDGE_BANDS` porta per ogni fascia il
guadagno, ±2se e le proposte di ciascuna famiglia (misurati sulle cinque leghe `b48`, tabella in
*Le tabelle col `b48`*), e ogni riga del tabellone e del mega-prompt dice quello della sua: un
Goal MARGINALE «rende +3.5 punti (±1.7) sopra il giocarlo sempre (3457 proposte dei mercati gol)»,
un tiri in porta FORTE «+7.2 (±8.0), 133 proposte dei mercati sui numeri». La legenda della card
dice le cifre dell'1X2 e che gli altri mercati rendono molto meno. Ordine, fasce e verdetti sono
quelli di prima: il CSV non cambia.

**A 390px il tabellone usciva di lato.** L'intestazione «Scarto · quanto rende» non andava a capo
e allargava la tabella a 393 px dentro un riquadro di 340: la pagina restava a 0 px di
scorrimento, quindi il banco non lo vedeva. Dal `b50` l'intestazione va a capo, e il banco misura
anche le tabelle compatte dentro il loro riquadro (col vecchio tabellone fallisce: `card-verdetti`
53 px).

### Le tre leghe nuove col `b48`: la regola

Scritta prima del batch del motore `b51` (probabilità identiche al `b48`) su Eredivisie, Liga
Portugal e Championship 2023/24–2025/26, confrontato con i file `b47` delle stesse partite. Di
queste leghe sono stati guardati copia conforme, Elo, formazioni e l'Elo corretto ricostruito
fuori dal motore; mai la selezione del pick, le soglie, i mercati né il tabellone.

**1. La coda alta (decide la voce di *Da fare*).** Ordinando dentro ogni file di stagione per
probabilità del pick, la resa del 10% più alto del calendario, `b48` meno `b47` sulle stesse
partite, con l'errore dal bootstrap sulle partite (il metodo delle cinque leghe).
- **Confermata** se la differenza è sotto −2 errori standard **e** più di metà delle partite
  che entrano nel 10% col `b48` sono contro una neopromossa (squadra assente dalla stagione
  prima nell'archivio, entrata dal basso o, in Championship, dall'alto). Allora si cerca una
  correzione dell'ingresso, da provare su leghe mai viste.
- **Smentita** se la differenza è ≥ 0: la voce si chiude, il `b48` resta.
- **Non decisa** in mezzo: la voce si chiude lo stesso, scrivendo che il test aveva poca potenza
  (circa 3.500 partite: su un effetto come quello visto, ±3 punti di rumore) e riportando la
  stima delle otto leghe insieme, solo descrittiva.
- Descrittivo: la calibrazione del pick contro una neopromossa per fascia (< 55, 55–65, 65–70,
  ≥ 70), `b47` e `b48`.

**2. I numeri della card fuori dai cinque campionati.** Sulle tre leghe insieme:
- le soglie di `PICK_RESA` **reggono** se la resa a ≥ 50 / 55 / 60 / 65 / 70 sta ciascuna
  entro 2 errori standard dal numero della card; altrimenti la card deve dire che valgono per
  i cinque campionati;
- `CONF_1X2_TABLE` **regge** se il χ² sulle 8 fasce del pick sta sotto 15.5 (il 95° percentile
  a 8 gradi di libertà).

**3. Il `b48` sul motore vero**, solo descrittivo (il test è già passato sulla ricostruzione):
logloss 1 contro 2 e 1X2, prese, pendenza di calibrazione, contro il `b47`.

**4. I mercati, chiesti dall'utente**, solo descrittivi, per lega: AUC di `1`, `2`, `X`, Over
2.5 e Goal; Over 2.5 e Goal previsti contro reali; corner, tiri in porta e gialli previsti
contro reali e AUC. Dalle righe delle probabilità, **non** dalla sezione `TABELLONE`, che resta
non guardata per un test futuro.

**Esito (`b52`).** Batch automatico del `b51`, 9 file, 3495 partite su 3495 in copia conforme,
l'Elo rifatto dall'archivio identico su ogni file, nessuna chiamata fallita; stesse partite dei
file `b47`.

*1. La coda alta: non decisa.* Il 10% più alto prende il 78.2% col `b48` e il 78.4% col `b47`:
−0.3 punti, errore dal bootstrap 0.98, `z = −0.29`. Non è sotto −2se (serviva −2.0), non è ≥ 0.
Il test aveva meno rumore di quanto scritto (±2.0 a 2se invece di ±3), e l'effetto delle cinque
leghe (−2.9) sta a 1.7σ da quello visto qui: non si ripete, ma non si esclude. Entrano nel 10%
solo 25 partite (17 contro una neopromossa, il 68%), previste al 74.2% e vinte al 76.0%; ne
escono 25, previste al 71.9% dal `b47` e vinte all'80.0%. Le otto leghe insieme, solo
descrittivo: −1.8 (errore 0.91, `z = −2.03`), 97 partite entrate, 86 contro una neopromossa,
previste al 71.6% e vinte al 60.8%. La voce si chiude, l'ingresso resta quello del `b48`.
Calibrazione del pick contro una neopromossa (previste / vinte) sulle tre leghe: `b47` sotto il
55% 44.0 / 43.8, 55–65 59.6 / 59.6, 65–70 66.9 / 72.7, ≥ 70 75.8 / 82.6; `b48` 44.2 / 41.4, 59.5 /
60.8, 67.3 / 59.4 (32 partite, ±17), 77.5 / 79.2. Sulle otto l'unica fascia storta del `b48` resta
65–70 (151 partite, previste 67.2, vinte 58.3 ±8.0), fra due fasce calibrate: da tenere d'occhio,
non da correggere.

*2. I numeri della card: le soglie non reggono, la confidence nemmeno.*

| soglia | tre leghe nuove | ±2se | quota del calendario | card (cinque leghe) | esito |
|---|---|---|---|---|---|
| ≥50% | 62.8% | 2.4 | 45% | 61.7% | regge |
| ≥55% | 69.0% | 2.8 | 32% | 66.0% | fuori |
| ≥60% | 73.6% | 3.1 | 22% | 69.3% | fuori |
| ≥65% | 77.6% | 3.5 | 16% | 73.2% | fuori |
| ≥70% | 82.6% | 3.9 | 11% | 77.1% | fuori |

Per lega (≥50 / 55 / 60 / 65 / 70, e quota del calendario): Championship 57.1 / 64.8 / 73.5 / 75.8
/ 82.8% su 31 / 17 / 9 / 4 / 2%, Eredivisie 63.1 / 68.7 / 70.5 / 74.3 / 81.0% su 61 / 47 / 36 / 26
/ 18%, Liga Portugal 68.4 / 72.4 / 76.9 / 81.4 / 84.0% su 54 / 43 / 34 / 27 / 21%. Pick su tutte
46.3 / 53.7 / 55.0%, «sempre in casa» 43.8 / 44.5 / 42.6%. Come dice la regola, dal `b52` la card
e il prompt dicono che le soglie valgono per i cinque campionati (`PICK_RESA.leghe`) e riportano
quelle di queste tre (`PICK_RESA.fuori`: pick su tutte e resa a ≥ 55, la soglia con abbastanza
partite in ogni lega; la Championship ha 29 partite sopra il 70%).

`CONF_1X2_TABLE`: χ² 32.2 su 8 (soglia 15.5), **non regge**; per lega (Championship, Eredivisie,
Liga Portugal) 15.2 / 20.0 / 12.5. Per
fascia (pick, tabella, vinte, ±2se): < 40 619 / 37.1 / 34.7 / 3.8; 40–45 712 / 45.1 / 42.0 / 3.7;
45–50 592 / 51.9 / 44.8 / 4.1; 50–55 459 / 54.7 / 47.7 / 4.7; 55–60 329 / 57.8 / 58.1 / 5.4; 60–65
230 / 66.5 / 63.9 / 6.3; 65–70 174 / 71.1 / 66.7 / 7.1; ≥ 70 380 / 78.2 / 82.6 / 3.9. Lo sbaglio
grosso è fra il 45 e il 55%, uguale in tutte e tre le leghe (45–50: vinte 45.2 / 45.4 / 42.9
contro 51.9 mostrati), dove la tabella alza probabilità che già stanno sopra il vero. Descrittivo,
non era nella regola: la probabilità nuda ha un Brier più basso della tabella (+0.00137 per la
tabella, `z = +2.68`). La card della confidence lo dice dal `b52`; il candidato è in «Il passo
dopo».

*3. Il `b48` sul motore vero*, contro il `b47` sulle stesse partite:

| lega | logloss 1 contro 2 | ricostruzione (`b47`) | logloss 1X2 | prese | pendenza 1 contro 2 |
|---|---|---|---|---|---|
| Championship | −0.00029 (`z = −0.57`) | −0.00031 | −0.00011 | 46.29 → 46.29 | 0.900 → 0.892 |
| Eredivisie | +0.00044 (`z = +0.12`) | +0.00037 | +0.00051 | 53.95 → 53.74 | 1.144 → 1.035 |
| Liga Portugal | −0.00253 (`z = −0.78`) | −0.00271 | −0.00247 | 55.09 → 54.98 | 1.200 → 1.125 |
| insieme | −0.00068 (`z = −0.51`) | −0.00076 | −0.00056 | 50.62 → 50.53 (±0.53) | 1.082 → 1.020 |

Il motore vero fa quello che la ricostruzione dall'archivio aveva previsto. In Championship la
pendenza sta sotto 1 già col `b47`: lì le probabilità sono troppo aperte, non timide.

*4. I mercati* (righe delle probabilità; tra parentesi le cinque leghe, `b41`):

| | Championship | Eredivisie | Liga Portugal |
|---|---|---|---|
| AUC `1` / `2` / `X` (0.685–0.736 / 0.696–0.752 / 0.544–0.584) | 0.628 / 0.621 / 0.537 | 0.744 / 0.751 / 0.570 | 0.757 / 0.775 / 0.624 |
| AUC Over 2.5 / GG (0.541–0.598 / 0.483–0.557) | 0.574 / 0.559 | 0.560 / 0.533 | 0.599 / 0.538 |
| Over 2.5 previsto / reale (da −1.0 a −7.1) | 44.7 / 48.9 | 57.3 / 60.5 | 46.9 / 52.7 |
| Goal previsto / reale | 48.0 / 52.8 | 54.8 / 58.5 | 44.9 / 50.2 |
| gol a partita | 2.57 | 3.14 | 2.71 |
| corner Over 9.5: previsto / reale, AUC | 50.7 / 55.6, 0.547 | 61.5 / 56.7, 0.527 | 49.8 / 48.1, 0.553 |
| tiri in porta Over 8.5 | 40.7 / 40.6, 0.554 | 64.0 / 64.1, 0.550 | 47.1 / 45.1, 0.612 |
| gialli Over 3.5 | 54.8 / 54.1, 0.535 | 44.2 / 36.0, 0.546 | 65.4 / 69.6, 0.574 |

In Eredivisie e Liga Portugal, con poche squadre che dominano, l'1X2 discrimina più che nelle
cinque leghe; in Championship molto meno. I due muri dei gol ci sono tutti e due:
l'ordinamento è lo stesso (AUC 0.53–0.60) e il livello manca anche qui (Over sotto il vero di 3–6
punti). Il riferimento dei mercati sui numeri sbaglia da lega a lega come nelle cinque: i gialli
in Eredivisie stanno 8 punti sopra il vero, in Liga Portugal 4 sotto.

**Il passo dopo: la confidence nuda, registrato prima di aprire le quattro leghe.** Candidato
unico: la confidence dell'1X2 (del pick e degli esiti non scelti) uguale alla probabilità del
motore, al posto di `CONF_1X2_TABLE`. Si prova su 2. Bundesliga, First Division A (Belgio),
Premiership (Scozia) e Super League (Svizzera) 2023/24–2025/26, batch del motore in uso, leghe mai
aperte. Metro: Brier della confidence del pick, tabella contro probabilità nuda, appaiato partita
per partita. **Passa** se la nuda ha il Brier più basso in almeno tre leghe su quattro e
sull'insieme con `z ≤ −2`. Se passa, la confidence dell'1X2 diventa la probabilità
(`CONF_1X2_MODE = 'nuda'`, la tabella resta come manopola) e card e prompt lo dicono; se non
passa, la tabella resta e la card continua a dire che vale per i cinque campionati. Solo
descrittivi: le soglie di `PICK_RESA` e i mercati sulle quattro leghe.

**Esito del passo dopo (`b53`): passa.** Batch automatico del `b52`, 12 file, 3202 partite su 3202
in copia conforme, Elo rifatto dall'archivio identico su ogni file, nessuna chiamata fallita.
Alla prima giornata il motore salta le partite delle squadre senza storico nella lega (neopromosse
e retrocesse dalla serie sopra), come lo Scanner. Prova di coincidenza: la tabella applicata alla
probabilità del CSV, arrotondata, è la `Confidence Globale` entro 1 su 3202 partite su 3202.

| lega | partite | Brier tabella | Brier nuda | nuda meno tabella | `z` |
|---|---|---|---|---|---|
| 2. Bundesliga | 908 | 0.24253 | 0.24108 | −0.00145 | −1.44 |
| First Division A | 931 | 0.23878 | 0.23640 | −0.00238 | −2.33 |
| Premiership (Scozia) | 683 | 0.22525 | 0.22407 | −0.00118 | −1.03 |
| Super League (Svizzera) | 680 | 0.24445 | 0.24046 | −0.00399 | −3.41 |
| insieme | 3202 | | | −0.00220 | **−4.09** |

Quattro leghe su quattro e `z ≤ −2`: dal `b53` `CONF_1X2_MODE = 'nuda'`. La tabella sbaglia qui
come sulle tre leghe nuove: χ² 40.4 su 8, fra il 45 e il 55% mostra 51.9 / 54.8 e i pick escono
il 44.5 / 46.1%. Anche la probabilità nuda lì sta sopra il vero (47.4 / 52.4), ma di meno.

Descrittivi. Le soglie di `PICK_RESA` sulle quattro insieme reggono tutte (≥50 / 55 / 60 / 65 / 70:
59.4 / 66.2 / 69.9 / 73.6 / 78.7% su 44 / 29 / 19 / 12 / 7% del calendario; pick su tutte 48.8%,
«sempre in casa» 44.3%). Per lega, sopra il 55%: 2. Bundesliga 62.8% sul 16% (su tutte 45.4%),
First Division A 65.5% sul 35% (50.2%), Premiership 68.9% sul 41% (53.3%), Super League 66.1% sul
26% (47.1%): entrano in `PICK_RESA.fuori` come le tre leghe del `b52`.

| | 2. Bundesliga | First Division A | Premiership | Super League |
|---|---|---|---|---|
| AUC `1` / `2` / `X` | 0.619 / 0.602 / 0.518 | 0.698 / 0.687 / 0.557 | 0.732 / 0.710 / 0.598 | 0.624 / 0.633 / 0.536 |
| AUC Over 2.5 / GG | 0.509 / 0.525 | 0.562 / 0.542 | 0.521 / 0.561 | 0.573 / 0.535 |
| Over 2.5 previsto / reale | 54.9 / 59.1 | 53.6 / 52.1 | 49.5 / 55.6 | 53.9 / 59.0 |
| Goal previsto / reale | 56.8 / 59.3 | 53.8 / 54.5 | 48.0 / 51.8 | 55.7 / 61.8 |
| gol a partita | 3.01 | 2.75 | 2.83 | 3.03 |
| corner Over 9.5: previsto / reale, AUC | 60.6 / 57.4, 0.496 | 55.0 / 53.2, 0.484 | 57.8 / 62.8, 0.568 | 59.8 / 55.9, 0.524 |
| tiri in porta Over 8.5 | 58.3 / 55.0, 0.531 | 54.6 / 54.9, 0.563 | 50.0 / 46.4, 0.580 | 59.5 / 60.7, 0.535 |
| gialli Over 3.5 | 65.1 / 65.9, 0.570 | 54.3 / 52.1, 0.546 | 53.4 / 52.0, 0.571 | 62.9 / 63.8, 0.568 |

Le leghe equilibrate (2. Bundesliga, Super League) hanno l'1X2 che distingue poco, come la
Championship. L'Over resta sotto il vero in tre leghe su quattro (−4.2 / −6.1 / −5.1; il Belgio
+1.5), e in 2. Bundesliga non distingue niente (AUC 0.509). I corner non si prevedono in due leghe
su quattro (AUC sotto 0.5 in 2. Bundesliga e Belgio).

## Formazioni e assenze

**Perché.** Il pick sbaglia il 47.2% delle partite: 25.6 punti sono pareggi, 21.6 vittorie
dello sfavorito. Forma, riposo, momento dell'Elo e fortuna sotto-xG non anticipano niente
(vedi *Cosa è già stato provato*): quello che il motore sa già dal passato, le probabilità lo
contengono. L'informazione nuova, se c'è, è chi scende in campo. PitchAPI dà la formazione
della partita prima del fischio: probabile fino a 48 ore prima (`confirmed: false`, con un
`lineup_type` come `lastStarting11`), confermata a ridosso del calcio d'inizio
(`confirmed: true`); per le 26 leghe ricostruite da Opta solo quella confermata, circa 30
minuti prima. Nel backtest la formazione di una partita giocata è quella reale, cioè quella
confermata: si prendono **solo i titolari**, perché panchina, cambi e marcatori sono dopo il
fischio.

**Cosa calcola il `b43`.** I `/lineups` dello storico il motore li scaricava già e ne usava
solo il modulo, quindi l'undici abituale costa zero chiamate. Per ogni squadra
`storicoFormazioni` tiene, dalle partite di `overall`: la quota di presenze da titolare di
ogni giocatore nelle ultime 10 formazioni (`LINEUP_WINDOW`), la rosa (in campo o in panchina
nelle ultime 5, `LINEUP_SQUAD_WINDOW`), i gol di ogni giocatore dagli `/events` dello storico,
il capitano più frequente, l'allenatore dell'ultima formazione e da quante partite c'è.
`partitaBersaglio` trova l'id della partita nell'archivio di lega, o con `/date/{giorno}?status=all`
se non c'è (le partite da giocare); `formazioneBersaglio` ne legge i titolari (dalla
`RAW_CACHE` se c'è, altrimenti una chiamata, tenuta in cache solo se confermata).
`indiciFormazione`:

| indice | definizione |
|---|---|
| titolari abituali assenti | giocatori con quota ≥ 0.5 (`LINEUP_REGULAR`) ancora in rosa che oggi non partono |
| peso degli assenti | la quota degli assenti divisa per quella di tutti gli abituali: 0 è l'undici tipo, 0.4 mezza squadra cambiata |
| gol degli assenti | quota dei gol di squadra dello storico segnati dagli abituali assenti |
| cambi dall'ultima | titolari dell'ultima partita che oggi non partono |
| capitano assente, allenatore nuovo, partite con l'allenatore | dall'ultima formazione dello storico contro quella di oggi |

Sotto le 5 formazioni in archivio (`LINEUP_MIN_HIST`) gli indici restano vuoti. Un titolare
fuori da cinque partite non è più in rosa, quindi non conta come assente: la squadra si è già
adattata, e l'Elo e gli xG lo sanno. Conta chi manca **oggi**.

**Non entrano nelle probabilità.** Il `b43` li mostra (card «Formazioni e stanchezza»,
che dice se la formazione è probabile o confermata) e li esporta (sezione CSV `FORMAZIONI`),
niente altro. Col motore `b42` caricato il banco vede diverse solo quella card, le venti righe
del CSV e il certificato.

**Il leakage.** La partita bersaglio entra solo coi titolari, l'allenatore e `confirmed`.
Sul banco, drogando panchina e marcatori della partita bersaglio (quattro gol di un giocatore
di panchina) gli indici e l'1X2 restano identici al bit; drogando tre titolari e l'allenatore
gli indici cambiano (assenti 1 → 4, peso 0.08 → 0.35, allenatore nuovo) e l'1X2 resta
identico, come deve finché non li usa.

**La regola, scritta prima del batch.** Si rifanno le cinque leghe col `b43`, stesse stagioni,
una per file, in copia conforme. **Un solo indice primario**: la differenza fra il peso degli
assenti di casa e di trasferta, aggiunta al log-odds bersaglio, `lgTarget + b·(pesoH − pesoA)`,
con `b` stimato fuori lega (su quattro leghe, misurato sulla quinta). **Passa** se la logloss
1 contro 2 migliora in almeno quattro leghe su cinque, sull'insieme con `z ≤ −2`, e le prese
del pick non scendono. Gol degli assenti, cambi dall'ultima e allenatore nuovo sono secondari:
tre prove in più, quindi contano solo con `z ≤ −3`. Sui mercati gol (Over e GG col gol degli
assenti) è solo descrittivo. Se passa, entra nel motore con il `b` stimato, e **solo con la
formazione confermata**: con quella probabile l'indice resta a schermo e non sposta niente.
Se non passa, la card resta come informazione e questa sezione dice perché.

**Esito (batch `b47`, cinque leghe, 5230 partite, 3891 senza pari): non passa.** Il
coefficiente ha lo stesso segno in tutti e cinque i fold (−0.25 … −0.46: la squadra che manca
di più rende di meno), ma l'effetto è quasi nullo:

| indice | Serie A | Premier | LaLiga | Bundesliga | Ligue 1 | insieme | prese |
|---|---|---|---|---|---|---|---|
| **peso degli assenti** (primario) | −0.00001 | −0.00156 (`z = −2.25`) | −0.00012 | −0.00009 | −0.00014 | −0.00041, `z = −0.72`, 5 su 5 | 52.79 → 52.52% |
| gol degli assenti | −0.00065 | −0.00236 | +0.00023 | −0.00199 | −0.00095 | −0.00112, `z = −1.41` | 52.79 → 52.87% |
| cambi dall'ultima | +0.00026 | −0.00070 | −0.00047 | −0.00026 | −0.00003 | −0.00025, `z = −0.64` | 52.79 → 52.56% |
| allenatore nuovo | +0.00013 | +0.00088 | −0.00004 | +0.00002 | −0.00007 | +0.00020, `z = +1.29` | invariate |

La soglia d'insieme (`z ≤ −2`) è lontana e le prese scendono; i secondari non arrivano a −3. La
card resta come informazione. **Descrittivo, trovato dopo:** nelle prime cinque giornate gli
«abituali assenti» sono anche i ceduti d'estate (4.5 a partita contro 3.5 dopo, indice più
disperso: sd 0.256 contro 0.179). Dalla sesta giornata, in campione, il coefficiente è −0.81 e
la logloss −0.0021 (`z = −1.88`): meglio, ma stimato sugli stessi dati.

**Il secondo giro, registrato prima di aprire le tre leghe nuove.** Lo stesso indice primario,
usato solo quando tutte e due le squadre hanno già giocato cinque partite di lega della
stagione (prima, correzione zero), col coefficiente fissato adesso a **−0.81** (le cinque leghe,
dalla sesta giornata). Si prova su Eredivisie, Liga Portugal e Championship 2023/24–2025/26,
batch `b47`, di cui finora sono stati guardati solo copia conforme ed Elo: passa se la logloss
1 contro 2 migliora in almeno due leghe su tre, `z ≤ −2` sull'insieme, prese del pick non in
calo. Niente secondari. Se passa, entra nel motore solo con la formazione confermata.

**Esito del secondo giro: non passa.** Eredivisie +0.00032, Liga Portugal −0.00016,
Championship +0.00031; insieme +0.00019 (`z = +0.16`), una lega su tre. L'indice delle
formazioni è chiuso: con la formazione confermata in mano il motore non prevede meglio.

### La formazione probabile

**Cosa dà l'API prima della confermata.** Fino a 48 ore prima una formazione con
`confirmed: false` e un `lineup_type`; la documentazione cita come esempio `lastStarting11`,
cioè l'undici dell'ultima partita ricopiato. Con quella «chi manca» mostra solo chi mancava
già l'ultima volta: un infortunio o una squalifica arrivati dopo non ci sono. Gli indici si
calcolano lo stesso, ma dal `b46` la card lo dice: «probabile: è l'ultimo undici», con una
nota che invita a rilanciare l'analisi a ridosso del calcio d'inizio. Con una probabile di
altro tipo la card dice che gli indici sono indicativi, perché il backtest li misura solo
sulle confermate (per le partite giocate l'API restituisce solo la formazione reale).

**Il confronto con la probabile.** `ricordaProbabile` salva nel browser
(`localStorage`, chiave `scanner_prob_<id partita>`, dieci giorni) i titolari di ogni lato
ancora non confermato. Quando lo stesso lato arriva confermato, `confrontoProbabile` dice chi
era nella probabile e non parte (**fuori**) e chi parte senza esserci (**dentro**), con quante
ore prima era stata vista: sono i cambi dell'ultimo momento, cioè le sorprese che il resto
del motore non può vedere. La riga «Rispetto alla probabile» scrive «salvata» finché la
formazione è probabile, e `--` se la probabile non era mai stata vista.

**Solo a schermo, mai nel CSV né in `__LINEUP_DEBUG`**: dipende da quando e su quale
dispositivo si è aperto lo Scanner, quindi non è riproducibile, e un backtest non può
misurarlo. Verificato su un banco modificato in cui la prima risposta di `/lineups` è una
probabile `lastStarting11` e la seconda la confermata: al primo giro «probabile: è l'ultimo
undici» e «salvata», al secondo «fuori … · dentro …», a 390px nessuno scorrimento laterale. Il
banco di parità normale non lo esercita (le sue formazioni sono tutte confermate).

### La stanchezza

**Perché le coppe.** Il riposo misurato nel `b42` contava solo le partite di lega, e non diceva
niente (+0.04 punti di prese): una squadra che ha giocato in Champions il mercoledì risultava
riposata da una settimana. Dal `b44` `archivioCoppe` carica Champions, Europa e Conference
League della stagione della partita (`UEFA_IDS`, tre chiamate con `status=all`, in memoria per
la sessione; se un archivio non arriva non si mette in cache e la riga del CSV lo dice). Gli id
delle squadre sono gli stessi fra le leghe, quindi le partite europee si agganciano da sole.

**Cosa calcola** `indiciStanchezza`, per squadra, da date e stato delle partite (mai dai
punteggi):

| indice | definizione |
|---|---|
| giorni di riposo | dall'ultima partita ufficiale conclusa, lega o coppa europea, filtrata con `_isPast` |
| giorni di riposo dalla lega | lo stesso contando solo la lega: è la misura vecchia, per confronto |
| partite in 14 giorni | partite ufficiali concluse nei 14 giorni prima |
| giorni dalla coppa europea | dall'ultima partita europea conclusa della stagione |
| giorni alla coppa europea | alla prossima partita europea in calendario |

**Il calendario è un'informazione legittima, il risultato no.** La prossima partita europea
si usa solo per la data, che è pubblica prima. Resta un caso limite: una partita a eliminazione
diretta esiste solo se la squadra si è qualificata, e il sorteggio può essere arrivato dopo la
data da prevedere. Dentro 5 giorni non può succedere (fra l'ultima partita di un turno e la
prima del successivo passano settimane), quindi nella regola l'indice «dopo» si usa solo come
flag entro 4 giorni.

**Cosa non vede.** Le coppe nazionali, che non sono in `leghe.json` (vedi *Da fare*), e le
nazionali: dopo una sosta il riposo di lega è lungo, ma i titolari hanno giocato.

**La regola, scritta prima del batch.** Indice primario, uno solo: il vantaggio di riposo,
`min(riposoH, 7) − min(riposoA, 7)` (oltre una settimana non c'è stanchezza da recuperare: il
tetto è una definizione, fissata adesso), aggiunto al log-odds bersaglio con un coefficiente
stimato fuori lega. **Si misura sopra le formazioni**: se l'indice delle formazioni passa, la
stanchezza deve migliorare il modello che lo contiene già, perché una squadra stanca ruota, e
la rotazione la formazione confermata la vede; contarla due volte sarebbe l'errore del
vantaggio campo contato due volte. Passa con le stesse soglie delle formazioni: logloss 1
contro 2 migliore in almeno quattro leghe su cinque, `z ≤ −2` sull'insieme, prese del pick non
in calo. Secondari, con `z ≤ −3`: partite in 14 giorni (differenza), coppa europea entro 4
giorni prima, coppa europea entro 4 giorni dopo (il turnover preventivo). Sui gol solo
descrittivo.

**Esito (batch `b47`, cinque leghe): non passa, nemmeno per poco.** Le formazioni non sono
entrate, quindi si è misurata sopra `lgTarget`. Il vantaggio di riposo peggiora la logloss
fuori lega in tutte e cinque le leghe (+0.00007 / +0.00009 / +0.00010 / +0.00060 / +0.00111;
insieme +0.00036, `z = +2.68`), col coefficiente che cambia segno da un fold all'altro (−0.016
… +0.021). Secondari: partite in 14 giorni +0.00038 (`z = +1.43`), coppa entro 4 giorni prima
+0.00035 (`z = +1.86`), dopo +0.00016 (`z = +0.75`). Il riposo di sola lega, rifatto per
confronto, +0.00088 (`z = +3.26`). Contare le coppe europee non ha acceso nessun segnale: il
calendario, nelle cinque leghe, le probabilità lo sanno già o non conta.

## Le statistiche dei giocatori

**Cosa mostra.** La card «Giocatori — le ultime 30 partite», col bottone: per ogni giocatore
della rosa di oggi e per un mercato scelto dal menu (falli subiti ≥ 1/2/3, falli commessi
≥ 1/2, tiri ≥ 1/2/3, tiri in porta ≥ 1/2, ammonito, segna, assist, gol o assist, contrasti
vinti ≥ 2) le partite da titolare sulle ultime 30 di campionato della squadra, la media, e
quante volte ha raggiunto la soglia nelle sue ultime 5 da titolare e in tutte. Le partite
sono le stesse 30 dello storico del motore (`matchList` di `aggregaTeam`), quindi solo
campionato, e passano da `_isPast` come tutto il resto.

**Da dove.** `/matches/{id}/players` per ogni partita dello storico (`fetchPlayersRaw`, in
memoria per la sessione, circa 60 chiamate la prima volta); titolari dai `/lineups` e gialli
dagli `/events` già in `RAW_CACHE`. La risposta è un elenco di giocatori con gruppi di
statistiche (`top_stats`, `attack`, `defense`, `duels`); `_statiGiocatore` li appiattisce e
`PLAYER_STATS` cerca ogni dato per chiave e, se manca, per etichetta. Le chiavi dei tiri
(`total_shots`, `shot_accuracy`, dove `value` sono i tiri in porta) vengono dalla
documentazione; quelle di falli e contrasti (`fouls`, `was_fouled`, `tackles_won` e varianti)
**no**: sono le più probabili, e la card avvisa se un dato c'è su meno di metà delle righe.
Valori mancanti come nel resto del motore: un conteggio assente con il suo gruppo presente è
0, con il gruppo assente (il portiere non ha `duels`) la riga esce dalla media.

**Su quali partite si conta.** Solo quelle da titolare (se la formazione della partita manca,
quelle con almeno 45 minuti): una scommessa sul giocatore si fa su un titolare, e un ingresso
al 80' abbassa la frequenza senza dire niente. Solo la rosa di oggi: chi è nella formazione
della partita (●) o ha giocato in una delle ultime 5. L'ordine usa `(riusciti + 1) / (partite +
2)`, perché un 2 su 3 non passi davanti a un 15 su 24; la percentuale a schermo resta quella
grezza.

**Cosa non è.** Una frequenza, non una probabilità: non sa niente dell'avversario, dei minuti
che giocherà, della posizione. Le ultime 5 sono cinque partite, e nel motore le medie brevi
non hanno mai previsto meglio della lunga (47 metriche su 47, vedi *Scanner in uso*): la card
lo dice, e la colonna da guardare è quella di tutte. Non è misurata contro il reale (vedi *Da
fare*).

**Fuori dal giro del motore, apposta.** Il bottone chiama `caricaGiocatori()` dopo l'analisi,
che lascia in `window.__PLAYER_CTX` le partite e le formazioni: il Comparatore non la esegue,
quindi i batch non pagano le chiamate e il confronto Scanner/Comparatore non cambia (una sola
scrittura nuova, il messaggio iniziale). Il banco la verifica a parte, premendo il bottone.

## Registro delle costanti

| costante | valore | tipo | da dove viene |
|---|---|---|---|
| `ENS_W` dc / mk / ol | 0.70 / 0.30 / 0.00 | stimata `b20` | griglia leave-one-league-out su 1743 partite, OL a 0 in 4 fold su 5. Vale −0.0013 di logloss, `z = −2.03`: pulizia più che guadagno |
| `ENS_SCOPE_W` | 1 | stimata `b21` | 1133 partite, logloss 1.0113 → 1.0071, monotono in 3 leghe su 3, `z = −3.96`, fuori campione 1.0 in 3 fold su 3. Solo 1X2 |
| `ELO_1X2_W` | 0.75 | stimata `b14`, riconfermata `b35` e `b41` a `S` fisso | 5 leghe, 1743 partite: w 0 → 0.50 a +5.02σ, ottimo a 0.75. `b35` (Serie A 1882, ramo giusto): ottimo interno piatto fra 0.50 e 0.75, estremi peggiori a 2σ. `b41` (1134 in copia conforme): idem. Spazzata **insieme a `ELO_SCALE`** su Serie A e Premier la coppia 0.40 / 2.00 vale −0.0063 (`z = −3.53`), 6 stagioni su 6, ma nel test registrato Ligue 1 non migliora (+0.0004): non passa. Vedi *Peso e scala dell'Elo insieme* |
| `ELO_SCALE` | 1.25 | stimata `b30`, confermata `b35` e `b41` a `w` fisso; la coppia con `w` non ha passato il test (`b41`) | pendenza di calibrazione dell'Elo 1.235 (`z = 3.13`); fuori campione 1.20–1.35 in 7 fold su 7; `b35`: 1.25 batte 1.00 a `z = 3.92`; `b41`: a `z = 3.55`, Elo a 1.119 ±0.089. Applicata alla sola differenza di rating, non all'HFA |
| `ELO_INGRESSO` / `ELO_RITORNO` / `ELO_PENDENZA` | `'uscite'` / 180 / `'netta'` | procedura senza parametri stimati (`b48`); 180 è una definizione | registrata prima del batch `b47`; cinque leghe −0.00375, `z = −2.64`, residuo delle neopromosse da −7.3 a −0.5 punti; tre leghe nuove −0.00076, nessuna oltre `z = +1`. 180 sta fra la pausa più lunga dentro una lega (106 giorni) e il ritorno più breve (454). Vedi *Le neopromosse* |
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
| `CONF_1X2_TABLE` | `[0,0]` + 8 fasce | stimata `b38`, riconfermata `b41` e `b49` | resa del pick per fascia, 1882 partite di Serie A post-`b30`; `b41`, 1134 in copia conforme: 8 fasce su 8 dentro 2se; Premier χ² 11.2 su 8, LaLiga 7.7, Bundesliga 7.1, Ligue 1 5.2. Il punto `[0,0]` (`b41`) serve gli esiti non scelti: hit/p 0.939 / 1.000 / 0.943 / 0.993 / 0.963 in Serie A / Premier / LaLiga / Bundesliga / Ligue 1, contro 0.960 della tabella. `b49` (motore `b48`, 5230 partite): χ² 16.2 su 8, ma fuori lega né le probabilità nude (−0.00043 di Brier, `z = −1.01`) né una tabella rifatta (+0.00007) la battono; esiti non scelti hit/p 0.996. Vedi *Le tabelle col `b48`*. `b52`, tre leghe nuove: χ² 32.2 su 8, **non regge** fuori dai cinque campionati, e la probabilità nuda la batte (Brier +0.00137 per la tabella, `z = +2.68`). **Dal `b53` non è in uso**: resta come manopola (`CONF_1X2_MODE = 'tabella'`) |
| `CONF_1X2_MODE` | `'nuda'` | procedura, decisa da un test registrato (`b53`) | la confidence dell'1X2 è la probabilità del motore. Registrato prima di aprire 2. Bundesliga, First Division A, Premiership e Super League: la nuda batte la tabella in quattro leghe su quattro, −0.00220 di Brier, `z = −4.09`. `'tabella'` torna a `CONF_1X2_TABLE`, `'retta'` alla retta del `b37` |
| `PICK_RESA` | tutte 52.7 · casa 43.0 · soglie ≥70 / 65 / 60 / 55 / 50: 77.1 / 73.2 / 69.3 / 66.0 / 61.7% su 9 / 16 / 26 / 38 / 52% del calendario | misurata `b49` | cinque leghe col motore `b48`, 5230 partite (tabella in *Stato attuale*). Dal `b51` una sola copia: la card delle soglie e il mega-prompt la leggono da qui. Si rifà con le tabelle, a ogni motore che sposta l'1X2. Dal `b52` porta `leghe` (le cinque, per id) e `fuori` (Championship 46.3 e 64.8% su 17%, Eredivisie 53.7 e 68.7% su 47%, Liga Portugal 55.0 e 72.4% su 43%: pick su tutte e a ≥55, 3495 partite col `b48`), perché sulle tre leghe nuove le soglie ≥55 / 60 / 65 / 70 escono dai 2se (vedi *Le tre leghe nuove col `b48`: la regola*). Dal `b53` `fuori` ha anche 2. Bundesliga (45.4 e 62.8% su 16%), First Division A (50.2 e 65.5% su 35%), Premiership scozzese (53.3 e 68.9% su 41%) e Super League svizzera (47.1 e 66.1% su 26%), 3202 partite col motore `b52` |
| retta dei mercati binari | −5.06 + 1.091·p | stimata, riconfermata `b38` e `b41` | 22.584 proposte, errore massimo 2.4 punti; `b41` 7938 proposte, 2.5 |
| `EDGE_BANDS` | ≥20 / ≥10 / ≥5, guadagno per famiglia (`b50`) | stimata `b38`, riconfermata `b41` e `b49`, per famiglia dal `b50` | 28.230 proposte: +24.6 / +14.8 / +6.3 punti, monotono, segno concorde in 5 stagioni su 5. `b41` (copia conforme): +25.6 / +15.6 / +4.8 sulle 13.148 proposte con base del `b40`, +25.0 / +14.9 / +5.7 sulle 14.742 del `b41`, monotono in 3 stagioni su 3; Premier (≥20 / 10–20 / 5–10) +27.4 / +10.7 / +6.0, LaLiga +25.0 / +13.7 / +7.3, Bundesliga +28.7 / +14.0 / +5.5, Ligue 1 +26.4 / +13.4 / +5.0. `b49` (motore `b48`, cinque leghe): +25.8 / +12.2 / +6.1, monotono in 5 leghe su 5; per famiglia 1X2 +27.5 / +15.5 / +8.0, gol +1.0 / +7.2 / +3.5, numeri +7.2 / +10.2 / +8.2. Dal `b50` l'etichetta mostra questi, per famiglia, con ±2se: 1X2 ±1.6 / ±1.6 / ±1.9 (2891 / 3573 / 2680 proposte), gol ±10.4 / ±2.3 / ±1.7 (92 / 1881 / 3457), numeri ±8.0 / ±2.9 / ±2.4 (133 / 1058 / 1628). Ordinare per guadagno atteso invece che per scarto: no (vedi *Il tabellone per famiglia di mercato: la regola*) |
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
| `LINEUP_WINDOW` / `LINEUP_SQUAD_WINDOW` / `LINEUP_REGULAR` / `LINEUP_MIN_HIST` | 10 / 5 / 0.5 / 5 | definizione di una misura (`b43`) | non entrano nelle probabilità: dicono chi è un titolare abituale e chi è ancora in rosa. Se l'indice passa la regola, vanno rimisurati prima di diventare costanti del motore. Vedi *Formazioni e assenze* |

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
  lega, a somma zero (controllo M: media 1500 senza pause e senza squadre entrate).
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
- **Un numero misurato sull'insieme non vale per le sue parti.** «FORTE, rende +24.6» era giusto
  in media e sbagliato per quasi ogni riga: +27.5 sull'1X2, +1.0 sui mercati gol. Un'etichetta
  che promette una resa va misurata sul gruppo a cui la si mostra.
- **Quello che non passa da `safeTxt`/`safeHtml` il banco non lo vede.** Il mega-prompt ha
  detto «2963 partite» dal `b27` al `b50`, e «nei mercati dei mercati gol» nel `b50`, con il banco
  verde. Dal `b51` il banco ne controlla la forma; il contenuto si rilegge a mano.
- **Pagina a 0 px non vuol dire tabella dentro lo schermo.** Il tabellone è uscito di lato di 53
  px dentro il suo riquadro per chissà quante build, con lo scorrimento della pagina a 0. Il
  banco misura anche le tabelle compatte, ma solo quelle dello Scanner.
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
| Ordinare il tabellone per guadagno atteso per famiglia o per mercato (`α + β·scarto`) | **no** (`b50`) | regola registrata; fuori lega sulle cinque leghe `b48` la prima proposta rende +0.12 ±0.29 in più (`z = +0.42`), tre leghe su cinque, LaLiga −0.96. Al posto dei gol sale un 1X2 che rende uguale. Resta l'etichetta per famiglia. Vedi *Il tabellone per famiglia di mercato: la regola* |
| Anticipare le sorprese con forma (punti nelle ultime 5), momento dell'Elo (ultime 5), giorni di riposo **di sola lega**, fortuna (gol − NPxG, ultime 10), NPxG recenti | **no** (`b42`); il riposo si rifà con le coppe europee (`b44`, vedi *La stanchezza*) | 5230 partite, fuori lega (stimato su quattro leghe, misurato sulla quinta), sopra `lgTarget`: logloss 1 contro 2 −0.0000 / −0.0001 / +0.0001 / −0.0012 (`z = −1.40`) / −0.0020 (`z = −1.85`), prese +0.13 / +0.10 / +0.04 / +0.17 / +0.06 punti; tutte insieme +0.31. Il riposo conta solo le partite di lega: le coppe non sono nell'archivio |
| L'indice delle formazioni (peso dei titolari abituali assenti, `b43`) | **no** (`b47`) | 5230 partite, fuori lega: −0.00041 di logloss, `z = −0.72`, stesso segno in 5 leghe su 5 ma prese 52.79 → 52.52%. Dalla sesta giornata −0.0021 in campione (`z = −1.88`): secondo giro registrato sulle tre leghe nuove. Vedi *Formazioni e assenze* |
| La stanchezza con le coppe europee (`b44`) | **no** (`b47`) | vantaggio di riposo peggiore fuori lega in 5 leghe su 5 (+0.00036, `z = +2.68`); partite in 14 giorni e coppa entro 4 giorni prima o dopo, niente. Vedi *La stanchezza* |
| Peso e scala dell'Elo, secondo giro (0.40 / 2.00 sopra l'Elo corretto) | **no** (`b48`) | tre leghe mai viste: −0.00135, `z = −0.89`, Championship peggiore. Vedi *Peso e scala dell'Elo insieme* |
| La coda alta della selezione contro le neopromosse (col `b48` il 10% più alto perde 2.9 punti sulle cinque leghe) | **non decisa, chiusa** (`b52`) | regola registrata sulle tre leghe nuove: −0.3 ±2.0 (confermata sotto −2se, smentita da 0 in su); otto leghe insieme −1.8 ±1.8, solo descrittivo. L'ingresso del `b48` resta. Vedi *Le tre leghe nuove col `b48`: la regola* |
| Indovinare più risultati combinando tutto quello che il motore calcola (stacking, `b53`) | **no** (`b53`) | 12 leghe, 11.927 partite, addestrato su undici e misurato sulla dodicesima. Logistica sulle sole probabilità: +0.08 ±0.18 punti di prese; coi sei modelli, `lgModel`, `lgElo`, ΔElo e HFA (19 feature): +0.22 ±0.40, ma logloss −0.0029 (`z = −2.89`, una calibrazione, non prese); con 67 feature (lambda, tiri, pendenze, neopromosse, formazioni, riposo, classifica della stagione): −0.13 ±0.51, e comincia a giocare `X` (388 volte) perdendo; gradient boosting +0.30 ±0.55. La selezione nemmeno: 10 / 20 / 30 / 50% più sicuro +0.5 / +0.7 / −0.1 / +0.6 (±1.7 / 1.2 / 0.9 / 0.7). Il modello è calibrato (probabilità media del pick 51.7%, prese 51.0%): l'informazione del motore è sfruttata |
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
| **L'ingresso delle neopromosse nell'Elo** (`b48`) | residuo delle neopromosse da −7.3 ±2.6 a −0.5 punti; logloss 1 contro 2 −0.0037 (`z = −2.64`) su cinque leghe, confermato non peggiore su tre leghe mai viste |
| **La confidence dell'1X2 uguale alla probabilità** (`b53`) | registrata prima, su quattro leghe mai aperte: Brier −0.00220, `z = −4.09`, quattro leghe su quattro; sulle tre leghe del `b52` −0.00137 (`z = −2.68`) |
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
moltiplicatore per scarto di gol, e **di lega** (filtra `_chosenLeagueId`). Usa tutte e tre le
stagioni caricate. Dal `b48` una squadra che entra nella lega dopo la prima stagione in archivio
parte dal livello delle squadre uscite (vedi *Le neopromosse*).

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

### Le neopromosse

**La pausa non è il difetto.** La curva distingue già le pause: 60 giorni 3.7%, la pausa
estiva (83) 9.0%, 180 giorni 28%, una stagione in B (circa 455) 61%. Nei CSV delle cinque leghe
nessuna pausa dentro la lega supera i 106 giorni e nessun ritorno ne conta meno di 454: il
regime «sei mesi» non esiste. Il difetto è **dove** porta la regressione: verso 1500, cioè
verso la squadra media della lega. Una squadra mai vista nell'archivio entra a 1500; una che
torna dopo una stagione in B viene tirata al 61% verso 1500 alla sua prima partita (il Sassuolo
del 2025/26 da 1360 a circa 1445). Alla prima giornata la previsione usa ancora il rating
vecchio, perché la regressione scatta dentro il ciclo alla partita stessa: il salto arriva
dalla seconda. E una neopromossa è quasi sempre più debole della media.

**La misura.** Sui CSV `b40`/`b41`, 2024/25 e 2025/26 (neopromossa = assente dal file della
stagione prima; 28 squadre-stagione), vittoria 1 contro 2 reale meno prevista, in punti:

| | prime 10 partite | 11–19 | dalla 20ª | tutte |
|---|---|---|---|---|
| prodotto finito | −8.3 | −5.4 | −4.8 | **−5.9** ±3.1 |
| solo modello (`lgModel`) | −10.2 | −6.7 | −6.2 | −7.4 ±3.2 |
| solo Elo (`lgElo`) | −7.9 | −5.1 | −4.5 | −5.6 ±3.1 |

Non è la timidezza generale: per fascia di attesa (punti a partita) le altre squadre stanno
fra −0.01 e +0.01, le neopromosse fra −0.02 e −0.05. In regressione (residuo su attesa e
neopromossa) −0.046 ±0.028 punti a partita; per lega (Serie A, Premier, LaLiga, Bundesliga,
Ligue 1) −0.058 / −0.081 / −0.040 / −0.060 / +0.004. Una partita su quattro ha una neopromossa
in campo.

**Quanto vale, a occhio.** Una correzione grezza sul prodotto (un log-odds fisso contro la
neopromossa, stimato fuori lega: da 0.28 a 0.44) fa −0.0023 di logloss 1 contro 2 sulle cinque
(`z = −1.53`), quattro leghe su cinque (Ligue 1 +0.0052), e le prese non si muovono (±0.4
punti): il pick contro una neopromossa è già il pick. È una correzione delle probabilità, e
quindi della selezione e del tabellone, non delle prese.

**Perché serve l'archivio.** L'Elo rifatto dai soli CSV non coincide col motore: ai file manca
da una a tre partite per stagione, e dal 16 al 36% dei rating esce diverso (mediana 1 punto,
90° percentile 5–6). Una correzione che sta dentro il ciclo dell'Elo non si misura così. Dal
`b47` il CSV porta in fondo l'archivio del database (sezione `ARCHIVIO DI LEGA`): sul banco
l'Elo rifatto da lì coincide su 89 partite su 89, col `buildGlobalElo` del motore e con
`strumenti/elo-archivio.py` (anche la pendenza, entro l'arrotondamento); sul primo file vero
(Serie A 2023/24, archivio di 1141 partite) coincide su 379 partite su 379. Lo strumento è la
replica in Python con le manopole libere: `python3 strumenti/elo-archivio.py <csv>` fa la prova
di coincidenza, da rifare su ogni file prima di ricostruire qualcosa (un CSV senza archivio
risponde «NON COINCIDE»).

**La pendenza porta dentro il salto.** `calcTrend` (media delle ultime 5 posizioni della serie
meno quella delle 10 prima) legge la serie dell'Elo, che contiene anche i salti della
regressione: il ritorno di una neopromossa diventa «forma» e alza il suo lambda fino all'8%
(`pen = trend/1200`) per cinque partite, e la pausa estiva dà una piccola pendenza negativa
alle forti e positiva alle deboli. Sull'1X2 pesa un quarto (circa mezzo punto), sui mercati
gol per intero. Dal `b47` il CSV esporta trend, `penH`/`penA` e la lunghezza della serie.

**La regola, scritta prima del batch `b47`.**

1. Si provano tre correzioni, e nient'altro:
   - **A.** Un livello d'ingresso `1500 − δ`: è il rating di partenza di una squadra mai vista
     (anche quando non ha ancora giocato e il motore usa il default) e il bersaglio della
     regressione per chi torna dopo più di 180 giorni. δ da 0 a 200 a passi di 25, scelto fuori
     lega (stimato su quattro leghe, misurato sulla quinta).
   - **B.** Lo stesso, col livello preso dalla lega: la media dei rating finali delle squadre
     che hanno giocato la stagione prima e non giocano questa. Zero parametri, e nelle leghe
     dove si entra anche dall'alto (Championship) si aggiusta da solo.
   - **C.** La pendenza calcolata sulla serie senza i salti della regressione.

   La curva dello stacco (soglia, τ, asintoto) si rispazza insieme, ma cambia solo se passa la
   stessa regola.
2. Metro: la logloss 1 contro 2 del prodotto finito ricostruito (`lgModel` del CSV, corretto
   per la pendenza dove serve C; peso e scala dell'Elo quelli in uso), e il residuo delle
   neopromosse.
3. Sulle cinque leghe note, fuori lega: logloss migliore in almeno quattro su cinque, `z ≤ −2`
   sull'insieme, prese del pick non in calo, residuo delle neopromosse dentro ±2se da zero.
   L'ipotesi viene da queste leghe: l'esito vale solo col punto 4.
4. Su Eredivisie, Liga Portugal e Championship, col δ fissato prima di aprirle: nessuna lega con
   `z > +1`, e sull'insieme una differenza non positiva.
5. Se A e B passano tutte e due, si spedisce B. Solo dopo si rifanno i pesi (vedi *Peso e scala
   dell'Elo insieme*, «Il secondo giro»).

**Esito sulle cinque leghe (batch `b47`, 5230 partite, Elo rifatto dall'archivio).** Prova di
coincidenza col motore in uso: differenza Elo e HFA identiche su 8725 partite su 8725,
`lgTarget` entro 0.00012, pendenza entro 0.00005. Il residuo delle neopromosse col motore in
uso è −7.3 ±2.6 punti (977 partite senza pari con una sola neopromossa in campo).

| correzione | Serie A | Premier | LaLiga | Bundesliga | Ligue 1 | insieme | prese (appaiate) | residuo neopromosse |
|---|---|---|---|---|---|---|---|---|
| A, δ fuori lega (150–200) | −0.00359 | −0.00732 | −0.00264 | −0.00557 | +0.00205 | −0.00354, `z = −2.48`, 4 su 5 | −0.10 (±0.48) | −0.4 ±2.6 |
| **B**, livello delle uscite | −0.00363 | −0.00677 | −0.00258 | −0.00545 | +0.00022 | −0.00372, `z = −2.61`, 4 su 5 | −0.08 (±0.45) | −0.4 ±2.6 |
| C, pendenza senza salti | −0.00002 | −0.00006 | −0.00013 | −0.00009 | −0.00000 | −0.00006, `z = −2.48`, 5 su 5 | −0.02 (±0.04) | −7.3 |
| B + C | −0.00368 | −0.00674 | −0.00260 | −0.00552 | +0.00018 | −0.00375, `z = −2.64`, 4 su 5 | −0.08 (±0.45) | −0.5 ±2.6 |

Il δ di A sulle cinque sarebbe 175. Logloss, leghe e residuo passano; **le prese no, alla
lettera**: la regola diceva «non in calo» senza margine, e con B il pick cambia esito in 140
partite su 5230 con saldo −4. È rumore (±0.45 punti), ma cambiare la regola dopo averlo visto
non si fa: **sulle cinque leghe non passa.**

**Il secondo passo, registrato prima di aprire l'Elo delle tre leghe nuove.** Candidato unico
**B + C**. Si prova su Eredivisie, Liga Portugal e Championship 2023/24–2025/26 contro l'Elo in
uso, peso e scala 0.75 / 1.25: passa se nessuna lega ha `z > +1`, la logloss 1 contro 2
d'insieme non peggiora, e le prese non calano **oltre il rumore**, cioè la differenza appaiata
delle prese è almeno −2 errori standard. Il residuo delle neopromosse lì è solo descrittivo: in
Championship si entra anche dalla Premier. Se passa, B + C entra nel motore.

**Esito sulle tre leghe nuove: passa.**

| lega | partite senza pari | differenza | `z` |
|---|---|---|---|
| Eredivisie | 690 | +0.00037 | +0.10 |
| Liga Portugal | 677 | −0.00271 | −0.85 |
| Championship | 1226 | −0.00031 | −0.62 |
| insieme | 2593 | −0.00076 | −0.58 |

Nessuna lega oltre `z = +1`, l'insieme non peggiora, le prese −0.03 punti contro un rumore di
−0.53. **Nel motore dal `b48`**:

- `buildGlobalElo` conosce la stagione di ogni partita (`_season`, messo al caricamento dallo
  Scanner come già dal Comparatore; un database in memoria salvato senza si riscarica). La
  prima stagione dell'archivio parte a 1500 come prima; una squadra che compare dopo parte da
  `livelloIngresso(stagione)`, la media dei rating finali delle squadre della stagione prima che
  non sono in questa (dal calendario, noto in anticipo); chi torna dopo più di `ELO_RITORNO` =
  180 giorni regredisce, con la curva di sempre, verso quel livello invece che verso 1500. Una
  squadra mai vista che non ha ancora giocato vale il livello della stagione più recente
  (`ELO._ingresso`), non 1500.
- La pendenza (`calcTrend`) legge `seriesTrend`, la serie dei rating tolte le regressioni;
  `series` resta quella di sempre per quello che la mostra.
- Manopole: `ELO_INGRESSO` (`'uscite'`; `'1500'` torna al `b47`), `ELO_RITORNO` (180),
  `ELO_PENDENZA` (`'netta'`; `'grezza'` torna al `b47`). La card dell'Elo ha la riga «Ingresso
  neopromosse»; il CSV le righe `Elo: ingresso delle neopromosse (livello della stagione)` e
  `Elo: regola d ingresso / pendenza`. `strumenti/elo-archivio.py` segue la regola nuova e
  riconosce da sola i CSV del `b47`.
- Verificato sul batch vero (`b48`, Championship, Premier e Serie A 2025/26, 1309 partite in
  copia conforme): l'Elo rifatto dall'archivio coincide col motore su ogni partita, e la
  differenza di rating prevista dai CSV `b47` con la replica è quella del motore al punto. Il
  `lgModel` previsto con la derivata della pendenza sbaglia al massimo di 0.030, il `lgTarget`
  di 0.0076: le misure sopra sono quelle del motore vero. Il `lgTarget` cambia sul 80–98% delle
  partite (tutti i rating si spostano quando una squadra entra più in basso).

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

## Il batch automatico

`strumenti/batch-auto.js` fa i batch senza telefono: apre `comparatore.html` in Chromium senza
schermo, da un server locale col `scanner.html` del repository accanto, restringe l'elenco delle
leghe a quelle chieste e lancia lo sweep del Comparatore. È il Comparatore vero, quindi ogni
riga porta il suo certificato di copia conforme come a mano. Le chiamate alla PitchAPI le
intercetta Node e le fa lui: la pagina non vede mai la chiave, e nemmeno lo script.

```bash
node strumenti/batch-auto.js --leghe "Serie A,Eredivisie,ENG:Championship" --stagioni 2023/2024,2024/2025,2025/2026
```

- `--leghe`: id o nomi di `leghe.json`, `PAESE:Nome` se il nome è ambiguo (`GER:Bundesliga`).
  `--stagioni` di default sono le tre con due stagioni alle spalle. `--out` di default è
  `batch/`, fuori da git.
- Ogni CSV si salva appena la sua stagione finisce, col nome che gli dà il Comparatore; una
  stagione che ha già il file si salta, quindi rilanciare riprende da dove era. Tutto il log del
  Comparatore va in `batch.log` nella stessa cartella; a schermo le righe che contano e, ogni
  minuto, a che partita è arrivato.
- **Serve la chiave, come credenziale API dell'ambiente**, non come variabile d'ambiente (quelle
  le legge chiunque usi l'ambiente). Nelle impostazioni dell'ambiente, *Credenziali API* →
  *Aggiungi credenziale*: tipo Bearer, sito `pitchapi-proxy.salvatorepampalone-sp.workers.dev`,
  header `X-API-KEY` **senza** prefisso, valore la chiave. Il proxy dell'ambiente la aggiunge a
  ogni richiesta verso quel sito, e il sito diventa raggiungibile anche con la rete su
  *Attendibili*. Fuori da un ambiente cloud la chiave si passa con `PITCHAPI_KEY`. Prima di
  aprire il browser lo script prova una chiamata e dice cosa manca. Node esce dal proxy
  dell'ambiente perché lo script si rilancia da solo con `NODE_USE_ENV_PROXY=1`.
- Il motore è quello della cartella di lavoro: su un branch che cambia `scanner.html` il batch
  misura il branch. La build è in testa al log e in ogni CSV.
- Una stagione vera dura ore (la Championship 2023/24, 557 partite, ne stimava quasi tre alla
  partenza): si lancia in background e si legge `batch.log`. Dopo ogni file,
  `python3 strumenti/elo-archivio.py <csv>` deve dire COINCIDE. I 404 si contano a parte
  («senza dati»): sono le `/advanced` delle stagioni che non le hanno, una chiamata su quattro,
  e quelle righe escono `riserva-k-motore` come a mano.
- Il batch vive nel computer della sessione: se la sessione resta inattiva il computer può
  essere spento, e con lui `batch/`. Ogni file finito va mandato all'utente appena salvato.
- `--finto` sostituisce la PitchAPI con la lega finta del banco (`banco-parita.js` si può
  importare, ed esporta la sua `api`). Verificato così: il CSV di Serie A 2025/26 finto è
  identico riga per riga a quello del batch del banco, tranne l'ora di generazione, e l'Elo
  rifatto dal suo archivio coincide; la ripresa salta la stagione già fatta.

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

Le confidence dell'1X2 (`Confidence Globale` e la colonna Confidence delle righe `1`, `X`, `2`)
dal `b53` sono la probabilità arrotondata; nei file fino al `b52` sono `CONF_1X2_TABLE` applicata
alla probabilità. Chi confronta file di build diverse le ricalcola dalla probabilità.

La sezione `FORMAZIONI` (dal `b43`) dice per ogni squadra se la formazione della partita
c'era e se era confermata, quante formazioni dello storico l'hanno misurata, e gli indici di
*Formazioni e assenze*. `Formazioni: partita bersaglio trovata` a `no` vuol dire che la
partita non è stata trovata nell'archivio né per data; `disponibile` a `no` che l'API non aveva
i titolari; `N/D` dappertutto che il motore caricato è precedente al `b43`.

La sezione `ARCHIVIO DI LEGA` (dal `b47`) sta **in fondo** al file e ha un'altra forma: una
riga per partita del database (tre stagioni, anche le non concluse, col punteggio vuoto), con
id, stagione, orario UTC, stato, squadre e gol. Serve a rifare l'Elo fuori dal motore con
`strumenti/elo-archivio.py` (`buildGlobalElo` tiene le partite concluse prima del giorno
bersaglio, nell'ordine dell'archivio a parità di orario). Un lettore che scorre le colonne
delle partite si ferma alla riga che comincia con `=== ARCHIVIO`. Le righe `Elo: pendenza …`
nella sezione `ELO` sono il trend che sposta i lambda (vedi *Le neopromosse*).

La sezione `STANCHEZZA` (dal `b44`) dice quale stagione delle coppe europee è stata caricata,
quante competizioni su tre hanno risposto e quante partite c'erano, e per squadra i giorni di
riposo (tutte le gare e solo la lega), le partite nei 14 giorni prima, i giorni dall'ultima e
alla prossima partita europea. `competizioni europee caricate` sotto 3 vuol dire che un
archivio non è arrivato: quelle righe contano meno partite del vero.

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
| M | la curva dello stacco dà 0% / 9.0% / 37.6% / 79.7% a 30 / 83 / 240 / 826 giorni, e la tabella Elo ha media 1500 quando non ci sono pause né squadre entrate | si tocca l'Elo |
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
| `b43` | le formazioni: chi manca rispetto all'undici abituale, capitano, allenatore nuovo, dalla formazione della partita e dai `/lineups` dello storico. Card e CSV, probabilità invariate; regola del test scritta prima del batch |
| `b44` | la stanchezza: giorni di riposo contando Champions, Europa e Conference League, partite in 14 giorni, coppa europea prima e dopo. Card e CSV, probabilità invariate; regola scritta prima del batch, da misurare sopra le formazioni |
| `b45` | la card dei giocatori: falli subiti e commessi, tiri, tiri in porta, gialli, gol, assist e contrasti per giocatore sulle ultime 30 partite, ultime 5 e tutte, da `/players` a richiesta. Fuori dal giro del motore; frequenze descrittive, non ancora misurate |
| `b46` | la formazione probabile: la card dice quando è solo l'ultimo undici, la salva nel browser e, con la confermata, mostra chi è uscito e chi è entrato rispetto alla probabile. Solo a schermo |
| `b47` | le neopromosse sono sopravvalutate (−5.9 punti di vittoria 1 contro 2, quattro leghe su cinque): il CSV porta l'archivio di lega e la pendenza dell'Elo, per rifare l'Elo fuori dal motore identico al bit. Probabilità invariate; regole per l'ingresso delle neopromosse e per i pesi dell'Elo scritte prima del batch |
| `b48` | l'ingresso delle neopromosse nell'Elo: entrano al livello delle squadre uscite, chi torna dalla serie inferiore regredisce verso quel livello, la pendenza non legge più le regressioni. Registrato prima del batch, passato sulle cinque leghe e sulle tre nuove. Formazioni e stanchezza non passano; il peso dell'Elo resta 0.75 / 1.25. Batch automatico da `strumenti/batch-auto.js` |
| `b49` | le tabelle col `b48`, dal batch automatico delle cinque leghe (5230 partite in copia conforme): il motore vero fa −0.00367 di logloss 1 contro 2 come previsto, e la pendenza di calibrazione scende da 1.143 a 1.053. `CONF_1X2_TABLE` e `EDGE_BANDS` restano; la card delle soglie del pick mostra le cinque leghe col `b48`. Due voci nuove: il guadagno delle fasce per famiglia di mercato, e la coda alta della selezione contro le neopromosse. Probabilità invariate |
| `b50` | il tabellone per famiglia di mercato: regola registrata, e ordinare per guadagno atteso non sceglie meglio (+0.12 ±0.29 sulla prima proposta, tre leghe su cinque), quindi l'ordine resta per scarto; l'etichetta di ogni riga dice quanto rende il suo tipo di mercato (1X2 FORTE +27.5, gol +1.0, numeri +7.2). A 390px il tabellone non esce più di lato, e il banco lo controlla. Probabilità e CSV invariati |
| `b51` | il mega-prompt riscritto per le due cose che servono all'utente, decidere cosa giocare e capire la partita: sintesi in cima, poi la partita, il perché delle proposte e i rischi. Aggiunti il pick con la sua fascia, i rischi calcolati e la stanchezza come contesto; tolti Ordered Logit, KNN e correzione residuale (peso 0), numeri vecchi e una frase rotta. Le soglie del pick in una costante sola (`PICK_RESA`) per card e prompt. Il banco controlla che il prompt non sia vuoto né rotto. Probabilità e CSV invariati |
| `b52` | le tre leghe nuove col `b48` (3495 partite in copia conforme): la coda alta contro le neopromosse non si ripete (−0.3 ±2.0, voce chiusa); le soglie del pick e `CONF_1X2_TABLE` non reggono fuori dai cinque campionati, quindi card e mega-prompt lo dicono e per Championship, Eredivisie e Liga Portugal danno le rese misurate a parte (`PICK_RESA.leghe` / `fuori`); il `b48` sul motore vero fa quello che la ricostruzione prevedeva; i due muri dei gol e il riferimento dei mercati sui numeri si ripetono. Registrato il test della confidence nuda su quattro leghe mai aperte. Probabilità e CSV invariati |
| `b53` | la confidence dell'1X2 è la probabilità del motore (`CONF_1X2_MODE = 'nuda'`): registrato prima, sulle quattro leghe mai aperte (2. Bundesliga, First Division A, Premiership scozzese, Super League svizzera, 3202 partite in copia conforme) batte la tabella del `b38` in quattro su quattro, −0.00220 di Brier (`z = −4.09`). Le quattro leghe entrano in `PICK_RESA.fuori`. Probabilità invariate; nel CSV cambiano solo le confidence dell'1X2 |
