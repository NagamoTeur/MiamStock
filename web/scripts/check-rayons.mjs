import { rayonDe, grouperParRayon, RAYONS } from '../.tmp-rayons.mjs';

let echecs = 0;
const verifier = (libelle, obtenu, attendu) => {
  const ok = JSON.stringify(obtenu) === JSON.stringify(attendu);
  if (!ok) echecs += 1;
  console.log(`  ${ok ? '✓' : '✗'} ${libelle}${ok ? '' : `  attendu ${JSON.stringify(attendu)}, obtenu ${JSON.stringify(obtenu)}`}`);
};

console.log('Classement par rayon, sur de vraies catégories Open Food Facts :');
verifier('Nutella → épicerie sucrée',
  rayonDe('Nutella', 'Produits à tartiner sucrés, Pâtes à tartiner').id, 'epicerie_sucree');
verifier('Skyr → crèmerie',
  rayonDe('Skyr', 'Produits laitiers, Yaourts').id, 'cremerie');
verifier('Sésame Gerblé → épicerie salée',
  rayonDe('Sésame', 'Biscuits apéritifs, graines').id, 'epicerie_salee');
verifier('Poulet Satay et son Riz → épicerie salée',
  rayonDe('Poulet Satay et son Riz', 'Plats préparés').id, 'epicerie_salee');

console.log('\nLe repli par emplacement :');
verifier('produit sans catégorie au congélateur → surgelés',
  rayonDe('Steaks hachés maison', null, 'freezer').id, 'surgeles');
verifier('produit sans catégorie au frigo → crèmerie',
  rayonDe('Truc', null, 'fridge').id, 'cremerie');
verifier('produit sans rien → autre',
  rayonDe('Truc', null, null).id, 'autre');

console.log('\nLes accents ne changent rien :');
verifier('« pâtes » et « pates » tombent au même rayon',
  rayonDe('Pates', null).id, rayonDe('Pâtes', null).id);
verifier('« épice » reconnu sans accent',
  rayonDe('Epices', null).id, 'epicerie_salee');

console.log('\nLa spécificité l’emporte sur la généralité :');
verifier('surgelé avant tout le reste',
  rayonDe('Pizza surgelée', 'Pizzas, Plats préparés').id, 'surgeles');
verifier('boisson avant épicerie',
  rayonDe('Jus de pomme', 'Boissons, Jus de fruits').id, 'boissons');

console.log('\nArticles saisis à la main, sans catégorie (le nom est tout) :');
verifier('Pommes → fruits et légumes', rayonDe('Pommes', null).id, 'legumes');
verifier('Pain de mie → boulangerie', rayonDe('Pain de mie', null).id, 'boulangerie');
verifier('Liquide vaisselle → entretien', rayonDe('Liquide vaisselle', null).id, 'entretien');
verifier("Jus d'orange → boissons", rayonDe("Jus d'orange", null).id, 'boissons');
verifier('Pâtes penne → épicerie salée', rayonDe('Pâtes penne', null).id, 'epicerie_salee');

console.log('\nLe transformé l’emporte sur son ingrédient :');
verifier('compote de pommes → épicerie sucrée',
  rayonDe('Compote de pommes', 'Desserts, Compotes').id, 'epicerie_sucree');
verifier('sauce tomate → épicerie salée',
  rayonDe('Sauce tomate', 'Sauces').id, 'epicerie_salee');
verifier('jus de pomme → boissons',
  rayonDe('Jus de pomme', null).id, 'boissons');
verifier('tarte aux pommes surgelée → surgelés',
  rayonDe('Tarte aux pommes', 'Desserts surgelés').id, 'surgeles');

console.log('\nRegroupement et ordre de parcours :');
const items = [
  { n: 'Skyr', c: 'Yaourts' },
  { n: 'Pâtes', c: 'Pâtes alimentaires' },
  { n: 'Jus', c: 'Boissons' },
];
const groupes = grouperParRayon(items, (i) => rayonDe(i.n, i.c));
verifier('ordonné selon le trajet en magasin',
  groupes.map((g) => g.rayon.id), ['epicerie_salee', 'boissons', 'cremerie']);
verifier('aucun produit perdu au passage',
  groupes.reduce((n, g) => n + g.items.length, 0), items.length);
verifier('chaque rayon a un ordre distinct',
  new Set(Object.values(RAYONS).map((r) => r.ordre)).size, Object.keys(RAYONS).length);

console.log(echecs === 0 ? '\nTout est vert.' : `\n${echecs} échec(s).`);
process.exit(echecs === 0 ? 0 : 1);
