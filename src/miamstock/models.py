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
    brand: str | None = None
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
    # Renseigné uniquement si Open Food Facts ne connaît pas le produit.
    name: str | None = Field(default=None, max_length=200)
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


class SummaryOut(BaseModel):
    expired: int
    urgent: int
    soon: int
    distinct_products: int
    total_items: int
    shopping_open: int
    urgent_days: int
    soon_days: int
