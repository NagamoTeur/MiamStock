---
name: MiamStock
description: Le stock d'un foyer, lu par la date — deux surfaces, un seul monde vert-charbon.
colors:
  fond: "#0d1310"
  surface: "#151e19"
  champ: "#1b2721"
  trait: "#253630"
  texte: "#e8f0ea"
  texte-attenue: "#93a69b"
  texte-efface: "#7c8f84"
  menthe: "#5fd39a"
  menthe-encre: "#062018"
  menthe-voile: "#1d3b2e"
  delai-large: "#5fd39a"
  delai-proche: "#e8b44a"
  delai-urgent: "#f0883e"
  delai-depasse: "#ef5f6b"
  fond-clair: "#f5f7f4"
  surface-clair: "#ffffff"
  champ-clair: "#eef1ed"
  trait-clair: "#dde3dd"
  texte-clair: "#131a15"
  texte-attenue-clair: "#5c6a60"
  texte-efface-clair: "#626f67"
  menthe-clair: "#0f7a50"
  menthe-encre-clair: "#ffffff"
  menthe-voile-clair: "#dff2e7"
  delai-large-clair: "#0f7a50"
  delai-proche-clair: "#8a5e00"
  delai-urgent-clair: "#a44608"
  delai-depasse-clair: "#b8232f"
typography:
  title:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 600
    lineHeight: 1.45
    letterSpacing: "-0.01em"
  subtitle:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 600
    lineHeight: 1.45
    letterSpacing: "normal"
  body:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "normal"
  secondary:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "0.85rem"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "normal"
  label:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "0.7rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.05em"
  number:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.4rem"
    fontWeight: 700
    lineHeight: 1.1
    fontFeature: "tabular-nums"
rounded:
  xs: "5px"
  sm: "8px"
  chip: "9px"
  field: "10px"
  md: "14px"
  lg: "20px"
  pill: "999px"
spacing:
  xs: "0.35rem"
  sm: "0.45rem"
  md: "0.7rem"
  lg: "0.9rem"
  xl: "1.1rem"
components:
  button:
    backgroundColor: "{colors.champ}"
    textColor: "{colors.texte}"
    rounded: "{rounded.md}"
    padding: "0 1rem"
    height: "46px"
  button-primary:
    backgroundColor: "{colors.menthe}"
    textColor: "{colors.menthe-encre}"
    rounded: "{rounded.md}"
    padding: "0 1rem"
    height: "46px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.texte}"
    rounded: "{rounded.md}"
    padding: "0 1rem"
    height: "46px"
  button-danger:
    backgroundColor: "{colors.champ}"
    textColor: "{colors.delai-depasse}"
    rounded: "{rounded.md}"
    padding: "0 1rem"
    height: "46px"
  chip:
    backgroundColor: "{colors.champ}"
    textColor: "{colors.texte}"
    rounded: "{rounded.pill}"
    padding: "0.35rem 0.7rem"
    typography: "{typography.secondary}"
  chip-on:
    backgroundColor: "{colors.menthe-voile}"
    textColor: "{colors.texte}"
    rounded: "{rounded.pill}"
    padding: "0.35rem 0.7rem"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.texte}"
    rounded: "{rounded.lg}"
    padding: "0.9rem"
  input:
    backgroundColor: "{colors.champ}"
    textColor: "{colors.texte}"
    rounded: "{rounded.md}"
    padding: "0.7rem 0.85rem"
  input-desk:
    backgroundColor: "{colors.champ}"
    textColor: "{colors.texte}"
    rounded: "{rounded.field}"
    padding: "0.45rem 0.55rem"
  lot-chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.texte}"
    rounded: "{rounded.chip}"
    padding: "0 0.5rem"
    height: "30px"
  lot-chip-selected:
    backgroundColor: "{colors.menthe-voile}"
    textColor: "{colors.texte}"
    rounded: "{rounded.chip}"
    height: "30px"
  rail-item:
    backgroundColor: "transparent"
    textColor: "{colors.texte-efface}"
    rounded: "{rounded.field}"
    padding: "0.6rem 0.2rem"
  rail-item-on:
    backgroundColor: "{colors.menthe-voile}"
    textColor: "{colors.menthe}"
    rounded: "{rounded.field}"
    padding: "0.6rem 0.2rem"
