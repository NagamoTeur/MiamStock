<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import ProductFields from '../lib/ProductFields.svelte';
  import { api } from '../lib/api';
  import { app } from '../lib/state.svelte';
  import type { HistoryEntry, Product } from '../lib/types';

  interface Props {
    product: Product;
    onclose: () => void;
  }

  let { product, onclose }: Props = $props();
  let history = $state<HistoryEntry[]>([]);

  $effect(() => {
    const barcode = product.barcode;
    void (async () => {
      const rows = await app.guard(() => api.history({ barcode, limit: 25 }));
      if (rows) history = rows;
    })();
  });

  const LABEL: Record<string, string> = {
    in: 'Entré',
    out: 'Sorti',
    discard: 'Jeté',
    adjust: 'Corrigé',
    shopping_auto: 'Mis aux courses',
    shopping_clear: 'Courses vidées',
  };

  function when(iso: string): string {
    return new Intl.DateTimeFormat('fr-FR', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso));
  }
</script>

<div
  class="backdrop"
  role="button"
  tabindex="-1"
  onclick={(event) => event.target === event.currentTarget && onclose()}
  onkeydown={(event) => event.key === 'Escape' && onclose()}
>
  <div class="sheet" role="dialog" aria-modal="true" aria-label="Fiche produit">
    <div class="row" style="margin-bottom:1rem">
      {#if product.image_url}
        <img class="thumb" src={product.image_url} alt="" />
      {:else}
        <div class="thumb placeholder"><Icon name="jar" size={22} /></div>
      {/if}
      <div class="grow">
        <h2 class="truncate">{product.name}</h2>
        <div class="faint">{product.barcode}</div>
      </div>
      <button class="btn ghost icon-btn" onclick={onclose} aria-label="Fermer">
        <Icon name="close" />
      </button>
    </div>

    <ProductFields {product} onsaved={() => app.refreshStock()} />

    <h3 class="section-head">Historique</h3>
    {#if history.length === 0}
      <p class="faint" style="margin:0">Aucun mouvement enregistré.</p>
    {:else}
      {#each history as event (event.id)}
        <div class="checkline">
          <span class="grow">
            {LABEL[event.kind] ?? event.kind}
            {#if event.quantity}<span class="qty"> × {event.quantity}</span>{/if}
          </span>
          <span class="faint">{when(event.at)}</span>
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .section-head {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-dim);
    margin: 1.6rem 0 0.5rem;
  }
</style>
