# Produktspezifikation

# Lebensmittel- und Vorratsverwaltung

**Projektname:** Lebensmittelverwaltung  
**Dokumentversion:** 1.0 – Fachlicher Spezifikationsentwurf  
**Status:** Zur fachlichen Prüfung und technischen Konzeption  
**Zielplattformen:** Webbrowser, Android-Smartphone  
**Bereitstellung:** Self-hosted, Docker-basiert  
**Sprache:** Deutsch

* * *

# 1\. Produktvision und Zielsetzung

## 1.1 Produktvision

Entwicklung einer einfach bedienbaren Anwendung zur digitalen Verwaltung sämtlicher Lebensmittel und Vorräte innerhalb eines privaten Haushalts.

Die Anwendung ermöglicht es, jederzeit festzustellen:

- Welche Lebensmittel sind im Haushalt vorhanden?
- In welchen Mengen sind sie vorhanden?
- An welchen Lagerplätzen befinden sie sich?
- Welche Lebensmittel sollten zeitnah verbraucht werden?
- Welche Lebensmittel müssen nachgekauft werden?
- Welche Lebensmittel stehen kurz vor dem Mindesthaltbarkeits- oder Verbrauchsdatum?
- Welche Veränderungen gab es am Vorratsbestand?

Die Erfassung und Aktualisierung der Vorräte soll möglichst einfach und mit minimalem manuellem Aufwand erfolgen.

Insbesondere sollen Smartphones und deren Kameras verwendet werden, um Lebensmittel durch das Scannen von Barcodes oder durch Bilderkennung zu identifizieren.

## 1.2 Hauptziele

**G1 – Transparenz über vorhandene Lebensmittel**

Der gesamte Lebensmittelbestand eines Haushalts soll zentral und übersichtlich dokumentiert werden.

**G2 – Einfache Bestandsführung**

Einlagerungen, Entnahmen und Umlagerungen sollen mit möglichst wenigen Bedienungsschritten durchgeführt werden können.

**G3 – Reduzierung unnötiger Einkäufe**

Durch eine aktuelle Bestandsübersicht sollen Doppelkäufe vermieden werden.

**G4 – Automatische Einkaufsunterstützung**

Die Anwendung soll anhand definierter Mindestbestände automatisch Vorschläge für den nächsten Einkauf erstellen.

**G5 – Vermeidung von Lebensmittelverschwendung**

Lebensmittel mit bevorstehendem Mindesthaltbarkeits- oder Verbrauchsdatum sollen frühzeitig identifiziert werden.

**G6 – Einfache Inventur**

Vorhandene Bestände sollen regelmäßig überprüft und unkompliziert korrigiert werden können.

**G7 – Datenschutz und Unabhängigkeit**

Die Anwendung soll grundsätzlich auf eigener Infrastruktur betrieben werden können. Die Speicherung der Bestandsdaten darf keine externe Cloud voraussetzen.

## 1.3 Erfolgskennzahlen

Zur Bewertung der Anwendung werden folgende Zielgrößen definiert:

| Kennzahl | Ziel |
| --- | --- |
| Erfassung eines bekannten Produkts per Barcode | Möglichst innerhalb von 15 Sekunden |
| Verbuchung einer einfachen Entnahme | Möglichst innerhalb von 10 Sekunden |
| Manuelle Eingaben bei bekanntem Produkt | Auf Menge, gegebenenfalls Datum und Lagerplatz reduziert |
| Aktuelle Bestandsübersicht | Jederzeit abrufbar |
| Erstellung einer Einkaufsliste | Auf Knopfdruck |
| Inventur | Lagerplatzweise durchführbar |
| Nachvollziehbarkeit | Jede Bestandsänderung ist dokumentiert |

Die angegebenen Zeiten sind Produktziele. Sie müssen während der Entwicklung unter realistischen Bedingungen überprüft werden.

* * *

# 2\. Produktumfang und Abgrenzung

## 2.1 Funktionsumfang der ersten Version (MVP)

Das Minimum Viable Product umfasst folgende Funktionsbereiche:

1.  Benutzerverwaltung für einen Haushalt
2.  Verwaltung der Lagerplätze
3.  Verwaltung eines Lebensmittelkatalogs
4.  Produkterkennung mittels Barcode
5.  Unterstützte Produkterkennung mittels Kamera und Bildanalyse
6.  Einlagerung neuer Lebensmittel
7.  Entnahme und Verbrauch von Lebensmitteln
8.  Umlagerung vorhandener Bestände
9.  Bestandsübersicht mit Such- und Filterfunktionen
10. Verwaltung von Mindestbeständen
11. Erstellung und Bearbeitung von Einkaufslisten
12. Überwachung von Haltbarkeitsdaten
13. Inventur und Bestandskorrekturen
14. Protokollierung von Bestandsbewegungen
15. Responsive Webanwendung einschließlich Android-Nutzung

## 2.2 Erweiterungsmöglichkeiten

Folgende Funktionen sind für spätere Entwicklungsstufen vorgesehen:

- Rezeptverwaltung
- Rezeptvorschläge anhand vorhandener Lebensmittel
- Automatische Bestandsentnahme beim Kochen nach Rezept
- Sprachgesteuerte Entnahmebuchungen
- Automatische Erkennung mehrerer Produkte auf einem Foto
- Verwaltung mehrerer Haushalte
- Erfassung von Preisen und Einkaufskosten
- Auswertung des Lebensmittelverbrauchs
- Statistiken zur Lebensmittelverschwendung
- Integration externer Einkaufsdienste
- Import digitaler Kassenbons
- Vollständige Offline-Funktionalität mit späterer Synchronisierung
- Native Android-App
- QR-Code-Etiketten für Lagerplätze
- Automatische Erfassung von Lagerbeständen durch intelligente Sensoren

Diese Erweiterungen sind nicht Bestandteil der ersten Entwicklungsstufe, müssen aber bei der Architektur berücksichtigt werden, soweit dadurch spätere Erweiterungen wesentlich erleichtert werden.

## 2.3 Nichtziele

Die Anwendung soll zunächst keine Warenwirtschaft für gewerbliche Betriebe darstellen.

Nicht vorgesehen sind:

- Verkauf von Lebensmitteln
- Rechnungsstellung
- Lieferantenverwaltung
- Buchhaltung
- Vollautomatische Erkennung tatsächlich verbrauchter Mengen
- Automatische Überwachung der Lebensmittelsicherheit durch Sensoren

Die Anwendung dokumentiert Bestände anhand der tatsächlich vorgenommenen Buchungen. Sie kann nicht automatisch feststellen, ob Lebensmittel ohne Buchung entnommen oder entsorgt wurden.

* * *

# 3\. Benutzer und Rollen

## 3.1 Benutzergruppen

Die Anwendung ist für die Mitglieder eines Haushalts vorgesehen.

Es werden zwei Rollen definiert.

### Administrator

Der Administrator besitzt sämtliche Berechtigungen.

Insbesondere kann er:

- Benutzer verwalten
- Lagerplätze anlegen, ändern und entfernen
- Lebensmittelstammdaten verwalten
- Mindestbestände konfigurieren
- Inventuren durchführen
- Bestandskorrekturen vornehmen
- Systemeinstellungen verwalten
- Datensicherungen auslösen oder konfigurieren

### Haushaltsmitglied

Ein Haushaltsmitglied kann:

- Lebensmittel erfassen
- Lebensmittel entnehmen
- Lebensmittel umlagern
- Vorräte durchsuchen
- Einkaufslisten bearbeiten
- Haltbarkeitsinformationen einsehen
- Inventuren durchführen, sofern freigegeben

Administrative Systemeinstellungen bleiben dieser Rolle vorenthalten.

## 3.2 Benutzerkonzept

Für den MVP wird ein einzelner Haushalt mit mehreren Benutzern vorgesehen.

Alle Benutzer arbeiten auf demselben Lebensmittelbestand.

Änderungen sollen für andere Benutzer nach erneuter Abfrage beziehungsweise Aktualisierung sichtbar sein.

Jede Bestandsänderung wird dem ausführenden Benutzer zugeordnet.

* * *

# 4\. Fachliches Datenmodell

## 4.1 Grundprinzip

Die Bestandsverwaltung unterscheidet zwischen:

1.  **Lebensmittelprodukt:** Was ist das Lebensmittel?
2.  **Produktvariante:** In welcher Verpackungsgröße oder Einheit liegt es vor?
3.  **Lagerplatz:** Wo befindet sich das Lebensmittel?
4.  **Bestandsposition:** Welche konkrete Menge liegt an welchem Lagerplatz und besitzt welches Haltbarkeitsdatum?
5.  **Bestandsbewegung:** Durch welchen Vorgang wurde der Bestand verändert?

Diese Trennung ist notwendig, da ein Lebensmittel gleichzeitig an mehreren Lagerplätzen mit unterschiedlichen Haltbarkeitsdaten vorhanden sein kann.

### Beispiel

Das Produkt „Milch 3,5 %“ ist dreimal vorhanden.

| Lagerplatz | Menge | Haltbarkeitsdatum |
| --- | --- | --- |
| Kühlschrank | 1 Liter | 20.11.2026 |
| Kühlschrank | 2 Liter | 25.11.2026 |
| Vorratsraum | 3 Liter | 15.01.2027 |

Der Gesamtbestand beträgt sechs Liter.

Die einzelnen Bestandspositionen bleiben dennoch unterscheidbar.

Bei einer Entnahme aus dem Kühlschrank soll bevorzugt die Milch mit dem früheren Haltbarkeitsdatum vorgeschlagen werden.

## 4.2 Lebensmittelprodukt

Ein Lebensmittelprodukt besteht mindestens aus folgenden Informationen:

| Attribut | Beschreibung | Pflicht |
| --- | --- | --- |
| Produkt-ID | Eindeutige interne Kennung | Ja  |
| Produktname | Bezeichnung des Lebensmittels | Ja  |
| Produktgruppe | Kategorie, z. B. Milchprodukte | Ja  |
| Hersteller/Marke | Hersteller oder Markenname | Nein |
| Barcode/GTIN | Eindeutige Produktkennung, soweit vorhanden | Nein |
| Produktbild | Bild zur einfacheren Wiedererkennung | Nein |
| Basiseinheit | Stück, Gramm oder Milliliter | Ja  |
| Mindestbestand | Gewünschte untere Bestandsgrenze | Nein |
| Zielbestand | Gewünschter Bestand nach dem Einkauf | Nein |
| Standardlagerplatz | Bevorzugter Lagerplatz | Nein |
| Standardhaltbarkeit | Optionaler Vorschlagswert | Nein |
| Haltbarkeitswarnfrist | Tage vor Ablauf | Nein |
| Aktiv | Kennzeichnung zur Verwendung im Produktkatalog | Ja  |

