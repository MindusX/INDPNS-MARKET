"""sync_schema : synchronisation automatique et additive du schéma au démarrage."""
from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase

from apps.accounts.models import User


class SyncSchemaTests(TransactionTestCase):
    def columns(self):
        with connection.cursor() as cursor:
            return {c.name for c in connection.introspection.get_table_description(cursor, User._meta.db_table)}

    def run_cmd(self, *args):
        out = StringIO()
        call_command("sync_schema", *args, stdout=out, stderr=StringIO())
        return out.getvalue()

    def test_noop_when_schema_is_up_to_date(self):
        self.assertIn("à jour", self.run_cmd())

    def test_adds_missing_column_then_is_idempotent(self):
        with connection.schema_editor() as editor:           # simule une base créée AVANT l'ajout du champ
            editor.remove_field(User, User._meta.get_field("headline"))
        self.assertNotIn("headline", self.columns())

        self.assertIn("headline", self.run_cmd("--check"))   # --check annonce le changement…
        self.assertNotIn("headline", self.columns())         # …mais ne modifie rien

        self.assertIn("Synchronisé", self.run_cmd())
        self.assertIn("headline", self.columns())
        self.assertIn("à jour", self.run_cmd())              # relancée : plus rien à faire
