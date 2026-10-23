---
name: schermate
description: Fa le schermate dello Scanner a 390px, come lo vede il telefono, sulla lega finta del banco o su una partita vera della PitchAPI. Controlla che nessuna scheda scorra di lato e che la pagina non abbia errori, poi le manda all'utente. Da usare dopo ogni modifica alla grafica, prima di proporre un cambiamento grafico, o quando l'utente chiede di vedere com'è una schermata.
---

# Schermate a 390px

Il telefono in verticale è il caso principale (AGENTS.md, *Regole di lavoro*). A 390px
`document.body.scrollWidth − larghezza` deve fare 0 in ogni scheda, con tutte le `details`
aperte.

## 1. Lega finta (nessuna chiamata, una quarantina di secondi)

```bash
node strumenti/schermate.js --out <scratchpad>/schermate
```

## 2. Partita vera

```bash
node strumenti/schermate.js --vera "Juventus|Atalanta|2026-09-20" --out <scratchpad>/schermate
node strumenti/schermate.js --vera "Lausanne|Lugano|2026-09-20" --lega "SUI:Super League"
```

- I nomi delle squadre vanno scritti come li mostra il menu dello Scanner. La lega di default è la
  Serie A, la stagione quella che contiene la data.
- Costa 200–300 chiamate: usala per controllare quello che la lega finta non mostra (nomi lunghi,
  quote automatiche, formazioni vere), non a ogni ritocco. La chiave è quella del batch (skill
  `batch`).
- Una partita giocata ha le quote di chiusura; una fra qualche giorno quelle della settimana.

## 3. Cosa esce

Diciotto file `finta-*.png` o `vera-*.png`:

- setup, anello dell'analisi, Partita (tre altezze);
- Tabellone;
- Squadre: formazioni, indisponibili (con due titolari della casa e uno della trasferta segnati, e dal `b89` la ricerca della casa con tre lettere), giocatori, ruolo e generale;
- Numeri, chiusi e aperti;
- Prompt, Dati, foglio Altro.

E il testo del mega-prompt, `finta-prompt.txt` o `vera-prompt.txt` (dal `b86`): quando si tocca il prompt, si rilegge
quello, con e senza quote, contro le misure di AGENTS.md (*Il mega-prompt*). Dal `b87` anche `<nome>-prompt-indisponibili.txt`, il prompt coi
tre giocatori segnati.

A schermo escono anche lo scorrimento laterale di ogni scheda, gli errori della pagina e le
chiamate fatte. Lo strumento esce con 1 se una scheda scorre di lato, se la pagina ha un errore o
se l'anello non si chiude.

Altre opzioni:

- `--ridotto`: movimento ridotto (dal `b78` i numeri non contano più da zero: serve solo a togliere le entrate);
- `--tema chiaro`: lo schema di colori chiaro del sistema (di default scuro); dal `b78` le pagine hanno tutti e due i temi, e una modifica alla grafica si guarda in tutti e due;
- `--istantanee`: salva anche ogni scheda dopo l'analisi (`<nome>-pagina-<scheda>.html`, senza script, con le
  `details` aperte e il tema fissato). Serve al rilevatore di impeccable, che sul file statico non vede la pagina
  analizzata. Da quella cartella:
  ```bash
  python3 -m http.server 8391 &
  printf '#!/bin/sh\nexec /opt/pw-browsers/chromium-1194/chrome-linux/chrome --no-sandbox "$@"\n' > <scratchpad>/chrome-ns && chmod +x <scratchpad>/chrome-ns
  IMPECCABLE_BROWSER=<scratchpad>/chrome-ns .claude/skills/impeccable/scripts/impeccable detect --viewport 390x844 http://localhost:8391/scuro-pagina-numeri.html
  ```
  Una modifica alla grafica si chiude con 0 segnalazioni in tutte le schede e in tutti e due i temi (dal `b79`);
- `--larghezza 1280`: la vista del computer;
- `--nome`: il prefisso dei file.

## 4. Guardarle e mandarle

- Guarda le schermate (Read sull'immagine) prima di mandarle. Cerca:
  - testi troncati: con la lega finta i nomi sono corti, quindi un «Juvent…» si vede solo su una
    partita vera;
  - parole spezzate e riquadri che escono dal loro spazio;
  - testo chiaro su fondo chiaro;
  - una card vuota.
- Manda all'utente solo quelle che rispondono alla domanda (`SendUserFile`, `display: render`),
  con una riga che dice cosa guardare.
- Se una schermata mostra un difetto, correggilo prima di mandarla, o dillo. Lo scorrimento 0 non
  basta: il tabellone è uscito di lato di 53 px dentro il suo riquadro per molte build, con la
  pagina a 0.
- Per la giornata, il Comparatore o la home lo strumento non basta: si guida la pagina con
  Playwright allo stesso modo. Il banco con `MOBILE=1` misura lo scorrimento anche della giornata
  e del Comparatore; la home no.