Für die Erkennung können einem Produkt mehrere Barcodes beziehungsweise Produktvarianten zugeordnet werden.

### Produktgruppen

Für die erste Version werden folgende Produktgruppen vorgeschlagen:

- Milchprodukte
- Fleisch und Wurst
- Fisch
- Obst
- Gemüse
- Brot und Backwaren
- Nudeln, Reis und Getreide
- Konserven
- Tiefkühlprodukte
- Getränke
- Gewürze
- Süßwaren
- Sonstige Lebensmittel

Die Kategorien müssen durch den Administrator erweitert und angepasst werden können.

## 4.3 Produktvarianten und Verpackungseinheiten

Ein Lebensmittel kann in unterschiedlichen Verpackungen vorhanden sein.

Beispiel:

**Produkt:** Zucker

| Variante | Packungsgröße | Basismenge |
| --- | --- | --- |
| Zucker 500 g | 500 g | 500 g |
| Zucker 1 kg | 1 kg | 1.000 g |
| Zucker 2 kg | 2 kg | 2.000 g |

Alle Varianten werden dem gleichen Lebensmittelprodukt zugeordnet.

Der Gesamtbestand wird in einer gemeinsamen Basiseinheit geführt.

Dabei gelten folgende Regeln:

- Masse wird intern in Gramm verwaltet.
- Volumen wird intern in Millilitern verwaltet.
- Zählbare Produkte werden in Stück verwaltet.
- Verpackungsgrößen können zur Umrechnung verwendet werden.
- Eine automatische Umrechnung zwischen Masse und Volumen ist ohne produktspezifischen Umrechnungsfaktor nicht zulässig.

Produktvarianten dürfen eigene Barcodes besitzen.

## 4.4 Lagerplätze

Lagerplätze müssen hierarchisch strukturiert werden können.

### Beispiel einer Lagerhierarchie

**Haushalt**

**Küche**

- Kühlschrank
    - Oberes Fach
    - Mittleres Fach
    - Gemüsefach
    - Türfach
- Gefrierschrank
    - Schublade 1
    - Schublade 2
- Vorratsschrank
    - Fach 1
    - Fach 2

**Vorratsraum**

- Regal links
    - Fach 1
    - Fach 2
- Regal rechts
    - Fach 1
    - Fach 2

**Keller**

- Vorratsraum
    - Regal 1
    - Regal 2
- Gefriertruhe

Ein Lagerplatz kann weitere untergeordnete Lagerplätze enthalten.

Bestände werden auf einem konkret auswählbaren Lagerplatz geführt.

Eine Bestandsauswertung über einen übergeordneten Lagerplatz berücksichtigt sämtliche darunterliegenden Lagerplätze.

## 4.5 Bestandsposition

Eine Bestandsposition repräsentiert eine konkrete Lebensmittelmenge.

| Attribut | Beschreibung |
| --- | --- |
| Bestands-ID | Eindeutige Kennung |
| Produkt-ID | Referenz zum Lebensmittel |
| Produktvariante | Zugehörige Verpackungsvariante, soweit bekannt |
| Lagerplatz-ID | Aktueller Lagerplatz |
| Menge | Aktueller Bestand in der Basiseinheit |
| Haltbarkeitsdatum | MHD oder Verbrauchsdatum |
| Datumstyp | MHD, Verbrauchsdatum, kein Datum, unbekannt |
| Einlagerungsdatum | Datum der Einlagerung |
| Öffnungsdatum | Optional |
| Status | Vorhanden, verbraucht, entsorgt |
| Anmerkung | Optionale Zusatzinformation |

Das Mindesthaltbarkeitsdatum wird auf Ebene der Bestandsposition gespeichert, nicht ausschließlich am Produkt.

Identische Produkte mit verschiedenen Haltbarkeitsdaten müssen unabhängig verwaltet werden können.

## 4.6 Bestandsbewegung

Jede Veränderung des Bestands wird protokolliert.

Unterstützte Bewegungsarten:

- Einlagerung
- Verbrauch
- Umlagerung
- Inventurkorrektur
- Entsorgung
- Stornierung beziehungsweise Gegenbuchung

Zu jeder Bewegung werden mindestens gespeichert:

- Bewegungs-ID
- Zeitpunkt
- Benutzer
- Bewegungsart
- Produkt
- Betroffene Bestandspositionen
- Menge
- Ausgangslagerplatz, falls relevant
- Ziellagerplatz, falls relevant
- Optionaler Kommentar

Historische Bewegungen werden nicht durch nachträgliches Überschreiben verändert.

Fehlerhafte Buchungen werden durch nachvollziehbare Korrekturbuchungen berichtigt.

* * *

# 5\. Funktionale Anforderungen

Die funktionalen Anforderungen sind mit eindeutigen IDs versehen.

Prioritäten:

**MUSS:** Erforderlich für den MVP.  
**SOLL:** Gewünscht, aber bei Bedarf nach dem MVP umsetzbar.  
**KANN:** Optionale Erweiterung.

## 5.1 Verwaltung der Lagerplätze

### FR-LOC-001 – Lagerplätze anlegen

**Priorität:** MUSS

Administratoren müssen neue Lagerplätze anlegen können.

Ein Lagerplatz besitzt:

- Name
- Optionalen übergeordneten Lagerplatz
- Optional eine Beschreibung
- Optional einen Lagerplatztyp

Beispiel: „Regal rechts, Fach 1“ innerhalb des Vorratsraums.

**Akzeptanzkriterien:**

- Lagerplätze können hierarchisch angelegt werden.
- Namen müssen innerhalb desselben übergeordneten Lagerplatzes eindeutig sein.
- Die maximale Hierarchietiefe wird nicht fachlich begrenzt.
- Ein Lagerplatz kann ohne Programmänderung ergänzt werden.

### FR-LOC-002 – Lagerplätze ändern

**Priorität:** MUSS

Ein vorhandener Lagerplatz kann umbenannt oder innerhalb der Hierarchie verschoben werden.

Bestehende Bestandszuordnungen bleiben erhalten.

### FR-LOC-003 – Lagerplätze entfernen

**Priorität:** MUSS

Lagerplätze mit vorhandenen Beständen dürfen nicht ohne vorherige Bestandsbereinigung entfernt werden.

Das System muss anzeigen, welche Bestände einer Löschung entgegenstehen.

Die Datenhistorie muss erhalten bleiben.

### FR-LOC-004 – Bestandsübersicht nach Lagerplatz

**Priorität:** MUSS

Ein Benutzer muss einen Lagerplatz auswählen und sämtliche dort vorhandenen Lebensmittel anzeigen können.

Bei Auswahl eines übergeordneten Lagerplatzes werden standardmäßig auch dessen untergeordnete Lagerplätze berücksichtigt.

* * *

## 5.2 Lebensmittelstammdaten

### FR-PRD-001 – Lebensmittel manuell anlegen

**Priorität:** MUSS

Ein Benutzer mit entsprechender Berechtigung kann ein bisher unbekanntes Lebensmittel anlegen.

Mindestens erforderlich sind:

- Produktname
- Produktkategorie
- Basiseinheit

Weitere Angaben können optional ergänzt werden.

### FR-PRD-002 – Lebensmittel über Barcode identifizieren

**Priorität:** MUSS

Die Anwendung muss Barcodes über die Smartphone-Kamera erfassen können.

Für den MVP sind mindestens die im Lebensmittelhandel üblichen Formate EAN-13, EAN-8 und UPC-A zu unterstützen.

Ablauf:

1.  Benutzer aktiviert die Barcode-Erkennung.
2.  Kamera wird geöffnet.
3.  Barcode wird erkannt.
4.  Anwendung sucht nach dem Barcode im lokalen Produktkatalog.
5.  Bei einem Treffer werden die Produktinformationen angezeigt.
6.  Der Benutzer kann das Produkt direkt weiterverarbeiten.

Ist der Barcode unbekannt, soll die Anwendung optional eine externe Produktdatenquelle abfragen können.

Ist auch dort kein Produkt ermittelbar, wird die manuelle Produkterfassung angeboten.

**Akzeptanzkriterien:**

- Bekannte Barcodes identifizieren das zugeordnete Produkt eindeutig.
- Unbekannte Barcodes führen nicht zu einem Fehlerabbruch.
- Der Barcode wird bei manueller Neuanlage übernommen.
- Ein Barcode darf nicht versehentlich mehreren widersprüchlichen Produktvarianten zugeordnet werden.
- Externe Dienste sind für die normale Bestandsverwaltung nicht erforderlich.

### FR-PRD-003 – Produktinformationen aus externen Datenquellen

**Priorität:** SOLL

Die Anwendung soll externe Produktdatenquellen verwenden können.

Mögliche Informationen:

- Produktname
- Hersteller
- Produktkategorie
- Verpackungsgröße
- Produktbild
- Mengeneinheit

Die Integration wird über eine austauschbare Schnittstelle realisiert.

Alle extern ermittelten Daten müssen vor ihrer erstmaligen Übernahme überprüft und gegebenenfalls korrigiert werden können.

Die konkreten Datenquellen, Nutzungsbedingungen und Lizenzanforderungen sind vor der Implementierung festzulegen.

### FR-PRD-004 – Lebensmittel mittels Bild erkennen

**Priorität:** MUSS

Lebensmittel sollen alternativ durch Fotografieren identifiziert werden können.

Der Benutzer fotografiert beispielsweise:

- Eine Lebensmittelverpackung
- Ein Produktetikett
- Ein einzelnes Lebensmittel
- Ein bereits geöffnetes Lebensmittelgebinde

Das System analysiert das Bild und versucht, das Produkt zu identifizieren.

Die Erkennung kann insbesondere auf folgenden Verfahren basieren:

- Texterkennung (OCR)
- Bildklassifikation
- Abgleich mit vorhandenen Produktbildern
- Kombination mehrerer Erkennungsverfahren

**Wichtige fachliche Anforderung:**

Die Bilderkennung muss nicht in jedem Fall ein eindeutiges Ergebnis liefern.

Kann das System das Produkt nicht sicher identifizieren, werden geeignete Produktvorschläge angezeigt.

Der Benutzer bestätigt das erkannte Produkt oder wählt es manuell aus.

Eine automatische Bestandsbuchung allein aufgrund einer unsicheren Bilderkennung ist nicht zulässig.

**Akzeptanzkriterien:**

