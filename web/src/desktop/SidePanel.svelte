<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import ProductFields from '../lib/ProductFields.svelte';
  import { describeExpiry } from '../lib/dates';
  import { daysUntil } from '../lib/dates';
  import { desk, flatten } from '../lib/desktop.svelte';
  import { app } from '../lib/state.svelte';

  const line = $derived(desk.focusedLine);
  const product = $derived(line?.product ?? null);
  const selection = $derived(desk.selectedLots);

  const aujourdhui = new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(new Date());

  const jour = $derived.by(() => {
    const lots = flatten(app.expiring).filter((lot) => lot.expires_on);
    return {
      urgents: lots.filter((lot) => daysUntil(lot.expires_on!) <= 0),
      semaine: lots.filter((lot) => daysUntil(lot.expires_on!) > 0),
    };
  });
  const urgentLots = $derived(jour.urgents);
  const semaineLots = $derived(jour.semaine);

  /* Le panneau est servi sur trois vues : l'invitation doit désigner la bonne. */
  const conseilVue = $derived(
    desk.view === 'frise'
      ? 'Clique un lot sur la frise pour ouvrir sa fiche.'
      : 'Clique une ligne du tableau pour ouvrir sa fiche.',
  );

  const KIND_LABEL: Record<string, string> = {
    in: 'entré',
    out: 'sorti',
    discard: 'jeté',
    adjust: 'corrigé',
    shopping_auto: 'mis aux courses',
    shopping_clear: 'courses vidées',
  };

  function when(iso: string): string {
    const date = new Date(iso);
    return new Intl.DateTimeFormat('fr-FR', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }
</script>

<aside class="panel">
  {#if selection.length > 1}
    <h2>{selection.length} lots sélectionnés</h2>
    <p class="muted">
      {selection.reduce((total, lot) => total + lot.quantity, 0)} articles au total.
      Les actions groupées sont en bas de la frise.
    </p>
    <section>
      <h3>Contenu de la sélection</h3>
      {#each selection as lot (lot.id)}
        <div class="checkline">
          <span class="dot bg-{lot.status}" aria-hidden="true"></span>
          <span class="grow truncate">{lot.quantity} × {lot.name}</span>
          <span class="faint">{describeExpiry(lot.expires_on)}</span>
        </div>
      {/each}
    </section>
  {:else if product}
    <div class="row" style="align-items:flex-start">
      {#if product.image_url}
        <img class="thumb" src={product.image_url} alt="" />
      {:else}
        <div class="thumb placeholder"><Icon name="jar" size={22} /></div>
      {/if}
      <div class="grow">
        <h2>{product.name}</h2>
        <div class="faint">{product.barcode}</div>
      </div>
      <button class="btn ghost icon-btn" onclick={() => desk.focusProduct(null)} aria-label="Fermer">
        <Icon name="close" size={16} />
      </button>
    </div>

    <section>
      <h3>Fiche produit</h3>
      <ProductFields
        {product}
        onsaved={async () => {
          await app.refreshStock();
          await desk.loadCatalog();
        }}
      />
    </section>

    {#if line}
      <section>
        <h3>Lots en stock · {line.total}</h3>
        {#each line.lots as lot (lot.id)}
          <div class="checkline">
            <span class="dot bg-{lot.status}" aria-hidden="true"></span>
            <span class="grow">
              <span class="qty">{lot.quantity}</span>
              <span class="faint"> · {lot.location_name ?? 'non rangé'}</span>
            </span>
            <input
              class="inline-input"
              style="width:9.5rem"
              type="date"
              value={lot.expires_on ?? ''}
              onchange={(event) =>
                desk.moveLot(lot.id, { expires_on: event.currentTarget.value || null })}
            />
          </div>
        {/each}
      </section>
    {/if}

    <section>
      <h3>Historique</h3>
      {#if desk.productHistory.length === 0}
        <p class="faint">Aucun mouvement enregistré.</p>
      {:else}
        {#each desk.productHistory as event (event.id)}
          <div class="checkline">
            <span class="grow">
              {KIND_LABEL[event.kind] ?? event.kind}
              {#if event.quantity}<span class="qty"> × {event.quantity}</span>{/if}
            </span>
            <span class="faint">{when(event.at)}</span>
          </div>
        {/each}
      {/if}
    </section>
  {:else}
    <!--
      Le contrat promet « le jour OU la sélection ». Sans sélection, c'est donc
      le jour qu'il faut montrer, éditable sur place — pas une invitation à
      cliquer ailleurs. Ces 336 px sont un quart du premier écran.
    -->
    <h2>Le jour</h2>
    <p class="muted" style="margin:.1rem 0 0">{aujourdhui}</p>

    {#if urgentLots.length === 0 && semaineLots.length === 0}
      <div class="empty" style="padding-top:2.5rem">
        <Icon name="check" size={36} />
        <p>Rien à consommer d'urgence. {conseilVue}</p>
      </div>
    {:else}
      {#if urgentLots.length > 0}
        <section>
          <h3 class="status-expired">Aujourd'hui et en retard · {urgentLots.length}</h3>
          {#each urgentLots as lot (lot.id)}
            <div class="checkline">
              <span class="dot bg-{lot.status}" aria-hidden="true"></span>
              <button class="grow truncate linkish-row" onclick={() => desk.focusProduct(lot.barcode)}>
                <span class="qty">{lot.quantity}</span> {lot.name}
              </button>
              <input
                class="inline-input"
                style="width:10.2rem"
                type="date"
                value={lot.expires_on ?? ''}
                onchange={(event) =>
                  desk.moveLot(lot.id, { expires_on: event.currentTarget.value || null })}
              />
            </div>
          {/each}
        </section>
      {/if}

      {#if semaineLots.length > 0}
        <section>
          <h3 class="status-soon">Cette semaine · {semaineLots.length}</h3>
          {#each semaineLots as lot (lot.id)}
            <div class="checkline">
              <span class="dot bg-{lot.status}" aria-hidden="true"></span>
              <button class="grow truncate linkish-row" onclick={() => desk.focusProduct(lot.barcode)}>
                <span class="qty">{lot.quantity}</span> {lot.name}
              </button>
              <span class="faint">{describeExpiry(lot.expires_on)}</span>
            </div>
          {/each}
        </section>
      {/if}

      <p class="faint" style="margin-top:1.2rem">{conseilVue}</p>
    {/if}
  {/if}
</aside>

<style>
  .linkish {
    color: var(--accent);
    padding: 0 0.25rem;
    font-size: inherit;
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  .empty p {
    max-width: 30ch;
    text-align: center;
  }

  .linkish-row {
    text-align: left;
    padding: 0;
    font: inherit;
    color: inherit;
  }

  .linkish-row:hover {
    color: var(--accent);
  }
</style>
