# Produktivsetzung – Abnahmeprotokoll (Phase 6)

Stand: 2026-11-15, Version 0.2.0 (in Vorbereitung)

Dieses Dokument hält fest, was vor der produktiven Nutzung geprüft wurde (Spez. Kap. 15,
Phase 6), und was noch offen ist.

## 1. Wiederherstellungstest (NFR-BCK-004)

**Ergebnis: bestanden.**

| | |
| --- | --- |
| Datum | 15.11.2026 |
| Sicherung | echte Sicherung der Live-Installation (`lmv-20261115-155009`), unmittelbar vorher erstellt |
| Ziel | eigener, leerer Stack (`docker compose -p lmv-restore`, eigene Volumes und Ports), Release-Images 0.1.0 |
| Vorgehen | exakt nach [BETRIEB.md](BETRIEB.md#wiederherstellung): `stop backend web` → `restore.sh` → `start backend web` |
| Prüfung Datenbank | alle 13 Tabellen: Zeilenzahl und MD5-Prüfsumme über sämtliche Zeileninhalte, Live gegen Wiederherstellung |
| Prüfung Bilder | SHA-256 über alle Dateien im Bildverzeichnis |

Ergebnis: Datenbank **identisch** (alle Tabellen, alle Inhalte), Produktbilder **bitgleich**
(2 Dateien). Alle Dienste liefen danach gesund. Die Live-Installation wurde dabei nur gelesen.

Hinweise:

- Gesichert werden Datenbank und Bilder. Die **`.env`** (Passwörter, Schlüssel) ist nicht Teil
  der Sicherung und muss getrennt aufbewahrt werden, etwa in einem Passwortmanager. Für eine
  Wiederherstellung auf einem neuen Rechner wird sie nicht zwingend gebraucht – eine neue `.env`
  genügt, angemeldete Geräte müssen sich dann neu anmelden.
- Sicherungen liegen auf derselben Platte wie die Daten. Gegen Plattendefekte hilft nur eine
  regelmäßige Kopie auf ein anderes Gerät (R-006).

## 2. Sicherheitsprüfung (NFR-SEC-001…006)

Unabhängige Prüfung des gesamten Codes mit eigenen Prüftests, u. a. 24 gezielten Zugriffen
eines fremden Haushalts auf Produkte, Varianten, Bilder, Lagerplätze, Bestandspositionen,
Buchungen, Einkaufslisten, Inventuren und Benutzer.

**Unauffällig:** Authentifizierung jedes Endpunkts, Passwörter mit Argon2id, serverseitige
Rechteprüfung und Mandantentrennung (alle 24 Fremdzugriffe abgewiesen), SQL-Injection,
XSS und Sicherheitsheader (strikte CSP, HSTS), CSRF (`SameSite=Strict`), HTTPS, keine Secrets
im Repository, Idempotenzschlüssel je Benutzer, Bild-Proxy nur zu Open Food Facts (SSRF).

| # | Befund | Schwere | Status |
| --- | --- | --- | --- |
| 1 | Keine Begrenzung von Login-Fehlversuchen | mittel | **behoben**: ab dem 5. Fehlversuch je Benutzername Wartezeit 30 s, verdoppelt bis 15 min (429) |
| 3 | Stark komprimierte Bilder mit sehr vielen Pixeln konnten den Speicher füllen | niedrig | **behoben**: Pixelgrenze (40 MP) vor dem Dekodieren, JPEG wird verkleinert dekodiert |
| 5 | API-Dokumentation ohne Anmeldung abrufbar | niedrig | **behoben**: in der Installation standardmäßig aus (`LMV_API_DOCS`) |
| 6 | Ports standardmäßig auf allen Schnittstellen | niedrig | **dokumentiert**: `LMV_BIND_ADDRESS` = Tailscale-IP empfohlen; Live-Installation: offen, siehe 5. |
| 2 | Abmelden macht das Anmeldetoken nicht serverseitig ungültig (Gültigkeit 14 Tage) | niedrig | offen, Entscheidung siehe 5. |
| 4 | Mitglieder dürfen Produktbilder ersetzen und Varianten anlegen, Löschen nur Admins | niedrig | offen, Entscheidung siehe 5. |
| 7 | Standard-Signaturschlüssel, wenn das Backend ohne Compose läuft | niedrig | akzeptiert: Compose erzwingt einen eigenen Schlüssel; betrifft nur lokale Entwicklung |
| 8 | Härtung: Caddy läuft als root mit Zugriff auf den Tailscale-Socket; Sicherungen sind für lokale Benutzer lesbar | niedrig | akzeptiert für 0.2.0: das Home-Verzeichnis ist für andere Benutzer gesperrt; Härtung der Container als spätere Verbesserung |

## 3. End-to-End-Tests (Spez. 15.4)

Browsertest `e2e/mobile_smoke.py` auf einem simulierten Android-Gerät (Pixel 7), 26 Schritte:

| Ablauf | Abgedeckt |
| --- | --- |
| 1 Produkt scannen und einlagern | ja (Kamera-Barcode per Testvideo) |
| 2 Unbekanntes Produkt anlegen und einlagern | ja |
| 3 Produkt über Foto identifizieren | entfällt – zurückgestellt (DEC-030) |
| 4 Produkt entnehmen | ja (FEFO, Waage) |
| 5 Zwischen Lagerplätzen verschieben | ja (inkl. Storno) |
| 6 Mindestbestand unterschreiten, Einkaufsbedarf | ja |
| 7 Einkaufsliste bearbeiten und einlagern | ja |
| 8 Inventur mit Differenzen | ja (inkl. Buchung während der Inventur) |
| 9 Haltbarkeitswarnungen | ja |
| 10 Fehlgeschlagene Buchung ohne inkonsistenten Bestand | ja (veralteter Vorschlag → Ablehnung → Bestand konsistent → erneuter Versuch) |

Der Test zu Ablauf 10 hat einen Fehler gefunden, der behoben ist: Nach einer abgelehnten
Buchung lud die Entnahmemaske Bestand und Vorschlag nicht neu, jeder weitere Versuch wurde
ebenfalls abgelehnt.

Backend: 185 automatisierte Tests gegen PostgreSQL; Frontend: 18 Tests.

## 4. Test auf echten Geräten (Spez. 15.5) – offen

Muss der Product Owner auf dem eigenen Android-Gerät durchführen:

- [ ] Kamerazugriff und Barcode-Scan mit echten Verpackungen
- [ ] App über *Zum Startbildschirm hinzufügen* installieren und starten
- [ ] Einlagern, Entnehmen, Einkaufsliste im Laden mit einer Hand
- [ ] Schlechter Empfang / kurzer Verbindungsabbruch: verständliche Meldung, keine doppelte Buchung
- [ ] Unterwegs über Tailscale (mobile Daten statt WLAN)

## 5. Offene Entscheidungen

1. **Abmelden (Befund 2):** Soll „Abmelden“ das Gerät sicher abmelden? Einfachste Lösung:
   Abmelden meldet *alle* Geräte dieses Benutzers ab. Alternative: Gültigkeit verkürzen
   (z. B. 7 statt 14 Tage).
2. **Rechte der Mitglieder (Befund 4):** Dürfen Mitglieder Produktbilder ersetzen und Varianten
   anlegen (heute ja), oder nur Administratoren?
3. **Live-Installation nur über Tailscale erreichbar machen (Befund 6):** `LMV_BIND_ADDRESS`
   auf die Tailscale-IP setzen. Danach ist die App aus dem WLAN nur noch über Tailscale
   erreichbar.

## 6. Definition of Done (Spez. 15.6)

| Kriterium | Stand |
| --- | --- |
| Fachliche Anforderungen umgesetzt | ja, außer Fotoerkennung (DEC-030, zurückgestellt) |
| Unit- und Integrationstests | ja (siehe 3.) |
| API dokumentiert | ja (OpenAPI, bei Bedarf über `LMV_API_DOCS` einschaltbar) |
| Fehlerfälle behandelt | ja |
| Auf vorgesehenen Endgeräten getestet | **offen** (siehe 4.) |
| Datenbankänderungen migrierbar | ja (Alembic, Prüfung in der CI) |
| Keine bekannten kritischen Fehler | ja |
| Fachliche Abnahme durch den Product Owner | **offen** |
