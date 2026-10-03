"""Construit la table d'aliments génériques à partir de Ciqual (ANSES).

Ciqual est la table de composition nutritionnelle officielle française :
environ 3 000 aliments génériques — une pomme, du riz cuit, un blanc de
poulet — que Open Food Facts, base de produits emballés, couvre mal.

Licence Ouverte / Etalab : réutilisation libre, avec mention de la source.

Usage :
    python scripts/build_ciqual.py <dossier contenant les XML Ciqual>

Le résultat, src/miamstock/data/ciqual.csv, est versionné : l'application
le charge au démarrage et n'a jamais besoin du réseau pour chercher un
aliment générique.
"""

from __future__ import annotations

import csv
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Codes des constituants dans Ciqual 2020.
KCAL = "328"        # Énergie, règlement UE 1169/2011 — celle des étiquettes
PROTEINES = "25000"
GLUCIDES = "31000"
LIPIDES = "40000"
VOULUS = {KCAL: "kcal", PROTEINES: "proteines", GLUCIDES: "glucides", LIPIDES: "lipides"}

SORTIE = Path(__file__).resolve().parents[1] / "src" / "miamstock" / "data" / "ciqual.csv"


def texte(element: ET.Element, balise: str) -> str:
    noeud = element.find(balise)
    return (noeud.text or "").strip() if noeud is not None else ""


def valeur(brute: str) -> float | None:
    """Ciqual mêle chiffres, « traces », « < 0,5 » et « - ».

    « - » signifie « non mesuré » : on garde l'absence plutôt que d'inventer
    un zéro. « traces » et « < x » sont sous le seuil de détection, donc
    nutritionnellement nuls à l'échelle d'un journal de repas.
    """
    brute = brute.strip().lower()
    if not brute or brute == "-":
        return None
    if brute == "traces" or brute.startswith("<"):
        return 0.0
    brute = re.sub(r"[^0-9,.\-]", "", brute).replace(",", ".")
    try:
        return round(float(brute), 2)
    except ValueError:
        return None


# Un « < » qui n'ouvre pas une balise : « (<1° alc.) », « < 0,5 ».
CHEVRON_ORPHELIN = re.compile(r"<(?![A-Za-z/?!])")
# Un « & » qui n'introduit pas une entité : « elle & Vire », « lettuce & tomato ».
ESPERLUETTE_ORPHELINE = re.compile(r"&(?![A-Za-z]+;|#\d+;|#x[0-9A-Fa-f]+;)")


def assainir(source: Path, destination: Path) -> Path:
    """Rend lisible un XML Ciqual mal formé.

    Les fichiers publiés par l'ANSES contiennent des chevrons et des
    esperluettes bruts dans le texte — « Panaché (<1° alc.) », « < 0,5 »,
    « elle & Vire ».
    C'est invalide en XML et tout parseur strict refuse le fichier. On échappe
    ces chevrons orphelins et on réécrit en UTF-8, plutôt que de corriger les
    données à la main, ce qui ne survivrait pas à la prochaine version de Ciqual.
    """
    texte_brut = source.read_bytes().decode("windows-1252")
    texte_brut = texte_brut.replace('encoding="windows-1252"', 'encoding="utf-8"', 1)
    # L'ordre compte : échapper les « & » avant d'introduire les « &lt; ».
    texte_brut = ESPERLUETTE_ORPHELINE.sub("&amp;", texte_brut)
    texte_brut = CHEVRON_ORPHELIN.sub("&lt;", texte_brut)
    destination.write_text(texte_brut, encoding="utf-8")
    return destination


def construire(dossier: Path) -> int:
    propre = Path(tempfile.mkdtemp(prefix="ciqual-"))

    def fichier(prefixe: str) -> Path:
        trouves = sorted(dossier.glob(f"{prefixe}_*.xml"))
        if not trouves:
            raise SystemExit(f"{prefixe}_*.xml introuvable dans {dossier}")
        return assainir(trouves[0], propre / trouves[0].name)

    groupes: dict[str, str] = {}
    for g in ET.parse(fichier("alim_grp")).getroot():
        code = texte(g, "alim_grp_code")
        if code and code not in groupes:
            groupes[code] = texte(g, "alim_grp_nom_fr")

    aliments: dict[str, dict] = {}
    for a in ET.parse(fichier("alim")).getroot():
        code = texte(a, "alim_code")
        nom = texte(a, "alim_nom_fr")
        if code and nom:
            aliments[code] = {
                "code": code,
                "nom": nom,
                "groupe": groupes.get(texte(a, "alim_grp_code"), ""),
            }

    # 57 Mo : lecture en flux, chaque élément est libéré aussitôt traité.
    for _, element in ET.iterparse(fichier("compo"), events=("end",)):
        if element.tag != "COMPO":
            continue
        code = texte(element, "alim_code")
        constituant = texte(element, "const_code")
        if code in aliments and constituant in VOULUS:
            aliments[code][VOULUS[constituant]] = valeur(texte(element, "teneur"))
        element.clear()

    # Un aliment sans énergie connue est inutilisable dans un journal de calories.
    retenus = [a for a in aliments.values() if a.get("kcal") is not None]
    retenus.sort(key=lambda a: a["nom"].lower())

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as flux:
        ecrivain = csv.writer(flux, delimiter=";")
        ecrivain.writerow(["code", "nom", "groupe", "kcal", "proteines", "glucides", "lipides"])
        for a in retenus:
            ecrivain.writerow([
                a["code"], a["nom"], a["groupe"], a["kcal"],
                a.get("proteines"), a.get("glucides"), a.get("lipides"),
            ])
    return len(retenus)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    n = construire(Path(sys.argv[1]))
    print(f"{n} aliments écrits dans {SORTIE}")
