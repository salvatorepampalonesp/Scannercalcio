---
name: nuova-build
description: Chiude una modifica di scanner.html o comparatore.html come vuole il progetto. Alza la build nei quattro posti, controlla sintassi e agganci del Comparatore, fa girare il banco di parità col motore di prima e aggiorna AGENTS.md. Poi committa e porta su main con la PR. Da usare ogni volta che si tocca il motore, la grafica dello Scanner o il Comparatore, prima di dire che una build è pronta.
---

# Nuova build

Vale per ogni modifica a `scanner.html` o `comparatore.html`, anche solo grafica. Le regole sono
in AGENTS.md, *Regole di lavoro* e *Come validare una modifica*. Questa è la sequenza.

## 0. Prima di toccare

- Il branch è quello della sessione (`claude/...`), allineato a main:
  `git fetch origin main && git rev-list --left-right --count origin/main...HEAD` deve dare `0 0`.
  Se la PR di prima è già unita, `git checkout -B <branch> origin/main`.
- Salva il motore di prima, per il banco:
  `git show origin/main:scanner.html > <scratchpad>/scanner-prima.html`.
- Leggi la sezione di AGENTS.md che tocchi. Se tocchi il JS, leggi anche *Il contratto Scanner ↔
  Comparatore*: il Comparatore dipende dalla forma testuale di alcune righe.
- Il JS non ha commenti (la spiegazione va in AGENTS.md). Nessun accento nelle stringhe JS di
  servizio. Edit puntuali, mai riscritture. Il codice dell'interfaccia cerca i nodi con
  `querySelector` + `instanceof Element`: nel Comparatore `getElementById` non torna mai `null`.

## 1. La build, nei quattro posti insieme

```bash
grep -nE "build 0905-b|__SCANNER_BUILD =|_bComp =" scanner.html comparatore.html
grep -n "Build corrente\|## Stato attuale" AGENTS.md
```

Le altre occorrenze di `0905-b4` e `0905-b3` nel Comparatore sono nomi di sezioni del CSV: restano
come sono.

- `scanner.html`: `window.__SCANNER_BUILD = '0905-bNN';` e il badge `id="build-ver"`.
- `comparatore.html`: `const _bComp = '0905-bNN';` e il badge `id="build-ver"`.
- `AGENTS.md`: «Build corrente» in *Regole di lavoro* e il titolo di *Stato attuale*.

Se i due file divergono, il Comparatore mostra un avviso arancione. Il badge è l'unico modo per
sapere cosa mostra il browser.

## 2. I controlli veloci

```bash
python3 - <<'PY'
import io,re
for f in ('scanner.html','comparatore.html'):
    s=io.open(f,encoding='utf-8').read()
    js='\n;\n'.join(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', s, re.S))
    io.open('/tmp/'+f.replace('.html','.js'),'w',encoding='utf-8').write(js)
PY
node --check /tmp/scanner.js && node --check /tmp/comparatore.js
node -e '
const js=require("fs").readFileSync("/tmp/scanner.js","utf8");
const t=[["cache lega",/(^|\n)\s*(?:let|var|const)\s+globalLeagueMatchesCache\s*=\s*\[\]\s*;?/],
 ["RAW_CACHE decl",/(^|\n)\s*(?:let|var|const)\s+RAW_CACHE\s*=\s*\{\}\s*;?/],
 ["RAW_CACHE save",/RAW_CACHE\[id\]\s*=\s*res;/],
 ["punto hook 1",/(const\s+confidence\s*=\s*Math\.round\([^;]*;)/],
 ["punto hook 2",/(const\s+m1\s*=[^;]*;\s*const\s+mX\s*=[^;]*;\s*const\s+m2\s*=[^;]*;)/]];
for(const [n,re] of t) console.log((re.test(js)?"OK  ":"KO  ")+n);'
```

Tutto `OK`. Un `KO` vuol dire che il Comparatore non aggancia più il motore.

## 3. Il banco di parità

```bash
mkdir -p <scratchpad>/banco
OUT=<scratchpad>/banco MOBILE=1 VECCHIO=<scratchpad>/scanner-prima.html node strumenti/banco-parita.js
```

Ci mette 3–5 minuti: lancialo in background. Deve uscire con 0. Il dettaglio è in
`<scratchpad>/banco/parita-report.json`.

- In ogni modalità: copia conforme, 0 scritture del motore diverse su 191, 0 righe del CSV su 122,
  0 px di scorrimento a 390px.
- Nella riga `vecchio` (il motore di prima caricato nel Comparatore) devono cambiare **solo** le
  scritture che la modifica voleva cambiare (`idDiversi` nel report), più il certificato.
  Qualunque altra differenza è un effetto non voluto.
- Il banco non vede quello che non passa da `safeTxt`/`safeHtml`: il mega-prompt, «In breve», le
  card scritte con `innerHTML` diretto. Lì la verifica si fa a parte, e va detto.
- Se la modifica aggiunge un controllo al banco, fai il controllo di potenza: una copia con un
  guasto messo apposta (`ROOT=<copia>`) deve far fallire il banco.
- Se cambia la grafica, guarda le schermate con la skill `schermate`.

## 4. AGENTS.md

- *Cronologia delle build*: una riga `bNN` in fondo, con quello che cambia e i numeri del banco.
- *Il Comparatore stampa come lo Scanner*: «Esito al `bNN`» e la frase «Al `bNN` il controllo
  col `bNN−1` vede …».
- La sezione che descrive quello che hai cambiato. Il *Registro delle costanti*, se una costante è
  nuova o cambia. *Da fare* e *Cosa è già stato provato*, se la modifica chiude una voce.
- I titoli che il codice cita (`vedi AGENTS.md, …`) non si rinominano.

## 5. Commit e main

- Commit in italiano: titolo `bNN: cosa cambia`, corpo con i numeri (banco, misure), e in fondo le
  righe di attribuzione che la sessione indica. Nessun nome di modello nel messaggio.
- `git push -u origin <branch>`. Solo sugli errori di rete, riprova fino a 4 volte (2, 4, 8, 16
  secondi).
- Il flusso dell'utente è PR verso main, squash merge, branch riallineato:
  `git fetch origin main && git checkout -B <branch> origin/main && git push --force-with-lease origin <branch>`,
  poi `git rev-list --left-right --count origin/main...HEAD` deve dare `0 0`.
- Nella risposta all'utente: cosa cambia a schermo, i numeri del banco, cosa non è stato
  verificato.
