"""Liste de courses : entrées automatiques (seuils) et entrées libres."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from .. import auth
from ..db import get_conn, log_event, now_iso, transaction
from ..models import ShoppingItemIn, ShoppingItemOut, ShoppingItemPatch

router = APIRouter(prefix="/api/shopping", dependencies=[Depends(auth.require_session)])


def _rows_to_items(rows) -> list[ShoppingItemOut]:
    items = []
    for row in rows:
        items.append(
            ShoppingItemOut(
                id=row["id"],
                barcode=row["barcode"],
                label=row["label"] or row["product_name"] or row["barcode"] or "Sans nom",
                quantity=row["quantity"],
                checked=bool(row["checked"]),
                auto=bool(row["auto"]),
                image_url=row["image_url"],
                brand=row["brand"],
            )
        )
    return items


SELECT_ITEMS = """
SELECT s.*, p.name AS product_name, p.image_url, p.brand
FROM shopping_items s LEFT JOIN products p ON p.barcode = s.barcode
"""


@router.get("", response_model=list[ShoppingItemOut])
def list_items() -> list[ShoppingItemOut]:
    with get_conn() as conn:
        rows = conn.execute(
            SELECT_ITEMS + " ORDER BY s.checked, COALESCE(s.label, p.name) COLLATE NOCASE"
        ).fetchall()
    return _rows_to_items(rows)


@router.post("", response_model=ShoppingItemOut, status_code=status.HTTP_201_CREATED)
def add_item(body: ShoppingItemIn) -> ShoppingItemOut:
    if not body.barcode and not (body.label or "").strip():
        raise HTTPException(status_code=400, detail="Indique un code-barres ou un libellé")

    with get_conn() as conn, transaction(conn):
        if body.barcode:
            barcode = body.barcode.strip()
            known = conn.execute(
                "SELECT 1 FROM products WHERE barcode = ?", (barcode,)
            ).fetchone()
            if known is None:
                # Un produit jamais entré en stock n'existe pas au catalogue :
                # on le garde alors comme simple libellé pour ne pas bloquer l'ajout.
                if not (body.label or "").strip():
                    raise HTTPException(status_code=404, detail="Produit inconnu au catalogue")
                barcode = None
            else:
                existing = conn.execute(
                    "SELECT id FROM shopping_items WHERE barcode = ?", (barcode,)
                ).fetchone()
                if existing is not None:
                    conn.execute(
                        "UPDATE shopping_items SET quantity = quantity + ?, checked = 0 WHERE id = ?",
                        (body.quantity, existing["id"]),
                    )
                    row = conn.execute(
                        SELECT_ITEMS + " WHERE s.id = ?", (existing["id"],)
                    ).fetchone()
                    return _rows_to_items([row])[0]
        else:
            barcode = None

        cursor = conn.execute(
            "INSERT INTO shopping_items (barcode, label, quantity, checked, auto, created_at)"
            " VALUES (?, ?, ?, 0, 0, ?)",
            (barcode, (body.label or "").strip() or None, body.quantity, now_iso()),
        )
        row = conn.execute(SELECT_ITEMS + " WHERE s.id = ?", (cursor.lastrowid,)).fetchone()
    return _rows_to_items([row])[0]


@router.patch("/{item_id}", response_model=ShoppingItemOut)
def patch_item(item_id: int, body: ShoppingItemPatch) -> ShoppingItemOut:
    with get_conn() as conn, transaction(conn):
        existing = conn.execute("SELECT id FROM shopping_items WHERE id = ?", (item_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Ligne introuvable")

        updates: list[str] = []
        params: list[object] = []
        if body.quantity is not None:
            updates.append("quantity = ?")
            params.append(body.quantity)
        if body.checked is not None:
            updates.append("checked = ?")
            params.append(1 if body.checked else 0)
        if body.label is not None:
            updates.append("label = ?")
            params.append(body.label.strip() or None)
        if updates:
            params.append(item_id)
            conn.execute(f"UPDATE shopping_items SET {', '.join(updates)} WHERE id = ?", params)
        row = conn.execute(SELECT_ITEMS + " WHERE s.id = ?", (item_id,)).fetchone()
    return _rows_to_items([row])[0]


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int) -> Response:
    with get_conn() as conn, transaction(conn):
        conn.execute("DELETE FROM shopping_items WHERE id = ?", (item_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/checked/all", status_code=status.HTTP_200_OK)
def clear_checked() -> dict:
    """Vide les lignes cochées après les courses."""
    with get_conn() as conn, transaction(conn):
        removed = conn.execute("DELETE FROM shopping_items WHERE checked = 1").rowcount
        log_event(conn, "shopping_clear", quantity=removed)
    return {"removed": removed}
