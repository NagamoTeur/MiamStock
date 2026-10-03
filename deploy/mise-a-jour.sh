#!/usr/bin/env bash
#
# Mise à jour automatique : appelé toutes les 5 minutes par miamstock-maj.timer.
#
# Si `main` a bougé sur GitHub, le script sauvegarde la base, construit la
# nouvelle image (les tests tournent pendant la construction), la démarre, puis
# vérifie qu'elle répond. Au moindre échec, il revient au commit précédent :
# l'app ne reste jamais cassée en attendant que quelqu'un s'en aperçoive.
#
# Le résultat est écrit dans data/mise-a-jour.json, que l'app affiche dans
# Réglages : un échec se voit depuis le téléphone, sans se connecter au serveur.
#
#   deploy/mise-a-jour.sh            # ne fait rien si main n'a pas bougé
#   deploy/mise-a-jour.sh --force    # reconstruit quand même, ou retente un échec
#   journalctl -u miamstock-maj      # l'historique des passages

set -euo pipefail

# Tout le script tient dans une fonction, appelée à la dernière ligne : bash la
# lit en entier avant de l'exécuter. Sans cela, le `git reset` qui réécrit ce
# fichier en cours de route ferait lire à bash la suite du nouveau fichier, à
# l'ancien décalage.
principal() {
    local app_dir="${MIAMSTOCK_APP_DIR:-/opt/miamstock}"
    local force=0
    [[ "${1:-}" == "--force" ]] && force=1

    cd "$app_dir"

    # Deux passages ne doivent jamais se chevaucher : une construction peut
    # durer plus longtemps que l'intervalle du timer.
    exec 9>"${MIAMSTOCK_VERROU:-/run/miamstock-maj.lock}"
    flock -n 9 || { echo "Une mise à jour est déjà en cours."; return 0; }

    git fetch --quiet origin main
    local avant apres
    avant="$(git rev-parse HEAD)"
    apres="$(git rev-parse origin/main)"

    if [[ "$avant" == "$apres" && $force -eq 0 ]]; then
        return 0
    fi

    # Après un échec, HEAD est revenu en arrière mais main désigne toujours le
    # commit cassé : sans ce garde-fou, il serait retenté toutes les 5 minutes,
    # tests et sauvegarde compris. On attend que main bouge (un correctif), ou
    # un --force.
    if [[ $force -eq 0 ]] && grep -qs "\"state\":\"echec\",\"commit\":\"${apres:0:7}\"" data/mise-a-jour.json; then
        return 0
    fi

    echo "Mise à jour ${avant:0:7} → ${apres:0:7}"
    ecrire_etat "en_cours" "$apres" "Construction de ${apres:0:7}"

    # Une copie de la base avant chaque déploiement : les migrations n'ajoutent
    # que des colonnes, mais une sauvegarde ne coûte rien. Dans son propre
    # dossier, pour que des déploiements rapprochés n'évincent pas les
    # sauvegardes nocturnes de la rotation.
    if [[ -f data/miamstock.db ]] && ! MIAMSTOCK_DB="$app_dir/data/miamstock.db" \
            "$app_dir/deploy/sauvegarde.sh" /var/backups/miamstock/avant-mise-a-jour >/dev/null; then
        # Une base qu'on ne sait pas sauvegarder est peut-être abîmée : ce n'est
        # pas le moment de lancer une migration dessus.
        ecrire_etat "echec" "$apres" "Sauvegarde impossible avant la mise à jour : la base est peut-être abîmée. Rien n'a été changé."
        return 1
    fi

    git reset --hard --quiet "$apres"
    exporter_version

    # Les tests tournent pendant la construction. Si elle échoue, rien n'a
    # encore été arrêté : l'ancien conteneur continue de servir.
    if ! docker compose build; then
        echo "La construction a échoué (tests ou compilation) : retour à ${avant:0:7}."
        git reset --hard --quiet "$avant"
        ecrire_etat "echec" "$apres" "Les tests ou la construction de ${apres:0:7} ont échoué : la version précédente tourne toujours."
        return 1
    fi

    docker compose up -d
    if attendre_version "$GIT_SHA"; then
        echo "En service : ${apres:0:7}"
        ecrire_etat "ok" "$apres" "Déployé"
        docker image prune -f >/dev/null 2>&1 || true
        return 0
    fi

    echo "La nouvelle version ne répond pas : retour à ${avant:0:7}."
    docker compose logs --tail 30 || true
    git reset --hard --quiet "$avant"
    exporter_version
    docker compose up -d --build
    attendre_version "$GIT_SHA" || true
    ecrire_etat "echec" "$apres" "${apres:0:7} ne démarrait pas : retour automatique à ${avant:0:7}."
    return 1
}

exporter_version() {
    GIT_SHA="$(git rev-parse --short HEAD)"
    BUILD_DATE="$(date -Iseconds)"
    export GIT_SHA BUILD_DATE
}

# Attend que le service réponde *avec la bonne version* : juste après un
# `up -d`, c'est parfois encore l'ancien conteneur qui répond.
attendre_version() {
    local attendue="$1"
    for _ in $(seq 1 "${MIAMSTOCK_ATTENTE:-60}"); do
        if curl -sf -m 2 http://127.0.0.1:8077/api/health 2>/dev/null \
                | grep -q "\"version\":\"$attendue\""; then
            return 0
        fi
        sleep 1
    done
    return 1
}

ecrire_etat() {
    local etat="$1" commit="$2" message="$3"
    local cible="data/mise-a-jour.json"
    mkdir -p data
    # Écriture atomique : l'app ne doit jamais lire un fichier à moitié écrit.
    printf '{"state":"%s","commit":"%s","at":"%s","message":"%s"}\n' \
        "$etat" "${commit:0:7}" "$(date -Iseconds)" "$message" > "$cible.tmp"
    chmod 644 "$cible.tmp"
    mv -f "$cible.tmp" "$cible"
}

# Sur la même ligne que l'appel : bash a déjà lu `exit` avant que le fichier
# ne soit réécrit, et ne relira rien après.
principal "$@"; exit $?
