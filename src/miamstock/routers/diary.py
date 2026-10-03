"""Journal alimentaire et recherche d'aliments par nom.

Un journal volontairement simple — calories face à un objectif, macros en
petit — pour une seule personne. Il partage avec le stock la recherche et la
base d'aliments, mais ne le touche que si on le lui demande explicitement.
"""

from __future__ import annotations

from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from .. import auth
from ..db import get_conn, log_event, now_iso, transaction
from ..models import (
    MEALS,
    DiaryDayOut,
    DiaryEntryIn,
    DiaryEntryOut,
    DiaryEntryPatch,
    DiarySettings,
    FoodOut,
    SearchOut,
    Totals,
)
from ..nutrition import chercher_ciqual, chercher_off, mots, pertinence
from ..service import consume_fifo, maybe_restock, total_in_stock

router = APIRouter(prefix="/api", dependencies=[Depends(auth.require_session)])


# --- Recherche --------------------------------------------------------------------


def _chercher_catalogue(requete: str, limite: int = 8) -> list[FoodOut]:
    termes = mots(requete)
    with get_conn() as conn:
        lignes = conn.execute(
            """
            SELECT p.*, COALESCE((SELECT SUM(quantity) FROM lots l WHERE l.barcode = p.barcode), 0)
                        AS in_stock
            FROM products p
            """
        ).fetchall()

    notes = []
    for ligne in lignes:
        score = pertinence(f"{ligne['name']} {ligne['brand'] or ''}", termes)
        if score is not None:
            notes.append((score, ligne))
    notes.sort(key=lambda paire: -paire[0])

    return [
        FoodOut(
            source="catalogue",
            ref=ligne["barcode"],
            name=ligne["name"],
            brand=ligne["brand"],
            kcal_100g=ligne["kcal_100g"],
            prot_100g=ligne["prot_100g"],
            gluc_100g=ligne["gluc_100g"],
            lip_100g=ligne["lip_100g"],
            portion_g=ligne["portion_g"],
            in_stock=int(ligne["in_stock"]),
            image_url=ligne["image_url"],
        )
        for _, ligne in notes[:limite]
    ]


@router.get("/search", response_model=SearchOut)
async def search(
    q: str = Query(min_length=1, max_length=100),
    scope: str = Query(default="local", pattern="^(local|off)$"),
) -> SearchOut:
    """Cherche un aliment par son nom.

    `local` répond instantanément — le catalogue du foyer puis Ciqual, sans
    réseau. `off` interroge Open Food Facts, plus lent et parfois indisponible.
    L'interface appelle les deux en parallèle et affiche le local d'abord : la
    recherche ne doit jamais attendre le réseau pour montrer quelque chose.
    """
    if scope == "local":
        resultats = _chercher_catalogue(q) + [
            FoodOut(
                source="ciqual",
                ref=a.ref,
                name=a.nom,
                kcal_100g=a.kcal,
                prot_100g=a.proteines,
                gluc_100g=a.glucides,
                lip_100g=a.lipides,
                group=a.groupe,
            )
            for a in chercher_ciqual(q)
        ]
        return SearchOut(query=q, results=resultats)

    try:
        aliments = await chercher_off(q)
    except (httpx.HTTPError, ValueError):
        return SearchOut(query=q, results=[], off_unavailable=True)

    return SearchOut(
        query=q,
        results=[
            FoodOut(
                source="off",
                ref=a.ref,
                name=a.nom,
                brand=a.marque,
                kcal_100g=a.kcal,
                prot_100g=a.proteines,
                gluc_100g=a.glucides,
                lip_100g=a.lipides,
                portion_g=a.portion_g,
            )
            for a in aliments
        ],
    )


# --- Journal ------------------------------------------------------------------------


# Deux décimales, jamais une : l'interface arrondit une seule fois, à l'affichage.
# Arrondir ici au dixième puis là-bas à l'unité faisait afficher 5 g dans la
# feuille d'ajout et 6 g dans la journée pour la même entrée (5,46 → 5,5 → 6).
PRECISION = 2


def _part(valeur_100g: float | None, grammes: float) -> float | None:
    return None if valeur_100g is None else round(valeur_100g * grammes / 100, PRECISION)


def _vers_sortie(ligne) -> DiaryEntryOut:
    g = ligne["grams"]
    return DiaryEntryOut(
        id=ligne["id"],
        day=ligne["day"],
        meal=ligne["meal"],
        label=ligne["label"],
        brand=ligne["brand"],
        source=ligne["source"],
        ref=ligne["ref"],
        grams=g,
        kcal=round(ligne["kcal_100g"] * g / 100, PRECISION),
        prot=_part(ligne["prot_100g"], g),
        gluc=_part(ligne["gluc_100g"], g),
        lip=_part(ligne["lip_100g"], g),
        kcal_100g=ligne["kcal_100g"],
        prot_100g=ligne["prot_100g"],
        gluc_100g=ligne["gluc_100g"],
        lip_100g=ligne["lip_100g"],
    )


def _additionner(entrees: list[DiaryEntryOut]) -> Totals:
    return Totals(
        kcal=round(sum(e.kcal for e in entrees), PRECISION),
        prot=round(sum(e.prot or 0 for e in entrees), PRECISION),
        gluc=round(sum(e.gluc or 0 for e in entrees), PRECISION),
        lip=round(sum(e.lip or 0 for e in entrees), PRECISION),
    )


