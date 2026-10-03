import type { Meal } from './types';

export const REPAS: { id: Meal; label: string }[] = [
  { id: 'petit_dejeuner', label: 'Petit-déjeuner' },
  { id: 'dejeuner', label: 'Déjeuner' },
  { id: 'collation', label: 'Collation' },
  { id: 'diner', label: 'Dîner' },
];

/** Le repas probable selon l'heure : un choix de moins à faire, la plupart du temps. */
export function repasDuMoment(maintenant = new Date()): Meal {
  const h = maintenant.getHours() + maintenant.getMinutes() / 60;
  if (h < 10.5) return 'petit_dejeuner';
  if (h < 15) return 'dejeuner';
  if (h < 18) return 'collation';
  return 'diner';
}

/** Entier lisible, avec l'espace fine française pour les milliers : 1 240. */
export function entier(valeur: number): string {
  return Math.round(valeur).toLocaleString('fr-FR');
}
