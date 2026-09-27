/** Helpers de dates : tout est manipulé en ISO local (YYYY-MM-DD), jamais en UTC.
 *
 * Une DLC est une date de calendrier, pas un instant : passer par UTC ferait
 * basculer la date d'un jour selon le fuseau, et un yaourt afficherait « demain »
 * au lieu d'« aujourd'hui ».
 */

export function toIso(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function todayIso(): string {
  return toIso(new Date());
}

export function addDaysIso(days: number, from: string = todayIso()): string {
  const [year, month, day] = from.split('-').map(Number);
  const date = new Date(year ?? 1970, (month ?? 1) - 1, day ?? 1);
  date.setDate(date.getDate() + days);
  return toIso(date);
}

export function daysUntil(iso: string): number {
  const [year, month, day] = iso.split('-').map(Number);
  const target = new Date(year ?? 1970, (month ?? 1) - 1, day ?? 1);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

const FORMAT = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short' });

/** « périmé depuis 2 j », « aujourd'hui », « dans 5 j · 3 oct. » */
export function describeExpiry(iso: string | null): string {
  if (!iso) return 'sans date';
  const days = daysUntil(iso);
  const [year, month, day] = iso.split('-').map(Number);
  const pretty = FORMAT.format(new Date(year ?? 1970, (month ?? 1) - 1, day ?? 1));
  if (days < -1) return `périmé depuis ${-days} j`;
  if (days === -1) return 'périmé depuis hier';
  if (days === 0) return "aujourd'hui";
  if (days === 1) return `demain · ${pretty}`;
  if (days <= 30) return `dans ${days} j · ${pretty}`;
  return pretty;
}

export const SHELF_PRESETS = [
  { label: '+3 j', days: 3 },
  { label: '+1 sem.', days: 7 },
  { label: '+2 sem.', days: 14 },
  { label: '+1 mois', days: 30 },
  { label: '+6 mois', days: 182 },
  { label: '+1 an', days: 365 },
];
