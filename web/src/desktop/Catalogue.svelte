<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import { api } from '../lib/api';
  import { describeExpiry } from '../lib/dates';
  import { desk } from '../lib/desktop.svelte';
  import { app } from '../lib/state.svelte';

  let query = $state('');
  let filter = $state<'all' | 'in' | 'out'>('all');
  let timer: ReturnType<typeof setTimeout> | null = null;

  function search(value: string) {
    query = value;
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => desk.loadCatalog(value.trim() || undefined), 250);
  }

  const rows = $derived(
    desk.catalog.filter((entry) => {
      if (filter === 'in') return entry.in_stock > 0;
      if (filter === 'out') return entry.in_stock === 0;
      return true;
    }),
  );

  async function saveField(barcode: string, field: string, value: string | number | null) {
    const updated = await app.guard(() => api.patchProduct(barcode, { [field]: value }));
    if (updated) {
      await Promise.all([desk.loadCatalog(query.trim() || undefined), app.refreshStock()]);
    }
  }
</script>

<div class="registre">
  <div class="toolbar">
    <div class="row grow" style="gap:.5rem">
      <Icon name="search" size={16} />
      <input
        class="bare grow"
        type="search"
        placeholder="Chercher dans le catalogue…"
        value={query}
        oninput={(event) => search(event.currentTarget.value)}
      />
    </div>
    <div class="chips">
      <button class="chip" class:on={filter === 'all'} onclick={() => (filter = 'all')}>Tout</button>
      <button class="chip" class:on={filter === 'in'} onclick={() => (filter = 'in')}>En stock</button>
      <button class="chip" class:on={filter === 'out'} onclick={() => (filter = 'out')}>Épuisé</button>
    </div>
    <span class="faint">{rows.length} référence{rows.length > 1 ? 's' : ''}</span>
  </div>

  <div class="table-wrap">
    <table class="grid">
      <thead>
        <tr>
          <th style="width:46px"></th>
          <th>Produit</th>
          <th>Marque</th>
          <th class="num">Stock</th>
          <th class="num">Lots</th>
          <th>Prochaine DLC</th>
          <th class="num">Seuil</th>
          <th>Emplacement par défaut</th>
          <th class="num">Conservation</th>
        </tr>
      </thead>
      <tbody>
        {#each rows as entry (entry.product.barcode)}
          <tr
            class:selected={desk.focusedBarcode === entry.product.barcode}
            onclick={() => desk.focusProduct(entry.product.barcode)}
          >
            <td>
              {#if entry.product.image_url}
                <img class="mini" src={entry.product.image_url} alt="" loading="lazy" />
              {:else}
                <span class="mini placeholder"><Icon name="jar" size={15} /></span>
              {/if}
            </td>
            <td class="truncate" style="max-width:26ch">
              {entry.product.name}
              {#if entry.on_shopping_list}
                <span class="tag"><Icon name="basket" size={11} /> à acheter</span>
              {/if}
            </td>
            <td class="faint truncate" style="max-width:16ch">{entry.product.brand ?? '—'}</td>
            <td class="num" class:faint={entry.in_stock === 0}>{entry.in_stock}</td>
            <td class="num faint">{entry.lot_count}</td>
            <td class="faint">{entry.next_expiry ? describeExpiry(entry.next_expiry) : '—'}</td>
            <td class="num">
              <input
                class="inline-input num"
                type="number"
                min="0"
                max="99"
                value={entry.product.min_quantity}
                style="width:4rem; text-align:right"
                onclick={(event) => event.stopPropagation()}
                onchange={(event) =>
                  saveField(entry.product.barcode, 'min_quantity', Number(event.currentTarget.value))}
              />
            </td>
            <td>
              <select
                class="inline-input"
                value={entry.product.default_location_id ?? ''}
                style="width:9rem"
                onclick={(event) => event.stopPropagation()}
                onchange={(event) =>
                  saveField(
                    entry.product.barcode,
                    'default_location_id',
                    event.currentTarget.value ? Number(event.currentTarget.value) : null,
                  )}
              >
                <option value="">Aucun</option>
                {#each app.locations as location (location.id)}
                  <option value={location.id}>{location.name}</option>
                {/each}
              </select>
            </td>
            <td class="num">
              <input
                class="inline-input num"
                type="number"
                min="0"
                max="3650"
                placeholder="—"
                value={entry.product.default_shelf_life_days ?? ''}
                style="width:5rem; text-align:right"
                onclick={(event) => event.stopPropagation()}
                onchange={(event) =>
                  saveField(
                    entry.product.barcode,
                    'default_shelf_life_days',
                    event.currentTarget.value ? Number(event.currentTarget.value) : null,
                  )}
              />
            </td>
          </tr>
        {/each}
      </tbody>
    </table>

    {#if rows.length === 0}
      <div class="empty">
        <Icon name="jar" size={40} />
        <p>
          {query
            ? 'Aucune référence ne correspond.'
            : "Le catalogue se remplit tout seul au premier scan d'un produit."}
        </p>
      </div>
    {/if}
  </div>
</div>

<style>
  .registre {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    height: 100%;
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    padding: 0.6rem 0.9rem;
    border-bottom: 1px solid var(--border);
    color: var(--text-dim);
  }

  input.bare {
    background: transparent;
    border: none;
    padding: 0.35rem 0;
    font-size: 0.9rem;
  }

  input.bare:focus-visible {
    outline: none;
  }

  .mini {
    width: 30px;
    height: 30px;
    border-radius: 7px;
    object-fit: cover;
    background: var(--bg-input);
    display: grid;
    place-items: center;
    color: var(--text-faint);
  }

  .tag {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    margin-left: 0.4rem;
    padding: 0.05rem 0.35rem;
    border-radius: 999px;
    background: var(--accent-soft);
    color: var(--accent);
    font-size: 0.68rem;
    vertical-align: 1px;
  }

  .empty {
    display: grid;
    justify-items: center;
    gap: 0.5rem;
    padding: 3rem 1rem;
    color: var(--text-dim);
  }
</style>
