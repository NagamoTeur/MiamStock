"""Point d'entrée : `miamstock` lance uvicorn avec les réglages de l'environnement."""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    uvicorn.run(
        "miamstock.main:app",
        host=os.environ.get("MIAMSTOCK_HOST", "0.0.0.0"),
        port=int(os.environ.get("MIAMSTOCK_PORT", "8077")),
        # Derrière Tailscale Serve / un reverse proxy, on veut le vrai schéma
        # https pour que le cookie de session soit marqué Secure.
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
