<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import { api } from '../lib/api';
  import { addDaysIso, todayIso } from '../lib/dates';
  import { REPAS, entier, repasDuMoment } from '../lib/repas';
  import { app } from '../lib/state.svelte';
  import type { DiaryDay, DiaryEntry, Food, Meal } from '../lib/types';
  import DiaryAdd from './DiaryAdd.svelte';
  import FoodSearch from './FoodSearch.svelte';

  let jour = $state(todayIso());
  let donnees = $state<DiaryDay | null>(null);
  let objectifSaisi = $state('');

  let recherchePour = $state<Meal | null>(null);
  let choisi = $state<{ food: Food; meal: Meal } | null>(null);
  let ouverte = $state<number | null>(null);

  async function charger() {
    const d = await app.guard(() => api.diary(jour));
    if (d) donnees = d;
  }

  $effect(() => {
    void jour;
    void charger();
  });

  const estAujourdhui = $derived(jour === todayIso());

  /* Deux lignes voulues plutôt qu'une coupée au hasard : le repère relatif
     (« Aujourd'hui ») en titre, la date exacte en dessous. */
  const dateExacte = $derived.by(() => {
    const [a, m, j] = jour.split('-').map(Number);
    return new Intl.DateTimeFormat('fr-FR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
    }).format(new Date(a!, m! - 1, j!));
  });

  const repereJour = $derived.by(() => {
    if (estAujourdhui) return "Aujourd'hui";
    if (jour === addDaysIso(-1)) return 'Hier';
    // Majuscule à l'initiale seulement : en français, « octobre » n'en prend pas.
    return dateExacte.charAt(0).toUpperCase() + dateExacte.slice(1);
  });

  const sousTitreJour = $derived(
    estAujourdhui || jour === addDaysIso(-1) ? dateExacte : '',
  );

  const total = $derived(donnees?.totals.kcal ?? 0);
  const objectif = $derived(donnees?.goal_kcal ?? null);
  const ratio = $derived(objectif ? Math.min(total / objectif, 1) : 0);
  const depasse = $derived(objectif != null && total > objectif);

  function entreesDe(repas: Meal): DiaryEntry[] {
    return donnees?.entries.filter((e) => e.meal === repas) ?? [];
  }

  async function enregistrerObjectif() {
    const valeur = Number(objectifSaisi);
    if (!Number.isFinite(valeur) || valeur < 500) {
      app.toast('Un objectif se situe entre 500 et 10 000 kcal', 'warn');
      return;
    }
    if (await app.guard(() => api.setDiaryGoal(Math.round(valeur)))) {
      objectifSaisi = '';
      await charger();
    }
  }

  async function changerQuantite(entree: DiaryEntry, valeur: number) {
    if (!(valeur > 0)) return;
    if (await app.guard(() => api.patchDiary(entree.id, { grams: valeur }))) await charger();
  }

  async function supprimer(entree: DiaryEntry) {
    if (await app.guard(() => api.deleteDiary(entree.id))) {
      ouverte = null;
      app.toast(`${entree.label} retiré`);
      await charger();
    }
  }
</script>

