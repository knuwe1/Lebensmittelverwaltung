# Browser-Test der mobilen Kernabläufe

`mobile_smoke.py` bedient die Anwendung in einem echten Chromium auf einem simulierten
Android-Gerät (Pixel 7) und prüft Einlagern, Entnehmen (FEFO), Entsorgen, Umlagern,
Historie mit Storno sowie den Schutz vor Doppelbuchungen (Spez. 15.4, 15.5).

Er ersetzt nicht den Test auf einem realen Gerät (Kamera, Bedienung mit einer Hand),
findet aber Fehler, die Typecheck und API-Tests nicht sehen.

## Ausführen

Benötigt nur Docker. Der Test braucht einen **leeren** Stack, daher ein eigenes
Compose-Projekt mit eigenen Ports:

```bash
cat > /tmp/lmv-e2e.env <<EOF
POSTGRES_PASSWORD=e2etest123
LMV_SECRET_KEY=$(openssl rand -hex 32)
LMV_BOOTSTRAP_ADMIN_USERNAME=admin
LMV_BOOTSTRAP_ADMIN_PASSWORD=adminpass123
LMV_SITE_ADDRESS=localhost
LMV_HTTP_PORT=18080
LMV_HTTPS_PORT=18443
LMV_BACKUP_DIR=/tmp/lmv-e2e-backups
EOF
docker compose -p lmv-e2e --env-file /tmp/lmv-e2e.env up -d --build --wait

mkdir -p /tmp/lmv-e2e-out
docker run --rm --network host -u "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD/e2e:/e2e:ro" -v /tmp/lmv-e2e-out:/out \
  mcr.microsoft.com/playwright/python:v1.49.0-noble \
  sh -c "pip install -q --user playwright==1.49.0 && python /e2e/mobile_smoke.py https://localhost:18443 /out"

docker compose -p lmv-e2e --env-file /tmp/lmv-e2e.env down -v
```

Screenshots der Masken landen in `/tmp/lmv-e2e-out`.
