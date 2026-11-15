# Machbarkeitsnachweis Bilderkennung (DEC-007 / DEC-022)

Stand: 2026-11-15

## Fragestellung

Reicht lokale OCR mit Tesseract und anschließendem Abgleich gegen den Produktkatalog aus, um

1. ein Lebensmittel anhand eines Fotos zu identifizieren (FR-PRD-004) und
2. das Mindesthaltbarkeitsdatum aus einem Foto des Aufdrucks zu lesen?

## Testmaterial

40 Smartphone-Fotos (12 MP) von 30 verschiedenen Produkten aus dem eigenen Haushalt. Die
Aufnahmen sind typisch für den späteren Einsatz: Produkt auf dem Tisch, schräg von oben,
Tageslicht. Der Bestand ist gemischt:

- verpackte Markenprodukte (Ritter Sport, Becel, Exquisa, Händlmaier, Alnatura, …)
- lose Ware (Banane, Orangen im Netz, Salatgurke)
- vier Fotos mit zwei Produkten
- drei Fotos, auf denen das MHD sichtbar sein soll

Zu jedem Foto ist das erwartete Ergebnis bekannt. Die Bilder liegen außerhalb des
Repositorys.

## Vorgehen

- Tesseract 5.5 mit den Sprachen `deu+eng`, in drei Stufen:
  1. Originalbild mit den Segmentierungsmodi `--psm 3` (automatisch) und `--psm 11` (verstreuter Text).
  2. Vorverarbeitet: Ausschnitt aus der Bildmitte, Hochskalierung, Graustufen, Kontrastanhebung,
     Schärfen, jeweils um 0°, 90° und 270° gedreht.
  3. Gegenprobe an zehn Fotos: von Hand eng auf das Produkt zugeschnitten. Das entspricht einem
     Benutzer, der das Produkt bildfüllend fotografiert.
- Abgleich gegen einen Testkatalog aus Name und Marke der 30 Produkte. Verfahren: unscharfer
  Wortvergleich mit Ähnlichkeit ≥ 0,8 und Wörtern ab vier Zeichen. Bewertet wird, ob das richtige
  Produkt auf Platz 1 bzw. unter den ersten drei Vorschlägen steht.
- MHD: Datumsmuster (`TT.MM.JJ`/`TT.MM.JJJJ`) im erkannten Text. Zusätzlich wurde der Aufdruck
  eng ausgeschnitten und mit Ziffern-Whitelist und Drehungen in 15°-Schritten gelesen.

## Ergebnisse

### Produkterkennung

| Variante | Richtig auf Platz 1 | Richtig unter Top 3 | Kein Vorschlag | Falscher Vorschlag |
| --- | --- | --- | --- | --- |
| Originalbild | 3 / 40 | 3 / 40 | 37 | 0 |
| Vorverarbeitet | 3 / 40 | 3 / 40 | 36 | 1 |
| Beides kombiniert | **5 / 40** | **5 / 40** | 34 | 1 |

Erkannt wurden nur Produkte mit großer, gerader Schrift in Standardschrift auf flacher
Verpackung: Corn Flakes, Erdnusscreme, Rübenzucker, Penne Dinkel und passierte Tomaten. Bei
den Orangen hat das Etikett zusätzlich „Banane“ ergeben, was zu einem falschen Vorschlag
geführt hat.

Auch bei den zehn eng zugeschnittenen Fotos (Stufe 3) kamen nur Fragmente heraus, zum
Beispiel „TOFY“, „FPETTARME … MILCH“ oder „ATURA“. Bei Becel, Exquisa, Butter und Brandt
wurde gar nichts erkannt. Der Bildausschnitt ist also nicht die Hauptursache.

### MHD

**0 von 3** Daten wurden erkannt. Einer der drei Fälle ist sogar besonders günstig: Bei den
Maultaschen steht das Datum „16.11.26“ fett und schwarz auf einer flachen Folie. Selbst bei
engem Zuschnitt lieferte Tesseract davon nur Bruchstücke („1.26 16:34“). Der Nadeldruck auf
dem Dosendeckel („M.H.D. 31.07.2029“) wurde in keiner Drehung erkannt.

## Ursachen

- **Gestaltete Schriften:** Logos und Produktnamen sind kursiv, verziert oder handschriftlich
  gesetzt (Almighurt, Exquisa, Händlmaier, Rama, Brandt). Tesseract ist auf Fließtext in
  Dokumenten trainiert.
- **Gewölbte und glänzende Oberflächen:** Dosen, Gläser, Becher und Folien verzerren die Schrift
  und erzeugen Reflexe.
- **Schräge Perspektive und gedrehter Text:** Tesseract erwartet waagerechte Zeilen.
- **Nadel- und Tintenstrahldruck** beim MHD: Die Ziffern bestehen aus Einzelpunkten. Dafür ist
  Tesseract nicht ausgelegt.