- Ein Foto kann direkt mit der Smartphone-Kamera aufgenommen werden.
- Das System verarbeitet das Foto und liefert, soweit möglich, Produktvorschläge.
- Mehrdeutige Erkennungsergebnisse sind auswählbar.
- Bei fehlendem Treffer ist die manuelle Produktauswahl möglich.
- Ein Benutzer muss vor der Bestandsbuchung das Produkt bestätigen.
- Ein technischer Fehler der Bilderkennung verhindert keine manuelle Buchung.

**Technischer Hinweis:**

Die zuverlässige Bilderkennung beliebiger Lebensmittel ist eine eigenständige technische Herausforderung.

Vor der endgültigen Festlegung der Erkennungstechnologie ist ein technischer Machbarkeitsnachweis durchzuführen.

Die Architektur muss sowohl lokale als auch optional externe KI-Dienste unterstützen können. Eine Weitergabe von Bildern an externe Dienste darf nur bei entsprechender Konfiguration und transparenter Information erfolgen.

### FR-PRD-005 – Lebensmittel suchen

**Priorität:** MUSS

Produkte können über folgende Kriterien gesucht werden:

- Produktname
- Produktkategorie
- Hersteller
- Barcode
- Lagerplatz

Eine Suche nach Namensbestandteilen muss möglich sein.

### FR-PRD-006 – Produktinformationen bearbeiten

**Priorität:** MUSS

Lebensmittelstammdaten müssen nachträglich bearbeitet werden können.

Änderungen an Produkten dürfen nicht unkontrolliert bestehende Bestände verändern.

Insbesondere Änderungen der Basiseinheit oder Verpackungsgröße müssen hinsichtlich ihrer Auswirkungen geprüft werden.

* * *

## 5.3 Einlagerung von Lebensmitteln

### FR-STK-001 – Neue Lebensmittel einlagern

**Priorität:** MUSS

Nach einem Einkauf müssen Lebensmittel schnell eingelagert werden können.

**Standardablauf:**

1.  Benutzer wählt „Einlagern“.
2.  Produkt wird per Barcode, Bild oder Suche identifiziert.
3.  Anwendung zeigt das erkannte Produkt.
4.  Benutzer erfasst beziehungsweise bestätigt die Menge.
5.  Benutzer erfasst das Haltbarkeitsdatum, sofern vorhanden.
6.  Benutzer wählt den Lagerplatz.
7.  Benutzer bestätigt die Einlagerung.
8.  Der Bestand wird aktualisiert.

Bei bekannten Produkten werden geeignete Vorgabewerte vorgeschlagen.

Insbesondere:

- Standardverpackungsgröße
- Standardlagerplatz
- Zuletzt verwendete Mengeneinheit

Beispiel:

**Produkt:** Milch 1 Liter  
**Anzahl:** 3 Packungen  
**Haltbar bis:** 25.11.2026  
**Lagerplatz:** Kühlschrank

Ergebnis: Einlagerung von drei Litern Milch.

### FR-STK-002 – Mehrfacherfassung gleicher Produkte

**Priorität:** MUSS

Mehrere identische Verpackungen müssen in einem Vorgang eingelagert werden können.

Beispiel:

Fünf Dosen Tomaten mit jeweils 400 Gramm werden gemeinsam erfasst.

Es darf nicht erforderlich sein, jede Dose einzeln zu buchen.

### FR-STK-003 – Unterschiedliche Haltbarkeitsdaten

**Priorität:** MUSS

Werden identische Produkte mit unterschiedlichen Haltbarkeitsdaten eingelagert, müssen diese als getrennte Bestandspositionen verwaltet werden können.

Beispiel:

Drei Joghurtbecher:

- Ein Becher: 20.11.2026
- Zwei Becher: 27.11.2026

Die Anwendung führt zwei unterscheidbare Bestandspositionen.

### FR-STK-004 – Haltbarkeitsdatum erfassen

**Priorität:** MUSS

Das Haltbarkeitsdatum muss manuell eingegeben werden können.

Die Anwendung unterscheidet:

- Mindesthaltbarkeitsdatum
- Verbrauchsdatum
- Kein Haltbarkeitsdatum
- Haltbarkeitsdatum unbekannt

Fehlt ein entsprechendes Datum auf einem Produkt, darf dies die Einlagerung nicht verhindern.

### FR-STK-005 – Haltbarkeitsdatum mittels Kamera erkennen

**Priorität:** SOLL

Das Haltbarkeitsdatum soll optional aus einem Foto der Verpackung beziehungsweise des Aufdrucks ermittelt werden können.

Der erkannte Wert wird zur Bestätigung angezeigt.

Ein nicht eindeutig erkanntes Datum darf nicht automatisch übernommen werden.

### FR-STK-006 – Wiederholte Erfassung

**Priorität:** MUSS

Werden Produkt, Lagerplatz, Haltbarkeitsdatum und gegebenenfalls weitere bestandsrelevante Merkmale identisch erfasst, kann die Menge zu einer vorhandenen Bestandsposition addiert werden.

Mehrfaches versehentliches Absenden derselben Buchung darf nicht zu doppelten Beständen führen.

### FR-STK-007 – Bestandsaktualisierung

**Priorität:** MUSS

Nach erfolgreicher Einlagerung müssen:

- Die betroffene Bestandsposition
- Der Gesamtbestand des Produkts
- Die Bestandsübersicht des Lagerplatzes
- Die Grundlage für Einkaufsvorschläge

aktualisiert sein.

* * *

## 5.4 Verbrauch und Entnahme

### FR-CNS-001 – Lebensmittel entnehmen

**Priorität:** MUSS

Die Entnahme erfolgt bevorzugt über das Android-Smartphone.

**Standardablauf:**

1.  Benutzer wählt „Entnehmen“.
2.  Produkt wird per Barcode, Foto oder Suche identifiziert.
3.  Anwendung zeigt den vorhandenen Bestand.
4.  Benutzer gibt die Entnahmemenge ein.
5.  Benutzer bestätigt die Buchung.
6.  Die Anwendung reduziert den Bestand.

Bei einfachen Entnahmen sollen möglichst wenige Eingaben erforderlich sein.

### FR-CNS-002 – Lagerplatz automatisch vorschlagen

**Priorität:** MUSS

Ist ein Produkt nur an einem Lagerplatz vorhanden, wird dieser automatisch vorausgewählt.

Ist das Produkt an mehreren Lagerplätzen vorhanden, zeigt die Anwendung die entsprechenden Bestände zur Auswahl an.

Der Benutzer muss nachvollziehen können, welcher konkrete Bestand reduziert wird.

### FR-CNS-003 – Haltbarkeitsorientierte Entnahme

**Priorität:** MUSS

Bei mehreren Bestandspositionen des gleichen Produkts soll bevorzugt die Position mit dem frühesten relevanten Haltbarkeitsdatum vorgeschlagen werden.

Dieses Verfahren entspricht dem Prinzip:

**First Expired – First Out (FEFO)**

Beispiel:

Zwei Packungen Milch:

- Packung A: haltbar bis 20.11.2026
- Packung B: haltbar bis 27.11.2026

Bei einer Entnahme wird zunächst Packung A vorgeschlagen.

Der Benutzer kann die Auswahl ändern.

### FR-CNS-004 – Teilentnahme

**Priorität:** MUSS

Eine Entnahme kann kleiner als die vorhandene Menge sein.

Beispiel:

Bestand: 1.000 g Zucker  
Entnahme: 250 g  
Neuer Bestand: 750 g

Die Anwendung muss mit Teilmengen und Dezimalwerten umgehen können, soweit die jeweilige Einheit dies erlaubt.

### FR-CNS-005 – Entnahme über mehrere Bestandspositionen

**Priorität:** MUSS

Übersteigt die Entnahmemenge die Menge einer einzelnen Bestandsposition, kann die Entnahme auf mehrere Positionen verteilt werden.

Beispiel:

- Position A: 200 g
- Position B: 500 g
- Entnahme: 350 g

Vorschlag:

- 200 g aus Position A
- 150 g aus Position B

Der Benutzer bestätigt die vorgeschlagene Aufteilung.

### FR-CNS-006 – Bestandsprüfung

**Priorität:** MUSS

Der Bestand darf durch eine reguläre Entnahme nicht negativ werden.

Eine Entnahme oberhalb des verfügbaren Bestands muss abgewiesen werden.

Als Alternative kann eine Bestandskorrektur angeboten werden.

### FR-CNS-007 – Schnellentnahme

**Priorität:** SOLL

Für häufig entnommene Lebensmittel soll eine vereinfachte Bedienung angeboten werden.

Beispiele:

- Zuletzt entnommene Produkte
- Favoriten
- Häufig verwendete Entnahmemengen

Damit sollen typische Entnahmen besonders schnell durchgeführt werden können.

### FR-CNS-008 – Entsorgung

**Priorität:** MUSS

Lebensmittel müssen auch als entsorgt verbucht werden können.

Bei der Entsorgung kann ein Grund angegeben werden:

- Haltbarkeit überschritten
- Verdorben
- Beschädigt
- Sonstiger Grund

Die Entsorgung reduziert den Bestand, wird jedoch nicht als regulärer Verbrauch klassifiziert.

* * *

## 5.5 Umlagerung

### FR-MOV-001 – Bestände umlagern

**Priorität:** MUSS

Lebensmittel können zwischen verschiedenen Lagerplätzen verschoben werden.

Beispiel:

Drei Packungen Milch werden vom Vorratsraum in den Kühlschrank umgelagert.

Ablauf:

1.  Produkt auswählen.
2.  Bestandsposition auswählen.
3.  Menge bestimmen.
4.  Ziellagerplatz auswählen.
5.  Umlagerung bestätigen.

Die Anwendung reduziert den Bestand am Ausgangslagerplatz und erhöht ihn am Ziellagerplatz.

Die gesamte Haushaltsmenge bleibt unverändert.

Eine Umlagerung wird als zusammengehöriger Vorgang protokolliert.

### FR-MOV-002 – Teilmengen umlagern

**Priorität:** MUSS

Auch Teilmengen einer Bestandsposition können umgelagert werden.

Haltbarkeitsinformationen bleiben dabei erhalten.

* * *

# 6\. Mindestbestände und Einkaufsplanung

## 6.1 Grundkonzept

Für jedes Lebensmittel kann ein Mindestbestand definiert werden.

Optional wird zusätzlich ein Zielbestand angegeben.

Beispiel:

| Produkt | Mindestbestand | Zielbestand |
| --- | --- | --- |
| Milch | 2 Liter | 6 Liter |
| Zucker | 1 kg | 3 kg |
| Nudeln | 500 g | 2 kg |
| Eier | 4 Stück | 12 Stück |

