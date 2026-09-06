# AGENTS.md — Scanner Calcio V9.7

Istruzioni per chi (agente o persona) mette mano a questo repository.

## Cos'è

Modello analitico per il calcio, servito come pagine statiche. Nessun build,
nessun package manager, nessun test runner: si aprono i file nel browser e
basta. Tutto il codice sta dentro un unico `<script>` inline per file.

| file | ruolo |
|---|---|
| `index.html` | menu, due link |
| `scanner.html` | **il motore**. Analizza una partita: Dixon-Coles + Markov (l'Ordered Logit è calcolato e mostrato ma pesa 0), mercati, statistiche previste |
| `comparatore.html` | **backtest**. Carica `scanner.html` come testo, lo inietta in memoria e ne guida il motore su centinaia di partite, poi esporta un CSV previsto-vs-reale |
| `leghe.json` | catalogo leghe/stagioni (id PitchAPI) |

Dati da PitchAPI via proxy Cloudflare: `PITCH_BASE` in `scanner.html`.
Endpoint usati per partita: `/stats`, `/lineups`, `/advanced`, `/events`,
tutti attraverso `fetchMatchRaw` (che li mette in `RAW_CACHE`).

### Dove trovare le cose

Il documento è lungo perché è la memoria del progetto: ogni sezione è una domanda a
cui si è già risposto, con i numeri. Le tre porte d'ingresso:

- **«Devo mettere mano al codice, cosa devo sapere per non rompere niente?»** →
  *Come funziona il motore*, *Il contratto Scanner ↔ Comparatore*, *Convenzioni del
  motore*, *Trappole già corrette*, *Come validare una modifica*.
- **«Ho un'idea per migliorare il modello, è già stata provata?»** → *Cosa è già stato
  provato*, e la tabella qui sotto. Quasi certamente sì, e c'è scritto con che numeri
  è stata chiusa.
- **«Ho appena fatto un backtest, come lo leggo?»** → *Come validare una modifica*
  (controlli H e I, da fare **prima** di analizzare), *Trappole* (l'AUC dei mercati gol
  non si legge aggregata, il CSV ha una cifra decimale), *Leggere il log del
  Comparatore*.
- **«Questo file dice il vero?»** → *L'audit del documento*: cosa è stato
  ricontrollato contro il sorgente, e i quattro punti in cui il testo era rimasto
  indietro.

**Le sei cose che più facilmente fanno perdere una giornata**, se non le sai:

1. `_base` **non** è una media di lega: è una media della **coppia**, e correla 0.84
   col numeratore. → *La baseline di coppia*.
2. L'**AUC dei mercati gol non si legge mai aggregata** fra leghe: i base rate diversi
   la gonfiano. Serie A 45.8% di Over, Premier 55.0%. → *Trappole*.
3. Il CSV scrive le probabilità a **una cifra decimale**: ±0.05 punti su ogni Brier,
   e i confronti con la soglia di giocabilità sbagliano al confine. → *Trappole*.
4. Il lambda è **inversamente proporzionale** alla media gol di lega. Prima di dedurre
   una direzione, scrivi la formula. → *Il paradosso della Premier*.
5. In `predictStat` **`k` alto = MENO shrinkage**; in `SHRINK_K` e `SHRINK_LAM_K`
   è l'opposto. → *Convenzioni del motore*.
6. Lo scope `role` è un **sottoinsieme** di `overall`: con `limit = 15` sono 8
   partite, non 15. Ogni costante è tarata su quelle 8. → *Il campione di ruolo è
   un sottoinsieme*.

**E una regola sul documento stesso.** Le sezioni qui sotto sono state scritte
lungo ventidue build, e un audit voce-per-voce contro il sorgente ha trovato quattro
punti in cui il testo descriveva un motore diverso da quello che gira — uno dei
quali stava proprio nell'elenco delle trappole *già corrette*. Prima di fondare una
misura su una frase di questo file, **verificala nel sorgente**: qui c'è la
memoria del progetto, non la sua verità corrente. → *L'audit del documento*.

## Stato del lavoro, e da dove ripartire

Sezione di consegna: dice a che punto siamo, così una sessione nuova non
ricomincia da capo. Aggiornala quando cambia qualcosa di sostanziale.

**Build corrente: `0905-b22`.** Scanner e Comparatore devono coincidere, e sul
Comparatore il badge sotto la dropzone deve uscire **verde** dopo aver trascinato
lo Scanner. Il branch di lavoro è `claude/scanner-stat-optimization-sgs62u`.

**Sul «N commit behind»:** GitHub conta i *merge commit* delle PR, che stanno su
`main` e non sul branch. Il contenuto è lo stesso: dopo ogni merge
`git diff origin/main -- scanner.html comparatore.html AGENTS.md` è vuoto e
`git rev-list --left-right --count origin/main...<branch>` dà `N 0` — lo zero a
destra vuol dire che il branch non ha niente che `main` non abbia. Non c'è niente
da recuperare: i file dei due rami sono byte per byte identici.

### Dove siamo

L'**1X2 funziona**: 51.4% di pick azzeccati sulle 1133 partite del `b21` contro il
~43% del «gioca sempre in casa», e la fascia ≥60% rende il 71–78%. L'ensemble è
`Dixon-Coles 70% + Markov 30%` su lambda stimati su **tutte** le partite di una
squadra; l'Ordered Logit è calcolato e mostrato ma ha **peso 0**.

I **mercati gol** restano il muro, ma dal `b22` si sa di che è fatto, e sono due cose
distinte che vanno tenute separate:

- **Ordinare le partite**: AUC dell'Over 2.5 fra 0.51 e 0.57. È il muro vero, e
  nessuna feature provata lo ha spostato più di qualche millesimo. L'unica che ha
  retto è `sum_sot` (vedi *I gol*).
- **Azzeccare il livello**: qui il `b22` ha chiuso tre ipotesi sbagliate (`rho`,
  sovradispersione, forma della distribuzione) e ne ha lasciata **una sola in piedi**,
  già strumentata: la media gol di lega è piatta su tre stagioni mentre il lambda le
  è inversamente proporzionale. Vedi *Il muro dell'Over/Under: tre ipotesi* e *La base
  di lega risponde alla domanda sbagliata*.

I **mercati sui numeri discriminano meglio dei gol**: cartellini ~0.59 di AUC dopo il
`b16`, tiri in porta ~0.56, corner ~0.53. Sono anche i meno guardati.

**Strade chiuse da misure, non da opinioni** (i numeri in *Cosa è già stato provato* e
nelle sezioni dedicate): prevedere meglio le stats avanzate — siamo al tetto; usare le
stats per calibrare la forza dell'avversario — si fa già; sistemare il KNN — ridondante
col Dixon-Coles; ritoccare l'Ordered Logit — è mal specificato *e* inutile
all'ensemble; `GOALS_UNIT_FIX` — la diagnosi regge, la cura no; `rho` e la
sovradispersione — scagionati con i dati in mano.

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
| `b17` | trovato un **disallineamento di unità** nel lambda: attacco e difesa sono NPxG divisi per la media **gol**. Correzione pronta ma spenta |
| `b18` | **la lega non arrivava mai al motore nei backtest**: media gol e rho erano fissi. Tutte le tarature vanno riviste |
| `b19` | **audit sistematico**: sette fallback morti, due tabelle di costanti divergenti, una metrica che non era di squadra |
| `b20` | l'**Ordered Logit contava la casa due volte** (bias +6.8 sull'`1`): soglie ristimate e peso a 0. Ensemble riscritto a due blocchi, ruolo e completo, con `ENS_SCOPE_W` |
| `b21` | **il completo batte il ruolo sull'1X2**, monotono in tre leghe su tre, `z = -3.96`: `ENS_SCOPE_W` a 1. E l'etichetta di lega del CSV veniva dalla dropdown, non dalla partita |
| `b22` | **`rho` e la sovradispersione scagionati**, il disallineamento di unità è già compensato: il muro dell'Over/Under è tutto nel **livello** del lambda, e la base di lega è una media piatta di tre stagioni. `aerials` era corretto solo nello Scanner |

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

0. ~~Un backtest `b20` che decida `ENS_SCOPE_W`~~ — **fatto, ed è 1**: il completo
   batte il ruolo sull'1X2 in tutte e tre le leghe, `z = -3.96`. Vedi *Ruolo o
   completo*.
0-bis. ~~Il `rho` come causa del muro dell'Over/Under~~ — **falsificato**: spegnerlo
   sposta l'Over 2.5 di **+0.0 punti** in tutte e tre le leghe. Anche la
   sovradispersione è esclusa (i totali sono *sotto*dispersi, var/media 0.85-0.98) e
   la forma non lascia residui significativi. Vedi *Il muro dell'Over/Under: tre
   ipotesi*.
0-ter. **Misurare `LEAGUE_HALFLIFE_DAYS`.** È l'unica cosa rimasta sul muro
   dell'Over/Under, ed è già strumentata: il lambda è **inversamente proporzionale**
   alla base di lega, e la base è una media **piatta su tre stagioni** mentre tutto il
   resto del motore decade con emivita 106 giorni. La Premier usa 3.041 gol di base
   contro i 2.754 veri e paga il 5% sul lambda. Il CSV esporta la versione piatta e
   quella decaduta fianco a fianco: **un backtest decide**, senza rilanciare il
   motore. Vedi *La base di lega risponde alla domanda sbagliata*.
1. **Rifare il backtest col `b18` su tutte e cinque le leghe.** Solo la Serie A è
   stata rifatta (`d644c70c`, 378 partite): media gol 1.365/1.183 invece di
   1.500/1.200, rho `-0.043` invece di `-0.11`, su 949 partite di lega vere. Ha
   spostato poco (bias λ `-2.5% -> -1.7%`, Over 2.5 `-2.2 -> -2.0`), ma **le altre
   quattro leghe hanno ancora tutte le misure prese con la lega congelata**, e i
   loro totali reali sono molto diversi (Bundesliga 3.25, Serie A 2.43): lì il bug
   mordeva molto di più. Prima cosa da guardare nel CSV nuovo:
   `Unita: partite di lega usate` deve essere alto, non 0.
2. ~~Provare `GOALS_UNIT_FIX`~~ — **chiuso, e resta spento.** Il disallineamento
   esiste (tutti e otto i moltiplicatori attacco/difesa stanno sotto 1) ma è **già
   compensato** dalla contrazione verso la media di lega. E la correzione del `b17`,
   così com'è scritta, romperebbe due cose: `_baseN` correla **0.77-0.87** col
   lambda (la trappola del `b9`/`b11`) e il livello sfonderebbe a 2.87-3.65 contro
   gol reali 2.43-2.75. Per correggerlo davvero servirebbe una media NPxG **di
   lega**, che il motore non ha. Vedi *Il disallineamento di unità è reale, ma è già
   compensato*.
3. **Continuare sui cartellini.** Il `b16` ha preso il primo pezzo (lo squilibrio,
   AUC 0.562 → 0.593). Restano: l'**arbitro** — `/v1/matches/{id}` lo espone e il
   nome è già in `globalLeagueMatchesCache`, ma i cartellini delle sue partite
   passate no, quindi servirebbero ~15 chiamate in più per profilarlo; la
   **posizione in classifica** (calcolabile a costo zero dai punteggi già in
   cache); e lo stesso effetto squilibrio sui **tiri in porta**, oggi a 2.8 sigma
   con una lega discorde.
4. ~~Capire la Premier sui tiri in porta~~ — **era rumore**: test di omogeneità
   sulle pendenze p = 0.12, con errori standard di 0.27–0.33 su ~300 partite.
   Nessuna lega è diversa dalle altre su nessuno dei tre mercati statistici.
5. ~~Capire perché il Dixon-Coles è cieco sull'Over in Premier e Serie A~~ —
   **domanda mal posta**, le cinque leghe sono indistinguibili (p = 0.19). Vedi
   *Il modello non fallisce in una lega più che in un'altra*. La domanda giusta
   resta quella di sempre: il lambda correla **+0.087** col totale dei gol, e
   nessuna feature provata lo alza. È il muro dell'Over/Under, punto.
6. **Verificare la pendenza dell'Elo** (`penH`/`penA`, ±8% sui lambda): non è mai
   stata misurata, e ora che il livello entra dall'inclinazione potrebbe essere
   ridondante. Serve esportarla nel CSV.
7. **`GOALS_SOT_W` e `ELO_1X2_W` alla sesta lega.** Il backtest dice 0.50, ma 0.75 e 1.00 sono
   migliori di un margine non distinguibile (±0.030 di errore standard). Il CSV
   ricostruisce tutti i pesi senza rilanciare il motore: basta un'altra lega.
8. **L'endpoint `/shots`.** Il candidato più serio per la forma della
   distribuzione dei gol, con la ragione spiegata in *Il muro dell'Over/Under*.
   Costa una chiamata in più per partita.
9. **Un ancoraggio di lega per i falli**, che oggi non ce l'hanno (il rapporto coi
   gol varia del 28% fra leghe, quindi `MARKET_PER_GOAL.fouls = null`).
10. **La tab «racconto»**: mostrare uno scenario invece di una distribuzione. Idea
   arrivata da fuori, già misurata e in parte bocciata — vedi *Lo scenario
   singolo*. La parte che sopravvive è la card dei risultati esatti.
11. **Ricontrollare `avg_def_x`**: pendenza 0.06, la previsione è quasi scorrelata
   dal reale. O è un problema di forma del modello, o la metrica va tolta.
12. **Togliere `vaep_def`, `pv_def`, `sca_def`** dalle feature: correlazione
   previsto/reale a zero su 1133 partite. Il fix additivo che le ha rese
   calcolabili era giusto, ma quello che si vede è rumore.

13. **Decidere che fare del campione di ruolo.** Oggi `role` è un sottoinsieme di
   `overall` (8 partite su 15), mentre questo documento ha sostenuto per parecchie
   build che i due insiemi fossero indipendenti. Non è un refuso da correggere di
   getto: renderli indipendenti sposta lo shrinkage dei lambda di ruolo dal 27% al
   17% e invalida ogni costante tarata finora. Strada canonica: esporre
   `ROLE_SCOPE_INDEPENDENT` a 0, esportare `role.n` nel CSV, un backtest decide.
   Vedi *Il campione di ruolo è un sottoinsieme*.
14. **Portare `RESID_GAMMA` a 0.360** (o rimisurarlo) prima di rileggere la sezione
   *A/B CORREZIONE RESIDUALE* del CSV: nel codice è ancora 0.678, cioè la scala che
   il `b5` ha dichiarato sbagliata. Non sposta probabilità (`RESID_ALPHA = 0`),
   sposta la diagnostica che dovrebbe dire se riaccendere la correzione.
