<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import { app } from '../lib/state.svelte';
  import type { Tab } from '../lib/state.svelte';
  import type { IconName } from '../lib/icons';

  const tabs: { id: Tab; icon: IconName; label: string }[] = [
    { id: 'scan', icon: 'scan', label: 'Scan' },
    { id: 'stock', icon: 'crate', label: 'Stock' },
    { id: 'journal', icon: 'utensils', label: 'Journal' },
    { id: 'shopping', icon: 'basket', label: 'Courses' },
    { id: 'settings', icon: 'sliders', label: 'Réglages' },
  ];

  function badgeFor(tab: Tab): number {
    if (tab === 'stock') return app.alertCount;
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
      <span class="icon"><Icon name={tab.icon} size={22} /></span>
      <span>{tab.label}</span>
      {#if badge > 0}
        <span class="badge">{badge > 99 ? '99+' : badge}</span>
      {/if}
    </button>
  {/each}
</nav>