Der Mindestbestand beschreibt die untere Grenze.

Der Zielbestand beschreibt die gewünschte Vorratsmenge nach einem Einkauf.

Mindest- und Zielbestände gelten im MVP für den gesamten Haushalt, nicht für einzelne Lagerplätze.

## 6.2 Funktionale Anforderungen

### FR-SHP-001 – Mindestbestand definieren

**Priorität:** MUSS

Für jedes Produkt kann ein Mindestbestand konfiguriert werden.

Ein nicht konfigurierter Mindestbestand wird als „keine Überwachung“ interpretiert.

Er wird nicht automatisch mit null gleichgesetzt.

### FR-SHP-002 – Zielbestand definieren

**Priorität:** MUSS

Optional kann ein Zielbestand konfiguriert werden.

Der Zielbestand darf nicht kleiner als der Mindestbestand sein.

### FR-SHP-003 – Mindestbestand überwachen

**Priorität:** MUSS

Die Anwendung ermittelt anhand des verfügbaren Gesamtbestands, ob ein Produkt seinen Mindestbestand unterschreitet.

Beispiel:

Mindestbestand: 2 Liter Milch  
Aktueller Bestand: 1 Liter

Ergebnis: Produkt ist nachzubestellen.

### FR-SHP-004 – Produkte nahe am Mindestbestand

**Priorität:** MUSS

Die Anwendung zeigt zusätzlich Produkte an, deren Bestand sich einer definierten Mindestbestandsgrenze nähert.

Dazu wird ein konfigurierbarer Warnfaktor eingeführt.

Vorschlag:

**Warnbereich = Mindestbestand × 1,25**

Beispiel:

Mindestbestand: 4 Liter  
Warnbereich: 5 Liter

| Bestand | Status |
| --- | --- |
| 7 Liter | Ausreichend |
| 5 Liter | Nahe am Mindestbestand |
| 4 Liter | Mindestbestand erreicht |
| 3 Liter | Mindestbestand unterschritten |

Der Warnfaktor muss administrativ konfigurierbar sein.

### FR-SHP-005 – Einkaufsliste erstellen

**Priorität:** MUSS

Die Anwendung muss auf Knopfdruck eine Einkaufsliste erstellen beziehungsweise bestehende Einkaufspositionen aktualisieren können.

Die Liste enthält:

- Produktname
- Aktuellen Bestand
- Mindestbestand
- Zielbestand
- Vorgeschlagene Einkaufsmenge
- Status

Produkte unterhalb oder auf dem Mindestbestand werden als Einkaufsbedarf vorgeschlagen.

Produkte nahe am Mindestbestand werden separat als optionale Einkaufspositionen angezeigt.

### FR-SHP-006 – Einkaufsmenge berechnen

**Priorität:** MUSS

Die vorgeschlagene Einkaufsmenge wird aus der Differenz zwischen Zielbestand und verfügbarem Bestand berechnet.

Beispiel:

Produkt: Milch  
Mindestbestand: 2 Liter  
Zielbestand: 6 Liter  
Aktueller Bestand: 1 Liter

Vorgeschlagene Einkaufsmenge: 5 Liter

Ist eine bevorzugte Verpackungsgröße hinterlegt, kann die Menge auf ganze Verpackungen aufgerundet werden.

### FR-SHP-007 – Einkaufsliste manuell bearbeiten

**Priorität:** MUSS

Der Benutzer kann:

- Produkte hinzufügen
- Produkte entfernen
- Einkaufsmengen verändern
- Kommentare ergänzen
- Optionale Produkte übernehmen
- Produkte als gekauft markieren

Manuell hinzugefügte Positionen dürfen nicht durch die automatische Bedarfsermittlung gelöscht werden.

### FR-SHP-008 – Einkaufsliste auf Android verwenden

**Priorität:** MUSS

Die Einkaufsliste muss auf dem Smartphone gut lesbar und bedienbar sein.

Beim Einkauf können Produkte einzeln als gekauft markiert werden.

Der Status wird zentral gespeichert.

### FR-SHP-009 – Gekaufte Produkte einlagern

**Priorität:** MUSS

Gekaufte Produkte sollen aus der Einkaufsliste direkt zur Einlagerung übernommen werden können.

Dabei werden Produkt und Einkaufsmenge vorausgewählt.

Der Benutzer ergänzt gegebenenfalls:

- Tatsächliche Menge
- Haltbarkeitsdatum
- Lagerplatz

Erst nach Bestätigung der Einlagerung wird der Vorratsbestand erhöht.

**Wichtige Geschäftsregel:**

Das Markieren eines Produkts als „gekauft“ verändert den Lagerbestand nicht.

Dadurch wird verhindert, dass gekaufte Lebensmittel bereits vor dem tatsächlichen Einräumen als verfügbar angezeigt werden.

### FR-SHP-010 – Einkaufslistenpositionen aktualisieren

**Priorität:** MUSS

Die automatische Bedarfsermittlung muss wiederholt werden können, ohne doppelte Einkaufspositionen zu erzeugen.

Manuelle Anpassungen und bereits gekaufte Positionen müssen dabei berücksichtigt werden.

Automatische Vorschläge und manuelle Einkaufswünsche sind fachlich zu unterscheiden.

* * *

# 7\. Überwachung der Haltbarkeit

## 7.1 Zielsetzung

Die Anwendung unterstützt dabei, Lebensmittel rechtzeitig zu verbrauchen.

Dabei muss zwischen Mindesthaltbarkeitsdatum und Verbrauchsdatum unterschieden werden.

Das Mindesthaltbarkeitsdatum beschreibt keine automatische Grenze der Genießbarkeit.

Ein überschrittenes Verbrauchsdatum ist dagegen als sicherheitsrelevanter Warnfall zu behandeln.

## 7.2 Anforderungen

### FR-EXP-001 – Haltbarkeitsdaten verwalten

**Priorität:** MUSS

Jede Bestandsposition kann ein eigenes Haltbarkeitsdatum besitzen.

### FR-EXP-002 – Bevorstehenden Ablauf erkennen

**Priorität:** MUSS

Die Anwendung muss Bestandspositionen identifizieren, deren Haltbarkeitsdatum innerhalb einer konfigurierbaren Frist liegt.

Vorgabe:

Warnung sieben Tage vor Ablauf.

Die Frist kann produktspezifisch überschrieben werden.

### FR-EXP-003 – Haltbarkeitsstatus darstellen

**Priorität:** MUSS

Folgende Zustände werden unterschieden:

| Status | Bedeutung |
| --- | --- |
| Grün | Kein aktueller Handlungsbedarf |
| Gelb | Haltbarkeitsdatum nähert sich |
| Rot | Datum erreicht oder überschritten |
| Grau | Kein Datum vorhanden oder unbekannt |

Die visuelle Darstellung muss zusätzlich zur Farbe einen Text beziehungsweise ein Symbol verwenden.

Bei einem überschrittenen Verbrauchsdatum muss eine deutliche Warnung erfolgen, dass das Produkt nicht mehr verwendet werden sollte.

### FR-EXP-004 – Übersicht gefährdeter Lebensmittel

**Priorität:** MUSS

Die Webanwendung enthält eine Übersicht aller Lebensmittel, deren Haltbarkeitsdatum:

- Bald erreicht wird
- Heute erreicht ist
- Bereits überschritten wurde

Die Übersicht ist nach Datum sortierbar und nach Lagerplatz filterbar.

### FR-EXP-005 – Keine automatische Bestandslöschung

**Priorität:** MUSS

Lebensmittel werden nach Überschreiten des Datums nicht automatisch aus dem physischen Bestand gelöscht.

Der Benutzer muss eine Verbrauchs-, Entsorgungs- oder Korrekturbuchung durchführen.

### FR-EXP-006 – Verfügbaren Bestand bestimmen

**Priorität:** MUSS

Für die Einkaufsplanung wird zwischen physisch vorhandenem und fachlich verfügbarem Bestand unterschieden.

Bestände mit überschrittenem Verbrauchsdatum werden nicht als für den Verbrauch verfügbar berücksichtigt.

Bestände mit überschrittenem Mindesthaltbarkeitsdatum bleiben im physischen Bestand sichtbar und werden gesondert gekennzeichnet.

Sie werden nicht allein aufgrund des überschrittenen MHD automatisch abgeschrieben.

* * *

# 8\. Inventur und Bestandskorrekturen

## 8.1 Zielsetzung

Die Anwendung muss eine regelmäßige Kontrolle der tatsächlichen Lebensmittelbestände ermöglichen.

Die Inventur erfolgt vorzugsweise über die Webanwendung.

Einzelne Lagerplätze sollen unabhängig voneinander inventarisiert werden können.

## 8.2 Anforderungen

### FR-INV-001 – Inventur starten

**Priorität:** MUSS

Ein Benutzer kann eine Inventur für:

- Einen einzelnen Lagerplatz
- Einen Lagerplatz einschließlich Unterlagerplätzen
- Den gesamten Haushalt

starten.

### FR-INV-002 – Inventurliste anzeigen

**Priorität:** MUSS

Die Anwendung zeigt die aktuell registrierten Bestände des gewählten Lagerplatzes.

Beispiel:

**Inventur – Vorratsschrank Küche**

| Lebensmittel | Sollbestand | Istbestand |
| --- | --- | --- |
| Zucker | 2.000 g | Eingabe |
| Nudeln | 1.500 g | Eingabe |
| Reis | 1.000 g | Eingabe |
| Mehl | 2.500 g | Eingabe |

Nach Eingabe des tatsächlichen Bestands wird die Differenz berechnet.

### FR-INV-003 – Inventurdifferenzen anzeigen

**Priorität:** MUSS

Die Anwendung muss alle Abweichungen zwischen dokumentiertem und gezähltem Bestand auflisten.

Beispiel:

| Produkt | Soll | Ist | Differenz |
| --- | --- | --- | --- |
| Zucker | 2.000 g | 1.500 g | \-500 g |
| Nudeln | 1.500 g | 1.500 g | 0 g |
| Reis | 1.000 g | 1.250 g | +250 g |

### FR-INV-004 – Inventur abschließen

**Priorität:** MUSS

Vor dem endgültigen Abschluss werden alle festgestellten Differenzen angezeigt.

Der Benutzer bestätigt die Korrekturen.

Das System erzeugt entsprechende Bestandskorrekturbuchungen.

### FR-INV-005 – Nicht erfasste Lebensmittel ergänzen

**Priorität:** MUSS

Während einer Inventur können bisher nicht dokumentierte Lebensmittel ergänzt werden.

Diese werden nach Bestätigung dem Bestand hinzugefügt.

