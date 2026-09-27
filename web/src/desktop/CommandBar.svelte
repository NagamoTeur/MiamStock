<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import { api } from '../lib/api';
  import { SHELF_PRESETS, addDaysIso, describeExpiry } from '../lib/dates';
  import { desk } from '../lib/desktop.svelte';
  import { app } from '../lib/state.svelte';
  import type { Lookup } from '../lib/types';

  interface Props {
    onclose: () => void;
  }

  let { onclose }: Props = $props();

  let field = $state('');
  let input: HTMLInputElement | null = $state(null);
  let pending = $state<Lookup | null>(null);
  let busy = $state(false);

  let quantity = $state(1);
  let expiresOn = $state('');
  let locationId = $state<number | null>(null);
  let manualName = $state('');

  /** Ce qui vient d'être rentré pendant cette session : la preuve que ça marche. */
  let entered = $state<{ name: string; quantity: number; at: number }[]>([]);

  const matches = $derived.by(() => {
    const needle = field.trim().toLowerCase();
    if (needle.length < 2 || /^\d+$/.test(needle)) return [];
    return desk.catalog
      .filter(
        (entry) =>
          entry.product.name.toLowerCase().includes(needle) ||
          (entry.product.brand ?? '').toLowerCase().includes(needle),
      )
      .slice(0, 6);
  });

  $effect(() => {
    input?.focus();
  });

  // Le catalogue alimente la recherche par nom : on le charge si ce n'est pas fait.
  $effect(() => {
    if (desk.catalog.length === 0) void desk.loadCatalog();
  });

  async function resolve(barcode: string) {
    busy = true;
    const lookup = await app.guard(() => api.lookup(barcode));
    busy = false;
    if (!lookup) return;

    pending = lookup;
    manualName = '';
    quantity = 1;
    locationId =
      lookup.suggested_location_id ?? lookup.product?.default_location_id ?? app.lastLocationId ?? null;
    const shelf = lookup.suggested_shelf_life_days ?? lookup.product?.default_shelf_life_days;
    expiresOn = shelf != null ? addDaysIso(shelf) : '';
  }

  async function submitField(event: Event) {
    event.preventDefault();
    const code = field.replace(/\D/g, '');
    if (code.length >= 8) {
      field = '';
      await resolve(code);
      return;
    }
    if (matches.length === 1) {
      field = '';
      await resolve(matches[0]!.product.barcode);
    }
  }

  async function confirm() {
    if (!pending || busy) return;
    busy = true;
    const created = await app.guard(() =>
      api.stockIn({
        barcode: pending!.barcode,
        quantity,
        expires_on: expiresOn || null,
        location_id: locationId,
        name: pending!.found ? null : manualName.trim(),
      }),
    );
    busy = false;
    if (!created) return;

    app.rememberLocation(locationId);
    entered = [{ name: created.product.name, quantity, at: Date.now() }, ...entered].slice(0, 8);
    pending = null;
    field = '';
    await app.refreshStock();
    // On rend la main au champ : le geste suivant est un autre code-barres.
    queueMicrotask(() => input?.focus());
  }

  function onkeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      if (pending) pending = null;
      else onclose();
    }
    if (event.key === 'Enter' && pending && !event.shiftKey) {
      event.preventDefault();
      void confirm();
    }
  }

  const canConfirm = $derived(
    Boolean(pending) && (pending!.found || manualName.trim().length > 1) && !busy,
  );
</script>

<svelte:window onkeydown={onkeydown} />

<div
  class="cmd-backdrop"
  role="button"
  tabindex="-1"
  onclick={(event) => event.target === event.currentTarget && onclose()}
  onkeydown={() => {}}
