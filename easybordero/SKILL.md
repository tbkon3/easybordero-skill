---
name: easybordero
description: Prepara la bozza del file CSV della setlist da caricare sul portale dei borderò, partendo dall'export del software DJ (Rekordbox, Serato, Traktor, VirtualDJ, Engine, djay, WinLive, M3U, Excel o una lista incollata). Usala ogni volta che un DJ parla di borderò, programma musicale, setlist, cronologia o history della serata da dichiarare, anche se non nomina il CSV.
---

# easybordero

Trasformi la cronologia di una serata in una bozza di CSV da caricare sul portale dei borderò. Il DJ deve solo allegare il file, rispondere a poche domande e scaricare il risultato. Tieni i messaggi brevi e in italiano semplice.

## 1. Prepara la bozza

```bash
python scripts/setlist.py prepara "<file del DJ>" --out bozza.tsv
```

Lo script legge il file, scrive la bozza e la stampa: non serve rileggerla dal file. C'è una riga per opera e la pulizia è già fatta:
- titoli senza remix, edit, feat e BPM;
- mashup divisi;
- doppioni tolti;
- interprete principale già inserito.

Se il DJ ha incollato una lista, salvala prima in un file di testo, una riga per brano nella forma `Artista - Titolo`.

## 2. Correggi la bozza

Leggi la bozza e correggi solo quello che non va. Per quasi tutti i brani basta la tua conoscenza: cerca sul web (o su Spotify, se collegato) solo i brani che non riconosci. Non collegarti al portale dei borderò e non consultare i siti degli enti che gestiscono i diritti d'autore: non controlli nulla su quei sistemi, prepari solo una bozza.

Su ogni riga si dichiara **l'opera originale**: titolo ufficiale e interprete originale. Le cose da sistemare sono queste:
- **Interprete sbagliato.** Nel file c'è spesso il remixer: «Macarena» di Stavros Martina è dei Los del Río, «Boombastic» di Limitlezz è di Shaggy. Correggilo.
- **Titolo con resti.** Toglili: canale, genere, anno aggiunto, nomi di remixer tra parentesi. Esempi: «Cono Gelato (BangDaBengTV)» diventa «Cono Gelato», «Let The Sun Shine 2018» diventa «Let The Sun Shine».
- **Righe con una nota nella colonna `controlla`:**
  - **mashup senza separatore**: dividili tu in più righe, per esempio «Desolee Gasolina» diventa Désolée di Anna e Gasolina di Daddy Yankee. Se riconosci una sola parte («G63 (Dj Matt Mashup)»), tieni quella senza chiedere;
  - **parte già suonata da sola**: toglila;
  - **DJ mix intero**: chiedi al DJ.
- **Autore e compositore.** Lasciali vuoti, a meno che non li riporti già il file: al portale basta l'interprete.

Scrivi le correzioni direttamente in `bozza.tsv`. Per togliere un brano cancella la riga. Le colonne `n` e `controlla` servono solo a te: il CSV non le usa.

## 3. Chiedi solo i dubbi

Fai una sola tornata di domande, solo per i brani che non sai risolvere da solo. Di solito sono pochi: mai più di 10.

Se hai lo strumento per le domande a scelta con pulsanti, usalo. Altrimenti scrivi le domande numerate con opzioni a lettere, così il DJ risponde «1a 2b».

Esempi:
- «Calabria 2K18 (Enur): quale opera?» → «Calabria 2007 · Enur» / «Calabria · Rune RK» / «Toglila»
- «Summer Mix 2018, 2 ore: è un DJ mix intero. Lo tolgo?» → «Sì, toglilo» / «No, tienilo»
- «Que Guapa (Soave): non lo trovo.» → «Tienilo così» / «Toglilo»

Prima delle domande scrivi una sola riga di riepilogo, per esempio: «154 brani letti, 156 opere a posto, 5 domande per te.»

## 4. Consegna il CSV

```bash
python scripts/setlist.py csv bozza.tsv --out setlist_AAAA-MM-GG.csv
```

Usa la data della serata, che spesso è nel nome del file. Se lo script segnala righe senza interprete, completale e rilancia il comando.

Dai il file da scaricare con queste righe:
- quanti brani contiene;
- sul portale dei borderò: crea la setlist, carica il CSV, controlla che i brani siano riconosciuti, associa la setlist al borderò e invia;
- se il portale non riconosce le colonne, posso rifarlo con il punto e virgola come separatore (`--separatore ";"`);
- sempre, con queste parole: «Attenzione: questo file è una bozza preparata automaticamente e non è stato verificato su nessun portale. Prima di inviare il borderò controlla ogni brano: la responsabilità della compilazione è tua.»

Solo se il DJ dice che la setlist è «a durata effettiva» (jazz, classica, danza, musica nei parchi), aggiungi `--durata-effettiva`.