---

# Design System: MiamStock

## Overview

**Creative North Star : « Le garde-manger à la lampe verte »**

MiamStock se lit comme un inventaire tenu à la main sous une lampe : fond
vert-charbon presque noir, surfaces à peine plus claires, traits d'un pixel, et
une seule couleur vivante — une menthe froide — qui ne sert qu'à dire
« maintenant », « sélectionné » ou « valide ». Rien n'est décoratif : la densité
vient des données, pas des ornements, et chaque chiffre est aligné en colonne
parce qu'un inventaire dont les chiffres dansent ne se lit pas.

Le monde a été posé par la surface téléphone et n'a pas changé depuis. La
surface PC, livrée ensuite, n'a rien réinventé : elle hérite des mêmes jetons,
des mêmes rayons, de la même pile système, et ne change que la **composition**.
Le téléphone capture debout, au pouce, en une colonne de 560 px ; le PC corrige
assis, au clavier, en trois colonnes pleine hauteur. Le système est un, les
compositions sont deux, et c'est un principe, pas un accident.

La thèse de la surface PC est que **le temps est l'axe et non une colonne** : la
date n'est pas une pastille dans la septième colonne d'un tableau trié, elle est
la position horizontale de la chose. Ce que ce monde refuse : la grille de
cartes pastel des applications de cuisine, l'illustration, et l'emoji tenant
lieu de pictogramme.

**Key Characteristics :**

- Vert-charbon sombre par défaut, thème clair complet en miroir, aucun réglage manuel de thème.
- Un seul accent (menthe) ; quatre couleurs de délai qui ne racontent qu'une échéance.
- Pile système, aucune webfont, chiffres en `tabular-nums` partout.
- Traits d'un pixel, rayons doux (14 px et 20 px), ombres portées douces et rares.
- Un jeu d'icônes dessiné maison, grille 24, trait 1,7 — jamais d'emoji.
- Interface intégralement en français, y compris les messages techniques.

## Colors

Une palette monochrome vert-charbon, traversée par un seul accent menthe et par
une échelle de quatre couleurs qui ne parlent que de dates.

Les deux thèmes sont normatifs. Le thème sombre est celui par défaut ; le thème
clair est servi par `prefers-color-scheme: light` et redéfinit les mêmes noms de
jetons. Toutes les paires texte/fond des deux thèmes ont été mesurées par la
formule de luminance relative WCAG et passent 4,5:1 : en clair, l'accent et le
vert « large » atteignent 4,97:1 sur le fond, le jaune « proche » 5,29:1,
l'orange « urgent » 5,64:1, le rouge « dépassé » 5,87:1, le texte atténué
5,29:1, le texte effacé 4,89:1, et l'accent posé sur son voile 4,59:1 ; en
sombre, la paire la plus basse est le texte effacé à 5,47:1.

### Primary

- **Menthe froide** : la seule couleur vivante du système. Elle marque le trait
  d'aujourd'hui sur la frise, l'onglet ou la vue active, la sélection, la
  bordure d'un champ au focus, et le fond des actions primaires (où elle porte
  une encre très sombre en thème sombre, blanche en thème clair). Son voile sert
  de fond de sélection : lignes de tableau retenues, puce choisie, couloir cible
  d'un glisser.
- **Encre d'accent** : le texte posé sur un aplat menthe, jamais ailleurs.
- **Voile d'accent** : fond de sélection et de surlignage, jamais un fond de page.

### Secondary

L'échelle des délais. Ces quatre couleurs n'ont qu'un métier : dire à quelle
distance se trouve une date limite. Elles apparaissent sur les points de statut,
sur la teinte de la zone « périmé », et sur la barre de proportion du journal.

