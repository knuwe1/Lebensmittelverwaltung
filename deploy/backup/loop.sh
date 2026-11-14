#!/bin/sh
# Führt täglich zur Uhrzeit LMV_BACKUP_TIME (HH:MM, Standard 03:00) eine Sicherung aus.
set -eu
TIME=${LMV_BACKUP_TIME:-03:00}
echo "Datensicherung aktiv, täglich um $TIME Uhr."
while true; do
  now=$(date +%s)
  next=$(date -d "$(date +%Y-%m-%d) $TIME" +%s)
  [ "$next" -le "$now" ] && next=$((next + 86400))
  sleep $((next - now))
  sh /scripts/backup.sh || echo "$(date -Iseconds) FEHLER: Sicherung fehlgeschlagen" >&2
done
