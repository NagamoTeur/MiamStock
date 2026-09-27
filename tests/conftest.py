"""Fixtures : une base neuve par test, et pas un seul appel réseau vers Open Food Facts."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

TMP = Path(tempfile.mkdtemp(prefix="miamstock-tests-"))
os.environ["MIAMSTOCK_DATA_DIR"] = str(TMP)
os.environ["MIAMSTOCK_PIN"] = "1234"
os.environ["MIAMSTOCK_SECRET"] = "secret-de-test"

from fastapi.testclient import TestClient  # noqa: E402

from miamstock import openfoodfacts, service  # noqa: E402
from miamstock.config import settings  # noqa: E402
from miamstock.db import get_conn, init_db  # noqa: E402
from miamstock.main import app  # noqa: E402

FAKE_CATALOG = {
    "3017620422003": {
        "name": "Nutella",
        "brand": "Nutella",
        "net_quantity": "400 g",
        "image_url": "https://example.invalid/nutella.jpg",
        "categories": "pâtes à tartiner",
        "nutriscore": "e",
    },
    "3033490004743": {
        "name": "Yaourt nature",
        "brand": "Danone",
        "net_quantity": "4 x 125 g",
        "image_url": None,
        "categories": "yaourts",
        "nutriscore": "a",
    },
}


@pytest.fixture(autouse=True)
def fake_off(monkeypatch):
    """Open Food Facts est remplacé par un catalogue figé : tests hermétiques et rapides."""

    async def _fetch(barcode: str):
        entry = FAKE_CATALOG.get(barcode)
        return openfoodfacts.ProductInfo(**entry) if entry else None

    monkeypatch.setattr(openfoodfacts, "fetch_product", _fetch)
    monkeypatch.setattr("miamstock.routers.stock.fetch_product", _fetch)


@pytest.fixture(autouse=True)
def clean_db():
    if settings.db_path.exists():
        settings.db_path.unlink()
    for suffix in ("-wal", "-shm"):
        extra = Path(str(settings.db_path) + suffix)
        if extra.exists():
            extra.unlink()
    init_db()
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        test_client.post("/api/session", json={"pin": "1234"})
        yield test_client


@pytest.fixture
def anon_client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def locations(client):
    return {row["kind"]: row["id"] for row in client.get("/api/locations").json()}


@pytest.fixture
def journal():
    """Écrit des mouvements datés dans le passé.

    L'API horodate toujours au présent : sans cette porte dérobée, impossible de
    tester un rythme, qui n'existe que sur une durée.
    """
    from datetime import datetime, timedelta, timezone

    def ecrire(barcode: str, kind: str, quantity: int, il_y_a_jours: float):
        moment = datetime.now(timezone.utc) - timedelta(days=il_y_a_jours)
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO events (kind, barcode, quantity, at) VALUES (?, ?, ?, ?)",
                (kind, barcode, quantity, moment.isoformat(timespec="seconds")),
            )

    return ecrire


@pytest.fixture
def db():
    with get_conn() as conn:
        yield conn


__all__ = ["service"]
