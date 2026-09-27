<script lang="ts">
  import { app } from '../lib/state.svelte';
  import ProductRow from './ProductRow.svelte';

  const groups = $derived.by(() => ({
    expired: app.expiring.filter((line) => line.worst_status === 'expired'),
    urgent: app.expiring.filter((line) => line.worst_status === 'urgent'),
    soon: app.expiring.filter((line) => line.worst_status === 'soon'),
  }));
</script>

<div class="stack">
  {#if app.expiring.length === 0}
    <div class="empty">
      <span class="big" aria-hidden="true">✅</span>
      Rien ne presse. Aucune date limite dans les {app.summary?.soon_days ?? 7} prochains jours.
    </div>
  {:else}
    {#if groups.expired.length}
      <h2 class="muted status-expired" style="margin:.2rem 0 -.2rem; font-size:.9rem">
        Périmé · {groups.expired.length}
      </h2>
      {#each groups.expired as line (line.product.barcode)}
        <ProductRow {line} expanded />
      {/each}
    {/if}

    {#if groups.urgent.length}
      <h2 class="muted status-urgent" style="margin:.6rem 0 -.2rem; font-size:.9rem">
        À consommer sous {app.summary?.urgent_days ?? 3} jours · {groups.urgent.length}
      </h2>
      {#each groups.urgent as line (line.product.barcode)}
        <ProductRow {line} expanded />
      {/each}
    {/if}

    {#if groups.soon.length}
      <h2 class="muted status-soon" style="margin:.6rem 0 -.2rem; font-size:.9rem">
        Cette semaine · {groups.soon.length}
      </h2>
      {#each groups.soon as line (line.product.barcode)}
        <ProductRow {line} />
      {/each}
    {/if}
  {/if}
</div>