def _objectif(conn) -> int | None:
    ligne = conn.execute("SELECT value FROM settings WHERE key = 'goal_kcal'").fetchone()
    return int(ligne["value"]) if ligne else None


@router.get("/diary", response_model=DiaryDayOut)
def read_day(day: date | None = None) -> DiaryDayOut:
    jour = day or date.today()
    with get_conn() as conn:
        lignes = conn.execute(
            "SELECT * FROM diary_entries WHERE day = ? ORDER BY created_at, id",
            (jour.isoformat(),),
        ).fetchall()
        objectif = _objectif(conn)

    entrees = [_vers_sortie(ligne) for ligne in lignes]
    return DiaryDayOut(
        day=jour,
        goal_kcal=objectif,
        totals=_additionner(entrees),
        meals={repas: _additionner([e for e in entrees if e.meal == repas]) for repas in MEALS},
        entries=entrees,
    )


@router.post("/diary", response_model=DiaryEntryOut, status_code=status.HTTP_201_CREATED)
def add_entry(body: DiaryEntryIn) -> DiaryEntryOut:
    with get_conn() as conn, transaction(conn):
        curseur = conn.execute(
            """
            INSERT INTO diary_entries (day, meal, label, brand, source, ref, grams,
                                       kcal_100g, prot_100g, gluc_100g, lip_100g, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                body.day.isoformat(), body.meal, body.label.strip(), body.brand, body.source,
                body.ref, body.grams, body.kcal_100g, body.prot_100g, body.gluc_100g,
                body.lip_100g, now_iso(),
            ),
        )

        # Le seul pont entre le journal et le stock, et il est explicite.
        if body.finished_pack:
            if body.source != "catalogue" or not body.ref:
                raise HTTPException(
                    status_code=400,
                    detail="Seul un produit de ton stock peut être retiré du stock",
                )
            if total_in_stock(conn, body.ref) == 0:
                raise HTTPException(status_code=409, detail="Ce produit n'est plus en stock")
            consume_fifo(conn, body.ref, 1)
            log_event(conn, "out", barcode=body.ref, quantity=1, detail="journal")
            maybe_restock(conn, body.ref, total_in_stock(conn, body.ref))

        ligne = conn.execute(
            "SELECT * FROM diary_entries WHERE id = ?", (curseur.lastrowid,)
        ).fetchone()
    return _vers_sortie(ligne)


@router.patch("/diary/{entry_id}", response_model=DiaryEntryOut)
def patch_entry(entry_id: int, body: DiaryEntryPatch) -> DiaryEntryOut:
    champs = body.model_dump(exclude_unset=True)
    with get_conn() as conn, transaction(conn):
        if conn.execute("SELECT 1 FROM diary_entries WHERE id = ?", (entry_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="Entrée introuvable")
        if champs:
            affectations = ", ".join(f"{cle} = ?" for cle in champs)
            conn.execute(
                f"UPDATE diary_entries SET {affectations} WHERE id = ?",
                [*champs.values(), entry_id],
            )
        ligne = conn.execute("SELECT * FROM diary_entries WHERE id = ?", (entry_id,)).fetchone()
    return _vers_sortie(ligne)


@router.delete("/diary/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: int) -> Response:
    with get_conn() as conn, transaction(conn):
        conn.execute("DELETE FROM diary_entries WHERE id = ?", (entry_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/diary/recent", response_model=list[FoodOut])
def recent_foods(limit: int = Query(default=15, ge=1, le=50)) -> list[FoodOut]:
    """Les aliments récemment saisis, pour les ressaisir en un geste.

    C'est ce qui rend un journal tenable : on mange souvent la même chose, et
    rechercher « skyr » chaque matin est exactement ce qui fait abandonner.
    """
    with get_conn() as conn:
        lignes = conn.execute(
            """
            SELECT d.* FROM diary_entries d
            JOIN (
                SELECT source, COALESCE(ref, label) AS cle, MAX(id) AS dernier
                FROM diary_entries GROUP BY source, COALESCE(ref, label)
            ) r ON r.dernier = d.id
            ORDER BY d.id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        FoodOut(
            source=ligne["source"],
            ref=ligne["ref"] or "",
            name=ligne["label"],
            brand=ligne["brand"],
            kcal_100g=ligne["kcal_100g"],
            prot_100g=ligne["prot_100g"],
            gluc_100g=ligne["gluc_100g"],
            lip_100g=ligne["lip_100g"],
            # La dernière quantité saisie sert de portion par défaut.
            portion_g=ligne["grams"],
        )
        for ligne in lignes
    ]


@router.get("/diary/settings", response_model=DiarySettings)
def read_settings() -> DiarySettings:
    with get_conn() as conn:
        return DiarySettings(goal_kcal=_objectif(conn))


@router.put("/diary/settings", response_model=DiarySettings)
def write_settings(body: DiarySettings) -> DiarySettings:
    with get_conn() as conn, transaction(conn):
        if body.goal_kcal is None:
            conn.execute("DELETE FROM settings WHERE key = 'goal_kcal'")
        else:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('goal_kcal', ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(body.goal_kcal),),
            )
    return body
