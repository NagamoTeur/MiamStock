"""Recherche de code-barres, bips d'entrée/sortie, édition des lots et des produits."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from .. import auth
from ..config import settings
from ..db import get_conn, log_event, now_iso, transaction
from ..models import (
    LookupOut,
    LotPatch,
    ProductOut,
    ProductPatch,
    StockInIn,
    StockLine,
    StockOutIn,
    StockOutResult,
)
from ..openfoodfacts import fetch_product
from ..service import (
    consume_fifo,
    location_kinds,
    lot_status,
    maybe_restock,
    row_to_product,
    stock_lines,
    total_in_stock,
    upsert_product,
)

router = APIRouter(prefix="/api", dependencies=[Depends(auth.require_session)])


@router.get("/lookup/{barcode}", response_model=LookupOut)
async def lookup(barcode: str) -> LookupOut:
    """Résout un code-barres : d'abord la base locale, puis Open Food Facts.

    Rien n'est écrit ici : un scan raté ne doit pas polluer le catalogue. Le
    produit n'est créé qu'au bip d'entrée confirmé.
    """
    barcode = barcode.strip()
    if not barcode:
        raise HTTPException(status_code=400, detail="Code-barres vide")

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM products WHERE barcode = ?", (barcode,)).fetchone()
        in_stock = total_in_stock(conn, barcode) if row is not None else 0

    if row is not None:
        product = row_to_product(row)
        return LookupOut(
            barcode=barcode,
            found=True,
            known_locally=True,
            product=ProductOut(**product),
            in_stock=in_stock,
            suggested_location_id=product["default_location_id"],
            suggested_shelf_life_days=product["default_shelf_life_days"],
        )

    info = await fetch_product(barcode)
    if info is None:
        return LookupOut(barcode=barcode, found=False, known_locally=False)

    return LookupOut(
        barcode=barcode,
        found=True,
        known_locally=False,
        product=ProductOut(barcode=barcode, **info),
    )


@router.get("/stock", response_model=list[StockLine])
def read_stock(
    location_id: int | None = None,
    q: str | None = Query(default=None, max_length=100),
) -> list[StockLine]:
    with get_conn() as conn:
        return [StockLine(**line) for line in stock_lines(conn, location_id=location_id, search=q)]


@router.get("/expiring", response_model=list[StockLine])
def read_expiring(days: int = Query(default=0, ge=0, le=365)) -> list[StockLine]:
    """Onglet « À consommer » : périmé, urgent et bientôt, du plus critique au moins.

    `days` à 0 utilise le seuil « bientôt » configuré ; sinon on filtre sur une
    fenêtre explicite en jours.
    """
    horizon = date.today() + timedelta(days=days or settings.soon_days)
    with get_conn() as conn:
        lines = stock_lines(conn)

    keep: list[StockLine] = []
    for line in lines:
        lots = [
            lot
            for lot in line["lots"]
            if lot["expires_on"]
            and date.fromisoformat(lot["expires_on"]) <= horizon
            and lot["status"] in ("expired", "urgent", "soon")
        ]
        if not lots:
            continue
        line = {**line, "lots": lots, "total": sum(lot["quantity"] for lot in lots)}
        keep.append(StockLine(**line))
    return keep


@router.post("/stock/in", response_model=StockLine, status_code=status.HTTP_201_CREATED)
async def stock_in(body: StockInIn) -> StockLine:
    """Bip d'entrée : crée un lot (quantité + DLC) et complète le catalogue au besoin."""
    barcode = body.barcode
    with get_conn() as conn:
        known = conn.execute(
            "SELECT barcode FROM products WHERE barcode = ?", (barcode,)
        ).fetchone()

    info: dict = {}
    if known is None:
        fetched = await fetch_product(barcode)
        if fetched is not None:
            info = dict(fetched)
        elif body.name:
            info = {"name": body.name.strip(), "source": "manual"}
        else:
            raise HTTPException(
                status_code=404,
                detail="Produit inconnu d'Open Food Facts : renseigne un nom pour le créer",
            )
    elif body.name:
        info = {"name": body.name.strip()}

    with get_conn() as conn, transaction(conn):
        upsert_product(conn, barcode, info)
        if body.name:
            conn.execute(
                "UPDATE products SET name = ?, updated_at = ? WHERE barcode = ?",
                (body.name.strip(), now_iso(), barcode),
            )

        product = conn.execute(
            "SELECT * FROM products WHERE barcode = ?", (barcode,)
        ).fetchone()
        location_id = body.location_id if body.location_id is not None else product["default_location_id"]
        if location_id is not None:
            exists = conn.execute(
                "SELECT 1 FROM locations WHERE id = ?", (location_id,)
            ).fetchone()
            if exists is None:
                raise HTTPException(status_code=400, detail="Emplacement inconnu")

        cursor = conn.execute(
            "INSERT INTO lots (barcode, location_id, quantity, expires_on, note, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                barcode,
                location_id,
                body.quantity,
                body.expires_on.isoformat() if body.expires_on else None,
                body.note,
                now_iso(),
            ),
        )
        log_event(conn, "in", barcode=barcode, lot_id=cursor.lastrowid, quantity=body.quantity)

        # Mémoriser les choix du bip : le prochain scan du même produit les propose d'office.
        updates: list[str] = []
        params: list[object] = []
        if location_id is not None and product["default_location_id"] is None:
            updates.append("default_location_id = ?")
            params.append(location_id)
        if body.expires_on and product["default_shelf_life_days"] is None:
            updates.append("default_shelf_life_days = ?")
            params.append((body.expires_on - date.today()).days)
        if updates:
            params.append(barcode)
            conn.execute(f"UPDATE products SET {', '.join(updates)} WHERE barcode = ?", params)

        # Le produit est rentré : il n'a plus rien à faire dans la liste de courses.
        conn.execute("DELETE FROM shopping_items WHERE barcode = ?", (barcode,))

        lines = stock_lines(conn, search=None)

    for line in lines:
        if line["product"]["barcode"] == barcode:
            return StockLine(**line)
    raise HTTPException(status_code=500, detail="Lot créé mais introuvable")


