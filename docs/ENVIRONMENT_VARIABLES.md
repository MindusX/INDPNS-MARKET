# Variables d'environnement

Sur Render : *Dashboard → service → Environment*. En local : fichier `.env` (copie de `.env.example`).
Les valeurs d'exemple ci-dessous sont **fictives**.

| Variable | Utilité | Obligatoire | Où l'obtenir | Exemple |
|---|---|---|---|---|
| `ENVIRONMENT` | Étiquette d'environnement | Non | — | `production` |
| `DEBUG` | Mode debug (jamais `true` en prod : le démarrage échoue) | Non | — | `false` |
| `SECRET_KEY` | Clé secrète Django | **Oui (prod)** | `python -c "import secrets;print(secrets.token_urlsafe(64))"` ; Render peut la générer (`render.yaml`) | `xxxxxxxx` |
| `ALLOWED_HOSTS` | Hôtes autorisés (virgules) | Oui (prod) | — | `market.indpns.com` |
| `CSRF_TRUSTED_ORIGINS` | Origines HTTPS de confiance | Oui (prod) | — | `https://market.indpns.com` |
| `SITE_URL` | URL publique (liens e-mails, QR code) | Oui | — | `https://market.indpns.com` |
| `FRONTEND_URL` | Réservée (non utilisée : SSR) | Non | — | |
| `DATABASE_URL` | Connexion PostgreSQL Neon | **Oui (prod)** | Neon → Connection Details | `postgresql://u:p@ep-x-pooler.eu-central-1.aws.neon.tech/db?sslmode=require` |
| `NEON_DATABASE_URL` | Alias si `DATABASE_URL` est vide | Non | idem | |
| `DATABASE_SSL_REQUIRE` | Force SSL (défaut `true` en prod) | Non | — | `true` |
| `DATABASE_POOLED` | Force le mode PgBouncer (auto-détecté si l'hôte contient `-pooler`) | Non | — | `false` |
| `DB_CONN_MAX_AGE` | Durée de vie des connexions (s) | Non | — | `60` |
| `REDIS_URL` | Cache + Celery (sans Redis : cache mémoire, tâches synchrones) | Recommandée | Render Redis (liée dans `render.yaml`) | `redis://…` |
| `WEB_CONCURRENCY` | Workers Gunicorn | Non | — | `2` |
| `GUNICORN_TIMEOUT` | Timeout Gunicorn (s) | Non | — | `60` |
| `EMAIL_HOST` `EMAIL_PORT` `EMAIL_HOST_USER` `EMAIL_HOST_PASSWORD` `EMAIL_USE_TLS` | SMTP (sans `EMAIL_HOST` : e-mails affichés en console → **les utilisateurs ne recevront rien**) | **Oui (prod)** | Votre fournisseur SMTP | `smtp.example.com` |
| `DEFAULT_FROM_EMAIL` | Expéditeur | Oui | domaine vérifié (SPF/DKIM) | `INDPNS Market <no-reply@indpns.com>` |
| `EMAIL_VERIFICATION_REQUIRED` | Confirmation e-mail obligatoire (défaut `true`) | Non | — | `true` |
| `AWS_STORAGE_BUCKET_NAME` `AWS_ACCESS_KEY_ID` `AWS_SECRET_ACCESS_KEY` `AWS_S3_ENDPOINT_URL` `AWS_S3_REGION_NAME` | Stockage S3-compatible (fichiers vendus privés + visuels publics). Sans eux : disque local **éphémère sur Render** | **Oui (prod)** | AWS S3 / Cloudflare R2 / Backblaze B2 | |
| `DOWNLOAD_LINK_TTL` | Durée de vie des liens de téléchargement (s) | Non | — | `300` |
| `PAYMENT_PROVIDER` | `stripe` ou vide (= mode catalogue) | Non | — | `stripe` |
| `STRIPE_SECRET_KEY` `STRIPE_PUBLISHABLE_KEY` `STRIPE_WEBHOOK_SECRET` | Stripe | Si Stripe | dashboard.stripe.com | `sk_test_…` |
| `PAYPAL_*` | Réservées : l'adaptateur PayPal n'est **pas implémenté** | Non | | |
| `PAYOUT_HOLD_DAYS` / `MIN_PAYOUT_AMOUNT` | Délai de rétention avant retrait / minimum | Non | — | `14` / `20.00` |
| `SUBSCRIPTIONS_ENABLED` | Réservée : facturation d'abonnements non implémentée | Non | | `false` |
| `GOOGLE_CLIENT_ID` `GITHUB_CLIENT_ID` | Réservées : OAuth non implémenté (boutons désactivés) | Non | | |
| `ANTIVIRUS_ENABLED` `ANTIVIRUS_REQUIRED` `ANTIVIRUS_CLAMD_HOST` `ANTIVIRUS_CLAMD_PORT` | ClamAV (clamd) | Non | serveur clamd à héberger | |
| `MAX_PRODUCT_FILE_MB` `MAX_IMAGE_MB` `BLOCKED_ARCHIVE_EXTENSIONS` … | Limites d'upload | Non | — | `200` |
| `ADMIN_URL` | Chemin de l'admin Django (changez-le) | Non | — | `gestion-7f3k/` |
| `SENTRY_DSN` | Suivi d'erreurs | Non | sentry.io | |
| `BOOTSTRAP_MIGRATIONS` | `1` = génère les migrations initiales au build si le dépôt n'en a pas | Non | — | `0` |
