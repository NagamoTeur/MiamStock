export type Status = 'none' | 'ok' | 'soon' | 'urgent' | 'expired';

export interface Location {
  id: number;
  name: string;
  kind: 'fridge' | 'freezer' | 'pantry' | 'other';
  position: number;
}

export interface Product {
  barcode: string;
  name: string;
  brand: string | null;
  net_quantity: string | null;
  image_url: string | null;
  categories: string | null;
  nutriscore: string | null;
  default_location_id: number | null;
  default_shelf_life_days: number | null;
  min_quantity: number;
  source: string;
  kcal_100g: number | null;
  prot_100g: number | null;
  gluc_100g: number | null;
  lip_100g: number | null;
  portion_g: number | null;
}

export interface Lot {
  id: number;
  quantity: number;
  expires_on: string | null;
  location_id: number | null;
  location_name: string | null;
  note: string | null;
  status: Status;
}

export interface StockLine {
  product: Product;
  total: number;
  lots: Lot[];
  worst_status: Status;
  next_expiry: string | null;
}

export interface Lookup {
  barcode: string;
  found: boolean;
  known_locally: boolean;
  product: Product | null;
  in_stock: number;
  suggested_location_id: number | null;
  suggested_shelf_life_days: number | null;
}

export interface StockOutResult {
  barcode: string;
  name: string;
  requested: number;
  consumed: number;
  remaining_total: number;
  consumed_lots: { lot_id: number; quantity: number; expires_on: string | null }[];
  added_to_shopping: boolean;
}

export interface ShoppingItem {
  id: number;
  barcode: string | null;
  label: string;
  quantity: number;
  checked: boolean;
  auto: boolean;
  image_url: string | null;
  brand: string | null;
  categories: string | null;
  location_kind: string | null;
}

export interface Summary {
  expired: number;
  urgent: number;
  soon: number;
  distinct_products: number;
  total_items: number;
  shopping_open: number;
  urgent_days: number;
  soon_days: number;
}

export interface Session {
  authenticated: boolean;
  auth_required: boolean;
}

export interface CatalogEntry {
  product: Product;
  in_stock: number;
  lot_count: number;
  next_expiry: string | null;
  on_shopping_list: boolean;
  last_seen: string | null;
}

export interface HistoryEntry {
  id: number;
  kind: 'in' | 'out' | 'discard' | 'adjust' | 'shopping_auto' | 'shopping_clear';
  barcode: string | null;
  name: string | null;
  quantity: number | null;
  detail: string | null;
  at: string;
}

export interface Stats {
  days: number;
  entered: number;
  consumed: number;
  discarded: number;
  waste_ratio: number;
  most_wasted: { barcode: string; name: string; quantity: number }[];
}

export interface ConsumptionEntry {
  barcode: string;
  name: string;
  brand: string | null;
  in_stock: number;
  min_quantity: number;
  consumed: number;
  discarded: number;
  per_week: number;
  events: number;
  days_left: number | null;
  suggested_min: number | null;
  reliable: boolean;
}

export type Meal = 'petit_dejeuner' | 'dejeuner' | 'diner' | 'collation';

export interface Food {
  source: 'catalogue' | 'ciqual' | 'off' | 'libre';
  ref: string;
  name: string;
  brand: string | null;
  kcal_100g: number | null;
  prot_100g: number | null;
  gluc_100g: number | null;
  lip_100g: number | null;
  portion_g: number | null;
  group: string | null;
  in_stock: number;
  image_url: string | null;
}

export interface SearchResult {
  query: string;
  results: Food[];
  off_unavailable: boolean;
}

export interface Totals {
  kcal: number;
  prot: number;
  gluc: number;
  lip: number;
}

export interface DiaryEntry {
  id: number;
  day: string;
  meal: Meal;
  label: string;
  brand: string | null;
  source: Food['source'];
  ref: string | null;
  grams: number;
  kcal: number;
  prot: number | null;
  gluc: number | null;
  lip: number | null;
  kcal_100g: number;
}

export interface DiaryDay {
  day: string;
  goal_kcal: number | null;
  totals: Totals;
  meals: Record<Meal, Totals>;
  entries: DiaryEntry[];
}
