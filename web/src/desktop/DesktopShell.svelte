<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import type { IconName } from '../lib/icons';
  import { desk, type DesktopView } from '../lib/desktop.svelte';
  import { app } from '../lib/state.svelte';
  import Catalogue from './Catalogue.svelte';
  import CommandBar from './CommandBar.svelte';
  import Frise from './Frise.svelte';
  import Journal from './Journal.svelte';
  import Registre from './Registre.svelte';
  import SidePanel from './SidePanel.svelte';
  import './desktop.css';

  const VIEWS: { id: DesktopView; icon: IconName; label: string; title: string }[] = [
    { id: 'frise', icon: 'clock', label: 'Frise', title: 'La frise des dates' },
    { id: 'registre', icon: 'crate', label: 'Registre', title: 'Registre des lots' },
    { id: 'catalogue', icon: 'jar', label: 'Catalogue', title: 'Catalogue des produits' },
    { id: 'journal', icon: 'list', label: 'Journal', title: 'Journal et gaspillage' },
  ];

  const current = $derived(VIEWS.find((view) => view.id === desk.view)!);
  const hasPanel = $derived(desk.view === 'frise' || desk.view === 'registre' || desk.view === 'catalogue');

  function onkeydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement | null;
    const typing =
      target && ['INPUT', 'SELECT', 'TEXTAREA'].includes(target.tagName);

    if ((event.key === '/' && !typing) || (event.key === 'k' && (event.metaKey || event.ctrlKey))) {
      event.preventDefault();
      desk.commandOpen = true;
      return;
    }
    if (event.key === 'Escape' && !desk.commandOpen && !typing) {
      desk.clearSelection();
    }
    if (!typing && !event.metaKey && !event.ctrlKey) {
      const index = Number(event.key) - 1;
      if (index >= 0 && index < VIEWS.length) void desk.setView(VIEWS[index]!.id);
    }
  }

  const subtitle = $derived.by(() => {
    if (!app.summary) return '';
    if (desk.view === 'journal') return `${app.summary.total_items} articles en stock`;
    return `${app.summary.total_items} articles · ${app.summary.distinct_products} produits en stock${
      app.alertCount ? ` · ${app.alertCount} à consommer` : ''
    }`;
  });
</script>

<svelte:window onkeydown={onkeydown} />

<div class="desk">
  <nav class="rail" aria-label="Vues">
    <div class="rail-mark"><img src="/icon-192.png" alt="MiamStock" /></div>
    {#each VIEWS as view (view.id)}
      <button
        class:on={desk.view === view.id}
        onclick={() => desk.setView(view.id)}
        aria-current={desk.view === view.id ? 'page' : undefined}
      >
        <Icon name={view.icon} size={20} />
        <span>{view.label}</span>
      </button>
    {/each}

    <div class="spacer"></div>

    <button onclick={() => (desk.commandOpen = true)} title="Saisie rapide — touche /">
      <Icon name="keyboard" size={20} />
      <span>Saisir</span>
    </button>
    <button onclick={() => app.refreshAll()} title="Rafraîchir">
      <Icon name="refresh" size={20} />
      <span>Rafraîchir</span>
    </button>
  </nav>

  <div class="desk-main">
    <header class="desk-top">
      <div class="grow">
        <h1>{current.title}</h1>
        {#if subtitle}<div class="sub">{subtitle}</div>{/if}
      </div>

      {#if app.summary && app.summary.shopping_open > 0}
        <span class="chip"><Icon name="basket" size={14} /> {app.summary.shopping_open} à acheter</span>
      {/if}

      <button class="btn" onclick={() => (desk.commandOpen = true)}>
        <Icon name="keyboard" size={16} />
        Saisir
        <kbd style="margin-left:.35rem">/</kbd>
      </button>
    </header>

    {#if app.offline}
      <div class="banner stacked" style="margin:.7rem .9rem 0">
        Serveur injoignable. Rien ne sera enregistré tant que la connexion n'est pas revenue.
      </div>
    {/if}

    <div class="desk-body" class:wide={!hasPanel}>
      <div class="desk-view">
        {#if desk.view === 'frise'}
          <Frise />
        {:else if desk.view === 'registre'}
          <Registre />
        {:else if desk.view === 'catalogue'}
          <Catalogue />
        {:else}
          <Journal />
        {/if}

        {#if desk.selected.size > 0}
          <div class="bulkbar" role="toolbar" aria-label="Actions groupées">
            <span class="n">{desk.selected.size} sélectionné{desk.selected.size > 1 ? 's' : ''}</span>
            <button class="btn" onclick={() => desk.bulk('consume')} disabled={desk.busy}>
              <Icon name="minus" size={15} /> Sortir
            </button>
            <select
              class="btn"
              style="width:auto; padding:0 .6rem"
              onchange={(event) => {
                const value = event.currentTarget.value;
                if (!value) return;
                void desk.bulk('move', { location_id: value === 'null' ? null : Number(value) });
                event.currentTarget.value = '';
              }}
            >
              <option value="">Déplacer vers…</option>
              {#each app.locations as location (location.id)}
                <option value={location.id}>{location.name}</option>
              {/each}
              <option value="null">Non rangé</option>
            </select>
            <button class="btn danger" onclick={() => desk.bulk('discard')} disabled={desk.busy}>
              <Icon name="trash" size={15} /> Jeter
            </button>
            <button class="btn ghost icon-btn" onclick={() => desk.clearSelection()} aria-label="Annuler la sélection">
              <Icon name="close" size={16} />
            </button>
          </div>
        {/if}
      </div>

      {#if hasPanel}
        <SidePanel />
      {/if}
    </div>
  </div>
</div>

{#if desk.commandOpen}
  <CommandBar onclose={() => (desk.commandOpen = false)} />
{/if}