- **Vert large** (même valeur que l'accent) : la date est loin, ou l'emplacement
  est le congélateur — un lot congelé ne déclenche aucune alerte avant échéance.
- **Jaune proche** : la date approche.
- **Orange urgent** : la date est à quelques jours.
- **Rouge dépassé** : la date est passée. Ce rouge porte en plus, dans tout le
  produit, le registre de la perte et de l'erreur : bandeau d'anomalie, pastille
  de compteur d'alerte, part « jetée » de la barre du journal, action
  destructrice. C'est la seule couleur de délai qui a ce second emploi.

### Neutral

- **Vert-charbon** : le fond de l'application, et le fond des en-têtes collants
  de tableau et de l'axe de la frise, pour qu'ils masquent le contenu qui passe dessous.
- **Surface élevée** : cartes, feuilles modales, panneau latéral, puces de lot,
  toasts, barre de commande. C'est le seul « plan au-dessus » du système.
- **Champ** : fond des entrées, des boutons neutres, des steppers, des segments.
- **Trait** : la bordure d'un pixel. C'est elle qui découpe la mise en page —
  couloirs, colonnes, en-têtes, séparateurs de lots — et non des ombres.
- **Texte / atténué / effacé** : trois niveaux et pas un de plus. Le texte plein
  pour la donnée, l'atténué pour les libellés et les légendes, l'effacé pour les
  onglets au repos, les compteurs et les repères mineurs de l'axe.

### Named Rules

**La règle de la voix unique.** La menthe ne dit que quatre choses :
aujourd'hui, actif, sélectionné, action primaire. Elle n'est jamais une
décoration, jamais un fond de page, jamais une couleur de titre.

**La règle de la couleur qui date.** Jaune, orange et rouge n'expriment qu'une
échéance. Aucun de ces trois n'est autorisé à qualifier une catégorie, une
marque ou un emplacement. Le rouge dispose seul d'un second registre, la perte
et l'erreur, et il l'exerce sur le bandeau, la pastille de compteur, l'action
destructrice et la part jetée du journal.

**La règle des deux thèmes.** Tout ce qui est écrit en couleur est écrit avec un
nom de jeton, jamais avec une valeur littérale : c'est la seule chose qui fait
tenir le thème clair. Un `#hex` posé dans un composant casse le miroir.

## Typography

**Police unique :** la pile système (`system-ui`, `-apple-system`, `Segoe UI`,
`Roboto`, sans-serif). Aucune webfont n'est chargée, aucune police d'affichage
n'existe.

**Caractère :** neutre, dense et local. Le choix de la pile système n'est pas une
économie : l'application est un outil consulté dix secondes devant un frigo ou
une heure devant un tableau, et elle doit ressembler à l'appareil qui l'affiche.
La personnalité vient de la couleur et de la composition, pas du dessin des
lettres.

### Hierarchy

- **Titre** (600, 1,15 rem téléphone / 1,05 rem PC, interlettrage -0,01 em) :
  le titre de la barre haute, un par écran, jamais deux.
- **Sous-titre** (600, 0,95–1,1 rem) : titre d'une feuille modale, d'un panneau
  latéral, d'une section de fiche.
- **Corps** (400, 16 px, interligne 1,45) : la donnée. Les entrées de formulaire
  restent à 16 px même là où le design serait plus compact — en dessous, Safari
  iOS zoome au focus.
- **Secondaire** (400, 0,85 rem, texte atténué) et **effacé** (0,78 rem, texte
  effacé) : légendes, marques, dates lues, aides.
- **Étiquette** (600, 0,7–0,72 rem, interlettrage 0,05 em, capitales) :
  en-têtes de tableau, titres de section du panneau, en-têtes de l'axe de la
  frise, bandeau « sans date ». C'est le seul emploi des capitales du système.
- **Nombre** (700, 1,05–1,4 rem, `tabular-nums`) : quantités, valeurs de
  stepper, compteurs.

### Named Rules

**La règle de la colonne de chiffres.** Tout chiffre susceptible de changer ou
d'être comparé est en `tabular-nums` : quantités, valeurs, cellules et en-têtes
de tableau, éléments `<time>`. La règle est posée globalement, pas composant par
composant.

**La règle des capitales rares.** Les capitales et l'interlettrage élargi sont
réservés aux étiquettes de structure sous 0,75 rem. Aucun titre, aucun bouton,
aucune donnée n'est en capitales.

## Layout

**Deux surfaces, un seuil.** Le basculement est structurel et non typographique :
au-dessus de 1024 px la surface PC est servie, en dessous la surface téléphone.
Il n'y a pas d'état intermédiaire — entre 768 et 1024 px, la frise n'est pas
servie du tout.

**Téléphone.** Une colonne unique de 560 px maximum, centrée, en rembourrage
latéral de 1 rem, avec les encoches respectées en haut et en bas
(`env(safe-area-inset-*)`). Une barre d'onglets fixe de 62 px en pied, à cinq
colonnes égales, en surface translucide floutée à 12 px. Tout le contenu
descendant réserve la hauteur de cette barre.

**PC.** Une grille pleine fenêtre, sans défilement de page : rail de navigation
de **76 px** à gauche, contenu au centre, panneau de **336 px** à droite.
Le panneau n'existe que pour les vues qui ont une sélection à montrer (frise,
registre, catalogue) ; le journal occupe toute la largeur. Le défilement est
interne à chaque zone, jamais global.

