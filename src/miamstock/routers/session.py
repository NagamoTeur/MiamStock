"""Session (code PIN du foyer), emplacements et résumé pour les badges d'onglets."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from .. import auth
from ..config import settings
from ..db import get_conn, transaction
from ..models import LocationIn, LocationOut, LoginIn, SessionOut, SummaryOut
from ..service import STATUS_RANK, lot_status

router = APIRouter(prefix="/api")


@router.get("/session", response_model=SessionOut)
def read_session(request: Request) -> SessionOut:
    return SessionOut(
        authenticated=auth.current_session(request), auth_required=auth.auth_required()
    )


@router.post("/session", response_model=SessionOut)
def login(body: LoginIn, request: Request, response: Response) -> SessionOut:
    if not auth.pin_matches(body.pin):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Code incorrect")
    auth.set_session_cookie(response, request)
    return SessionOut(authenticated=True, auth_required=auth.auth_required())


@router.delete("/session", response_model=SessionOut)
def logout(response: Response) -> SessionOut:
    auth.clear_session_cookie(response)
    return SessionOut(authenticated=not auth.auth_required(), auth_required=auth.auth_required())


@router.get("/locations", response_model=list[LocationOut], dependencies=[Depends(auth.require_session)])
def list_locations() -> list[LocationOut]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM locations ORDER BY position, name").fetchall()
    return [LocationOut(**dict(row)) for row in rows]


@router.post(
    "/locations",
    response_model=LocationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth.require_session)],
)
def create_location(body: LocationIn) -> LocationOut:
    with get_conn() as conn, transaction(conn):
        existing = conn.execute(
            "SELECT * FROM locations WHERE name = ?", (body.name.strip(),)
        ).fetchone()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Cet emplacement existe déjà")
        cursor = conn.execute(
            "INSERT INTO locations (name, kind, position) VALUES (?, ?, ?)",
            (body.name.strip(), body.kind, body.position),
        )
        row = conn.execute("SELECT * FROM locations WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return LocationOut(**dict(row))


@router.delete(
    "/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(auth.require_session)],
)
def delete_location(location_id: int) -> Response:
    with get_conn() as conn, transaction(conn):
        # Les lots concernés ne sont pas supprimés : ON DELETE SET NULL les laisse
        # visibles dans le stock, simplement sans emplacement.
        conn.execute("DELETE FROM locations WHERE id = ?", (location_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary", response_model=SummaryOut, dependencies=[Depends(auth.require_session)])
def summary() -> SummaryOut:
    with get_conn() as conn:
        kinds = {
            row["id"]: row["kind"]
            for row in conn.execute("SELECT id, kind FROM locations").fetchall()
        }
        rows = conn.execute(
            "SELECT barcode, quantity, expires_on, location_id FROM lots WHERE quantity > 0"
        ).fetchall()
        shopping_open = conn.execute(
            "SELECT COUNT(*) AS n FROM shopping_items WHERE checked = 0"
        ).fetchone()["n"]

    counts = {"expired": 0, "urgent": 0, "soon": 0}
    products: set[str] = set()
    total_items = 0
    for row in rows:
        products.add(row["barcode"])
        total_items += row["quantity"]
        state = lot_status(row["expires_on"], kinds.get(row["location_id"]))
        if state in counts:
            counts[state] += 1

    return SummaryOut(
        expired=counts["expired"],
        urgent=counts["urgent"],
        soon=counts["soon"],
        distinct_products=len(products),
        total_items=total_items,
        shopping_open=shopping_open,
        urgent_days=settings.urgent_days,
        soon_days=settings.soon_days,
    )


__all__ = ["router", "STATUS_RANK"]
