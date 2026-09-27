import type {
  CatalogEntry,
  ConsumptionEntry,
  HistoryEntry,
  Location,
  Product,
  Lookup,
  Session,
  ShoppingItem,
  StockLine,
  Stats,
  StockOutResult,
  Summary,
} from './types';

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

/** Erreur réseau (et non refus du serveur) : c'est ce qui déclenche le bandeau hors ligne. */
export class OfflineError extends Error {
  constructor() {
    super('Pas de connexion au serveur');
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      credentials: 'same-origin',
      headers: init.body ? { 'Content-Type': 'application/json' } : undefined,
      ...init,
    });
  } catch {
    throw new OfflineError();
  }

  if (response.status === 204) return undefined as T;

  let payload: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    const detail =
      payload && typeof payload === 'object' && 'detail' in payload
        ? String((payload as { detail: unknown }).detail)
        : `Erreur ${response.status}`;
    throw new ApiError(response.status, detail);
  }

  return payload as T;
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

export const api = {
  session: () => request<Session>('/session'),
  login: (pin: string) => request<Session>('/session', { method: 'POST', ...json({ pin }) }),
  logout: () => request<Session>('/session', { method: 'DELETE' }),

  summary: () => request<Summary>('/summary'),
  locations: () => request<Location[]>('/locations'),
  createLocation: (name: string, kind: string) =>
    request<Location>('/locations', { method: 'POST', ...json({ name, kind }) }),
  deleteLocation: (id: number) => request<void>(`/locations/${id}`, { method: 'DELETE' }),

  lookup: (barcode: string) => request<Lookup>(`/lookup/${encodeURIComponent(barcode)}`),

  stock: (params: { location_id?: number | null; q?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.location_id != null) query.set('location_id', String(params.location_id));
    if (params.q) query.set('q', params.q);
    const suffix = query.toString();
    return request<StockLine[]>(`/stock${suffix ? `?${suffix}` : ''}`);
  },
  expiring: () => request<StockLine[]>('/expiring'),

  stockIn: (body: {
    barcode: string;
    quantity: number;
    expires_on?: string | null;
    location_id?: number | null;
    name?: string | null;
    brand?: string | null;
    net_quantity?: string | null;
  }) => request<StockLine>('/stock/in', { method: 'POST', ...json(body) }),

  stockOut: (body: { barcode: string; quantity: number; add_to_shopping: boolean }) =>
    request<StockOutResult>('/stock/out', { method: 'POST', ...json(body) }),

  patchLot: (
    id: number,
    body: {
      quantity?: number;
      expires_on?: string | null;
      clear_expiry?: boolean;
      location_id?: number | null;
    },
  ) => request<StockLine>(`/lots/${id}`, { method: 'PATCH', ...json(body) }),
  deleteLot: (id: number) => request<void>(`/lots/${id}`, { method: 'DELETE' }),

  patchProduct: (
    barcode: string,
    body: {
      name?: string;
      brand?: string | null;
      net_quantity?: string | null;
      min_quantity?: number;
      default_location_id?: number | null;
      default_shelf_life_days?: number | null;
    },
  ) =>
    request<Product>(`/products/${encodeURIComponent(barcode)}`, {
      method: 'PATCH',
      ...json(body),
    }),

  catalog: (params: { q?: string; in_stock?: boolean } = {}) => {
    const query = new URLSearchParams();
    if (params.q) query.set('q', params.q);
    if (params.in_stock != null) query.set('in_stock', String(params.in_stock));
    const suffix = query.toString();
    return request<CatalogEntry[]>(`/products${suffix ? `?${suffix}` : ''}`);
  },

  history: (params: { limit?: number; barcode?: string; kind?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.limit) query.set('limit', String(params.limit));
    if (params.barcode) query.set('barcode', params.barcode);
    if (params.kind) query.set('kind', params.kind);
    const suffix = query.toString();
    return request<HistoryEntry[]>(`/history${suffix ? `?${suffix}` : ''}`);
  },

  stats: (days = 90) => request<Stats>(`/stats?days=${days}`),

  consumption: (params: { days?: number; cover_days?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.days) query.set('days', String(params.days));
    if (params.cover_days) query.set('cover_days', String(params.cover_days));
    const suffix = query.toString();
    return request<ConsumptionEntry[]>(`/consumption${suffix ? `?${suffix}` : ''}`);
  },

  shopping: () => request<ShoppingItem[]>('/shopping'),
  addShopping: (body: { barcode?: string | null; label?: string | null; quantity?: number }) =>
    request<ShoppingItem>('/shopping', { method: 'POST', ...json(body) }),
  patchShopping: (id: number, body: { quantity?: number; checked?: boolean }) =>
    request<ShoppingItem>(`/shopping/${id}`, { method: 'PATCH', ...json(body) }),
  deleteShopping: (id: number) => request<void>(`/shopping/${id}`, { method: 'DELETE' }),
  clearChecked: () => request<{ removed: number }>('/shopping/checked/all', { method: 'DELETE' }),
};
