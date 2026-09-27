"""Schémas d'entrée/sortie de l'API."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator


class LoginIn(BaseModel):
    pin: str = Field(min_length=1, max_length=64)


class SessionOut(BaseModel):
    authenticated: bool
    auth_required: bool


class LocationIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    kind: str = Field(default="other", pattern="^(fridge|freezer|pantry|other)$")
    position: int = 0


class LocationOut(BaseModel):
    id: int
    name: str
    kind: str
    position: int


class ProductOut(BaseModel):
    barcode: str
    name: str
    brand: str | None = None
    net_quantity: str | None = None
    image_url: str | None = None
    categories: str | None = None
    nutriscore: str | None = None
    default_location_id: int | None = None
    default_shelf_life_days: int | None = None
    min_quantity: int = 0
    source: str = "off"


class ProductPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=120)
    net_quantity: str | None = Field(default=None, max_length=60)
    categories: str | None = Field(default=None, max_length=200)
    default_location_id: int | None = None
    default_shelf_life_days: int | None = Field(default=None, ge=0, le=3650)
    min_quantity: int | None = Field(default=None, ge=0, le=999)


class LookupOut(BaseModel):
    barcode: str
    found: bool
    known_locally: bool
    product: ProductOut | None = None
    in_stock: int = 0
    suggested_location_id: int | None = None
    suggested_shelf_life_days: int | None = None


class LotOut(BaseModel):
    id: int
    quantity: int
    expires_on: date | None = None
    location_id: int | None = None
    location_name: str | None = None
    note: str | None = None
    status: str  # ok | soon | urgent | expired | none


class StockLine(BaseModel):
    product: ProductOut
    total: int
    lots: list[LotOut]
    worst_status: str
    next_expiry: date | None = None


class StockInIn(BaseModel):
    barcode: str = Field(min_length=1, max_length=64)
    quantity: int = Field(default=1, ge=1, le=999)
    expires_on: date | None = None
    location_id: int | None = None
    # Renseignés uniquement si Open Food Facts ne connaît pas le produit.
    name: str | None = Field(default=None, max_length=200)
    brand: str | None = Field(default=None, max_length=120)
    net_quantity: str | None = Field(default=None, max_length=60)
    note: str | None = Field(default=None, max_length=200)

    @field_validator("barcode")
    @classmethod
    def clean_barcode(cls, value: str) -> str:
        return value.strip()


class StockOutIn(BaseModel):
    barcode: str = Field(min_length=1, max_length=64)
    quantity: int = Field(default=1, ge=1, le=999)
    # Si le stock tombe à zéro, basculer le produit en liste de courses.
    add_to_shopping: bool = True

    @field_validator("barcode")
    @classmethod
    def clean_barcode(cls, value: str) -> str:
        return value.strip()


class ConsumedLot(BaseModel):
    lot_id: int
    quantity: int
    expires_on: date | None = None


class StockOutResult(BaseModel):
    barcode: str
    name: str
    requested: int
    consumed: int
    remaining_total: int
    consumed_lots: list[ConsumedLot]
    added_to_shopping: bool = False


class LotPatch(BaseModel):
    quantity: int | None = Field(default=None, ge=0, le=999)
    expires_on: date | None = None
    clear_expiry: bool = False
    location_id: int | None = None
    note: str | None = Field(default=None, max_length=200)


class ShoppingItemIn(BaseModel):
    barcode: str | None = None
    label: str | None = Field(default=None, max_length=200)
    quantity: int = Field(default=1, ge=1, le=999)


class ShoppingItemPatch(BaseModel):
    quantity: int | None = Field(default=None, ge=1, le=999)
    checked: bool | None = None
    label: str | None = Field(default=None, max_length=200)


class ShoppingItemOut(BaseModel):
    id: int
    barcode: str | None = None
    label: str
    quantity: int
    checked: bool
    auto: bool
    image_url: str | None = None
    brand: str | None = None
    # Servent au classement en rayon, côté client.
    categories: str | None = None
    location_kind: str | None = None


class CatalogEntry(BaseModel):
    """Une ligne du catalogue : le produit et ce qu'il en reste."""

    product: ProductOut
    in_stock: int
    lot_count: int
    next_expiry: date | None = None
    on_shopping_list: bool = False
    last_seen: str | None = None


class HistoryEntry(BaseModel):
    id: int
    kind: str
    barcode: str | None = None
    name: str | None = None
    quantity: int | None = None
    detail: str | None = None
    at: str


class WastedProduct(BaseModel):
    barcode: str
    name: str
    quantity: int


class StatsOut(BaseModel):
    """Bilan sur une fenêtre glissante, calculé depuis le journal réel des bips."""

    days: int
    entered: int
    consumed: int
    discarded: int
    # Part de ce qui est sorti du stock qui l'a été par la poubelle.
    waste_ratio: float
    most_wasted: list[WastedProduct]


class ConsumptionEntry(BaseModel):
    """Rythme auquel un produit quitte le stock, et ce qu'on peut en déduire.

    « Sortie » réunit le consommé et le jeté : les deux vident l'étagère, et
    c'est la vitesse à laquelle elle se vide qui dit quand racheter. Le
    gaspillage reste compté séparément pour ne rien maquiller.
    """

    barcode: str
    name: str
    brand: str | None = None
    in_stock: int
    min_quantity: int
    consumed: int
    discarded: int
    per_week: float
    events: int
    days_left: float | None = None
    suggested_min: int | None = None
    # Faux tant qu'il n'y a pas assez d'historique : un rythme tiré d'un seul
    # mouvement serait une invention présentée comme une mesure.
    reliable: bool = False


class SummaryOut(BaseModel):
    expired: int
    urgent: int
    soon: int
    distinct_products: int
    total_items: int
    shopping_open: int
    urgent_days: int
    soon_days: int
