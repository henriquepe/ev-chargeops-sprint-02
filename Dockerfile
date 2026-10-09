ARG DOCKER_LIBRARY=docker.io/library
FROM ${DOCKER_LIBRARY}/node:22-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ${DOCKER_LIBRARY}/python:3.13-slim
ENV PYTHONUNBUFFERED=1 DATA_DIR=/app/data FRONTEND_DIST=/app/static
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/dist /app/static
RUN useradd --create-home chargeops && mkdir -p /app/data && chown -R chargeops:chargeops /app
USER chargeops
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.simulator && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
