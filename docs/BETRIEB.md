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

### Empfohlen: eigener Betriebsordner

Läuft die Installation auf einem Rechner, auf dem auch entwickelt wird, gehört sie in einen
eigenen Ordner außerhalb des Repositorys. Er enthält nur die Betriebsdateien aus einem
Release-Tag, die `.env` und die Sicherungen. So wirkt kein Branchwechsel und kein
`docker compose` im Repository auf die Live-Installation.

```bash
REPO=~/Work/Dev/Lebensmittelverwaltung   # Klon des Repositorys
LIVE=~/Lebensmittelverwaltung-Live       # Betriebsordner
mkdir -p "$LIVE"
git -C "$REPO" fetch --tags
git -C "$REPO" archive v0.1.0 docker-compose.yml docker-compose.tailscale.yml deploy/backup .env.example \
  | tar -x -C "$LIVE"
cd "$LIVE" && cp .env.example .env && chmod 600 .env
# .env anpassen (siehe oben) und die Version festlegen: LMV_VERSION=0.1.0
docker compose pull && docker compose up -d --no-build
```

`LMV_VERSION` immer auf eine feste Version setzen, nicht `latest` – dann läuft genau der
Stand eines Releases, und lokal gebaute Images können ihn nicht unbemerkt ersetzen.
Daten liegen in den benannten Volumes `lebensmittelverwaltung_*`. Ein Umzug des
Betriebsordners braucht daher nur `docker compose down` im alten und `up -d` im neuen Ordner.

Beim ersten Start wird der Administrator aus `LMV_BOOTSTRAP_ADMIN_*` angelegt.
Das Passwort sollte danach in der Anwendung unter *Einstellungen → Mein Konto*
geändert und `LMV_BOOTSTRAP_ADMIN_PASSWORD` aus der `.env` entfernt werden.

| Container | Aufgabe |
| --- | --- |
| `web` | Caddy: HTTPS, Reverse Proxy, Auslieferung der Web-App/PWA |
| `backend` | REST-API (FastAPI); führt beim Start die DB-Migrationen aus |
| `db` | PostgreSQL 17 |
| `backup` | Tägliche Datensicherung |

Die API-Dokumentation (OpenAPI) ist standardmäßig abgeschaltet, damit ohne Anmeldung nichts
über die API abrufbar ist. Bei Bedarf `LMV_API_DOCS=true` in der `.env` setzen; sie ist dann
unter `https://<adresse>/api/v1/docs` erreichbar. In der lokalen Entwicklung ist sie an.

## HTTPS

Kamera und PWA-Installation funktionieren auf Android nur über HTTPS. Die Zertifikatsquelle
wird über `LMV_TLS_MODE` gewählt.

### Empfohlen: Tailscale (`LMV_TLS_MODE=tailscale`, DEC-009)

Die Anwendung ist dann nur im eigenen Tailnet erreichbar – zu Hause und unterwegs, ohne
Portfreigabe im Router. Das Zertifikat ist ein reguläres Let's-Encrypt-Zertifikat für den
`*.ts.net`-Namen; auf den Handys muss nichts installiert werden.

1. Tailscale auf dem Server installieren und anmelden:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
2. In der Tailscale-Admin-Konsole unter *DNS* **MagicDNS** und **HTTPS Certificates** aktivieren.
3. Den Namen des Servers ermitteln: `tailscale status --self --json | grep DNSName`
   (z. B. `heimserver.tail1234.ts.net`).
4. In der `.env`:
   ```ini
   LMV_SITE_ADDRESS=heimserver.tail1234.ts.net
   LMV_TLS_MODE=tailscale
   COMPOSE_FILE=docker-compose.yml:docker-compose.tailscale.yml
   LMV_BIND_ADDRESS=100.x.y.z    # Ausgabe von: tailscale ip -4 (empfohlen, sperrt das Heimnetz aus)
   ```
5. `docker compose up -d` – danach ist die App unter `https://heimserver.tail1234.ts.net`
   erreichbar.
   Mit `LMV_BIND_ADDRESS` muss Docker nach einem Neustart des Rechners auf Tailscale warten –
   sonst existiert die Tailscale-IP beim Start der Container noch nicht und der Web-Container
   kann nicht starten. Einmalig einrichten:
   ```bash
   sudo mkdir -p /etc/systemd/system/docker.service.d
   printf '[Unit]\nAfter=tailscaled.service\nWants=tailscaled.service\n' \
     | sudo tee /etc/systemd/system/docker.service.d/nach-tailscale.conf
   sudo systemctl daemon-reload
   ```
6. Auf jedem Android-Gerät die Tailscale-App installieren und im selben Tailnet anmelden.
   Anschließend die Adresse in Chrome öffnen und über *Zum Startbildschirm hinzufügen*
   als App installieren.

### Alternativen

