# Profil avancé + lien public partageable — INDPNS Market

Copier le contenu du zip PAR-DESSUS le projet (mêmes chemins).

## Après copie (obligatoire : nouveaux champs sur User)
python manage.py makemigrations accounts
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py test tests.test_profiles

## Nouveautés
- Page Profil & paramètres : photo, couverture, nom, identifiant, accroche, bio, localisation, site, GitHub / X / LinkedIn, visibilité.
- Lien public : /u/<identifiant>/ (privé par défaut, l'utilisateur l'active). Boutons Copier / Partager.
- Images ré-encodées en WebP (recadrage, EXIF supprimé, nom aléatoire) ; refus des faux fichiers, SVG, GIF.
- Avatar affiché dans la barre du dashboard et le menu du site.

## Attention production
Sans stockage S3 configuré, les images vont sur le disque local de Render (éphémère, perdu à chaque déploiement). Configurez S3 (variables AWS_*) pour conserver les photos.
