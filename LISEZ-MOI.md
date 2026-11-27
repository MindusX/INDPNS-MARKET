# Comptes de réception (PayPal / carte bancaire) + vérification d'identité (KYC)

Copier le zip PAR-DESSUS le projet (mêmes chemins) et redéployer. Les nouvelles tables/colonnes sont créées
automatiquement au démarrage par sync_schema (déjà installé). Rien d'autre à lancer.

## Nouvelles pages
Vendeur  : Tableau de bord > Vendeur > « Payout methods » (/dashboard/seller/payout-methods/)
           Tableau de bord > Vendeur > « Identity verification » (/dashboard/seller/verification/)
Équipe   : Tableau de bord > Admin > « Identity checks » (/dashboard/admin/kyc/) — rôle admin minimum

## À configurer (variables d'environnement Render)
1. KYC_ENCRYPTION_KEY  (OBLIGATOIRE si SECRET_KEY n'est pas fixe) — chiffre les pièces d'identité en base :
     python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ⚠ Conservez cette clé : sans elle, les documents déjà envoyés sont illisibles. Rotation : "nouvelle,ancienne".
   Sans clé stable, l'envoi de documents est automatiquement DÉSACTIVÉ (aucune perte de données).
2. PayPal (« Se connecter avec PayPal ») — réutilise PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET (+ PAYPAL_SANDBOX=true pour tester).
   Dans developer.paypal.com > votre application > Features : activer « Log in with PayPal ».
     - Return URL            : https://VOTRE-DOMAINE/dashboard/seller/payout-methods/paypal/callback/
     - Informations demandées : « Full name », « Email address », et « Account verification / PayPal account ID (payer_id) »
   SITE_URL doit être l'adresse publique exacte du site (https://…).
3. Carte / compte bancaire — réutilise STRIPE_SECRET_KEY. Dans le tableau de bord Stripe : activer **Connect**
   (comptes « Express »). Le vendeur est redirigé vers la page hébergée par Stripe : carte et IBAN ne passent jamais par nos serveurs.
4. Optionnel : KYC_PURGE_DOCS_ON_APPROVAL=true (supprime les images dès l'approbation) ;
   python manage.py purge_kyc_documents --days 90 (supprime les images des dossiers traités depuis 90 jours).

## Comportement
- Retraits : un moyen de paiement connecté ET une identité vérifiée sont désormais exigés. La destination est figée sur chaque
  demande et visible par l'admin (Admin > Payouts > « Send to »).
- KYC : envoi (identité, adresse, pièce recto/verso, selfie) -> « En attente » -> un admin approuve ou refuse (motif obligatoire,
  notifié au vendeur, nouvel envoi possible). L'approbation passe shop.kyc_status à « verified » (déblocage des retraits).
- Sécurité : images ré-encodées (EXIF supprimé), chiffrées (Fernet), jamais d'URL publique ; seuls les admins les voient, via une vue
  qui écrit une entrée d'audit à chaque consultation ; un admin ne peut pas valider sa propre boutique.

## Limites (honnêtes)
- L'argent n'est PAS envoyé automatiquement : l'admin continue d'approuver puis de marquer « payé » (comme avant) ; il voit maintenant
  exactement où verser (PayPal / carte). Les virements automatiques (PayPal Payouts, Stripe Transfers) sont une étape suivante.
- La vérification d'identité est manuelle (revue humaine), sans fournisseur automatisé de type Stripe Identity / Onfido.
- Les flux PayPal/Stripe n'ont pas pu être testés avec de vrais comptes ici : ils sont validés contre un faux serveur PayPal et des
  simulations Stripe. Faites un essai en sandbox (PAYPAL_SANDBOX=true, clés Stripe de test) avant la production.

Tests : python manage.py test tests.test_payout_methods tests.test_kyc
