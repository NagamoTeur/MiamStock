# MiamStock

Inventaire alimentaire de la maison, piloté au scan de code-barres depuis le
téléphone. Une PWA à ajouter à l'écran d'accueil, une API FastAPI et une base
SQLite, le tout dans un seul process à héberger sur le Proxmox.

- **Bip d'entrée** : le code-barres est résolu via [Open Food Facts](https://world.openfoodfacts.org)
  (nom, marque, contenance, photo, Nutri-Score), puis rangé comme un **lot** avec
  sa quantité, sa date limite et son emplacement.
- **Bip de sortie** : décrémente en **FIFO** le lot qui périme le plus tôt, et
  bascule le produit en liste de courses quand le stock passe sous son seuil.
- **Onglet DLC** : périmé / à consommer sous 3 jours / cette semaine, trié du
  plus critique au moins. Le congélateur n'alerte qu'une fois la date passée.
- **Liste de courses** : alimentée automatiquement par les seuils, complétée à la
  main, partageable en un tap.

## Démarrage rapide (développement)

```bash
./dev.sh
```

Le script crée le virtualenv, installe les dépendances et lance l'API
(port 8077, rechargement à chaud) puis Vite (port 5273). Ouvre
<http://localhost:5273>.

Pour tout lancer depuis un seul port, comme en production :

```bash
npm --prefix web run build
.venv/bin/miamstock          # http://localhost:8077
```

Tests du backend :

```bash
.venv/bin/python -m pytest tests -q
```

Les tests n'appellent jamais Open Food Facts : le client est remplacé par un
catalogue figé, pour que la suite reste rapide et ne dépende pas du réseau.

## Le point qui bloque tout le monde : la caméra exige du HTTPS

`getUserMedia` n'est accessible que dans un **contexte sécurisé** : HTTPS, ou
`localhost`. Sur `http://192.168.1.x:8077` depuis un téléphone,
`navigator.mediaDevices` est purement et simplement `undefined` — aucun code ne
peut contourner ça. La saisie manuelle du code reste disponible, mais le scan,
non.

La solution retenue ici est **Tailscale**, qui fournit un certificat valide sans
ouvrir le moindre port sur Internet.

### Mise en place de Tailscale Serve

Prérequis, une seule fois, dans la console d'administration Tailscale : activer
**MagicDNS** puis **HTTPS Certificates** (onglet DNS). Sans ça, `tailscale serve`
n'a pas de certificat à présenter.

Sur la machine qui héberge MiamStock :

```bash
tailscale serve --bg 8077
```

L'app est alors disponible sur `https://<nom-machine>.<ton-tailnet>.ts.net`,
uniquement pour les appareils de ton tailnet. Vérifie avec `tailscale serve status`.

> N'utilise **pas** `tailscale funnel` : il exposerait ton stock alimentaire sur
> l'Internet public.

Autres options possibles : un reverse proxy Caddy/Traefik avec Let's Encrypt si
tu as déjà un domaine, ou `mkcert` sur le LAN — dans ce dernier cas il faut
installer l'autorité racine sur chaque téléphone, sinon Android et iOS bloquent
la caméra malgré le HTTPS.

## Déploiement sur Proxmox

### Donner au LXC l'accès au dépôt

Le dépôt est privé : le conteneur a besoin de ses propres identifiants. Une
**clé de déploiement** est préférable à un jeton personnel — elle est en lecture
seule, limitée à ce seul dépôt, et se révoque sans toucher au reste du compte.

Dans le LXC :

```bash
ssh-keygen -t ed25519 -C "miamstock-lxc" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```

Puis, depuis une machine où `gh` est connecté (ou via Settings → Deploy keys
sur GitHub), en collant la clé publique affichée :

```bash
gh repo deploy-key add cle.pub --title "proxmox-lxc" --repo NagamoTeur/MiamStock
```

Laisse la case « Allow write access » décochée : le conteneur n'a qu'à lire.

### Avec Docker (recommandé)

Dans un LXC Debian avec Docker, ou une VM :

```bash
git clone git@github.com:NagamoTeur/MiamStock.git /opt/miamstock && cd /opt/miamstock
cp .env.example .env && nano .env      # définis au moins MIAMSTOCK_PIN
docker compose up -d --build
tailscale serve --bg 8077
```

Le port est publié sur `127.0.0.1` uniquement : c'est Tailscale qui expose le
service, pas Docker. La base vit dans `./data`, monté en volume.

> LXC non privilégié : Docker y fonctionne, mais il faut activer `keyctl=1` et
> `nesting=1` dans les options du conteneur, côté Proxmox.

### Sans Docker

```bash
sudo adduser --system --group --home /var/lib/miamstock miam
sudo git clone git@github.com:NagamoTeur/MiamStock.git /opt/miamstock
cd /opt/miamstock
python3 -m venv .venv && .venv/bin/pip install .
npm --prefix web ci && npm --prefix web run build
echo 'MIAMSTOCK_PIN=1234' | sudo tee /etc/default/miamstock
sudo cp deploy/miamstock.service /etc/systemd/system/
sudo systemctl enable --now miamstock
```

### Sauvegardes

```bash
deploy/sauvegarde.sh /var/backups/miamstock
```

