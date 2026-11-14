#!/bin/sh
# Stellt eine Sicherung wieder her (NFR-BCK-003). Aufruf siehe docs/BETRIEB.md.
# ACHTUNG: Überschreibt den aktuellen Datenbestand vollständig.
set -eu
NAME=${1:?Verzeichnisname der Sicherung angeben, z. B. lmv-20261114-030000}
SRC="/backups/$NAME"
[ -f "$SRC/db.dump" ] || { echo "Keine Sicherung in $SRC gefunden" >&2; exit 1; }

pg_restore --clean --if-exists --no-owner --single-transaction --dbname="$PGDATABASE" "$SRC/db.dump"
find /lmv-media -mindepth 1 -delete
tar -xzf "$SRC/media.tar.gz" -C /lmv-media
echo "Wiederherstellung aus $SRC abgeschlossen."
