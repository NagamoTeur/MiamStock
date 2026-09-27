<script lang="ts">
  import Icon from '../lib/Icon.svelte';
  import { api } from '../lib/api';
  import { grouperParRayon, rayonDe } from '../lib/rayons';
  import { app } from '../lib/state.svelte';
  import type { ShoppingItem } from '../lib/types';

  interface Props {
    onclose: () => void;
  }

  let { onclose }: Props = $props();
  let busy = $state(false);

  /* Groupé par rayon et non par ordre alphabétique : dans un magasin on suit un
     trajet, pas un index. Les lignes cochées restent en place, barrées — une
     liste qui se réorganise sous le pouce fait perdre le fil. */
  const groupes = $derived(
    grouperParRayon(app.shopping, (item: ShoppingItem) =>
      rayonDe(item.label, item.categories, item.location_kind),
    ),
  );

  const total = $derived(app.shopping.length);
  const pris = $derived(app.shopping.filter((item) => item.checked).length);

  async function basculer(item: ShoppingItem) {
    // Retour immédiat sous le pouce : le réseau confirme derrière.
    const avant = item.checked;
    item.checked = !avant;
    navigator.vibrate?.(15);
    const ok = await app.guard(() => api.patchShopping(item.id, { checked: !avant }));
    if (ok) await app.refreshShopping();
    else item.checked = avant;
  }

  async function terminer() {
    if (busy) return;
    busy = true;
    const result = await app.guard(() => api.clearChecked());
    busy = false;
    if (result) {
      app.toast(`${result.removed} article${result.removed > 1 ? 's' : ''} rentré${result.removed > 1 ? 's' : ''}`);
      await app.refreshShopping();
      onclose();
    }
  }
</script>

<div class="courses">
  <header>
    <button class="btn ghost icon-btn" onclick={onclose} aria-label="Quitter le mode courses">
      <Icon name="close" />
    </button>
    <div class="grow">
      <strong>Courses</strong>
      <div class="faint">{pris} sur {total}</div>
    </div>
    <div class="jauge" aria-hidden="true">
      <span style="transform:scaleX({total ? pris / total : 0})"></span>
    </div>
  </header>

  <div class="liste">
    {#each groupes as groupe (groupe.rayon.id)}
      <h2>{groupe.rayon.label}</h2>
      {#each groupe.items as item (item.id)}
        <button class="ligne" class:pris={item.checked} onclick={() => basculer(item)}>
          <span class="case" class:on={item.checked}>
            {#if item.checked}<Icon name="check" size={18} />{/if}
          </span>
          <span class="grow">
            <span class="nom">{item.label}</span>
            {#if item.brand}<span class="faint"> · {item.brand}</span>{/if}
          </span>
          {#if item.quantity > 1}<span class="qty">×{item.quantity}</span>{/if}
        </button>
      {/each}
    {/each}

    {#if total === 0}
      <div class="empty" style="padding-top:4rem">
        <Icon name="basket" size={44} />
        <p>Rien à acheter.</p>
      </div>
    {/if}
  </div>

  {#if pris > 0}
    <footer>
      <button class="btn primary block lg" onclick={terminer} disabled={busy}>
        {busy ? 'Enregistrement…' : `Retirer les ${pris} articles pris`}
      </button>
    </footer>
  {/if}
</div>

<style>
  /* Plein écran : dans un magasin, une main tient le chariot et l'écran ne doit
     rien montrer d'autre que la liste. */
  .courses {
    position: fixed;
    inset: 0;
    z-index: 70;
    background: var(--bg);
    display: grid;
    grid-template-rows: auto minmax(0, 1fr) auto;
  }

  header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: calc(env(safe-area-inset-top) + 0.6rem) 0.8rem 0.6rem;
    border-bottom: 1px solid var(--border);
  }

  .jauge {
    width: 72px;
    height: 5px;
    border-radius: 999px;
    background: var(--bg-input);
    overflow: hidden;
  }

  /* Mise à l'échelle plutôt que largeur animée : animer une propriété de mise
     en page force un recalcul du layout à chaque image. */
  .jauge span {
    display: block;
    width: 100%;
    height: 100%;
    background: var(--accent);
    transform-origin: left center;
    transition: transform 0.2s ease;
  }

  .liste {
    overflow-y: auto;
    padding: 0.4rem 0.8rem calc(1rem + env(safe-area-inset-bottom));
  }

  h2 {
    margin: 1.1rem 0 0.3rem;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--accent);
  }

  h2:first-child {
    margin-top: 0.5rem;
  }

  /* 60 px de haut : on vise avec le pouce, en marchant. */
  .ligne {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    width: 100%;
    min-height: 60px;
    padding: 0.5rem 0.2rem;
    text-align: left;
    border-bottom: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
    font-size: 1.02rem;
  }

  .ligne:active {
    background: color-mix(in srgb, var(--accent) 10%, transparent);
  }

  .ligne.pris .nom {
    text-decoration: line-through;
    color: var(--text-faint);
  }

  .case {
    width: 30px;
    height: 30px;
    flex: none;
    border-radius: 9px;
    border: 1.5px solid var(--border);
    background: var(--bg-input);
    display: grid;
    place-items: center;
  }

  .case.on {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--accent-ink);
  }

  footer {
    padding: 0.7rem 0.8rem calc(0.7rem + env(safe-area-inset-bottom));
    border-top: 1px solid var(--border);
    background: var(--bg-elevated);
  }

  .empty {
    display: grid;
    justify-items: center;
    gap: 0.5rem;
    color: var(--text-dim);
  }
</style>
