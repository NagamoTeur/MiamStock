#!/usr/bin/env bash
#
# Bootstrap complet de MiamStock sur un LXC Debian fraîchement créé.
#
# Le dépôt étant privé, le script se copie depuis le PC plutôt que de se
# télécharger :
#
#   scp deploy/install-lxc.sh root@<ip-du-lxc>:/root/
#   ssh root@<ip-du-lxc> 'bash /root/install-lxc.sh'
#
# Pas dans /tmp : le script peut demander un redémarrage du conteneur (device
# TUN pour Tailscale), et /tmp est vidé au boot. Une fois le dépôt cloné, le
# script vit de toute façon dans /opt/miamstock/deploy/.
#
# Le script est idempotent : le relancer met simplement à jour et redéploie.
# Il s'arrête au premier échec plutôt que de continuer sur un état à moitié fait.

set -euo pipefail

REPO_SSH="${MIAMSTOCK_REPO:-git@github.com:NagamoTeur/MiamStock.git}"
APP_DIR="${MIAMSTOCK_APP_DIR:-/opt/miamstock}"
DEPLOY_KEY="/root/.ssh/id_ed25519"

vert()  { printf '\033[32m%s\033[0m\n' "$*"; }
jaune() { printf '\033[33m%s\033[0m\n' "$*"; }
rouge() { printf '\033[31m%s\033[0m\n' "$*"; }
etape() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

# Un LXC fait tourner systemd ; un conteneur Docker, non. Le distinguer évite
# un échec cryptique de systemctl et permet de tester le script hors LXC.
systemd_actif() { [[ -d /run/systemd/system ]]; }

activer_service() {
    if systemd_actif; then
        systemctl enable --now "$1"
    else
        jaune "systemd absent : pense à activer $1 toi-même."
    fi
}

[[ $EUID -eq 0 ]] || { rouge "À lancer en root."; exit 1; }
[[ -r /etc/os-release ]] || { rouge "Système non reconnu."; exit 1; }
# shellcheck disable=SC1091
. /etc/os-release
CODENAME="${VERSION_CODENAME:-bookworm}"
vert "Système : $PRETTY_NAME (codename $CODENAME)"

# --- 1. Paquets de base ------------------------------------------------------
etape "Paquets de base"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg git sqlite3 >/dev/null
vert "curl, git, gnupg, sqlite3 installés"

# --- 2. Docker ---------------------------------------------------------------
# Dépôt officiel Docker signé, plutôt qu'un script distant exécuté à l'aveugle :
# la clé est vérifiée par apt à chaque mise à jour.
etape "Docker"
if command -v docker >/dev/null 2>&1; then
    vert "Docker déjà présent : $(docker --version)"
else
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL "https://download.docker.com/linux/debian/gpg" \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $CODENAME stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null
    activer_service docker
    vert "Installé : $(docker --version)"
fi

if ! docker info >/dev/null 2>&1; then
    rouge "Le démon Docker ne répond pas."
    jaune "Dans un LXC non privilégié, il faut activer 'nesting=1' ET 'keyctl=1'."
    jaune "Sur l'hôte Proxmox : pct set <ID> --features nesting=1,keyctl=1 && pct reboot <ID>"
    exit 1
fi

# --- 3. Tailscale ------------------------------------------------------------
etape "Tailscale"
if command -v tailscale >/dev/null 2>&1; then
    vert "Tailscale déjà présent : $(tailscale version | head -1)"
else
    curl -fsSL "https://pkgs.tailscale.com/stable/debian/${CODENAME}.noarmor.gpg" \
        -o /usr/share/keyrings/tailscale-archive-keyring.gpg
    curl -fsSL "https://pkgs.tailscale.com/stable/debian/${CODENAME}.tailscale-keyring.list" \
        -o /etc/apt/sources.list.d/tailscale.list
    apt-get update -qq
    apt-get install -y -qq tailscale >/dev/null
    activer_service tailscaled
    vert "Installé : $(tailscale version | head -1)"
fi

# Sans /dev/net/tun, tailscaled démarre mais ne peut pas monter d'interface.
if [[ ! -c /dev/net/tun ]]; then
    rouge "/dev/net/tun absent : Tailscale ne pourra pas fonctionner en mode normal."
    jaune "Sur l'hôte Proxmox, ajoute à /etc/pve/lxc/<ID>.conf :"
    jaune "  lxc.cgroup2.devices.allow: c 10:200 rwm"
    jaune "  lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file"
    jaune "puis 'pct reboot <ID>'. Repli sans toucher à l'hôte :"
    jaune "  tailscale up --tun=userspace-networking"
fi

