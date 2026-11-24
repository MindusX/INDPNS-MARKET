#!/usr/bin/env bash
# Build Render : installation -> collectstatic -> check. Les migrations sont exécutées séparément (preDeployCommand).
set -o errexit
export DJANGO_SETTINGS_MODULE=config.settings.production
pip install --upgrade pip
pip install -r requirements.txt
python scripts/compile_po.py || true
python manage.py collectstatic --noinput
python manage.py check --deploy --fail-level ERROR
# Migrations "bootstrap" : uniquement si le dépôt n'en contient pas encore ET que vous l'avez demandé explicitement.
# Recommandé : générez-les en local (voir docs/DEPLOYMENT.md) et commitez-les.
if [ "${BOOTSTRAP_MIGRATIONS:-0}" = "1" ] && [ -z "$(find apps -path '*/migrations/0001_*.py' | head -1)" ]; then
  echo ">> BOOTSTRAP_MIGRATIONS=1 : génération des migrations initiales (création de tables uniquement)"
  python manage.py makemigrations accounts core catalog sellers licenses products orders payments commissions payouts reviews moderation notifications dashboard
fi