### FR-INV-006 – Inventur unterbrechen

**Priorität:** SOLL

Eine begonnene Inventur kann gespeichert und später fortgesetzt werden.

### FR-INV-007 – Inventurprotokoll

**Priorität:** MUSS

Jede abgeschlossene Inventur wird dokumentiert.

Erfasst werden:

- Inventur-ID
- Start- und Abschlusszeitpunkt
- Benutzer
- Inventarisierte Lagerplätze
- Festgestellte Abweichungen
- Durchgeführte Korrekturen

### FR-INV-008 – Bestand während der Inventur

**Priorität:** MUSS

Die Anwendung muss verhindern, dass zwischen Inventurstart und Inventurabschluss erfolgte Buchungen unbemerkt überschrieben werden.

Bei zwischenzeitlichen Änderungen wird vor Abschluss ein Konflikt angezeigt.

Der Benutzer muss die betroffenen Positionen erneut überprüfen.

### FR-INV-009 – Inventur auf Bestandspositionsebene

**Priorität:** MUSS

Sind für ein Produkt mehrere Haltbarkeitsdaten vorhanden, muss die Inventur diese Bestandspositionen getrennt bearbeiten können.

Nur so bleibt die Bestandsführung einschließlich der Haltbarkeitsinformationen konsistent.

* * *

# 9\. Benutzeroberfläche und Bedienkonzept

## 9.1 Grundanforderungen

Die Anwendung soll eine einfache und intuitive Bedienung ermöglichen.

Die Benutzeroberfläche muss responsiv sein und sich automatisch an verschiedene Bildschirmgrößen anpassen.

Die Darstellung auf Smartphones wird speziell für schnelle Buchungen optimiert.

## 9.2 Webanwendung

Die Webanwendung ist für die vollständige Verwaltung vorgesehen.

### Hauptnavigation

**Dashboard**

Übersicht über:

- Anzahl der registrierten Lebensmittelprodukte
- Anzahl der Bestandspositionen
- Lebensmittel mit niedrigem Bestand
- Lebensmittel mit bevorstehendem Haltbarkeitsdatum
- Aktuelle Einkaufsliste
- Letzte Bestandsbewegungen

**Lebensmittel**

Verwaltung aller Lebensmittelstammdaten.

**Vorräte**

Aktuelle Bestandsübersicht.

**Lagerplätze**

Hierarchische Verwaltung und Bestandsanzeige.

**Einkaufsliste**

Automatisch vorgeschlagene und manuell ergänzte Einkaufspositionen.

**Haltbarkeit**

Übersicht gefährdeter Lebensmittel.

**Inventur**

Durchführung und Dokumentation von Inventuren.

**Historie**

Nachvollziehbarkeit aller Bestandsbewegungen.

**Einstellungen**

Benutzer, Mengeneinheiten, Warnfristen und Systemeinstellungen.

## 9.3 Android-Smartphone

Die mobile Benutzeroberfläche konzentriert sich auf häufige Alltagstätigkeiten.

### Startbildschirm

Große, gut erreichbare Aktionen:

**Einlagern**

**Entnehmen**

**Vorräte**

**Einkaufsliste**

Zusätzlich eine kompakte Anzeige relevanter Warnungen.

## 9.4 Mobile Einlagerungsmaske

Die Einlagerungsmaske besteht aus folgenden Elementen:

**Produkterkennung**

- Barcode scannen
- Foto aufnehmen
- Produkt suchen

**Produktinformationen**

- Produktname
- Produktbild
- Verpackungseinheit

**Buchungsdaten**

- Menge
- Haltbarkeitsdatum
- Lagerplatz

**Aktion**

- Einlagern

Nach erfolgreicher Buchung wird eine Bestätigung angezeigt.

Anschließend kann unmittelbar das nächste Produkt erfasst werden.

## 9.5 Mobile Entnahmemaske

Die Entnahmemaske zeigt:

- Produktname
- Gesamtbestand
- Vorhandene Lagerplätze
- Relevante Haltbarkeitsdaten
- Entnahmemenge

Nach Bestätigung wird der neue Bestand angezeigt.

Die Anwendung soll nach einer Buchung schnell wieder für den nächsten Vorgang bereitstehen.

## 9.6 Bedienbarkeit

Folgende Grundsätze gelten:

- Große Schaltflächen auf Smartphones
- Möglichst wenige Pflichtfelder
- Sinnvolle Vorbelegung häufig verwendeter Werte
- Direkte Rückmeldung nach Buchungen
- Eindeutige Fehlermeldungen
- Keine unnötigen Bestätigungsdialoge
- Suchfunktion von zentralen Ansichten aus erreichbar
- Unterstützung der deutschen Zahlen- und Datumsformate
- Verständliche Darstellung der Mengeneinheiten
- Nutzbarkeit ohne Maus auf Touch-Geräten

* * *

# 10\. Geschäftsregeln

Die folgenden Regeln gelten unabhängig von der konkreten Benutzeroberfläche.

| ID  | Geschäftsregel |
| --- | --- |
| BR-001 | Ein Produkt kann mehrere Bestandspositionen besitzen. |
| BR-002 | Eine Bestandsposition ist eindeutig einem Lagerplatz zugeordnet. |
| BR-003 | Unterschiedliche Haltbarkeitsdaten müssen getrennt verwaltet werden können. |
| BR-004 | Reguläre Entnahmen dürfen keine negativen Bestände erzeugen. |
| BR-005 | Umlagerungen dürfen den Gesamtbestand nicht verändern. |
| BR-006 | Jede Bestandsveränderung muss protokolliert werden. |
| BR-007 | Die Einkaufsliste wird nicht automatisch als Bestand verbucht. |
| BR-008 | Der Bestand wird erst nach erfolgreicher Einlagerung erhöht. |
| BR-009 | Unsichere Produkterkennungen müssen vom Benutzer bestätigt werden. |
| BR-010 | Das Mindesthaltbarkeitsdatum führt nicht zur automatischen Entsorgung. |
| BR-011 | Lebensmittel mit überschrittenem Verbrauchsdatum gelten für die Einkaufsplanung nicht als verfügbar. |
| BR-012 | Ein Lagerplatz mit Beständen darf nicht ersatzlos gelöscht werden. |
| BR-013 | Ein Produkt mit Bestands- oder Bewegungshistorie darf nicht physisch gelöscht werden. |
| BR-014 | Mengen müssen in einer definierten Basiseinheit gespeichert werden. |
| BR-015 | Bestandsänderungen müssen atomar erfolgen. |
| BR-016 | Gleichzeitige Änderungen dürfen keine verlorenen Buchungen verursachen. |
| BR-017 | Doppelt übermittelte Buchungsanforderungen dürfen nicht zu Doppelbuchungen führen. |
| BR-018 | Historische Buchungen dürfen nicht unbemerkt überschrieben werden. |
| BR-019 | Der Benutzer darf bei unsicherer Produkterkennung jederzeit manuell fortfahren. |
| BR-020 | Einkaufspositionen aus automatischen Vorschlägen und manuellen Ergänzungen müssen unterscheidbar sein. |

* * *

# 11\. Technische Architektur

## 11.1 Architekturprinzip

Die Anwendung wird als zentral betriebenes Client-Server-System realisiert.

Das Backend wird innerhalb einer Docker-basierten Umgebung betrieben.

Die Anwendung muss vollständig auf eigener Hardware betrieben werden können.

Beispiele:

- Heimserver
- Mini-PC
- NAS mit geeigneter Container-Unterstützung
- Privater virtueller Server

## 11.2 Vorgeschlagene Architektur

```
                  Benutzer
                     |
          +----------+----------+
          |                     |
          v                     v
   Desktop-Browser       Android-Smartphone
          |                     |
          |                Web-App / PWA
          |                     |
          +----------+----------+
                     |
                   HTTPS
                     |
                     v
             Reverse Proxy
                     |
                     v
             Web-Frontend
                     |
                     v
                  REST API
                     |
       +-------------+-------------+
       |             |             |
       v             v             v
    Produkt-      Bestands-     Erkennungs-
    verwaltung    verwaltung    service
       |             |             |
       +-------------+-------------+
                     |
                     v
              PostgreSQL
                     |
             Datensicherung
```

Ein Hintergrundprozess übernimmt regelmäßig anfallende Aufgaben wie die Auswertung von Haltbarkeitsfristen.

Die Bilderkennung wird über eine austauschbare Service-Schnittstelle angebunden.

## 11.3 Frontend

**Empfehlung:** Responsive Progressive Web App.

Mögliche technische Umsetzung:

- React mit TypeScript
- Alternativ Vue mit TypeScript
- Komponentenbasierte Benutzeroberfläche
- Unterstützung von Kamera und Barcode-Erkennung
- Installation auf Android über den Browser

Die konkrete Frameworkauswahl erfolgt in der technischen Konzeption.

### Vorteile der PWA

- Eine gemeinsame Codebasis
- Nutzung am PC und Smartphone
- Keine zwingende Installation über einen App-Store
- Vereinfachte Updates
- Zugriff auf die Smartphone-Kamera bei geeigneter Browserunterstützung
- Erweiterbarkeit um begrenzte Offline-Funktionen

Für Kamerazugriff und sicherheitsrelevante Browserfunktionen ist insbesondere eine geeignete HTTPS-Konfiguration erforderlich.

Eine vollständige Offline-Verbuchung ist nicht Bestandteil des MVP.

## 11.4 Backend

Das Backend stellt eine dokumentierte REST-API bereit.

Empfohlene technische Eigenschaften:

- Klare Trennung von Fachlogik und Datenzugriff
- Versionierte API
- Einheitliches Fehlerformat
- Validierung sämtlicher Eingaben
- Transaktionale Verarbeitung von Bestandsänderungen
- Protokollierung relevanter Aktionen
- Automatisierte Datenbankmigrationen
- Erweiterbare Produkterkennung

Als Technologien kommen beispielsweise Python/FastAPI oder eine vergleichbare serverseitige Plattform infrage.

Die technische Auswahl muss insbesondere die Anforderungen an Wartbarkeit, Bibliotheksunterstützung und Entwicklungsgeschwindigkeit berücksichtigen.

## 11.5 Datenbank

**Vorgeschlagene Datenbank: PostgreSQL**

Gründe:

- Relationale Datenhaltung
- Transaktionsunterstützung
- Konsistente Bestandsänderungen
- Unterstützung komplexerer Abfragen
- Gute Docker-Unterstützung
- Geeignet für spätere Erweiterungen

## 11.6 Containerisierung

Die Anwendung soll mittels Docker Compose betrieben werden können.