# --- 4. Clé de déploiement ---------------------------------------------------
etape "Accès au dépôt"
mkdir -p /root/.ssh && chmod 700 /root/.ssh
if [[ ! -f "$DEPLOY_KEY" ]]; then
    ssh-keygen -t ed25519 -C "miamstock-lxc-$(hostname)" -f "$DEPLOY_KEY" -N "" -q
    vert "Clé de déploiement générée."
fi
ssh-keyscan -t ed25519 github.com 2>/dev/null >> /root/.ssh/known_hosts
sort -u /root/.ssh/known_hosts -o /root/.ssh/known_hosts

if ! ssh -o BatchMode=yes -o ConnectTimeout=8 -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    rouge "GitHub refuse cette machine : le dépôt est privé et la clé n'est pas encore autorisée."
    echo
    jaune "Il s'agit de la clé DE CE CONTENEUR, pas de celle de ton poste :"
    echo
    cat "${DEPLOY_KEY}.pub"
    echo
    # La commande est donnée prête à coller, IP comprise : se tromper de clé et
    # autoriser celle de son PC est l'erreur naturelle à ce stade.
    IP_LOCALE="$(hostname -I 2>/dev/null | awk '{print $1}')"
    jaune "Depuis ton PC, en une commande :"
    echo
    echo "  ssh root@${IP_LOCALE} 'cat ${DEPLOY_KEY}.pub' > /tmp/miamstock-lxc.pub \\"
    echo "    && gh repo deploy-key add /tmp/miamstock-lxc.pub --title \"miamstock-lxc\" --repo NagamoTeur/MiamStock"
    echo
    jaune "Ou sur github.com → le dépôt → Settings → Deploy keys → Add deploy key,"
    jaune "en collant le bloc ci-dessus et sans cocher 'Allow write access'."
    echo
    jaune "Puis relance ce script : il reprendra où il s'est arrêté."
    exit 2
fi
vert "GitHub authentifie cette machine."

# --- 5. Code source ----------------------------------------------------------
etape "Dépôt"
if [[ -d "$APP_DIR/.git" ]]; then
    git -C "$APP_DIR" fetch --quiet origin
    git -C "$APP_DIR" reset --hard --quiet origin/main
    vert "Mis à jour sur $(git -C "$APP_DIR" rev-parse --short HEAD)"
else
    git clone --quiet "$REPO_SSH" "$APP_DIR"
    vert "Cloné dans $APP_DIR"
fi
cd "$APP_DIR"

# --- 6. Configuration --------------------------------------------------------
etape "Configuration"
if [[ -f .env ]]; then
    vert ".env déjà présent, laissé intact."
else
    # Le PIN est tiré ici, sur ta machine : il n'a jamais transité ailleurs.
    PIN="$(shuf -i 100000-999999 -n 1)"
    cat > .env <<EOF
MIAMSTOCK_PIN=$PIN
MIAMSTOCK_USER_AGENT=MiamStock/0.1 (maison)
MIAMSTOCK_URGENT_DAYS=3
MIAMSTOCK_SOON_DAYS=7
TZ=Europe/Paris
EOF
    chmod 600 .env
    vert ".env créé."
    jaune "Code du foyer tiré au hasard : $PIN"
    jaune "Change-le quand tu veux dans $APP_DIR/.env, puis 'docker compose up -d'."
fi

# --- 7. Démarrage ------------------------------------------------------------
etape "Construction et démarrage"
docker compose up -d --build
sleep 3

for _ in $(seq 1 30); do
    if curl -sf -m 2 http://127.0.0.1:8077/api/health >/dev/null 2>&1; then break; fi
    sleep 1
done

if curl -sf -m 3 http://127.0.0.1:8077/api/health >/dev/null 2>&1; then
    vert "MiamStock répond : $(curl -s http://127.0.0.1:8077/api/health)"
else
    rouge "Le service ne répond pas. Journal :"
    docker compose logs --tail 40
    exit 1
fi

# --- 8. Suite ----------------------------------------------------------------
etape "Il reste à connecter Tailscale"
if tailscale status >/dev/null 2>&1; then
    vert "Tailscale est déjà connecté."
    tailscale serve --bg 8077 || true
    echo
    vert "Adresse de l'application :"
    tailscale serve status 2>/dev/null || true
else
    jaune "1. Connecte la machine au tailnet (une URL à ouvrir dans ton navigateur) :"
    echo "     tailscale up"
    jaune "2. Publie l'application en HTTPS :"
    echo "     tailscale serve --bg 8077"
    jaune "3. L'URL s'affiche avec :"
    echo "     tailscale serve status"
fi

echo
vert "Terminé. L'app écoute sur 127.0.0.1:8077, exposée uniquement via Tailscale."
