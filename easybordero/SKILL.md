---
name: easybordero
description: Prepara la bozza del file CSV della setlist da caricare sul portale dei borderò, partendo dall'export del software DJ (Rekordbox, Serato anche da file .crate, Traktor, VirtualDJ, Engine, djay, WinLive, M3U, Excel o una lista incollata). Usala ogni volta che un DJ parla di borderò, programma musicale, setlist, crate, cronologia o history della serata da dichiarare, anche se non nomina il CSV.
---

# easybordero

Trasformi la cronologia di una serata in una bozza di CSV da caricare sul portale dei borderò. Il DJ deve solo allegare il file, rispondere a poche domande e scaricare il risultato. Tieni i messaggi brevi e in italiano semplice.

## 1. Prepara la bozza

Se il DJ non ha ancora allegato il file della serata, chiediglielo. Appena ce l'hai, prima di tutto il resto, chiedi con i pulsanti (salta la domanda solo se te l'ha già indicato lui):

«Hai anche un file Excel, un CSV o un elenco con brani da aggiungere sempre, che hai suonato ma non sono in questo export? Per esempio i dischi della preserata o quelli finiti in un altro crate.»
→ «Sì, te lo allego» / «No»

Se dice sì, aspetta il file e in ogni comando `prepara` aggiungi `--aggiuntivi "<file dei brani da aggiungere>"`. Un elenco incollato salvalo prima in un file `.txt`, una riga per brano, nella forma `Artista - Titolo` o col solo titolo.

Di norma entrano tutte le righe del file. Se il DJ dice quali prendere, segui le sue istruzioni senza fare domande: se indica una colonna (per esempio «solo quelli con la X»), aggiungi `--solo-con "<nome della colonna>"`; per altre indicazioni crea una copia del file con le sole righe volute e usa quella. Non scegliere mai righe a caso o a rotazione: se te lo chiede, spiega che il borderò riguarda solo i brani eseguiti.

Poi lancia:

```bash
python scripts/setlist.py prepara "<file del DJ>" --out bozza.tsv
```

Lo script legge il file, scrive la bozza e la stampa: non serve rileggerla dal file. C'è una riga per opera e la pulizia è già fatta:
- titoli senza remix, edit, feat e BPM;
- mashup divisi;
- doppioni tolti;
- interprete principale già inserito.

In testa stampa anche **AMBIENTE**, le due righe **STIMA** (minuti, calcolati sul numero di brani) e se **MusicBrainz** è raggiungibile: ti servono subito.

Se il DJ ha incollato una lista, salvala prima in un file di testo, una riga per brano nella forma `Artista - Titolo`.

Se lo script si ferma con un messaggio (file di Serato sbagliato, file danneggiato, file non leggibile), riferiscilo al DJ con parole semplici e chiedi il file giusto. Non provare a leggere quel file per conto tuo e non scrivere altri script.

**File `.crate` di Serato.** Se nella prima riga stampata il formato è `serato crate`, il file contiene solo i nomi dei file audio, senza interpreti né durate, ed elenca i brani messi nella cartella, non quelli suonati. Prima delle domande del passo 2 chiedi, con i pulsanti:

«Questo crate contiene solo i brani che hai suonato in quella serata?»
→ «Sì, solo quelli» / «No, ti mando la History»

Se sceglie la History, spiegagli: in Serato apri History, scegli la serata, Export, formato CSV. Poi lavora il nuovo file. Se dice sì, continua con il crate.

## 2. Le prime domande: storico e autori

**Storico, solo da app desktop.** Se AMBIENTE è `desktop`, oppure se il DJ ti ha fatto aprire una cartella del suo computer, chiedi per prima cosa, con i pulsanti:

«Vuoi tenere lo storico dei brani in un file nella tua cartella? Alla prossima serata i brani già decisi vengono confermati in automatico, senza domande e senza cercare di nuovo gli autori.»
→ «Sì, tieni lo storico» / «No»

Se AMBIENTE è `browser` o `sconosciuto` e il DJ non ha aperto nessuna cartella, non parlare dello storico. Una cartella temporanea della chat non vale: il file si perderebbe.

Se il DJ dice sì, il file è `memoria_easybordero.csv` nella sua cartella: se non c'è ancora, lo script parte da zero. Rilancia con la memoria:

```bash
python scripts/setlist.py prepara "<file del DJ>" --out bozza.tsv --storico "<cartella del DJ>/memoria_easybordero.csv"
```

La riga **STORICO** dice quante righe sono già confermate, e le righe STIMA tengono conto solo dei brani nuovi. Se stampa **STORICO ILLEGGIBILE**, dillo al DJ: il file non è stato toccato e questa serata si lavora senza.

Se il DJ tiene lo storico e ti ha dato il file dei brani da aggiungere, chiedi con i pulsanti:

