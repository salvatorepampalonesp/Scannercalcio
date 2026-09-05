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

**Taratura di `STAT_SHRINK_TABLE` (0905-b3)** — grid search sui componenti che
la diagnostica del motore espone, 76 partite di Serie A (marzo + aprile 2026),
con verifica mese per mese: nessun valore peggiora di più dello 0.3% in un
singolo mese.

| metrica | k | ottimo | apr | mar | RMSE al nuovo k |
|---|---|---|---|---|---|
| `poss` | 0.75 | 0.80 | 0.75 | 0.90 | 8.335 → 8.031 (−3.7%) |
| `gca` | 0.75 | 0.80 | 0.90 | 0.75 | 2.142 → 2.099 (−2.0%) |
| `carries_box` | 0.70 | 0.80 | 0.60 | 1.00 | 2.113 → 2.060 (−2.5%) |
| `prog_passes` | 0.60 | 0.60 | 0.65 | 0.55 | 7.601 → 7.538 (−0.8%) |
| `sca` | 0.40 | 0.40 | 0.35 | 0.40 | 8.777 → 8.757 (−0.2%) |
| `npxg`, `xg` | 0.50 | 0.45 | 0.65 | 0.35 | curva piatta, mesi discordi |
| `passes_box` | 0.60 | — | — | — | solo pendenza lato Comparatore |
| `prog_carries` | 0.55 | — | — | — | solo pendenza lato Comparatore |
| `xag` | 0.40 | — | — | — | mesi discordi: prudente |
| default | 0.50 | | | | |

Dove i due mesi discordano il valore è smorzato verso il centro. `xgot` e
`tch_box` usano il default. Il Comparatore ha una **seconda** tabella
(`CMP_DC_SHRINK_TABLE`) per le metriche che il motore non aggrega
(VAEP, xT, PV): scope e baseline diversi, quindi valori diversi — non
copiarli da una parte all'altra.

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

Per rivalutarla serve una stagione intera e possibilmente più leghe. Con un
mese solo non si distingue un effetto da un capriccio del calendario: con lo
stesso identico motore, marzo 2026 ha dato 66.7% di pick azzeccati e aprile
2026 il 47.5%.

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
