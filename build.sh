#!/usr/bin/env bash
# build.sh — Render build script
# Runs on every deployment. All steps are idempotent and safe to re-run.

set -e  # Exit immediately if any command fails

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files (including Django admin CSS/JS)..."
# --clear removes stale files from previous builds to avoid manifest conflicts
python manage.py collectstatic --noinput --clear

echo "==> Running database migrations..."
python manage.py migrate

echo "==> Creating superuser if not present..."
# Reads DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD
# from env vars. Safe to run on every deploy — skips if superuser already exists.
python manage.py create_superuser_if_missing

echo "==> Build complete!"