from django.core import signing

SALT = "indpns.email-verify"
MAX_AGE = 60 * 60 * 48


def make_verify_token(user):
    return signing.dumps({"uid": user.pk, "email": user.email}, salt=SALT)


def read_verify_token(token):
    """Retourne le dict du token ou None si invalide/expiré."""
    try:
        return signing.loads(token, salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature:
        return None
