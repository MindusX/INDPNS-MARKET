"""Synchronise AUTOMATIQUEMENT le schéma de la base avec les modèles Django, à chaque démarrage du service.

Pourquoi ? Les migrations ne sont pas commitées dans le dépôt : elles sont régénérées à chaque démarrage du conteneur et
Django considère « 0001_initial » comme déjà appliquée. Un champ ou un modèle ajouté après la première installation n'était
donc jamais créé en base (erreur « column … does not exist »). Cette commande comble ce manque, de façon SÛRE :

  * additive uniquement : elle crée les tables manquantes et ajoute les colonnes manquantes ;
  * elle ne supprime ni ne modifie jamais rien (aucune perte de données possible) ;
  * idempotente : relancée sur une base à jour, elle ne fait rien ;
  * utilise le schema_editor de Django : mêmes types, contraintes d'unicité, index et clés étrangères qu'une migration.

Options : --check affiche ce qui serait fait sans rien modifier.
Elle reste inoffensive le jour où les migrations seront commitées : plus rien ne manquera, elle n'aura rien à faire."""
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


def _models():
    for model in apps.get_models():          # exclut les tables « through » auto-créées : create_model les gère avec leur modèle
        meta = model._meta
        if meta.proxy or not meta.managed or meta.swapped:
            continue
        yield model


def _auto_through_models(model):
    for f in model._meta.local_many_to_many:
        through = f.remote_field.through
        if through._meta.auto_created:
            yield through


class Command(BaseCommand):
    help = "Crée les tables et colonnes manquantes (additif, idempotent, sans suppression)."

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true", help="Affiche les changements nécessaires sans les appliquer.")

    def _tables(self):
        with connection.cursor() as cursor:
            return set(connection.introspection.table_names(cursor))

    def _columns(self, table):
        with connection.cursor() as cursor:
            return {c.name for c in connection.introspection.get_table_description(cursor, table)}

    def handle(self, *args, **options):
        check, errors, changes = options["check"], [], []

        # ---- Phase 1 : tables manquantes (une seule transaction : les clés étrangères entre nouvelles tables sont différées) ----
        tables = self._tables()
        new_models = [m for m in _models() if m._meta.db_table not in tables]
        if new_models:
            changes += [f"table {m._meta.db_table}" for m in new_models]
            if not check:
                try:
                    with connection.schema_editor() as editor:
                        for m in new_models:
                            editor.create_model(m)
                except Exception as exc:                      # noqa: BLE001 - on continue pour signaler tout le reste
                    errors.append(f"création des tables {[m._meta.db_table for m in new_models]} : {exc}")
            tables = self._tables()

        # ---- Phase 2 : colonnes manquantes, table par table (un problème n'empêche pas les autres) ----
        for model in _models():
            table = model._meta.db_table
            if table not in tables:
                continue
            existing = self._columns(table)
            missing = [f for f in model._meta.local_concrete_fields if f.column not in existing]
            through_missing = [t for t in _auto_through_models(model) if t._meta.db_table not in tables]
            if not missing and not through_missing:
                continue
            changes += [f"colonne {table}.{f.column}" for f in missing] + [f"table {t._meta.db_table}" for t in through_missing]
            if check:
                continue
            try:
                with connection.schema_editor() as editor:
                    for f in missing:
                        editor.add_field(model, f)
                    for t in through_missing:
                        editor.create_model(t)
                tables = self._tables()
            except Exception as exc:                          # noqa: BLE001
                errors.append(f"{table} : {exc}")

        if not changes:
            self.stdout.write("Schéma à jour : rien à synchroniser.")
        else:
            verb = "À synchroniser" if check else "Synchronisé"
            self.stdout.write(self.style.SUCCESS(f"{verb} ({len(changes)}) : " + ", ".join(changes)))
        if errors:
            for e in errors:
                self.stderr.write(self.style.ERROR("ÉCHEC " + e))
            raise CommandError(f"{len(errors)} élément(s) n'ont pas pu être synchronisés (voir ci-dessus).")