15. **Ripulire il codice morto trovato dall'audit del documento**: otto variabili
   riempite dal payload `/advanced` e mai usate, `getTopScorersPlain`, `xgSpH`/
   `xgSpA`, `predH`/`predA`, `roleLimit`, `nMinRole`, `STAT_SHRINK`, e la seconda
   copia di `_calibConf1X2` nel Comparatore. Zero effetto sui numeri, quindi va
   fatto con la verifica per confronto di AST (vedi *Come validare*).

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
  (`400·log10(wr_casa/wr_trasferta)`, limitato fra 30 e 100, e solo con almeno 50
  partite in archivio), K adattivo (30 sotto le 15 partite, poi 20),
  moltiplicatore per scarto di gol, cronologico e a somma zero. Il **salto data**
  era una funzione a gradini ed è stato smussato nel `b9`: oggi è
  `0.9·(1 − exp(−(giorni − 45)/110))`, verificato nel sorgente. Vedi *Il salto
  data dell'Elo*.

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
- **Markov** — `markovFlow` con rate dipendenti dal punteggio. Verificato negli
  invarianti (`p1+pX+p2` fa 1, simmetrico scambiando i lambda, scarto massimo dal
  Dixon-Coles 0.035) e, dal `b20`, **come modello a sé sul backtest**: su 1743
  partite fa logloss **1.0091** e pick **51.5%**, cioè leggermente *meglio* del
  Dixon-Coles (1.0098 / 51.4%). Non è un dettaglio: è il motivo per cui la selezione
  fuori campione gli ha portato il peso da 0.10 a **0.30**. I suoi **parametri
  interni** restano però non verificati.
- **Probabili formazioni**: PitchAPI espone `/lineups` anche in versione prevista.
  Da valutare dopo il resto.
- **Le metriche fuori dal CSV**: `cross`, `thru`, `aer`, `seq_time` e `xg_shot` il
  motore le raccoglie e le mostra, ma nessun backtest le ha mai viste. Aggiungerle
  al CSV costa poche righe e sarebbe il primo passo per sapere se valgono qualcosa.
  **Attenzione**: questa voce elencava anche `pass_acc`, `ht` e `xg_op`, e per
  quelle era falsa. Non sono «fuori dal CSV», sono **fuori da tutto**: vengono
  lette dal payload `/advanced` in una variabile locale che non entra mai in
  `matchDetails`. Vedi *Otto variabili che leggono il payload e non arrivano da
  nessuna parte*.
- **Il `k` di `aerials` e la sua riga nella Progressione Storica**: il `k = 0.54` è
  tarato sulla quantità *condivisa* di prima del `b19`, e la riga `t = +2.4` misurava
  un volume di partita. Ora che il CSV esporta il valore giusto (`b22`) si possono
  finalmente rifare tutte e due.
- **Le sette metriche col `k` di default 0.50** (`gf`, `direct_speed`, `seq_time`,
  `avg_x`, `cp_regains`, `rec_time`, `xg_sp`): nessuno le ha mai misurate. Non è un
  errore, ma non è nemmeno una scelta.

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
sono quelle **fra queste** che la squadra ha giocato nel proprio ruolo — in casa
per la squadra di casa, in trasferta per l'ospite. **`role` è un sottoinsieme di
`overall`, non un insieme indipendente**: in codice è
`roleMatches = overallMatches.filter(...)`, e con il default `limit = 15`
restano **8 partite** per parte (misurato, non stimato). Questo documento ha
sostenuto il contrario per parecchie build — vedi *Il campione di ruolo è un
sottoinsieme, e il documento diceva di no*. I lambda
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

**L'ensemble 1X2** (dal `b22`) è `Dixon-Coles 70% + Markov 30%`, su lambda stimati su
**tutte** le partite di una squadra, con l'Ordered Logit a **peso 0**. In codice sono
tre costanti esposte, tutte e tre misurate fuori campione:

```js
window.ENS_W = { dc: 0.70, mk: 0.30, ol: 0.00 };   // scelti leave-one-league-out
window.ENS_SCOPE_W = 1;                            // 1 = lambda su tutte le partite
```

e la forma è due blocchi identici più un termine:

```
RUOLO    = ENS_W.dc·probsRole + ENS_W.mk·mk_ro     (lambda casa/trasferta)
COMPLETO = ENS_W.dc·probsOver + ENS_W.mk·mk_ov     (lambda su tutte le partite)
core     = (1 − ENS_SCOPE_W)·RUOLO + ENS_SCOPE_W·COMPLETO
finale   = (1 − ENS_W.ol)·core + ENS_W.ol·probsOL
```

Con `dc/mk/ol = 6/1`, `ol = 0.30` e `ENS_SCOPE_W = 0` si riottiene **esattamente**
l'ensemble del `b19` — c'è un test che lo verifica, ed è il modo per confrontare una
build nuova con la vecchia senza rileggere il diff.

**Attenzione a una asimmetria deliberata**: `ENS_SCOPE_W = 1` vale **solo per l'1X2**.
La matrice da cui escono GG, Over/Under, multigol, risultati esatti e handicap resta
quella di **ruolo** (`dcMat = dcRole`), perché sui mercati gol il completo ordina
meglio in due leghe su tre ma peggiora la calibrazione ovunque. È scritto nel commento
della costante perché è il tipo di cosa che qualcuno «sistema» in buona fede.

- L'**Ordered Logit** ha preso il posto del KNN. Su 2639 partite, stesse
  partite per entrambi, il KNN faceva 46.3% e l'OL 50.2% — ma il problema vero
  era la calibrazione: quando il KNN diceva "70%" succedeva il 63%, quando
  diceva "50-60%" succedeva il 42%, scarti fino a −18 punti. Causa: media di
  pochi vicini, stime estreme e instabili (dava prob >70% in 1007 partite su
  6824, il DC solo in 55). L'OL modella l'esito come variabile **ordinale**
  (2 < X < 1) su una scala latente `y* = beta × (forza_casa − forza_trasferta)`
  tagliata da due soglie, e ha scarti di calibrazione entro ±3.6 punti su tutte
  le fasce. I parametri originali erano `OL_BETA = 1.950`, `OL_T1 = −0.850`,
  `OL_T2 = 0.350`, stimati per massima verosimiglianza su 1903 partite (split
  temporale 70/30) e validati su 816 mai viste — **sostituiti nel `b20`** da
  `2.056 / −0.475 / +0.671`, ristimati su 1743 partite e validati
  leave-one-league-out, perché i primi contavano il vantaggio casa due volte. La forza è `0.7 × attacco + 0.3 × difesa_avversaria`:
  l'additivo batte il moltiplicativo, e l'attacco pesa più della difesa
  avversaria (correlazione 0.26 contro 0.17).
- **Il peso dell'OL è 0 dal `b20`**, e le sue soglie sono state ristimate a
  `OL_BETA = 2.056`, `OL_T1 = −0.475`, `OL_T2 = +0.671`: quelle vecchie contavano il
  vantaggio casa **due volte** e producevano +6.8 punti di bias sull'`1`. Resta
  calcolato e mostrato perché la card dei modelli e il mega-prompt lo citano, e un
  numero a schermo va tenuto giusto anche quando non pesa. Vedi *L'ensemble 1X2*.
  Il sospetto che l'aveva tenuto sotto il picco 0.45 del KNN era fondato e si è
  rivelato più forte del previsto: l'OL mangia lo stesso NPxG del Dixon-Coles, quindi
  non porta informazione in più — misurato, non congetturato.
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
| breakdown SCA | `sca_dead` 0.18 · `sca_takeon` 0.16 · `sca_foul` 0.11 · `sca_shot` 0.10 |
| passaggi | `passes` 0.54 · `prog_passes` 0.47 · `passes_box` 0.44 · `prog_pass_dist` 0.36 · `switches` 0.28 · `assists` 0.16 · `second_assists` 0.17 |
| conduzioni | `carries` 0.49 · `prog_carry_dist` 0.50 · `carry_dist` 0.48 · `prog_carries` 0.48 · `carries_f3` 0.38 · `take_ons` 0.37 · `carries_box` 0.55 |
| difesa | `aerials` 0.54 · `ppda_num` 0.53 · `ppda_den` 0.29 · `clearances` 0.30 · `tackles` 0.23 · `interceptions` 0.23 · `duels_won` 0.22 · `blocks` 0.20 · `challenges` 0.14 · `yel` 0.23 · `fouls` 0.48 |
| possession value | `xt` 0.40 · `vaep_off` 0.23 · `pv_off` 0.21 · `vaep` 0.18 · `pv` 0.15 |
| default | 0.50 |

Sono **51 voci**, e 51 sono le chiavi di `STAT_SHRINK_TABLE` nel codice: i valori
qui sopra coincidono con quelli del sorgente cifra per cifra (ricontrollato). Le
tre voci `vaep_def`, `pv_def` e `sca_def` che questa tabella ha elencato fino
all'audit del documento **non ci sono più dal `b7`**, quando le metriche sono
uscite da `ADV_SPEC`: se le rimetti, rimetti anche il loro `k`.

Leghe discordi (pendenze con spread > 0.35, valore tenuto prudente): `fouls`,
`vaep_off`, `pv_off`, `assists`.

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