- **Lose Ware** (Banane, Gurke) hat grundsätzlich keinen Text. Dafür wäre Bildklassifikation
  nötig, nicht OCR.

## Bewertung

Lokale OCR mit Tesseract ist für beide Anwendungsfälle **nicht tragfähig**. Eine Trefferquote
von 12 % bei der Produkterkennung und 0 % beim MHD bringt dem Benutzer keinen Nutzen. Weitere
Vorverarbeitung wie Entzerrung oder Binarisierung würde die Grundprobleme (Schriftarten,
Wölbung, Nadeldruck) nicht lösen.

## Gegenprobe mit KI-Modellen mit Bildverständnis

Weil OCR nicht reicht, wurden zwei multimodale Sprachmodelle mit demselben Bildsatz geprüft. Sie
bekamen dieselbe Aufgabe: alle Lebensmittel auf dem Foto nennen und einem Eintrag aus dem
Testkatalog zuordnen, außerdem ein lesbares MHD angeben.

### Gemini (externer Dienst, `gemini-3.8-flash`, kostenloses Kontingent)

Von 40 Anfragen wurden nur 2 beantwortet, beide richtig. Den Frischkäse hat Gemini mit der
genauen Sorte benannt, auf dem Tetrapack der passierten Tomaten zusätzlich ein MHD gelesen. Alle
übrigen Anfragen scheiterten an den Grenzen des Dienstes: zu viele Anfragen (HTTP 429), Dienst
überlastet (HTTP 503) oder Zeitüberschreitung. Auch mit Wiederholungen und Pausen war nach
kurzer Zeit das Tageslimit erreicht.

**Bewertung:** Fachlich vielversprechend. Das kostenlose Kontingent ist für den Alltag aber
nicht verlässlich, ein bezahlter Zugang ist nicht vorgesehen. Hinzu kommt, dass die Fotos an
einen externen Anbieter gehen. Gemini scheidet deshalb aus.

### Lokales Modell (Ollama, Qwen2.5-VL 3B) auf dem Server

Der Server ist ein Mini-PC mit Intel N150 (4 Kerne, 14 GB RAM) ohne eigene Grafikkarte. Ollama
lief testweise als Docker-Container. Geprüft wurden 10 Fotos, darunter die drei MHD-Fotos und
die Fotos mit zwei Produkten.

| Variante | Dauer pro Foto | Ergebnis |
| --- | --- | --- |
| Prozessor, Bild auf 1024 px verkleinert | ca. 190 s | 9 / 10 Fotos vollständig richtig, MHD 2 / 3 |
| Prozessor, 640 px, kurzer Prompt ohne Katalog | ca. 170 s | schlechter (Senf als „Honig“ erkannt, kein MHD) |
| Eingebaute Intel-Grafik über Vulkan | 30–45 s | unbrauchbar (leere oder ablehnende Antworten) |

Die Qualität ist gut. Die Katalog-IDs hält das kleine Modell zwar nicht ein, seine
Beschreibungen entsprechen aber den Katalognamen, sodass die Zuordnung in der App erfolgen kann.
Das Problem ist die Zeit. Ein kurzer Text ist in 2 s verarbeitet, das Einlesen des Bildes
braucht dagegen rund 160 s. Diese Zeit hängt kaum von der Bildgröße ab, sondern von der
Rechenleistung. Während dieser Zeit sind alle vier Kerne ausgelastet, auch für die laufende
Anwendung.

**Bewertung:** Fachlich geeignet, auf der vorhandenen Hardware für den Alltag aber zu langsam.

## Empfehlung

1. **Fotoerkennung und MHD-Lesen vorerst zurückstellen.** Phase 4 wird mit Barcode, Suche und
   manueller Eingabe abgeschlossen.
2. **Schnittstelle trotzdem vorsehen.** Die Bilderkennung bleibt als austauschbarer Adapter
   eingeplant, damit sie später ohne Umbau ergänzt werden kann. Bevorzugt wird ein lokales
   Modell über Ollama, sobald ein Rechner mit geeigneter Grafikkarte im Tailnet verfügbar ist.
   Ein externer Dienst bleibt nur als ausdrücklich konfigurierte Option.
3. **Tesseract nicht einbauen.**
4. **Bevor ein Adapter umgesetzt wird,** denselben Bildsatz auf der dann vorhandenen Hardware
   erneut prüfen. Zielwerte: mindestens 90 % der Produkte richtig, Antwort in höchstens etwa
   10 s pro Foto.

Umgesetzt als DEC-030 im [Entscheidungsprotokoll](ENTSCHEIDUNGEN.md); DEC-007 / DEC-022 ist
dort als ersetzt markiert.
