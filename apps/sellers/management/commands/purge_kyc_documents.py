"""Supprime les IMAGES des pièces d'identité des dossiers déjà traités (approuvés ou refusés) depuis plus de N jours.
Le dossier (identité déclarée, décision, dates) est conservé pour l'historique ; seules les images sont effacées (minimisation des données).

    python manage.py purge_kyc_documents --days 90          # supprime
    python manage.py purge_kyc_documents --days 90 --dry-run # affiche seulement
Les dossiers en attente ne sont JAMAIS touchés."""
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.sellers.models import KycDocument


class Command(BaseCommand):
    help = "Supprime les images KYC des dossiers traités depuis plus de N jours."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, required=True, help="Âge minimal (jours) depuis la décision.")
        parser.add_argument("--dry-run", action="store_true", help="Compte sans supprimer.")

    def handle(self, *args, **opts):
        days = opts["days"]
        if days < 1:
            raise CommandError("--days doit être >= 1.")
        cutoff = timezone.now() - timedelta(days=days)
        qs = KycDocument.objects.exclude(data=None).filter(verification__status__in=("approved", "rejected"), verification__reviewed_at__lt=cutoff)
        n = qs.count()
        if opts["dry_run"]:
            self.stdout.write(f"{n} image(s) seraient supprimées (décision antérieure au {cutoff:%Y-%m-%d}).")
            return
        qs.update(data=None)
        self.stdout.write(self.style.SUCCESS(f"{n} image(s) supprimée(s)."))