Il Comparatore ha la tabella speculare `CMP_NEW_SPEC`, che serve a estrarre i
valori reali per il CSV. Se aggiungi una riga in `ADV_SPEC`, aggiungila anche lì
(e in `NEWK` dell'export), altrimenti la metrica viene prevista ma mai verificata.

**Quante sono, oggi**: `ADV_SPEC` ha **31 voci**, `CMP_NEW_SPEC` ne ha **34** —
le tre in più sono `vaep_def`, `pv_def` e `sca_def`, uscite da `ADV_SPEC` nel `b7`
ma tenute nel Comparatore perché il CSV continui a esportarne il valore reale.
Sulle 31 condivise i due getter leggono lo **stesso campo, nello stesso ordine**
(controllo E, rifatto: zero divergenze). Il «34 metriche nuove» che si legge nella
cronologia e nel commento sopra `CMP_NEW_SPEC` è il conto del `b4`, non quello di
oggi.

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
    e `predictStat` tornava `null`. I guardiani per le additive sono su
    `isFinite`, non sul segno.

    Oggi `STAT_TYPE` contiene **quattro** voci e non sei: `avg_x`, `avg_def_x`,
    `vaep`, `pv`. `vaep_def` e `pv_def` sono uscite da `ADV_SPEC` nel `b7`, quindi
    il motore non le prevede più — ma il predittore di riserva del Comparatore
    (`cmpDcPredict`) le tiene in `CMP_ADV_KEYS` e le tratta ancora con la **forma
    moltiplicativa**. Su quelle righe (`Origine metriche avanzate = riserva-*`) il
    numero non vale niente per lo stesso motivo scritto qui sopra.
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
   restavano ~7 gare. **Questa voce era falsa e va letta al contrario**: nel
   `scanner.html` di oggi il ruolo *è* ancora un sottoinsieme, e con `limit = 15`
   restano 8 partite. Vedi *Il campione di ruolo è un sottoinsieme, e il documento
   diceva di no*.
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
- **Il CSV scrive le probabilità a un decimale.** Qualunque controllo che
  confronti un verdetto con una soglia (la giocabilità a 55%) sbaglia sui casi al
  confine, e ogni Brier o AUC calcolato su quelle colonne porta ±0.05 punti di
  quantizzazione. Non è un errore del motore: è il limite del file.
- **Una metrica senza «concesso» non entra in `STAT_PAIRS`**, quindi
  `predictStat` le restituisce la sola media di squadra e il suo `k` tarato non
  viene mai usato — in silenzio. Era il caso di `f3_entries`. Dopo aver aggiunto
  una metrica, controllare a runtime che `Object.keys(STAT_PAIRS)` la contenga e
  che ogni voce di `STAT_SHRINK_TABLE` corrisponda a una coppia.
- **Non normalizzare un valore prima di aver provato tutte le sue fonti.**
  `zeroIf` girava prima dei fallback su `/stats` e li rendeva codice morto per
  sette metriche. Regola: prima si tenta ogni fonte, poi si decide cosa fare del
  mancante. Un `if (x === null)` dopo un `x = zeroIf(x, ...)` non scatta mai.
- **Due copie della stessa costante divergono, sempre.** `CMP_DC_SHRINK_TABLE`
  era rimasta ai valori pre-`b5` mentre lo Scanner era stato ritarato. Se una
  costante deve esistere in entrambi i file, il Comparatore la legge da
  `window.*` del motore e tiene la propria solo come rete, dicendolo nel log.
- **Una metrica condivisa fra le due squadre non è una metrica di squadra.**
  `defending.aerials` (duelli aerei della partita) era identico per casa e
  trasferta nel 100% dei casi: `predictStat` contava due volte la stessa cosa.
  Controllo da rifare su ogni metrica nuova: il valore reale di casa e quello di
  trasferta sono mai identici?
- **Un valore di ripiego plausibile è più pericoloso di un errore.** `avgH 1.50 /
  avgA 1.20` sono numeri ragionevoli per il calcio, e per sedici build hanno
  nascosto che la lega non arrivava mai al motore nei backtest. Ogni fallback deve
  esporre **su quante osservazioni** è stato prodotto. Vedi *La lega che non
  arrivava mai*.
- **Assegnare un valore a una `<select>` senza l'`<option>` corrispondente non fa
  niente**, e non solleva errori: `el.value` resta `""`. Se il codice passa
  configurazione via DOM, va verificato che sia attecchita.
- **Prima di spiegare una differenza fra leghe, misurare se esiste.** Con una
  stagione a lega l'errore standard di una correlazione è ~0.053: due leghe
  possono distare 0.15 per puro caso. Prendere il minimo di cinque stime rumorose
  e cercarne la causa è confronto multiplo, e il calcio offre un aneddoto
  plausibile per qualunque ipotesi. Ci sono cascato io nel `b14`. Vedi *Il modello
  non fallisce in una lega più che in un'altra*.
- **Una correzione applicata in un file va applicata in tutti e due.** Il `b19` aveva
  scoperto che `aerials` leggeva i duelli *della partita* invece di quelli *vinti*, e
  aveva corretto `ADV_SPEC` nello Scanner — ma `CMP_NEW_SPEC` nel Comparatore era
  rimasto indietro, quindi il CSV confrontava una previsione di squadra (14.5) con una
  quantità di partita (28.4), rapporto **0.511**. Dopo aver toccato un getter, il
  controllo è meccanico: estrarre le due tabelle e confrontare campo per campo
  (`spec.js`). Vale anche per le costanti — è la stessa forma del caso
  `CMP_DC_SHRINK_TABLE`.
- **Una diagnosi giusta non rende giusta la cura.** Il disallineamento di unità del
  `b17` era reale (otto moltiplicatori su otto sotto 1), ma la correzione proposta
  usava una baseline che correla 0.77-0.87 col lambda e avrebbe sfondato il livello del
  30%. Prima di accendere una correzione, misurare **quanto sposta** e **contro cosa
  divide**, non solo se la diagnosi regge.
- **Un valore preso dal DOM è una lettura di un istante, non un dato dell'entità
  che stai descrivendo.** `cmpBuildResult` scriveva la lega di ogni partita leggendo
  il testo selezionato in `#cmp-league` *in quel momento*; `cmpUpdateLeagues()` lo
  svuota a `'-- --'` a ogni cambio di paese, e in un archivio multi-lega il 59-88%
  delle righe usciva con la lega sbagliata. Se un valore appartiene a un'entità
  (partita, lega, stagione), va letto da quell'entità. È la seconda volta in tre
  build che il DOM è la causa (la prima è `sel-league` senza `<option>`, `b18`).
- **Una chiave di raggruppamento va verificata contro qualcosa di indipendente.**
  Un'etichetta sbagliata non rompe niente: sposta le conclusioni, in silenzio. Per
  la lega bastano i nomi delle squadre — tre righe di codice che hanno trovato il
  bug qui sopra e confermato che i 25 CSV precedenti erano puliti. **Ogni CSV nuovo
  va passato da lì prima di analizzarlo per lega.**
- **Una correzione espressa come *rapporto* non è trasportabile su un'altra
  baseline.** `goalsSotCorrection` torna una `scale` calcolata contro il totale che
  le passi; il `b19` applicava la scala del ruolo **anche** ai lambda completi, che
  quindi venivano tirati verso il totale del ruolo invece che verso i tiri. Se una
  funzione torna un rapporto, il denominatore fa parte del risultato. È la stessa
  forma di errore della `_base` di coppia, ricomparsa due build dopo in un punto
  diverso. Corretta nel `b20` con un `_GCo` proprio.
- **Il vantaggio del campo si conta due volte con una facilità sorprendente.** È la
  trappola numero 1 di questo elenco, corretta anni fa nel modello di ruolo, e nel
  `b20` è stata ritrovata **identica** dentro l'Ordered Logit: la variabile usava lo
  scope `role` (che il vantaggio casa già ce l'ha, +0.196 di media) e le soglie
  erano centrate a `-0.250` (che glielo ridà). Regola: ogni volta che un modello
  usa numeri di ruolo, chiedersi se ha *anche* un termine casa esplicito, e
  misurare la media della variabile — se non è centrata su zero, la costante che la
  accompagna non può essere simmetrica. Vedi *L'ensemble 1X2*.
- **Un componente con peso 0 va comunque tenuto giusto.** L'Ordered Logit del
  `b20` non entra più nel risultato, ma resta a schermo e nel mega-prompt: lasciarlo
  con le vecchie soglie voleva dire mostrare 52% di `1` dove la verità è 45%. Il
  peso zero toglie l'effetto sul conto, non la responsabilità sul numero.
- **Le etichette di riga del CSV devono essere uniche.** Tre sezioni diverse
  usavano `applicata`, due `peso w` e due `ha toccato il cap`: un parser che
  cerca per etichetta prende la prima e legge la sezione sbagliata **senza
  accorgersene**. Corretto nel `b14` con un prefisso (`Tiri:`, `Elo:`). Le uniche
  ripetizioni legittime sono le metriche nelle sezioni CASA e TRASFERTA, che vanno
  in coppia per costruzione.
- **Non leggere mai l'AUC dei mercati gol aggregata fra leghe.** Con base rate
  diversi (Premier 55.1% di Over 2.5, Serie A 45.7%) l'aggregato dava 0.531 dove
  dentro ogni lega era 0.495 e 0.500, cioè caso puro. Sempre per lega.
- **Anche un elenco di trappole corrette è una costante non stimata.** Il punto 6
  qui sopra dava per risolto un difetto che nel `scanner.html` di questo repository
  non è mai stato risolto, e lo descriveva con il numero giusto («con 15 restavano
  ~7 gare», sono 8). Una voce del genere non fa danno da sola: fa danno perché
  chiude la domanda. La regola è la stessa delle costanti — **accanto a «corretto»
  va scritto dove guardare nel sorgente per riverificarlo**, altrimenti fra sei
  build nessuno sa più se è vero. Vedi *L'audit del documento*.

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
| Ritoccare i pesi dell'ensemble (DC/OL/Markov) | **quasi non serve** | rimisurato nel `b20` con selezione fuori campione: la griglia toglie l'Ordered Logit (0.00 in 4 fold su 5) e porta Markov a 0.30. Vale `−0.0013` di logloss con `z = −2.03` e una lega discorde: al bordo del rumore, adottato più per pulizia che per guadagno. Vedi *L'ensemble 1X2* |
| Correggere le soglie dell'Ordered Logit | **funziona sul modello, non sull'ensemble** | il bias sull'`1` passa da +6.8 a −0.1 e il logloss da 1.0397 a 1.0270 fuori campione, ma l'ensemble si muove di `0.0001`: l'OL mangia lo stesso NPxG del Dixon-Coles. Fatto lo stesso, perché il numero è a schermo |
| **Lambda su tutte le partite invece che casa/trasferta** (`ENS_SCOPE_W`) | **funziona** | logloss 1.0113 → **1.0071**, pick 50.9% → 51.4%, monotono in **3 leghe su 3**, `z = −3.96`, scelta fuori campione 1.0 in 3 fold su 3. Il guadagno più solido della serie `b20`–`b22`. Vale solo per l'1X2: sui gol la calibrazione peggiora. Vedi *Ruolo o completo* |
| `rho` come causa del bias dell'Over 2.5 | **falsificata** | spegnerlo sposta l'Over 2.5 di **+0.0 punti** in tutte e tre le leghe: `rho` stimato vale fra −0.001 e −0.043 e tocca quattro celle di una matrice 11×11 |
| Una distribuzione a coda più grassa per i gol | **falsificata, ed era di segno sbagliato** | il totale gol è **sotto**disperso rispetto a Poisson: var/media 0.849 / 0.895 / 0.975 |
| `GOALS_UNIT_FIX` (normalizzare attacco/difesa sugli NPxG) | **diagnosi giusta, cura sbagliata** | il disallineamento c'è (8 moltiplicatori su 8 sotto 1) ma è già compensato a valle; la cura divide per una baseline che correla 0.77–0.87 col lambda e porterebbe il livello a 3.13–3.65 contro 2.43–2.75 veri |
| Ricalibrare le rette della confidence | **non serve** | rifittate su 756 partite danno 16.88 + 0.686·p contro 6.26 + 0.880·p: ai punti che contano (50–60%) coincidono entro un punto |
| Affilare le probabilità (temperatura) | **non serve** | il Brier peggiora oltre T≈1.1 su 716 partite |
| Stimare attacco/difesa su **tutta la lega** invece che su 15 partite a squadra | **non serve** | AUC 0.681 contro 0.680 del modello attuale; mescolato 0.688 contro lo 0.690 che l'Elo dà già. Sul totale gol è perfino peggio. Vedi *L'Elo nell'1X2* |
| Individuare le partite che finiranno pari | **non regge** | `pX` ha AUC **0.487** (SE ±0.020) su 1133 partite: nessuna capacità di distinguere. Anche `-\|p1−p2\|` e `-max(p1,p2)` stanno a 0.495–0.498. La calibrazione è giusta in media (27.6% detto contro 25.9% reale) ma piatta a fasce. Vedi *Lo scenario singolo* |

**Le cose che hanno superato la verifica incrociata su più leghe** (in ordine di
quanto valgono):

| idea | esito | numeri |
|---|---|---|
| **L'Elo che inclina i lambda** dell'1X2 | **regge, ed è il pezzo più forte** | confermato su cinque leghe, peso salito a 0.75. Vedi *L'Elo nell'1X2* |
| **`ENS_SCOPE_W = 1`** (lambda su tutte le partite) | **regge** | 3 leghe su 3, `z = −3.96`. Vedi *Ruolo o completo* |
| **Lo squilibrio della partita sui cartellini** | **regge** | AUC 0.562 → 0.593, stesso segno in tutte e cinque le leghe, `−5.8` sigma sul coefficiente comune, a costo zero. Vedi *Lo squilibrio e i cartellini* |
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

**Il `b22` ha separato i due muri, che erano stati trattati come uno solo.**

- **L'ordinamento** (AUC 0.51–0.57) è il muro vero e non l'ha mosso niente. Qui
  l'ipotesi ancora non testata è che manchi la *forma* della distribuzione dei tiri:
  dieci tiri da 0.10 xG e due da 0.50 danno lo stesso lambda ma distribuzioni di gol
  diverse. Servirebbe l'endpoint `/v1/matches/{id}/shots`, che dà ogni tiro con
  `expected_goals`, `is_on_target`, `is_inside_box`, `situation` e coordinate. Costa
  una chiamata in più per partita storica (da 4 a 5, +25% sul batch) ed è il candidato
  più serio rimasto. `sum_sot` funziona già come *proxy* grezzo della stessa
  informazione — i tiri in porta sono la coda buona della distribuzione dei tiri — ed
  è probabilmente per questo che è l'unica cosa che ha retto.
- **Il livello** (bias fino a −6.6 punti) è un problema diverso e quasi chiuso: tre
  ipotesi falsificate e una sola rimasta, già strumentata. Vedi *Il muro
  dell'Over/Under: tre ipotesi* e *La base di lega risponde alla domanda sbagliata*.

Tenerli separati non è pedanteria: il Brier li mescola, quindi una modifica che
sistema il livello e peggiora l'ordinamento (o viceversa) può sembrare neutra. Guarda
sempre **bias e AUC insieme**, e per lega.

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

## L'audit sistematico del `b19`: cosa è stato controllato e cosa è saltato fuori

Fatto prima di lanciare altri backtest, su richiesta di non lasciare niente al
caso. Tutti i controlli sono **script rieseguibili** nello scratchpad, non
letture a occhio.

### Cosa è stato controllato

| controllo | come | esito |
|---|---|---|
| campi API letti contro lo schema | incrocio col PDF di PitchAPI | il PDF è un estratto: inconcludente da solo |
| i 31 getter di `ADV_SPEC` | percorso `gruppo.campo` contro lo schema | **puliti** (i 5 segnalati erano annidati più a fondo) |
| copertura di ogni riga del CSV | 316 righe numeriche su 1133 partite | 27 segnalate, 23 costanti **attese** |
| scala previsto/reale, 137 metriche | rapporto delle medie | **3 rotte**, vedi sotto |
| scambio casa/trasferta | il previsto di casa correla di più col reale di casa o di trasferta? | **zero scambi** su 43 metriche |
| metriche non di squadra | reale identico fra casa e trasferta | **1 trovata**, vedi sotto |
| fallback irraggiungibili | variabile azzerata prima del suo `=== null` | **7 su 10 morti** |
| costanti duplicate nei due file | confronto tabella per tabella | **10 valori divergenti** |
| azzeramenti silenziosi `?? 0` / `\|\| 0` | 42 occorrenze passate in rassegna | 1 rischio reale sui punteggi |

### 1. I fallback che non scattavano mai

`aggregaTeam` azzerava i valori mancanti **prima** di provare le fonti
alternative:

```js
drib = zeroIf(drib, anyOk);                               // riga 1125: null -> 0
...
if (drib === null && d) drib = extractSafeStat(d, ...);   // riga 1144: mai vero
```

`zeroIf(v, ok)` trasforma `null` in `0` quando almeno una delle due chiamate è
andata a buon fine. Dopo quella riga `v === null` è **sempre falso**, quindi i
sette fallback su `/stats` (`xg_sp`, `cross`, `drib`, `thru`, `aer`, `misc`,
`disp`) erano codice morto. Quando `/advanced` non portava il campo, la media
storica della squadra veniva diluita con degli zeri.

Si vedeva nei dati e nessuno l'aveva letto: nel CSV il **previsto** stava allo
**0.63–0.64** del reale su esattamente quelle metriche —

| | previsto | reale | rapporto |
|---|---|---|---|
| Dribbling | 4.52 | 7.18 | 0.63 |
| Controlli sbagliati | 10.00 | 15.61 | 0.64 |
| Palle perse | 5.34 | 8.31 | 0.64 |

— perché il Comparatore, che non ha lo `zeroIf`, leggeva il valore giusto mentre
lo Scanner leggeva zero. **Corretto spostando `zeroIf` dopo i fallback**, e
insieme `_rawSnap`, così la card della copertura dice «abbiamo il valore» invece
di «l'ha dato `/advanced`».

### 2. La doppia verità sullo shrinkage

`CMP_DC_SHRINK_TABLE` nel Comparatore aveva **10 valori su 10 diversi** da
`STAT_SHRINK_TABLE` dello Scanner: erano i valori pre-`b5`, mai aggiornati dopo
la ritaratura su 1133 partite (`gca` 0.53 contro 0.31, `vaep_off` 0.55 contro
0.23, `xt` 0.63 contro 0.40…).

Vive in `cmpDcPredict`, che è un **percorso di riserva**: si accende solo se
l'hook non espone `__PRED_STATS`. Dal `b4` non dovrebbe mai succedere, ma se
succedesse il CSV conterrebbe previsioni fatte con costanti di due anni fa e
**nessuno se ne accorgerebbe**. Ora `cmpDcPredict` usa la tabella del motore
quando c'è, il percorso di riserva si annuncia nel log, e il CSV esporta
`Origine metriche avanzate` (`motore` / `riserva-k-motore` / `riserva-k-locali`).

### 3. Le metriche che non erano di squadra

`aerials` aveva il **valore reale identico fra casa e trasferta nel 100% delle
partite**: `defending.aerials` è il numero di duelli aerei *della partita*, una
quantità condivisa. `predictStat` ci calcolava sopra `mine` e `conc` che erano lo
stesso numero, cioè `lg · sh(r)²` sulla stessa cosa contata due volte.

Corretto in `defending.aerials_won`, che è una metrica di squadra vera.

> **E la correzione era a metà: il `b22` l'ha finita.** `ADV_SPEC` nello Scanner era
> stato sistemato, `CMP_NEW_SPEC` nel Comparatore **no** — era rimasto su
> `defending.aerials`. Quindi per tre build il CSV ha confrontato una previsione di
> squadra (14.51 duelli vinti) con una quantità di partita (28.41 duelli totali):
> rapporto **0.511**, e reale identico fra casa e trasferta in **1132 partite su
> 1132**. Il difetto sembrava corretto e non lo era. Vedi *Il controllo
> dell'idraulica* e la trappola «una correzione applicata in un file va applicata in
> tutti e due».

**Due cose restano da rifare:** il suo `k` (0.54, tarato sulla quantità condivisa) e
la riga `aerials t=+2.4` nella sezione della Progressione Storica, che misurava
un volume di partita e non una forma di squadra. Nessuna delle due si poteva fare
prima del `b22`, perché fino ad allora il CSV non esportava il valore giusto.

### 4. I punteggi nulli

`computeLeagueParams` ed `estimateRho` facevano `m.score_home ?? 0`: una partita
marcata `finished` senza punteggio veniva contata come **0-0**, abbassando la
media di lega. Ora quelle partite si saltano.

### Cosa è risultato sano

- **Nessuno scambio casa/trasferta** in 43 metriche: il previsto di casa correla
  sempre di più col reale di casa. La sola eccezione apparente era `aerials`, ed
  era il sintomo del punto 3.
- **`ADV_SPEC` è pulito**: tutti i percorsi `gruppo.campo` esistono.
- **L'emivita del decadimento è 106 in entrambi i file.**
- Le 23 righe costanti nel CSV sono tutte attese (i `k`, i pesi, `alpha` a zero
  perché la correzione residuale è spenta, la baseline del possesso a 50).

### Cosa resta scoperto, e va detto

- **`cross`, `thru`, `aer` non sono esportati dal Comparatore**, quindi nessun
  backtest li ha mai verificati. Alimentano solo la card dello stile d'attacco e
  il prompt.
- Il rapporto previsto/reale di `vaep` (0.87) e `pv` (0.88) resta sotto 1 senza
  una spiegazione trovata: sono le due metriche di tipo `additivo`, e vanno
  guardate quando si riprende in mano quel tipo.
- Il PDF di PitchAPI in `scratchpad/pitch.txt` è un **estratto parziale**: non
  elenca tutte le chiavi, quindi «non nello schema» non vuol dire «non esiste».
  L'unico controllo che vale è la copertura reale nei CSV.

### Il secondo giro, e cosa resta davvero scoperto

Alla domanda «sei sicuro che non ce ne siano altri?» la risposta onesta è **no**.
Un audit copre le *classi* di errore che sa cercare. Ecco cosa è stato aggiunto
al secondo giro e, soprattutto, cosa **non** è stato controllato.

**Controllato al secondo giro, e risultato sano:**

- **Fuga di dati dal futuro.** Ogni ciclo su liste di partite nei due file: tutti
  hanno il taglio `< targetTimeMs` entro le righe adiacenti. Nessuna fuga.
- **Ordinamento della serie Elo.** `series[t].unshift(...)` mette il più recente
  in testa, e `calcTrend` fa `slice(0,5)` meno `slice(5,15)`: coerente.
- **Allineamento del CSV.** Ogni riga dati ha `1 + 4·N` colonne, nessun campo
  contiene il separatore. Le tre righe di larghezza diversa sono intestazioni.
- **Tipi delle metriche.** Le quattro `additivo` sono esattamente le coordinate e
  i valori con segno (`avg_x`, `avg_def_x`, `vaep`, `pv`).
- **`ADV_SPEC`**: nessuna chiave duplicata, nessuna coppia di metriche che legge
  lo stesso campo.
- **`statShrinkFor`** torna sempre un `k` in `(0,1]`, e il default su una chiave
  inventata è 0.50.
- **La verità di riferimento.** I 1743 verdetti di ogni mercato ricalcolati dal
  punteggio: **corretti**. I 26 apparenti disaccordi stanno tutti esattamente a
  `p = 55,0%`, cioè al confine della soglia di giocabilità: il CSV scrive le
  probabilità a **un decimale**, quindi «55,0%» può essere un 54,96% che il
  motore giustamente non considera giocabile. Errore del controllo, non del
  motore — ma va saputo che **ogni analisi fatta su quelle colonne ha ±0.05 punti
  di quantizzazione**.

**Trovato al secondo giro:** `f3_entries` aveva un `k` tarato (0.29) che non
veniva mai usato, perché la metrica non aveva un «concesso» e quindi non era in
`STAT_PAIRS`: `predictStat` restituiva la sola media della squadra, senza il
termine avversario. Aggiunto `opp_f3_entries` seguendo il pattern delle altre
otto metriche orfane. Le coppie passano da 57 a 58.

**Sette metriche non hanno un `k` tarato** e usano il default 0.50: `gf`,
`direct_speed`, `seq_time`, `avg_x`, `cp_regains`, `rec_time`, `xg_sp`. Non è un
errore, ma non è nemmeno una scelta: nessuno le ha mai misurate.

### Cosa NON è stato controllato

Detto esplicitamente, perché un elenco di controlli superati fa credere che il
resto sia a posto:

- ~~**L'Ordered Logit** nei suoi parametri~~ — **fatto nel `b20`**, ed erano
  sbagliati: le soglie sono state ristimate su 1743 partite e validate
  leave-one-league-out. **Markov resta non verificato** nei suoi parametri: solo
  invarianti (le probabilità sommano a 1, la simmetria).
- **Le rette di calibrazione della confidence**, stimate su 6824 partite in un
  contesto che non conosciamo.
- **Il percorso di rendering della UI** oltre alla presenza degli id: nessuno ha
  verificato che ogni numero a schermo sia quello che il motore ha calcolato.
- **Il mega-prompt**, che è testo generato e non è mai stato riletto contro i
  valori che cita.
- **I casi numerici estremi**: lambda molto alti o molto bassi, squadre con
  pochissime partite, leghe con meno di 30 partite in archivio.
- **Le cinque metriche che il Comparatore non esporta** (`cross`, `thru`, `aer`,
  `seq_time`, `xg_shot`): il motore le prevede, nessun
  backtest le ha mai viste. Scoperto nel `b22` contando cosa finisce davvero nel CSV
  (43 metriche) contro cosa il motore calcola. `pass_acc`, `ht` e `xg_op` stavano in
  questo elenco per errore: non le prevede nessuno, vedi la sezione qui sotto.
- **Il comportamento con dati parziali dell'API**: cosa succede se `/advanced`
  manca per metà delle partite di una squadra, ora che i fallback funzionano.

Ognuno di questi è una classe che, se contiene un errore, l'audit fatto finora
non lo vedrebbe.

## L'audit del documento: quattro cose che AGENTS.md diceva e il codice smentisce

Gli audit del `b19` e del `b22` hanno guardato il codice contro se stesso. Questo
ha guardato il **documento contro il codice**, voce per voce, ed è una classe di
errore che nessuno dei controlli precedenti poteva trovare: un file che descrive
un motore diverso da quello che gira non rompe niente, manda fuori strada chi lo
legge. Le quattro trovate qui sotto sono state corrette nel testo dove comparivano;
questa sezione tiene il conto di cosa è stato verificato e come.

**Cosa è stato ricontrollato, e ha retto.** Non è aria: sono i controlli del `b19`
e del `b22` rifatti sul sorgente di oggi.

| controllo | esito |
|---|---|
| sintassi dei due file (`node --check` sul JS estratto) | OK |
| i cinque agganci testuali del Comparatore | 5 su 5 fanno presa |
| build allineate (`__SCANNER_BUILD`, `_bComp`, i due badge `#build-ver`) | tutte `0905-b22` |
| i nomi cercati da `exposeNames` esistono nel motore | 21 su 21 |
| **A** — fallback irraggiungibili (`zeroIf`/`keepNull` poi `=== null`) | zero |
| **E** — `ADV_SPEC` contro `CMP_NEW_SPEC` e `CMP_ADV_KEYS` | 31 chiavi comuni, stesso campo, stesso ordine |
| **F** — ogni chiave letta dal CSV è esposta dall'hook | zero orfane |
| **G** — etichette di riga del CSV duplicate | 81 etichette, zero duplicati |
| ogni id scritto da `safeTxt`/`safeHtml` esiste nel DOM | zero mancanti |
| le costanti del motore contro quelle scritte qui | tutte coincidono (vedi sotto) |
| invarianti dei mercati, ricalcolati fuori dal motore | tutti veri (vedi sotto) |
| `predictStat` su tutte e 58 le coppie di `STAT_PAIRS` | mai `null`, mai non finito |
| giro completo del motore su dati sintetici, in Chromium | zero errori, zero `NaN` a schermo |

Le costanti verificate una per una contro il sorgente: `ENS_W` 0.70/0.30/0.00,
`ENS_SCOPE_W` 1, `SHRINK_K` 4, `SHRINK_LAM_K` 3, `RESID_ALPHA` 0,
`GOALS_UNIT_FIX` 0, `LEAGUE_HALFLIFE_DAYS` 0, `ELO_1X2_W` 0.75, `GOALS_SOT_W`
0.50, `SOT_PER_GOAL` 3.25, `GOALS_SOT_CAP` 0.20, `OL_BETA/T1/T2`
2.056/−0.475/+0.671, `CARDS_ELO_B` −0.0035 con cap 0.30, le tre tabelle `MARKET_*`,
le due rette della confidence, l'emivita 106 in tutti e due i file, e le 51 voci di
`STAT_SHRINK_TABLE`. **Una sola non torna**: `RESID_GAMMA`, che nel codice è ancora
0.678 mentre il `b5` aveva misurato 0.360 (vedi *Il caso della correzione
residuale*).

Gli invarianti, ricalcolati fuori dal motore su quattro coppie di lambda: la
matrice somma a 1; `p1+pX+p2` fa 1; l'handicap asiatico somma a 1 su tutte le
tredici linee da −1.5 a +1.5, è monotono, e AH −0.5 coincide con `p1` e AH +0.5
con `p1+pX` fino all'ultima cifra; le fasce multigol disgiunte sommano a 1; le
probabilità Over decrescono al salire della linea; il Markov somma a 1 e dista al
massimo 0.018 dal Dixon-Coles.

### Il campione di ruolo è un sottoinsieme, e il documento diceva di no

La più grossa, e vale la pena capire perché è sopravvissuta tanto.

Il codice fa questo, e lo ha sempre fatto in tutta la storia del repository (è così
già nel primo `Add files via upload`):

```js
let overallMatches = past.slice(0, limit);
let roleMatches = overallMatches.filter(m => (m.home_team.id === teamId) === isHomeTeamUI);
const roleLimit = roleMatches.length;   // dichiarata e mai usata
```

Cioè `role` è **quello che c'è dentro le ultime `limit` partite**, non le ultime
`limit` in casa. Misurato facendo girare il motore su un campionato sintetico da 18
squadre: con `limit = 15`, `dH.role.n = 8` e `dA.role.n = 8`.

AGENTS.md sosteneva il contrario in **due punti**, e uno dei due era la trappola
numero 6 dell'elenco *Trappole già corrette*, che descriveva esattamente questo
comportamento («con 15 restavano ~7 gare») dandolo per **corretto**. Entrambi
riscritti.

`roleLimit`, assegnata e mai letta, è la traccia di una versione in cui il ruolo
aveva un limite proprio: nel file pre-ripulitura ci sono due commenti che parlano
di «`roleLimit=20`» e «`roleLimit=12`» come di una configurazione. Quella versione
non è mai arrivata nel v9.7 di questo repository.

**Cosa cambia nei conti, se qualcuno «lo sistema».** Non è una riga cosmetica:
`nHr` e `nAr` entrano in due shrinkage.

| | con `role` sottoinsieme (oggi) | con `role` indipendente |
|---|---|---|
| partite di ruolo a `limit = 15` | 8 | 15 |
| `wS = n/(n+SHRINK_LAM_K)` con `k = 3` | 0.73 | 0.83 |
| `shrink(x, n, SHRINK_K)` con `k = 4` | 0.67 | 0.79 |

Cioè oggi i lambda di ruolo sono tirati verso la media di lega del **27%**, e
sarebbero tirati del 17%. Ogni costante tarata finora — `SHRINK_LAM_K`, le tre
`MARKET_*`, il `sampleFactor` dei narrativi — è stata scelta su un campione di
ruolo di ~8 partite. **Non toccare la riga senza un backtest**: è una modifica al
motore travestita da correzione di un refuso, ed è esattamente la forma che il
punto 2 di *Le costanti messe a mano* chiama «una stima invecchia quando cambia
ciò che sta a monte».

Se e quando si vuole misurare, la strada è quella canonica: esporre
`window.ROLE_SCOPE_INDEPENDENT` con default 0 (comportamento di oggi), esportare
`dH.role.n` e `dA.role.n` nel CSV, e far decidere un backtest. Va messo in conto
che a 1 il `fetchSet` cresce da ~15 a ~22 partite per squadra, cioè **il 50% di
chiamate in più**.

### Otto variabili che leggono il payload e non arrivano da nessuna parte

In `aggregaTeam`, dentro il ramo `if (myAdv)`, otto variabili vengono riempite dal
payload `/advanced` e poi **non entrano in `matchDetails`**: `pass_acc`, `ht`,
`pps`, `build_att`, `dir_att`, `centr`, `box_entries`, `xg_op`. Non finiscono in
`out.vals`, non passano da `calcFeatures`, non compaiono a schermo, non stanno nel
CSV. Sono lette e buttate.

Non fanno danno — costano un accesso a un oggetto già in memoria — ma tre di loro
(`pass_acc`, `ht`, `xg_op`) erano elencate in questo documento fra le «metriche che
il motore prevede e mostra, ma che nessun backtest ha mai visto». Non è vero: il
motore non le prevede affatto. Chi fosse partito da quella riga per aggiungerle al
CSV avrebbe cercato per mezz'ora una previsione che non esiste.

Insieme a queste, il linter segnala morti anche `getTopScorersPlain` (mai chiamata,
nemmeno da un `onclick`), `xgSpH`/`xgSpA` (soppiantate da `_xgSpFallback`),
`predH`/`predA`, `nMinRole`, `STAT_SHRINK` e la già citata `roleLimit`. `lamH_mix`
e `lamA_mix` sembrano morte al linter ma **non lo sono**: le legge l'hook del
Comparatore, che è testo iniettato e il linter non vede.

### Due copie della stessa riga, di nuovo

`_calibConf1X2` è scritta **due volte, identica**, in `comparatore.html`. Oggi
coincidono; è la forma esatta del caso `CMP_DC_SHRINK_TABLE` descritto in
*Trappole*, e la prossima ritaratura delle rette della confidence ne aggiornerà
una sola. Vale la stessa cura: una sola verità, letta da `window.*` del motore.

### `aer` e `aerials` sono ormai la stessa cosa

Dopo la correzione del `b19`, `ADV_SPEC.aerials` legge
`defending.aerials_won ?? duels.aerials_won`. La variabile `aer`, raccolta a parte
per la card a schermo, legge **gli stessi due campi nello stesso ordine**. Prima
del `b19` erano due quantità diverse (duelli della partita contro duelli vinti);
ora sono lo stesso numero sotto due chiavi. Non è un bug, ma quando si rifarà il
`k` di `aerials` conviene togliere il doppione invece di ritarare due volte.

## La lega che non arrivava mai: il bug che invalida le tarature

**Leggere prima di fidarsi di qualunque costante di questo repository.**

Trovato nel `b18` guardando la diagnostica del `b17`: `LG.avgH` valeva **1.500** e
`LG.avgA` **1.200** in tutte e 1133 le partite del backtest, **in ogni lega**. Non
sono medie: sono i valori di ripiego scritti in `computeLeagueParams`.

### Il meccanismo

Il Comparatore passa la lega al motore così:

```js
const setV = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
setV('sel-league', lId);
```

ma il suo `<select id="sel-league">` **non ha nessuna `<option>`**. Assegnare un
valore a una `<select>` che non contiene quell'opzione è un no-op silenzioso: il
DOM lascia `value` a `""`. Quindi nel motore `lId === ''`, e:

| funzione | guardia | effetto con lega vuota |
|---|---|---|
| `computeLeagueParams` | `m.league_id !== leagueId → continue` | scarta tutto, `n = 0`, **ripiega su avgH 1.50 / avgA 1.20** |
| `estimateRho` | idem | scarta tutto, **ripiega su rho −0.11** |
| `buildGlobalElo` | `if (_chosenLeagueId && ...)` | la guardia **si spegne**, l'Elo usa tutta la cache e funziona |

Quell'`&&` è la ragione per cui l'Elo era l'unica cosa che batteva il modello: era
l'unico pezzo che riceveva i dati veri.

**Lo Scanner in produzione non ha il problema**: popola le sue `<option>` con
`lSel.add(new Option(l.name, l.id))`, quindi `lId` è un id vero e le medie di lega
si calcolano. Il bug era **solo nel banco di prova** — che è quasi peggio, perché
significa che ogni costante è stata tarata contro un modello azzoppato.

### Cosa invalida

Ogni backtest fino al `b17` compreso ha misurato un motore con **2.70 gol a
partita e rho −0.11 fissi per tutte le leghe**. Vanno quindi riviste, in ordine di
esposizione:

- **La diagnosi del `b17` sul disallineamento di unità.** `attH = npxg / LG.avgH`
  con `LG.avgH` bloccato a 1.50: il deficit del lambda in Bundesliga (−8.8%, la
  lega da 3.25 gol) si spiega molto meglio con la base a 2.70 che col rapporto
  NPxG/gol. **La sezione va riletta come sospetta**, e `GOALS_UNIT_FIX` non va
  acceso finché non si rimisura con la lega vera.
- **Il livello dell'Over 2.5** (−3.8 punti) e la sovrastima del pareggio: stessa
  causa probabile.
- **`SOT_PER_GOAL`, `MARKET_PER_GOAL`**, che sono ancorati a `LG.avgH + LG.avgA`:
  tarati contro un ancoraggio sbagliato.
- **`MARKET_SHRINK_K`, `MARKET_BASE_SHRINK`, `GOALS_SOT_W`, `CARDS_ELO_B`**:
  tarati su previsioni che partivano da una base sbagliata.

Meno esposte, perché costruite su quantità che il bug non toccava: **`ELO_1X2_W`**
(l'Elo riceveva i dati giusti) e **`STAT_SHRINK_TABLE`** (`predictStat` usa
`_base`, non `LG`).

### La correzione

`setV` ora crea l'`<option>` mancante prima di assegnare, verifica che il valore
sia attecchito e **ferma il batch** se la lega non arriva al motore, invece di
produrre 1743 righe di risultati silenziosamente sbagliati. Il CSV esporta anche
`Unita: partite di lega usate` (`LG.n`) e `Unita: rho stimato`: se `LG.n` è 0, il
motore sta ripiegando e si vede a colpo d'occhio.

### La lezione

Un valore di ripiego **plausibile** è più pericoloso di un errore. 1.50 e 1.20
sono numeri ragionevoli per il calcio: non hanno fatto scattare nessun allarme per
sedici build. Un fallback deve essere **osservabile** — o esporre quante
osservazioni l'hanno prodotto, o essere abbastanza assurdo da non passare
inosservato.

## L'ensemble 1X2: l'Ordered Logit contava il vantaggio casa due volte

Domanda posta al `b20`: *e se togliessimo l'Ordered Logit? E se il problema fosse
la divisione per ruolo?* Sono due domande diverse e hanno due risposte diverse.

### Il difetto: la casa contata due volte

L'Ordered Logit del motore è un modello ordinale su una sola variabile:

```
x   = olH - olA           con olH = 0.7·NPxG(casa, ruolo) + 0.3·NPxGA(trasferta, ruolo)
y   = beta · x
p2  = sig(T1 - y)         pX = sig(T2 - y) - p2         p1 = 1 - sig(T2 - y)
```

`NPxG` è preso con lo scope **ruolo**: per la squadra di casa i suoi numeri *in
casa*, per l'ospite i suoi *in trasferta*. Quindi `x` **contiene già** il vantaggio
del campo. Misurato invertendo le probabilità esportate da 1743 backtest:

```
x = olH - olA   media +0.1955   sd 0.2914   (5°-95° da -0.260 a +0.679)
```

Ma le soglie erano `T1 = -0.850, T2 = +0.350`, cioè una banda di pareggio centrata a
**-0.250**: anche a parità di `x` il modello dava la casa favorita. Le due cose
spingono nello stesso verso e il vantaggio casa finiva **contato due volte**.

Si vedeva nei backtest, e in tutte e cinque le leghe:

| | bias su `1` | logloss | pick |
|---|---|---|---|
| Dixon-Coles | +1.6 | 1.0098 | 51.4% |
| Markov | +1.1 | 1.0091 | 51.5% |
| **Ordered Logit** | **+6.8** | **1.0397** | **48.1%** |
| ensemble `b19` (0.6/0.3/0.1) | +0.3 | 1.0115 | 51.5% |

Il bias sull'`1` era positivo in tutte e cinque (+7.4 Bundesliga, +1.4 LaLiga,
+7.4 Ligue 1, +8.3 Premier, +9.7 Serie A) — non è rumore di una lega.

### La correzione, e come è stata validata

Le probabilità dell'OL sono invertibili esattamente (`p1` e `p2` danno due stime di
`y` che concordano allo 0.0016 mediano, cioè alla quantizzazione del CSV), quindi
`x` si recupera e i parametri si ristimano per massima verosimiglianza:

