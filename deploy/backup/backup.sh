#!/bin/sh
# Erstellt eine Datensicherung von Datenbank und Produktbildern (NFR-BCK-001/002).
# Ergebnis: /backups/lmv-<Zeitstempel>/{db.dump,media.tar.gz}
set -eu
STAMP=$(date +%Y%m%d-%H%M%S)
TARGET="/backups/lmv-$STAMP"
mkdir -p "$TARGET.partial"

pg_dump --format=custom --no-owner --file="$TARGET.partial/db.dump"
tar -czf "$TARGET.partial/media.tar.gz" -C /lmv-media .
mv "$TARGET.partial" "$TARGET"
echo "$(date -Iseconds) Sicherung erstellt: $TARGET"

# Alte Sicherungen entfernen (Aufbewahrung in Tagen)
KEEP=${LMV_BACKUP_KEEP_DAYS:-14}
find /backups -mindepth 1 -maxdepth 1 -type d -name 'lmv-2*' -mtime "+$KEEP" -exec rm -r -- {} +
