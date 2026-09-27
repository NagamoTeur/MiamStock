"""Logique métier : statut des DLC, sortie FIFO, réappro automatique."""

from __future__ import annotations

import sqlite3
from datetime import date

from .config import settings
from .db import log_event, now_iso

# Ordre FIFO : la DLC la plus proche d'abord, les lots sans date en dernier
# (on suppose qu'une conserve attend mieux qu'un yaourt), puis le plus ancien.
FIFO_ORDER = "ORDER BY (expires_on IS NULL), expires_on ASC, created_at ASC, id ASC"
FIFO_ORDER_L = "ORDER BY (l.expires_on IS NULL), l.expires_on ASC, l.created_at ASC, l.id ASC"

STATUS_RANK = {"none": 0, "ok": 1, "soon": 2, "urgent": 3, "expired": 4}


def lot_status(expires_on: str | None, location_kind: str | None, today: date | None = None) -> str:
    """Traduit une DLC en niveau d'alerte.

    Un congélateur ne déclenche pas d'alerte « bientôt » : une pizza surgelée à
    DLC dans 5 jours n'a rien d'urgent, et noyer l'onglet d'alertes avec le
    congélo le rendrait inutile.
    """
    if not expires_on:
        return "none"
    try:
        deadline = date.fromisoformat(expires_on)
    except ValueError:
        return "none"
    days_left = (deadline - (today or date.today())).days
    if days_left < 0:
        return "expired"
    if location_kind == "freezer":
        return "ok"
    if days_left <= settings.urgent_days:
        return "urgent"
    if days_left <= settings.soon_days:
        return "soon"
    return "ok"


def worst_status(statuses: list[str]) -> str:
    if not statuses:
        return "none"
    return max(statuses, key=lambda s: STATUS_RANK.get(s, 0))


def row_to_product(row: sqlite3.Row) -> dict:
    return {
        "barcode": row["barcode"],
        "name": row["name"],
        "brand": row["brand"],
        "net_quantity": row["net_quantity"],
        "image_url": row["image_url"],
        "categories": row["categories"],
        "nutriscore": row["nutriscore"],
        "default_location_id": row["default_location_id"],
        "default_shelf_life_days": row["default_shelf_life_days"],
        "min_quantity": row["min_quantity"],
        "source": row["source"],
    }


