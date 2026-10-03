<script lang="ts">
  import Icon from './lib/Icon.svelte';
  import ExpiringView from './components/ExpiringView.svelte';
  import JournalView from './components/JournalView.svelte';
  import Login from './components/Login.svelte';
  import ScanView from './components/ScanView.svelte';
  import SettingsView from './components/SettingsView.svelte';
  import ShoppingView from './components/ShoppingView.svelte';
  import StockView from './components/StockView.svelte';
  import Tabbar from './components/Tabbar.svelte';
  import Toasts from './components/Toasts.svelte';
  import { app } from './lib/state.svelte';
  import { viewport } from './lib/breakpoint.svelte';
  import DesktopShell from './desktop/DesktopShell.svelte';

  const TITLES = {
    scan: 'Scanner',
    stock: 'Stock',
    expiring: 'À consommer',
    journal: 'Journal',
    shopping: 'Courses',
    settings: 'Réglages',
  } as const;

  void app.bootstrap();

  // Revenir sur l'app après un moment doit montrer l'état réel, pas un stock figé
  // depuis la veille : les DLC se rapprochent même quand l'onglet est en arrière-plan.
  $effect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible' && app.authenticated) void app.refreshAll();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  });

  const subtitle = $derived.by(() => {
    if (!app.summary) return '';
    if (app.tab === 'stock') {
      return `${app.summary.total_items} articles · ${app.summary.distinct_products} produits en stock`;
    }
    if (app.tab === 'expiring') {
      return `${app.summary.expired} périmés · ${app.summary.urgent} urgents`;
    }
    if (app.tab === 'shopping') return `${app.summary.shopping_open} à acheter`;
    return '';
  });
</script>

{#if !app.ready}
  <div class="empty" style="padding-top:35vh">Chargement…</div>
{:else if app.authRequired && !app.authenticated}
  <Login />
{:else if viewport.isDesktop}
  <!-- Le PC ne scanne pas : il corrige, saisit au clavier et donne la vue d'ensemble. -->
  <DesktopShell />
{:else}
  <div class="shell">
    <header class="topbar">
      <div>
        <h1>{TITLES[app.tab]}</h1>
        {#if subtitle}<div class="sub">{subtitle}</div>{/if}
      </div>
      <button class="btn ghost icon-btn" onclick={() => app.refreshAll()} aria-label="Rafraîchir">
        <Icon name="refresh" />
      </button>
    </header>

    {#if app.offline}
      <div class="banner">
        Serveur injoignable. Tu peux consulter ce qui est déjà chargé, mais aucun bip ne sera
        enregistré.
      </div>
    {/if}

    {#if app.tab === 'scan'}
      <ScanView />
    {:else if app.tab === 'stock'}
      <StockView />
    {:else if app.tab === 'expiring'}
      <ExpiringView />
    {:else if app.tab === 'journal'}
      <JournalView />
    {:else if app.tab === 'shopping'}
      <ShoppingView />
    {:else}
      <SettingsView />
    {/if}
  </div>

  <Tabbar />
{/if}

<Toasts />
