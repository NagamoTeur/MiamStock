/* L'échelle de temps de la frise — non linéaire, et c'est tout l'intérêt.
 *
 * Une frise à échelle constante sur trois mois écrase les sept prochains jours
 * dans les premiers pour-cent de la largeur : exactement là où se prennent les
 * décisions. On donne donc la moitié de l'écran à la semaine qui vient, et on
 * comprime le reste progressivement.
 *
 * Le module est pur (aucune dépendance au DOM ni à Svelte) pour rester
 * vérifiable : voir `npm run check:timescale`.
 */

export interface Segment {
  /** Bornes en jours depuis aujourd'hui. */
  fromDay: number;
  toDay: number;
  /** Bornes en pourcentage de la largeur de la piste. */
  fromPct: number;
  toPct: number;
}

/** La semaine qui vient prend la moitié de la piste ; six mois tiennent dans le reste. */
export const SEGMENTS: readonly Segment[] = [
  { fromDay: 0, toDay: 7, fromPct: 0, toPct: 50 },
  { fromDay: 7, toDay: 42, fromPct: 50, toPct: 77 },
  { fromDay: 42, toDay: 180, fromPct: 77, toPct: 94 },
  { fromDay: 180, toDay: 730, fromPct: 94, toPct: 100 },
];

export const HORIZON_DAYS = 730;

/** Jours depuis aujourd'hui → position en % sur la piste. Borné à [0, 100]. */
export function dayToPercent(day: number): number {
  if (day <= 0) return 0;
  if (day >= HORIZON_DAYS) return 100;
  for (const segment of SEGMENTS) {
    if (day <= segment.toDay) {
      const ratio = (day - segment.fromDay) / (segment.toDay - segment.fromDay);
      return segment.fromPct + ratio * (segment.toPct - segment.fromPct);
    }
  }
  return 100;
}

/** Inverse de `dayToPercent` : indispensable pour savoir où l'on vient de lâcher une puce. */
export function percentToDay(pct: number): number {
  const clamped = Math.min(100, Math.max(0, pct));
  for (const segment of SEGMENTS) {
    if (clamped <= segment.toPct) {
      const ratio = (clamped - segment.fromPct) / (segment.toPct - segment.fromPct);
      return Math.round(segment.fromDay + ratio * (segment.toDay - segment.fromDay));
    }
  }
  return HORIZON_DAYS;
}

export interface Tick {
  day: number;
  label: string;
  /** Les repères majeurs portent un libellé plus appuyé et une ligne plus visible. */
  major: boolean;
}

const JOURS = ['dim.', 'lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.'];

/** Les repères de l'axe : denses sur la semaine, de plus en plus espacés ensuite. */
export function ticks(today: Date = new Date()): Tick[] {
  const out: Tick[] = [{ day: 0, label: "auj.", major: true }];

  for (let day = 1; day <= 7; day += 1) {
    const date = new Date(today);
    date.setDate(date.getDate() + day);
    out.push({
      day,
      label: day === 1 ? 'demain' : JOURS[date.getDay()]!,
      major: day === 7,
    });
  }

  for (const week of [2, 3, 4, 5, 6]) {
    out.push({ day: week * 7, label: `${week} sem.`, major: week === 6 });
  }

  for (const month of [3, 6]) {
    out.push({ day: Math.round(month * 30.4), label: `${month} mois`, major: month === 6 });
  }

  out.push({ day: 365, label: '1 an', major: true });
  return out;
}

/**
 * Empile les puces d'un couloir sur plusieurs rangs pour qu'aucune n'en recouvre
 * une autre. Glouton et stable : les puces sont traitées de gauche à droite et
 * prennent le premier rang libre, ce qui garde l'ordre visuel prévisible d'un
 * rendu à l'autre.
 */
export function packRows<T extends { x: number }>(
  items: T[],
  itemWidth: number,
  gap = 6,
): { item: T; row: number }[] {
  const rowEnds: number[] = [];
  const placed: { item: T; row: number }[] = [];

  for (const item of [...items].sort((a, b) => a.x - b.x)) {
    let row = rowEnds.findIndex((end) => item.x >= end + gap);
    if (row === -1) {
      row = rowEnds.length;
      rowEnds.push(0);
    }
    rowEnds[row] = item.x + itemWidth;
    placed.push({ item, row });
  }

  return placed;
}
