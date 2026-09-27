import { dayToPercent, percentToDay, ticks, packRows, SEGMENTS } from '../.tmp-timescale.mjs';

let failures = 0;
const check = (label, actual, expected) => {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  if (!ok) failures += 1;
  console.log(`  ${ok ? '✓' : '✗'} ${label}${ok ? '' : `  attendu ${JSON.stringify(expected)}, obtenu ${JSON.stringify(actual)}`}`);
};

console.log("Échelle de temps :");
check("aujourd'hui est à 0 %", dayToPercent(0), 0);
check('une date passée est plaquée à 0 %', dayToPercent(-30), 0);
check('7 jours prennent la moitié de la piste', dayToPercent(7), 50);
check('6 semaines occupent 77 %', dayToPercent(42), 77);
check('6 mois occupent 94 %', dayToPercent(180), 94);
check('au-delà de l’horizon, plaqué à 100 %', dayToPercent(5000), 100);

const croissant = [0, 1, 3, 7, 20, 42, 100, 180, 400].every(
  (d, i, all) => i === 0 || dayToPercent(d) > dayToPercent(all[i - 1]),
);
check('la position croît strictement avec la date', croissant, true);

const j3 = dayToPercent(3) - dayToPercent(2);
const j30 = dayToPercent(30) - dayToPercent(29);
check('un jour proche est plus large qu’un jour lointain', j3 > j30 * 3, true);

console.log('\nAller-retour (pour le glisser-déposer) :');
for (const day of [0, 1, 4, 7, 21, 42, 120, 180, 400]) {
  check(`J+${day}`, percentToDay(dayToPercent(day)), day);
}

console.log('\nRepères de l’axe :');
const t = ticks(new Date(2026, 8, 27));
check('le premier repère est aujourd’hui', t[0].label, "auj.");
check('le deuxième est demain', t[1].label, 'demain');
check('tous les repères tiennent dans la piste', t.every((x) => dayToPercent(x.day) <= 100), true);
check('aucun repère en double', new Set(t.map((x) => x.day)).size, t.length);

console.log('\nEmpilement des puces :');
check('deux puces éloignées tiennent sur un rang',
  packRows([{ x: 0 }, { x: 400 }], 160).map((p) => p.row), [0, 0]);
check('deux puces qui se chevauchent sont empilées',
  packRows([{ x: 0 }, { x: 50 }], 160).map((p) => p.row), [0, 1]);
check('la troisième redescend au rang libre',
  packRows([{ x: 0 }, { x: 50 }, { x: 200 }], 160).map((p) => p.row), [0, 1, 0]);
check('les segments sont contigus',
  SEGMENTS.every((s, i) => i === 0 || s.fromPct === SEGMENTS[i - 1].toPct), true);

console.log(failures === 0 ? '\nTout est vert.' : `\n${failures} échec(s).`);
process.exit(failures === 0 ? 0 : 1);
