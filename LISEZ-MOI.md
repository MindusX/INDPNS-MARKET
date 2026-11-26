# Migration automatique au démarrage

Désormais, à CHAQUE démarrage du service (docker-entrypoint.sh, et scripts/predeploy.sh sur Render natif) :
  migrate  ->  sync_schema  ->  seed_initial  ->  gunicorn

`sync_schema` compare les modèles Django à la base et CRÉE les tables et colonnes manquantes.
Additif uniquement (jamais de suppression ni de modification), idempotent, avec le schema_editor de Django.
Elle règle l'erreur "column accounts_user.username does not exist" et toutes les futures du même type.

Logs au démarrage :  "Schéma à jour : rien à synchroniser."  ou  "Synchronisé (11) : colonne accounts_user.username, ..."

## Installation
1. Copier le zip sur le projet (mêmes chemins) et redéployer. Rien d'autre à faire : le site se répare au démarrage.
2. Si vous aviez déjà copié l'ancien correctif, supprimez apps/accounts/management/commands/ensure_profile_schema.py (remplacé).
3. Optionnel : python manage.py test tests.test_sync_schema

scripts/fix_profile_columns.sql reste disponible pour réparer immédiatement via Neon sans attendre le redéploiement.

Limite : les changements destructifs ou de type (renommer/supprimer/modifier une colonne) restent à faire avec une vraie migration
commitée ; sync_schema ne s'en occupe volontairement pas.
