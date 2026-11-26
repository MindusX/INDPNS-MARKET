# Correctif : photo de profil et couverture qui ne s'affichent pas

## Cause
1. En production, Django ne servait pas /media/ (réservé au mode DEBUG) -> images introuvables (icône "image cassée").
2. Même servis, les fichiers étaient écrits sur le disque de Render, EFFACÉ à chaque déploiement.
3. Sur mobile, la carte de couverture avait un padding qui la décalait et la faisait déborder.

## Correctif
- Médias publics (profils, couvertures, logos, visuels produits) stockés dans la base de données (table core_storedfile) :
  persistants sans S3. Activé automatiquement en production si S3 n'est pas configuré. Avec S3, rien ne change.
- Nouvelle route /media/<nom> : cache d'un an, X-Content-Type-Options: nosniff, CSP sandbox, seules les vraies images sont affichées.
- La table core_storedfile est créée automatiquement au démarrage par sync_schema (inclus ici).
- Mise en page mobile corrigée ; si une image est introuvable, un placeholder (initiale / dégradé) remplace l'icône cassée.

## Installation
Copier le zip sur le projet (mêmes chemins) et redéployer. Aucune commande à lancer.
Les photos téléversées AVANT ce correctif étaient sur le disque éphémère : elles sont perdues, il faut les téléverser à nouveau.
Tests : python manage.py test tests.test_db_storage tests.test_profiles tests.test_sync_schema