```
beta 1.950 -> 2.056     T1 -0.850 -> -0.475     T2 +0.350 -> +0.671
centro della banda di pareggio: -0.250 -> +0.098
```

Ora le soglie **sottraggono** un po' di vantaggio casa, perché `x` ne fornisce già
in eccesso. Validato **fuori campione** (si stima su quattro leghe, si misura sulla
quinta): bias sull'`1` da **+6.8 a -0.1**, logloss da **1.0397 a 1.0270**, pick da
**48.1% a 49.9%**. Migliora in quattro leghe su cinque; peggiora in LaLiga, dove il
bias era già solo +1.4 perché il vantaggio casa spagnolo è più piccolo.

### Ma sull'ensemble non cambia niente, ed è questa la notizia

| | logloss ensemble | pick |
|---|---|---|
| `b19` | 1.0115 | 51.5% |
| solo OL ristimato | **1.0114** | 51.9% |
| solo pesi ripesati | **1.0102** | 51.3% |
| tutti e due | 1.0103 | 51.5% |

Sistemare l'OL sposta l'ensemble di **0.0001**. Il motivo è che l'OL è guidato
dallo *stesso* NPxG del Dixon-Coles: aggiustarlo lo rende un modello migliore da
solo, non un componente più utile.

La scelta dei pesi fatta **fuori campione** (griglia cercata su quattro leghe,
misurata sulla quinta) mette l'Ordered Logit a **0.00** in quattro fold su cinque,
e a 0.10 nel quinto; il peso di Markov sale a 0.30. Quindi il `b20` spedisce
`ENS_W = { dc: 0.70, mk: 0.30, ol: 0.00 }`.

