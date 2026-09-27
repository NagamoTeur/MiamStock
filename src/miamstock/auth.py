"""Authentification par code PIN partagé, stockée dans un cookie signé.

Le cookie ne contient qu'une date d'expiration et une signature HMAC : aucun
secret côté client, et un cookie fabriqué à la main ne passe pas la vérification.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

from fastapi import Depends, HTTPException, Request, Response, status

from .config import settings

COOKIE_NAME = "miamstock_session"


def _sign(payload: str) -> str:
    digest = hmac.new(settings.secret.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def issue_token(now: float | None = None) -> str:
    expires_at = int((now or time.time()) + settings.session_days * 86400)
    payload = str(expires_at)
    return f"{payload}.{_sign(payload)}"


def token_is_valid(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    payload, _, signature = token.rpartition(".")
    if not hmac.compare_digest(signature, _sign(payload)):
        return False
    try:
        return int(payload) > time.time()
    except ValueError:
        return False


def auth_required() -> bool:
    """Sans PIN configuré, l'app est ouverte (cas « strictement derrière le VPN »)."""
    return bool(settings.pin)


def pin_matches(candidate: str) -> bool:
    if not settings.pin:
        return True
    return hmac.compare_digest(candidate.strip(), settings.pin)


def set_session_cookie(response: Response, request: Request) -> None:
    # `secure` seulement en HTTPS, sinon le cookie serait refusé pendant le dev en http://localhost.
    is_https = request.url.scheme == "https" or request.headers.get(
        "x-forwarded-proto", ""
    ).startswith("https")
    response.set_cookie(
        COOKIE_NAME,
        issue_token(),
        max_age=settings.session_days * 86400,
        httponly=True,
        samesite="lax",
        secure=is_https,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def current_session(request: Request) -> bool:
    if not auth_required():
        return True
    return token_is_valid(request.cookies.get(COOKIE_NAME))


def require_session(authenticated: bool = Depends(current_session)) -> None:
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session requise"
        )