**La frise.** Une grille à trois colonnes reproduite ligne par ligne :
libellé du couloir (**132 px**), zone « périmé » compressée (**108 px**), puis
la piste du temps en `minmax(0, 1fr)`. L'axe est collant en haut, la bande
« sans date » est collée en bas et plafonnée à 28 % de la hauteur de fenêtre,
et les couloirs défilent entre les deux. Un couloir fait au minimum 74 px et
grandit par rangs de 36 px quand les puces doivent s'empiler pour ne pas se
recouvrir. Une ligne de remplissage prolonge les trois colonnes sous le dernier
couloir, pour que le champ se termine par une limite et non par une interruption.

**Rythme.** Le pas d'espacement est en rem et se lit en cinq crans :
0,35 / 0,45 / 0,7 / 0,9 / 1,1 rem. Les cibles tactiles du téléphone ne
descendent pas sous 44–46 px ; le PC, qui vise à la souris, compresse ses
contrôles à 30–34 px.

### Named Rules

**La règle de l'échelle non linéaire.** Sur la frise, un jour n'a pas une
largeur constante : la piste donne **la moitié de sa largeur aux 7 prochains
jours**, puis 50→77 % aux jours 7 à 42, 77→94 % aux jours 42 à 180, et comprime
tout le reste jusqu'à l'horizon de deux ans dans les 6 % restants. La raison
est la décision : on choisit ce qu'on mange à sept jours, pas à trois mois, et
une échelle constante écraserait la semaine qui vient dans les premiers
pour-cent de l'écran. La courbe est **monotone et exactement inversible au jour
près** — c'est cette propriété, et non les chiffres, qui doit survivre à toute
évolution : elle est ce qui fait qu'une puce lâchée atterrit sur la date visée.
Tout nouvel usage du temps comme espace passe par ce module ; personne ne
recalcule une position de date à la main.

**La règle des repères lisibles.** Les repères de l'axe sont placés majeurs
d'abord ; un repère mineur n'est posé que s'il reste au moins 54 px libres entre
lui et tous les repères déjà placés. Dans la zone comprimée, mieux vaut trois
repères lisibles que dix illisibles.

**La règle du défilement local.** Aucune surface PC ne défile globalement. Le
rail, l'axe et la barre haute sont fixes ; seules les zones de données
défilent, chacune pour son compte.

## Elevation & Depth

Le système est **presque plat et fonctionne par superposition tonale** : trois
plans de fond (fond, surface élevée, champ) séparés par des bordures d'un pixel.
La bordure est le principal outil de profondeur — c'est elle qui fait exister les
couloirs, les colonnes, les cartes et les lignes de tableau. Le rail de
navigation pousse la logique plus loin encore : il est simplement teinté plus
froid que le contenu, ce qui suffit à le détacher sans une seule bordure
supplémentaire.

Les ombres sont réservées à ce qui **flotte réellement au-dessus du plan** :
une feuille modale, un toast, une barre d'actions groupées, la barre de commande,
la puce en cours de glissement. Elles sont toujours décalées vers le bas et
floues — jamais un halo centré, jamais un décalage dur sans flou.

### Shadow Vocabulary

- **Ombre de surface** (`--shadow`, `0 10px 30px rgb(0 0 0 / 0.45)` en sombre,
  `0 8px 24px rgb(19 26 21 / 0.12)` en clair) : feuilles modales et toasts.
- **Ombre de puce** (`0 2px 6px rgb(0 0 0 / 0.3)`) : les puces de lot de la
  frise, posées juste au-dessus de leur couloir.
- **Ombre d'aperçu de glisser** (`0 6px 18px rgb(0 0 0 / 0.45)`) : la puce
  fantôme qui suit le pointeur.
