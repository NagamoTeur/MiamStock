import type { Food, Lookup } from './types';

/** Un code-barres résolu, sous la forme d'un aliment de la recherche.

    Un produit déjà connu du foyer garde la source `catalogue` (c'est ce qui
    permet de cocher « j'ai fini le paquet ») ; un produit trouvé seulement sur
    Open Food Facts reste `off`. Sans fiche nulle part, il n'y a rien à
    proposer : l'appelant renvoie vers la recherche par nom. */
export function alimentDepuisCode(lookup: Lookup): Food | null {
  const p = lookup.product;
  if (!lookup.found || !p) return null;
  return {
    source: lookup.known_locally ? 'catalogue' : 'off',
    ref: lookup.barcode,
    name: p.name,
    brand: p.brand,
    kcal_100g: p.kcal_100g,
    prot_100g: p.prot_100g,
    gluc_100g: p.gluc_100g,
    lip_100g: p.lip_100g,
    portion_g: p.portion_g,
    group: null,
    in_stock: lookup.in_stock,
    image_url: p.image_url,
  };
}
