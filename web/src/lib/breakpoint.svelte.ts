/* Le basculement téléphone / PC.
 *
 * Structurel, pas typographique : les deux surfaces ont des métiers différents
 * (le téléphone capture, le PC corrige et donne la vue d'ensemble), donc on
 * change de composant, pas de taille de police.
 */

const DESKTOP_QUERY = '(min-width: 1024px)';

class Viewport {
  isDesktop = $state(false);

  constructor() {
    if (typeof window === 'undefined') return;
    const media = window.matchMedia(DESKTOP_QUERY);
    this.isDesktop = media.matches;
    media.addEventListener('change', (event) => {
      this.isDesktop = event.matches;
    });
  }
}

export const viewport = new Viewport();
