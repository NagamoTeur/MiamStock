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
- **Mode courses** : un écran plein, sans rien d'autre, où la liste est groupée
  **par rayon** plutôt que par ordre alphabétique — parce qu'en magasin on suit
  un trajet. Cibles de 60 px, et les lignes cochées se barrent sur place : une
  liste qui se réorganise sous le pouce fait perdre le fil.
- **Journal alimentaire** : calories du jour face à un objectif, macros en
  petit, quatre repas. On cherche un aliment par son nom ou on **scanne son
  code-barres**, la portion réelle du produit est proposée par défaut, et les
  aliments récents se ressaisissent en un geste. Un repas vide propose de
  reprendre **la dernière fois** (« Comme hier »), un repas rempli s'enregistre
  en **favori** d'une étoile, et la **saisie rapide** note un restaurant en
  calories, sans rien peser. Le journal ne retire rien du stock, sauf si on
  coche « j'ai fini le paquet ».
- **Recherche par nom** : ton stock d'abord, puis les aliments courants (table
  Ciqual de l'ANSES, embarquée, sans réseau), puis les produits du commerce
  (Open Food Facts). Elle sert au journal comme à la liste de courses.
- **Rythme de consommation** : l'application mesure la vitesse à laquelle chaque
  produit quitte le stock et en déduit le seuil de réappro. Mesuré sur le journal
  réel des sorties, jamais estimé : tant qu'il n'y a pas assez de mouvements
  étalés dans le temps, elle le dit au lieu d'inventer un chiffre.

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

Sur un LXC Debian fraîchement créé, [`deploy/install-lxc.sh`](deploy/install-lxc.sh)
fait tout : paquets de base, dépôt Docker signé, Tailscale, clé de déploiement,
clone, `.env` avec un code tiré au hasard, build et démarrage. Il est idempotent,
donc le relancer sert aussi à mettre à jour.

```bash
scp deploy/install-lxc.sh root@<ip-du-lxc>:/root/
ssh root@<ip-du-lxc> 'bash /root/install-lxc.sh'
```

Dépose-le dans `/root`, pas dans `/tmp` : le script peut réclamer un
redémarrage du conteneur pour le device TUN, et `/tmp` est vidé au boot. Une
fois le dépôt cloné, les mises à jour se font directement depuis lui :

```bash
ssh root@<ip-du-lxc> 'bash /opt/miamstock/deploy/install-lxc.sh'
```

Au premier passage il s'arrête sur la clé de déploiement, qu'il affiche : autorise-la
(section précédente), puis relance la même commande — il reprend où il s'était arrêté.

Il vérifie aussi ce que le conteneur ne peut pas corriger seul, et te donne la
commande à passer sur l'hôte Proxmox le cas échéant : `nesting=1` et `keyctl=1`
pour Docker, `/dev/net/tun` pour Tailscale.

À la main, si tu préfères :

```bash
git clone git@github.com:NagamoTeur/MiamStock.git /opt/miamstock && cd /opt/miamstock
cp .env.example .env && nano .env      # définis au moins MIAMSTOCK_PIN
docker compose up -d --build
tailscale serve --bg 8077
```

Le port est publié sur `127.0.0.1` uniquement : c'est Tailscale qui expose le
service, pas Docker. La base vit dans `./data`, monté en volume.

### Mises à jour automatiques

Le script d'installation pose deux timers systemd. Une fois en place, il n'y a
plus à se connecter au serveur : **un merge sur `main` est en ligne dans les
5 minutes**.

- `miamstock-maj.timer` lance [`deploy/mise-a-jour.sh`](deploy/mise-a-jour.sh)
  toutes les 5 minutes. Si `main` a bougé : sauvegarde de la base, construction
  de l'image — **les tests tournent pendant la construction**, et un test qui
  échoue l'arrête —, démarrage, puis vérification que c'est bien la nouvelle
  version qui répond. Au moindre échec, retour automatique au commit précédent.
  Un commit en échec n'est pas retenté en boucle : il faut un nouveau commit sur
  `main`, ou `deploy/mise-a-jour.sh --force`.
- `miamstock-sauvegarde.timer` sauvegarde la base chaque nuit à 3 h 15.

