<script lang="ts">
  import { api } from '../lib/api';
  import { SHELF_PRESETS, addDaysIso, describeExpiry } from '../lib/dates';
  import { app } from '../lib/state.svelte';
  import type { Lookup } from '../lib/types';

  interface Props {
    lookup: Lookup;
    /** Mode proposé d'emblée : « out » quand l'utilisateur scanne pour consommer. */
    initialMode?: 'in' | 'out';
    onclose: () => void;
  }

  let { lookup, initialMode = 'in', onclose }: Props = $props();

  // Un produit absent du stock ne peut pas être sorti : on force l'entrée.
  // La feuille est recréée à chaque scan : capturer la valeur initiale est voulu.
  // svelte-ignore state_referenced_locally
  let mode = $state<'in' | 'out'>(lookup.in_stock > 0 ? initialMode : 'in');
  let quantity = $state(1);
  let expiresOn = $state<string>('');
  let locationId = $state<number | null>(null);
  let manualName = $state('');
  let addToShopping = $state(true);
  let busy = $state(false);

  const product = $derived(lookup.product);
  const needsName = $derived(!lookup.found);

  // Pré-remplissage : les choix mémorisés du produit d'abord, sinon le dernier
  // emplacement utilisé — devant le frigo, chaque menu évité compte.
  $effect(() => {
    locationId =
      lookup.suggested_location_id ?? product?.default_location_id ?? app.lastLocationId ?? null;
    const shelf = lookup.suggested_shelf_life_days ?? product?.default_shelf_life_days;
    expiresOn = shelf != null ? addDaysIso(shelf) : '';
  });

  const nextOutLot = $derived.by(() => {
    const line = app.stock.find((entry) => entry.product.barcode === lookup.barcode);
    return line?.lots[0] ?? null;
  });

  async function submit() {
    if (busy) return;
    busy = true;

    if (mode === 'in') {
      const created = await app.guard(() =>
        api.stockIn({
          barcode: lookup.barcode,
          quantity,
          expires_on: expiresOn || null,
          location_id: locationId,
          name: needsName ? manualName.trim() : null,
        }),
      );
      if (created) {
        app.rememberLocation(locationId);
        const where = app.locationName(locationId);
        app.toast(
          `+${quantity} ${created.product.name}${where ? ` · ${where}` : ''}`,
          'ok',
        );
        await app.refreshStock();
        onclose();
      }
    } else {
      const result = await app.guard(() =>
        api.stockOut({ barcode: lookup.barcode, quantity, add_to_shopping: addToShopping }),
      );
      if (result) {
        const suffix = result.added_to_shopping ? ' · ajouté aux courses' : '';
        app.toast(`−${result.consumed} ${result.name}${suffix}`, 'ok');
        await Promise.all([app.refreshStock(), app.refreshShopping()]);
        onclose();
      }
    }

    busy = false;
  }

  const canSubmit = $derived(!busy && (!needsName || manualName.trim().length > 1));
</script>

<div
  class="backdrop"
  role="button"
  tabindex="-1"
  onclick={(event) => event.target === event.currentTarget && onclose()}
  onkeydown={(event) => event.key === 'Escape' && onclose()}
>
  <div class="sheet" role="dialog" aria-modal="true" aria-label="Enregistrer le scan">
    <div class="row" style="margin-bottom:.9rem">
      {#if product?.image_url}
        <img class="thumb" src={product.image_url} alt="" />
      {:else}
        <div class="thumb placeholder" aria-hidden="true">🥫</div>
      {/if}
      <div class="grow">
        <h2 class="truncate">{product?.name ?? 'Produit inconnu'}</h2>
        <div class="muted truncate">
          {[product?.brand, product?.net_quantity].filter(Boolean).join(' · ') || lookup.barcode}
        </div>
      </div>
      <button class="btn ghost" onclick={onclose} aria-label="Fermer">✕</button>
    </div>

    {#if needsName}
      <div class="banner warn">
        Ce code-barres est inconnu d'Open Food Facts. Donne-lui un nom, il sera enregistré
        dans ton catalogue.
      </div>
      <input
        placeholder="Nom du produit"
        bind:value={manualName}
        autocomplete="off"
        style="margin-bottom:.8rem"
      />
    {/if}

    {#if lookup.in_stock > 0}
      <div class="seg" style="margin-bottom:.9rem">
        <button class:on={mode === 'in'} onclick={() => (mode = 'in')}>
          Entrée (+)
        </button>
        <button class:on={mode === 'out'} onclick={() => (mode = 'out')}>
          Sortie (−)
        </button>
      </div>
      <p class="muted" style="margin:-.4rem 0 .8rem">
        {lookup.in_stock} en stock
        {#if nextOutLot}
          · prochain à sortir : {describeExpiry(nextOutLot.expires_on)}
        {/if}
      </p>
    {/if}

    <div class="row" style="justify-content:space-between; margin-bottom:.9rem">
      <span class="muted">Quantité</span>
      <div class="stepper">
        <button onclick={() => (quantity = Math.max(1, quantity - 1))} aria-label="Moins un">
          −
        </button>
        <span class="value">{quantity}</span>
        <button onclick={() => (quantity = Math.min(99, quantity + 1))} aria-label="Plus un">
          +
        </button>
      </div>
    </div>

    {#if mode === 'in'}
      <div class="stack" style="margin-bottom:.9rem">
        <span class="muted">Date limite</span>
        <div class="chips">
          <button
            class="chip"
            class:on={expiresOn === ''}
            onclick={() => (expiresOn = '')}
          >
            Sans date
          </button>
          {#each SHELF_PRESETS as preset (preset.days)}
            <button
              class="chip"
              class:on={expiresOn === addDaysIso(preset.days)}
              onclick={() => (expiresOn = addDaysIso(preset.days))}
            >
              {preset.label}
            </button>
          {/each}
        </div>
        <input type="date" min={addDaysIso(-3650)} bind:value={expiresOn} />
        {#if expiresOn}
          <span class="faint">{describeExpiry(expiresOn)}</span>
        {/if}
      </div>

      {#if app.locations.length}
        <div class="stack" style="margin-bottom:1rem">
          <span class="muted">Emplacement</span>
          <div class="chips">
            {#each app.locations as location (location.id)}
              <button
                class="chip"
                class:on={locationId === location.id}
                onclick={() => (locationId = location.id)}
              >
                {location.name}
              </button>
            {/each}
            <button class="chip" class:on={locationId === null} onclick={() => (locationId = null)}>
              Non rangé
            </button>
          </div>
        </div>
      {/if}
    {:else}
      <label class="row" style="margin-bottom:1rem; gap:.6rem">
        <button
          class="tick"
          class:on={addToShopping}
          onclick={() => (addToShopping = !addToShopping)}
          aria-pressed={addToShopping}
          type="button"
        >
          {addToShopping ? '✓' : ''}
        </button>
        <span class="muted grow">Ajouter aux courses si le stock tombe sous le seuil</span>
      </label>
    {/if}

    <button class="btn primary block lg" disabled={!canSubmit} onclick={submit}>
      {#if busy}
        Enregistrement…
      {:else if mode === 'in'}
        Rentrer {quantity} en stock
      {:else}
        Sortir {quantity} du stock
      {/if}
    </button>

    <p class="faint" style="text-align:center; margin:.7rem 0 0">
      {lookup.barcode}{expiresOn && mode === 'in' ? ` · DLC ${expiresOn}` : ''}
    </p>
  </div>
</div>
