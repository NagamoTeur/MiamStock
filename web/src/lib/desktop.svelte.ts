/* État propre à la surface PC.
 *
 * Volontairement séparé de `state.svelte.ts` : le téléphone n'a ni sélection
 * multiple, ni vue courante, ni catalogue chargé, et lui imposer ce poids
 * ralentirait le seul écran où la vitesse compte vraiment.
 */

import { api } from './api';
import { app } from './state.svelte';
import type { CatalogEntry, HistoryEntry, Lot, StockLine, Stats } from './types';

export type DesktopView = 'frise' | 'registre' | 'catalogue' | 'journal' | 'repas';

/** Un lot aplati avec son produit : la frise et le registre manipulent ça. */
export interface FlatLot extends Lot {
  barcode: string;
  name: string;
  brand: string | null;
  image_url: string | null;
  net_quantity: string | null;
}

export function flatten(lines: StockLine[]): FlatLot[] {
  return lines.flatMap((line) =>
    line.lots.map((lot) => ({
      ...lot,
      barcode: line.product.barcode,
      name: line.product.name,
      brand: line.product.brand,
      image_url: line.product.image_url,
      net_quantity: line.product.net_quantity,
    })),
  );
}

class DesktopState {
  view = $state<DesktopView>('frise');

  /** Sélection multiple par identifiant de lot : la barre d'actions groupées en dépend. */
  selected = $state<Set<number>>(new Set());
  /** Le produit ouvert dans le panneau latéral, s'il y en a un. */
  focusedBarcode = $state<string | null>(null);

  catalog = $state<CatalogEntry[]>([]);
  history = $state<HistoryEntry[]>([]);
  stats = $state<Stats | null>(null);
  productHistory = $state<HistoryEntry[]>([]);

  commandOpen = $state(false);
  busy = $state(false);

  get lots(): FlatLot[] {
    return flatten(app.stock);
  }

  get selectedLots(): FlatLot[] {
    return this.lots.filter((lot) => this.selected.has(lot.id));
  }

  get focusedLine(): StockLine | null {
    if (!this.focusedBarcode) return null;
    return app.stock.find((line) => line.product.barcode === this.focusedBarcode) ?? null;
  }

  /** Les Set ne sont pas réactifs en profondeur : on remplace, on ne mute pas. */
  private replaceSelection(next: Set<number>) {
    this.selected = next;
  }

  toggle(lotId: number, additive: boolean) {
    const next = additive ? new Set(this.selected) : new Set<number>();
    if (additive && this.selected.has(lotId)) next.delete(lotId);
    else next.add(lotId);
    this.replaceSelection(next);
  }

  selectOnly(lotIds: number[]) {
    this.replaceSelection(new Set(lotIds));
  }

  clearSelection() {
    this.replaceSelection(new Set());
  }

  isSelected(lotId: number): boolean {
    return this.selected.has(lotId);
  }

  async setView(view: DesktopView) {
    this.view = view;
    this.clearSelection();
    if (view === 'catalogue') await this.loadCatalog();
    if (view === 'journal') await this.loadJournal();
  }

  async loadCatalog(q?: string) {
    const rows = await app.guard(() => api.catalog(q ? { q } : {}));
    if (rows) this.catalog = rows;
  }

  async loadJournal() {
    const result = await app.guard(() =>
      Promise.all([api.history({ limit: 200 }), api.stats(90)]),
    );
    if (!result) return;
    [this.history, this.stats] = result;
  }

  async focusProduct(barcode: string | null) {
    this.focusedBarcode = barcode;
    this.productHistory = [];
    if (!barcode) return;
    const rows = await app.guard(() => api.history({ barcode, limit: 40 }));
    if (rows) this.productHistory = rows;
  }

  /** Déplace un lot dans le temps et/ou d'emplacement — le geste signature de la frise. */
  async moveLot(lotId: number, changes: { expires_on?: string | null; location_id?: number | null }) {
    const body: Record<string, unknown> = {};
    if ('expires_on' in changes) {
      if (changes.expires_on) body.expires_on = changes.expires_on;
      else body.clear_expiry = true;
    }
    if ('location_id' in changes) body.location_id = changes.location_id;

    this.busy = true;
    const updated = await app.guard(() => api.patchLot(lotId, body));
    this.busy = false;
    if (updated) await app.refreshStock();
    return updated;
  }

  /** Corrige la quantité d'un lot ; zéro le supprime, côté serveur. */
  async setLotQuantity(lotId: number, quantity: number) {
    if (!Number.isFinite(quantity) || quantity < 0) return;
    this.busy = true;
    const updated = await app.guard(() => api.patchLot(lotId, { quantity }));
    this.busy = false;
    if (updated) await app.refreshStock();
  }

  /** Applique une action à toute la sélection, en série pour rester lisible côté serveur. */
  async bulk(action: 'discard' | 'consume' | 'move', payload?: { location_id?: number | null }) {
    const lots = this.selectedLots;
    if (lots.length === 0) return;

    this.busy = true;
    let done = 0;
    for (const lot of lots) {
      const result = await app.guard(async () => {
        if (action === 'discard') return api.deleteLot(lot.id);
        if (action === 'consume') {
          return api.stockOut({ barcode: lot.barcode, quantity: lot.quantity, add_to_shopping: true });
        }
        return api.patchLot(lot.id, { location_id: payload?.location_id ?? null });
      });
      if (result !== null) done += 1;
    }
    this.busy = false;

    const verbe = { discard: 'jeté', consume: 'sorti', move: 'déplacé' }[action];
    app.toast(`${done} lot${done > 1 ? 's' : ''} ${verbe}${done > 1 ? 's' : ''}`);
    this.clearSelection();
    await Promise.all([app.refreshStock(), app.refreshShopping()]);
  }
}

export const desk = new DesktopState();
