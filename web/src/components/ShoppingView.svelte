<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import { api } from '../lib/api';
  import { app } from '../lib/state.svelte';

  let newLabel = $state('');
  let busy = $state(false);

  const open = $derived(app.shopping.filter((item) => !item.checked));
  const done = $derived(app.shopping.filter((item) => item.checked));

  async function add(event: Event) {
    event.preventDefault();
    const label = newLabel.trim();
    if (!label || busy) return;
    busy = true;
    const item = await app.guard(() => api.addShopping({ label, quantity: 1 }));
    if (item) {
      newLabel = '';
      await app.refreshShopping();
    }
    busy = false;
  }

  async function toggle(id: number, checked: boolean) {
    await app.guard(() => api.patchShopping(id, { checked }));
    await app.refreshShopping();
  }

  async function setQuantity(id: number, quantity: number) {
    if (quantity < 1) return;
    await app.guard(() => api.patchShopping(id, { quantity }));
    await app.refreshShopping();
  }

  async function remove(id: number) {
    await app.guard(() => api.deleteShopping(id));
    await app.refreshShopping();
  }

  async function clearChecked() {
    const result = await app.guard(() => api.clearChecked());
    if (result) app.toast(`${result.removed} ligne(s) retirée(s)`);
    await app.refreshShopping();
  }

  /** Partage natif : le plus court chemin vers la liste dans la poche de quelqu'un d'autre. */
  async function share() {
    const text = open.map((item) => `- ${item.quantity} × ${item.label}`).join('\n');
    if (!text) return;
    const payload = { title: 'Liste de courses', text };
    if (navigator.share) {
      try {
        await navigator.share(payload);
        return;
      } catch {
        /* Partage annulé : on retombe sur le presse-papiers. */
      }
    }
    await navigator.clipboard?.writeText(text);
    app.toast('Liste copiée');
  }
</script>

<div class="stack">
  <form class="row" onsubmit={add}>
    <input
      class="grow"
      placeholder="Ajouter un article (pain, œufs…)"
      bind:value={newLabel}
      autocomplete="off"
    />
    <button
      class="btn primary icon-btn"
      disabled={busy || !newLabel.trim()}
      aria-label="Ajouter à la liste"
    >
      <Icon name="plus" />
    </button>
  </form>

  {#if app.shopping.length === 0}
    <div class="empty">
      <Icon name="basket" size={44} />
      Liste vide. Elle se remplira toute seule quand un produit sera épuisé ou passera sous
      son seuil.
    </div>
  {:else}
    <div class="card">
      {#each open as item (item.id)}
        <div class="checkline">
          <button class="tick" onclick={() => toggle(item.id, true)} aria-label="Cocher"></button>
          <div class="grow">
            <div class="label truncate">{item.label}</div>
            <div class="faint truncate">
              {[item.brand, item.auto ? 'ajouté automatiquement' : null]
                .filter(Boolean)
                .join(' · ')}
            </div>
          </div>
          <div class="stepper">
            <button
              onclick={() => setQuantity(item.id, item.quantity - 1)}
              style="width:32px; height:32px"
              aria-label="Moins un"
            >
              <Icon name="minus" size={15} />
            </button>
            <span class="value" style="font-size:1rem">{item.quantity}</span>
            <button
              onclick={() => setQuantity(item.id, item.quantity + 1)}
              style="width:32px; height:32px"
              aria-label="Plus un"
            >
              <Icon name="plus" size={15} />
            </button>
          </div>
          <button
            class="btn ghost danger"
            style="min-height:32px; padding:0 .5rem"
            onclick={() => remove(item.id)}
            aria-label="Retirer"
          >
            <Icon name="close" size={16} />
          </button>
        </div>
      {/each}

      {#if done.length}
        {#each done as item (item.id)}
          <div class="checkline done">
            <button
              class="tick on"
              onclick={() => toggle(item.id, false)}
              aria-label="Décocher"
            >
              <Icon name="check" size={16} />
            </button>
            <div class="grow label truncate">{item.quantity} × {item.label}</div>
          </div>
        {/each}
      {/if}
    </div>

    <div class="row">
      <button class="btn grow" onclick={share} disabled={open.length === 0}>Partager</button>
      {#if done.length}
        <button class="btn grow" onclick={clearChecked}>
          Vider les {done.length} cochés
        </button>
      {/if}
    </div>
  {/if}
</div>
