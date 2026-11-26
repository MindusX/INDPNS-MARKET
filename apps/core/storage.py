"""Stockage privé des fichiers vendus (jamais sous MEDIA_ROOT, jamais public)."""
import mimetypes
from urllib.parse import urljoin

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.encoding import filepath_to_uri


def private_storage():
    if settings.S3_ENABLED:
        from storages.backends.s3boto3 import S3Boto3Storage

        class PrivateS3Storage(S3Boto3Storage):
            default_acl = "private"
            querystring_auth = True
            file_overwrite = False
            location = "private"

        return PrivateS3Storage()
    settings.PRIVATE_FILES_ROOT.mkdir(parents=True, exist_ok=True)
    return FileSystemStorage(location=str(settings.PRIVATE_FILES_ROOT), base_url=None)


def public_media_storage():
    if settings.S3_ENABLED:
        from storages.backends.s3boto3 import S3Boto3Storage

        class PublicS3Storage(S3Boto3Storage):
            default_acl = "public-read"
            querystring_auth = False
            file_overwrite = False
            location = "public"

        return PublicS3Storage()
    return FileSystemStorage()


class DatabaseStorage(Storage):
    """Stockage des médias PUBLICS dans la base de données (table core_storedfile), servis par apps.core.views.stored_media.
    Persistant sans S3 : les images de profil, couvertures et logos survivent aux déploiements Render.
    Utilisé automatiquement en production quand S3 n'est pas configuré (config/settings/production.py)."""

    @staticmethod
    def _norm(name):
        return str(name).replace("\\", "/").lstrip("/")

    def _model(self):
        from .models import StoredFile      # import tardif : le stockage est instancié avant le chargement des modèles
        return StoredFile

    def _open(self, name, mode="rb"):
        row = self._model().objects.filter(name=self._norm(name)).first()
        if row is None:
            raise FileNotFoundError(name)
        return ContentFile(bytes(row.content), name=name)

    def _save(self, name, content):
        name = self._norm(name)
        data = b"".join(content.chunks())
        ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        self._model().objects.update_or_create(name=name, defaults={"content": data, "size": len(data), "content_type": ctype})
        return name

    def delete(self, name):
        if name:
            self._model().objects.filter(name=self._norm(name)).delete()

    def exists(self, name):
        return self._model().objects.filter(name=self._norm(name)).exists()

    def size(self, name):
        row = self._model().objects.filter(name=self._norm(name)).only("size").first()
        if row is None:
            raise FileNotFoundError(name)
        return row.size

    def url(self, name):
        return urljoin(settings.MEDIA_URL, filepath_to_uri(self._norm(name)))
