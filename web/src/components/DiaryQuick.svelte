<script lang="ts">
  /* La saisie rapide : un nom et des calories, sans peser quoi que ce soit.

     Pour le restaurant, le plat de la cantine, la part de gâteau d'un
     anniversaire : tout ce qu'on ne trouvera jamais dans une base, et qu'on
     finit par ne pas noter du tout si le journal exige des grammes. */
  import Icon from '../lib/Icon.svelte';
  import { api } from '../lib/api';
  import { REPAS, entier, repasDuMoment } from '../lib/repas';
  import { app } from '../lib/state.svelte';
  import type { Food, Meal } from '../lib/types';

  interface Props {
    /** Un nom tapé dans la recherche, ou une saisie rapide récente à refaire. */
    depart: { nom: string; food?: Food };
    day: string;
    meal?: Meal;
    onclose: () => void;
    onadded: () => void;
  }

  let { depart, day, meal, onclose, onadded }: Props = $props();

  const texte = (v: number | null | undefined) => (v == null ? '' : String(Math.round(v)));

  // svelte-ignore state_referenced_locally
  let nom = $state(depart.food?.name ?? depart.nom);
  // svelte-ignore state_referenced_locally
  let kcal = $state(texte(depart.food?.kcal_100g));
  // svelte-ignore state_referenced_locally
  let prot = $state(texte(depart.food?.prot_100g));
  // svelte-ignore state_referenced_locally
  let gluc = $state(texte(depart.food?.gluc_100g));
  // svelte-ignore state_referenced_locally
  let lip = $state(texte(depart.food?.lip_100g));
  // svelte-ignore state_referenced_locally
  let repas = $state<Meal>(meal ?? repasDuMoment());
  // svelte-ignore state_referenced_locally
  let detail = $state(
    [depart.food?.prot_100g, depart.food?.gluc_100g, depart.food?.lip_100g].some((v) => v != null),
  );
  let busy = $state(false);

  let champKcal: HTMLInputElement | null = $state(null);
  let champNom: HTMLInputElement | null = $state(null);

  // Le curseur va là où il reste quelque chose à écrire — une fois, à l'ouverture.
  // svelte-ignore state_referenced_locally
  const nomDejaConnu = Boolean((depart.food?.name ?? depart.nom).trim());
  $effect(() => {
    (nomDejaConnu ? champKcal : champNom)?.focus();
  });

  const nombre = (v: string) => (v.trim() === '' ? null : Number(v.replace(',', '.')));
  const kcalValeur = $derived(nombre(kcal));
  const valide = $derived(
    nom.trim().length > 0 &&
      kcalValeur != null &&
      Number.isFinite(kcalValeur) &&
      kcalValeur >= 0 &&
      kcalValeur <= 5000 &&
      !busy,
  );

  async function ajouter(event: Event) {
    event.preventDefault();
    if (!valide) return;
    busy = true;
    const ok = await app.guard(() =>
      api.addDiary({
        day,
        meal: repas,
        label: nom.trim(),
        source: 'rapide',
        grams: 100,
        kcal_100g: kcalValeur!,
        prot_100g: detail ? nombre(prot) : null,
        gluc_100g: detail ? nombre(gluc) : null,
        lip_100g: detail ? nombre(lip) : null,
      }),
    );
    busy = false;
    if (!ok) return;
    app.toast(`${nom.trim()} · ${entier(kcalValeur!)} kcal`);
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
  <div class="sheet" role="dialog" aria-modal="true" aria-label="Saisie rapide">
    <form onsubmit={ajouter}>
      <div class="row" style="margin-bottom:.9rem">
        <h2 class="grow">Saisie rapide</h2>
        <button type="button" class="btn ghost icon-btn" onclick={onclose} aria-label="Fermer">
          <Icon name="close" />
        </button>
      </div>

      <label class="stack" style="margin-bottom:1rem">
        <span class="muted">Quoi</span>
        <input bind:this={champNom} bind:value={nom} placeholder="Restaurant, part de pizza…" maxlength="200" />
      </label>

      <label class="stack" style="margin-bottom:1rem">
        <span class="muted">Calories, à peu près</span>
        <span class="row" style="gap:.6rem">
          <input
            bind:this={champKcal}
            bind:value={kcal}
            class="grow kcal"
            type="text"
            inputmode="numeric"
            placeholder="900"
            aria-label="Calories"
          />
          <span class="muted">kcal</span>
        </span>
      </label>

      {#if detail}
        <div class="macros">
          <label><span class="faint">Protéines</span><input bind:value={prot} inputmode="decimal" placeholder="g" /></label>
          <label><span class="faint">Glucides</span><input bind:value={gluc} inputmode="decimal" placeholder="g" /></label>
          <label><span class="faint">Lipides</span><input bind:value={lip} inputmode="decimal" placeholder="g" /></label>
        </div>
      {:else}
        <button type="button" class="btn ghost plus-detail" onclick={() => (detail = true)}>
          <Icon name="plus" size={16} />
          Ajouter les macros
        </button>
      {/if}

      <div class="stack" style="margin-bottom:1rem">
        <span class="muted">Repas</span>
        <div class="seg">
          {#each REPAS as r (r.id)}
            <button type="button" class:on={repas === r.id} onclick={() => (repas = r.id)}>{r.label}</button>
          {/each}
        </div>
      </div>

      <button class="btn primary block lg" disabled={!valide}>
        {busy ? 'Enregistrement…' : 'Ajouter au journal'}
      </button>
    </form>
  </div>
</div>

<style>
  .kcal {
    font-size: 1.25rem;
    font-weight: 650;
    text-align: right;
  }

  .macros {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.6rem;
    margin-bottom: 1rem;
  }

  .macros label {
    display: grid;
    gap: 0.25rem;
    font-size: 0.8rem;
  }

  .macros input {
    text-align: right;
  }

  .plus-detail {
    margin: -0.4rem 0 0.8rem;
    padding-left: 0;
    color: var(--accent);
  }

  .seg {
    grid-template-columns: repeat(2, 1fr);
    grid-auto-flow: row;
  }
</style>