def upsert_product(conn: sqlite3.Connection, barcode: str, info: dict) -> None:
    """Crée le produit, ou complète les champs issus d'Open Food Facts.

    COALESCE côté valeur entrante : un champ absent de la réponse OFF ne doit pas
    écraser une donnée déjà présente en base (ni un nom corrigé à la main).
    """
    existing = conn.execute(
        "SELECT barcode FROM products WHERE barcode = ?", (barcode,)
    ).fetchone()
    stamp = now_iso()
    if existing is None:
        conn.execute(
            """
            INSERT INTO products (barcode, name, brand, net_quantity, image_url, categories,
                                  nutriscore, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                barcode,
                info.get("name") or barcode,
                info.get("brand"),
                info.get("net_quantity"),
                info.get("image_url"),
                info.get("categories"),
                info.get("nutriscore"),
                info.get("source", "off"),
                stamp,
                stamp,
            ),
        )
        return
    conn.execute(
        """
        UPDATE products SET
            brand        = COALESCE(brand, ?),
            net_quantity = COALESCE(net_quantity, ?),
            image_url    = COALESCE(image_url, ?),
            categories   = COALESCE(categories, ?),
            nutriscore   = COALESCE(nutriscore, ?),
            updated_at   = ?
        WHERE barcode = ?
        """,
        (
            info.get("brand"),
            info.get("net_quantity"),
            info.get("image_url"),
            info.get("categories"),
            info.get("nutriscore"),
            stamp,
            barcode,
        ),
    )


def total_in_stock(conn: sqlite3.Connection, barcode: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) AS total FROM lots WHERE barcode = ?", (barcode,)
    ).fetchone()
    return int(row["total"])


def location_kinds(conn: sqlite3.Connection) -> dict[int, str]:
    return {
        row["id"]: row["kind"] for row in conn.execute("SELECT id, kind FROM locations").fetchall()
    }


def stock_lines(
    conn: sqlite3.Connection,
    *,
    location_id: int | None = None,
    search: str | None = None,
) -> list[dict]:
    """Stock agrégé par produit, chaque produit portant ses lots en ordre FIFO."""
    kinds = location_kinds(conn)
    names = {
        row["id"]: row["name"] for row in conn.execute("SELECT id, name FROM locations").fetchall()
    }

    clauses = ["l.quantity > 0"]
    params: list[object] = []
    if location_id is not None:
        clauses.append("l.location_id = ?")
        params.append(location_id)
    if search:
        clauses.append("(p.name LIKE ? OR p.brand LIKE ? OR p.barcode LIKE ?)")
        needle = f"%{search.strip()}%"
        params.extend([needle, needle, needle])

    rows = conn.execute(
        f"""
        SELECT l.*, p.name, p.brand, p.net_quantity, p.image_url, p.categories, p.nutriscore,
               p.default_location_id, p.default_shelf_life_days, p.min_quantity, p.source
        FROM lots l
        JOIN products p ON p.barcode = l.barcode
        WHERE {' AND '.join(clauses)}
        {FIFO_ORDER_L}
        """,
        params,
    ).fetchall()

    grouped: dict[str, dict] = {}
    for row in rows:
        line = grouped.setdefault(
            row["barcode"],
            {"product": row_to_product(row), "total": 0, "lots": [], "worst_status": "none",
             "next_expiry": None},
        )
        status = lot_status(row["expires_on"], kinds.get(row["location_id"]))
        line["total"] += row["quantity"]
        line["lots"].append(
            {
                "id": row["id"],
                "quantity": row["quantity"],
                "expires_on": row["expires_on"],
                "location_id": row["location_id"],
                "location_name": names.get(row["location_id"]),
                "note": row["note"],
                "status": status,
            }
        )

    for line in grouped.values():
        line["worst_status"] = worst_status([lot["status"] for lot in line["lots"]])
        dated = [lot["expires_on"] for lot in line["lots"] if lot["expires_on"]]
        line["next_expiry"] = min(dated) if dated else None

    return sorted(
        grouped.values(),
        key=lambda line: (-STATUS_RANK.get(line["worst_status"], 0), line["product"]["name"].lower()),
    )


def consume_fifo(conn: sqlite3.Connection, barcode: str, quantity: int) -> list[dict]:
    """Décrémente les lots du plus urgent au moins urgent. Les lots vidés sont supprimés."""
    remaining = quantity
    consumed: list[dict] = []
    rows = conn.execute(
        f"SELECT id, quantity, expires_on FROM lots WHERE barcode = ? AND quantity > 0 {FIFO_ORDER}",
        (barcode,),
    ).fetchall()

    for row in rows:
        if remaining <= 0:
            break
        take = min(remaining, row["quantity"])
        left = row["quantity"] - take
        if left == 0:
            conn.execute("DELETE FROM lots WHERE id = ?", (row["id"],))
        else:
            conn.execute("UPDATE lots SET quantity = ? WHERE id = ?", (left, row["id"]))
        consumed.append({"lot_id": row["id"], "quantity": take, "expires_on": row["expires_on"]})
        remaining -= take

    return consumed


def maybe_restock(conn: sqlite3.Connection, barcode: str, remaining_total: int) -> bool:
    """Ajoute le produit en liste de courses si le stock passe sous son seuil.

    Avec le seuil par défaut à 0, cela ne se déclenche qu'à l'épuisement complet —
    donc « bip de sortie qui vide le stock » et « seuil mini » sont la même règle.
    """
    row = conn.execute(
        "SELECT min_quantity FROM products WHERE barcode = ?", (barcode,)
    ).fetchone()
    if row is None:
        return False
    if remaining_total > row["min_quantity"]:
        return False

    existing = conn.execute(
        "SELECT id, checked FROM shopping_items WHERE barcode = ?", (barcode,)
    ).fetchone()
    if existing is not None:
        if existing["checked"]:
            # Déjà coché comme acheté : on le réactive plutôt que d'en créer un doublon.
            conn.execute(
                "UPDATE shopping_items SET checked = 0, auto = 1 WHERE id = ?", (existing["id"],)
            )
            return True
        return False

    needed = max(1, row["min_quantity"] - remaining_total)
    conn.execute(
        "INSERT INTO shopping_items (barcode, label, quantity, checked, auto, created_at)"
        " VALUES (?, NULL, ?, 0, 1, ?)",
        (barcode, needed, now_iso()),
    )
    log_event(conn, "shopping_auto", barcode=barcode, quantity=needed)
    return True