«Vuoi tenere nello storico anche i dati dei brani aggiunti dal tuo file (interpreti, autori, compositori)? Così la prossima volta non li cerco di nuovo online.»
→ «Sì, tienili» / «No»

Lo storico conserva il legame tra il brano come è scritto nel file e i dati trovati: se in un upload successivo lo stesso brano arriva con pochi dettagli, i dati si riprendono da lì senza cercarli online.

**Solo interpreti o anche autori.** Subito dopo, prima di correggere, fai questa domanda **con lo strumento delle domande a pulsanti** (in Claude è sempre disponibile: usalo). Metti nei pulsanti i minuti delle righe STIMA, per esempio con 154 brani:

«Ho letto 154 brani. Nel file metto solo gli interpreti o anche autori e compositori? Autori e compositori li cerco su MusicBrainz, un servizio esterno gratuito che risponde a un brano per volta: li trovo per circa un brano su quattro, molto meno per la musica italiana.»
→ «Solo interpreti · circa 4 minuti» / «Anche autori e compositori · circa 19 minuti, servizio esterno»

Se lo script ha scritto **MusicBrainz: NON RAGGIUNGIBILE**:
- **se sei Claude**, il secondo pulsante diventa «Anche autori e compositori · prima va sbloccato MusicBrainz». Se il DJ lo sceglie, spiegagli come sbloccarlo: Impostazioni, Funzionalità, sotto «Elenco domini consentiti» scrive `musicbrainz.org` nel campo «Domini aggiuntivi consentiti» e preme «Aggiungi». Vale subito, anche in questa chat. Intanto vai avanti con le correzioni e i dubbi; quando ti dice che ha fatto, lancia `python scripts/setlist.py rete`. Se è ancora non raggiungibile, continua con i soli interpreti;
- **se non sei Claude**, non fare la domanda: di' in una riga che qui autori e compositori non si possono cercare e vai avanti con i soli interpreti.

## 3. Correggi la bozza

Leggi la bozza e correggi solo quello che non va. Per quasi tutti i brani basta la tua conoscenza: cerca sul web (o su Spotify, se collegato) solo i brani che non riconosci. Non collegarti al portale dei borderò e non consultare i siti degli enti che gestiscono i diritti d'autore: non controlli nulla su quei sistemi, prepari solo una bozza.

Su ogni riga si dichiara **l'opera originale**: titolo ufficiale e interprete originale. Le cose da sistemare sono queste:
- **Interprete sbagliato.** Nel file c'è spesso il remixer: «Macarena» di Stavros Martina è dei Los del Río, «Boombastic» di Limitlezz è di Shaggy. Correggilo.
- **Titolo con resti.** Toglili: canale, genere, anno aggiunto, nomi di remixer tra parentesi. Esempi: «Cono Gelato (BangDaBengTV)» diventa «Cono Gelato», «Let The Sun Shine 2018» diventa «Let The Sun Shine».
- **Righe con una nota nella colonna `controlla`:**
  - **mashup senza separatore**: dividili tu in più righe, per esempio «Desolee Gasolina» diventa Désolée di Anna e Gasolina di Daddy Yankee. Se riconosci una sola parte («G63 (Dj Matt Mashup)»), tieni quella senza chiedere;
  - **parte già suonata da sola**: toglila;
  - **DJ mix intero**: chiedi al DJ.
- **Righe da un crate.** Dove manca l'interprete, inserisci quello originale riconoscendo il brano dal titolo: senza interprete il CSV salta la riga. Se non riconosci il brano, mettilo tra i dubbi. Sistema i nomi rovinati: «La BebÇ Remix» diventa «La Bebé», «L amour toujours» diventa «L'amour toujours». Se il nome non è un titolo (una sequenza casuale di lettere e numeri), chiedi al DJ.
- **Righe con la nota «aggiunto dal DJ».** Non toglierle, non cambiare quello che ha scritto il DJ e non chiedere se sono state suonate: questo vale solo per queste righe, tutte le altre seguono le regole di questo passo. Se mancano dati, completali come per gli altri brani, a meno che non siano già arrivati dallo storico: l'interprete lo riconosci dal titolo o lo cerchi sul web (o su Spotify, se collegato), autori e compositori li cerca il passo 5 se il DJ li ha chiesti. Se non trovi l'interprete con certezza e la riga ha già autori o compositori, lascialo vuoto. Chiedilo al DJ solo per le righe di **AGGIUNTIVI SENZA INTERPRETE** che non trovi: senza nessun nome il CSV le salta. Se correggendo una riga dell'export diventa uguale a una riga aggiunta dal DJ, cancella quella dell'export.
- **Righe con la nota «confermato dallo storico».** Non correggerle e non fare domande su queste righe, a meno che non te lo chieda il DJ.
- **Autore e compositore.** Non scriverli tu, né a memoria né cercandoli sul web: o li riporta già il file, o li cerca lo script al passo 5.

