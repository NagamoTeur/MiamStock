<script lang="ts">
  import { app } from '../lib/state.svelte';

  let pin = $state('');
  let busy = $state(false);
  let failed = $state(false);

  async function submit(event: Event) {
    event.preventDefault();
    if (!pin.trim() || busy) return;
    busy = true;
    failed = false;
    const ok = await app.login(pin.trim());
    busy = false;
    if (ok) {
      pin = '';
    } else {
      failed = true;
      pin = '';
    }
  }
</script>

<div class="shell" style="display:grid; place-items:center; min-height:100vh">
  <form class="card" style="width:100%; max-width:340px" onsubmit={submit}>
    <div style="text-align:center; margin-bottom:1rem">
      <img src="/icon-192.png" alt="" width="64" height="64" style="border-radius:16px" />
      <h1 style="font-size:1.25rem; margin:.6rem 0 .1rem">MiamStock</h1>
      <p class="muted" style="margin:0">Code du foyer</p>
    </div>

    <input
      type="password"
      inputmode="numeric"
      autocomplete="current-password"
      placeholder="••••"
      bind:value={pin}
      style="text-align:center; letter-spacing:.3em; font-size:1.3rem"
    />

    {#if failed}
      <p class="muted status-expired" style="text-align:center; margin:.6rem 0 0">
        Code incorrect
      </p>
    {/if}

    <button class="btn primary block lg" style="margin-top:.9rem" disabled={busy || !pin.trim()}>
      {busy ? 'Vérification…' : 'Entrer'}
    </button>
  </form>
</div>
