#!/bin/sh
set -e

echo "Exécution des migrations Alembic..."
alembic upgrade head

echo "Démarrage de l'application FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000