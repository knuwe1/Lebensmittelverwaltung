# Betrieb

## Installation

Voraussetzung: ein Linux-Host mit Docker und Docker Compose (Heimserver, Mini-PC, NAS, VPS).

```bash
git clone https://github.com/knuwe1/Lebensmittelverwaltung.git
cd Lebensmittelverwaltung
git checkout main            # oder ein bestimmtes Release-Tag, z. B. v0.1.0
cp .env.example .env
# .env anpassen: POSTGRES_PASSWORD, LMV_SECRET_KEY (openssl rand -hex 32),
# LMV_BOOTSTRAP_ADMIN_PASSWORD, LMV_SITE_ADDRESS
docker compose pull          # fertige Images aus ghcr.io (Version über LMV_VERSION)
docker compose up -d
```

Alternativ lassen sich die Images lokal bauen: `docker compose up -d --build`.

Beim ersten Start wird der Administrator aus `LMV_BOOTSTRAP_ADMIN_*` angelegt.
Das Passwort sollte danach in der Anwendung unter *Einstellungen → Mein Konto*
geändert und `LMV_BOOTSTRAP_ADMIN_PASSWORD` aus der `.env` entfernt werden.

| Container | Aufgabe |
| --- | --- |
| `web` | Caddy: HTTPS, Reverse Proxy, Auslieferung der Web-App/PWA |
| `backend` | REST-API (FastAPI); führt beim Start die DB-Migrationen aus |
| `db` | PostgreSQL 17 |
| `backup` | Tägliche Datensicherung |

Die API-Dokumentation (OpenAPI) ist unter `https://<adresse>/api/v1/docs` erreichbar.

## HTTPS

Kamera und PWA-Installation funktionieren auf Android nur über HTTPS. Drei Varianten:

1. **Eigene Domain mit öffentlichem DNS** – `LMV_SITE_ADDRESS=vorrat.example.de`,
   `LMV_TLS=<E-Mail>`. Caddy holt automatisch ein Let's-Encrypt-Zertifikat
   (Ports 80/443 müssen erreichbar sein).
2. **Tailscale / VPN** (empfohlen für Zugriff von unterwegs, DEC-009) – Zugriff nur über
   das private Netz; Zertifikat z. B. über `tailscale cert`.
3. **Nur Heimnetz** – `LMV_TLS=internal`. Caddy erzeugt eine eigene Zertifizierungsstelle.
   Deren Stammzertifikat muss einmalig auf jedem Gerät installiert werden:
   ```bash
   docker compose cp web:/data/caddy/pki/authorities/local/root.crt ./lmv-root.crt
   ```
   Android: *Einstellungen → Sicherheit → Verschlüsselung → Zertifikat installieren → CA-Zertifikat*.

## Datensicherung

Der Container `backup` sichert täglich um `LMV_BACKUP_TIME` (Standard 03:00):

- Datenbank (`pg_dump`, Custom-Format) → `db.dump`
- Produktbilder → `media.tar.gz`

Ziel ist `LMV_BACKUP_DIR/lmv-<JJJJMMTT-HHMMSS>/`. Sicherungen älter als
`LMV_BACKUP_KEEP_DAYS` werden entfernt. Das Sicherungsverzeichnis sollte zusätzlich
auf ein anderes Gerät kopiert werden (z. B. NAS, externe Platte) – eine Sicherung auf
derselben Platte schützt nicht vor Hardwaredefekten (R-006).

Manuelle Sicherung:

```bash
docker compose exec backup sh /scripts/backup.sh
```

## Wiederherstellung

```bash
docker compose stop backend web
docker compose exec backup sh /scripts/restore.sh lmv-20261114-030000
docker compose start backend web
```

Der Restore ersetzt Datenbank und Produktbilder vollständig durch den Stand der Sicherung.
Er läuft in einer Transaktion; schlägt er fehl, bleibt der vorherige Datenbankstand erhalten.

> **Vor Produktivsetzung** muss eine Wiederherstellung einmal erfolgreich getestet
> werden (NFR-BCK-004).

## Update

```bash
git pull                     # bzw. neues Release-Tag auschecken
# LMV_VERSION in .env auf die neue Version setzen
docker compose pull && docker compose up -d
```

Datenbankmigrationen laufen beim Start des Backends automatisch. Vor einem Update
empfiehlt sich eine manuelle Sicherung.

## Lokale Entwicklung

```bash
# Datenbank
docker run -d --name lmv-pg -e POSTGRES_USER=lmv -e POSTGRES_PASSWORD=lmv \
  -e POSTGRES_DB=lmv -p 127.0.0.1:5432:5432 postgres:17-alpine
docker exec lmv-pg psql -U lmv -c "CREATE DATABASE lmv_test"

# Backend
cd backend
uv sync
export LMV_DATABASE_URL=postgresql+psycopg://lmv:lmv@localhost:5432/lmv LMV_COOKIE_SECURE=false \
       LMV_BOOTSTRAP_ADMIN_USERNAME=admin LMV_BOOTSTRAP_ADMIN_PASSWORD=admin123 LMV_MEDIA_DIR=./data
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
LMV_TEST_DATABASE_URL=postgresql+psycopg://lmv:lmv@localhost:5432/lmv_test uv run pytest

# Frontend (Vite-Proxy leitet /api an localhost:8000 weiter)
cd frontend
npm install
npm run dev
```

Neue Migration nach Modelländerung:

```bash
uv run alembic revision --autogenerate --rev-id 0002 -m "beschreibung"
```
