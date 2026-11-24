# Déploiement (Render + Neon)

## Étape 0 — Générer et commiter les migrations (une seule fois, en local)
Le projet est livré **sans fichiers de migration** (ils ne pouvaient pas être générés sans exécuter Django dans l'environnement de livraison).
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # SECRET_KEY facultative en développement
python manage.py makemigrations accounts core catalog sellers licenses products orders payments commissions payouts reviews moderation notifications dashboard
python manage.py migrate
python manage.py seed_initial
python manage.py test tests
git add apps/*/migrations && git commit -m "Initial migrations"
```
Si `makemigrations` signale un problème de dépendance circulaire, relancez-le une seconde fois ; sinon corrigez et notez-le dans PROJECT_STATUS.md.
Option de secours : `BOOTSTRAP_MIGRATIONS=1` sur Render génère les migrations initiales au build (non persistées : à éviter en régime normal).

## Étape 1 — Services
Neon (`DATABASE_URL`), bucket S3, SMTP : voir `API_KEYS_SETUP.md`.

## Étape 2 — Render
*New → Blueprint* → sélectionner le dépôt. Renseigner les variables marquées `sync: false`.
- Build : `./build.sh` (install → compilation des traductions → collectstatic → `check --deploy`).
- Pre-deploy : `./scripts/predeploy.sh` (vérifie qu'aucune migration manquante, `migrate`, `seed_initial`). **Aucune migration destructrice automatique** : relisez chaque nouvelle migration avant de déployer (`autoDeploy: false`).
- Health check : `/healthz`.

## Étape 3 — Premier administrateur
```bash
python manage.py createsuperuser   # Render Shell
```
Puis `/admin/` (ou `ADMIN_URL`) : vérifier les plans (`SellerPlan`), types de licence, catégories ; définir les prix des plans et taux de commission.

## Étape 4 — Domaine
Ajouter `market.indpns.com` au service Render + enregistrement CNAME. HTTPS automatique.

## Sauvegardes / secrets
Activer les sauvegardes Neon (PITR) ; versionner le bucket S3 ; faire tourner `SECRET_KEY` et clés API régulièrement (la rotation de `SECRET_KEY` invalide sessions et liens signés).
