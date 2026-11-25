# INDPNS Market — mise à jour du frontend (identité bleu + jaune, menu latéral central, pages juridiques)

Aucun fichier Python, aucune migration, aucune route, aucun modèle ni mécanisme de sécurité n'est modifié.
Les 42 fichiers ci-dessous se copient **par-dessus le projet, aux mêmes chemins**.

## Fichiers créés (8)
- `static/css/legal.css`
- `static/css/sidebar.css`
- `static/js/modules/legal.js`
- `static/js/modules/sidebar.js`
- `templates/components/icon_sprite.html`
- `templates/components/menu_button.html`
- `templates/components/sidebar.html`
- `templates/public/legal/_title.html`

## Fichiers modifiés (34)
- `locale/fr/LC_MESSAGES/django.mo`
- `locale/fr/LC_MESSAGES/django.po`
- `static/css/auth.css`
- `static/css/base.css`
- `static/css/dashboard.css`
- `static/css/home.css`
- `static/css/public.css`
- `static/css/tokens.css`
- `static/images/logo/favicon.svg`
- `static/images/logo/logo-mark.svg`
- `static/js/main.js`
- `static/js/modules/nav.js`
- `static/js/service-worker.js`
- `templates/auth/base_auth.html`
- `templates/auth/become_seller.html`
- `templates/auth/components/auth_footer.html`
- `templates/auth/components/auth_header.html`
- `templates/auth/register.html`
- `templates/components/head.html`
- `templates/dashboard/base_dashboard.html`
- `templates/dashboard/components/topbar.html`
- `templates/public/components/footer.html`
- `templates/public/components/navbar.html`
- `templates/public/components/product_card.html`
- `templates/public/legal/cookies.html`
- `templates/public/legal/ip.html`
- `templates/public/legal/page.html`
- `templates/public/legal/privacy.html`
- `templates/public/legal/refund.html`
- `templates/public/legal/report.html`
- `templates/public/legal/retention.html`
- `templates/public/legal/seller-terms.html`
- `templates/public/legal/terms.html`
- `templates/public/product_detail.html`

## Fonctionnalités ajoutées
**Identité visuelle** — `tokens.css` : palette (gris clair #F8F9FA, blanc, bleu, jaune #FACC15, texte #1F2937, bordures #E5E7EB) + jaunes dérivés (`--color-yellow-soft`, `--color-yellow-ink`) pour clair et sombre.
Jaune utilisé comme accent : badge *Premium* sur les cartes produit payantes, indicateur de l'élément actif (menu latéral, navigation, menus juridiques, tableau de bord), bandeau « mode catalogue », champs « À compléter », boutons secondaires `.btn-accent` (« Devenir vendeur » du menu, bouton du bandeau d'accueil du tableau de bord et du panneau d'appel à l'action), logo (barre centrale), bordure du pied de page.
Le bleu reste dominant. Accessibilité : le jaune sert toujours de fond avec texte #1F2937 (9,6:1) ou de repère graphique, jamais de texte jaune sur fond clair.
> Écart volontaire : le texte blanc sur #3B82F6 n'atteint que 3,7:1 (WCAG AA exige 4,5:1). Les boutons et pastilles à texte blanc utilisent donc le bleu existant #2563EB (5,2:1) ; #3B82F6 reste la couleur de marque (focus, repères, aplats). Le bleu du mode sombre a été légèrement renforcé (4,4 → 5,2:1).

**Barre latérale centrale** — `templates/components/sidebar.html` (+ `sidebar.css`, `modules/sidebar.js`, `menu_button.html`, `icon_sprite.html`). Incluse **une seule fois** par chaque gabarit de base : pages publiques (via `navbar.html`), authentification (`base_auth.html`), tableau de bord (`base_dashboard.html`). Pour l'utiliser ailleurs : `{% include "components/sidebar.html" %}` + `{% include "components/menu_button.html" %}`.
Ouverture par l'icône de menu (en-tête public, en-tête d'authentification, barre du tableau de bord), fermeture par le bouton ✕, le clic sur l'arrière-plan ou Échap ; animation fluide, voile + léger flou ; panneau 340 px (≤ 88 % de l'écran sur mobile) ; focus déplacé dans le panneau puis rendu au bouton, piège à Tab, panneau `inert` quand fermé, `aria-expanded`, `role=dialog`/`aria-modal`, défilement de la page bloqué, `prefers-reduced-motion` respecté.
Contenu selon la session : visiteur (Accueil, Explorer, Catégories, Premium, Vendeurs, À propos, Centre d'aide, Support, Connexion, Inscription) ; connecté (Tableau de bord, Mes achats, Mes téléchargements, Mes favoris, Notifications, Profil et paramètres, Sécurité, Support, Déconnexion en POST) ; vendeur (`user.is_seller`) ; administration (`user.is_internal`, avec Rapports à partir du rôle *support* et Utilisateurs/Commandes/Reversements à partir du rôle *admin*, comme les décorateurs existants).
**Le menu ne fait qu'afficher ou masquer des liens** : les contrôles d'accès restent ceux des vues (`login_required`, `seller_required`, `staff_role_required`).
Seuls des liens vers des routes existantes sont utilisés (vérifié automatiquement : tous les `{% url %}` des gabarits existent, sauf `downloads:request`, déjà présent dans `library.html` avant cette mise à jour et définie dans `apps/orders/urls_downloads.py`).
Le « Profil » et les « Paramètres du compte » partagent la page existante `dashboard:buyer_profile` (une seule entrée, pas de doublon).

**Pied de page** — refait : logo, description, 5 colonnes (Marketplace, Catégories, Vendre, Aide, Mentions et politiques), colonnes repliables sur mobile, liens : confidentialité, mentions légales, CGU, CGV, cookies, remboursement, propriété intellectuelle/licences, politique vendeur, contact. Liens juridiques aussi ajoutés sur l'inscription, l'ouverture de boutique, le pied des pages d'authentification et la fiche produit (à côté de l'achat).

