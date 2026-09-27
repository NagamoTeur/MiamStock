"""Configuration, lue dans l'environnement avec des defaults utilisables tels quels."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    db_path: Path
    pin: str | None
    secret: str
    session_days: int
    user_agent: str
    off_base_url: str
    off_timeout: float
    urgent_days: int
    soon_days: int
    web_dist: Path


def _load_or_create_secret(data_dir: Path) -> str:
    """Le secret de signature des sessions survit aux redémarrages.

    Sans persistance, chaque restart déconnecterait tous les téléphones du foyer.
    """
    from_env = os.environ.get("MIAMSTOCK_SECRET")
    if from_env:
        return from_env
    path = data_dir / "secret.key"
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = secrets.token_urlsafe(32)
    data_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return value


def _default_web_dist() -> Path:
    """Le front compilé, cherché aux deux endroits où il peut se trouver.

    En dev l'app est installée en editable depuis les sources (`web/dist` à la
    racine du dépôt) ; dans l'image Docker elle est copiée à côté du paquet.
    """
    from_env = os.environ.get("MIAMSTOCK_WEB_DIST")
    if from_env:
        return Path(from_env).expanduser().resolve()
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "web" / "dist",  # dépôt en editable : src/miamstock -> racine
        here.parent / "web",               # paquet installé : front copié dans le module
    ]
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return candidates[0]


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("MIAMSTOCK_DATA_DIR", "./data")).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = Path(os.environ.get("MIAMSTOCK_DB", str(data_dir / "miamstock.db"))).expanduser()
    pin = os.environ.get("MIAMSTOCK_PIN") or None
    return Settings(
        data_dir=data_dir,
        db_path=db_path,
        pin=pin,
        secret=_load_or_create_secret(data_dir),
        session_days=_env_int("MIAMSTOCK_SESSION_DAYS", 365),
        # Open Food Facts demande un User-Agent identifiant l'application.
        user_agent=os.environ.get(
            "MIAMSTOCK_USER_AGENT", "MiamStock/0.1 (self-hosted home inventory)"
        ),
        off_base_url=os.environ.get("MIAMSTOCK_OFF_URL", "https://world.openfoodfacts.org"),
        off_timeout=float(os.environ.get("MIAMSTOCK_OFF_TIMEOUT", "8")),
        urgent_days=_env_int("MIAMSTOCK_URGENT_DAYS", 3),
        soon_days=_env_int("MIAMSTOCK_SOON_DAYS", 7),
        web_dist=_default_web_dist(),
    )


settings = load_settings()
