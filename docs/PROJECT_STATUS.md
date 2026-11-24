# PROJECT_STATUS — INDPNS Market

Date de livraison : 23 novembre 2026.

## ⚠️ Vérification réelle effectuée
Django n'a pas pu être installé dans l'environnement de livraison (pas d'accès réseau). **Aucun test n'a été exécuté, le serveur n'a jamais démarré, aucune migration n'a été générée.**
Contrôles réellement faits : compilation Python de tous les fichiers (`compileall`), cohérence des imports entre modules (analyse AST), équilibre des balises de templates, existence de toutes les routes `{% url %}`/`reverse()` référencées, compilation des traductions FR/ES et lecture du `.mo`.
Une première exécution (`makemigrations`, `migrate`, `python manage.py test tests`) est la **première action à faire** ; attendez-vous à quelques corrections de détail.
Les 37 tests fournis (`tests/test_core_flows.py`) couvrent : pages publiques, inscription/confirmation e-mail, mot de passe faible, verrouillage, reset, permissions par rôle, modération, filtres, validation ZIP, commissions, idempotence, grand livre immuable, remboursement, mode catalogue, produit gratuit, KYC/payout, téléchargements sécurisés, webhook Stripe, API. **Leur résultat est inconnu.**

## ✅ Implémenté (code écrit, non exécuté)
- Design system `tokens.css` (fond #F8F9FA, mode sombre persistant), 3 navigations indépendantes et centralisées, drawer mobile, sidebar rétractable.
- Pages publiques : accueil (données réelles uniquement, états vides), catalogue (filtres catégorie/prix/techno/licence/note/date/compat/gratuit, tri, pagination serveur), produit (licences, versions, avis vérifiés, similaires, favoris AJAX, signalement), vendeurs, profil vendeur, tarifs (depuis la base), pages d'aide, légales, contact, `/download/` PWA.
- Comptes : utilisateur custom e-mail, rôles, confirmation e-mail obligatoire, reset, verrouillage, rate limiting, sessions actives, historique de connexion, acheteur → vendeur.
- Vendeur : boutique, assistant produit en 7 étapes, validation de fichiers, SHA-256, statuts Draft/Pending/Approved/Rejected/Suspended/Archived.
- Modération avec historique + journal d'audit ; administration (utilisateurs/rôles, commandes/remboursements, reversements, signalements).
- Commandes, licences (clé UUID), factures imprimables, téléchargements signés temporaires liés à l'utilisateur.
- Paiements : `PaymentProvider` abstrait, Stripe Checkout + webhook signé idempotent + contrôle du montant, mode catalogue.
- Journal comptable append-only, commissions figées à l'achat, reversements bloqués sans KYC.
- Notifications + e-mails HTML, PWA (manifest, service worker sans cache des zones sensibles), i18n EN/FR/ES, Render/Neon/Docker.

## 🟡 Partiel
- Traductions : navigation, accueil, catalogue, produit, auth et dashboard principaux en FR/ES (~270 chaînes) ; le reste retombe en anglais. Les pages d'aide/légales ne sont traduites qu'en EN (légal : EN+FR). Les offres du pricing (champs en base) ne sont pas traduites.
- Licence PDF : page imprimable seulement (pas de PDF généré). Facture : page imprimable, pas de PDF.
- Recherche : `icontains` (simple et correct, non optimisé plein texte).
- Antivirus : intégration ClamAV écrite, jamais testée contre un vrai clamd. Sans antivirus, les fichiers sont « skipped » (visible des modérateurs).
- Tâches Celery : e-mails seulement ; scan synchrone après commit.
- Admin : pas d'interface dédiée pour traductions/CMS/litiges/abonnements (Django admin pour le reste).

## 🔑 Nécessite une clé / un service
SMTP, S3, Redis, Neon, Sentry (optionnel), Stripe, ClamAV — voir `API_KEYS_SETUP.md`.

## ⚖️ Intervention juridique
Les 8 textes légaux sont des **résumés brouillons** à faire rédiger/valider (CGU, vendeurs, confidentialité/RGPD, cookies, remboursement, PI, signalement, conservation). Aucune conformité n'est revendiquée. Consulter aussi sur la TVA/taxes de vente de produits numériques, les factures, et la détention de fonds de tiers (statut d'établissement de paiement).

## 🏦 Nécessite un compte fournisseur
Stripe (éligibilité du pays de l'entreprise à vérifier). **Stripe Connect Transfers non implémenté** : les reversements sont approuvés puis marqués payés à la main. KYC : statut saisi par l'équipe dans l'admin Django (pas d'intégration d'onboarding Connect). PayPal : non implémenté.

## ❌ Non implémenté
2FA TOTP (champ réservé), OAuth Google/GitHub (boutons désactivés), facturation des abonnements vendeurs (Pro/Business non encaissables : « Contact us »), coupons/promotions, affiliation (page « bientôt »), support lié aux commandes/litiges, demande de remboursement côté acheteur (remboursement initié par l'admin), statistiques avancées, notifications push, API d'écriture.

## 🐞 Problèmes connus / risques
- Pas de migrations livrées (voir DEPLOYMENT.md étape 0). Des dépendances circulaires entre apps (licenses/orders/products) peuvent nécessiter un second `makemigrations`.
- `Product` publié : l'édition de la description par le vendeur est verrouillée (seuls fichiers/prix modifiables).
- Les covers et galeries sont stockées publiquement ; les ACL publiques S3 dépendent de votre fournisseur.
- Prix et commissions des plans (Starter 15 %, Pro 10 % / 19 $, Business 7 % / 49 $) sont des **valeurs initiales de départ** à valider.
- Le code Mindus Forge (Flask) n'a **pas été réutilisé** : seules ses icônes PWA ont été regardées, puis remplacées par des icônes INDPNS générées.

## 🎯 Actions avant lancement commercial
1. Générer/commiter les migrations, exécuter les tests, corriger. 2. Configurer Neon, S3, SMTP, Redis. 3. Valider les textes légaux et la fiscalité. 4. Choisir et configurer le prestataire de paiement, tester en sandbox (webhooks, remboursement). 5. Définir le processus KYC/reversements réel. 6. Test de charge, revue de sécurité (pentest), sauvegardes. 7. Compléter traductions, ajouter les icônes/branding finaux. 8. `python manage.py check --deploy`.

## Taux de préparation (estimation honnête)
Code écrit pour l'essentiel du périmètre, mais **non exécuté** : on ne peut pas affirmer ≥ 90 %. Estimation prudente : ~55–65 % du périmètre demandé est codé ; la part vérifiée en exécution est de 0 % tant que les tests n'ont pas tourné.
