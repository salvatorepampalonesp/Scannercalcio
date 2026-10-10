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

Quindici file `finta-*.png` o `vera-*.png`:

- setup, anello dell'analisi, Partita (tre altezze);
- Tabellone;
- Squadre: formazioni, giocatori, ruolo e generale;
- Numeri, chiusi e aperti;
- Prompt, Dati, foglio Altro.

A schermo escono anche lo scorrimento laterale di ogni scheda, gli errori della pagina e le
chiamate fatte. Lo strumento esce con 1 se una scheda scorre di lato, se la pagina ha un errore o
se l'anello non si chiude.

Altre opzioni:

- `--ridotto`: movimento ridotto, così i numeri che contano sono già al valore finale;
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
