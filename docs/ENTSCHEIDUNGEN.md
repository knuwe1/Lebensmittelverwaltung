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
| DEC-007 / DEC-022 | Bilderkennung | Lokale OCR (Tesseract) mit Abgleich gegen den Produktkatalog als Standard; optionaler Adapter für einen externen KI-Dienst, nur nach expliziter Konfiguration. Beides hinter einer austauschbaren Schnittstelle. Machbarkeitsnachweis zu Beginn von Phase 4. | 2026-11-14 |
| DEC-009 | Betrieb außerhalb des Heimnetzwerks | **Tailscale.** Die Anwendung ist nur im privaten Tailnet erreichbar; HTTPS-Zertifikat für den `*.ts.net`-Namen über den Tailscale-Dienst des Hosts (`LMV_TLS_MODE=tailscale`). Keine Portfreigabe ins Internet. Alternativen (lokale CA, öffentliche Domain) bleiben konfigurierbar. | 2026-11-14 |
| DEC-023 | Bruchteile bei Stück-Produkten (FR-CNS-004) | **Erlaubt.** Mengen werden für alle Basiseinheiten als Dezimalzahl mit bis zu drei Nachkommastellen gespeichert (`NUMERIC(14,3)`), z. B. 0,5 Stück Gurke oder 1,25 Stück Butter. | 2026-11-14 |
| DEC-024 | Branch-Modell | `dev → test → main`, alle geschützt, nur per Pull Request; Releases aus `main`. Details: [ENTWICKLUNGSPROZESS.md](ENTWICKLUNGSPROZESS.md) | 2026-11-14 |
| DEC-029 | Restmenge per Waage (Wunsch des Product Owners) | Pro Produkt einschaltbar (nur Basiseinheit Gramm). Der Benutzer wiegt nach der Entnahme die **angebrochene** Packung; enthält die Position mehrere Packungen, gelten die übrigen als voll. Ein pro Verpackungsvariante hinterlegtes **Leergewicht** wird vom abgelesenen Gewicht abgezogen. Die Differenz zum erwarteten Inhalt wird als Verbrauch gebucht (Grund `weighed`, Rechenweg im Kommentar) und ist wie jede Buchung stornierbar. Ein höheres Gewicht als erwartet wird abgewiesen (Korrektur per Inventur). | 2026-11-14 |