**Pages juridiques** — nouvelle mise en page (menu des documents, sommaire « Sur cette page » généré, date de mise à jour fixe, bandeau « projet à valider », documents liés, impression) et contenus FR + EN réécrits pour une marketplace de produits numériques. Tous les éléments inconnus sont marqués **« À compléter par INDPNS : … »** (raison sociale, adresse, immatriculation, représentant, hébergeur, droit applicable, durées, âge minimum, taxes, sous-traitants…). Aucune société, adresse ou conformité n'est inventée. Les textes sont des **projets à faire valider par un juriste**.
Contrainte : seules 8 URL juridiques existent dans le backend (`LEGAL_PAGES`) et on ne les modifie pas. Les 10 documents demandés sont donc répartis ainsi :
| Document demandé | Emplacement |
|---|---|
| Politique de confidentialité | `/legal/privacy/` |
| Mentions légales | `/legal/terms/#legal-notice` |
| CGU | `/legal/terms/#terms-of-use` |
| CGV | `/legal/terms/#terms-of-sale` |
| Cookies | `/legal/cookies/` |
| Remboursement et annulation | `/legal/refund/` |
| Propriété intellectuelle **et licences des produits** | `/legal/ip/` (section `#licenses`) |
| Politique vendeur | `/legal/seller-terms/` |
| Contact juridique / réclamations | `/legal/report/` |
| Conservation des données (existant) | `/legal/retention/` |
Pour disposer d'URL dédiées plus tard, il suffira d'ajouter des clés dans `LEGAL_PAGES` (`apps/core/views.py`) et un gabarit par clé : changement backend volontairement **non fait** ici.

**Autres** : `service-worker.js` passe en `indpns-v3` (sinon les anciens CSS/JS restent servis depuis le cache des visiteurs) ; ancien tiroir mobile supprimé (CSS, JS, HTML) au profit du composant central ; traductions FR des nouvelles chaînes (`django.po` + `django.mo` recompilé).

## Dépendances
Aucune nouvelle dépendance (ni Python, ni npm, ni CDN).

## Intégration
1. Décompresser l'archive **par-dessus** le projet (mêmes chemins).
2. `python manage.py collectstatic --noinput` (fait par le Dockerfile au build).
3. Redéployer, puis vider le cache navigateur une fois si besoin.
4. Faire relire les 8 pages juridiques par un juriste et remplir les champs « À compléter par INDPNS » (recherche : `class="todo"`).

## Tests effectués
Django n'étant pas installable dans l'environnement de travail (pas de réseau), les gabarits ont été rendus avec un convertisseur Django→Jinja (sous-ensemble de balises utilisé), puis testés dans Chromium (Playwright) via un serveur HTTP local avec les vrais fichiers `static/`.
- ✅ Menu (bureau 1280 px et mobile 390 px) : ouverture, fermeture (✕, arrière-plan, Échap), `aria-expanded`, focus à l'ouverture et rendu à la fermeture, piège à Tab/Shift+Tab sur 60 appuis, défilement bloqué puis rétabli, largeur du panneau, `prefers-reduced-motion`.
- ✅ Liens du menu par rôle (visiteur, acheteur, vendeur, modérateur, admin) : présence/absence attendues ; déconnexion en POST.
- ✅ Les 8 pages juridiques en FR et en EN : titre, sommaire généré, aucun reste de balise Django, ancres (`#legal-notice`, `#terms-of-use`, `#terms-of-sale`, `#licenses`, `#infringement`, `#rights`), 8 liens de navigation juridique, liens juridiques du pied de page.
- ✅ Aucun débordement horizontal (10 pages × 2 largeurs), aucune erreur JavaScript, aucune ressource CSS/JS/image en 404 (hors `healthz` et service worker, absents du banc d'essai).
- ✅ Page de tableau de bord (coque + menu central) sur bureau et mobile.
- ✅ Tous les noms `{% url %}` des gabarits comparés aux `urls.py` ; contrastes WCAG calculés (voir ci-dessus) ; analyse des secrets dans `static/` et `templates/` : rien.
- ⚠️ Non testés : rendu avec le vrai moteur Django et la vraie base (aucun accès), pages produit/explorer/boutiques/tarifs avec données réelles, rendu iOS/Android physiques (émulation de viewport seulement), lecteurs d'écran, ES (les chaînes nouvelles retombent sur l'anglais, comme avant).

## Reste à faire / limites
- Icônes PNG (`logo-mark.png`, `static/icons/*`, `og-image.png`) non régénérées : elles gardent l'ancien logo sans barre jaune (`scripts/gen_images.py` permet de les refaire avec Pillow).
- Pages secondaires (explorer, boutiques, tarifs, aide, tableau de bord détaillé) héritent de la nouvelle palette et des composants par le CSS partagé ; je n'ai pas refait leur mise en page une à une.
- Gabarits dashboard « seller/admin » : hérités tels quels (leur barre latérale locale reste ; le menu central s'y ajoute).
- Traduction ES des nouvelles chaînes, et textes juridiques ES (retombent sur l'anglais).
