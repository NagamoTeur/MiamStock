<script lang="ts">
  import { api } from '../lib/api';
  import {
    beep,
    closeCamera,
    openCamera,
    secureContextOk,
    startScanning,
    vibrate,
    type ScanSession,
  } from '../lib/scanner';
  import { app } from '../lib/state.svelte';
  import type { Lookup } from '../lib/types';
  import ScanSheet from './ScanSheet.svelte';

  let video: HTMLVideoElement | null = $state(null);
  let stream: MediaStream | null = null;
  let session: ScanSession | null = $state(null);
  let engine = $state<'native' | 'zxing' | null>(null);
  let cameraError = $state('');
  let starting = $state(false);

  let manualCode = $state('');
  let pending = $state<Lookup | null>(null);
  let looking = $state(false);

  /** Mémorisé entre les sessions : vider le frigo est un enchaînement de sorties. */
  let defaultMode = $state<'in' | 'out'>(
    (localStorage.getItem('miamstock.mode') as 'in' | 'out') ?? 'in',
  );

  $effect(() => {
    localStorage.setItem('miamstock.mode', defaultMode);
  });

  async function start() {
    if (starting || session || !video) return;
    starting = true;
    cameraError = '';
    try {
      stream = await openCamera(video);
      session = await startScanning(video, handleCode);
      engine = session.engine;
    } catch (error) {
      cameraError = (error as Error).message;
      stop();
    } finally {
      starting = false;
    }
  }

  function stop() {
    session?.stop();
    session = null;
    closeCamera(stream);
    stream = null;
    engine = null;
  }

  async function handleCode(code: string) {
    // La détection est suspendue pendant la saisie : sinon le même emballage
    // encore devant l'objectif rouvrirait la feuille en boucle.
    session?.stop();
    session = null;
    beep(true);
    vibrate(40);
    await resolve(code);
  }

  async function resolve(code: string) {
    looking = true;
    const lookup = await app.guard(() => api.lookup(code));
    looking = false;
    if (!lookup) {
      await resumeScanning();
      return;
    }
    if (!lookup.found) {
      beep(false);
      vibrate([25, 60, 25]);
    }
    pending = lookup;
  }

  async function resumeScanning() {
    if (!video || !stream || session) return;
    session = await startScanning(video, handleCode);
    engine = session.engine;
  }

  async function closeSheet() {
    pending = null;
    await resumeScanning();
  }

  async function submitManual(event: Event) {
    event.preventDefault();
    const code = manualCode.replace(/\D/g, '');
    if (code.length < 8) {
      app.toast('Un code-barres fait au moins 8 chiffres', 'warn');
      return;
    }
    manualCode = '';
    await resolve(code);
  }

  // Libère la caméra dès qu'on quitte l'onglet : un voyant qui reste allumé
  // inquiète, et le flux consomme de la batterie pour rien.
  $effect(() => () => stop());
</script>

<div class="stack">
  <div class="seg">
    <button class:on={defaultMode === 'in'} onclick={() => (defaultMode = 'in')}>
      Je range
    </button>
    <button class:on={defaultMode === 'out'} onclick={() => (defaultMode = 'out')}>
      Je consomme
    </button>
  </div>

  {#if !secureContextOk()}
    <div class="banner">
      Cette page n'est pas en HTTPS : le navigateur refuse l'accès à la caméra. Passe par
      l'adresse sécurisée (Tailscale) ou saisis le code à la main ci-dessous.
    </div>
  {/if}

  <div class="viewfinder" class:idle={!session}>
    <!-- svelte-ignore a11y_media_has_caption -->
    <video bind:this={video} muted playsinline></video>
    {#if session}
      <div class="reticle"></div>
      <span class="engine-tag">
        {engine === 'native' ? 'décodeur natif' : 'décodeur ZXing'}
      </span>
    {:else}
      <div class="viewfinder-idle">
        <span class="big" aria-hidden="true">⌷</span>
        <span>Vise le code-barres, le produit se remplit tout seul</span>
      </div>
    {/if}
  </div>

  {#if cameraError}
    <div class="banner">{cameraError}</div>
  {/if}

  {#if session}
    <button class="btn block" onclick={stop}>Arrêter la caméra</button>
  {:else}
    <button class="btn primary block lg" onclick={start} disabled={starting || looking}>
      {starting ? 'Ouverture de la caméra…' : looking ? 'Recherche…' : 'Scanner un code-barres'}
    </button>
  {/if}

  <form class="card" onsubmit={submitManual}>
    <div class="muted" style="margin-bottom:.5rem">Saisie manuelle</div>
    <div class="row">
      <input
        class="grow"
        inputmode="numeric"
        autocomplete="off"
        placeholder="3017620422003"
        bind:value={manualCode}
      />
      <button class="btn" disabled={looking}>OK</button>
    </div>
    <p class="faint" style="margin:.6rem 0 0">
      Utile pour le vrac et les fruits et légumes : n'importe quel code fera l'affaire, ou
      crée l'article avec un nom libre.
    </p>
  </form>

  {#if app.summary}
    <div class="kpis">
      <div class="kpi">
        <div class="n">{app.summary.total_items}</div>
        <div class="l">articles</div>
      </div>
      <div class="kpi">
        <div class="n status-urgent">{app.summary.expired + app.summary.urgent}</div>
        <div class="l">à consommer vite</div>
      </div>
      <div class="kpi">
        <div class="n">{app.summary.shopping_open}</div>
        <div class="l">à acheter</div>
      </div>
    </div>
  {/if}
</div>

{#if pending}
  <ScanSheet lookup={pending} initialMode={defaultMode} onclose={closeSheet} />
{/if}