**L'OL resta calcolato e mostrato** (la card dei modelli e il mega-prompt lo
citano) ma **con le soglie giuste**, perché un componente a schermo che dice 52%
di `1` dove la verità è 45% è una bugia anche se non entra nel conto.

Va detto con onestà quanto vale: `-0.0013` di logloss con `z = -2.03`, e una lega
su cinque che va nell'altro verso. È al bordo del rumore. Non è il miglioramento
che i sei mercati aspettano — è pulizia.

## Ruolo o completo: la domanda giusta, e la risposta è «completo» (per l'1X2)

L'altra ipotesi — *«magari è la divisione per ruolo che ci frega»* — è ragionevole:
con una finestra di 15 partite lo scope `role` ne lascia ~7, e la media di 7 ha
il 40% di errore standard in più di quella di 15. In cambio compra la differenza
casa/trasferta **della singola squadra**, che la letteratura dice essere quasi
tutta rumore (il vantaggio casa vero è già in `LG.avgH`/`LG.avgA`).

### Quello che i dati di oggi possono dire

Il CSV non esportava il blocco completo, ma esportava l'**A/B su `SHRINK_K`**: `k`
alto tira i rapporti attacco/difesa verso 1, cioè crede **meno** ai numeri del
ruolo. È il più vicino che i dati esistenti hanno alla domanda.

| `SHRINK_K` | logloss 1X2 | pick | Brier Over 2.5 |
|---|---|---|---|
| 4 | **1.0115** | **51.5%** | 0.2469 |
| 12 | 1.0137 | 51.1% | 0.2463 |
| 28 | 1.0161 | 50.5% | 0.2462 |

Sull'**1X2 il ruolo si guadagna il posto**: credergli meno peggiora, in modo
monotono, **in tutte e cinque le leghe**. Sull'**Over 2.5** va nell'altro verso, ma
il segnale non regge il test: `z = -1.57` e `-1.08` sulla differenza appaiata, e il
guadagno viene quasi tutto dalla Premier. Peggio: quei backtest sono **pre-`b18`**,
con la media di lega congelata a 1.50/1.20, quindi «tirare verso la media» tirava
verso 2.70 — giusto per caso in Serie A (bias `-2.2 -> +1.5`) e sbagliato in
Bundesliga (`-8.7 -> -9.0`). **Quel confronto è contaminato e non va usato.**

Storia coerente, ma non ancora dimostrata: il ruolo serve dove conta
l'**asimmetria** (1X2), e disturba dove conta solo il **totale** (Over/Under).

### Come il `b20` la chiude in un backtest solo

Il motore calcolava già `probsOver` e `mk_ov` — Dixon-Coles e Markov sui lambda di
*tutte* le partite — e li mostrava a schermo senza usarli. Ora l'ensemble è scritto
come due blocchi identici per forma:

```
RUOLO    = 0.70·probsRole + 0.30·mk_ro
COMPLETO = 0.70·probsOver + 0.30·mk_ov
core     = (1 - ENS_SCOPE_W)·RUOLO + ENS_SCOPE_W·COMPLETO
finale   = (1 - ENS_W.ol)·core + ENS_W.ol·probsOL
```

Nel `b20` `ENS_SCOPE_W` partiva da 0 — il comportamento di prima — perché nessuno
l'aveva ancora misurata. Il CSV esporta `DCover 1/X/2`, `MKover 1/X/2`, `DCover GG`,
`DCover Over 2.5` e i quattro lambda dei due ambiti, così **un solo backtest
ricostruisce ogni valore fra 0 e 1** senza rilanciare il motore — lo stesso schema di
`GOALS_SOT_W`. Il backtest è arrivato subito dopo, e ha risposto: vedi qui sotto.

### La risposta: il completo vince, ed è il primo guadagno sopra il rumore

Backtest `b20` su **1133 partite** (Serie A, Premier, LaLiga 2025/26), con i due
blocchi esportati separati.

| `ENS_SCOPE_W` | logloss | pick | LaLiga | Premier | Serie A |
|---|---|---|---|---|---|
| **0.00** (solo ruolo) | 1.0113 | 50.9% | 0.9899 | 1.0324 | 1.0114 |
| 0.25 | 1.0101 | 51.1% | 0.9894 | 1.0309 | 1.0099 |
| 0.50 | 1.0090 | 51.1% | 0.9891 | 1.0294 | 1.0085 |
| 0.75 | 1.0080 | 51.1% | 0.9888 | 1.0280 | 1.0071 |
| **1.00** (solo completo) | **1.0071** | **51.4%** | 0.9886 | 1.0267 | 1.0059 |

Monotono fino al bordo **in tutte e tre le leghe**, senza eccezioni. Sulla
differenza appaiata: `z = -4.28` a 0.50, `z = -3.96` a 1.00. La scelta fuori
campione (`s` cercato su due leghe, misurato sulla terza) prende **1.0 in tutti e
tre i fold**, e l'aggregato passa da 1.0113 a 1.0071.

Per scala: la ritaratura dei pesi del `b20` valeva `-0.0013` con `z = -2.03`, e la
correzione dell'Ordered Logit `-0.0001`. Questo vale **`-0.0042` con `z = -3.96`**.
È tre volte più grande e molto più solido. **`ENS_SCOPE_W` va a 1 nel `b21`.**

L'intuizione dietro era giusta: con una finestra di 15 partite lo scope `role` ne
lascia ~7, e quello che compra — la differenza casa/trasferta *della singola
squadra* — vale meno del rumore che aggiunge. Il vantaggio casa vero sta già in
`LG.avgH`/`LG.avgA`, che sono di lega e stimati su ~1000 partite.

**Ma vale solo per l'1X2.** Sui mercati gol il confronto non ha un vincitore:

| | Over 2.5 bias | Over 2.5 AUC | GG bias | GG AUC |
|---|---|---|---|---|
| ruolo, LaLiga / Premier / Serie A | −1.5 / −6.6 / −2.0 | 0.573 / 0.513 / 0.522 | −5.8 / −4.7 / +2.8 | 0.514 / 0.535 / 0.553 |
| completo | −2.1 / −8.8 / −3.2 | 0.595 / 0.517 / 0.506 | −6.5 / −6.7 / +1.6 | 0.543 / 0.532 / 0.532 |

Il completo ordina meglio in due leghe su tre ma **peggiora la calibrazione
ovunque**. Quindi `dcMat` resta `dcRole`: l'1X2 passa al completo, i gol no. La
divisione è deliberata ed è scritta nel commento della costante, perché è il tipo
di asimmetria che qualcuno "sistema" in buona fede fra sei mesi.

### Il paradosso della Premier, e come mi ha portato fuori strada per una build

Nello stesso file c'era un fatto che non tornava:

| lega | base di lega usata | gol reali 25/26 | scarto | bias Over 2.5 |
|---|---|---|---|---|
| LaLiga | 2.637 | 2.698 | −2.3% | −1.5 |
| **Premier** | **3.041** | **2.754** | **+10.4%** | **−6.6** |
| Serie A | 2.548 | 2.426 | +5.0% | −2.0 |

In Premier il motore parte da una base di lega **del 10% più alta** del vero, e
nonostante questo l'Over 2.5 esce **6.6 punti troppo basso**. Da qui ho concluso che
un errore di livello non potesse produrlo, e che dovesse esserci qualcosa che
**stringe la distribuzione** — con `rho` come primo indiziato.