- **Ombre de barre flottante** (`0 8px 24px rgb(0 0 0 / 0.45)`) : la barre
  d'actions groupées.
- **Ombre de dialogue** (`0 18px 50px rgb(0 0 0 / 0.5)`) : la barre de commande,
  le seul élément qui s'élève au-dessus de toute la fenêtre.

### Named Rules

**La règle du trait avant l'ombre.** La séparation par défaut est une bordure
d'un pixel ou un changement de plan tonal. Une ombre ne se justifie que si
l'élément flotte vraiment au-dessus du reste ; une carte au repos n'en porte pas.

**La règle de l'ombre décalée.** Toute ombre a un décalage vertical et un flou.
Une ombre sans décalage n'est qu'un halo, et un décalage sans flou appartient à
un autre monde que celui-ci.

## Shapes

Des rectangles à coins doux, jamais de biseau, jamais de cercle décoratif. Le
rayon suit la taille et le rôle : **20 px** pour les grandes surfaces (cartes,
feuilles modales, viseur, barre de commande), **14 px** pour les contrôles de
taille normale (boutons, entrées, segments, barre d'actions groupées), **10 à
12 px** pour les contrôles compressés du PC et les boutons du rail, **8 à 9 px**
pour les plus petits objets (puce de lot, case à cocher, champ en ligne de
tableau), **5 px** pour un `code` ou une touche `kbd`. Les feuilles modales du
téléphone n'arrondissent que leurs deux coins hauts : elles montent du bas de
l'écran et leur base appartient au bord.

La forme en pilule (999 px) est réservée à ce qui compte ou qui filtre :
pastilles de filtre, badges, toasts, étiquettes, et le repère « aujourd'hui » au
pied du trait de la frise. Les points de statut sont des disques de 9 px, la
seule géométrie parfaitement ronde du système.

**Icônes.** Un jeu dessiné pour le projet : grille de 24 × 24, trait unique de
**1,7**, extrémités et jonctions arrondies, remplissage nul, couleur héritée par
`currentColor`. Les formes qui devraient être des cercles sont décrites en arcs,
pour ne garder qu'un seul type de nœud dans tout le jeu. Les tailles réellement
employées sont 14, 15, 16, 20, 22 et 44 px ; une icône seule sans libellé est
marquée décorative, une icône porteuse de sens reçoit un `label`.

### Named Rules

**La règle du trait unique.** Toute nouvelle icône se dessine sur la même grille
24, au même trait 1,7, avec les mêmes extrémités arrondies, sans aplat. Une
icône qui n'obéit pas à ces trois valeurs se voit immédiatement à côté des
autres.

**La règle : un emoji n'est pas une icône.** Aucun emoji ne tient lieu de
pictogramme, nulle part. Cinq emoji côte à côte dans une barre d'onglets sont
cinq dessins empruntés à cinq endroits : ni grille, ni graisse, ni style
communs, et un rendu qui change avec le système. Un besoin de pictogramme se
règle en ajoutant une entrée au jeu d'icônes.

## Components

### Buttons

- **Forme :** coins doux (14 px), hauteur minimale 46 px au téléphone, 56 px
  pour la variante longue.
- **Neutre :** fond champ, bordure d'un pixel, graisse 550.
- **Primaire :** aplat menthe, bordure menthe, encre d'accent.
- **Fantôme :** fond transparent, bordure conservée.
- **Danger :** texte rouge dépassé, bordure rouge à 40 % — jamais un aplat
  rouge plein.
- **Icône seule :** carré de 46 px (40 px en fantôme), sans le rembourrage
  horizontal calibré pour du texte.
- **États :** enfoncement par `scale(0.97)` en 80 ms au tapotement ; opacité
  0,45 et curseur interdit à l'état désactivé ; contour menthe de 2 px à 2 px
  de décalage au focus clavier.

### Chips

- **Filtre :** pilule à fond champ, bordure d'un pixel, 0,82 rem. À l'état
  retenu, fond voile d'accent et bordure menthe à 45 %.
- **Rangée :** les rangées de pastilles défilent horizontalement sans barre
  visible ; le fondu de bord n'est posé que sur les rangées qui débordent
  vraiment. Dans un panneau étroit, la rangée passe à la ligne au lieu de
  défiler.

### Cards / Containers

- **Rayon :** 20 px. **Fond :** surface élevée. **Bordure :** un pixel de trait.
  **Ombre :** aucune au repos. **Rembourrage :** 0,9 rem. Deux cartes
  consécutives sont séparées de 0,7 rem.

### Inputs / Fields

- **Style :** fond champ, bordure d'un pixel, rayon 14 px (10 px dans le
  panneau PC et les formulaires denses), 16 px de corps au téléphone.
