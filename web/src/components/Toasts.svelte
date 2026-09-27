<script lang="ts">
  import { app } from '../lib/state.svelte';
</script>

<div class="toasts" aria-live="polite">
  {#each app.toasts as toast (toast.id)}
    <div class="toast {toast.tone}">{toast.text}</div>
  {/each}
</div>
