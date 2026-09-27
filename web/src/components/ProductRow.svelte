<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import ProductSheet from './ProductSheet.svelte';
  import { api } from '../lib/api';
  import { describeExpiry } from '../lib/dates';
  import { app } from '../lib/state.svelte';
  import type { StockLine } from '../lib/types';

  interface Props {
    line: StockLine;
    /** Ouvre les lots d'emblée : utile dans l'onglet « À consommer ». */
    expanded?: boolean;
  }

  let { line, expanded = false }: Props = $props();
  // État d'ouverture initial seulement : replier une ligne doit rester possible.
  // svelte-ignore state_referenced_locally
  let open = $state(expanded);
  let busy = $state(false);
  let sheetOpen = $state(false);

  async function consumeOne() {
    if (busy) return;
    busy = true;
    const result = await app.guard(() =>
      api.stockOut({ barcode: line.product.barcode, quantity: 1, add_to_shopping: true }),
    );
    if (result) {
      app.toast(
        `−1 ${result.name}${result.added_to_shopping ? ' · ajouté aux courses' : ''}`,
      );
      await Promise.all([app.refreshStock(), app.refreshShopping()]);
    }
    busy = false;
  }

  async function discardLot(lotId: number) {
    if (busy) return;
    busy = true;
    const done = await app.guard(() => api.deleteLot(lotId));
    if (done !== null) {
      app.toast('Lot jeté');
      await Promise.all([app.refreshStock(), app.refreshShopping()]);
    }
    busy = false;
  }

  async function changeLotQuantity(lotId: number, quantity: number) {
    if (busy) return;
    busy = true;
    const updated = await app.guard(() => api.patchLot(lotId, { quantity }));
    if (updated) await app.refreshStock();
    busy = false;
  }

  async function changeLotDate(lotId: number, value: string) {
    busy = true;
    const updated = await app.guard(() =>
      api.patchLot(lotId, value ? { expires_on: value } : { clear_expiry: true }),
    );
    if (updated) await app.refreshStock();
    busy = false;
  }
</script>

<div class="card">
  <div class="row">
    {#if line.product.image_url}
      <img class="thumb" src={line.product.image_url} alt="" loading="lazy" />
    {:else}
      <div class="thumb placeholder"><Icon name="jar" size={22} /></div>
    {/if}

    <button class="grow" style="text-align:left" onclick={() => (open = !open)}>
      <div class="row" style="gap:.4rem">
        <span class="dot bg-{line.worst_status}" aria-hidden="true"></span>
        <span class="truncate" style="font-weight:550">{line.product.name}</span>
      </div>
      <div class="faint truncate">
        {[line.product.brand, line.product.net_quantity].filter(Boolean).join(' · ') ||
          line.product.barcode}
      </div>
      <div class="muted status-{line.worst_status} row" style="gap:.3rem">
        <span class="caret" class:open aria-hidden="true">
          <Icon name="chevronRight" size={13} />
        </span>
        {line.lots.length > 1
          ? `${line.lots.length} lots · au plus tôt ${describeExpiry(line.next_expiry)}`
          : describeExpiry(line.next_expiry)}
      </div>
    </button>

    <span class="qty">{line.total}</span>
    <button class="btn" onclick={consumeOne} disabled={busy} aria-label="Consommer un exemplaire">
      −1
    </button>
  </div>

  {#if open}
    <div style="margin-top:.7rem">
      {#each line.lots as lot (lot.id)}
        <div class="lot">
          <span class="dot bg-{lot.status}" aria-hidden="true"></span>
          <div class="grow">
            <input
              type="date"
              value={lot.expires_on ?? ''}
              onchange={(event) => changeLotDate(lot.id, event.currentTarget.value)}
              style="padding:.35rem .5rem; font-size:.85rem"
            />
            <div class="faint">
              {lot.location_name ?? 'non rangé'} · {describeExpiry(lot.expires_on)}
            </div>
          </div>
          <div class="stepper">
            <button
              onclick={() => changeLotQuantity(lot.id, lot.quantity - 1)}
              disabled={busy}
              aria-label="Retirer un du lot"
              style="width:34px; height:34px"
            >
              <Icon name="minus" size={16} />
            </button>
            <span class="value" style="font-size:1rem">{lot.quantity}</span>
            <button
              onclick={() => changeLotQuantity(lot.id, lot.quantity + 1)}
              disabled={busy}
              aria-label="Ajouter un au lot"
              style="width:34px; height:34px"
            >
              <Icon name="plus" size={16} />
            </button>
          </div>
          <button
            class="btn ghost danger"
            style="min-height:34px; padding:0 .55rem"
            onclick={() => discardLot(lot.id)}
            disabled={busy}
            aria-label="Jeter ce lot"
          >
            <Icon name="trash" size={17} />
          </button>
        </div>
      {/each}

      <button class="btn block" style="margin-top:.7rem" onclick={() => (sheetOpen = true)}>
        <Icon name="pencil" size={16} />
        Fiche produit
      </button>
    </div>
  {/if}
</div>

{#if sheetOpen}
  <ProductSheet product={line.product} onclose={() => (sheetOpen = false)} />
{/if}

<style>
  /* Sans ce chevron, rien n'annonçait que la ligne s'ouvre — et la fiche
     produit, qui n'est atteignable que par là, restait introuvable. */
  .caret {
    display: inline-flex;
    transition: transform 0.15s ease;
    color: var(--text-faint);
  }

  .caret.open {
    transform: rotate(90deg);
  }
</style>