- **Focus :** contour menthe de 2 px, décalé de 2 px — le même sur les boutons
  et les listes déroulantes.
- **Champ en ligne de tableau :** invisible au repos (fond et bordure
  transparents), révélé au survol par la bordure de trait et le fond champ,
  bordure menthe au focus. Un tableau ne montre ses champs que lorsqu'on
  s'approche d'eux.
- **Presets d'étagère :** une rangée de pastilles (+3 j, +1 sem., +2 sem.,
  +1 mois, +6 mois, +1 an) accompagne toute saisie de date limite.

### Navigation

- **Téléphone :** barre d'onglets fixe de 62 px, cinq colonnes égales, fond de
  surface élevée à 92 % avec flou d'arrière-plan de 12 px, bordure haute d'un
  pixel. Icône 22 px au-dessus d'un libellé de 0,66 rem ; texte effacé au repos,
  menthe à l'état actif. Le badge de compteur est une pilule rouge posée sur
  l'icône, détachée par un liseré de 2 px de la couleur du fond.
- **PC :** rail vertical de 76 px, teinté plus froid que le contenu, bordure
  droite d'un pixel. Marque de l'application en haut (34 px, rayon 9 px), quatre
  vues, un ressort, puis les actions globales (saisir, rafraîchir) en pied.
  Chaque bouton est une icône de 20 px au-dessus d'un libellé de 0,66 rem, en
  rayon 12 px ; survol par un voile de texte à 6 %, état actif en menthe sur
  voile d'accent. Les vues sont aussi atteignables aux touches 1 à 4.

### Tables

- **En-têtes :** collants, en capitales de 0,7 rem, interlettrage 0,04 em, texte
  atténué, fond de page opaque, bordure basse d'un pixel. Les colonnes triables
  passent au texte plein au survol et affichent leur sens de tri en menthe.
- **Cellules :** 0,45 rem sur 0,7 rem, séparateur à 65 % d'opacité du trait, les
  colonnes numériques alignées à droite en `tabular-nums`.
- **Lignes :** survol par un voile de texte à 4 %, sélection en voile d'accent.

### La frise des dates (composant signature)

Le cœur de la surface PC. Un couloir horizontal par emplacement, chaque lot posé
à sa date sur la piste non linéaire. À gauche du trait d'aujourd'hui, une zone
« périmé » compressée et teintée du rouge dépassé à 7 % ; les lots périmés y sont
empilés en puces larges, hors de la piste. Le trait d'aujourd'hui est une ligne
menthe de 2 px à 55 % d'opacité qui traverse tous les couloirs d'un seul tenant
et se nomme par une pilule à son extrémité basse.

- **Puce de lot :** hauteur 30 px, rayon 9 px, surface élevée sur bordure de
  trait, ombre de puce, curseur `grab`. Elle porte un point de statut, une
  quantité en 700 et un nom tronqué à 13 caractères. Survol : bordure à
  mi-chemin de la menthe. Sélection : bordure menthe pleine et fond voile
  d'accent. En cours de glissement : opacité 0,55 et curseur `grabbing`.
- **Glisser :** horizontalement la puce change de date, verticalement
  d'emplacement. Le couloir survolé s'éclaire en voile d'accent. Un aperçu suit
  le pointeur et **annonce la date d'atterrissage en toutes lettres** avant le
  lâcher. Un clic sans déplacement reste un clic : il sélectionne. `Échap`
  abandonne le glisser en cours.
- **Bande « sans date » :** collée en bas, fond intermédiaire entre surface et
  fond, séparée par une bordure haute. Les lots sans date limite y vivent en
  puces libres ; on ne leur invente pas une position sur l'axe. Y faire glisser
  une puce lui retire sa date ; en faire sortir une la lui donne. Vide, la bande
  se réduit à sa seule étiquette.

