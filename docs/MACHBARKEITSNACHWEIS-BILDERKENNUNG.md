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

## Empfehlung

1. **Barcode bleibt der Hauptweg** zur Produktidentifikation (Phase 4a). Er ist zuverlässig und
   deckt fast alle verpackten Produkte ab.
2. **Bilderkennung über einen externen KI-Dienst mit Bildverständnis** (multimodales
   Sprachmodell) als optionalen Adapter umsetzen, so wie in DEC-022 bereits vorgesehen. Er wird
   aber nicht mehr nur als Zusatz neben Tesseract betrachtet, sondern als der eigentliche Weg für
   Fotoerkennung und MHD-Lesen. Ein solcher Dienst kann gestaltete Schriften, gewölbte
   Verpackungen, lose Ware und mehrere Produkte pro Foto verarbeiten. Datenschutz bleibt wie
   festgelegt: Bilder werden nur nach ausdrücklicher Konfiguration und mit Hinweis an den
   Benutzer übertragen.
3. **Tesseract nicht als Standard einbauen.** Ohne konfigurierten Dienst bleibt es bei Barcode,
   Suche und manueller Eingabe. Das entspricht FR-PRD-004: Ein Ausfall der Bilderkennung darf
   eine manuelle Buchung nicht verhindern.
4. Vor der Umsetzung von Punkt 2 denselben Bildsatz gegen den gewählten Dienst laufen lassen,
   als Vergleichswert zu diesem Nachweis.

Umgesetzt als DEC-030 im [Entscheidungsprotokoll](ENTSCHEIDUNGEN.md); DEC-007 / DEC-022 ist
dort als ersetzt markiert. Erster Kandidat für den externen Dienst ist Gemini.
