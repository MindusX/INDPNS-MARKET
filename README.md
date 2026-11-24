# INDPNS Market

Marketplace internationale de produits numériques (EN/FR/ES) — Django 5, PostgreSQL (Neon), Render. Cible : `market.indpns.com`.

**Lisez d'abord `docs/PROJECT_STATUS.md`** (état honnête) puis `docs/DEPLOYMENT.md` (étape 0 : générer les migrations).

Démarrage local :
```bash
python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations accounts core catalog sellers licenses products orders payments commissions payouts reviews moderation notifications dashboard
python manage.py migrate && python manage.py seed_initial && python manage.py createsuperuser
python manage.py test tests
python manage.py runserver
```
Docs : `docs/` (variables, clés API, déploiement, architecture, guides).
