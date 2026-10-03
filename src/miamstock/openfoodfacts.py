"""Client Open Food Facts : API publique v2, sans clé, avec cache local en base.

Un produit déjà scanné une fois n'est plus jamais redemandé au réseau : c'est ce
qui rend le bip instantané au deuxième passage, et ce qui fait que l'app reste
utilisable même si Open Food Facts est indisponible.
"""

from __future__ import annotations

import logging

import httpx

from .config import settings

log = logging.getLogger(__name__)

FIELDS = ",".join(
    [
        "code",
        "product_name",
        "product_name_fr",
        "generic_name_fr",
        "brands",
        "quantity",
        "categories_tags",
        "image_front_small_url",
        "image_small_url",
        "nutriscore_grade",
        "nutriments",
        "serving_quantity",
    ]
)


class ProductInfo(dict):
    """Dictionnaire plat : name, brand, net_quantity, image_url, categories, nutriscore."""


def _pick_name(product: dict) -> str | None:
    for key in ("product_name_fr", "product_name", "generic_name_fr"):
        value = (product.get(key) or "").strip()
        if value:
            return value
    return None


def _readable_categories(tags: list[str] | None, brand: str | None = None) -> str | None:
    """Garde les trois catégories les plus spécifiques, sans la marque.

    Les tags arrivent préfixés par une langue ("en:", "fr:") qui ne dit rien de
    la langue du libellé, et vont du plus général au plus spécifique. Ils sont
    collaboratifs, donc parfois bruités : on retire au moins les tags qui ne font
    que répéter la marque.
    """
    if not tags:
        return None
    labels: list[str] = []
    for tag in tags:
        label = tag.split(":", 1)[-1].replace("-", " ").strip()
        if not label or (brand and label.casefold() == brand.casefold()):
            continue
        labels.append(label)
    unique = list(dict.fromkeys(labels))
    return ", ".join(unique[-3:]) or None


async def fetch_product(barcode: str) -> ProductInfo | None:
    """Interroge Open Food Facts. Renvoie None si inconnu ou si le réseau échoue."""
    url = f"{settings.off_base_url}/api/v2/product/{barcode}.json"
    try:
        async with httpx.AsyncClient(
            timeout=settings.off_timeout, headers={"User-Agent": settings.user_agent}
        ) as client:
            response = await client.get(url, params={"fields": FIELDS})
    except httpx.HTTPError as exc:
        log.warning("Open Food Facts injoignable pour %s : %s", barcode, exc)
        return None

    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        log.warning("Open Food Facts a répondu %s pour %s", response.status_code, barcode)
        return None

    try:
        payload = response.json()
    except ValueError:
        return None

    if payload.get("status") != 1:
        return None

    product = payload.get("product") or {}
    name = _pick_name(product)
    if not name:
        return None

    brands = (product.get("brands") or "").split(",")[0].strip() or None
    from .nutrition import nutriments_off

    valeurs = nutriments_off(product)
    return ProductInfo(
        kcal_100g=valeurs["kcal"],
        prot_100g=valeurs["proteines"],
        gluc_100g=valeurs["glucides"],
        lip_100g=valeurs["lipides"],
        portion_g=valeurs["portion_g"],
        name=name,
        brand=brands,
        net_quantity=(product.get("quantity") or "").strip() or None,
        image_url=product.get("image_front_small_url") or product.get("image_small_url"),
        categories=_readable_categories(product.get("categories_tags"), brands),
        nutriscore=(product.get("nutriscore_grade") or "").strip().lower() or None,
    )
