<script lang="ts">
  import { api } from './api';
  import { SHELF_PRESETS } from './dates';
  import { app } from './state.svelte';
  import type { ConsumptionEntry, Product } from './types';

  interface Props {
    product: Product;
    /** Rappelé après chaque écriture, pour que l'appelant rafraîchisse ce qu'il affiche. */
    onsaved?: () => void | Promise<void>;
  }

  let { product, onsaved }: Props = $props();
  let saving = $state(false);
  let rythme = $state<ConsumptionEntry | null>(null);

  /* Le rythme est mesuré sur le journal des sorties, pas estimé : il n'apparaît
     que lorsqu'il repose sur assez de mouvements étalés dans le temps. */
  $effect(() => {
    const barcode = product.barcode;
    void (async () => {
      const lignes = await app.guard(() => api.consumption());
      rythme = lignes?.find((ligne) => ligne.barcode === barcode) ?? null;
    })();
  });

  /* Partagé par la fiche du téléphone et le panneau du PC : deux formulaires
     séparés finiraient par diverger, et la même donnée se corrigerait
     différemment selon l'écran. */
  async function save(field: string, value: string | number | null) {
    saving = true;
    const updated = await app.guard(() => api.patchProduct(product.barcode, { [field]: value }));
    saving = false;
    if (updated) {
      await onsaved?.();
      app.toast('Fiche mise à jour');
    }
  }

  const id = (suffix: string) => `pf-${product.barcode}-${suffix}`;
</script>

<div class="fields">
  <div class="field">
    <label for={id('name')}>Nom {#if saving}<span class="faint">· enregistrement…</span>{/if}</label>
    <input
      id={id('name')}
      value={product.name}
      onchange={(event) => save('name', event.currentTarget.value.trim())}
    />
  </div>

  <div class="field">
    <label for={id('brand')}>Marque</label>
    <input
      id={id('brand')}
      value={product.brand ?? ''}
      placeholder="—"
      onchange={(event) => save('brand', event.currentTarget.value.trim() || null)}
    />
  </div>

  <div class="field">
    <label for={id('net')}>Contenance</label>
    <input
      id={id('net')}
      value={product.net_quantity ?? ''}
      placeholder="400 g"
      onchange={(event) => save('net_quantity', event.currentTarget.value.trim() || null)}
    />
  </div>

  <div class="field">
    <label for={id('loc')}>Emplacement par défaut</label>
    <select
      id={id('loc')}
      value={product.default_location_id ?? ''}
      onchange={(event) =>
        save('default_location_id', event.currentTarget.value ? Number(event.currentTarget.value) : null)}
    >
      <option value="">Aucun</option>
      {#each app.locations as location (location.id)}
        <option value={location.id}>{location.name}</option>
      {/each}
    </select>
  </div>

  <div class="field">
    <label for={id('shelf')}>Durée de conservation habituelle, en jours</label>
    <input
      id={id('shelf')}
      type="number"
      min="0"
      max="3650"
      placeholder="—"
      value={product.default_shelf_life_days ?? ''}
      onchange={(event) =>
        save('default_shelf_life_days', event.currentTarget.value ? Number(event.currentTarget.value) : null)}
    />
    <div class="chips wrap" style="margin-top:.35rem">
      {#each SHELF_PRESETS as preset (preset.days)}
        <button
          type="button"
          class="chip"
          class:on={product.default_shelf_life_days === preset.days}
          onclick={() => save('default_shelf_life_days', preset.days)}
        >
          {preset.label}
        </button>
      {/each}
    </div>
    <span class="faint">Pré-remplit la date limite au prochain scan.</span>
  </div>

  <div class="field">
    <label for={id('min')}>Toujours en avoir au moins</label>
    <input
      id={id('min')}
      type="number"
      min="0"
      max="99"
      value={product.min_quantity}
      onchange={(event) => save('min_quantity', Number(event.currentTarget.value))}
    />
    <span class="faint">Sous ce seuil, le produit part tout seul en liste de courses.</span>

    {#if rythme?.reliable && rythme.suggested_min != null}
      <div class="suggestion">
        <span class="grow">
          Tu en sors environ <b>{rythme.per_week}</b> par semaine.
          {#if rythme.days_left != null}
            Au rythme actuel, il t'en reste pour <b>{Math.round(rythme.days_left)}</b> jour{Math.round(rythme.days_left) > 1 ? 's' : ''}.
          {/if}
        </span>
        {#if rythme.suggested_min !== product.min_quantity}
          <button
            type="button"
            class="btn"
            style="min-height:36px"
            onclick={() => save('min_quantity', rythme!.suggested_min!)}
          >
            Passer le seuil à {rythme.suggested_min}
          </button>
        {/if}
      </div>
    {:else if rythme}
      <span class="faint">
        Pas encore assez de sorties enregistrées pour en déduire un rythme.
      </span>
    {/if}
  </div>
</div>

<style>
  .fields {
    display: grid;
    gap: 0.2rem;
  }

  .suggestion {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-top: 0.5rem;
    padding: 0.6rem 0.7rem;
    border-radius: var(--radius);
    background: var(--accent-soft);
    border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
    font-size: 0.82rem;
    color: var(--text-dim);
  }

  .suggestion b {
    color: var(--text);
    font-variant-numeric: tabular-nums;
  }
</style>
