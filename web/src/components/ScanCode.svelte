<script lang="ts">
  /* Un scanner plein écran qui ne fait qu'une chose : lire un code et le rendre.

     L'onglet Scanner range et consomme ; celui-ci sert à la recherche (journal,
     courses), où un code-barres n'est qu'une autre manière de nommer un
     aliment. La caméra s'ouvre d'elle-même et s'éteint dès la première lecture. */
  import Icon from '../lib/Icon.svelte';
  import {
    beep,
    closeCamera,
    messageCamera,
    openCamera,
    startScanning,
    vibrate,
    type ScanSession,
  } from '../lib/scanner';

  interface Props {
    titre: string;
    oncode: (code: string) => void;
    onclose: () => void;
  }

  let { titre, oncode, onclose }: Props = $props();

  let video: HTMLVideoElement | null = $state(null);
  let stream: MediaStream | null = null;
  let session: ScanSession | null = $state(null);
  let erreur = $state('');
  let saisie = $state('');

  function arreter() {
    session?.stop();
    session = null;
    closeCamera(stream);
    stream = null;
  }

  $effect(() => {
    if (!video) return;
    let annule = false;
    void (async () => {
      try {
        stream = await openCamera(video!);
        if (annule) return arreter();
        session = await startScanning(video!, lu);
      } catch (error) {
        erreur = messageCamera(error);
        arreter();
      }
    })();
    return () => {
      annule = true;
      arreter();
    };
  });

  function lu(code: string) {
    arreter();
    beep(true);
    vibrate(40);
    oncode(code);
  }

  function valider(event: Event) {
    event.preventDefault();
    const code = saisie.replace(/\D/g, '');
    if (code.length >= 8) lu(code);
  }
</script>

<div class="scan" role="dialog" aria-modal="true" aria-label={titre}>
  <header>
    <h2 class="grow">{titre}</h2>
    <button class="btn ghost icon-btn" onclick={onclose} aria-label="Fermer le scanner">
      <Icon name="close" />
    </button>
  </header>

  <div class="viewfinder" class:idle={!session}>
    <!-- svelte-ignore a11y_media_has_caption -->
    <video bind:this={video} muted playsinline></video>
    {#if session}
      <div class="reticle"></div>
    {:else}
      <div class="viewfinder-idle">
        <Icon name="scan" size={40} />
        <span>{erreur || 'Ouverture de la caméra…'}</span>
      </div>
    {/if}
  </div>

  <form class="row" onsubmit={valider}>
    <input
      class="grow"
      inputmode="numeric"
      autocomplete="off"
      placeholder="Ou tape le code-barres"
      aria-label="Code-barres"
      bind:value={saisie}
    />
    <button class="btn" disabled={saisie.replace(/\D/g, '').length < 8}>OK</button>
  </form>
</div>

<style>
  /* Au-dessus de la feuille de recherche qui l'a ouvert. */
  .scan {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: grid;
    grid-template-rows: auto minmax(0, 1fr) auto;
    gap: 0.8rem;
    padding: calc(0.8rem + env(safe-area-inset-top)) 1rem calc(1rem + env(safe-area-inset-bottom));
    background: var(--bg);
  }

  header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  h2 {
    margin: 0;
    font-size: 1.05rem;
  }

  .viewfinder {
    align-self: center;
    width: 100%;
    max-width: 30rem;
    max-height: 100%;
    margin: 0 auto;
  }
</style>
