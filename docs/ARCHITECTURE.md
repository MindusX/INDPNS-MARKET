# Architecture

Django 5 (SSR) + DRF (API publique en lecture) · PostgreSQL (Neon) · Redis/Celery · WhiteNoise · stockage S3.

| App | Rôle |
|---|---|
| core | audit, contact, utilitaires, rate-limit, validation de fichiers, stockage privé, pages statiques/légales, PWA, healthz |
| accounts | utilisateur custom (email), rôles, vérification e-mail signée, verrouillage anti-brute-force, sessions suivies, historique de connexion |
| sellers | plans (table `SellerPlan`, source de la page Tarifs), boutiques, KYC/vérification (statuts) |
| catalog | catégories (2 niveaux), technologies |
| products | produits, versions (fichiers privés + SHA-256 + scan), favoris, signalements, catalogue filtrable, API |
| licenses | types de licence, prix par licence, licences émises (clé UUID) |
| orders | commandes, lignes (commission figée à l'achat), factures, téléchargements signés |
| payments | `PaymentProvider` abstrait, Stripe, webhooks idempotents |
| commissions | journal comptable **append-only** (aucun solde mutable) |
| payouts | demandes de reversement (bloquées sans KYC), approbation, suivi |
| reviews | avis liés à une licence achetée |
| moderation | décisions de modération historisées |
| notifications | centre de notifications + e-mails (Celery si Redis) |
| dashboard | espaces acheteur / vendeur / admin |

## Les trois navigations (indépendantes, centralisées)
- Public : `templates/public/base.html` inclut `components/navbar.html` et `components/footer.html` (uniques).
- Auth : `templates/auth/base_auth.html` + `auth_header.html` / `auth_footer.html`.
- Dashboard : `templates/dashboard/base_dashboard.html` + `sidebar.html`, `topbar.html`, `mobile_navigation.html` ; menus par rôle dans `apps/dashboard/navigation.py`.
Couleurs : uniquement `static/css/tokens.css` (`--color-bg: #F8F9FA`, mode sombre via `data-theme="dark"`).

## Flux financier
Achat → `Order(pending)` → provider Checkout → webhook signé → `mark_order_paid` (verrou de ligne, idempotent) → licence + facture + écritures `sale_earning` (+) / `platform_commission` (+). Remboursement → écritures inverses + licence révoquée. Solde vendeur = somme des écritures ; retirable = écritures plus anciennes que `PAYOUT_HOLD_DAYS`, moins demandes en cours, **uniquement si KYC vérifié**.

## Mode catalogue
Sans provider configuré (`PAYMENT_PROVIDER` vide) : navigation OK, produits gratuits obtenables, bouton d'achat désactivé et message clair ; aucun paiement n'est jamais simulé.
