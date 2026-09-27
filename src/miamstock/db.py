"""Accès SQLite : schéma, connexion par requête, migrations idempotentes."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timezone

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS locations (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    kind        TEXT    NOT NULL DEFAULT 'other',
    position    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
    barcode                 TEXT PRIMARY KEY,
    name                    TEXT NOT NULL,
    brand                   TEXT,
    net_quantity            TEXT,
    image_url               TEXT,
    categories              TEXT,
    nutriscore              TEXT,
    default_location_id     INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    default_shelf_life_days INTEGER,
    min_quantity            INTEGER NOT NULL DEFAULT 0,
    source                  TEXT NOT NULL DEFAULT 'off',
    created_at              TEXT NOT NULL,
    updated_at              TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lots (
    id          INTEGER PRIMARY KEY,
    barcode     TEXT    NOT NULL REFERENCES products(barcode) ON DELETE CASCADE,
    location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    quantity    INTEGER NOT NULL CHECK (quantity >= 0),
    expires_on  TEXT,
    note        TEXT,
    created_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lots_barcode ON lots(barcode);
CREATE INDEX IF NOT EXISTS idx_lots_expires ON lots(expires_on);

CREATE TABLE IF NOT EXISTS shopping_items (
    id         INTEGER PRIMARY KEY,
    barcode    TEXT UNIQUE REFERENCES products(barcode) ON DELETE CASCADE,
    label      TEXT,
    quantity   INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    checked    INTEGER NOT NULL DEFAULT 0,
    auto       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY,
    kind     TEXT NOT NULL,
    barcode  TEXT,
    lot_id   INTEGER,
    quantity INTEGER,
    detail   TEXT,
    at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_at ON events(at DESC);
"""

DEFAULT_LOCATIONS = [
    ("Frigo", "fridge", 0),
    ("Congélateur", "freezer", 1),
    ("Placard", "pantry", 2),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today_iso() -> str:
    return date.today().isoformat()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL : lectures concurrentes pendant qu'un bip écrit, sans verrou global.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def init_db() -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        count = conn.execute("SELECT COUNT(*) AS n FROM locations").fetchone()["n"]
        if count == 0:
            conn.executemany(
                "INSERT INTO locations (name, kind, position) VALUES (?, ?, ?)",
                DEFAULT_LOCATIONS,
            )


def log_event(
    conn: sqlite3.Connection,
    kind: str,
    *,
    barcode: str | None = None,
    lot_id: int | None = None,
    quantity: int | None = None,
    detail: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO events (kind, barcode, lot_id, quantity, detail, at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (kind, barcode, lot_id, quantity, detail, now_iso()),
    )
