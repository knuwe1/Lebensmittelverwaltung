#!/bin/sh
set -e

# Der Container startet als root, damit die Rechte am Bildverzeichnis korrigiert werden
# können (Docker-Volumes gehören beim Anlegen oft root). Danach läuft alles – auch die
# Migrationen – als unprivilegierter Benutzer "lmv".
if [ "$(id -u)" = "0" ]; then
  mkdir -p "$LMV_MEDIA_DIR"
  chown -R lmv:lmv "$LMV_MEDIA_DIR"
  exec setpriv --reuid=lmv --regid=lmv --init-groups "$0" "$@"
fi

# Datenbankmigrationen bei jedem Start anwenden (NFR-MNT-003/006).
alembic upgrade head
exec "$@"