Scrivi le correzioni direttamente in `bozza.tsv`. Per togliere un brano cancella la riga. Se dividi una riga in più opere, numerale così: `12.1`, `12.2`. Le colonne `n` e `controlla` servono solo a te: il CSV non le usa.

## 4. Chiedi solo i dubbi

Fai una sola tornata di domande, solo per i brani che non sai risolvere da solo. Di solito sono pochi: mai più di 10.

Se hai lo strumento per le domande a scelta con pulsanti, usalo. Altrimenti scrivi le domande numerate con opzioni a lettere, così il DJ risponde «1a 2b».

Esempi:
- «Calabria 2K18 (Enur): quale opera?» → «Calabria 2007 · Enur» / «Calabria · Rune RK» / «Toglila»
- «Summer Mix 2018, 2 ore: è un DJ mix intero. Lo tolgo?» → «Sì, toglilo» / «No, tienilo»
- «Que Guapa (Soave): non lo trovo.» → «Tienilo così» / «Toglilo»

Prima delle domande scrivi una sola riga di riepilogo, per esempio: «154 brani letti, 156 opere a posto, 5 domande per te.»

## 5. Autori e compositori (solo se il DJ li ha chiesti)

Salta questo passo se il DJ ha scelto «Solo interpreti». Altrimenti, con la bozza già corretta:

```bash
python scripts/setlist.py autori bozza.tsv
```

Prima di lanciarlo scrivi al DJ quanto ci vorrà, con i minuti della ricerca della riga STIMA, per esempio: «Cerco gli autori su MusicBrainz: circa 15 minuti. Ti avviso quando ho finito.» Lo script lavora al massimo 4 minuti per volta e salva man mano:
- se stampa **RESTANO**, rilancia lo stesso comando finché non stampa **FINITO**, senza chiedere nulla al DJ;
- se stampa **NON RAGGIUNGIBILE**, di' al DJ in una riga che stavolta il file avrà solo gli interpreti e continua;
- se stampa **NON RISPONDE**, il sito è sovraccarico. Chiedi al DJ se riprovare fra qualche minuto o continuare con quello che hai trovato.

Gli autori trovati sono già nella bozza: non toccarli e non completare a mano quelli mancanti. Nella colonna `controlla` quelle righe hanno la nota «autori da MusicBrainz, da controllare».

## 6. Consegna il CSV

```bash
python scripts/setlist.py csv bozza.tsv --out setlist_AAAA-MM-GG.csv
```

Usa la data della serata, che spesso è nel nome del file. Se lo script segnala righe senza interprete, completale e rilancia il comando.

Se il DJ ha scelto lo storico, salvalo subito:

```bash
python scripts/setlist.py storico bozza.tsv --memoria "<cartella del DJ>/memoria_easybordero.csv" --tolti "12,35"
```

Se il DJ ha scelto di tenere nello storico anche i dati dei brani aggiunti, aggiungi `--aggiuntivi` a questo comando.

In `--tolti` metti solo le righe (colonna `n`) che il DJ ha detto di togliere rispondendo a una domanda; se non ce ne sono, ometti l'opzione. Non metterci i brani che hai tolto tu perché doppi o già suonati quella sera: varrebbero anche per le serate future.

Se dopo la consegna il DJ dice che un brano è sbagliato, correggilo in `bozza.tsv` e rilancia i comandi `csv` e `storico`. Se vuole rimettere un brano tolto in passato, aggiungi la riga in `bozza.tsv` e, nel comando `storico`, aggiungi `--dimentica "<titolo com'è nel file>"`.

Dai il file da scaricare con queste righe:
- quanti brani contiene;
- se hai usato lo storico: quanti brani sono stati confermati in automatico, che vanno controllati anche quelli, e quali sono stati tolti come deciso in passato;
- se il DJ ha indicato il file dei brani da aggiungere: quanti ne hai aggiunti e che il borderò deve contenere solo i brani eseguiti, quindi se stasera uno di quelli non l'ha suonato lo deve togliere;
- se il file era un crate: che gli interpreti mancanti li hai dedotti dal titolo e che vanno controllati;
- se hai cercato gli autori: per quanti brani li hai trovati, che vengono da MusicBrainz e che vanno controllati, perché possono essere incompleti o scritti con il nome d'arte;
- sul portale dei borderò: crea la setlist, carica il CSV, controlla che i brani siano riconosciuti, associa la setlist al borderò e invia;
- se il portale non riconosce le colonne, posso rifarlo con il punto e virgola come separatore (`--separatore ";"`);
- sempre, con queste parole: «Attenzione: questo file è una bozza preparata automaticamente e non è stato verificato su nessun portale. Prima di inviare il borderò controlla ogni brano: la responsabilità della compilazione è tua.»

Solo se il DJ dice che la setlist è «a durata effettiva» (jazz, classica, danza, musica nei parchi), aggiungi `--durata-effettiva`.
