import { ApiError, OfflineError, api } from './api';
import type { Location, ShoppingItem, StockLine, Summary } from './types';

export type Tab = 'scan' | 'stock' | 'expiring' | 'shopping' | 'settings';

export interface Toast {
  id: number;
  text: string;
  tone: 'ok' | 'warn' | 'error';
}

let toastSeq = 0;

class AppState {
  ready = $state(false);
  authenticated = $state(false);
  authRequired = $state(true);
  offline = $state(false);

  tab = $state<Tab>('scan');
  locations = $state<Location[]>([]);
  summary = $state<Summary | null>(null);
  stock = $state<StockLine[]>([]);
  expiring = $state<StockLine[]>([]);
  shopping = $state<ShoppingItem[]>([]);

  stockFilter = $state<number | null>(null);
  stockQuery = $state('');
  toasts = $state<Toast[]>([]);

  /** Dernier emplacement utilisé : réutilisé comme défaut du prochain bip d'entrée. */
  lastLocationId = $state<number | null>(null);

  constructor() {
    const saved = localStorage.getItem('miamstock.lastLocation');
    if (saved) this.lastLocationId = Number(saved);
  }

  toast(text: string, tone: Toast['tone'] = 'ok') {
    const item: Toast = { id: ++toastSeq, text, tone };
    this.toasts = [...this.toasts, item];
    setTimeout(() => {
      this.toasts = this.toasts.filter((candidate) => candidate.id !== item.id);
    }, tone === 'error' ? 5000 : 2800);
  }

  /** Enveloppe tous les appels : distingue « hors ligne » de « session expirée ». */
  async guard<T>(action: () => Promise<T>, failureText?: string): Promise<T | null> {
    try {
      const result = await action();
      this.offline = false;
      return result;
    } catch (error) {
      if (error instanceof OfflineError) {
        this.offline = true;
        this.toast('Hors ligne — le bip n’a pas été enregistré', 'error');
        return null;
      }
      if (error instanceof ApiError && error.status === 401) {
        this.authenticated = false;
        return null;
      }
      this.toast(failureText ?? (error as Error).message, 'error');
      return null;
    }
  }

  async bootstrap() {
    const session = await this.guard(() => api.session());
    if (session) {
      this.authenticated = session.authenticated;
      this.authRequired = session.auth_required;
    }
    if (this.authenticated) await this.refreshAll();
    this.ready = true;
  }

  async login(pin: string): Promise<boolean> {
    try {
      const session = await api.login(pin);
      this.authenticated = session.authenticated;
      this.offline = false;
      await this.refreshAll();
      return true;
    } catch (error) {
      if (error instanceof OfflineError) {
        this.offline = true;
        this.toast('Serveur injoignable', 'error');
      }
      return false;
    }
  }

  async logout() {
    await this.guard(() => api.logout());
    this.authenticated = false;
    this.stock = [];
    this.shopping = [];
    this.expiring = [];
    this.summary = null;
  }

  async refreshAll() {
    const results = await this.guard(() =>
      Promise.all([
        api.locations(),
        api.summary(),
        api.stock({ location_id: this.stockFilter, q: this.stockQuery }),
        api.expiring(),
        api.shopping(),
      ]),
    );
    if (!results) return;
    const [locations, summary, stock, expiring, shopping] = results;
    this.locations = locations;
    this.summary = summary;
    this.stock = stock;
    this.expiring = expiring;
    this.shopping = shopping;
  }

  async refreshStock() {
    const [stock, summary, expiring] = (await this.guard(() =>
      Promise.all([
        api.stock({ location_id: this.stockFilter, q: this.stockQuery }),
        api.summary(),
        api.expiring(),
      ]),
    )) ?? [null, null, null];
    if (stock) this.stock = stock;
    if (summary) this.summary = summary;
    if (expiring) this.expiring = expiring;
  }

  async refreshShopping() {
    const [shopping, summary] = (await this.guard(() =>
      Promise.all([api.shopping(), api.summary()]),
    )) ?? [null, null];
    if (shopping) this.shopping = shopping;
    if (summary) this.summary = summary;
  }

  /** Change d'onglet et recharge : deux téléphones scannent souvent en parallèle. */
  async setTab(tab: Tab) {
    const changed = this.tab !== tab;
    this.tab = tab;
    if (changed && this.authenticated) await this.refreshAll();
  }

  rememberLocation(id: number | null) {
    this.lastLocationId = id;
    if (id == null) localStorage.removeItem('miamstock.lastLocation');
    else localStorage.setItem('miamstock.lastLocation', String(id));
  }

  locationName(id: number | null): string | null {
    return this.locations.find((location) => location.id === id)?.name ?? null;
  }

  get alertCount(): number {
    if (!this.summary) return 0;
    return this.summary.expired + this.summary.urgent + this.summary.soon;
  }
}

export const app = new AppState();
