#!/usr/bin/env bash
# Sauvegarde cohérente de la base, même pendant que l'app écrit.
#
# `sqlite3 .backup` prend un verrou propre : copier le fichier .db à chaud
# produirait une base corrompue dès qu'un bip tombe au mauvais moment.
#
# Lancé chaque nuit par miamstock-sauvegarde.timer (installé par install-lxc.sh),
# et avant chaque mise à jour automatique.
#
# Restaurer : arrêter l'app, décompresser par-dessus data/miamstock.db, relancer.
#   docker compose stop
#   gunzip -c /var/backups/miamstock/miamstock-AAAAMMJJ-HHMMSS.db.gz > data/miamstock.db
#   rm -f data/miamstock.db-wal data/miamstock.db-shm && docker compose start

set -euo pipefail

SOURCE="${MIAMSTOCK_DB:-/var/lib/miamstock/miamstock.db}"
DESTINATION="${1:-/var/backups/miamstock}"
HORODATAGE="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$DESTINATION"
COPIE="$DESTINATION/miamstock-$HORODATAGE.db"
sqlite3 "$SOURCE" ".backup '$COPIE'"

# Une sauvegarde qu'on n'a jamais relue n'en est pas une : on vérifie que la
# copie s'ouvre et qu'elle est intègre avant de la garder.
VERDICT="$(sqlite3 "$COPIE" 'PRAGMA integrity_check;' 2>&1 || true)"
if [[ "$VERDICT" != "ok" ]]; then
    rm -f "$COPIE"
    echo "Sauvegarde corrompue, abandonnée : $VERDICT" >&2
    exit 1
fi
gzip -f "$COPIE"

# On ne garde que les 30 dernières.
ls -1t "$DESTINATION"/miamstock-*.db.gz | tail -n +31 | xargs -r rm --

echo "Sauvegarde : $DESTINATION/miamstock-$HORODATAGE.db.gz"
