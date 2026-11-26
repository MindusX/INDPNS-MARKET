#!/usr/bin/env bash
# Exécuté avant chaque déploiement (Render preDeployCommand). Jamais de migration destructrice automatique.
set -o errexit
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py makemigrations --check --dry-run || { echo "ERREUR: des modèles ont changé sans migration commitée."; exit 1; }
python manage.py migrate --noinput
python manage.py sync_schema
python manage.py seed_initial
