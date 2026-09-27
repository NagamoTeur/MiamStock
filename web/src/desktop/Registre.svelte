<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import { describeExpiry } from '../lib/dates';
  import { desk, type FlatLot } from '../lib/desktop.svelte';
  import { app } from '../lib/state.svelte';

  type Column = 'name' | 'brand' | 'quantity' | 'expires_on' | 'location' | 'status';

  let sort = $state<{ by: Column; desc: boolean }>({ by: 'expires_on', desc: false });
  let query = $state('');
  let locationFilter = $state<number | null | 'all'>('all');

  const STATUS_RANK: Record<string, number> = {
    expired: 4, urgent: 3, soon: 2, ok: 1, none: 0,
  };

  const rows = $derived.by(() => {
    const needle = query.trim().toLowerCase();
    const filtered = desk.lots.filter((lot) => {
      if (locationFilter !== 'all' && lot.location_id !== locationFilter) return false;
      if (!needle) return true;
      return (
        lot.name.toLowerCase().includes(needle) ||
        (lot.brand ?? '').toLowerCase().includes(needle) ||
        lot.barcode.includes(needle)
      );
    });

    const direction = sort.desc ? -1 : 1;
    return [...filtered].sort((a, b) => {
      switch (sort.by) {
        case 'quantity':
          return (a.quantity - b.quantity) * direction;
        case 'status':
          return ((STATUS_RANK[a.status] ?? 0) - (STATUS_RANK[b.status] ?? 0)) * direction;
        case 'expires_on': {
          // Les lots sans date vont toujours à la fin, quel que soit le sens du tri :
          // « pas de date » n'est ni plus tôt ni plus tard, c'est autre chose.
          if (!a.expires_on && !b.expires_on) return 0;
          if (!a.expires_on) return 1;
          if (!b.expires_on) return -1;
          return a.expires_on.localeCompare(b.expires_on) * direction;
        }
        case 'location':
          return (a.location_name ?? '').localeCompare(b.location_name ?? '') * direction;
        case 'brand':
          return (a.brand ?? '').localeCompare(b.brand ?? '') * direction;
        default:
          return a.name.localeCompare(b.name) * direction;
      }
    });
  });

  function toggleSort(column: Column) {
    sort = sort.by === column ? { by: column, desc: !sort.desc } : { by: column, desc: false };
  }

  function rowClick(event: MouseEvent, lot: FlatLot) {
    desk.toggle(lot.id, event.shiftKey || event.metaKey || event.ctrlKey);
    void desk.focusProduct(lot.barcode);
  }

  const allSelected = $derived(rows.length > 0 && rows.every((lot) => desk.isSelected(lot.id)));

  const COLUMNS: { key: Column; label: string; numeric?: boolean }[] = [
    { key: 'status', label: '' },
    { key: 'name', label: 'Produit' },
    { key: 'brand', label: 'Marque' },
    { key: 'quantity', label: 'Qté', numeric: true },
    { key: 'expires_on', label: 'Date limite' },
    { key: 'location', label: 'Emplacement' },
  ];
</script>

<div class="registre">
  <div class="toolbar">
    <div class="row grow" style="gap:.5rem">
      <Icon name="search" size={16} />
      <input
        class="bare grow"
        type="search"
        placeholder="Filtrer par produit, marque ou code-barres…"
        bind:value={query}
      />
    </div>
    <div class="chips">
      <button class="chip" class:on={locationFilter === 'all'} onclick={() => (locationFilter = 'all')}>
        Tout
      </button>
      {#each app.locations as location (location.id)}
        <button
          class="chip"
          class:on={locationFilter === location.id}
          onclick={() => (locationFilter = location.id)}
        >
          {location.name}
        </button>
      {/each}
    </div>
    <span class="faint">{rows.length} lot{rows.length > 1 ? 's' : ''}</span>
  </div>

  <div class="table-wrap">
    <table class="grid">
      <thead>
        <tr>
          <th style="width:34px">
            <button
              class="tick"
              class:on={allSelected}
              aria-label={allSelected ? 'Tout désélectionner' : 'Tout sélectionner'}
              onclick={() => (allSelected ? desk.clearSelection() : desk.selectOnly(rows.map((r) => r.id)))}
            >
              {#if allSelected}<Icon name="check" size={14} />{/if}
            </button>
          </th>
          {#each COLUMNS as column (column.key)}
            <th
              class="sortable"
              class:num={column.numeric}
              style={column.key === 'status' ? 'width:24px' : undefined}
              onclick={() => toggleSort(column.key)}
            >
              {column.label}
              {#if sort.by === column.key}
                <span class="dir">{sort.desc ? '↓' : '↑'}</span>
              {/if}
            </th>
          {/each}
          <th style="width:44px"></th>
        </tr>
      </thead>
      <tbody>
        {#each rows as lot (lot.id)}
          <tr class:selected={desk.isSelected(lot.id)} onclick={(event) => rowClick(event, lot)}>
            <td>
              <button
                class="tick"
                class:on={desk.isSelected(lot.id)}
                aria-label="Sélectionner ce lot"
                onclick={(event) => {
                  event.stopPropagation();
                  desk.toggle(lot.id, true);
                }}
              >
                {#if desk.isSelected(lot.id)}<Icon name="check" size={14} />{/if}
              </button>
            </td>
            <td><span class="dot bg-{lot.status}" aria-hidden="true"></span></td>
            <td class="truncate" style="max-width:24ch">{lot.name}</td>
            <td class="faint truncate" style="max-width:16ch">{lot.brand ?? '—'}</td>
            <td class="num">
              <input
                class="inline-input num"
                type="number"
                min="0"
                max="999"
                value={lot.quantity}
                style="width:4.5rem; text-align:right"
                onclick={(event) => event.stopPropagation()}
                onchange={(event) => desk.setLotQuantity(lot.id, Number(event.currentTarget.value))}
              />
            </td>
            <td>
              <input
                class="inline-input"
                type="date"
                value={lot.expires_on ?? ''}
                style="width:9.5rem"
                onclick={(event) => event.stopPropagation()}
                onchange={(event) =>
                  desk.moveLot(lot.id, { expires_on: event.currentTarget.value || null })}
              />
              <span class="faint status-{lot.status}"> {describeExpiry(lot.expires_on)}</span>
            </td>
            <td>
              <select
                class="inline-input"
                value={lot.location_id ?? ''}
                style="width:9rem"
                onclick={(event) => event.stopPropagation()}
                onchange={(event) =>
                  desk.moveLot(lot.id, {
                    location_id: event.currentTarget.value ? Number(event.currentTarget.value) : null,
                  })}
              >
                <option value="">Non rangé</option>
                {#each app.locations as location (location.id)}
                  <option value={location.id}>{location.name}</option>
                {/each}
              </select>
            </td>
            <td>
              <button
                class="btn ghost danger icon-btn"
                style="width:32px; min-height:30px"
                aria-label="Jeter ce lot"
                onclick={async (event) => {
                  event.stopPropagation();
                  desk.selectOnly([lot.id]);
                  await desk.bulk('discard');
                }}
              >
                <Icon name="trash" size={15} />
              </button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>

    {#if rows.length === 0}
      <div class="empty">
        <Icon name="search" size={40} />
        <p>Aucun lot ne correspond à ce filtre.</p>
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

  .empty {
    display: grid;
    justify-items: center;
    gap: 0.5rem;
    padding: 3rem 1rem;
    color: var(--text-dim);
  }
</style>
