<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import { app } from '../lib/state.svelte';
  import ExpiringView from './ExpiringView.svelte';
  import ProductRow from './ProductRow.svelte';

  let query = $state(app.stockQuery);
  let aConsommer = $state(false);
  let timer: ReturnType<typeof setTimeout> | null = null;

  function search(value: string) {
    query = value;
    // Anti-rebond : on ne veut pas une requête par frappe sur un clavier mobile.
    if (timer) clearTimeout(timer);
    timer = setTimeout(async () => {
      app.stockQuery = value.trim();
      await app.refreshStock();
    }, 280);
  }

  async function filterBy(id: number | null) {
    app.stockFilter = id;
    await app.refreshStock();
  }
</script>

<div class="stack">
  <input
    type="search"
    placeholder="Chercher un produit, une marque…"
    value={query}
    oninput={(event) => search(event.currentTarget.value)}
  />

  <div class="chips scroll">
    <button
      class="chip"
      class:on={aConsommer}
      onclick={() => (aConsommer = !aConsommer)}
    >
      À consommer{#if app.alertCount} · {app.alertCount}{/if}
    </button>
    <button
      class="chip"
      class:on={!aConsommer && app.stockFilter === null}
      onclick={() => { aConsommer = false; void filterBy(null); }}
    >
      Tout
    </button>
    {#each app.locations as location (location.id)}
      <button
        class="chip"
        class:on={!aConsommer && app.stockFilter === location.id}
        onclick={() => { aConsommer = false; void filterBy(location.id); }}
      >
        {location.name}
      </button>
    {/each}
  </div>

  {#if aConsommer}
    <ExpiringView />
  {:else if app.stock.length === 0}
    <div class="empty">
      <Icon name="crate" size={44} />
      {#if app.stockQuery || app.stockFilter !== null}
        Rien ne correspond à ce filtre.
      {:else}
        Ton stock est vide. Va scanner un premier produit.
      {/if}
    </div>
  {:else}
    {#each app.stock as line (line.product.barcode)}
      <ProductRow {line} />
    {/each}
  {/if}
</div>
