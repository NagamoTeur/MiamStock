"""Aliments, valeurs nutritionnelles et recherche par nom.

Trois sources, interrogées dans cet ordre de confiance :

1. le catalogue du foyer — ce qui a déjà été scanné ;
2. Ciqual, la table officielle de l'ANSES — les aliments génériques (une
   pomme, du riz cuit, un filet de poulet), que Open Food Facts couvre mal ;
3. Open Food Facts — les produits emballés, par son moteur de recherche.

Toutes les valeurs sont exprimées pour 100 g, comme sur les étiquettes.
"""

from __future__ import annotations

import csv
import logging
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import httpx

from .config import settings

log = logging.getLogger(__name__)

CIQUAL_CSV = Path(__file__).parent / "data" / "ciqual.csv"
OFF_SEARCH_URL = "https://search.openfoodfacts.org/search"


@dataclass(frozen=True)
class Aliment:
    source: str          # "catalogue" | "ciqual" | "off"
    ref: str             # code-barres ou code Ciqual
    nom: str
    marque: str | None
    kcal: float | None   # pour 100 g
    proteines: float | None
    glucides: float | None
    lipides: float | None
    portion_g: float | None = None
    groupe: str | None = None


# --- Normalisation et classement ---------------------------------------------


def normaliser(texte: str) -> str:
    """Minuscules, sans accents : « Pâtes » et « pates » doivent se rencontrer."""
    decompose = unicodedata.normalize("NFD", texte.lower())
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")


def mots(texte: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normaliser(texte))


# Terminaisons de pluriel et de féminin, sans accents (« ée » est devenu « ee »).
# Une liste plutôt qu'un nombre de lettres : avec « deux lettres d'écart
# autorisées », « poulets » devenait une forme de « poule » (+ « ts »), et la
# recherche de poulet renvoyait de la poule.
FLEXIONS = frozenset({"s", "x", "e", "es", "ee", "ees"})


def flechi(court: str, long_: str) -> bool:
    """`long_` est-il `court` augmenté d'une terminaison de pluriel ou de féminin ?"""
    return (
        len(court) >= 3
        and long_.startswith(court)
        and long_[len(court):] in FLEXIONS
    )


def correspond(jeton: str, mot: str) -> bool:
    """Le mot tapé désigne-t-il ce mot du nom ?

    Dans les deux sens, parce que le français fléchit : « complètes » doit
    trouver « complet », « pommes » trouver « pomme », « cuites » trouver
    « cuit ». Le sens direct couvre aussi la frappe en cours (« pom » → pomme).
    """
    return jeton.startswith(mot) or flechi(jeton, mot)


def meme_mot(jeton: str, mot: str) -> bool:
    """Deux formes du même mot : « pomme » et « pommes », « cuit » et « cuite »."""
    if jeton == mot:
        return True
    court, long_ = sorted((jeton, mot), key=len)
    return flechi(court, long_)


def pertinence(nom: str, requete: list[str]) -> float | None:
    """Score d'un nom pour une requête, ou None s'il ne correspond pas.

    Chaque mot de la requête doit commencer un mot du nom, dans n'importe quel
    ordre : « yaourt nature » trouve « Yaourt, lait fermenté…, nature », qu'une
    recherche par sous-chaîne manquait entièrement.

    Le classement privilégie, dans l'ordre :
    - un nom qui commence par le premier mot cherché — « Pomme, crue » avant
      « Aligot (purée de pomme de terre) » ;
    - une correspondance exacte plutôt qu'un préfixe — « pomme » avant « pommes » ;
    - un nom court, donc probablement l'aliment de base plutôt qu'une préparation.
    """
    if not requete:
        return None
    jetons = mots(nom)
    if not jetons:
        return None

    for mot in requete:
        if not any(correspond(jeton, mot) for jeton in jetons):
            return None

    score = 0.0
    premier = requete[0]
    # Le bonus de tête passe par les mêmes règles que l'appariement : sans
    # cela, chercher « pommes » au pluriel privait le fruit (« Pomme, crue »)
    # de son avance, et le chausson aux pommes passait devant.
    if correspond(jetons[0], premier):
        score += 100
        if meme_mot(jetons[0], premier):
            score += 40
            # À flexion égale, la forme exacte l'emporte : « pomme » devant
            # « pommes de terre » quand on a tapé « pomme ».
            if jetons[0] == premier:
                score += 5
    # Chaque mot cherché présent sous une forme du même mot.
    score += 10 * sum(1 for mot in requete if any(meme_mot(j, mot) for j in jetons))
    score -= len(jetons)
    return score


# --- Ciqual ---------------------------------------------------------------------


