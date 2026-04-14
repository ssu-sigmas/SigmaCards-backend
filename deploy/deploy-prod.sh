#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/sigmacards/SigmaCards-backend}"
BRANCH="${BRANCH:-main}"
TAG="${TAG:-latest}"

cd "$APP_DIR"

echo "[deploy] Updating repository ($BRANCH)..."
git fetch --all --prune
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "[deploy] Preparing env files..."
if [[ ! -f .env.prod ]]; then
  cp .env.prod.example .env.prod
  echo "[deploy] Created .env.prod from template. Fill secrets and rerun."
  exit 1
fi
if [[ ! -f .env.db.prod ]]; then
  cp .env.db.prod.example .env.db.prod
  echo "[deploy] Created .env.db.prod from template. Fill secrets and rerun."
  exit 1
fi

echo "[deploy] Starting stack with image tag: ${TAG}"
APP_IMAGE_TAG="$TAG" docker compose -f docker-compose.prod.yml pull
APP_IMAGE_TAG="$TAG" docker compose -f docker-compose.prod.yml up -d --remove-orphans

echo "[deploy] Applying database migrations"
APP_IMAGE_TAG="$TAG" docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head

echo "[deploy] Completed successfully"