**Era sbagliato, e vale la pena lasciarlo scritto insieme all'errore.** Il `b22` ha
mostrato che `rho` non sposta niente (+0.0 punti) e che il lambda **è inversamente
proporzionale** alla base:

```
lamH = LG.avgH · (npxg_H / LG.avgH) · (npxga_A / LG.avgH)   →   lamH ∝ 1 / LG.avgH
```

Una base troppo alta **abbassa** il lambda, non lo alza. Il paradosso non era un
paradosso: era il segno che avevo assunto la direzione sbagliata senza scrivere la
formula. Con la formula davanti, la Premier è il caso *previsto*, non l'anomalia.

**La lezione**: prima di dedurre da un segno, scrivi la relazione. Bastavano tre
simboli e avrei saltato una build. Vedi *Il muro dell'Over/Under: tre ipotesi* per la
falsificazione e *La base di lega risponde alla domanda sbagliata* per la conclusione.

### L'etichetta di lega letta dal DOM: 59-88% delle righe sbagliate

Trovato controllando i numeri per lega di questo stesso backtest, e va raccontato
perché è la classe di bug più pericolosa che ci sia: **non rompe niente, sposta le
conclusioni**.

`cmpBuildResult` scriveva la lega così:

```js
const _lgSel = document.getElementById('cmp-league');
const _lgName = _lgSel.selectedOptions[0].text;   // <- la dropdown ADESSO
const ids = { league: _lgName, ... };
```

cioè il testo **attualmente selezionato nella dropdown**, non la lega della
partita. Finché si lavora su una lega sola coincidono. Ma `cmpUpdateLeagues()`
svuota il menu a `'-- --'` a ogni cambio di paese, e in un archivio multi-lega
l'etichetta finiva su partite di un'altra lega. Nei tre export del 06/09:

```
confini VERI (dai nomi delle squadre):   378 -> Premier,  756 -> LaLiga
confini della colonna LEGA:               84 -> '-- --',   88 -> Premier,  381 -> LaLiga
righe con etichetta sbagliata: 669 su 1133 (59%), e 88% nei file da 756
```

Partite di Serie A etichettate «Premier League», partite di Premier etichettate
«LaLiga». **Tutti i CSV precedenti al 06/09 sono puliti** (verificato riconoscendo
la lega dai nomi delle squadre su ognuno dei 25 file: zero errori), quindi le
misure delle build da `b11` a `b20` reggono — ma questo è un caso, non una
garanzia.

Corretto risolvendo il nome **dall'id della partita**, con `cmpLeagues` che è la
lista completa e copre anche le leghe di un altro paese:

```js
const _lgById = cmpLeagueName(match.league_id || cmpCurrentLeagueId);
league: _lgById || _lgName          // la dropdown solo come ultima rete
```

E, perché non ricapiti in silenzio, l'export ora **dichiara la composizione del
file** nel log (`Serie A 378 · Premier League 378 · LaLiga 377`) e segnala ogni id
di lega che non ha trovato un nome.

**La trappola generale**: *un valore preso dal DOM è una lettura fatta a un certo
istante, non un dato della cosa che stai descrivendo.* Se il valore appartiene a
un'entità (una partita, una lega, una stagione), va letto da quell'entità. Il DOM
è stato già la causa del bug del `b18` (`sel-league` senza `<option>`) e ora di
questo: due volte lo stesso errore di categoria in tre build.

**Come accorgersene senza fortuna**: quando un file raggruppa per una chiave, la
chiave va **verificata contro qualcosa di indipendente**. Qui i nomi delle squadre
davano la lega senza bisogno della colonna, e il controllo è tre righe di codice.
Ogni CSV nuovo va passato da lì prima di analizzarlo per lega.

### Un bug trovato mentre si guardava lì

`goalsSotCorrection` restituisce una **scala**, cioè un rapporto contro il *proprio*
totale. La scala calcolata sul totale del ruolo veniva applicata **anche** ai lambda
completi:

```js
const _GC = goalsSotCorrection(dH, dA, lamH_role + lamA_role);
lamH_role *= _GC.scale;  lamA_role *= _GC.scale;
lamH_over *= _GC.scale;  lamA_over *= _GC.scale;   // <- sbagliato
```

Invece di portare i lambda completi verso la stima dai tiri, li portava verso il
totale **del ruolo**. Finché il blocco completo restava fuori dall'ensemble era solo
un numero storto a schermo; ora che può entrarci, è un difetto vero. Corretto con un
`_GCo` calcolato su `lamH_over + lamA_over`.

**Trappola generale**: una correzione espressa come *rapporto contro una baseline*
non è trasportabile su una baseline diversa. Se `f(lam)` torna `scale`, applicare
`scale` a un `lam'` diverso non è un'approssimazione, è un'altra cosa. È lo stesso
errore di forma della `_base` di coppia (vedi *La baseline di coppia*), scoperto due
build più tardi in un punto diverso.

## Il muro dell'Over/Under: tre ipotesi, tutte falsificate coi dati già in mano

Il `b21` metteva `rho` in cima alla coda come «la prima ipotesi falsificabile». Si è
rivelata falsificabile davvero, e falsa. Le tre che seguono sono state chiuse
riproducendo la matrice fuori dal motore sul backtest di 1133 partite, senza
rilanciare niente.

**La riproduzione è esatta.** `calcDCMatrix` + `probsFromMatrix` riscritti in Python
sui lambda che il CSV esporta: scarto mediano dal `pOv` del motore **0.00025**, massimo
0.00074, cioè la sola quantizzazione a una cifra decimale del file. Quello che segue si
può leggere con fiducia.

### 1. `rho` non c'entra niente

| lega | rho | Over 2.5 | con `rho = 0` | reale |
|---|---|---|---|---|
| LaLiga | −0.001 | 48.6% | 48.6% | 50.1% |
| Premier | −0.022 | 48.4% | 48.4% | 55.0% |
| Serie A | −0.043 | 43.8% | 43.8% | 45.8% |

**Spegnere `rho` sposta l'Over 2.5 di +0.0 punti in tutte e tre le leghe.** Il
ragionamento («un rho negativo gonfia 0-0 e 1-1 e toglie massa sopra le 2.5») è giusto
in linea di principio ma quantitativamente irrilevante: `rho` stimato vale fra −0.001 e
−0.043, e la correzione di Dixon-Coles tocca quattro celle di una matrice 11×11. Sul GG
sposta al massimo 0.5 punti. **Ipotesi morta.**

### 2. Non è sovradispersione. È il contrario

| lega | media | varianza | var/media |
|---|---|---|---|
| LaLiga | 2.698 | 2.291 | **0.849** |
| Premier | 2.754 | 2.466 | **0.895** |
| Serie A | 2.426 | 2.366 | **0.975** |

Il totale gol è **sotto**disperso rispetto a Poisson, non sopra. L'idea che serva una
distribuzione a coda più grassa è sbagliata di segno.

### 3. Con il livello giusto, non resta niente di significativo

A = il lambda del motore, B = lo stesso modello col lambda riscalato ai gol veri della
lega, C = la realtà:

| lega | A | B (livello giusto) | C reale | A→B | B→C |
|---|---|---|---|---|---|
| LaLiga | 48.6% | 50.3% | 50.1% | +1.6 | **−0.2** |
| Premier | 48.4% | 51.8% | 55.0% | +3.3 | +3.3 |
| Serie A | 43.8% | 43.6% | 45.8% | −0.2 | +2.2 |

In LaLiga il livello chiude **tutto**. In Premier ne chiude la metà, in Serie A niente —
ma su 378 partite l'errore standard di una proporzione è **2.6 punti**, quindi né +3.3
né +2.2 sono distinguibili da zero (z = 1.3 e 0.85). **Tutto il bias dell'Over 2.5 che
si riesce a misurare è un errore di livello del lambda.** Non c'è un problema di forma
da inseguire.

## Il disallineamento di unità è reale, ma è già compensato — e la correzione del `b17` lo romperebbe

Con i parametri di lega veri (post-`b18`) si vede finalmente la catena per intero.

I moltiplicatori attacco e difesa dovrebbero avere media ~1: sono rapporti fra il NPxG
di una squadra e la media **gol** della lega. Non ce l'hanno, e **tutti e otto stanno
sotto 1, in tutte e tre le leghe**:

| lega | att casa | dif trasf | att trasf | dif casa | prodotto H | prodotto A |
|---|---|---|---|---|---|---|
| LaLiga | 0.934 | 0.918 | 0.959 | 0.951 | 0.857 | 0.910 |
| Premier | 0.900 | 0.884 | 0.886 | 0.862 | **0.795** | **0.762** |
| Serie A | 0.925 | 0.920 | 0.907 | 0.901 | 0.850 | 0.817 |

È il disallineamento diagnosticato nel `b17`: NPxG esclude i rigori ed è
sistematicamente sotto i gol veri. Costa il 12-22% del totale. **Ma la contrazione
verso la media di lega (`SHRINK_LAM_K`) ne restituisce +12.3% in tutte e tre**, e il
lambda finale esce a −2.5% / −5.0% / +0.3% dai gol veri. Il difetto c'è nei numeri
intermedi ed è **già compensato a valle**.

Quindi `GOALS_UNIT_FIX` resta a 0, e adesso per un motivo misurato invece che per un
sospetto:

- `_baseN` (la baseline NPxG di coppia che il `b17` userebbe come denominatore)
  **correla 0.769-0.873 col lambda**. È esattamente la trappola del `b9`/`b11`: un
  rapporto contro una baseline correlata cancella la variazione fra partite.
- E la correzione che implica **sfonda il livello**: dividendo per `R = _baseN/mu` il
  lambda passerebbe a 2.87 / 3.09 / 2.76, per `R²` a 3.13 / 3.65 / 3.13, contro gol
  reali 2.70 / 2.75 / 2.43.

La riga della coda «provare `GOALS_UNIT_FIX`» va cancellata: quella correzione, così
com'è scritta, peggiora sia il livello sia la discriminazione. Il disallineamento
esiste, ma va corretto con una media NPxG **di lega**, che oggi il motore non ha.

## La base di lega risponde alla domanda sbagliata

Resta una cosa sola, e spiega la Premier. Il lambda vale

```
lamH = LG.avgH · (npxg_H / LG.avgH) · (npxga_A / LG.avgH)
```

cioè è **inversamente proporzionale** alla base di lega. Una base troppo alta abbassa il
lambda.

| lega | base usata | gol reali 25/26 | scarto | lambda vs reale |
|---|---|---|---|---|
| LaLiga | 2.637 | 2.698 | −2.3% | −2.5% |
| **Premier** | **3.041** | **2.754** | **+10.4%** | **−5.0%** |
| Serie A | 2.548 | 2.426 | +5.0% | +0.3% |

`computeLeagueParams` è una media **piatta su tutte le stagioni caricate**, senza peso
di recenza — l'unica stima del motore che non decade, mentre tutto il resto usa
un'emivita di 106 giorni. La Premier è passata da ~3.28 gol a partita nel 2023/24 a
~2.75 nel 2025/26: la media piatta dà 3.04, e il lambda ne paga il 10% al contrario.

Il `b22` aggiunge `window.LEAGUE_HALFLIFE_DAYS`, **spenta (0 = media piatta, com'è
sempre stata)**, e il CSV esporta le due versioni fianco a fianco
(`Unita: media gol casa (piatta)` e `(emivita 106)`) così un solo backtest decide
senza rilanciare il motore. Stessa disciplina di `ENS_SCOPE_W`: si espone, si misura,
poi si sceglie.

## Il controllo dell'idraulica: cosa legge davvero ciascuno dei due file

Richiesto esplicitamente, e ha trovato un difetto vero.

**`aerials`: il `b19` era stato corretto solo da una parte.** Il motore legge
`defending.aerials_won ?? duels.aerials_won`, ma `CMP_NEW_SPEC` nel Comparatore era
rimasto su `defending.aerials`, cioè i duelli **della partita**. Nel backtest del
06/09 si vede senza margine di dubbio:

```
aerials reale identico fra casa e trasferta: 1132 partite su 1132 (100%)
previsto 14.51  contro  reale 28.41   rapporto 0.511
```

Il motore prevede i duelli **vinti** da una squadra (~14.5) e il CSV li confrontava col
totale dei duelli della partita (~28.4), che è quasi esattamente il doppio. Ogni misura
su `aerials` dal `b19` in poi è da buttare. Corretto.

**Cosa è risultato sano**, con gli script rieseguibili (`spec.js`, `audit20.js`):

- **31 chiavi di `ADV_SPEC` contro `CMP_NEW_SPEC`**: dopo la correzione di `aerials`,
  **zero divergenze**. Stesso controllo sulle 7 metriche lette direttamente in
  `aggregaTeam` (`gca`, `sca`, `xag`, `prog_passes`, `passes_box`, `carries_box`,
  `prog_carries`): stesso campo in tutti e due i file.
- **Le due tabelle interne al Comparatore** (`CMP_NEW_SPEC` e `CMP_ADV_KEYS`)
  concordano sulle 4 chiavi che condividono.
- **Ogni chiave letta come `m.R.*` nel CSV è esposta dall'hook**: 60 esposte, 17 lette,
  zero orfane.
- **187 id del DOM** scritti da `safeTxt`/`safeHtml`: tutti presenti nell'HTML.
- **Le 5 regex di riscrittura testuale** del motore attecchiscono ancora tutte.
- **Nessuna etichetta di riga del CSV duplicata** (55 controllate). Le due
  segnalazioni iniziali erano le tabelle di lookup, che condividono le chiavi per
  costruzione e con lo stesso getter — falso allarme del controllo, non del codice.

**Cosa nessun backtest ha mai visto.** Il Comparatore esporta 43 metriche; il motore ne
prevede di più. Queste **non finiscono nel CSV**, quindi non sono mai state verificate
da nessuna parte: `cross`, `thru`, `aer`, `pass_acc`, `ht`, `seq_time`, `xg_op`,
`xg_shot`. Non è detto che siano rotte — è detto che nessuno lo sa.

## I sei mercati che contano: dove siamo davvero

Audit su 1743 partite e cinque leghe (`b17`). Sono i mercati su cui si scommette
davvero, e per metà di essi questa è la **prima** misura separata mai fatta.

| mercato | base | detto | bias | AUC | Brier |
|---|---|---|---|---|---|
| `1` / `X2` | 43.9% | 44.2% | +0.3 | **0.686** | 0.2224 |
| `2` / `1X` | 30.6% | 28.8% | −1.8 | **0.695** | 0.1935 |
| `X` / `12` | 25.4% | 27.0% | +1.6 | 0.521 | 0.1893 |
| `Goal` / `NoGoal` | 53.9% | 53.2% | −0.7 | 0.544 | 0.2471 |
| `Over 2.5` / `Under` | 53.1% | **49.3%** | **−3.8** | 0.564 | 0.2469 |