Vorgesehene Komponenten:

| Komponente | Aufgabe |
| --- | --- |
| Frontend | Bereitstellung der Webanwendung |
| Backend | Geschäftslogik und REST-API |
| PostgreSQL | Persistente Datenhaltung |
| Recognition Service | Optionale Bild- und Texterkennung |
| Reverse Proxy | HTTPS und Weiterleitung |

Frontend, Backend und Erkennungsservice dürfen technisch zusammengefasst werden, sofern dadurch keine fachlichen Anforderungen beeinträchtigt werden.

## 11.7 Persistenz

Folgende Daten müssen dauerhaft gespeichert werden:

- Benutzer
- Produktstammdaten
- Produktvarianten und Barcodes
- Produktbilder
- Lagerplätze
- Bestandspositionen
- Bestandsbewegungen
- Mindest- und Zielbestände
- Einkaufslisten
- Inventuren
- Konfigurationen

Das Löschen oder Neuerstellen eines Containers darf keinen Datenverlust verursachen.

Datenbank- und Dateispeicherung müssen deshalb über persistente Volumes beziehungsweise geeignete externe Speichersysteme erfolgen.

## 11.8 Externe Schnittstellen

Die Anwendung soll optionale Integrationen unterstützen.

Vorgesehene Schnittstellentypen:

**Produktdatenservice**

Abfrage von Produktinformationen anhand eines Barcodes.

**Bilderkennungsservice**

Erkennung eines Lebensmittels anhand eines Fotos.

**OCR-Service**

Erkennung von Text und Datumsangaben.

Externe Dienste müssen über klar definierte Adapter angebunden werden.

Ein Ausfall dieser Dienste darf die manuelle Bestandsführung nicht verhindern.

## 11.9 REST-API

Die Schnittstelle muss mindestens folgende fachliche Operationen unterstützen.

| Methode | Endpunkt | Funktion |
| --- | --- | --- |
| GET | `/api/v1/products` | Produkte suchen und auflisten |
| POST | `/api/v1/products` | Produkt anlegen |
| GET | `/api/v1/products/{id}` | Produktinformationen lesen |
| PATCH | `/api/v1/products/{id}` | Produkt ändern |
| GET | `/api/v1/products/barcode/{code}` | Produkt per Barcode suchen |
| POST | `/api/v1/recognition/images` | Foto analysieren |
| GET | `/api/v1/locations` | Lagerplätze abrufen |
| POST | `/api/v1/locations` | Lagerplatz anlegen |
| GET | `/api/v1/stock` | Bestände abfragen |
| POST | `/api/v1/stock/receipts` | Einlagerung buchen |
| POST | `/api/v1/stock/consumptions` | Verbrauch buchen |
| POST | `/api/v1/stock/transfers` | Umlagerung buchen |
| POST | `/api/v1/stock/disposals` | Entsorgung buchen |
| GET | `/api/v1/stock/movements` | Bewegungen abrufen |
| GET | `/api/v1/shopping-list` | Einkaufsliste lesen |
| POST | `/api/v1/shopping-list/recalculate` | Einkaufsvorschläge aktualisieren |
| GET | `/api/v1/expirations` | Haltbarkeitsübersicht abrufen |
| POST | `/api/v1/inventories` | Inventur starten |
| POST | `/api/v1/inventories/{id}/complete` | Inventur abschließen |

Die Tabelle definiert den fachlich benötigten Schnittstellenumfang, noch nicht den endgültigen API-Vertrag.

Für die Entwicklung ist zusätzlich eine OpenAPI-Spezifikation mit Request- und Response-Schemas, Fehlercodes und Berechtigungen zu erstellen.

* * *

# 12\. Vorgeschlagenes relationales Datenmodell

Die folgenden Tabellen bilden eine mögliche Basis für die Implementierung.

## 12.1 Haupttabellen

### households

Haushaltsinformationen.

### users

Benutzer und Zugriffsberechtigungen.

### locations

Hierarchische Lagerplätze.

Wichtige Felder:

- id
- parent_location_id
- name
- description
- location_type
- active

### product_categories

Lebensmittelgruppen.

### products

Lebensmittelstammdaten.

Wichtige Felder:

- id
- name
- brand
- category_id
- base_unit
- minimum_stock
- target_stock
- default_location_id
- expiry_warning_days
- image_reference
- active

### product_variants

Produktvarianten und Verpackungsgrößen.

Wichtige Felder:

- id
- product_id
- barcode
- package_quantity
- package_unit
- base_quantity

### stock_items

Aktuelle Bestandspositionen.

Wichtige Felder:

- id
- product_id
- product_variant_id
- location_id
- quantity
- expiry_date
- expiry_date_type
- received_at
- opened_at
- version

### stock_movements

Historie sämtlicher Bestandsbewegungen.

Wichtige Felder:

- id
- movement_type
- product_id
- source_stock_item_id
- target_stock_item_id
- source_location_id
- target_location_id
- quantity
- created_at
- created_by
- reason
- transaction_id

### shopping_lists

Einkaufslisten.

### shopping_list_items

Positionen innerhalb einer Einkaufsliste.

Zusätzliche Informationen:

- Herkunft der Position
- Vorgeschlagene Menge
- Manuell angepasste Menge
- Status
- Bereits eingelagerte Menge

### inventories

Inventurvorgänge.

### inventory_items

Gezählte Bestandspositionen und festgestellte Differenzen.

## 12.2 Datenintegrität

Die Datenbank muss sicherstellen, dass:

- Fremdschlüssel gültig sind.
- Mengen nicht versehentlich negativ werden.
- Unzulässige Mengeneinheiten verhindert werden.
- Kritische Bestandsänderungen transaktional erfolgen.
- Gleichzeitige Buchungen korrekt verarbeitet werden.
- Historische Bestandsbewegungen erhalten bleiben.
- Produktvarianten nicht mit widersprüchlichen Barcodes verknüpft werden.

Für Bestandspositionen ist ein geeignetes Verfahren zur Behandlung gleichzeitiger Änderungen vorzusehen, beispielsweise optimistisches Locking über eine Versionsnummer.

* * *

# 13\. Nichtfunktionale Anforderungen

## 13.1 Performance

### NFR-PERF-001

Die Anwendung soll bei typischer Haushaltsgröße flüssig bedienbar sein.

Als Referenzgröße gelten:

- Bis zu 5 Benutzer
- Bis zu 10.000 Lebensmittelprodukte
- Bis zu 50.000 Bestandspositionen
- Bis zu 1.000.000 historische Bestandsbewegungen

Diese Werte dienen als technische Auslegungs- und Testgrößen, nicht als erwartete Haushaltsgröße.

### NFR-PERF-002

Normale Lese- und Buchungsoperationen sollen innerhalb des lokalen Netzwerks bei üblicher Hardware im Regelfall innerhalb von zwei Sekunden beantwortet werden.

Für externe Bild- und Produkterkennung gelten separate Leistungsziele.

## 13.2 Zuverlässigkeit

### NFR-REL-001

Alle Bestandsbuchungen müssen transaktional erfolgen.

Eine fehlgeschlagene Buchung darf keine teilweise aktualisierten Bestände hinterlassen.

### NFR-REL-002

Doppelte Anfragen durch wiederholtes Antippen, Netzwerkwiederholungen oder Verbindungsprobleme dürfen keine doppelten Buchungen erzeugen.

### NFR-REL-003

Bei nicht verfügbarer Netzwerkverbindung muss die Anwendung deutlich anzeigen, dass keine verbindliche Buchung möglich ist.

Eine Buchung darf nicht als erfolgreich dargestellt werden, wenn sie nicht gespeichert wurde.

## 13.3 Sicherheit

### NFR-SEC-001

Zugriff auf die Anwendung erfolgt nach Authentifizierung.

### NFR-SEC-002

Passwörter dürfen nicht im Klartext gespeichert werden.

### NFR-SEC-003

Berechtigungen müssen serverseitig überprüft werden.

### NFR-SEC-004

Der Zugriff über das Netzwerk soll verschlüsselt per HTTPS erfolgen.

### NFR-SEC-005

Zugangsdaten für externe Dienste dürfen nicht im Quellcode gespeichert werden.

### NFR-SEC-006

Die Anwendung muss gegen übliche Webangriffe abgesichert werden.

Dazu gehören insbesondere:

- Unberechtigte API-Zugriffe
- SQL-Injection
- Cross-Site-Scripting
- Missbrauch von Datei-Uploads
- Unzulässige Zugriffe auf fremde oder geschützte Ressourcen

## 13.4 Datenschutz

### NFR-DAT-001

Sämtliche Haushalts- und Bestandsdaten können lokal gespeichert werden.

### NFR-DAT-002

Eine externe Übermittlung von Bildern oder Bestandsdaten darf nur über bewusst konfigurierte Integrationen erfolgen.

### NFR-DAT-003

Die Anwendung muss transparent machen, wenn für eine Funktion externe Dienste verwendet werden.

### NFR-DAT-004

Temporär verarbeitete Produktbilder sollen nicht unbegrenzt gespeichert werden.

## 13.5 Datensicherung

### NFR-BCK-001

Die Anwendung muss eine automatisierbare Datensicherung ermöglichen.

### NFR-BCK-002

Gesichert werden müssen:

- Datenbank
- Produktbilder
- Anwendungskonfiguration, soweit erforderlich

### NFR-BCK-003

Eine dokumentierte Wiederherstellungsprozedur muss vorhanden sein.

### NFR-BCK-004

Die Wiederherstellung aus einer Datensicherung muss vor Produktivsetzung erfolgreich getestet worden sein.

Als Standard wird eine tägliche Datensicherung vorgeschlagen.

## 13.6 Wartbarkeit

### NFR-MNT-001

Die Anwendung muss modular aufgebaut sein.

### NFR-MNT-002

Backend und Frontend müssen unabhängig voneinander testbar sein.

### NFR-MNT-003

Datenbankänderungen erfolgen über versionierte Migrationen.

### NFR-MNT-004

Die REST-API muss dokumentiert sein.

### NFR-MNT-005

Die Anwendung muss aussagekräftige technische Logs bereitstellen.

### NFR-MNT-006

Anwendungsupdates müssen möglich sein, ohne vorhandene Nutzdaten zu verlieren.

## 13.7 Kompatibilität

Die Anwendung soll aktuelle Versionen gängiger Desktop-Browser unterstützen.

Für Smartphones wird Android mit einem aktuellen Chromium-basierten Browser als primäre Zielplattform festgelegt.

Weitere Browser können unterstützt werden, sofern die benötigten Funktionen verfügbar sind.

* * *

