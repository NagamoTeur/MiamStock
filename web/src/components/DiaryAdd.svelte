<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import { api } from '../lib/api';
  import { REPAS, entier, repasDuMoment } from '../lib/repas';
  import { app } from '../lib/state.svelte';
  import type { Food, Meal } from '../lib/types';

  interface Props {
    food: Food;
    day: string;
    meal?: Meal;
    onclose: () => void;
    onadded: () => void;
  }

  let { food, day, meal, onclose, onadded }: Props = $props();

  // svelte-ignore state_referenced_locally
  let aliment = $state<Food>(food);
  // svelte-ignore state_referenced_locally
  let grammes = $state(food.portion_g ?? 100);
  // svelte-ignore state_referenced_locally
  let repas = $state<Meal>(meal ?? repasDuMoment());
  let fini = $state(false);
  let busy = $state(false);
  // Un produit scanné qu'Open Food Facts connaît sans ses valeurs : rien à compléter.
  // svelte-ignore state_referenced_locally
  let completion = $state<'inutile' | 'encours' | 'echec'>(
    food.source !== 'catalogue' && food.kcal_100g == null ? 'echec' : 'inutile',
  );

  /* Les produits scannés avant l'ajout du journal n'ont pas de valeurs
     nutritionnelles. On les complète à la volée depuis Open Food Facts plutôt
     que d'enregistrer un repas à zéro calorie. */
  $effect(() => {
    if (aliment.source !== 'catalogue' || aliment.kcal_100g != null) return;
    completion = 'encours';
    void api
      .refreshProduct(aliment.ref)
      .then((p) => {
        aliment = { ...aliment, kcal_100g: p.kcal_100g, prot_100g: p.prot_100g,
                    gluc_100g: p.gluc_100g, lip_100g: p.lip_100g, portion_g: p.portion_g };
        if (p.portion_g && grammes === 100) grammes = p.portion_g;
        completion = p.kcal_100g == null ? 'echec' : 'inutile';
      })
      .catch(() => (completion = 'echec'));
  });

  const part = (v: number | null) => (v == null ? null : (v * grammes) / 100);
  const kcal = $derived(part(aliment.kcal_100g));

  const raccourcis = $derived.by(() => {
    const valeurs = [50, 100, 150, 200];
    if (aliment.portion_g && !valeurs.includes(aliment.portion_g)) {
      return [{ g: aliment.portion_g, label: `1 portion · ${entier(aliment.portion_g)} g` }]
        .concat(valeurs.map((g) => ({ g, label: `${g} g` })));
    }
    return valeurs.map((g) => ({ g, label: `${g} g` }));
  });

  const peutRetirer = $derived(aliment.source === 'catalogue' && aliment.in_stock > 0);
  const valide = $derived(aliment.kcal_100g != null && grammes > 0 && !busy);

  async function ajouter() {
    if (!valide) return;
    busy = true;
    const ok = await app.guard(() =>
      api.addDiary({
        day,
        meal: repas,
        label: aliment.name,
        brand: aliment.brand,
        source: aliment.source,
        ref: aliment.ref || null,
        grams: grammes,
        kcal_100g: aliment.kcal_100g!,
        prot_100g: aliment.prot_100g,
        gluc_100g: aliment.gluc_100g,
        lip_100g: aliment.lip_100g,
        finished_pack: fini,
      }),
    );
    busy = false;
    if (!ok) return;
    app.toast(`${aliment.name} · ${entier(kcal ?? 0)} kcal${fini ? ' · retiré du stock' : ''}`);
    if (fini) await app.refreshStock();
    onadded();
  }
</script>

<div
  class="backdrop"
  role="button"
  tabindex="-1"
  onclick={(e) => e.target === e.currentTarget && onclose()}
  onkeydown={(e) => e.key === 'Escape' && onclose()}
>
  <div class="sheet" role="dialog" aria-modal="true" aria-label="Ajouter au journal">
    <div class="row" style="margin-bottom:.9rem; align-items:flex-start">
      <div class="grow">
        <h2>{aliment.name}</h2>
        <div class="faint">
          {[aliment.brand, aliment.kcal_100g != null ? `${entier(aliment.kcal_100g)} kcal / 100 g` : null]
            .filter(Boolean)
            .join(' · ')}
        </div>
      </div>
      <button class="btn ghost icon-btn" onclick={onclose} aria-label="Fermer">
        <Icon name="close" />
      </button>
    </div>

    {#if completion === 'encours'}
      <p class="muted">Récupération des valeurs nutritionnelles…</p>
    {:else if completion === 'echec'}
      <div class="banner warn stacked">
        Open Food Facts n'a pas de valeurs nutritionnelles pour ce produit. Cherche plutôt
        l'aliment générique équivalent.
      </div>
    {/if}

    <div class="stack" style="margin-bottom:1rem">
      <span class="muted">Quantité</span>
      <div class="row" style="gap:.6rem">
        <input
          type="number"
          inputmode="decimal"
          min="1"
          max="5000"
          bind:value={grammes}
          class="grow"
          style="font-size:1.25rem; font-weight:650; text-align:right"
        />
        <span class="muted">grammes</span>
      </div>
      <div class="chips scroll">
        {#each raccourcis as r (r.g)}
          <button class="chip" class:on={grammes === r.g} onclick={() => (grammes = r.g)}>
            {r.label}
          </button>
        {/each}
      </div>
    </div>

    <div class="stack" style="margin-bottom:1rem">
      <span class="muted">Repas</span>
      <div class="seg">
        {#each REPAS as r (r.id)}
          <button class:on={repas === r.id} onclick={() => (repas = r.id)}>{r.label}</button>
        {/each}
      </div>
    </div>

    {#if kcal != null}
      <div class="bilan">
        <span class="kcal">{entier(kcal)}</span>
        <span class="muted">kcal</span>
        <span class="macros faint">
          P {entier(part(aliment.prot_100g) ?? 0)} g · G {entier(part(aliment.gluc_100g) ?? 0)} g ·
          L {entier(part(aliment.lip_100g) ?? 0)} g
        </span>
      </div>
    {/if}

    {#if peutRetirer}
      <label class="row" style="gap:.6rem; margin-bottom:1rem">
        <button
          type="button"
          class="tick"
          class:on={fini}
          aria-pressed={fini}
          onclick={() => (fini = !fini)}
        >
          {#if fini}<Icon name="check" size={16} />{/if}
        </button>
        <span class="muted grow">
          J'ai fini le paquet — le retirer du stock ({aliment.in_stock} restant{aliment.in_stock > 1 ? 's' : ''})
        </span>
      </label>
    {/if}

    <button class="btn primary block lg" disabled={!valide} onclick={ajouter}>
      {busy ? 'Enregistrement…' : 'Ajouter au journal'}
    </button>
  </div>
</div>

<style>
  .bilan {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.35rem 0.5rem;
    margin-bottom: 1rem;
    padding: 0.75rem 0.9rem;
    border-radius: var(--radius);
    background: var(--bg-input);
  }

  .kcal {
    font-size: 1.7rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    line-height: 1;
  }

  .macros {
    width: 100%;
    font-variant-numeric: tabular-nums;
  }

  .seg {
    grid-template-columns: repeat(2, 1fr);
    grid-auto-flow: row;
  }
</style>
