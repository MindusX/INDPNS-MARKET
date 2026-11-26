#!/bin/sh
# Démarrage Render (Docker) : migrations -> seed -> gunicorn.
set -e
export DJANGO_SETTINGS_MODULE=config.settings.production

# Premier déploiement : si le dépôt n'a pas de migrations commitées, on génère les migrations INITIALES
# (création de tables uniquement). Recommandé ensuite : les générer en local et les commiter.
if [ -z "$(find apps -path '*/migrations/0001_*.py' | head -1)" ]; then
  echo ">> Aucune migration trouvée : génération des migrations initiales"
  python manage.py makemigrations accounts core catalog sellers licenses products orders payments commissions payouts reviews moderation notifications || echo "!! makemigrations a échoué"
fi

python manage.py migrate --noinput
# Synchronisation automatique du schéma : crée les tables/colonnes ajoutées depuis la première installation (additif, idempotent).
python manage.py sync_schema || echo "!! sync_schema a échoué (voir les erreurs ci-dessus)"
python manage.py seed_initial || echo "!! seed_initial a échoué"

exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-10000} --workers ${WEB_CONCURRENCY:-1} --timeout ${GUNICORN_TIMEOUT:-60} --access-logfile -