- **Nur Heimnetz** (`LMV_TLS_MODE=internal`): Caddy erzeugt eine eigene Zertifizierungsstelle.
  Deren Stammzertifikat muss auf jedem Gerät installiert werden:
  ```bash
  docker compose cp web:/data/caddy/pki/authorities/local/root.crt ./lmv-root.crt
  ```
  Android: *Einstellungen → Sicherheit → Verschlüsselung → Zertifikat installieren → CA-Zertifikat*.
- **Öffentliche Domain** (`LMV_TLS_MODE=acme`, `LMV_ACME_EMAIL=…`): Let's Encrypt;
  Ports 80/443 müssen aus dem Internet erreichbar sein. Für eine Haushaltsanwendung
  nur mit zusätzlicher Absicherung zu empfehlen.

## Externe Produktdaten (Open Food Facts)

Standardmäßig **aus**. Ein Administrator kann sie unter *Einstellungen → System*
einschalten. Dann wird bei einem unbekannten Barcode ausschließlich die Barcode-Nummer
vom Server (nicht vom Handy) an `world.openfoodfacts.org` gesendet; Bilder werden über
den eigenen Server geladen und neu kodiert. Der Server benötigt dafür ausgehenden
Internetzugang. Alternativer Endpunkt (z. B. Spiegel): `LMV_OFF_BASE_URL`.

## Datensicherung

Der Container `backup` sichert täglich um `LMV_BACKUP_TIME` (Standard 03:00). War der Rechner
zu diesem Zeitpunkt ausgeschaltet oder im Ruhezustand, wird die Sicherung nachgeholt, sobald
der Dienst wieder läuft (Prüfung alle 5 Minuten). Gesichert werden:

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

Im Betriebsordner (siehe oben), Beispiel für `v0.2.0`:

```bash
cd ~/Lebensmittelverwaltung-Live
docker compose exec -T backup sh /scripts/backup.sh       # 1. Sicherung
git -C ~/Work/Dev/Lebensmittelverwaltung fetch --tags       # 2. Betriebsdateien des Releases
git -C ~/Work/Dev/Lebensmittelverwaltung archive v0.2.0 \
  docker-compose.yml docker-compose.tailscale.yml deploy/backup .env.example | tar -x -C .
sed -i 's/^LMV_VERSION=.*/LMV_VERSION=0.2.0/' .env          # 3. Version
docker compose pull                                         # 4. Images holen (App läuft weiter)
docker compose up -d --no-build                             # 5. Neustart, kurze Unterbrechung
docker compose ps                                           # 6. Kontrolle
```

- Neue Einstellungen eines Releases stehen in `.env.example` und in den Release-Notes; bei
  Bedarf in die `.env` übernehmen.
- Datenbankmigrationen laufen beim Start des Backends automatisch.
- **Zurück auf eine ältere Version** nur zusammen mit der Wiederherstellung der Sicherung
  aus Schritt 1: Migrationen werden nur vorwärts ausgeführt, eine ältere Version passt
  danach nicht mehr zur Datenbank.

Ohne Betriebsordner (Installation direkt im Klon): neues Release-Tag auschecken,
`LMV_VERSION` setzen, `docker compose pull && docker compose up -d`.

## Testen auf dem eigenen Rechner und Handy

> **Achtung, wenn auf demselben Rechner eine Live-Installation läuft:** Die Compose-Datei
> legt den Projektnamen `lebensmittelverwaltung` fest. Ein `docker compose` im
> Repository würde deshalb die Container und Daten-Volumes der Live-Installation
> verwenden – `down -v` löscht dann echte Daten. Zum Testen immer einen eigenen
> Projektnamen, eigene Ports und einen eigenen Image-Tag verwenden:
> `docker compose -p lmv-test --env-file /tmp/lmv-test.env up -d --build` mit
> `LMV_VERSION=test`, `LMV_HTTP_PORT`/`LMV_HTTPS_PORT` (z. B. 18080/18443) in der Datei.

Schnellster Weg ohne Tailscale – Rechner und Handy im selben WLAN
(`192.168.178.105` durch die eigene IP ersetzen, siehe `hostname -I`):

```bash
cat > .env <<EOF
POSTGRES_PASSWORD=$(openssl rand -hex 12)
LMV_SECRET_KEY=$(openssl rand -hex 32)
LMV_BOOTSTRAP_ADMIN_USERNAME=admin
LMV_BOOTSTRAP_ADMIN_PASSWORD=admin12345
LMV_SITE_ADDRESS=localhost, 192.168.178.105
LMV_DEFAULT_SNI=192.168.178.105
LMV_TLS_MODE=internal
EOF
docker compose up -d --build
```

- Rechner: `https://localhost`
- Handy: `https://192.168.178.105`

Der Browser warnt vor dem Zertifikat (lokale Zertifizierungsstelle). Zum Testen
über *Erweitert → Weiter zu …* bestätigen. Für die Installation als App und den
dauerhaften Gebrauch Tailscale verwenden (siehe oben).

Beenden: `docker compose down` (Daten bleiben erhalten) bzw.
`docker compose down -v` (Daten werden gelöscht).

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
