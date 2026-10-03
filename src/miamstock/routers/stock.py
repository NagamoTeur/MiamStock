"""Recherche de code-barres, bips d'entrée/sortie, édition des lots et des produits."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from .. import auth
from ..config import settings
from ..db import get_conn, log_event, now_iso, transaction
from ..models import (
    CatalogEntry,
    ConsumptionEntry,
    HistoryEntry,
    LookupOut,
    LotPatch,
    ProductOut,
    ProductPatch,
    StockInIn,
    StatsOut,
    StockLine,
    StockOutIn,
    StockOutResult,
    WastedProduct,
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

    # Les valeurs saisies à la main l'emportent sur Open Food Facts : quelqu'un
    # qui prend la peine de corriger une fiche en sait plus que la base.
    manual = {
        key: value.strip()
        for key, value in (
            ("name", body.name),
            ("brand", body.brand),
            ("net_quantity", body.net_quantity),
        )
        if value and value.strip()
    }

    info: dict = {}
    if known is None:
        fetched = await fetch_product(barcode)
        if fetched is not None:
            info = {**dict(fetched), **manual}
        elif manual.get("name"):
            info = {**manual, "source": "manual"}
        else:
            raise HTTPException(
                status_code=404,
                detail="Produit inconnu d'Open Food Facts : renseigne un nom pour le créer",
            )
    else:
        info = dict(manual)

    with get_conn() as conn, transaction(conn):
        upsert_product(conn, barcode, info)
        if manual:
            assignments = ", ".join(f"{field} = ?" for field in manual)
            conn.execute(
                f"UPDATE products SET {assignments}, updated_at = ? WHERE barcode = ?",
                [*manual.values(), now_iso(), barcode],
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
            # Rentrer un produit déjà périmé ne dit rien de sa durée de
            # conservation habituelle : une valeur négative pré-remplirait une
            # date passée au scan suivant.
            shelf_life = (body.expires_on - date.today()).days
            if shelf_life > 0:
                updates.append("default_shelf_life_days = ?")
                params.append(shelf_life)
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


@router.get("/products", response_model=list[CatalogEntry])
def read_catalog(
    q: str | None = Query(default=None, max_length=100),
    in_stock: bool | None = Query(default=None),
) -> list[CatalogEntry]:
    """Le catalogue : tout produit jamais scanné, y compris à zéro.

    Le stock ne montre que ce qui existe ; le catalogue montre ce que le foyer
    consomme, c'est là que vivent les réglages durables (seuil, emplacement
    par défaut, durée de conservation).
    """
    clauses: list[str] = []
    params: list[object] = []
    if q:
        clauses.append("(p.name LIKE ? OR p.brand LIKE ? OR p.barcode LIKE ?)")
        needle = f"%{q.strip()}%"
        params.extend([needle, needle, needle])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT p.*,
                   COALESCE(SUM(l.quantity), 0) AS in_stock,
                   COUNT(l.id)                  AS lot_count,
                   MIN(l.expires_on)            AS next_expiry,
                   EXISTS(SELECT 1 FROM shopping_items s WHERE s.barcode = p.barcode)
                        AS on_shopping_list,
                   (SELECT MAX(e.at) FROM events e WHERE e.barcode = p.barcode) AS last_seen
            FROM products p LEFT JOIN lots l ON l.barcode = p.barcode AND l.quantity > 0
            {where}
            GROUP BY p.barcode
            ORDER BY p.name COLLATE NOCASE
            """,
            params,
        ).fetchall()

    entries = [
        CatalogEntry(
            product=ProductOut(**row_to_product(row)),
            in_stock=row["in_stock"],
            lot_count=row["lot_count"],
            next_expiry=row["next_expiry"],
            on_shopping_list=bool(row["on_shopping_list"]),
            last_seen=row["last_seen"],
        )
        for row in rows
    ]
    if in_stock is None:
        return entries
    return [entry for entry in entries if (entry.in_stock > 0) == in_stock]


@router.post("/products/{barcode}/refresh", response_model=ProductOut)
async def refresh_product(barcode: str) -> ProductOut:
    """Recharge depuis Open Food Facts les données qui lui appartiennent.

    Remplace les valeurs nutritionnelles, les catégories et la photo — ce que
    la base fournit et qui a pu être mal extrait ou absent lors du premier
    scan. Ne touche jamais au nom, à la marque ni à la contenance, que
    l'utilisateur a pu corriger à la main.
    """
    barcode = barcode.strip()
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM products WHERE barcode = ?", (barcode,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="Produit inconnu")

    info = await fetch_product(barcode)
    if info is None:
        raise HTTPException(status_code=404, detail="Open Food Facts ne connaît pas ce produit")

    with get_conn() as conn, transaction(conn):
        conn.execute(
            """
            UPDATE products SET
                categories = ?, image_url = COALESCE(?, image_url),
                kcal_100g = ?, prot_100g = ?, gluc_100g = ?, lip_100g = ?, portion_g = ?,
                updated_at = ?
            WHERE barcode = ?
            """,
            (
                info.get("categories"), info.get("image_url"),
                info.get("kcal_100g"), info.get("prot_100g"), info.get("gluc_100g"),
                info.get("lip_100g"), info.get("portion_g"), now_iso(), barcode,
            ),
        )
        row = conn.execute("SELECT * FROM products WHERE barcode = ?", (barcode,)).fetchone()
    return ProductOut(**row_to_product(row))


