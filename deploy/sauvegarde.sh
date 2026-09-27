#!/usr/bin/env bash
# Sauvegarde cohérente de la base, même pendant que l'app écrit.
#
# `sqlite3 .backup` prend un verrou propre : copier le fichier .db à chaud
# produirait une base corrompue dès qu'un bip tombe au mauvais moment.
#
# Exemple de cron quotidien :
#   15 3 * * * /opt/miamstock/deploy/sauvegarde.sh /var/backups/miamstock

set -euo pipefail

SOURCE="${MIAMSTOCK_DB:-/var/lib/miamstock/miamstock.db}"
DESTINATION="${1:-/var/backups/miamstock}"
HORODATAGE="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$DESTINATION"
sqlite3 "$SOURCE" ".backup '$DESTINATION/miamstock-$HORODATAGE.db'"
gzip -f "$DESTINATION/miamstock-$HORODATAGE.db"

# On ne garde que les 30 dernières.
ls -1t "$DESTINATION"/miamstock-*.db.gz | tail -n +31 | xargs -r rm --

echo "Sauvegarde : $DESTINATION/miamstock-$HORODATAGE.db.gz"
