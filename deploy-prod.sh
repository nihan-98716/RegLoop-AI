#!/usr/bin/env bash
# deploy-prod.sh — Production deployment script for RegLoop AI (Linux / macOS)
#
# Usage:
#   chmod +x deploy-prod.sh
#   ./deploy-prod.sh
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - .env file populated (copy from .env.example and fill in secrets)
#
# What this script does:
#   1. Validates required environment variables are set
#   2. Pulls the latest code (if in a git repo)
#   3. Builds and starts all Docker services using PostgreSQL
#   4. Waits for the backend to become healthy before exiting

set -euo pipefail

echo "==> RegLoop AI — Production Deployment"

# ── 1. Environment validation ─────────────────────────────────────────────────
REQUIRED_VARS=("DATABASE_URL" "OPENAI_API_KEY")

for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "ERROR: Required environment variable '$var' is not set."
    echo "       Copy .env.example to .env and fill in all values."
    exit 1
  fi
done

# Export production database URL (PostgreSQL)
export PROD_DATABASE_URL="${DATABASE_URL}"

echo "  Database : ${DATABASE_URL%%@*}@***"
echo "  LLM      : ${LLM_PROVIDER:-openai}"

# ── 2. Build and start services ───────────────────────────────────────────────
echo "==> Building Docker images..."
docker compose build --no-cache

echo "==> Starting services..."
docker compose up -d

# ── 3. Health check ───────────────────────────────────────────────────────────
echo "==> Waiting for backend to become healthy..."
RETRIES=30
until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
  RETRIES=$((RETRIES - 1))
  if [[ $RETRIES -eq 0 ]]; then
    echo "ERROR: Backend health check timed out."
    docker compose logs backend --tail=50
    exit 1
  fi
  sleep 2
done

echo ""
echo "✅ RegLoop AI is running!"
echo "   Frontend  : http://localhost:3000"
echo "   API       : http://localhost:8000"
echo "   API Docs  : http://localhost:8000/docs"
