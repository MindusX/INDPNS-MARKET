# Guide administrateur
- Rôles : buyer < seller < moderator < support < admin < superadmin. Seul un superadmin attribue admin/superadmin.
- Modération : *Moderation queue* → vérifier description, fichiers (statut de scan), décider (raison obligatoire pour rejeter/suspendre). Tout est historisé + journal d'audit.
- Reversements : approuver (écrit le débit), envoyer l'argent via votre prestataire, puis « Mark paid » avec la référence. Aucune exécution automatique.
- KYC / vérification boutique : à modifier dans `/admin/` (Shops) après validation réelle par le prestataire.
- Plans, commissions, licences, catégories : `/admin/`.
- Remboursement : *Orders & refunds* (appelle d'abord Stripe pour un paiement Stripe).