Le résultat de la dernière mise à jour s'affiche dans **Réglages → Version**,
avec le commit qui tourne : un déploiement raté se voit depuis le téléphone.
Sur le serveur, l'historique se lit avec `journalctl -u miamstock-maj`.

Pour installer les timers sur un serveur déjà en place, relance simplement le
script d'installation (il est idempotent) :

```bash
ssh root@<ip-du-lxc> 'cd /opt/miamstock && git pull --ff-only && bash deploy/install-lxc.sh'
```

### Vérifications sur GitHub

Chaque PR passe par [`.github/workflows/ci.yml`](.github/workflows/ci.yml) :
tests de l'API, `svelte-check` et contrôles de l'interface, `shellcheck` des
scripts de déploiement, puis construction de l'image Docker et démarrage sur une
base vide (l'interface est servie, la table Ciqual est embarquée, la recherche
répond). C'est ce qui garantit que `main` est déployable à tout moment.

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
MIAMSTOCK_DB=/opt/miamstock/data/miamstock.db deploy/sauvegarde.sh /var/backups/miamstock
```

Le script passe par `sqlite3 .backup`, qui prend un verrou propre : copier le
fichier `.db` à chaud produirait une base corrompue dès qu'un bip tombe au
mauvais moment. Chaque copie est **relue et vérifiée** (`PRAGMA integrity_check`)
avant d'être gardée ; les 30 dernières sont conservées. Le timer nocturne s'en
charge, et une copie à part est prise avant chaque mise à jour, dans
`/var/backups/miamstock/avant-mise-a-jour`. La marche à suivre pour restaurer
est en tête du script. Laisse le snapshot Proxmox faire le reste.

## Deux surfaces, deux métiers

L'application bascule d'elle-même à 1024 px. Ce n'est pas la même interface
redimensionnée : le téléphone et le PC ne font pas le même travail.

**Le téléphone capture.** Tout est jugé au nombre de gestes entre viser un
code-barres et l'avoir enregistré. Bascule « Je range / Je consomme » mémorisée,
dates par boutons rapides, emplacement pré-rempli par l'historique du produit.

**Le PC corrige et donne la vue d'ensemble**, et n'a pas de scanner — une caméra
de portable ne sert à rien devant un placard. Quatre vues, au clavier :

- **La frise des dates** — l'écran d'accueil. Le temps est l'axe horizontal, à
  échelle **non linéaire** : les sept prochains jours occupent la moitié de la
  largeur, parce que c'est là que les décisions se prennent, et six mois tiennent
  dans le reste. Un couloir par emplacement, chaque lot posé à sa date. Faire
  glisser une puce change sa date horizontalement et son emplacement
  verticalement — et la lâcher dans le couloir du congélateur éteint son alerte,
  puisque c'est précisément ce que congeler veut dire. `Échap` annule un glisser
  en cours. Les produits sans date vivent dans une bande à part : une conserve
  n'a pas sa place sur une frise et on ne lui invente pas une date.
- **Le registre** — un lot par ligne, colonnes triables et filtrables, édition en
  place, sélection multiple et actions groupées (sortir, déplacer, jeter).
- **Le catalogue** — tout produit jamais scanné, y compris à zéro, avec ses
  réglages durables : seuil mini, emplacement par défaut, durée de conservation.
- **Le journal** — le vrai relevé des bips, et le taux de gaspillage qui en
  découle : la part de ce qui sort du stock qui finit à la poubelle. Calculé, pas
  estimé.

Raccourcis : `/` ou `Ctrl+K` ouvre la saisie rapide (codes-barres à la chaîne
sans jamais toucher la souris), `1` à `4` changent de vue, `Échap` vide la
sélection.

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
├── lib/scanner.ts        BarcodeDetector natif, repli ZXing
├── lib/timescale.ts      l'échelle de temps non linéaire de la frise (module pur)
├── lib/rayons.ts         classement des produits en rayons de magasin (module pur)
├── lib/icons.ts          jeu d'icônes dessiné, grille 24, trait 1,7
├── lib/state.svelte.ts   état partagé (runes Svelte 5)
├── lib/desktop.svelte.ts état propre au PC : vue, sélection, catalogue
├── lib/ProductFields.svelte  la fiche produit, partagée par les deux surfaces
├── components/           surface téléphone
└── desktop/              surface PC : frise, registre, catalogue, journal
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
- **Le rythme de consommation est rapporté à la période réellement observée**,
  pas à la fenêtre d'analyse. Sur une application utilisée depuis trois semaines,
  diviser par quatre-vingt-dix jours sous-estimerait la consommation d'un facteur
  quatre. Et un rythme tiré de deux mouvements du même jour n'est pas une mesure :
  l'application refuse alors de proposer un seuil.
- **La recherche tolère les flexions du français, mais par leurs terminaisons
  réelles.** « complètes » doit trouver « complet », « pommes » trouver
  « pomme ». Une première version autorisait deux lettres d'écart, et
  « poulets » devenait alors une forme de « poule » : chercher du poulet
  renvoyait de la poule. La règle s'appuie donc sur une liste de terminaisons
  (s, x, e, es, ée, ées), pas sur une longueur.
- **Une seule décision d'arrondi, à l'affichage.** Le serveur garde deux
  décimales ; arrondir au dixième côté serveur puis à l'unité côté interface
  affichait 5 g dans un écran et 6 g dans l'autre pour la même entrée.
- **Le classement en rayon est grossier, et c'est voulu.** Les catégories d'Open
  Food Facts décrivent un aliment, pas un emplacement en magasin. Se tromper de
  rayon fait perdre dix secondes ; une taxonomie fine serait ingérable à la main.
  Les pièges réels sont les produits composés — un plat préparé au poulet n'est
  pas de la boucherie, un biscuit apéritif n'est pas de l'épicerie sucrée — et
  `npm --prefix web run check:rayons` les vérifie.
- **L'échelle de temps de la frise est non linéaire et inversible.** Inversible
  parce que lâcher une puce doit retrouver exactement la date visée :
  `npm --prefix web run check:timescale` le vérifie, ainsi que la monotonie et
  l'empilement des puces qui se chevauchent.

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
| `GET` | `/products` | Catalogue : tout produit connu, stock compris. |
| `GET` | `/history` | Journal des bips (`barcode`, `kind`, `limit`). |
| `GET` | `/stats` | Entrées, sorties, rebuts et taux de gaspillage. |
| `GET` | `/consumption` | Rythme par produit, autonomie restante, seuil suggéré. |
| `GET` | `/search` | Recherche par nom ; `scope=local` (stock + Ciqual, instantané) ou `off`. |
| `POST` | `/products/{code}/refresh` | Recharge valeurs et catégories depuis Open Food Facts. |
| `GET`/`POST`/`PATCH`/`DELETE` | `/diary` | Journal alimentaire d'un jour. |
| `GET` | `/diary/recent` | Aliments récemment saisis, pour les ressaisir. |
| `POST` | `/diary/repeat` | « Comme hier » : recopie un repas d'un jour précédent. |
| `GET`/`POST` | `/diary/templates` | Repas favoris : les lister, en enregistrer un depuis le journal. |
| `POST` | `/diary/templates/{id}/apply` | Ajoute un repas favori à un repas du jour. |
| `DELETE` | `/diary/templates/{id}` | Retire un repas favori. |
| `GET`/`PUT` | `/diary/settings` | Objectif calorique quotidien. |
| `GET` | `/health` | État et commit déployé (sans session : sert au script de mise à jour). |
| `GET` | `/about` | Version, date de construction, résultat de la dernière mise à jour. |

Documentation interactive : `/docs`.

## Données

**Aliments génériques** : table de composition nutritionnelle Ciqual 2020,
ANSES, diffusée sous Licence Ouverte (Etalab). Elle est convertie par
`scripts/build_ciqual.py` en un fichier de 224 Ko embarqué dans le paquet
Python : la recherche d'un aliment courant ne passe jamais par le réseau. Le
script répare au passage les fichiers XML publiés, qui contiennent des
caractères `<` et `&` non échappés et que tout parseur strict refuse.

```bash
.venv/bin/python scripts/build_ciqual.py <dossier des XML Ciqual>
```

**Produits du commerce** : les fiches viennent d'Open Food Facts, base ouverte et collaborative,
sans clé d'API. Si un produit manque, tu peux le créer localement avec un nom
libre — et, tant qu'à faire, [contribuer la fiche](https://world.openfoodfacts.org)
pour la prochaine personne.
