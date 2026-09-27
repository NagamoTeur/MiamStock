<script lang="ts">
  import { ICONS, type IconName } from './icons';

  interface Props {
    name: IconName;
    size?: number;
    /** Décoratif par défaut : un libellé visible accompagne presque toujours l'icône. */
    label?: string;
  }

  let { name, size = 20, label }: Props = $props();
  const paths = $derived(ICONS[name]);
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="1.7"
  stroke-linecap="round"
  stroke-linejoin="round"
  role={label ? 'img' : 'presentation'}
  aria-hidden={label ? undefined : 'true'}
  aria-label={label}
>
  {#each paths as d (d)}
    <path {d} />
  {/each}
</svg>