@router.post("/stock/out", response_model=StockOutResult)
def stock_out(body: StockOutIn) -> StockOutResult:
    """Bip de sortie : décrémente en FIFO le lot qui périme le plus tôt."""
    barcode = body.barcode
    with get_conn() as conn, transaction(conn):
        product = conn.execute(
            "SELECT name FROM products WHERE barcode = ?", (barcode,)
        ).fetchone()
        if product is None:
            raise HTTPException(status_code=404, detail="Produit absent du stock")

        available = total_in_stock(conn, barcode)
        if available == 0:
            raise HTTPException(status_code=409, detail="Plus aucun exemplaire en stock")

        consumed = consume_fifo(conn, barcode, body.quantity)
        taken = sum(item["quantity"] for item in consumed)
        remaining = available - taken
        log_event(conn, "out", barcode=barcode, quantity=taken)

        added = maybe_restock(conn, barcode, remaining) if body.add_to_shopping else False

    return StockOutResult(
        barcode=barcode,
        name=product["name"],
        requested=body.quantity,
        consumed=taken,
        remaining_total=remaining,
        consumed_lots=consumed,
        added_to_shopping=added,
    )


@router.patch("/lots/{lot_id}", response_model=StockLine)
def patch_lot(lot_id: int, body: LotPatch) -> StockLine:
    with get_conn() as conn, transaction(conn):
        lot = conn.execute("SELECT * FROM lots WHERE id = ?", (lot_id,)).fetchone()
        if lot is None:
            raise HTTPException(status_code=404, detail="Lot introuvable")

        updates: list[str] = []
        params: list[object] = []
        if body.quantity is not None:
            updates.append("quantity = ?")
            params.append(body.quantity)
        if body.clear_expiry:
            updates.append("expires_on = NULL")
        elif body.expires_on is not None:
            updates.append("expires_on = ?")
            params.append(body.expires_on.isoformat())
        if body.location_id is not None:
            updates.append("location_id = ?")
            params.append(body.location_id)
        if body.note is not None:
            updates.append("note = ?")
            params.append(body.note)

        if updates:
            params.append(lot_id)
            conn.execute(f"UPDATE lots SET {', '.join(updates)} WHERE id = ?", params)
            log_event(conn, "adjust", barcode=lot["barcode"], lot_id=lot_id, quantity=body.quantity)

        if body.quantity == 0:
            conn.execute("DELETE FROM lots WHERE id = ?", (lot_id,))

        lines = stock_lines(conn)

    for line in lines:
        if line["product"]["barcode"] == lot["barcode"]:
            return StockLine(**line)
    # Plus aucun lot pour ce produit : renvoyer une ligne vide plutôt qu'une erreur.
    with get_conn() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE barcode = ?", (lot["barcode"],)
        ).fetchone()
    return StockLine(
        product=ProductOut(**row_to_product(product)),
        total=0,
        lots=[],
        worst_status="none",
        next_expiry=None,
    )


@router.delete("/lots/{lot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lot(lot_id: int, reason: str = Query(default="discard")) -> Response:
    with get_conn() as conn, transaction(conn):
        lot = conn.execute("SELECT * FROM lots WHERE id = ?", (lot_id,)).fetchone()
        if lot is None:
            raise HTTPException(status_code=404, detail="Lot introuvable")
        conn.execute("DELETE FROM lots WHERE id = ?", (lot_id,))
        log_event(
            conn,
            reason if reason in ("discard", "out") else "discard",
            barcode=lot["barcode"],
            lot_id=lot_id,
            quantity=lot["quantity"],
        )
        maybe_restock(conn, lot["barcode"], total_in_stock(conn, lot["barcode"]))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/products/{barcode}", response_model=ProductOut)
def read_product(barcode: str) -> ProductOut:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM products WHERE barcode = ?", (barcode.strip(),)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Produit inconnu")
    return ProductOut(**row_to_product(row))


@router.patch("/products/{barcode}", response_model=ProductOut)
def patch_product(barcode: str, body: ProductPatch) -> ProductOut:
    barcode = barcode.strip()
    with get_conn() as conn, transaction(conn):
        row = conn.execute("SELECT * FROM products WHERE barcode = ?", (barcode,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Produit inconnu")

        fields = body.model_dump(exclude_unset=True)
        if fields:
            assignments = ", ".join(f"{key} = ?" for key in fields)
            conn.execute(
                f"UPDATE products SET {assignments}, updated_at = ? WHERE barcode = ?",
                [*fields.values(), now_iso(), barcode],
            )
        if "min_quantity" in fields:
            maybe_restock(conn, barcode, total_in_stock(conn, barcode))
        row = conn.execute("SELECT * FROM products WHERE barcode = ?", (barcode,)).fetchone()
    return ProductOut(**row_to_product(row))


@router.get("/history")
def read_history(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT e.*, p.name
            FROM events e LEFT JOIN products p ON p.barcode = e.barcode
            ORDER BY e.at DESC, e.id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


__all__ = ["router", "lot_status", "location_kinds"]