def _nombre(brut: str) -> float | None:
    if brut in ("", "None"):
        return None
    try:
        return float(brut)
    except ValueError:
        return None


@lru_cache(maxsize=1)
def ciqual() -> tuple[Aliment, ...]:
    """Chargée une fois : 2 300 aliments, quelques centaines de kilo-octets."""
    if not CIQUAL_CSV.exists():
        log.warning("Table Ciqual absente (%s) : recherche d'aliments génériques désactivée", CIQUAL_CSV)
        return ()
    with CIQUAL_CSV.open(encoding="utf-8") as flux:
        return tuple(
            Aliment(
                source="ciqual",
                ref=ligne["code"],
                nom=ligne["nom"],
                marque=None,
                kcal=_nombre(ligne["kcal"]),
                proteines=_nombre(ligne["proteines"]),
                glucides=_nombre(ligne["glucides"]),
                lipides=_nombre(ligne["lipides"]),
                groupe=ligne["groupe"] or None,
            )
            for ligne in csv.DictReader(flux, delimiter=";")
        )


def chercher_ciqual(requete: str, limite: int = 12) -> list[Aliment]:
    termes = mots(requete)
    notes = [(pertinence(a.nom, termes), a) for a in ciqual()]
    retenus = [(s, a) for s, a in notes if s is not None]
    retenus.sort(key=lambda paire: (-paire[0], paire[1].nom))
    return [a for _, a in retenus[:limite]]


def aliment_ciqual(code: str) -> Aliment | None:
    return next((a for a in ciqual() if a.ref == code), None)


# --- Open Food Facts --------------------------------------------------------------


def nutriments_off(produit: dict) -> dict[str, float | None]:
    """Extrait les valeurs pour 100 g d'une fiche Open Food Facts."""
    n = produit.get("nutriments") or {}

    def lire(cle: str) -> float | None:
        valeur = n.get(cle)
        try:
            return round(float(valeur), 2) if valeur not in (None, "") else None
        except (TypeError, ValueError):
            return None

    kcal = lire("energy-kcal_100g")
    if kcal is None and lire("energy_100g") is not None:
        # Certaines fiches ne donnent que des kilojoules.
        kcal = round(lire("energy_100g") / 4.184, 1)

    portion = produit.get("serving_quantity")
    try:
        portion_g = float(portion) if portion not in (None, "") else None
    except (TypeError, ValueError):
        portion_g = None

    return {
        "kcal": kcal,
        "proteines": lire("proteins_100g"),
        "glucides": lire("carbohydrates_100g"),
        "lipides": lire("fat_100g"),
        "portion_g": portion_g if portion_g and portion_g > 0 else None,
    }


def _texte_localise(valeur) -> str | None:
    """Le moteur renvoie parfois un dictionnaire par langue, parfois une liste."""
    if isinstance(valeur, dict):
        return valeur.get("fr") or valeur.get("main") or next(iter(valeur.values()), None)
    if isinstance(valeur, list):
        return ", ".join(str(v) for v in valeur if v) or None
    return valeur or None


async def chercher_off(requete: str, limite: int = 10) -> list[Aliment]:
    """Interroge le moteur de recherche d'Open Food Facts.

    La base est collaborative : une bonne part des fiches n'a aucune valeur
    nutritionnelle. Celles-là sont écartées — un résultat sans calories ne sert
    à rien dans un journal — et les doublons nom + marque fusionnés.
    """
    if len(requete.strip()) < 2:
        return []
    try:
        async with httpx.AsyncClient(
            timeout=4.0, headers={"User-Agent": settings.user_agent}
        ) as client:
            reponse = await client.get(
                OFF_SEARCH_URL,
                params={
                    "q": requete,
                    "langs": "fr",
                    "page_size": 40,
                    "fields": "code,product_name,brands,nutriments,serving_quantity",
                },
            )
        reponse.raise_for_status()
        resultats = reponse.json().get("hits", [])
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("Recherche Open Food Facts indisponible pour %r : %s", requete, exc)
        raise

    vus: set[tuple[str, str]] = set()
    aliments: list[Aliment] = []
    for produit in resultats:
        nom = _texte_localise(produit.get("product_name"))
        code = str(produit.get("code") or "").strip()
        if not nom or not code:
            continue
        valeurs = nutriments_off(produit)
        if valeurs["kcal"] is None:
            continue
        marque = _texte_localise(produit.get("brands"))
        marque = marque.split(",")[0].strip() if marque else None
        cle = (normaliser(nom), normaliser(marque or ""))
        if cle in vus:
            continue
        vus.add(cle)
        aliments.append(
            Aliment(source="off", ref=code, nom=nom.strip(), marque=marque, **valeurs)
        )
        if len(aliments) >= limite:
            break
    return aliments
