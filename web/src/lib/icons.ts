/* Jeu d'icônes dessiné pour MiamStock.
 *
 * Une seule grille (24 × 24), une seule graisse de trait, des extrémités et
 * jonctions arrondies partout. Des emoji auraient été plus rapides, mais ils
 * n'ont ni grille, ni graisse, ni style communs : posés côte à côte dans une
 * barre d'onglets, ils se lisent comme cinq dessins empruntés à cinq endroits.
 *
 * Chaque entrée est une liste de `d` d'éléments <path>. Les formes qui doivent
 * rester des cercles sont décrites en arcs pour garder un seul type de nœud.
 */

export type IconName = keyof typeof ICONS;

export const ICONS = {
  // --- Navigation ---------------------------------------------------------
  scan: [
    'M3 8V5.5A2.5 2.5 0 0 1 5.5 3H8',
    'M16 3h2.5A2.5 2.5 0 0 1 21 5.5V8',
    'M21 16v2.5a2.5 2.5 0 0 1-2.5 2.5H16',
    'M8 21H5.5A2.5 2.5 0 0 1 3 18.5V16',
    'M7.5 8v8',
    'M11 8v8',
    'M14 8v8',
    'M17 8v8',
  ],
  crate: ['M12 3.5 20.5 7.5v9L12 20.5 3.5 16.5v-9z', 'M3.5 7.5 12 11.5l8.5-4', 'M12 11.5v9'],
  clock: [
    'M12 3.5a8.5 8.5 0 1 1 0 17 8.5 8.5 0 0 1 0-17z',
    'M12 7.5V12l3 1.8',
  ],
  basket: [
    'M4.5 9h15l-1.4 9.2A2.2 2.2 0 0 1 15.9 20H8.1a2.2 2.2 0 0 1-2.2-1.8z',
    'M9 9l2.2-5',
    'M15 9l-2.2-5',
    'M9.8 12.8v3.4',
    'M14.2 12.8v3.4',
  ],
  sliders: [
    'M3.5 8h8',
    'M16.5 8h4',
    'M3.5 16h4',
    'M12.5 16h8',
    'M14 5.8a2.2 2.2 0 1 1 0 4.4 2.2 2.2 0 0 1 0-4.4z',
    'M10 13.8a2.2 2.2 0 1 1 0 4.4 2.2 2.2 0 0 1 0-4.4z',
  ],

  // Fourchette et couteau : le journal alimentaire.
  utensils: [
    'M5.5 3v4.1a2.5 2.5 0 0 0 5 0V3',
    'M8 3v3.6',
    'M8 9.6V21',
    'M17.2 3c-1.8 1.3-2.9 3.6-2.9 6.3V13h2.9',
    'M17.2 3v18',
  ],
  chevronLeft: ['M14.8 5.8 8.6 12l6.2 6.2'],

  // --- Emplacements -------------------------------------------------------
  fridge: ['M6 3h12v18H6z', 'M6 10h12', 'M9 6.2v2.2', 'M9 12.4v2.4'],
  freezer: [
    'M12 3.2v17.6',
    'M4.8 7.4 19.2 16.6',
    'M19.2 7.4 4.8 16.6',
    'M9.6 4.6 12 6.6l2.4-2',
    'M9.6 19.4 12 17.4l2.4 2',
  ],
  pantry: ['M4.5 3.5h15v17h-15z', 'M12 3.5v17', 'M9.4 11v2.2', 'M14.6 11v2.2'],
  jar: [
    'M7.5 8.5h9V19a2 2 0 0 1-2 2h-5a2 2 0 0 1-2-2z',
    'M8.6 8.5V5.8a2 2 0 0 1 2-2h2.8a2 2 0 0 1 2 2v2.7',
    'M7.5 12.6h9',
  ],

  // --- Actions ------------------------------------------------------------
  plus: ['M12 5.5v13', 'M5.5 12h13'],
  minus: ['M5.5 12h13'],
  check: ['M4.8 12.6 9.6 17.4 19.2 6.8'],
  close: ['M6.2 6.2 17.8 17.8', 'M17.8 6.2 6.2 17.8'],
  search: ['M10.8 4.2a6.6 6.6 0 1 1 0 13.2 6.6 6.6 0 0 1 0-13.2z', 'M15.6 15.6 20.5 20.5'],
  refresh: ['M20.3 12a8.3 8.3 0 1 1-2.6-6.1', 'M20.5 4.4v5.3h-5.3'],
  undo: ['M4.5 9.2h10.8a4.9 4.9 0 0 1 0 9.8H9.4', 'M8.3 5.4 4.5 9.2l3.8 3.8'],
  trash: [
    'M4.5 6.8h15',
    'M9.6 3.5h4.8v3.3H9.6z',
    'M6.8 6.8 7.8 20a1.2 1.2 0 0 0 1.2 1.1h6a1.2 1.2 0 0 0 1.2-1.1l1-13.2',
    'M10.4 10.6v6.2',
    'M13.6 10.6v6.2',
  ],
  pencil: ['M4 20.2h4.3L20.2 8.3a2.6 2.6 0 0 0-3.7-3.7L4.6 16.5z', 'M14.9 6.2l3.7 3.7'],
  keyboard: [
    'M3.2 6.4h17.6v11.2H3.2z',
    'M7 10.1h.01',
    'M11 10.1h.01',
    'M15 10.1h.01',
    'M8.4 13.9h7.2',
  ],
  list: [
    'M9 6.5h11.5',
    'M9 12h11.5',
    'M9 17.5h11.5',
    'M4.2 6.5h.01',
    'M4.2 12h.01',
    'M4.2 17.5h.01',
  ],
  chevronDown: ['M5.8 9.2 12 15.4l6.2-6.2'],
  chevronRight: ['M9.2 5.8 15.4 12l-6.2 6.2'],
  alert: ['M12 4.2 21 19.5H3z', 'M12 10v4', 'M12 16.8h.01'],
  offline: [
    'M3.5 3.5 20.5 20.5',
    'M5.2 9.6a11 11 0 0 1 3.4-2.1',
    'M15.4 7.6a11 11 0 0 1 3.4 2',
    'M8.4 13a6.6 6.6 0 0 1 2-1.2',
    'M13.8 11.9a6.6 6.6 0 0 1 1.8 1.1',
    'M12 18.2h.01',
  ],
} as const;
