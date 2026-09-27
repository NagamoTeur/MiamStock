<script lang="ts">
  import { app } from '../lib/state.svelte';
  import ProductRow from './ProductRow.svelte';

  let query = $state(app.stockQuery);
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

  <div class="chips">
    <button class="chip" class:on={app.stockFilter === null} onclick={() => filterBy(null)}>
      Tout
    </button>
    {#each app.locations as location (location.id)}
      <button
        class="chip"
        class:on={app.stockFilter === location.id}
        onclick={() => filterBy(location.id)}
      >
        {location.name}
      </button>
    {/each}
  </div>

  {#if app.stock.length === 0}
    <div class="empty">
      <span class="big" aria-hidden="true">📦</span>
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
