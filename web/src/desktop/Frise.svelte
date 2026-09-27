<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import type { IconName } from '../lib/icons';
  import { addDaysIso, daysUntil } from '../lib/dates';
  import { desk, type FlatLot } from '../lib/desktop.svelte';
  import { app } from '../lib/state.svelte';
  import { dayToPercent, packRows, percentToDay, ticks } from '../lib/timescale';
  import LotChip from './LotChip.svelte';

  const CHIP_W = 158;
  const ROW_H = 36;

  interface Lane {
    id: number | null;
    name: string;
    kind: string;
    icon: IconName;
  }

  const ICON_BY_KIND: Record<string, IconName> = {
    fridge: 'fridge',
    freezer: 'freezer',
    pantry: 'pantry',
    other: 'crate',
  };

  const lanes = $derived.by<Lane[]>(() => {
    const fromLocations = app.locations.map((location) => ({
      id: location.id,
      name: location.name,
      kind: location.kind,
      icon: ICON_BY_KIND[location.kind] ?? 'crate',
    }));
    // Le couloir « non rangé » n'apparaît que s'il a quelque chose à montrer :
    // un couloir vide permanent ferait croire à un emplacement réel.
    const orphans = desk.lots.some((lot) => lot.location_id == null);
    return orphans
      ? [...fromLocations, { id: null, name: 'Non rangé', kind: 'other', icon: 'crate' as IconName }]
      : fromLocations;
  });

  const dated = $derived(desk.lots.filter((lot) => lot.expires_on));
  const undated = $derived(desk.lots.filter((lot) => !lot.expires_on));

  const axisTicks = ticks();

  /* À l'extrémité comprimée de l'axe, « 3 mois », « 6 mois » et « 1 an » tombaient
     à quelques pixels les uns des autres et se mélangeaient en bouillie. On place
     d'abord les repères majeurs, puis on ne glisse les mineurs que là où il reste
     la place de les lire. */
  const MIN_GAP = 54;

  const visibleTicks = $derived.by(() => {
    if (trackWidth <= 0) return axisTicks;
    const px = (tick: { day: number }) => (dayToPercent(tick.day) / 100) * trackWidth;

    const kept: typeof axisTicks = [];
    const fits = (tick: { day: number }) =>
      kept.every((other) => Math.abs(px(other) - px(tick)) >= MIN_GAP);

    for (const tick of axisTicks) {
      if (tick.day === 0 || (tick.major && fits(tick))) kept.push(tick);
    }
    for (const tick of axisTicks) {
      if (!tick.major && tick.day !== 0 && fits(tick)) kept.push(tick);
    }
    return kept.sort((a, b) => a.day - b.day);
  });

  let trackWidth = $state(0);
  let lanesEl: HTMLDivElement | null = $state(null);
  const laneEls: Record<string, HTMLElement> = {};

  function lotsOf(laneId: number | null, expired: boolean) {
    return dated.filter(
      (lot) =>
        lot.location_id === laneId && daysUntil(lot.expires_on!) < 0 === expired,
    );
  }

  /** Puces futures d'un couloir, positionnées puis empilées pour ne pas se recouvrir. */
  function placed(laneId: number | null) {
    const items = lotsOf(laneId, false).map((lot) => {
      const raw = (dayToPercent(daysUntil(lot.expires_on!)) / 100) * trackWidth;
      return { lot, x: Math.min(Math.max(0, raw), Math.max(0, trackWidth - CHIP_W)) };
    });
    return packRows(items, CHIP_W).map(({ item, row }) => ({
      lot: item.lot,
      x: item.x,
      y: row * ROW_H,
    }));
  }

  function laneHeight(laneId: number | null): number {
    const rows = placed(laneId).reduce((max, p) => Math.max(max, p.y / ROW_H + 1), 1);
    return Math.max(74, rows * ROW_H + 18);
  }

  // --- Glisser-déposer : le geste signature de cette surface ------------------

  interface Drag {
    lot: FlatLot;
    pointerX: number;
    pointerY: number;
    moved: boolean;
    trackLeft: number;
    trackWidth: number;
    hoverLane: number | null | undefined;
    overUndated: boolean;
  }

  let drag = $state<Drag | null>(null);

  const dropDate = $derived(drag && !drag.overUndated ? dropDateFor(drag) : null);

  function startDrag(event: PointerEvent, lot: FlatLot) {
    if (event.button !== 0) return;
    const track = lanesEl?.querySelector<HTMLElement>('.lane-track');
    if (!track) return;
    const rect = track.getBoundingClientRect();

    drag = {
      lot,
      pointerX: event.clientX,
      pointerY: event.clientY,
      moved: false,
      trackLeft: rect.left,
      trackWidth: rect.width,
      hoverLane: lot.location_id,
      overUndated: false,
    };
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  }

  function moveDrag(event: PointerEvent) {
    if (!drag) return;
    const dx = Math.abs(event.clientX - drag.pointerX);
    const dy = Math.abs(event.clientY - drag.pointerY);
    drag.pointerX = event.clientX;
    drag.pointerY = event.clientY;
    if (dx > 3 || dy > 3) drag.moved = true;

    const undatedBand = document.querySelector<HTMLElement>('.undated');
    const bandRect = undatedBand?.getBoundingClientRect();
    drag.overUndated = Boolean(
      bandRect && event.clientY >= bandRect.top && event.clientY <= bandRect.bottom,
    );

    if (!drag.overUndated) {
      for (const [key, element] of Object.entries(laneEls)) {
        const rect = element.getBoundingClientRect();
        if (event.clientY >= rect.top && event.clientY <= rect.bottom) {
          drag.hoverLane = key === 'null' ? null : Number(key);
          break;
        }
      }
    }
  }

  async function endDrag() {
    const current = drag;
    drag = null;
    if (!current) return;

    // Un clic sans déplacement reste un clic : il sélectionne, il ne déplace pas.
    if (!current.moved) return;

    const changes: { expires_on?: string | null; location_id?: number | null } = {};
    if (current.overUndated) {
      if (current.lot.expires_on) changes.expires_on = null;
    } else {
      const target = dropDateFor(current);
      if (target && target !== current.lot.expires_on) changes.expires_on = target;
      if (current.hoverLane !== undefined && current.hoverLane !== current.lot.location_id) {
        changes.location_id = current.hoverLane;
      }
    }
    if (Object.keys(changes).length === 0) return;

    await desk.moveLot(current.lot.id, changes);

    const where = app.locationName(changes.location_id ?? current.lot.location_id);
    if ('expires_on' in changes && changes.expires_on === null) {
      app.toast(`${current.lot.name} · date retirée`);
    } else if ('location_id' in changes) {
      app.toast(`${current.lot.name} → ${where ?? 'non rangé'}`);
    } else {
      app.toast(`${current.lot.name} · DLC au ${changes.expires_on}`);
    }
  }

  function dropDateFor(current: Drag): string | null {
    if (current.trackWidth <= 0) return null;
    const pct = ((current.pointerX - current.trackLeft) / current.trackWidth) * 100;
    return addDaysIso(percentToDay(pct));
  }

  /* Un glisser commencé par erreur doit pouvoir être abandonné : sans ça, la
     seule issue est de relâcher quelque part, donc de valider un déplacement
     qu'on ne voulait pas. */
  function cancelDrag(event: KeyboardEvent) {
    if (event.key === 'Escape' && drag) {
      event.preventDefault();
      drag = null;
    }
  }

  function select(event: MouseEvent, lot: FlatLot) {
    desk.toggle(lot.id, event.shiftKey || event.metaKey || event.ctrlKey);
    void desk.focusProduct(lot.barcode);
  }
