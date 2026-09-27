# --- Étape 1 : compilation de la PWA -----------------------------------------
FROM node:22-alpine AS web

WORKDIR /build
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# --- Étape 2 : image finale ---------------------------------------------------
FROM python:3.13-slim

# L'API et le front sont servis par le même process : un seul port à exposer,
# pas de CORS, et une seule chose à surveiller sur le serveur.
WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

COPY --from=web /build/dist /app/web/dist

ENV MIAMSTOCK_WEB_DIST=/app/web/dist \
    MIAMSTOCK_DATA_DIR=/data \
    MIAMSTOCK_PORT=8077 \
    PYTHONUNBUFFERED=1

RUN useradd --uid 10001 --no-create-home --home-dir /data --shell /usr/sbin/nologin miam \
    && mkdir -p /data \
    && chown -R miam:miam /data

# Le conteneur démarre en root et redescend en uid 10001 dans l'entrypoint,
# après avoir rendu le volume inscriptible : un bind mount arrive avec les
# propriétaires de l'hôte, que la construction ne peut pas connaître.
COPY deploy/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

VOLUME ["/data"]
EXPOSE 8077

HEALTHCHECK --interval=60s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8077/api/health').read()"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["miamstock"]
