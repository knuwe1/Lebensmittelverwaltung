#!/bin/sh
set -e
# Datenbankmigrationen bei jedem Start anwenden (NFR-MNT-003/006).
alembic upgrade head
exec "$@"
