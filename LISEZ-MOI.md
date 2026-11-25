# Image d'arrière-plan de la page d'accueil — INDPNS Market

Copier le contenu du zip PAR-DESSUS le projet, aux mêmes chemins. Aucun fichier Python, route ou migration modifié.

## Créés (2)
- static/images/hero/space-hero.webp      (1672x941, 129 Ko — l'original pesait 1,7 Mo)
- static/images/hero/space-hero-sm.webp   (900x507, 49 Ko — servi automatiquement sur mobile)

## Modifiés (2)
- templates/public/home.html  -> préchargement de l'image + bloc .market-hero (image derrière l'annonce et l'intro)
- static/css/home.css         -> bloc ajouté en fin de fichier (le reste est inchangé)

## Après déploiement
python manage.py collectstatic --noinput
