# Envoi des e-mails avec l'API Brevo (INDPNS Market)

INDPNS Market envoie **tous** ses e-mails par l'API HTTPS de Brevo (`POST https://api.brevo.com/v3/smtp/email`),
sans connexion SMTP : plus de blocage des ports SMTP sur Render. C'est le même principe que Mindus Forge.

## Fonctionnement

- `apps/notifications/brevo.py` : client Brevo (bibliothèque standard, aucune nouvelle dépendance) et backend Django `BrevoEmailBackend`.
- `config/settings/base.py` : si `BREVO_API_KEY` est définie, `EMAIL_BACKEND` = `apps.notifications.brevo.BrevoEmailBackend`.
  Sans clé : SMTP historique si `EMAIL_HOST` est défini, sinon affichage console (développement).
- Tous les envois existants passent par ce backend, sans changement de code métier :
  confirmation d'e-mail et e-mail de commande (`apps.notifications.services.send_email`, via Celery si Redis est configuré),
  réinitialisation de mot de passe (vues Django).
- Expéditeur : `MAIL_FROM` (sinon `DEFAULT_FROM_EMAIL`, ancien nom conservé pour compatibilité).
- Délai d'attente de 15 s (`BREVO_TIMEOUT`). La clé n'est jamais écrite dans les logs ni dans les erreurs.
- Worker Celery : les erreurs temporaires (réseau, 429, 5xx) sont réessayées (3 fois) ; les erreurs définitives (4xx : expéditeur non validé, adresse invalide…) ne le sont pas.

## 1. Configurer Brevo

1. Créez un compte sur https://www.brevo.com.
2. **Expéditeurs, domaines et IP → Expéditeurs** : ajoutez et validez l'adresse d'expédition (ex. `no-reply@indpns.com`).
   Pour une bonne délivrabilité, authentifiez aussi le domaine (SPF, DKIM, DMARC).
3. **SMTP et API → Clés API** : créez une clé API (`xkeysib-…`). Ne la committez jamais.
4. Si la sécurité des adresses IP autorisées est active dans Brevo (Sécurité → Adresses IP autorisées), désactivez-la
   ou autorisez les IP sortantes de Render, sinon l'API répond 401.

## 2. Configurer Render

À renseigner dans le Web Service **et** le Background Worker (Environment) :

| Variable | Valeur |
|---|---|
| `BREVO_API_KEY` | votre clé API Brevo (secret) |
| `MAIL_FROM` | `INDPNS Market <no-reply@indpns.com>` (adresse validée dans Brevo) |
| `DEFAULT_FROM_EMAIL` | facultatif, utilisé seulement si `MAIL_FROM` est vide |
| `BREVO_TIMEOUT` | facultatif, 15 par défaut |

Les anciennes variables `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` ne sont plus déclarées dans `render.yaml`
et peuvent être supprimées dans Render. `render.yaml` ne contient aucune vraie clé (`sync: false`).
Après modification, redéployez le Web Service et le Worker.

## 3. Vérifier

1. Créez un compte de test : le message « Confirm your email » doit arriver.
2. Testez « Mot de passe oublié ».
3. En cas de problème, consultez les logs Render : `Brevo send failed: Brevo API error 401 …` (clé ou IP),
   `… 400 … sender` (expéditeur non validé), `Brevo network error: …` (réseau).
4. Brevo → Logs transactionnels : statut de chaque e-mail.

## 4. Tests

```
python manage.py test tests apps
```

Les tests Brevo (`apps/notifications/tests/test_brevo.py`) simulent l'API : aucun e-mail réel, aucune vraie clé.

## Limites

- Les pièces jointes ne sont prises en charge que sous la forme `(nom, contenu, type)` (`msg.attach(...)`) ; les objets MIME ne sont pas transmis.
- Une seule adresse `Reply-To` est transmise (limite de l'API Brevo).
- Le plan gratuit de Brevo a un quota quotidien d'envois.
