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

Un test funzionale delle funzioni pure si fa estraendo la fetta di file fra
`// SHRINKAGE ADATTIVO` e `async function avviaScanner()` e importandola in
node con `globalThis.window = globalThis` in testa.

Il giro completo (una partita vera) richiede rete verso PitchAPI: se non ce
l'hai, **dillo** invece di dichiarare verificato quello che non lo è.

## Stile

- Commenti e testi UI **in italiano**, senza accenti nelle stringhe JS di
  servizio (il file gira anche incollato dentro `new Function`).
- I commenti spiegano **perché**, e quando sostituiscono un comportamento
  precedente dicono cosa c'era prima e cosa non andava. Mantieni l'abitudine:
  è quello che rende recuperabile una taratura sbagliata sei mesi dopo.
- Nessuna dipendenza esterna, nessun CDN. Tutto inline.
- File singoli e grossi: si modificano con edit puntuali, non riscritture.

## Git

Branch di lavoro `claude/*`, mai push diretto su `main`. Commit in italiano,
con i numeri della misura che giustifica il cambiamento quando c'è.