<div class="stack journal">
  <div class="nav-jour">
    <button class="btn ghost icon-btn" onclick={() => (jour = addDaysIso(-1, jour))} aria-label="Jour précédent">
      <Icon name="chevronLeft" />
    </button>
    <button class="grow date" onclick={() => (jour = todayIso())} disabled={estAujourdhui}>
      <span class="repere">{repereJour}</span>
      {#if sousTitreJour}<span class="exacte">{sousTitreJour}</span>{/if}
    </button>
    <button
      class="btn ghost icon-btn"
      onclick={() => (jour = addDaysIso(1, jour))}
      disabled={estAujourdhui}
      aria-label="Jour suivant"
    >
      <Icon name="chevronRight" />
    </button>
  </div>

  <section class="card resume">
    <div class="row" style="align-items:baseline; gap:.4rem">
      <span class="total" class:depasse>{entier(total)}</span>
      <span class="muted">kcal</span>
      {#if objectif}
        <span class="grow"></span>
        <span class="muted">sur {entier(objectif)}</span>
      {/if}
    </div>

    {#if objectif}
      <div class="barre" aria-hidden="true">
        <span class:depasse style="transform:scaleX({ratio})"></span>
      </div>
      <p class="reste" class:depasse>
        {#if depasse}
          {entier(total - objectif)} kcal au-dessus de ton objectif
        {:else}
          Il reste {entier(objectif - total)} kcal
        {/if}
      </p>
    {:else}
      <form class="row objectif" onsubmit={(e) => { e.preventDefault(); void enregistrerObjectif(); }}>
        <input
          class="grow"
          type="number"
          inputmode="numeric"
          placeholder="Ton objectif quotidien, en kcal"
          bind:value={objectifSaisi}
        />
        <button class="btn" disabled={!objectifSaisi}>Fixer</button>
      </form>
    {/if}

    {#if donnees}
      <p class="macros">
        <span>Protéines <b>{entier(donnees.totals.prot)}</b> g</span>
        <span>Glucides <b>{entier(donnees.totals.gluc)}</b> g</span>
        <span>Lipides <b>{entier(donnees.totals.lip)}</b> g</span>
      </p>
    {/if}
  </section>

  <button class="btn primary block lg" onclick={() => (recherchePour = repasDuMoment())}>
    <Icon name="plus" />
    Ajouter un aliment
  </button>

  {#each REPAS as r (r.id)}
    {@const entrees = entreesDe(r.id)}
    <section class="repas">
      <header>
        <h2 class="grow">{r.label}</h2>
        {#if entrees.length}
          <span class="sous-total">{entier(donnees?.meals[r.id]?.kcal ?? 0)} kcal</span>
        {/if}
        <button class="btn ghost icon-btn" onclick={() => (recherchePour = r.id)} aria-label="Ajouter au {r.label.toLowerCase()}">
          <Icon name="plus" size={18} />
        </button>
      </header>

      {#each entrees as e (e.id)}
        <div class="entree" class:ouverte={ouverte === e.id}>
          <button class="resume-entree" onclick={() => (ouverte = ouverte === e.id ? null : e.id)}>
            <span class="grow">
              <span class="nom truncate">{e.label}</span>
              <span class="faint">{entier(e.grams)} g{e.brand ? ` · ${e.brand}` : ''}</span>
            </span>
            <span class="kcal">{entier(e.kcal)}</span>
          </button>
          {#if ouverte === e.id}
            <div class="edition">
              <input
                type="number"
                inputmode="decimal"
                min="1"
                value={e.grams}
                onchange={(ev) => changerQuantite(e, Number(ev.currentTarget.value))}
                aria-label="Quantité en grammes"
              />
              <span class="muted">g</span>
              <span class="grow"></span>
              <button class="btn ghost danger" onclick={() => supprimer(e)}>
                <Icon name="trash" size={16} />
                Retirer
              </button>
            </div>
          {/if}
        </div>
      {:else}
        <p class="faint vide">Rien pour l'instant.</p>
      {/each}
    </section>
  {/each}
</div>

{#if recherchePour}
  <FoodSearch
    titre="Ajouter un aliment"
    recents
    onclose={() => (recherchePour = null)}
    onpick={(food) => {
      choisi = { food, meal: recherchePour! };
      recherchePour = null;
    }}
  />
{/if}

{#if choisi}
  <DiaryAdd
    food={choisi.food}
    meal={choisi.meal}
    day={jour}
    onclose={() => (choisi = null)}
    onadded={() => {
      choisi = null;
      void charger();
    }}
  />
{/if}

<style>
  .nav-jour {
    display: flex;
    align-items: center;
    gap: 0.3rem;
  }

  .date {
    display: grid;
    justify-items: center;
    gap: 0.05rem;
    padding: 0.35rem 0.5rem;
    border-radius: 10px;
  }

  .repere {
    font-weight: 650;
    font-size: 1rem;
  }

  .exacte {
    font-size: 0.78rem;
    color: var(--text-dim);
  }

  .date:not(:disabled):hover {
    color: var(--accent);
  }

  .resume {
    padding: 1rem 1rem 0.9rem;
  }

  .total {
    font-size: 2.6rem;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
  }

  .total.depasse,
  .reste.depasse {
    color: var(--urgent);
  }

  /* Mise à l'échelle, pas une largeur animée : pas de recalcul de mise en page. */
  .barre {
    height: 8px;
    margin: 0.8rem 0 0.45rem;
    border-radius: 999px;
    background: var(--bg-input);
    overflow: hidden;
  }

  .barre span {
    display: block;
    width: 100%;
    height: 100%;
    background: var(--accent);
    transform-origin: left center;
    transition: transform 0.25s ease;
  }

  .barre span.depasse {
    background: var(--urgent);
  }

  .reste {
    margin: 0;
    font-size: 0.88rem;
    color: var(--text-dim);
  }

  .objectif {
    margin-top: 0.8rem;
  }

  .macros {
    display: flex;
    flex-wrap: wrap;
    gap: 0.2rem 1rem;
    margin: 0.75rem 0 0;
    padding-top: 0.7rem;
    border-top: 1px solid var(--border);
    font-size: 0.82rem;
    color: var(--text-dim);
  }

  .macros b {
    color: var(--text);
    font-variant-numeric: tabular-nums;
  }

  .repas header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.4rem;
    border-bottom: 1px solid var(--border);
  }

  .repas h2 {
    margin: 0;
    font-size: 0.95rem;
  }

  .sous-total {
    color: var(--text-dim);
    font-size: 0.85rem;
    font-variant-numeric: tabular-nums;
  }

  .resume-entree {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    width: 100%;
    min-height: 52px;
    padding: 0.4rem 0;
    text-align: left;
  }

  .resume-entree .grow {
    display: grid;
    min-width: 0;
  }

  .entree {
    border-bottom: 1px solid color-mix(in srgb, var(--border) 55%, transparent);
  }

  .kcal {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
  }

  .edition {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0 0 0.6rem;
  }

  .edition input {
    width: 6rem;
    text-align: right;
  }

  .vide {
    margin: 0.55rem 0 0.2rem;
  }
</style>
