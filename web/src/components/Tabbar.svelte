<script lang="ts">
  import { app } from '../lib/state.svelte';
  import type { Tab } from '../lib/state.svelte';

  const tabs: { id: Tab; icon: string; label: string }[] = [
    { id: 'scan', icon: '⌷', label: 'Scan' },
    { id: 'stock', icon: '▦', label: 'Stock' },
    { id: 'expiring', icon: '⏳', label: 'DLC' },
    { id: 'shopping', icon: '🛒', label: 'Courses' },
    { id: 'settings', icon: '⚙', label: 'Réglages' },
  ];

  function badgeFor(tab: Tab): number {
    if (tab === 'expiring') return app.alertCount;
    if (tab === 'shopping') return app.summary?.shopping_open ?? 0;
    return 0;
  }
</script>

<nav class="tabbar">
  {#each tabs as tab (tab.id)}
    {@const badge = badgeFor(tab.id)}
    <button
      class:on={app.tab === tab.id}
      onclick={() => app.setTab(tab.id)}
      aria-current={app.tab === tab.id ? 'page' : undefined}
    >
      <span class="icon" aria-hidden="true">{tab.icon}</span>
      <span>{tab.label}</span>
      {#if badge > 0}
        <span class="badge">{badge > 99 ? '99+' : badge}</span>
      {/if}
    </button>
  {/each}
</nav>