Da leggere così: **1X2 e doppie chance funzionano** (AUC 0.69, e le doppie sono la
stessa cosa degli esiti singoli per costruzione — `1X` è il complemento di `2`).
Il **pareggio non funziona** e trascina il `12` con sé: AUC 0.521, e sotto 0.50 in
Premier e Serie A. **GG è debole** (0.544, e 0.476 in Bundesliga). L'**Over 2.5
ordina discretamente ma sbaglia il livello di 3.8 punti**.

Quel −3.8 non è rumore ed era la cosa più concreta emersa: non un problema di
ordinamento ma di **taratura**, e si porta dietro anche il pareggio (sovrastimato di
1.6, coerente con lambda troppo bassi).

> **Aggiornamento `b22`.** La lettura «è taratura, non ordinamento» è stata
> confermata e resa precisa: riscalando il lambda ai gol veri della lega, il bias
> dell'Over 2.5 si chiude **del tutto** in LaLiga e a metà in Premier, e quello che
> resta non è distinguibile da zero (z = 1.3 e 0.85). L'unica leva rimasta è la base
> di lega. Le AUC di questa tabella, invece, restano il muro: quelle non le ha mosse
> nessuno. **Attenzione a leggerle**: sono calcolate in aggregato su cinque leghe e
> per i mercati gol l'aggregato è gonfiato dai base rate diversi — vedi *Trappole*.

### Gli stessi sei mercati, misurati sull'ensemble del `b22`

Rifatta sulle 1133 partite del `b21` (LaLiga, Premier, Serie A) con l'ensemble
attuale — `DC 70% + Markov 30%` su lambda completi. È la fotografia da cui ripartire.

| mercato | base | detto | bias | AUC | Brier | AUC per lega (LaLiga / Premier / Serie A) |
|---|---|---|---|---|---|---|
| `1` | 43.4% | 41.9% | −1.6 | **0.694** | 0.2187 | 0.699 / 0.675 / 0.702 |
| `2` | 30.6% | 31.3% | +0.7 | **0.694** | 0.1918 | 0.669 / 0.675 / 0.725 |
| `X` | 25.9% | 26.8% | +0.9 | 0.531 | 0.1911 | 0.591 / **0.488** / 0.523 |
| `1X` | 69.4% | 68.7% | −0.7 | 0.694 | 0.1918 | — come `2` |
| `X2` | 56.6% | 58.1% | +1.6 | 0.694 | 0.2187 | — come `1` |
| `12` | 74.1% | 73.2% | −0.9 | 0.531 | 0.1911 | — come `X` |
| `Goal` | 52.6% | 50.1% | −2.5 | 0.551 | 0.2479 | 0.514 / 0.535 / 0.553 |
| `Over 2.5` | 50.3% | 47.0% | −3.4 | 0.549 | 0.2492 | 0.573 / 0.513 / 0.522 |

**Come si legge, e cosa non va dedotto.**

- **Le doppie chance non sono mercati in più.** `1X` è il complemento di `2`, `X2` di
  `1`, `12` di `X`: stessa AUC, stesso Brier, per costruzione. Sei righe di tabella,
  **tre** informazioni. Nessuna modifica può migliorare `1X` senza migliorare `2`.
- **`1` e `2` funzionano** (AUC 0.694, stabile fra le tre leghe) e il bias è entro
  ±1.6 punti. È il pezzo sano del motore.
- **`X` non funziona, e trascina `12`.** AUC 0.531 in aggregato ma **0.488 in
  Premier**, cioè sotto il caso. Coerente con la misura dedicata: `pX` ha AUC 0.487 su
  1133 partite. Non è un difetto di taratura — il livello è giusto (+0.9) — è che il
  pareggio *non si prevede*. Vedi *Lo scenario singolo*.
- **`Goal` e `Over 2.5` hanno il problema opposto**: ordinano poco (0.55) **e**
  sbagliano il livello (−2.5 e −3.4). Sono due difetti distinti e vanno inseguiti
  separatamente. Il livello è quasi chiuso (*La base di lega risponde alla domanda
  sbagliata*); l'ordinamento è il muro.

**Il confronto con la tabella del `b17` non è pulito**: quella era su cinque leghe e
1743 partite pre-`b18`, questa su tre leghe e 1133 post-`b18`, con un ensemble diverso.
Le due si somigliano molto, il che è già un'informazione: **due anni di modifiche non
hanno spostato la struttura**, hanno tolto errori.

## Il disallineamento di unità nel lambda

> **Verdetto del `b22`: la diagnosi regge, la cura no.** Le misure qui sotto vengono
> da backtest con `LG.avgH`/`LG.avgA` bloccati a 1.50/1.20 (*La lega che non arrivava
> mai*), ma il meccanismo è stato **riconfermato con i parametri veri**: tutti e otto
> i moltiplicatori attacco/difesa stanno sotto 1 in tutte e tre le leghe misurate.
> Quello che è cambiato è la conclusione operativa: il difetto è **già compensato** a
> valle e `GOALS_UNIT_FIX` così com'è scritta lo peggiorerebbe. Leggi prima
> *Il disallineamento di unità è reale, ma è già compensato*; questa sezione resta per
> il meccanismo e le misure per lega.

Il lambda nasce così:

```js
attH = shrink(npxg_casa / LG.avgH)     // NPxG diviso la media GOL
defA = shrink(npxga_trasf / LG.avgH)   // NPxG diviso la media GOL
lamH = LG.avgH * attH * defA * (1+pen) + pxH
```

**Attacco e difesa sono NPxG normalizzati sulla media dei gol.** Sono unità
diverse: gli NPxG escludono i rigori e stanno sotto ai gol veri. Il rapporto
misurato:

| lega | gol/squadra | NPxG/squadra | NPxG÷gol | effetto al quadrato |
|---|---|---|---|---|
| Bundesliga | 1.623 | 1.434 | 0.884 | **−21.9%** |
| LaLiga | 1.349 | 1.215 | 0.901 | −18.8% |
| Ligue 1 | 1.413 | 1.292 | 0.914 | −16.4% |
| Premier | 1.377 | 1.305 | 0.947 | −10.2% |
| Serie A | 1.213 | 1.150 | 0.948 | −10.1% |

Siccome `lambda = base × attacco × difesa`, lo scarto entra **due volte**: da qui
la colonna al quadrato. Il deficit misurato sui lambda è più piccolo — −8.8%
Bundesliga, −3.6% LaLiga, −2.5% Serie A, −1.5% Premier, +1.3% Ligue 1, **−3.1%
complessivo** — perché il termine rigori (`xG − NPxG`, aggiunto dopo) e lo
shrinkage verso la media di lega ne compensano una parte.

**Ed è per questo che nessuno l'aveva visto: sono due errori che si annullano a
metà.** L'ordine delle leghe però torna quasi esattamente fra deficit teorico e
misurato, ed è la prova che il meccanismo è quello.

Il deficit **non è stagionale**: −2.6% / −4.1% / −2.7% nei tre terzi di stagione.

### Perché la correzione è spenta, e perché ci resta

`window.GOALS_UNIT_FIX` (default **0**, cioè comportamento identico a prima)
normalizza attacco e difesa sugli **NPxG** invece che sui gol, usando la media dei
`_base.npxg` delle due squadre, e nello stesso passo **toglie il termine rigori**,
che a quel punto sarebbe doppio (`LG.avgH` contiene già i gol su rigore).

Al `b17` non era accesa per prudenza: tocca il cuore del lambda e muove tutti i
mercati della matrice insieme. Al `b22` la prudenza si è rivelata giustificata da due
misure, e la voce esce dalla coda:

1. **Il denominatore è correlato col numeratore.** `_baseN` correla **0.769–0.873**
   col lambda. È letteralmente la trappola della *baseline di coppia*: un rapporto
   contro una baseline correlata cancella la variazione fra partite. Il `b17`
   riproponeva l'errore del `b9` in un altro punto, e nessuno se n'era accorto perché
   la costante era a zero.
2. **Il livello sfonderebbe.** Dividendo per `R = _baseN/mu` il lambda passa a
   2.87 / 3.09 / 2.76; per `R²` a 3.13 / 3.65 / 3.13. I gol veri sono
   2.70 / 2.75 / 2.43. Il «21% su un esempio realistico» del `b17` era il segnale
   giusto letto senza la conclusione giusta.

**Perché il codice resta.** Il meccanismo che descrive è reale e un giorno andrà
corretto — ma con una media NPxG **di lega**, che il motore oggi non ha (servirebbe
aggregare `/advanced` su tutta la lega, non sulle due squadre). Finché quella non c'è,
la costante è documentazione eseguibile di un difetto noto, non una leva da tirare.
**Non accenderla senza aver prima sostituito `_baseN`.**

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
  `tackles` +2.7, `ppda_den` +2.5, `carries_box` +2.4, `aerials` +2.4 (**da rifare**: allora leggeva i duelli di partita, non quelli
  vinti dalla squadra),
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

**Il `b20` aggiunge un quarto caso, e va nominato: la costante stimata sui dati
che poi si scopre non servire.** `OL_BETA`, `OL_T1`, `OL_T2` erano di tipo 1 —
stimate per massima verosimiglianza, con il campione scritto nel commento — e
nonostante questo erano **sbagliate**, perché la variabile su cui erano state
stimate non era più quella su cui giravano (lo scope della feature era diventato
`role`). Una stima invecchia quando cambia ciò che sta a monte. Regola aggiuntiva:
accanto al campione va scritta anche **la forma della variabile** su cui la stima
è stata fatta, e ogni volta che si tocca quella variabile la stima va rifatta o
almeno ricontrollata sul bias medio.

Costanti dell'ensemble introdotte nel `b20`, con la loro classificazione:

| costante | valore | tipo | come è stata scelta |
|---|---|---|---|
| `ENS_W.dc` / `.mk` | 0.70 / 0.30 | stimata | griglia scelta su quattro leghe, misurata sulla quinta; modale in 4 fold su 5 |
| `ENS_W.ol` | 0.00 | stimata | stessa griglia; l'OL esce a 0 in 4 fold su 5 |
| `ENS_SCOPE_W` | 1 | stimata (`b21`) | sweep su 1133 partite, monotono in 3 leghe su 3, `z = -3.96`; scelta fuori campione 1.0 in 3 fold su 3 |
| `LEAGUE_HALFLIFE_DAYS` | 0 | **non stimata, dichiarata tale** (`b22`) | 0 = media piatta, comportamento di sempre; il CSV esporta piatta e decaduta fianco a fianco |
| `GOALS_UNIT_FIX` | 0 | **spenta per misura** (`b22`) | il denominatore correla 0.77–0.87 col lambda e il livello sfonderebbe del 30%: non accendere finché `_baseN` non è sostituita da una media NPxG di lega |
| `OL_BETA` / `T1` / `T2` | 2.056 / −0.475 / +0.671 | stimata | massima verosimiglianza su 1743 partite, validata leave-one-league-out |

Nel `b20` `ENS_SCOPE_W` era l'unica senza una misura dietro, ed è per questo che
valeva zero: spedire un valore diverso sarebbe stato cambiare il motore sulla base di
un'intuizione. Un backtest dopo la misura c'era, ed è passata a 1. È il ciclo giusto —
**esporre, misurare, decidere** — e ha impiegato una build. `LEAGUE_HALFLIFE_DAYS` è
oggi nella stessa posizione: esposta, esportata nel CSV in entrambe le versioni, ferma
a zero finché un backtest non parla.

**La forma canonica di questo ciclo**, da riusare ogni volta che si aggiunge un grado
di libertà al motore:

1. La costante è esposta su `window` con un default che **riproduce esattamente il
   comportamento precedente** (di solito 0). Nessuno rischia di svegliarsi con un
   motore diverso.
2. Il CSV esporta **tutte le quantità che servono a ricostruirla** — non il risultato
   con la costante accesa, ma i pezzi da cui si ricompone ogni suo valore. Per
   `ENS_SCOPE_W` erano i due blocchi separati; per `LEAGUE_HALFLIFE_DAYS` sono le due
   medie di lega.
3. **Un solo backtest** basta a spazzare tutto l'intervallo, offline, senza rilanciare
   il motore.
4. Si sceglie **fuori campione** (leave-one-league-out), non sul minimo in-sample.
5. Il valore scelto va nel codice **col commento che dice su quale campione, con che
   z, e in quanti fold**.

Chi salta il punto 2 si condanna a un backtest per valore. `GOALS_SOT_W`,
`ELO_1X2_W` ed `ENS_SCOPE_W` sono stati decisi così; `GOALS_UNIT_FIX`, che il punto 2
non ce l'aveva, è rimasto in sospeso per cinque build.

**La regola.** Per ogni costante nel motore deve valere una di queste tre:
1. **e' stimata dai dati** e c'e' scritto su quale campione;
2. **e' un a priori dichiarato** che si spegne quando i dati bastano;
3. **e' un paracadute di cui e' stato misurato che non morde.**

Se non vale nessuna delle tre, o la si stima, o si mostra che il risultato non
cambia facendola variare del ±50%. Il rischio non e' che la matematica smetta di
funzionare — continua a girare benissimo — ma che ogni costante non stimata sia
un parametro nascosto, e che i parametri nascosti **interagiscano** senza che
nessuno se ne accorga.

## Leggere il log del Comparatore: quattro messaggi che sembrano bug e non lo sono

Ricorrono negli screenshot, quindi vale la pena averli scritti una volta.

- **`⚠️ data fuori dallo storico caricato (2023-08-19 → 2026-05-24)`** e
  **`Nessuna partita per <data>`**. Sono lo stesso fatto: la data chiesta non è
  coperta dall'archivio scaricato. Le stagioni le sceglie la dropdown del
  Comparatore, e l'API non ha ancora le partite della stagione in corso; il
  messaggio è il guardrail che funziona, non un errore. La variante «nessuna
  partita il *g* — si gioca il *g±n*» dice invece che la data è dentro l'archivio
  ma è un turno di sosta.
- **`Il V9.7 non ha esposto _V97_probs`**. L'hook viene iniettato **dopo**
  `const confidence = Math.round(...)`. Se `avviaScanner` esce prima di quella
  riga, l'oggetto non nasce. Il caso di gran lunga più comune è il guardrail
  `dH.overall.n === 0 || dA.overall.n === 0` («Storico insufficiente»): tipico di
  una **neopromossa** nelle prime giornate, che nell'archivio di lega non ha
  partite precedenti alla data target. Non è un bug del contratto: è il motore che
  rifiuta di prevedere senza storico, e il batch che lo riporta.
