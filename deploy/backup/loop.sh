#!/bin/sh
# Sichert täglich zur Uhrzeit LMV_BACKUP_TIME (HH:MM, Standard 03:00).
# Verpasste Sicherungen – Rechner ausgeschaltet oder im Ruhezustand – werden nachgeholt,
# sobald der Dienst wieder läuft: Es wird regelmäßig geprüft, ob seit dem letzten
# planmäßigen Termin eine Sicherung existiert (NFR-BCK-001).
set -eu
TIME=${LMV_BACKUP_TIME:-03:00}
CHECK_EVERY=${LMV_BACKUP_CHECK_SECONDS:-300}
echo "Datensicherung aktiv, täglich um $TIME Uhr; verpasste Sicherungen werden nachgeholt."

# Zeitpunkt (Epoch) der neuesten vollständigen Sicherung, 0 wenn es keine gibt.
last_backup() {
  newest=$(ls -1d /backups/lmv-2* 2>/dev/null | grep -v '\.partial$' | sort | tail -n 1)
  if [ -n "$newest" ]; then stat -c %Y "$newest"; else echo 0; fi
}

# Letzter planmäßiger Termin: heute um TIME, falls schon vorbei, sonst gestern um TIME.
last_slot() {
  now=$(date +%s)
  slot=$(date -d "$(date +%Y-%m-%d) $TIME" +%s)
  if [ "$slot" -gt "$now" ]; then slot=$((slot - 86400)); fi
  echo "$slot"
}

while true; do
  if [ "$(last_backup)" -lt "$(last_slot)" ]; then
    sh /scripts/backup.sh ||
      echo "$(date -Iseconds) FEHLER: Sicherung fehlgeschlagen, neuer Versuch in ${CHECK_EVERY}s" >&2
  fi
  sleep "$CHECK_EVERY"
done