</script>

<svelte:window
  onpointermove={moveDrag}
  onpointerup={endDrag}
  onpointercancel={endDrag}
  onkeydown={cancelDrag}
/>

<div class="frise">
  <!-- Axe du temps -->
  <div class="frise-grid frise-axis">
    <div class="axis-head">Emplacement</div>
    <div class="axis-head expired">Périmé</div>
    <div class="axis-track" bind:clientWidth={trackWidth}>
      {#each visibleTicks as tick (tick.day)}
        <div
          class="axis-tick"
          class:major={tick.major}
          class:today={tick.day === 0}
          style="left:{dayToPercent(tick.day)}%"
        >
          {tick.label}
        </div>
      {/each}
    </div>
  </div>

  <!-- Couloirs -->
  <div class="frise-lanes" bind:this={lanesEl}>
    <div class="today-rule"><span>aujourd'hui</span></div>

    {#each lanes as lane (lane.id ?? 'null')}
      {@const expired = lotsOf(lane.id, true)}
      {@const chips = placed(lane.id)}
      <div
        class="frise-grid lane"
        class:drop-target={drag?.moved && !drag.overUndated && drag.hoverLane === lane.id}
        style="min-height:{laneHeight(lane.id)}px"
        bind:this={laneEls[String(lane.id)]}
      >
        <div class="lane-label">
          <Icon name={lane.icon} size={16} />
          <span>{lane.name}</span>
          <span class="count">{expired.length + chips.length}</span>
        </div>

        <div class="lane-expired">
          {#each expired as lot (lot.id)}
            <LotChip
              {lot}
              placed={false}
              selected={desk.isSelected(lot.id)}
              dragging={drag?.lot.id === lot.id}
              onpointerdown={(event) => startDrag(event, lot)}
              onclick={(event) => select(event, lot)}
            />
          {/each}
        </div>

        <div class="lane-track">
          {#each chips as chip (chip.lot.id)}
            <LotChip
              lot={chip.lot}
              x={chip.x}
              y={chip.y}
              selected={desk.isSelected(chip.lot.id)}
              dragging={drag?.lot.id === chip.lot.id}
              onpointerdown={(event) => startDrag(event, chip.lot)}
              onclick={(event) => select(event, chip.lot)}
            />
          {/each}
        </div>
      </div>
    {/each}

    <!--
      Le champ continue sous le dernier couloir. Sans cette prolongation, les
      filets de colonnes s'arrêtaient net tandis que le trait d'aujourd'hui
      courait seul sur un demi-écran vide : lu comme un rendu interrompu.
    -->
    {#if lanes.length > 0}
      <div class="frise-grid lane-filler" aria-hidden="true">
        <div class="lane-label"></div>
        <div class="lane-expired"></div>
        <div class="lane-track"></div>
      </div>
    {/if}

    {#if lanes.length === 0}
      <div class="empty">
        <Icon name="crate" size={44} />
        <p>Aucun emplacement. Le stock arrive par le téléphone, au scan.</p>
      </div>
    {/if}
  </div>

  <!-- Les sans-date : hors de l'axe, parce qu'elles n'y ont pas leur place -->
  <div class="undated" class:empty-band={undated.length === 0}>
    <h2>Sans date · {undated.length}</h2>
    {#if undated.length > 0}
      <p>
        Conserves, épices, sec. Rien à placer sur une frise — fais-en glisser une vers un
        couloir pour lui donner une date, ou ramène une puce ici pour la lui retirer.
      </p>
    {/if}
    <div class="undated-chips">
      {#each undated as lot (lot.id)}
        <LotChip
          {lot}
          placed={false}
          selected={desk.isSelected(lot.id)}
          dragging={drag?.lot.id === lot.id}
          onpointerdown={(event) => startDrag(event, lot)}
          onclick={(event) => select(event, lot)}
        />
      {/each}
      {#if undated.length === 0}
        <span class="faint">Tout ce que tu as en stock porte une date.</span>
      {/if}
    </div>
  </div>
</div>

<!-- Aperçu qui suit le pointeur : on voit où la puce va atterrir, et à quelle date -->
{#if drag?.moved}
  <div
    class="drag-ghost"
    style="left:{drag.pointerX}px; top:{drag.pointerY}px"
    aria-hidden="true"
  >
    <span class="dot bg-{drag.lot.status}"></span>
    <span>{drag.lot.quantity} × {drag.lot.name}</span>
    <strong>
      {#if drag.overUndated}sans date{:else if dropDate}{dropDate}{/if}
    </strong>
  </div>
{/if}

<style>
  .drag-ghost {
    position: fixed;
    z-index: 90;
    transform: translate(12px, -50%);
    display: flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.35rem 0.6rem;
    border-radius: 10px;
    background: var(--bg-elevated);
    border: 1px solid var(--accent);
    box-shadow: 0 6px 18px rgb(0 0 0 / 0.45);
    font-size: 0.8rem;
    pointer-events: none;
    white-space: nowrap;
  }

  .drag-ghost strong {
    color: var(--accent);
    font-variant-numeric: tabular-nums;
  }

  .empty {
    display: grid;
    justify-items: center;
    gap: 0.5rem;
    padding: 3rem 1rem;
    color: var(--text-dim);
  }
</style>
