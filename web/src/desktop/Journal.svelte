<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import type { IconName } from '../lib/icons';
  import { desk } from '../lib/desktop.svelte';

  let kindFilter = $state<string | 'all'>('all');

  const KINDS: { value: string; label: string; icon: IconName }[] = [
    { value: 'in', label: 'Entrées', icon: 'plus' },
    { value: 'out', label: 'Sorties', icon: 'minus' },
    { value: 'discard', label: 'Jetés', icon: 'trash' },
    { value: 'adjust', label: 'Corrections', icon: 'pencil' },
  ];

  const LABEL: Record<string, string> = {
    in: 'Entré en stock',
    out: 'Sorti du stock',
    discard: 'Jeté',
    adjust: 'Corrigé',
    shopping_auto: 'Ajouté aux courses',
    shopping_clear: 'Liste de courses vidée',
  };

  const rows = $derived(
    kindFilter === 'all' ? desk.history : desk.history.filter((e) => e.kind === kindFilter),
  );

  const stats = $derived(desk.stats);
  const wastePercent = $derived(stats ? Math.round(stats.waste_ratio * 100) : 0);

  function when(iso: string): string {
    return new Intl.DateTimeFormat('fr-FR', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso));
  }
</script>

<div class="journal">
  {#if stats}
    <!--
      Pas de bande de tuiles : quatre cartes « grand chiffre, petit libellé »
      sont le gabarit que le plancher refuse comme structure de page, et la
      substance de cette vue est le relevé, pas le résumé. Une phrase dit les
      mêmes nombres, et la proportion ne se dessine que s'il y a matière.
    -->
    <div class="bilan">
      <p class="phrase">
        Sur {stats.days} jours : <b>{stats.entered}</b> article{stats.entered > 1 ? 's' : ''}
        rentré{stats.entered > 1 ? 's' : ''}, <b class="status-ok">{stats.consumed}</b>
        consommé{stats.consumed > 1 ? 's' : ''},
        <b class="status-expired">{stats.discarded}</b> jeté{stats.discarded > 1 ? 's' : ''}.
      </p>

      {#if stats.discarded > 0}
        <div class="proportion" aria-hidden="true">
          <span class="part-ok" style="flex:{stats.consumed}"></span>
          <span class="part-perdu" style="flex:{stats.discarded}"></span>
        </div>
        <p class="phrase secondaire">
          <b class="status-expired">{wastePercent}&#8239;%</b> de ce qui sort du stock
          finit à la poubelle.
          {#if stats.most_wasted.length > 0}
            Surtout {stats.most_wasted
              .slice(0, 3)
              .map((product) => product.name)
              .join(', ')}.
          {/if}
        </p>
      {:else}
        <p class="phrase secondaire">Rien n'a été jeté sur la période.</p>
      {/if}
    </div>
  {/if}

  <div class="toolbar">
    <div class="chips">
      <button class="chip" class:on={kindFilter === 'all'} onclick={() => (kindFilter = 'all')}>
        Tout
      </button>
      {#each KINDS as kind (kind.value)}
        <button
          class="chip"
          class:on={kindFilter === kind.value}
          onclick={() => (kindFilter = kind.value)}
        >
          <Icon name={kind.icon} size={13} />
          {kind.label}
        </button>
      {/each}
    </div>
    <span class="faint">{rows.length} mouvement{rows.length > 1 ? 's' : ''}</span>
  </div>

  <div class="table-wrap">
    <table class="grid">
      <thead>
        <tr>
          <th style="width:16rem">Quand</th>
          <th>Mouvement</th>
          <th>Produit</th>
          <th class="num">Quantité</th>
        </tr>
      </thead>
      <tbody>
        {#each rows as event (event.id)}
          <tr>
            <td class="faint">{when(event.at)}</td>
            <td>
              <span class="dot bg-{event.kind === 'discard' ? 'expired' : event.kind === 'out' ? 'soon' : 'ok'}"></span>
              {LABEL[event.kind] ?? event.kind}
            </td>
            <td class="truncate" style="max-width:26ch">{event.name ?? event.barcode ?? '—'}</td>
            <td class="num">{event.quantity ?? '—'}</td>
          </tr>
        {/each}
      </tbody>
    </table>

    {#if rows.length === 0}
      <div class="empty">
        <Icon name="clock" size={40} />
        <p>Aucun mouvement de ce type.</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .journal {
    display: grid;
    grid-template-rows: auto auto minmax(0, 1fr);
    height: 100%;
  }

  .bilan {
    padding: 1.1rem 1.1rem 0;
    max-width: 62ch;
  }

  .phrase {
    margin: 0;
    font-size: 1.02rem;
    line-height: 1.55;
    color: var(--text-dim);
  }

  .phrase b {
    color: var(--text);
    font-variant-numeric: tabular-nums;
    font-weight: 650;
  }

  .phrase.secondaire {
    margin-top: 0.5rem;
    font-size: 0.88rem;
  }

  /* Une proportion réelle entre consommé et jeté, affichée seulement quand il
     y a quelque chose à proportionner. */
  .proportion {
    display: flex;
    height: 7px;
    margin-top: 0.8rem;
    border-radius: 999px;
    overflow: hidden;
    background: var(--bg-input);
  }

  .part-ok {
    background: var(--ok);
  }

  .part-perdu {
    background: var(--expired);
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    padding: 1rem 0.9rem 0.6rem;
    border-bottom: 1px solid var(--border);
    color: var(--text-dim);
  }

  .dot {
    display: inline-block;
    margin-right: 0.45rem;
    vertical-align: 1px;
  }

  .empty {
    display: grid;
    justify-items: center;
    gap: 0.5rem;
    padding: 3rem 1rem;
    color: var(--text-dim);
  }
</style>
