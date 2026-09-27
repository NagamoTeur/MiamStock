/* Classement d'un produit en rayon de magasin.
 *
 * Les catégories d'Open Food Facts sont du texte libre et collaboratif
 * (« Produits à tartiner sucrés, Pâtes à tartiner, Nuttela ») : elles décrivent
 * un aliment, pas un emplacement en magasin. On les ramène à la poignée de
 * rayons dans lesquels on marche réellement, pour que la liste de courses suive
 * le trajet plutôt que l'ordre alphabétique.
 *
 * Classement par mots-clés, volontairement grossier : se tromper de rayon fait
 * perdre dix secondes, alors qu'une taxonomie fine serait ingérable à la main.
 * Module pur — voir `npm run check:rayons`.
 */

export interface Rayon {
  id: string;
  label: string;
  /** Ordre de parcours d'un magasin type : le frais en fin de course. */
  ordre: number;
}

export const RAYONS: Record<string, Rayon> = {
  legumes: { id: 'legumes', label: 'Fruits et légumes', ordre: 1 },
  boulangerie: { id: 'boulangerie', label: 'Boulangerie', ordre: 2 },
  epicerie_salee: { id: 'epicerie_salee', label: 'Épicerie salée', ordre: 3 },
  epicerie_sucree: { id: 'epicerie_sucree', label: 'Épicerie sucrée', ordre: 4 },
  boissons: { id: 'boissons', label: 'Boissons', ordre: 5 },
  entretien: { id: 'entretien', label: 'Hygiène et entretien', ordre: 6 },
  boucherie: { id: 'boucherie', label: 'Boucherie et poissonnerie', ordre: 7 },
  cremerie: { id: 'cremerie', label: 'Crèmerie', ordre: 8 },
  surgeles: { id: 'surgeles', label: 'Surgelés', ordre: 9 },
  autre: { id: 'autre', label: 'Autre', ordre: 10 },
};

/* Testé dans l'ordre : le premier rayon dont un mot-clé apparaît gagne, donc
   l'ordre encode la priorité. Les pièges viennent des produits composés, où un
   mot d'ingrédient l'emporterait à tort sur la nature du produit : un « Poulet
   Satay et son Riz » n'est pas de la boucherie, un « biscuit apéritif » n'est
   pas de l'épicerie sucrée. Les règles les plus spécifiques passent devant. */
