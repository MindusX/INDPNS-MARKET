# Configuration des clés et services

## 1. Neon (PostgreSQL)
1. https://neon.tech → créer un projet → copier la *connection string* (préférer l'hôte `-pooler`).
2. Render → Environment → `DATABASE_URL` = cette URL (garder `sslmode=require`).
3. Le code détecte `-pooler` et désactive les curseurs serveur / requêtes préparées (PgBouncer). Docs : https://neon.tech/docs/connect/connection-pooling

## 2. Render
Blueprint : *New → Blueprint* → dépôt Git → `render.yaml`. Docs : https://render.com/docs/blueprint-spec

## 3. Stockage S3 (obligatoire en production)
Le disque Render est éphémère. Créez un bucket (AWS S3, Cloudflare R2, Backblaze B2…), un utilisateur avec accès restreint à ce bucket, puis renseignez les `AWS_*`.
Les fichiers vendus sont écrits sous le préfixe `private/` (ACL privée, URL présignée courte). Les covers/galeries sous `public/` (lecture publique) — vérifiez que votre fournisseur autorise les ACL publiques, sinon exposez `public/` via une politique de bucket/CDN.
Docs : https://docs.aws.amazon.com/s3/ · https://developers.cloudflare.com/r2/

## 4. SMTP
Brevo, Postmark, SES, Mailgun… Renseignez `EMAIL_*` et `DEFAULT_FROM_EMAIL`, puis configurez SPF/DKIM/DMARC du domaine. Testez : inscription → réception du lien.

## 5. Stripe (uniquement si votre pays d'entreprise est éligible)
Vérifiez l'éligibilité : https://stripe.com/global — et Connect : https://docs.stripe.com/connect
1. Compte Stripe en mode test → clés `sk_test_…` / `pk_test_…`.
2. Webhook : endpoint `https://market.indpns.com/payments/webhook/stripe/`, évènements `checkout.session.completed` et `checkout.session.async_payment_succeeded` → copier le *signing secret* dans `STRIPE_WEBHOOK_SECRET`.
3. Local : `stripe listen --forward-to localhost:8000/payments/webhook/stripe/`.
4. Définir `PAYMENT_PROVIDER=stripe`. Tester avec la carte 4242 4242 4242 4242.
5. Production : clés `live`, nouveau webhook live, rotation des secrets de test.
**Important** : ce projet encaisse via Stripe Checkout mais **n'exécute pas** les virements vendeurs (Stripe Connect Transfers non implémenté). Les reversements sont suivis dans le journal, approuvés puis marqués payés manuellement. Consultez un conseiller juridique/financier sur la détention de fonds de tiers.

## 6. PayPal
Adaptateur non implémenté (`is_configured()` retourne toujours `False`). Docs : https://developer.paypal.com/docs/

## 7. OAuth Google / GitHub
Non implémenté (boutons désactivés). Prévu : https://developers.google.com/identity/protocols/oauth2 · https://docs.github.com/en/apps/oauth-apps

## 8. ClamAV (optionnel)
Déployez un conteneur `clamav/clamav` (port 3310), puis `ANTIVIRUS_ENABLED=true`, `ANTIVIRUS_CLAMD_HOST=…`. Avec `ANTIVIRUS_REQUIRED=true`, aucun fichier non scanné n'est publié ni téléchargeable.