# 14\. Fachliche Anwendungsszenarien und Abnahmetests

Die folgenden Szenarien beschreiben das erwartete Verhalten aus Sicht des Anwenders.

Sie dienen als Grundlage für spätere automatisierte und manuelle Tests.

## AC-001 – Bekanntes Produkt einlagern

**Ausgangslage:**

Das Produkt „Milch 1 Liter“ existiert im Produktkatalog.

Der zugehörige Barcode ist bekannt.

**Wenn**

der Benutzer den Barcode scannt, drei Packungen auswählt, ein Haltbarkeitsdatum angibt und den Kühlschrank als Lagerplatz bestätigt,

**dann**

muss die Anwendung:

- Das korrekte Produkt identifizieren
- Drei Liter einlagern
- Das Haltbarkeitsdatum speichern
- Den Kühlschrank zuordnen
- Den Gesamtbestand aktualisieren
- Eine Einlagerungsbewegung protokollieren

## AC-002 – Unbekanntes Produkt erfassen

**Ausgangslage:**

Ein Barcode ist in der Anwendung unbekannt.

**Wenn**

der Benutzer den Barcode scannt,

**dann**

muss die Anwendung eine Produktsuche über konfigurierte Datenquellen versuchen können.

Ist kein Produkt ermittelbar, muss die manuelle Erfassung angeboten werden.

Nach Anlage kann das Produkt eingelagert werden.

Der erkannte Barcode bleibt mit der neuen Produktvariante verknüpft.

## AC-003 – Produkt anhand eines Fotos erkennen

**Ausgangslage:**

Ein Produkt besitzt keinen lesbaren Barcode.

**Wenn**

der Benutzer das Produkt fotografiert,

**dann**

muss die Anwendung versuchen, das Produkt zu identifizieren.

Bei mehreren Treffern werden Auswahlmöglichkeiten angeboten.

Bei keinem Treffer ist eine manuelle Produktauswahl möglich.

Erst nach Bestätigung darf eine Buchung erfolgen.

## AC-004 – Teilmenge entnehmen

**Ausgangslage:**

Im Vorratsschrank befinden sich 1.000 g Zucker.

**Wenn**

der Benutzer 250 g entnimmt,

**dann**

muss der neue Bestand 750 g betragen.

Die Entnahme muss in der Historie sichtbar sein.

## AC-005 – Entnahme nach Haltbarkeit

**Ausgangslage:**

Im Kühlschrank befinden sich:

- Ein Liter Milch mit MHD 20.11.2026
- Ein Liter Milch mit MHD 27.11.2026

**Wenn**

der Benutzer einen Liter Milch entnimmt,

**dann**

muss die Anwendung bevorzugt die Position mit MHD 20.11.2026 vorschlagen.

Nach Bestätigung verbleibt die spätere Position.

## AC-006 – Mindestbestand unterschritten

**Ausgangslage:**

Milch besitzt:

- Mindestbestand: 2 Liter
- Zielbestand: 6 Liter
- Aktueller verfügbarer Bestand: 1 Liter

**Wenn**

der Benutzer die Einkaufsliste aktualisiert,

**dann**

muss die Anwendung Milch als Einkaufsbedarf vorschlagen.

Die vorgeschlagene Einkaufsmenge beträgt fünf Liter.

## AC-007 – Produkt nahe am Mindestbestand

**Ausgangslage:**

Ein Produkt besitzt:

- Mindestbestand: 4 Stück
- Warnfaktor: 1,25
- Aktueller Bestand: 5 Stück

**Wenn**

die Einkaufsplanung ausgeführt wird,

**dann**

muss das Produkt als optionaler Einkaufsbedarf erscheinen.

Es darf nicht mit Produkten verwechselt werden, deren Mindestbestand erreicht oder unterschritten wurde.

## AC-008 – Einkauf verbuchen

**Ausgangslage:**

Fünf Liter Milch stehen auf der Einkaufsliste.

**Wenn**

der Benutzer die Milch als gekauft markiert,

**dann**

darf der Lagerbestand noch nicht steigen.

**Erst wenn**

der Benutzer die Einlagerung bestätigt,

**dann**

muss die tatsächlich eingelagerte Menge dem Bestand hinzugefügt werden.

## AC-009 – Umlagerung

**Ausgangslage:**

Im Vorratsraum liegen sechs Liter Milch.

**Wenn**

drei Liter in den Kühlschrank umgelagert werden,

**dann**

muss der Vorratsraum drei Liter weniger und der Kühlschrank drei Liter mehr enthalten.

Der Gesamtbestand bleibt unverändert.

## AC-010 – Inventurdifferenz

**Ausgangslage:**

Das System führt 2.000 g Zucker.

Bei der Inventur werden 1.500 g festgestellt.

**Wenn**

der Benutzer die Inventur abschließt,

**dann**

muss:

- Die Differenz von -500 g angezeigt werden
- Nach Bestätigung der Bestand auf 1.500 g korrigiert werden
- Eine Inventurkorrektur dokumentiert werden

## AC-011 – Haltbarkeitswarnung

**Ausgangslage:**

Ein Lebensmittel besitzt ein Haltbarkeitsdatum, das innerhalb der nächsten sieben Tage liegt.

**Wenn**

der Benutzer die Haltbarkeitsübersicht öffnet,

**dann**

muss das Produkt mit Menge, Lagerplatz und Datum angezeigt werden.

## AC-012 – Gleichzeitige Entnahmen

**Ausgangslage:**

Von einem Produkt ist nur noch ein Stück vorhanden.

Zwei Benutzer versuchen nahezu gleichzeitig, jeweils ein Stück zu entnehmen.

**Wenn**

beide Buchungen an das Backend übermittelt werden,

**dann**

darf höchstens eine Buchung erfolgreich sein.

Die zweite Buchung muss mit einer verständlichen Meldung abgewiesen werden.

Ein negativer Bestand darf nicht entstehen.

## AC-013 – Doppelte Buchungsanfrage

**Ausgangslage:**

Ein Benutzer erfasst zwei Packungen eines Produkts.

**Wenn**

die identische Buchungsanfrage aufgrund eines Netzwerkfehlers erneut übertragen wird,

**dann**

darf der Bestand nur einmal um die entsprechende Menge erhöht werden.

## AC-014 – Inventurkonflikt

**Ausgangslage:**

Eine Inventur wurde gestartet.

Währenddessen entnimmt ein anderer Benutzer ein Produkt.

**Wenn**

die Inventur abgeschlossen werden soll,

**dann**

muss die Anwendung die zwischenzeitliche Bestandsänderung erkennen.

Eine unbemerkte Überschreibung des neueren Bestands darf nicht erfolgen.

* * *

# 15\. Qualitätssicherung und Teststrategie

## 15.1 Grundsatz

Die Qualitätssicherung beginnt mit der Implementierung der ersten fachlichen Funktionen.

Besonders kritisch ist die Korrektheit der Bestandsführung.

Eine fehlerhafte Bestandsbuchung darf weder zu Datenverlust noch zu dauerhaft inkonsistenten Beständen führen.

## 15.2 Unit-Tests

Unit-Tests müssen insbesondere folgende Funktionen absichern:

- Umrechnung von Mengeneinheiten
- Mindestbestandsberechnung
- Zielbestandsberechnung
- Rundung von Einkaufsmengen
- Haltbarkeitsbewertung
- FEFO-Auswahl
- Aufteilung von Entnahmen auf Bestandspositionen
- Berechnung von Inventurdifferenzen
- Validierung von Buchungsmengen

## 15.3 Integrationstests

Integrationstests prüfen insbesondere:

- Bestandsbuchungen mit Datenbanktransaktionen
- Gleichzeitige Bestandsänderungen
- Erzeugung von Bewegungsprotokollen
- Produkt- und Barcodezuordnungen
- Aktualisierung der Einkaufsliste
- Abschluss von Inventuren
- Fehlerbehandlung externer Produktservices
- API-Berechtigungen

## 15.4 End-to-End-Tests

Folgende fachliche Abläufe müssen vollständig getestet werden:

1.  Produkt scannen und einlagern
2.  Unbekanntes Produkt anlegen und einlagern
3.  Produkt über Foto identifizieren und einlagern
4.  Produkt entnehmen
5.  Produkt zwischen Lagerplätzen verschieben
6.  Mindestbestand unterschreiten und Einkaufsbedarf erzeugen
7.  Einkaufsliste bearbeiten und Produkte anschließend einlagern
8.  Inventur durchführen und Differenzen korrigieren
9.  Haltbarkeitswarnungen anzeigen
10. Fehlgeschlagene Buchung ohne inkonsistenten Bestand behandeln

## 15.5 Mobile Tests

Die Anwendung muss auf realen Android-Geräten überprüft werden.

Testschwerpunkte:

- Kamerazugriff
- Barcode-Erkennung
- Fotoaufnahme
- Bedienbarkeit mit einer Hand
- Unterschiedliche Displaygrößen
- Verarbeitung langsamer Netzwerkverbindungen
- Wiederherstellung nach Verbindungsabbruch
- Verständliche Fehlermeldungen

## 15.6 Definition of Done

Eine Funktion gilt als fertig, wenn:

- Die definierten fachlichen Anforderungen umgesetzt sind.
- Die Akzeptanzkriterien erfüllt sind.
- Relevante Unit-Tests vorhanden sind.
- Erforderliche Integrationstests erfolgreich sind.
- Die API dokumentiert ist.
- Fehlerfälle behandelt werden.
- Die Funktion auf den vorgesehenen Endgeräten getestet wurde.
- Änderungen an Datenbankstrukturen migrierbar sind.
- Keine bekannten kritischen Fehler offen sind.
- Der Product Owner die fachliche Umsetzung abgenommen hat.

* * *

# 16\. Entwicklungsschritte und Umsetzungsplanung

Die Entwicklung wird in fachlich zusammenhängende Ausbaustufen gegliedert.

## Phase 1 – Technische Basis

**Ziel:** Betriebsfähige Anwendung mit Datenhaltung.

Umfang:

- Repository und Projektstruktur
- Docker-Compose-Umgebung
- PostgreSQL
- Backend-Grundstruktur
- Web-Frontend
- Benutzeranmeldung
- Datenbankmigrationen
- Grundlegende API-Dokumentation
- Automatisierte Tests
- Datensicherungskonzept

**Ergebnis:**

Die Anwendung kann lokal gestartet werden und besitzt eine funktionsfähige technische Grundlage.

## Phase 2 – Lebensmittel und Lagerplätze

**Ziel:** Verwaltung des Lebensmittelkatalogs und der Lagerhierarchie.

Umfang:

