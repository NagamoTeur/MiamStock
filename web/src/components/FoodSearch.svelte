<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import { alimentDepuisCode } from '../lib/aliments';
  import { api } from '../lib/api';
  import { entier } from '../lib/repas';
  import { cameraAvailable } from '../lib/scanner';
  import { app } from '../lib/state.svelte';
  import type { Food, MealTemplate } from '../lib/types';
  import ScanCode from './ScanCode.svelte';

  interface Props {
    titre: string;
    onpick: (food: Food) => void;
    onclose: () => void;
    /** Montrer les aliments récents du journal tant que rien n'est tapé. */
    recents?: boolean;
    /** Proposer d'ajouter le texte tapé tel quel (liste de courses). */
    libre?: (texte: string) => void;
    /** Proposer une saisie en calories, sans poids (journal). */
    rapide?: (texte: string) => void;
    /** Montrer les repas favoris, et ce qu'on fait de celui qu'on choisit. */
    favori?: (modele: MealTemplate) => void;
    /** Offrir le scan d'un code-barres ; `'direct'` ouvre la caméra d'emblée. */
    scan?: boolean | 'direct';
  }

  let { titre, onpick, onclose, recents = false, libre, rapide, favori, scan = false }: Props =
    $props();

  const scanPossible = $derived(Boolean(scan) && cameraAvailable());
  // svelte-ignore state_referenced_locally
  let scanner = $state(scan === 'direct' && cameraAvailable());
  let resolution = $state(false);
  let favoris = $state<MealTemplate[]>([]);

  let q = $state('');
  let local = $state<Food[]>([]);
  let commerce = $state<Food[]>([]);
  let etatOff = $state<'repos' | 'charge' | 'fait' | 'panne'>('repos');
  let recentes = $state<Food[]>([]);
  let champ: HTMLInputElement | null = $state(null);

  let numero = 0;
  let minuterie: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    champ?.focus();
  });

  $effect(() => {
    if (!recents) return;
    void api.diaryRecent().then((r) => (recentes = r)).catch(() => {});
  });

  $effect(() => {
    if (!favori) return;
    void api.templates().then((t) => (favoris = t)).catch(() => {});
  });

  /* Un code inconnu partout ne bloque pas : on revient à la recherche par nom,
     qui trouvera l'équivalent générique. */
  async function codeLu(code: string) {
    scanner = false;
    resolution = true;
    const lookup = await app.guard(() => api.lookup(code));
    resolution = false;
    if (!lookup) return;
    const aliment = alimentDepuisCode(lookup);
    if (aliment) {
      onpick(aliment);
      return;
    }
    app.toast("Produit inconnu d'Open Food Facts : cherche-le par son nom", 'warn');
    champ?.focus();
  }

  const sansAccents = (t: string) =>
    t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

  const favorisVisibles = $derived.by(() => {
    const requete = sansAccents(q.trim());
    if (requete.length < 2) return favoris;
    return favoris.filter((f) => sansAccents(f.name).includes(requete));
  });

  function apercu(f: MealTemplate): string {
    return `${f.labels.slice(0, 3).join(', ')}${f.count > 3 ? '…' : ''} · ${entier(f.kcal)} kcal`;
  }

  function saisir(valeur: string) {
    q = valeur;
    if (minuterie) clearTimeout(minuterie);
    minuterie = setTimeout(() => void chercher(valeur), 220);
  }

  /* Le local répond tout de suite ; Open Food Facts arrive après, et on ne
     l'attend jamais pour montrer quelque chose. Le numéro écarte les réponses
     d'une frappe déjà dépassée, qui écraseraient sinon la recherche en cours. */
  async function chercher(valeur: string) {
    const id = ++numero;
    if (valeur.trim().length < 2) {
      local = [];
      commerce = [];
      etatOff = 'repos';
      return;
    }
    api
      .search(valeur, 'local')
      .then((r) => id === numero && (local = r.results))
      .catch(() => {});
    etatOff = 'charge';
    api
      .search(valeur, 'off')
      .then((r) => {
        if (id !== numero) return;
        commerce = r.results;
        etatOff = r.off_unavailable ? 'panne' : 'fait';
      })
      .catch(() => id === numero && (etatOff = 'panne'));
  }

  const dansLeStock = $derived(local.filter((f) => f.source === 'catalogue'));
  const generiques = $derived(local.filter((f) => f.source === 'ciqual'));
  // Un produit déjà dans ton stock n'a pas à réapparaître parmi ceux du commerce.
  const duCommerce = $derived(
    commerce.filter((f) => !dansLeStock.some((s) => s.ref === f.ref)),
  );

  const rien = $derived(
    q.trim().length >= 2 &&
      dansLeStock.length + generiques.length + duCommerce.length +
        (favori ? favorisVisibles.length : 0) === 0 &&
      etatOff !== 'charge',
  );

  function detail(f: Food): string {
    if (f.source === 'rapide') return `saisie rapide · ${entier(f.kcal_100g ?? 0)} kcal`;
    const morceaux = [f.brand];
    morceaux.push(f.kcal_100g != null ? `${entier(f.kcal_100g)} kcal / 100 g` : 'valeurs à compléter');
    return morceaux.filter(Boolean).join(' · ');
  }
</script>