@router.get("/history", response_model=list[HistoryEntry])
def read_history(
    limit: int = Query(default=50, ge=1, le=500),
    barcode: str | None = Query(default=None, max_length=64),
    kind: str | None = Query(default=None, max_length=20),
) -> list[HistoryEntry]:
    clauses: list[str] = []
    params: list[object] = []
    if barcode:
        clauses.append("e.barcode = ?")
        params.append(barcode.strip())
    if kind:
        clauses.append("e.kind = ?")
        params.append(kind)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT e.id, e.kind, e.barcode, e.quantity, e.detail, e.at, p.name
            FROM events e LEFT JOIN products p ON p.barcode = e.barcode
            {where}
            ORDER BY e.at DESC, e.id DESC LIMIT ?
            """,
            params,
        ).fetchall()
    return [HistoryEntry(**dict(row)) for row in rows]


@router.get("/consumption", response_model=list[ConsumptionEntry])
def read_consumption(
    days: int = Query(default=90, ge=7, le=3650),
    cover_days: int = Query(default=7, ge=1, le=90),
) -> list[ConsumptionEntry]:
    """Le rythme auquel chaque produit quitte le stock, mesuré sur le journal.

    Le rythme est rapporté à la période réellement observée — du premier
    mouvement de la fenêtre à aujourd'hui — et non à la fenêtre entière : sur
    une application utilisée depuis trois semaines, diviser par quatre-vingt-dix
    jours sous-estimerait la consommation d'un facteur quatre.

    `cover_days` est la durée que le seuil proposé doit couvrir : par défaut une
    semaine, soit « garde de quoi tenir jusqu'aux prochaines courses ».
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    now = datetime.now(timezone.utc)

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT p.barcode, p.name, p.brand, p.min_quantity,
                   COALESCE(SUM(CASE WHEN e.kind = 'out'     THEN e.quantity END), 0) AS consumed,
                   COALESCE(SUM(CASE WHEN e.kind = 'discard' THEN e.quantity END), 0) AS discarded,
                   COUNT(e.id) AS events,
                   MIN(e.at)   AS first_at,
                   MAX(e.at)   AS last_at,
                   (SELECT COALESCE(SUM(l.quantity), 0) FROM lots l WHERE l.barcode = p.barcode)
                        AS in_stock
            FROM products p
            JOIN events e ON e.barcode = p.barcode
            WHERE e.at >= ? AND e.kind IN ('out', 'discard')
            GROUP BY p.barcode
            """,
            (since,),
        ).fetchall()

    entries: list[ConsumptionEntry] = []
    for row in rows:
        depleted = int(row["consumed"]) + int(row["discarded"])
        if depleted <= 0:
            continue

        first = datetime.fromisoformat(row["first_at"])
        last = datetime.fromisoformat(row["last_at"])
        # Plancher à sept jours : sur quelques heures d'observation, tout rythme
        # ramené à la semaine serait un chiffre inventé.
        observed_days = max((now - first).days, 7)
        per_week = round(depleted / observed_days * 7, 2)

        # Un rythme n'a de sens qu'avec plusieurs mouvements étalés dans le temps.
        reliable = int(row["events"]) >= 3 and (last - first).days >= 14

        per_day = per_week / 7
        entries.append(
            ConsumptionEntry(
                barcode=row["barcode"],
                name=row["name"],
                brand=row["brand"],
                in_stock=int(row["in_stock"]),
                min_quantity=int(row["min_quantity"]),
                consumed=int(row["consumed"]),
                discarded=int(row["discarded"]),
                per_week=per_week,
                events=int(row["events"]),
                days_left=round(int(row["in_stock"]) / per_day, 1) if per_day > 0 else None,
                suggested_min=max(1, ceil(per_week * cover_days / 7)) if reliable else None,
                reliable=reliable,
            )
        )

    # Le plus pressant d'abord : ce qui s'épuise le plus tôt.
    return sorted(
        entries,
        key=lambda entry: (entry.days_left is None, entry.days_left or 0.0),
    )


@router.get("/stats", response_model=StatsOut)
def read_stats(days: int = Query(default=90, ge=1, le=3650)) -> StatsOut:
    """Bilan sur une fenêtre glissante, lu dans le journal réel des bips.

    Le taux de gaspillage rapporte ce qui a été jeté à tout ce qui est sorti du
    stock : c'est la seule mesure honnête de ce que l'application fait gagner,
    et rien ici n'est estimé.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")

    with get_conn() as conn:
        totals = {
            row["kind"]: row["total"]
            for row in conn.execute(
                "SELECT kind, COALESCE(SUM(quantity), 0) AS total FROM events"
                " WHERE at >= ? AND kind IN ('in', 'out', 'discard') GROUP BY kind",
                (since,),
            ).fetchall()
        }
        wasted = conn.execute(
            """
            SELECT e.barcode, COALESCE(p.name, e.barcode) AS name,
                   COALESCE(SUM(e.quantity), 0) AS quantity
            FROM events e LEFT JOIN products p ON p.barcode = e.barcode
            WHERE e.at >= ? AND e.kind = 'discard' AND e.barcode IS NOT NULL
            GROUP BY e.barcode ORDER BY quantity DESC LIMIT 5
            """,
            (since,),
        ).fetchall()

    consumed = int(totals.get("out", 0))
    discarded = int(totals.get("discard", 0))
    left_stock = consumed + discarded

    return StatsOut(
        days=days,
        entered=int(totals.get("in", 0)),
        consumed=consumed,
        discarded=discarded,
        waste_ratio=round(discarded / left_stock, 4) if left_stock else 0.0,
        most_wasted=[WastedProduct(**dict(row)) for row in wasted],
    )


__all__ = ["router", "lot_status", "location_kinds"]
