# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Un foyer, pas un utilisateur isolé. Tous les membres partagent un seul code PIN
et le même stock : l'application doit rester utilisable par quelqu'un qui n'a
jamais lu de documentation et qui ne l'a pas installée.

Deux situations distinctes, par le même foyer :

- **Au téléphone, debout dans la cuisine**, une main tenant le produit. Le geste
  dominant est le bip — ranger les courses, ou sortir ce qu'on va consommer.
  L'attention disponible est quasi nulle et l'interaction doit tenir au pouce.
- **Au PC, assis**, pour tout ce que le téléphone rend pénible : corriger en
  série, saisir au clavier un gros retour de courses, consulter l'ensemble du
  stock d'un coup d'œil, et regarder l'historique. Confirmé par l'utilisateur
  comme couvrant ces quatre usages à parts égales, sans dominante.

## Product Purpose

Savoir ce qu'il y a dans la maison et quand racheter — sans tenir de tableur.

**Correction issue de l'usage réel**, après la première mise en service : la
gestion des dates limites n'est pas le centre de ce produit, contrairement à ce
que supposait la conception initiale. L'utilisateur ne saisit pas les DLC. Le
gros du stock est une épicerie sèche, salée et sucrée, pour laquelle une date
limite n'a pas de sens exploitable ; la part réfrigérée, seule vraiment
concernée par les dates, reste minoritaire.

Le succès se mesure donc d'abord à : ne plus racheter ce qu'on a déjà, et ne
plus découvrir un manque au moment de cuisiner.

Les sorties **sont** enregistrées, le plus souvent au bouton « − 1 » depuis la
liste de stock. Le journal contient donc un signal de consommation réel, ce qui
rend calculable un rythme par produit — et non seulement estimable par
comptage. Ne pas jeter reste un bénéfice,
mais secondaire et limité au frais.

Conséquence pour la conception : le suivi par lot et l'ordre FIFO restent
justes et utiles — ils gèrent correctement les quantités — mais la date n'est
plus l'axe structurant de l'expérience. Toute surface qui présuppose des DLC
renseignées sera majoritairement vide chez cet utilisateur.

## Positioning

Le stock est suivi **par lot**, pas par produit : chaque entrée porte sa propre
quantité, sa propre date limite et son propre emplacement, et une sortie
consomme d'abord le lot qui périme le plus tôt. C'est ce qui rend la date
affichée vraie quand on achète le même yaourt deux semaines de suite — là où un
compteur unique par produit devient faux dès le deuxième achat.

Les fiches produits viennent d'Open Food Facts, base ouverte et sans clé, mises
en cache localement. L'ensemble est auto-hébergé : aucun compte, aucun
abonnement, et aucune donnée du foyer ne sort de la maison.

## Operating Context

Hébergé dans un conteneur LXC sur un Proxmox domestique, publié en HTTPS par
Tailscale et joignable uniquement depuis le tailnet du foyer. La PWA est
installée sur l'écran d'accueil du téléphone.

Le téléphone sert devant le frigo, le congélateur et les placards. Le PC sert
au bureau. Les deux attaquent la même base SQLite par la même API, et deux
personnes peuvent agir en même temps.

## Capabilities and Constraints

Fonctionnalités établies et livrées :

- Lots (quantité, date limite, emplacement) ; sortie FIFO sur la date la plus
  proche ; les lots sans date sont consommés en dernier.
- Emplacements typés. Le congélateur ne déclenche aucune alerte avant la date
  échue, contrairement au frigo et aux placards.
- Liste de courses alimentée par un seuil minimum par produit, le seuil 0 par
  défaut faisant coïncider « épuisé » et « à racheter ».
- Résolution des codes-barres via Open Food Facts, avec cache local permanent.
- Journal de tous les bips (entrée, sortie, rebut, ajustement), exposé par
  l'API et affiché nulle part à ce jour.
- Authentification par code PIN partagé, session d'un an par navigateur.

Contraintes qui ne se négocient pas :

- La caméra exige un contexte sécurisé. Hors HTTPS, le scan est impossible quel
  que soit le code.
- Le scan n'a aucun sens sur PC : la surface desktop s'en passe entièrement et
  doit offrir une saisie clavier au moins aussi rapide.
- Hors ligne, l'application se consulte mais ne s'écrit pas. Choix assumé : un
  faux succès sur un bip serait pire qu'une erreur franche.
- Pas de notification poussée. Les alertes de date sont visuelles, dans
  l'application. Choix assumé.
- Les quantités se comptent en pièces. La contenance d'Open Food Facts est
  affichée à titre indicatif et ne pilote aucun calcul.

Lacunes confirmées par l'utilisateur comme devant être comblées :

- Un produit absent d'Open Food Facts ne peut aujourd'hui recevoir qu'un nom.
  Il doit pouvoir porter ses propres valeurs.
- Aucune fiche produit n'existe : on ne peut ni renommer, ni régler un
  emplacement par défaut, ni consulter l'historique d'un produit.

## Brand Commitments

Le nom est **MiamStock**. L'interface est intégralement en français, y compris
les messages d'erreur et les libellés techniques.

## Evidence on Hand

Les données produits sont réelles et proviennent d'Open Food Facts. Aucun
contenu produit ne doit être inventé : un code-barres inconnu est déclaré
inconnu, jamais rempli de valeurs plausibles.

L'instance de production contient le stock réel d'un foyer. Il n'existe aucun
témoignage, aucune métrique d'usage, aucun client : rien de tel ne doit
apparaître dans l'interface.

## Product Principles

0. **Le stock et le réassort priment sur les dates.** L'axe utile est « combien
   il m'en reste et quand racheter », pas « quand ça périme ». Une fonctionnalité
   qui exige de saisir une date pour être utile sera inutilisée.
1. **Le bip prime sur tout le reste.** Chaque écran, chaque menu, chaque
   confirmation placée entre viser un code-barres et l'avoir enregistré est une
   régression. Le téléphone se juge au nombre de gestes, pas au nombre d'options.
2. **Une date fausse est pire qu'une date absente.** Le modèle par lot, l'ordre
   FIFO et la règle du congélateur existent pour ça. Toute évolution qui rendrait
   une date approximative est à refuser, même si elle simplifie l'interface.
3. **Les deux surfaces ont des métiers différents.** Le téléphone capture, le PC
   corrige et donne la vue d'ensemble. Porter la densité du PC sur le téléphone,
   ou la parcimonie du téléphone sur le PC, dégrade les deux.
4. **Rien ne s'invente.** Un produit inconnu est déclaré inconnu. Une statistique
   affichée sort du journal réel des bips ou n'est pas affichée.
5. **Utilisable sans mode d'emploi.** Le foyer entier s'en sert, pas seulement
   la personne qui l'a installée.
