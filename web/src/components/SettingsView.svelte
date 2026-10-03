<script lang="ts">
  import { api } from '../lib/api';
  import { app } from '../lib/state.svelte';

  let newLocation = $state('');
  let newKind = $state<'fridge' | 'freezer' | 'pantry' | 'other'>('pantry');
  let busy = $state(false);
  let objectif = $state<string>('');

  $effect(() => {
    void api.diarySettings().then((s) => (objectif = s.goal_kcal ? String(s.goal_kcal) : ''));
  });

  async function enregistrerObjectif() {
    const valeur = objectif.trim() ? Math.round(Number(objectif)) : null;
    if (valeur != null && (!Number.isFinite(valeur) || valeur < 500 || valeur > 10000)) {
      app.toast('Un objectif se situe entre 500 et 10 000 kcal', 'warn');
      return;
    }
    if (await app.guard(() => api.setDiaryGoal(valeur))) {
      app.toast(valeur ? `Objectif fixé à ${valeur.toLocaleString('fr-FR')} kcal` : 'Objectif retiré');
    }
  }

  const KINDS = [
    { value: 'fridge', label: 'Réfrigéré' },
    { value: 'freezer', label: 'Congelé' },
    { value: 'pantry', label: 'Sec' },
    { value: 'other', label: 'Autre' },
  ] as const;

  async function addLocation(event: Event) {
    event.preventDefault();
    const name = newLocation.trim();
    if (!name || busy) return;
    busy = true;
    const created = await app.guard(() => api.createLocation(name, newKind));
    if (created) {
      newLocation = '';
      await app.refreshAll();
      app.toast(`Emplacement « ${created.name} » créé`);
    }
    busy = false;
  }

  async function removeLocation(id: number, name: string) {
    if (!confirm(`Supprimer « ${name} » ? Les produits rangés là resteront en stock, sans emplacement.`))
      return;
    await app.guard(() => api.deleteLocation(id));
    await app.refreshAll();
  }

  const installed = $derived(
    window.matchMedia('(display-mode: standalone)').matches ||
      (navigator as unknown as { standalone?: boolean }).standalone === true,
  );
</script>

<div class="stack">
  <div class="card">
    <h2 style="margin:0 0 .5rem; font-size:1rem">Emplacements</h2>
    {#each app.locations as location (location.id)}
      <div class="checkline">
        <div class="grow">
          <div>{location.name}</div>
          <div class="faint">
            {KINDS.find((kind) => kind.value === location.kind)?.label ?? location.kind}
            {#if location.kind === 'freezer'}
              · pas d'alerte avant la date
            {/if}
          </div>
        </div>
        <button
          class="btn ghost danger"
          style="min-height:34px; padding:0 .6rem"
          onclick={() => removeLocation(location.id, location.name)}
        >
          Supprimer
        </button>
      </div>
    {/each}

    <form class="stack" style="margin-top:.8rem" onsubmit={addLocation}>
      <input placeholder="Nouvel emplacement (cellier, garage…)" bind:value={newLocation} />
      <div class="chips">
        {#each KINDS as kind (kind.value)}
          <button
            type="button"
            class="chip"
            class:on={newKind === kind.value}
            onclick={() => (newKind = kind.value)}
          >
            {kind.label}
          </button>
        {/each}
      </div>
      <button class="btn" disabled={busy || !newLocation.trim()}>Ajouter</button>
    </form>
  </div>

  <div class="card">
    <h2 style="margin:0 0 .5rem; font-size:1rem">Journal alimentaire</h2>
    <form class="row" onsubmit={(e) => { e.preventDefault(); void enregistrerObjectif(); }}>
      <input
        class="grow"
        type="number"
        inputmode="numeric"
        placeholder="Objectif quotidien"
        bind:value={objectif}
        aria-label="Objectif calorique quotidien"
      />
      <span class="muted">kcal</span>
      <button class="btn">Enregistrer</button>
    </form>
    <p class="faint" style="margin:.6rem 0 0">
      Laisse vide pour suivre sans objectif. Les aliments génériques viennent de la
      table Ciqual de l'ANSES, les produits du commerce d'Open Food Facts.
    </p>
  </div>

  {#if app.summary}
    <div class="card">
      <h2 style="margin:0 0 .5rem; font-size:1rem">Ce que contient la maison</h2>
      <div class="kpis">
        <div class="kpi">
          <div class="n">{app.summary.distinct_products}</div>
          <div class="l">références</div>
        </div>
        <div class="kpi">
          <div class="n">{app.summary.total_items}</div>
          <div class="l">articles</div>
        </div>
        <div class="kpi">
          <div class="n status-expired">{app.summary.expired}</div>
          <div class="l">périmés</div>
        </div>
      </div>
      <p class="faint" style="margin:.7rem 0 0">
        Alerte urgente à {app.summary.urgent_days} jours, alerte « bientôt » à
        {app.summary.soon_days} jours. Ces seuils se règlent côté serveur avec
        <code>MIAMSTOCK_URGENT_DAYS</code> et <code>MIAMSTOCK_SOON_DAYS</code>.
      </p>
    </div>
  {/if}

  <div class="card">
    <h2 style="margin:0 0 .5rem; font-size:1rem">Installation</h2>
    {#if installed}
      <p class="muted" style="margin:0">
        L'app tourne en mode installé. Elle s'ouvre même sans réseau, mais un bip a besoin du
        serveur pour être enregistré.
      </p>
    {:else}
      <p class="muted" style="margin:0">
        Ajoute MiamStock à ton écran d'accueil pour l'ouvrir en plein écran : dans Chrome via
        le menu « Installer l'application », dans Safari via Partager puis « Sur l'écran
        d'accueil ».
      </p>
    {/if}
  </div>

  <div class="card">
    <h2 style="margin:0 0 .5rem; font-size:1rem">Données</h2>
    <p class="muted" style="margin:0 0 .7rem">
      Les fiches produits viennent d'Open Food Facts, base ouverte et gratuite. Un produit
      déjà scanné est mis en cache localement : le deuxième bip ne touche plus le réseau.
    </p>
    {#if app.authRequired}
      <button class="btn block" onclick={() => app.logout()}>Se déconnecter</button>
    {:else}
      <p class="banner stacked" style="margin:0">
        Aucun code PIN n'est configuré : quiconque atteint cette adresse peut modifier le
        stock. Définis <code>MIAMSTOCK_PIN</code> côté serveur.
      </p>
    {/if}
  </div>
</div>
