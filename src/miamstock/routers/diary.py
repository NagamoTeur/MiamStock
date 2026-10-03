"""Journal alimentaire et recherche d'aliments par nom.

Un journal volontairement simple — calories face à un objectif, macros en
petit — pour une seule personne. Il partage avec le stock la recherche et la
base d'aliments, mais ne le touche que si on le lui demande explicitement.
"""

from __future__ import annotations

from datetime import date, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from .. import auth
from ..db import get_conn, log_event, now_iso, transaction
from ..models import (
    MEALS,
    SAISIE_RAPIDE,
    ApplyTemplateIn,
    DiaryDayOut,
    DiaryEntryIn,
    DiaryEntryOut,
    DiaryEntryPatch,
    DiarySettings,
    FoodOut,
    RepeatIn,
    RepeatSuggestion,
    SearchOut,
    TemplateIn,
    TemplateOut,
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


# Au-delà, « la dernière fois » n'est plus une habitude : on ne propose rien.
REPRISE_JOURS = 14


def _apercu(lignes) -> dict:
    return {
        "count": len(lignes),
        "kcal": round(sum(l["kcal_100g"] * l["grams"] / 100 for l in lignes), PRECISION),
        "labels": [l["label"] for l in lignes],
    }


def _suggestions(conn, jour: date, remplis: set[str]) -> list[RepeatSuggestion]:
    """Pour chaque repas encore vide, la dernière fois qu'on l'a rempli.

    C'est ce qui rend un journal tenable au quotidien : le petit-déjeuner
    d'aujourd'hui ressemble presque toujours à celui d'hier.
    """
    derniers = conn.execute(
        """
        SELECT meal, MAX(day) AS from_day FROM diary_entries
        WHERE day < ? AND day >= ?
        GROUP BY meal
        """,
        (jour.isoformat(), (jour - timedelta(days=REPRISE_JOURS)).isoformat()),
    ).fetchall()
    par_repas = {ligne["meal"]: ligne["from_day"] for ligne in derniers}

    suggestions = []
    for repas in MEALS:
        if repas in remplis or repas not in par_repas:
            continue
        lignes = conn.execute(
            "SELECT * FROM diary_entries WHERE day = ? AND meal = ? ORDER BY created_at, id",
            (par_repas[repas], repas),
        ).fetchall()
        suggestions.append(
            RepeatSuggestion(meal=repas, from_day=par_repas[repas], **_apercu(lignes))
        )
    return suggestions


def _journee(conn, jour: date) -> DiaryDayOut:
    lignes = conn.execute(
        "SELECT * FROM diary_entries WHERE day = ? ORDER BY created_at, id",
        (jour.isoformat(),),
    ).fetchall()
    entrees = [_vers_sortie(ligne) for ligne in lignes]
    return DiaryDayOut(
        day=jour,
        goal_kcal=_objectif(conn),
        totals=_additionner(entrees),
        meals={repas: _additionner([e for e in entrees if e.meal == repas]) for repas in MEALS},
        entries=entrees,
        suggestions=_suggestions(conn, jour, {e.meal for e in entrees}),
    )


def _recopier(conn, lignes, jour: date, repas: str) -> None:
    """Recopie des aliments (d'un autre jour ou d'un favori) dans un repas.

    Le stock n'est jamais touché : reprendre son petit-déjeuner n'est pas
    déclarer qu'on a fini un paquet.
    """
    horodatage = now_iso()
    conn.executemany(
        """
        INSERT INTO diary_entries (day, meal, label, brand, source, ref, grams,
                                   kcal_100g, prot_100g, gluc_100g, lip_100g, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                jour.isoformat(), repas, l["label"], l["brand"], l["source"], l["ref"],
                l["grams"], l["kcal_100g"], l["prot_100g"], l["gluc_100g"], l["lip_100g"],
                horodatage,
            )
            for l in lignes
        ],
    )


@router.get("/diary", response_model=DiaryDayOut)
def read_day(day: date | None = None) -> DiaryDayOut:
    with get_conn() as conn:
        return _journee(conn, day or date.today())


@router.post("/diary/repeat", response_model=DiaryDayOut)
def repeat_meal(body: RepeatIn) -> DiaryDayOut:
    """« Comme hier » : recopie un repas d'un jour précédent."""
    with get_conn() as conn, transaction(conn):
        lignes = conn.execute(
            "SELECT * FROM diary_entries WHERE day = ? AND meal = ? ORDER BY created_at, id",
            (body.from_day.isoformat(), body.meal),
        ).fetchall()
        if not lignes:
            raise HTTPException(status_code=404, detail="Ce repas est vide ce jour-là")
        _recopier(conn, lignes, body.day, body.meal)
        return _journee(conn, body.day)


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
        entree = conn.execute(
            "SELECT source FROM diary_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if entree is None:
            raise HTTPException(status_code=404, detail="Entrée introuvable")
        # Une saisie rapide se corrige en calories ; un aliment pesé, en grammes.
        # Changer les valeurs pour 100 g d'un aliment réécrirait sa fiche figée.
        rapide = entree["source"] == SAISIE_RAPIDE
        if rapide and "grams" in champs:
            raise HTTPException(status_code=400, detail="Une saisie rapide se corrige en calories")
        if not rapide and "kcal_100g" in champs:
            raise HTTPException(status_code=400, detail="Seule une saisie rapide se corrige en calories")
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


# --- Repas favoris ------------------------------------------------------------------


def _favoris(conn, identifiant: int | None = None) -> list[TemplateOut]:
    modeles = conn.execute(
        "SELECT * FROM meal_templates"
        + (" WHERE id = ?" if identifiant is not None else "")
        + " ORDER BY name COLLATE NOCASE",
        (identifiant,) if identifiant is not None else (),
    ).fetchall()
    sortie = []
    for modele in modeles:
        lignes = conn.execute(
            "SELECT * FROM meal_template_items WHERE template_id = ? ORDER BY position",
            (modele["id"],),
        ).fetchall()
        sortie.append(TemplateOut(id=modele["id"], name=modele["name"], **_apercu(lignes)))
    return sortie


@router.get("/diary/templates", response_model=list[TemplateOut])
def list_templates() -> list[TemplateOut]:
    with get_conn() as conn:
        return _favoris(conn)


@router.post("/diary/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(body: TemplateIn) -> TemplateOut:
    """Enregistre un repas du journal, tel qu'il est ce jour-là, comme favori."""
    nom = body.name.strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Donne un nom à ce repas")
    with get_conn() as conn, transaction(conn):
        lignes = conn.execute(
            "SELECT * FROM diary_entries WHERE day = ? AND meal = ? ORDER BY created_at, id",
            (body.day.isoformat(), body.meal),
        ).fetchall()
        if not lignes:
            raise HTTPException(status_code=400, detail="Ce repas est vide")
        if conn.execute(
            "SELECT 1 FROM meal_templates WHERE name = ?", (nom,)
        ).fetchone():
            raise HTTPException(status_code=409, detail=f"Un repas « {nom} » existe déjà")

        curseur = conn.execute(
            "INSERT INTO meal_templates (name, created_at) VALUES (?, ?)", (nom, now_iso())
        )
        conn.executemany(
            """
            INSERT INTO meal_template_items (template_id, position, label, brand, source, ref,
                                             grams, kcal_100g, prot_100g, gluc_100g, lip_100g)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    curseur.lastrowid, position, l["label"], l["brand"], l["source"], l["ref"],
                    l["grams"], l["kcal_100g"], l["prot_100g"], l["gluc_100g"], l["lip_100g"],
                )
                for position, l in enumerate(lignes)
            ],
        )
        return _favoris(conn, curseur.lastrowid)[0]


@router.post("/diary/templates/{template_id}/apply", response_model=DiaryDayOut)
def apply_template(template_id: int, body: ApplyTemplateIn) -> DiaryDayOut:
    with get_conn() as conn, transaction(conn):
        lignes = conn.execute(
            "SELECT * FROM meal_template_items WHERE template_id = ? ORDER BY position",
            (template_id,),
        ).fetchall()
        if not lignes:
            raise HTTPException(status_code=404, detail="Repas favori introuvable")
        _recopier(conn, lignes, body.day, body.meal)
        return _journee(conn, body.day)


@router.delete("/diary/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int) -> Response:
    with get_conn() as conn, transaction(conn):
        conn.execute("DELETE FROM meal_templates WHERE id = ?", (template_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