{#snippet ligne(f: Food)}
  <button class="resultat" onclick={() => onpick(f)}>
    <span class="grow">
      <span class="nom truncate">{f.name}</span>
      <span class="faint truncate">{detail(f)}</span>
    </span>
    {#if f.in_stock > 0}<span class="pastille">{f.in_stock} en stock</span>{/if}
  </button>
{/snippet}

{#snippet repasFavoris()}
  {#if favori && favorisVisibles.length}
    <h3>Mes repas</h3>
    {#each favorisVisibles as f (f.id)}
      <button class="resultat" onclick={() => favori(f)}>
        <Icon name="star" size={18} />
        <span class="grow">
          <span class="nom truncate">{f.name}</span>
          <span class="faint truncate">{apercu(f)}</span>
        </span>
      </button>
    {/each}
  {/if}
{/snippet}

<div
  class="backdrop"
  role="button"
  tabindex="-1"
  onclick={(e) => e.target === e.currentTarget && onclose()}
  onkeydown={(e) => e.key === 'Escape' && onclose()}
>
  <div class="sheet recherche" role="dialog" aria-modal="true" aria-label={titre}>
    <div class="row" style="margin-bottom:.7rem">
      <h2 class="grow">{titre}</h2>
      <button class="btn ghost icon-btn" onclick={onclose} aria-label="Fermer">
        <Icon name="close" />
      </button>
    </div>

    <div class="champ">
      <Icon name="search" size={18} />
      <input
        bind:this={champ}
        value={q}
        oninput={(e) => saisir(e.currentTarget.value)}
        placeholder="Pomme, skyr, pâtes complètes…"
        autocomplete="off"
        enterkeyhint="search"
      />
      {#if scanPossible}
        <button
          class="btn ghost icon-btn scanner"
          onclick={() => (scanner = true)}
          disabled={resolution}
          aria-label="Scanner un code-barres"
        >
          <Icon name="scan" size={20} />
        </button>
      {/if}
    </div>

    <div class="resultats">
      {#if resolution}
        <p class="faint invite">Recherche du produit scanné…</p>
      {/if}

      {#if q.trim().length < 2}
        {#if rapide}
          <button class="resultat libre" onclick={() => rapide('')}>
            <Icon name="pencil" size={18} />
            <span class="grow">
              <span class="nom">Saisie rapide</span>
              <span class="faint">Restaurant, plat maison : juste les calories</span>
            </span>
          </button>
        {/if}
        {@render repasFavoris()}
        {#if recents && recentes.length}
          <h3>Récents</h3>
          {#each recentes as f (f.source + f.ref + f.name)}
            {@render ligne(f)}
          {/each}
        {:else if !favoris.length}
          <p class="faint invite">
            Tape au moins deux lettres. La recherche couvre ton stock, les aliments
            courants et les produits du commerce{scanPossible ? ', ou scanne un code-barres' : ''}.
          </p>
        {/if}
      {:else}
        {#if libre}
          <button class="resultat libre" onclick={() => libre(q.trim())}>
            <Icon name="plus" size={18} />
            <span class="grow">Ajouter « {q.trim()} » tel quel</span>
          </button>
        {/if}
        {#if rapide}
          <button class="resultat libre" onclick={() => rapide(q.trim())}>
            <Icon name="pencil" size={18} />
            <span class="grow">Saisir « {q.trim()} » en calories</span>
          </button>
        {/if}

        {@render repasFavoris()}

        {#if dansLeStock.length}
          <h3>Dans ton stock</h3>
          {#each dansLeStock as f (f.ref)}{@render ligne(f)}{/each}
        {/if}

        {#if generiques.length}
          <h3>Aliments</h3>
          {#each generiques as f (f.ref)}{@render ligne(f)}{/each}
        {/if}

        {#if duCommerce.length}
          <h3>Produits du commerce</h3>
          {#each duCommerce as f (f.ref)}{@render ligne(f)}{/each}
        {/if}

        {#if etatOff === 'charge'}
          <p class="faint invite">Recherche dans Open Food Facts…</p>
        {:else if etatOff === 'panne'}
          <p class="faint invite">
            Open Food Facts ne répond pas : seuls ton stock et les aliments courants
            sont affichés.
          </p>
        {/if}

        {#if rien}
          <p class="faint invite">Rien trouvé pour « {q.trim()} ».</p>
        {/if}
      {/if}
    </div>
  </div>
</div>

{#if scanner}
  <ScanCode titre="Scanner un produit" oncode={codeLu} onclose={() => (scanner = false)} />
{/if}

<style>
  .recherche {
    height: 88vh;
    display: grid;
    grid-template-rows: auto auto minmax(0, 1fr);
  }

  .champ {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0 0.8rem;
    border-radius: var(--radius);
    background: var(--bg-input);
    border: 1px solid var(--border);
    color: var(--text-faint);
  }

  .champ input {
    border: none;
    background: transparent;
    padding: 0.8rem 0;
  }

  .champ input:focus-visible {
    outline: none;
  }

  .champ:focus-within {
    border-color: var(--accent);
  }

  .scanner {
    margin-right: -0.5rem;
    color: var(--accent);
  }

  .resultats {
    overflow-y: auto;
    margin-top: 0.4rem;
  }

  h3 {
    margin: 1rem 0 0.2rem;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--accent);
  }

  .resultat {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    width: 100%;
    min-height: 54px;
    padding: 0.45rem 0.1rem;
    text-align: left;
    border-bottom: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
  }

  .resultat:active {
    background: color-mix(in srgb, var(--accent) 10%, transparent);
  }

  .resultat .grow {
    display: grid;
    min-width: 0;
  }

  .nom {
    font-size: 0.95rem;
  }

  .resultat.libre {
    color: var(--accent);
  }

  .resultat.libre .faint {
    color: var(--text-faint);
  }

  .pastille {
    flex: none;
    padding: 0.1rem 0.45rem;
    border-radius: 999px;
    background: var(--accent-soft);
    color: var(--accent);
    font-size: 0.7rem;
  }

  .invite {
    margin: 1rem 0.1rem;
    line-height: 1.5;
  }
</style>