- Produktkategorien
- Lebensmittelstammdaten
- Produktvarianten
- Lagerplatzverwaltung
- Suchfunktionen
- Manuelle Einlagerung
- Bestandsübersicht

**Ergebnis:**

Lebensmittel können manuell erfasst und verschiedenen Lagerplätzen zugeordnet werden.

## Phase 3 – Bestandsbewegungen

**Ziel:** Vollständige grundlegende Bestandsverwaltung.

Umfang:

- Entnahmen
- Teilentnahmen
- FEFO-Unterstützung
- Umlagerungen
- Entsorgung
- Bewegungshistorie
- Transaktionale Bestandsverarbeitung
- Schutz vor Doppelbuchungen

**Ergebnis:**

Ein Haushalt kann seine Vorräte über die Webanwendung vollständig verwalten.

## Phase 4 – Mobile Erfassung

**Ziel:** Alltagstaugliche Nutzung über Android.

Umfang:

- Mobile Benutzeroberfläche
- Barcode-Erkennung
- Produktidentifikation
- Einlagerung per Smartphone
- Entnahme per Smartphone
- Kamerabasierte Produkterkennung
- Optimierte Schnellerfassung

**Ergebnis:**

Einlagerungen und Entnahmen können direkt am Lagerplatz über das Smartphone durchgeführt werden.

## Phase 5 – Intelligente Bestandsunterstützung

**Ziel:** Einkaufsplanung und Haltbarkeitsüberwachung.

Umfang:

- Mindestbestände
- Zielbestände
- Warnschwellen
- Automatische Einkaufsvorschläge
- Manuelle Einkaufslisten
- Mobile Einkaufslisten
- Haltbarkeitsüberwachung
- Dashboard

**Ergebnis:**

Die Anwendung unterstützt aktiv die Einkaufsplanung und die rechtzeitige Verwendung vorhandener Lebensmittel.

## Phase 6 – Inventur und Produktivsetzung

**Ziel:** Vollständiger MVP.

Umfang:

- Inventurfunktionen
- Bestandskorrekturen
- Inventurhistorie
- Abschließende Integrationstests
- Mobile Praxistests
- Sicherheitsprüfung
- Backup- und Restore-Test
- Dokumentation
- Deployment

**Ergebnis:**

Eine vollständig nutzbare erste Version der Lebensmittelverwaltung.

* * *

# 17\. Offene fachliche und technische Entscheidungen

Vor der Umsetzung müssen folgende Punkte verbindlich entschieden werden.

| ID  | Entscheidung | Aktueller Vorschlag |
| --- | --- | --- |
| DEC-001 | Native Android-App oder PWA? | PWA für den MVP |
| DEC-002 | Anzahl Haushalte | Ein Haushalt |
| DEC-003 | Mehrere Benutzer | Ja  |
| DEC-004 | Backend-Technologie | Python/FastAPI oder vergleichbar |
| DEC-005 | Datenbank | PostgreSQL |
| DEC-006 | Frontend-Technologie | React oder Vue mit TypeScript |
| DEC-007 | Produkterkennung | Barcode, OCR und ergänzende Bilderkennung |
| DEC-008 | Externe Produktdatenbank | Optional, austauschbar |
| DEC-009 | Betrieb außerhalb des Heimnetzwerks | Über abgesicherten Zugang |
| DEC-010 | Offline-Verfügbarkeit | Nicht im MVP |
| DEC-011 | Mengeneinheiten | Stück, Gramm, Milliliter als Basiseinheiten |
| DEC-012 | Lagerplatzmodell | Hierarchisch |
| DEC-013 | Bestandsmodell | Einzelne Positionen nach Lagerplatz und Haltbarkeitsdatum |
| DEC-014 | Mindestbestände | Produktbezogen über gesamten Haushalt |
| DEC-015 | Zielbestände | Optional pro Produkt |
| DEC-016 | Warnfaktor Mindestbestand | Standard 1,25 |
| DEC-017 | Haltbarkeitswarnung | Standard sieben Tage |
| DEC-018 | Einkaufslisten | Gemeinsame aktive Liste |
| DEC-019 | Inventur | Lagerplatzweise und vollständig |
| DEC-020 | Datensicherung | Täglich, automatisierbar |
| DEC-021 | Speicherung von Produktbildern | Lokal, mit konfigurierbarer Aufbewahrung |
| DEC-022 | Bilderkennung | Technologieauswahl nach Machbarkeitsnachweis |

* * *

# 18\. Wesentliche Projektrisiken

## R-001 – Zuverlässigkeit der Bilderkennung

**Risiko: Hoch**

Eine Bilderkennung kann nicht garantieren, beliebige Produkte oder Verpackungen eindeutig zu identifizieren.

Besonders problematisch sind:

- Ähnlich aussehende Verpackungen
- Lose Lebensmittel
- Fehlende Beschriftungen
- Schlechte Lichtverhältnisse
- Bereits geöffnete Verpackungen

**Maßnahme:**

Frühzeitiger Machbarkeitsnachweis. Kombination aus Barcode, OCR, Bilderkennung und manueller Bestätigung.

## R-002 – Unvollständige Verbrauchsbuchungen

**Risiko: Hoch**

Benutzer könnten vergessen, verbrauchte Lebensmittel auszubuchen.

Dadurch entstehen Abweichungen zwischen tatsächlichem und dokumentiertem Bestand.

**Maßnahme:**

Entnahme konsequent vereinfachen. Favoriten und vorbelegte Entnahmemengen verwenden. Regelmäßige Inventuren ermöglichen.

## R-003 – Falsche Mengeneinheiten

**Risiko: Mittel**

Bei Produkten mit verschiedenen Verpackungsgrößen können Umrechnungsfehler auftreten.

**Maßnahme:**

Einheitliches Basiseinheitenmodell und automatisierte Tests der Mengenumrechnung.

## R-004 – Unzuverlässige externe Produktdaten

**Risiko: Mittel**

Externe Produktdatenbanken können unvollständige oder falsche Informationen enthalten.

**Maßnahme:**

Externe Daten nur als Vorschlag verwenden. Lokale Korrekturmöglichkeiten bereitstellen.

## R-005 – Gleichzeitige Bestandsänderungen

**Risiko: Mittel**

Mehrere Benutzer könnten gleichzeitig denselben Bestand verändern.

**Maßnahme:**

Datenbanktransaktionen, Konflikterkennung und Schutz vor Doppelbuchungen.

## R-006 – Datenverlust

**Risiko: Hoch**

Ein Datenbank- oder Hardwarefehler könnte den gesamten Vorratsbestand und dessen Historie zerstören.

**Maßnahme:**

Automatische Datensicherungen und getestetes Wiederherstellungsverfahren.

## R-007 – Zu hoher Erfassungsaufwand

**Risiko: Hoch**

Wenn Einlagerungen und Entnahmen zu umständlich sind, wird die Anwendung im Alltag nicht konsequent verwendet.

**Maßnahme:**

Mobile Kernabläufe frühzeitig mit realen Benutzern testen. Anzahl notwendiger Eingaben minimieren. Schnelle manuelle Alternativen bereitstellen.

* * *

# 19\. Abnahmekriterien für den MVP

Der MVP ist fachlich abnahmefähig, wenn folgende Voraussetzungen erfüllt sind:

**1\. Produktverwaltung**

Lebensmittel können angelegt, bearbeitet, gesucht und kategorisiert werden.

**2\. Lagerplatzverwaltung**

Lagerplätze können hierarchisch verwaltet und Bestände eindeutig zugeordnet werden.

**3\. Einlagerung**

Lebensmittel können einschließlich Menge, Haltbarkeitsdatum und Lagerplatz eingelagert werden.

**4\. Barcode-Erkennung**

Bekannte Produkte können per Barcode identifiziert und anschließend gebucht werden.

**5\. Bilderkennung**

Produktfotos können analysiert werden. Die Anwendung liefert geeignete Produktvorschläge, soweit eine Erkennung möglich ist, und bietet jederzeit eine manuelle Alternative.

**6\. Entnahme**

Lebensmittel können vollständig oder teilweise entnommen werden. Negative Bestände werden verhindert.

**7\. Umlagerung**

Bestände können zwischen Lagerplätzen verschoben werden, ohne den Gesamtbestand zu verändern.

**8\. Einkaufsplanung**

Mindestbestände und Zielbestände werden berücksichtigt. Eine bearbeitbare Einkaufsliste kann erstellt werden.

**9\. Haltbarkeitsüberwachung**

Produkte mit bevorstehendem oder überschrittenem Haltbarkeitsdatum werden korrekt angezeigt.

**10\. Inventur**

Bestände können überprüft und durch dokumentierte Korrekturen angepasst werden.

**11\. Android-Nutzung**

Die wesentlichen Alltagsfunktionen können über ein Android-Smartphone genutzt werden.

**12\. Datenintegrität**

Einlagerungen, Entnahmen, Umlagerungen und Korrekturen verändern Bestände konsistent und nachvollziehbar.

**13\. Sicherheit**

Die Anwendung besitzt eine funktionierende Authentifizierung und überprüft Zugriffsberechtigungen.

**14\. Betrieb**

Die Anwendung ist über Docker Compose installierbar und verwendet persistente Datenspeicherung.

**15\. Wiederherstellung**

Eine erfolgreiche Wiederherstellung der Daten aus einer Sicherung wurde nachgewiesen.

**16\. Qualitätssicherung**

Die definierten kritischen fachlichen Abnahmetests wurden erfolgreich durchgeführt.

* * *

# 20\. Zusammenfassung

Die Lebensmittelverwaltung wird als zentrale, selbst gehostete Haushaltsanwendung realisiert.

Der fachliche Kern besteht aus einer verlässlichen Verwaltung von Produkten, Lagerplätzen, Bestandspositionen und Bestandsbewegungen.

Die Bedienung soll im Alltag insbesondere durch Smartphone-Kameras und möglichst einfache Buchungsvorgänge unterstützt werden.

Darauf aufbauend ermöglichen Mindestbestände, Einkaufslisten und Haltbarkeitsüberwachung eine aktive Unterstützung der Haushaltsführung.

Die technische Architektur wird modular und erweiterbar ausgelegt, um später zusätzliche Funktionen wie Rezeptverwaltung, automatische Verbrauchsbuchungen oder weitergehende KI-Unterstützung ergänzen zu können.

**Oberste Produktpriorität ist die Kombination aus einfacher Bedienung und korrekter Bestandsführung.**

Die Anwendung soll im Alltag so wenig Aufwand wie möglich verursachen, gleichzeitig aber zuverlässige und nachvollziehbare Bestandsinformationen bereitstellen.