### Bulk bar

Barre flottante centrée à 1,1 rem du bas de la vue, surface élevée, **bordure
menthe pleine** — la seule bordure d'accent pleine du système hors sélection.
Rayon 14 px, ombre de barre flottante, entrée en 180 ms avec une courbe sortante
depuis 10 px plus bas. Elle n'existe que lorsqu'il y a une sélection.

### Command bar

Ouverte par `/` ou `Ctrl/⌘+K`, centrée à 14 % de la hauteur de fenêtre sur un
voile noir à 50 %. Largeur `min(560px, 92vw)`, rayon 20 px, ombre de dialogue.
Le champ occupe toute la largeur sans bordure ni rayon propres, en 1,05 rem, et
supprime son contour de focus — c'est le dialogue entier qui est le focus. Une
ligne d'aide en texte effacé ferme le bas, avec les touches en `kbd`.

### Named Rules

**La règle de l'aperçu honnête.** Un geste qui modifie une donnée annonce son
résultat avant de le commettre : le glisser d'une puce affiche la date exacte à
laquelle elle va atterrir, et un lâcher sans déplacement ne modifie rien.

**La règle du mouvement porteur.** Le mouvement ne sert qu'à porter un
changement d'état : transitions d'état en 150 ms, entrées de surface en
180–220 ms, enfoncement de bouton en 80 ms. Aucune chorégraphie au chargement,
aucune animation décorative, et toute animation est désactivée sous
`prefers-reduced-motion: reduce`.

## Do's and Don'ts

### Do:

- **Do** n'écrire les couleurs qu'en noms de jetons (`var(--accent)`,
  `var(--border)`) : c'est la seule chose qui fait tenir le thème clair.
- **Do** passer par le module d'échelle de temps pour toute conversion
  jour ↔ position, et préserver son inversibilité exacte au jour près.
- **Do** donner la moitié de la piste aux sept prochains jours : c'est
  l'horizon de décision du foyer.
- **Do** dessiner toute nouvelle icône sur la grille 24 au trait 1,7, extrémités
  arrondies, sans aplat, en `currentColor`.
- **Do** mettre en `tabular-nums` tout chiffre comparable ou changeant.
- **Do** séparer par une bordure d'un pixel ou un changement de plan tonal
  avant d'envisager une ombre.
- **Do** garder 16 px de corps sur les entrées du téléphone, sous peine de zoom
  automatique au focus sur iOS.
- **Do** réserver les capitales et l'interlettrage élargi aux étiquettes de
  structure sous 0,75 rem.
- **Do** composer différemment sur les deux surfaces : le téléphone capture en
  une colonne au pouce, le PC corrige en trois colonnes au clavier.
- **Do** annoncer le résultat d'un geste destructeur ou modifiant avant qu'il ne
  soit commis.

### Don't:

- **Don't** employer un emoji comme pictogramme, nulle part, dans aucune des
  deux surfaces.
- **Don't** charger une webfont ni introduire une seconde famille : la pile
  système est la seule police du produit.
- **Don't** utiliser le jaune, l'orange ou le rouge pour autre chose qu'une
  échéance — le rouge ayant seul le droit supplémentaire de dire la perte et
  l'erreur.
- **Don't** peindre une page ou un grand aplat en menthe : l'accent vit sur
  des traits, des états et des petites surfaces.
- **Don't** poser une ombre sans décalage vertical ni flou, ni une ombre sur une
  carte au repos.
- **Don't** faire défiler globalement une vue PC : le rail, la barre haute et
  l'axe restent en place, les données défilent.
- **Don't** inventer une position sur l'axe pour un lot sans date : la bande
  « sans date » existe pour ça.
- **Don't** porter la densité du PC sur le téléphone, ni la parcimonie du
  téléphone sur le PC.
- **Don't** animer au chargement : le mouvement ne sert qu'à porter un
  changement d'état, et cède devant `prefers-reduced-motion`.
- **Don't** embarquer d'image générée ou de banque : les seuls rasters livrés
  sont les icônes d'application, rendues par `rsvg-convert` depuis les SVG
  commités à côté d'elles ; les photographies de produits sont chargées à
  l'exécution depuis Open Food Facts et ne sont jamais empaquetées.
