# INDPNS Market — mise à jour frontend

Copier `static/`, `templates/` et `scripts/` par-dessus le projet (mêmes chemins), puis commit + push.
Aucun fichier Python du backend n'est modifié ; aucune migration.

## Contenu
- static/css : tokens (clair #F8F9FA / sombre gris neutre), base, public, home, auth, dashboard
- static/js : main + modules (thème, nav, favoris, galerie/lightbox, filtres, UI, PWA), service-worker v2
- static/images : logo (SVG + PNG), hero, 8 visuels de catégories, 12 illustrations ; static/icons : icônes PWA
- templates : base publique, navbar (méga-menu), footer avancé, accueil, catalogue, produit, tarifs, pages d'aide, légal, erreurs, auth (écran scindé), dashboard (sidebar, topbar, accueils)
- scripts/gen_images.py : régénère logo/illustrations (python scripts/gen_images.py, nécessite Pillow)

## Notes
- Les anciens templates dashboard (library, orders, products…) restent valides : ils héritent du nouveau style via le CSS.
- Nouvelles chaînes : EN uniquement pour l'instant (FR/ES retombent sur l'anglais).
- Régénérer les statiques : `python manage.py collectstatic` (fait par le Dockerfile).
