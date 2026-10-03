"""Application FastAPI : API JSON + service de la PWA compilée, dans un seul process."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import init_db
from .routers import diary as diary_router
from .routers import session as session_router
from .routers import shopping as shopping_router
from .routers import stock as stock_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("miamstock")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info("Base prête : %s", settings.db_path)
    if not settings.pin:
        log.warning(
            "MIAMSTOCK_PIN non défini : l'application est ouverte à quiconque atteint l'URL."
        )
    yield


app = FastAPI(title="MiamStock", version="0.1.0", lifespan=lifespan)

app.include_router(session_router.router)
app.include_router(stock_router.router)
app.include_router(shopping_router.router)
app.include_router(diary_router.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "web_built": settings.web_dist.joinpath("index.html").exists()}


# --- Service de la PWA -------------------------------------------------------
# Le front compilé est monté après l'API : une route /api/* ne peut jamais être
# masquée par un fichier statique.

_dist = settings.web_dist
_assets = _dist / "assets"

if _assets.is_dir():
    app.mount("/assets", StaticFiles(directory=_assets), name="assets")


@app.get("/sw.js", include_in_schema=False, response_model=None)
def service_worker() -> FileResponse | PlainTextResponse:
    path = _dist / "sw.js"
    if not path.is_file():
        return PlainTextResponse("", media_type="application/javascript")
    # no-store : sans ça, un service worker périmé peut servir indéfiniment
    # l'ancienne version de l'app depuis le cache du navigateur.
    return FileResponse(
        path,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store", "Service-Worker-Allowed": "/"},
    )


@app.get("/{full_path:path}", include_in_schema=False, response_model=None)
def spa_fallback(full_path: str, request: Request):
    """Toute URL non-API renvoie index.html : la navigation est gérée côté client."""
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    candidate = (_dist / full_path).resolve()
    if full_path and candidate.is_file() and candidate.is_relative_to(_dist.resolve()):
        return FileResponse(candidate)

    index = _dist / "index.html"
    if not index.is_file():
        return PlainTextResponse(
            "Le front n'est pas compilé. Lance : cd web && npm install && npm run build",
            status_code=503,
        )
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
