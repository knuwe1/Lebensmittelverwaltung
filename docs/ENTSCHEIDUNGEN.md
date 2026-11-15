# Entscheidungsprotokoll

Verbindliche Festlegungen zu den offenen Punkten der Produktspezifikation (Kap. 17)
und zu Fragen, die während der Umsetzung aufgekommen sind. Neue Einträge werden unten
angehängt; überholte Entscheidungen werden nicht gelöscht, sondern als ersetzt markiert.

| ID | Thema | Entscheidung | Datum |
| --- | --- | --- | --- |
| DEC-001 | Android-App | PWA für den MVP | 2026-11-14 |
| DEC-004 | Backend-Technologie | Python 3.13, FastAPI, SQLAlchemy 2, Alembic | 2026-11-14 |
| DEC-005 | Datenbank | PostgreSQL 17 | 2026-11-14 |
| DEC-006 | Frontend-Technologie | React + TypeScript + Vite, Mantine UI, TanStack Query | 2026-11-14 |
| DEC-007 / DEC-022 | Bilderkennung | **Ersetzt durch DEC-030.** ~~Lokale OCR (Tesseract) mit Abgleich gegen den Produktkatalog als Standard; optionaler Adapter für einen externen KI-Dienst, nur nach expliziter Konfiguration. Beides hinter einer austauschbaren Schnittstelle. Machbarkeitsnachweis zu Beginn von Phase 4.~~ | 2026-11-14 |
| DEC-009 | Betrieb außerhalb des Heimnetzwerks | **Tailscale.** Die Anwendung ist nur im privaten Tailnet erreichbar; HTTPS-Zertifikat für den `*.ts.net`-Namen über den Tailscale-Dienst des Hosts (`LMV_TLS_MODE=tailscale`). Keine Portfreigabe ins Internet. Alternativen (lokale CA, öffentliche Domain) bleiben konfigurierbar. | 2026-11-14 |
| DEC-023 | Bruchteile bei Stück-Produkten (FR-CNS-004) | **Erlaubt.** Mengen werden für alle Basiseinheiten als Dezimalzahl mit bis zu drei Nachkommastellen gespeichert (`NUMERIC(14,3)`), z. B. 0,5 Stück Gurke oder 1,25 Stück Butter. | 2026-11-14 |
| DEC-024 | Branch-Modell | `dev → test → main`, alle geschützt, nur per Pull Request; Releases aus `main`. Details: [ENTWICKLUNGSPROZESS.md](ENTWICKLUNGSPROZESS.md) | 2026-11-14 |
| DEC-029 | Restmenge per Waage (Wunsch des Product Owners) | Pro Produkt einschaltbar (nur Basiseinheit Gramm). Der Benutzer wiegt nach der Entnahme die **angebrochene** Packung; enthält die Position mehrere Packungen, gelten die übrigen als voll. Ein pro Verpackungsvariante hinterlegtes **Leergewicht** wird vom abgelesenen Gewicht abgezogen. Die Differenz zum erwarteten Inhalt wird als Verbrauch gebucht (Grund `weighed`, Rechenweg im Kommentar) und ist wie jede Buchung stornierbar. Ein höheres Gewicht als erwartet wird abgewiesen (Korrektur per Inventur). | 2026-11-14 |
| DEC-030 | Bilderkennung (ersetzt DEC-007 / DEC-022) | **Vorerst zurückgestellt.** Laut [Machbarkeitsnachweis](MACHBARKEITSNACHWEIS-BILDERKENNUNG.md) ist lokale OCR mit Tesseract nicht tragfähig (Produkt 5/40, MHD 0/3) und wird nicht eingebaut. Gemini im kostenlosen Kontingent ist wegen Anfrage- und Tageslimits nicht verlässlich. Ein lokales Modell über Ollama (Qwen2.5-VL 3B) erkennt gut, braucht auf dem Server (Intel N150, ohne Grafikkarte) aber rund 3 Minuten pro Foto. Phase 4 wird daher mit Barcode, Suche und manueller Eingabe abgeschlossen. Die Bilderkennung bleibt als austauschbarer Adapter vorgesehen, bevorzugt lokal über Ollama auf einem Rechner mit Grafikkarte im Tailnet. Ein externer Dienst ist nur nach ausdrücklicher Konfiguration zulässig. Vor einer Umsetzung wird derselbe Bildsatz auf der dann vorhandenen Hardware erneut geprüft. | 2026-11-15 |
| DEC-031 | Abmelden, Rechte der Mitglieder, Erreichbarkeit (Befunde Sicherheitsprüfung, [Protokoll](PRODUKTIVSETZUNG.md)) | **Abmelden meldet alle Geräte des Benutzers ab** (serverseitig, `token_version`); Anmeldungen bleiben sonst 14 Tage gültig. **Mitglieder dürfen weiterhin Produktbilder ersetzen und Verpackungsvarianten anlegen**; Löschen von Bildern und Ändern von Varianten bleibt Administratoren vorbehalten. **Die Installation ist nur über Tailscale erreichbar** (`LMV_BIND_ADDRESS` = Tailscale-IP des Hosts). | 2026-11-15 |
