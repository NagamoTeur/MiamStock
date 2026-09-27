#!/bin/sh
# Démarre en root juste le temps de rendre le volume de données inscriptible,
# puis abandonne définitivement les privilèges.
#
# Le chown de la construction ne survit pas à un montage : un bind mount
# recouvre /data par un dossier de l'hôte, avec les propriétaires de l'hôte
# (root, la plupart du temps). Sans cette correction au démarrage, le service
# ne peut pas écrire sa base et s'arrête sur un PermissionError.

set -e

APP_UID=10001
APP_GID=10001
DATA_DIR="${MIAMSTOCK_DATA_DIR:-/data}"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$DATA_DIR"
    if [ "$(stat -c %u "$DATA_DIR")" != "$APP_UID" ]; then
        echo "Volume $DATA_DIR appartenant à l'uid $(stat -c %u "$DATA_DIR") : correction vers $APP_UID."
        chown -R "$APP_UID:$APP_GID" "$DATA_DIR"
    fi
    # setpriv vient d'util-linux, déjà présent dans l'image : pas de gosu à ajouter.
    exec setpriv --reuid="$APP_UID" --regid="$APP_GID" --clear-groups "$@"
fi

# Déjà démarré sans privilèges (docker run --user, par exemple) : rien à faire.
exec "$@"