>
  <div class="cmd" role="dialog" aria-modal="true" aria-label="Saisie rapide">
    {#if !pending}
      <form onsubmit={submitField}>
        <div class="row" style="padding-left:1.1rem; gap:.6rem">
          <Icon name="keyboard" size={18} />
          <input
            bind:this={input}
            bind:value={field}
            class="grow"
            placeholder="Code-barres, ou nom d'un produit déjà connu…"
            autocomplete="off"
            inputmode="text"
          />
          {#if busy}<span class="faint" style="padding-right:1rem">…</span>{/if}
        </div>
      </form>

      {#if matches.length > 0}
        <div class="matches">
          {#each matches as entry (entry.product.barcode)}
            <button class="match" onclick={() => resolve(entry.product.barcode)}>
              <span class="grow truncate">{entry.product.name}</span>
              <span class="faint">{entry.in_stock} en stock</span>
            </button>
          {/each}
        </div>
      {/if}

      {#if entered.length > 0}
        <div class="session">
          <h3>Rentré à l'instant</h3>
          {#each entered as item (item.at)}
            <div class="checkline">
              <Icon name="check" size={14} />
              <span class="grow truncate">{item.name}</span>
              <span class="qty">+{item.quantity}</span>
            </div>
          {/each}
        </div>
      {/if}

      <div class="cmd-hint">
        <kbd>Entrée</kbd> valide · <kbd>Échap</kbd> ferme. Tape les codes à la chaîne, la
        fenêtre reste ouverte.
      </div>
    {:else}
      <div class="confirm">
        <div class="row" style="margin-bottom:.9rem">
          {#if pending.product?.image_url}
            <img class="thumb" src={pending.product.image_url} alt="" />
          {:else}
            <div class="thumb placeholder"><Icon name="jar" size={20} /></div>
          {/if}
          <div class="grow">
            <strong>{pending.product?.name ?? 'Produit inconnu'}</strong>
            <div class="faint">
              {[pending.product?.brand, pending.product?.net_quantity]
                .filter(Boolean)
                .join(' · ') || pending.barcode}
              {#if pending.in_stock > 0} · {pending.in_stock} déjà en stock{/if}
            </div>
          </div>
        </div>

        {#if !pending.found}
          <div class="banner warn stacked" style="margin-bottom:.8rem">
            Code inconnu d'Open Food Facts. Nomme-le, il rejoint ton catalogue.
          </div>
          <input
            class="grow"
            style="margin-bottom:.8rem"
            placeholder="Nom du produit"
            bind:value={manualName}
          />
        {/if}

        <div class="row" style="gap:1rem; margin-bottom:.8rem">
          <div class="stepper">
            <button onclick={() => (quantity = Math.max(1, quantity - 1))} aria-label="Moins un">
              <Icon name="minus" size={16} />
            </button>
            <span class="value">{quantity}</span>
            <button onclick={() => (quantity = Math.min(99, quantity + 1))} aria-label="Plus un">
              <Icon name="plus" size={16} />
            </button>
          </div>
          <input type="date" bind:value={expiresOn} style="width:11rem" />
          <select
            value={locationId ?? ''}
            onchange={(event) =>
              (locationId = event.currentTarget.value ? Number(event.currentTarget.value) : null)}
            style="width:10rem"
          >
            <option value="">Non rangé</option>
            {#each app.locations as location (location.id)}
              <option value={location.id}>{location.name}</option>
            {/each}
          </select>
        </div>

        <div class="chips scroll" style="margin-bottom:1rem">
          <button class="chip" class:on={expiresOn === ''} onclick={() => (expiresOn = '')}>
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

        <div class="row">
          <span class="faint grow">
            {expiresOn ? describeExpiry(expiresOn) : 'aucune date limite'}
          </span>
          <button class="btn" onclick={() => (pending = null)}>Annuler</button>
          <button class="btn primary" disabled={!canConfirm} onclick={confirm}>
            {busy ? 'Enregistrement…' : `Rentrer ${quantity}`}
          </button>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .matches,
  .session {
    border-top: 1px solid var(--border);
    padding: 0.5rem 1.1rem;
  }

  .session h3 {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-dim);
    margin: 0.2rem 0 0.3rem;
  }

  .match {
    display: flex;
    width: 100%;
    align-items: center;
    gap: 0.6rem;
    padding: 0.45rem 0.2rem;
    border-radius: 8px;
    text-align: left;
    font-size: 0.88rem;
  }

  .match:hover {
    background: var(--bg-input);
  }

  .confirm {
    padding: 1rem 1.1rem 1.1rem;
  }
</style>