const REGLES: { rayon: string; motsCles: string[] }[] = [
  {
    rayon: 'surgeles',
    motsCles: ['surgel', 'congel', 'glace', 'sorbet'],
  },
  {
    // Un plat préparé se range par sa nature, pas par son ingrédient principal.
    rayon: 'epicerie_salee',
    motsCles: ['plat prepare', 'plat préparé', 'plats prepares', 'plats préparés', 'conserve'],
  },
  {
    // L'apéritif est salé, même quand il s'appelle « biscuit ».
    rayon: 'epicerie_salee',
    motsCles: ['aperitif', 'apéritif', 'apero', 'apéro', 'chips', 'biscuit sale', 'biscuit salé'],
  },
  {
    rayon: 'boissons',
    motsCles: [
      'boisson', 'jus', 'soda', 'eau ', 'eaux', 'limonade', 'sirop', 'biere',
      'bière', 'vin', 'cidre', 'the glace', 'cafe soluble', 'infusion',
    ],
  },
  {
    rayon: 'boucherie',
    motsCles: [
      'viande', 'boucherie', 'poisson', 'volaille', 'poulet', 'boeuf', 'bœuf',
      'porc', 'agneau', 'jambon', 'charcuterie', 'saucisse', 'steak', 'saumon',
      'thon frais', 'crevette',
    ],
  },
  {
    rayon: 'cremerie',
    motsCles: [
      'yaourt', 'yogourt', 'fromage', 'lait fermente', 'produits laitiers',
      'creme fraiche', 'crème fraîche', 'beurre', 'oeuf', 'œuf', 'skyr',
      'fromage blanc', 'petit-suisse', 'dessert lacte',
    ],
  },
  {
    rayon: 'entretien',
    motsCles: [
      'hygiene', 'hygiène', 'entretien', 'lessive', 'savon', 'shampoing',
      'dentifrice', 'papier toilette', 'essuie-tout', 'nettoyant', 'menager',
      'vaisselle', 'liquide vaisselle', 'eponge', 'éponge', 'javel',
      'ménager', 'couche',
    ],
  },
  {
    rayon: 'epicerie_sucree',
    motsCles: [
      'sucre', 'sucré', 'biscuit', 'chocolat', 'confiture', 'miel', 'cereale',
      'céréale', 'gateau', 'gâteau', 'bonbon', 'confiserie', 'tartiner',
      'dessert', 'compote', 'petit dejeuner', 'petit-déjeuner', 'viennoiserie',
      'pate a tartiner', 'goute', 'goûter',
    ],
  },
  {
    rayon: 'boulangerie',
    motsCles: ['pain', 'baguette', 'brioche', 'boulanger'],
  },
  {
    rayon: 'epicerie_salee',
    motsCles: [
      'pate', 'pâte', 'riz', 'conserve', 'huile', 'vinaigre', 'sauce', 'epice',
      'épice', 'sel', 'farine', 'legumineuse', 'légumineuse', 'lentille',
      'haricot', 'pois', 'semoule', 'soupe', 'plat prepare', 'plat préparé',
      'apéritif', 'aperitif', 'chips', 'moutarde', 'bouillon', 'graine',
      'sesame', 'sésame',
    ],
  },
  {
    rayon: 'legumes',
    motsCles: [
      'legume', 'fruit', 'salade', 'tomate', 'pomme', 'carotte', 'oignon',
      'banane', 'courgette', 'poireau', 'ail', 'herbes fraiches', 'champignon',
      'citron', 'orange', 'poire', 'fraise', 'raisin', 'avocat', 'concombre',
    ],
  },
];

/** Enlève les accents pour que « pâtes » et « pates » se comportent pareil. */
function normaliser(texte: string): string {
  return texte
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');
}

/**
 * Devine le rayon d'un produit.
 *
 * `kindEmplacement` sert de dernier recours : un produit rangé au congélateur
 * s'achète au rayon surgelés même si ses catégories ne le disent pas.
 */
export function rayonDe(
  nom: string,
  categories: string | null | undefined,
  kindEmplacement?: string | null,
): Rayon {
  // L'emplacement congélateur prime sur les mots-clés : ce qui vit au
  // congélateur se rachète au rayon surgelés, quel que soit l'aliment.
  if (kindEmplacement === 'freezer') return RAYONS.surgeles!;

  const foin = normaliser(`${categories ?? ''} ${nom}`);

  for (const regle of REGLES) {
    if (regle.motsCles.some((mot) => foin.includes(normaliser(mot)))) {
      return RAYONS[regle.rayon]!;
    }
  }

  // Le frigo est un repli plus faible : il contient aussi de la viande et des
  // légumes, donc les mots-clés doivent passer avant lui.
  if (kindEmplacement === 'fridge') return RAYONS.cremerie!;
  return RAYONS.autre!;
}

/** Regroupe et ordonne selon le trajet en magasin. */
export function grouperParRayon<T>(
  items: T[],
  classer: (item: T) => Rayon,
): { rayon: Rayon; items: T[] }[] {
  const groupes = new Map<string, { rayon: Rayon; items: T[] }>();
  for (const item of items) {
    const rayon = classer(item);
    const groupe = groupes.get(rayon.id) ?? { rayon, items: [] };
    groupe.items.push(item);
    groupes.set(rayon.id, groupe);
  }
  return [...groupes.values()].sort((a, b) => a.rayon.ordre - b.rayon.ordre);
}