Le script passe par `sqlite3 .backup`, qui prend un verrou propre : copier le
fichier `.db` à chaud produirait une base corrompue dès qu'un bip tombe au
mauvais moment. Ajoute-le au cron, et laisse le snapshot Proxmox faire le reste.

## Installation sur le téléphone

Ouvre l'URL HTTPS, puis :

- **Android / Chrome** : menu ⋮ → « Installer l'application ».
- **iOS / Safari** : Partager → « Sur l'écran d'accueil ».

L'app s'ouvre alors en plein écran et démarre instantanément même sans réseau.
En revanche, **un bip a besoin du serveur** : hors ligne, l'interface affiche un
bandeau et refuse d'enregistrer plutôt que de faire croire à un succès.

## Configuration

Toutes les variables sont optionnelles sauf `MIAMSTOCK_PIN`, vivement conseillée.

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `MIAMSTOCK_PIN` | *(vide)* | Code du foyer. Vide = application ouverte. |
| `MIAMSTOCK_DATA_DIR` | `./data` | Base SQLite et clé de signature des sessions. |
| `MIAMSTOCK_DB` | `<data>/miamstock.db` | Chemin explicite de la base. |
| `MIAMSTOCK_SECRET` | *(généré, persisté)* | Signature des cookies de session. |
| `MIAMSTOCK_SESSION_DAYS` | `365` | Durée de vie d'une session. |
| `MIAMSTOCK_URGENT_DAYS` | `3` | Seuil de l'alerte rouge. |
| `MIAMSTOCK_SOON_DAYS` | `7` | Seuil de l'alerte « bientôt ». |
| `MIAMSTOCK_USER_AGENT` | `MiamStock/0.1 …` | En-tête exigé par Open Food Facts. |
| `MIAMSTOCK_WEB_DIST` | *(détecté)* | Dossier du front compilé. |
| `MIAMSTOCK_HOST` / `MIAMSTOCK_PORT` | `0.0.0.0` / `8077` | Écoute du serveur. |

## Comment c'est fait

```
src/miamstock/
├── config.py          réglages lus dans l'environnement
├── db.py              schéma SQLite, connexions, transactions
├── service.py         statut des DLC, sortie FIFO, réappro automatique
├── openfoodfacts.py   client API + normalisation des champs
├── auth.py            code PIN et cookie signé HMAC
├── main.py            application FastAPI, service de la PWA
└── routers/           session · stock · shopping
web/src/
├── lib/scanner.ts     BarcodeDetector natif, repli ZXing
├── lib/state.svelte.ts  état global (runes Svelte 5)
└── components/        scan, stock, DLC, courses, réglages
```

Quelques décisions qui méritent d'être connues avant de toucher au code :

- **Un lot par bip d'entrée.** Trois yaourts identiques achetés à trois dates
  différentes sont trois lots. Sans ça, la date affichée devient fausse dès le
  deuxième achat — et une date fausse est pire que pas de date.
- **La sortie est FIFO sur la DLC**, pas sur la date d'achat : on consomme ce qui
  périme le plus tôt. Les lots sans date passent en dernier.
- **Le congélateur n'alerte pas avant la date.** Une pizza surgelée à J+5 n'a rien
  d'urgent, et noyer l'onglet DLC avec le congélo le rendrait inutile.
- **Seuil et épuisement sont la même règle** : la liste de courses se déclenche
  quand `stock restant ≤ seuil`, et le seuil vaut 0 par défaut.
- **Les produits sont mis en cache localement.** Le deuxième scan d'un même
  code-barres ne touche plus le réseau, et l'app reste utilisable si Open Food
  Facts est indisponible.
- **ZXing n'est téléchargé que par les navigateurs qui en ont besoin.** Sur
  Chrome/Android, `BarcodeDetector` fait le travail nativement et les 390 ko du
  décodeur de secours ne sont jamais chargés.

## API

Toutes les routes sont sous `/api` et exigent le cookie de session dès qu'un PIN
est configuré.

| Méthode | Route | Rôle |
| --- | --- | --- |
| `POST` | `/session` | Ouvre une session avec le code du foyer. |
| `GET` | `/lookup/{code}` | Résout un code-barres (local puis Open Food Facts). N'écrit rien. |
| `POST` | `/stock/in` | Bip d'entrée : crée un lot. |
| `POST` | `/stock/out` | Bip de sortie : décrémente en FIFO. |
| `GET` | `/stock` | Stock agrégé par produit (`location_id`, `q`). |
| `GET` | `/expiring` | Ce qui périme, groupé par urgence. |
| `PATCH`/`DELETE` | `/lots/{id}` | Corriger ou jeter un lot. |
| `PATCH` | `/products/{code}` | Seuil mini, emplacement par défaut, nom. |
| `GET`/`POST`/`PATCH`/`DELETE` | `/shopping` | Liste de courses. |
| `GET` | `/summary` | Compteurs pour les badges d'onglets. |
| `GET` | `/history` | Journal des bips. |

Documentation interactive : `/docs`.

## Données

Les fiches produits viennent d'Open Food Facts, base ouverte et collaborative,
sans clé d'API. Si un produit manque, tu peux le créer localement avec un nom
libre — et, tant qu'à faire, [contribuer la fiche](https://world.openfoodfacts.org)
pour la prochaine personne.
