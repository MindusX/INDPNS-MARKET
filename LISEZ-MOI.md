# Liens dans les barres latérales + retrait de l'icône clair/sombre du haut

Copier le zip PAR-DESSUS le projet (mêmes chemins) et redéployer. Aucune commande à lancer.

## Pourquoi vous ne voyiez pas les liens
Le menu ☰ (celui du téléphone) est un composant écrit à la main : il ne contenait pas les nouvelles pages.
Et un vendeur qui se trouvait dans l'espace « Acheteur » ne les voyait pas non plus dans la barre de bureau.

## Maintenant
- Menu ☰ (mobile) : groupe « Vendeur » > « Payout methods » + « Identity verification » (avec l'étiquette « Action needed » tant que
  l'identité n'est pas vérifiée). Groupe « Administration » > « Identity checks » (rôle admin).
- Bandeau jaune en haut du menu ☰ pour un vendeur non vérifié : « Verify your identity to receive payouts » (lien direct).
- Barre latérale de bureau : les mêmes liens, y compris quand le vendeur est dans l'espace « Acheteur ».
- Un acheteur sans boutique ne voit rien de tout cela.
- Menu ☰ : votre photo de profil s'affiche maintenant à la place de l'initiale.
- Icône clair/sombre retirée des barres horizontales du haut (tableau de bord ET pages connexion/inscription).
  Elle reste disponible dans le menu ☰ et dans le pied de page.

Tests : python manage.py test tests.test_navigation_links
