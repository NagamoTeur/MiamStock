---
version: 1
slug: "web-src-desktop-desktopshell-svelte"
primary_target: "web/src/desktop/DesktopShell.svelte"
related_targets: ["web/src/App.svelte","web/src/desktop"]
---

## Scope

La surface PC de MiamStock (≥ 1024 px). Mode : Operate. Le monde visuel est
celui déjà livré dans le code et reste inchangé ; ce contrat fixe la composition.
Le téléphone garde sa propre surface et n'hérite de rien d'ici.

## Audience et tâche

Le foyer, assis au bureau, pour les quatre usages qu'il a nommés à parts égales :
corriger en série, saisir au clavier un gros retour de courses, voir l'ensemble
du stock d'un coup, et consulter l'historique. Pas de scan : le PC n'a pas de
caméra utile, il a un clavier.

## Direction contract

THESIS: Le temps est l'axe, pas une colonne. Cette surface refuse l'arrangement
que cette catégorie livre toujours — un tableau trié par date où l'urgence est
une pastille de couleur dans la septième colonne. Ici, la date *est* la position :
ce qui presse est physiquement à gauche, près du trait d'aujourd'hui, et on lit
la semaine qui vient sans trier quoi que ce soit.

OWN-WORLD: Le monde livré, inchangé. Fond vert-charbon `#0d1310`, surfaces
`#151e19`, bordures `#253630`, accent menthe `#5fd39a` réservé à aujourd'hui, à
la sélection et aux actions primaires. Urgence en `#e8b44a` / `#f0883e` /
`#ef5f6b`, jamais ailleurs que sur une date. Pile système, chiffres en
`tabular-nums` partout. Rayons 14 px, traits 1 px. Icônes : le jeu dessiné maison,
grille 24, trait 1,7 — aucun emoji. Rail de navigation en surface légèrement plus
froide que le contenu.

STORY: L'utilisateur arrive, voit immédiatement ce qui meurt cette semaine sans
avoir rien trié, corrige une date en faisant glisser un lot, sauve un produit en
le faisant tomber dans le couloir du congélateur, et repart en sachant ce qu'il
doit manger avant samedi.

FIRST VIEWPORT: Rail de navigation à gauche (72 px, icônes + libellés : Frise,
Registre, Catalogue, Journal), surface légèrement plus froide. Le reste est la
frise. En haut, l'axe du temps sur toute la largeur, à échelle **non linéaire** :
les 7 prochains jours occupent la moitié de la largeur, les 5 semaines suivantes
un tiers, le reste comprimé — parce que les décisions se prennent à sept jours,
pas à trois mois. Le trait d'aujourd'hui en menthe pleine hauteur. À sa gauche,
une zone « périmé » compressée et teintée rouge sourd. Sous l'axe, un couloir
horizontal par emplacement, chaque lot posé à sa date comme une puce portant nom,
quantité et point de statut. Tout en bas, une bande distincte « sans date » :
les conserves n'ont pas de place sur une frise et on ne leur en invente pas une
fausse. À droite, un panneau de 320 px qui montre le jour ou la sélection en
cours, éditable sur place. Barre de saisie clavier en haut à droite, toujours
atteignable par `/`, qui accepte un code-barres ou un nom.

FORM: « La frise des dates », index 4 de ma liste ordonnée de sept structures,
tirée en tête par les dés et verrouillée par l'utilisateur. Seed key : 6fa8672a.
Interaction signature : le glisser d'une puce. Horizontalement elle change de
date, verticalement elle change d'emplacement — et faire tomber un produit dans
le couloir du congélateur draine sa couleur d'urgence, parce que c'est exactement
ce que congeler veut dire. Motion : 150–250 ms, uniquement pour porter un
changement d'état, jamais de chorégraphie au chargement.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Décisions non tranchées

- Le registre, le catalogue et le journal sont des vues sœurs dans la même
  coquille : ils héritent du système sans que ce contrat fixe leur composition.
- Le seuil de bascule téléphone/PC est à 1024 px ; entre 768 et 1024 la frise
  n'est pas servie.