- **`⚠️ RISERVA: le metriche avanzate NON vengono dal motore ma da cmpDcPredict`**
  seguito da **`Estratti da 0/0 match storici`**. Il primo dice che
  `R.predStats` era vuoto per almeno una delle due squadre, quindi il Comparatore
  è passato al proprio predittore; il secondo che anche quello non ha trovato
  partite utilizzabili. Nei backtest riusciti la riga giusta è
  `→ Metriche avanzate: previste dal motore`, e nel CSV
  `Origine metriche avanzate` deve dire `motore` su **tutte** le partite: se dice
  `riserva-*`, quelle righe sono state prodotte con un secondo modello e non
  vanno confrontate con le altre. **Controllarlo prima di analizzare un CSV.**

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
   `loadLegheJson`, `fetchMatchRaw`, `predictStat`.
   Sono **ventuno**, e ventuno sono le voci di `exposeNames`. Il **contenuto** è
   libero, i **nomi** no.

3. **Il punto di aggancio dell'hook** è la riga della confidence, trovata con
   `/(const\s+confidence\s*=\s*Math\.round\([^;]*;)/`. Non riscriverla e non
   citarla testualmente altrove nel file: la regex prenderebbe la citazione.
   Tutto ciò che l'hook deve leggere va prodotto **prima** di quella riga:
   `__PRED_STATS`, `__PRED_DEBUG`, `__RESID_DEBUG`, `__GOALS_DEBUG`, `__ELO_DEBUG`,
   `__UNIT_DEBUG`, `__ENS_DEBUG`, `m1/mX/m2`, `probsRole`, `probsOver`, `probsOL`,
   `mk_ro`, `mk_ov`, `dcMat`, `lamH_mix/lamA_mix`, `lamH_over/lamA_over`.
   Una variabile dichiarata **dopo** l'hook viene letta con `typeof` e finisce a
   `null` senza errori: il CSV mostra una colonna di `N/D` che nessuno guarda. Il
   controllo F in *Come validare* lo trova.

   **C'è un secondo aggancio, di riserva**, sulle tre righe `const m1 = …; const mX =
   …; const m2 = …;`. Serve se la riga della confidence cambia forma, e in quel caso
   la confidence esce `null`. Se il log dice «Hook iniettato dopo l'ensemble
   (fallback)», qualcosa nel motore è cambiato e va guardato.

4. **`RAW_CACHE[id] = res;`** viene riscritta dal Comparatore per non
   memorizzare le risposte vuote. Se cambi quella riga, la patch smette di
   applicarsi (silenziosamente: il log dice solo che non l'ha fatta).

4-bis. **Le tabelle di estrazione esistono in due copie.** `ADV_SPEC` nello Scanner e
   `CMP_NEW_SPEC` nel Comparatore devono leggere **lo stesso campo per la stessa
   chiave**, altrimenti il CSV confronta due cose diverse e sembra solo che il modello
   sbagli. È già successo con `aerials` (rapporto previsto/reale **0.511** per tre
   build). Vale anche per `CMP_ADV_KEYS` e per le costanti duplicate
   (`CMP_DC_SHRINK_TABLE`). Dopo aver toccato un getter, esegui il **controllo E** di
   *Come validare*: è meccanico e dura un secondo.

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
volte — è esattamente il bug corretto nella v9.4 sui lambda.

**E non basta saperlo: è già stato rifatto una volta.** L'Ordered Logit costruiva
la sua variabile con `predictStat(..., 'role')` — quindi il vantaggio casa dentro,
`+0.196` di media misurata — e poi lo *ridava* con soglie centrate a `−0.250`.
Risultato: +6.8 punti di bias sull'`1`, per tre anni, in una funzione di dieci righe
che sembrava a posto. **La regola operativa**: ogni volta che scrivi o tocchi un
modello che usa numeri di ruolo, misura la **media** della variabile. Se non è
centrata su zero, nessuna costante simmetrica che la accompagna può essere giusta.
Vedi *L'ensemble 1X2*.

**Il time decay** è `_timeDecayDates` con emivita 106 giorni, applicato in
`calcFeatures`. Il Comparatore lo replica in `cmpTimeDecayWeighted`: se cambi
l'emivita da una parte, cambiala dall'altra.

**Niente leakage.** Il taglio temporale è `T00:00` del giorno della partita
(`matchTime` in `avviaScanner`). Qualunque nuova aggregazione deve filtrare
`t < targetMs`, altrimenti il modello vede il risultato che deve prevedere.

**Le costanti calibrate portano la loro provenienza qui dentro, non nel codice.**
I file non hanno commenti (vedi *Stile*), quindi `OL_BETA/OL_T1/OL_T2`, le rette
della confidence, `RESID_GAMMA`, `STAT_SHRINK_TABLE`, le tre tabelle `MARKET_*`,
`SOT_PER_GOAL`, `GOALS_SOT_W`, `ENS_W`, `ENS_SCOPE_W` e `LEAGUE_HALFLIFE_DAYS`
devono dire **in AGENTS.md** su quante partite sono state stimate e con che metodo.
Se ne cambi una, aggiorna la sezione che la descrive; se ne aggiungi una, scrivila da
qualche parte prima di committare.

Accanto al campione va scritta anche **la forma della variabile** su cui la stima è
stata fatta. `OL_BETA` e le soglie erano stimate correttamente, con il campione nel
commento, e nonostante questo erano **sbagliate**: la variabile a monte era cambiata
scope. Una stima invecchia quando cambia ciò che la alimenta, e il campione da solo
non lo dice.

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

**Ma nel codice `RESID_GAMMA` è ancora 0.678**, non 0.360: la misura è stata
scritta qui e non è mai stata riportata nel motore. Con `RESID_ALPHA = 0` non
sposta nessuna probabilità, però `sig`, `edge` e `resid` finiscono nel CSV — cioè
la sezione *A/B CORREZIONE RESIDUALE*, l'unica cosa che direbbe quando riaccendere
la correzione, è calcolata con la scala che questo stesso documento dichiara
sbagliata. È la regola *un componente con peso 0 va comunque tenuto giusto*
applicata a una diagnostica invece che a un numero a schermo. Prima di rileggere
quella sezione del CSV, portare `RESID_GAMMA` a 0.360 (o rimisurarlo).

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
# leghe.json STA nel repository (git ls-files lo elenca): servito da li' non da 404,
# e a fine giro le tre pagine devono uscire con zero errori e zero richieste fallite.
# Controlla anche che ogni id scritto da safeTxt/safeHtml esista nel DOM: una
# card riscritta lascia facilmente scritture verso id che non ci sono più.
```

**I quattro controlli dell'audit** (`b19`), da rifare quando si tocca l'estrazione
o si aggiunge una metrica. Girano sul sorgente o sul CSV di un backtest, e ognuno
ha trovato un bug vero:

- **A. Fallback irraggiungibili.** Cerca ogni variabile assegnata con
  `zeroIf(...)` o `keepNull(...)` e poi testata con `=== null` a una riga
  successiva: quel test non può mai essere vero. Ha trovato **7 fallback morti su
  10**.
- **B. Scala previsto/reale.** Per ogni metrica del CSV, `media(previsto) /
  media(reale)`. Lontano da 1.00 significa che stiamo confrontando due cose
  diverse. Ha trovato **0.63 su Dribbling, Controlli sbagliati e Palle perse**.
- **C. Scambio casa/trasferta.** Il previsto di casa correla di più col reale di
  casa (giusto) o con quello di trasferta (scambio)? **43 metriche controllate,
  zero scambi.**
- **D. Metriche non di squadra.** Il valore reale di casa e quello di trasferta
  sono identici? Se sì, la metrica è una quantità della partita e `predictStat` la
  conta due volte. Ha trovato **`aerials`** (e, tre build dopo, il fatto che la
  correzione fosse stata applicata a un file solo).

**I tre controlli aggiunti dal `b22`**, che guardano l'*idraulica* invece dei numeri —
girano sul solo sorgente, quindi si possono fare a ogni commit senza un backtest:

- **E. Le due tabelle di estrazione leggono lo stesso campo.** Estrai `ADV_SPEC`
  (Scanner) e `CMP_NEW_SPEC` / `CMP_ADV_KEYS` (Comparatore), normalizza i percorsi
  (`m.defending?.aerials_won` → `defending.aerials_won`) e confronta chiave per
  chiave. Ha trovato **`aerials`**, che era stato corretto solo nello Scanner. Stesso
  controllo per le metriche lette direttamente in `aggregaTeam` (`gca`, `sca`, `xag`,
  `prog_passes`, `passes_box`, `carries_box`, `prog_carries`).
  **Attenzione a un falso positivo**: se il parser si ferma al primo `??` vede una
  divergenza dove ci sono solo fallback diversi in numero. Confronta il percorso
  *principale*, o tutti i rami.
- **F. Ogni chiave letta dal CSV è esposta dall'hook.** Raccogli ogni `m.R.<chiave>`
  nel Comparatore e confrontala con le chiavi dell'oggetto `globalThis._V97_probs`.
  Una chiave non esposta non dà errore: dà una colonna di `N/D` che nessuno guarda.
  Oggi: 60 esposte, 17 lette, zero orfane.
- **G. Etichette di riga del CSV duplicate.** Solo quelle che finiscono davvero in
  prima colonna (`mdl`, `uRows`, `statList`, `rowMkt`), **non** le tabelle di lookup:
  quelle condividono le chiavi per costruzione e segnalarle è un falso allarme del
  controllo. Oggi: 55 etichette, zero duplicati.

**I due controlli aggiunti dall'audit del documento**, che girano sul solo sorgente:

- **J. Le costanti scritte qui esistono, con quel valore, nel motore.** Estrarre i
  `window.*` dello Scanner e la tabella `STAT_SHRINK_TABLE`, e confrontarli con i
  numeri di questo file. Ha trovato `RESID_GAMMA` (0.678 nel codice, 0.360 misurato
  qui) e tre voci di `STAT_SHRINK_TABLE` rimaste in tabella dopo che le metriche
  erano uscite da `ADV_SPEC`. Vale anche al contrario: un nome citato nel contratto
  che nel motore non esiste (`leagueStatBaseline`).
- **K. Variabili assegnate e mai lette.** Un `eslint` con `no-unused-vars` e
  `no-undef` sul JS estratto. Ha trovato otto variabili riempite dal payload
  `/advanced` e buttate, e una funzione mai chiamata. **Due avvertenze**: le
  funzioni chiamate da un `onclick` nell'HTML risultano non usate (contarne le
  occorrenze nei due `.html` prima di crederci), e `lamH_mix`/`lamA_mix` risultano
  non usate ma le legge l'hook iniettato, che il linter non vede.

**Il giro completo senza rete.** Il motore si può far girare per intero su dati
finti, in Chromium, senza toccare PitchAPI: è il controllo che ha misurato
`role.n = 8` e che avrebbe intercettato qualunque `NaN` a schermo. La ricetta, in
breve, perché ha due trabocchetti che costano un'ora:

1. Aprire **`comparatore.html`** (ha già gli id DOM ombra che il motore si aspetta),
   leggere `scanner.html` via `fetch`, applicare **le stesse regex del Comparatore**
   e iniettare con `new Function`.
2. Popolare `window.globalLeagueMatchesCache` con un campionato sintetico. Funziona
   **solo** dopo la patch della cache: `globalLeagueMatchesCache` è dichiarata `let`,
   quindi non è una proprietà di `window` e assegnarla da fuori non arriva al motore.
3. **Non provare a sostituire `fetchMatchRaw` da fuori**: le dichiarazioni di
   funzione dentro `new Function` sono riassegnabili solo *da dentro*. Si alimenta il
   motore precaricando `window.__RAW_CACHE[id] = [stats, lineups, advanced, events]`
   per ogni partita, che è quello che `fetchMatchRaw` legge per primo.
4. Poi `setV` su `sel-league`/`sel-home`/`sel-away`, `avviaScanner()`, e si guardano
   `_V97_probs`, i `__*_DEBUG` e ogni nodo con `id` in cerca di `NaN`/`undefined`.

E due controlli che vanno fatti sul **CSV appena arrivato**, prima di analizzarlo:

- **H. La colonna `LEGA` è giusta?** Ricostruisci la lega dai nomi delle squadre e
  confrontala con l'etichetta. Tre righe di codice; ha trovato **59-88% di righe
  sbagliate** nei tre export del 06/09 (vedi *L'etichetta di lega letta dal DOM*).
  Qualunque misura per lega su un file non controllato è aria.
- **I. `Origine metriche avanzate` dice `motore` su tutte le partite?** Se su qualcuna
  dice `riserva-*`, quelle righe vengono da un secondo predittore con scope e baseline
  diversi e **non sono confrontabili** con le altre.

Per B, C e D il CSV va letto sapendo che **ogni partita occupa 4 colonne**
(Previsto, Confidence, Reale, Esito) e che le sezioni CASA e TRASFERTA ripetono le
stesse etichette: la seconda occorrenza è la trasferta. Attenzione anche alle
etichette ripetute fra sezioni diverse (vedi *Trappole*): cercare per etichetta
senza specificare quale occorrenza legge la sezione sbagliata in silenzio.

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

- **riprodurre la matrice fuori dal motore.** `calcDCMatrix` + `probsFromMatrix`
  riscritti in una ventina di righe di Python, alimentati con i lambda che il CSV
  esporta: se il `pOv` ricalcolato coincide con quello del file entro la
  quantizzazione (0.0005), da lì in poi si può **testare qualunque variante offline**
  — `rho = 0`, un lambda riscalato, una linea diversa — senza rilanciare niente. È
  quello che ha chiuso tre ipotesi sul muro dell'Over/Under in un pomeriggio. Il
  controllo di coincidenza va fatto **per primo**: senza quello non si sa se si sta
  misurando il motore o la propria trascrizione.

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

Le uniche eccezioni sono una quarantina di marcatori brevi, nei punti dove una
modifica in buona fede rompe tutto **in silenzio**: le righe che il Comparatore
aggancia per testo, le due convenzioni opposte di `k`, `RESID_ALPHA` a zero, la
provenienza di `OL_BETA` e delle rette della confidence, il `k` fisso
dell'Ordered Logit, il fatto che il riferimento dei mercati deve restare costante
dentro la lega, e che la correzione dai tiri è una media di lambda e non un
moltiplicatore. Rimandano tutti qui. Se ne aggiungi uno, che sia perché *senza*
quella riga qualcuno romperebbe qualcosa, non perché il codice è complicato.

Le build `b20`–`b22` ne hanno aggiunti alcuni più lunghi del solito, e la ragione è
sempre la stessa: **una scelta deliberata che sembra un errore**. `ENS_SCOPE_W = 1`
vale per l'1X2 ma non per i mercati gol; `GOALS_UNIT_FIX` resta a 0 nonostante la
diagnosi che descrive sia vera; `LEAGUE_HALFLIFE_DAYS` è a 0 pur essendo il candidato
migliore in coda. Senza quelle righe, il prossimo che passa «sistema» in buona fede una
delle tre e nessuno se ne accorge per sei mesi. Il criterio resta: si commenta il
**controintuitivo**, mai il complicato.

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
