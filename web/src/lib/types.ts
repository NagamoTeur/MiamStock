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
