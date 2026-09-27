<script lang="ts">
  import { describeExpiry } from '../lib/dates';
  import type { FlatLot } from '../lib/desktop.svelte';

  interface Props {
    lot: FlatLot;
    selected?: boolean;
    dragging?: boolean;
    /** Positionnée sur la piste du temps, ou posée dans un flux normal. */
    placed?: boolean;
    x?: number;
    y?: number;
    onpointerdown?: (event: PointerEvent) => void;
    onclick?: (event: MouseEvent) => void;
  }

  let {
    lot,
    selected = false,
    dragging = false,
    placed = true,
    x = 0,
    y = 0,
    onpointerdown,
    onclick,
  }: Props = $props();

  const title = $derived(
    `${lot.quantity} × ${lot.name}${lot.brand ? ` · ${lot.brand}` : ''} — ${describeExpiry(lot.expires_on)}`,
  );
</script>

<button
  class="chip-lot"
  class:selected
  class:dragging
  class:static={!placed}
  style={placed ? `left:${x}px; top:${y}px` : undefined}
  {title}
  aria-pressed={selected}
  onpointerdown={onpointerdown}
  onclick={onclick}
>
  <span class="dot bg-{lot.status}" aria-hidden="true"></span>
  <span class="n">{lot.quantity}</span>
  <span class="nm">{lot.name}</span>
</button>
